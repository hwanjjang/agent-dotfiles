"""Native delivery lifecycle in disposable homes; no client or model calls."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_setup_account as fixtures

setup = fixtures.setup
storage = fixtures.storage
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from account.observation.store import Store
from account_doctor import diagnose


class NativeInstallerLifecycleTests(unittest.TestCase):
    # Reuse helpers only: inheriting the fixture TestCase repeats its tests.
    setUp = fixtures.AccountSetupTests.setUp
    git = fixtures.AccountSetupTests.git
    commit = fixtures.AccountSetupTests.commit
    prepare = fixtures.AccountSetupTests.prepare
    apply = fixtures.AccountSetupTests.apply
    config = fixtures.AccountSetupTests.config

    def native_grant(self):
        return Store(self.home).grant(self.repo, client='claude', source='claude-hooks-v1')

    def test_selected_update_rollback_and_uninstall_preserve_store_and_personal_settings(self):
        personal = {'permissions': {'deny': ['Bash(rm *)']}, 'hooks': {
            'Stop': [{'hooks': [{'command': 'personal-check'}]}]}}
        settings = self.config('.claude/settings.json', personal)
        grant = self.native_grant()
        self.apply(observation_registration=grant['registration_id'])
        payload = json.dumps(dict(cwd=str(self.repo), session_id='session-1',
                                  hook_event_name='SessionStart')).encode()
        callback = subprocess.run([sys.executable, str(self.home / '.agents/bin/observation-hook.py'),
                                   grant['registration_id'], grant['epoch']], cwd=self.repo,
                                  input=payload, capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'', b''))
        self.assertEqual(len(Store(self.home).events(grant['registration_id'])), 1)
        observations = self.home / '.agents/agent-dotfiles/observations'
        private_before = storage.observed(observations)
        settings_before = settings.read_bytes()
        receipt_before = setup.load_receipt(self.home)
        policy = self.repo / 'policies/communication.md'
        policy.write_text(policy.read_text() + '\nSynthetic update.\n')
        self.commit('policy update')
        transaction = self.apply(action='update')
        self.assertIsNotNone(transaction)
        with storage.lock(self.home):
            storage.rollback(self.home, transaction)
        self.assertEqual(settings.read_bytes(), settings_before)
        self.assertEqual(setup.load_receipt(self.home), receipt_before)
        self.assertEqual(storage.observed(observations), private_before)
        commands = [h['command'] for route in json.loads(settings.read_text())['hooks']['SessionStart']
                    for h in route['hooks']]
        self.assertTrue(any('planning-hook.py' in c for c in commands))
        self.assertTrue(any('observation-hook.py' in c for c in commands))
        self.apply(action='uninstall')
        self.assertEqual(json.loads(settings.read_text()), personal)
        self.assertEqual(storage.observed(observations), private_before)
        self.assertEqual(len(Store(self.home).events(grant['registration_id'])), 1)
        self.assertFalse((self.home / '.agents/bin/observation-hook.py').exists())

    def test_rollback_of_selection_retains_planning_and_grant(self):
        self.apply()
        settings = self.home / '.claude/settings.json'
        before = settings.read_bytes()
        grant = self.native_grant()
        observations = self.home / '.agents/agent-dotfiles/observations'
        private_before = storage.observed(observations)
        transaction = self.apply(action='update', observation_registration=grant['registration_id'])
        with storage.lock(self.home):
            storage.rollback(self.home, transaction)
        self.assertEqual(settings.read_bytes(), before)
        self.assertIn('planning-hook.py', settings.read_text())
        self.assertNotIn('observation-hook.py', settings.read_text())
        self.assertIsNone(setup.load_receipt(self.home)['observation'])
        self.assertEqual(storage.observed(observations), private_before)

    def test_selected_rollback_refuses_local_drift_without_losing_observations(self):
        grant = self.native_grant()
        self.apply(observation_registration=grant['registration_id'])
        policy = self.repo / 'policies/communication.md'
        policy.write_text(policy.read_text() + '\nSynthetic update.\n')
        self.commit('update for guarded rollback')
        transaction = self.apply(action='update')
        delivered = self.home / setup.BUNDLE / 'policies/communication.md'
        delivered.write_text('Personal edit after update.\n')
        before = storage.observed(self.home)
        with storage.lock(self.home):
            with self.assertRaises(ValueError):
                storage.rollback(self.home, transaction)
        self.assertEqual(storage.observed(self.home), before)
        self.assertIsNotNone(Store(self.home).registration(grant['registration_id']))

    def test_selection_refuses_revoked_expired_synthetic_and_unknown_grants(self):
        native = self.native_grant()
        synthetic = Store(self.home).grant(self.repo, start_after=0)
        for ident in (synthetic['registration_id'],):
            with self.subTest(registration=ident):
                before = storage.observed(self.home)
                with self.assertRaisesRegex(ValueError, 'Select an active Claude observation grant'):
                    self.prepare(observation_registration=ident)
                self.assertEqual(storage.observed(self.home), before)
        expires = Store(self.home).registration(native['registration_id'])['expires_at']
        before = storage.observed(self.home)
        unknown = subprocess.run([sys.executable, str(ROOT / 'scripts/setup_account.py'),
                                  'install', '--home', str(self.home), '--repo', str(self.repo),
                                  '--observation-registration', '0' * 64],
                                 capture_output=True, timeout=10)
        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(unknown.stdout, b'')
        self.assertNotIn(b'Traceback', unknown.stderr)
        self.assertEqual(storage.observed(self.home), before)
        with patch('account.observation.store.time.time', return_value=expires + 1):
            with self.assertRaisesRegex(ValueError, 'Select an active Claude observation grant'):
                self.prepare(observation_registration=native['registration_id'])
        Store(self.home).revoke(native['registration_id'])
        with self.assertRaisesRegex(ValueError, 'Select an active Claude observation grant'):
            self.prepare(observation_registration=native['registration_id'])
        self.assertFalse((self.home / storage.RECEIPT).exists())
        self.assertFalse((self.home / '.agents/bin/observation-hook.py').exists())

    def test_malformed_observation_receipt_is_rejected_before_mutation(self):
        grant = self.native_grant()
        self.apply(observation_registration=grant['registration_id'])
        receipt = self.home / storage.RECEIPT
        original = json.loads(receipt.read_text())
        for bad in ('invalid', {}, {'client': 'synthetic', 'registration_id': grant['registration_id'],
                                    'epoch': grant['epoch']},
                    {'client': 'claude', 'registration_id': '../escape', 'epoch': grant['epoch']},
                    {'client': 'claude', 'registration_id': grant['registration_id'], 'epoch': 'invalid'}):
            with self.subTest(observation=bad):
                receipt.write_text(json.dumps(dict(original, observation=bad)))
                before = storage.observed(self.home)
                with self.assertRaisesRegex(ValueError, 'Invalid observation receipt'):
                    setup.load_receipt(self.home)
                with self.assertRaisesRegex(ValueError, 'Invalid observation receipt'):
                    self.prepare(action='uninstall')
                self.assertEqual(storage.observed(self.home), before)

    def test_downgrade_requires_explicit_disable_and_retains_planning(self):
        grant = self.native_grant()
        self.apply(observation_registration=grant['registration_id'])
        (self.repo / 'account/observation/native.py').unlink()
        self.commit('synthetic revision without native adapter')
        before = storage.observed(self.home)
        with self.assertRaisesRegex(ValueError, 'Selected revision has no native observation adapter'):
            self.prepare(action='update')
        self.assertEqual(storage.observed(self.home), before)
        self.apply(action='update', observation_registration='none')
        settings = (self.home / '.claude/settings.json').read_text()
        self.assertIn('planning-hook.py', settings)
        self.assertNotIn('observation-hook.py', settings)
        self.assertIsNotNone(Store(self.home).registration(grant['registration_id']))

    def test_native_cli_refuses_cursor_and_unsupported_profile_or_source(self):
        command = [sys.executable, str(ROOT / 'scripts/improvement/observations.py'),
                   '--home', str(self.home), 'grant', '--client', 'claude', '--project', str(self.repo)]
        for args, reason in [(['--start-after', '0'], 'native_sequence_is_automatic'),
                             (['--profile', 'other'], 'unsupported_adapter'),
                             (['--source', 'fixture-v1'], 'unsupported_adapter')]:
            with self.subTest(args=args):
                before = storage.observed(self.home)
                result = subprocess.run(command + args, capture_output=True, timeout=10)
                self.assertEqual((result.returncode, result.stderr), (1, b''))
                self.assertEqual(json.loads(result.stdout), {'status': 'rejected', 'reason': reason})
                self.assertEqual(storage.observed(self.home), before)

    def test_doctor_active_grant_pass_by_id_does_not_claim_native_delivery(self):
        grant = self.native_grant()
        self.apply(observation_registration=grant['registration_id'])
        before = storage.observed(self.home)
        with patch('account_doctor.shutil.which', return_value='/synthetic/client'):
            result = diagnose(self.home)
        selected = [c for c in result['checks'] if c['id'] == 'observation.grant']
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['status'], 'pass')
        self.assertFalse(result['native_activation_verified'])
        self.assertEqual(storage.observed(self.home), before)


if __name__ == '__main__':
    unittest.main()
