#!/usr/bin/env python3
"""Regenerate the ErrorBank category analysis from recorded S1--S7 outputs.

The ErrorBank reuses question identifiers across NIST revisions.  Revision and
question_id therefore form the analysis key; joining on question_id alone is
ambiguous and can silently discard the hand-assigned failure categories.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


SYSTEM_OUTPUT_DIRS = {
    "S1": "system_1_bm25",
    "S2": "system_2_dense",
    "S3": "system_3_rewrite_only",
    "S4": "system_4_qur_rrf",
    "S5": "system_5_hybrid_rrf",
    "S6": "system_6_hybrid_rerank",
    "S7": "system_7_compliance_gpt",
}


def normalize_version(value: object) -> str:
    text = str(value).strip().lower().replace(".", "")
    match = re.fullmatch(r"(?:revision|rev|r)?\s*([45])", text)
    if not match:
        raise ValueError(f"Unsupported ErrorBank version: {value!r}")
    return f"rev{match.group(1)}"


def normalize_question_id(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="raise")
    if not (numeric % 1 == 0).all():
        raise ValueError("question_id must contain integers only")
    return numeric.astype("int64")


def reciprocal_rank_at_10(rank: object) -> float:
    if pd.isna(rank):
        return 0.0
    rank_value = int(rank)
    return 1.0 / rank_value if 1 <= rank_value <= 10 else 0.0


def read_labels(path: Path) -> pd.DataFrame:
    labels = pd.read_csv(path)
    required = {"version", "question_id", "question", "gold_control_id", "failure_category"}
    missing = sorted(required.difference(labels.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")

    labels = labels[list(required)].copy()
    labels["version"] = labels["version"].map(normalize_version)
    labels["question_id"] = normalize_question_id(labels["question_id"])
    labels["failure_category"] = labels["failure_category"].astype("string").str.strip()

    if labels["failure_category"].isna().any() or labels["failure_category"].eq("").any():
        raise ValueError("Every ErrorBank row must have a non-empty failure_category")
    if labels.duplicated(["version", "question_id"]).any():
        duplicates = labels.loc[
            labels.duplicated(["version", "question_id"], keep=False),
            ["version", "question_id"],
        ]
        raise ValueError(f"Duplicate ErrorBank keys:\n{duplicates.to_string(index=False)}")
    return labels.sort_values(["version", "question_id"]).reset_index(drop=True)


def find_result_file(output_root: Path, system: str, version: str) -> Path:
    directory = output_root / SYSTEM_OUTPUT_DIRS[system]
    matches = sorted(directory.glob(f"{system}_*_error_bank_{version}_results.csv"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one {system} {version} ErrorBank result in {directory}; found {matches}"
        )
    return matches[0]


def read_system_results(output_root: Path, system: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for version in ("rev4", "rev5"):
        path = find_result_file(output_root, system, version)
        frame = pd.read_csv(path)
        required = {"question_id", "question", "gold_control_id", "rank"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"{path} is missing columns: {missing}")
        frame = frame[list(required)].copy()
        frame.insert(0, "version", version)
        frame["question_id"] = normalize_question_id(frame["question_id"])
        frame[f"{system}_rank"] = pd.to_numeric(frame.pop("rank"), errors="coerce")
        frame[f"{system}_RR@10"] = frame[f"{system}_rank"].map(reciprocal_rank_at_10)
        frame = frame.rename(
            columns={
                "question": f"{system}_question",
                "gold_control_id": f"{system}_gold_control_id",
            }
        )
        frames.append(frame)

    results = pd.concat(frames, ignore_index=True)
    if results.duplicated(["version", "question_id"]).any():
        raise ValueError(f"{system} results contain duplicate revision/question keys")
    return results


def validate_identity(merged: pd.DataFrame, system: str) -> None:
    missing = merged[f"{system}_rank"].isna()
    if missing.any():
        keys = merged.loc[missing, ["version", "question_id"]]
        raise ValueError(f"{system} has no results for:\n{keys.to_string(index=False)}")

    source_questions = merged["question"].astype(str).str.strip()
    result_questions = merged[f"{system}_question"].astype(str).str.strip()
    source_controls = merged["gold_control_id"].astype(str).str.strip().str.upper()
    result_controls = merged[f"{system}_gold_control_id"].astype(str).str.strip().str.upper()
    mismatch = source_questions.ne(result_questions) | source_controls.ne(result_controls)
    if mismatch.any():
        keys = merged.loc[mismatch, ["version", "question_id"]]
        raise ValueError(f"{system} identity mismatch for:\n{keys.to_string(index=False)}")


def markdown_table(frame: pd.DataFrame, decimals: int = 4) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include="number").columns:
        if column == "N":
            display[column] = display[column].map(lambda value: str(int(value)))
        else:
            display[column] = display[column].map(lambda value: f"{value:.{decimals}f}")
    headers = [str(column) for column in display.columns]
    rows = [[str(value) for value in row] for row in display.itertuples(index=False, name=None)]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def run(repo_root: Path) -> None:
    labels_path = repo_root / "data/error_bank/error_bank_v1.csv"
    output_root = repo_root / "experiments/retriever_ablation/ablation_outputs"
    report_dir = repo_root / "experiments/retriever_ablation/error_analysis/generated_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    merged = read_labels(labels_path)
    expected_rows = len(merged)
    for system in SYSTEM_OUTPUT_DIRS:
        system_results = read_system_results(output_root, system)
        merged = merged.merge(
            system_results,
            on=["version", "question_id"],
            how="left",
            validate="one_to_one",
        )
        if len(merged) != expected_rows:
            raise AssertionError("Merge changed the number of ErrorBank rows")
        validate_identity(merged, system)
        merged = merged.drop(columns=[f"{system}_question", f"{system}_gold_control_id"])

    rr_columns = [f"{system}_RR@10" for system in SYSTEM_OUTPUT_DIRS]
    pivot = (
        merged.groupby("failure_category", sort=True)
        .agg(N=("question_id", "size"), **{column: (column, "mean") for column in rr_columns})
        .reset_index()
    )
    pivot = pivot.rename(columns={column: column.replace("_RR@10", " MRR@10") for column in rr_columns})

    if int(pivot["N"].sum()) != expected_rows:
        raise AssertionError("Category counts do not sum to the ErrorBank size")
    if expected_rows != 37:
        raise AssertionError(f"Expected the recorded 37-row ErrorBank; found {expected_rows}")

    merged.to_csv(report_dir / "merged_results_data.csv", index=False, float_format="%.6f")
    pivot.to_csv(report_dir / "pivot_table.csv", index=False, float_format="%.4f")
    (report_dir / "pivot_table.md").write_text(markdown_table(pivot), encoding="utf-8")

    print(f"Validated {expected_rows} ErrorBank rows across {len(SYSTEM_OUTPUT_DIRS)} systems.")
    print(pivot.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"Wrote reports to {report_dir}")


def main() -> None:
    default_repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root)
    args = parser.parse_args()
    run(args.repo_root.resolve())


if __name__ == "__main__":
    main()
