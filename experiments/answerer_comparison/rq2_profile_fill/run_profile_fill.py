#!/usr/bin/env python3
"""Register or execute the frozen-input profile-resolution mechanism study."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from experiments.answerer_comparison.rq2_preserve_replay import run_preserve_replay as frozen
from answerer_comparison.matched_window_runner import file_sha256, load_gold_rows, assert_same_evidence_window
from compliancegpt.generator.verifier.verifier import verify_contract_validity, normalize_odp_id
from compliancegpt.pipeline.profile_resolution import PROFILE_RESOLUTION_PATCH_ID

RESULT_ID = "rq2_profile_fill_v1"
CONDITIONS = ("empty", "complete", "partial", "wrong_revision", "unknown_keys",
              "unversioned", "placeholder_values", "literal_backslashes")
MUTATIONS = ("unsupported_prose", "forged_value_and_record", "binding_removed", "record_revision",
             "profile_hash", "canonical_span", "unknown_source", "record_and_policy_removed",
             "external_profile_replaced", "unknown_binding")
CODE_PATHS = (
    "experiments/answerer_comparison/rq2_profile_fill/run_profile_fill.py",
    "experiments/answerer_comparison/rq2_profile_fill/PROTOCOL.md",
    "experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py",
    "src/answerer_comparison/matched_window_runner.py",
    "src/compliancegpt/pipeline/pipeline.py",
    "src/compliancegpt/pipeline/odp_policy.py",
    "src/compliancegpt/pipeline/profile_resolution.py",
    "src/compliancegpt/pipeline/evidence_window.py",
    "src/compliancegpt/generator/generator.py",
    "src/compliancegpt/generator/verifier/verifier.py",
    "tests/test_profile_resolution.py",
)
CORE_FIELDS = ("answer_text", "evidence_spans", "status", "odp_required_list", "ask_list",
               "primary_citation", "all_citations")
TOKEN_RE = re.compile(r"\{+\s*insert\s*:\s*(?:param\s*,\s*)?([^}]+?)\s*\}+", re.I)
ASSIGN_RE = re.compile(r"\[\s*assignment\s*:\s*[^\]]+\]", re.I)
SENTINEL = "__ASSIGNMENT_REQUIRED__"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def code_hashes(repo):
    return {p: file_sha256(repo/p) for p in CODE_PATHS}


def load_inputs(repo):
    archive = repo/frozen.ARCHIVE_RELATIVE
    frozen._assert_sha256(archive, frozen.ARCHIVE_SHA256)
    loaded, hashes = {}, {frozen.ARCHIVE_RELATIVE: frozen.ARCHIVE_SHA256}
    with zipfile.ZipFile(archive) as bundle:
        for member, expected in frozen.ARCHIVE_MEMBER_SHA256.items():
            if hashlib.sha256(bundle.read(member)).hexdigest() != expected:
                raise AssertionError(f"Frozen archive member changed: {member}")
            hashes["archive:"+member] = expected
        for revision in ("rev4", "rev5"):
            paths = frozen.REPO_INPUTS[revision]
            for kind in ("gold", "ccs"):
                frozen._assert_sha256(repo/paths[kind], paths[kind+"_sha256"])
                hashes[paths[kind]] = paths[kind+"_sha256"]
            hashes[paths["odp_registry"]] = file_sha256(repo/paths["odp_registry"])
            preserve_reference = (
                "experiments/answerer_comparison/rq2_preserve_replay/results_v1/contracts/"
                f"{revision}_contracts.jsonl"
            )
            hashes[preserve_reference] = file_sha256(repo/preserve_reference)
            contexts = frozen._read_jsonl_bytes(bundle.read(f"contexts/{revision}_prepared_contexts.jsonl"))
            contracts = {r["query_id"]: frozen._read_contract(r) for r in
                         frozen._read_csv_bytes(bundle.read(f"contracts/{revision}_compliancegpt.csv"))}
            gold = load_gold_rows(repo/paths["gold"], expected_rows=100 if revision == "rev5" else 36)
            if {r["query_id"] for r in contexts} != set(gold) or set(contracts) != set(gold):
                raise AssertionError("Frozen query identities changed")
            entries = []
            for context in contexts:
                qid = context["query_id"]
                old = contracts[qid]
                selector = old["debug"]["selector_raw"]
                window = context["evidence_window_manifest"]
                if context["question"] != gold[qid]["question"]:
                    raise AssertionError("Frozen question mismatch")
                selector_ids = [s["source_id"] for s in selector["evidence_spans"]]
                if not selector_ids or not set(selector_ids).issubset(window["source_ids"]):
                    raise AssertionError("Frozen selector outside its window")
                entries.append({"query_id": qid, "question": context["question"], "selector_raw": selector,
                                "evidence_window_source_ids": window["source_ids"]})
            loaded[revision] = {"gold": gold, "contexts": contexts, "contracts": contracts,
                                "selector_entries": entries, "ccs_path": repo/paths["ccs"],
                                "odp_registry_path": repo/paths["odp_registry"]}
    return loaded, hashes


def registered_cases(inputs):
    cases = []
    data = inputs["rev5"]
    for context in data["contexts"]:
        qid = context["query_id"]
        old = data["contracts"][qid]
        original = "\n\n".join(s["span_text"] for s in old["evidence_spans"]).strip()
        if original != old["answer_text"]:
            raise AssertionError("Frozen ASK answer is not canonical span assembly")
        keys = sorted({m.group(1).strip() for m in TOKEN_RE.finditer(original)})
        complete = {k: "synthetic::rev5::"+k for k in keys}
        for condition in CONDITIONS:
            values = dict(complete)
            profile = {"framework_version": "rev5", "odp_values": values}
            if condition == "empty": values.clear()
            elif condition == "partial" and keys: del values[keys[-1]]
            elif condition == "wrong_revision": profile["framework_version"] = "rev4"
            elif condition == "unknown_keys":
                values.clear()
                values["__unknown_parameter_not_in_evidence__"] = "synthetic::unused"
            elif condition == "unversioned": del profile["framework_version"]
            elif condition == "placeholder_values":
                values.update({k: "{{ insert: param, unapproved_new_parameter }}" for k in keys})
            elif condition == "literal_backslashes":
                values.update({k: "C:\\Synthetic\\1\\"+k for k in keys})
            cases.append({"query_id": qid, "condition": condition,
                          "author_odp_positive": bool(data["gold"][qid]["odp_required"].strip()),
                          "org_profile": profile, "frozen_visible_keys": keys,
                          "context_sha256": context["context_sha256"],
                          "evidence_window_sha256": context["evidence_window_manifest"]["sha256"]})
    return cases


def condition_oracle(case, old):
    """Predict from frozen evidence and fixed conditions, never production fields."""
    original = "\n\n".join(s["span_text"] for s in old["evidence_spans"]).strip()
    may_fill = case["condition"] in {"complete", "partial", "literal_backslashes"}
    values = case["org_profile"]["odp_values"] if may_fill else {}
    answer = original
    used = {}
    for match in list(TOKEN_RE.finditer(original)):
        key = match.group(1).strip()
        if key in values:
            answer = answer.replace(match.group(0), values[key])
            used[key] = values[key]
    required = set(case["frozen_visible_keys"]) - set(used)
    if ASSIGN_RE.search(original): required.add(SENTINEL)
    return {"answer_text": answer, "required": {normalize_odp_id(k) for k in required},
            "status": "PARAMS_REQUIRED" if required else "OK", "bindings": used}


def pipeline(data, revision, policy):
    spec = {"ccs_path": data["ccs_path"], "odp_registry_path": data["odp_registry_path"],
            "selector_entries": data["selector_entries"]}
    pipe = frozen._build_pipeline(revision, spec)
    pipe.resolution_policy = policy
    return pipe


def execute(pipe, context, gold=None):
    return pipe.answer(context["question"], prepared_context=copy.deepcopy(context), top_k=12,
                       rewrites=list(context.get("rewrites", [])), gold_row=gold,
                       use_generator=True, run_verify=gold is not None)["contract"]


def verify_profile(contract, pipe, profile):
    return verify_contract_validity(contract, corpus=pipe._get_verifier_corpus(), org_profile=profile,
                                   corpus_version="rev5", expected_resolution_policy="FILL_FROM_PROFILE")


def mutate(contract, profile, operator):
    c, p = copy.deepcopy(contract), copy.deepcopy(profile)
    if operator == "unsupported_prose": c["answer_text"] += " Unsupported statement."
    elif operator == "forged_value_and_record":
        binding = c["profile_resolution"]["bindings"][0]
        c["answer_text"] = c["answer_text"].replace(binding["value"], "unapproved::value")
        binding["value"] = "unapproved::value"
    elif operator == "binding_removed": c["profile_resolution"]["bindings"].pop(0)
    elif operator == "record_revision": c["profile_resolution"]["corpus_version"] = "rev4"
    elif operator == "profile_hash": c["profile_resolution"]["profile_sha256"] = "0" * 64
    elif operator == "canonical_span": c["evidence_spans"][0]["span_text"] += " Unsupported span."
    elif operator == "unknown_source": c["evidence_spans"][0]["source_id"] = "not_in_corpus_smt"
    elif operator == "record_and_policy_removed":
        del c["profile_resolution"]
        del c["resolution_policy"]
    elif operator == "external_profile_replaced": p = {"framework_version": "rev5", "odp_values": {}}
    elif operator == "unknown_binding":
        c["profile_resolution"]["bindings"].append({"param_id": "unknown", "value": "forged",
                                                       "source_ids": [], "profile_path": ["unknown"]})
    else: raise ValueError(operator)
    return c, p


def register(repo, folder):
    inputs, hashes = load_inputs(repo)
    cases = registered_cases(inputs)
    if len(cases) != 800 or sum(c["author_odp_positive"] for c in cases) != 504:
        raise AssertionError("Registered case counts must be 800, including 504 ODP-positive cases")
    targets = [folder/"protocol.json", folder/"registered_cases.jsonl"]
    if any(p.exists() for p in targets): raise FileExistsError("Registration already exists")
    write_jsonl(targets[1], cases)
    protocol = {"result_id": RESULT_ID, "schema_version": "rq2-profile-fill-study-v1",
                "registered_at_utc": datetime.now(timezone.utc).isoformat(),
                "preparation_parent_commit": git(repo, "rev-parse", "HEAD"),
                "conditions": list(CONDITIONS), "mutation_operators": list(MUTATIONS),
                "rev5_questions": 100, "author_odp_positive_questions": 63,
                "author_negative_questions": 37, "expected_cases": 800,
                "new_inference": False, "new_retrieval": False,
                "profile_patch_id": PROFILE_RESOLUTION_PATCH_ID,
                "input_sha256": hashes, "code_sha256": code_hashes(repo),
                "registered_cases_sha256": file_sha256(targets[1]),
                "acceptance": ["all_case_oracles", "all_runtime_contracts", "all_frozen_inputs_unchanged",
                               "all_136_ask_regressions", "all_8_preserve_regressions", "all_mutations_detected"]}
    dump(targets[0], protocol)
    print(json.dumps({"registered_cases": len(cases), "protocol_sha256": file_sha256(targets[0])}))


def run(repo, folder, output):
    if git(repo, "status", "--porcelain"):
        raise RuntimeError("Formal execution requires a clean committed registration")
    protocol = json.loads((folder/"protocol.json").read_text())
    if code_hashes(repo) != protocol["code_sha256"]:
        raise AssertionError("Registered implementation changed")
    if file_sha256(folder/"registered_cases.jsonl") != protocol["registered_cases_sha256"]:
        raise AssertionError("Registered cases changed")
    inputs, hashes = load_inputs(repo)
    if hashes != protocol["input_sha256"]: raise AssertionError("Registered inputs changed")
    cases = [json.loads(line) for line in (folder/"registered_cases.jsonl").read_text().splitlines()]
    if cases != registered_cases(inputs): raise AssertionError("Case matrix does not match protocol")
    frozen._ensure_new_output_dir(output)
    config = {"result_id": RESULT_ID, "execution_repo_commit": git(repo, "rev-parse", "HEAD"),
              "executed_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "protocol_sha256": file_sha256(folder/"protocol.json"),
              "registered_cases_sha256": protocol["registered_cases_sha256"],
              "input_sha256": hashes, "code_sha256": protocol["code_sha256"],
              "profile_patch_id": PROFILE_RESOLUTION_PATCH_ID, "new_inference": False, "new_retrieval": False,
              "frozen_model_id": frozen.MODEL_ID, "frozen_model_revision": frozen.MODEL_REVISION,
              "frozen_runtime_commit": frozen.FROZEN_RUNTIME_COMMIT,
              "scoring": "registered condition oracle; not historical ASK strict-pass accuracy"}
    dump(output/"run_config.json", config)
    data = inputs["rev5"]
    pipe = pipeline(data, "rev5", "FILL_FROM_PROFILE")
    context_by_id = {c["query_id"]: c for c in data["contexts"]}
    audits, mutation_audits = [], []
    with (output/"contracts.jsonl").open("w", encoding="utf-8") as contract_file:
        with (output/"mutation_attempts.jsonl").open("w", encoding="utf-8") as mutation_file:
            for case in cases:
                qid = case["query_id"]
                context, old = context_by_id[qid], data["contracts"][qid]
                pipe.org_profile = copy.deepcopy(case["org_profile"])
                c = execute(pipe, context)
                oracle = condition_oracle(case, old)
                direct, errors = verify_profile(c, pipe, case["org_profile"])
                actual_bindings = {b["param_id"]: b["value"] for b in c["profile_resolution"]["bindings"]}
                window = c["debug"]["evidence_window"]
                assert_same_evidence_window(window, context["evidence_window_manifest"])
                checks = {
                    "answer_matches_oracle": c["answer_text"] == oracle["answer_text"],
                    "status_matches_oracle": c["status"] == oracle["status"],
                    "required_keys_match_oracle": {normalize_odp_id(k) for k in c["odp_required_list"]} == oracle["required"],
                    "bindings_match_oracle": actual_bindings == oracle["bindings"],
                    "canonical_spans_unchanged": c["evidence_spans"] == old["evidence_spans"],
                    "selector_unchanged": digest(c["debug"]["selector_raw"]) == digest(old["debug"]["selector_raw"]),
                    "window_unchanged": window["sha256"] == case["evidence_window_sha256"],
                    "context_unchanged": c["debug"]["prepared_context_sha256"] == case["context_sha256"],
                    "all_source_ids_in_frozen_window": all(s["source_id"] in window["source_ids"] for s in c["evidence_spans"]),
                    "runtime_valid": direct and c["validity_check"] == {"is_pass": True, "errors": []},
                }
                audit = {"query_id": qid, "condition": case["condition"],
                         "author_odp_positive": case["author_odp_positive"], "status": c["status"],
                         "binding_count": len(actual_bindings), "remaining_key_count": len(c["odp_required_list"]),
                         "anonymous_assignment_required": c["profile_resolution"]["anonymous_assignment_required"],
                         "runtime_errors": errors, "checks": checks, "accepted": all(checks.values()),
                         "contract_sha256": digest(c), "org_profile_sha256": c["profile_resolution"]["profile_sha256"]}
                audits.append(audit)
                contract_file.write(json.dumps({"query_id": qid, "condition": case["condition"], "contract": c},
                                               ensure_ascii=False, sort_keys=True)+"\n")
                if case["condition"] == "complete" and case["author_odp_positive"]:
                    if not actual_bindings: raise AssertionError("ODP-positive mutation control has no bindings")
                    for operator in MUTATIONS:
                        changed, external_profile = mutate(c, case["org_profile"], operator)
                        passed, tags = verify_profile(changed, pipe, external_profile)
                        mutation_audits.append({"query_id": qid, "operator": operator,
                                                "detected": not passed, "error_tags": tags})
                        mutation_file.write(json.dumps({"query_id": qid, "operator": operator,
                                                        "contract": changed, "external_profile": external_profile,
                                                        "detected": not passed, "error_tags": tags},
                                                       ensure_ascii=False, sort_keys=True)+"\n")
    write_jsonl(output/"per_case_audit.jsonl", audits)
    write_jsonl(output/"mutation_audit.jsonl", mutation_audits)
    regressions = []
    for revision in ("rev4", "rev5"):
        d = inputs[revision]
        legacy = pipeline(d, revision, "ASK")
        for context in d["contexts"]:
            qid = context["query_id"]
            c = execute(legacy, context, d["gold"][qid])
            old = d["contracts"][qid]
            different = [f for f in CORE_FIELDS if c.get(f) != old.get(f)]
            # The archive stores offline results flattened into the wrapped contract.
            same_offline = c.get("verifier_pass") == old.get("verifier_pass") and \
                c.get("verifier_errors") == old.get("verifier_errors")
            regressions.append({"revision": revision, "query_id": qid, "policy": "ASK",
                                "changed_core_fields": different, "offline_outcome_unchanged": same_offline,
                                "accepted": not different and same_offline})
        previous = repo/"experiments/answerer_comparison/rq2_preserve_replay/results_v1/contracts"/f"{revision}_contracts.jsonl"
        preserved = [json.loads(line) for line in previous.read_text().splitlines()]
        selected = [ctx for ctx in d["contexts"] if ctx["query_id"] in frozen.EXPECTED_QUERY_IDS[revision]]
        if len(preserved) != len(selected): raise AssertionError("PRESERVE reference count changed")
        legacy.resolution_policy = "PRESERVE"
        for context, old in zip(selected, preserved):
            qid = context["query_id"]
            c = execute(legacy, context, d["gold"][qid])
            different = [f for f in CORE_FIELDS if c.get(f) != old.get(f)]
            regressions.append({"revision": revision, "query_id": qid, "policy": "PRESERVE",
                                "changed_core_fields": different,
                                "accepted": not different and c["validity_check"]["is_pass"]})
    write_jsonl(output/"legacy_regressions.jsonl", regressions)
    by_condition = {}
    for condition in CONDITIONS:
        rows = [r for r in audits if r["condition"] == condition]
        by_condition[condition] = {"cases": len(rows), "accepted": sum(r["accepted"] for r in rows),
            "runtime_valid": sum(r["checks"]["runtime_valid"] for r in rows),
            "status_counts": dict(Counter(r["status"] for r in rows)),
            "binding_occurrences": sum(r["binding_count"] for r in rows),
            "by_author_stratum": {label: {"cases": len(sub := [r for r in rows if r["author_odp_positive"] == positive]),
                                          "accepted": sum(r["accepted"] for r in sub),
                                          "status_counts": dict(Counter(r["status"] for r in sub))}
                                  for label, positive in (("odp_positive", True), ("author_negative", False))}}
    mutation_counts = {op: {"attempts": len(sub := [r for r in mutation_audits if r["operator"] == op]),
                            "detected": sum(r["detected"] for r in sub)} for op in MUTATIONS}
    acceptance = {"all_case_oracles": all(r["accepted"] for r in audits) and len(audits) == 800,
                  "all_runtime_contracts": all(r["checks"]["runtime_valid"] for r in audits),
                  "all_frozen_inputs_unchanged": all(all(v for k,v in r["checks"].items() if "unchanged" in k)
                                                     for r in audits),
                  "all_136_ask_regressions": len(sub := [r for r in regressions if r["policy"] == "ASK"]) == 136
                                                and all(r["accepted"] for r in sub),
                  "all_8_preserve_regressions": len(sub := [r for r in regressions if r["policy"] == "PRESERVE"]) == 8
                                                and all(r["accepted"] for r in sub),
                  "all_mutations_detected": len(mutation_audits) == 630 and all(r["detected"] for r in mutation_audits)}
    summary = {"result_id": RESULT_ID, "cases": len(audits), "accepted_cases": sum(r["accepted"] for r in audits),
               "by_condition": by_condition, "mutations": mutation_counts,
               "legacy_regressions": {"ASK": 136, "PRESERVE": 8, "accepted": sum(r["accepted"] for r in regressions)},
               "acceptance_checks": acceptance, "accepted": all(acceptance.values())}
    dump(output/"summary.json", summary)
    lines = ["# Profile-resolution study", "", f"Result identity: `{RESULT_ID}`.", "",
             f"Formal execution commit: `{config['execution_repo_commit']}`.",
             f"Registered protocol SHA-256: `{config['protocol_sha256']}`.", "",
             f"Accepted condition cases: **{summary['accepted_cases']}/800**.", "",
             "| Condition | Runtime-valid | Oracle agreement | OK | PARAMS_REQUIRED |",
             "|---|---:|---:|---:|---:|"]
    for condition, counts in by_condition.items():
        lines.append(f"| {condition} | {counts['runtime_valid']}/100 | {counts['accepted']}/100 | "
                     f"{counts['status_counts'].get('OK',0)} | {counts['status_counts'].get('PARAMS_REQUIRED',0)} |")
    lines += ["", f"Detected mutations: **{sum(r['detected'] for r in mutation_audits)}/630**, "
              "with 63 positive-control contracts and ten operators.",
              f"Unchanged ASK/PRESERVE regressions: **{sum(r['accepted'] for r in regressions)}/144**.",
              f"Registered acceptance: **{'PASS' if summary['accepted'] else 'FAIL'}**.", "",
              "## Interpretation", "",
              "Canonical evidence, prepared windows and frozen selector outputs are retained. "
              "The full pipeline now emits profile-bound resolution provenance, and runtime verification "
              "checks literal construction against the caller-supplied profile and corpus revision.", "",
              "These are deterministic mechanism outcomes on synthetic profiles, not new historical "
              "ASK strict-pass accuracy estimates. They do not validate gold labels, establish evidence "
              "completeness, or validate organizational approval, parameter-domain/cardinality rules, "
              "or behavior under new model/retrieval outputs. Anonymous assignments remain blocked.", "",
              "See PROTOCOL.md, protocol.json and registered_cases.jsonl in the parent directory for "
              "the published design and all profile inputs. Per-case contracts, attempted mutations "
              "and legacy comparisons are retained here."]
    (output/"SUMMARY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    frozen._write_sha256sums(output)
    archive = frozen._write_deterministic_zip(output)
    # The generic archive helper names a PRESERVE archive; use this study's identity.
    correct_archive = output/(RESULT_ID+".zip")
    archive.rename(correct_archive)
    (output/"ARCHIVE_SHA256SUMS").write_text(file_sha256(correct_archive)+"  "+correct_archive.name+"\n")
    print(json.dumps(summary, indent=2))
    if not summary["accepted"]: raise AssertionError("Formal study failed registered acceptance; outcomes retained")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="Register inputs without executing the study")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    folder = Path(__file__).resolve().parent
    if args.prepare: register(repo, folder)
    else: run(repo, folder, args.output_dir.resolve() if args.output_dir else folder/"results_v1")


if __name__ == "__main__":
    main()
