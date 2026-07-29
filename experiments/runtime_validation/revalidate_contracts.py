# -*- coding: utf-8 -*-
"""Revalidate recorded answer artifacts with the gold-independent contract checker."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from compliancegpt.generator.verifier.verifier import (  # noqa: E402
    VERIFIER_PATCH_ID,
    verify_contract_validity,
)


RUNS: Tuple[Tuple[str, str, Path], ...] = (
    (
        "ComplianceGPT",
        "rev5",
        PROJECT_ROOT / "experiments/pipeline_runs/pipeline_rev5_contracts_20260312_150620.csv",
    ),
    (
        "ComplianceGPT",
        "rev4",
        PROJECT_ROOT / "experiments/pipeline_runs/pipeline_rev4_contracts_20260312_152654.csv",
    ),
    (
        "Generative baseline",
        "rev5",
        PROJECT_ROOT
        / "experiments/answerer_comparison/baseline_runs/generative_baseline_rev5_contracts_20260313_121821.csv",
    ),
    (
        "Generative baseline",
        "rev4",
        PROJECT_ROOT
        / "experiments/answerer_comparison/baseline_runs/generative_baseline_rev4_contracts_20260313_121821.csv",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_corpus(revision: str) -> Tuple[Path, Dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "data/ccs/nist800-53"
        / f"NIST_SP-800-53_{revision}_catalog.jsonl"
    )
    corpus: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            source_id = str(record.get("id", "")).strip()
            if source_id:
                corpus[source_id] = str(record.get("text", ""))
    return path, corpus


def read_contract_rows(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def validate_run(
    system: str,
    revision: str,
    source_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ccs_path, corpus = load_corpus(revision)
    source_hash = sha256(source_path)
    ccs_hash = sha256(ccs_path)
    results: List[Dict[str, Any]] = []
    error_counts: Counter[str] = Counter()

    for row in read_contract_rows(source_path):
        contract = json.loads(row["contract_json"])
        is_pass, errors = verify_contract_validity(
            contract,
            corpus=corpus,
            org_profile=None,
            strict_verbatim=True,
        )
        error_counts.update(errors)
        results.append({
            "system": system,
            "revision": revision,
            "query_id": str(row.get("query_id", "")),
            "runtime_structural_pass": bool(is_pass),
            "runtime_structural_errors": json.dumps(errors, ensure_ascii=True),
            "status": str(contract.get("status", "")),
            "evidence_span_count": len(contract.get("evidence_spans", []) or []),
            "source_contract_file": str(source_path.relative_to(PROJECT_ROOT)),
            "source_contract_sha256": source_hash,
            "ccs_file": str(ccs_path.relative_to(PROJECT_ROOT)),
            "ccs_sha256": ccs_hash,
            "verifier_patch_id": VERIFIER_PATCH_ID,
        })

    passed = sum(1 for row in results if row["runtime_structural_pass"])
    summary = {
        "system": system,
        "revision": revision,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "error_counts": dict(sorted(error_counts.items())),
        "source_contract_file": str(source_path.relative_to(PROJECT_ROOT)),
        "source_contract_sha256": source_hash,
        "ccs_file": str(ccs_path.relative_to(PROJECT_ROOT)),
        "ccs_sha256": ccs_hash,
        "verifier_patch_id": VERIFIER_PATCH_ID,
    }
    return results, summary


def output_stem(system: str, revision: str) -> str:
    normalized = system.lower().replace(" ", "_")
    return f"contract_validity_{normalized}_{revision}_20260712"


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: List[Dict[str, Any]] = []

    for system, revision, source_path in RUNS:
        results, summary = validate_run(system, revision, source_path)
        summaries.append(summary)
        output_path = output_dir / f"{output_stem(system, revision)}.csv"
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)

    summary_path = output_dir / "runtime_validation_summary_20260712.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "verifier_patch_id": VERIFIER_PATCH_ID,
                "gold_labels_used": False,
                "runs": summaries,
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


if __name__ == "__main__":
    main()
