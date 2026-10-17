"""Run the task/feedback CLI against a disposable account."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/improvement/observations.py'


class FeedbackCliTests(unittest.TestCase):
    def test_feedback_cli_scope_retry_and_revoke(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve()
            project = home / 'project'; project.mkdir()
            def call(*args, body=None, expected=0):
                result = subprocess.run([sys.executable, str(CLI), '--home', str(home), *args],
                    input=json.dumps(body).encode() if body is not None else None,
                    capture_output=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(result.stderr, b'')
                return json.loads(result.stdout)
            grant = call('grant', '--project', str(project), '--start-after', '0')
            event = call('capture', '--registration', grant['registration_id'], '--epoch', grant['epoch'],
                body=dict(schema_version=1, project_root=str(project), client='synthetic',
                          source='fixture-v1', profile='default', session_id='session',
                          sequence=1, source_event_id='event', event_kind='tool_end'))
            request = dict(goal='검증 결과 확인', request_id='bind',
                selections=[dict(grant, session_id='session', event_ids=event['event_ids'])])
            task = call('task-bind', body=request)
            self.assertEqual(call('task-bind', body=request)['status'], 'duplicate')
            self.assertEqual(call('task-bind', body=dict(request, goal='changed'), expected=1)['reason'], 'request_conflict')
            feedback = call('feedback-add', '--task', task['task_id'], body=dict(
                symptom='Incorrect success claim', correction='The command was unavailable',
                request_id='feedback', evidence_ids=event['event_ids']))
            self.assertEqual(feedback['evidence_status'], 'reported_correction')
            self.assertEqual(len(call('task-show', '--task', task['task_id'])['feedback']), 1)
            self.assertEqual(call('feedback-add', '--task', task['task_id'],
                body=dict(symptom='bad', request_id='invalid', transcript_path='/private'), expected=1)['reason'], 'task_input_fields')
            call('revoke', '--registration', grant['registration_id'])
            self.assertEqual(call('task-show', '--task', task['task_id'])['status'], 'disabled')
            self.assertFalse((home / '.codex').exists())
            self.assertFalse((home / '.agents/agent-dotfiles/state').exists())
