"""Fake Docker lifecycle with real synthetic files; no native/account execution."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial


class FakeDocker:
    """Finite in-memory command responses, including inspected resource state."""
    def __init__(self, selected, reject_boundary=False):
        self.selected = selected
        self.names = trial.resource_names(selected.data['identity'])
        self.containers = {}
        self.volume = None
        self.calls = []
        self.staged = None
        self.reject_boundary = reject_boundary

    def __call__(self, argv, timeout, *, limit=12000, env=None, payload=None):
        assert argv[:3] == [self.selected.data['runtime']['docker'], '--host', 'unix:///synthetic/docker.sock']
        args = argv[3:]
        self.calls.append(list(args))
        result = {'exit': 0, 'stdout': '', 'stderr': '', 'stop_reason': None}
        if args[:2] == ['image', 'inspect']:
            value = {'Id': self.selected.data['runtime']['image'], 'Architecture': 'arm64', 'Os': 'linux'}
        elif args[:2] == ['volume', 'inspect']:
            if self.volume is None:
                return dict(result, exit=1, stderr='No such volume')
            value = [self.volume]
        elif args[:2] == ['volume', 'create']:
            self.volume = {'Name': self.names['volume'], 'CreatedAt': 'synthetic-creation-1',
                           'Labels': {trial.LABEL: self.selected.digest}}
            value = self.names['volume']
        elif args[:2] == ['volume', 'rm']:
            self.volume = None; value = ''
        elif args[0] == 'inspect':
            value = self.containers.get(args[-1])
            if value is None:
                return dict(result, exit=1, stderr='No such object')
        elif args[0] == 'create':
            name = args[args.index('--name')+1]
            stage = name == self.names['stage']
            memory = (256 if stage else 768)*1024**2
            info = {'Id': ('1' if stage else '2')*64, 'Name': '/'+name,
                    'Image': self.selected.data['runtime']['image'],
                    'Config': {'User': '0:0' if stage else '65532:65532',
                               'Labels': {trial.LABEL: self.selected.digest}},
                    'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True,
                        'Privileged': False, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
                        'PidMode': '', 'IpcMode': 'private', 'CgroupnsMode': 'private', 'UTSMode': '',
                        'UsernsMode': '', 'Runtime': 'runc', 'Memory': memory, 'MemorySwap': memory,
                        'PidsLimit': 64 if stage else 128, 'NanoCpus': 1000000000,
                        'Tmpfs': {'/tmp': 'rw,nosuid,nodev,noexec,size=32m,mode=1777'}},
                    'Mounts': [{'Type': 'volume', 'Name': self.names['volume'],
                                'Destination': '/runtime', 'RW': stage}]}
            if not stage:
                info['HostConfig']['Tmpfs']['/work'] = 'rw,nosuid,nodev,size=128m,mode=1777'
                if self.reject_boundary: info['HostConfig']['NetworkMode'] = 'host'
            self.containers[name] = info
            value = info['Id']
        elif args[0] == 'cp':
            root = Path(args[1][:-2])
            self.staged = {'arm_mode': stat.S_IMODE((root/'arm').stat().st_mode),
                           'entry_mode': stat.S_IMODE((root/'arm/instructions.md').stat().st_mode),
                           'entry_bytes': (root/'arm/instructions.md').read_bytes(),
                           'case_not_in_runtime': not (root/'fixture.txt').exists()}
            value = ''
        elif args[0] == 'rm':
            for name, info in list(self.containers.items()):
                if info['Id'] == args[-1]: del self.containers[name]
            value = ''
        elif args[0] == 'start': value = args[-1]
        elif args[0] == 'exec':
            contents = json.loads(payload)
            case = [{'path': item['path'], 'sha256': hashlib.sha256(base64.b64decode(item['bytes'])).hexdigest()}
                    for item in contents['case']]
            bundle = [{'path': name, 'sha256': hashlib.sha256(data).hexdigest()}
                      for (kind, name), data in sorted(self.selected.files.items()) if kind == 'bundle']
            value = {'uid': 65532, 'cap_eff': '0000000000000000', 'no_new_privs': '1', 'seccomp': '2',
                     'loopback_only': True, 'case_digest': trial.plan.digest(case),
                     'bundle_digest': trial.plan.digest(bundle), 'arm_inventory_exact': True, 'arm_write_errno': 30,
                     'mount_write_errno': 30, 'runtime_script_verified': None, 'runtime_digest': trial.EXECUTOR_SHA256}
        else: raise AssertionError('Unexpected fake command: '+args[0])
        return dict(result, stdout=json.dumps(value) if isinstance(value, (dict,list)) else value)


class NoClock:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def arm(self, deadline): pass
    def cancel(self): pass


def synthetic_selected(root):
    state = root/'state'; state.mkdir(mode=0o700)
    archive = root/'synthetic-archive'; archive.write_bytes(b'fake archive, never executed')
    files = {('case','fixture.txt'): b'SYNTHETIC_CASE', ('bundle','instructions.md'): b'SYNTHETIC_ARM'}
    data = {'schema_version':1, 'profile':trial.plan.PROFILE, 'mode':'trial',
            'identity':{'trial_id':'a'*64,'attempt_id':'synthetic-attempt','arm':'baseline'},
            'state_root':str(state), 'inputs':{'entrypoint':'instructions.md'},
            'prompt':'Synthetic selected task', 'sources':{}, 'limits':dict(trial.plan.LIMITS),
            'runtime':{'docker':'/synthetic/docker','docker_host':'unix:///synthetic/docker.sock',
                       'image':'sha256:'+'d'*64, 'codex':'/synthetic/codex',
                       'code_mode_host':'/synthetic/code-mode-host','executor_archive':str(archive),
                       'hashes':{'executor_archive':hashlib.sha256(archive.read_bytes()).hexdigest()}}}
    return SimpleNamespace(data=data, files=files, digest=trial.plan.digest(data))


def fake_extract(archive, root):
    binary = root/'bin/codex'; binary.parent.mkdir(mode=0o755)
    binary.write_bytes(b'synthetic runtime, never executed'); binary.chmod(0o555)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('NATIVE_TRIAL_TEST_TMP'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.selected = synthetic_selected(self.root)
        self.docker = FakeDocker(self.selected)
        self.addCleanup(patch.stopall)
        patch.object(trial, 'bounded', side_effect=self.docker).start()
        patch.object(trial.native_isolation, 'extract_verified', side_effect=fake_extract).start()
        self.copy_auth = patch.object(trial, 'copy_native_home', side_effect=AssertionError('auth must not be read')).start()
        patch.object(trial, 'supported_host').start()

    def controller(self):
        controller = trial.Controller(self.selected)
        self.addCleanup(controller.release)
        return controller

    def test_staging_is_readonly_for_arm_and_executor_volume_uses_nocopy(self):
        controller = self.controller(); controller.setup()
        self.assertEqual(self.docker.staged, {'arm_mode':0o555,'entry_mode':0o444,
            'entry_bytes':b'SYNTHETIC_ARM','case_not_in_runtime':True})
        creates = [args for args in self.docker.calls if args[0]=='create']
        self.assertEqual(len(creates), 2)
        for index,args in enumerate(creates):
            self.assertIn('--read-only', args)
            mount = args[args.index('--mount')+1]
            self.assertIn('volume-nocopy', mount)
            self.assertEqual('readonly' in mount, index==1)
            self.assertNotIn('--volume', args)
        result = controller.cleanup()
        self.assertTrue(result['complete']); self.assertIsNone(self.docker.volume)
        self.assertFalse(self.docker.containers); self.assertTrue(controller.attempt.exists())
        self.copy_auth.assert_not_called()

    def fake_run(self, observe):
        with patch.object(trial.plan,'load_plan',return_value=self.selected), \
             patch.object(trial,'PhaseClock',NoClock), \
             patch.object(trial.Controller,'observe',autospec=True,side_effect=observe):
            return trial.run(self.root/'unused-plan',auth_source=self.root/'never-opened-auth')

    def test_rejected_observed_boundary_refuses_before_auth_and_cleans(self):
        self.docker.reject_boundary = True
        observe = Mock(side_effect=AssertionError('observation must not start'))
        result = self.fake_run(observe)
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(result['cleanup']['complete'])
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        observe.assert_not_called(); self.copy_auth.assert_not_called()

    def test_fake_observed_completion_runs_real_finally_cleanup_and_keeps_claim(self):
        def observed(controller,*args,**kwargs):
            controller.observation = {'status':'completed_ungraded','terminal_completed':True}
        result = self.fake_run(observed)
        self.assertEqual(result['status'],'completed_ungraded'); self.assertFalse(result['live_eligible'])
        self.assertTrue(result['cleanup']['complete'])
        attempt = Path(self.selected.data['state_root'])/('a'*64)/'synthetic-attempt'
        self.assertTrue((attempt/'manifest.json').exists()); self.assertFalse((attempt/'control').exists())
        self.assertTrue(list((attempt/'records').glob('*-receipt.json')))
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        with self.assertRaisesRegex(trial.plan.Refusal,'attempt_exists'): self.controller()
        self.copy_auth.assert_not_called()

    def test_observation_failure_keeps_primary_and_runs_cleanup(self):
        def failed(*args,**kwargs): raise RuntimeError('private detail must be dropped')
        result = self.fake_run(failed)
        self.assertEqual(result['status'],'blocked'); self.assertTrue(result['cleanup']['complete'])
        self.assertNotIn('private detail',json.dumps(result))
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        self.copy_auth.assert_not_called()

    def test_replaced_volume_creation_identity_is_not_removed(self):
        controller = self.controller(); controller.setup()
        self.docker.volume['CreatedAt'] = 'different-creation'
        result = controller.cleanup()
        self.assertFalse(result['complete']); self.assertIn('volume_cleanup',result['errors'])
        self.assertIsNotNone(self.docker.volume)
        self.assertFalse(any(args[:2]==['volume','rm'] for args in self.docker.calls))

    def recovery_records(self, controller):
        controller.release()
        journal, records = trial.Journal.resume(controller.attempt/'records', self.selected.data['limits']['retained_bytes'])
        return journal, records

    def test_recovery_setup_residue_uses_exact_existing_journal_without_auth(self):
        controller = self.controller(); controller.setup()
        journal, records = self.recovery_records(controller)
        with patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)), \
             patch.object(trial.protocol.NativeSession,'start',side_effect=AssertionError('no native restart')) as start:
            result = trial.recover(controller.attempt)
        self.assertEqual(result,{'status':'reconciled','cleanup_complete':True})
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        self.assertTrue((controller.attempt/'manifest.json').exists())
        self.copy_auth.assert_not_called(); start.assert_not_called()

    def test_recovery_launch_without_prior_supervision_refuses_before_cleanup(self):
        controller = self.controller(); controller.setup()
        journal, records = self.recovery_records(controller)
        records['native_launch_intent'] = [{'launch':1,'executable':'/synthetic/codex'}]
        records['native_launch_complete'] = [{'pid':123,'owner_digest':'a'*64}]
        before = copy.deepcopy(self.docker.containers)
        with patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)):
            with self.assertRaisesRegex(trial.plan.Refusal,'recovery_launch_unresolved'):
                trial.recover(controller.attempt)
        self.assertEqual(self.docker.containers,before); self.copy_auth.assert_not_called()

    def test_recovery_changed_binding_refuses_before_resource_cleanup(self):
        controller = self.controller(); controller.setup()
        journal, records = self.recovery_records(controller)
        records['frozen_binding'][0]['manifest_digest'] = 'f'*64
        calls = len(self.docker.calls)
        with patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)):
            with self.assertRaisesRegex(trial.plan.Refusal,'recovery_binding'):
                trial.recover(controller.attempt)
        self.assertEqual(len(self.docker.calls),calls)
        self.copy_auth.assert_not_called()

    def test_recovery_auth_copy_intent_without_home_identity_retains_control(self):
        controller = self.controller(); controller.setup()
        journal, records = self.recovery_records(controller)
        records['auth_copy_intent'] = [{'attempted': True}]
        calls = len(self.docker.calls)
        with patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)):
            with self.assertRaisesRegex(trial.plan.Refusal,'recovery_home_unresolved'):
                trial.recover(controller.attempt)
        self.assertEqual(len(self.docker.calls),calls)
        self.assertTrue(controller.control.exists()); self.copy_auth.assert_not_called()

    def test_recovery_prior_supervision_still_rechecks_saved_process_absence(self):
        controller = self.controller(); controller.setup()
        journal, records = self.recovery_records(controller)
        owner={'pid':123,'ppid':100,'pgid':123,'start':'synthetic-start','exe':'/synthetic/codex'}
        records.update(native_launch_intent=[{'launch':1,'executable':'/synthetic/codex'}],
            native_launch_complete=[{'pid':123,'owner_digest':trial.plan.digest(owner)}],process_owner=[owner],
            cleanup=[{'processes_stopped':True,'watch_uncertain':False,'process_query_uncertain':False}])
        def uncertain(self,pid,**kwargs):
            self.process_uncertain=True
            raise trial.plan.Refusal('process_query')
        with patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)), \
             patch.object(trial.Controller,'process',autospec=True,side_effect=uncertain) as query:
            result=trial.recover(controller.attempt)
        self.assertEqual(result['status'],'blocked'); self.assertFalse(result['cleanup_complete'])
        query.assert_called_once(); self.copy_auth.assert_not_called()
        self.assertTrue(controller.control.exists())


if __name__=='__main__': unittest.main()
