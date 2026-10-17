"""Exercise the manual CLI through a disposable account; no native hosts involved."""
import json
import fcntl
import importlib.util
import io
import sqlite3
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/improvement/observations.py'


class ObservationCliTests(unittest.TestCase):
    def test_manual_synthetic_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix='observation CLI ') as directory:
            base = Path(directory).resolve()
            home, project = base / 'home', base / 'project'
            home.mkdir()
            project.mkdir()
            def call(*args, payload=None, expected=0):
                result = subprocess.run([sys.executable, str(CLI), '--home', str(home), *args],
                                        input=payload, capture_output=True, timeout=10, cwd=base)
                self.assertEqual(result.returncode, expected, result.stderr)
                return json.loads(result.stdout)
            grant = call('grant', '--project', str(project), '--start-after', '0')
            identity = ['--registration', grant['registration_id'], '--epoch', grant['epoch']]
            event = dict(schema_version=1, client='synthetic', project_root=str(project),
                         source='fixture-v1', profile='default', session_id='session-1',
                         sequence=1, source_event_id='event-1', event_kind='tool_end',
                         output='SYNTHETIC_PRIVATE_SENTINEL')
            payload = json.dumps(event).encode()
            self.assertEqual(call('capture', *identity, payload=payload)['status'], 'recorded')
            self.assertEqual(call('capture', *identity, payload=payload)['status'], 'duplicate')
            event.update(sequence=2, source_event_id='event-2')
            batch = json.dumps(event).encode() + b'\n'
            incomplete = call('import', *identity, '--offset', '0', payload=batch[:-1])
            self.assertEqual(incomplete['status'], 'incomplete')
            self.assertEqual(incomplete['next_offset'], 0)
            self.assertEqual(call('import', *identity, '--offset', '1', payload=batch, expected=1)['reason'], 'cursor_mismatch')
            imported = call('import', *identity, '--offset', '0', payload=batch)
            self.assertEqual(imported['next_offset'], len(batch))
            self.assertEqual(call('rebuild-index')['indexed_events'], 2)
            observed = call('events', '--registration', grant['registration_id'])
            self.assertEqual(len(observed['events']), 2)
            self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(observed))
            self.assertEqual(call('capture', *identity, payload=b'invalid', expected=1)['status'], 'rejected')
            self.assertEqual(call('revoke', '--registration', grant['registration_id'])['status'], 'revoked')
            self.assertEqual(call('capture', *identity, payload=payload)['status'], 'disabled')
            self.assertEqual(call('events', '--registration', grant['registration_id'])['events'], [])
            self.assertFalse((home / '.agents/agent-dotfiles/state').exists())
            self.assertFalse((home / '.codex').exists())

    def test_refusals_preserve_fixed_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home, project = base / 'home', base / 'project'
            home.mkdir()
            project.mkdir()

            def call(*args, expected=0):
                result = subprocess.run([sys.executable, str(CLI), '--home', str(home), *args],
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, expected)
                self.assertEqual(result.stderr, b'')
                return json.loads(result.stdout)

            grant_args = ['grant', '--project', str(project), '--start-after', '10']
            grant = call(*grant_args)
            self.assertEqual(call(*grant_args, expected=1),
                             {'status': 'rejected', 'reason': 'already_granted'})
            call('revoke', '--registration', grant['registration_id'])
            self.assertEqual(call('grant', '--project', str(project), '--start-after', '9', expected=1),
                             {'status': 'rejected', 'reason': 'source_high_water'})
            self.assertEqual(call('revoke', '--registration', '0' * 64, expected=1),
                             {'status': 'rejected', 'reason': 'not_found'})
            self.assertEqual(call('events', '--registration', 'invalid', expected=1),
                             {'status': 'rejected', 'reason': 'registration_id'})
            self.assertEqual(call('prune')['purged_registrations'], 1)

    def test_maintenance_lock_contention_is_busy(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            result = subprocess.run([sys.executable, str(CLI), '--home', str(home), 'grant',
                                     '--project', str(home), '--start-after', '0'],
                                    capture_output=True, check=True)
            grant = json.loads(result.stdout)
            with (home / '.agents/agent-dotfiles/observations/store.lock').open('rb') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                result = subprocess.run([sys.executable, str(CLI), '--home', str(home),
                                         'revoke', '--registration', grant['registration_id']],
                                        capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, b'')
            self.assertEqual(json.loads(result.stdout), {'status': 'busy', 'reason': 'store_busy'})

    def test_nested_stored_json_does_not_leak_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            result = subprocess.run([sys.executable, str(CLI), '--home', str(home), 'grant',
                                     '--project', str(home), '--start-after', '0'],
                                    capture_output=True, check=True)
            grant = json.loads(result.stdout)
            path = home / '.agents/agent-dotfiles/observations/grants' / (grant['registration_id'] + '.json')
            path.write_text('[' * 2000 + '0' + ']' * 2000)
            result = subprocess.run([sys.executable, str(CLI), '--home', str(home),
                                     'events', '--registration', grant['registration_id']],
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, b'')
            self.assertEqual(json.loads(result.stdout), {'status': 'error', 'reason': 'operation_failed'})

    def test_database_failure_uses_fixed_diagnostics(self):
        spec = importlib.util.spec_from_file_location('observation_cli', CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(cli.Store, 'rebuild_index', side_effect=sqlite3.DatabaseError('PRIVATE_DETAIL')), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(['--home', directory, 'rebuild-index']), 1)
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(json.loads(stdout.getvalue()), {'status': 'error', 'reason': 'operation_failed'})

    def test_unserializable_stored_result_uses_fixed_diagnostics(self):
        spec = importlib.util.spec_from_file_location('observation_cli', CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(cli.Store, 'events', return_value=[{'occurred_at': float('nan')}]), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(['--home', directory, 'events', '--registration', '0' * 64]), 1)
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(json.loads(stdout.getvalue()), {'status': 'error', 'reason': 'operation_failed'})

    def test_help_does_not_require_an_account(self):
        result = subprocess.run([sys.executable, str(CLI), '--help'], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'rebuild-index', result.stdout)


if __name__ == '__main__':
    unittest.main()
