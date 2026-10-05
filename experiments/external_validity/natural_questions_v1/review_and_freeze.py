#!/usr/bin/env python3
"""Validate human source/label review and freeze separate question/label files."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
REPO = FOLDER.parents[2]
CODE_PATHS = [
    "experiments/external_validity/natural_questions_v1/review_and_freeze.py",
    "experiments/external_validity/natural_questions_v1/run_natural_questions.py",
    "experiments/external_validity/natural_questions_v1/score_results.py",
    "experiments/external_validity/natural_questions_v1/requirements-colab.txt",
    "src/answerer_comparison/matched_window_runner.py",
    "experiments/answerer_comparison/rq2_matched/run_matched_rq2.py",
    "src/compliancegpt/retriever/retriever_s7.py",
    "src/compliancegpt/pipeline/pipeline.py",
    "src/compliancegpt/pipeline/evidence_window.py",
    "src/compliancegpt/pipeline/odp_policy.py",
    "src/compliancegpt/pipeline/profile_resolution.py",
    "src/compliancegpt/generator/generator.py",
    "src/compliancegpt/generator/citation_contract_80053.md",
    "src/compliancegpt/generator/verifier/verifier.py",
    "src/generative_answerer/pipeline.py",
    "src/generative_answerer/generator.py",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                 for row in rows))


def code_hashes(repo=REPO):
    return {p: sha(Path(repo) / p) for p in CODE_PATHS}


def load_review(path):
    """Read the flat Review worksheet or its exact CSV export; never run formulas."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    if path.suffix.lower() != ".xlsx":
        raise ValueError("Review must be the completed XLSX or its Review-sheet CSV export")
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(path) as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        sheet = next((x for x in workbook.findall("s:sheets/s:sheet", ns)
                      if x.attrib["name"] == "Review"), None)
        if sheet is None:
            raise ValueError("The workbook has no Review worksheet")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = next(x.attrib["Target"] for x in rels
                      if x.attrib["Id"] == sheet.attrib["{" + ns["r"] + "}id"])
        member = target.lstrip("/") if target.startswith("/") else "xl/" + target
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(si.itertext()) for si in
                       ET.fromstring(z.read("xl/sharedStrings.xml"))]
        def matrix_for(target_member, convenience_formula=False):
            matrix = []
            for row in ET.fromstring(z.read(target_member)).findall("s:sheetData/s:row", ns):
                cells = {}
                for c in row.findall("s:c", ns):
                    col = re.match(r"[A-Z]+", c.attrib["r"]).group()
                    idx = 0
                    for letter in col:
                        idx = idx * 26 + ord(letter) - ord("A") + 1
                    if c.find("s:f", ns) is not None:
                        if not convenience_formula or col != "O":
                            raise ValueError(f"Formula in a review/source input: {c.attrib['r']}")
                        continue
                    value = c.findtext("s:v", "", ns)
                    if c.attrib.get("t") == "s":
                        value = strings[int(value)]
                    elif c.attrib.get("t") == "inlineStr":
                        value = "".join(c.find("s:is", ns).itertext())
                    cells[idx - 1] = value
                if cells:
                    matrix.append([cells.get(i, "") for i in range(max(cells) + 1)])
            return matrix
        matrix = matrix_for(member, convenience_formula=True)
        header = matrix[0]
        rows = [dict(zip(header, row + [""] * (len(header) - len(row))))
                for row in matrix[1:] if any(row)]
        question_sheet = next((x for x in workbook.findall("s:sheets/s:sheet", ns)
                               if x.attrib["name"] == "Questions"), None)
        if question_sheet is None:
            raise ValueError("The source Questions worksheet is missing")
        target = next(x.attrib["Target"] for x in rels
                      if x.attrib["Id"] == question_sheet.attrib["{" + ns["r"] + "}id"])
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        questions = matrix_for(target)
        actual = {row[0]: hashlib.sha256(row[4].encode()).hexdigest() for row in questions[1:] if row and row[0]}
        expected = {row["query_id"]: row["question_sha256"] for row in rows}
        if actual != expected:
            raise ValueError("The workbook source question text changed. Recover/version the source captures before freezing.")
        return rows


def json_list(text, field, qid):
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{qid}: {field} needs a JSON list, including [] for an explicit empty list") from e
    if not isinstance(value, list):
        raise ValueError(f"{qid}: {field} must be a JSON list")
    return value


