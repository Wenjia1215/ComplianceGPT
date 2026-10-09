"""Evaluation-only regression tests; no generation or external services."""

import copy
import unittest

from answerer_comparison.strict_pass import (
    RULE_VERSION, SEMANTIC_GATES, evaluate_contract,
    full_retention_certificate, mechanical_checks, normalize_odp_id,
    parameter_inventory, resolve_parameter_id, review_id,
)


class StrictPassTests(unittest.TestCase):
    def setUp(self):
        self.sid = "ac-1_smt"
        self.text = "Review access decisions and report findings."
        self.records = {self.sid: {"id": self.sid, "kind": "smt", "text": self.text}}
        self.gold = {
            "id": "1", "control_id": "AC-1", "gold_source_version": "Revision 5",
            "gold_control_path": self.sid, "odp_required": "", "resolution_policy": "ASK",
        }
        self.contract = {
            "question": "What must the organization review and report?",
            "answer_text": "Review access decisions; report the findings.",
            "evidence_spans": [{"source_id": self.sid, "span_text": self.text}],
            "status": "OK", "odp_required_list": [], "ask_list": [],
        }

    def review(self, contract=None, gate=None, verdict="fail", **overrides):
        contract = contract or self.contract
        verdicts = {g: "pass" for g in SEMANTIC_GATES}
        findings = []
        if gate:
            verdicts[gate] = verdict
            findings = [{
                "gate": gate, "reason": "The required reporting action is not expressed.",
                "answer_excerpt": contract["answer_text"],
                "references": [{"source_id": self.sid, "excerpt": self.text}],
            }]
        value = {
            "rule_version": RULE_VERSION, "review_id": review_id("rev5", "1", contract),
            "verdicts": verdicts, "rationale": "Compare the review and reporting actions.",
            "findings": findings,
        }
        value.update(overrides)
        return {value["review_id"]: value}

    def evaluate(self, reviews, contract=None):
        return evaluate_contract(
            revision="rev5", query_id="1", contract=contract or self.contract,
            gold=self.gold, records=self.records, window_ids=list(self.records), reviews=reviews,
        )

    def add_parameter(self, pid, definition):
        self.records[pid] = {"id": pid, "kind": "odp", "text": pid + " " + definition}

    def test_correct_paraphrase_can_pass_without_copying(self):
        self.assertFalse(full_retention_certificate(self.contract, self.gold, self.records))
        result = self.evaluate(self.review())
        self.assertTrue(result["contract_checks_pass"])
        self.assertTrue(result["strict_pass"])
        self.assertEqual(result["review_method"], "source_inspection")

    def test_canonical_auxiliary_span_does_not_rescue_omitted_body(self):
        self.contract["answer_text"] = "Review access decisions."
        result = self.evaluate(self.review(gate="answer_coverage"))
        self.assertTrue(result["contract_checks_pass"])
        self.assertFalse(result["strict_pass"])

    def test_unused_citation_can_fail_despite_verbatim_span(self):
        self.contract["answer_text"] = "Review access decisions."
        child = "ac-1_smt.b"
        self.records[child] = {"id": child, "kind": "smt", "text": "Report findings."}
        self.contract["evidence_spans"].append({"source_id": child, "span_text": "Report findings."})
        reviews = self.review(gate="citation_use")
        finding = next(iter(reviews.values()))["findings"][0]
        finding["references"] = [{"source_id": child, "excerpt": "Report findings."}]
        result = self.evaluate(reviews)
        self.assertTrue(result["contract_checks_pass"])
        self.assertEqual(result["citation_use"], "fail")
        self.assertFalse(result["strict_pass"])

    def test_complete_retention_proves_body_only(self):
        self.contract["answer_text"] = self.text
        result = self.evaluate({})
        self.assertTrue(result["full_retention_certificate"])
        self.assertTrue(result["strict_pass"])

    def test_parent_text_cannot_rescue_missing_gold_child_id(self):
        self.contract["answer_text"] = self.text
        child = "ac-1_smt.a"
        self.records[child] = {"id": child, "kind": "smt", "text": "Review access decisions"}
        self.gold["gold_control_path"] = child
        result = self.evaluate({})
        self.assertFalse(result["contract_checks_pass"])
        self.assertFalse(result["strict_pass"])

    def test_clarification_value_domain_is_not_scored(self):
        pid = "ac-01_odp.01"
        self.add_parameter(pid, "personnel or roles")
        self.text = "Report findings to {{ insert: param, ac-01_odp.01 }}."
        self.records[self.sid]["text"] = self.text
        self.gold["odp_required"] = pid
        self.contract.update(answer_text=self.text, status="PARAMS_REQUIRED", odp_required_list=[pid])
        self.contract["evidence_spans"][0]["span_text"] = self.text
        self.contract["ask_list"] = [{"param_id": pid, "ask_prompt": "Answer with a duration.", "data_type": "duration"}]
        result = self.evaluate({})
        self.assertTrue(result["strict_pass"])
        self.assertNotIn("clarification_domains", result)
        self.assertNotIn("extended_strict_pass", result)

    def test_union_includes_body_and_all_spans(self):
        first, second = "ac-01_odp.01", "ac-01_odp.02"
        self.add_parameter(first, "frequency")
        self.add_parameter(second, "personnel or roles")
        self.records[self.sid]["text"] = "Review {{ insert: param, ac-01_odp.01 }} and notify {{ insert: param, ac-01_odp.02 }}."
        self.contract.update(
            answer_text="Review {{ insert: param, ac-01_odp.01 }}.", status="PARAMS_REQUIRED",
            odp_required_list=[first], ask_list=[{"param_id": first, "ask_prompt": "Which recurrence interval?"}],
        )
        self.contract["evidence_spans"][0]["span_text"] = self.records[self.sid]["text"]
        self.gold["odp_required"] = first
        result = self.evaluate(self.review())
        self.assertTrue(result["contract_checks_pass"])
        self.assertFalse(result["complete_parameter_accounting"])
        self.assertFalse(result["strict_pass"])

    def test_exact_parent_and_enhancement_parameters_are_not_merged(self):
        first, second = "ac-02_odp.01", "ac-2.1_odp"
        self.assertEqual(normalize_odp_id(first), normalize_odp_id(second))
        self.add_parameter(first, "personnel or roles")
        self.add_parameter(second, "time period")
        inventory = parameter_inventory(self.records)
        self.assertEqual(resolve_parameter_id(first, inventory), first)
        self.assertEqual(resolve_parameter_id(second, inventory), second)
        self.contract["answer_text"] = "{{ insert: param, ac-02_odp.01 }} {{ insert: param, ac-2.1_odp }}"
        self.contract.update(status="PARAMS_REQUIRED", odp_required_list=[first])
        checks = mechanical_checks(self.contract, self.records, list(self.records))
        self.assertFalse(checks["complete_parameter_accounting"])

    def test_exact_provenance_checks_window_and_duplicate_ids(self):
        self.contract["evidence_spans"].append(copy.deepcopy(self.contract["evidence_spans"][0]))
        checks = mechanical_checks(self.contract, self.records, [])
        self.assertFalse(checks["exact_provenance"])
        self.assertIn("DuplicateEvidenceId", checks["provenance_errors"])
        self.assertIn("OutsideFrozenEvidenceWindow:ac-1_smt", checks["provenance_errors"])

    def test_system_identity_does_not_change_review_fingerprint(self):
        other = copy.deepcopy(self.contract)
        other.update(system="another", model="another", debug={"score": 100}, verifier_pass=False)
        self.assertEqual(review_id("rev5", "1", self.contract), review_id("rev5", "1", other))

    def test_changed_answer_invalidates_previous_review(self):
        reviews = self.review()
        self.contract["answer_text"] = "Review only."
        with self.assertRaisesRegex(ValueError, "Missing semantic review"):
            self.evaluate(reviews)

    def test_noncanonical_finding_is_rejected(self):
        reviews = self.review(gate="claim_faithfulness")
        next(iter(reviews.values()))["findings"][0]["references"][0]["excerpt"] = "Not in the source."
        with self.assertRaisesRegex(ValueError, "source excerpt is not canonical"):
            self.evaluate(reviews)

    def test_uncertain_judgment_has_no_strict_credit(self):
        result = self.evaluate(self.review(gate="parameter_semantics", verdict="uncertain"))
        self.assertTrue(result["contract_checks_pass"])
        self.assertFalse(result["strict_pass"])
        self.assertTrue(result["semantic_uncertain"])

    def test_stale_rule_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Stale or mismatched"):
            self.evaluate(self.review(rule_version="old-rubric"))

    def test_empty_body_receives_no_strict_credit(self):
        self.contract["answer_text"] = ""
        result = self.evaluate(self.review())
        self.assertFalse(result["exact_provenance"])
        self.assertFalse(result["strict_pass"])


if __name__ == "__main__":
    unittest.main()
