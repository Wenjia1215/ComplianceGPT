# -*- coding: utf-8 -*-
"""
ComplianceGPT Verifier (v3 - Research Grade, compatibility-preserving)

Goal: Mechanically verifiable, auditable QA checks for NIST SP 800-53.

This refactor is intentionally *API-stable* relative to verifier.py (v2) in this repo:
- Same dataclasses: EvidenceSpan, AnswerContract, GoldLabel, VerifierResult
- Same helper function names (normalize_control_id, normalize_version, normalize_odp_id, etc.)
- Same main entrypoint signature:
    verify_answer(json_output, gold_row, corpus=None, *, org_profile=None,
                  corpus_version=None, strict_extras=True, strict_verbatim=True, strict_version=False)
- Same metrics keys returned.

Key improvements vs v2 (without changing pass/fail semantics unless explicitly noted):
- More robust ODP placeholder extraction: supports { ... } or {{ ... }} and optional "param,"
  (aligned with pipeline placeholder acceptance).
- De-duplicated regex definitions and hardened normalization.
- PRESERVE enforcement uses placeholder extraction (format-independent) rather than a single rigid regex.

NOTE: This file is standalone; no sys.path hacks, no fallback imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Iterable, Set


_ASSIGNMENT_REQUIRED_SENTINEL = "__ASSIGNMENT_REQUIRED__"
VERIFIER_PATCH_ID = "2026-07-12-contract-validity-fix"


# ==========================================================
# 1) Data Models
# ==========================================================

@dataclass
class EvidenceSpan:
    source_id: str
    span_text: str


@dataclass
class AnswerContract:
    answer_text: str
    evidence_spans: List[EvidenceSpan]
    status: str
    odp_required_list: List[str] = field(default_factory=list)


@dataclass
class GoldLabel:
    question_id: str
    framework: str
    version: str                    # normalized: "rev4" / "rev5" / "unknown"
    control_ids: List[str]          # e.g., ["AC-2"]
    doc_ids: List[str]              # e.g., ["ac-2_smt.h.1", ...]
    odp_ids_required: List[str]     # e.g., ["ac-02_odp.05", ...]
    resolution_policy: str          # "ASK", "PRESERVE", "FILL_FROM_PROFILE", or ""


@dataclass
class VerifierResult:
    question_id: str
    is_pass: bool
    error_tags: List[str]
    metrics: Dict[str, float]


__all__ = [
    "EvidenceSpan",
    "AnswerContract",
    "GoldLabel",
    "VerifierResult",
    "VERIFIER_PATCH_ID",
    "normalize_version",
    "normalize_control_id",
    "normalize_odp_id",
    "extract_odp_ids_from_text",
    "has_unresolved_odp_placeholder",
    "doc_id_candidates",
    "resolve_official_text",
    "parse_control_from_source_id",
    "verify_span_against_corpus",
    "compute_set_metrics",
    "check_status_consistency",
    "check_citations",
    "check_odp_behavior",
    "check_version_correctness",
    "verify_answer",
    "parse_answer_contract",
    "verify_contract_validity",
]


# ==========================================================
# 2) Normalization & Regex (Crucial for NIST)
# ==========================================================

# Regex to capture "AC-2" or "AC-2(1)"
_CTRL_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2}-\d+(?:\(\d+\)|\.\d+)?)(?=$|[^A-Z0-9])")


def _canonicalize_control_id(cid: str) -> str:
    """Normalize control IDs like 'AC-02(1)' or 'AC-02.01' -> 'AC-2(1)'.

    Dot enhancement form 'AT-2.1' is normalized to 'AT-2(1)'.
    """
    s = str(cid or "").strip().upper()
    m = re.match(r"^([A-Z]{2})-(\d+)(?:\((\d+)\)|\.(\d+))?$", s)
    if not m:
        return s

    fam = m.group(1)
    num_raw = m.group(2)
    enh_raw = m.group(3) or m.group(4) or ""

    try:
        num = str(int(num_raw))
    except Exception:
        num = num_raw

    enh = ""
    if enh_raw:
        try:
            enh = f"({int(enh_raw)})"
        except Exception:
            enh = f"({enh_raw})"

    return f"{fam}-{num}{enh}"

_VER_RE = re.compile(r"\brev(?:ision)?\s*([45])\b", flags=re.IGNORECASE)

# Curly placeholder patterns:
#   {{ insert: param, ac-02_odp.05 }}
#   { insert: ac-07_odp.01 }
#   { insert: param, ac-7_odp_1 }
# We intentionally allow one-or-more braces on each side and make "param," optional.
# We capture the payload after "insert:" and parse it for a token.
_ODP_CURLY_RE = re.compile(
    r"\{+\s*insert\s*:\s*(?:param\s*,\s*)?([^}]+?)\s*\}+",
    flags=re.IGNORECASE,
)

# Some NIST texts also include:
#   [assignment: organization-defined parameter]
# This does not carry an ID but indicates unresolved ODP.
_ODP_ASSIGNMENT_RE = re.compile(r"\[\s*assignment\s*:\s*([^\]]+)\]", flags=re.IGNORECASE)


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_version(v: Any) -> str:
    """
    Accepts: "Revision 5", "rev5", "Rev.4", etc.
    Returns: "rev5", "rev4", or "unknown".
    """
    if v is None:
        return "unknown"
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return "unknown"
    m = _VER_RE.search(s.replace(".", " "))
    if m:
        return f"rev{m.group(1)}"
    if "5" in s and "rev" in s.lower():
        return "rev5"
    if "4" in s and "rev" in s.lower():
        return "rev4"
    return "unknown"


def normalize_control_id(s: Any) -> Optional[str]:
    """
    Extracts 'AC-2' from 'AC-2(1)' or raw text.
    NOTE: This function preserves the parenthetical form if present.
    """
    if s is None:
        return None
    t = str(s).strip().upper()
    if not t or t.lower() == "nan":
        return None
    m = _CTRL_RE.search(t)
    return _canonicalize_control_id(m.group(1)) if m else None


def _split_listish(value: Any) -> List[str]:
    """
    Handles:
      - NaN / None
      - single string with newlines
      - comma-separated strings
      - already-a-list
    """
    if value is None:
        return []
    if isinstance(value, list):
        parts = value
    else:
        s = str(value)
        if not s or s.lower() == "nan":
            return []
        parts: List[str] = []
        for chunk in s.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in chunk.split(",")])
    return [p for p in (p.strip() for p in parts) if p]


def normalize_odp_id(raw: str) -> str:
    """
    Best-effort canonicalization for ODP/PRM ids.

    Notes:
      - This is intentionally heuristic and must never "invent" ids.
      - It only normalizes formatting (zero-padding, separators) so comparisons are stable.
    """
    s = (raw or "").strip()
    if not s:
        return ""

    # preserve the special sentinel used by the pipeline
    if s == _ASSIGNMENT_REQUIRED_SENTINEL:
        return s

    t = re.sub(r"\s+", "", s.lower())

    if t in {"assignment_required", "assignmentrequired"}:
        return _ASSIGNMENT_REQUIRED_SENTINEL

    # Canonical / near-canonical: ra-03_odp.02 ; ac-02.05_prm.01 ; at-2_prm_1
    m = re.match(r"^([a-z]{2})-?(\d{1,2})(?:\.(\d{1,2}))?_(odp|prm)[\._-]?(\d{1,2})$", t)
    if m:
        fam, ctrl, enh, kind, idx = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        ctrl_s = f"{int(ctrl):02d}"
        enh_s = f".{int(enh):02d}" if enh is not None else ""
        idx_s = f"{int(idx):02d}"
        return f"{fam}-{ctrl_s}{enh_s}_{kind}.{idx_s}"

    # Legacy form: cp-02.06_odp  (meaning control=02, idx=06, kind=odp)
    m2 = re.match(r"^([a-z]{2})-(\d{1,2})\.(\d{1,2})_(odp|prm)$", t)
    if m2:
        fam, ctrl, idx, kind = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
        return f"{fam}-{int(ctrl):02d}_{kind}.{int(idx):02d}"

    # If we cannot confidently normalize, return a conservative cleaned token
    return t
def _extract_placeholder_token(payload: str) -> Optional[str]:
    """
    Extract the ODP/PRM token from the placeholder payload after 'insert:'.

    Examples of payload:
      - "param, ac-02_odp.05"
      - "ac-7_odp_1"
      - "param,  ac-07_odp.01  "
    Strategy:
      - split by comma, take the last segment
      - take the first whitespace-delimited token
      - normalize_odp_id
    """
    if not payload:
        return None
    # take last comma-separated segment (covers "param, <id>")
    tail = payload.split(",")[-1].strip()
    if not tail:
        return None
    tok = tail.split()[0].strip()
    if not tok:
        return None
    return normalize_odp_id(tok)


def extract_odp_ids_from_text(text: str) -> List[str]:
    """Extract ODP/PRM IDs from {+ insert: ... }+ patterns (robust to brace count and optional 'param,')."""
    if not text:
        return []
    ids: List[str] = []
    for m in _ODP_CURLY_RE.finditer(text):
        payload = m.group(1)
        tok = _extract_placeholder_token(payload)
        if tok:
            ids.append(tok)
    return sorted(set(ids))


def has_unresolved_odp_placeholder(text: str) -> bool:
    """
    Returns True if text contains:
      - curly placeholders { insert: ... } / {{ insert: ... }}
      - OR [assignment: ...] bracket placeholders
    """
    if not text:
        return False
    return bool(_ODP_CURLY_RE.search(text) or _ODP_ASSIGNMENT_RE.search(text))


def doc_id_candidates(source_id: str) -> List[str]:
    """
    Generate reasonable doc-id candidates:
      - as-is
      - last segment after ':', '/', '#'
      - lowercased variants
    """
    s = (source_id or "").strip()
    if not s:
        return []
    cands = [s]
    for sep in (":", "/", "#"):
        if sep in s:
            cands.append(s.split(sep)[-1].strip())
    cands.extend([c.lower() for c in cands])
    out: List[str] = []
    seen: Set[str] = set()
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def resolve_official_text(source_id: str, corpus: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Returns (official_text, matched_key) if it can locate by doc id or normalized key."""
    if not corpus:
        return None, None

    for cand in doc_id_candidates(source_id):
        if cand in corpus:
            return corpus[cand], cand

    lower_map = {k.lower(): k for k in corpus.keys()}
    for cand in doc_id_candidates(source_id):
        k = lower_map.get(cand.lower())
        if k:
            return corpus[k], k

    return None, None


