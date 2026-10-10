#!/usr/bin/env python3
"""Apply strict-pass-v1 to the immutable original no-selector contracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from answerer_comparison import strict_pass as scoring

RESULT_ID = "rq2_no_selector_strict_pass_v1"
INPUT_SHA256 = {
    "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl": "71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08",
    "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv": "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5",
    "experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/references/rev5_generative_baseline_4bit.csv": "85a3e52b75b283a3fda6c50ae59d8dde4e59748ada7d58c5b88ae8c5c8f2cb63",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev5_no_selector.csv": "606024e83dacdabac8e0dcbe7bbd37aa61d7a9823d23341b3de6d1d58fcfff3d",
    "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl": "500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726",
    "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv": "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2",
    "experiments/answerer_comparison/rq2_frontier_baseline/results_v1/references/rev4_generative_baseline_4bit.csv": "cf891ddd0710125e5d37b43913166f0e7cef50426605133d87915229a90f53b5",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev4_no_selector.csv": "af05e97e7c0078a1f576700922ca292331bc778db4d9948337b38d6364be7602",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path, id_field: str = "query_id") -> dict[str, dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {str(row[id_field]): row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"Duplicate question IDs: {path}")
    return by_id


def run(output_dir: Path) -> None:
    if output_dir.exists():
        raise ValueError("Use a new output directory to preserve earlier assessments")
    for relative, expected in INPUT_SHA256.items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Frozen input changed: {relative}")
    if scoring.RULE_VERSION != "strict-pass-v1":
        raise ValueError("This audit requires the versioned strict-pass-v1 scorer")

    assessments = []
    revisions = {}
    for revision, n, folder in (
        ("rev5", 100, "rq2_frontier_baseline_rev5"),
        ("rev4", 36, "rq2_frontier_baseline"),
    ):
        base = ROOT / "experiments/answerer_comparison"
        rows = csv_rows(base / f"rq2_no_selector/results_v1/contracts/{revision}_no_selector.csv")
        references = csv_rows(base / f"{folder}/results_v1/references/{revision}_generative_baseline_4bit.csv")
        gold = csv_rows(ROOT / f"data/gold_standard_datasets/nist800-53/nist_sp800-53_{revision}_gold-set_{n}q.csv", id_field="id")
        if len(rows) != n or set(rows) != set(gold) or set(rows) != set(references):
            raise ValueError(f"Question sets differ: {revision}")
        records = {}
        for line in (ROOT / f"data/ccs/nist800-53/NIST_SP-800-53_{revision}_catalog.jsonl").read_text().splitlines():
            record = json.loads(line)
            if record["id"] in records:
                raise ValueError(f"Duplicate canonical source: {record['id']}")
            records[record["id"]] = record
        current = []
        for qid in sorted(rows, key=int):
            row, reference = rows[qid], references[qid]
            for field in ("question", "context_sha256", "evidence_window_sha256"):
                if row[field] != reference[field]:
                    raise ValueError(f"Frozen matched input differs: {revision}/{qid}/{field}")
            result = scoring.evaluate_contract(
                revision=revision, query_id=qid,
                contract=json.loads(row["contract_json"]), gold=gold[qid],
                records=records,
                window_ids=reference["evidence_window_source_ids"].split("|"),
                reviews={},
            )
            legacy = row["offline_strict_pass"].lower() == "true"
            if result["contract_checks_pass"] != legacy:
                raise ValueError(f"Recorded contract decision differs: {revision}/{qid}")
            result.update(system="original_no_selector", legacy_contract_pass=legacy)
            current.append(result)
        revisions[revision] = {
            "n": n,
            "legacy_contract_pass": sum(row["legacy_contract_pass"] for row in current),
            "strict_pass": sum(row["strict_pass"] for row in current),
            "legacy_passes_failing_parameter_accounting": sum(
                row["legacy_contract_pass"] and not row["complete_parameter_accounting"] for row in current
            ),
            "assessment_methods": dict(sorted(Counter(row["review_method"] for row in current).items())),
        }
        assessments.extend(current)

    code = {
        relative: digest(ROOT / relative) for relative in (
            "tools/audit_no_selector_strict_pass.py",
            "src/answerer_comparison/strict_pass.py",
            "src/compliancegpt/generator/verifier/verifier.py",
        )
    }
    summary = {
        "result_id": RESULT_ID, "rule_version": scoring.RULE_VERSION,
        "source_condition": "rq2_no_selector_v1; original saved contracts",
        "revisions": revisions, "input_sha256": INPUT_SHA256, "code_sha256": code,
        "boundary": "Retrospective assessment; no new model inference, retrieval, request repair, or human semantic judgment. Eligible bodies use the existing complete-retention proof. Gold labels remain author-defined.",
    }
    output_dir.mkdir(parents=True)
    (output_dir / "strict_pass_rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in assessments), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    files = {name: digest(output_dir / name) for name in ("strict_pass_rows.jsonl", "summary.json")}
    (output_dir / "FILES_SHA256.json").write_text(json.dumps(files, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    for relative, expected in INPUT_SHA256.items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Input modified during scoring: {relative}")
    print(json.dumps(revisions, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir.resolve())
