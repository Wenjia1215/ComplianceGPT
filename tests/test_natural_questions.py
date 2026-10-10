"""Synthetic safety/measurement fixtures. These are not author study labels."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

FOLDER = pathlib.Path(__file__).resolve().parents[1] / "experiments/external_validity/natural_questions_v1"
sys.path.insert(0, str(FOLDER))
import review_and_freeze as review
import score_results as score
import run_natural_questions as runner


class ReviewGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.questions, cls.corpora, cls.registries = review.check_candidates()
        cls.rows = review.load_review(FOLDER / "review_labels.template.csv")

    def complete_synthetic(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row.update(decision="reviewed", source_checked="yes", reviewer_name="TEST FIXTURE ONLY",
                       reviewed_at_utc="2026-10-05T12:30:00Z")
            if row["answerability"] == "ambiguous":
                row.update(odp_applicability="uncertain", required_odp_ids="null")
            elif row["answerability"] != "outside":
                row.update(odp_applicability="not_required", required_odp_ids="[]")
        return rows

    def validate(self, rows):
        return review.validate_review(rows, self.questions, self.corpora, self.registries)

    def test_candidate_integrity(self):
        self.assertEqual(len(self.questions), 20)
        self.assertEqual(len({q["source_url"] for q in self.questions}), 20)
        self.assertTrue(all(q["required_odp_ids"] is None for q in self.questions))

    def test_unreviewed_template_refused(self):
        with self.assertRaisesRegex(ValueError, "review is pending"):
            self.validate(self.rows)

    def test_completed_synthetic_validation(self):
        labels = self.validate(self.complete_synthetic())
        self.assertEqual(len(labels), 20)
        self.assertTrue(all(not r["independent_expert_review"] for r in labels))

    def test_source_confirmation_is_separate(self):
        rows = self.complete_synthetic()
        rows[0]["source_checked"] = ""
        with self.assertRaisesRegex(ValueError, "confirm the original source"):
            self.validate(rows)

    def test_missing_odp_judgment_refused(self):
        rows = self.complete_synthetic()
        rows[0]["odp_applicability"] = ""
        with self.assertRaisesRegex(ValueError, "ODP applicability"):
            self.validate(rows)

    def test_question_rewording_refused(self):
        rows = self.complete_synthetic()
        rows[0]["question_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "question wording changed"):
            self.validate(rows)

    def test_unknown_and_duplicate_rows_refused(self):
        for changes in [{"query_id": "unknown"}, {"query_id": "NQ02"}]:
            rows = self.complete_synthetic()
            rows[0].update(changes)
            with self.assertRaisesRegex(ValueError, "Unknown or duplicated"):
                self.validate(rows)

    def test_unknown_clause_refused(self):
        rows = self.complete_synthetic()
        rows[0]["evidence_groups"] = '[["invented_smt"]]'
        with self.assertRaisesRegex(ValueError, "unknown/non-evidence"):
            self.validate(rows)

    def test_clause_outside_governing_control_refused(self):
        rows = self.complete_synthetic()
        rows[0]["evidence_groups"] = '[["ac-2_smt.a"]]'
        with self.assertRaisesRegex(ValueError, "outside the labeled controls"):
            self.validate(rows)

    def test_alternative_clause_group_supported(self):
        rows = self.complete_synthetic()
        rows[0]["evidence_groups"] = '[["si-2.2_smt", "si-2.2_smt"]]'
        with self.assertRaisesRegex(ValueError, "distinct acceptable"):
            self.validate(rows)

    def test_uncertain_not_converted_to_negative(self):
        rows = self.complete_synthetic()
        rows[0].update(odp_applicability="uncertain", required_odp_ids="null")
        self.assertIsNone(self.validate(rows)[0]["required_odp_ids"])
        rows[0]["required_odp_ids"] = "[]"
        with self.assertRaisesRegex(ValueError, "not an empty negative"):
            self.validate(rows)

    def test_required_ids_nonempty_known(self):
        rows = self.complete_synthetic()
        rows[0].update(odp_applicability="required", required_odp_ids="[]")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            self.validate(rows)
        rows[0]["required_odp_ids"] = '["made_up"]'
        with self.assertRaisesRegex(ValueError, "unknown ODP"):
            self.validate(rows)

    def test_outside_cannot_be_negative(self):
        rows = self.complete_synthetic()
        row = next(r for r in rows if r["answerability"] == "outside")
        row["odp_applicability"] = "not_required"
        with self.assertRaisesRegex(ValueError, "cannot become a positive or negative"):
            self.validate(rows)

    def test_review_time_requires_utc_and_collection_date(self):
        for stamp in ["2026-10-05", "2026-10-05T10:00:00-04:00", "2000-01-01T00:00:00Z"]:
            rows = self.complete_synthetic()
            rows[0]["reviewed_at_utc"] = stamp
            with self.assertRaises(ValueError):
                self.validate(rows)


class Measurement(unittest.TestCase):
    def setUp(self):
        self.label = {"answerability": "full", "evidence_groups": [["a", "alternative"]],
                      "odp_applicability": "not_required", "required_odp_ids": []}
        self.records = {"a": {"text": "One complete duty."},
                        "alternative": {"text": "An equivalent complete duty."}}
        self.contract = {"status": "OK", "answer_text": "One complete duty.",
                         "evidence_spans": [{"source_id": "a", "span_text": "One complete duty."}],
                         "odp_required_list": []}

    def measured(self):
        return score.score_contract(self.contract, self.label, self.records, True)

    def test_full_coverage_and_contract(self):
        self.assertTrue(self.measured()["strict_full_catalog_contract"])

    def test_alternative_evidence_supported(self):
        self.contract["evidence_spans"] = [{"source_id": "alternative", "span_text": self.records["alternative"]["text"]}]
        self.assertTrue(self.measured()["strict_full_catalog_contract"])

    def test_short_quote_not_complete_duty(self):
        self.contract["evidence_spans"][0]["span_text"] = "complete duty."
        row = self.measured()
        self.assertTrue(row["clause_id_group_coverage"])
        self.assertTrue(row["all_spans_verbatim"])
        self.assertFalse(row["complete_clause_text_group_coverage"])
        self.assertFalse(row["strict_full_catalog_contract"])

    def test_partial_is_not_full_success(self):
        self.label["answerability"] = "partial"
        row = self.measured()
        self.assertTrue(row["complete_clause_text_group_coverage"])
        self.assertIsNone(row["strict_full_catalog_contract"])

    def test_outside_has_no_accuracy_or_odp_negative(self):
        self.label.update(answerability="outside", evidence_groups=[], odp_applicability="not_applicable")
        row = self.measured()
        for key in ["clause_id_group_coverage", "complete_clause_text_group_coverage",
                    "strict_full_catalog_contract", "odp_author_label_agreement"]:
            self.assertIsNone(row[key])

    def test_uncertain_has_no_strict_denominator(self):
        self.label.update(odp_applicability="uncertain", required_odp_ids=None)
        self.assertFalse(self.measured()["strict_denominator_eligible"])

    def test_odp_required_status_and_list(self):
        self.label.update(odp_applicability="required", required_odp_ids=["p"])
        self.assertFalse(self.measured()["strict_full_catalog_contract"])
        self.contract.update(status="PARAMS_REQUIRED", odp_required_list=["p"])
        self.assertTrue(self.measured()["strict_full_catalog_contract"])
        self.contract["odp_required_list"] = []
        self.assertFalse(self.measured()["strict_full_catalog_contract"])

    def test_empty_contract_never_strict(self):
        self.contract["evidence_spans"] = []
        self.assertFalse(self.measured()["strict_full_catalog_contract"])

    def test_invalid_source_never_strict(self):
        self.contract["evidence_spans"][0]["source_id"] = "invented"
        self.assertFalse(self.measured()["strict_full_catalog_contract"])

    def test_zero_denominator_not_zero_accuracy(self):
        row = score.proportion([None, None])
        self.assertIsNone(row["rate"])
        self.assertEqual(row["denominator"], 0)
        self.assertIsNone(row["wilson_95"])

    def test_wilson_known_reference(self):
        low, high = score.wilson(5, 10)
        self.assertAlmostEqual(low, 0.2365930905)
        self.assertAlmostEqual(high, 0.7634069095)

    def test_mcnemar_exact(self):
        self.assertEqual(score.mcnemar(0, 0), 1.0)
        self.assertEqual(score.mcnemar(0, 3), 0.25)
        self.assertEqual(score.mcnemar(1, 1), 1.0)


class GenerationCapture(unittest.TestCase):
    def test_checkpoint_must_use_canonical_evidence(self):
        record = {"id": "a", "text": "Canonical clause", "kind": "smt", "control_id": "a"}
        context = {"retrieved_docs": [dict(record)], "evidence_window": [dict(record)]}
        runner.validate_context_authority(context, {"a": record})
        context["evidence_window"][0]["text"] = "Changed clause"
        with self.assertRaisesRegex(ValueError, "canonical catalog"):
            runner.validate_context_authority(context, {"a": record})

    def test_failed_generation_is_retained(self):
        class Tensor:
            def detach(self): return self
            def cpu(self): return self
            def tolist(self): return [[1, 2]]
        class Model:
            def generate(self, *args, **kwargs):
                raise RuntimeError("Synthetic generation failure")
        class Pipeline:
            model = Model()
            tokenizer = None
            def answer(self, *args, **kwargs):
                return self.model.generate(input_ids=Tensor())
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "calls.jsonl"
            pipeline = Pipeline()
            runner.attach_generation_capture(pipeline, path, {})
            with self.assertRaisesRegex(RuntimeError, "Synthetic generation failure"):
                pipeline.answer("q", prepared_context={"query_id": "test", "framework_version": "rev5"})
            event = json.loads(path.read_text())
            self.assertEqual(event["query_id"], "test")
            self.assertFalse(event["ok"])
            self.assertEqual(event["input_ids"], [[1, 2]])


if __name__ == "__main__":
    unittest.main()
