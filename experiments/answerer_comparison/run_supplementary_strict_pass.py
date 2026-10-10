#!/usr/bin/env python3
"""Score frozen supplementary outputs with the complete strict-pass rule without generating new answers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
from answerer_comparison import strict_pass as scoring
from experiments.answerer_comparison.run_strict_pass import load_inputs

BASE = Path("experiments/answerer_comparison")
FROZEN_SHA256 = {
    "experiments/answerer_comparison/rq2_bf16_baseline/results_v1/contracts/rev4_generative_baseline_bf16.csv": "1b84eb673145bdae15d8e52c22678f2cf780d5f09f6e8603e6578ec586c2fc60",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-00": "a485699b25eca2d4489867fa4db10dbd6c69693463d2bd447a1bcfeef8e64fed",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-01": "f5aebbb185b065c7d8e9935191d09fc750f09e9f435ab95faf5039effca46512",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-02": "868df4c3ce717d042e3f81c9202c8ee1a3f715bcc87356265d8b2e8e1a231c60",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-03": "914c03ad1ff2ede532dbd98b365d7cdaac54a36001c541e28f7e08d8a4acc333",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-04": "9103ee130d80a95ccc9029f39fd55c39865873868ca1d8c47cc50ebccf8318d3",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-05": "d089c18b27bbdc41cdf796c223337e8988b93e50e4dfcb1ab7b90e73ead4aa5a",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-06": "328f3b9b79daae5a9c52be891d5a5a14d7a333f6c38615f9626d665b111e556b",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-07": "69c827f982c2127d18949adec5d76d7b527613f5bd6f12ec9322730885f2d5d8",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-08": "e8a0a2bdd997bf379955bd6578eb828dd70a12c327d78f94188cc10c5f1a8224",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-09": "7fa52a69b9b9908641a11df9841cafd7af64502abe7c6ada5579d6a275531221",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-10": "9f139635d712591c06f8b7b3c2ce1df6e9f4aac4d42c965bc930905009f46291",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev4_no_selector.csv": "af05e97e7c0078a1f576700922ca292331bc778db4d9948337b38d6364be7602",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev5_no_selector.csv": "606024e83dacdabac8e0dcbe7bbd37aa61d7a9823d23341b3de6d1d58fcfff3d",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev4_rescue_off.csv": "1f707ab93063fc82dd4c014a55396da872f4fa7cf780b405dcebcd313daa1b45",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev4_rescue_on.csv": "5a29bce877990ef3f52a270a4d8038464bf3b7973409ae35e87e630dddae8aa8",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev5_rescue_off.csv": "df0a9884fe8f8f284a2bf38d7c110d361faf12c63e46204e082496d022e176c6",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev5_rescue_on.csv": "369587fe442acd0b5f80039af034d3fa412823fdb0ec020deeced2b86829c59f"
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(data: bytes) -> dict:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    result = {r["query_id"]: r for r in rows}
    if len(rows) != len(result):
        raise ValueError("Duplicate contract question IDs")
    return result


def truth(value) -> bool:
    return str(value).lower() in {"true", "1"}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def publication_field_names(value):
    """Name the complete endpoint explicitly in derived historical templates."""
    names = {"offline_strict_pass": "strict_pass",
             "offline_strict_pass_rate": "strict_pass_rate"}
    if isinstance(value, dict):
        return {names.get(key, key): publication_field_names(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [publication_field_names(item) for item in value]
    return value


def run(output_root: Path) -> dict:
    output_root = output_root.resolve()
    if output_root == REPO_ROOT or REPO_ROOT in output_root.parents:
        raise ValueError("Use an external output directory to preserve published evidence")
    output_root.mkdir(parents=True, exist_ok=False)
    inputs, input_hashes = load_inputs(REPO_ROOT)
    primary_reviews = scoring.load_reviews(REPO_ROOT / BASE / "strict_pass_reviews.jsonl")
    supplemental_path = REPO_ROOT / BASE / "strict_pass_supplementary_reviews.jsonl"
    extra_reviews = scoring.load_reviews(supplemental_path)
    if set(primary_reviews) & set(extra_reviews):
        raise ValueError("Main and supplementary review IDs overlap")
    reviews = {**primary_reviews, **extra_reviews}
    primary = {
        rev: {system: scoring.score_rows(revision=rev, rows=rows, gold_rows=gold, repo_root=REPO_ROOT, reviews=reviews)
              for system, rows in systems.items()}
        for rev, (_, gold, systems) in inputs.items()
    }
    blobs = {}
    for name, expected in FROZEN_SHA256.items():
        blobs[name] = (REPO_ROOT / name).read_bytes()
        input_hashes[name] = digest(blobs[name])
        if input_hashes[name] != expected:
            raise ValueError(f"Frozen supplementary input changed: {name}")
    parts = sorted(name for name in blobs if ".zip.part-" in name)
    archive = zipfile.ZipFile(io.BytesIO(b"".join(blobs[name] for name in parts)))
    groups = {}
    used_reviews = set()
    all_rows = []
    for rev, (records, gold, systems) in inputs.items():
        main_rows = systems["compliancegpt"]
        conditions = [
            ("no_selector", f"{BASE}/rq2_no_selector/results_v1/contracts/{rev}_no_selector.csv", None),
            ("rescue_off", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{rev}_rescue_off.csv", None),
            ("rescue_on", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{rev}_rescue_on.csv", None),
        ]
        if rev == "rev4":
            conditions.append(("baseline_bf16", f"{BASE}/rq2_bf16_baseline/results_v1/contracts/rev4_generative_baseline_bf16.csv", None))
        for width in (1, 2, 3, 5):
            conditions.append((f"top{width}", f"contracts/top{width}_{rev}_compliancegpt.csv", f"contexts/top{width}_{rev}_prepared_contexts.jsonl"))
        for condition, name, context_name in conditions:
            data = archive.read(name) if context_name else blobs[name]
            if context_name:
                input_hashes[f"archive:{name}"] = digest(data)
                context_data = archive.read(context_name)
                input_hashes[f"archive:{context_name}"] = digest(context_data)
                context_list = [json.loads(line) for line in context_data.decode().splitlines()]
                contexts = {r["query_id"]: r for r in context_list}
                if len(context_list) != len(contexts) or set(contexts) != set(gold):
                    raise ValueError("Archived context question IDs are incomplete or duplicated")
            rows = read_csv(data)
            if set(rows) != set(gold):
                raise ValueError(f"Supplementary contract question IDs do not match the gold labels: {name}")
            results = {}
            for qid in sorted(rows, key=int):
                row = rows[qid]
                contract = json.loads(row["contract_json"])
                if context_name:
                    context = contexts[qid]
                    manifest = context["evidence_window_manifest"]
                    window_ids = [r["id"] for r in context["evidence_window"]]
                    if (row["context_sha256"] != context["context_sha256"]
                            or row["evidence_window_sha256"] != manifest["sha256"]
                            or window_ids != manifest["source_ids"]
                            or window_ids != row["evidence_window_source_ids"].split("|")):
                        raise ValueError(f"Gate-width contract does not match its frozen window: {rev}/{condition}/{qid}")
                    for record, pinned in zip(context["evidence_window"], manifest["records"], strict=True):
                        if record["id"] != pinned["source_id"] or digest(record["text"].encode()) != pinned["text_sha256"]:
                            raise ValueError("Archived window content hash does not match")
                        if record["id"] not in records or record["text"] != records[record["id"]]["text"]:
                            raise ValueError("Archived window does not match the active CCS")
                    window_sha = manifest["sha256"]
                else:
                    matched = main_rows[qid]
                    if row["context_sha256"] != matched["context_sha256"]:
                        raise ValueError(f"Supplementary context does not match the main comparison: {rev}/{condition}/{qid}")
                    window_ids = matched["evidence_window_source_ids"].split("|")
                    window_sha = matched["evidence_window_sha256"]
                    if "evidence_window_sha256" in row and row["evidence_window_sha256"] != window_sha:
                        raise ValueError("Supplementary frozen window hash does not match")
                    if "evidence_window_source_ids" in row and row["evidence_window_source_ids"].split("|") != window_ids:
                        raise ValueError("Supplementary frozen window source IDs do not match")
                result = scoring.evaluate_contract(revision=rev, query_id=qid, contract=contract,
                    gold=gold[qid], records=records, window_ids=window_ids, reviews=reviews)
                recorded = truth(row.get("verifier_pass", row.get("offline_strict_pass")))
                if result["contract_checks_pass"] != recorded:
                    raise ValueError(f"Original contract-check decision did not reproduce: {rev}/{condition}/{qid}")
                covered = truth(row.get("doc_full_recall", row.get("full_gold_clause_coverage")))
                runtime = truth(row.get("contract_validity_pass", row.get("runtime_contract_pass")))
                if result["strict_pass"] and not covered:
                    raise ValueError("Strict pass lacks complete gold-clause coverage")
                if result["review_method"] == "source_inspection":
                    used_reviews.add(result["review_id"])
                result = {**result, "condition": condition, "question": contract["question"],
                    "full_gold_clause_coverage": covered, "runtime_contract_pass": runtime,
                    "evidence_window_sha256": window_sha, "input_path": name}
                results[qid] = result
                all_rows.append(result)
            groups[(rev, condition)] = results
    if set(extra_reviews) != used_reviews & set(extra_reviews):
        raise ValueError("Supplementary reviews are missing, stale, or unused")

    def rate(results):
        return {"count": sum(r["strict_pass"] for r in results.values()), "n": len(results),
                "rate": sum(r["strict_pass"] for r in results.values()) / len(results)}

    def update_rate(target, results):
        target.update(rate(results))

    definition = "Strict pass requires C, W, L, U, A, F, and P together: complete gold-clause coverage, valid sources and spans, complete retained-parameter accounting, citation use in the body, complete answer requirements, faithful normative claims, and faithful parameter semantics. Faithful paraphrases can pass. Clarification value domains are outside this endpoint."
    boundary = "The common rule assesses frozen stored answers through source inspection or complete-retention proofs. No independent expert adjudication is available. Uncertain cases remain in the denominator and receive no pass credit. Paired tests are retrospective, exploratory, and unadjusted."
    written = []
    for study in ("rq2_bf16_baseline", "rq2_no_selector", "rq2_rescue_ablation", "rq2_control_gate_width"):
        relative = BASE / study / "results_v1"
        summary = json.loads((REPO_ROOT / relative / "summary.json").read_text())
        summary["strict_pass_definition"] = definition
        summary["strict_pass_assessment_boundary"] = boundary
        summary["strict_pass_rule_version"] = scoring.RULE_VERSION
        if study == "rq2_bf16_baseline":
            configs = {"generative_baseline_bf16": groups[("rev4", "baseline_bf16")],
                       "generative_baseline_4bit": primary["rev4"]["baseline"],
                       "compliancegpt_4bit": primary["rev4"]["compliancegpt"]}
            for key, results in configs.items():
                update_rate(summary["configurations"][key]["strict_pass"], results)
            for key, right in (("bf16_vs_4bit_baseline", "generative_baseline_4bit"),
                               ("bf16_baseline_vs_4bit_compliancegpt", "compliancegpt_4bit")):
                summary["paired_strict_pass"][key].update(scoring.paired_strict_pass(configs["generative_baseline_bf16"], configs[right]))
        elif study == "rq2_control_gate_width":
            configs = {f"{rev}_{condition}": results for (rev, condition), results in groups.items() if condition.startswith("top")}
            configs.update({f"{rev}_adaptive_v3": primary[rev]["compliancegpt"] for rev in inputs})
            for key, results in configs.items():
                update_rate(summary["configurations"][key]["strict_pass"], results)
            for key, target in summary["pairwise_strict_pass"].items():
                left, right = key.split("_vs_")
                rev = left.split("_")[0]
                target.update(scoring.paired_strict_pass(configs[left], configs[f"{rev}_{right}"]))
        else:
            for rev in inputs:
                r = summary["revisions"][rev]
                if study == "rq2_no_selector":
                    left, right = primary[rev]["compliancegpt"], groups[(rev, "no_selector")]
                    update_rate(r["selector_v3"]["offline_strict_pass"], left)
                    update_rate(r["no_selector_v1"]["offline_strict_pass"], right)
                    r["delta_no_selector_minus_selector"]["offline_strict_pass_rate"] = rate(right)["rate"] - rate(left)["rate"]
                    p = scoring.paired_strict_pass(left, right)
                    r["paired"]["offline_strict_pass"] = {"selector_only": p["left_only"], "no_selector_only": p["right_only"],
                        "both": p["both_pass"], "neither": p["neither_pass"], "exact_mcnemar_two_sided_p": p["exact_mcnemar_two_sided_p"]}
                else:
                    left, right = groups[(rev, "rescue_off")], groups[(rev, "rescue_on")]
                    update_rate(r["rescue_off"]["offline_strict_pass"], left)
                    update_rate(r["rescue_on"]["offline_strict_pass"], right)
                    r["delta_on_minus_off"]["offline_strict_pass_rate"] = rate(right)["rate"] - rate(left)["rate"]
                    p = scoring.paired_strict_pass(left, right)
                    r["paired"]["offline_strict_pass"] = {"rescue_off_only": p["left_only"], "rescue_on_only": p["right_only"],
                        "both": p["both_pass"], "neither": p["neither_pass"], "n": p["paired_rows"], "exact_mcnemar_two_sided_p": p["exact_mcnemar_two_sided_p"]}
        published = BASE / "supplementary_strict_pass/results_v1/studies" / study
        summary["publication_scope"] = "Complete-endpoint reassessment of immutable historical outputs"
        summary["historical_source_summary"] = str(relative / "summary.json")
        target = output_root / published / "summary.json"
        write_json(target, publication_field_names(summary))
        written.append(target)
        table = [f"# {study} complete strict-pass results", "", definition, "", boundary, "",
                 "| Revision and condition | Strict pass | Complete clause coverage | Mean answer words | Mean gold-clause precision |",
                 "| --- | --- | --- | --- | --- |"]
        if "configurations" in summary:
            for key, item in summary["configurations"].items():
                n = item["n_questions"]
                table.append(f"| {key} | {item['strict_pass']['count']}/{n} | {item['full_gold_clause_coverage']['count']}/{n} | {item['answer_word_count']['mean']:.2f} | {item['mean_gold_clause_precision']:.4f} |")
        else:
            keys = ("selector_v3", "no_selector_v1") if study == "rq2_no_selector" else ("rescue_off", "rescue_on")
            for rev, revision_summary in summary["revisions"].items():
                for key in keys:
                    item = revision_summary[key]
                    n = item["n_questions"]
                    table.append(f"| {rev}/{key} | {item['offline_strict_pass']['count']}/{n} | {item['full_gold_clause_coverage']['count']}/{n} | {item['review_burden']['answer_word_count']['mean']:.2f} | {item['review_burden']['gold_clause_precision']['mean']:.4f} |")
        table.extend(["", "See [row-level assessments](../../strict_pass_rows.jsonl) and the [manifest](../../manifest.json). Original contract CSVs retain their historical C-check fields. This separate summary reports the complete endpoint. Answer length is a proxy for review burden; it does not measure professional review time.", ""])
        if study == "rq2_no_selector":
            table.append("The stored diagnostic contracts have empty `ask_list` fields. In Rev. 5, 85 C-passing answers lack the required parameter requests; Rev. 4 has 32 such answers. The strict-pass difference cannot be attributed entirely to the selector. Coverage, length, precision, and the original parameter-set measurements retain their recorded values.")
            for rev in inputs:
                pair = summary["revisions"][rev]["paired"]["offline_strict_pass"]
                table.append(f"\n{rev}: main-path-only passes {pair['selector_only']}, no-selector-only passes {pair['no_selector_only']}, two-sided exact McNemar p = {pair['exact_mcnemar_two_sided_p']:.10g}。")
            comparison = REPO_ROOT / relative / "per_row_comparison.csv"
            with comparison.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = reader.fieldnames
                comparison_rows = list(reader)
            for row in comparison_rows:
                rev, qid = row["framework_version"], row["query_id"]
                row["selector_offline_strict_pass"] = primary[rev]["compliancegpt"][qid]["strict_pass"]
                row["no_selector_offline_strict_pass"] = groups[(rev, "no_selector")][qid]["strict_pass"]
            renamed = {"selector_offline_strict_pass": "selector_strict_pass",
                       "no_selector_offline_strict_pass": "no_selector_strict_pass"}
            fields = [renamed.get(field, field) for field in fields]
            comparison_rows = [{renamed.get(key, key): value for key, value in row.items()}
                               for row in comparison_rows]
            comparison_target = output_root / published / "per_row_comparison.csv"
            with comparison_target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(comparison_rows)
            written.append(comparison_target)
        elif study == "rq2_control_gate_width":
            table.append("Rev. 5 fixed top-5 answers Q12, Q39, and Q61 cite valid CCS sources outside their own frozen windows and fail W. Complete coverage remains 67/100, while strict pass is 64/100. Other fixed-width conditions have equal strict-pass and complete-coverage counts.")
        elif study == "rq2_bf16_baseline":
            table.append("BF16 Q17 leaves uncertain whether the information system must enforce the restriction or the organization alone must act. It receives no strict-pass credit and remains in the 36-question denominator. This is an author judgment without independent expert adjudication.")
            for key, pair in summary["paired_strict_pass"].items():
                table.append(f"\n{key}: left-only passes {pair['left_only']}, right-only passes {pair['right_only']}, two-sided exact McNemar p = {pair['exact_mcnemar_two_sided_p']:.10g}。")
        else:
            table.append("Under the common rule, frozen Rev. 5 rescue-off and rescue-on outputs pass 59/100 and 65/100, respectively. Both Rev. 4 conditions pass 29/36. Other measurements match the original archive.")
        markdown = output_root / published / "SUMMARY.md"
        markdown.write_text("\n".join(table) + "\n", encoding="utf-8")
        written.append(markdown)

    relative = BASE / "supplementary_strict_pass/results_v1"
    destination = output_root / relative
    destination.mkdir(parents=True, exist_ok=True)
    jsonl = destination / "strict_pass_rows.jsonl"
    jsonl.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_rows), encoding="utf-8")
    metrics = {}
    for (rev, condition), results in groups.items():
        covered = [r for r in results.values() if r["full_gold_clause_coverage"]]
        metrics[f"{rev}_{condition}"] = {
            "strict_pass": rate(results), "full_gold_clause_coverage": len(covered),
            "coverage_complete_failures": sum(not r["strict_pass"] for r in covered),
            "uncertain_query_ids": [qid for qid, r in results.items() if r["semantic_uncertain"]],
            "strict_pass_query_ids": [qid for qid, r in results.items() if r["strict_pass"]],
            "paired_vs_main_compliancegpt": scoring.paired_strict_pass(primary[rev]["compliancegpt"], results),
        }
    metrics["rev4_baseline_bf16"]["paired_vs_4bit_baseline"] = scoring.paired_strict_pass(groups[("rev4", "baseline_bf16")], primary["rev4"]["baseline"])
    write_json(destination / "summary.json", {"rule_version": scoring.RULE_VERSION, "assessment_boundary": boundary, "conditions": metrics})
    written.extend([jsonl, destination / "summary.json"])
    code_paths = [Path(__file__).relative_to(REPO_ROOT), BASE / "strict_pass_supplementary_reviews.jsonl",
                  BASE / "strict_pass_reviews.jsonl", Path("src/answerer_comparison/strict_pass.py"), BASE / "run_strict_pass.py"]
    manifest = {"rule_version": scoring.RULE_VERSION, "original_data_commit": "72979835f1e05bae513468ca4074b4d43497da2c",
                "inputs": input_hashes, "evaluation": {str(p): digest((REPO_ROOT / p).read_bytes()) for p in code_paths},
                "outputs": {str(p.relative_to(output_root)): digest(p.read_bytes()) for p in written},
                "supplementary_answer_count": len(all_rows), "supplementary_body_review_count": len(extra_reviews)}
    write_json(destination / "manifest.json", manifest)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assess supplementary outputs with the complete strict-pass rule")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_root.resolve())
    print(json.dumps({key: value["strict_pass"] for key, value in result.items()}, ensure_ascii=False, indent=2))
