"""Fixed post-tool deadline scenario; fake protocol only, no native/model claim."""
import json
import shutil
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/improvement'))
import native_execution as runner
FAKE = ROOT/'tests/fixtures/native_execution_fake.py'
SCENARIO = 'response-deadline-after-tools'


class DeadlineScenarioTests(unittest.TestCase):
    def test_verified_tool_outputs_are_held_to_original_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'attempt'
            started = time.monotonic()
            receipt = runner.run_fixture(output, [sys.executable, str(FAKE), 'success'],
                [sys.executable, '-c', 'pass'], timeout=2, scenario=SCENARIO)
            self.assertEqual(receipt['status'], 'blocked')
            self.assertEqual(receipt['mock_submissions_observed'], 2)
            self.assertEqual(receipt['fault_observation'], {
                'scenario': SCENARIO, 'checkpoint_reached': True,
                'response_withheld': True, 'deadline_reached': True})
            self.assertGreaterEqual(receipt['elapsed_seconds'], 2)
            self.assertLess(time.monotonic()-started, 5)
            self.assertFalse(receipt['live_eligible'])
            self.assertFalse(receipt['authentication_qualified'])
            self.assertFalse(receipt['isolation_qualified'])
            self.assertTrue(receipt['cleanup']['harness']['process_reaped'])
            self.assertTrue(receipt['cleanup']['listeners_closed'])
            self.assertTrue(receipt['cleanup']['temporary_home_absent'])
            self.assertEqual(receipt, json.loads((output/'receipt.json').read_text()))
            self.assertLessEqual(sum(p.stat().st_size for p in output.iterdir()), receipt['archive']['limit_bytes'])
            self.assertEqual((output/'receipt.json').stat().st_mode & 0o777, 0o600)
            events = [json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
            self.assertEqual(sum(e['kind']=='mock_response' for e in events), 1)
            self.assertEqual(sum(e['kind']=='fault_checkpoint' for e in events), 1)

    def test_omitted_and_explicit_completion_have_the_same_receipt_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            receipts = []
            for name, options in [('omitted', {}), ('explicit', {'scenario': 'completion'})]:
                with self.subTest(plan=name):
                    receipt = runner.run_fixture(Path(folder)/name,
                        [sys.executable, str(FAKE), 'success'], [sys.executable, '-c', 'pass'],
                        timeout=3, **options)
                    self.assertEqual(receipt['scenario'], 'completion')
                    self.assertNotIn('fault_observation', receipt)
                    self.assertEqual(receipt['status'], 'mock_complete')
                    self.assertEqual(receipt['mock_submissions_observed'], 2)
                    self.assertEqual(receipt['terminal']['status'], 'completed')
                    self.assertIsNone(receipt['reason'])
                    self.assertIsNone(receipt['provider_error'])
                    self.assertTrue(receipt['cleanup']['harness']['process_reaped'])
                    self.assertTrue(receipt['cleanup']['listeners_closed'])
                    self.assertTrue(receipt['cleanup']['temporary_home_absent'])
                    receipts.append(receipt)
            # Attempt IDs, timestamps, temp-path hashes and elapsed time differ.
            # Compare the public semantic contract, not incidental identity.
            fields = ['schema_version', 'kind', 'scenario', 'status', 'reason',
                      'mock_submissions_observed', 'provider_error', 'live_eligible',
                      'authentication_qualified', 'isolation_qualified', 'model', 'usage']
            self.assertEqual({k: receipts[0][k] for k in fields},
                             {k: receipts[1][k] for k in fields})

    def test_unknown_scenario_refuses_before_side_effects(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'Archive') as archive, patch.object(runner, 'Session') as session:
            with self.assertRaisesRegex(ValueError, 'unsupported_scenario'):
                runner.run_fixture(Path(folder)/'attempt', [sys.executable], [sys.executable], scenario='disconnect')
            archive.assert_not_called()
            session.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])

    @staticmethod
    def payload(mode='valid'):
        nested = ['apply_patch', 'exec_command', 'view_image', 'write_stdin', 'skills__list', 'skills__read']
        tools = [{'name': 'exec', 'type': 'custom', 'description': '\n'.join('### `'+x+'`' for x in nested)},
                 {'name': 'wait', 'type': 'function'}]
        checks = [{'type': 'input_text', 'text': 'CELL1_COMPLETED'}]
        for name, marker in [('assigned_body', 'ASSIGNED_REMOTE_SKILL_BODY'), ('assigned_reference', 'ASSIGNED_REMOTE_SKILL_REFERENCE')]:
            checks.append({'type': 'input_text', 'text': json.dumps({'check': name, 'result': {'contents': 'wrong' if mode==name else marker}})})
        outputs = [{'type': 'function_call_output', 'output': 'wrong' if mode=='collaboration' else 'unsupported call: collaborationlist_agents'},
                   {'type': 'custom_tool_call_output', 'output': checks}]
        if mode == 'echo':
            outputs = [{'type': 'message', 'content': json.dumps(outputs)}]
        return json.dumps({'model': 'gpt-6-luna', 'stream': True, 'tools': tools, 'input': outputs}).encode()

    def test_early_close_is_not_a_deadline_observation(self):
        archive = Mock()
        provider = runner.FixtureProvider(archive, time.monotonic()+30, 'file:///synthetic', scenario=SCENARIO)
        provider.requests = 1
        provider.closing.set()
        with self.assertRaisesRegex(runner.Refusal, 'response_hold_cancelled_before_deadline'):
            provider.response(self.payload())
        self.assertTrue(provider.fault_observation['checkpoint_reached'])
        self.assertTrue(provider.fault_observation['response_withheld'])
        self.assertFalse(provider.fault_observation['deadline_reached'])
        self.assertFalse(provider.completed)

    def test_unverified_tool_evidence_cannot_arm_deadline(self):
        for mode in ['assigned_body', 'assigned_reference', 'collaboration', 'echo']:
            with self.subTest(mode=mode):
                archive = Mock()
                provider = runner.FixtureProvider(archive, time.monotonic()+30, 'file:///synthetic', scenario=SCENARIO)
                provider.requests = 1
                provider.closing.set()
                with self.assertRaises(runner.Refusal):
                    provider.response(self.payload(mode))
                self.assertFalse(provider.fault_observation['checkpoint_reached'])
                self.assertFalse(provider.fault_observation['response_withheld'])
                self.assertFalse(provider.fault_observation['deadline_reached'])
                archive.record.assert_not_called()

    def test_setup_timeout_does_not_claim_post_tool_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = runner.run_fixture(Path(folder)/'attempt', [sys.executable, str(FAKE), 'silent'],
                [sys.executable, '-c', 'pass'], timeout=.2, scenario=SCENARIO)
            self.assertEqual(receipt['status'], 'blocked')
            self.assertEqual(receipt['mock_submissions_observed'], 0)
            self.assertFalse(receipt['fault_observation']['checkpoint_reached'])
            self.assertFalse(receipt['fault_observation']['deadline_reached'])
            self.assertTrue(receipt['cleanup']['listeners_closed'])
            self.assertTrue(receipt['cleanup']['temporary_home_absent'])

    def test_deadline_observation_does_not_hide_cleanup_uncertainty(self):
        original = runner.Session.close
        def uncertain(session):
            result = original(session)
            result['group_signal_error'] = 'synthetic cleanup uncertainty'
            return result
        with tempfile.TemporaryDirectory() as folder, patch.object(runner.Session, 'close', uncertain):
            receipt = runner.run_fixture(Path(folder)/'attempt', [sys.executable, str(FAKE), 'success'],
                [sys.executable, '-c', 'pass'], timeout=2, scenario=SCENARIO)
            self.assertEqual(receipt['status'], 'blocked')
            self.assertTrue(receipt['fault_observation']['deadline_reached'])
            self.assertIn('group_signal_error', receipt['cleanup']['harness'])
            self.assertFalse(receipt['cleanup']['temporary_home_absent'])
            # This fake creates no descendants; its original close reaped it.
            # Only this test owner may remove its known retained synthetic root.
            self.assertTrue(receipt['cleanup']['harness']['process_reaped'])
            shutil.rmtree(receipt['cleanup']['retained_temporary_root'])


if __name__ == '__main__':
    unittest.main()
