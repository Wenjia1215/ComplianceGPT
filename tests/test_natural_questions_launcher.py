"""Exercise the launcher layout against the unchanged runner checkpoint guard."""
import ast
import contextlib
import io
import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDY = pathlib.Path('experiments/external_validity/natural_questions_v2')
NOTEBOOK = json.loads((ROOT / STUDY / 'Batch_Natural_Questions_v2.ipynb').read_text())
MAIN_CELL = ''.join(NOTEBOOK['cells'][6]['source'])
SETUP = ast.parse(''.join(NOTEBOOK['cells'][1]['source']))
SOURCE_COMMIT = next(ast.literal_eval(node.value) for node in SETUP.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'SOURCE_COMMIT' for t in node.targets))
LOG_NAMES = {'LAUNCHER_LOG_DIR', 'CONSOLE_LOG', 'LAUNCHER_LOG'}
LOG_SETUP = [node for node in SETUP.body
             if (isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id in LOG_NAMES for t in node.targets))
             or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Attribute)
                 and isinstance(node.value.func.value, ast.Name)
                 and node.value.func.value.id == 'LAUNCHER_LOG_DIR'
                 and node.value.func.attr == 'mkdir')]
RUNNER = ast.parse((ROOT / STUDY / 'run_natural_questions.py').read_text())
GUARD = next(node for node in ast.walk(RUNNER)
             if isinstance(node, ast.If) and isinstance(node.test, ast.Call)
             and isinstance(node.test.func, ast.Attribute)
             and isinstance(node.test.func.value, ast.Name)
             and node.test.func.value.id == 'config_path'
             and node.test.func.attr == 'exists')
GUARD_CODE = compile(ast.Module(body=[GUARD], type_ignores=[]), '<frozen runner guard>', 'exec')


class LauncherLogLayout(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = pathlib.Path(self.temp.name) / 'results'
        self.output.mkdir()
        self.calls = []
        self.namespace = {
            'Path': pathlib.Path, 'OUTPUT_DIR': self.output,
            'SOURCE_COMMIT': SOURCE_COMMIT,
            'datetime': datetime, 'timezone': timezone, 'json': json, 'shutil': shutil,
            'EXPERIMENT_PYTHON': '/isolated/python', 'STUDY_RELATIVE': STUDY,
            'REPO_DIR': ROOT, 'run_logged': self.run_logged,
        }
        exec(compile(ast.Module(body=LOG_SETUP, type_ignores=[]), '<launcher setup>', 'exec'),
             self.namespace)

    def event_bytes(self, command=None, return_code=0):
        return (json.dumps({'command': command or ['git', 'show'], 'cwd': str(ROOT),
                           'started_at_utc': '2026-10-05T16:00:00+00:00',
                           'return_code': return_code,
                           'finished_at_utc': '2026-10-05T16:00:01+00:00'}) + '\n').encode()

    def frozen_guard(self):
        namespace = {
            'config_path': self.output / 'run_config.json', 'output': self.output,
            'identity': 'registered-test-runtime', 'signature': {'unchanged': True},
            'public_url': 'registered-before-inference',
            'datetime': datetime, 'timezone': timezone, 'json': json,
            'write_json': lambda path, value: path.write_text(json.dumps(value)),
        }
        exec(GUARD_CODE, namespace)

    def run_logged(self, command, cwd=None):
        self.calls.append((command, cwd))
        return_code = 1
        try:
            self.assertEqual(command, ['/isolated/python', '-u',
                                      str(STUDY / 'run_natural_questions.py'),
                                      '--output-dir', str(self.output)])
            self.assertEqual(cwd, ROOT)
            self.frozen_guard()
            return_code = 0
        finally:
            with self.namespace['LAUNCHER_LOG'].open('ab') as stream:
                stream.write(self.event_bytes(command, return_code))

    def run_cell(self):
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(MAIN_CELL, '<experiment notebook cell>', 'exec'), self.namespace)

    def test_fresh_launcher_events_stay_outside_results_until_configuration(self):
        log_dir = self.namespace['LAUNCHER_LOG_DIR']
        self.assertEqual(log_dir.parent, self.output.parent)
        self.assertNotEqual(log_dir, self.output)
        self.assertEqual(self.namespace['CONSOLE_LOG'].parent, log_dir)
        self.namespace['LAUNCHER_LOG'].write_bytes(self.event_bytes())
        self.assertFalse(list(self.output.rglob('*.jsonl')))
        self.run_cell()
        self.assertTrue((self.output / 'run_config.json').is_file())
        self.assertEqual((self.output / 'launcher_logs/launcher_steps.jsonl').read_bytes(),
                         self.namespace['LAUNCHER_LOG'].read_bytes())

    def test_original_failure_and_repair_preserve_old_console_and_event_bytes(self):
        legacy = self.output / 'launcher_steps.jsonl'
        original = self.event_bytes() + self.event_bytes(return_code=1)
        legacy.write_bytes(original)
        console = self.output / 'console.log'
        console.write_bytes(b'original preparation and traceback\n')
        self.namespace['LAUNCHER_LOG'] = legacy  # Already prepared older Colab session.
        self.namespace['CONSOLE_LOG'] = console
        with self.assertRaisesRegex(ValueError, 'Existing outcome files'):
            self.frozen_guard()
        self.run_cell()
        self.assertFalse(legacy.exists())
        archived = list(self.namespace['LAUNCHER_LOG_DIR'].glob('legacy_launcher_steps_*.jsonl'))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), original)
        self.assertEqual(console.read_bytes(), b'original preparation and traceback\n')
        self.assertEqual((self.output / 'launcher_logs' / archived[0].name).read_bytes(), original)

    def test_actual_unregistered_csv_or_jsonl_outcomes_still_block(self):
        for name in ['retrieval/results.csv', 'contexts/rev5.jsonl']:
            with self.subTest(name=name):
                outcome = self.output / name
                outcome.parent.mkdir(parents=True, exist_ok=True)
                original = b'original study output\n'
                outcome.write_bytes(original)
                with self.assertRaisesRegex(ValueError, 'Existing outcome files'):
                    self.run_cell()
                self.assertEqual(outcome.read_bytes(), original)
                self.assertFalse((self.output / 'run_config.json').exists())
                self.assertFalse((self.output / 'launcher_logs').exists())
                outcome.unlink()  # Isolate the next synthetic case only.

    def test_invalid_legacy_file_is_never_moved_or_overwritten(self):
        legacy = self.output / 'launcher_steps.jsonl'
        valid = json.loads(self.event_bytes())
        naive = dict(valid, started_at_utc='2026-10-05T16:00:00')
        boolean_code = dict(valid, return_code=True)
        for original in [b'{"query_id":"NQ01"}\n', b'{broken json',
                         (json.dumps(naive) + '\n').encode(),
                         (json.dumps(boolean_code) + '\n').encode()]:
            with self.subTest(original=original):
                legacy.write_bytes(original)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.run_cell()
                self.assertEqual(legacy.read_bytes(), original)
                self.assertFalse(list(self.namespace['LAUNCHER_LOG_DIR'].glob('legacy_*')))
                self.assertEqual(self.calls, [])

    def test_compatible_resume_keeps_configuration_and_outcomes(self):
        self.run_cell()
        config = self.output / 'run_config.json'
        before = config.read_bytes()
        outcome = self.output / 'per_question_outcomes.jsonl'
        outcome.write_bytes(b'{"query_id":"NQ01","existing":true}\n')
        self.run_cell()
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(outcome.read_bytes(), b'{"query_id":"NQ01","existing":true}\n')
        self.assertEqual(len(self.namespace['LAUNCHER_LOG'].read_text().splitlines()), 2)

    def test_incompatible_resume_remains_blocked(self):
        config = self.output / 'run_config.json'
        config.write_text(json.dumps({'signature_sha256': 'different-runtime'}))
        before = config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Runtime/source/registration differs'):
            self.run_cell()
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((self.output / 'launcher_logs').exists())

    def test_logs_are_not_copied_if_a_successful_command_did_not_register_run(self):
        self.namespace['run_logged'] = lambda *args, **kwargs: None
        with self.assertRaisesRegex(RuntimeError, 'without a run configuration'):
            self.run_cell()
        self.assertFalse((self.output / 'launcher_logs').exists())