def parse_control_from_source_id(source_id: str) -> Optional[str]:
    if not source_id:
        return None
    m = _CTRL_RE.search(source_id.upper())
    return _canonicalize_control_id(m.group(1)) if m else None


# ==========================================================
# 4) Verifiable Proof Logic
# ==========================================================

def verify_span_against_corpus(span_text: str, official_text: str) -> Tuple[bool, bool]:
    """
    Returns (strict_ok, normalized_ok).
    - strict_ok: span is verbatim substring of official text (after whitespace normalization)
    - normalized_ok: allows stripping curly placeholders and [assignment:...] (ODP syntax) before substring check
    """
    if official_text is None:
        return False, False

    span_norm = _normalize_ws(span_text)
    doc_norm = _normalize_ws(official_text)
    strict_ok = bool(span_norm) and (span_norm == doc_norm or span_norm in doc_norm)

    def strip_placeholders(x: str) -> str:
        # remove any brace-based insert placeholders, regardless of brace count
        x = re.sub(r"\{+.*?\}+", "", x, flags=re.DOTALL)
        # remove assignment blocks
        x = re.sub(r"\[\s*assignment\s*:\s*[^\]]+\]", "", x, flags=re.IGNORECASE)
        return _normalize_ws(x)

    span_stripped = strip_placeholders(span_text)
    doc_stripped = strip_placeholders(official_text)
    normalized_ok = bool(span_stripped) and (span_stripped == doc_stripped or span_stripped in doc_stripped)

    return strict_ok, normalized_ok


