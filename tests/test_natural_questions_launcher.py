"""Exercise the launcher layout against the unchanged runner checkpoint guard."""
import ast
import contextlib
import io
import json
import pathlib
import shutil
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDY = pathlib.Path('experiments/external_validity/natural_questions_v2')
NOTEBOOK = json.loads((ROOT / STUDY / 'Batch_Natural_Questions_v2.ipynb').read_text())
MAIN_CELL = ''.join(NOTEBOOK['cells'][6]['source'])
SETUP = ast.parse(''.join(NOTEBOOK['cells'][1]['source']))
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


if __name__ == '__main__':
    unittest.main()
