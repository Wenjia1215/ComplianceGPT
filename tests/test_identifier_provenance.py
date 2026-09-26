import unittest

from compliancegpt.pipeline.pipeline import _build_identifier_provenance


class IdentifierProvenanceTests(unittest.TestCase):
    def test_emits_ordered_positive_origins_and_window_membership(self):
        actual = _build_identifier_provenance(
            final_spans=[
                {"source_id": "a_smt", "span_text": "A"},
                {"source_id": "b_smt", "span_text": "B"},
                {"source_id": "c_smt", "span_text": "C"},
                {"source_id": "d_smt", "span_text": "D"},
            ],
            selector_ids=["a_smt"],
            fallback_ids=["b_smt"],
            hierarchy_ids=["c_smt"],
            rescue_ids=["d_smt"],
            evidence_window_ids=["a_smt", "b_smt", "d_smt"],
        )

        self.assertEqual(
            actual,
            [
                {"source_id": "a_smt", "origin": "selector", "in_evidence_window": True},
                {"source_id": "b_smt", "origin": "fallback", "in_evidence_window": True},
                {"source_id": "c_smt", "origin": "hierarchy", "in_evidence_window": False},
                {"source_id": "d_smt", "origin": "rescue", "in_evidence_window": True},
            ],
        )

    def test_rejects_missing_origin(self):
        with self.assertRaisesRegex(ValueError, "exactly one provenance origin"):
            _build_identifier_provenance(
                final_spans=[{"source_id": "a_smt", "span_text": "A"}],
                selector_ids=[],
                fallback_ids=[],
                hierarchy_ids=[],
                rescue_ids=[],
            )

    def test_rejects_multiple_origins(self):
        with self.assertRaisesRegex(ValueError, "exactly one provenance origin"):
            _build_identifier_provenance(
                final_spans=[{"source_id": "a_smt", "span_text": "A"}],
                selector_ids=["a_smt"],
                fallback_ids=[],
                hierarchy_ids=[],
                rescue_ids=["a_smt"],
            )

    def test_rejects_duplicate_final_identifier(self):
        with self.assertRaisesRegex(ValueError, "Duplicate final source_id"):
            _build_identifier_provenance(
                final_spans=[
                    {"source_id": "a_smt", "span_text": "A"},
                    {"source_id": "a_smt", "span_text": "A"},
                ],
                selector_ids=["a_smt"],
                fallback_ids=[],
                hierarchy_ids=[],
                rescue_ids=[],
            )


if __name__ == "__main__":
    unittest.main()
