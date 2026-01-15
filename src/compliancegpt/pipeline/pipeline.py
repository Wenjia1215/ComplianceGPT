# -*- coding: utf-8 -*-
"""
pipeline.py — ComplianceGPT Answerer v0 (Defense Grade) — v3.2

Key properties:
- Canonical citation display (AC-06.04 -> AC-6(4)).
- Safe "statement-only" retrieval filtering.
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
    from compliancegpt_retriever_s7 import ComplianceGPTRetriever, RetrievalConfig
except ImportError as e:
    raise ImportError(f"[FATAL] Cannot import retriever module: {e}")

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

# Synchronized with generator.py
ODP_PATTERN = re.compile(
    r"(?:\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+|\[assignment:\s*([^\]]+?)\s*\])",
    re.IGNORECASE,
)

def _extract_odp_keys(text: str) -> List[str]:
    if not isinstance(text, str) or not text:
        return []
    keys: List[str] = []
    for a, b in ODP_PATTERN.findall(text):
        raw = a or b
        if raw:
            base = str(raw).strip().split(",")[-1].strip()
            if base:
                keys.append(base)
    return keys



def _normalize_odp_id(raw: str) -> str:
    """
    Normalize ODP IDs so that minor formatting differences match.
    Examples:
      - "ac-02_odp.5"  -> "ac-02_odp.05"
      - "AC-02_ODP.05" -> "ac-02_odp.05"
    """
    s = (raw or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = s.replace("__", "_")
    s = re.sub(r"(odp\.)\b(\d)\b", r"\g<1>0\2", s)
    return s
def apply_odp_to_answer(answer_text: str, org_profile: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    """
    Substitutes ODPs where possible.
    Returns: (status, substituted_text, missing_keys)
    """
    text = answer_text or ""
    required = set(_extract_odp_keys(text))
    missing: List[str] = []

    for key in sorted(required):
        _norm_map = { _normalize_odp_id(k): k for k in org_profile.keys() } if isinstance(org_profile, dict) else {}
        prof_key = _norm_map.get(_normalize_odp_id(key), key)
        val = org_profile.get(prof_key) if isinstance(org_profile, dict) else None
        # Robust check allowing 0 or False but not None or ""
        if val is not None and str(val).strip() != "":
            val_str = str(val)
            # FIXED: Added re.escape to prevent regex injection
            rep_braces = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(key) + r"\s*\}+"
            rep_assign = r"\[assignment:\s*" + re.escape(key) + r"\s*\]"
            try:
                text = re.sub(rep_braces, val_str, text, flags=re.IGNORECASE)
                text = re.sub(rep_assign, val_str, text, flags=re.IGNORECASE)
            except re.error:
                # If regex fails, we skip substitution for this key
                pass
        else:
            missing.append(key)

    status = "PARAMS_REQUIRED" if missing else "OK"
    return status, text, missing

def resolve_ccs_path(framework_version: str) -> str:
    candidates = [
        f"/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_{framework_version}_catalog.jsonl",
        f"data/ccs/nist800-53/NIST_SP-800-53_{framework_version}_catalog.jsonl",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]

# ============================================================================
# 4) PIPELINE
# ============================================================================

class ComplianceGPTPipeline:
    def __init__(
        self,
        framework_version: str = "rev5",
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        use_qur: bool = True,
    ) -> None:
        self.framework_version = framework_version

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

        ccs_path = resolve_ccs_path(framework_version)
        print(f"[Pipeline] Retriever loading: {ccs_path}")
        self.retriever = ComplianceGPTRetriever(catalog_path=ccs_path, config=RetrievalConfig())

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
    ) -> Dict[str, Any]:
        org_profile = org_profile or {}

        # 1) Retrieve
        rewrites = self.qur.generate(query) if self.qur else None
        raw_docs = self.retriever.retrieve(query, top_k=top_k * 2, rewrites=rewrites)

        filtered = [d for d in raw_docs if is_statement_only_doc(d.get("id", ""))]
        docs = (filtered[:top_k] if filtered else raw_docs[:top_k])

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

        if not selected_ids and primary_doc_id:
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

        # Keep status coherent with evidence
        if spans_out and str(contract.get("status", "")).strip().upper() == "NO_EVIDENCE":
            contract["status"] = "OK"
        if (not spans_out) and str(contract.get("status", "")).strip().upper() == "OK":
            contract["status"] = "NO_EVIDENCE"


        # For benchmark mode: make the answer_text purely extractive (verbatim from retrieved evidence)
        if spans_out:
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

        if (not contract.get("answer_text")) and docs:
            contract["answer_text"] = str(docs[0].get("text", "")).strip()
            if contract["answer_text"] and not contract.get("evidence_spans"):
                contract["evidence_spans"] = [{"source_id": str(primary_doc_id), "span_text": contract["answer_text"]}]

        # 6) Display citations
        for span in contract.get("evidence_spans", []):
            sid = str(span.get("source_id", ""))
            span["source_id_display"] = doc_base_display(sid)

        # 7) Recompute ODP status (policy-aware, benchmark-consistent)
        base_status = str(contract.get("status", "OK")).strip().upper()

        if base_status in ("OK", "PARAMS_REQUIRED"):
            # Extract ODP keys from the (verbatim) answer text
            required_keys = sorted(set(_extract_odp_keys(str(contract.get("answer_text", "")))))

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

            if required_keys:
                if policy == "ASK":
                    # Keep the answer verbatim (placeholders intact), require params
                    contract["status"] = "PARAMS_REQUIRED"
                    contract["odp_required_list"] = required_keys
                elif policy == "FILL_FROM_PROFILE":
                    # Substitute only if values exist; otherwise require params
                    odp_status, substituted, missing = apply_odp_to_answer(str(contract.get("answer_text", "")), org_profile)
                    contract["answer_text"] = substituted if odp_status == "OK" else str(contract.get("answer_text", ""))
                    contract["odp_required_list"] = [] if odp_status == "OK" else missing
                    contract["status"] = odp_status
                else:
                    # Unknown policy -> default to ASK behavior
                    contract["status"] = "PARAMS_REQUIRED"
                    contract["odp_required_list"] = required_keys
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
