import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Iterable


# ==========================================================
# ComplianceGPT Verifier (v2)
# Goal: mechanically verifiable, auditable QA checks:
#   - Status mutual consistency (OK / PARAMS_REQUIRED / NO_EVIDENCE)
#   - Citation correctness (control-level + optional doc-id level)
#   - ODP behavior correctness (placeholder detection + required list)
#   - Version correctness (when provable)
#   - Verbatim evidence proof vs corpus (strict + normalized)
# ==========================================================


# -----------------------------
# Data models
# -----------------------------
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
    resolution_policy: str          # "ASK", "FILL_FROM_PROFILE", or ""


@dataclass
class VerifierResult:
    question_id: str
    is_pass: bool
    error_tags: List[str]
    metrics: Dict[str, float]


# -----------------------------
# Normalization helpers
# -----------------------------
_CTRL_RE = re.compile(r"\b([A-Z]{2}-\d+(?:\(\d+\))?)\b")
_VER_RE = re.compile(r"\brev(?:ision)?\s*([45])\b", flags=re.IGNORECASE)

# Common ODP patterns observed in your gold sets, e.g.:
#   {{ insert: param, ac-02_odp.05 }}
#   {{insert:param,ra-9_odp_1}}
_ODP_CURLY_RE = re.compile(r"\{\{\s*insert\s*:\s*param\s*,\s*([^}\s]+)\s*\}\}", flags=re.IGNORECASE)

# Some NIST texts also include:
#   [assignment: organization-defined parameter]
# This does not carry an ID in that form, but it indicates unresolved ODP.
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
    # Allow "Revision 5", "Rev 5", "rev5"
    m = _VER_RE.search(s.replace(".", " "))
    if m:
        return f"rev{m.group(1)}"
    # As fallback, detect raw "5" or "4" if string looks like a revision label
    if "5" in s and "rev" in s.lower():
        return "rev5"
    if "4" in s and "rev" in s.lower():
        return "rev4"
    return "unknown"


def normalize_control_id(s: Any) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip().upper()
    if not t or t.lower() == "nan":
        return None
    m = _CTRL_RE.search(t)
    return m.group(1) if m else None


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
        # Split on newlines first; then commas.
        parts = []
        for chunk in s.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in chunk.split(",")])
    return [p for p in (p.strip() for p in parts) if p]


def normalize_odp_id(raw: str) -> str:
    """
    Make ODP IDs comparable across minor formatting differences.
    Example: "ac-02_odp.5" -> "ac-02_odp.05" (pad single digit after 'odp.')
    """
    s = (raw or "").strip().lower()
    # collapse whitespace
    s = re.sub(r"\s+", "", s)

    # normalize common variants like ac_02 -> ac-02 (optional; keep both in matching)
    s = s.replace("ac_","ac-").replace("ra_","ra-").replace("pl_","pl-").replace("pm_","pm-")
    s = s.replace("__","_")

    # pad ".<digit>" after "odp."
    # e.g., odp.5 -> odp.05
    s = re.sub(r"(odp\.)\b(\d)\b", r"\g<1>0\2", s)

    return s


def extract_odp_ids_from_text(text: str) -> List[str]:
    """
    Extracts ODP IDs from brace placeholders.
    Returns normalized ODP IDs.
    """
    if not text:
        return []
    ids = [normalize_odp_id(m.group(1)) for m in _ODP_CURLY_RE.finditer(text)]
    return sorted(set(i for i in ids if i))


def has_unresolved_odp_placeholder(text: str) -> bool:
    """
    Detects unresolved ODP markers, including curly and [assignment: ...].
    """
    if not text:
        return False
    return bool(_ODP_CURLY_RE.search(text) or _ODP_ASSIGNMENT_RE.search(text))


def truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if not s or s == "nan":
        return False
    return s not in {"false", "0", "no", "none", ""}


