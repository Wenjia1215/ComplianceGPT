"""Answer-content strict pass for frozen answer contracts.

The legacy verifier remains unchanged. Semantic judgments are input records,
not keyword rules, model calls, or system-specific exceptions. Missing or
uncertain judgments never receive strict-pass credit.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from compliancegpt.generator.verifier.verifier import (
    normalize_odp_id,
    verify_answer,
)


RULE_VERSION = "answer-content-strict-pass-v1"
SEMANTIC_GATES = (
    "citation_use", "answer_coverage", "claim_faithfulness", "parameter_semantics",
)
VERDICTS = {"pass", "fail", "uncertain"}
ASSIGNMENT_SENTINEL = "__ASSIGNMENT_REQUIRED__"


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def answer_surface(revision: str, query_id: str, contract: Mapping[str, Any]) -> dict:
    """Exclude system identity, legacy scores, model metadata and debug traces."""
    return {
        "revision": revision,
        "query_id": str(query_id),
        "question": str(contract.get("question", "")),
        "answer_text": str(contract.get("answer_text", "")),
        "evidence_spans": contract.get("evidence_spans", []),
        "status": contract.get("status"),
        "odp_required_list": contract.get("odp_required_list", []),
        "ask_list": contract.get("ask_list", []),
    }


def review_id(revision: str, query_id: str, contract: Mapping[str, Any]) -> str:
    return canonical_sha256(answer_surface(revision, query_id, contract))


def _listish(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [x.strip() for x in re.split(r"[,\n]", str(value or "")) if x.strip()]


def parameter_inventory(records: Mapping[str, Mapping[str, Any]]) -> dict[str, dict]:
    return {source_id: dict(record) for source_id, record in records.items() if record.get("kind") in {"odp", "prm"}}


def resolve_parameter_id(raw: str, inventory: Mapping[str, Mapping[str, Any]]) -> str:
    """Prefer exact inventory identity; accept only unambiguous legacy aliases.

    The legacy normalizer can map a parent ODP and an enhancement ODP to the
    same string. Never merge those distinct canonical parameters here.
    """
    token = str(raw).strip()
    if token == ASSIGNMENT_SENTINEL or token in inventory:
        return token
    lower_matches = [pid for pid in inventory if pid.lower() == token.lower()]
    if len(lower_matches) == 1:
        return lower_matches[0]
    normalized = normalize_odp_id(token)
    matches = [pid for pid in inventory if normalize_odp_id(pid) == normalized]
    return matches[0] if len(matches) == 1 else token


def retained_parameter_ids(text: str, inventory: Mapping[str, Mapping[str, Any]]) -> set[str]:
    ids = set()
    for payload in re.findall(r"\{+\s*insert\s*:\s*([^}]+?)\s*\}+", text, flags=re.I):
        tail = payload.split(",")[-1].strip()
        if tail:
            ids.add(resolve_parameter_id(tail.split()[0], inventory))
    return ids


def mechanical_checks(contract: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]], window_ids: Sequence[str]) -> dict:
    spans = list(contract.get("evidence_spans", []) or [])
    status = str(contract.get("status", "")).upper()
    answer = str(contract.get("answer_text", ""))
    window = set(window_ids)
    provenance_errors = []
    source_ids = [str(span.get("source_id", "")) for span in spans]
    for source_id in source_ids:
        if source_id not in records or records[source_id].get("kind") not in {"smt", "gdn"}:
            provenance_errors.append(f"NotExactEligibleCCSId:{source_id}")
        if source_id not in window:
            provenance_errors.append(f"OutsideFrozenEvidenceWindow:{source_id}")
    if len(source_ids) != len(set(source_ids)):
        provenance_errors.append("DuplicateEvidenceId")
    if not spans or not answer.strip() or status not in {"OK", "PARAMS_REQUIRED"}:
        provenance_errors.append("NoNormalNonemptyAnswer")

    inventory = parameter_inventory(records)
    expected = retained_parameter_ids(answer, inventory)
    for span in spans:
        expected.update(retained_parameter_ids(str(span.get("span_text", "")), inventory))
        # A named paraphrase's Assignment marker is accounted for by its named
        # canonical spans. Anonymous assignments in the canonical evidence are
        # separate obligations and require the sentinel.
        if re.search(r"\[\s*assignment\s*:", str(span.get("span_text", "")), re.I):
            expected.add(ASSIGNMENT_SENTINEL)
    declared_list = [resolve_parameter_id(x, inventory) for x in _listish(contract.get("odp_required_list"))]
    declared = set(declared_list)
    accounting_errors = []
    if expected != declared:
        accounting_errors.append(f"RetainedParameterUnionMismatch:expected={sorted(expected)},declared={sorted(declared)}")
    if len(declared_list) != len(declared):
        accounting_errors.append("DuplicateDeclaredParameter")
    for pid in declared:
        if pid not in inventory and pid != ASSIGNMENT_SENTINEL:
            accounting_errors.append(f"UnknownDeclaredParameter:{pid}")
    if status != ("PARAMS_REQUIRED" if expected else "OK"):
        accounting_errors.append("StatusNotEqualRetainedParameterState")
    asks = contract.get("ask_list", []) or []
    ask_ids = [resolve_parameter_id(str(ask.get("param_id", "")), inventory) for ask in asks]
    if set(ask_ids) != declared or len(ask_ids) != len(set(ask_ids)):
        accounting_errors.append("AskListNotEqualDeclaredParameters")
    for ask in asks:
        if not str(ask.get("ask_prompt", "")).strip():
            accounting_errors.append("EmptyClarificationPrompt")
        for source_id in ask.get("source_ids", []) or []:
            if source_id not in source_ids:
                accounting_errors.append(f"ClarificationSourceNotReturned:{source_id}")
    return {
        "exact_provenance": not provenance_errors,
        "complete_parameter_accounting": not accounting_errors,
        "provenance_errors": provenance_errors,
        "accounting_errors": accounting_errors,
    }


def full_retention_certificate(contract: Mapping[str, Any], gold: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]) -> bool:
    """Sufficient source-retention proof; paraphrases can pass through review.

    This shortcut proves the selected source text is expressed without
    alteration. It does not certify label independence, relevance/minimality,
    or correctness of clarification value domains, which are outside this endpoint.
    """
    spans = list(contract.get("evidence_spans", []) or [])
    if not spans:
        return False
    selected = set()
    for span in spans:
        source_id = str(span.get("source_id", ""))
        record = records.get(source_id)
        if record is None or record.get("kind") not in {"smt", "gdn"}:
            return False
        if normalize_whitespace(str(span.get("span_text", ""))) != normalize_whitespace(str(record.get("text", ""))):
            return False
        selected.add(source_id)
    required = set(_listish(gold.get("gold_control_path", "")))
    if not required.issubset(selected):
        return False
    return normalize_whitespace(str(contract.get("answer_text", ""))) == normalize_whitespace(
        " ".join(str(span.get("span_text", "")) for span in spans)
    )


def validate_review(review: Mapping[str, Any], expected_id: str, contract: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]) -> None:
    if review.get("rule_version") != RULE_VERSION or review.get("review_id") != expected_id:
        raise ValueError("Stale or mismatched semantic review")
    verdicts = review.get("verdicts", {})
    if set(verdicts) != set(SEMANTIC_GATES) or any(x not in VERDICTS for x in verdicts.values()):
        raise ValueError("Incomplete or invalid semantic review")
    if not str(review.get("rationale", "")).strip():
        raise ValueError("Semantic review requires a rationale")
    findings = review.get("findings", [])
    for gate, verdict in verdicts.items():
        if verdict != "pass" and not any(f.get("gate") == gate for f in findings):
            raise ValueError(f"Nonpassing semantic gate lacks a finding: {gate}")
    for finding in findings:
        if finding.get("gate") not in SEMANTIC_GATES or not finding.get("reason"):
            raise ValueError("Invalid semantic finding")
        excerpt = finding.get("answer_excerpt", "")
        if excerpt and excerpt not in str(contract.get("answer_text", "")):
            raise ValueError("Review's answer excerpt is not in the pinned answer")
        refs = finding.get("references", [])
        if not refs:
            raise ValueError("Semantic finding needs canonical source references")
        for ref in refs:
            source_id = ref.get("source_id", "")
            if source_id not in records or not ref.get("excerpt") or ref["excerpt"] not in records[source_id].get("text", ""):
                raise ValueError(f"Review's source excerpt is not canonical: {source_id}")


def evaluate_contract(*, revision: str, query_id: str, contract: Mapping[str, Any], gold: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]], window_ids: Sequence[str], reviews: Mapping[str, Mapping[str, Any]]) -> dict:
    legacy = verify_answer(
        dict(contract), dict(gold), {sid: str(rec.get("text", "")) for sid, rec in records.items()},
        org_profile={}, corpus_version=revision, strict_extras=False,
        strict_verbatim=True, strict_version=False,
    )
    mechanical = mechanical_checks(contract, records, window_ids)
    rid = review_id(revision, query_id, contract)
    certificate = False
    if not legacy.is_pass:
        method = "legacy_failure_short_circuit"
        verdicts = {gate: "not_required" for gate in SEMANTIC_GATES}
        findings = []
    elif full_retention_certificate(contract, gold, records):
        method = "full_retention_certificate"
        certificate = True
        verdicts = {gate: "pass" for gate in SEMANTIC_GATES}
        findings = []
    else:
        if rid not in reviews:
            raise ValueError(f"Missing semantic review for eligible answer: {rid}")
        review = reviews[rid]
        validate_review(review, rid, contract, records)
        method = "source_inspection"
        verdicts = dict(review["verdicts"])
        findings = list(review.get("findings", []))
    semantic_pass = all(verdicts[gate] == "pass" for gate in SEMANTIC_GATES)
    semantic_possible = all(verdicts[gate] in {"pass", "uncertain"} for gate in SEMANTIC_GATES)
    common = legacy.is_pass and mechanical["exact_provenance"] and mechanical["complete_parameter_accounting"]
    answer_pass = common and semantic_pass
    return {
        "query_id": str(query_id), "revision": revision, "rule_version": RULE_VERSION,
        "review_id": rid, "review_method": method, "legacy_pass": legacy.is_pass,
        "legacy_errors": legacy.error_tags, **mechanical, **verdicts,
        "full_retention_certificate": certificate, "semantic_findings": findings,
        "answer_content_pass": answer_pass,
        "possible_answer_content_pass": common and semantic_possible,
    }
