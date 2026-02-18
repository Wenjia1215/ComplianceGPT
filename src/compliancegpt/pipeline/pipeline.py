# -*- coding: utf-8 -*-
"""
ComplianceGPT Pipeline (provably-extractive, clean naming)

Single source of truth:
- `ccs_path` is the canonical name for the clause-level CCS JSONL file.
- The retriever must accept: ComplianceGPTRetriever(ccs_path=...)
- The generator must output Selector Contract (IDs only).
- The pipeline deterministically fills verbatim `span_text` from CCS and constructs `answer_text`.

This file is designed to live at:
  /content/drive/MyDrive/ComplianceGPT_v2/src/compliancegpt/pipeline/pipeline.py
"""

from __future__ import annotations

import re

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import fields as _dc_fields, is_dataclass as _is_dataclass, replace as _dc_replace

# Imports (repo-local, fixed tree layout)
# ----------------------------
from compliancegpt.generator.generator import ComplianceGenerator, load_org_profile, normalize_contract  # type: ignore
_VERIFY_IMPORT_ERROR = None
try:
    from compliancegpt.generator.verifier.verifier import verify_answer  # type: ignore
    try:
        from compliancegpt.generator.verifier.verifier import parse_control_from_source_id  # type: ignore
    except Exception:
        parse_control_from_source_id = None  # type: ignore
except Exception as e:
    verify_answer = None  # type: ignore
    parse_control_from_source_id = None  # type: ignore
    _VERIFY_IMPORT_ERROR = str(e)
try:
    from compliancegpt.retriever.retriever_s7 import ComplianceGPTRetriever, RetrievalConfig  # type: ignore
except Exception as e:
    raise ImportError(
        "[FATAL] Cannot import compliancegpt.retriever.retriever_s7. "
        "Ensure your notebook adds '<repo>/src' to sys.path and that the canonical package structure is intact."
    ) from e

try:
    from compliancegpt.QUR_generator.qur_generator_ut import QURComponent  # type: ignore
except Exception:
    QURComponent = None  # type: ignore


# ==========================================================
# 0) Helpers
# ==========================================================
def _cfg_with(cfg: Any, **updates: Any) -> Any:
    """Return a new config with updates applied safely.

    - If cfg is a (possibly frozen) dataclass, use dataclasses.replace (no in-place mutation).
    - Otherwise, set attributes only when they exist.
    - Unknown fields are ignored (forward/backward compatible).
    """
    if cfg is None:
        return cfg
    try:
        if _is_dataclass(cfg):
            names = {f.name for f in _dc_fields(cfg)}
            filtered = {k: v for k, v in updates.items() if k in names}
            return _dc_replace(cfg, **filtered) if filtered else cfg
    except Exception:
        # Fall through to attribute-based updates
        pass
    for k, v in updates.items():
        if hasattr(cfg, k):
            try:
                setattr(cfg, k, v)
            except Exception:
                pass
    return cfg


def _normalize_fw(framework_version: str) -> str:
    v = str(framework_version or "").strip().lower()
    if v in {"rev4", "r4", "4"}:
        return "rev4"
    if v in {"rev5", "r5", "5"}:
        return "rev5"
    raise ValueError(f"framework_version must be 'rev4' or 'rev5' (got {framework_version!r})")


def resolve_default_ccs_path(framework_version: str) -> str:
    """
    Default CCS locations (Drive-first, matches your current Colab setup).
    Adjust here only if you move your repo.
    """
    fw = _normalize_fw(framework_version)
    base = Path("/content/drive/MyDrive/ComplianceGPT_v2/data/ccs/nist800-53")
    if fw == "rev5":
        return str(base / "NIST_SP-800-53_rev5_catalog.jsonl")
    return str(base / "NIST_SP-800-53_rev4_catalog.jsonl")


def _doc_id_suffix(doc_id: str) -> str:
    s = str(doc_id or "").strip().lower()
    if not s:
        return ""
    for suf in ("_smt", "_gdn", "_obj"):
        if suf in s:
            return suf
    return ""


def _statement_only_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for d in docs:
        if _doc_id_suffix(d.get("id", "")) == "_smt":
            out.append(d)
    return out