def compute_set_metrics(gen: Iterable[str], gold: Iterable[str]) -> Dict[str, float]:
    gen_set = {g for g in gen if g}
    gold_set = {g for g in gold if g}

    tp = len(gen_set & gold_set)
    fp = len(gen_set - gold_set)
    fn = len(gold_set - gen_set)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
    }


# ==========================================================
# 5) Check Implementations
# ==========================================================

def check_status_consistency(contract: AnswerContract) -> List[str]:
    errors: List[str] = []
    status = (contract.status or "").strip().upper()

    if status not in {"OK", "PARAMS_REQUIRED", "NO_EVIDENCE", "ERROR"}:
        errors.append("InvalidStatus")
        return errors

    if status == "ERROR":
        errors.append("StatusERROR")
        return errors

    has_placeholders = has_unresolved_odp_placeholder(contract.answer_text) or any(
        has_unresolved_odp_placeholder(s.span_text) for s in contract.evidence_spans
    )

    # Normalize ODP list; treat bad tokens as errors
    odp_list = [normalize_odp_id(x) for x in _split_listish(contract.odp_required_list) if x]
    if any(x in {"param", "insert:param"} for x in odp_list):
        errors.append("ODPListContainsParamToken")

    if status == "PARAMS_REQUIRED":
        if not has_placeholders:
            errors.append("ParamsRequiredButNoPlaceholders")
        if not odp_list:
            errors.append("ParamsRequiredButODPListEmpty")

    if status == "OK" and has_placeholders:
        errors.append("OKButUnresolvedODPPlaceholders")

    if status == "NO_EVIDENCE":
        if contract.evidence_spans:
            errors.append("NoEvidenceButSpansProvided")
        if _normalize_ws(contract.answer_text) not in {"", "NO_EVIDENCE"}:
            errors.append("NoEvidenceButAnswerTextNonEmpty")

    return errors


