import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial_protocol as protocol


def usage(total=100, output=10, thread='thread', turn='turn'):
    values = dict(totalTokens=total, inputTokens=total-output, outputTokens=output,
                  cachedInputTokens=0, cacheWriteInputTokens=0, reasoningOutputTokens=0)
    return {'method': 'thread/tokenUsage/updated', 'params': {
        'threadId': thread, 'turnId': turn,
        'tokenUsage': {'total': values, 'last': dict(values), 'modelContextWindow': 258400}}}


def terminal(status='completed', thread='thread', turn='turn'):
    return {'method': 'turn/completed', 'params': {
        'threadId': thread, 'turn': {'id': turn, 'status': status, 'error': None}}}


class FakeSession:
    def __init__(self, events):
        self.events = list(events)
        self.calls = []
        self.responses = {}

    def send(self, value):
        self.calls.append(('send', value))

    def rpc(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method in self.responses:
            return self.responses[method]
        if method == 'account/read':
            return {'account': {'type': 'chatgpt'}, 'requiresOpenaiAuth': True}
        if method == 'thread/start':
            return {'model': 'gpt-6-luna', 'thread': {'id': 'thread'}}
        if method == 'turn/start':
            return {'turn': {'id': 'turn'}}
        if method in ('hooks/list', 'skills/list'):
            key = 'hooks' if method == 'hooks/list' else 'skills'
            row = {'cwd': params['cwds'][0], key: [], 'errors': []}
            if key == 'hooks':
                row['warnings'] = []
            return {'data': [row]}
        if method == 'mcpServerStatus/list':
            return {'data': [], 'nextCursor': None}
        return {}

    def until(self, predicate):
        while self.events:
            value = self.events.pop(0)
            if predicate(value):
                return value
        raise TimeoutError('synthetic deadline')


class ProtocolTests(unittest.TestCase):
    def run_observer(self, events, **changes):
        session = FakeSession(events)
        session.responses.update(changes.pop('fake_responses', {}))
        options = dict(prompt='SYNTHETIC_TASK_INPUT', project='/synthetic/project',
                       codehome='/synthetic/home/.codex', metadata_check=lambda: {
                           'status': 'recognized', 'compatibility_match': True},
                       soft_total=131072, soft_output=4096)
        options.update(changes)
        return session, protocol.observe(session, **options)

    def test_one_initial_turn_and_matching_terminal_preserve_unknown_outcome(self):
        session, result = self.run_observer([usage(), terminal()])
        self.assertEqual(result['status'], 'completed_ungraded')
        self.assertEqual(result['initial_turns'], 1)
        turns = [p for m, p in session.calls if m == 'turn/start']
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]['input'][0]['text'], 'SYNTHETIC_TASK_INPUT')
        self.assertFalse(result['live_eligible'])
        self.assertNotIn('SYNTHETIC_TASK_INPUT', json.dumps(result))
        thread = next(p for m, p in session.calls if m == 'thread/start')
        self.assertEqual(thread['selectedCapabilityRoots'][0]['location']['path'], '/runtime/arm')

    def test_metadata_unknown_or_mismatch_refuses_before_turn(self):
        for metadata in [{'status': 'unknown', 'compatibility_match': False},
                         {'status': 'recognized', 'compatibility_match': False}]:
            session, result = self.run_observer([], metadata_check=lambda: metadata)
            self.assertEqual(result['reason'], 'model_tool_contract')
            self.assertEqual(result['initial_turns'], 0)
            self.assertFalse(any(m == 'turn/start' for m, _ in session.calls))

    def test_wrong_usage_or_terminal_identity_cannot_complete(self):
        for events in [[usage(thread='other'), terminal()],
                       [usage(), terminal(turn='other')]]:
            _, result = self.run_observer(events)
            self.assertEqual(result['status'], 'blocked')
            self.assertIn(result['reason'], ('usage_identity', 'terminal_identity'))

    def test_soft_stop_persists_before_one_interrupt_and_never_becomes_pass(self):
        observed = []
        session, result = self.run_observer([usage(300, 25), usage(310, 26), terminal()],
                                           soft_total=200, usage_sink=observed.append)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['reason'], 'soft_usage_stop')
        self.assertEqual(sum(m == 'turn/interrupt' for m, _ in session.calls), 1)
        self.assertTrue(observed)
        self.assertTrue(result['terminal_completed'])

    def test_missing_usage_failed_terminal_and_unexpected_account_refuse(self):
        _, result = self.run_observer([terminal()])
        self.assertEqual(result['reason'], 'usage_unavailable')
        _, result = self.run_observer([usage(), terminal(status='failed')])
        self.assertEqual(result['reason'], 'terminal_failed')

    def test_usage_sink_failure_is_fixed_reason_without_input_or_error(self):
        def sink(_):
            raise RuntimeError('SECRET_ARBITRARY_ERROR')
        _, result = self.run_observer([usage(), terminal()], usage_sink=sink)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['reason'], 'usage_persistence_failed')
        self.assertNotIn('SECRET_ARBITRARY_ERROR', json.dumps(result))

    def test_null_native_ids_never_create_a_matching_null_identity(self):
        for responses, thread in [
            ({'thread/start': {'model': 'gpt-6-luna', 'thread': {'id': None}},
              'turn/start': {'turn': {'id': None}}}, None),
            ({'turn/start': {'turn': {'id': None}}}, 'thread'),
        ]:
            session, result = self.run_observer(
                [usage(thread=thread, turn=None), terminal(thread=thread, turn=None)],
                fake_responses=responses)
            self.assertEqual(result['status'], 'blocked')
            self.assertIn(result['reason'], ('thread_identity', 'turn_identity'))

    def test_malformed_discovery_is_not_treated_as_empty_safe_inventory(self):
        for method, response in [
            ('hooks/list', {'data': [{}]}),
            ('hooks/list', {'data': [{'cwd': '/wrong', 'hooks': [], 'errors': []}]}),
            ('skills/list', {'data': [{'cwd': '/wrong', 'skills': [], 'errors': []}]}),
            ('mcpServerStatus/list', {'data': None}),
        ]:
            session, result = self.run_observer([usage(), terminal()],
                                               fake_responses={method: response})
            self.assertEqual(result['initial_turns'], 0)
            self.assertFalse(any(m == 'turn/start' for m, _ in session.calls))

    def test_native_launch_failure_keeps_own_session_available_for_close(self):
        # A synthetic Python child exercises ownership ordering without invoking
        # the native client, Docker, a model or an authentication file.
        archive = protocol.CounterArchive()
        session = protocol.NativeSession(archive, time.monotonic() + 5)
        launched = []
        def fail_after_spawn(pid):
            launched.append(pid)
            raise RuntimeError('SYNTHETIC_JOURNAL_FAILURE')
        with tempfile.TemporaryDirectory() as folder:
            try:
                with self.assertRaisesRegex(RuntimeError, 'SYNTHETIC_JOURNAL_FAILURE'):
                    session.start([sys.executable, '-I', '-S', '-c', 'import time;time.sleep(5)'],
                                  Path(folder), {'PATH': '/usr/bin:/bin'}, fail_after_spawn)
            finally:
                result = session.close()
        self.assertEqual(launched, [session.proc.pid])
        self.assertTrue(result['process_reaped'])
        self.assertEqual(session.close(), result)


if __name__ == '__main__':
    unittest.main()
