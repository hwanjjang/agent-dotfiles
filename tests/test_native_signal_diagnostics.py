"""Real unauthenticated Python peer drain with injected owned-group OS errors."""
import errno
import json
import os
import signal
import tempfile
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_native_routing as fixtures

protocol = fixtures.protocol


class SignalDiagnosticTests(unittest.TestCase):
    observer = fixtures.RoutingTests.observer
    start = fixtures.DrainLifecycleTests.start

    def close_with_error(self, error):
        with tempfile.TemporaryDirectory() as folder:
            session = self.start(folder, 'import sys;sys.stdin.buffer.read()')
            session.routing.bind('thread', 'turn')
            session.routing.feed(fixtures.line('codex.user_prompt'))
            real_killpg = os.killpg
            try:
                with patch.object(protocol.os, 'killpg', side_effect=error) as kill:
                    result = session.close()
                self.assertEqual(kill.call_args_list[0].args, (session.proc.pid, signal.SIGKILL))
                self.assertTrue(all(call.args == (session.proc.pid, 0) for call in kill.call_args_list[1:]))
                self.assertTrue(result['process_reaped'])
                self.assertTrue(result['routing_drain']['stdout_eof'])
                self.assertTrue(result['routing_drain']['stderr_eof'])
                self.assertFalse(result['owned_process_group_kill_sent'])
                self.assertNotIn('PRIVATE_SIGNAL', json.dumps(result))
                return result, session.routing
            finally:
                if session.proc.returncode is None:
                    try: real_killpg(session.proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    session.proc.wait(timeout=2)
                if session.close_result is None:
                    session.selector.close()
                    for stream in (session.proc.stdin, session.proc.stdout, session.proc.stderr):
                        stream.close()

    def test_known_errno_is_finite_without_waiving_signal_failure_after_eof(self):
        for number, expected in ((errno.EPERM, 'permission_denied'),
                                 (errno.EACCES, 'permission_denied'),
                                 (errno.EINVAL, 'invalid_argument'),
                                 (errno.EINTR, 'interrupted')):
            with self.subTest(errno=number):
                result, observer = self.close_with_error(OSError(number, 'PRIVATE_SIGNAL /private/path'))
                self.assertEqual(result.get('group_signal_error_code'), expected)
                self.assertEqual(result['group_signal_error'], 'signal_failed')
                self.assertEqual(result['routing_drain']['close_mode'], 'incomplete')
                self.assertEqual(observer.reason, 'routing_drain')
                self.assertEqual(observer.finish(True, result['routing_drain'])['status'], 'blocked')

    def test_unknown_errno_or_hostile_message_is_other_os_error(self):
        for error in (OSError(987654321, 'PRIVATE_SIGNAL token=not-real'),
                      OSError('PRIVATE_SIGNAL /private/path')):
            with self.subTest(errno=error.errno):
                result, observer = self.close_with_error(error)
                self.assertEqual(result.get('group_signal_error_code'), 'other_os_error')
                self.assertEqual(result['group_signal_error'], 'signal_failed')
                self.assertEqual(observer.reason, 'routing_drain')
                self.assertNotIn('987654321', json.dumps(result))

    def test_esrch_retains_existing_no_signal_error_classification(self):
        result, observer = self.close_with_error(OSError(errno.ESRCH, 'PRIVATE_SIGNAL'))
        self.assertIsNone(result['group_signal_error'])
        self.assertIn('group_signal_error_code', result)
        self.assertIsNone(result['group_signal_error_code'])
        self.assertEqual(result['routing_drain']['close_mode'], 'graceful_stdin_eof')
        self.assertIsNone(observer.reason)
        self.assertEqual(observer.finish(True, result['routing_drain'])['status'], 'observed')

    @unittest.skipUnless(sys.platform == 'darwin', 'Darwin process-group reconciliation')
    def test_real_darwin_eof_peer_closes_with_proven_group_absence(self):
        with tempfile.TemporaryDirectory() as folder:
            session=self.start(folder,'import sys;sys.stdin.buffer.read()')
            session.routing.bind('thread','turn')
            session.routing.feed(fixtures.line('codex.user_prompt'))
            try:
                result=session.close()
                self.assertTrue(result['process_reaped'])
                self.assertIsNone(result['group_signal_error'])
                if result['group_signal_error_code']=='permission_denied':
                    self.assertTrue(result['group_absent_after_reap'])
                self.assertEqual(session.routing.finish(True,result['routing_drain'])['status'],'observed')
            finally:
                if session.proc.returncode is None:session.proc.wait(timeout=2)
                if session.close_result is None:
                    session.selector.close()
                    for stream in (session.proc.stdin,session.proc.stdout,session.proc.stderr):stream.close()

    def reconciled_close(self, probe='absent', *, platform='darwin', fault=None):
        with tempfile.TemporaryDirectory() as folder:
            session = self.start(folder, 'import sys;sys.stdin.buffer.read()')
            session.routing.bind('thread', 'turn')
            session.routing.feed(fixtures.line('codex.user_prompt'))
            if fault == 'prior_routing':session.routing.fail('routing_json')
            if fault == 'deadline':session.cleanup_deadline=time.monotonic()-1
            real_wait, real_killpg = session.proc.wait, os.killpg
            signals = []
            def send(pid, sig):
                self.assertEqual(pid, session.proc.pid)
                signals.append(sig)
                if sig == signal.SIGKILL:
                    self.assertIsNone(session.proc.returncode)
                    raise PermissionError(errno.EPERM, 'PRIVATE_SIGNAL')
                self.assertEqual(sig, 0)
                self.assertIsNotNone(session.proc.returncode)
                if probe == 'absent':raise ProcessLookupError(errno.ESRCH, 'PRIVATE_SIGNAL')
                if probe == 'denied':raise PermissionError(errno.EPERM, 'PRIVATE_SIGNAL')
                if probe == 'other':raise OSError(errno.EINVAL, 'PRIVATE_SIGNAL')
                if probe == 'interrupted':raise InterruptedError(errno.EINTR, 'PRIVATE_SIGNAL')
            def wait(*args, **kwargs):
                if fault == 'unreaped':raise subprocess.TimeoutExpired('synthetic', .01)
                result=real_wait(*args, **kwargs)
                if fault == 'missing_eof':session.eof.discard('stderr')
                if fault == 'buffer':session.buffer.extend(b'x')
                if fault == 'routing_buffer':session.routing.buffer.extend(b'x')
                if fault == 'pending':session.pending.append({'method':'synthetic'})
                return result
            try:
                with patch.object(protocol, 'sys', SimpleNamespace(platform=platform), create=True), patch.object(protocol.os, 'killpg', side_effect=send), patch.object(session.proc, 'wait', side_effect=wait):
                    result=session.close()
                self.assertNotIn('PRIVATE_SIGNAL', json.dumps(result))
                self.assertEqual(signals[0], signal.SIGKILL)
                self.assertTrue(all(sig == 0 for sig in signals[1:]))
                return result, session.routing, signals
            finally:
                if session.proc.returncode is None:
                    # The peer exits on stdin EOF; reap without another group signal.
                    real_wait(timeout=2)
                if session.close_result is None:
                    session.selector.close()
                    for stream in (session.proc.stdin, session.proc.stdout, session.proc.stderr):stream.close()

    def test_darwin_permission_error_requires_reaped_exact_group_absence(self):
        result, observer, signals=self.reconciled_close()
        self.assertIsNone(result['group_signal_error'])
        self.assertEqual(result['group_signal_error_code'], 'permission_denied')
        self.assertTrue(result['group_absent_after_reap'])
        self.assertEqual(signals, [signal.SIGKILL, 0])
        self.assertEqual(result['routing_drain']['close_mode'], 'graceful_stdin_eof')
        self.assertEqual(observer.finish(True, result['routing_drain'])['status'], 'observed')

    def test_present_denied_or_unknown_group_probe_remains_blocked(self):
        for probe in ('present','denied','other','interrupted'):
            with self.subTest(probe=probe):
                result, observer, signals=self.reconciled_close(probe)
                self.assertEqual(result['group_signal_error'], 'signal_failed')
                self.assertFalse(result['group_absent_after_reap'])
                self.assertEqual(signals,[signal.SIGKILL,0])
                self.assertEqual(observer.reason,'routing_drain')
                self.assertEqual(result['routing_drain']['close_mode'],'incomplete')

    def test_missing_io_reap_deadline_or_platform_cannot_reconcile(self):
        for fault in ('missing_eof','buffer','routing_buffer','pending','unreaped','deadline','non_darwin'):
            with self.subTest(fault=fault):
                result, observer, signals=self.reconciled_close(platform='linux' if fault=='non_darwin' else 'darwin',fault=fault)
                self.assertEqual(result['group_signal_error'],'signal_failed')
                self.assertFalse(result['group_absent_after_reap'])
                self.assertEqual(signals,[signal.SIGKILL])
                self.assertEqual(observer.reason,'routing_drain')

    def test_reconciled_group_does_not_clear_prior_routing_failure(self):
        result, observer, _=self.reconciled_close(fault='prior_routing')
        self.assertIsNone(result['group_signal_error'])
        self.assertTrue(result['group_absent_after_reap'])
        self.assertEqual(observer.reason,'routing_json')
        self.assertEqual(observer.finish(True,result['routing_drain'])['status'],'blocked')


if __name__ == '__main__':
    unittest.main()