def check_citations(contract: AnswerContract, gold: GoldLabel, strict_extras: bool = True) -> Tuple[List[str], Dict[str, float], Dict[str, float]]:
    """
    Citation checks:
      - Control-level: parse controls from evidence_spans.source_id
      - Doc-id level: compare evidence_spans.source_id vs gold.doc_ids (best-effort mapping via doc_id_candidates)
    Returns: (errors, control_metrics, doc_metrics)
    """
    errors: List[str] = []

    gen_ctrls = sorted(set(filter(None, (parse_control_from_source_id(s.source_id) for s in contract.evidence_spans))))
    gold_ctrls = sorted(set(filter(None, (normalize_control_id(c) for c in gold.control_ids))))
    control_metrics = compute_set_metrics(gen_ctrls, gold_ctrls) if gold_ctrls else {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}

    gold_doc_ids = [d.strip() for d in gold.doc_ids if d and str(d).strip().lower() != "nan"]
    gold_doc_lower = {d.lower(): d for d in gold_doc_ids}

    gen_doc_ids: List[str] = []
    for s in contract.evidence_spans:
        chosen: Optional[str] = None
        for cand in doc_id_candidates(s.source_id):
            if cand.lower() in gold_doc_lower:
                chosen = gold_doc_lower[cand.lower()]
                break
        if chosen is None:
            cands = doc_id_candidates(s.source_id)
            chosen = cands[0] if cands else s.source_id
        gen_doc_ids.append(chosen)

    doc_metrics = compute_set_metrics([d.lower() for d in gen_doc_ids], [d.lower() for d in gold_doc_ids]) if gold_doc_ids else {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}

    if gold_ctrls:
        missing_ctrls = sorted(set(gold_ctrls) - set(gen_ctrls))
        extra_ctrls = sorted(set(gen_ctrls) - set(gold_ctrls))
        if missing_ctrls:
            errors.append(f"MissedControlCitations:{missing_ctrls}")
        if extra_ctrls and strict_extras:
            errors.append(f"ExtraControlCitations:{extra_ctrls}")

    if gold_doc_ids:
        gen_doc_set = {d.lower() for d in gen_doc_ids if d}
        gold_doc_set = {d.lower() for d in gold_doc_ids if d}
        missing_docs = sorted(gold_doc_set - gen_doc_set)
        extra_docs = sorted(gen_doc_set - gold_doc_set)
        if missing_docs:
            errors.append(f"MissedDocIds:{missing_docs}")
        if extra_docs and strict_extras:
            errors.append(f"ExtraDocIds:{extra_docs}")

    return errors, control_metrics, doc_metrics


