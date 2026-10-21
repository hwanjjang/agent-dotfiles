"""Committed-fixture delivery mechanics through the public CLI; no client calls."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_setup_account as fixtures
from account.observation.store import Store

ROOT = Path(__file__).resolve().parents[1]
setup, storage = fixtures.setup, fixtures.storage


def tree_entries(path):
    """Per-path fingerprints whose equality matches storage.observed(path), but which can name a difference."""
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        # storage.observed does not descend into a symlinked or non-directory root either.
        return {'.': storage.observed(path)}
    entries = {'.': {'directory': True, 'mode': path.stat().st_mode & 0o777}}
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            item = Path(root) / name
            entries[item.relative_to(path).as_posix()] = (
                {'directory': True, 'mode': item.stat().st_mode & 0o777}
                if item.is_dir() and not item.is_symlink() else storage.observed(item))
    return entries


def describe(paths, limit=20):
    shown = sorted(paths)
    extra = f' +{len(shown) - limit} more' if len(shown) > limit else ''
    return repr(shown[:limit]) + extra


def summarize(before, after):
    """A short description of how one fingerprint changed: kind, content digest or mode."""
    def kind(value):
        return 'absent' if value is None else '/'.join(sorted(value))

    if before is None or after is None or before.keys() != after.keys():
        return f'kind {kind(before)}->{kind(after)}'
    parts = []
    for key in sorted(before):
        if before[key] == after[key]:
            continue
        old, new = before[key], after[key]
        if key == 'sha256':
            parts.append(f'sha256 {old[:12]}->{new[:12]}')
        elif key == 'mode':
            parts.append(f'mode {oct(old)}->{oct(new)}')
        else:
            parts.append(f'{key} {str(old)[:40]}->{str(new)[:40]}')
    return ', '.join(parts)


def assert_tree_unchanged(testcase, path, before):
    """Fail testcase with the added, removed and changed paths when path no longer matches before."""
    after = tree_entries(path)
    if after != before:
        added, removed = after.keys() - before.keys(), before.keys() - after.keys()
        changed = {key for key in before.keys() & after.keys() if before[key] != after[key]}
        testcase.fail(f'Tree changed under {Path(path).name}: added={describe(added)} '
                      f'removed={describe(removed)} changed={describe_changes(before, after, changed)}')


def describe_changes(before, after, keys, limit=20):
    shown = sorted(keys)
    extra = f' +{len(shown) - limit} more' if len(shown) > limit else ''
    return '[' + ', '.join(f"'{k}' ({summarize(before[k], after[k])})" for k in shown[:limit]) + ']' + extra


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

    def assert_tree_unchanged(self, path, before):
        assert_tree_unchanged(self, path, before)

    def preview_apply(self, action, revision):
        before = tree_entries(self.home)
        source = tree_entries(self.repo)
        plan = self.cli(action, '--revision', revision)
        self.assertEqual(plan['source_revision'], revision)
        self.assertEqual(plan['conflicts'], [])
        self.assert_tree_unchanged(self.home, before)
        self.assert_tree_unchanged(self.repo, source)
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
        before = tree_entries(self.home)
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
        self.assert_tree_unchanged(self.home, before)
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
        before = tree_entries(self.home)
        rollback = self.cli('rollback', '--transaction', bad['transaction'])
        self.assertEqual(rollback['action'], 'rollback')
        self.assert_tree_unchanged(self.home, before)
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
        before = tree_entries(self.home)
        for flags in ((), ('--apply',)):
            error = self.cli('rollback', '--transaction', bad['transaction'], *flags, code=2)
            self.assertIn('Rollback would overwrite later changes:', error)
            self.assert_tree_unchanged(self.home, before)
            self.assertEqual(self.preserved(), self.original)



class TreeDiagnosticTests(unittest.TestCase):
    def test_tree_mismatch_message_names_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'kept.txt').write_text('same\n')
            (root / 'changed.txt').write_text('before\n')
            (root / 'removed.txt').write_text('gone\n')
            before = tree_entries(root)
            (root / 'changed.txt').write_text('after\n')
            (root / 'removed.txt').unlink()
            (root / 'nested').mkdir()
            (root / 'nested' / 'added.txt').write_text('new\n')
            with self.assertRaises(AssertionError) as caught:
                assert_tree_unchanged(self, root, before)
            message = str(caught.exception)
            for expected in ("added=['nested', 'nested/added.txt']", "removed=['removed.txt']",
                             "changed=['changed.txt' (sha256 "):
                self.assertIn(expected, message)
            self.assertNotIn('kept.txt', message)

    def test_root_replaced_by_symlink_is_a_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / 'tree'; root.mkdir(); (root / 'file.txt').write_text('same\n')
            before = tree_entries(root)
            shutil.move(str(root), str(base / 'moved'))
            os.symlink(base / 'moved', root)
            self.assertNotEqual(storage.observed(root), storage.observed(base / 'moved'))
            with self.assertRaises(AssertionError) as caught:
                assert_tree_unchanged(self, root, before)
            self.assertIn("changed=['.'", str(caught.exception))

    def test_changed_entries_summarize_the_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'content.txt').write_text('before\n')
            (root / 'mode.txt').write_text('x\n'); (root / 'mode.txt').chmod(0o644)
            before = tree_entries(root)
            (root / 'content.txt').write_text('after\n')
            (root / 'mode.txt').chmod(0o755)
            with self.assertRaises(AssertionError) as caught:
                assert_tree_unchanged(self, root, before)
            message = str(caught.exception)
            self.assertRegex(message, r"'content\.txt' \(sha256 [0-9a-f]{12}->[0-9a-f]{12}\)")
            self.assertIn("'mode.txt' (mode 0o644->0o755)", message)

    def test_root_removed_or_created_is_summarized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'tree'
            root.mkdir(); (root / 'file.txt').write_text('x\n')
            present = tree_entries(root)
            shutil.rmtree(root)
            with self.assertRaises(AssertionError) as caught:
                assert_tree_unchanged(self, root, present)
            self.assertIn("changed=['.' (kind directory/mode->absent)]", str(caught.exception))
            absent = tree_entries(root)
            root.mkdir()
            with self.assertRaises(AssertionError) as caught:
                assert_tree_unchanged(self, root, absent)
            self.assertIn("changed=['.' (kind absent->directory/mode)]", str(caught.exception))


if __name__ == '__main__':
    unittest.main()
