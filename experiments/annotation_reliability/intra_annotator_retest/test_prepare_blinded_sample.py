#!/usr/bin/env python3
"""Offline tests for the blinded intra-annotator sampler."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "prepare_blinded_sample", HERE / "prepare_blinded_sample.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture_rows(count: int, prefix: str) -> list[dict[str, str]]:
    return [
        {
            "id": str(index),
            "question": f"{prefix} question {index}",
            "control_id": f"{prefix}-{index}",
            "gold_control_path": f"{prefix.lower()}-{index}_smt",
            "odp_required": "secret-label" if index % 2 else "",
        }
        for index in range(1, count + 1)
    ]


class BlindedSamplerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rev4 = fixture_rows(36, "R4")
        self.rev5 = fixture_rows(100, "R5")
        self.seed = "unit-test-seed"

    def test_selection_is_deterministic_and_fully_automatic(self) -> None:
        first = MODULE.prepare_sample(self.rev4, self.rev5, seed=self.seed)
        second = MODULE.prepare_sample(self.rev4, self.rev5, seed=self.seed)
        self.assertEqual(first, second)
        self.assertEqual(30, len(first))
        self.assertEqual(8, sum(row.revision == MODULE.REV4_LABEL for row in first))
        self.assertEqual(22, sum(row.revision == MODULE.REV5_LABEL for row in first))
        self.assertEqual(
            [f"IR-{index:03d}" for index in range(1, 31)],
            [row.blind_id for row in first],
        )

    def test_selection_does_not_depend_on_gold_labels(self) -> None:
        original = MODULE.prepare_sample(self.rev4, self.rev5, seed=self.seed)
        changed_rev4 = [
            {**row, "control_id": "CHANGED", "odp_required": "CHANGED"}
            for row in self.rev4
        ]
        changed_rev5 = [
            {**row, "gold_control_path": "CHANGED", "odp_required": "CHANGED"}
            for row in self.rev5
        ]
        changed = MODULE.prepare_sample(changed_rev4, changed_rev5, seed=self.seed)
        self.assertEqual(original, changed)

    def test_blinded_output_excludes_gold_and_original_identifiers(self) -> None:
        selected = MODULE.prepare_sample(self.rev4, self.rev5, seed=self.seed)
        records = MODULE.blinded_records(selected)
        self.assertEqual(set(MODULE.BLINDED_COLUMNS), set(records[0]))
        self.assertFalse(
            MODULE.FORBIDDEN_BLINDED_COLUMNS.intersection(records[0]), records[0]
        )
        self.assertTrue(all(not row["governing_control"] for row in records))
        self.assertTrue(all(not row["expected_clause_ids"] for row in records))
        self.assertTrue(all(not row["required_odp_ids"] for row in records))

    def test_commitment_is_stable_and_content_sensitive(self) -> None:
        selected = MODULE.prepare_sample(self.rev4, self.rev5, seed=self.seed)
        commitment = MODULE.sample_commitment(selected)
        self.assertEqual(64, len(commitment))
        changed = list(selected)
        changed[0] = MODULE.SelectedRow(
            **{**changed[0].__dict__, "question": changed[0].question + " changed"}
        )
        self.assertNotEqual(commitment, MODULE.sample_commitment(changed))

    def test_protocol_source_hashes_match_frozen_gold_files(self) -> None:
        repo_root = HERE.parents[2]
        gold_root = repo_root / "data" / "gold_standard_datasets" / "nist800-53"
        paths = {
            MODULE.REV4_LABEL: gold_root / "nist_sp800-53_rev4_gold-set_36q.csv",
            MODULE.REV5_LABEL: gold_root / "nist_sp800-53_rev5_gold-set_100q.csv",
        }
        for revision, path in paths.items():
            self.assertEqual(
                MODULE.EXPECTED_SOURCE_SHA256[revision], MODULE.sha256_file(path)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
