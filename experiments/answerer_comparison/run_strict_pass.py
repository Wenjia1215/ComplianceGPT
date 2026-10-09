#!/usr/bin/env python3
"""Score the three saved RQ2 systems with the complete strict-pass standard."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
from answerer_comparison import strict_pass as scoring  # noqa: E402
from compliancegpt.generator.verifier.verifier import normalize_odp_id  # noqa: E402
from experiments.answerer_comparison.rq2_frontier_baseline import run_frontier_baseline as rev4_runner  # noqa: E402
from experiments.answerer_comparison.rq2_frontier_baseline_rev5 import run_frontier_baseline_rev5 as rev5_runner  # noqa: E402

SOURCE_SNAPSHOT = "72979835f1e05bae513468ca4074b4d43497da2c"
EXPECTED_N = {"rev5": 100, "rev4": 36}
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


SYSTEM_KEYS = {
    "baseline": "generative_baseline_4bit", "compliancegpt": "compliancegpt_4bit",
    "gemini": "generative_frontier_api",
}


def result_path(revision: str) -> Path:
    folder = "rq2_frontier_baseline_rev5" if revision == "rev5" else "rq2_frontier_baseline"
    return Path(BASE) / folder / "results_v1"


def run(output_root: Path) -> dict:
    inputs, hashes = load_inputs(REPO_ROOT)
    review_path = REPO_ROOT / BASE / "strict_pass_reviews.jsonl"
    reviews = scoring.load_reviews(review_path)
    reviewed_ids = set()
    for revision, (_, gold, systems) in inputs.items():
        for rows in systems.values():
            assessments = scoring.score_rows(revision=revision, rows=rows, gold_rows=gold, reviews=reviews)
            reviewed_ids.update(r["review_id"] for r in assessments.values() if r["review_method"] == "source_inspection")
    if reviewed_ids != set(reviews):
        raise ValueError("Review ledger contains missing, stale, or unused records")

    summaries = {}
    for revision, (_, gold, systems) in inputs.items():
        source = REPO_ROOT / result_path(revision)
        destination = output_root / result_path(revision)
        prior = json.loads((source / "summary.json").read_text(encoding="utf-8"))
        destination.mkdir(parents=True, exist_ok=True)
        if destination.resolve() != source.resolve():
            paths = [contract_path(revision, system) for system in systems]
            if revision == "rev4":
                paths.append(str(result_path(revision) / "references/rev4_generative_baseline_bf16.csv"))
            for relative in paths:
                target = output_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO_ROOT / relative, target)
        runner = rev5_runner if revision == "rev5" else rev4_runner
        summaries[revision] = runner.summarize_completed_run(
            output_dir=destination, gold_rows=gold, normalize_odp_id=normalize_odp_id,
            api_manifest=prior["api_provenance"],
        )
        output_names = ["summary.json", "SUMMARY.md", "strict_pass_rows.csv", "strict_pass_rows.jsonl"]
        code_paths = [
            "src/answerer_comparison/strict_pass.py", f"{BASE}/run_strict_pass.py",
            f"{BASE}/rq2_frontier_baseline/run_frontier_baseline.py",
            f"{BASE}/rq2_frontier_baseline_rev5/run_frontier_baseline_rev5.py",
            "src/answerer_comparison/README.md", "src/compliancegpt/generator/verifier/verifier.py",
        ]
        manifest = {
            "rule_version": scoring.RULE_VERSION, "source_snapshot": SOURCE_SNAPSHOT,
            "framework_version": revision, "systems": list(SYSTEM_KEYS.values()),
            "rows": EXPECTED_N[revision] * 3, "input_sha256": hashes,
            "code_and_rubric_sha256": {p: sha256(REPO_ROOT / p) for p in code_paths},
            "semantic_reviews_sha256": sha256(review_path), "recorded_contract_check_disagreements": 0,
            "contract_check_configuration": {
                "strict_extras": False, "strict_verbatim": True, "strict_version": False,
                "org_profile": {}, "gold_resolution_policy": "unchanged per row", "generation_resolution_policy": "ASK",
            },
            "assessment_boundary": scoring.ASSESSMENT_BOUNDARY,
            "output_sha256": {p: sha256(destination / p) for p in output_names},
        }
        write_json(destination / "manifests/strict_pass.json", manifest)
        original_manifest = json.loads((source / "manifests/outputs.json").read_text(encoding="utf-8"))
        current_files = {
            path: sha256(destination / path) if (destination / path).exists() else digest
            for path, digest in original_manifest["files"].items()
        }
        current_files.update({p: sha256(destination / p) for p in output_names + ["manifests/strict_pass.json", "README.md"] if (destination / p).exists()})
        write_json(destination / "manifests/outputs.json", {
            "schema_version": original_manifest["schema_version"], "result_id": original_manifest["result_id"],
            "scope": "Current materialized evaluation; byte-exact execution manifests remain in the saved ZIP archives.",
            "files": current_files, "files_sha256": scoring.canonical_sha256(current_files),
        })
    for relative, digest in hashes.items():
        if sha256(REPO_ROOT / relative) != digest:
            raise ValueError(f"Input modified during evaluation: {relative}")
    print("revision,system,strict_pass,n")
    for revision, summary in summaries.items():
        for system, key in SYSTEM_KEYS.items():
            metric = summary["configurations"][key]["strict_pass"]
            print(f"{revision},{system},{metric['count']},{metric['n']}")
    print("408 saved outputs assessed; recorded contract-check disagreements: 0")
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT,
                        help="Write the canonical result paths under this directory (default: repository)")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()

