# -*- coding: utf-8 -*-
"""Regression tests for gold-independent contract validation."""

import unittest

from compliancegpt.generator.verifier.verifier import verify_contract_validity


class ContractValidityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_id = "ac-1_smt"
        self.source_text = (
            "The organization reviews the policy "
            "{{ insert: param, ac-01_odp.01 }}."
        )
        self.corpus = {self.source_id: self.source_text}

    def test_valid_params_required_contract_passes(self) -> None:
        contract = {
            "answer_text": self.source_text,
            "evidence_spans": [
                {"source_id": self.source_id, "span_text": self.source_text}
            ],
            "status": "PARAMS_REQUIRED",
            "odp_required_list": ["ac-01_odp.01"],
        }

        is_pass, errors = verify_contract_validity(contract, corpus=self.corpus)

        self.assertTrue(is_pass)
        self.assertEqual(errors, [])

    def test_unknown_source_id_fails(self) -> None:
        contract = {
            "answer_text": "Unsupported text.",
            "evidence_spans": [
                {"source_id": "missing_smt", "span_text": "Unsupported text."}
            ],
            "status": "OK",
            "odp_required_list": [],
        }

        is_pass, errors = verify_contract_validity(contract, corpus=self.corpus)

        self.assertFalse(is_pass)
        self.assertIn("UnknownSourceId", errors)

    def test_nonverbatim_span_fails(self) -> None:
        contract = {
            "answer_text": "A model-written paraphrase.",
            "evidence_spans": [
                {"source_id": self.source_id, "span_text": "A model-written paraphrase."}
            ],
            "status": "OK",
            "odp_required_list": [],
        }

        is_pass, errors = verify_contract_validity(contract, corpus=self.corpus)

        self.assertFalse(is_pass)
        self.assertIn("SpanNotVerbatim", errors)

    def test_ok_with_unresolved_placeholder_fails(self) -> None:
        contract = {
            "answer_text": self.source_text,
            "evidence_spans": [
                {"source_id": self.source_id, "span_text": self.source_text}
            ],
            "status": "OK",
            "odp_required_list": [],
        }

        is_pass, errors = verify_contract_validity(contract, corpus=self.corpus)

        self.assertFalse(is_pass)
        self.assertIn("OKButUnresolvedODPPlaceholders", errors)

    def test_empty_no_evidence_contract_passes(self) -> None:
        contract = {
            "answer_text": "",
            "evidence_spans": [],
            "status": "NO_EVIDENCE",
            "odp_required_list": [],
        }

        is_pass, errors = verify_contract_validity(contract, corpus=self.corpus)

        self.assertTrue(is_pass)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
