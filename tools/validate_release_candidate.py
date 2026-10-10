#!/usr/bin/env python3
"""Check revised runtime integration against immutable profile-study fixtures.

This diagnostic has its own identity. It does not execute or amend a historical
registration, perform new inference, or measure strict-pass accuracy.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from experiments.answerer_comparison.rq2_profile_fill_v2 import run_profile_fill as study
from compliancegpt.generator.verifier.verifier import normalize_odp_id

VALIDATION_ID = "release_candidate_profile_integration_v2"
FOLDER = ROOT / "experiments/answerer_comparison/rq2_profile_fill_v2"


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main(output):
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Write release diagnostics outside the repository's frozen result tree")
    study.frozen._ensure_new_output_dir(output)
    inputs, input_hashes = study.load_inputs(ROOT)
    protocol = json.loads((FOLDER / "protocol.json").read_text(encoding="utf-8"))
    if input_hashes != protocol["input_sha256"]:
        raise AssertionError("Historical input identities changed")
    if study.file_sha256(FOLDER / "registered_cases.jsonl") != protocol["registered_cases_sha256"]:
        raise AssertionError("Historical case matrix changed")
    cases = read_rows(FOLDER / "registered_cases.jsonl")
    if len(cases) != 800 or cases != study.registered_cases(inputs):
        raise AssertionError("Historical case matrix does not match frozen inputs")

    data = inputs["rev5"]
    pipe = study.pipeline(data, "rev5", "FILL_FROM_PROFILE")
    contexts = {row["query_id"]: row for row in data["contexts"]}
    audits, mutations = [], []
    historical_cases = {(r["query_id"], r["condition"]): r for r in
                        read_rows(FOLDER / "results_v2/per_case_audit.jsonl")}
    for case in cases:
        qid = case["query_id"]
        context, old = contexts[qid], data["contracts"][qid]
        pipe.org_profile = copy.deepcopy(case["org_profile"])
        contract = study.execute(pipe, context)
        oracle = study.condition_oracle(case, old)
        valid, errors = study.verify_profile(contract, pipe, case["org_profile"])
        bindings = {b["param_id"]: b["value"] for b in contract["profile_resolution"]["bindings"]}
        window = contract["debug"]["evidence_window"]
        study.assert_same_evidence_window(window, context["evidence_window_manifest"])
        checks = {
            "answer_matches_oracle": contract["answer_text"] == oracle["answer_text"],
            "status_matches_oracle": contract["status"] == oracle["status"],
            "required_keys_match_oracle": {normalize_odp_id(k) for k in contract["odp_required_list"]} == oracle["required"],
            "bindings_match_oracle": bindings == oracle["bindings"],
            "canonical_spans_unchanged": contract["evidence_spans"] == old["evidence_spans"],
            "selector_unchanged": study.digest(contract["debug"]["selector_raw"]) == study.digest(old["debug"]["selector_raw"]),
            "fallback_unchanged": study.fallback_trace_matches(contract, old),
            "window_unchanged": window["sha256"] == case["evidence_window_sha256"],
            "context_unchanged": contract["debug"]["prepared_context_sha256"] == case["context_sha256"],
            "all_source_ids_in_frozen_window": all(s["source_id"] in window["source_ids"] for s in contract["evidence_spans"]),
            "runtime_valid": valid and contract["validity_check"] == {"is_pass": True, "errors": []},
        }
        audit = {
            "query_id": qid, "condition": case["condition"],
            "author_odp_positive": case["author_odp_positive"], "status": contract["status"],
            "binding_count": len(bindings), "remaining_key_count": len(contract["odp_required_list"]),
            "anonymous_assignment_required": contract["profile_resolution"]["anonymous_assignment_required"],
            "fallback_state_reconstructed": qid in study.RECORDED_FALLBACK_IDS["rev5"],
            "runtime_errors": errors, "checks": checks, "accepted": all(checks.values()),
            "contract_sha256": study.digest(contract),
            "org_profile_sha256": contract["profile_resolution"]["profile_sha256"],
        }
        historical = historical_cases[(qid, case["condition"])]
        # New registry provenance changes the wrapper hash, not these outcomes.
        audit["historical_outcomes_match"] = all(
            audit[key] == value for key, value in historical.items() if key != "contract_sha256"
        )
        audit["registry_identity_matches"] = contract["odp_registry"] == pipe.odp_registry_metadata
        audit["registry_metadata"] = contract["odp_registry"]
        audits.append(audit)
        if case["condition"] == "complete" and case["author_odp_positive"]:
            if not bindings:
                raise AssertionError("Mutation positive control has no resolved binding")
            for operator in study.MUTATIONS:
                changed, profile = study.mutate(contract, case["org_profile"], operator)
                passed, tags = study.verify_profile(changed, pipe, profile)
                mutations.append({"query_id": qid, "operator": operator,
                                  "detected": not passed, "error_tags": tags})

    regressions = []
    for revision, data in inputs.items():
        legacy = study.pipeline(data, revision, "ASK")
        for context in data["contexts"]:
            qid = context["query_id"]
            contract = study.execute(legacy, context, data["gold"][qid])
            old = data["contracts"][qid]
            changed = [f for f in study.CORE_FIELDS if contract.get(f) != old.get(f)]
            same_offline = (contract.get("verifier_pass") == old.get("verifier_pass") and
                            contract.get("verifier_errors") == old.get("verifier_errors"))
            same_trace = (study.digest(contract["debug"]["selector_raw"]) == study.digest(old["debug"]["selector_raw"])
                          and study.fallback_trace_matches(contract, old))
            regressions.append({"revision": revision, "query_id": qid, "policy": "ASK",
                                "changed_core_fields": changed, "offline_outcome_unchanged": same_offline,
                                "selection_trace_unchanged": same_trace,
                                "accepted": not changed and same_offline and same_trace})
        previous = read_rows(ROOT /
                   f"experiments/answerer_comparison/rq2_preserve_replay/results_v1/contracts/{revision}_contracts.jsonl")
        expected = set(study.frozen.EXPECTED_QUERY_IDS[revision])
        selected = [context for context in data["contexts"] if context["query_id"] in expected]
        if len(previous) != len(selected) or len(selected) != len(expected):
            raise AssertionError("PRESERVE reference identities changed")
        preserved = {context["query_id"]: old for context, old in zip(selected, previous)}
        legacy.resolution_policy = "PRESERVE"
        for context in data["contexts"]:
            qid = context["query_id"]
            if qid not in expected:
                continue
            contract = study.execute(legacy, context, data["gold"][qid])
            changed = [f for f in study.CORE_FIELDS if contract.get(f) != preserved[qid].get(f)]
            regressions.append({"revision": revision, "query_id": qid, "policy": "PRESERVE",
                                "changed_core_fields": changed,
                                "accepted": not changed and contract["validity_check"]["is_pass"]})

    historical_mutations = read_rows(FOLDER / "results_v2/mutation_audit.jsonl")
    historical_regressions = read_rows(FOLDER / "results_v2/legacy_regressions.jsonl")
    acceptance = {
        "all_800_cases": len(audits) == 800 and all(r["accepted"] for r in audits),
        "all_case_outcomes_match_history": all(r["historical_outcomes_match"] for r in audits),
        "all_registry_identities": all(r["registry_identity_matches"] for r in audits),
        "all_630_mutations_detected": len(mutations) == 630 and all(r["detected"] for r in mutations),
        "mutation_outcomes_match_history": mutations == historical_mutations,
        "all_136_ask_regressions": len(sub := [r for r in regressions if r["policy"] == "ASK"]) == 136
                                   and all(r["accepted"] for r in sub),
        "all_8_preserve_regressions": len(sub := [r for r in regressions if r["policy"] == "PRESERVE"]) == 8
                                      and all(r["accepted"] for r in sub),
        "legacy_outcomes_match_history": regressions == historical_regressions,
    }
    summary = {
        "validation_id": VALIDATION_ID, "validation_kind": "retrospective integration diagnostic",
        "historical_fixture_identity": study.RESULT_ID,
        "cases": len(audits), "accepted_cases": sum(r["accepted"] for r in audits),
        "mutations": len(mutations), "detected_mutations": sum(r["detected"] for r in mutations),
        "legacy_regressions": dict(Counter(r["policy"] for r in regressions)),
        "acceptance_checks": acceptance, "accepted": all(acceptance.values()),
        "boundary": "Synthetic profiles and stored normalized selector traces; two recorded fallback states reconstructed. No new inference, retrieval, organization approval, domain validation, or strict-pass estimate.",
    }
    code_hashes = study.code_hashes(ROOT)
    extra_paths = ("src/compliancegpt/pipeline/odp_registry.py", "tools/validate_release_candidate.py",
                   "src/compliancegpt/generator/verifier/verifier_revision_v2.py")
    code_hashes.update({p: study.file_sha256(ROOT / p) for p in extra_paths})
    config = {
        "validation_id": VALIDATION_ID,
        "checkout_head_at_validation": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "checkout_dirty_at_validation": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "input_sha256": input_hashes, "code_sha256": code_hashes,
        "historical_protocol_sha256": study.file_sha256(FOLDER / "protocol.json"),
        "historical_code_hashes_match": study.code_hashes(ROOT) == protocol["code_sha256"],
        "historical_registration_modified": False, "new_inference": False, "new_retrieval": False,
        "registry_selection": "original registries passed by explicit custom path",
    }
    study.write_jsonl(output / "per_case_audit.jsonl", audits)
    study.write_jsonl(output / "mutation_audit.jsonl", mutations)
    study.write_jsonl(output / "legacy_regressions.jsonl", regressions)
    study.dump(output / "validation_config.json", config)
    study.dump(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    if not summary["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    main(parser.parse_args().output_dir)
