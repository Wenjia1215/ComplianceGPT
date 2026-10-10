"""Check revision failures independently of model output and semantic reviews."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from answerer_comparison import strict_pass as v1
from answerer_comparison import strict_pass_v2 as v2
from compliancegpt.generator.verifier import verifier as legacy
from compliancegpt.generator.verifier import verifier_revision_v2 as revised
from compliancegpt.pipeline.profile_resolution import resolve_profile_answer


class RevisionValidationTests(unittest.TestCase):
    def fixture(self, revision="rev5", parameter=False):
        sid, pid = "ac-1_smt", "ac-01_odp.01"
        text = "Report findings." if not parameter else f"Report findings to {{{{ insert: param, {pid} }}}}."
        contract = {"framework_version": revision, "question": "What must be reported?",
                    "answer_text": text, "evidence_spans": [{"source_id": sid, "span_text": text}],
                    "status": "PARAMS_REQUIRED" if parameter else "OK",
                    "odp_required_list": [pid] if parameter else [],
                    "ask_list": [{"param_id": pid, "ask_prompt": "Who receives findings?"}] if parameter else [],
                    "primary_citation": sid, "all_citations": sid}
        corpus = {sid: text}
        records = {sid: {"id": sid, "kind": "smt", "text": text}}
        if parameter:
            corpus[pid] = "personnel or roles"
            records[pid] = {"id": pid, "kind": "odp", "text": "personnel or roles"}
        gold = {"id": "1", "control_id": "AC-1", "gold_source_version": "Revision " + revision[-1],
                "gold_control_path": sid, "odp_required": pid if parameter else "", "resolution_policy": "ASK"}
        return contract, corpus, records, gold

    def evaluate(self, revision, contract, records, gold, reviews=None, version=v2):
        return version.evaluate_contract(revision=revision, query_id="1", contract=contract,
                                         gold=gold, records=records, window_ids=["ac-1_smt"], reviews=reviews or {})

    def test_matching_revisions_pass_runtime_and_strict_on_both_catalogs(self):
        for revision in ("rev4", "rev5"):
            for parameter in (False, True):
                with self.subTest(revision=revision, parameter=parameter):
                    c, corpus, records, gold = self.fixture(revision, parameter)
                    self.assertEqual(revised.verify_contract_validity(c, corpus, corpus_version=revision), (True, []))
                    self.assertTrue(self.evaluate(revision, c, records, gold)["strict_pass"])

    def test_opposite_declaration_closes_the_legacy_gap_in_both_directions(self):
        for revision in ("rev4", "rev5"):
            for policy in ("ASK", "PRESERVE"):
                with self.subTest(revision=revision, policy=policy):
                    c, corpus, records, gold = self.fixture(revision, parameter=True)
                    c["resolution_policy"] = policy
                    gold["resolution_policy"] = policy
                    c["framework_version"] = "rev4" if revision == "rev5" else "rev5"
                    self.assertTrue(legacy.verify_contract_validity(c, corpus, corpus_version=revision)[0])
                    old = self.evaluate(revision, c, records, gold, version=v1)
                    new = self.evaluate(revision, c, records, gold)
                    self.assertTrue(old["strict_pass"])
                    self.assertFalse(new["strict_pass"])
                    self.assertFalse(new["declared_revision_pass"])
                    self.assertFalse(revised.verify_contract_validity(c, corpus, corpus_version=revision)[0])
                    self.assertTrue(any(e.startswith("FrameworkVersionMismatch:") for e in new["contract_errors"]))

    def test_missing_invalid_and_ambiguous_declarations_fail_closed(self):
        c, corpus, _, _ = self.fixture()
        for value in (None, "", "unknown", "rev6", "rev45", "Revision 4 / Revision 5", "prefix rev5", 5, True, [], {}):
            with self.subTest(value=value):
                altered = {**c, "framework_version": value}
                self.assertFalse(revised.verify_contract_validity(altered, corpus, corpus_version="rev5")[0])
        del c["framework_version"]
        self.assertIn("FrameworkVersionMissing", revised.verify_contract_validity(c, corpus, corpus_version="rev5")[1])

    def test_one_whole_supported_alias_can_identify_a_revision(self):
        c, corpus, _, _ = self.fixture()
        for value in ("rev5", "Revision 5", "Rev. 5", "r5", "5", " REV5 "):
            with self.subTest(value=value):
                c["framework_version"] = value
                self.assertEqual(revised.verify_contract_validity(c, corpus, corpus_version="rev5"), (True, []))

    def test_active_revision_is_required_and_cannot_be_inferred_from_the_contract(self):
        c, corpus, _, gold = self.fixture()
        for active in (None, "", "rev6", "rev45", "rev4/5", 5):
            with self.subTest(active=active):
                self.assertIn("ActiveCorpusRevisionMissingOrInvalid",
                              revised.verify_contract_validity(c, corpus, corpus_version=active)[1])
                self.assertFalse(revised.verify_answer(c, gold, corpus, corpus_version=active).is_pass)

    def test_reference_revision_must_match_the_active_corpus(self):
        c, corpus, _, gold = self.fixture()
        for value in ("Revision 4", "unknown", None):
            with self.subTest(value=value):
                changed = {**gold, "gold_source_version": value}
                self.assertFalse(revised.verify_answer(c, changed, corpus, corpus_version="rev5").is_pass)

    def test_namespace_alias_cannot_hide_the_opposite_revision(self):
        for revision in ("rev4", "rev5"):
            wrong = "rev4" if revision == "rev5" else "rev5"
            c, corpus, _, _ = self.fixture(revision)
            for prefix in (f"NIST_SP-800-53_{wrong}:", f"https://catalog.example/{wrong}/", f"{wrong}#",
                           f"NIST.SP.800-53r{wrong[-1]}.pdf#"):
                with self.subTest(revision=revision, prefix=prefix):
                    changed = copy.deepcopy(c)
                    changed["evidence_spans"][0]["source_id"] = prefix + "ac-1_smt"
                    self.assertTrue(legacy.verify_contract_validity(changed, corpus, corpus_version=revision)[0])
                    self.assertFalse(revised.verify_contract_validity(changed, corpus, corpus_version=revision)[0])

    def test_explicit_citation_labels_must_match_the_active_revision(self):
        c, corpus, _, _ = self.fixture()
        for field in ("primary_citation", "all_citations", "answer_text_with_citation", "answer_text_with_citations"):
            with self.subTest(field=field):
                c2 = {**c, field: "Citations: ac-1_smt (NIST SP 800-53 Rev. 4)"}
                self.assertFalse(revised.verify_contract_validity(c2, corpus, corpus_version="rev5")[0])
        self.assertFalse(revised.verify_contract_validity({**c, "all_citations": "rev6:ac-1_smt"}, corpus,
                                                         corpus_version="rev5")[0])

    def test_body_references_to_another_revision_are_not_metadata_declarations(self):
        c, _, _, _ = self.fixture()
        text = "Compare the requirements with Revision 4."
        c["answer_text"] = text
        c["evidence_spans"][0]["span_text"] = text
        c["answer_text_with_citations"] = text + "\n\nCitations: ac-1_smt (NIST SP 800-53 Rev. 5)"
        self.assertEqual(revised.verify_contract_validity(c, {"ac-1_smt": text}, corpus_version="rev5"), (True, []))

    def test_revision_agreement_applies_to_error_and_no_evidence_statuses(self):
        for status in ("ERROR", "NO_EVIDENCE"):
            c = {"framework_version": "rev5", "status": status, "answer_text": "",
                 "evidence_spans": [], "odp_required_list": []}
            self.assertEqual(revised.verify_contract_validity(c, {}, corpus_version="rev5"),
                             legacy.verify_contract_validity(c, {}, corpus_version="rev5"))
            passed, errors = revised.verify_contract_validity({**c, "framework_version": "rev4"}, {}, corpus_version="rev5")
            self.assertFalse(passed)
            self.assertTrue(any(e.startswith("FrameworkVersionMismatch:") for e in errors))

    def test_fill_policy_retains_its_external_profile_checks(self):
        for revision in ("rev4", "rev5"):
            c, corpus, _, _ = self.fixture(revision, parameter=True)
            profile = {"framework_version": revision, "odp_values": {"ac-01_odp.01": "reviewers"}}
            body, required, status, record = resolve_profile_answer(c["evidence_spans"], profile, revision)
            c.update(answer_text=body, odp_required_list=required, status=status,
                     resolution_policy="FILL_FROM_PROFILE", profile_resolution=record)
            self.assertTrue(revised.verify_contract_validity(c, corpus, profile, corpus_version=revision,
                                                             expected_resolution_policy="FILL_FROM_PROFILE")[0])
            self.assertFalse(revised.verify_contract_validity(c, corpus, {}, corpus_version=revision)[0])
            c["framework_version"] = "rev4" if revision == "rev5" else "rev5"
            self.assertFalse(revised.verify_contract_validity(c, corpus, profile, corpus_version=revision)[0])

    def test_v2_identity_binds_metadata_while_semantic_reviews_keep_v1_identity(self):
        c, _, records, gold = self.fixture()
        c["answer_text"] = "The findings must be reported."
        rid = v1.review_id("rev5", "1", c)
        review = {"rule_version": v1.RULE_VERSION, "review_id": rid,
                  "verdicts": {gate: "pass" for gate in v1.SEMANTIC_GATES},
                  "rationale": "The paraphrase retains the reporting duty.", "findings": []}
        result = self.evaluate("rev5", c, records, gold, {rid: review})
        self.assertTrue(result["strict_pass"])
        self.assertEqual(result["semantic_review_id"], rid)
        self.assertEqual(result["semantic_review_rule_version"], "strict-pass-v1")
        self.assertFalse(result["new_semantic_review"])
        opposite = {**c, "framework_version": "rev4"}
        self.assertEqual(v1.review_id("rev5", "1", opposite), rid)
        self.assertNotEqual(v2.review_id("rev5", "1", opposite), result["review_id"])
        failed = self.evaluate("rev5", opposite, records, gold, {rid: review})
        self.assertFalse(failed["strict_pass"])
        for gate in v1.SEMANTIC_GATES:
            self.assertEqual(failed[gate], result[gate])

    def test_inherited_assessment_cannot_change_the_answer_surface(self):
        c, _, records, gold = self.fixture()
        old = self.evaluate("rev5", c, records, gold, version=v1)
        with self.assertRaisesRegex(ValueError, "answer surface"):
            v2.upgrade_assessment(revision="rev5", query_id="1", contract={**c, "answer_text": "Other claim."},
                                  gold=gold, legacy=old)

    def test_verifier_metrics_and_old_scoring_are_unchanged_for_valid_metadata(self):
        c, corpus, records, gold = self.fixture()
        old = legacy.verify_answer(c, gold, corpus, corpus_version="rev5")
        new = revised.verify_answer(c, gold, corpus, corpus_version="rev5")
        self.assertEqual(old.metrics, new.metrics)
        self.assertEqual(old.error_tags, new.error_tags)
        before = self.evaluate("rev5", c, records, gold, version=v1)
        after = self.evaluate("rev5", c, records, gold)
        for key in ("strict_pass", "contract_errors", "contract_checks_pass", "exact_provenance", "complete_parameter_accounting"):
            self.assertEqual(before[key], after[key])

    def test_compliance_and_generative_paths_share_the_v2_runtime_checker(self):
        from compliancegpt.pipeline import pipeline
        from generative_answerer import pipeline as baseline
        self.assertIs(pipeline.verify_contract_validity, revised.verify_contract_validity)
        self.assertIs(baseline.verify_contract_validity, revised.verify_contract_validity)
        self.assertIs(pipeline.verify_answer, revised.verify_answer)
        self.assertIs(baseline.verify_answer, revised.verify_answer)

    def test_real_prepared_contexts_pass_through_both_answer_paths_without_inference(self):
        from answerer_comparison.matched_window_runner import FrozenCCSRetriever
        from compliancegpt.pipeline.evidence_window import evidence_window_manifest
        from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline
        from generative_answerer.pipeline import BaselineGenerativeRAGPipeline
        sid, text = "ac-1_smt", "Report findings."
        record = {"id": sid, "kind": "smt", "control_id": "AC-1", "text": text}

        class Selector:
            def generate(self, *args):
                return {"status": "OK", "evidence_spans": [{"source_id": sid}]}

        class Answerer:
            def generate(self, *args):
                return {"status": "OK", "answer_text": text, "cited_source_ids": [sid], "odp_required_list": []}

        with tempfile.TemporaryDirectory() as tmp:
            ccs, registry = Path(tmp) / "ccs.jsonl", Path(tmp) / "registry.json"
            ccs.write_text(json.dumps(record) + "\n")
            registry.write_text("{}")
            for revision in ("rev4", "rev5"):
                contract, _, _, gold = self.fixture(revision)
                context = {"question": contract["question"], "framework_version": revision,
                           "retrieved_docs": [record], "evidence_window": [record],
                           "evidence_window_manifest": evidence_window_manifest([record]),
                           "retrieval_meta": {"selected_controls": ["AC-1"], "primary_control": "AC-1"}}
                kwargs = {"framework_version": revision, "shared_model": SimpleNamespace(config=SimpleNamespace(_commit_hash="fixture")),
                          "shared_tokenizer": SimpleNamespace(pad_token_id=0, eos_token_id=1, init_kwargs={"_commit_hash": "fixture"}),
                          "generator_instance": Selector(), "retriever_instance": FrozenCCSRetriever({sid: record}),
                          "use_qur": False, "strict_ccs_assert": False, "ccs_path": str(ccs),
                          "odp_registry_path": str(registry), "resolution_policy": "ASK", "enable_hierarchy_closure": False}
                with patch("generative_answerer.pipeline.BaselineGenerativeAnswerer", return_value=Answerer()):
                    pipelines = [ComplianceGPTPipeline(**kwargs), BaselineGenerativeRAGPipeline(**kwargs)]
                for pipeline in pipelines:
                    with self.subTest(revision=revision, path=type(pipeline).__name__):
                        result = pipeline.answer(contract["question"], prepared_context=copy.deepcopy(context),
                                                 gold_row=gold, run_verify=True)["contract"]
                        self.assertEqual(result["validity_check"], {"is_pass": True, "errors": []})
                        self.assertTrue(result["verifier_pass"])
                        self.assertEqual(result["revision_validation_rule"], revised.REVISION_RULE_VERSION)


if __name__ == "__main__":
    unittest.main()
