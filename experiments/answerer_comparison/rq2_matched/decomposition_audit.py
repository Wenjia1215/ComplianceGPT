"""Recompute the Batch 2 strict-pass decomposition from frozen contracts."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


ARCHIVE = (
    Path(__file__).resolve().parent
    / "results_v3"
    / "compliancegpt_rq2_matched_v3.zip"
)


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def load_rows(
    archive: zipfile.ZipFile, revision: str, system: str
) -> list[dict[str, str]]:
    member = f"contracts/{revision}_{system}.csv"
    with archive.open(member) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8")))


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    full_coverage = [row for row in rows if as_bool(row["doc_full_recall"])]
    strict_pass = [row for row in rows if as_bool(row["verifier_pass"])]
    coverage_without_strict = [
        row
        for row in rows
        if as_bool(row["doc_full_recall"]) and not as_bool(row["verifier_pass"])
    ]
    strict_without_coverage = [
        row
        for row in rows
        if as_bool(row["verifier_pass"]) and not as_bool(row["doc_full_recall"])
    ]
    error_tags: Counter[str] = Counter()
    for row in coverage_without_strict:
        for error in filter(None, row["verifier_errors"].split("|")):
            error_tags[error.split(":", 1)[0]] += 1
    total = len(rows)
    return {
        "n": total,
        "full_gold_clause_coverage": {
            "count": len(full_coverage),
            "rate": len(full_coverage) / total,
        },
        "coverage_complete_but_fails_another_strict_predicate": {
            "count": len(coverage_without_strict),
            "rate": len(coverage_without_strict) / total,
            "error_tag_counts": dict(sorted(error_tags.items())),
        },
        "offline_strict_pass": {
            "count": len(strict_pass),
            "rate": len(strict_pass) / total,
        },
        "strict_pass_without_full_clause_coverage": len(strict_without_coverage),
    }


def main() -> None:
    report: dict[str, Any] = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for revision in ("rev5", "rev4"):
            report[revision] = {}
            for system in ("compliancegpt", "generative_baseline"):
                report[revision][system] = summarize(
                    load_rows(archive, revision, system)
                )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