# -----------------------------
# Source-id resolution
# -----------------------------
def doc_id_candidates(source_id: str) -> List[str]:
    """
    Generate reasonable doc-id candidates:
      - as-is
      - last segment after ':' or '/' (common for fully-qualified IDs)
      - lowercased variants
    """
    s = (source_id or "").strip()
    if not s:
        return []
    cands = [s]
    # common separators
    for sep in (":", "/", "#"):
        if sep in s:
            cands.append(s.split(sep)[-1].strip())
    # lower variants
    cands.extend([c.lower() for c in cands])
    # de-dup
    out = []
    seen = set()
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def resolve_official_text(source_id: str, corpus: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (official_text, matched_key) if it can locate by doc id or normalized key.
    """
    if not corpus:
        return None, None

    # direct matching with multiple candidates
    for cand in doc_id_candidates(source_id):
        if cand in corpus:
            return corpus[cand], cand

    # Try case-insensitive match
    lower_map = {k.lower(): k for k in corpus.keys()}
    for cand in doc_id_candidates(source_id):
        k = lower_map.get(cand.lower())
        if k:
            return corpus[k], k

    return None, None


def parse_control_from_source_id(source_id: str) -> Optional[str]:
    """
    Extracts control ID from any source_id using regex.
    """
    if not source_id:
        return None
    m = _CTRL_RE.search(str(source_id).upper())
    return m.group(1) if m else None


# -----------------------------
# Verbatim proof
# -----------------------------
def verify_span_against_corpus(span_text: str, official_text: str) -> Tuple[bool, bool]:
    """
    Returns:
      (strict_ok, normalized_ok)
    strict_ok: normalized whitespace containment
    normalized_ok: additionally strips ODP placeholders on BOTH sides before containment
    """
    if official_text is None:
        return False, False

    span_norm = _normalize_ws(span_text)
    doc_norm = _normalize_ws(official_text)

    strict_ok = bool(span_norm) and (span_norm == doc_norm or span_norm in doc_norm)

    # Normalized: strip placeholder syntax (both curly + assignment) on both sides
    def strip_placeholders(x: str) -> str:
        x = re.sub(r"\{\{.*?\}\}", "", x)
        x = re.sub(r"\[\s*assignment\s*:\s*[^\]]+\]", "", x, flags=re.IGNORECASE)
        return _normalize_ws(x)

    span_stripped = strip_placeholders(span_text)
    doc_stripped = strip_placeholders(official_text)

    normalized_ok = bool(span_stripped) and (span_stripped == doc_stripped or span_stripped in doc_stripped)

    return strict_ok, normalized_ok


# -----------------------------
# Checks
# -----------------------------
def check_status_consistency(contract: AnswerContract) -> List[str]:
    errors: List[str] = []

    status = (contract.status or "").strip().upper()
    if status not in {"OK", "PARAMS_REQUIRED", "NO_EVIDENCE"}:
        errors.append("InvalidStatus")

    # Look for unresolved ODP placeholders in answer_text OR in any span.
    has_placeholders = has_unresolved_odp_placeholder(contract.answer_text) or any(
        has_unresolved_odp_placeholder(s.span_text) for s in contract.evidence_spans
    )

    # Normalize odp_required_list
    odp_list = [normalize_odp_id(x) for x in _split_listish(contract.odp_required_list)]
    odp_list = [x for x in odp_list if x]

    # Catch the classic bug where "param" is mistakenly used as ODP id.
    if any(x in {"param", "insert:param", "insert:param"} for x in odp_list):
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
        # allow answer_text empty or "NO_EVIDENCE"
        if _normalize_ws(contract.answer_text) not in {"", "NO_EVIDENCE"}:
            errors.append("NoEvidenceButAnswerTextNonEmpty")

    return errors


def compute_set_metrics(gen: Iterable[str], gold: Iterable[str]) -> Dict[str, float]:
    gen_set = {g for g in gen if g}
    gold_set = {g for g in gold if g}

    tp = len(gen_set & gold_set)
    fp = len(gen_set - gold_set)
    fn = len(gold_set - gen_set)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {"precision": precision, "recall": recall, "f1": f1, "tp": float(tp), "fp": float(fp), "fn": float(fn)}


def check_citations(contract: AnswerContract, gold: GoldLabel, strict_extras: bool = True) -> Tuple[List[str], Dict[str, float], Dict[str, float]]:
    """
    Returns:
      (error_tags, control_metrics, doc_metrics)
    """
    errors: List[str] = []

    # Control-level from generated evidence spans
    gen_ctrls = sorted(set(filter(None, (parse_control_from_source_id(s.source_id) for s in contract.evidence_spans))))
    gold_ctrls = sorted(set(filter(None, (normalize_control_id(c) for c in gold.control_ids))))

    control_metrics = compute_set_metrics(gen_ctrls, gold_ctrls)

    # Doc-id level (if gold doc_ids provided)
    gold_doc_ids = [d.strip() for d in gold.doc_ids if d and str(d).strip().lower() != "nan"]
    gold_doc_lower = {d.lower(): d for d in gold_doc_ids}

    gen_doc_ids: List[str] = []
    for s in contract.evidence_spans:
        chosen = None
        for cand in doc_id_candidates(s.source_id):
            if cand.lower() in gold_doc_lower:
                chosen = gold_doc_lower[cand.lower()]
                break
        if chosen is None:
            # keep a normalized candidate for metrics (best effort)
            cands = doc_id_candidates(s.source_id)
            chosen = cands[0] if cands else s.source_id
        gen_doc_ids.append(chosen)

    doc_metrics = compute_set_metrics([d.lower() for d in gen_doc_ids], [d.lower() for d in gold_doc_ids]) if gold_doc_ids else {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}

    # Error tags for strict evaluation
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


def check_odp_behavior(contract: AnswerContract, gold: GoldLabel, org_profile: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Checks:
      - if gold requires ODPs and policy=ASK, status should be PARAMS_REQUIRED
      - if policy=FILL_FROM_PROFILE and org_profile provided:
          - if all required are present -> OK
          - else -> PARAMS_REQUIRED
      - odp_required_list should match extracted placeholder ids when extractable
    """
    errors: List[str] = []
    status = (contract.status or "").strip().upper()

    gold_odps = [normalize_odp_id(x) for x in gold.odp_ids_required]
    gold_odps = sorted(set([x for x in gold_odps if x]))

    # Parse generated list
    gen_odps = [normalize_odp_id(x) for x in _split_listish(contract.odp_required_list)]
    gen_odps = sorted(set([x for x in gen_odps if x]))

    # Extract from text (if present)
    extracted = extract_odp_ids_from_text(contract.answer_text)
    if not extracted:
        for s in contract.evidence_spans:
            extracted.extend(extract_odp_ids_from_text(s.span_text))
    extracted = sorted(set(extracted))

    # If we can extract IDs from placeholders, they should be consistent with gen_odps.
    if extracted:
        if status == "PARAMS_REQUIRED":
            if set(extracted) != set(gen_odps):
                errors.append(f"ODPListMismatch:extracted={extracted},gen_list={gen_odps}")

    # Compare against gold ODP list (when provided)
    if gold_odps:
        # If gold says ASK, you should not claim OK unless you explicitly provide an org_profile-based fill
        policy = (gold.resolution_policy or "").strip().upper()
        if policy == "ASK":
            if status != "PARAMS_REQUIRED":
                errors.append("GoldPolicyASKButStatusNotParamsRequired")
        elif policy == "FILL_FROM_PROFILE":
            if org_profile is None:
                # cannot confirm; do not hard-fail, but flag as not provable
                errors.append("GoldPolicyFillFromProfileButNoOrgProfileProvided")
            else:
                # org_profile expected to be a mapping from ODP id -> value (or nested; you can adapt upstream)
                # We'll support either flat keys or nested under "odp_values".
                odp_values = org_profile.get("odp_values", org_profile) if isinstance(org_profile, dict) else {}
                present = set(normalize_odp_id(k) for k in odp_values.keys()) if isinstance(odp_values, dict) else set()
                missing = sorted(set(gold_odps) - present)
                if missing:
                    if status != "PARAMS_REQUIRED":
                        errors.append(f"MissingODPsButStatusNotParamsRequired:{missing}")
                else:
                    if status != "OK":
                        errors.append("AllODPsPresentButStatusNotOK")

        # If gold provides a list, generated ODP list should equal gold list in PARAMS_REQUIRED mode.
        if status == "PARAMS_REQUIRED" and gen_odps and set(gen_odps) != set(gold_odps):
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


# -----------------------------
# Main entry point (compat)
# -----------------------------
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

    Pass criteria (default):
      - no hard errors
      - 100% control-id recall (when gold control_id exists)
      - verbatim strict proof passes for all spans (when corpus provided)
    """
    # ---- gold parsing
    qid = str(gold_row.get("query_id", gold_row.get("ID", gold_row.get("id", "unknown"))))

    gold_control = normalize_control_id(gold_row.get("control_id"))
    gold_doc_ids = _split_listish(gold_row.get("gold_control_path"))
    gold_doc_ids = [d.strip() for d in gold_doc_ids if d and str(d).strip().lower() != "nan"]

    gold_odps = _split_listish(gold_row.get("odp_required"))
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

    # ---- contract parsing
    try:
        spans_raw = json_output.get("evidence_spans", []) or []
        evidence_spans = []
        for s in spans_raw:
            if isinstance(s, dict):
                evidence_spans.append(EvidenceSpan(
                    source_id=str(s.get("source_id", "")),
                    span_text=str(s.get("span_text", "")),
                ))
            else:
                # tolerate unexpected span representations
                evidence_spans.append(EvidenceSpan(source_id=str(s), span_text=""))

        contract = AnswerContract(
            answer_text=str(json_output.get("answer_text", "")),
            evidence_spans=evidence_spans,
            status=str(json_output.get("status", "ERROR")),
            odp_required_list=_split_listish(json_output.get("odp_required_list", [])),
        )
    except Exception:
        return VerifierResult(qid, False, ["MalformedJSON"], {"control_precision": 0.0, "control_recall": 0.0, "control_f1": 0.0})

    # ---- checks
    errors: List[str] = []

    # status mutual consistency
    errors.extend(check_status_consistency(contract))

    # ODP behavior vs gold
    errors.extend(check_odp_behavior(contract, gold_label, org_profile=org_profile))

    # version correctness (when provable)
    errors.extend(check_version_correctness(contract, gold_label, strict_version=strict_version, corpus_version=corpus_version))

    # citations
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

    # ---- pass/fail
    is_pass = True

    # Require 100% control recall if control_id exists in gold
    if gold_label.control_ids and ctrl_metrics.get("recall", 0.0) < 1.0:
        is_pass = False
        errors.append("LowControlRecall")

    # Hard errors (treat WARN tags as non-fatal)
    hard_errors = [e for e in errors if not e.startswith("WARN:")]
    if hard_errors:
        is_pass = False

    # ---- metrics
    metrics: Dict[str, float] = {
        "control_precision": float(ctrl_metrics.get("precision", 0.0)),
        "control_recall": float(ctrl_metrics.get("recall", 0.0)),
        "control_f1": float(ctrl_metrics.get("f1", 0.0)),
        "doc_precision": float(doc_metrics.get("precision", 0.0)),
        "doc_recall": float(doc_metrics.get("recall", 0.0)),
        "doc_f1": float(doc_metrics.get("f1", 0.0)),
    }


    # Backward-compatible aliases (legacy notebooks expect these)
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
