"""Offline fixture and evidence-boundary checks; these never call a model."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('intake_runner', ROOT / 'scripts/check_sdlc_intake.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class IntakeRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def prepare(self, cases):
        destination = self.root / 'run'
        runner.prepare(destination, ROOT, cases)
        return destination

    def test_real_diff_and_private_expectations(self):
        dest = self.prepare(['review'])
        project = dest / 'review/project'
        diff = runner.git(project, 'diff', 'HEAD^', 'HEAD')
        self.assertIn('get("state")', diff)
        self.assertNotIn('expectations', runner.git(project, 'ls-files'))
        self.assertFalse((project / 'expectations.json').exists())
        self.assertTrue((project / '.claude/skills/sdlc/SKILL.md').is_file())
        self.assertEqual(runner.hashes(dest / 'bundle'), json.loads((dest / 'manifest.json').read_text())['source_hashes'])

    def test_preserves_prior_evidence(self):
        dest = self.prepare(['vague'])
        (dest / 'vague/native.jsonl').write_text('prior evidence\n')
        with patch.object(runner.subprocess, 'run') as launch:
            with self.assertRaises(ValueError):
                runner.run(dest, 'vague', 'unused', 1)
            launch.assert_not_called()
        with self.assertRaises(FileExistsError):
            runner.prepare(dest, ROOT, ['vague'])

    def test_source_mutation_is_observable(self):
        dest = self.prepare(['vague'])
        before = runner.hashes(dest / 'bundle')
        (dest / 'bundle/skills/sdlc/SKILL.md').write_text('changed\n')
        self.assertNotEqual(before, runner.hashes(dest / 'bundle'))

    def test_outside_write_attempt_is_retained(self):
        project = self.root / 'project'
        events = [{'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'inside', 'name': 'Write', 'input': {'file_path': 'smoke.py'}},
            {'type': 'tool_use', 'id': 'outside', 'name': 'Write', 'input': {'file_path': '../smoke.py'}}]}}]
        attempts = runner.outside_write_attempts(events, project)
        self.assertEqual([x['tool_use_id'] for x in attempts], ['outside'])

    def test_timeout_is_ungraded_not_success(self):
        dest = self.prepare(['vague'])
        with patch.object(runner.subprocess, 'run', side_effect=runner.subprocess.TimeoutExpired('claude', 1)), \
             patch.object(runner.subprocess, 'check_output', return_value='test-client'):
            runner.run(dest, 'vague', 'test-model', 1)
        result = json.loads((dest / 'vague/execution.json').read_text())
        self.assertTrue(result['timeout'])
        self.assertIsNone(result['result'])
        self.assertTrue(result['qualification'].startswith('ungraded'))


if __name__ == '__main__':
    unittest.main()
