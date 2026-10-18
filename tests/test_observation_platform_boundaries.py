"""Synthetic platform preparation; these checks do not execute a native child/client."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from account.observation.store import Store


class PlatformBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.project = self.home / 'project'
        self.project.mkdir()
        self.store = Store(self.home)
        self.grant = self.store.grant(self.project, client='codex', source='codex-hooks-v1')
        context = patch('account.observation.native.Path.cwd', return_value=self.project)
        context.start()
        self.addCleanup(context.stop)

    def capture(self, **changes):
        payload = dict(cwd=str(self.project), session_id='session-parent', turn_id='turn',
                       hook_event_name='PreToolUse', tool_name='Bash', tool_use_id='tool',
                       agent_id='SYNTHETIC_AGENT_SENTINEL', agent_type='explorer',
                       model='synthetic-model', permission_mode='default',
                       tool_input={}, transcript_path=None)
        payload.update(changes)
        return self.store.capture_native(self.grant['registration_id'], self.grant['epoch'],
                                         io.BytesIO(json.dumps(payload).encode()))

    def events(self):
        return self.store.events(self.grant['registration_id'])

    def test_agent_metadata_does_not_become_inferred_actor_or_parent(self):
        self.assertEqual(self.capture()['status'], 'recorded')
        event, = self.events()
        self.assertIsNone(event['actor_id'])
        self.assertIsNone(event['parent_actor_id'])
        self.assertIn('actor_id_not_observed', event['gaps'])
        self.assertIn('parent_actor_id_not_observed', event['gaps'])
        for path in self.store.root.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'SYNTHETIC_AGENT_SENTINEL', path.read_bytes())

    def test_distinct_sessions_do_not_merge_same_turn_and_tool_identifiers(self):
        self.assertEqual(self.capture()['status'], 'recorded')
        self.assertEqual(self.capture(session_id='session-child')['status'], 'recorded')
        self.assertEqual(self.capture()['status'], 'duplicate')
        self.assertEqual({event['session_id'] for event in self.events()},
                         {'session-parent', 'session-child'})
        self.assertTrue(all(event['parent_actor_id'] is None for event in self.events()))

    def test_unsupported_event_is_rejected_without_completing_pending_tool(self):
        """A synthetic unsupported event is not a native interruption callback."""
        self.assertEqual(self.capture()['status'], 'recorded')
        result = self.capture(hook_event_name='Interrupt', reason='interrupted')
        self.assertEqual(result, {'status': 'rejected', 'reason': 'unsupported_event'})
        event, = self.events()
        self.assertEqual((event['event_kind'], event['status']), ('tool_start', 'pending'))
        self.assertFalse(any(event['event_kind'] in ('tool_end', 'response_end')
                             for event in self.events()))

    def test_child_process_cwd_is_rejected_by_exact_project_guard(self):
        """Process scope rejects before the event payload is interpreted."""
        child = self.project / 'child'
        child.mkdir()
        with patch('account.observation.native.Path.cwd', return_value=child):
            result = self.capture(cwd=str(child), session_id='session-child')
        self.assertEqual(result, {'status': 'rejected', 'reason': 'project_scope'})
        self.assertEqual(self.events(), [])

    def test_child_payload_cwd_is_rejected_with_authorized_process_cwd(self):
        """The process stays authorized; the payload guard rejects its child cwd."""
        child = self.project / 'child'
        child.mkdir()
        result = self.capture(cwd=str(child), session_id='session-child')
        self.assertEqual(result, {'status': 'rejected', 'reason': 'project_scope'})
        self.assertEqual(self.events(), [])


if __name__ == '__main__':
    unittest.main()
