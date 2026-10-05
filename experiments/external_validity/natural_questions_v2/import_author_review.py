#!/usr/bin/env python3
"""Validate a returned author workbook and archive its descriptive judgments.

This import is independent of the immutable automatic scoring outputs. It uses
only Python's standard library and never evaluates workbook formulas.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import posixpath
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path


STUDY = Path(__file__).resolve().parent
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
FIELDS = ["query_id", "system", "scope_appropriate", "responsive_to_entire_question",
          "unsupported_implementation_or_legal_claim", "reviewer", "notes"]
JUDGMENTS = FIELDS[2:5]
SYSTEMS = ("compliancegpt", "generative_baseline")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def workbook_sheets(path: Path) -> dict[str, dict[int, dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(element.itertext()) for element in
                      ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        relationships = {element.attrib["Id"]: element.attrib["Target"] for element in
                         ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", NS):
            target = relationships[sheet.attrib[f"{{{REL_NS}}}id"]]
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            rows = {}
            for row in ET.fromstring(archive.read(target)).findall("m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value = cell.find("m:v", NS)
                    text = value.text or "" if value is not None else ""
                    if cell.attrib.get("t") == "s":
                        text = shared[int(text)]
                    elif cell.attrib.get("t") == "inlineStr":
                        text = "".join(cell.find("m:is", NS).itertext())
                    # Only displayed values are read. Cached completion formulas
                    # are deliberately not used to determine review completion.
                    cells[cell.attrib["r"].rstrip("0123456789")] = text
                rows[int(row.attrib["r"])] = cells
            sheets[sheet.attrib["name"]] = rows
    return sheets


def validate_review(sheets: dict) -> tuple[list[dict], dict]:
    if set(sheets) != {"Author review", "Frozen questions"}:
        raise ValueError("Unexpected workbook sheet inventory")
    questions = jsonl(STUDY / "registered_questions.jsonl")
    labels = {row["query_id"]: row for row in jsonl(STUDY / "registered_labels.jsonl")}
    outcomes = jsonl(STUDY / "results_v1/per_question_outcomes.jsonl")
    statuses = {(row["query_id"], row["system"]): row["status"] for row in outcomes}
    expected_pairs = [(question["query_id"], system) for question in questions for system in SYSTEMS]
    if len(expected_pairs) != 40 or len(statuses) != 40:
        raise ValueError("Registered pairing is not the expected 20 questions by two systems")
    expected_header = ["Query ID", "System", "Within scope?", "Answers whole question?",
                       "Unsupported implementation/legal claim?", "Reviewer", "Notes",
                       "Review state", "Recorded runtime status"]
    if [sheets["Author review"].get(9, {}).get(column, "") for column in "ABCDEFGHI"] != expected_header:
        raise ValueError("Author review headers changed")
    populated = [(number, cells) for number, cells in sorted(sheets["Author review"].items())
                 if number >= 10 and any(cells.get(column, "") for column in "ABCDEFGI")]
    if len(populated) != 40:
        raise ValueError("Expected exactly 40 populated author-review rows")
    rows = []
    for (number, cells), pair in zip(populated, expected_pairs):
        if (cells.get("A"), cells.get("B")) != pair:
            raise ValueError(f"Missing, duplicate, altered, or reordered pairing at workbook row {number}")
        if cells.get("I") != statuses[pair]:
            raise ValueError(f"Recorded runtime status changed at workbook row {number}")
        row = dict(zip(FIELDS, (cells.get(column, "") for column in "ABCDEFG")))
        for field in JUDGMENTS:
            if row[field] not in {"yes", "no", "uncertain"}:
                raise ValueError(f"Invalid or missing judgment {field} at row {number}")
        if not row["reviewer"].strip() or not row["notes"].strip():
            raise ValueError(f"Reviewer or explanatory notes missing at row {number}")
        rows.append(row)
    frozen = [(number, cells) for number, cells in sorted(sheets["Frozen questions"].items())
              if number >= 5 and any(cells.get(column, "") for column in "ABCDEFG")]
    if len(frozen) != 20:
        raise ValueError("Frozen question sheet does not contain exactly 20 references")
    for (number, cells), question in zip(frozen, questions):
        label = labels[question["query_id"]]
        expected = {"A": question["query_id"], "B": question["question"].split("\n", 1)[0],
                    "C": label["answerability"], "D": label["odp_applicability"],
                    "E": ", ".join(label["governing_controls"]), "G": question["source_url"]}
        for column, value in expected.items():
            if cells.get(column) != value:
                raise ValueError(f"Frozen question reference changed at row {number}, column {column}")
        if json.loads(cells.get("F", "null")) != label["evidence_groups"]:
            raise ValueError(f"Frozen evidence groups changed at row {number}")
    return rows, {"expected_review_rows": 40, "validated_review_rows": len(rows),
                  "validated_frozen_questions": len(frozen), "runtime_statuses_preserved": True,
                  "pairing_and_order_preserved": True, "judgments_checked_directly": True,
                  "cached_completion_formulas_used": False}


def summarize(rows: list[dict], validation: dict, workbook: Path) -> dict:
    counts = {}
    for system in SYSTEMS:
        system_rows = [row for row in rows if row["system"] == system]
        counts[system] = {field: {value: Counter(row[field] for row in system_rows)[value]
                                  for value in ("yes", "no", "uncertain")} for field in JUDGMENTS}
    return {"result_id": "natural_questions_v2", "record_id": "author_post_run_review_v1",
            "author_post_run_review_complete": True, "technical_run_complete": True,
            "independent_correctness_validated": False,
            "design": "Single-author, unblinded post-run descriptive review; companion audit observations were available.",
            "reviewer_names": sorted({row["reviewer"] for row in rows}),
            "denominator_per_system": 20, "validation": validation, "systems": counts,
            "uncertain_judgments": [{"query_id": row["query_id"], "system": row["system"],
                                     "field": field, "notes": row["notes"]} for row in rows
                                    for field in JUDGMENTS if row[field] == "uncertain"],
            "interpretation": ["All yes/no/uncertain values are retained without imputation.",
                               "Responsiveness and unsupported-claim judgments are distinct; neither is an independent correctness endpoint.",
                               "No inferential comparison, composite correctness score, or new gold label is introduced.",
                               "Original automatic scoring files, blank review template, contracts and run archive are unchanged."],
            "inputs": {"workbook": {"file": workbook.name, "sha256": digest(workbook)},
                       **{name: {"sha256": digest(STUDY / name)} for name in
                          ("registered_questions.jsonl", "registered_labels.jsonl", "protocol.json",
                           "results_v1/per_question_outcomes.jsonl", "results_v1/summary.json")}}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    rows, validation = validate_review(workbook_sheets(args.workbook))
    summary = summarize(rows, validation, args.workbook)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.workbook.resolve() != (args.output_dir / args.workbook.name).resolve():
        shutil.copyfile(args.workbook, args.output_dir / args.workbook.name)
    with (args.output_dir / "author_post_run_review.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": validation, "systems": summary["systems"],
                      "uncertain_judgments": len(summary["uncertain_judgments"]),
                      "independent_correctness_validated": False}, indent=2))


if __name__ == "__main__":
    main()
