"""Strict-pass-v2: preserve v1 gates and add active revision agreement.

Semantic judgments remain inherited v1 judgments on the same answer surface.
The v2 assessment identity also includes the contract's revision declaration.
"""
from __future__ import annotations

from typing import Any, Mapping

from answerer_comparison import strict_pass as v1
from compliancegpt.generator.verifier.verifier_revision_v2 import reference_revision_errors

RULE_VERSION = "strict-pass-v2"
SEMANTIC_GATES = v1.SEMANTIC_GATES
STRICT_PASS_DEFINITION = v1.STRICT_PASS_DEFINITION + (
    " The contract must declare exactly one supported revision that matches the "
    "active corpus and reference row. Explicit source and citation revision labels "
    "must also agree with that corpus."
)
ASSESSMENT_BOUNDARY = v1.ASSESSMENT_BOUNDARY + (
    " V2 adds only a mechanical revision gate. It inherits v1 semantic judgments "
    "and complete-retention proofs; it adds no independent semantic adjudication."
)


def answer_surface(revision: str, query_id: str, contract: Mapping[str, Any]) -> dict:
    return {**v1.answer_surface(revision, query_id, contract),
            "rule_version": RULE_VERSION,
            "framework_version_present": "framework_version" in contract,
            "framework_version": contract.get("framework_version"),
            "primary_citation": contract.get("primary_citation"),
            "all_citations": contract.get("all_citations"),
            "answer_text_with_citation": contract.get("answer_text_with_citation"),
            "answer_text_with_citations": contract.get("answer_text_with_citations")}


def review_id(revision: str, query_id: str, contract: Mapping[str, Any]) -> str:
    """Identify the v2 assessment; inherited reviews keep their own v1 IDs."""
    return v1.canonical_sha256(answer_surface(revision, query_id, contract))


def upgrade_assessment(*, revision: str, query_id: str, contract: Mapping[str, Any],
                       gold: Mapping[str, Any], legacy: Mapping[str, Any]) -> dict:
    """Add the revision gate while retaining every existing semantic verdict."""
    if legacy.get("rule_version") != v1.RULE_VERSION:
        raise ValueError("V2 requires an explicitly identified v1 assessment")
    if legacy.get("review_id") != v1.review_id(revision, query_id, contract):
        raise ValueError("The inherited assessment has a different answer surface")
    errors = reference_revision_errors(contract, gold, revision)
    passed = not errors
    combined_errors = list(legacy["contract_errors"]) + [e for e in errors if e not in legacy["contract_errors"]]
    method = legacy["review_method"]
    provenance = {"source_inspection": "inherited_v1_source_inspection",
                  "full_retention_certificate": "unchanged_v1_complete_retention_proof",
                  "contract_failure_short_circuit": "v1_contract_failure_short_circuit"}[method]
    return {
        **legacy, "rule_version": RULE_VERSION,
        "review_id": review_id(revision, query_id, contract),
        "legacy_review_id": legacy["review_id"],
        "semantic_review_id": legacy["review_id"] if method == "source_inspection" else None,
        "semantic_review_rule_version": v1.RULE_VERSION if method == "source_inspection" else None,
        "semantic_provenance": provenance, "new_semantic_review": False,
        "declared_revision_pass": passed, "declared_revision_errors": errors,
        "legacy_contract_checks_pass": legacy["contract_checks_pass"],
        "legacy_strict_pass": legacy["strict_pass"],
        "contract_checks_pass": legacy["contract_checks_pass"] and passed,
        "contract_errors": combined_errors,
        "strict_pass": legacy["strict_pass"] and passed,
    }


def evaluate_contract(*, revision, query_id, contract, gold, records, window_ids, reviews):
    legacy = v1.evaluate_contract(revision=revision, query_id=query_id, contract=contract,
                                  gold=gold, records=records, window_ids=window_ids, reviews=reviews)
    return upgrade_assessment(revision=revision, query_id=query_id, contract=contract,
                              gold=gold, legacy=legacy)
