import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from compliancegpt.generator.verifier.verifier import normalize_odp_id
from experiments.answerer_comparison.rq2_frontier_baseline_rev5 import (
    run_frontier_baseline_rev5 as runner,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class FrontierBaselineRev5RunnerTest(unittest.TestCase):
    def test_runner_matches_published_precommitment(self):
        registered = runner.load_precommitment(REPO_ROOT)
        self.assertEqual(registered["result_id"], runner.RESULT_ID)
        self.assertEqual(registered["n_questions"], 100)
        self.assertEqual(registered["framework_version"], "rev5")
        self.assertTrue(registered["no_api_outputs_observed_at_registration"])
        self.assertEqual(registered["api"]["model_id"], "gemini-3.5-flash")
        self.assertEqual(
            registered["api"]["generation_settings"], runner.GENERATION_SETTINGS
        )

    def test_registered_generation_settings_preserve_batch_5c_boundary(self):
        self.assertEqual(runner.MODEL_ID, "gemini-3.5-flash")
        self.assertEqual(runner.GENERATION_SETTINGS["thinking_level"], "LOW")
        self.assertEqual(runner.GENERATION_SETTINGS["temperature"], 1.0)
        self.assertEqual(runner.GENERATION_SETTINGS["max_output_tokens"], 2048)
        self.assertEqual(runner.GENERATION_SETTINGS["max_parse_retries"], 2)
        self.assertFalse(runner.GENERATION_SETTINGS["tools_enabled"])
        self.assertFalse(runner.GENERATION_SETTINGS["structured_output_enforced"])

    def test_frozen_archive_contains_100_valid_gold_free_contexts(self):
        archive_path = REPO_ROOT / runner.DEFAULT_ARCHIVE
        self.assertEqual(runner.sha256_file(archive_path), runner.FROZEN_ARCHIVE_SHA256)
        with zipfile.ZipFile(archive_path) as archive:
            data = archive.read("contexts/rev5_prepared_contexts.jsonl")
        contexts = runner.parse_contexts(data)
        self.assertEqual(len(contexts), 100)
        self.assertEqual(len({row["query_id"] for row in contexts}), 100)
        self.assertFalse(any(runner.gold_key_paths(row) for row in contexts))

    def test_prepare_only_inputs_reproduce_frozen_compliance_metrics(self):
        archive_path = REPO_ROOT / runner.DEFAULT_ARCHIVE
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            contexts, gold_rows = runner.prepare_experiment(
                REPO_ROOT, output, archive_path
            )
            self.assertEqual(len(contexts), 100)
            self.assertFalse(runner.has_api_activity(output))
            rows = runner.read_csv_rows(
                output / "references" / "rev5_compliancegpt_4bit.csv"
            )
            metrics = runner.aggregate_rows(
                rows=rows,
                gold_rows=gold_rows,
                normalize_odp_id=normalize_odp_id,
            )
            self.assertEqual(metrics["strict_pass"]["count"], 65)
            self.assertEqual(metrics["full_gold_clause_coverage"]["count"], 65)
            self.assertEqual(metrics["runtime_contract_pass"]["count"], 100)
            self.assertEqual(metrics["right_governing_control"]["count"], 97)
            self.assertEqual(metrics["realization_loss"]["count"], 0)
            self.assertEqual(metrics["realization_loss"]["n"], 65)
            odp = metrics["odp_against_author_labels"]
            self.assertEqual(odp["params_required_sensitivity"]["count"], 63)
            self.assertEqual(odp["params_required_sensitivity"]["n"], 63)
            self.assertEqual(odp["specificity"]["count"], 17)
            self.assertEqual(odp["specificity"]["n"], 37)
            preflight = json.loads(
                (output / "preflight" / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(preflight["api_calls_performed"], 0)

    def test_registered_exact_statistics(self):
        self.assertAlmostEqual(
            runner.fisher_exact_two_sided(0, 29, 4, 24),
            0.0518341307814992,
        )
        self.assertEqual(runner.exact_mcnemar(8, 3), 0.2265625)
        interval = runner.wilson_interval(0, 29)
        self.assertEqual(interval["lower"], 0.0)
        self.assertGreater(interval["upper"], 0.0)
        self.assertLess(interval["upper"], 0.12)

    def test_summary_pipeline_uses_complete_strict_pass(self):
        archive_path = REPO_ROOT / runner.DEFAULT_ARCHIVE
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            _, gold_rows = runner.prepare_experiment(REPO_ROOT, output, archive_path)
            source = output / "references" / "rev5_generative_baseline_4bit.csv"
            destination = runner.frontier_csv(output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("r", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                self.assertIsNotNone(reader.fieldnames)
                rows = []
                for row in reader:
                    row["model_id"] = runner.MODEL_ID
                    row["model_requested_revision"] = runner.MODEL_REQUESTED_REVISION
                    row["model_resolved_revision"] = runner.MODEL_RESOLVED_REVISION_MARKER
                    row["tokenizer_resolved_revision"] = runner.TOKENIZER_REVISION_MARKER
                    rows.append(row)
            with destination.open("w", encoding="utf-8", newline="") as output_handle:
                writer = csv.DictWriter(output_handle, fieldnames=reader.fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            summary = runner.summarize_completed_run(
                output_dir=output,
                gold_rows=gold_rows,
                normalize_odp_id=normalize_odp_id,
                api_manifest={"completed_result_rows": 100, "synthetic_test": True},
            )
            paired = summary["paired_strict_pass"]["compliancegpt_vs_frontier"]
            self.assertEqual(paired["left_only"], 46)
            self.assertEqual(paired["right_only"], 2)
            self.assertAlmostEqual(
                paired["exact_mcnemar_two_sided_p"], 8.363087999896379e-12
            )
            self.assertEqual(
                summary["configurations"]["generative_frontier_api"]
                ["realization_loss"]["count"],
                32,
            )
            self.assertEqual(
                summary["configurations"]["generative_frontier_api"]
                ["realization_loss"]["n"],
                53,
            )
            markdown = (output / "SUMMARY.md").read_text(encoding="utf-8")
            self.assertIn("Coverage-complete rejections", markdown)
            self.assertIn("ODP status operating point", markdown)

    def test_activity_detects_logged_call_without_completed_row(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = runner.api_log_path(output)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"response_id": "resp_billed"}) + "\n",
                encoding="utf-8",
            )
            self.assertTrue(runner.has_api_activity(output))

    def test_output_manifest_uses_batch_5d_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "sample.txt").write_text("sample", encoding="utf-8")
            manifest = runner.write_output_manifest(output)
            self.assertEqual(manifest["schema_version"], runner.SCHEMA_VERSION)
            self.assertEqual(manifest["result_id"], runner.RESULT_ID)
            stored = json.loads(
                (output / "manifests" / "outputs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["files"], manifest["files"])


if __name__ == "__main__":
    unittest.main()
