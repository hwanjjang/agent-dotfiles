"""A review checkout gets an exact host profile and bundle, and the integrity check catches drift."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11: the profile parse checks skip; the helper needs 3.11+.
    tomllib = None

import review_workspace as rw


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = rw.main(list(argv))
    return code, json.loads(out.getvalue())


class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.checkout = self.root / 'checkout'
        self.checkout.mkdir()
        git = ['git', '-C', str(self.checkout), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
        subprocess.run([*git, 'init', '-q'], check=True)
        (self.checkout / 'tracked.txt').write_text('base\n')
        subprocess.run([*git, 'add', 'tracked.txt'], check=True)
        subprocess.run([*git, 'commit', '-q', '-m', 'base'], check=True)
        self.head = subprocess.check_output(['git', '-C', str(self.checkout), 'rev-parse', 'HEAD'], text=True).strip()
        self.record = self.root / 'coordinator/record.json'
        self.outside = self.root / 'outside'
        self.outside.mkdir()
        self.evidence = self.root / 'evidence.log'
        self.evidence.write_text('844 tests OK\n')

    def helper(self, command, *argv):
        return run(command, '--checkout', str(self.checkout), '--record', str(self.record), *argv)

    def bundle(self, name='review-bundle', *dests):
        return self.helper('bundle', '--name', name, *[f'--file={dest}={self.evidence}' for dest in dests or ['run.log']])

    def test_bundle_refuses_names_that_collide(self):
        cases = (['MANIFEST.json'], ['manifest.json'], ['a.txt', 'A.txt'], ['a.txt', 'a.txt'], ['a', 'a/b'], ['D/x', 'd/x'],
                 ['caf\u00e9.txt', 'cafe\u0301.txt'])
        for index, names in enumerate(cases):
            with self.subTest(names=names):
                code, result = self.bundle(f'b{index}', *names)
                self.assertEqual(code, 1)
                self.assertIn('collide', result['error'])
                self.assertFalse((self.checkout / 'reports' / f'b{index}').exists())
        self.assertFalse(self.record.exists())

    def test_bundle_refuses_names_that_are_not_plain(self):
        for name in ('../escaped', 'a/b', '.hidden', '/abs', ''):
            with self.subTest(name=name):
                self.assertEqual(self.bundle(name)[0], 2)
        for dest in ('../x', '/abs', 'a/../b', 'a//b', './a', '.', ''):
            with self.subTest(dest=dest):
                self.assertEqual(self.bundle('review-bundle', dest)[0], 2)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['checkout', 'evidence.log', 'outside'])
        self.assertFalse((self.checkout / 'reports').exists())

    def test_writes_refuse_symbolic_links_into_the_checkout(self):
        (self.checkout / 'reports').symlink_to(self.outside)
        self.assertEqual(self.bundle()[0], 1)
        (self.checkout / '.codex').symlink_to(self.outside)
        self.assertEqual(self.helper('profile', '--host', 'codex')[0], 1)
        (self.checkout / '.grok').mkdir()
        (self.checkout / '.grok/config.toml').symlink_to(self.outside / 'missing.toml')
        self.assertEqual(self.helper('profile', '--host', 'grok')[0], 1)
        self.assertEqual(list(self.outside.iterdir()), [])

    def test_checkout_must_be_the_top_of_a_git_checkout(self):
        (self.checkout / 'sub').mkdir()
        for checkout in (self.checkout / 'sub', self.outside):
            with self.subTest(checkout=str(checkout)):
                code, result = run('profile', '--checkout', str(checkout), '--record', str(self.record), '--host', 'codex')
                self.assertEqual(code, 2)
                self.assertIn('top directory', result['error'])
        self.assertEqual(list(self.outside.iterdir()), [])

    def test_record_stays_outside_the_checkout(self):
        link = self.root / 'link'
        link.symlink_to(self.checkout)
        for record in (self.checkout / 'record.json', link / 'record.json'):
            with self.subTest(record=str(record)):
                code, result = run('profile', '--checkout', str(self.checkout), '--record', str(record), '--host', 'codex')
                self.assertEqual(code, 2)
                self.assertIn('outside', result['error'])
        self.assertFalse((self.checkout / '.codex').exists())
        self.assertEqual(self.helper('integrity', '--head', self.head)[0], 2)

    def test_bundle_verifies_and_reports_tampering(self):
        code, result = self.bundle('review-bundle', 'evidence/run.log', 'sub/MANIFEST.json')
        self.assertEqual((code, result['files']), (0, 2))
        folder = self.checkout / 'reports/review-bundle'
        self.assertEqual(run('verify-bundle', str(folder)), (0, {'ok': True, 'bundle': str(folder), 'problems': []}))
        (folder / 'evidence/run.log').write_text('edited\n')
        (folder / 'extra.txt').write_text('x\n')
        (folder / 'sub/MANIFEST.json').unlink()
        code, result = run('verify-bundle', str(folder))
        self.assertEqual(code, 1)
        self.assertEqual(result['problems'], ['missing sub/MANIFEST.json', 'unrecorded extra.txt', 'changed evidence/run.log'])

    @unittest.skipIf(tomllib is None, 'tomllib needs Python 3.11+')
    def test_codex_profile_allows_local_binding_without_outbound_domains(self):
        self.assertEqual(self.helper('profile', '--host', 'codex')[0], 0)
        config = tomllib.loads((self.checkout / '.codex/config.toml').read_text())
        self.assertIs(config['sandbox_workspace_write']['network_access'], True)
        self.assertEqual(config['features']['network_proxy'], {'enabled': True, 'allow_local_binding': True})

    @unittest.skipIf(tomllib is None, 'tomllib needs Python 3.11+')
    def test_grok_profile_denies_writes_and_publication(self):
        self.assertEqual(self.helper('profile', '--host', 'grok')[0], 0)
        deny = tomllib.loads((self.checkout / '.grok/config.toml').read_text())['permission']['deny']
        for rule in ('Edit', 'Write', 'Bash(git push*)', 'Bash(git commit*)', 'Bash(gh *)', 'Bash(rm *)'):
            self.assertIn(rule, deny)

    def test_existing_profile_with_other_content_is_not_replaced(self):
        (self.checkout / '.codex').mkdir()
        (self.checkout / '.codex/config.toml').write_text('model = "x"\n')
        self.assertEqual(self.helper('profile', '--host', 'codex')[0], 1)
        self.assertEqual((self.checkout / '.codex/config.toml').read_text(), 'model = "x"\n')

    def test_untrusted_grok_project_fails_the_profile_check(self):
        real_run = subprocess.run

        def fake_grok(command, *args, **kwargs):
            if command[0] != 'grok':
                return real_run(command, *args, **kwargs)
            return subprocess.CompletedProcess(command, 0, json.dumps({'projectTrusted': False, 'permissions': {'loaded': 0}}), '')

        with mock.patch.object(rw.subprocess, 'run', side_effect=fake_grok):
            code, result = self.helper('profile', '--host', 'grok', '--check-grok')
        self.assertEqual(code, 1)
        self.assertIn('not trusted', result['error'])

    def test_integrity_trusts_only_the_external_record(self):
        self.helper('profile', '--host', 'codex')
        digest = self.bundle('review-bundle', 'run.log', 'my file.log')[1]['record_sha256']
        self.assertEqual(self.helper('integrity', '--head', self.head, '--expect-record-sha256', digest), (0, {
            'ok': True, 'checkout': str(self.checkout), 'head': self.head, 'problems': []}))
        folder = self.checkout / 'reports/review-bundle'

        def rewrite_bundle_and_manifest():
            (folder / 'run.log').write_text('edited\n')
            (folder / rw.MANIFEST).write_text(json.dumps({'files': {'run.log': rw.sha(folder / 'run.log')}}))

        def decoy_record():
            (self.checkout / 'notes.md').write_text('x\n')
            (self.checkout / 'reports/review-workspace.json').write_text(json.dumps({'placed': {'notes.md': 'x'}}))

        cases = {
            'tracked edit': lambda: (self.checkout / 'tracked.txt').write_text('changed\n'),
            'new file': lambda: (self.checkout / 'notes.md').write_text('x\n'),
            'profile edit': lambda: (self.checkout / '.codex/config.toml').write_text('# edited\n'),
            'bundle edit': lambda: (folder / 'run.log').write_text('edited\n'),
            'bundle and manifest rewritten': rewrite_bundle_and_manifest,
            'file added to the bundle': lambda: (folder / 'extra.txt').write_text('x\n'),
            'decoy record in the checkout': decoy_record,
        }
        for name, change in cases.items():
            with self.subTest(name):
                snapshot = {p: p.read_bytes() for p in self.checkout.rglob('*') if p.is_file() and '.git' not in p.parts}
                change()
                self.assertEqual(self.helper('integrity', '--head', self.head)[0], 1)
                for path in list(self.checkout.rglob('*')):
                    if path.is_file() and '.git' not in path.parts and path not in snapshot:
                        path.unlink()
                for path, data in snapshot.items():
                    path.write_bytes(data)
        code, result = self.helper('integrity', '--head', '0' * 40)
        self.assertEqual(code, 1)
        self.assertIn('expected ' + '0' * 40, result['problems'][0])
        code, result = self.helper('integrity', '--head', self.head, '--expect-record-sha256', '0' * 64)
        self.assertEqual(code, 1)
        self.assertIn('record changed', result['error'])

    def test_integrity_compares_ignored_files_with_the_preparation_snapshot(self):
        (self.checkout / '.gitignore').write_text('/reports/\n*.log\nsecret/\n__pycache__/\n')
        (self.checkout / 'old.log').write_text('kept\n')
        git = ['git', '-C', str(self.checkout), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
        subprocess.run([*git, 'add', '.gitignore'], check=True)
        subprocess.run([*git, 'commit', '-q', '-m', 'ignore'], check=True)
        head = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
        self.helper('profile', '--host', 'grok')
        digest = self.bundle()[1]['record_sha256']
        self.assertEqual(json.loads(self.record.read_text())['ignored'], ['old.log'])
        self.assertEqual(self.helper('integrity', '--head', head, '--expect-record-sha256', digest)[0], 0)
        (self.checkout / 'notes.log').write_text('x\n')
        (self.checkout / 'secret').mkdir()
        (self.checkout / 'secret/payload.txt').write_text('x\n')
        (self.checkout / 'reports/extra.txt').write_text('x\n')
        (self.checkout / 'tests/__pycache__').mkdir(parents=True)
        (self.checkout / 'tests/__pycache__/t.pyc').write_bytes(b'x')
        (self.checkout / 'old.log').unlink()
        code, result = self.helper('integrity', '--head', head)
        self.assertEqual(code, 1)
        self.assertEqual(result['problems'], [
            'new ignored file: notes.log', 'new ignored file: reports/extra.txt', 'new ignored file: secret/payload.txt',
            'new ignored file: tests/__pycache__/t.pyc', 'ignored file removed: old.log'])
        code, result = self.helper('integrity', '--head', head, '--allow-ignored', '*.log', '--allow-ignored', '*__pycache__/*')
        self.assertEqual(result['problems'], ['new ignored file: reports/extra.txt', 'new ignored file: secret/payload.txt'])

    def test_remove_deletes_only_unchanged_helper_profiles(self):
        self.helper('profile', '--host', 'grok')
        self.helper('profile', '--host', 'codex')
        (self.checkout / '.grok/config.toml').write_text('# edited by reviewer\n')
        data = json.loads(self.record.read_text())
        (self.outside / 'keep.txt').write_text('keep\n')
        data['placed'].update({'tracked.txt': rw.sha(self.checkout / 'tracked.txt'),
                               '../outside/keep.txt': rw.sha(self.outside / 'keep.txt')})
        self.record.write_text(json.dumps(data))
        self.assertEqual(self.helper('remove', '--expect-record-sha256', '0' * 64)[0], 1)
        self.assertTrue((self.checkout / '.codex/config.toml').exists())
        code, result = self.helper('remove')
        self.assertEqual(code, 1)
        self.assertEqual(result['removed'], ['.codex/config.toml'])
        self.assertEqual(len(result['problems']), 3)
        self.assertFalse((self.checkout / '.codex').exists())
        for kept in (self.checkout / '.grok/config.toml', self.checkout / 'tracked.txt', self.outside / 'keep.txt'):
            self.assertTrue(kept.exists(), kept)

    def test_runtimes_checks_every_named_tool(self):
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name, text in {'node': 'v20.20.2', 'java': 'openjdk version "17" 2026-07-21'}.items():
            tool = bin_dir / name
            tool.write_text(f'#!/bin/sh\necho \'{text}\' >&2\necho \'{text}\'\n')
            tool.chmod(0o755)
        with mock.patch.dict(os.environ, {'PATH': str(bin_dir)}):
            code, result = run('runtimes', '--tool', 'node', '--min', 'node=22.18', '--min', 'java=11')
            self.assertEqual(code, 1)
            self.assertEqual(result['tools']['node']['version'], '20.20.2')
            self.assertIs(result['tools']['node']['meets_minimum'], False)
            self.assertIs(result['tools']['java']['meets_minimum'], True)
            self.assertEqual(run('runtimes', '--min', 'java=17.0')[0], 0)
            self.assertEqual(run('runtimes', '--min', 'java=17.0.1')[0], 1)
            code, result = run('runtimes', '--min', 'deno=2')
            self.assertEqual((code, result['tools']['deno']), (1, {
                'path': None, 'version': None, 'minimum': '2', 'meets_minimum': False}))
            self.assertEqual(run('runtimes', '--tool', 'bun')[0], 1)
            self.assertEqual(run('runtimes')[0], 0)
            for bad in (['--min', 'node=abc'], ['--min', 'ruby=3'], ['--tool', 'ruby']):
                with self.subTest(bad=bad):
                    self.assertEqual(run('runtimes', *bad)[0], 2)


if __name__ == '__main__':
    unittest.main()
