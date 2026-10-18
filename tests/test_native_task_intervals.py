"""Receipt interval provenance through task feedback, without export dependencies."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from account.observation.store import Store


class NativeTaskIntervalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        self.project = self.home / 'project'
        self.project.mkdir()
        self.store = Store(self.home)
        context = patch('account.observation.native.Path.cwd', return_value=self.project)
        context.start()
        self.addCleanup(context.stop)

    def check_interval(self, client):
        if client == 'synthetic':
            grant = self.store.grant(self.project)
            payload = dict(schema_version=1, project_root=str(self.project),
                client='synthetic', profile='default', source='fixture-v1',
                session_id='interval-session', sequence=1, source_event_id='event-1',
                event_kind='tool_end', status='failure')
            result = self.store.capture(grant['registration_id'], grant['epoch'],
                                        json.dumps(payload).encode())
            expected_basis = 'synthetic_receipt_interval'
        else:
            grant = self.store.grant(self.project, client=client, source=client + '-hooks-v1')
            payload = dict(cwd=str(self.project), session_id='interval-session',
                hook_event_name='PostToolUseFailure' if client == 'claude' else 'PostToolUse',
                tool_name='Bash', tool_use_id='call-1', turn_id='native-turn',
                tool_response={'exit_code': 2})
            result = self.store.capture_native(grant['registration_id'], grant['epoch'],
                                               io.BytesIO(json.dumps(payload).encode()))
            expected_basis = 'native_receipt_interval'
        self.assertEqual(result['status'], 'recorded', result)
        task = self.store.bind_task(selections=[dict(grant, session_id='interval-session',
            start_sequence=1, end_sequence=10)], goal='Check interval provenance',
            request_id='bind-' + client)
        feedback = self.store.add_feedback(task['task_id'], symptom='Check callback provenance',
            correction='Retain the selected callback receipt basis',
            evidence_ids=result['event_ids'], request_id='feedback-' + client)
        self.assertEqual(feedback['status'], 'recorded', feedback)
        view = self.store.task(task['task_id'])
        selection, = view['revisions'][0]['selections']
        row, = view['feedback']
        self.assertEqual(row['revision_id'], task['revision_id'])
        self.assertEqual(row['evidence_ids'], result['event_ids'])
        self.assertEqual([event['event_id'] for event in selection['events']], result['event_ids'])
        self.assertEqual(selection['basis'], expected_basis)

    def test_claude_interval_feedback_retains_native_basis(self):
        self.check_interval('claude')

    def test_codex_interval_feedback_retains_native_basis(self):
        self.check_interval('codex')

    def test_synthetic_interval_feedback_retains_legacy_basis(self):
        self.check_interval('synthetic')
