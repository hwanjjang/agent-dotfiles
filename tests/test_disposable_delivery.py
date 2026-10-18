"""Committed-fixture delivery mechanics through the public CLI; no client calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_setup_account as fixtures
from account.observation.store import Store

ROOT = Path(__file__).resolve().parents[1]
setup, storage = fixtures.setup, fixtures.storage


class DisposableDeliveryTests(unittest.TestCase):
    # Reuse construction helpers without inheriting and repeating the entire suite.
    setUp = fixtures.AccountSetupTests.setUp
    git = fixtures.AccountSetupTests.git
    commit = fixtures.AccountSetupTests.commit
    config = fixtures.AccountSetupTests.config
    COMPONENT = 'skills/tdd/delivery-fixture.py'

    def revisions(self):
        path = self.repo / self.COMPONENT
        commits = []
        for marker, code in [('baseline-ok', 0), ('candidate-ok', 0), ('regression-seeded', 7)]:
            path.write_text(f'print({marker!r})\nraise SystemExit({code})\n')
            commits.append(self.commit('Synthetic delivery mechanics: ' + marker))
        return commits

    def cli(self, action, *options, code=0):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/setup_account.py'), action,
                                 '--repo', str(self.repo), '--home', str(self.home), *options],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        if code:
            self.assertEqual(result.stdout, '')
            self.assertNotIn('Traceback', result.stderr)
            return result.stderr
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout) if result.stdout else None

    def preserved(self):
        observations = self.home / '.agents/agent-dotfiles/observations'
        settings = json.loads((self.home / '.claude/settings.json').read_text())
        return (storage.observed(observations), Store(self.home).events(self.grant['registration_id']),
                Store(self.home).registration(self.grant['registration_id']),
                storage.observed(self.home / '.agents/skills/paseo'),
                settings['permissions'], settings['hooks']['Stop'])

    def seed(self):
        self.config('.claude/settings.json', {'permissions': {'deny': ['Bash(personal-command)']},
                    'hooks': {'Stop': [{'hooks': [{'command': 'personal-check'}]}]}})
        path = self.home / '.agents/skills/paseo/SKILL.md'
        path.parent.mkdir(parents=True)
        path.write_text('Synthetic host-owned content\n')
        store = Store(self.home)
        self.grant = store.grant(self.repo, start_after=0)
        payload = json.dumps(dict(schema_version=1, project_root=str(self.repo), client='synthetic',
                                  profile='default', source='fixture-v1', session_id='session-1',
                                  sequence=1, source_event_id='event-1', event_kind='response_end')).encode()
        self.assertEqual(store.capture(self.grant['registration_id'], self.grant['epoch'], payload)['status'],
                         'recorded')
        self.original = self.preserved()

    def preview_apply(self, action, revision):
        before = storage.observed(self.home)
        source = storage.observed(self.repo)
        plan = self.cli(action, '--revision', revision)
        self.assertEqual(plan['source_revision'], revision)
        self.assertEqual(plan['conflicts'], [])
        self.assertEqual(storage.observed(self.home), before)
        self.assertEqual(storage.observed(self.repo), source)
        result = self.cli(action, '--revision', revision, '--apply')
        self.assertEqual(result['source_revision'], revision)
        self.assertFalse(result['native_activation_verified'])
        self.assertEqual(self.preserved(), self.original)
        return result

    def installed(self, revision, marker, exit_code=0):
        receipt = json.loads((self.home / storage.RECEIPT).read_text())
        self.assertEqual(receipt['source_revision'], revision)
        paths = self.git('ls-tree', '-r', '--name-only', revision).splitlines()
        expected = {setup.BUNDLE + '/' + name: name for name in paths
                    if name.startswith(('account/', 'policies/', 'skills/', 'mcp/', 'tools/', 'docs/'))
                    or name in ('README.md', 'LICENSE')}
        actual = {name for name in receipt['assets'] if name.startswith(setup.BUNDLE + '/')}
        self.assertEqual(actual, set(expected))
        for target, source in expected.items():
            committed = subprocess.check_output(['git', '-C', str(self.repo), 'show', revision + ':' + source])
            path = self.home / target
            self.assertEqual(path.read_bytes(), committed, source)
            self.assertEqual(receipt['assets'][target]['sha256'], hashlib.sha256(committed).hexdigest())
            mode = self.git('ls-tree', revision, source).split()[0]
            self.assertEqual(path.stat().st_mode & 0o777, 0o755 if mode == '100755' else 0o644)
        for client in ('.agents', '.claude'):
            for skill in ('tdd', 'planning-with-files'):
                link = self.home / client / 'skills' / skill
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), self.home / setup.BUNDLE / 'skills' / skill)
        status = self.cli('status')
        self.assertEqual(status['drift'], [])
        self.assertEqual(status['source_revision'], revision)
        before = storage.observed(self.home)
        # Offline readiness may legitimately be blocked by absent host clients.
        report = subprocess.run([sys.executable, str(ROOT / 'scripts/setup_account.py'), 'doctor',
                                 '--home', str(self.home), '--json'], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(report.stderr, '')
        doctor = json.loads(report.stdout)
        unavailable = [row for row in doctor['checks'] if row['status'] in ('blocked', 'fail')]
        self.assertTrue(all(row['id'] in ('codex.executable', 'claude.executable') and
                            row['status'] == 'blocked' for row in unavailable), unavailable)
        self.assertEqual(report.returncode, 1 if unavailable else 0)
        self.assertEqual(doctor['status'], 'blocked' if unavailable else 'pass')
        self.assertEqual(doctor['comparison'], {'status': 'not_run', 'promotion_eligible': False})
        self.assertFalse(doctor['model_execution_verified'])
        self.assertFalse(doctor['native_activation_verified'])
        self.assertEqual(storage.observed(self.home), before)
        result = subprocess.run([sys.executable, str(self.home / setup.BUNDLE / self.COMPONENT)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (exit_code, marker + '\n', ''))
        self.assertEqual(self.preserved(), self.original)

    def test_committed_update_behavior_regression_and_rollback_preserve_observations(self):
        baseline, candidate, regression = self.revisions()
        self.seed()
        self.preview_apply('install', baseline)
        self.installed(baseline, 'baseline-ok')
        self.preview_apply('update', candidate)
        self.installed(candidate, 'candidate-ok')
        unchanged = self.preview_apply('update', candidate)
        self.assertIsNone(unchanged['transaction'])
        self.assertEqual(unchanged['changed_paths'], 0)
        before_receipt = (self.home / storage.RECEIPT).read_bytes()
        # Dirty edits must not replace the committed regression fixture.
        (self.repo / self.COMPONENT).write_text('print("uncommitted-success")\n')
        bad = self.preview_apply('update', regression)
        self.installed(regression, 'regression-seeded', 7)
        before = storage.observed(self.home)
        rollback = self.cli('rollback', '--transaction', bad['transaction'])
        self.assertEqual(rollback['action'], 'rollback')
        self.assertEqual(storage.observed(self.home), before)
        self.cli('rollback', '--transaction', bad['transaction'], '--apply')
        self.assertEqual((self.home / storage.RECEIPT).read_bytes(), before_receipt)
        self.installed(candidate, 'candidate-ok')
        self.cli('uninstall', '--apply')
        self.assertFalse(self.cli('status')['installed'])
        self.assertFalse((self.home / '.agents/skills/tdd').exists())
        self.assertEqual(self.preserved(), self.original)

    def test_intervening_edit_refuses_rollback_preview_and_apply_without_mutation(self):
        baseline, _, regression = self.revisions()
        self.seed()
        self.preview_apply('install', baseline)
        bad = self.preview_apply('update', regression)
        component = self.home / setup.BUNDLE / self.COMPONENT
        component.write_text('Synthetic intervening personal edit\n')
        before = storage.observed(self.home)
        for flags in ((), ('--apply',)):
            error = self.cli('rollback', '--transaction', bad['transaction'], *flags, code=2)
            self.assertIn('Rollback would overwrite later changes:', error)
            self.assertEqual(storage.observed(self.home), before)
            self.assertEqual(self.preserved(), self.original)


if __name__ == '__main__':
    unittest.main()
