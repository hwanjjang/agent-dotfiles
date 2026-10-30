"""A review checkout gets an exact host profile and bundle, and the integrity check catches drift."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock

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
        self.root = Path(self.tmp.name)
        self.checkout = self.root / 'checkout'
        self.checkout.mkdir()
        git = ['git', '-C', str(self.checkout), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
        subprocess.run([*git, 'init', '-q'], check=True)
        (self.checkout / 'tracked.txt').write_text('base\n')
        subprocess.run([*git, 'add', 'tracked.txt'], check=True)
        subprocess.run([*git, 'commit', '-q', '-m', 'base'], check=True)
        self.head = subprocess.check_output(['git', '-C', str(self.checkout), 'rev-parse', 'HEAD'], text=True).strip()
        self.evidence = self.root / 'evidence.log'
        self.evidence.write_text('844 tests OK\n')

    def test_bundle_refuses_names_that_collide_without_case(self):
        for index, names in enumerate((['MANIFEST.json'], ['manifest.json'], ['a.txt', 'A.txt'], ['a.txt', 'a.txt'])):
            with self.subTest(names=names):
                code, result = run('bundle', '--checkout', str(self.checkout), '--name', f'b{index}',
                                   *[f'--file={name}={self.evidence}' for name in names])
                self.assertEqual(code, 1)
                self.assertIn('case-insensitive', result['error'])
                self.assertFalse((self.checkout / 'reports' / f'b{index}').exists())

    def test_bundle_verifies_and_reports_tampering(self):
        code, result = run('bundle', '--checkout', str(self.checkout), '--name', 'review-bundle',
                           f'--file=evidence/run.log={self.evidence}')
        self.assertEqual((code, result['files']), (0, 1))
        folder = self.checkout / 'reports/review-bundle'
        self.assertEqual(run('verify-bundle', str(folder))[0], 0)
        (folder / 'evidence/run.log').write_text('edited\n')
        (folder / 'extra.txt').write_text('x\n')
        code, result = run('verify-bundle', str(folder))
        self.assertEqual(code, 1)
        self.assertEqual(result['problems'], ['unrecorded extra.txt', 'changed evidence/run.log'])

    def test_codex_profile_allows_local_binding_without_outbound_domains(self):
        code, result = run('profile', '--checkout', str(self.checkout), '--host', 'codex')
        self.assertEqual(code, 0)
        config = tomllib.loads((self.checkout / '.codex/config.toml').read_text())
        self.assertIs(config['sandbox_workspace_write']['network_access'], True)
        self.assertEqual(config['features']['network_proxy'], {'enabled': True, 'allow_local_binding': True})
        self.assertNotIn('domains', config['features']['network_proxy'])

    def test_grok_profile_denies_writes_and_publication(self):
        self.assertEqual(run('profile', '--checkout', str(self.checkout), '--host', 'grok')[0], 0)
        deny = tomllib.loads((self.checkout / '.grok/config.toml').read_text())['permission']['deny']
        for rule in ('Edit', 'Write', 'Bash(git push*)', 'Bash(git commit*)', 'Bash(gh *)', 'Bash(rm *)'):
            self.assertIn(rule, deny)

    def test_existing_profile_with_other_content_is_not_replaced(self):
        (self.checkout / '.codex').mkdir()
        (self.checkout / '.codex/config.toml').write_text('model = "x"\n')
        code, result = run('profile', '--checkout', str(self.checkout), '--host', 'codex')
        self.assertEqual(code, 1)
        self.assertEqual((self.checkout / '.codex/config.toml').read_text(), 'model = "x"\n')

    def test_untrusted_grok_project_fails_the_profile_check(self):
        inspect = subprocess.CompletedProcess([], 0, json.dumps({'projectTrusted': False, 'permissions': {'loaded': 0}}), '')
        with mock.patch.object(rw.subprocess, 'run', return_value=inspect):
            code, result = run('profile', '--checkout', str(self.checkout), '--host', 'grok', '--check-grok')
        self.assertEqual(code, 1)
        self.assertIn('not trusted', result['error'])

    def test_integrity_accepts_only_what_the_helper_placed(self):
        run('profile', '--checkout', str(self.checkout), '--host', 'codex')
        run('bundle', '--checkout', str(self.checkout), '--name', 'review-bundle', f'--file=run.log={self.evidence}')
        code, result = run('integrity', '--checkout', str(self.checkout), '--head', self.head)
        self.assertEqual((code, result['problems']), (0, []))
        cases = {
            'tracked edit': lambda: (self.checkout / 'tracked.txt').write_text('changed\n'),
            'new file': lambda: (self.checkout / 'notes.md').write_text('x\n'),
            'profile edit': lambda: (self.checkout / '.codex/config.toml').write_text('# edited\n'),
            'bundle edit': lambda: (self.checkout / 'reports/review-bundle/run.log').write_text('edited\n'),
        }
        for name, change in cases.items():
            with self.subTest(name):
                snapshot = {p: p.read_bytes() for p in self.checkout.rglob('*') if p.is_file() and '.git' not in p.parts}
                change()
                self.assertEqual(run('integrity', '--checkout', str(self.checkout), '--head', self.head)[0], 1)
                for path in list(self.checkout.rglob('*')):
                    if path.is_file() and '.git' not in path.parts and path not in snapshot:
                        path.unlink()
                for path, data in snapshot.items():
                    path.write_bytes(data)
        code, result = run('integrity', '--checkout', str(self.checkout), '--head', '0' * 40)
        self.assertEqual(code, 1)
        self.assertIn('expected ' + '0' * 40, result['problems'][0])

    def test_remove_keeps_a_changed_profile_for_inspection(self):
        run('profile', '--checkout', str(self.checkout), '--host', 'grok')
        run('profile', '--checkout', str(self.checkout), '--host', 'codex')
        (self.checkout / '.grok/config.toml').write_text('# edited by reviewer\n')
        code, result = run('remove', '--checkout', str(self.checkout))
        self.assertEqual(code, 1)
        self.assertEqual(result['removed'], ['.codex/config.toml'])
        self.assertFalse((self.checkout / '.codex').exists())
        self.assertTrue((self.checkout / '.grok/config.toml').exists())

    def test_runtimes_compares_versions_resolved_on_path(self):
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name, text in {'node': 'v20.20.2', 'java': 'openjdk version "17.0.20" 2026-07-21'}.items():
            tool = bin_dir / name
            tool.write_text(f'#!/bin/sh\necho \'{text}\' >&2\necho \'{text}\'\n')
            tool.chmod(0o755)
        with mock.patch.dict(os.environ, {'PATH': str(bin_dir)}):
            code, result = run('runtimes', '--tool', 'node', '--tool', 'java', '--min', 'node=22.18', '--min', 'java=11')
        self.assertEqual(code, 1)
        self.assertEqual(result['tools']['node']['version'], '20.20.2')
        self.assertIs(result['tools']['node']['meets_minimum'], False)
        self.assertIs(result['tools']['java']['meets_minimum'], True)


if __name__ == '__main__':
    unittest.main()
