"""Evidence-contract regressions; these do not evaluate model behavior."""
import copy
import unittest

import sdlc_state as state


def results(mode='tdd'):
    phases = ['red', 'green', 'post-refactor', 'smoke'] if mode == 'tdd' else ['alternative', 'smoke']
    data = dict(candidate='candidate', verification_mode=mode, scenarios=[dict(
        id='S1', requirement='AC1', required=True, environment='local',
        prerequisites='scratch instance', actions='exercise public operation',
        expected='required result', failure='wrong result', cleanup='remove scratch state')], runs=[])
    for i, phase in enumerate(phases):
        data['runs'].append(dict(id=f'run-{i}', phase=phase, candidate='candidate',
            command=f'python verify.py {phase}', environment='local', observed='assertion observed',
            evidence=f'{phase}.log', status='passed', exit_code=1 if phase == 'red' else 0,
            intended_failure=phase == 'red', scenario_id='S1', execution_kind='real'))
    if mode == 'alternative':
        data['tdd_exception'] = dict(reason='No practical test seam in existing harness',
            attempted='Inspected harness and reproduced through public CLI',
            limitation='No failing-before automated test; CLI behavior checked directly')
    return data


class VerificationModes(unittest.TestCase):
    def validate(self, data, kind='behavior', criteria=None):
        state.validate_results(data, kind, 'candidate', criteria or ['AC1'])

    def test_existing_tdd_and_legacy_default_still_pass(self):
        data = results()
        self.validate(data)
        del data['verification_mode']
        self.validate(data)

    def test_alternative_requires_real_focused_and_separate_smoke(self):
        for kind in ('behavior', 'configuration'):
            self.validate(results('alternative'), kind)

    def test_missing_exception_detail_rejected(self):
        for field in ('reason', 'attempted', 'limitation'):
            data = results('alternative')
            del data['tdd_exception'][field]
            with self.subTest(field=field), self.assertRaises(state.GateError):
                self.validate(data)

    def test_failed_stale_mock_or_unknown_scenario_rejected(self):
        for update in ({'exit_code': 1}, {'candidate': 'old'}, {'execution_kind': 'mock'},
                       {'scenario_id': 'unknown'}, {'status': 'not-run'}):
            data = results('alternative')
            data['runs'][0].update(update)
            with self.subTest(update=update), self.assertRaises(state.GateError):
                self.validate(data)

    def test_uncovered_criterion_rejected(self):
        with self.assertRaises(state.GateError):
            self.validate(results('alternative'), criteria=['AC1', 'AC2'])

    def test_smoke_cannot_replace_focused_verification(self):
        data = results('alternative')
        data['runs'] = data['runs'][1:]
        with self.assertRaises(state.GateError):
            self.validate(data)

    def test_shared_evidence_or_wrong_order_rejected(self):
        for mode in ('tdd', 'alternative'):
            data = results(mode)
            data['runs'][-1]['evidence'] = data['runs'][0]['evidence']
            with self.subTest(mode=mode), self.assertRaises(state.GateError):
                self.validate(data)

            data = results(mode)
            data['runs'].reverse()
            with self.subTest(mode=mode), self.assertRaises(state.GateError):
                self.validate(data)

    def test_all_alternative_checks_precede_integration_smoke(self):
        data = results('alternative')
        late = copy.deepcopy(data['runs'][0])
        late.update(id='late-check', evidence='late.log')
        data['runs'].append(late)
        with self.assertRaises(state.GateError):
            self.validate(data)

    def test_tdd_cannot_silently_skip_red(self):
        data = results()
        data['runs'] = data['runs'][1:]
        with self.assertRaises(state.GateError):
            self.validate(data)

    def test_no_refactor_can_reuse_green_but_not_skip_smoke(self):
        data = results()
        data['refactor_performed'] = False
        data['runs'] = [r for r in data['runs'] if r['phase'] != 'post-refactor']
        self.validate(data)
        data['runs'] = data['runs'][:-1]
        with self.assertRaises(state.GateError):
            self.validate(data)

    def test_refactor_requires_post_change_check(self):
        data = results()
        data['refactor_performed'] = True
        data['runs'] = [r for r in data['runs'] if r['phase'] != 'post-refactor']
        with self.assertRaises(state.GateError):
            self.validate(data)

    def test_unknown_mode_and_mixed_claim_rejected(self):
        for mode in ('unknown', 'alternative'):
            data = results()
            data['verification_mode'] = mode
            data['tdd_exception'] = copy.deepcopy(results('alternative')['tdd_exception'])
            with self.subTest(mode=mode), self.assertRaises(state.GateError):
                self.validate(data)


if __name__ == '__main__':
    unittest.main()
