"""Review-date edge cases and integrity of the revised pre-inference inputs."""
import importlib.util
import json
import pathlib
import unittest
from collections import Counter

FOLDER = pathlib.Path(__file__).resolve().parents[1] / "experiments/external_validity/natural_questions_v2"
SPEC = importlib.util.spec_from_file_location("natural_review_v2_test", FOLDER / "review_and_freeze.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ExcelReviewDates(unittest.TestCase):
    def test_existing_serial_keeps_utc_time(self):
        self.assertEqual(review.excel_utc_timestamp("46300.607511574075"),
                         "2026-10-05T14:34:49.000Z")

    def test_1904_workbook_date_system(self):
        self.assertEqual(review.excel_utc_timestamp("44838.607511574075", date1904=True),
                         "2026-10-05T14:34:49.000Z")

    def test_invalid_serials_are_not_today(self):
        for value in ["", "not a date", "NaN", "Infinity", "-1", "999999999999"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.excel_utc_timestamp(value)


class RegisteredReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.questions, cls.labels, cls.manifest = review.validate_registration()

    def test_all_twenty_stay_in_sample_with_small_eligible_subsets(self):
        self.assertEqual(len(self.questions), 20)
        self.assertEqual(Counter(r["answerability"] for r in self.labels),
                         Counter(full=3, partial=12, outside=5))
        self.assertEqual(Counter(r["odp_applicability"] for r in self.labels),
                         Counter(required=2, not_required=13, not_applicable=5))
        self.assertTrue(all(r["reviewer_name"] == "Wenjia" and not r["independent_expert_review"]
                            for r in self.labels))

    def test_reference_labels_are_absent_from_model_input(self):
        self.assertEqual(len({q["source_url"] for q in self.questions}), 20)
        expected = {"query_id", "question", "question_sha256", "framework_version",
                    "source_url", "source_posted_date"}
        self.assertTrue(all(set(q) == expected for q in self.questions))

    def test_corrected_text_has_new_identity_and_matches_registration(self):
        log = json.loads((FOLDER / "SOURCE_CORRECTIONS.json").read_text())
        by_id = {q["query_id"]: q for q in self.questions}
        self.assertEqual([r["query_id"] for r in log["corrections"]], ["NQ03", "NQ12", "NQ16"])
        for row in log["corrections"]:
            self.assertNotEqual(row["previous_question_sha256"], row["corrected_question_sha256"])
            self.assertEqual(by_id[row["query_id"]]["question_sha256"], row["corrected_question_sha256"])
        self.assertTrue(log["no_model_outcomes_observed"])


if __name__ == "__main__":
    unittest.main()