def validate_review(rows, candidates, corpora, registries, expected=20):
    """Source confirmation, review attestation and labels must all be present."""
    by_id = {q["query_id"]: q for q in candidates}
    if len(by_id) != len(candidates) or len(rows) != expected:
        raise ValueError("Candidate identities or review row count changed")
    row_ids = [row.get("query_id", "").strip() for row in rows]
    if len(set(row_ids)) != len(row_ids) or set(row_ids) != set(by_id):
        raise ValueError("Unknown or duplicated review row identities")
    labels, seen = [], set()
    for row in rows:
        qid = row.get("query_id", "").strip()
        if qid not in by_id or qid in seen:
            raise ValueError(f"Unknown or duplicated review row {qid!r}")
        seen.add(qid)
        q = by_id[qid]
        if row.get("question_sha256") != q["question_sha256"]:
            raise ValueError(f"{qid}: question wording changed; recover/review the source and version the candidate set")
        if row.get("decision", "").strip() != "reviewed":
            raise ValueError(f"{qid}: author review is pending (or a replacement source is needed)")
        if row.get("source_checked", "").strip() != "yes":
            raise ValueError(f"{qid}: confirm the original source, question completeness and posted date")
        reviewer = row.get("reviewer_name", "").strip()
        if not reviewer:
            raise ValueError(f"{qid}: reviewer name is missing")
        stamp = row.get("reviewed_at_utc", "").strip()
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
                raise ValueError()
        except ValueError as e:
            raise ValueError(f"{qid}: record an ISO-8601 UTC review timestamp, e.g. 2026-10-05T12:30:00Z") from e
        if parsed.date().isoformat() < q["source_retrieved_date_utc"]:
            raise ValueError(f"{qid}: review timestamp predates source collection")
        rev = row.get("framework_version", "").strip()
        if rev not in corpora:
            raise ValueError(f"{qid}: framework_version must be rev4 or rev5")
        scope = row.get("answerability", "").strip()
        if scope not in {"full", "partial", "outside", "ambiguous"}:
            raise ValueError(f"{qid}: choose full, partial, outside or ambiguous")
        controls = json_list(row.get("governing_controls"), "governing_controls", qid)
        groups = json_list(row.get("evidence_groups"), "evidence_groups", qid)
        if any(not isinstance(c, str) for c in controls) or len(set(controls)) != len(controls):
            raise ValueError(f"{qid}: control IDs must be distinct strings")
        inventory = corpora[rev]
        valid_controls = {r["control_id"] for r in inventory.values()}
        if set(controls) - valid_controls:
            raise ValueError(f"{qid}: unknown governing control ID")
        if scope in {"full", "partial"} and (not controls or not groups):
            raise ValueError(f"{qid}: answerable catalog duties need governing controls and evidence groups")
        if scope == "outside" and (controls or groups):
            raise ValueError(f"{qid}: outside requires explicit empty catalog label lists")
        for group in groups:
            if (not isinstance(group, list) or not group or any(not isinstance(s, str) for s in group)
                    or len(set(group)) != len(group)):
                raise ValueError(f"{qid}: each evidence group needs distinct acceptable clause IDs")
            for sid in group:
                if sid not in inventory or inventory[sid]["kind"] not in {"smt", "gdn"}:
                    raise ValueError(f"{qid}: unknown/non-evidence clause {sid!r}")
                if inventory[sid]["control_id"] not in controls:
                    raise ValueError(f"{qid}: evidence {sid} is outside the labeled controls")
        applicability = row.get("odp_applicability", "").strip()
        if applicability not in {"required", "not_required", "not_applicable", "uncertain"}:
            raise ValueError(f"{qid}: complete the ODP applicability field")
        raw_ids = row.get("required_odp_ids", "").strip()
        required = None if raw_ids == "null" else json_list(raw_ids, "required_odp_ids", qid)
        if applicability == "uncertain":
            if required is not None:
                raise ValueError(f"{qid}: uncertain ODP labels need null, not an empty negative label")
        else:
            if required is None or any(not isinstance(s, str) for s in required):
                raise ValueError(f"{qid}: determinate required ODP IDs need a JSON list")
            if len(set(required)) != len(required) or set(required) - set(registries[rev]):
                raise ValueError(f"{qid}: duplicated or unknown ODP ID")
            if applicability == "required" and not required:
                raise ValueError(f"{qid}: required ODPs cannot be empty")
            if applicability != "required" and required:
                raise ValueError(f"{qid}: only required ODP labels may list required IDs")
        if scope in {"outside", "ambiguous"} and applicability not in {"not_applicable", "uncertain"}:
            raise ValueError(f"{qid}: unresolved/outside scope cannot become a positive or negative ODP label")
        if applicability == "not_applicable" and scope in {"full", "partial"}:
            raise ValueError(f"{qid}: for answerable duties use required, not_required or uncertain")
        labels.append({"query_id": qid, "framework_version": rev, "answerability": scope,
                       "governing_controls": controls, "evidence_groups": groups,
                       "odp_applicability": applicability, "required_odp_ids": required,
                       "ambiguity_notes": row.get("ambiguity_notes", ""),
                       "reviewer_name": reviewer, "reviewed_at_utc": stamp,
                       "source_checked": True, "independent_expert_review": False})
    return sorted(labels, key=lambda q: q["query_id"])