def check_odp_behavior(
    contract: AnswerContract,
    gold: GoldLabel,
    org_profile: Optional[Dict[str, Any]] = None,
    strict_odp_extras: bool = True,
) -> List[str]:
    """
    Checks:
      - If gold requires ODPs and policy=ASK or PRESERVE: status must be PARAMS_REQUIRED
      - If policy=PRESERVE: placeholders for required IDs must appear (format-independent, using extraction)
      - If policy=FILL_FROM_PROFILE and org_profile provided:
          - if all required are present -> OK
          - else -> PARAMS_REQUIRED
      - odp_required_list should match extracted placeholder ids when extractable
    """
    errors: List[str] = []
    status = (contract.status or "").strip().upper()

    gold_odps = [normalize_odp_id(x) for x in gold.odp_ids_required]
    gold_odps = sorted(set([x for x in gold_odps if x]))

    gen_odps = [normalize_odp_id(x) for x in _split_listish(contract.odp_required_list)]
    gen_odps = sorted(set([x for x in gen_odps if x]))

    extracted: List[str] = []
    extracted.extend(extract_odp_ids_from_text(contract.answer_text))
    if not extracted:
        for s in contract.evidence_spans:
            extracted.extend(extract_odp_ids_from_text(s.span_text))
    extracted = sorted(set(extracted))

    if extracted and status == "PARAMS_REQUIRED":
        if set(extracted) != set(gen_odps):
            errors.append(f"ODPListMismatch:extracted={extracted},gen_list={gen_odps}")

    if gold_odps:
        policy = (gold.resolution_policy or "").strip().upper()

        if policy in {"ASK", "PRESERVE"}:
            if status != "PARAMS_REQUIRED":
                errors.append("GoldPolicyASKButStatusNotParamsRequired")

        if policy == "PRESERVE":
            # PRESERVE requires literal placeholder preservation for each required ODP token.
            combined_ids: Set[str] = set()
            combined_ids.update(extract_odp_ids_from_text(contract.answer_text))
            for s in contract.evidence_spans:
                combined_ids.update(extract_odp_ids_from_text(s.span_text))
            missing = [tok for tok in gold_odps if tok not in combined_ids]
            for tok in missing:
                errors.append(f"PreserveMissingPlaceholder:{tok}")

        elif policy == "FILL_FROM_PROFILE":
            if org_profile is None:
                # Preserve v2 behavior: treat as a hard error (not WARN) because we cannot validate fill.
                errors.append("GoldPolicyFillFromProfileButNoOrgProfileProvided")
            else:
                odp_values = org_profile.get("odp_values", org_profile) if isinstance(org_profile, dict) else {}
                present = set(normalize_odp_id(k) for k in odp_values.keys()) if isinstance(odp_values, dict) else set()
                missing = sorted(set(gold_odps) - present)
                if missing:
                    if status != "PARAMS_REQUIRED":
                        errors.append(f"MissingODPsButStatusNotParamsRequired:{missing}")
                else:
                    if status != "OK":
                        errors.append("AllODPsPresentButStatusNotOK")

        if status == "PARAMS_REQUIRED" and gen_odps:
            gold_set = set(gold_odps)
            gen_set = set(gen_odps)
            missing = sorted(gold_set - gen_set)
            extra = sorted(gen_set - gold_set)
            # Missing required ODPs is always a hard error.
            # Extra ODPs are allowed when strict_odp_extras=False (e.g., research mode tolerating over-asking).
            if missing or (extra and strict_odp_extras):
                errors.append(f"ODPRequiredListNotEqualGold:gold={gold_odps},gen={gen_odps}")

        if status == "OK" and has_unresolved_odp_placeholder(contract.answer_text):
            errors.append("StatusOKButStillHasODPPlaceholders")

    return errors


