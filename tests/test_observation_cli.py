"""Exercise the manual CLI through a disposable account; no native hosts involved."""
import json
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

    def test_help_does_not_require_an_account(self):
        result = subprocess.run([sys.executable, str(CLI), '--help'], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'rebuild-index', result.stdout)


if __name__ == '__main__':
    unittest.main()
