"""Regression checks for the recorded empty-selection fallback replay."""
import copy
import unittest
from pathlib import Path

from experiments.answerer_comparison.rq2_profile_fill_v2 import run_profile_fill as study


class RecordedFallbackReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, _ = study.load_inputs(Path(__file__).resolve().parents[1])

    def test_only_recorded_fallbacks_reconstruct_an_empty_selection(self):
        for revision, data in self.inputs.items():
            generator = study.RecordedFallbackGenerator(data["selector_entries"])
            for entry in data["selector_entries"]:
                docs = [{"id": sid} for sid in entry["evidence_window_source_ids"]]
                result = generator.generate(entry["question"], docs, {})
                if entry["query_id"] in study.RECORDED_FALLBACK_IDS[revision]:
                    self.assertEqual(result["evidence_spans"], [])
                else:
                    self.assertEqual(result, entry["selector_raw"])

    def test_changed_evidence_window_is_rejected(self):
        data = self.inputs["rev5"]
        entry = next(e for e in data["selector_entries"] if e["query_id"] == "99")
        generator = study.RecordedFallbackGenerator(data["selector_entries"])
        with self.assertRaises(AssertionError):
            generator.generate(entry["question"], [{"id": "not_the_frozen_source"}], {})

    def test_real_pipeline_reproduces_both_recorded_fallback_traces(self):
        data = self.inputs["rev5"]
        pipe = study.pipeline(data, "rev5", "FILL_FROM_PROFILE")
        for context in data["contexts"]:
            qid = context["query_id"]
            if qid not in study.RECORDED_FALLBACK_IDS["rev5"]:
                continue
            pipe.org_profile = {"framework_version": "rev5", "odp_values": {}}
            contract = study.execute(pipe, context)
            old = data["contracts"][qid]
            self.assertEqual(contract["evidence_spans"], old["evidence_spans"])
            self.assertEqual(contract["debug"]["selector_raw"], old["debug"]["selector_raw"])
            self.assertTrue(study.fallback_trace_matches(contract, old))
            forged = copy.deepcopy(contract)
            for origin in forged["provenance"]:
                if origin["origin"] == "fallback":
                    origin["origin"] = "selector"
            self.assertFalse(study.fallback_trace_matches(forged, old))


if __name__ == "__main__":
    unittest.main()
