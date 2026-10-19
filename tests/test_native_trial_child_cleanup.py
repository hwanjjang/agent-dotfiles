"""Owned child exit races; no credentials, VM or native model calls."""
import errno
import copy
import select
import os
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch
import test_native_trial_lifecycle as support
trial = support.trial


class ChildCleanupTests(unittest.TestCase):
    setUp = support.LifecycleTests.setUp
    controller = support.LifecycleTests.controller
    real_bounded = staticmethod(trial.bounded)

    def owned(self):
        self.selected = copy.deepcopy(self.selected)
        self.selected.data['identity']['attempt_id'] += '-next'
        self.selected.digest = trial.plan.digest(self.selected.data)
        c = self.controller()
        saved = dict(pid=12345, ppid=os.getpid(), pgid=12345,
                     start='synthetic owned start', exe=c.runtime['docker'])
        c.seen = {saved['pid']: saved}
        c.launch_called = c.launch_complete = True
        c.live = Mock(); c.live.proc = Mock(pid=12344)
        c.live.close.return_value = dict(process_reaped=True, group_signal_error=None)
        c.data['limits']['cleanup_seconds'] = .1
        return c, saved

    def test_allowed_signal_race_requires_fresh_pid_and_group_absence(self):
        for code in (errno.ESRCH, errno.EPERM, errno.EACCES):
            with self.subTest(errno=code):
                c, saved = self.owned()
                with patch.object(trial.sys, 'platform', 'darwin'), \
                     patch.object(c, 'process', side_effect=[saved, None]) as query, \
                     patch.object(trial.os, 'killpg', side_effect=[OSError(code, 'SECRET'), ProcessLookupError(errno.ESRCH, 'SECRET')]) as kill:
                    result = c.cleanup()
                self.assertTrue(result['complete']); self.assertEqual(query.call_count, 2)
                self.assertLessEqual(query.call_args_list[1].kwargs['until'], c.cleanup_deadline)
                self.assertEqual([call.args for call in kill.call_args_list], [(saved['pgid'], signal.SIGKILL), (saved['pgid'], 0)])
                self.assertEqual(result['process_absence'], [{'pid':saved['pid'], 'absent':True}])
                self.assertEqual(result['process_signal_reconciliations'], [dict(pid=saved['pid'],
                    signal_error_code='not_found' if code == errno.ESRCH else 'permission_denied', group_absent=True)])
                self.assertNotIn('SECRET', str(result))
                c.release()

    def test_successful_signal_waits_for_same_owner_then_confirms_absence(self):
        c, saved = self.owned(); c.data['limits']['cleanup_seconds']=.5
        with patch.object(c, 'process', side_effect=[saved, saved, None]), \
             patch.object(trial.os, 'killpg') as kill:
            result=c.cleanup()
        self.assertTrue(result['complete'])
        kill.assert_called_once_with(saved['pgid'], signal.SIGKILL)
        self.assertEqual(result['process_signal_reconciliations'], [])

    def test_permission_race_waits_for_same_owner_and_group_before_absence(self):
        c, saved = self.owned(); c.data['limits']['cleanup_seconds']=.5
        with patch.object(trial.sys, 'platform', 'darwin'), \
             patch.object(c, 'process', side_effect=[saved, saved, None, None]), \
             patch.object(trial.os, 'killpg', side_effect=[
                 PermissionError(errno.EPERM, 'private'), PermissionError(errno.EPERM, 'private'),
                 ProcessLookupError(errno.ESRCH, 'gone')]) as kill:
            result=c.cleanup()
        self.assertTrue(result['complete'])
        self.assertEqual([call.args for call in kill.call_args_list],
                         [(saved['pgid'], signal.SIGKILL), (saved['pgid'], 0), (saved['pgid'], 0)])
        self.assertEqual(result['process_signal_reconciliations'], [dict(
            pid=saved['pid'], signal_error_code='permission_denied', group_absent=True)])

    def test_unrecognized_signal_error_or_non_darwin_permission_stays_blocked(self):
        for platform, code in (('linux', errno.EPERM), ('darwin', errno.EINVAL)):
            with self.subTest(platform=platform, code=code):
                c, saved = self.owned()
                with patch.object(trial.sys, 'platform', platform), \
                     patch.object(c, 'process', return_value=saved) as query, \
                     patch.object(trial.os, 'killpg', side_effect=OSError(code, 'PRIVATE ERROR')):
                    result = c.cleanup()
                self.assertFalse(result['complete']); self.assertEqual(query.call_count, 1)
                self.assertIn('process_cleanup', result['errors'])
                self.assertEqual(result['process_cleanup_diagnostic']['phase'], 'signal')
                self.assertNotIn('PRIVATE ERROR', str(result)); c.release()

    def test_pid_reuse_before_or_after_signal_never_authorizes_cleanup(self):
        for before in (True, False):
            with self.subTest(before=before):
                c, saved = self.owned(); changed = dict(saved, start='different process')
                with patch.object(c, 'process', side_effect=[changed] if before else [saved, changed]), \
                     patch.object(trial.os, 'killpg', side_effect=ProcessLookupError(errno.ESRCH, 'gone')) as kill:
                    result = c.cleanup()
                self.assertFalse(result['processes_stopped']); self.assertEqual(result['process_absence'], [])
                self.assertEqual(kill.call_count, 0 if before else 1); c.release()

    def test_group_presence_or_ambiguous_probe_never_counts_as_absence(self):
        for probe in ('present', 'permission', 'invalid'):
            with self.subTest(probe=probe):
                c, saved = self.owned(); queries=[]
                def process(*args, **kwargs): queries.append(1); return saved if len(queries)==1 else None
                def kill(pgid, sig):
                    if sig == signal.SIGKILL: raise ProcessLookupError(errno.ESRCH, 'gone')
                    if probe != 'present': raise OSError(errno.EPERM if probe == 'permission' else errno.EINVAL, 'PRIVATE')
                with patch.object(trial.sys, 'platform', 'darwin'), patch.object(c, 'process', side_effect=process), \
                     patch.object(trial.os, 'killpg', side_effect=kill): result=c.cleanup()
                self.assertFalse(result['complete']); self.assertFalse(result['processes_stopped'])
                self.assertEqual(result['process_absence'], [])
                self.assertEqual(result['process_signal_reconciliations'], []); c.release()

    def test_signal_delay_cannot_extend_existing_cleanup_deadline(self):
        c, saved = self.owned(); c.data['limits']['cleanup_seconds']=.03
        def kill(*args): time.sleep(.04); raise ProcessLookupError(errno.ESRCH, 'gone')
        with patch.object(c, 'process', return_value=saved) as query, patch.object(trial.os, 'killpg', side_effect=kill) as signaled:
            result=c.cleanup()
        self.assertFalse(result['complete']); self.assertEqual(query.call_count,1); self.assertEqual(signaled.call_count,1)

    def test_late_group_absence_cannot_extend_cleanup_deadline(self):
        c, saved = self.owned(); c.data['limits']['cleanup_seconds']=.03
        def kill(pgid, sig):
            if sig == 0: time.sleep(.04)
            raise ProcessLookupError(errno.ESRCH, 'gone')
        with patch.object(c, 'process', side_effect=[saved, None]), patch.object(trial.os, 'killpg', side_effect=kill):
            result=c.cleanup()
        self.assertFalse(result['processes_stopped'])
        self.assertEqual(result['process_signal_reconciliations'], [])

    def test_query_uncertainty_after_signal_blocks_auth_cleanup(self):
        c, saved = self.owned(); calls=[]
        def process(*args, **kwargs):
            calls.append(1)
            if len(calls)==1: return saved
            c.process_uncertain=True
            raise trial.plan.Refusal('process_query')
        with patch.object(c, 'process', side_effect=process), \
             patch.object(trial.os, 'killpg', side_effect=ProcessLookupError(errno.ESRCH, 'gone')):
            result=c.cleanup()
        self.assertFalse(result['processes_stopped']); self.assertTrue(result['process_query_uncertain'])
        self.assertEqual(result['process_cleanup_diagnostic']['reason'], 'process_query')
        self.assertIn('home_retained', result['errors'])

    def test_absence_query_uses_remaining_owner_window_not_another_two_seconds(self):
        c=self.controller(); c.cleanup_deadline=145
        until=100.004
        def query(argv, timeout, **kwargs):
            self.assertLessEqual(timeout, .004001)
            return dict(exit=1, stdout='', stderr='', stop_reason=None)
        with patch.object(trial.time, 'monotonic', return_value=100), \
             patch.object(trial, 'bounded', side_effect=query):
            self.assertIsNone(c.process(12345, cleanup=True, until=until))

    @unittest.skipUnless(sys.platform == 'darwin', 'Darwin exited-session EPERM reconciliation')
    def test_actual_owned_exited_child_permission_race(self):
        c=self.controller(); real_bounded=self.real_bounded
        child=subprocess.Popen([sys.executable,'-I','-S','-c',
            'import sys; sys.stdout.write("ready\\n"); sys.stdout.flush(); sys.stdin.buffer.read(1)'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        real_killpg=os.killpg; errors=[]
        try:
            self.assertTrue(select.select([child.stdout], [], [], 3)[0])
            self.assertEqual(child.stdout.readline(),b'ready\n')
            with patch.object(trial,'bounded',side_effect=real_bounded): saved=c.process(child.pid)
            self.assertEqual(saved['pgid'],child.pid)
            c.seen={child.pid:saved}; c.runtime['docker']=saved['exe']
            c.launch_called=c.launch_complete=True; c.live=Mock(); c.live.proc=Mock(pid=child.pid+1)
            c.live.close.return_value=dict(process_reaped=True,group_signal_error=None)
            original_process=c.process; first=True
            def process(pid, **kwargs):
                nonlocal first
                value=original_process(pid,**kwargs)
                if first:
                    first=False; child.stdin.close()
                    self.assertTrue(select.select([child.stdout], [], [], 3)[0])
                    child.stdout.read(1)
                return value
            def signal_owned(pgid, sig):
                self.assertEqual(pgid,child.pid)
                try:return real_killpg(pgid,sig)
                except OSError as exc:
                    if sig==signal.SIGKILL: errors.append(exc.errno); child.wait(timeout=3)
                    raise
            with patch.object(trial,'bounded',side_effect=real_bounded), \
                 patch.object(c,'process',side_effect=process), patch.object(trial.os,'killpg',side_effect=signal_owned):
                result=c.cleanup()
            self.assertEqual(errors,[errno.EPERM]); self.assertTrue(result['complete'])
            self.assertTrue(result['process_signal_reconciliations'][0]['group_absent'])
            self.assertIsNotNone(child.returncode)
        finally:
            if child.poll() is None: real_killpg(child.pid,signal.SIGKILL); child.wait(timeout=3)
            for stream in (child.stdin,child.stdout,child.stderr): stream.close()

if __name__ == '__main__': unittest.main()
