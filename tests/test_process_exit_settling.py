"""Cleanup may wait for a transient exit record; ambiguity never means absence."""
import sys
import time
import unittest
from unittest.mock import patch

from test_process_query_diagnostics import controller, GOOD, ABSENT, trial

EXITING = dict(GOOD, stdout=GOOD['stdout'].replace('/synthetic/worker', '<defunct>'))


class ProcessExitSettlingTests(unittest.TestCase):
    def owned(self):
        c = controller()
        c.seen = {123: trial.parse_process_query(GOOD, 123)}
        return c

    def test_owned_cleanup_waits_for_fresh_absence_without_signaling(self):
        c = self.owned()
        with patch.object(sys, 'platform', 'darwin'), \
                patch.object(trial, 'bounded', side_effect=[EXITING, ABSENT]) as query, \
                patch.object(trial.os, 'killpg') as signal:
            self.assertIsNone(c.process(123, cleanup=True))
        self.assertEqual(query.call_count, 2)
        signal.assert_not_called()
        self.assertFalse(c.process_uncertain)
        self.assertIsNone(c.process_query_diagnostic)

    def test_replacement_is_returned_for_existing_identity_check_not_absence(self):
        c = self.owned()
        replacement = dict(GOOD, stdout=GOOD['stdout'].replace('/synthetic/worker', '/synthetic/replacement'))
        with patch.object(sys, 'platform', 'darwin'), \
                patch.object(trial, 'bounded', side_effect=[EXITING, replacement]):
            current = c.process(123, cleanup=True)
        self.assertFalse(trial.same_process(c.seen[123], current))
        self.assertIsNotNone(current)

    def test_persistent_ambiguity_expires_and_retains_uncertainty(self):
        c = self.owned(); c.cleanup_deadline = time.monotonic() + .08
        with patch.object(sys, 'platform', 'darwin'), \
                patch.object(trial, 'bounded', return_value=EXITING) as query:
            with self.assertRaises(trial.plan.Refusal):
                c.process(123, cleanup=True)
        self.assertGreater(query.call_count, 1)
        self.assertTrue(c.process_uncertain)
        self.assertEqual(c.process_query_diagnostic['reason'], 'executable_not_absolute')

    def test_unknown_owner_launch_watch_and_other_platform_do_not_retry(self):
        for platform, mode, owned in [('darwin', {}, True), ('darwin', {'watch': True}, True),
                                     ('darwin', {'cleanup': True}, False), ('linux', {'cleanup': True}, True)]:
            with self.subTest(platform=platform, mode=mode, owned=owned):
                c = self.owned()
                if not owned: c.seen = {}
                with patch.object(sys, 'platform', platform), \
                        patch.object(trial, 'bounded', return_value=EXITING) as query:
                    with self.assertRaises(trial.plan.Refusal): c.process(123, **mode)
                self.assertEqual(query.call_count, 1)
                self.assertTrue(c.process_uncertain)

    def test_other_query_error_is_not_retried(self):
        c = self.owned()
        with patch.object(sys, 'platform', 'darwin'), \
                patch.object(trial, 'bounded', side_effect=[EXITING, dict(GOOD, stop_reason='timeout'), ABSENT]) as query:
            with self.assertRaises(trial.plan.Refusal): c.process(123, cleanup=True)
        self.assertEqual(query.call_count, 2)
        self.assertEqual(c.process_query_diagnostic['reason'], 'timeout')

    def test_prior_uncertainty_is_never_cleared(self):
        c = self.owned(); c.process_uncertain = True
        c.process_query_diagnostic = {'phase': 'watch', 'pid': 123, 'reason': 'stderr'}
        with patch.object(sys, 'platform', 'darwin'), \
                patch.object(trial, 'bounded', side_effect=[EXITING, ABSENT]):
            self.assertIsNone(c.process(123, cleanup=True))
        self.assertTrue(c.process_uncertain)
        self.assertEqual(c.process_query_diagnostic['reason'], 'stderr')


if __name__ == '__main__':
    unittest.main()