class AuthorityRepairRecovery(unittest.TestCase):
    ORIGINAL = '71a9a187d0a3fe0d64d71cdefbacdb345cce890d'
    ORIGINAL_REGISTRATION = json.loads((ROOT / STUDY / 'EXECUTION_REPAIR.json').read_text())['original_registration_sha256']

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = pathlib.Path(self.temp.name) / 'natural_questions_v2'
        self.output.mkdir()
        self.prior_config = self.output / 'run_config.json'
        self.prior_config.write_text(json.dumps({'signature': {
            'source_commit': self.ORIGINAL, 'registration_sha256': self.ORIGINAL_REGISTRATION}}))
        context = self.output / 'contexts/rev4.jsonl'
        context.parent.mkdir()
        context.write_bytes(b'original interrupted retrieval checkpoint\n')
        self.original_bytes = {p.relative_to(self.output): p.read_bytes()
                               for p in self.output.rglob('*') if p.is_file()}
        self.log_dir = self.output.with_name(self.output.name + '_launcher_logs')
        self.log_dir.mkdir()
        (self.log_dir / 'launcher_steps.jsonl').write_bytes(b'original preparation events\n')
        self.head = self.ORIGINAL
        self.dirty = False
        self.commands = []
        self.fail_study = False
        self.subprocess = Mock()
        self.subprocess.check_output.side_effect = self.check_output
        self.namespace = {'Path': pathlib.Path, 'OUTPUT_DIR': self.output,
            'SOURCE_COMMIT': self.ORIGINAL, 'REPO_DIR': ROOT, 'STUDY_RELATIVE': STUDY,
            'EXPERIMENT_PYTHON': '/isolated/python', 'subprocess': self.subprocess,
            'json': json, 'datetime': datetime, 'timezone': timezone, 'shutil': shutil,
            'digest': lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(),
            'run_logged': self.run_logged}

    def check_output(self, command, **kwargs):
        if command == ['git', 'rev-parse', 'HEAD']:
            return self.head + '\n'
        if command == ['git', 'status', '--porcelain', '--untracked-files=no']:
            return ' M changed.py\n' if self.dirty else ''
        raise AssertionError(command)

    def run_logged(self, command, cwd=None):
        self.commands.append(command)
        if command[:2] == ['git', 'checkout']:
            self.head = command[-1]
        elif command[:2] == ['/isolated/python', '-u'] and '--preflight-only' not in command:
            output = self.namespace['OUTPUT_DIR']
            exec(GUARD_CODE, {'config_path': output / 'run_config.json', 'output': output,
                'identity': 'repaired-runtime', 'signature': {'source_commit': SOURCE_COMMIT},
                'public_url': 'published-repair-registration', 'json': json,
                'datetime': datetime, 'timezone': timezone,
                'write_json': lambda p, v: p.write_text(json.dumps(v))})
            if self.fail_study:
                raise RuntimeError('Synthetic study interruption')
        with self.namespace['LAUNCHER_LOG'].open('a') as stream:
            stream.write(json.dumps({'command': command}) + '\n')

    def run_cell(self):
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(MAIN_CELL, '<authority recovery cell>', 'exec'), self.namespace)

    def assert_prior_bytes_preserved(self):
        for relative, content in self.original_bytes.items():
            self.assertEqual((self.output / relative).read_bytes(), content)

    def test_prepared_session_switches_registration_and_preserves_both_attempts(self):
        self.run_cell()
        self.assert_prior_bytes_preserved()
        repaired = self.namespace['OUTPUT_DIR']
        self.assertEqual(repaired.name, 'natural_questions_v2_authority_fix')
        self.assertEqual(self.namespace['SOURCE_COMMIT'], SOURCE_COMMIT)
        self.assertEqual(self.head, SOURCE_COMMIT)
        self.assertTrue(any('--preflight-only' in cmd for cmd in self.commands))
        self.assertTrue(any('tests.test_natural_questions_authority' in cmd for cmd in self.commands))
        for relative, content in self.original_bytes.items():
            self.assertEqual((repaired / 'prior_attempt/result_files' / relative).read_bytes(), content)
        self.assertEqual((repaired / 'prior_attempt/launcher_logs/launcher_steps.jsonl').read_bytes(),
                         b'original preparation events\n')
        self.assertNotEqual((repaired / 'run_config.json').read_bytes(), self.prior_config.read_bytes())

    def test_prior_generation_artifacts_prevent_restart_before_checkout(self):
        for name in ['generation_calls.jsonl', 'contracts/rev4_compliancegpt.csv']:
            with self.subTest(name=name):
                artifact = self.output / name
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_bytes(b'preserve every previous generation\n')
                with self.assertRaisesRegex(RuntimeError, 'generation artifacts'):
                    self.run_cell()
                self.assertEqual(artifact.read_bytes(), b'preserve every previous generation\n')
                self.assert_prior_bytes_preserved()
                self.assertEqual(self.commands, [])
                artifact.unlink()  # Separate synthetic cases only.

    def test_unexpected_registration_prevents_checkout(self):
        config = json.loads(self.prior_config.read_text())
        config['signature']['registration_sha256'] = 'unexpected-registration'
        self.prior_config.write_text(json.dumps(config))
        before = self.prior_config.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'another registration'):
            self.run_cell()
        self.assertEqual(self.prior_config.read_bytes(), before)
        self.assertEqual(self.commands, [])

    def test_modified_source_is_preserved_and_blocks_recovery(self):
        self.dirty = True
        with self.assertRaisesRegex(RuntimeError, 'modified source'):
            self.run_cell()
        self.assert_prior_bytes_preserved()
        self.assertEqual(self.commands, [])

    def test_interruption_keeps_original_and_new_checkpoint_separate(self):
        self.fail_study = True
        with self.assertRaisesRegex(RuntimeError, 'Synthetic study interruption'):
            self.run_cell()
        self.assert_prior_bytes_preserved()
        self.assertTrue((self.namespace['OUTPUT_DIR'] / 'run_config.json').exists())
        self.assertTrue((self.namespace['OUTPUT_DIR'] / 'prior_attempt_provenance.json').exists())
        self.assertFalse((self.namespace['OUTPUT_DIR'] / 'prior_attempt').exists())

    def test_compatible_retry_does_not_repeat_source_switch(self):
        self.run_cell()
        source_switches = sum(cmd[:2] == ['git', 'checkout'] for cmd in self.commands)
        config_path = self.namespace['OUTPUT_DIR'] / 'run_config.json'
        before = config_path.read_bytes()
        self.run_cell()
        self.assertEqual(sum(cmd[:2] == ['git', 'checkout'] for cmd in self.commands), source_switches)
        self.assertEqual(config_path.read_bytes(), before)
        self.assert_prior_bytes_preserved()


if __name__ == '__main__':
    unittest.main()
