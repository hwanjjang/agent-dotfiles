from pathlib import Path
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial


class ControllerTests(unittest.TestCase):
    def test_invalid_frozen_plan_never_reaches_authentication(self):
        with patch.object(trial.plan, 'load_plan', side_effect=trial.plan.Refusal('input_changed')), \
             patch.object(trial, 'copy_native_home') as copied:
            with self.assertRaisesRegex(trial.plan.Refusal, '^input_changed$'):
                trial.run(Path('/synthetic/plan.json'), auth_source=Path('/synthetic/auth.json'))
            copied.assert_not_called()

    def test_credential_free_fixture_rejects_an_authentication_argument(self):
        with patch.object(trial, 'copy_native_home') as copied:
            with self.assertRaisesRegex(trial.plan.Refusal, '^fixture_auth_forbidden$'):
                trial.run(Path('/synthetic/plan.json'), fixture=True,
                          auth_source=Path('/synthetic/auth.json'))
            copied.assert_not_called()

    @unittest.skipUnless(hasattr(__import__('signal'),'SIGALRM'),'POSIX interval timer required')
    def test_phase_clock_interrupts_and_restores_the_native_timer(self):
        import signal
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        previous=signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(trial.plan.Refusal,'^deadline$'):
            with trial.PhaseClock() as clock:
                clock.arm(time.monotonic()+.02)
                time.sleep(.5)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM),previous)

    def test_fixture_and_authenticated_profiles_disable_image_generation(self):
        import tomllib
        for profile in (trial.native_execution.PROFILE, trial.DIRECT_PROFILE):
            self.assertIs(tomllib.loads(profile)['features'].get('image_generation'), False)

    def test_qualification_prepares_short_loader_before_remote_setup(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            c = trial.Controller.__new__(trial.Controller)
            c.control = Path(folder).resolve()
            c.selected = SimpleNamespace(files=trial.plan.QUALIFICATION_FILES)
            c.data = {'inputs': {'entrypoint': 'skills/assigned/SKILL.md'}}
            c.protected = {}; c.journal = Mock(); c.checked = Mock()
            prompt = c.prepare_qualification()
            c.checked.assert_not_called()
            self.assertIn('/runtime/qualification.js', prompt)
            self.assertLess(len(prompt), 2500)
            self.assertGreater(len(c.qualification_source), len(prompt))
            self.assertNotIn(c.challenge, prompt)
            self.assertNotIn(c.challenge.encode(), c.qualification_source)
            self.assertTrue(c.verify_protected())
            c.ids = {'executor': 'synthetic-executor'}
            c.deliver_challenge()
            self.assertEqual(c.checked.call_args.kwargs['payload'], c.challenge.encode())

    def test_journal_reserves_cleanup_and_final_receipt_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = trial.Journal(Path(folder).resolve() / 'records', 65536)
            journal.save('ordinary', {'synthetic': 'x' * 32000})
            with self.assertRaisesRegex(trial.plan.Refusal, '^capture_limit$'):
                journal.save('too_large', {'synthetic': 'x' * 2000})
            journal.save('cleanup', {'synthetic': 'x' * 2000}, cleanup=True)
            path = journal.save('receipt', {'status': 'blocked'}, final=True)
            self.assertLessEqual(journal.used, 65536)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_control_cleanup_refuses_unknown_links_without_deleting_target(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            target = parent / 'outside'
            target.write_text('SYNTHETIC_OUTSIDE_TARGET')
            control = parent / 'control'
            control.mkdir(mode=0o700)
            info = control.stat()
            identity = info.st_dev, info.st_ino, info.st_uid
            (control / 'unknown').symlink_to(target)
            with self.assertRaises(trial.plan.Refusal):
                trial.remove_control(control, identity, time.monotonic() + 3)
            self.assertEqual(target.read_text(), 'SYNTHETIC_OUTSIDE_TARGET')
            (control / 'unknown').unlink()
            trial.remove_control(control, identity, time.monotonic() + 3)
            self.assertFalse(control.exists())

    def test_process_query_uncertainty_is_not_absence(self):
        good = {'exit': 0, 'stop_reason': None, 'stderr': '',
                'stdout': '123 100 123 Sun Oct 18 16:00:00 2026 /synthetic/codex'}
        self.assertEqual(trial.parse_process_query(good, 123)['pid'], 123)
        for changed in [{'exit': 1, 'stderr': 'QUERY_ERROR'},
                        {'stdout': '123 100 123 Sun Oct 18 16:00:00 2026 codex'},
                        {'stop_reason': 'timeout'}]:
            with self.assertRaises(trial.plan.Refusal):
                trial.parse_process_query(dict(good, **changed), 123)

    def test_child_inventory_uncertainty_is_not_an_empty_inventory(self):
        empty = {'exit': 1, 'stdout': '', 'stderr': '', 'stop_reason': None}
        self.assertEqual(trial.child_inventory(empty), [])
        self.assertEqual(trial.child_inventory(dict(empty, exit=0, stdout='123\n456')), [123, 456])
        for bad in (dict(empty, exit=0), dict(empty, stderr='ERROR'),
                    dict(empty, exit=0, stdout='123 BAD'),
                    dict(empty, exit=0, stdout=' '.join(str(i+1) for i in range(9)))):
            with self.assertRaises(trial.plan.Refusal):
                trial.child_inventory(bad)

    def test_native_close_starts_only_after_process_watcher_stops(self):
        from unittest.mock import Mock
        c=trial.Controller.__new__(trial.Controller)
        c.data={'limits':{'cleanup_seconds':45}}
        c.watch_stop=__import__('threading').Event();c.watcher=Mock()
        c.watcher.is_alive.return_value=False
        c.live=Mock()
        def close():
            self.assertTrue(c.watch_stop.is_set())
            c.watcher.join.assert_called_once()
            return {'process_reaped':True,'group_signal_error':None}
        c.live.close.side_effect=close
        c.launch_called=True;c.launch_complete=True;c.live.proc=Mock()
        c.seen={};c.process_uncertain=False;c.watch_error=False
        c.begun=set();c.volume_begun=False;c.home=None;c.capture_failed=False
        c.control=Path('/synthetic/absent');c.control_identity=(1,2,os.getuid());c.journal=Mock()
        c.cleanup()
        c.live.close.assert_called_once()
        self.assertNotIn('native_close',c.journal.save.call_args.args[1]['errors'])

    def test_cleanup_never_purges_auth_when_launch_or_queries_are_uncertain(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        for launch_unknown, query_unknown in ((True, False), (False, True)):
            controller = trial.Controller.__new__(trial.Controller)
            controller.data = {'limits': {'cleanup_seconds': 45}}
            controller.live = None
            controller.launch_called = launch_unknown
            controller.launch_complete = False
            controller.process_uncertain = query_unknown
            controller.watch_error = False
            controller.watch_stop = __import__('threading').Event()
            controller.watcher = None
            controller.seen = {}
            controller.begun = set()
            controller.volume_begun = False
            controller.home = Mock()
            controller.home.cleanup.return_value = {'status': 'incomplete', 'auth_absent': None}
            controller.runtime = {'codex': '/synthetic/codex'}
            controller.journal = Mock()
            controller.control = Path('/synthetic/control')
            controller.control_identity = (1, 2, os.getuid())
            controller.capture_failed = False
            with patch.object(trial, 'remove_control') as removed:
                result = controller.cleanup()
            self.assertFalse(result['processes_stopped'])
            self.assertFalse(result['complete'])
            self.assertFalse(controller.home.cleanup.call_args.kwargs['processes_stopped'])
            removed.assert_not_called()

    def test_container_boundary_refuses_a_writable_arm_or_host_bind(self):
        names = {'executor': 'owned', 'volume': 'owned-volume'}
        info = {'Id': 'a'*64, 'Name': '/owned', 'Image': 'sha256:'+'b'*64,
                'Config': {'User': '65532:65532', 'Labels': {trial.LABEL: 'c'*64}},
                'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True,
                    'Privileged': False, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
                    'PidMode': '', 'IpcMode': 'private', 'CgroupnsMode': 'private',
                    'UTSMode': '', 'UsernsMode': '', 'Runtime': 'runc',
                    'Memory': 768*1024**2, 'MemorySwap': 768*1024**2,
                    'PidsLimit': 128, 'NanoCpus': 1000000000,
                    'Tmpfs': {'/work': 'rw,nosuid,nodev,size=128m,mode=1777',
                              '/tmp': 'rw,nosuid,nodev,noexec,size=32m,mode=1777'}},
                'Mounts': [{'Type': 'volume', 'Name': 'owned-volume', 'Destination': '/runtime', 'RW': False}]}
        kwargs = {'names': names, 'image': info['Image'], 'binding': 'c'*64}
        self.assertTrue(trial.container_boundary(info, **kwargs))
        info['Mounts'][0]['RW'] = True
        self.assertFalse(trial.container_boundary(info, **kwargs))
        info['Mounts'][0]['RW'] = False
        info['HostConfig']['Binds'] = ['/host:/runtime']
        self.assertFalse(trial.container_boundary(info, **kwargs))

    def test_run_always_cleans_up_after_setup_or_observation_failure(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        selected = SimpleNamespace(data={'mode': 'trial', 'identity': {}, 'runtime': {}, 'limits': {}},
                                   digest='a'*64)
        for phase in ('setup', 'observe'):
            controller = Mock()
            controller.data = selected.data
            controller.home = None
            controller.archive = None
            controller.qualification = None
            controller.auth_copy_attempted = False
            controller.auth_copy_succeeded = False
            controller.capture_failed = False
            controller.observation = None
            controller.primary = None
            controller.verify_protected.return_value = None
            getattr(controller, phase).side_effect = RuntimeError('PRIVATE_RUNTIME_DETAIL')
            controller.cleanup.return_value = {'complete': True}
            controller.finish.return_value = {'status': 'blocked', 'reason': 'operation'}
            with patch.object(trial.plan, 'load_plan', return_value=selected), \
                 patch.object(trial, 'supported_host'), \
                 patch.object(trial, 'PhaseClock'), \
                 patch.object(trial, 'Controller', return_value=controller):
                result = trial.run(Path('/synthetic/plan.json'), auth_source=Path('/synthetic/auth.json'))
            controller.cleanup.assert_called_once()
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn('PRIVATE_RUNTIME_DETAIL', str(controller.finish.call_args))

    def test_recovery_refuses_unresolved_launch_before_any_cleanup_or_auth(self):
        with patch.object(trial, 'read_recovery', return_value=(None, {
                'native_launch_intent': [{'launch': 1}], 'native_launch_complete': [],
                'cleanup': []}, None)), \
             patch.object(trial, 'supported_host'), \
             patch.object(trial, 'copy_native_home') as copied, \
             patch.object(trial.Controller, 'cleanup') as cleaned:
            with self.assertRaisesRegex(trial.plan.Refusal, '^recovery_launch_unresolved$'):
                trial.recover(Path('/synthetic/attempt'))
            copied.assert_not_called()
            cleaned.assert_not_called()

    def test_resumed_journal_preserves_the_original_retained_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / 'records'
            first = trial.Journal(root, 65536)
            original = first.save('synthetic', {'value': 'fixed'})
            used = first.used
            second, records = trial.Journal.resume(root, 65536)
            self.assertEqual(second.used, used)
            self.assertEqual(records['synthetic'], [{'value': 'fixed'}])
            next_record = second.save('recovery', {'attempted': True}, cleanup=True)
            self.assertEqual(next_record.name, '002-recovery.json')
            self.assertGreater(second.used, used)
            self.assertEqual(original.read_text(), '{"value":"fixed"}\n')

    def test_control_cleanup_removes_only_owned_readonly_staging_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            control = Path(folder).resolve() / 'control'
            control.mkdir(mode=0o700)
            arm = control / 'runtime/arm'
            arm.mkdir(parents=True, mode=0o700)
            (arm / 'instructions.md').write_text('SYNTHETIC_ARM')
            (arm / 'instructions.md').chmod(0o444)
            arm.chmod(0o555)
            info = control.stat()
            try:
                trial.remove_control(control, (info.st_dev, info.st_ino, info.st_uid), time.monotonic()+3)
                self.assertFalse(control.exists())
            finally:
                if arm.exists():
                    arm.chmod(0o700)

    def test_control_command_postspawn_initialization_failure_reaps_its_child(self):
        import signal
        import subprocess
        original = subprocess.Popen
        children = []
        def launched(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        try:
            with patch.object(trial.subprocess, 'Popen', side_effect=launched), \
                 patch.object(trial.selectors, 'DefaultSelector', side_effect=RuntimeError('synthetic selector failure')):
                with self.assertRaisesRegex(RuntimeError, 'synthetic selector failure'):
                    trial.bounded([sys.executable, '-c', 'import time;time.sleep(30)'], 1)
            self.assertIsNotNone(children[0].returncode)
            self.assertTrue(all(stream.closed for stream in (children[0].stdout, children[0].stderr)))
        finally:
            for child in children:
                if child.returncode is None:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(timeout=2)
                for stream in (child.stdout, child.stderr):
                    stream.close()

    def test_owned_native_child_requires_exact_transport_or_helper_and_self_group(self):
        runtime = {'codex': '/synthetic/codex', 'docker': '/synthetic/docker',
                   'code_mode_host': '/synthetic/code-mode-host'}
        parent = {'pid': 123, 'exe': runtime['codex']}
        for executable in (runtime['docker'], runtime['code_mode_host']):
            child = {'pid': 456, 'ppid': 123, 'pgid': 456, 'start': 'fixed', 'exe': executable}
            self.assertTrue(trial.owned_native_child(child, parent, runtime))
            for bad in (dict(child, ppid=999), dict(child, pgid=123),
                        dict(child, exe='/other/docker'), dict(child, exe='docker')):
                self.assertFalse(trial.owned_native_child(bad, parent, runtime))
        self.assertFalse(trial.owned_native_child(dict(child, exe=runtime['codex']), parent, runtime))


if __name__ == '__main__':
    unittest.main()
