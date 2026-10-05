#!/usr/bin/env python3
"""Audit the returned immutable natural-question package without model inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
REPO = FOLDER.parents[2]
sys.path[:0] = [str(FOLDER), str(REPO / 'src'), str(REPO)]

from review_and_freeze import canonical_sha, read_jsonl, sha, validate_registration
from answerer_comparison.matched_window_runner import validate_paired_outputs, validate_prepared_context
from run_natural_questions import validate_context_authority
from score_results import score_folder


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(root, notebook, replay, report_path):
    root = root.resolve()
    recorded = json.loads((root / 'SHA256SUMS.json').read_text())
    actual = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
              if p.is_file() and p.name != 'SHA256SUMS.json'}
    require(recorded == actual, 'Archive files do not match the complete checksum manifest')
    config = json.loads((root / 'run_config.json').read_text())
    signature = config['signature']
    require(canonical_sha(signature) == config['signature_sha256'], 'Run signature digest mismatch')
    protocol, questions, labels, registration = validate_registration()
    require(signature['registration_sha256'] == sha(FOLDER / 'registration.json'), 'Wrong registration')
    require(signature['protocol_sha256'] == sha(FOLDER / 'protocol.json'), 'Wrong protocol')
    require(signature['code_sha256'] == registration['code_sha256'], 'Wrong executable fingerprint')
    require(signature['models'] == protocol['models'] and signature['inputs'] == protocol['inputs'],
            'Wrong registered models or catalog inputs')
    snapshot = root / 'source_snapshot'
    snapshot_study = snapshot / FOLDER.relative_to(REPO)
    require(sha(snapshot_study / 'registration.json') == signature['registration_sha256'],
            'Snapshot registration differs from runtime')
    for name, expected in registration['file_sha256'].items():
        require(sha(snapshot_study / name) == expected, f'Snapshot input differs: {name}')
    for relative, expected in registration['code_sha256'].items():
        require(sha(snapshot / relative) == expected, f'Snapshot executable differs: {relative}')
        public_bytes = subprocess.check_output(['git', 'show', signature['source_commit'] + ':' + relative], cwd=REPO)
        require(hashlib.sha256(public_bytes).hexdigest() == expected, f'Published executable differs: {relative}')
    original = json.loads((root / 'prior_attempt_provenance.json').read_text())
    for relative, expected in original['file_sha256'].items():
        require(sha(root / 'prior_attempt/result_files' / relative) == expected,
                f'Prior attempt bytes changed: {relative}')
    require(not list((root / 'prior_attempt/result_files').rglob('generation_calls.jsonl'))
            and not list((root / 'prior_attempt/result_files/contracts').rglob('*.csv')),
            'Earlier attempt unexpectedly contains generation artifacts')
    require(sha(root / 'prior_attempt/result_files/contexts/rev4.jsonl') == sha(root / 'contexts/rev4.jsonl'),
            'Repeated retrieval changed the original five contexts')
    by_question = {q['query_id']: q for q in questions}
    by_label = {r['query_id']: r for r in labels}
    contexts = {}
    locks = json.loads((root / 'context_file_hashes.json').read_text())
    pairs = json.loads((root / 'paired_identity_audit.json').read_text())
    outputs = {}
    for rev in ['rev4', 'rev5']:
        records = {r['id']: r for r in read_jsonl(REPO / protocol['inputs'][rev]['ccs']['path'])}
        path = root / 'contexts' / (rev + '.jsonl')
        require(sha(path) == locks[rev], 'Context file lock mismatch')
        captured = read_jsonl(path)
        expected = [q for q in questions if q['framework_version'] == rev]
        require([c['query_id'] for c in captured] == [q['query_id'] for q in expected], 'Context order mismatch')
        for context, question in zip(captured, expected):
            validate_prepared_context(context)
            validate_context_authority(context, records)
            require(context['question'] == question['question'], 'Context question mismatch')
            contexts[context['query_id']] = context
        fresh_pair = validate_paired_outputs(root / 'contracts' / (rev + '_compliancegpt.csv'),
                                            root / 'contracts' / (rev + '_generative_baseline.csv'))
        require(fresh_pair == pairs[rev], 'Recorded paired identity audit differs')
        for system in ['compliancegpt', 'generative_baseline']:
            with (root / 'contracts' / (rev + '_' + system + '.csv')).open(newline='') as f:
                rows = list(csv.DictReader(f))
            require([r['query_id'] for r in rows] == [q['query_id'] for q in expected], 'Outcome row order mismatch')
            for row in rows:
                key = (row['query_id'], system)
                require(key not in outputs, 'Duplicate final answer')
                outputs[key] = row
    calls = read_jsonl(root / 'generation_calls.jsonl')
    systems = {'ComplianceGPTPipeline': 'compliancegpt', 'BaselineGenerativeRAGPipeline': 'generative_baseline'}
    counts = Counter()
    decoding = {}
    for call in calls:
        key = (call['query_id'], systems[call['system']])
        require(key in outputs and call['context_sha256'] == contexts[key[0]]['context_sha256'],
                'Generation call has an unknown query or mismatched context')
        require(call['ok'] is True, 'Generation exception requires separate retained-failure audit')
        require(call['output_ids'][0][:len(call['input_ids'][0])] == call['input_ids'][0],
                'Captured output is not an extension of its input token sequence')
        require(len(call['attention_mask'][0]) == len(call['input_ids'][0]), 'Input attention-mask length differs')
        settings = call['generation_config']
        budget = 512 if key[1] == 'compliancegpt' else 640
        require(settings['do_sample'] is False and settings['num_beams'] == 1
                and settings['repetition_penalty'] == 1.05 and settings['max_new_tokens'] == budget,
                'Generation configuration differs from the frozen answer-path defaults')
        decoding[key[1]] = {'do_sample': False, 'num_beams': 1, 'repetition_penalty': 1.05,
                            'max_new_tokens': budget}
        counts[key] += 1
    require(set(counts) == set(outputs) and len(outputs) == 40, 'Raw calls or paired outputs are incomplete')
    require(all(n <= 3 for n in counts.values()), 'Generation count exceeds the registered parsing-retry allowance')
    with (root / 'post_run_semantic_review.csv').open(newline='') as f:
        manual = list(csv.DictReader(f))
    require(len(manual) == 40 and all(not r[k] for r in manual for k in
            ['scope_appropriate', 'responsive_to_entire_question', 'unsupported_implementation_or_legal_claim', 'reviewer']),
            'The author review is not wholly pending; preserve and audit submitted judgments separately')
    nb = json.loads(notebook.read_text())
    executed = [c for c in nb['cells'] if c['cell_type'] == 'code']
    require(len(executed) == 7 and all(c.get('execution_count') is not None for c in executed),
            'Executed notebook does not contain all seven executed code cells')
    require(not any(o.get('output_type') == 'error' for c in executed for o in c.get('outputs', [])),
            'Executed notebook retains a terminal error')
    require(signature['source_commit'] in ''.join(''.join(o.get('text', [])) for c in executed
            for o in c.get('outputs', []) if o.get('output_type') == 'stream'),
            'Notebook output does not record the repaired execution identity')
    require(not replay.exists(), 'Use a new replay directory to preserve audit provenance')
    shutil.copytree(root, replay)
    score_folder(replay)
    scoring_files = ['summary.json', 'per_question_outcomes.jsonl', 'SUMMARY.md', 'post_run_semantic_review.csv']
    require(all(sha(root / name) == sha(replay / name) for name in scoring_files),
            'Offline scoring replay differs from submitted outputs')
    cases = []
    for question in questions:
        qid = question['query_id']
        for system in ['compliancegpt', 'generative_baseline']:
            contract = json.loads(outputs[(qid, system)]['contract_json'])
            cases.append({'query_id': qid, 'system': system, 'question': question['question'],
                'source_url': question['source_url'], 'framework_version': question['framework_version'],
                'author_reference': by_label[qid], 'contract': contract,
                'raw_generation_calls': counts[(qid, system)]})
    report = {'status': 'technical_identity_and_scoring_audit_passed',
        'source_commit': signature['source_commit'], 'registration_sha256': signature['registration_sha256'],
        'notebook_sha256': sha(notebook), 'checked_archive_files': len(actual),
        'questions': 20, 'paired_answer_outputs': 40, 'raw_generation_calls': len(calls),
        'calls_by_system': {s: sum(n for (q, path), n in counts.items() if path == s)
                           for s in ['compliancegpt', 'generative_baseline']},
        'additional_calls_by_question': {q + '/' + s: n - 1 for (q, s), n in counts.items() if n > 1},
        'repeated_first_five_contexts_byte_identical': True,
        'all_original_code_and_input_fingerprints_verified': True,
        'paired_model_and_evidence_identities_verified': True,
        'decoding_settings_verified': decoding,
        'generation_input_token_range': [min(len(c['input_ids'][0]) for c in calls),
                                         max(len(c['input_ids'][0]) for c in calls)],
        'generation_new_token_range': [min(len(c['output_ids'][0])-len(c['input_ids'][0]) for c in calls),
                                       max(len(c['output_ids'][0])-len(c['input_ids'][0]) for c in calls)],
        'offline_scoring_replayed_exactly': scoring_files,
        'runtime': {k: signature[k] for k in ['python', 'gpu', 'gpu_memory_bytes', 'cuda', 'packages']},
        'scope_counts': dict(Counter(r['answerability'] for r in labels)),
        'post_run_author_review_rows_pending': 40, 'independent_correctness_validated': False,
        'model_inference_during_audit': False}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    report_path.with_name('review_cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, required=True)
    parser.add_argument('--notebook', type=Path, required=True)
    parser.add_argument('--replay-dir', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    audit(args.results_dir, args.notebook, args.replay_dir, args.report)
