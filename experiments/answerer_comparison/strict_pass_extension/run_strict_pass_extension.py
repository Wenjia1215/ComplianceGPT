#!/usr/bin/env python3
"""Re-score frozen RQ2 outputs without generation, retrieval, or API calls."""

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
from answerer_comparison.strict_pass_extension import (  # noqa: E402
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
        "rule_version": RULE_VERSION, "source_snapshot": SOURCE_SNAPSHOT,
        "scope": "retrospective exploratory frozen-output re-evaluation",
        "review_boundary": "Source-inspection judgments are provisional, not independently adjudicated; full-retention certificates are sufficient proofs, not a required writing style.",
        "denominators": EXPECTED_N, "configurations": {}, "paired_comparison": {},
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
                    revision=revision, query_id=query_id, contract=contract, gold=gold[query_id],
                    records=records, window_ids=row["evidence_window_source_ids"].split("|"), reviews=reviews,
                )
                if result["legacy_pass"] != (row["verifier_pass"] == "True"):
                    raise ValueError(f"Legacy disagreement: {revision}/{system}/{query_id}")
                result["system"] = system
                result["question"] = row["question"]
                result["input_path"] = contract_path(revision, system)
                if result["review_method"] == "source_inspection":
                    used_reviews.add(result["review_id"])
                evaluated.append(result)
                results.append(result)
            if sum(x["legacy_pass"] for x in evaluated) != EXPECTED_LEGACY[revision][system]:
                raise ValueError("Legacy total changed")
            by_result[system] = {r["query_id"]: r for r in evaluated}
            n = len(evaluated)
            counts = {}
            for key in ("legacy_pass", "answer_content_pass", "extended_strict_pass", "possible_extended_pass"):
                count = sum(bool(x[key]) for x in evaluated)
                counts[key] = {"count": count, "n": n, "rate": count / n, "wilson_95_ci": wilson(count, n)}
            counts["new_failure_query_ids"] = [x["query_id"] for x in evaluated if x["legacy_pass"] and not x["extended_strict_pass"]]
            counts["answer_failure_query_ids"] = [x["query_id"] for x in evaluated if x["legacy_pass"] and not x["answer_content_pass"]]
            counts["clarification_failure_query_ids"] = [x["query_id"] for x in evaluated if x["legacy_pass"] and not x["clarification_domains"]]
            counts["uncertain_eligible_rows"] = [x["query_id"] for x in evaluated if x["legacy_pass"] and any(x[g] == "uncertain" for g in SEMANTIC_GATES)]
            counts["review_methods"] = dict(Counter(x["review_method"] for x in evaluated))
            summary["configurations"][f"{revision}/{system}"] = counts
        summary["paired_comparison"][revision] = {
            key: exact_mcnemar(by_result["compliancegpt"], by_result["gemini"], key)
            for key in ("legacy_pass", "answer_content_pass", "extended_strict_pass")
        }
    if set(reviews) != used_reviews:
        raise ValueError("Semantic review ledger contains missing, stale, or unused records")
    for path, digest in hashes.items():
        if sha256(root / path) != digest:
            raise ValueError(f"Input modified during evaluation: {path}")
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "per_row_results.jsonl", results)
    flat = []
    for row in results:
        flat.append({k: (json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v) for k, v in row.items()})
    fields = list(flat[0])
    with (output / "per_row_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(flat)
    write_json(output / "summary.json", summary)
    code_paths = [
        "src/answerer_comparison/strict_pass_extension.py",
        f"{BASE}/strict_pass_extension/run_strict_pass_extension.py",
        f"{BASE}/strict_pass_extension/STANDARD_V2.md",
        "src/compliancegpt/generator/verifier/verifier.py",
    ]
    write_json(output / "manifest.json", {
        "rule_version": RULE_VERSION, "source_snapshot": SOURCE_SNAPSHOT,
        "python_version": platform.python_version(), "input_sha256": hashes,
        "code_and_rubric_sha256": {p: sha256(root / p) for p in code_paths},
        "semantic_reviews_sha256": sha256(reviews_path),
        "legacy_configuration": {"strict_extras": False, "strict_verbatim": True, "strict_version": False, "org_profile": {}, "gold_resolution_policy": "unchanged per row", "generation_resolution_policy": "ASK"},
        "rows": len(results), "legacy_disagreements": 0,
        "output_sha256": {name: sha256(output / name) for name in ["per_row_results.csv", "per_row_results.jsonl", "summary.json"]},
    })
    text = [
        "# Strict-pass extension v2: completed frozen-output audit\n",
        "This is a retrospective exploratory re-evaluation. Historical scores, labels, model outputs and Runtime Verifier behavior remain unchanged. No generation or API calls were made. Semantic source-inspection judgments have not received independent expert adjudication.\n",
        "The final extension requires every old strict-pass condition plus exact provenance, complete retained-parameter/clarification accounting, actual citation use, required answer content, supported claims, preserved parameter meaning, and compatible clarification value domains. Correct paraphrases are accepted.\n",
        "| Revision | System | Legacy strict | Answer-content extension | Full extension, including clarification domains |\n| --- | --- | ---: | ---: | ---: |",
    ]
    for revision in EXPECTED_N:
        for system in ("baseline", "compliancegpt", "gemini"):
            counts = summary["configurations"][f"{revision}/{system}"]
            parts = [f"{counts[k]['count']}/{counts[k]['n']} ({counts[k]['rate']:.1%})" for k in ("legacy_pass", "answer_content_pass", "extended_strict_pass")]
            text.append(f"| {revision} | {system} | " + " | ".join(parts) + " |")
    text.append("\nThe full extension is the new strict-pass endpoint in this trial. The answer-content column separates realization errors from shared clarification-template errors; it is not substituted for the full score.\n")
    for key, counts in summary["configurations"].items():
        if counts["uncertain_eligible_rows"]:
            lower = counts["extended_strict_pass"]["count"]
            upper = counts["possible_extended_pass"]["count"]
            text.append(f"{key}: strict credited count {lower}; possible count if all uncertain cases pass {upper}. Uncertain cases remain in the denominator.\n")
    for revision in EXPECTED_N:
        pair = summary["paired_comparison"][revision]["extended_strict_pass"]
        text.append(f"{revision}: ComplianceGPT-only passes {pair['compliancegpt_only']}; Gemini-only passes {pair['gemini_only']}; exact two-sided McNemar p = {pair['two_sided_exact_p']:.6g}.\n")
    text.extend(["## New failures\n", "Each ID below previously passed the unchanged legacy endpoint. Overlapping failure categories count once.\n"])
    for revision in EXPECTED_N:
        for system in ("baseline", "compliancegpt", "gemini"):
            counts = summary["configurations"][f"{revision}/{system}"]
            text.append(f"- {revision}/{system}: " + ", ".join("Q" + q for q in counts["new_failure_query_ids"]))
            if counts["uncertain_eligible_rows"]:
                text.append("  Uncertain semantic cases receive no strict credit: " + ", ".join(counts["uncertain_eligible_rows"]))
    text.extend([
        "\n## Reproduction\n",
        "```bash\npython experiments/answerer_comparison/strict_pass_extension/run_strict_pass_extension.py --output-dir /tmp/compliancegpt_strict_v2\n```\n",
        "The script verifies all six frozen contract hashes, both canonical-source hashes, both gold hashes, matched per-question windows, all 408 legacy outcomes, review fingerprints and exact source excerpts. Missing/stale reviews stop scoring. No uncertain case is silently dropped from the denominator.\n",
        "The semantic ledger is `../reviews_v2.jsonl`; every failure cites the pinned answer and canonical evidence. Full source-retention certificates account for unchanged canonical assembly, but exact copying is not a requirement for other answers.\n",
        "## Interpretation boundary\n",
        "These counts concern the archived matched-window Qwen 4-bit and Gemini 3.5 Flash outputs. They do not measure the advisor's later prompt, another Gemini model, or an independently validated holdout task. The criteria were developed after examining these outputs. A changed ranking does not establish general model superiority, and a highest point estimate need not imply a statistically significant difference.\n",
    ])
    (output / "SUMMARY.md").write_text("\n".join(text).rstrip() + "\n")
    print("revision,system,legacy,answer_content,full_extension")
    for key, counts in summary["configurations"].items():
        print(key.replace("/", ",") + "," + ",".join(str(counts[k]["count"]) for k in ("legacy_pass", "answer_content_pass", "extended_strict_pass")))
    print("Legacy disagreements: 0; total rows:", len(results))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results_v2")
    parser.add_argument("--reviews", type=Path, default=Path(__file__).parent / "reviews_v2.jsonl")
    parser.add_argument("--prepare", action="store_true", help="Prepare identity-free review surfaces without producing semantic scores")
    args = parser.parse_args()
    inputs, hashes = load_inputs(args.repo_root)
    if args.prepare:
        prepare_packet(inputs, args.output_dir)
    else:
        run(args.repo_root, args.output_dir, args.reviews, inputs, hashes)


if __name__ == "__main__":
    main()