def check_version_correctness(contract: AnswerContract, gold: GoldLabel, strict_version: bool = False, corpus_version: Optional[str] = None) -> List[str]:
    """
    Enforces version correctness only when provable.
      - If corpus_version is supplied, compare it.
      - Else if source_id strings contain 'rev4'/'rev5', compare those.
      - Otherwise: if strict_version=True, fail; else emit a warning tag.
    """
    errors: List[str] = []
    expected = gold.version

    if expected not in {"rev4", "rev5"}:
        return errors

    if corpus_version:
        cv = normalize_version(corpus_version)
        if cv in {"rev4", "rev5"} and cv != expected:
            errors.append(f"CorpusVersionMismatch:expected={expected},got={cv}")
        return errors

    found_versions = set()
    for s in contract.evidence_spans:
        sid = (s.source_id or "").lower()
        if "rev4" in sid:
            found_versions.add("rev4")
        if "rev5" in sid:
            found_versions.add("rev5")

    if found_versions:
        if len(found_versions) > 1:
            errors.append(f"MixedVersionsInCitations:{sorted(found_versions)}")
        elif next(iter(found_versions)) != expected:
            errors.append(f"VersionMismatchInCitations:expected={expected},got={next(iter(found_versions))}")
    else:
        if strict_version:
            errors.append("VersionNotProvableFromSourceIds")
        else:
            errors.append("WARN:VersionNotProvableFromSourceIds")

    return errors


# ==========================================================
# 6) Main Entry Point (compat)
# ==========================================================

def _gold_get_odp_required(gold_row: Dict[str, Any]) -> Any:
    """
    Compatibility helper: support multiple column names for required ODP/PRM IDs.
    Current gold sets use 'odp_required', but some pipeline paths may use 'odp_ids_required'.
    """
    for key in ("odp_required", "odp_ids_required", "odp_required_list"):
        if key in gold_row and gold_row.get(key) is not None:
            return gold_row.get(key)
    return None


def _gold_get_doc_ids(gold_row: Dict[str, Any]) -> Any:
    """Compatibility helper for gold doc-id column names."""
    for key in ("gold_control_path", "gold_doc_ids", "doc_ids"):
        if key in gold_row and gold_row.get(key) is not None:
            return gold_row.get(key)
    return None


