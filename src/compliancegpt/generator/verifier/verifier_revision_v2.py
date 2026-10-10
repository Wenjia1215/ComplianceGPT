"""Require contract revision declarations to agree with the active corpus.

The legacy verifier remains available for exact historical scoring. These entry
points add revision checks to its existing runtime and reference checks.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from compliancegpt.generator.verifier import verifier as legacy

REVISION_RULE_VERSION = "active-revision-v2"
VERIFIER_PATCH_ID = "2026-10-09-active-revision-v2"
_DECLARATION = re.compile(r"(?:rev(?:ision)?\s*\.?\s*|r\s*)?([45])", re.I)
_LABEL = re.compile(r"\b(?:rev(?:ision)?|r)\s*\.?\s*(\d+)\b", re.I)
_PACKED_NIST_LABEL = re.compile(r"800[\s._-]*53\s*r\s*(\d+)\b", re.I)


def declared_revision(value: Any) -> str | None:
    """Accept one whole revision declaration, never a substring or mixed value."""
    if not isinstance(value, str):
        return None
    match = _DECLARATION.fullmatch(value.strip())
    return "rev" + match.group(1) if match else None


def revision_errors(contract: Mapping[str, Any], corpus_version: Any) -> list[str]:
    """Check required metadata and explicit labels without interpreting prose."""
    active = declared_revision(corpus_version)
    errors = []
    if active is None:
        errors.append("ActiveCorpusRevisionMissingOrInvalid")
    if not isinstance(contract, Mapping):
        return sorted(set(errors + ["ContractNotDict"]))
    if "framework_version" not in contract:
        errors.append("FrameworkVersionMissing")
    else:
        declared = declared_revision(contract["framework_version"])
        if declared is None:
            errors.append("FrameworkVersionInvalid")
        elif active is not None and declared != active:
            errors.append(f"FrameworkVersionMismatch:expected={active},got={declared}")

    def check_label(value, location):
        if not isinstance(value, str):
            return
        labels = {"rev" + m.group(1) for m in _LABEL.finditer(value.replace("_", " "))}
        labels.update("rev" + m.group(1) for m in _PACKED_NIST_LABEL.finditer(value))
        if any(v not in {"rev4", "rev5"} for v in labels):
            errors.append(f"UnsupportedRevisionLabel:{location}")
        if active is not None and labels - {active}:
            errors.append(f"RevisionLabelMismatch:{location}:expected={active},got={','.join(sorted(labels))}")

    spans = contract.get("evidence_spans", [])
    if isinstance(spans, list):
        for index, span in enumerate(spans):
            if isinstance(span, Mapping):
                check_label(span.get("source_id"), f"evidence_spans[{index}].source_id")
    for field in ("primary_citation", "all_citations"):
        check_label(contract.get(field), field)
    for field in ("answer_text_with_citation", "answer_text_with_citations"):
        value = contract.get(field)
        if isinstance(value, str):
            parts = re.split(r"\bCitations?\s*:\s*", value, flags=re.I)
            if len(parts) > 1:
                check_label(parts[-1], field)
    return sorted(set(errors))


def verify_contract_validity(json_output, corpus=None, org_profile=None, strict_verbatim=True,
                             *, corpus_version=None, expected_resolution_policy=None):
    """Validate without gold; the caller must identify the active revision."""
    passed, errors = legacy.verify_contract_validity(
        json_output, corpus, org_profile, strict_verbatim,
        corpus_version=corpus_version, expected_resolution_policy=expected_resolution_policy,
    )
    added = revision_errors(json_output, corpus_version)
    return passed and not added, sorted(set(errors + added))


def reference_revision_errors(json_output, gold_row, corpus_version):
    errors = revision_errors(json_output, corpus_version)
    active = declared_revision(corpus_version)
    gold = declared_revision(gold_row.get("gold_source_version"))
    if gold is None:
        errors.append("GoldRevisionMissingOrInvalid")
    elif active is not None and gold != active:
        errors.append(f"GoldRevisionMismatch:expected={active},got={gold}")
    return sorted(set(errors))


def verify_answer(json_output, gold_row, corpus=None, *, org_profile=None, corpus_version=None,
                  strict_extras=True, strict_verbatim=True, strict_version=False):
    """Add explicit revision agreement to the unchanged reference checker."""
    result = legacy.verify_answer(
        json_output, gold_row, corpus, org_profile=org_profile, corpus_version=corpus_version,
        strict_extras=strict_extras, strict_verbatim=strict_verbatim, strict_version=strict_version,
    )
    added = reference_revision_errors(json_output, gold_row, corpus_version)
    errors = list(result.error_tags) + [e for e in added if e not in result.error_tags]
    return legacy.VerifierResult(question_id=result.question_id,
                                 is_pass=result.is_pass and not added,
                                 error_tags=errors, metrics=dict(result.metrics))
