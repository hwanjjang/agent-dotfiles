"""Synthetic controller cleanup; no authentication, native process or Docker."""
import json
import sys
import threading
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial


class CleanupSignalDiagnosticsTests(unittest.TestCase):
    def cleanup(self, code, reconciled=False):
        c = trial.Controller.__new__(trial.Controller)
        c.data = {'limits': {'cleanup_seconds': 45}}
        c.watch_stop = threading.Event(); c.watcher = None
        c.live = Mock()
        c.live.close.return_value = {'process_reaped': True, 'group_signal_error': None if reconciled else 'signal_failed',
                                    'group_signal_error_code': code, 'group_absent_after_reap': reconciled}
        c.launch_called = c.launch_complete = True
        c.seen = {}; c.process_uncertain = c.watch_error = False
        c.begun = set(); c.volume_begun = False; c.home = None; c.capture_failed = False
        c.control = Path('/synthetic/absent'); c.control_identity = (1, 2, 0); c.journal = Mock()
        with patch.object(trial.plan, 'directory', side_effect=FileNotFoundError()):
            result = c.cleanup()
        self.assertEqual(c.journal.save.call_args.args[0], 'cleanup')
        self.assertEqual(c.journal.save.call_args.args[1], result)
        return result

    def test_signal_category_reaches_canonical_cleanup_without_waiving_uncertainty(self):
        result = self.cleanup('permission_denied')
        self.assertEqual(result['group_signal_error_code'], 'permission_denied')
        self.assertTrue(result['group_signal_uncertain'])
        self.assertFalse(result['processes_stopped'])
        self.assertFalse(result['complete'])

    def test_independent_group_absence_fact_reaches_receipt(self):
        result = self.cleanup('permission_denied', reconciled=True)
        self.assertTrue(result['group_absent_after_reap'])
        self.assertFalse(result['group_signal_uncertain'])
        self.assertEqual(result['group_signal_error_code'], 'permission_denied')

    def test_unknown_metadata_does_not_leak_arbitrary_messages(self):
        result = self.cleanup('PRIVATE_ERROR_PATH_OR_VALUE')
        self.assertNotIn('PRIVATE_ERROR_PATH_OR_VALUE', json.dumps(result))
        self.assertEqual(result['group_signal_error_code'], 'other_os_error')
        self.assertFalse(result['complete'])


if __name__ == '__main__':
    unittest.main()
