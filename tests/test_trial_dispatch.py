"""Frozen-trial input projection, never execution or authenticated admission."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.improvement import evaluation as ev
from scripts.improvement import trial_dispatch as dispatch
import test_improvement_evaluation as fixtures

ROOT = Path(__file__).resolve().parents[1]


class TrialDispatchTests(unittest.TestCase):
    def setUp(self):
        self.spec = fixtures.spec()
        self.experiment = ev.freeze(self.spec)

    def prepare(self, trial=None, **changes):
        args = dict(experiment=self.experiment, current_spec=self.spec,
                    trial_id=(trial or self.experiment['trials'][0])['trial_id'],
                    attempt_id='supervisor-attempt-1')
        args.update(changes)
        return dispatch.prepare(**args)

    def test_projects_only_selected_variant_and_arm(self):
        for trial in self.experiment['trials']:
            with self.subTest(variant=trial['variant'], arm=trial['arm']):
                result = self.prepare(trial)
                expected = {'request': 'Report observed verification.',
                            'files': {'check.txt': 'failure' if trial['variant'] == 'reproduction' else 'success'}}
                self.assertEqual(result.get('executor_input'), expected)
                self.assertEqual(result['binding']['trial'], trial)
                self.assertEqual(result['binding']['source_digest'], self.spec['identities'][trial['arm']])
                self.assertNotIn(self.spec['identities']['candidate' if trial['arm'] == 'baseline' else 'baseline'],
                                 json.dumps(result))

    def test_executor_excludes_grading_and_unselected_material(self):
        spec = copy.deepcopy(self.spec)
        first = spec['cases'][0]
        first['counterpart']['inputs']['request'] = 'UNSELECTED_VARIANT_MARKER'
        first['outcome_contract']['required'] = ['CONTRACT_MARKER']
        first['case_digest'] = ev.digest({k: v for k, v in first.items() if k != 'case_digest'})
        spec['checks'][first['case_id']]['reproduction'] = dict(
            contract_digest=ev.digest(first['outcome_contract']), criteria=[dict(
                id='grader', dimension='outcome', kind='value_equals', target='result',
                expected='GRADER_EXPECTED_MARKER', critical=True)])
        other = copy.deepcopy(first)
        other['case_id'] = 'other-case'
        other['inputs']['request'] = 'OTHER_CASE_MARKER'
        other['case_digest'] = ev.digest({k: v for k, v in other.items() if k != 'case_digest'})
        spec['cases'].append(other)
        spec['checks'][other['case_id']] = copy.deepcopy(spec['checks'][first['case_id']])
        plan = ev.freeze(spec)
        trial = next(t for t in plan['trials'] if t['case_id'] == first['case_id'] and t['variant'] == 'reproduction')
        result = self.prepare(trial, experiment=plan, current_spec=spec)
        encoded = ev.encoded(result['executor_input'])
        for marker in [b'UNSELECTED_VARIANT_MARKER', b'CONTRACT_MARKER', b'GRADER_EXPECTED_MARKER', b'OTHER_CASE_MARKER']:
            self.assertNotIn(marker, encoded)
        self.assertEqual(set(result['executor_input']), {'request', 'files'})
        for key in ('checks', 'expected', 'outcome_contract', 'counterpart', 'budget', 'runtime'):
            self.assertNotIn(key, result['executor_input'])

    def test_binding_digests_and_requested_runtime_are_declarations(self):
        result = self.prepare()
        self.assertEqual(set(result), {'schema_version', 'kind', 'binding', 'executor_input',
            'requested_runtime', 'executor_input_digest', 'dispatch_digest'})
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['kind'], 'development_trial_dispatch')
        self.assertEqual(result['binding']['experiment_digest'], self.experiment['experiment_digest'])
        self.assertEqual(result['binding']['experiment_budget_digest'], ev.digest(self.spec['budget']))
        self.assertEqual(result['requested_runtime'], self.spec['runtime'])
        self.assertEqual(result['executor_input_digest'], ev.digest(result['executor_input']))
        self.assertEqual(result['dispatch_digest'], ev.digest({k: v for k, v in result.items() if k != 'dispatch_digest'}))
        for key in ('experiment_budget', 'budget', 'observed_model', 'live_eligible', 'authenticated', 'holdout_custody'):
            self.assertNotIn(key, result)
        self.assertEqual(set(result['binding']), {'experiment_digest', 'trial', 'attempt_id',
                                                  'source_digest', 'experiment_budget_digest'})

    def test_output_is_detached_and_same_input_is_deterministic(self):
        result = self.prepare()
        self.assertEqual(result, self.prepare())
        original = ev.encoded(result)
        self.experiment['spec']['cases'][0]['inputs']['files']['check.txt'] = 'changed'
        self.spec['runtime']['capabilities'].append('changed')
        self.assertEqual(ev.encoded(result), original)
        result['binding']['trial']['arm'] = 'changed'
        self.assertNotEqual(self.experiment['trials'][0]['arm'], 'changed')

    def test_attempt_id_binds_output_without_claiming_cross_call_reservation(self):
        first = self.prepare()
        second = self.prepare(attempt_id='supervisor-attempt-2')
        self.assertEqual(first['executor_input'], second['executor_input'])
        self.assertNotEqual(first['dispatch_digest'], second['dispatch_digest'])
        self.assertEqual(first, self.prepare())  # Reservation/replay ownership is external.
        for value in (None, True, 1, '', '-wrong', 'a' * 129, 'attempt/escape'):
            with self.subTest(value=value), self.assertRaises(ev.Invalid):
                self.prepare(attempt_id=value)

    def test_unknown_and_malformed_trial_ids_refuse(self):
        for value in (None, True, 1, '', '0' * 64, 'a' * 65):
            with self.subTest(value=value), self.assertRaises(ev.Invalid):
                self.prepare(trial_id=value)

    def test_duplicate_or_tampered_inventory_refuses(self):
        for change in ('duplicate', 'binding', 'boolean_version', 'missing_identity'):
            plan = copy.deepcopy(self.experiment)
            if change == 'duplicate':
                plan['trials'].append(copy.deepcopy(plan['trials'][0]))
            elif change == 'binding':
                plan['trials'][0]['binding_digest'] = 'e' * 64
            elif change == 'boolean_version':
                plan['schema_version'] = True
            else:
                del plan['spec']['identities']['candidate']
            with self.subTest(change=change), self.assertRaises(ev.Invalid):
                self.prepare(experiment=plan)

    def test_current_spec_identity_runtime_and_budget_drift_refuse(self):
        for identity in self.spec['identities']:
            current = copy.deepcopy(self.spec)
            current['identities'][identity] = 'e' * 64
            with self.subTest(identity=identity), self.assertRaises(ev.Invalid):
                self.prepare(current_spec=current)
        for group, key, value in [('runtime', 'model', 'other'), ('budget', 'seconds', 31)]:
            current = copy.deepcopy(self.spec)
            current[group][key] = value
            with self.subTest(group=group), self.assertRaises(ev.Invalid):
                self.prepare(current_spec=current)

    def test_historical_grader_cannot_prepare_new_dispatch(self):
        spec = copy.deepcopy(self.spec)
        spec['identities']['grader'] = 'e' * 64
        plan = ev.freeze(spec)
        with self.assertRaises(ev.Invalid):
            self.prepare(plan['trials'][0], experiment=plan, current_spec=spec)

    def cli(self, body):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/improvement/trial_dispatch.py'), 'prepare'],
                              input=body, capture_output=True, timeout=10)

    def request(self):
        return dict(experiment=self.experiment, current_spec=self.spec,
                    trial_id=self.experiment['trials'][0]['trial_id'], attempt_id='cli-attempt')

    def test_cli_roundtrip(self):
        result = self.cli(ev.encoded(self.request()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), dispatch.prepare(**self.request()))
        self.assertEqual(result.stderr, b'')

    def test_cli_malformed_or_extra_fields_refuse_without_dispatch(self):
        for body in [b'{', b'{}', b'{"trial_id":1,"trial_id":2}', b'{"trial_id":NaN}', b'\xff',
                     ev.encoded(dict(self.request(), live_eligible=True)),
                     ev.encoded(dict(self.request(), attempt_id=True)), b' ' * (ev.MAX_BYTES + 1)]:
            with self.subTest(length=len(body)):
                result = self.cli(body)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout), {'status': 'rejected', 'reason': 'invalid_dispatch_input'})
                self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
