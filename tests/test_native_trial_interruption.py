"""Interrupted production observation keeps finite progress through collection."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial
import native_trial_protocol as protocol
import test_native_trial_collection as collection_tests
from test_native_trial_protocol import FakeSession, usage
from test_native_trial_lifecycle import NoClock


class InterruptedSession(FakeSession):
    def __init__(self, point, error):
        super().__init__([usage()])
        self.point, self.error = point, error
        self.proc = Mock()

    def rpc(self, method, params):
        if method == self.point:
            self.calls.append((method, params))
            raise self.error('SYNTHETIC_PRIVATE_INTERRUPT')
        return super().rpc(method, params)

    def until(self, predicate):
        if self.events:
            return super().until(predicate)
        raise self.error('SYNTHETIC_PRIVATE_INTERRUPT')

    def start(self, *args):
        pass

    def close(self):
        return {'process_reaped': True, 'group_signal_error': None}


class InterruptionTests(unittest.TestCase):
    def test_interruption_preserves_exact_turn_progress_and_known_usage(self):
        for point, attempted, started in [('account/read', 0, 0),
                                           ('turn/start', 1, 0), ('observation', 1, 1)]:
            for error in (KeyboardInterrupt, SystemExit):
                with self.subTest(point=point, interruption=error.__name__):
                    session = InterruptedSession(point, error)
                    try:
                        result = protocol.observe(session, prompt='SYNTHETIC_TASK',
                            project='/synthetic/project', codehome='/synthetic/home/.codex',
                            metadata_check=lambda: {'status': 'recognized', 'compatibility_match': True},
                            soft_total=131072, soft_output=4096)
                    except (KeyboardInterrupt, SystemExit):
                        self.fail('Interrupted observation did not return retained progress')
                    self.assertEqual(result['status'], 'blocked')
                    self.assertEqual(result['reason'], 'interrupted')
                    self.assertEqual(result['initial_turn_requests_attempted'], attempted)
                    self.assertEqual(result['initial_turns'], started)
                    self.assertFalse(result['terminal_completed'])
                    self.assertEqual(result['usage']['notifications'], started)
                    self.assertEqual(result['usage']['latest'] is not None, bool(started))
                    self.assertNotIn('SYNTHETIC_PRIVATE_INTERRUPT', json.dumps(result))
                    self.assertEqual(sum(m == 'turn/start' for m, _ in session.calls), attempted)

    def test_interruption_does_not_replace_an_existing_soft_stop(self):
        session = InterruptedSession('turn/interrupt', KeyboardInterrupt)
        result = protocol.observe(session, prompt='SYNTHETIC_TASK',
            project='/synthetic/project', codehome='/synthetic/home/.codex',
            metadata_check=lambda: {'status': 'recognized', 'compatibility_match': True},
            soft_total=50, soft_output=4096)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['reason'], 'soft_usage_stop')
        self.assertEqual(result['post_stop_observation'], 'interrupted')
        self.assertTrue(result['interrupt_attempted'])
        self.assertEqual(result['usage']['notifications'], 1)
        self.assertEqual(sum(m == 'turn/interrupt' for m, _ in session.calls), 1)

    def test_production_observe_collection_and_finish_preserve_interruption(self):
        # Reuse declared-collection fake Docker; observation, collection, journal
        # and finish are production code, with no client or authentication bytes.
        fixture = collection_tests.CollectionTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        controller = fixture.controller()
        home = Mock(); home.root = controller.control / 'synthetic-codehome'
        home.root.mkdir(mode=0o700); home.identity = (1, 2)
        home.cleanup.return_value = {'home_absent': True}
        session = InterruptedSession('observation', KeyboardInterrupt)
        with patch.object(trial, 'copy_native_home', return_value=home), \
             patch.object(protocol, 'NativeSession', return_value=session), \
             patch.object(controller, 'metadata', return_value={
                 'status': 'recognized', 'compatibility_match': True}), \
             patch.object(trial.plan, 'load_plan', return_value=fixture.selected), \
             patch.object(trial, 'Controller', return_value=controller), \
             patch.object(controller, 'setup'), \
             patch.object(trial, 'supported_host'), \
             patch.object(trial, 'PhaseClock', NoClock):
            receipt = trial.run(Path('/synthetic/unused-plan'),
                                auth_source=Path('/synthetic/never-opened-auth'))
        observation, cleanup = receipt['observation'], receipt['cleanup']
        self.assertEqual(receipt['status'], 'blocked')
        self.assertEqual(receipt['reason'], 'interrupted')
        self.assertEqual(observation['initial_turns'], 1)
        self.assertEqual(receipt['observation']['usage']['notifications'], 1)
        self.assertEqual(receipt['collection']['status'], 'captured')
        self.assertTrue(cleanup['complete'])
        self.assertFalse(fixture.docker.containers)
        self.assertIsNone(fixture.docker.volume)
        self.assertFalse(controller.control.exists())
        records = list((controller.attempt / 'records').glob('*-observation.json'))
        self.assertEqual(len(records), 1)
        self.assertNotIn('SYNTHETIC_PRIVATE_INTERRUPT', json.dumps(receipt))


if __name__ == '__main__':
    unittest.main()
