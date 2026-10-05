#!/usr/bin/env python3
"""Offline author-reference coverage and contract scoring; no model invocation."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from review_and_freeze import (FOLDER, REPO, read_jsonl, sha, validate_registration,
                               write_json, write_jsonl)


def wilson(successes, total):
    if total == 0:
        return None
    z = 1.959963984540054
    rate = successes / total
    denom = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denom
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def proportion(values):
    values = [v for v in values if v is not None]
    count = sum(bool(v) for v in values)
    return {"numerator": count, "denominator": len(values),
            "rate": count / len(values) if values else None,
            "wilson_95": wilson(count, len(values))}


def mcnemar(left_only, right_only):
    n = left_only + right_only
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(left_only, right_only) + 1)) / (2 ** n)) if n else 1.0


def score_contract(contract, label, records, validity):
    spans = contract.get("evidence_spans", [])
    if not isinstance(spans, list):
        spans = []
    ids, full_text_ids = set(), set()
    verbatim_flags = []
    for span in spans:
        if not isinstance(span, dict):
            verbatim_flags.append(False)
            continue
        sid = str(span.get("source_id", "") or "")
        text = str(span.get("span_text", "") or "")
        rec = records.get(sid)
        if rec:
            ids.add(sid)
            source = rec.get("text", "")
            exact = bool(text) and text in source
            verbatim_flags.append(exact)
            if text == source and source:
                full_text_ids.add(sid)
        else:
            verbatim_flags.append(False)
    groups = label["evidence_groups"]
    coverage_applicable = label["answerability"] in {"full", "partial"} and bool(groups)
    id_coverage = all(any(s in ids for s in group) for group in groups) if coverage_applicable else None
    full_coverage = all(any(s in full_text_ids for s in group) for group in groups) if coverage_applicable else None
    status = str(contract.get("status", "")).upper()
    applicability = label["odp_applicability"]
    odp_classification = None
    required_recall = None
    predicted_ids = contract.get("odp_required_list", [])
    predicted_ids = set(predicted_ids) if isinstance(predicted_ids, list) and all(isinstance(s, str) for s in predicted_ids) else set()
    if applicability in {"required", "not_required"}:
        odp_classification = (status == "PARAMS_REQUIRED") == (applicability == "required")
        required = set(label["required_odp_ids"] or [])
        required_recall = required.issubset(predicted_ids) if required else None
    strict = None
    if label["answerability"] == "full" and odp_classification is not None:
        strict = (bool(validity) and bool(full_coverage) and bool(spans)
                  and all(verbatim_flags) and status in {"OK", "PARAMS_REQUIRED"}
                  and odp_classification and (required_recall is not False))
    answer = str(contract.get("answer_text", "") or "")
    return {"answerability": label["answerability"], "status": status,
            "runtime_contract_valid": bool(validity),
            "has_evidence": bool(spans), "clause_id_group_coverage": id_coverage,
            "complete_clause_text_group_coverage": full_coverage,
            "all_spans_verbatim": all(verbatim_flags) if spans else False,
            "odp_applicability": applicability, "odp_author_label_agreement": odp_classification,
            "required_odp_ids_listed": required_recall,
            "strict_full_catalog_contract": strict,
            "strict_denominator_eligible": strict is not None,
            "answer_characters": len(answer), "answer_words": len(re.findall(r"\b\w+\b", answer)),
            "evidence_span_count": len(spans), "listed_odp_count": len(predicted_ids),
            "additional_listed_odp_ids_not_in_author_reference": (
                sorted(predicted_ids - set(label["required_odp_ids"] or []))
                if applicability in {"required", "not_required"} else None),
            "scope_and_semantic_correctness": "not independently assessed"}


def score_folder(output):
    protocol, questions, labels, _registration = validate_registration()
    config = json.loads((output / "run_config.json").read_text())
    if config["signature"]["registration_sha256"] != sha(FOLDER / "registration.json"):
        raise ValueError("Outcome package belongs to another registration")
    sys.path.insert(0, str(REPO / "src"))
    from compliancegpt.generator.verifier.verifier import verify_contract_validity
    from answerer_comparison.matched_window_runner import validate_paired_outputs, validate_prepared_context
    from run_natural_questions import validate_context_authority
    label_by_id = {r["query_id"]: r for r in labels}
    question_by_id = {q["query_id"]: q for q in questions}
    records = {rev: {r["id"]: r for r in read_jsonl(REPO / paths["ccs"]["path"])}
               for rev, paths in protocol["inputs"].items()}
    locked = {}
    for rev in {q["framework_version"] for q in questions}:
        path = output / "contexts" / f"{rev}.jsonl"
        lock = json.loads((output / "context_file_hashes.json").read_text())
        if sha(path) != lock[rev]:
            raise ValueError("Scoring context differs from the locked model-visible context")
        contexts = read_jsonl(path)
        expected_ids = [q["query_id"] for q in questions if q["framework_version"] == rev]
        if [c["query_id"] for c in contexts] != expected_ids:
            raise ValueError("Scoring contexts have different question identities/order")
        for c in contexts:
            validate_prepared_context(c)
            validate_context_authority(c, records[rev])
            q = question_by_id[c["query_id"]]
            if c["question"] != q["question"] or c["framework_version"] != rev:
                raise ValueError("Scoring context question differs from registration")
        locked.update({c["query_id"]: c for c in contexts})
    paired = json.loads((output / "paired_identity_audit.json").read_text())
    for rev in {q["framework_version"] for q in questions}:
        fresh = validate_paired_outputs(output / "contracts" / f"{rev}_compliancegpt.csv",
                                        output / "contracts" / f"{rev}_generative_baseline.csv")
        if fresh != paired.get(rev):
            raise ValueError("Paired identity audit no longer matches its outcome files")
    outcomes, captured = [], {}
    for system in ["compliancegpt", "generative_baseline"]:
        seen = set()
        for rev in sorted({q["framework_version"] for q in questions}):
            with (output / "contracts" / f"{rev}_{system}.csv").open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                qid = row["query_id"]
                if qid not in question_by_id or qid in seen:
                    raise ValueError("Unknown/duplicated outcome question")
                seen.add(qid)
                q = question_by_id[qid]
                model = protocol["models"]["answerer"]
                if row.get("model_id") != model["id"] or any(row.get(key) != model["revision"]
                        for key in ["model_requested_revision", "model_resolved_revision", "tokenizer_resolved_revision"]):
                    raise ValueError("Outcome model/tokenizer differs from the registered pin")
                if row["question"] != q["question"] or row["framework_version"] != q["framework_version"]:
                    raise ValueError("Outcome question or revision differs from registration")
                if row["context_sha256"] != locked[qid]["context_sha256"] or row["evidence_window_sha256"] != locked[qid]["evidence_window_manifest"]["sha256"]:
                    raise ValueError("Outcome evidence differs from the locked context")
                contract = json.loads(row["contract_json"])
                valid, errors = verify_contract_validity(
                    contract, corpus={sid: rec["text"] for sid, rec in records[rev].items()},
                    org_profile={}, strict_verbatim=True, corpus_version=rev,
                    expected_resolution_policy="ASK")
                outcome = {"query_id": qid, "framework_version": rev, "system": system,
                           **score_contract(contract, label_by_id[qid], records[rev], valid),
                           "runtime_verifier_errors": errors}
                outcomes.append(outcome)
                captured[(system, qid)] = outcome
        if seen != set(question_by_id):
            raise ValueError("Natural-question outcome package is incomplete")
    if sum(p["paired_rows"] for p in paired.values()) != len(questions):
        raise ValueError("Paired identity audit has the wrong denominator")
    for qid in question_by_id:
        left = captured[("compliancegpt", qid)]
        right = captured[("generative_baseline", qid)]
        if left["strict_denominator_eligible"] != right["strict_denominator_eligible"]:
            raise ValueError("Different strict denominators between answer paths")
    report = {"result_id": protocol["result_id"], "separate_from_136_row_benchmark": True,
              "question_count": len(questions), "paired_generation_count": len(outcomes),
              "scope_counts": dict(Counter(r["answerability"] for r in labels)),
              "odp_label_counts": dict(Counter(r["odp_applicability"] for r in labels)),
              "independent_correctness_validated": False,
              "post_run_semantic_review_status": "pending separate author review",
              "experiment_complete": False, "systems": {}}
    for system in ["compliancegpt", "generative_baseline"]:
        rows = [r for r in outcomes if r["system"] == system]
        positives = [r for r in rows if r["odp_applicability"] == "required"]
        negatives = [r for r in rows if r["odp_applicability"] == "not_required"]
        report["systems"][system] = {
            "runtime_contract_valid": proportion([r["runtime_contract_valid"] for r in rows]),
            "clause_id_group_coverage": proportion([r["clause_id_group_coverage"] for r in rows]),
            "complete_clause_text_group_coverage": proportion([r["complete_clause_text_group_coverage"] for r in rows]),
            "strict_full_catalog_contract": proportion([r["strict_full_catalog_contract"] for r in rows]),
            "odp_author_reference_sensitivity": proportion([r["odp_author_label_agreement"] for r in positives]),
            "odp_author_reference_specificity": proportion([r["odp_author_label_agreement"] for r in negatives]),
            "total_answer_words": sum(r["answer_words"] for r in rows),
            "total_evidence_spans": sum(r["evidence_span_count"] for r in rows),
            "total_listed_odps": sum(r["listed_odp_count"] for r in rows)}
    left_only = right_only = determinate = 0
    for qid in question_by_id:
        left = captured[("compliancegpt", qid)]["strict_full_catalog_contract"]
        right = captured[("generative_baseline", qid)]["strict_full_catalog_contract"]
        if left is None or right is None:
            continue
        determinate += 1
        left_only += bool(left and not right)
        right_only += bool(right and not left)
    report["paired_strict"] = {"denominator": determinate, "compliance_only": left_only,
                               "baseline_only": right_only,
                               "exact_mcnemar_p": mcnemar(left_only, right_only) if determinate else None}
    report["limits"] = [
        "One-forum purposive convenience sample. It does not estimate population-wide performance.",
        "Wilson intervals describe the eligible observed rows under a binomial assumption. They do not account for purposive source selection or correlated forum users.",
        "Original post captures include source control quotations and explicit IDs. Their presence is documented.",
        "Author-reviewed labels are reference judgments, not independent professional correctness.",
        "Full-text coverage is a conservative contract/evidence criterion and does not prove responsive semantic interpretation.",
        "Partial, outside and ambiguous questions remain visible. They are not counted as successful whole-question answers.",
        "Untestable ODP cases are not negative labels. Additional listed IDs are unadjudicated expansions.",
        "Answer-length and clarification counts are burden proxies, not measured user effort.",
        "Nonsignificant paired results do not establish equivalence."]
    write_jsonl(output / "per_question_outcomes.jsonl", outcomes)
    write_json(output / "summary.json", report)
    manual_rows = [{"query_id": q["query_id"], "system": s,
                    "scope_appropriate": "", "responsive_to_entire_question": "",
                    "unsupported_implementation_or_legal_claim": "", "reviewer": "", "notes": ""}
                   for q in questions for s in ["compliancegpt", "generative_baseline"]]
    review_path = output / "post_run_semantic_review.csv"
    if not review_path.exists():
        with review_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(manual_rows[0]))
            w.writeheader()
            w.writerows(manual_rows)
    lines = ["# Separate natural-question results", "", f"Questions: {len(questions)}. Paired outputs: {len(outcomes)}.",
             "", "These are author-reference coverage and contract outcomes. Independent correctness and the full responsiveness of partial/outside questions have not been assessed.",
             "", "| Answer path | Runtime validity | Strict full-catalog contract | ODP sensitivity | ODP specificity |", "|---|---:|---:|---:|---:|"]
    def fraction(m):
        return f"{m['numerator']}/{m['denominator']}" if m["denominator"] else "n.a. (0 eligible)"
    for s, m in report["systems"].items():
        lines.append("| " + s + " | " + " | ".join(fraction(m[key]) for key in
                     ["runtime_contract_valid", "strict_full_catalog_contract", "odp_author_reference_sensitivity", "odp_author_reference_specificity"]) + " |")
    lines += ["", "## Limits", ""] + ["- " + text for text in report["limits"]]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    score_folder(parser.parse_args().output_dir.resolve())
