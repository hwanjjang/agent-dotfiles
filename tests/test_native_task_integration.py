"""Native callback metadata through tasks, feedback and reviewed public exports."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from account.observation.files import Files
from account.observation.store import Store
from test_improvement_cases import synthetic_case


class NativeTaskIntegrationTests(unittest.TestCase):
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

    def grant(self, client):
        return self.store.grant(self.project, client=client, source=client + '-hooks-v1')

    def capture(self, grant, number):
        client = self.store.registration(grant['registration_id'])['client']
        payload = dict(cwd=str(self.project), session_id='native-session',
                       hook_event_name='PostToolUseFailure' if client == 'claude' else 'PostToolUse',
                       tool_name='Bash', tool_use_id=f'call-{number}', turn_id='native-turn',
                       tool_response={'exit_code': 2, 'output': 'PRIVATE_CALLBACK_CONTENT'})
        return self.store.capture_native(grant['registration_id'], grant['epoch'],
                                         io.BytesIO(json.dumps(payload).encode()))

    def bind(self, grant, *, event_ids=None, request_id='bind'):
        selection = dict(grant, session_id='native-session')
        selection.update(dict(event_ids=event_ids) if event_ids is not None else
                         dict(start_sequence=1, end_sequence=100))
        return self.store.bind_task(selections=[selection], goal='PRIVATE_TASK', request_id=request_id + '-' + grant['registration_id'])

    def prepare(self, task, ids, purpose):
        feedback = self.store.add_feedback(task['task_id'], symptom='PRIVATE_SYMPTOM',
            correction='PRIVATE_CORRECTION', evidence_ids=ids, request_id='feedback')
        example = synthetic_case()
        example.update(case_id=purpose + '-en', purpose=purpose)
        return self.store.prepare_case(task['task_id'], revision_id=task['revision_id'],
            feedback_ids=[feedback['feedback_id']], synthetic_case=example, request_id=purpose,
            triage=dict(category='instruction', evidence_ids=ids))

    def export(self, task, case):
        self.store.review_case(task['task_id'], case['case_id'], expected_digest=case['case_digest'],
            reviewer='synthetic-maintainer', synthetic_data_confirmed=True, privacy_reviewed=True)
        target = self.home / (task['task_id'] + '-' + case['case_id'] + '.json')
        self.store.export_case(task['task_id'], case['case_id'],
                              expected_digest=case['case_digest'], destination=target)
        raw = target.read_text()
        self.assertNotIn('PRIVATE_', raw)
        self.assertNotIn(task['task_id'], raw)
        self.assertEqual(json.loads(raw)['classification'], 'development')

    def test_native_intervals_keep_their_receipt_basis(self):
        for client in ('claude', 'codex'):
            with self.subTest(client=client):
                grant = self.grant(client)
                self.assertEqual(self.capture(grant, 1)['status'], 'recorded')
                task = self.bind(grant)
                selection, = self.store.task(task['task_id'])['revisions'][0]['selections']
                self.assertEqual(selection['basis'], 'native_receipt_interval')
                self.assertIsNone(selection['events'][0]['actor_id'])
                self.assertIn('native_sequence_reservation_gaps_possible', selection['events'][0]['gaps'])

    def test_actual_native_failure_and_unknown_status_control_case_eligibility(self):
        for client in ('claude', 'codex'):
            with self.subTest(client=client):
                grant = self.grant(client)
                result = self.capture(grant, 1)
                self.assertEqual(result['status'], 'recorded')
                task = self.bind(grant, event_ids=result['event_ids'])
                outcome = self.prepare(task, result['event_ids'], 'outcome')
                if client == 'claude':
                    self.assertEqual(outcome['status'], 'prepared')
                    self.export(task, outcome)
                else:
                    self.assertEqual(outcome, dict(status='insufficient', reason='failed_tool_evidence_missing'))
                routing = self.prepare(task, result['event_ids'], 'routing')
                self.assertEqual(routing['status'], 'prepared')
                self.export(task, routing)
                self.store.revoke(grant['registration_id'])
                self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
                self.assertFalse((self.store.root / 'tasks' / task['task_id']).exists())

    def test_reservation_gap_interval_and_composite_native_revoke(self):
        claude, codex = self.grant('claude'), self.grant('codex')
        first = self.capture(claude, 1)
        original = Files.write
        def fail_record(files, path, value):
            if path[0] == 'records':
                raise OSError('injected before record publication')
            return original(files, path, value)
        with patch.object(Files, 'write', fail_record):
            self.assertEqual(self.capture(claude, 2)['status'], 'error')
        third = self.capture(claude, 3)
        other = self.capture(codex, 1)
        task = self.store.bind_task(selections=[dict(claude, session_id='native-session',
            start_sequence=1, end_sequence=3), dict(codex, session_id='native-session',
            event_ids=other['event_ids'])], goal='PRIVATE_COMPOSITE', request_id='composite')
        view = self.store.task(task['task_id'])
        selected = view['revisions'][0]['selections']
        self.assertEqual([e['sequence'] for e in selected[0]['events']], [1, 3])
        self.assertEqual({e['event_id'] for e in selected[0]['events']},
                         set(first['event_ids'] + third['event_ids']))
        self.assertEqual(selected[1]['basis'], 'explicit_event_ids')
        self.store.add_feedback(task['task_id'], symptom='PRIVATE_COMPOSITE',
            correction='PRIVATE_CORRECTION', evidence_ids=first['event_ids'], request_id='feedback')
        self.store.revoke(codex['registration_id'])
        self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
        self.assertFalse((self.store.root / 'tasks' / task['task_id']).exists())
        self.assertEqual(len(self.store.events(claude['registration_id'])), 2)
