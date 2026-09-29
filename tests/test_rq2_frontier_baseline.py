import json
import tempfile
import unittest
from pathlib import Path

from experiments.answerer_comparison.rq2_frontier_baseline import run_frontier_baseline as runner


class FrontierBaselineRunnerTest(unittest.TestCase):
    def test_registered_generation_settings_are_conservative_and_auditable(self):
        self.assertEqual(runner.MODEL_ID, "gpt-6-astra")
        self.assertEqual(runner.GENERATION_SETTINGS["reasoning_effort"], "low")
        self.assertEqual(runner.GENERATION_SETTINGS["max_parse_retries"], 2)
        self.assertFalse(runner.GENERATION_SETTINGS["store"])
        self.assertFalse(runner.GENERATION_SETTINGS["tools_enabled"])
        self.assertFalse(runner.GENERATION_SETTINGS["structured_output_enforced"])

    def test_activity_detects_call_log_without_completed_csv_row(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = runner.api_log_path(output)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"response_id": "resp_billed"}) + "\n", encoding="utf-8")
            self.assertTrue(runner.has_api_activity(output))

    def test_output_manifest_uses_batch_5c_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "sample.txt").write_text("sample", encoding="utf-8")
            manifest = runner.write_output_manifest(output)
            self.assertEqual(manifest["schema_version"], runner.SCHEMA_VERSION)
            self.assertEqual(manifest["result_id"], runner.RESULT_ID)
            stored = json.loads((output / "manifests" / "outputs.json").read_text())
            self.assertEqual(stored["files"], manifest["files"])


if __name__ == "__main__":
    unittest.main()
