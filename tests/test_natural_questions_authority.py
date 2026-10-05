"""Authority checks use real CCS inventories and production record normalization."""
import copy
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

from answerer_comparison.matched_window_runner import build_prepared_context, validate_prepared_context
from compliancegpt.retriever.retriever_s7 import load_all_records_by_id_jsonl


ROOT = pathlib.Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'experiments/external_validity/natural_questions_v2'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = load_module('authority_review_v2', FOLDER / 'review_and_freeze.py')
with patch.dict(sys.modules, {'review_and_freeze': review}):
    runner = load_module('authority_runner_v2', FOLDER / 'run_natural_questions.py')


class CanonicalEvidenceAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        protocol = json.loads((FOLDER / 'protocol.json').read_text())
        cls.raw, cls.runtime = {}, {}
        for rev, inputs in protocol['inputs'].items():
            path = ROOT / inputs['ccs']['path']
            cls.raw[rev] = {r['id']: r for r in review.read_jsonl(path)}
            cls.runtime[rev] = load_all_records_by_id_jsonl(str(path))

    def test_all_15839_real_runtime_records_pass_both_authority_fields(self):
        self.assertEqual(sum(len(rows) for rows in self.raw.values()), 15839)
        for rev in ['rev4', 'rev5']:
            with self.subTest(revision=rev):
                raw, runtime = self.raw[rev], self.runtime[rev]
                self.assertEqual(set(raw), set(runtime))
                self.assertTrue(all(raw[k]['text'] == runtime[k]['text']
                                    and raw[k]['kind'] == runtime[k]['kind'] for k in raw))
                self.assertTrue(all(raw[k]['control_id'] != runtime[k]['control_id'] for k in raw))
                docs = list(runtime.values())
                runner.validate_context_authority({'query_id': 'ALL-CATALOG-RECORDS',
                    'retrieved_docs': docs, 'evidence_window': docs}, raw)

    def test_actual_enhancement_notation_is_equivalent(self):
        raw = self.raw['rev4']['si-2.2_smt']
        doc = self.runtime['rev4']['si-2.2_smt']
        self.assertEqual(raw['control_id'], 'si-2.2')
        self.assertEqual(doc['control_id'], 'SI-2(2)')
        runner.validate_context_authority({'retrieved_docs': [doc], 'evidence_window': [doc]},
                                          self.raw['rev4'])

    def test_altered_id_text_kind_and_control_still_fail_in_either_field(self):
        for field in ['retrieved_docs', 'evidence_window']:
            for key, value in [('id', 'invented_source'), ('text', 'A different duty.'),
                               ('kind', 'gdn'), ('control_id', 'SI-2(3)')]:
                with self.subTest(field=field, key=key):
                    doc = dict(self.runtime['rev4']['si-2.2_smt'], **{key: value})
                    with self.assertRaises(ValueError):
                        runner.validate_context_authority({field: [doc]}, self.raw['rev4'])

    def test_boundary_and_internal_text_changes_are_not_normalized_away(self):
        doc = self.runtime['rev4']['si-2.2_smt']
        for text in [' ' + doc['text'], doc['text'] + '\n', doc['text'].replace(' ', '  ', 1)]:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'text'):
                    runner.validate_context_authority({'retrieved_docs': [dict(doc, text=text)]},
                                                      self.raw['rev4'])

    def context(self):
        doc = self.runtime['rev4']['si-2.2_smt']
        contract = {'question': 'Synthetic authority regression fixture', 'debug': {
            'retrieval_meta': {'selected_controls': [doc['control_id']],
                'selected_clause_ids_by_control': {doc['control_id']: [doc['id']]},
                'n_docs': 1}, 'query_plan': {'rewrites': []}}}
        return build_prepared_context(query_id='AUTHORITY-TEST', framework_version='rev4',
                                      contract=contract, ccs_by_id=self.runtime['rev4'])

    def test_real_prepared_context_passes_hash_and_raw_catalog_authority(self):
        context = self.context()
        self.assertEqual(len(context['evidence_window']), 1)
        validate_prepared_context(context)
        runner.validate_context_authority(context, self.raw['rev4'])

    def test_self_consistent_rehashed_tampering_still_fails_authority(self):
        context = self.context()
        for field in ['retrieved_docs', 'evidence_window']:
            context[field][0]['text'] = 'Tampered duty with a self-consistent context hash.'
        from compliancegpt.pipeline.evidence_window import evidence_window_manifest
        context['evidence_window_manifest'] = evidence_window_manifest(context['evidence_window'])
        unhashed = {k: v for k, v in context.items() if k != 'context_sha256'}
        context['context_sha256'] = review.canonical_sha(unhashed)
        validate_prepared_context(context)
        with self.assertRaisesRegex(ValueError, 'text'):
            runner.validate_context_authority(context, self.raw['rev4'])

    def test_authority_validation_does_not_rewrite_records_or_context(self):
        context = self.context()
        records = {'si-2.2_smt': copy.deepcopy(self.raw['rev4']['si-2.2_smt'])}
        before = copy.deepcopy((context, records))
        runner.validate_context_authority(context, records)
        self.assertEqual((context, records), before)


if __name__ == '__main__':
    unittest.main()
