"""Validated plans and real setup/cleanup; Docker/extraction facts are FAKE."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import unittest
from unittest.mock import patch

import test_native_trial_plan as plan_fixtures
import test_native_routing as routing_fixtures
import test_native_trial_lifecycle as lifecycle

trial = lifecycle.trial


class SetupDocker(lifecycle.FakeDocker):
    def __init__(self, selected, write_errno=30):
        super().__init__(selected)
        self.write_errno = write_errno
        self.materialize = None

    def __call__(self, argv, timeout, **kwargs):
        args = argv[3:]
        if args[0] == 'cp':
            assert argv[:3] == [self.selected.data['runtime']['docker'], '--host',
                                'unix:///synthetic/docker.sock']
            self.calls.append(list(args))
            arm = Path(args[1][:-2]) / 'arm'
            self.staged = {
                'arm_mode': stat.S_IMODE(arm.stat().st_mode),
                'files': {str(p.relative_to(arm)): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
                          for p in arm.rglob('*') if p.is_file()},
            }
            return dict(exit=0, stdout='', stderr='', stop_reason=None)
        result = super().__call__(argv, timeout, **kwargs)
        if args[0] == 'exec':
            self.materialize = json.loads(kwargs['payload'])
            facts = json.loads(result['stdout'])
            facts['arm_write_errno'] = self.write_errno
            result['stdout'] = json.dumps(facts)
        return result


class NaturalSetupTests(unittest.TestCase):
    setUp = plan_fixtures.PlanTests.setUp
    load = plan_fixtures.PlanTests.load
    natural = routing_fixtures.RoutingPlanTests.natural

    def catalog_only(self):
        value = self.natural()
        value['inputs']['files'] = [r for r in reversed(value['inputs']['files'])
                                   if (r['kind'], r['path']) != ('bundle', 'instructions.md')]
        (self.inputs / 'bundle/instructions.md').unlink()
        return value

    def exercise(self, value, *, write_errno=30, failure=None):
        selected = self.load(value)
        frozen = copy.deepcopy(selected.data)
        docker = SetupDocker(selected, write_errno)
        with patch.object(trial, 'bounded', side_effect=docker), \
             patch.object(trial.native_isolation, 'extract_verified', side_effect=lifecycle.fake_extract), \
             patch.object(trial, 'copy_native_home', side_effect=AssertionError('auth must not be read')) as auth, \
             patch.object(trial.protocol, 'NativeSession', side_effect=AssertionError('native must not launch')) as native:
            controller = trial.Controller(selected)
            try:
                if failure:
                    with self.assertRaisesRegex(trial.plan.Refusal, '^'+failure+'$'):
                        controller.setup()
                else:
                    controller.setup()
                self.assertEqual(controller.data, frozen)
                self.assertFalse(controller.auth_copy_attempted)
                self.assertFalse(controller.launch_called)
                self.assertIsNone(controller.observation)
            finally:
                try:
                    cleanup = controller.cleanup()
                    self.assertTrue(cleanup['complete'])
                    self.assertFalse(docker.containers)
                    self.assertIsNone(docker.volume)
                    self.assertFalse(controller.control.exists())
                    auth.assert_not_called(); native.assert_not_called()
                finally:
                    controller.release()
        return selected, docker

    def test_natural_validated_catalog_without_entrypoint_completes_setup(self):
        selected, docker = self.exercise(self.catalog_only())
        self.assertNotIn('entrypoint', selected.data['inputs'])
        names = sorted(name for kind, name in selected.files if kind == 'bundle')
        self.assertEqual(docker.materialize['entrypoint'], names[0])
        self.assertEqual(docker.materialize['bundle_paths'], names)
        self.assertEqual(docker.staged['arm_mode'], 0o555)
        self.assertEqual(docker.staged['files'], {
            name: (selected.files['bundle', name], 0o444) for name in names})

    def test_forced_schema1_and_schema2_keep_explicit_entrypoint(self):
        for schema in (1, 2):
            with self.subTest(schema=schema):
                value = copy.deepcopy(self.value) if schema == 1 else self.natural()
                value['identity']['attempt_id'] = 'forced-'+str(schema)
                if schema == 2:
                    value['routing']['mode'] = 'forced_entrypoint'
                    value['inputs']['entrypoint'] = 'instructions.md'
                extra = self.inputs/'bundle/0-probe.txt'
                extra.write_bytes(b'SYNTHETIC_EARLIER_FILE')
                value['inputs']['files'].append(dict(kind='bundle', path='0-probe.txt',
                    sha256=hashlib.sha256(extra.read_bytes()).hexdigest()))
                _, docker = self.exercise(value)
                self.assertEqual(docker.materialize['bundle_paths'][0], '0-probe.txt')
                self.assertEqual(docker.materialize['entrypoint'], 'instructions.md')

    def test_natural_readonly_probe_failure_refuses_and_cleans_before_auth(self):
        _, docker = self.exercise(self.catalog_only(), write_errno=0, failure='executor_setup')
        self.assertIsNotNone(docker.materialize)


if __name__ == '__main__':
    unittest.main()
