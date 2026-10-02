#!/usr/bin/env python3
"""Score a frozen intra-annotator re-labeling file against original gold labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence


REV4_LABEL = "Revision 4"
REV5_LABEL = "Revision 5"
EXPECTED_SAMPLE_COMMITMENT = (
    "a6582b20ea6605395627dd0229981be6841ef76e55af022526ce773f71a686c0"
)
EXPECTED_SOURCE_SHA256 = {
    REV4_LABEL: "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2",
    REV5_LABEL: "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def value(row: Mapping[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return (row[name] or "").strip()
    raise KeyError(f"Missing all expected columns: {names}")


def normalize_control(raw: str) -> str:
    text = raw.strip().upper()
    match = re.fullmatch(r"([A-Z]+)-0*(\d+)(?:(?:\(|\.)0*(\d+)\)?)?", text)
    if not match:
        return text
    family, base, enhancement = match.groups()
    normalized = f"{family}-{int(base)}"
    if enhancement is not None:
        normalized += f"({int(enhancement)})"
    return normalized


def parse_id_set(raw: str) -> frozenset[str]:
    text = raw.strip()
    if not text or text.upper() == "NONE":
        return frozenset()
    return frozenset(part.strip().lower() for part in text.splitlines() if part.strip())


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def cohens_kappa(left: Sequence[str], right: Sequence[str]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Cohen's kappa requires two non-empty equal-length sequences")
    count = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / count
    left_counts = Counter(left)
    right_counts = Counter(right)
    categories = set(left_counts) | set(right_counts)
    expected = sum(
        (left_counts[category] / count) * (right_counts[category] / count)
        for category in categories
    )
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else float("nan")
    return (observed - expected) / (1.0 - expected)


def percent(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float("nan")


def canonical_sample_payload(rows: Iterable[Mapping[str, str]]) -> bytes:
    return "".join(
        f"{row['blind_id']}\t{row['revision']}\t{row['question']}\n" for row in rows
    ).encode("utf-8")


def verify_source(path: Path, revision: str) -> str:
    actual = sha256_file(path)
    expected = EXPECTED_SOURCE_SHA256[revision]
    if actual != expected:
        raise ValueError(
            f"{revision} source hash mismatch: expected {expected}, found {actual}"
        )
    return actual


def load_mapping(path: Path) -> tuple[list[dict[str, str]], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("mapping")
    if not isinstance(rows, list) or len(rows) != 30:
        raise ValueError("Mapping must contain exactly 30 rows")
    return rows, sha256_file(path)


def load_gold(
    rev4_path: Path, rev5_path: Path
) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, str]]:
    source_hashes = {
        REV4_LABEL: verify_source(rev4_path, REV4_LABEL),
        REV5_LABEL: verify_source(rev5_path, REV5_LABEL),
    }
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for revision, path in ((REV4_LABEL, rev4_path), (REV5_LABEL, rev5_path)):
        for row in read_csv(path):
            key = (revision, row["id"].strip())
            if key in indexed:
                raise ValueError(f"Duplicate gold key: {key}")
            indexed[key] = row
    return indexed, source_hashes


def prepare_comparisons(
    completed_path: Path,
    mapping_path: Path,
    rev4_path: Path,
    rev5_path: Path,
) -> tuple[list[dict[str, object]], dict[str, str]]:
    completed = read_csv(completed_path)
    if len(completed) != 30:
        raise ValueError(f"Completed label file must contain 30 rows, found {len(completed)}")
    mapping_rows, mapping_hash = load_mapping(mapping_path)
    mapping = {row["blind_id"]: row for row in mapping_rows}
    if len(mapping) != 30:
        raise ValueError("Mapping blind IDs are not unique")
    gold, source_hashes = load_gold(rev4_path, rev5_path)

    normalized_completed: list[dict[str, str]] = []
    comparisons: list[dict[str, object]] = []
    seen_blind_ids: set[str] = set()
    for completed_row in completed:
        blind_id = value(completed_row, "Blind ID", "blind_id")
        revision = value(completed_row, "NIST revision", "nist_revision")
        question = value(completed_row, "Question", "question")
        status = value(completed_row, "Status", "status")
        if blind_id in seen_blind_ids:
            raise ValueError(f"Duplicate completed blind ID: {blind_id}")
        seen_blind_ids.add(blind_id)
        if status and status != "Complete":
            raise ValueError(f"{blind_id} status is not Complete: {status}")
        mapped = mapping.get(blind_id)
        if mapped is None:
            raise ValueError(f"No mapping entry for {blind_id}")
        if mapped["nist_revision"] != revision:
            raise ValueError(f"Revision mismatch for {blind_id}")
        if mapped["question_sha256"] != sha256_text(question):
            raise ValueError(f"Question hash mismatch for {blind_id}")
        gold_row = gold[(revision, mapped["original_id"])]
        if sha256_text(gold_row["question"].strip()) != mapped["question_sha256"]:
            raise ValueError(f"Gold question does not match mapping for {blind_id}")

        retest_control = normalize_control(
            value(completed_row, "Governing control", "governing_control")
        )
        original_control = normalize_control(gold_row["control_id"])
        retest_clauses = parse_id_set(
            value(completed_row, "Expected clause IDs", "expected_clause_ids")
        )
        original_clauses = parse_id_set(gold_row["gold_control_path"])
        retest_odps = parse_id_set(
            value(completed_row, "Required ODP IDs", "required_odp_ids")
        )
        original_odps = parse_id_set(gold_row["odp_required"])

        comparison = {
            "blind_id": blind_id,
            "revision": revision,
            "original_id": mapped["original_id"],
            "question": question,
            "original_control": original_control,
            "retest_control": retest_control,
            "control_exact": original_control == retest_control,
            "original_clause_ids": original_clauses,
            "retest_clause_ids": retest_clauses,
            "clause_set_exact": original_clauses == retest_clauses,
            "clause_jaccard": jaccard(original_clauses, retest_clauses),
            "clauses_added_in_retest": retest_clauses - original_clauses,
            "clauses_missing_from_retest": original_clauses - retest_clauses,
            "original_odp_ids": original_odps,
            "retest_odp_ids": retest_odps,
            "odp_set_exact": original_odps == retest_odps,
            "odp_jaccard": jaccard(original_odps, retest_odps),
            "odps_added_in_retest": retest_odps - original_odps,
            "odps_missing_from_retest": original_odps - retest_odps,
            "notes": value(completed_row, "Notes", "notes"),
        }
        comparison["all_components_exact"] = (
            comparison["control_exact"]
            and comparison["clause_set_exact"]
            and comparison["odp_set_exact"]
        )
        comparisons.append(comparison)
        normalized_completed.append(
            {"blind_id": blind_id, "revision": revision, "question": question}
        )

    if seen_blind_ids != set(mapping):
        raise ValueError("Completed blind IDs do not match the revealed mapping")
    commitment = sha256_bytes(canonical_sample_payload(normalized_completed))
    if commitment != EXPECTED_SAMPLE_COMMITMENT:
        raise ValueError(
            f"Sample commitment mismatch: expected {EXPECTED_SAMPLE_COMMITMENT}, found {commitment}"
        )
    hashes = {
        "completed_csv_sha256": sha256_file(completed_path),
        "mapping_sha256": mapping_hash,
        "sample_commitment_sha256": commitment,
        "rev4_gold_sha256": source_hashes[REV4_LABEL],
        "rev5_gold_sha256": source_hashes[REV5_LABEL],
    }
    return comparisons, hashes


def summarize(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not rows:
        raise ValueError("Cannot summarize an empty comparison set")
    count = len(rows)
    control_exact = sum(bool(row["control_exact"]) for row in rows)
    clause_exact = sum(bool(row["clause_set_exact"]) for row in rows)
    odp_exact = sum(bool(row["odp_set_exact"]) for row in rows)
    all_exact = sum(bool(row["all_components_exact"]) for row in rows)
    return {
        "n": count,
        "control_exact_count": control_exact,
        "control_exact_rate": percent(control_exact, count),
        "control_cohens_kappa": cohens_kappa(
            [str(row["original_control"]) for row in rows],
            [str(row["retest_control"]) for row in rows],
        ),
        "clause_set_exact_count": clause_exact,
        "clause_set_exact_rate": percent(clause_exact, count),
        "clause_mean_jaccard": mean(float(row["clause_jaccard"]) for row in rows),
        "odp_set_exact_count": odp_exact,
        "odp_set_exact_rate": percent(odp_exact, count),
        "odp_mean_jaccard": mean(float(row["odp_jaccard"]) for row in rows),
        "all_components_exact_count": all_exact,
        "all_components_exact_rate": percent(all_exact, count),
        "rows_with_any_disagreement": count - all_exact,
    }


def fmt_ids(ids: object) -> str:
    values = sorted(str(item) for item in ids)
    return "\n".join(values) if values else "NONE"


def csv_value(value_to_write: object) -> object:
    if isinstance(value_to_write, (set, frozenset)):
        return fmt_ids(value_to_write)
    if isinstance(value_to_write, bool):
        return "TRUE" if value_to_write else "FALSE"
    return value_to_write


def write_results_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "blind_id",
        "revision",
        "original_id",
        "question",
        "original_control",
        "retest_control",
        "control_exact",
        "original_clause_ids",
        "retest_clause_ids",
        "clause_set_exact",
        "clause_jaccard",
        "clauses_added_in_retest",
        "clauses_missing_from_retest",
        "original_odp_ids",
        "retest_odp_ids",
        "odp_set_exact",
        "odp_jaccard",
        "odps_added_in_retest",
        "odps_missing_from_retest",
        "all_components_exact",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row[field]) for field in fields})


def metric_cell(summary: Mapping[str, object], prefix: str) -> str:
    count = int(summary[f"{prefix}_count"])
    total = int(summary["n"])
    rate = float(summary[f"{prefix}_rate"])
    return f"{count}/{total} ({rate:.1%})"


def write_report(
    path: Path,
    summaries: Mapping[str, Mapping[str, object]],
    rows: Sequence[Mapping[str, object]],
    hashes: Mapping[str, str],
    completed_xlsx_sha256: str,
    frozen_at: str,
) -> None:
    lines = [
        "# Intra-annotator test-retest agreement",
        "",
        "## Frozen inputs",
        "",
        f"- Completed workbook SHA-256: `{completed_xlsx_sha256}`",
        f"- Frozen at: {frozen_at}",
        f"- Canonical sample commitment: `{hashes['sample_commitment_sha256']}`",
        f"- Revealed mapping SHA-256: `{hashes['mapping_sha256']}`",
        "",
        "The original and second labels were compared only after the completed workbook was hashed. The analysis treats clause and ODP fields as sets, ignores order and surrounding whitespace, and treats `NONE` as an empty set. Jaccard similarity is 1.0 when both sets are empty.",
        "",
        "## Results",
        "",
        "| Metric | Overall | Revision 4 | Revision 5 |",
        "| --- | ---: | ---: | ---: |",
    ]
    overall = summaries["overall"]
    rev4 = summaries["revision_4"]
    rev5 = summaries["revision_5"]
    lines.extend(
        [
            f"| Control exact agreement | {metric_cell(overall, 'control_exact')} | {metric_cell(rev4, 'control_exact')} | {metric_cell(rev5, 'control_exact')} |",
            f"| Control Cohen's kappa | {overall['control_cohens_kappa']:.3f} | {rev4['control_cohens_kappa']:.3f} | {rev5['control_cohens_kappa']:.3f} |",
            f"| Clause-set exact agreement | {metric_cell(overall, 'clause_set_exact')} | {metric_cell(rev4, 'clause_set_exact')} | {metric_cell(rev5, 'clause_set_exact')} |",
            f"| Clause-set mean Jaccard | {overall['clause_mean_jaccard']:.3f} | {rev4['clause_mean_jaccard']:.3f} | {rev5['clause_mean_jaccard']:.3f} |",
            f"| ODP-set exact agreement | {metric_cell(overall, 'odp_set_exact')} | {metric_cell(rev4, 'odp_set_exact')} | {metric_cell(rev5, 'odp_set_exact')} |",
            f"| ODP-set mean Jaccard | {overall['odp_mean_jaccard']:.3f} | {rev4['odp_mean_jaccard']:.3f} | {rev5['odp_mean_jaccard']:.3f} |",
            f"| All three components exact | {metric_cell(overall, 'all_components_exact')} | {metric_cell(rev4, 'all_components_exact')} | {metric_cell(rev5, 'all_components_exact')} |",
            "",
            "## Row-level disagreement audit",
            "",
        ]
    )
    disagreements = [row for row in rows if not bool(row["all_components_exact"])]
    if not disagreements:
        lines.append("No row-level disagreements were observed.")
    else:
        lines.extend(
            [
                "| Blind ID | Rev. | Original row | Different components | Added in retest | Missing from retest |",
                "| --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for row in disagreements:
            components = []
            added = []
            missing = []
            if not row["control_exact"]:
                components.append("control")
                added.append(f"control: {row['retest_control']}")
                missing.append(f"control: {row['original_control']}")
            if not row["clause_set_exact"]:
                components.append("clauses")
                added_ids = fmt_ids(row["clauses_added_in_retest"]).replace("\n", ", ")
                missing_ids = fmt_ids(row["clauses_missing_from_retest"]).replace("\n", ", ")
                if added_ids != "NONE":
                    added.append(f"clauses: {added_ids}")
                if missing_ids != "NONE":
                    missing.append(f"clauses: {missing_ids}")
            if not row["odp_set_exact"]:
                components.append("ODPs")
                added_ids = fmt_ids(row["odps_added_in_retest"]).replace("\n", ", ")
                missing_ids = fmt_ids(row["odps_missing_from_retest"]).replace("\n", ", ")
                if added_ids != "NONE":
                    added.append(f"ODPs: {added_ids}")
                if missing_ids != "NONE":
                    missing.append(f"ODPs: {missing_ids}")
            lines.append(
                "| {blind_id} | {revision} | {original_id} | {components} | {added} | {missing} |".format(
                    blind_id=row["blind_id"],
                    revision=str(row["revision"]).replace("Revision ", ""),
                    original_id=row["original_id"],
                    components=", ".join(components),
                    added="; ".join(added) or "—",
                    missing="; ".join(missing) or "—",
                )
            )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This is an intra-annotator test-retest check of label stability. It is weaker than independent adjudication and does not establish that the labels are externally correct.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def json_ready(value_to_convert: object) -> object:
    if isinstance(value_to_convert, dict):
        return {key: json_ready(item) for key, item in value_to_convert.items()}
    if isinstance(value_to_convert, (list, tuple)):
        return [json_ready(item) for item in value_to_convert]
    if isinstance(value_to_convert, (set, frozenset)):
        return sorted(value_to_convert)
    if isinstance(value_to_convert, float) and math.isnan(value_to_convert):
        return None
    return value_to_convert


def run(args: argparse.Namespace) -> dict[str, object]:
    comparisons, hashes = prepare_comparisons(
        args.completed_csv,
        args.mapping_json,
        args.rev4_csv,
        args.rev5_csv,
    )
    completed_xlsx_hash = sha256_file(args.completed_xlsx)
    if completed_xlsx_hash != args.expected_completed_xlsx_sha256:
        raise ValueError(
            "Completed workbook hash mismatch: "
            f"expected {args.expected_completed_xlsx_sha256}, found {completed_xlsx_hash}"
        )
    summaries = {
        "overall": summarize(comparisons),
        "revision_4": summarize(
            [row for row in comparisons if row["revision"] == REV4_LABEL]
        ),
        "revision_5": summarize(
            [row for row in comparisons if row["revision"] == REV5_LABEL]
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "protocol_id": "compliancegpt-intra-annotator-retest-v1",
        "frozen_at": args.frozen_at,
        "completed_xlsx_sha256": completed_xlsx_hash,
        "hashes": hashes,
        "scoring_conventions": {
            "control": "Canonicalized control ID exact agreement",
            "clause_and_odp": "Set comparison after trimming whitespace and lowercasing IDs",
            "empty_set_jaccard": 1.0,
            "jaccard_aggregation": "Unweighted mean across rows",
        },
        "summary": summaries,
    }
    (args.output_dir / "agreement_summary.json").write_text(
        json.dumps(json_ready(summary_payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_results_csv(args.output_dir / "agreement_results.csv", comparisons)
    write_report(
        args.output_dir / "AGREEMENT_REPORT.md",
        summaries,
        comparisons,
        hashes,
        completed_xlsx_hash,
        args.frozen_at,
    )
    return summary_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completed-csv", type=Path, required=True)
    parser.add_argument("--completed-xlsx", type=Path, required=True)
    parser.add_argument("--expected-completed-xlsx-sha256", required=True)
    parser.add_argument("--mapping-json", type=Path, required=True)
    parser.add_argument("--rev4-csv", type=Path, required=True)
    parser.add_argument("--rev5-csv", type=Path, required=True)
    parser.add_argument("--frozen-at", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(json_ready(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
