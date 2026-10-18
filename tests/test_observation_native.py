"""Native metadata boundaries; no live client or real account needed."""
import concurrent.futures
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from account.observation.store import Store


class NativeObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.project = self.home / 'project'; self.project.mkdir()
        self.store = Store(self.home)
        context = patch('account.observation.native.Path.cwd', return_value=self.project)
        context.start(); self.addCleanup(context.stop)

    def grant(self):
        return self.store.grant(self.project, client='claude', source='claude-hooks-v1')

    def capture(self, grant, **changes):
        payload = dict(cwd=str(self.project), session_id='session-1',
                       hook_event_name='PostToolUse', tool_name='Read', tool_use_id='tool-1',
                       tool_input={'file_path':'PRIVATE_SENTINEL'}, tool_response='PRIVATE_SENTINEL',
                       transcript_path='PRIVATE_SENTINEL', last_assistant_message='PRIVATE_SENTINEL')
        payload.update(changes)
        return self.store.capture_native(grant['registration_id'], grant['epoch'],
                                         io.BytesIO(json.dumps(payload).encode()))

    def test_outside_process_project_does_not_read_or_scan_records(self):
        class Unreadable:
            def read(self, *args): raise AssertionError('out-of-scope stdin read')
        grant = self.grant()
        with patch('account.observation.native.Path.cwd', return_value=self.home), \
             patch.object(self.store, '_records', side_effect=AssertionError('out-of-scope scan')):
            result = self.store.capture_native(grant['registration_id'], grant['epoch'], Unreadable())
        self.assertEqual(result, {'status': 'rejected', 'reason': 'project_scope'})

    def test_native_metadata_and_dedup_without_content_or_inferred_success(self):
        grant = self.grant()
        self.assertEqual(self.capture(grant)['status'], 'recorded')
        self.assertEqual(self.capture(grant, tool_response='different secret')['status'], 'duplicate')
        event, = self.store.events(grant['registration_id'])
        self.assertEqual(event['client'], 'claude')
        self.assertEqual(event['event_kind'], 'tool_end')
        self.assertEqual(event['tool_category'], 'file')
        self.assertEqual(event['status'], 'unknown')
        self.assertIsNone(event['actor_id'])
        self.assertIn('environment_not_observed', event['gaps'])
        for path in self.store.root.rglob('*'):
            if path.is_file(): self.assertNotIn(b'PRIVATE_SENTINEL', path.read_bytes())

    def test_disabled_and_revoked_do_not_read_stdin_or_resurrect_after_regrant(self):
        class Unreadable:
            def read(self, *args): raise AssertionError('must not read')
        self.assertEqual(self.store.capture_native('f'*64, 'f'*32, Unreadable())['status'], 'disabled')
        grant = self.grant(); self.capture(grant)
        self.store.revoke(grant['registration_id'])
        self.assertEqual(self.store.capture_native(grant['registration_id'], grant['epoch'], Unreadable())['status'], 'disabled')
        replacement = self.grant()
        self.assertEqual(self.capture(grant)['status'], 'disabled')
        self.assertEqual(self.capture(replacement)['status'], 'recorded')
        self.assertEqual(len(self.store.events(replacement['registration_id'])), 1)

    def test_scope_unknown_events_and_content_limits(self):
        grant = self.grant()
        child = self.project / 'child'; child.mkdir()
        self.assertEqual(self.capture(grant, cwd=str(child))['status'], 'rejected')
        self.assertEqual(self.capture(grant, hook_event_name='NewUnknownEvent')['status'], 'rejected')
        huge = io.BytesIO(b'x' * 131073)
        self.assertEqual(self.store.capture_native(grant['registration_id'], grant['epoch'], huge)['status'], 'rejected')
        self.assertEqual(self.store.events(grant['registration_id']), [])

    def test_stop_is_not_task_success_and_lacks_stable_event_identity(self):
        grant = self.grant()
        for _ in range(2): self.assertEqual(self.capture(grant, hook_event_name='Stop')['status'], 'recorded')
        events = self.store.events(grant['registration_id'])
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event['status'], 'unknown')
            self.assertEqual(event['event_kind'], 'response_end')
            self.assertIn('possible_duplicate', event['gaps'])
            self.assertIsNone(event['tool_call_id'])

    def test_concurrent_duplicate_routes_commit_once(self):
        grant = self.grant()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.capture(grant), range(8)))
        self.assertEqual(sum(r['status']=='recorded' for r in results), 1)
        self.assertEqual(sum(r['status']=='duplicate' for r in results), 7)

    def test_manual_import_cannot_impersonate_native_events(self):
        grant = self.grant()
        for result in [self.store.capture(grant['registration_id'], grant['epoch'], b'{}'),
                       self.store.import_batch(grant['registration_id'], grant['epoch'], 0, b'{}\n')]:
            self.assertEqual(result['status'], 'rejected')
            self.assertEqual(result['reason'], 'adapter_mismatch')

    def test_expired_grant_does_not_read_payload(self):
        grant = self.grant()
        class Unreadable:
            def read(self, *args): raise AssertionError('must not read')
        with patch('account.observation.store.time.time', return_value=10**12):
            self.assertEqual(self.store.capture_native(grant['registration_id'], grant['epoch'], Unreadable())['status'], 'disabled')

    def test_event_identity_and_status_do_not_conflate_failures_or_sessions(self):
        grant = self.grant()
        self.capture(grant, hook_event_name='PreToolUse')
        self.capture(grant, hook_event_name='PostToolUseFailure')
        self.capture(grant, hook_event_name='PostToolUseFailure', session_id='session-2')
        events = self.store.events(grant['registration_id'])
        self.assertEqual(len(events), 3)
        self.assertEqual(sorted(e['sequence'] for e in events), [1,2,3])
        self.assertEqual(sorted(e['status'] for e in events), ['failure','failure','pending'])

    def test_missing_tool_identity_retains_duplicate_uncertainty(self):
        grant = self.grant()
        for _ in range(2): self.capture(grant, tool_use_id=None)
        events = self.store.events(grant['registration_id'])
        self.assertEqual(len(events), 2)
        self.assertTrue(all('possible_duplicate' in e['gaps'] for e in events))


if __name__ == '__main__':
    unittest.main()
