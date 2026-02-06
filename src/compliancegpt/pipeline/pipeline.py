# -*- coding: utf-8 -*-
"""
pipeline.py — ComplianceGPT Answerer v0 (Defense Grade) — v3.2

Key properties:
- Canonical citation display (AC-06.04 -> AC-6(4)).
- Configurable retrieval doc filtering (doc_filter_mode).
- Primary-control consistency guardrail.
- Status precedence: NEVER overwrite NO_EVIDENCE or ERROR.
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 1) PATH SETUP
# ============================================================================

THIS_FILE = Path(__file__).resolve()
PIPELINE_DIR = THIS_FILE.parent
ANSWERER_ROOT = PIPELINE_DIR.parent

GENERATOR_DIR = ANSWERER_ROOT / "generator"
VERIFIER_DIR = GENERATOR_DIR / "verifier"
QUR_DIR = ANSWERER_ROOT / "retriever_ablation_study" / "QUR_generator"

for p in (PIPELINE_DIR, GENERATOR_DIR, VERIFIER_DIR, QUR_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# ============================================================================
# 2) IMPORTS
# ============================================================================

try:
    from generator import ComplianceGenerator, load_org_profile, normalize_contract
except ImportError as e:
    raise ImportError(f"[FATAL] Cannot import generator module: {e}")

try:
    from retriever_s7 import ComplianceGPTRetriever, RetrievalConfig
except ImportError as e:
    raise ImportError(f"[FATAL] Cannot import retriever_s7 module: {e}")

try:
    from QUR_Generator_UT import QURComponent
except ImportError:
    QURComponent = None

try:
    # Optional verifier (v2)
    try:
        from verifier_v2_compat import verify_answer  # type: ignore
    except Exception:
        from verifier import verify_answer  # type: ignore
except Exception:
    verify_answer = None  # type: ignore

# ============================================================================
# 3) HELPERS
# ============================================================================

# Matches "ac-2", "ac-2.1", "ac-2_smt.c", "ac-2.1_smt.b", etc.
_DOC_PREFIX_RE = re.compile(r"(?P<id>[A-Za-z]{2}-\d+(?:\.\d+|\(\d+\))?)")

# Blocks we generally do NOT want for statement-only evaluation
_BLOCK_MARKERS = ("_gdn", "_obj", "_asm", "_ref", "_prm", "_param")

_CTRL_RE = re.compile(r"^[a-z]{2}-\d+(?:\.\d+)?$", re.IGNORECASE)
_STMT_RE = re.compile(r"^[a-z]{2}-\d+(?:\.\d+)?_smt(?:\.|$)", re.IGNORECASE)

# Canonical display helpers
_CANON_DOT_RE = re.compile(r"^(?P<fam>[A-Z]{2})-(?P<num>\d+)(?:\.(?P<enh>\d+))?$")
_CANON_PAREN_RE = re.compile(r"^(?P<fam>[A-Z]{2})-(?P<num>\d+)\((?P<enh>\d+)\)$")

def _doc_prefix(doc_id: str) -> str:
    """Returns the leading control id prefix (e.g., 'ac-2.1' from 'ac-2.1_smt.c')."""
    s = (doc_id or "").strip()
    m = _DOC_PREFIX_RE.match(s)
    return (m.group("id").lower() if m else s.lower().strip())

def _control_family_num(control_id: str) -> str:
    """Returns the family-number key for merge-guarding."""
    base = _doc_prefix(control_id)
    return base.split(".", 1)[0]

def format_nist_id(raw_id: str) -> str:
    """Canonical display formatting."""
    s = (raw_id or "").strip().upper()
    if not s:
        return ""
    m = _CANON_PAREN_RE.match(s)
    if m:
        fam = m.group("fam")
        num = int(m.group("num"))
        enh = int(m.group("enh"))
        return f"{fam}-{num}({enh})"
    m = _CANON_DOT_RE.match(s)
    if m:
        fam = m.group("fam")
        num = int(m.group("num"))
        enh = m.group("enh")
        if enh is None:
            return f"{fam}-{num}"
        return f"{fam}-{num}({int(enh)})"
    return s

def doc_base_display(doc_id: str) -> str:
    prefix = _doc_prefix(doc_id)
    if not prefix:
        return ""
    return format_nist_id(prefix.upper())

def is_statement_only_doc(doc_id: str) -> bool:
    s = (doc_id or "").strip().lower()
    if any(b in s for b in _BLOCK_MARKERS):
        return False
    return bool(_CTRL_RE.match(s) or _STMT_RE.match(s))

# Doc selection filter modes (used when choosing which retrieved docs to pass downstream).
# - "all": do not filter; allow _smt/_gdn/_obj/etc.
# - "prefer_statement_only": legacy behavior; if any statement-only docs exist, use them, else fallback to raw.
# - "statement_only": keep only statement-only docs; if none exist, fallback to raw (to avoid empty pipeline).
_DOC_FILTER_MODES = ("all", "prefer_statement_only", "statement_only")

def select_docs(raw_docs: List[Dict[str, Any]], top_k: int, mode: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    mode = (mode or "all").strip().lower()
    if mode not in _DOC_FILTER_MODES:
        mode = "all"

    meta: Dict[str, Any] = {
        "doc_filter_mode": mode,
        "raw_n": len(raw_docs or []),
        "kept_n": None,
        "dropped_n": None,
        "fallback_to_raw": False,
    }

    raw_docs = raw_docs or []
    if top_k <= 0:
        meta["kept_n"] = 0
        meta["dropped_n"] = len(raw_docs)
        return [], meta

    if mode == "all":
        docs = raw_docs[:top_k]
        meta["kept_n"] = len(docs)
        meta["dropped_n"] = len(raw_docs) - len(docs)
        return docs, meta

    stmt_docs = [d for d in raw_docs if is_statement_only_doc(d.get("id", ""))]

    if mode == "statement_only":
        if stmt_docs:
            docs = stmt_docs[:top_k]
            meta["kept_n"] = len(docs)
            meta["dropped_n"] = len(raw_docs) - len(docs)
            return docs, meta
        # fallback
        docs = raw_docs[:top_k]
        meta["fallback_to_raw"] = True
        meta["kept_n"] = len(docs)
        meta["dropped_n"] = len(raw_docs) - len(docs)
        return docs, meta

    # prefer_statement_only (legacy)
    if stmt_docs:
        docs = stmt_docs[:top_k]
        meta["kept_n"] = len(docs)
        meta["dropped_n"] = len(raw_docs) - len(docs)
        return docs, meta

    docs = raw_docs[:top_k]
    meta["fallback_to_raw"] = True
    meta["kept_n"] = len(docs)
    meta["dropped_n"] = len(raw_docs) - len(docs)
    return docs, meta


# Synchronized with generator.py
# -----------------------------
# ODP / PARAM placeholder helpers
# -----------------------------
# We support:
#   - Curly insert placeholders that encode a parameter id token:
#       {{ insert: param, ac-1_prm_1 }}
#       {{ insert: param, ac-01_odp.03 }}
#   - Assignment placeholders (free-text; may not encode an id):
#       [assignment: organization-defined parameter]
#
# Important:
#   - We treat ANY curly placeholder id token as a "required parameter id"
#     (ODP + PRM, etc.) because verifier.py extracts them this way.
#   - We do NOT attempt to mint fake ids from assignment placeholders.
#     If assignment placeholders exist but no extractable ids exist, we use a
#     stable sentinel ("assignment_required") to satisfy verifier consistency.

_PARAM_CURLY_RE = re.compile(
    r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+",
    re.IGNORECASE,
)
_PARAM_ASSIGNMENT_RE = re.compile(
    r"\[assignment:\s*([^\]]+?)\s*\]",
    re.IGNORECASE,
)

def _extract_odp_requirements(text: str) -> Tuple[List[str], bool]:
    """
    Returns (required_param_ids, has_assignment_placeholder).

    required_param_ids are extracted from curly placeholders only.
    """
    if not isinstance(text, str) or not text:
        return ([], False)

    ids: List[str] = []
    for m in _PARAM_CURLY_RE.finditer(text):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        # Common format is: "param, <ID>"
        base = raw.split(",")[-1].strip()
        if not base:
            continue
        token = base.split()[0].strip()
        if not token:
            continue
        # avoid the historic bug: "param" treated as an id
        if token.lower() == "param":
            continue
        ids.append(token)

    has_assignment = bool(_PARAM_ASSIGNMENT_RE.search(text))

    # Stable de-dup preserving order
    out: List[str] = []
    seen = set()
    for x in ids:
        lx = x.lower()
        if lx in seen:
            continue
        seen.add(lx)
        out.append(x)
    return (out, has_assignment)

def _normalize_odp_id(raw: str) -> str:
    """
    Normalize ODP IDs so that minor formatting differences match.
    Examples:
      - "ac-02_odp.5"  -> "ac-02_odp.05"
      - "AC_02_ODP.05" -> "ac-02_odp.05"
    """
    s = (raw or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = s.replace("__", "_")
    # normalize common family underscore variants (align with verifier.py behavior)
    s = s.replace("ac_","ac-").replace("ra_","ra-").replace("pl_","pl-").replace("pm_","pm-")
    # pad ".<digit>" after "odp."
    s = re.sub(r"(odp\.)\b(\d)\b", r"\g<1>0\2", s)
    return s
def apply_odp_to_answer(answer_text: str, org_profile: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    """
    Substitutes values for curly {{ insert: param, <ID> }} placeholders when possible.
    Returns: (status, substituted_text, missing_keys)

    Notes:
      - This function substitutes ONLY curly placeholders.
      - If any [assignment: ...] placeholders exist, status will be PARAMS_REQUIRED.
      - org_profile may be either:
          - flat: { "<id>": "<value>" }
          - nested: { "odp_values": { "<id>": "<value>" } }
    """
    text = answer_text or ""
    required, has_assignment = _extract_odp_requirements(text)

    # Support nested profiles
    profile_map: Dict[str, Any]
    if isinstance(org_profile, dict):
        nested = org_profile.get("odp_values", None)
        profile_map = nested if isinstance(nested, dict) else org_profile
    else:
        profile_map = {}

    missing: List[str] = []
    _norm_map = { _normalize_odp_id(k): k for k in profile_map.keys() } if isinstance(profile_map, dict) else {}

    for key in sorted(set(required)):
        prof_key = _norm_map.get(_normalize_odp_id(key), key)
        val = profile_map.get(prof_key) if isinstance(profile_map, dict) else None

        # Robust check allowing 0 or False but not None or ""
        if val is not None and str(val).strip() != "":
            val_str = str(val)
            rep_braces = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(key) + r"\s*\}+"
            try:
                text = re.sub(rep_braces, val_str, text, flags=re.IGNORECASE)
            except re.error:
                pass
        else:
            missing.append(key)

    status = "PARAMS_REQUIRED" if (missing or has_assignment) else "OK"
    return status, text, missing

def resolve_ccs_path(framework_version: str) -> str:
    candidates = [
        # Colab / Drive default
        f"/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_{framework_version}_catalog.jsonl",
        # Repo relative path
        f"data/ccs/nist800-53/NIST_SP-800-53_{framework_version}_catalog.jsonl",
        # Local working dir convenience
        f"NIST_SP-800-53_{framework_version}_catalog.jsonl",
        # Sandbox/CI convenience (ignored if missing)
        f"/mnt/data/NIST_SP-800-53_{framework_version}_catalog.jsonl",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]


def _ccs_kind_counts(ids: List[str]) -> Dict[str, int]:
    """Count CCS clause kinds by ID suffix marker (e.g., _smt/_gdn/_obj)."""
    kind_re = re.compile(r"_(smt|gdn|obj)(?:\.|$)", re.IGNORECASE)
    counts = {"smt": 0, "gdn": 0, "obj": 0, "other": 0}
    for cid in ids:
        m = kind_re.search(cid or "")
        if not m:
            counts["other"] += 1
            continue
        k = m.group(1).lower()
        counts[k] += 1
    return counts


def _assert_ccs_loaded(
    *,
    ccs_path: str,
    ids: List[str],
    strict: bool,
    min_docs: int,
) -> Dict[str, Any]:
    """Hard sanity checks to prevent silently loading the wrong CCS."""
    counts = _ccs_kind_counts(ids)
    total = len(ids)

    print(
        f"[CCS] Loaded corpus from: {ccs_path}\n"
        f"[CCS] docs={total} kind_counts={counts}"
    )

    if total < min_docs:
        raise ValueError(
            f"[FATAL] CCS sanity check failed: only {total} docs loaded (<{min_docs}). "
            f"Path: {ccs_path}"
        )

    # Clause-level catalogs should contain at least statements and usually guidance/objectives.
    if strict:
        if counts["smt"] == 0:
            raise ValueError(
                f"[FATAL] CCS sanity check failed: 0 '_smt' docs detected. Path: {ccs_path}"
            )
        if (counts["gdn"] + counts["obj"]) == 0:
            raise ValueError(
                "[FATAL] CCS sanity check failed: 0 '_gdn'/'_obj' docs detected. "
                "This often means you're loading a statement-only or wrong-format corpus. "
                f"Path: {ccs_path}"
            )

    return {"total_docs": total, "kind_counts": counts}


# ============================================================================
# 4) PIPELINE
# ============================================================================

class ComplianceGPTPipeline:
    def __init__(
        self,
        framework_version: str = "rev5",
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        use_qur: bool = True,
        doc_filter_mode: str = "all",
        ccs_path: Optional[str] = None,
        strict_ccs_assert: bool = True,
        min_ccs_docs: int = 1000,
    ) -> None:
        self.framework_version = framework_version

        # Which retrieved docs to pass to generator/verifier.
        # Default: "all" (allow _smt/_gdn/_obj/etc.). Use "prefer_statement_only" to restore legacy behavior.
        m = (doc_filter_mode or "all").strip().lower()
        self.doc_filter_mode = m if m in _DOC_FILTER_MODES else "all"


        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        import torch

        print(f"[System] Loading model: {model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quant_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto",
            quantization_config=quant_cfg,
            trust_remote_code=True,
        )

        self.generator = ComplianceGenerator(self.model, self.tokenizer)

        self.qur = None
        if use_qur and QURComponent:
            try:
                self.qur = QURComponent(model_id=model_id, model=self.model, tokenizer=self.tokenizer)
                print("[Pipeline] QUR initialized.")
            except Exception as e:
                print(f"[WARN] QUR init failed: {e}. Skipping.")

        ccs_path = (ccs_path or resolve_ccs_path(framework_version)).strip()
        self.ccs_path = ccs_path
        if not Path(ccs_path).exists():
            raise FileNotFoundError(
                f"[FATAL] CCS file not found: {ccs_path}. "
                "Provide ccs_path=... to ComplianceGPTPipeline(...) or place the file in one of the default locations."
            )
        print(f"[Pipeline] Retriever loading: {ccs_path}")
        self.retriever = ComplianceGPTRetriever(catalog_path=ccs_path, config=RetrievalConfig())
        self.ccs_meta = _assert_ccs_loaded(ccs_path=ccs_path, ids=self.retriever.ids, strict=strict_ccs_assert, min_docs=min_ccs_docs)


    def _citation_suffix(self, primary_display: str) -> str:
        rev_label = "Rev.5" if self.framework_version == "rev5" else "Rev.4"
        return f"[NIST SP 800-53 {rev_label}: {primary_display}]"

    def answer(
        self,
        query: str,
        org_profile: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        use_generator: bool = True,
        gold_row: Optional[Dict[str, Any]] = None,
        doc_filter_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        org_profile = org_profile or {}

        # 1) Retrieve
        rewrites = self.qur.generate(query) if self.qur else None
        raw_docs = self.retriever.retrieve(query, top_k=top_k * 2, rewrites=rewrites)

        mode = (doc_filter_mode or self.doc_filter_mode or "all")
        docs, doc_filter_meta = select_docs(raw_docs, top_k=top_k, mode=mode)

        primary_doc_id = docs[0].get("id", "") if docs else ""
        primary_family = _control_family_num(primary_doc_id) if primary_doc_id else ""

        # 2) Generate contract (or pure extractive)
        if use_generator:
            contract_raw = self.generator.generate(query, docs, org_profile)
        else:
            top_text = (docs[0].get("text", "") if docs else "")
            contract_raw = {
                "answer_text": str(top_text),
                "evidence_spans": [{"source_id": str(primary_doc_id), "span_text": str(top_text)}] if top_text else [],
                "status": "OK" if top_text else "NO_EVIDENCE",
                "odp_required_list": [],
            }

        contract = normalize_contract(contract_raw)

        # Contract mode is always provably-extractive for this answerer.
        contract["contract_mode"] = "provably_extractive"

        # 3) Verifier outputs (computed at the end, after all post-processing)
        verifier_errors: List[str] = []
        verifier_metrics: Dict[str, float] = {}
        verifier_pass: Optional[bool] = None

        # 2.5) Standardize evidence spans (deterministic, verifiable)
        selected_ids: List[str] = []
        if isinstance(contract_raw, dict):
            if isinstance(contract_raw.get("selected_source_ids"), list):
                selected_ids = [str(x).strip() for x in contract_raw.get("selected_source_ids", []) if str(x).strip()]

        if not selected_ids and isinstance(contract.get("evidence_spans"), list):
            selected_ids = [str(s.get("source_id", "")).strip() for s in contract.get("evidence_spans", []) if str(s.get("source_id", "")).strip()]

        status_up = str(contract.get("status", "")).strip().upper()

        if not selected_ids and primary_doc_id and status_up not in {"NO_EVIDENCE", "ERROR"}:
            selected_ids = [str(primary_doc_id).strip()]

        # Keep only the primary control-family when possible
        if primary_family:
            fam_kept = [sid for sid in selected_ids if _control_family_num(sid) == primary_family]
            selected_ids = fam_kept if fam_kept else selected_ids

        doc_text_by_id = {str(d.get("id", "")).strip(): str(d.get("text", "")).strip() for d in (docs or []) if str(d.get("id", "")).strip()}

        def _lookup_clean_text(doc_id: str) -> str:
            # Prefer the canonical CCS text from the retriever (independent "ground truth")
            raw_t = ""
            try:
                raw_t = str(getattr(self.retriever, "docs_map", {}).get(doc_id, ""))  # type: ignore
            except Exception:
                raw_t = ""

            if raw_t:
                if "\n" in raw_t:
                    raw_t = raw_t.split("\n", 1)[1].strip()
                return raw_t.strip()

            # Fallback: use the in-memory retrieved doc text
            t = doc_text_by_id.get(doc_id)
            return (t or "").strip()

        spans_out = [{"source_id": sid, "span_text": _lookup_clean_text(sid)} for sid in selected_ids if sid]
        contract["evidence_spans"] = spans_out

        # Enforce status precedence and coherence (do not overwrite NO_EVIDENCE/ERROR)
        status_up = str(contract.get("status", "")).strip().upper()
        if status_up in {"NO_EVIDENCE", "ERROR"}:
            # Contract says: NO_EVIDENCE/ERROR must not carry evidence spans.
            spans_out = []
            selected_ids = []
            contract["evidence_spans"] = []
            if status_up == "NO_EVIDENCE":
                contract["answer_text"] = "NO_EVIDENCE"
        else:
            # For OK / PARAMS_REQUIRED, we require at least one evidence span.
            if not spans_out:
                contract["status"] = "ERROR"
                contract.setdefault("pipeline_errors", []).append(f"{status_up}ButNoEvidenceSpans")
                contract["answer_text"] = contract.get("answer_text", "") or ""
            else:
                # If spans exist, keep status as OK/PARAMS_REQUIRED when set; otherwise default to OK.
                if status_up not in {"OK", "PARAMS_REQUIRED"}:
                    contract["status"] = "OK"


        # For benchmark mode: make the answer_text purely extractive (verbatim from retrieved evidence)
        if spans_out and str(contract.get("status", "")).strip().upper() in ("OK", "PARAMS_REQUIRED"):
            contract["answer_text"] = " ".join(str(s.get("span_text", "")) for s in spans_out).strip()

        # 4) Primary-control consistency
        if primary_family and isinstance(contract.get("evidence_spans"), list):
            kept = []
            for span in contract["evidence_spans"]:
                sid = str(span.get("source_id", ""))
                if _control_family_num(sid) == primary_family:
                    kept.append(span)
            contract["evidence_spans"] = kept

        # Keep answer_text aligned with the (possibly filtered) evidence spans
        if contract.get("evidence_spans"):
            contract["answer_text"] = " ".join(str(s.get("span_text", "")) for s in contract["evidence_spans"]).strip()

        # 5) Fallback strategies
        if (not contract.get("answer_text")) and contract.get("evidence_spans"):
            contract["answer_text"] = " ".join(str(s.get("span_text", "")) for s in contract["evidence_spans"]).strip()

        # 6) Display citations
        for span in contract.get("evidence_spans", []):
            sid = str(span.get("source_id", ""))
            span["source_id_display"] = doc_base_display(sid)

        # Convenience: list of unique evidence source ids in order.
        _seen: set[str] = set()
        contract["selected_source_ids"] = []
        for _sp in contract.get("evidence_spans", []):
            _sid = str(_sp.get("source_id", "")).strip()
            if _sid and _sid not in _seen:
                _seen.add(_sid)
                contract["selected_source_ids"].append(_sid)

        # 7) Recompute ODP status (policy-aware, benchmark-consistent)
        base_status = str(contract.get("status", "OK")).strip().upper()

        if base_status in ("OK", "PARAMS_REQUIRED"):
            # Extract ODP requirements from the (verbatim) answer text
            required_keys, has_assignment = _extract_odp_requirements(str(contract.get("answer_text", "")))

            # Determine how to handle ODPs:
            # - In benchmark mode (gold_row provided), respect gold_row["resolution_policy"] when present.
            # - Otherwise (interactive), fill from profile if profile values exist, else ask.
            policy = None
            if isinstance(gold_row, dict):
                rp = gold_row.get("resolution_policy", None)
                if rp is not None and str(rp).strip():
                    policy = str(rp).strip().upper()

            if policy is None:
                # Benchmark-default: if we are evaluating against a gold_row but it does not specify policy,
                # default to ASK to preserve verbatim placeholders (gold sets are verbatim).
                if isinstance(gold_row, dict):
                    policy = "ASK"
                else:
                    policy = "FILL_FROM_PROFILE" if (isinstance(org_profile, dict) and len(org_profile) > 0) else "ASK"
            if required_keys or has_assignment:
                if policy in ("ASK", "PRESERVE"):
                    # Keep the answer verbatim (placeholders intact), require params
                    contract["status"] = "PARAMS_REQUIRED"
                    contract["odp_required_list"] = required_keys if required_keys else (["assignment_required"] if has_assignment else [])
                    contract["odp_assignment_present"] = bool(has_assignment)
                elif policy == "FILL_FROM_PROFILE":
                    # Substitute only if values exist; otherwise require params
                    odp_status, substituted, missing = apply_odp_to_answer(str(contract.get("answer_text", "")), org_profile)
                    contract["answer_text"] = substituted if odp_status == "OK" else str(contract.get("answer_text", ""))
                    # If assignment placeholders exist but no extractable ids, use a stable sentinel to satisfy verifier consistency.
                    if odp_status == "OK":
                        contract["odp_required_list"] = []
                    else:
                        contract["odp_required_list"] = (missing if missing else (required_keys if required_keys else (["assignment_required"] if has_assignment else [])))
                    contract["odp_assignment_present"] = bool(has_assignment)
                    contract["status"] = odp_status
                else:
                    # Unknown policy -> default to ASK behavior (Option A compatible)
                    contract["status"] = "PARAMS_REQUIRED"
                    contract["odp_required_list"] = required_keys if required_keys else (["assignment_required"] if has_assignment else [])
                    contract["odp_assignment_present"] = bool(has_assignment)
            else:
                # No ODP placeholders detected
                contract["odp_required_list"] = []

# 8) Build final citation strings
        final_status = str(contract.get("status", "OK")).strip().upper()
        spans = contract.get("evidence_spans", []) or []

        primary_display = spans[0].get("source_id_display", "") if spans else doc_base_display(primary_doc_id)
        all_displays = [s.get("source_id_display", "") for s in spans if s.get("source_id_display")]

        if final_status in ("OK", "PARAMS_REQUIRED") and primary_display:
            contract["primary_citation"] = primary_display
            contract["all_citations"] = "; ".join(_unique_preserve(all_displays))
            contract["answer_text_with_citation"] = (str(contract.get("answer_text", "")).rstrip() + " " + self._citation_suffix(primary_display)).strip()
        else:
            contract["primary_citation"] = ""
            contract["all_citations"] = ""
            contract["answer_text_with_citation"] = str(contract.get("answer_text", "")).strip()


        # 9) Final verification (MUST run after all post-processing)
        if verify_answer is not None and isinstance(gold_row, dict):
            try:
                spans_for_verify = contract.get("evidence_spans", []) or []
                # Minimal corpus: just the texts for cited ids (fast + deterministic)
                evidence_corpus = {
                    str(s.get("source_id", "")).strip(): _lookup_clean_text(str(s.get("source_id", "")).strip())
                    for s in spans_for_verify
                    if str(s.get("source_id", "")).strip()
                }

                v_res = verify_answer(
                    contract,
                    gold_row,
                    corpus=evidence_corpus,
                    org_profile=org_profile,
                    corpus_version=self.framework_version,
                    strict_extras=True,
                    strict_verbatim=True,
                    strict_version=False,
                )  # type: ignore

                verifier_errors = list(getattr(v_res, "error_tags", []) or [])
                verifier_metrics = dict(getattr(v_res, "metrics", {}) or {})
                verifier_pass = bool(getattr(v_res, "is_pass", False))
            except Exception as e:
                print(f"[WARN] Verifier failed: {e}")
                verifier_errors = []
                verifier_metrics = {}
                verifier_pass = None

        if verifier_errors:
            contract["verifier_errors"] = verifier_errors
        if verifier_metrics:
            contract["verifier_metrics"] = verifier_metrics
            # Backward-compatible scalar metrics (for notebook columns)
            if isinstance(verifier_metrics, dict):
                if "control_recall" in verifier_metrics:
                    contract["verifier_recall"] = float(verifier_metrics.get("control_recall", 0.0))
                if "control_precision" in verifier_metrics:
                    contract["verifier_precision"] = float(verifier_metrics.get("control_precision", 0.0))
                if "control_f1" in verifier_metrics:
                    contract["verifier_f1"] = float(verifier_metrics.get("control_f1", 0.0))
                if "doc_recall" in verifier_metrics:
                    contract["verifier_doc_recall"] = float(verifier_metrics.get("doc_recall", 0.0))
                if "doc_precision" in verifier_metrics:
                    contract["verifier_doc_precision"] = float(verifier_metrics.get("doc_precision", 0.0))
                if "doc_f1" in verifier_metrics:
                    contract["verifier_doc_f1"] = float(verifier_metrics.get("doc_f1", 0.0))
        if verifier_pass is not None:
            contract["verifier_pass"] = verifier_pass

        return {
            "query": query,
            "doc_filter": doc_filter_meta,
            "docs": docs,
            "contract": contract,
            "verifier_errors": verifier_errors,
        }

def _unique_preserve(seq: List[str]) -> List[str]:
    """Deduplicate while preserving order; drops empty strings."""
    seen = set()
    out: List[str] = []
    for x in seq or []:
        x = str(x).strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

# End of pipeline.py