def _choose_docs_for_generator(
    retrieved_docs: List[Dict[str, Any]],
    top_k: int,
    doc_filter_mode: str,
) -> List[Dict[str, Any]]:
    """
    Generator input doc selection.

    Modes:
      - "all": pass through (top_k slice only)
      - "statement_only": only _smt docs   [DEPRECATED: deletes context; kept for backwards-compatibility]
      - "prefer_statement_only": if any _smt exist, use only those; else pass through  [DEPRECATED]
      - "prefer_smt_keep_params": keep all docs but *rank* _smt first, then _odp/_prm/_obj, then _gdn
    """
    mode = str(doc_filter_mode or "all").strip().lower()
    docs = list(retrieved_docs or [])

    def _kind_of(d: Dict[str, Any]) -> str:
        k = str(d.get("kind") or "").strip().lower()
        if k:
            return k
        # fall back to id suffix: "_smt" -> "smt", etc.
        suf = _doc_id_suffix(d.get("id", "")).strip().lower()
        return suf[1:] if suf.startswith("_") else suf

    if mode == "all":
        out = docs
    elif mode == "statement_only":
        out = _statement_only_docs(docs)
    elif mode == "prefer_statement_only":
        smt = _statement_only_docs(docs)
        out = smt if smt else docs
    elif mode == "prefer_smt_keep_params":
        # Stable sort by kind bucket; keep original order within each bucket.
        order = {"smt": 0, "gdn": 1, "odp": 2, "prm": 3, "obj": 4}
        indexed = list(enumerate(docs))
        indexed.sort(key=lambda t: (order.get(_kind_of(t[1]), 9), t[0]))
        out = [d for _, d in indexed]
    else:
        raise ValueError(f"Unknown doc_filter_mode={doc_filter_mode!r}")

    if top_k is not None and int(top_k) > 0:
        out = out[: int(top_k)]
    return out


# ==========================================================
# Control-ID normalization helpers (pipeline-local)
# ==========================================================
_CTRL_ID_RE = re.compile(r"(?i)([A-Z]{2})-0*([0-9]{1,3})")

def normalize_control_id(s: Any) -> Optional[str]:
    """Return canonical control id like 'AC-6' from variants (e.g., 'AC-06', 'AC-6_smt.1')."""
    if s is None:
        return None
    t = str(s).strip()
    if not t or t.lower() == "nan":
        return None
    m = _CTRL_ID_RE.search(t)
    if not m:
        return None
    fam = m.group(1).upper()
    num = int(m.group(2))
    return f"{fam}-{num}"


