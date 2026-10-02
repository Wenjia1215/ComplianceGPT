#!/usr/bin/env python3
"""Prepare the frozen 30-row intra-annotator re-labeling sample.

The sampler is deterministic and label-blind. It ranks rows using only a
private seed, the NIST revision, and the original row identifier. Gold labels,
ODP status, system outputs, and evaluation outcomes never enter selection.

The private seed and generated mapping are intentionally withheld until the
second labeling file has been completed and cryptographically frozen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


PROTOCOL_ID = "compliancegpt-intra-annotator-retest-v1"
ALGORITHM_VERSION = "sha256-stratified-ranking-v1"
REV4_LABEL = "Revision 4"
REV5_LABEL = "Revision 5"
REV4_SAMPLE_SIZE = 8
REV5_SAMPLE_SIZE = 22

EXPECTED_SOURCE_SHA256 = {
    REV4_LABEL: "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2",
    REV5_LABEL: "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5",
}

BLINDED_COLUMNS = (
    "blind_id",
    "nist_revision",
    "question",
    "governing_control",
    "expected_clause_ids",
    "required_odp_ids",
    "notes",
)

FORBIDDEN_BLINDED_COLUMNS = {
    "id",
    "control_id",
    "answer",
    "gold_exact_citation",
    "gold_control_path",
    "odp_required",
    "resolution_policy",
}


@dataclass(frozen=True)
class SelectedRow:
    blind_id: str
    revision: str
    original_id: str
    question: str
    selection_rank_sha256: str
    display_rank_sha256: str


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


def read_gold_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Gold CSV is empty: {path}")
    required = {"id", "question"}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Gold CSV {path} lacks required columns: {sorted(missing)}")
    if any(not row["id"].strip() or not row["question"].strip() for row in rows):
        raise ValueError(f"Gold CSV contains a blank id or question: {path}")
    return rows


def rank_value(seed: str, purpose: str, revision: str, original_id: str) -> str:
    return sha256_text(f"{seed}|{purpose}|{revision}|{original_id}")


def select_stratum(
    rows: Sequence[Mapping[str, str]],
    *,
    revision: str,
    sample_size: int,
    seed: str,
) -> list[dict[str, str]]:
    if sample_size <= 0 or sample_size > len(rows):
        raise ValueError(
            f"Invalid sample size {sample_size} for {revision} population {len(rows)}"
        )
    seen_ids: set[str] = set()
    ranked: list[dict[str, str]] = []
    for row in rows:
        original_id = row["id"].strip()
        if original_id in seen_ids:
            raise ValueError(f"Duplicate {revision} row id: {original_id}")
        seen_ids.add(original_id)
        ranked.append(
            {
                "original_id": original_id,
                "question": row["question"].strip(),
                "selection_rank_sha256": rank_value(
                    seed, "select", revision, original_id
                ),
            }
        )
    if len({row["selection_rank_sha256"] for row in ranked}) != len(ranked):
        raise ValueError(f"SHA-256 selection-rank collision in {revision}")
    ranked.sort(key=lambda row: row["selection_rank_sha256"])
    return ranked[:sample_size]


def prepare_sample(
    rev4_rows: Sequence[Mapping[str, str]],
    rev5_rows: Sequence[Mapping[str, str]],
    *,
    seed: str,
) -> list[SelectedRow]:
    if not seed:
        raise ValueError("The private seed must not be empty")

    selected: list[dict[str, str]] = []
    for revision, rows, sample_size in (
        (REV4_LABEL, rev4_rows, REV4_SAMPLE_SIZE),
        (REV5_LABEL, rev5_rows, REV5_SAMPLE_SIZE),
    ):
        for row in select_stratum(
            rows, revision=revision, sample_size=sample_size, seed=seed
        ):
            selected.append(
                {
                    **row,
                    "revision": revision,
                    "display_rank_sha256": rank_value(
                        seed, "order", revision, row["original_id"]
                    ),
                }
            )

    selected.sort(key=lambda row: row["display_rank_sha256"])
    if len({row["display_rank_sha256"] for row in selected}) != len(selected):
        raise ValueError("SHA-256 display-rank collision in selected sample")
    prepared = [
        SelectedRow(
            blind_id=f"IR-{index:03d}",
            revision=row["revision"],
            original_id=row["original_id"],
            question=row["question"],
            selection_rank_sha256=row["selection_rank_sha256"],
            display_rank_sha256=row["display_rank_sha256"],
        )
        for index, row in enumerate(selected, start=1)
    ]
    validate_prepared_sample(prepared)
    return prepared


def validate_prepared_sample(rows: Sequence[SelectedRow]) -> None:
    if len(rows) != REV4_SAMPLE_SIZE + REV5_SAMPLE_SIZE:
        raise ValueError(f"Expected 30 selected rows, found {len(rows)}")
    rev4_count = sum(row.revision == REV4_LABEL for row in rows)
    rev5_count = sum(row.revision == REV5_LABEL for row in rows)
    if (rev4_count, rev5_count) != (REV4_SAMPLE_SIZE, REV5_SAMPLE_SIZE):
        raise ValueError(
            f"Expected Revision 4/5 counts 8/22, found {rev4_count}/{rev5_count}"
        )
    if len({row.blind_id for row in rows}) != len(rows):
        raise ValueError("Blind IDs are not unique")
    if len({(row.revision, row.original_id) for row in rows}) != len(rows):
        raise ValueError("Revision-scoped original IDs are not unique")
    if len({row.question for row in rows}) != len(rows):
        raise ValueError("Selected questions are not unique")


def canonical_sample_payload(rows: Iterable[SelectedRow]) -> bytes:
    text = "".join(
        f"{row.blind_id}\t{row.revision}\t{row.question}\n" for row in rows
    )
    return text.encode("utf-8")


def sample_commitment(rows: Sequence[SelectedRow]) -> str:
    return sha256_bytes(canonical_sample_payload(rows))


def blinded_records(rows: Sequence[SelectedRow]) -> list[dict[str, str]]:
    records = [
        {
            "blind_id": row.blind_id,
            "nist_revision": row.revision,
            "question": row.question,
            "governing_control": "",
            "expected_clause_ids": "",
            "required_odp_ids": "",
            "notes": "",
        }
        for row in rows
    ]
    leaked = FORBIDDEN_BLINDED_COLUMNS.intersection(BLINDED_COLUMNS)
    if leaked:
        raise AssertionError(f"Forbidden columns in blinded output: {sorted(leaked)}")
    return records


def write_csv(path: Path, records: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BLINDED_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def verify_source_hash(path: Path, revision: str) -> str:
    actual = sha256_file(path)
    expected = EXPECTED_SOURCE_SHA256[revision]
    if actual != expected:
        raise ValueError(
            f"{revision} source hash mismatch: expected {expected}, found {actual}"
        )
    return actual


def run(args: argparse.Namespace) -> dict[str, object]:
    seed = args.seed_file.read_text(encoding="utf-8").strip()
    if not seed:
        raise ValueError("Seed file is empty")

    source_hashes = {
        REV4_LABEL: verify_source_hash(args.rev4_csv, REV4_LABEL),
        REV5_LABEL: verify_source_hash(args.rev5_csv, REV5_LABEL),
    }
    rev4_rows = read_gold_csv(args.rev4_csv)
    rev5_rows = read_gold_csv(args.rev5_csv)
    rows = prepare_sample(rev4_rows, rev5_rows, seed=seed)
    commitment = sample_commitment(rows)
    if args.expected_sample_commitment and commitment != args.expected_sample_commitment:
        raise ValueError(
            "Sample commitment mismatch: "
            f"expected {args.expected_sample_commitment}, found {commitment}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "blinded_csv": args.output_dir / "blinded_relabeling_packet.csv",
        "private_mapping": args.output_dir / "private_blind_id_mapping.json",
        "run_manifest": args.output_dir / "sampling_run_manifest.json",
    }
    existing = [str(path) for path in output_paths.values() if path.exists()]
    if existing and not args.force:
        raise FileExistsError(
            "Refusing to overwrite existing outputs without --force: " + ", ".join(existing)
        )

    write_csv(output_paths["blinded_csv"], blinded_records(rows))
    write_json(
        output_paths["private_mapping"],
        {
            "protocol_id": PROTOCOL_ID,
            "warning": "WITHHOLD UNTIL THE COMPLETED SECOND-LABEL FILE IS HASHED",
            "mapping": [
                {
                    "blind_id": row.blind_id,
                    "nist_revision": row.revision,
                    "original_id": row.original_id,
                    "question_sha256": sha256_text(row.question),
                    "selection_rank_sha256": row.selection_rank_sha256,
                    "display_rank_sha256": row.display_rank_sha256,
                }
                for row in rows
            ],
        },
    )
    manifest = {
        "algorithm_version": ALGORITHM_VERSION,
        "protocol_id": PROTOCOL_ID,
        "population": {
            "total": len(rev4_rows) + len(rev5_rows),
            "revision_4": len(rev4_rows),
            "revision_5": len(rev5_rows),
        },
        "sample": {"total": 30, "revision_4": 8, "revision_5": 22},
        "source_sha256": source_hashes,
        "seed_sha256": sha256_text(seed),
        "sample_commitment_sha256": commitment,
        "blinded_csv_sha256": sha256_file(output_paths["blinded_csv"]),
        "private_mapping_sha256": sha256_file(output_paths["private_mapping"]),
    }
    write_json(output_paths["run_manifest"], manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rev4-csv", type=Path, required=True)
    parser.add_argument("--rev5-csv", type=Path, required=True)
    parser.add_argument(
        "--seed-file",
        type=Path,
        required=True,
        help="Private UTF-8 seed file; do not commit it before the reveal phase.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-sample-commitment")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    manifest = run(build_parser().parse_args())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
