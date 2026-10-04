import copy
import json
import tempfile
import unittest
from pathlib import Path

from answerer_comparison.matched_window_runner import FrozenCCSRetriever
from compliancegpt.pipeline.evidence_window import evidence_window_manifest
from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline
from compliancegpt.pipeline.profile_resolution import resolve_profile_answer
from compliancegpt.generator.verifier.verifier import verify_contract_validity, verify_answer


class ProfileResolutionTests(unittest.TestCase):
    def setUp(self):
        self.text = "Notify {{ insert: param, ac-01_odp.01 }} within {{ insert: param, ac-01_odp.02 }}."
        self.spans = [{"source_id": "ac-1_smt", "span_text": self.text}]
        self.profile = {"framework_version": "rev5", "odp_values": {
            "ac-01_odp.01": "Security Officer", "ac-01_odp.02": "24 hours"}}
        self.corpus = {"ac-1_smt": self.text}

    def contract(self, profile=None, spans=None):
        answer, required, status, record = resolve_profile_answer(
            spans or self.spans, self.profile if profile is None else profile, "rev5")
        return {"framework_version": "rev5", "resolution_policy": "FILL_FROM_PROFILE",
                "answer_text": answer, "odp_required_list": required, "status": status,
                "evidence_spans": copy.deepcopy(spans or self.spans), "profile_resolution": record}

    def verify(self, contract, profile=None, **kw):
        args = {"corpus": self.corpus, "org_profile": self.profile if profile is None else profile,
                "corpus_version": "rev5", "expected_resolution_policy": "FILL_FROM_PROFILE"}
        args.update(kw)
        return verify_contract_validity(contract, **args)

    def test_complete_profile_preserves_canonical_spans_and_passes_runtime(self):
        c = self.contract()
        self.assertEqual(c["answer_text"], "Notify Security Officer within 24 hours.")
        self.assertEqual(c["evidence_spans"], self.spans)
        self.assertEqual(c["status"], "OK")
        self.assertEqual(self.verify(c), (True, []))

    def test_original_failure_is_not_bypassed_without_resolution_record(self):
        c = self.contract()
        del c["profile_resolution"]
        passed, errors = self.verify(c)
        self.assertFalse(passed)
        self.assertIn("OKButUnresolvedODPPlaceholders", errors)
        self.assertIn("ProfileResolutionRecordMissing", errors)

    def test_partial_profile_requires_only_unresolved_keys(self):
        profile = copy.deepcopy(self.profile)
        del profile["odp_values"]["ac-01_odp.02"]
        c = self.contract(profile)
        self.assertEqual(c["odp_required_list"], ["ac-01_odp.02"])
        self.assertEqual(c["status"], "PARAMS_REQUIRED")
        self.assertEqual(self.verify(c, profile), (True, []))
        c["odp_required_list"] = []
        self.assertIn("ProfileUnresolvedListMismatch", self.verify(c, profile)[1])

    def test_wrong_or_unversioned_profiles_do_not_fill(self):
        for revision in ("rev4", "", "not-a-revision"):
            with self.subTest(revision=revision):
                profile = copy.deepcopy(self.profile)
                profile["framework_version"] = revision
                c = self.contract(profile)
                self.assertEqual(c["answer_text"], self.text)
                self.assertEqual(c["status"], "PARAMS_REQUIRED")
                self.assertEqual(c["profile_resolution"]["bindings"], [])
                self.assertEqual(self.verify(c, profile), (True, []))

    def test_literal_replacements_are_not_regex_backreferences(self):
        profile = copy.deepcopy(self.profile)
        profile["odp_values"]["ac-01_odp.01"] = r"C:\Policy\1\g<1>"
        c = self.contract(profile)
        self.assertIn(r"C:\Policy\1\g<1>", c["answer_text"])
        self.assertEqual(self.verify(c, profile), (True, []))

    def test_anonymous_assignment_stays_blocked(self):
        spans = copy.deepcopy(self.spans)
        spans[0]["span_text"] += " [ Assignment: organizational discretion ]."
        c = self.contract(spans=spans)
        self.assertEqual(c["odp_required_list"], ["__ASSIGNMENT_REQUIRED__"])
        self.assertEqual(c["status"], "PARAMS_REQUIRED")
        self.assertEqual(self.verify(c, corpus={"ac-1_smt": spans[0]["span_text"]}), (True, []))

    def test_supported_profile_shapes_and_zero_value(self):
        for container in ("odp_values", "odps", None):
            values = {"ac-01_odp.01": 0, "ac-01_odp.02": False}
            profile = {"framework_version": "rev5"}
            if container:
                profile[container] = values
            else:
                profile.update(values)
            c = self.contract(profile)
            self.assertEqual(c["answer_text"], "Notify 0 within False.")
            self.assertEqual(self.verify(c, profile), (True, []))

    def test_bad_and_placeholder_bearing_values_remain_unresolved(self):
        for value in (None, " ", [], {}, "{{ insert: param, new_odp }}", "[ Assignment: someone ]"):
            with self.subTest(value=value):
                profile = copy.deepcopy(self.profile)
                profile["odp_values"]["ac-01_odp.01"] = value
                c = self.contract(profile)
                self.assertIn("ac-01_odp.01", c["odp_required_list"])
                self.assertEqual(self.verify(c, profile), (True, []))

    def test_record_cannot_authorize_its_own_value_or_extra_prose(self):
        for mutation in ("value", "answer", "binding", "revision", "hash", "source", "span"):
            with self.subTest(mutation=mutation):
                c = self.contract()
                if mutation == "value":
                    c["answer_text"] = c["answer_text"].replace("Security Officer", "Unapproved Officer")
                    c["profile_resolution"]["bindings"][0]["value"] = "Unapproved Officer"
                elif mutation == "answer": c["answer_text"] += " Extra unsupported claim."
                elif mutation == "binding": c["profile_resolution"]["bindings"].pop()
                elif mutation == "revision": c["framework_version"] = "rev4"
                elif mutation == "hash": c["profile_resolution"]["profile_sha256"] = "0" * 64
                elif mutation == "source": c["evidence_spans"][0]["source_id"] = "unknown"
                elif mutation == "span": c["evidence_spans"][0]["span_text"] += " extra"
                self.assertFalse(self.verify(c)[0])

    def test_external_profile_corpus_and_revision_are_required(self):
        c = self.contract()
        for kwargs in ({"org_profile": None}, {"corpus": None}, {"corpus_version": None},
                       {"org_profile": {"framework_version": "rev5", "odp_values": {}}}):
            with self.subTest(kwargs=kwargs): self.assertFalse(self.verify(c, **kwargs)[0])

    def test_profile_cannot_be_removed_from_partial_contract_in_fill_mode(self):
        profile = copy.deepcopy(self.profile)
        del profile["odp_values"]["ac-01_odp.02"]
        c = self.contract(profile)
        del c["profile_resolution"]
        del c["resolution_policy"]
        self.assertIn("ProfileResolutionRecordMissing", self.verify(c, profile)[1])

    def test_offline_profile_check_uses_remaining_obligations(self):
        gold = {"id": "1", "control_id": "AC-1", "gold_control_path": "ac-1_smt",
                "gold_source_version": "rev5", "resolution_policy": "FILL_FROM_PROFILE",
                "odp_required": "ac-01_odp.01\nac-01_odp.02"}
        for drop in (False, True):
            profile = copy.deepcopy(self.profile)
            if drop: del profile["odp_values"]["ac-01_odp.02"]
            v = verify_answer(self.contract(profile), gold, self.corpus, org_profile=profile, corpus_version="rev5")
            self.assertTrue(v.is_pass, v.error_tags)

    def test_complete_pipeline_applies_profile_and_runtime_verification(self):
        class Config: _commit_hash = "frozen-test"
        class Model: config = Config()
        class Tokenizer:
            pad_token_id = 0
            eos_token_id = 1
            init_kwargs = {"_commit_hash": "frozen-test"}
        class Selector:
            def generate(self, *args):
                return {"status": "OK", "evidence_spans": [{"source_id": "ac-1_smt"}]}
        record = {"id": "ac-1_smt", "kind": "smt", "control_id": "AC-1", "text": self.text}
        window = evidence_window_manifest([record])
        context = {"question": "What does AC-1 require?", "framework_version": "rev5",
                   "retrieved_docs": [record], "evidence_window": [record],
                   "evidence_window_manifest": window,
                   "retrieval_meta": {"selected_controls": ["AC-1"], "primary_control": "AC-1"}}
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "odp.json"
            registry.write_text(json.dumps({}), encoding="utf-8")
            pipe = ComplianceGPTPipeline(framework_version="rev5", model_id="frozen-test",
                model_revision="frozen-test", shared_model=Model(), shared_tokenizer=Tokenizer(),
                generator_instance=Selector(), retriever_instance=FrozenCCSRetriever({"ac-1_smt": record}),
                use_qur=False, ccs_path=str(Path(temp)/"unused.jsonl"), odp_registry_path=str(registry),
                strict_ccs_assert=False, resolution_policy="FILL_FROM_PROFILE")
            pipe.org_profile = self.profile
            c = pipe.answer(context["question"], prepared_context=context)["contract"]
        self.assertEqual(c["status"], "OK")
        self.assertEqual(c["evidence_spans"], self.spans)
        self.assertEqual(c["answer_text"], "Notify Security Officer within 24 hours.")
        self.assertEqual(c["validity_check"], {"is_pass": True, "errors": []})


if __name__ == "__main__":
    unittest.main()
