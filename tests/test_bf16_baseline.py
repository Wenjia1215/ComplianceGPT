import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.answerer_comparison.rq2_bf16_baseline.run_bf16_baseline import (
    ARCHIVE_MEMBERS,
    DEFAULT_ARCHIVE,
    EXPECTED_CONTEXT_SCHEMA,
    EXPECTED_ROWS,
    FROZEN_ARCHIVE_SHA256,
    INPUTS,
    MODEL_ID,
    MODEL_REVISION,
    aggregate_rows,
    exact_mcnemar,
    extract_registered_archive,
    load_gold_rows,
    paired_strict_pass,
    parse_contexts,
    read_csv_rows,
    require_bf16_gpu,
    sha256_file,
    validate_context,
    validate_matched_rows,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = REPO_ROOT / DEFAULT_ARCHIVE


def normalize_odp_id(value):
    return str(value or "").strip().lower()


class Bf16BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gold = load_gold_rows(REPO_ROOT / INPUTS["gold"])
        with tempfile.TemporaryDirectory() as directory:
            cls.output_dir = Path(directory)
            cls.contexts, cls.manifest = extract_registered_archive(
                archive_path=ARCHIVE_PATH,
                output_dir=cls.output_dir,
            )
            cls.baseline_rows = read_csv_rows(
                cls.output_dir / "references" / "rev4_generative_baseline_4bit.csv"
            )
            cls.compliance_rows = read_csv_rows(
                cls.output_dir / "references" / "rev4_compliancegpt_4bit.csv"
            )
            cls.context_bytes = (
                cls.output_dir / "contexts" / "rev4_prepared_contexts.jsonl"
            ).read_bytes()

    def test_registered_identity_is_locked(self):
        self.assertEqual(MODEL_ID, "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(MODEL_REVISION, "a09a35458c702b33eeacc393d103063234e8bc28")
        self.assertEqual(EXPECTED_ROWS, 36)
        self.assertEqual(EXPECTED_CONTEXT_SCHEMA, "compliancegpt-rq2-prepared-context")

    def test_frozen_archive_and_members_are_locked(self):
        self.assertEqual(sha256_file(ARCHIVE_PATH), FROZEN_ARCHIVE_SHA256)
        self.assertEqual(
            self.manifest["archive_sha256"],
            FROZEN_ARCHIVE_SHA256,
        )
        self.assertEqual(set(self.manifest["members"]), set(ARCHIVE_MEMBERS))

    def test_all_rev4_contexts_validate_without_gold(self):
        contexts = parse_contexts(self.context_bytes)
        self.assertEqual(len(contexts), EXPECTED_ROWS)
        self.assertEqual(len({row["context_sha256"] for row in contexts}), EXPECTED_ROWS)
        self.assertTrue(all(row["framework_version"] == "rev4" for row in contexts))

    def test_context_tampering_is_detected(self):
        context = copy.deepcopy(self.contexts[0])
        context["question"] += " changed"
        with self.assertRaises(AssertionError):
            validate_context(context)

    def test_frozen_reference_metrics_match_registered_result(self):
        baseline = aggregate_rows(
            rows=self.baseline_rows,
            gold_rows=self.gold,
            normalize_odp_id=normalize_odp_id,
        )
        compliance = aggregate_rows(
            rows=self.compliance_rows,
            gold_rows=self.gold,
            normalize_odp_id=normalize_odp_id,
        )
        self.assertEqual(baseline["strict_pass"]["count"], 8)
        self.assertEqual(compliance["strict_pass"]["count"], 29)
        self.assertEqual(baseline["status_counts"], {"OK": 36})
        self.assertEqual(compliance["status_counts"], {"OK": 8, "PARAMS_REQUIRED": 28})

    def test_matched_validation_accepts_identical_frozen_windows(self):
        validation = validate_matched_rows(
            self.baseline_rows,
            self.baseline_rows,
            self.compliance_rows,
        )
        self.assertEqual(validation["paired_rows"], EXPECTED_ROWS)
        self.assertEqual(validation["context_mismatches"], 0)
        self.assertEqual(validation["evidence_window_mismatches"], 0)

    def test_exact_mcnemar_matches_frozen_rev4_comparison(self):
        paired = paired_strict_pass(self.compliance_rows, self.baseline_rows)
        self.assertEqual(paired["left_only"], 22)
        self.assertEqual(paired["right_only"], 1)
        self.assertEqual(exact_mcnemar(22, 1), 5.7220458984375e-06)

    def test_t4_is_rejected_for_registered_bf16_run(self):
        class FakeCuda:
            @staticmethod
            def is_available():
                return True

            @staticmethod
            def is_bf16_supported():
                return False

            @staticmethod
            def get_device_name(_index):
                return "Tesla T4"

        class FakeTorch:
            cuda = FakeCuda()

        with self.assertRaisesRegex(RuntimeError, "T4 is not valid"):
            require_bf16_gpu(FakeTorch())


if __name__ == "__main__":
    unittest.main()
