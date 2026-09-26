#!/usr/bin/env python3
"""Mutation-test the gold-independent Runtime Verifier on frozen contracts."""

from __future__ import annotations

import argparse
import bisect
import copy
import csv
import hashlib
import io
import json
import platform
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


RESULT_ID = "runtime_verifier_mutation_v1"
SCHEMA_VERSION = "compliancegpt-runtime-verifier-mutation-v1"
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
CONTRACT_MEMBERS = {
    "rev5": "contracts/rev5_compliancegpt.csv",
    "rev4": "contracts/rev4_compliancegpt.csv",
}
CCS_PATHS = {
    "rev5": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
    "rev4": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
}
OPERATORS = (
    "valid_active_id_swap",
    "span_character_change",
    "rev4_only_id_in_rev5",
    "drop_odp_entry",
    "flip_status",
)
OPERATOR_LABELS = {
    "valid_active_id_swap": "Valid active-revision ID swap",
    "span_character_change": "One-character span alteration",
    "rev4_only_id_in_rev5": "Rev. 4-only ID in Rev. 5",
    "drop_odp_entry": "Remove one ODP-list entry",
    "flip_status": "Status flip",
}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    default_archive = (
        repo_root
        / "experiments"
        / "answerer_comparison"
        / "rq2_matched"
        / "results_v3"
        / "compliancegpt_rq2_matched_v3.zip"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--frozen-archive", type=Path, default=default_archive)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def manifest_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )
            handle.write("\n")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_contract_rows(
    archive: zipfile.ZipFile,
    member: str,
) -> Tuple[List[Dict[str, str]], str]:
    payload = archive.read(member)
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"), newline="")))
    return [dict(row) for row in rows], sha256_bytes(payload)


def load_corpus(path: Path) -> Dict[str, str]:
    corpus: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            source_id = str(record.get("id", "") or "").strip()
            if not source_id:
                raise ValueError(f"Missing CCS id at {path}:{line_number}")
            if source_id in corpus:
                raise ValueError(f"Duplicate CCS id {source_id!r} in {path}")
            corpus[source_id] = str(record.get("text", "") or "")
    if not corpus:
        raise ValueError(f"Empty CCS: {path}")
    return corpus


def numeric_query_key(row: Mapping[str, Any]) -> Tuple[int, Any]:
    query_id = str(row.get("query_id", ""))
    return (0, int(query_id)) if query_id.isdigit() else (1, query_id)


def evidence_spans(contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    spans = contract.get("evidence_spans", []) or []
    if not isinstance(spans, list):
        return []
    return [span for span in spans if isinstance(span, dict)]


def next_different_id(current: str, sorted_ids: Sequence[str]) -> Optional[str]:
    if len(sorted_ids) < 2:
        return None
    start = bisect.bisect_right(sorted_ids, current)
    for offset in range(len(sorted_ids)):
        candidate = sorted_ids[(start + offset) % len(sorted_ids)]
        if candidate != current:
            return candidate
    return None


def rotate_ascii_alnum(character: str) -> str:
    if "a" <= character <= "y":
        return chr(ord(character) + 1)
    if character == "z":
        return "a"
    if "A" <= character <= "Y":
        return chr(ord(character) + 1)
    if character == "Z":
        return "A"
    if "0" <= character <= "8":
        return chr(ord(character) + 1)
    if character == "9":
        return "0"
    raise ValueError(f"Not an ASCII alphanumeric character: {character!r}")


def mutate_valid_active_id_swap(
    contract: Mapping[str, Any],
    *,
    active_ids: Sequence[str],
    **_: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    spans = evidence_spans(contract)
    if not spans:
        return None, {"reason": "no evidence span"}
    current = str(spans[0].get("source_id", "") or "").strip()
    replacement = next_different_id(current, active_ids)
    if not current or replacement is None:
        return None, {"reason": "no different active-revision identifier"}
    mutated = copy.deepcopy(dict(contract))
    mutated["evidence_spans"][0]["source_id"] = replacement
    return mutated, {
        "field": "evidence_spans[0].source_id",
        "original_value": current,
        "mutated_value": replacement,
    }


def mutate_span_character(
    contract: Mapping[str, Any],
    **_: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    spans = evidence_spans(contract)
    if not spans:
        return None, {"reason": "no evidence span"}
    span_text = str(spans[0].get("span_text", "") or "")
    match = re.search(r"[A-Za-z0-9]", span_text)
    if match is None:
        return None, {"reason": "first span has no ASCII alphanumeric character"}
    position = match.start()
    replacement = rotate_ascii_alnum(span_text[position])
    mutated_text = span_text[:position] + replacement + span_text[position + 1 :]
    mutated = copy.deepcopy(dict(contract))
    mutated["evidence_spans"][0]["span_text"] = mutated_text
    return mutated, {
        "field": f"evidence_spans[0].span_text[{position}]",
        "original_value": span_text[position],
        "mutated_value": replacement,
    }


def mutate_rev4_id_into_rev5(
    contract: Mapping[str, Any],
    *,
    revision: str,
    query_id: str,
    rev4_only_ids: Sequence[str],
    **_: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    if revision != "rev5":
        return None, {"reason": "operator is defined only for Rev. 5 contracts"}
    spans = evidence_spans(contract)
    if not spans:
        return None, {"reason": "no evidence span"}
    if not rev4_only_ids:
        return None, {"reason": "no Rev. 4-only identifiers available"}
    if query_id.isdigit():
        index = (int(query_id) - 1) % len(rev4_only_ids)
    else:
        index = int(sha256_bytes(query_id.encode("utf-8"))[:8], 16) % len(rev4_only_ids)
    replacement = rev4_only_ids[index]
    current = str(spans[0].get("source_id", "") or "").strip()
    mutated = copy.deepcopy(dict(contract))
    mutated["evidence_spans"][0]["source_id"] = replacement
    return mutated, {
        "field": "evidence_spans[0].source_id",
        "original_value": current,
        "mutated_value": replacement,
    }


def mutate_drop_odp_entry(
    contract: Mapping[str, Any],
    **_: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    raw_values = contract.get("odp_required_list", []) or []
    if isinstance(raw_values, list):
        values = list(raw_values)
    else:
        values = [str(raw_values)] if str(raw_values).strip() else []
    if not values:
        return None, {"reason": "empty odp_required_list"}
    mutated = copy.deepcopy(dict(contract))
    removed = str(values[-1])
    mutated["odp_required_list"] = values[:-1]
    return mutated, {
        "field": f"odp_required_list[{len(values) - 1}]",
        "original_value": removed,
        "mutated_value": "<removed>",
    }


def mutate_flip_status(
    contract: Mapping[str, Any],
    **_: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    current = str(contract.get("status", "") or "").strip().upper()
    replacements = {"OK": "PARAMS_REQUIRED", "PARAMS_REQUIRED": "OK"}
    if current not in replacements:
        return None, {"reason": f"status {current or '<empty>'} is outside flip domain"}
    replacement = replacements[current]
    mutated = copy.deepcopy(dict(contract))
    mutated["status"] = replacement
    return mutated, {
        "field": "status",
        "original_value": current,
        "mutated_value": replacement,
    }


MUTATORS: Dict[
    str,
    Callable[..., Tuple[Optional[Dict[str, Any]], Dict[str, str]]],
] = {
    "valid_active_id_swap": mutate_valid_active_id_swap,
    "span_character_change": mutate_span_character,
    "rev4_only_id_in_rev5": mutate_rev4_id_into_rev5,
    "drop_odp_entry": mutate_drop_odp_entry,
    "flip_status": mutate_flip_status,
}


def summarize(
    matrix_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    operator_summary: Dict[str, Any] = {}
    revision_summary: Dict[str, Any] = {}
    total_attempted = 0
    total_detected = 0

    for operator in OPERATORS:
        attempted = [row for row in matrix_rows if row["operator"] == operator and row["applicable"]]
        detected = [row for row in attempted if row["detected"]]
        tags = Counter(
            tag
            for row in detected
            for tag in str(row["error_tags"]).split("|")
            if tag
        )
        undetected = [row for row in attempted if not row["detected"]]
        operator_summary[operator] = {
            "label": OPERATOR_LABELS[operator],
            "attempted": len(attempted),
            "detected": len(detected),
            "detection_rate": len(detected) / len(attempted) if attempted else None,
            "trigger_tag_counts": dict(sorted(tags.items())),
            "undetected": len(undetected),
            "undetected_examples": [
                {
                    "revision": row["framework_version"],
                    "query_id": row["query_id"],
                    "field": row["mutated_field"],
                    "original_value": row["original_value"],
                    "mutated_value": row["mutated_value"],
                }
                for row in undetected[:10]
            ],
        }
        total_attempted += len(attempted)
        total_detected += len(detected)

    for revision in ("rev5", "rev4"):
        revision_summary[revision] = {}
        for operator in OPERATORS:
            attempted = [
                row
                for row in matrix_rows
                if row["framework_version"] == revision
                and row["operator"] == operator
                and row["applicable"]
            ]
            detected = [row for row in attempted if row["detected"]]
            revision_summary[revision][operator] = {
                "attempted": len(attempted),
                "detected": len(detected),
                "detection_rate": len(detected) / len(attempted) if attempted else None,
            }

    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "baseline_contracts": len(baseline_rows),
        "baseline_passed": sum(bool(row["runtime_pass"]) for row in baseline_rows),
        "planned_operator_cells": len(matrix_rows),
        "total_attempted_mutations": total_attempted,
        "total_detected_mutations": total_detected,
        "pooled_detection_rate": total_detected / total_attempted if total_attempted else None,
        "operators": operator_summary,
        "by_revision": revision_summary,
        "interpretation_boundary": (
            "Detection rates apply only to the five deterministic operators and the implemented "
            "gold-independent predicates. They do not measure evidence completeness, semantic or "
            "legal correctness, or general mutation adequacy."
        ),
    }


def markdown_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        f"# {RESULT_ID}",
        "",
        "## Baseline qualification",
        "",
        f"All {summary['baseline_passed']}/{summary['baseline_contracts']} frozen ComplianceGPT contracts passed the gold-independent Runtime Verifier before mutation.",
        "",
        "## Detection by operator",
        "",
        "| Operator | Attempted | Detected | Detection rate | Triggering predicates |",
        "|---|---:|---:|---:|---|",
    ]
    for operator in OPERATORS:
        item = summary["operators"][operator]
        tags = "; ".join(
            f"`{tag}` ({count})" for tag, count in item["trigger_tag_counts"].items()
        ) or "—"
        rate = item["detection_rate"]
        rate_text = "—" if rate is None else f"{rate:.4f}"
        lines.append(
            f"| {item['label']} | {item['attempted']} | {item['detected']} | {rate_text} | {tags} |"
        )

    lines.extend(
        [
            "",
            "## Revision breakdown",
            "",
            "| Revision | Operator | Attempted | Detected | Detection rate |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for revision in ("rev5", "rev4"):
        for operator in OPERATORS:
            item = summary["by_revision"][revision][operator]
            rate = item["detection_rate"]
            rate_text = "—" if rate is None else f"{rate:.4f}"
            lines.append(
                f"| {revision} | {OPERATOR_LABELS[operator]} | {item['attempted']} | {item['detected']} | {rate_text} |"
            )

    lines.extend(["", "## Undetected mutations", ""])
    for operator in OPERATORS:
        item = summary["operators"][operator]
        lines.append(f"- **{item['label']}:** {item['undetected']} undetected.")
        for example in item["undetected_examples"][:3]:
            lines.append(
                "  - "
                f"{example['revision']} query {example['query_id']}: "
                f"`{example['field']}` changed from `{example['original_value']}` "
                f"to `{example['mutated_value']}`."
            )

    lines.extend(
        [
            "",
            "## Scope",
            "",
            str(summary["interpretation_boundary"]),
            "",
            "The pooled rate is retained only as an artifact check; operator-specific rates are the reported results because the operators have different applicability and predicates.",
            "",
        ]
    )
    return "\n".join(lines)


def package_directory(directory: Path, archive_path: Path) -> None:
    if archive_path.exists():
        raise FileExistsError(archive_path)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(str(path.relative_to(directory)))
            info.date_time = (2026, 9, 25, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    frozen_archive = args.frozen_archive.resolve()
    output_dir = args.output_dir.resolve()
    archive_path = output_dir.with_suffix(".zip")

    if output_dir.exists() or archive_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite result identity: {output_dir} or {archive_path}"
        )
    if not frozen_archive.is_file():
        raise FileNotFoundError(frozen_archive)

    output_dir.mkdir(parents=True)
    sys.path.insert(0, str(repo_root / "src"))
    from compliancegpt.generator.verifier.verifier import verify_contract_validity  # type: ignore

    ccs_paths = {revision: repo_root / relative for revision, relative in CCS_PATHS.items()}
    corpora = {revision: load_corpus(path) for revision, path in ccs_paths.items()}
    active_ids = {revision: sorted(corpus) for revision, corpus in corpora.items()}
    rev4_only_ids = sorted(set(corpora["rev4"]) - set(corpora["rev5"]))
    if not rev4_only_ids:
        raise AssertionError("Expected at least one Rev. 4-only CCS identifier")

    frozen_hash_before = sha256_file(frozen_archive)
    contract_rows: Dict[str, List[Dict[str, str]]] = {}
    input_member_hashes: Dict[str, str] = {}
    with zipfile.ZipFile(frozen_archive, "r") as archive:
        for revision in ("rev5", "rev4"):
            rows, member_hash = read_contract_rows(archive, CONTRACT_MEMBERS[revision])
            if len(rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(
                    f"Unexpected {revision} contract count: {len(rows)}"
                )
            contract_rows[revision] = sorted(rows, key=numeric_query_key)
            input_member_hashes[CONTRACT_MEMBERS[revision]] = member_hash

    baseline_rows: List[Dict[str, Any]] = []
    matrix_rows: List[Dict[str, Any]] = []
    attempted_rows: List[Dict[str, Any]] = []

    for revision in ("rev5", "rev4"):
        corpus = corpora[revision]
        for frozen_row in contract_rows[revision]:
            query_id = str(frozen_row["query_id"])
            contract = json.loads(str(frozen_row.get("contract_json", "") or "{}"))
            baseline_pass, baseline_errors = verify_contract_validity(
                contract,
                corpus=corpus,
                strict_verbatim=True,
            )
            baseline_rows.append(
                {
                    "framework_version": revision,
                    "query_id": query_id,
                    "question": str(frozen_row.get("question", "") or ""),
                    "status": str(contract.get("status", "") or ""),
                    "evidence_span_count": len(evidence_spans(contract)),
                    "odp_required_count": len(contract.get("odp_required_list", []) or []),
                    "runtime_pass": baseline_pass,
                    "runtime_error_tags": "|".join(baseline_errors),
                    "contract_sha256": canonical_sha256(contract),
                }
            )
            if not baseline_pass:
                raise AssertionError(
                    f"Baseline failed for {revision} query {query_id}: {baseline_errors}"
                )

            for operator in OPERATORS:
                mutated, details = MUTATORS[operator](
                    contract,
                    revision=revision,
                    query_id=query_id,
                    active_ids=active_ids[revision],
                    rev4_only_ids=rev4_only_ids,
                )
                base_matrix = {
                    "framework_version": revision,
                    "query_id": query_id,
                    "operator": operator,
                    "operator_label": OPERATOR_LABELS[operator],
                    "question": str(frozen_row.get("question", "") or ""),
                    "baseline_contract_sha256": canonical_sha256(contract),
                }
                if mutated is None:
                    matrix_rows.append(
                        {
                            **base_matrix,
                            "applicable": False,
                            "nonapplicable_reason": details.get("reason", "not applicable"),
                            "detected": False,
                            "error_tags": "",
                            "mutated_field": "",
                            "original_value": "",
                            "mutated_value": "",
                            "mutated_contract_sha256": "",
                        }
                    )
                    continue

                if canonical_sha256(mutated) == canonical_sha256(contract):
                    raise AssertionError(
                        f"Mutation made no change: {revision} query {query_id} {operator}"
                    )
                mutation_pass, mutation_errors = verify_contract_validity(
                    mutated,
                    corpus=corpus,
                    strict_verbatim=True,
                )
                detected = not mutation_pass
                matrix_row = {
                    **base_matrix,
                    "applicable": True,
                    "nonapplicable_reason": "",
                    "detected": detected,
                    "error_tags": "|".join(mutation_errors),
                    "mutated_field": details["field"],
                    "original_value": details["original_value"],
                    "mutated_value": details["mutated_value"],
                    "mutated_contract_sha256": canonical_sha256(mutated),
                }
                matrix_rows.append(matrix_row)
                attempted_rows.append(
                    {
                        "result_id": RESULT_ID,
                        "framework_version": revision,
                        "query_id": query_id,
                        "operator": operator,
                        "operator_label": OPERATOR_LABELS[operator],
                        "question": str(frozen_row.get("question", "") or ""),
                        "mutated_field": details["field"],
                        "original_value": details["original_value"],
                        "mutated_value": details["mutated_value"],
                        "baseline_contract_sha256": canonical_sha256(contract),
                        "mutated_contract_sha256": canonical_sha256(mutated),
                        "detected": detected,
                        "runtime_pass": mutation_pass,
                        "error_tags": mutation_errors,
                        "mutated_contract": mutated,
                    }
                )

    if len(baseline_rows) != sum(EXPECTED_ROWS.values()):
        raise AssertionError(f"Unexpected baseline total: {len(baseline_rows)}")
    if len(matrix_rows) != sum(EXPECTED_ROWS.values()) * len(OPERATORS):
        raise AssertionError(f"Unexpected matrix total: {len(matrix_rows)}")

    summary = summarize(matrix_rows, baseline_rows)
    base_path = output_dir / "base_contract_validation.csv"
    matrix_path = output_dir / "mutation_matrix.csv"
    attempts_path = output_dir / "attempted_mutations.jsonl"
    summary_path = output_dir / "summary.json"
    summary_md_path = output_dir / "SUMMARY.md"

    write_csv(
        base_path,
        baseline_rows,
        (
            "framework_version",
            "query_id",
            "question",
            "status",
            "evidence_span_count",
            "odp_required_count",
            "runtime_pass",
            "runtime_error_tags",
            "contract_sha256",
        ),
    )
    write_csv(
        matrix_path,
        matrix_rows,
        (
            "framework_version",
            "query_id",
            "operator",
            "operator_label",
            "applicable",
            "nonapplicable_reason",
            "detected",
            "error_tags",
            "mutated_field",
            "original_value",
            "mutated_value",
            "baseline_contract_sha256",
            "mutated_contract_sha256",
            "question",
        ),
    )
    write_jsonl(attempts_path, attempted_rows)
    write_json(summary_path, summary)
    summary_md_path.write_text(markdown_summary(summary), encoding="utf-8")

    frozen_hash_after = sha256_file(frozen_archive)
    if frozen_hash_after != frozen_hash_before:
        raise AssertionError("Frozen RQ2 archive changed during mutation run")

    verifier_path = repo_root / "src/compliancegpt/generator/verifier/verifier.py"
    runner_path = Path(__file__).resolve()
    output_hashes = {
        path.name: sha256_file(path)
        for path in (base_path, matrix_path, attempts_path, summary_path, summary_md_path)
    }
    run_config = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "strict_verbatim": True,
        "gold_used": False,
        "expected_contracts": EXPECTED_ROWS,
        "operators": list(OPERATORS),
        "input_archive": {
            "path": manifest_path(frozen_archive, repo_root),
            "sha256_before": frozen_hash_before,
            "sha256_after": frozen_hash_after,
            "member_sha256": input_member_hashes,
        },
        "source_files": {
            manifest_path(runner_path, repo_root): sha256_file(runner_path),
            manifest_path(verifier_path, repo_root): sha256_file(verifier_path),
            **{
                manifest_path(path, repo_root): sha256_file(path)
                for path in ccs_paths.values()
            },
        },
        "ccs_counts": {revision: len(corpus) for revision, corpus in corpora.items()},
        "rev4_only_id_count": len(rev4_only_ids),
        "output_sha256": output_hashes,
    }
    write_json(output_dir / "run_config.json", run_config)
    package_directory(output_dir, archive_path)

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"result_dir={output_dir}")
    print(f"result_archive={archive_path}")
    print(f"result_archive_sha256={sha256_file(archive_path)}")


if __name__ == "__main__":
    main()
