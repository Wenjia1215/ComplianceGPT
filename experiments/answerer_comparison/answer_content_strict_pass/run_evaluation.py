#!/usr/bin/env python3
"""Apply Answer-content strict pass to frozen RQ2 outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from answerer_comparison.answer_content_strict_pass import (  # noqa: E402
    RULE_VERSION, SEMANTIC_GATES, answer_surface, evaluate_contract,
    full_retention_certificate, review_id,
)
from compliancegpt.generator.verifier.verifier import verify_answer  # noqa: E402

SOURCE_SNAPSHOT = "72979835f1e05bae513468ca4074b4d43497da2c"
EXPECTED_N = {"rev5": 100, "rev4": 36}
EXPECTED_LEGACY = {
    "rev5": {"baseline": 25, "compliancegpt": 65, "gemini": 66},
    "rev4": {"baseline": 8, "compliancegpt": 29, "gemini": 24},
}
CSV_SHA256 = {
    ("rev5", "baseline"): "85a3e52b75b283a3fda6c50ae59d8dde4e59748ada7d58c5b88ae8c5c8f2cb63",
    ("rev5", "compliancegpt"): "9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9",
    ("rev5", "gemini"): "8380b370d061dc772e25b353b353b06023540c6c5f6613839c4f36bedccae06e",
    ("rev4", "baseline"): "cf891ddd0710125e5d37b43913166f0e7cef50426605133d87915229a90f53b5",
    ("rev4", "compliancegpt"): "cb8d49cdff4b1ebcd68f0010b4fbecafd457352cb9e963856b03ef1a0aae50f9",
    ("rev4", "gemini"): "14f5c33146a06ada055057e221bfc226282d11e2930281603a7b6c6e491876b7",
}
SOURCE_SHA256 = {
    "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl": "500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726",
    "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl": "71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08",
    "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv": "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2",
    "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv": "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5",
}
BASE = "experiments/answerer_comparison"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def contract_path(revision: str, system: str) -> str:
    folder = "rq2_frontier_baseline_rev5" if revision == "rev5" else "rq2_frontier_baseline"
    name = {
        "baseline": f"references/{revision}_generative_baseline_4bit.csv",
        "compliancegpt": f"references/{revision}_compliancegpt_4bit.csv",
        "gemini": f"contracts/{revision}_generative_frontier_api.csv",
    }[system]
    return f"{BASE}/{folder}/results_v1/{name}"


def load_inputs(root: Path):
    inputs = {}
    hashes = {}
    for revision, expected_n in EXPECTED_N.items():
        ccs_path = f"data/ccs/nist800-53/NIST_SP-800-53_{revision}_catalog.jsonl"
        gold_path = f"data/gold_standard_datasets/nist800-53/nist_sp800-53_{revision}_gold-set_{expected_n}q.csv"
        for path in (ccs_path, gold_path):
            hashes[path] = sha256(root / path)
            if hashes[path] != SOURCE_SHA256[path]:
                raise ValueError(f"Frozen source or gold bytes changed: {path}")
        records = {}
        for line in (root / ccs_path).read_text().splitlines():
            record = json.loads(line)
            if record["id"] in records:
                raise ValueError("Duplicate CCS ID")
            records[record["id"]] = record
        with (root / gold_path).open(encoding="utf-8-sig", newline="") as handle:
            gold_rows = list(csv.DictReader(handle))
        gold = {row["id"]: row for row in gold_rows}
        expected_ids = {str(x) for x in range(1, expected_n + 1)}
        if len(gold_rows) != expected_n or set(gold) != expected_ids:
            raise ValueError("Unexpected gold rows")
        by_system = {}
        for system in ("baseline", "compliancegpt", "gemini"):
            path = contract_path(revision, system)
            hashes[path] = sha256(root / path)
            if hashes[path] != CSV_SHA256[(revision, system)]:
                raise ValueError(f"Frozen contract bytes changed: {path}")
            with (root / path).open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if len(rows) != expected_n or {r["query_id"] for r in rows} != expected_ids:
                raise ValueError(f"Unexpected or duplicate contract rows: {path}")
            by_system[system] = {row["query_id"]: row for row in rows}
        for query_id in expected_ids:
            contexts = {
                (rows[query_id]["context_sha256"], rows[query_id]["evidence_window_sha256"], rows[query_id]["evidence_window_source_ids"])
                for rows in by_system.values()
            }
            if len(contexts) != 1:
                raise ValueError(f"Evidence windows are not matched: {revision}/{query_id}")
        inputs[revision] = (records, gold, by_system)
    return inputs, hashes


def wilson(count: int, n: int) -> dict:
    z = 1.959963984540054
    p = count / n
    divisor = 1 + z * z / n
    center = (p + z * z / (2 * n)) / divisor
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / divisor
    return {"lower": center - half, "upper": center + half, "level": 0.95}


def exact_mcnemar(first: dict, second: dict, key: str) -> dict:
    first_only = sum(first[q][key] and not second[q][key] for q in first)
    second_only = sum(second[q][key] and not first[q][key] for q in first)
    n = first_only + second_only
    p = min(1.0, 2 * sum(math.comb(n, x) for x in range(min(first_only, second_only) + 1)) / 2**n) if n else 1.0
    return {"compliancegpt_only": first_only, "gemini_only": second_only, "two_sided_exact_p": p}


def prepare_packet(inputs, output: Path) -> None:
    packets = {}
    original_counts = {}
    for revision, (records, gold, by_system) in inputs.items():
        corpus = {sid: r["text"] for sid, r in records.items()}
        for system, rows in by_system.items():
            passed = 0
            for query_id, row in rows.items():
                contract = json.loads(row["contract_json"])
                old = verify_answer(contract, gold[query_id], corpus, org_profile={}, corpus_version=revision, strict_extras=False, strict_verbatim=True, strict_version=False)
                if old.is_pass != (row["verifier_pass"] == "True"):
                    raise ValueError("Legacy outcome did not reproduce")
                passed += old.is_pass
                if not old.is_pass or full_retention_certificate(contract, gold[query_id], records):
                    continue
                rid = review_id(revision, query_id, contract)
                param_ids = set(contract.get("odp_required_list", []))
                packets[rid] = {
                    "review_id": rid, "rule_version": RULE_VERSION,
                    **answer_surface(revision, query_id, contract),
                    "required_clause_ids": gold[query_id]["gold_control_path"].splitlines(),
                    "parameter_definitions": {pid: records[pid]["text"] for pid in sorted(param_ids) if pid in records},
                }
            original_counts[(revision, system)] = passed
            if passed != EXPECTED_LEGACY[revision][system]:
                raise ValueError("Unexpected legacy count")
    write_jsonl(output / "review_packet.jsonl", [packets[key] for key in sorted(packets)])
    print(f"Prepared {len(packets)} distinct answer surfaces for source inspection; legacy outcomes reproduced.")


def load_reviews(path: Path) -> dict:
    reviews = {}
    for line in path.read_text().splitlines():
        review = json.loads(line)
        rid = review["review_id"]
        if rid in reviews:
            raise ValueError(f"Duplicate semantic review: {rid}")
        reviews[rid] = review
    return reviews


def run(root: Path, output: Path, reviews_path: Path, inputs: dict, hashes: dict):
    reviews = load_reviews(reviews_path)
    results = []
    summary = {
        "rule_version": RULE_VERSION,
        "strict_pass_endpoint": "Answer-content extension",
        "source_snapshot": SOURCE_SNAPSHOT,
        "scope": "retrospective frozen-output re-evaluation",
        "review_boundary": "Source-inspection judgments are not independently adjudicated. Canonical retention is sufficient proof, not a required writing style.",
        "denominators": EXPECTED_N,
        "configurations": {}, "paired_comparison": {},
    }
    used_reviews = set()
    for revision, (records, gold, by_system) in inputs.items():
        by_result = {}
        for system, rows in by_system.items():
            evaluated = []
            for query_id in sorted(rows, key=int):
                row = rows[query_id]
                contract = json.loads(row["contract_json"])
                result = evaluate_contract(
                    revision=revision, query_id=query_id, contract=contract,
                    gold=gold[query_id], records=records,
                    window_ids=row["evidence_window_source_ids"].split("|"), reviews=reviews,
                )
                if result["legacy_pass"] != (row["verifier_pass"] == "True"):
                    raise ValueError(f"Legacy disagreement: {revision}/{system}/{query_id}")
                if result["answer_content_pass"] and not result["legacy_pass"]:
                    raise ValueError("An old failure cannot become an extended strict pass")
                result.update(system=system, question=row["question"], input_path=contract_path(revision, system))
                if result["review_method"] == "source_inspection":
                    used_reviews.add(result["review_id"])
                evaluated.append(result)
                results.append(result)
            if sum(x["legacy_pass"] for x in evaluated) != EXPECTED_LEGACY[revision][system]:
                raise ValueError("Legacy total changed")
            by_result[system] = {r["query_id"]: r for r in evaluated}
            n = len(evaluated)
            counts = {}
            for key in ("legacy_pass", "answer_content_pass", "possible_answer_content_pass"):
                count = sum(bool(x[key]) for x in evaluated)
                counts[key] = {"count": count, "n": n, "rate": count / n, "wilson_95_ci": wilson(count, n)}
            eligible = [x for x in evaluated if x["legacy_pass"]]
            counts["new_failure_query_ids"] = [x["query_id"] for x in eligible if not x["answer_content_pass"]]
            counts["uncertain_eligible_rows"] = [x["query_id"] for x in eligible if any(x[g] == "uncertain" for g in SEMANTIC_GATES)]
            counts["legacy_and_mechanical_pass_count"] = sum(x["exact_provenance"] and x["complete_parameter_accounting"] for x in eligible)
            counts["added_gate_no_credit_counts"] = {
                g: sum(x[g] != "pass" for x in eligible) for g in SEMANTIC_GATES
            }
            counts["review_methods"] = dict(Counter(x["review_method"] for x in evaluated))
            summary["configurations"][f"{revision}/{system}"] = counts
        summary["paired_comparison"][revision] = {
            key: exact_mcnemar(by_result["compliancegpt"], by_result["gemini"], key)
            for key in ("legacy_pass", "answer_content_pass")
        }
    if set(reviews) != used_reviews:
        raise ValueError("Review ledger contains missing, stale, or unused records")
    for path, digest in hashes.items():
        if sha256(root / path) != digest:
            raise ValueError(f"Input modified during evaluation: {path}")

    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "per_row_results.jsonl", results)
    flat = [
        {k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()}
        for row in results
    ]
    with (output / "per_row_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(flat)
    write_json(output / "summary.json", summary)
    experiment = f"{BASE}/answer_content_strict_pass"
    code_paths = [
        "src/answerer_comparison/answer_content_strict_pass.py",
        f"{experiment}/run_evaluation.py", f"{experiment}/README.md",
        "src/compliancegpt/generator/verifier/verifier.py",
    ]
    write_json(output / "manifest.json", {
        "rule_version": RULE_VERSION, "strict_pass_endpoint": "Answer-content extension",
        "source_snapshot": SOURCE_SNAPSHOT, "python_version": platform.python_version(),
        "input_sha256": hashes,
        "code_and_rubric_sha256": {p: sha256(root / p) for p in code_paths},
        "semantic_reviews_sha256": sha256(reviews_path),
        "legacy_configuration": {
            "strict_extras": False, "strict_verbatim": True, "strict_version": False,
            "org_profile": {}, "gold_resolution_policy": "unchanged per row",
            "generation_resolution_policy": "ASK",
        },
        "rows": len(results), "legacy_disagreements": 0,
        "output_sha256": {name: sha256(output / name) for name in ["per_row_results.csv", "per_row_results.jsonl", "summary.json"]},
    })
    lines = [
        "# Answer-content strict-pass results\n",
        "The strict-pass endpoint in this evaluation is Answer-content extension. Every legacy strict condition remains mandatory. This is a retrospective audit of saved outputs; models and labels were not changed or regenerated. Source-inspection judgments are not independently adjudicated.\n",
        "| Revision | System | Legacy strict pass | Answer-content strict pass | Nominal 95% Wilson interval |\n| --- | --- | ---: | ---: | ---: |",
    ]
    for revision in EXPECTED_N:
        for system in ("baseline", "compliancegpt", "gemini"):
            counts = summary["configurations"][f"{revision}/{system}"]
            old, new = counts["legacy_pass"], counts["answer_content_pass"]
            ci = new["wilson_95_ci"]
            lines.append(f"| {revision} | {system} | {old['count']}/{old['n']} ({old['rate']:.1%}) | {new['count']}/{new['n']} ({new['rate']:.1%}) | [{ci['lower']:.3f}, {ci['upper']:.3f}] |")
    lines.extend([
        "\n## Added requirements\n",
        "Exact source/window identity and full retained-parameter accounting are checked mechanically. Actual citation use, required body content, claim faithfulness and parameter meaning are assessed by versioned source inspection or a complete canonical-retention proof. Correct paraphrases can pass. Clarification value domains are not scored.\n",
        "## Count reconciliation\n",
        "| Revision / system | Legacy passes | Added failures or uncertain cases | Final passes |\n| --- | ---: | ---: | ---: |",
    ])
    for key, counts in summary["configurations"].items():
        old, new = counts["legacy_pass"]["count"], counts["answer_content_pass"]["count"]
        lines.append(f"| {key} | {old} | {old - new} | {new} |")
    lines.append("\nNew nonpassing IDs among previous passes:\n")
    for key, counts in summary["configurations"].items():
        ids = ", ".join("Q" + q for q in counts["new_failure_query_ids"]) or "none"
        lines.append(f"- {key}: {ids}")
    for key, counts in summary["configurations"].items():
        if counts["uncertain_eligible_rows"]:
            qids = ", ".join("Q" + q for q in counts["uncertain_eligible_rows"])
            lines.append(f"\n{key}: {qids} receives no strict credit. If all uncertain cases pass, the possible count is {counts['possible_answer_content_pass']['count']}/{counts['legacy_pass']['n']}. No row is dropped from the denominator.\n")
    lines.append("## Paired comparison\n")
    for revision in EXPECTED_N:
        pair = summary["paired_comparison"][revision]["answer_content_pass"]
        lines.append(f"{revision}: ComplianceGPT-only passes {pair['compliancegpt_only']}; Gemini-only passes {pair['gemini_only']}; exact two-sided McNemar p = {pair['two_sided_exact_p']:.6g}.\n")
    lines.extend([
        "These are unadjusted exploratory comparisons. A higher point estimate does not establish general or independently confirmed model superiority.\n",
        "## Reproduce\n",
        "```bash\npython experiments/answerer_comparison/answer_content_strict_pass/run_evaluation.py --output-dir /tmp/compliancegpt_answer_content\n```\n",
        "All ten input hashes, matched windows, all 408 historical outcomes, review fingerprints and exact failure excerpts are verified. Missing or stale reviews stop scoring.\n",
        "See [the full standard](../README.md), [the review ledger](../reviews.jsonl), and [three detailed examples](../EXAMPLES.md).\n",
    ])
    (output / "SUMMARY.md").write_text("\n".join(lines).rstrip() + "\n")
    print("revision,system,legacy,answer_content")
    for key, counts in summary["configurations"].items():
        print(key.replace("/", ",") + f",{counts['legacy_pass']['count']},{counts['answer_content_pass']['count']}")
    print(f"Legacy disagreements: 0; total rows: {len(results)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results_v1")
    parser.add_argument("--reviews", type=Path, default=Path(__file__).parent / "reviews.jsonl")
    parser.add_argument("--prepare", action="store_true", help="Prepare identity-free review surfaces without producing semantic scores")
    args = parser.parse_args()
    inputs, hashes = load_inputs(args.repo_root)
    if args.prepare:
        prepare_packet(inputs, args.output_dir)
    else:
        run(args.repo_root, args.output_dir, args.reviews, inputs, hashes)


if __name__ == "__main__":
    main()
