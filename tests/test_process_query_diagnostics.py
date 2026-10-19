"""Finite process-query diagnostics must not weaken cleanup decisions."""
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial

GOOD = {'exit': 0, 'stop_reason': None, 'stderr': '',
        'stdout': '123 100 123 Mon Oct 19 12:00:00 2026 /synthetic/worker'}
ABSENT = {'exit': 1, 'stop_reason': None, 'stderr': '', 'stdout': ''}


def controller():
    c = trial.Controller.__new__(trial.Controller)
    c.deadline = c.cleanup_deadline = time.monotonic() + 45
    c.env = {}; c.process_uncertain = False
    c.process_lock = threading.Lock()
    c.process_query_diagnostic = None
    return c


class ProcessQueryDiagnosticsTests(unittest.TestCase):
    def test_rejections_have_finite_categories_and_preserve_public_reason(self):
        cases = [({'stop_reason': 'timeout'}, 'timeout'),
                 ({'stop_reason': 'output_limit'}, 'output_limit'),
                 ({'stop_reason': 'PRIVATE_STOP_DETAIL'}, 'control_stopped'),
                 ({'exit': 2}, 'exit_status'),
                 ({'stderr': 'PRIVATE_ERROR_DETAIL'}, 'stderr'),
                 ({'stdout': 'PRIVATE_COMMAND_DETAIL'}, 'field_count'),
                 ({'stdout': GOOD['stdout'].replace('123 100', '124 100')}, 'identity'),
                 ({'stdout': GOOD['stdout'].replace('123 100', 'BAD 100')}, 'identity'),
                 ({'stdout': GOOD['stdout'].replace('/synthetic/worker', '<defunct>')},
                  'executable_not_absolute')]
        for change, expected in cases:
            with self.subTest(expected=expected):
                c = controller()
                with patch.object(trial, 'bounded', return_value=dict(GOOD, **change)):
                    with self.assertRaisesRegex(trial.plan.Refusal, '^process_query$'):
                        c.process(123, cleanup=True)
                self.assertTrue(c.process_uncertain)
                self.assertEqual(c.process_query_diagnostic,
                                 {'phase': 'cleanup', 'pid': 123, 'reason': expected})
                self.assertNotIn('PRIVATE_', json.dumps(c.process_query_diagnostic))

    def test_deadline_and_unexpected_exception_are_classified_without_text(self):
        c = controller(); c.deadline = time.monotonic() - 1
        with patch.object(trial, 'bounded') as query:
            with self.assertRaises(trial.plan.Refusal): c.process(123)
            query.assert_not_called()
        self.assertEqual(c.process_query_diagnostic,
                         {'phase': 'launch', 'pid': 123, 'reason': 'deadline'})
        c = controller()
        with patch.object(trial, 'bounded', side_effect=OSError('PRIVATE_EXCEPTION_DETAIL')):
            with self.assertRaises(trial.plan.Refusal): c.process(123, watch=True)
        self.assertEqual(c.process_query_diagnostic,
                         {'phase': 'watch', 'pid': 123, 'reason': 'operation'})

    def test_later_absence_does_not_clear_first_failure_or_permit_home_cleanup(self):
        c = controller()
        with patch.object(trial, 'bounded', side_effect=[dict(GOOD, stderr='PRIVATE'), ABSENT]):
            with self.assertRaises(trial.plan.Refusal): c.process(123, watch=True)
            self.assertIsNone(c.process(123, cleanup=True))
        first = dict(c.process_query_diagnostic)
        with patch.object(trial, 'bounded', return_value=dict(GOOD, stop_reason='timeout')):
            with self.assertRaises(trial.plan.Refusal): c.process(124, cleanup=True)
        self.assertEqual(c.process_query_diagnostic, first)
        c.data = {'limits': {'cleanup_seconds': 45}}
        c.live = None; c.launch_called = False; c.launch_complete = False
        c.watch_error = False; c.watch_stop = threading.Event(); c.watcher = None
        c.seen = {}; c.begun = set(); c.volume_begun = False
        c.home = Mock(); c.home.cleanup.return_value = {'home_absent': False}
        c.runtime = {'codex': '/synthetic/worker'}; c.journal = Mock()
        c.control = Path('/synthetic/control'); c.control_identity = (1, 2, 3)
        c.capture_failed = False
        with patch.object(trial, 'remove_control') as remove:
            result = c.cleanup()
        self.assertFalse(result['processes_stopped'])
        self.assertFalse(result['complete'])
        self.assertEqual(result['process_query_diagnostic'], first)
        self.assertFalse(c.home.cleanup.call_args.kwargs['processes_stopped'])
        remove.assert_not_called()

    def test_valid_presence_and_absence_add_no_failure(self):
        c = controller()
        with patch.object(trial, 'bounded', side_effect=[GOOD, ABSENT]):
            self.assertEqual(c.process(123)['pid'], 123)
            self.assertIsNone(c.process(123, cleanup=True))
        self.assertFalse(c.process_uncertain)
        self.assertIsNone(c.process_query_diagnostic)

    def test_first_failure_during_cleanup_is_in_the_cleanup_record(self):
        c = controller()
        c.data = {'limits': {'cleanup_seconds': 45}}
        c.live = None; c.launch_called = False; c.launch_complete = False
        c.watch_error = False; c.watch_stop = threading.Event(); c.watcher = None
        c.seen = {123: {'pid': 123}}; c.begun = set(); c.volume_begun = False
        c.home = None; c.journal = Mock(); c.capture_failed = False
        c.control = Path('/synthetic/control'); c.control_identity = (1, 2, 3)
        with patch.object(trial, 'bounded', return_value=dict(GOOD, stop_reason='timeout')), \
                patch.object(trial, 'remove_control') as remove:
            result = c.cleanup()
        self.assertEqual(result['process_query_diagnostic'],
                         {'phase': 'cleanup', 'pid': 123, 'reason': 'timeout'})
        self.assertTrue(result['process_query_uncertain'])
        self.assertFalse(result['processes_stopped'])
        self.assertIn('process_cleanup', result['errors'])
        self.assertEqual(c.journal.save.call_args.args[1], result)
        remove.assert_not_called()

    def test_overlapping_watch_and_cleanup_failures_keep_one_complete_record(self):
        c = controller()
        ready = threading.Barrier(2)
        failures = []

        def query(argv, *args, **kwargs):
            ready.wait(timeout=2)
            return dict(GOOD, stop_reason='timeout')

        def run(pid, **mode):
            try:
                c.process(pid, **mode)
            except trial.plan.Refusal as exc:
                failures.append(str(exc))

        threads = [threading.Thread(target=run, args=(123,), kwargs={'watch': True}),
                   threading.Thread(target=run, args=(124,), kwargs={'cleanup': True})]
        with patch.object(trial, 'bounded', side_effect=query):
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(failures, ['process_query', 'process_query'])
        first = dict(c.process_query_diagnostic)
        self.assertIn(first, [{'phase': 'watch', 'pid': 123, 'reason': 'timeout'},
                              {'phase': 'cleanup', 'pid': 124, 'reason': 'timeout'}])
        with patch.object(trial, 'bounded', return_value=ABSENT):
            self.assertIsNone(c.process(124, cleanup=True))
        self.assertEqual(c.process_query_diagnostic, first)
        self.assertTrue(c.process_uncertain)


if __name__ == '__main__':
    unittest.main()
