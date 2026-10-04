"""Primary gate transitions, score-cache integrity, and paired-statistic checks."""
import copy
import math
import unittest
from pathlib import Path

import numpy as np

from experiments.retriever_ablation.constant_sensitivity import primary_adapter as p
from experiments.retriever_ablation.constant_sensitivity.statistics import rank_metrics, exact_mcnemar, wilson, paired


class LexicalFixture:
    def __init__(self, indices, size):
        self.indices, self.size = indices, size

    def get_top_n(self, tokens, n=50):
        return self.indices[:n]

    def get_scores(self, tokens):
        scores = np.zeros(self.size, dtype=np.float32)
        for rank, index in enumerate(self.indices, 1):
            scores[index] = 1.0 / rank
        return scores


class DenseFixture:
    def __init__(self, ids):
        self.ids, self.last_best_clause = ids, {}

    def search(self, query, top_k=50):
        self.last_best_clause = {cid: cid.lower() + "_smt" for cid in self.ids}
        return [(cid, 1.0 / rank) for rank, cid in enumerate(self.ids[:top_k], 1)]

    def best_clause_text_for_control(self, cid):
        return "Canonical text for " + cid


class CrossFixture:
    def predict(self, pairs, show_progress_bar=False):
        return np.array([1.0 if text.endswith("B") else 0.0 for _, text in pairs], dtype=np.float32)


class PrimarySensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = p.load_primary(Path(__file__).resolve().parents[1])

    def fixture(self, separated=False):
        controls = ["A", "B", "C", "D"]
        lexical, dense = controls, controls
        if separated:
            lexical = ["A"] + [f"L{i}" for i in range(1, 7)] + ["B"]
            dense = ["A"] + [f"D{i}" for i in range(1, 7)] + ["B"]
            controls = list(dict.fromkeys(lexical + dense))
        case = {"revision": "fixture", "query_id": "1", "question": "Control requirement",
                "rewrites": [], "accepted_variants": ["Control requirement"], "gold_control_id": "A"}
        fallback = {cid: "Canonical text for " + cid for cid in controls}
        trace = p.capture(self.ns, case, LexicalFixture([controls.index(cid) for cid in lexical], len(controls)),
                          DenseFixture(dense), CrossFixture(), controls, fallback)
        return trace, controls, fallback, case

    def run_condition(self, trace, controls, fallback, condition):
        return p.replay(self.ns, trace, controls, fallback, p.config(condition))

    def test_seven_conditions_change_only_one_registered_constant(self):
        self.assertEqual(len(p.CONDITIONS), 7)
        for name in p.CONDITIONS:
            settings = p.config(name)
            different = [key for key in settings if settings[key] != p.BASELINE[key]]
            self.assertEqual(len(different), int(name != "baseline"))
            if different:
                ratio = settings[different[0]] / p.BASELINE[different[0]]
                self.assertAlmostEqual(ratio, 0.8 if "minus" in name else 1.2)

    def test_primary_definitions_preserve_query_encoding_and_fixed_adoption_rule(self):
        sources = p.definitions(Path(__file__).resolve().parents[1])
        self.assertIn('self.model.encode([query]', sources["DenseIndex"])
        self.assertIn('f"passage: {full}"', sources["build_dense_retriever"])
        self.assertNotIn("effective_apply_min", sources["s7_heavy_retrieve_details"])
        self.assertIn("rerank_margin_ratio < float(rerank_apply_min_margin_ratio)", sources["s7_heavy_retrieve_details"])

    def test_adoption_threshold_blocks_a_flip_in_the_expected_margin_interval(self):
        trace, controls, fallback, _ = self.fixture()
        base = self.run_condition(trace, controls, fallback, "baseline")
        changed = self.run_condition(trace, controls, fallback, "adoption_plus20")
        self.assertEqual(base["final_ranked_cids"][0], "B")
        self.assertTrue(base["meta"]["rerank_applied"])
        self.assertGreater(base["meta"]["rerank_margin_ratio"], 0.15)
        self.assertLess(base["meta"]["rerank_margin_ratio"], 0.18)
        self.assertEqual(changed["final_ranked_cids"], controls)
        self.assertFalse(changed["meta"]["rerank_applied"])

    def test_blend_change_reuses_the_same_scores_and_changes_the_winner(self):
        trace, controls, fallback, _ = self.fixture()
        fingerprint = p.digest(trace)
        base = self.run_condition(trace, controls, fallback, "baseline")
        changed = self.run_condition(trace, controls, fallback, "alpha_plus20")
        self.assertEqual(base["final_ranked_cids"][0], "B")
        self.assertEqual(changed["final_ranked_cids"][0], "A")
        self.assertEqual(base["meta"]["base_margin_ratio"], changed["meta"]["base_margin_ratio"])
        self.assertEqual(p.digest(trace), fingerprint)

    def test_skip_change_can_call_a_previously_skipped_cross_encoder(self):
        trace, controls, fallback, _ = self.fixture(separated=True)
        base = self.run_condition(trace, controls, fallback, "baseline")
        changed = self.run_condition(trace, controls, fallback, "skip_plus20")
        self.assertGreater(base["meta"]["base_margin_ratio"], 0.10)
        self.assertLess(base["meta"]["base_margin_ratio"], 0.12)
        self.assertFalse(base["meta"]["reranker_called"])
        self.assertTrue(changed["meta"]["reranker_called"])
        self.assertEqual(base["final_ranked_cids"][0], "A")
        self.assertEqual(changed["final_ranked_cids"][0], "B")

    def test_dense_cache_mismatch_is_rejected_despite_the_historical_exception_handler(self):
        trace, controls, fallback, _ = self.fixture()
        trace["dense_calls"][0]["query"] = "A different question"
        with self.assertRaises(AssertionError):
            self.run_condition(trace, controls, fallback, "baseline")

    def test_cross_encoder_pairs_cannot_be_replaced(self):
        trace, controls, fallback, _ = self.fixture()
        trace["cross_encoder_calls"][0]["pairs"][0][1] = "Altered source text"
        with self.assertRaises(AssertionError):
            self.run_condition(trace, controls, fallback, "baseline")

    def test_json_roundtrip_preserves_exact_probe_and_all_condition_results(self):
        import json
        trace, controls, fallback, _ = self.fixture()
        encoded = json.loads(json.dumps(trace))
        for condition in p.CONDITIONS:
            self.assertEqual(self.run_condition(trace, controls, fallback, condition),
                             self.run_condition(encoded, controls, fallback, condition))

    def test_reference_control_label_is_not_an_inference_input(self):
        trace, controls, fallback, case = self.fixture()
        case["gold_control_id"] = "Unrelated label"
        other = p.capture(self.ns, case, LexicalFixture(list(range(4)), 4), DenseFixture(controls),
                          CrossFixture(), controls, fallback)
        self.assertEqual(trace, other)

    def test_rank_metrics_treat_misses_as_zero_and_use_one_relevant_control(self):
        self.assertEqual(rank_metrics(0), {"success_at_1": 0, "success_at_5": 0, "success_at_10": 0, "mrr_at_10": 0.0, "ndcg_at_10": 0.0})
        self.assertAlmostEqual(rank_metrics(10)["mrr_at_10"], 0.1)
        self.assertAlmostEqual(rank_metrics(2)["ndcg_at_10"], 1 / math.log2(3))
        self.assertEqual(rank_metrics(11)["success_at_10"], 0)

    def test_exact_mcnemar_and_wilson_match_known_counts(self):
        self.assertEqual(exact_mcnemar(0, 0), 1.0)
        self.assertEqual(exact_mcnemar(0, 1), 1.0)
        self.assertAlmostEqual(exact_mcnemar(0, 9), 0.00390625)
        low, high = wilson(90, 100)
        self.assertAlmostEqual(low, 0.82563434, places=7)
        self.assertAlmostEqual(high, 0.94477086, places=7)

    def test_paired_statistics_keep_revision_identities_and_delta_direction(self):
        def row(revision, rank):
            return {"revision": revision, "query_id": "1", "rank": rank,
                    "ranked_controls": ["A" if rank == 1 else "B"], "metrics": rank_metrics(rank)}
        base = [row("rev4", 0), row("rev5", 1)]
        changed = [row("rev4", 1), row("rev5", 1)]
        result = paired(base, changed, bootstrap_samples=500)
        self.assertEqual(result["metrics"]["success_at_1"]["gains"], 1)
        self.assertEqual(result["metrics"]["success_at_1"]["delta"], 0.5)
        self.assertEqual(paired(changed, base, bootstrap_samples=500)["metrics"]["mrr_at_10"]["delta"], -0.5)
        changed[0]["revision"] = "rev5"
        with self.assertRaises(AssertionError):
            paired(base, changed, bootstrap_samples=500)

    def test_fixture_report_has_complete_pairs_gate_effects_and_verified_archive(self):
        import contextlib
        import hashlib
        import io
        import json
        import tempfile
        import zipfile
        from unittest.mock import patch
        from experiments.retriever_ablation.constant_sensitivity import run_sensitivity as runner
        template, controls, fallback, template_case = self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder, output = root / "registration", root / "fixture_outputs"
            folder.mkdir()
            protocol = {"queries": 4, "expected_evaluations": 28, "code_sha256": {},
                        "input_sha256": {}, "seed": 42, "bootstrap_samples": 100,
                        "acceptance": ["fixture_probes_reproduce", "fixture_matrix_complete"]}
            runner.write(folder / "protocol.json", protocol)
            fingerprint = runner.sha(folder / "protocol.json")
            cases, manifest = [], {}
            baseline = self.run_condition(template, controls, fallback, "baseline")
            for revision in ("rev4", "rev5"):
                for qid, gold in (("1", "A"), ("2", "B")):
                    case = dict(template_case, revision=revision, query_id=qid, gold_control_id=gold,
                                historical_rank_at_10=2 if gold == "A" else 1,
                                historical_top10=baseline["final_ranked_cids"], historical_meta=baseline["meta"])
                    cases.append(case)
                    trace = copy.deepcopy(template)
                    trace.update(revision=revision, query_id=qid, model_revisions=runner.MODELS,
                                 protocol_sha256=fingerprint)
                    relative = runner.cache_relative(case)
                    runner.write(output / relative, trace)
                    manifest[relative] = runner.sha(output / relative)
            runner.write(output / "cache_manifest.json", manifest)
            runner.write(output / "run_config.json", {"protocol_sha256": fingerprint, "code_sha256": {},
                         "input_sha256": {}, "execution_repo_commit": "synthetic-fixture",
                         "runtime": {"model_revisions": runner.MODELS, "is_fixture": True}})
            with patch.object(runner, "base_index", return_value=(None, controls, fallback)), contextlib.redirect_stdout(io.StringIO()):
                runner.score_all(root, folder, output, protocol, cases, self.ns)
            report = json.loads((output / "summary.json").read_text())
            self.assertTrue(report["accepted"])
            self.assertEqual(report["evaluations"], 28)
            self.assertEqual(report["verified_cache_captures"], 4)
            self.assertEqual(report["historical_baseline"]["top10_unchanged"], 4)
            for group in report["strata"].values():
                self.assertEqual(len(group["conditions"]), 7)
                self.assertEqual(len(group["paired_vs_baseline"]), 6)
            plus = report["strata"]["pooled"]["conditions"]["adoption_plus20"]
            self.assertEqual(plus["gates"]["adoption"]["prevented_reference_errors"], 2)
            self.assertEqual(plus["gates"]["adoption"]["blocked_reference_corrections"], 2)
            with zipfile.ZipFile(output / (runner.RESULT_ID + ".zip")) as archive:
                self.assertIsNone(archive.testzip())
                for line in (output / "SHA256SUMS").read_text().splitlines():
                    expected, name = line.split("  ", 1)
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