def verify_answer(
    json_output: Dict[str, Any],
    gold_row: Dict[str, Any],
    corpus: Optional[Dict[str, str]] = None,
    *,
    org_profile: Optional[Dict[str, Any]] = None,
    corpus_version: Optional[str] = None,
    strict_extras: bool = True,
    strict_verbatim: bool = True,
    strict_version: bool = False,
) -> VerifierResult:
    """
    Verify a single model output against a single gold row.

    Pass criteria (default, unchanged from v2):
      - no hard errors
      - 100% control-id recall (when gold control_id exists)
      - verbatim strict proof passes for all spans (when corpus provided and strict_verbatim=True)
    """
    # ---- gold parsing (compat)
    qid = str(gold_row.get("query_id", gold_row.get("ID", gold_row.get("id", "unknown"))))

    gold_control = normalize_control_id(gold_row.get("control_id"))
    gold_doc_ids = _split_listish(_gold_get_doc_ids(gold_row))
    gold_doc_ids = [d.strip() for d in gold_doc_ids if d and str(d).strip().lower() != "nan"]

    gold_odps_raw = _gold_get_odp_required(gold_row)
    gold_odps = _split_listish(gold_odps_raw)
    gold_odps = [normalize_odp_id(x) for x in gold_odps]
    gold_odps = [x for x in gold_odps if x]

    gold_label = GoldLabel(
        question_id=qid,
        framework="NIST SP 800-53",
        version=normalize_version(gold_row.get("gold_source_version")),
        control_ids=[gold_control] if gold_control else [],
        doc_ids=gold_doc_ids,
        odp_ids_required=gold_odps,
        resolution_policy=str(gold_row.get("resolution_policy", "") if gold_row.get("resolution_policy") is not None else ""),
    )

    # ---- contract parsing (model output)
    try:
        spans_raw = json_output.get("evidence_spans", []) or []
        evidence_spans: List[EvidenceSpan] = []
        for s in spans_raw:
            if isinstance(s, dict):
                evidence_spans.append(EvidenceSpan(
                    source_id=str(s.get("source_id", "")),
                    span_text=str(s.get("span_text", "")),
                ))
            else:
                evidence_spans.append(EvidenceSpan(source_id=str(s), span_text=""))

        contract = AnswerContract(
            answer_text=str(json_output.get("answer_text", "")),
            evidence_spans=evidence_spans,
            status=str(json_output.get("status", "ERROR")),
            odp_required_list=_split_listish(json_output.get("odp_required_list", [])),
        )
    except Exception:
        return VerifierResult(qid, False, ["MalformedJSON"], {"control_precision": 0.0, "control_recall": 0.0, "control_f1": 0.0})

    # Short-circuit: ERROR is a valid contract status but not a "pass" outcome.
    status_up = (contract.status or "").strip().upper()
    if status_up == "ERROR":
        metrics: Dict[str, float] = {
            "control_precision": 0.0,
            "control_recall": 0.0,
            "control_f1": 0.0,
            "doc_precision": 0.0,
            "doc_recall": 0.0,
            "doc_f1": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "verbatim_strict_pass_rate": float("nan"),
            "verbatim_normalized_pass_rate": float("nan"),
        }
        return VerifierResult(
            question_id=qid,
            is_pass=False,
            error_tags=["StatusERROR"],
            metrics=metrics,
        )

    # ---- checks
    errors: List[str] = []

    errors.extend(check_status_consistency(contract))
    errors.extend(check_odp_behavior(contract, gold_label, org_profile=org_profile, strict_odp_extras=bool(strict_extras)))
    errors.extend(check_version_correctness(contract, gold_label, strict_version=strict_version, corpus_version=corpus_version))

    cit_errors, ctrl_metrics, doc_metrics = check_citations(contract, gold_label, strict_extras=strict_extras)
    errors.extend(cit_errors)

    # verbatim proof (when corpus is available)
    strict_ok_count = 0
    norm_ok_count = 0
    checked = 0

    if corpus and contract.evidence_spans:
        for span in contract.evidence_spans:
            official, matched_key = resolve_official_text(span.source_id, corpus)
            if official is None:
                errors.append(f"CorpusMissingSourceId:{span.source_id}")
                checked += 1
                continue

            strict_ok, norm_ok = verify_span_against_corpus(span.span_text, official)
            checked += 1
            strict_ok_count += int(strict_ok)
            norm_ok_count += int(norm_ok)

            if strict_verbatim:
                if not strict_ok:
                    errors.append(f"NonVerbatimStrict:{span.source_id}::matched={matched_key}")
            else:
                if not norm_ok:
                    errors.append(f"NonVerbatimNormalized:{span.source_id}::matched={matched_key}")

    # ---- pass/fail (unchanged)
    is_pass = True

    if gold_label.control_ids and ctrl_metrics.get("recall", 0.0) < 1.0:
        is_pass = False
        errors.append("LowControlRecall")

    hard_errors = [e for e in errors if not e.startswith("WARN:")]
    if hard_errors:
        is_pass = False

    # ---- metrics (unchanged keys)
    metrics: Dict[str, float] = {
        "control_precision": float(ctrl_metrics.get("precision", 0.0)),
        "control_recall": float(ctrl_metrics.get("recall", 0.0)),
        "control_f1": float(ctrl_metrics.get("f1", 0.0)),
        "doc_precision": float(doc_metrics.get("precision", 0.0)),
        "doc_recall": float(doc_metrics.get("recall", 0.0)),
        "doc_f1": float(doc_metrics.get("f1", 0.0)),
    }

    metrics["precision"] = metrics["control_precision"]
    metrics["recall"] = metrics["control_recall"]
    metrics["f1"] = metrics["control_f1"]

    if checked:
        metrics["verbatim_strict_pass_rate"] = strict_ok_count / checked
        metrics["verbatim_normalized_pass_rate"] = norm_ok_count / checked
    else:
        metrics["verbatim_strict_pass_rate"] = float("nan")
        metrics["verbatim_normalized_pass_rate"] = float("nan")

    return VerifierResult(
        question_id=qid,
        is_pass=is_pass,
        error_tags=errors,
        metrics=metrics,
    )