def check_candidates(folder=FOLDER, repo=REPO):
    protocol = json.loads((folder / "protocol.json").read_text())
    if sha(folder / "candidate_questions.jsonl") != protocol["candidate_questions_sha256"]:
        raise ValueError("The candidate question file differs from the recorded preparation protocol")
    questions = read_jsonl(folder / "candidate_questions.jsonl")
    if len(questions) != protocol["expected_questions"]:
        raise ValueError("Candidate count changed")
    if len({q["query_id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate candidate ID")
    if len({q["source_url"] for q in questions}) != len(questions):
        raise ValueError("More than one candidate from the same source post")
    corpora, registries = {}, {}
    for rev, paths in protocol["inputs"].items():
        for entry in paths.values():
            if sha(repo / entry["path"]) != entry["sha256"]:
                raise ValueError(f"Canonical input changed: {entry['path']}")
        corpora[rev] = {r["id"]: r for r in read_jsonl(repo / paths["ccs"]["path"])}
        registries[rev] = json.loads((repo / paths["odp_registry"]["path"]).read_text())
    for q in questions:
        if q["question"] != q["original_title"] + "\n\n" + q["captured_original_post_body"]:
            raise ValueError(f"{q['query_id']}: original question capture changed")
        if hashlib.sha256(q["question"].encode()).hexdigest() != q["question_sha256"]:
            raise ValueError(f"{q['query_id']}: question digest mismatch")
        if not protocol["collection"]["posted_date_window"][0] <= q["source_posted_date"] <= protocol["collection"]["posted_date_window"][1]:
            raise ValueError(f"{q['query_id']}: source outside the collection window")
    return protocol, questions, corpora, registries


def validate_registration(folder=FOLDER, repo=REPO):
    protocol, candidates, corpora, registries = check_candidates(folder, repo)
    path = folder / "registration.json"
    if not path.exists():
        raise ValueError("Author source/label review is still pending. Complete the review packet, freeze it, and publish the registration before inference.")
    manifest = json.loads(path.read_text())
    for name, expected in manifest["file_sha256"].items():
        if sha(folder / name) != expected:
            raise ValueError(f"Registered file changed: {name}")
    if manifest["code_sha256"] != code_hashes(repo):
        raise ValueError("Executable code differs from the frozen registration")
    questions = read_jsonl(folder / "registered_questions.jsonl")
    labels = read_jsonl(folder / "registered_labels.jsonl")
    if len(questions) != protocol["expected_questions"] or len(labels) != len(questions):
        raise ValueError("Registered row count differs")
    checked = validate_review(read_jsonl(folder / "reviewed_labels.jsonl"), candidates,
                              corpora, registries, protocol["expected_questions"])
    if checked != labels:
        raise ValueError("Registered labels differ from the recorded human review")
    label_by_id = {r["query_id"]: r for r in labels}
    for candidate, question in zip(candidates, questions):
        expected = {"query_id": candidate["query_id"], "question": candidate["question"],
                    "question_sha256": candidate["question_sha256"],
                    "framework_version": label_by_id[candidate["query_id"]]["framework_version"],
                    "source_url": candidate["source_url"],
                    "source_posted_date": candidate["source_posted_date"]}
        if question != expected:
            raise ValueError("Registered questions differ from the reviewed original inputs")
    return protocol, questions, labels, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review", type=Path)
    p.add_argument("--check-candidates", action="store_true")
    args = p.parse_args()
    protocol, candidates, corpora, registries = check_candidates()
    if args.check_candidates:
        print(json.dumps({"candidates": len(candidates), "source_confirmation": "pending",
                          "author_labels": "pending", "inference_authorized_by_registration": False}))
        return
    if args.review is None:
        p.error("Provide --review completed.xlsx or --review completed.csv")
    if (FOLDER / "registration.json").exists():
        raise ValueError("A registration already exists. Use a new version rather than overwrite it")
    rows = load_review(args.review)
    labels = validate_review(rows, candidates, corpora, registries, protocol["expected_questions"])
    by_id = {r["query_id"]: r for r in labels}
    questions = [{"query_id": q["query_id"], "question": q["question"],
                  "question_sha256": q["question_sha256"],
                  "framework_version": by_id[q["query_id"]]["framework_version"],
                  "source_url": q["source_url"], "source_posted_date": q["source_posted_date"]}
                 for q in candidates]
    write_jsonl(FOLDER / "registered_questions.jsonl", questions)
    write_jsonl(FOLDER / "registered_labels.jsonl", labels)
    write_jsonl(FOLDER / "reviewed_labels.jsonl", rows)
    names = ["protocol.json", "candidate_questions.jsonl", "discovery_ledger.jsonl",
             "authority_records.jsonl", "registered_questions.jsonl", "registered_labels.jsonl",
             "reviewed_labels.jsonl"]
    write_json(FOLDER / "registration.json", {
        "schema_version": "compliancegpt-natural-question-registration-v1",
        "file_sha256": {name: sha(FOLDER / name) for name in names},
        "code_sha256": code_hashes(), "review_input_sha256": sha(args.review),
        "review_count": len(labels), "independent_expert_review": False,
        "status": "frozen_locally_requires_public_commit_before_inference"})
    validate_registration()
    print("Human review frozen. Publish this registration and pin the Colab checkout before inference.")


if __name__ == "__main__":
    main()