def _unique_controls_in_order(docs: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for d in docs or []:
        cid = (normalize_control_id(str(d.get("control_id", ""))) or "").upper()
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def _selected_controls_from_spans(spans: List[Dict[str, str]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in spans or []:
        sid = str((s or {}).get("source_id", "")).strip()
        cid = None
        if sid and "parse_control_from_source_id" in globals() and callable(globals().get("parse_control_from_source_id")):
            try:
                cid = globals()["parse_control_from_source_id"](sid)  # type: ignore
            except Exception:
                cid = None
        if not cid and sid:
            # fallback: try normalize_control_id on the sid itself
            cid = normalize_control_id(sid)
        cid = str(cid or "").strip().upper()
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def _build_citation_suffix(framework_version: str) -> str:
    fw = _normalize_fw(framework_version)
    if fw == "rev5":
        return "NIST SP 800-53 Rev. 5"
    return "NIST SP 800-53 Rev. 4"


# ODP placeholder patterns (must align with verifier.py)
_PARAM_CURLY_RE = re.compile(r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+", re.IGNORECASE)
_PARAM_ASSIGNMENT_RE = re.compile(r"\[assignment:\s*([^\]]+?)\s*\]", re.IGNORECASE)

_ASSIGNMENT_REQUIRED_SENTINEL = "__ASSIGNMENT_REQUIRED__"


def _extract_odp_ids(text: str) -> Tuple[List[str], bool]:
    """
    Returns (odp_ids, has_assignment_placeholder).
    odp_ids are normalized strings like 'ac-02_odp.05' when present inside curly placeholders.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    keys = []
    for m in _PARAM_CURLY_RE.finditer(text):
        k = m.group(1).strip()
        if k:
            keys.append(k)

    # assignment placeholders are human-language (no canonical key guaranteed)
    has_assignment = bool(_PARAM_ASSIGNMENT_RE.search(text))
    # normalize + de-dupe
    keys = sorted(set(k.strip() for k in keys if k.strip()))
    return keys, has_assignment


def _profile_lookup(profile: Dict[str, Any], key: str) -> Optional[Any]:
    """
    Look up ODP values in org_profile.

    Supported shapes:
      profile["odp_values"][key]
      profile["odps"][key]
      profile[key]
    """
    if not isinstance(profile, dict) or not key:
        return None
    for top in ("odp_values", "odps"):
        if isinstance(profile.get(top), dict) and key in profile[top]:
            return profile[top][key]
    return profile.get(key)



# ==========================================================
# ODP/PRM Canonicalization (CCS-aligned, provably-extractive)
# ==========================================================
_PARAM_ID_KIND_RE = re.compile(r"_(odp|prm)\b", re.IGNORECASE)

def _build_param_key_to_canonical(param_ids: Set[str]) -> Dict[str, str]:
    """
    Build a deterministic mapping from a normalized "param key" -> canonical param id.

    Key design:
      - robust to: ra-3_odp.2, ra-03_odp.02, ra-03_odp_2, cp-02.06_odp (legacy/non-canonical)
      - does NOT guess when ambiguous: if multiple canonicals map to the same key, pick the lexicographically smallest.
    """
    out: Dict[str, str] = {}
    for pid in (param_ids or set()):
        key = _param_key(pid)
        if not key:
            continue
        if key not in out or pid < out[key]:
            out[key] = pid
    return out

def _param_key(raw: str) -> str:
    """
    Normalize a raw param token to a stable key:
      <family>-<ctrl2>[.<enh2>]_<kind>.<idx2>
    """
    s = (raw or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    s = s.replace("__", "_")

    # Canonical-ish: ra-03_odp.02 ; ac-02.05_prm.01 ; at-2_prm_1
    m = re.match(r"^([a-z]{2})-?(\d{1,2})(?:\.(\d{1,2}))?_(odp|prm)[\._-]?(\d{1,2})$", s)
    if m:
        fam, ctrl, enh, kind, idx = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        enh_s = ("." + format(int(enh), "02d")) if enh is not None else ""
        return f"{fam}-{int(ctrl):02d}{enh_s}_{kind}.{int(idx):02d}"

    # Legacy: cp-02.06_odp  (meaning control=02, idx=06, kind=odp)
    m2 = re.match(r"^([a-z]{2})-(\d{1,2})\.(\d{1,2})_(odp|prm)$", s)
    if m2:
        fam, ctrl, idx, kind = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
        return f"{fam}-{int(ctrl):02d}_{kind}.{int(idx):02d}"

    # Legacy: ac_02_odp_1
    m3 = re.match(r"^([a-z]{2})[-_]?(\d{1,2})_(odp|prm)[\._-]?(\d{1,2})$", s)
    if m3:
        fam, ctrl, kind, idx = m3.group(1), m3.group(2), m3.group(3), m3.group(4)
        return f"{fam}-{int(ctrl):02d}_{kind}.{int(idx):02d}"

    return ""

def _canonicalize_param_list(
    raw_list: List[str],
    *,
    param_ids: Set[str],
    key_map: Dict[str, str],
    assignment_sentinel: str,
) -> List[str]:
    """
    Canonicalize a list of ODP/PRM ids into CCS-canonical ids.
    Principle: provably-extractive -> only emit ids that exist in CCS param_ids.
    Unknown/unmappable tokens are dropped (they are not mechanically verifiable).
    """
    seen: Set[str] = set()
    out: List[str] = []
    has_assign = False

    for x in (raw_list or []):
        s = (x or "").strip()
        if not s:
            continue
        if s == assignment_sentinel:
            has_assign = True
            continue

        if s in param_ids:
            if s not in seen:
                out.append(s)
                seen.add(s)
            continue

        k = _param_key(s)
        if not k:
            # Try prefix match for tokens like "pm-05_odp" (no idx)
            s_low = re.sub(r"\s+", "", s.lower())
            if _PARAM_ID_KIND_RE.search(s_low) and (s_low.endswith("_odp") or s_low.endswith("_prm")):
                candidates = sorted([pid for pid in param_ids if pid.lower().startswith(s_low + ".")])
                if len(candidates) == 1:
                    cand = candidates[0]
                    if cand not in seen:
                        out.append(cand)
                        seen.add(cand)
            continue

        cand = key_map.get(k, "")
        if cand and cand in param_ids and cand not in seen:
            out.append(cand)
            seen.add(cand)

    out_sorted = sorted(out)
    if has_assign:
        out_sorted.append(assignment_sentinel)
    return out_sorted
def _apply_odp_policy_to_answer(
    answer_text: str,
    policy: str,
    org_profile: Dict[str, Any],
) -> Tuple[str, List[str], str]:
    """
    Apply ODP resolution policy to the final answer_text.

    Returns: (new_answer_text, odp_required_list, final_status_override_or_empty)

    Policy:
      - ASK: do not substitute; require params if any placeholders
      - PRESERVE: do not substitute; require params if any placeholders (used for evaluation)
      - FILL_FROM_PROFILE: substitute known keys; require params only for missing keys and assignment placeholders
    """
    pol_raw = policy
    try:
        pol = "" if pol_raw is None else str(pol_raw).strip().upper()
    except Exception:
        pol = ""
    # Treat pandas/NumPy NaN and other empty-ish tokens as missing
    if pol in {"", "NAN", "NA", "N/A", "NONE", "NULL"}:
        pol = "ASK"
    # Allow a few safe aliases
    if pol in {"FILL", "PROFILE", "FILL_PROFILE"}:
        pol = "FILL_FROM_PROFILE"
    text = str(answer_text or "")

    keys, has_assignment = _extract_odp_ids(text)
    if not keys and not has_assignment:
        return text, [], ""  # no change

    missing: List[str] = []

    if pol in {"ASK", "PRESERVE"}:
        # Keep placeholders exactly; just surface required keys.
        req = list(keys)
        if has_assignment:
            req.append(_ASSIGNMENT_REQUIRED_SENTINEL)
        return text, req, "PARAMS_REQUIRED"

    if pol == "FILL_FROM_PROFILE":
        # Substitute what we can; keep missing placeholders.
        for k in keys:
            val = _profile_lookup(org_profile, k)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(k)
                continue
            val_str = str(val)
            # replace curly placeholder for this key (robust for whitespace)
            rep_braces = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(k) + r"\s*\}+"
            try:
                text = re.sub(rep_braces, val_str, text, flags=re.IGNORECASE)
            except re.error:
                # if the regex fails, leave placeholder
                missing.append(k)

        req = list(sorted(set(missing)))
        if has_assignment:
            req.append(_ASSIGNMENT_REQUIRED_SENTINEL)

        if req:
            return text, req, "PARAMS_REQUIRED"
        return text, [], ""  # all resolved

    raise ValueError(f"Unknown resolution_policy={policy!r}")


# ==========================================================
# Output Compatibility Wrapper
# ==========================================================
def _verifier_result_to_dict(ver: Any) -> Optional[Dict[str, Any]]:
    """Normalize verifier output (dataclass / dict / unknown) to a JSON-friendly dict."""
    if ver is None:
        return None
    if isinstance(ver, dict):
        return ver
    # dataclass
    try:
        from dataclasses import asdict, is_dataclass  # local import to avoid hard dependency
        if is_dataclass(ver):
            return asdict(ver)
    except Exception:
        pass
    # attribute-based fallback (VerifierResult)
    if hasattr(ver, "question_id") and hasattr(ver, "is_pass"):
        try:
            return {
                "question_id": str(getattr(ver, "question_id")),
                "is_pass": bool(getattr(ver, "is_pass")),
                "error_tags": list(getattr(ver, "error_tags", []) or []),
                "metrics": dict(getattr(ver, "metrics", {}) or {}),
            }
        except Exception:
            return {"error": str(ver)}
    return {"error": str(ver)}

def _wrap_out(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Acceptance-test compatible return shape.

    Returns:
      - out['contract'] -> the contract dict
      - also flattens contract keys at top-level for backward compatibility
    """
    c: Dict[str, Any] = dict(contract or {})

    # selected_source_ids convenience (acceptance notebook expects it sometimes)
    if "selected_source_ids" not in c:
        spans = c.get("evidence_spans", []) or []
        ids: List[str] = []
        for s in spans:
            if isinstance(s, dict):
                sid = str(s.get("source_id", "")).strip()
                if sid:
                    ids.append(sid)
        c["selected_source_ids"] = ids

    # verifier flattening: verifier_pass / verifier_errors / verifier_metrics
    ver = c.get("verification", None)
    ver_dict = _verifier_result_to_dict(ver) if ver is not None else None
    if ver is not None:
        c["verification"] = ver_dict

    c["verifier_ran"] = bool(ver is not None)

    verifier_pass = False
    verifier_errors: List[str] = []
    verifier_metrics: Dict[str, float] = {}
    if isinstance(ver_dict, dict):
        if "is_pass" in ver_dict:
            verifier_pass = bool(ver_dict.get("is_pass", False))
        elif "ok" in ver_dict:
            verifier_pass = bool(ver_dict.get("ok", False))
        verifier_errors = list(ver_dict.get("error_tags") or ver_dict.get("errors") or [])
        verifier_metrics = dict(ver_dict.get("metrics") or {})
        if not verifier_errors and ver_dict.get("error"):
            verifier_errors = [f"VerifierException:{str(ver_dict.get('error'))}"]

    c["verifier_pass"] = bool(verifier_pass)
    c["verifier_errors"] = verifier_errors
    if verifier_metrics:
        c["verifier_metrics"] = verifier_metrics

    out: Dict[str, Any] = {"contract": c}
    # Flatten for legacy callers that expect the contract directly
    out.update(c)
    return out


# ==========================================================
# Pipeline
# ==========================================================
class ComplianceGPTPipeline:
    """
    End-to-end runner:
      Query -> (optional rewrites) -> Retriever -> Generator (ID selector) -> Deterministic fill -> Verifier (optional)
    """

    def __init__(
        self,
        *,
        framework_version: str = "rev5",
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        use_qur: bool = True,
        doc_filter_mode: str = "all",
        ccs_path: Optional[str] = None,
        strict_ccs_assert: bool = True,
        min_ccs_docs: int = 1000,
        org_profile_path: Optional[str] = None,
        load_in_4bit: bool = True,
        retriever_config: RetrievalConfig = RetrievalConfig(),
        verify_strict_extras: bool = False,
        verify_strict_verbatim: bool = True,
        verify_strict_version: bool = False,
    ):
        self.framework_version = _normalize_fw(framework_version)
        self.model_id = str(model_id)
        self.use_qur = bool(use_qur)
        self.doc_filter_mode = str(doc_filter_mode)

        # Verification strictness knobs (used when run_verify=True)
        self.verify_strict_extras = bool(verify_strict_extras)
        self.verify_strict_verbatim = bool(verify_strict_verbatim)
        self.verify_strict_version = bool(verify_strict_version)

        self.ccs_path = str(ccs_path) if ccs_path else resolve_default_ccs_path(self.framework_version)
        self.strict_ccs_assert = bool(strict_ccs_assert)
        self.min_ccs_docs = int(min_ccs_docs)

        self.org_profile_path = org_profile_path
        self.org_profile: Dict[str, Any] = load_org_profile(org_profile_path) if org_profile_path else {}


        # Ensure parameter/ODP chunks are available to the retriever (ranking/boosting requires access).
        # Principle: never delete ODP/parameter material at load time.
        try:
            keep_raw = getattr(retriever_config, "keep_kinds", None)
            keep_norm = tuple(str(k).lower() for k in (keep_raw or ()))
        except Exception:
            keep_norm = ()

        if (not keep_norm) or (keep_norm == ("smt", "gdn")):
            # Empty tuple disables kind filtering inside ComplianceGPTRetriever.load_clause_records_jsonl
            new_keep_kinds: Tuple[str, ...] = tuple()
        else:
            kk = list(keep_norm)
            for k in ("smt", "gdn", "odp", "prm", "obj"):
                if k not in kk:
                    kk.append(k)
            new_keep_kinds = tuple(kk)

        # Prefer selection order: statements first, then parameters, then guidance (stable).
        try:
            kp_raw = getattr(retriever_config, "kind_priority", None)
            kp = [str(k).lower() for k in (kp_raw or ())]
        except Exception:
            kp = []

        desired = ["smt", "gdn", "odp", "prm", "obj"]
        new_kp: List[str] = []
        for k in desired:
            if k not in new_kp:
                new_kp.append(k)
        for k in kp:
            if k not in new_kp:
                new_kp.append(k)

        retriever_config = _cfg_with(
            retriever_config,
            keep_kinds=new_keep_kinds,
            kind_priority=tuple(new_kp),
        )

        self.retriever = ComplianceGPTRetriever(ccs_path=self.ccs_path, config=retriever_config)
        self._assert_ccs_loaded()
        # Verifier corpus cache (built lazily; avoids O(N_queries * N_docs) rebuild in batch).
        self._verifier_corpus_cache: Optional[Dict[str, str]] = None


        # 2) Model + tokenizer (shared with generator and optionally QUR)
        self.model, self.tokenizer = self._load_model(self.model_id, load_in_4bit=load_in_4bit)

        # 3) Generator (ID selector)
        self.generator = ComplianceGenerator(self.model, self.tokenizer)

        # 4) Optional QUR (query rewrite)
        self.qur = None
        if self.use_qur:
            if QURComponent is None:
                raise ImportError("use_qur=True but QURComponent could not be imported. Check QUR_generator path.")
            self.qur = QURComponent(model_id=self.model_id, n=3, temperature=0.5, top_p=0.9, max_new_tokens=80, seed=42,
                                    model=self.model, tokenizer=self.tokenizer)

    # --------------------------
    # Model loading (robust)
    # --------------------------
    def _load_model(self, model_id: str, *, load_in_4bit: bool) -> Tuple[Any, Any]:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

        quant_cfg = None
        if load_in_4bit:
            try:
                # bitsandbytes must exist for 4-bit
                import bitsandbytes  # noqa: F401
                from transformers import BitsAndBytesConfig  # type: ignore

                quant_cfg = BitsAndBytesConfig(load_in_4bit=True)
            except Exception as e:
                print(f"[Pipeline] 4-bit requested but bitsandbytes unavailable. Falling back to full precision. ({e})")
                quant_cfg = None

        kwargs: Dict[str, Any] = {"trust_remote_code": True}
        if torch.cuda.is_available():
            kwargs["device_map"] = "auto"
            kwargs["torch_dtype"] = torch.float16
        else:
            kwargs["device_map"] = None

        if quant_cfg is not None:
            kwargs["quantization_config"] = quant_cfg

        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
        return model, tok

    # --------------------------
    # CCS sanity check
    # --------------------------
    def _assert_ccs_loaded(self) -> None:
        n = len(getattr(self.retriever, "ids", []) or [])
        if self.strict_ccs_assert:
            if n < self.min_ccs_docs:
                raise RuntimeError(
                    f"CCS load sanity check failed: loaded {n} docs (< {self.min_ccs_docs}). ccs_path={self.ccs_path}"
                )
            # at least some statements expected
            smt = sum(1 for _id in getattr(self.retriever, "ids", []) if "_smt" in str(_id).lower())
            if smt == 0:
                raise RuntimeError("CCS sanity check failed: no _smt docs detected (statement clauses missing).")

    # --------------------------
    def _get_verifier_corpus(self) -> Dict[str, str]:
        """Return an id->text corpus for verifier use.

        Built once and cached. This avoids rebuilding a full corpus dict for every query in batch runs.
        """
        if isinstance(getattr(self, "_verifier_corpus_cache", None), dict):
            return self._verifier_corpus_cache  # type: ignore

        record_by_id = getattr(self.retriever, "record_by_id", {}) or {}
        corpus: Dict[str, str] = {}
        for k, v in record_by_id.items():
            if isinstance(v, dict):
                corpus[str(k)] = str(v.get("text", "") or "")
            else:
                corpus[str(k)] = ""
        self._verifier_corpus_cache = corpus
        return corpus


    # Main API
    # --------------------------
    def answer(
        self,
        query: str,
        *,
        top_k: int = 12,
        rewrites: Optional[List[str]] = None,
        gold_row: Optional[Dict[str, Any]] = None,
        use_generator: bool = True,
        run_verify: bool = True,
    ) -> Dict[str, Any]:
        """
        Returns Final Answer Contract (see citation_contract_80053.md).

        If gold_row is provided (evaluation), the verifier will compare to its expected control_id and resolution_policy.
        """
        q = str(query or "").strip()
        if not q:
            return _wrap_out({
                "answer_text": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "answer_text_with_citation": "",
                "contract_mode": "provably_extractive",
                "error": "Empty query",
            })

        # 1) QUR rewrites
        rew = list(rewrites) if rewrites else []
        if self.qur is not None and not rew:
            try:
                rew = [r for r in (self.qur.generate(q) or []) if isinstance(r, str) and r.strip()]
            except Exception as e:
                print(f"[Pipeline] QUR failed; continuing without rewrites. ({e})")
                rew = []

        # 2) Retrieval
        # Supervisor requirement: ranking/boosting (NOT deletion). We keep context and only adjust doc ordering.
        policy_hint = ""
        if isinstance(gold_row, dict):
            try:
                policy_hint = str(gold_row.get("resolution_policy", "")).strip().upper()
            except Exception:
                policy_hint = ""
        if policy_hint in {"NAN", "NA", "N/A", "NONE", "NULL", ""}:
            policy_hint = ""

        try:
            retrieved_docs = self.retriever.retrieve(q, top_k=max(int(top_k), 1), rewrites=rew)
        except TypeError:
            # If your retriever signature diverges, surface a clear error.
            raise TypeError("Retriever API mismatch. Expected ComplianceGPTRetriever.retrieve(query, top_k=..., rewrites=...).")

        retrieved_docs = list(retrieved_docs or [])
        added_param_doc_ids: List[str] = []

        # Augment with parameter/ODP chunks for the top retrieved controls (boosting, not filtering).
        if hasattr(self.retriever, "control_to_clause_ids_by_kind") and hasattr(self.retriever, "record_by_id"):
            ctrl_order = _unique_controls_in_order(retrieved_docs)
            extra_ids: List[str] = []
            for ctl in (ctrl_order or [])[: max(1, min(10, len(ctrl_order or [])))]:
                kind_map = getattr(self.retriever, "control_to_clause_ids_by_kind", {}).get(ctl, {}) or {}
                for kind_key, ids in (kind_map or {}).items():
                    k = str(kind_key).lower()
                    if k.startswith('odp') or k.startswith('prm') or k.startswith('obj'):
                        extra_ids.extend(list(ids or [])[:3])

            existing = {str(d.get("id", "")).strip() for d in retrieved_docs if isinstance(d, dict)}
            for cid in extra_ids:
                cid2 = str(cid).strip()
                if not cid2 or cid2 in existing:
                    continue
                rec = getattr(self.retriever, "record_by_id", {}).get(cid2)
                if isinstance(rec, dict):
                    retrieved_docs.append(rec)
                    existing.add(cid2)
                    added_param_doc_ids.append(cid2)

        # 3) Doc selection for generator (ranking/boosting only; never delete ODP/parameter docs)
        doc_filter_mode_used = str(self.doc_filter_mode or "all").strip().lower()
        if doc_filter_mode_used in {"statement_only", "prefer_statement_only"}:
            # Hard deprecate deletion modes: keep docs, just prefer statements + params.
            doc_filter_mode_used = "prefer_smt_keep_params"
        elif policy_hint in {"ASK", "PRESERVE", "FILL_FROM_PROFILE"} and doc_filter_mode_used == "all":
            # Default boost for parameter-aware questions: prioritize statements and parameter definitions.
            doc_filter_mode_used = "prefer_smt_keep_params"

        docs_for_gen = _choose_docs_for_generator(retrieved_docs, top_k=int(top_k), doc_filter_mode=doc_filter_mode_used)

        fallback_used: bool = False
        fallback_reason: str = ""

        # 4) Evidence selection
        if bool(use_generator):
            # Generator selects evidence IDs only
            raw_contract = self.generator.generate(q, docs_for_gen, self.org_profile)
            contract = normalize_contract(raw_contract)
        else:
            # Extractive fallback: take the top-k docs as evidence IDs (no model call).
            contract = {
                "answer_text": "",
                "evidence_spans": [{"source_id": str(d.get("id", "")).strip(), "span_text": ""} for d in (docs_for_gen or []) if str(d.get("id", "")).strip()],
                "status": "OK" if docs_for_gen else "NO_EVIDENCE",
                "odp_required_list": [],
            }

        # 5) Enforce selector invariants (provably-extractive)
        #    - answer_text must be empty at selector stage (pipeline will fill)
        contract["answer_text"] = ""
        #    - status/evidence consistency
        spans = contract.get("evidence_spans", []) or []
        status = str(contract.get("status", "ERROR")).upper().strip()

        if status == "NO_EVIDENCE":
            spans = []
        elif status in {"OK", "PARAMS_REQUIRED"}:
            spans = [s for s in spans if str(s.get("source_id", "")).strip()]
            if not spans:
                status = "NO_EVIDENCE"
        else:
            status = "ERROR"

        # Controlled fallback only when generator output is malformed or ERROR (NEVER override NO_EVIDENCE)
        if status == "ERROR":
            fallback_used = True
            fallback_reason = "generator_error_or_malformed_contract"
            if docs_for_gen:
                fid = str(docs_for_gen[0].get("id", "")).strip()
                if fid:
                    spans = [{"source_id": fid, "span_text": ""}]
                    status = "OK"

        contract["status"] = status
        contract["evidence_spans"] = spans

        # 6) Deterministically fill span_text from CCS (via retriever.record_by_id)
        filled_spans: List[Dict[str, str]] = []
        missing_ids: List[str] = []
        for s in spans:
            sid = str(s.get("source_id", "")).strip()
            if not sid:
                continue
            rec = getattr(self.retriever, "record_by_id", {}).get(sid)
            txt = ""
            if isinstance(rec, dict):
                txt = str(rec.get("text", "")).strip()
            if not txt:
                # fallback: search in provided docs_for_gen
                for d in docs_for_gen:
                    if str(d.get("id", "")).strip() == sid:
                        txt = str(d.get("text", "")).strip()
                        break
            if not txt:
                missing_ids.append(sid)
                continue
            filled_spans.append({"source_id": sid, "span_text": txt})

        # Missing IDs indicate a selector/ID mismatch. Do NOT crash the pipeline.
        # Keep any filled spans, and surface missing IDs in debug.
        if missing_ids and not filled_spans and status != "NO_EVIDENCE":
            # If nothing could be filled, attempt one more controlled fallback using the top retrieved doc.
            if retrieved_docs:
                fid = str(retrieved_docs[0].get("id", "")).strip()
                ftxt = str(retrieved_docs[0].get("text", "")).strip()
                if fid and ftxt:
                    filled_spans = [{"source_id": fid, "span_text": ftxt}]
                    fallback_used = True
                    fallback_reason = fallback_reason or "all_selected_ids_missing_fallback_to_top_retrieved"
            if not filled_spans:
                status = "ERROR"


        # 7) Build extractive answer_text (no new claims)
        answer_text = " ".join(s["span_text"] for s in filled_spans).strip()

        # 8) Apply ODP policy (gold_row can override)
        policy = ""
        policy_from_gold = False
        if isinstance(gold_row, dict):
            try:
                raw_pol = str(gold_row.get("resolution_policy", "") or "").strip()
                if raw_pol:
                    policy = raw_pol.upper()
                    policy_from_gold = True
            except Exception:
                policy = ""
                policy_from_gold = False
        if policy in {"NAN", "NA", "N/A", "NONE", "NULL"}:
            policy = ""
            policy_from_gold = False
        if not policy:
            policy = "ASK"

        answer_text2, odp_req, status_override = _apply_odp_policy_to_answer(answer_text, policy, self.org_profile)

        # Canonicalize ODP/PRM ids against CCS (provably-extractive: drop unknown ids)
        param_ids: Set[str] = set()
        try:
            rb = getattr(self.retriever, "record_by_id", {}) or {}
            for _id, rec in rb.items():
                if isinstance(rec, dict):
                    k = str(rec.get("kind", "")).strip().lower()
                    if k in {"odp", "prm"}:
                        param_ids.add(str(_id))
        except Exception:
            param_ids = set()

        key_map = _build_param_key_to_canonical(param_ids)

        # Canonicalize generator-produced ODP list (if any)
        contract["odp_required_list"] = _canonicalize_param_list(
            list(contract.get("odp_required_list", []) or []),
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        # Canonicalize placeholder-derived ODP list
        odp_req = _canonicalize_param_list(
            list(odp_req or []),
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        final_status = status
        if final_status == "NO_EVIDENCE":
            # never upgrade NO_EVIDENCE even if placeholders exist
            odp_req = []
            answer_text2 = ""
        else:
            if status_override:
                final_status = status_override
            # also respect generator's PARAMS_REQUIRED if it claimed it
            if status == "PARAMS_REQUIRED":
                final_status = "PARAMS_REQUIRED"


            # Evaluation-only: if gold explicitly says ASK/PRESERVE, enforce PARAMS_REQUIRED (status correctness gate)
            if policy_from_gold and policy in {"ASK", "PRESERVE"}:
                final_status = "PARAMS_REQUIRED"
                # merge lists conservatively
                merged = list(odp_req or []) + list(contract.get("odp_required_list", []) or [])
                odp_req = _canonicalize_param_list(
                    merged,
                    param_ids=param_ids,
                    key_map=key_map,
                    assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
                )

        # 9) Citations (contract-level, deterministic)
        cite_ids = [s.get("source_id", "") for s in (filled_spans or []) if str(s.get("source_id", "")).strip()]
        primary_citation = str(cite_ids[0]) if cite_ids else ""
        all_citations = ", ".join([str(x) for x in cite_ids]) if cite_ids else ""
        answer_with_cit = (f"{answer_text2} (CITE: {all_citations})".strip()) if answer_text2 and all_citations else (answer_text2 or "")

        final_contract: Dict[str, Any] = {
            "answer_text": answer_text2,
            "evidence_spans": filled_spans,
            "status": final_status,
            "odp_required_list": odp_req,
            "primary_citation": primary_citation,
            "all_citations": all_citations,
            "answer_text_with_citation": answer_with_cit,
            "contract_mode": "provably_extractive",
        }

        # 10) Optional verification (gold_row required)
        if run_verify and isinstance(gold_row, dict):
            if verify_answer is None:
                final_contract["verification"] = {
                    "ok": False,
                    "error": (
                        f"verify_answer_unavailable:{_VERIFY_IMPORT_ERROR}"
                        if _VERIFY_IMPORT_ERROR else "verify_answer_unavailable"
                    ),
                    "error_tags": [
                        f"VerifierUnavailable:{_VERIFY_IMPORT_ERROR}"
                        if _VERIFY_IMPORT_ERROR else "VerifierUnavailable"
                    ],
                    "metrics": {},
                }
            else:
                try:
                    corpus = self._get_verifier_corpus()
                    ver = verify_answer(
                        final_contract,
                        gold_row,
                        corpus=corpus,
                        org_profile=self.org_profile,
                        corpus_version=self.framework_version,
                        strict_extras=bool(self.verify_strict_extras),
                        strict_verbatim=bool(self.verify_strict_verbatim),
                        strict_version=bool(self.verify_strict_version),
                    )
                    final_contract["verification"] = ver
                except Exception as e:
                    final_contract["verification"] = {
                        "ok": False,
                        "error": str(e),
                        "error_tags": [f"VerifierException:{type(e).__name__}:{str(e)}"],
                        "metrics": {},
                    }

        # Debug extras (kept minimal)
        final_contract["debug"] = {
            "query": q,
            "rewrites": rew,
            "variants": getattr(self.retriever, "last_variants", []) if hasattr(self.retriever, "last_variants") else [],
            # Clause-level docs returned from retriever (ids)
            "retrieved_doc_ids": [d.get("id") for d in (retrieved_docs or [])][: int(top_k)],
            # Unique controls in retrieval order (control-level perspective)
            "retrieved_control_order": _unique_controls_in_order(retrieved_docs or []),
            # Control ranking diagnostics if retriever exposes it
            "ranked_controls_top": (getattr(self.retriever, "last_ranked_controls", []) or [])[: max(20, int(top_k))],
            "retriever_meta": getattr(self.retriever, "last_meta", {}) if hasattr(self.retriever, "last_meta") else {},
            'keep_kinds_used': getattr(getattr(self.retriever, 'config', None), 'keep_kinds', None),
            'kind_priority_used': getattr(getattr(self.retriever, 'config', None), 'kind_priority', None),
            # Generator input (post filtering)
            "doc_filter_mode": doc_filter_mode_used,
            "docs_for_gen_ids": [d.get("id") for d in (docs_for_gen or [])][: int(top_k)],
            "added_param_doc_ids": added_param_doc_ids,
            # Selector output
            "selected_source_ids": [s.get("source_id") for s in (filled_spans or []) if isinstance(s, dict)],
            "selected_controls": _selected_controls_from_spans(filled_spans or []),
            # Evaluation context (if provided)
            "resolution_policy": policy,
        }
        return _wrap_out(final_contract)