# ==========================================================
# Contract-only validity checks (no gold dependence)
# ==========================================================

def parse_answer_contract(json_output: Dict[str, Any]) -> AnswerContract:
    """Parse runtime-visible contract fields without consulting gold labels."""
    spans_raw = json_output.get("evidence_spans", []) or []
    evidence_spans: List[EvidenceSpan] = []

    for span in spans_raw:
        if isinstance(span, dict):
            evidence_spans.append(EvidenceSpan(
                source_id=str(span.get("source_id", "")),
                span_text=str(span.get("span_text", "")),
            ))
        else:
            evidence_spans.append(EvidenceSpan(
                source_id=str(span),
                span_text="",
            ))

    return AnswerContract(
        answer_text=str(json_output.get("answer_text", "")),
        evidence_spans=evidence_spans,
        status=str(json_output.get("status", "ERROR")),
        odp_required_list=_split_listish(json_output.get("odp_required_list", [])),
    )

def verify_contract_validity(
    json_output: Dict[str, Any],
    corpus: Optional[Dict[str, str]] = None,
    org_profile: Optional[Dict[str, Any]] = None,
    strict_verbatim: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Validate the answer contract without using gold labels.

    This is intentionally separate from verify_answer(), which mixes:
      (a) contract validity, and
      (b) agreement with a particular gold labeling (doc ids, controls, policy).

    Returns:
      (is_pass, error_tags)
    """
    errors: List[str] = []

    # Basic structural checks
    if not isinstance(json_output, dict):
        return False, ["ContractNotDict"]

    status = str(json_output.get("status", "") or "").strip().upper()
    spans = json_output.get("evidence_spans", [])
    if spans is None:
        spans = []
    if not isinstance(spans, list):
        errors.append("EvidenceSpansNotList")
        spans = []

    if status == "NO_EVIDENCE":
        if spans:
            errors.append("NoEvidenceButHasSpans")
    elif status in {"OK", "PARAMS_REQUIRED"}:
        if not spans:
            errors.append("MissingEvidenceSpans")
    elif status == "ERROR":
        # ERROR is allowed to have empty spans.
        pass
    else:
        errors.append("UnknownStatus")

    for sp in spans:
        if not isinstance(sp, dict):
            errors.append("EvidenceSpanNotDict")
            continue
        sid = str(sp.get("source_id", "") or "").strip()
        stxt = str(sp.get("span_text", "") or "")
        if not sid:
            errors.append("MissingSourceId")
        if status != "NO_EVIDENCE" and not str(stxt).strip():
            errors.append("MissingSpanText")

        if corpus is not None and sid:
            official, _matched_key = resolve_official_text(sid, corpus)
            if official is None:
                errors.append("UnknownSourceId")
            else:
                strict_ok, normalized_ok = verify_span_against_corpus(stxt, official)
                span_ok = strict_ok if strict_verbatim else normalized_ok
                if not span_ok:
                    errors.append("SpanNotVerbatim")

    # Contract consistency checks (placeholders vs odp list vs status)
    try:
        contract = parse_answer_contract(json_output)
        errors.extend(check_status_consistency(contract))
    except Exception:
        errors.append("ContractParseError")

    # Ensure error tags are unique and deterministic order
    errors = sorted(set(errors))
    return (len(errors) == 0), errors
