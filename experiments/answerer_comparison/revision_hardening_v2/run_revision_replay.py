#!/usr/bin/env python3
"""Rescore frozen contracts and audit revision mutations without new inference."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import platform
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from answerer_comparison import strict_pass as v1
from answerer_comparison import strict_pass_v2 as v2
from compliancegpt.generator.verifier import verifier as legacy_verifier
from compliancegpt.generator.verifier import verifier_revision_v2 as revised_verifier
from experiments.answerer_comparison.run_strict_pass import load_inputs, contract_path, sha256
from experiments.answerer_comparison import run_supplementary_strict_pass as supplementary

RESULT_ID = "strict_pass_revision_replay_v2"
MUTATION_ID = "runtime_revision_mutations_v2"
BASE = "experiments/answerer_comparison"
REPLAY_ARCHIVE = f"{BASE}/retrospective_repairs/ComplianceGPT_Batch_02_No_Selector_Replay.zip"
REPLAY_ARCHIVE_SHA256 = "e1c0c200b72eb33cc7d465c93f20b438d5cb98b465f36d1e55db5a9dae2be4b6"
SYSTEM_NAMES = {"baseline": "generative_baseline_4bit", "compliancegpt": "compliancegpt_4bit",
                "gemini": "generative_frontier_api"}
OPERATORS = ("opposite_declaration", "missing_declaration", "unknown_declaration",
             "ambiguous_declaration", "nonstring_declaration", "opposite_source_namespace",
             "opposite_packed_source_namespace", "opposite_citation_label")
CODE_PATHS = (
    "src/compliancegpt/generator/verifier/verifier.py",
    "src/compliancegpt/generator/verifier/verifier_revision_v2.py",
    "src/answerer_comparison/strict_pass.py", "src/answerer_comparison/strict_pass_v2.py",
    f"{BASE}/run_strict_pass.py", f"{BASE}/run_supplementary_strict_pass.py",
    f"{BASE}/revision_hardening_v2/run_revision_replay.py",
)
ENDPOINT_FIELDS = ("strict_pass", "contract_checks_pass", "contract_errors", "exact_provenance",
                   "complete_parameter_accounting", "provenance_errors", "accounting_errors",
                   "full_retention_certificate", "semantic_findings", "semantic_uncertain",
                   *v1.SEMANTIC_GATES)


def read_jsonl(payload):
    return [json.loads(line) for line in payload.decode("utf-8").splitlines()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_cases():
    inputs, hashes = load_inputs(ROOT)
    cases = []
    for revision, (records, gold, systems) in inputs.items():
        folder = "rq2_frontier_baseline_rev5" if revision == "rev5" else "rq2_frontier_baseline"
        relative = f"{BASE}/{folder}/results_v1/strict_pass_rows.jsonl"
        hashes[relative] = sha256(ROOT / relative)
        saved = {(r["system"], r["query_id"]): r for r in read_jsonl((ROOT / relative).read_bytes())}
        if len(saved) != len(gold) * 3:
            raise ValueError("Original main assessment identities changed")
        for system, rows in systems.items():
            for qid in sorted(rows, key=int):
                row = rows[qid]
                cases.append({"family": "main", "condition": system, "revision": revision,
                              "query_id": qid, "row": row, "gold": gold[qid], "records": records,
                              "window_ids": row["evidence_window_source_ids"].split("|"),
                              "saved_v1": saved[(SYSTEM_NAMES[system], qid)],
                              "source": contract_path(revision, system)})

    blobs = {}
    for name, expected in supplementary.FROZEN_SHA256.items():
        blobs[name] = (ROOT / name).read_bytes()
        hashes[name] = hashlib.sha256(blobs[name]).hexdigest()
        if hashes[name] != expected:
            raise ValueError("Frozen supplementary input changed: " + name)
    part_names = sorted(n for n in blobs if ".zip.part-" in n)
    relative = f"{BASE}/supplementary_strict_pass/results_v1/strict_pass_rows.jsonl"
    hashes[relative] = sha256(ROOT / relative)
    saved = {(r["revision"], r["condition"], r["query_id"]): r
             for r in read_jsonl((ROOT / relative).read_bytes())}
    if len(saved) != 988:
        raise ValueError("Original supplementary assessment identities changed")
    with zipfile.ZipFile(io.BytesIO(b"".join(blobs[n] for n in part_names))) as archive:
        for revision, (records, gold, systems) in inputs.items():
            specs = [("no_selector", f"{BASE}/rq2_no_selector/results_v1/contracts/{revision}_no_selector.csv", None),
                     ("rescue_off", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{revision}_rescue_off.csv", None),
                     ("rescue_on", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{revision}_rescue_on.csv", None)]
            if revision == "rev4":
                specs.append(("baseline_bf16", f"{BASE}/rq2_bf16_baseline/results_v1/contracts/rev4_generative_baseline_bf16.csv", None))
            specs.extend((f"top{width}", f"contracts/top{width}_{revision}_compliancegpt.csv",
                          f"contexts/top{width}_{revision}_prepared_contexts.jsonl") for width in (1, 2, 3, 5))
            for condition, name, context_name in specs:
                payload = archive.read(name) if context_name else blobs[name]
                source = "gate_width_archive:" + name if context_name else name
                hashes[source] = hashlib.sha256(payload).hexdigest()
                rows = supplementary.read_csv(payload)
                if set(rows) != set(gold):
                    raise ValueError("Supplementary question identities changed: " + name)
                if context_name:
                    payload_context = archive.read(context_name)
                    hashes["gate_width_archive:" + context_name] = hashlib.sha256(payload_context).hexdigest()
                    context_rows = read_jsonl(payload_context)
                    contexts = {r["query_id"]: r for r in context_rows}
                    if len(contexts) != len(context_rows) or set(contexts) != set(gold):
                        raise ValueError("Gate-width context identities changed")
                for qid in sorted(rows, key=int):
                    row = rows[qid]
                    if context_name:
                        context = contexts[qid]
                        manifest = context["evidence_window_manifest"]
                        ids = [r["id"] for r in context["evidence_window"]]
                        if (row["context_sha256"] != context["context_sha256"] or
                            row["evidence_window_sha256"] != manifest["sha256"] or
                            row["evidence_window_source_ids"].split("|") != ids or ids != manifest["source_ids"]):
                            raise ValueError("Gate-width output no longer matches its frozen context")
                        for record, pinned in zip(context["evidence_window"], manifest["records"], strict=True):
                            if (record["id"] != pinned["source_id"] or
                                hashlib.sha256(record["text"].encode()).hexdigest() != pinned["text_sha256"] or
                                record["text"] != records[record["id"]]["text"]):
                                raise ValueError("Gate-width window content changed")
                    else:
                        matched = systems["compliancegpt"][qid]
                        ids = matched["evidence_window_source_ids"].split("|")
                        if row["context_sha256"] != matched["context_sha256"]:
                            raise ValueError("Supplementary output no longer matches its matched context")
                        if row.get("evidence_window_sha256", matched["evidence_window_sha256"]) != matched["evidence_window_sha256"]:
                            raise ValueError("Supplementary evidence-window hash changed")
                        if row.get("evidence_window_source_ids", "|".join(ids)).split("|") != ids:
                            raise ValueError("Supplementary evidence-window ordering changed")
                    cases.append({"family": "supplementary", "condition": condition, "revision": revision,
                                  "query_id": qid, "row": row, "gold": gold[qid], "records": records,
                                  "window_ids": ids, "saved_v1": saved[(revision, condition, qid)], "source": source})

    if sha256(ROOT / REPLAY_ARCHIVE) != REPLAY_ARCHIVE_SHA256:
        raise ValueError("Batch 2 request-replay archive changed")
    hashes[REPLAY_ARCHIVE] = REPLAY_ARCHIVE_SHA256
    with zipfile.ZipFile(ROOT / REPLAY_ARCHIVE) as archive:
        manifest_bytes = archive.read("results_v1/manifest.json")
        hashes["batch2_archive:results_v1/manifest.json"] = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes)
        if manifest["result_id"] != "rq2_no_selector_requests_v1" or manifest["rule_version"] != v1.RULE_VERSION:
            raise ValueError("Batch 2 replay has the wrong identity")
        payload = archive.read("results_v1/strict_pass_rows.jsonl")
        if hashlib.sha256(payload).hexdigest() != manifest["output_sha256"]["strict_pass_rows.jsonl"]:
            raise ValueError("Batch 2 assessment bytes changed")
        hashes["batch2_archive:results_v1/strict_pass_rows.jsonl"] = hashlib.sha256(payload).hexdigest()
        saved_rows = [r for r in read_jsonl(payload) if r["condition"] == "no_selector_requests"]
        saved = {(r["revision"], r["query_id"]): r for r in saved_rows}
        if len(saved) != 136 or len(saved_rows) != 136:
            raise ValueError("Batch 2 repaired assessment identities changed")
        for revision, (records, gold, systems) in inputs.items():
            member = f"results_v1/contracts/{revision}_no_selector_requests.csv"
            payload = archive.read(member)
            if hashlib.sha256(payload).hexdigest() != manifest["output_sha256"][member.removeprefix("results_v1/")]:
                raise ValueError("Batch 2 repaired contract bytes changed")
            source = "batch2_archive:" + member
            hashes[source] = hashlib.sha256(payload).hexdigest()
            rows = supplementary.read_csv(payload)
            if set(rows) != set(gold):
                raise ValueError("Batch 2 repaired question identities changed")
            for qid in sorted(rows, key=int):
                row, matched = rows[qid], systems["compliancegpt"][qid]
                if any(row[key] != matched[key] for key in
                       ("context_sha256", "evidence_window_sha256", "evidence_window_source_ids")):
                    raise ValueError("Batch 2 repaired context or evidence window changed")
                cases.append({"family": "repaired_no_selector", "condition": "no_selector_requests",
                              "revision": revision, "query_id": qid, "row": row, "gold": gold[qid],
                              "records": records, "window_ids": row["evidence_window_source_ids"].split("|"),
                              "saved_v1": saved[(revision, qid)], "source": source})
    if Counter(c["family"] for c in cases) != Counter(main=408, supplementary=988, repaired_no_selector=136):
        raise ValueError("Unexpected replay case counts")
    return cases, hashes


def mutate(contract, revision, operator):
    changed = copy.deepcopy(contract)
    wrong = "rev4" if revision == "rev5" else "rev5"
    if operator == "opposite_declaration": changed["framework_version"] = wrong
    elif operator == "missing_declaration": del changed["framework_version"]
    elif operator == "unknown_declaration": changed["framework_version"] = "unknown"
    elif operator == "ambiguous_declaration": changed["framework_version"] = "Revision 4 / Revision 5"
    elif operator == "nonstring_declaration": changed["framework_version"] = int(revision[-1])
    elif operator == "opposite_source_namespace":
        changed["evidence_spans"][0]["source_id"] = f"NIST_SP-800-53_{wrong}:" + changed["evidence_spans"][0]["source_id"]
    elif operator == "opposite_packed_source_namespace":
        changed["evidence_spans"][0]["source_id"] = f"NIST.SP.800-53r{wrong[-1]}.pdf#" + changed["evidence_spans"][0]["source_id"]
    elif operator == "opposite_citation_label":
        changed["all_citations"] = f"Citations: {changed['evidence_spans'][0]['source_id']} (NIST SP 800-53 Rev. {wrong[-1]})"
    else: raise ValueError(operator)
    return changed


def run(output):
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Write the new replay outside the repository's frozen result tree")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError("Refusing to overwrite or mix a completed replay")
    output.mkdir(parents=True, exist_ok=True)
    cases, hashes = load_cases()
    paths = [f"{BASE}/strict_pass_reviews.jsonl", f"{BASE}/strict_pass_supplementary_reviews.jsonl"]
    reviews = {}
    for path in paths:
        loaded = v1.load_reviews(ROOT / path)
        if set(loaded) & set(reviews):
            raise ValueError("Duplicate inherited semantic review identities")
        reviews.update(loaded)
        hashes[path] = sha256(ROOT / path)
    code_hashes = {p: sha256(ROOT / p) for p in CODE_PATHS}
    assessments, deltas, semantic_links, source_index, runtime_deltas, mutations = [], [], [], [], [], []
    groups = defaultdict(list)
    eligibility = Counter()
    corpora = {}
    for case in cases:
        family, condition, revision, qid = (case[k] for k in ("family", "condition", "revision", "query_id"))
        contract = json.loads(case["row"]["contract_json"])
        if contract.get("question") != case["gold"]["question"]:
            raise ValueError("Frozen contract question differs from its reference")
        old = v1.evaluate_contract(revision=revision, query_id=qid, contract=contract, gold=case["gold"],
                                   records=case["records"], window_ids=case["window_ids"], reviews=reviews)
        if any(case["saved_v1"].get(key) != value for key, value in old.items()):
            raise ValueError(f"V1 assessment does not reproduce: {family}/{revision}/{condition}/{qid}")
        new = v2.upgrade_assessment(revision=revision, query_id=qid, contract=contract, gold=case["gold"], legacy=old)
        if any(new[gate] != old[gate] for gate in v1.SEMANTIC_GATES):
            raise ValueError("The revision repair changed a semantic verdict")
        meta = {"family": family, "condition": condition, "revision": revision, "query_id": qid}
        fingerprint = v1.canonical_sha256(contract)
        if revision not in corpora:
            corpora[revision] = {sid: record["text"] for sid, record in case["records"].items()}
        corpus = corpora[revision]
        runtime_old = legacy_verifier.verify_contract_validity(contract, corpus, {}, corpus_version=revision)
        runtime_new = revised_verifier.verify_contract_validity(contract, corpus, {}, corpus_version=revision)
        row = {**new, **meta, "question": contract["question"], "contract_sha256": fingerprint,
               "framework_version": contract.get("framework_version"),
               "context_sha256": case["row"]["context_sha256"],
               "evidence_window_sha256": case["row"].get("evidence_window_sha256", case["saved_v1"]["evidence_window_sha256"]),
               "input_source": case["source"], "full_gold_clause_coverage": case["saved_v1"]["full_gold_clause_coverage"],
               "runtime_v1_pass": runtime_old[0], "runtime_v2_pass": runtime_new[0],
               "runtime_v1_errors": runtime_old[1], "runtime_v2_errors": runtime_new[1],
               "status": contract["status"]}
        assessments.append(row)
        groups[(family, revision, condition)].append(row)
        changed_fields = [key for key in ENDPOINT_FIELDS if old[key] != new[key]]
        deltas.append({**meta, "endpoint_changed_fields": changed_fields,
                       "strict_v1_pass": old["strict_pass"], "strict_v2_pass": new["strict_pass"],
                       "added_revision_errors": new["declared_revision_errors"],
                       "semantic_verdicts_unchanged": True,
                       "legacy_review_id": old["review_id"], "v2_assessment_id": new["review_id"]})
        if runtime_old != runtime_new:
            runtime_deltas.append({**meta, "v1_pass": runtime_old[0], "v2_pass": runtime_new[0],
                                   "v1_errors": runtime_old[1], "v2_errors": runtime_new[1]})
        source_index.append({**meta, "source": case["source"], "contract_sha256": fingerprint,
                             "context_sha256": row["context_sha256"], "evidence_window_sha256": row["evidence_window_sha256"]})
        semantic_links.append({**meta, "v2_assessment_id": new["review_id"], "v1_body_fingerprint": old["review_id"],
                               "semantic_review_id": new["semantic_review_id"], "provenance": new["semantic_provenance"],
                               "review_record_sha256": v1.canonical_sha256(reviews[old["review_id"]]) if old["review_method"] == "source_inspection" else None,
                               "new_semantic_review": False})
        if not (runtime_old[0] and runtime_new[0] and contract["status"] in {"OK", "PARAMS_REQUIRED"}):
            eligibility[(family, revision, "excluded")] += 1
            continue
        eligibility[(family, revision, "positive_controls")] += 1
        for operator in OPERATORS:
            changed = mutate(contract, revision, operator)
            passed_old, errors_old = legacy_verifier.verify_contract_validity(changed, corpus, {}, corpus_version=revision)
            passed_new, errors_new = revised_verifier.verify_contract_validity(changed, corpus, {}, corpus_version=revision)
            same_surface = v1.review_id(revision, qid, changed) == old["review_id"]
            changed_strict = v2.upgrade_assessment(revision=revision, query_id=qid, contract=changed,
                                                  gold=case["gold"], legacy=old) if same_surface else None
            mutations.append({**meta, "operator": operator, "original_contract_sha256": fingerprint,
                              "mutated_contract_sha256": v1.canonical_sha256(changed),
                              "v1_runtime_pass": passed_old, "v2_runtime_pass": passed_new,
                              "v1_runtime_errors": errors_old, "v2_runtime_errors": errors_new,
                              "detected": not passed_new,
                              "revision_rejection_identified": bool(revised_verifier.revision_errors(changed, revision)),
                              "v1_semantic_surface_unchanged": same_surface,
                              "v1_strict_pass": old["strict_pass"] if same_surface else None,
                              "v2_strict_pass": changed_strict["strict_pass"] if same_surface else None,
                              "strict_assessment_boundary": "unchanged v1 surface; inherited semantic verdicts" if same_surface else
                                  "source IDs changed; runtime mutation only; no new semantic review"})

    count_rows = []
    for (family, revision, condition), rows in groups.items():
        count_rows.append({"family": family, "revision": revision, "condition": condition, "n": len(rows),
                           "strict_v1": sum(r["legacy_strict_pass"] for r in rows),
                           "strict_v2": sum(r["strict_pass"] for r in rows),
                           "revision_gate_pass": sum(r["declared_revision_pass"] for r in rows),
                           "strict_decisions_changed": sum(r["legacy_strict_pass"] != r["strict_pass"] for r in rows)})
    mutation_counts = []
    for revision in ("rev4", "rev5"):
        for operator in OPERATORS:
            rows = [r for r in mutations if r["revision"] == revision and r["operator"] == operator]
            mutation_counts.append({"revision": revision, "operator": operator, "attempts": len(rows),
                                    "legacy_runtime_accepted": sum(r["v1_runtime_pass"] for r in rows),
                                    "v2_detected": sum(r["detected"] for r in rows),
                                    "legacy_strict_accepted_where_surface_unchanged": sum(r["v1_strict_pass"] is True for r in rows),
                                    "v2_strict_accepted_where_surface_unchanged": sum(r["v2_strict_pass"] is True for r in rows)})
    acceptance = {"all_1532_v1_assessments_reproduced": len(assessments) == 1532,
                  "all_semantic_verdicts_unchanged": all(r["semantic_verdicts_unchanged"] for r in deltas),
                  "only_revision_gate_can_lower_strict_pass": all(not r["strict_v2_pass"] or r["strict_v1_pass"] for r in deltas),
                  "every_positive_control_has_eight_mutations": len(mutations) == 8 * sum(v for k, v in eligibility.items() if k[-1] == "positive_controls"),
                  "all_revision_mutations_detected": bool(mutations) and all(r["detected"] and r["revision_rejection_identified"] for r in mutations),
                  "strict_metadata_mutations_never_pass_v2": all(r["v2_strict_pass"] is not True for r in mutations),
                  "both_revision_directions_have_positive_controls": all(any(k[1] == rev and k[-1] == "positive_controls" and v for k, v in eligibility.items()) for rev in ("rev4", "rev5")),
                  "code_hashes_unchanged_during_execution": all(sha256(ROOT / p) == h for p, h in code_hashes.items()),
                  "ordinary_file_inputs_unchanged_during_execution": all(sha256(ROOT / p) == h for p, h in hashes.items() if (ROOT / p).is_file())}
    summary = {"result_id": RESULT_ID, "mutation_result_id": MUTATION_ID, "rule_version": v2.RULE_VERSION,
               "parent_rule_version": v1.RULE_VERSION, "assessments": len(assessments),
               "family_counts": dict(Counter(r["family"] for r in assessments)), "counts": count_rows,
               "strict_decisions_changed": sum(r["strict_v1_pass"] != r["strict_v2_pass"] for r in deltas),
               "assessment_rows_with_endpoint_changes": sum(bool(r["endpoint_changed_fields"]) for r in deltas),
               "runtime_rows_with_changes": len(runtime_deltas),
               "semantic_provenance_counts": dict(Counter(r["provenance"] for r in semantic_links)),
               "new_semantic_reviews": 0,
               "mutation_positive_controls": [{"family": k[0], "revision": k[1], "eligibility": k[2], "count": value}
                                              for k, value in sorted(eligibility.items())],
               "mutation_attempts": len(mutations), "mutation_counts": mutation_counts,
               "acceptance_checks": acceptance, "accepted": all(acceptance.values()),
               "boundary": v2.ASSESSMENT_BOUNDARY,
               "mutation_boundary": "Retrospective mutations of runtime-valid normal frozen contracts. Repeated conditions share questions; attempts are not independent observations. Source-namespace mutations receive runtime checks only, without new semantic reviews. This diagnostic tests revision handling, not global verifier sensitivity."}
    write_jsonl(output / "strict_pass_rows.jsonl", assessments)
    write_jsonl(output / "score_deltas.jsonl", deltas)
    write_jsonl(output / "semantic_review_links.jsonl", semantic_links)
    write_jsonl(output / "input_case_index.jsonl", source_index)
    write_jsonl(output / "runtime_deltas.jsonl", runtime_deltas)
    write_jsonl(output / "revision_mutation_audit.jsonl", mutations)
    with (output / "comparison_counts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(count_rows[0])); writer.writeheader(); writer.writerows(count_rows)
    config = {"result_id": RESULT_ID, "rule_version": v2.RULE_VERSION, "python": platform.python_version(),
              "checkout_head_at_execution": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "checkout_dirty_at_execution": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
              "input_sha256": hashes, "code_sha256": code_hashes, "new_inference": False, "new_retrieval": False,
              "semantic_judgments": "Inherited v1 source inspections and unchanged complete-retention proofs; no new independent adjudication",
              "strict_definition": v2.STRICT_PASS_DEFINITION, "revision_rule": revised_verifier.REVISION_RULE_VERSION,
              "mutation_operators": list(OPERATORS), "registration_status": "Retrospective repair and diagnostic; no new registered model study"}
    write_json(output / "run_config.json", config)
    write_json(output / "summary.json", summary)
    write_json(output / "FILES_SHA256.json", {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()})
    print(json.dumps({k: summary[k] for k in ("result_id", "assessments", "strict_decisions_changed", "runtime_rows_with_changes", "mutation_attempts", "accepted")}, indent=2))
    if not summary["accepted"]:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir)
