"""Pure numeric usage behavior; no native client or account access."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'improvement'))
from native_usage import Usage


def payload(total=100, output=10):
    return {'total': {'totalTokens': total, 'inputTokens': total-output,
                     'outputTokens': output}, 'last': {'totalTokens': 50}}


class UsageTests(unittest.TestCase):
    def usage(self, **kwargs):
        return Usage(soft_total=10000, soft_output=1000, **kwargs)

    def test_deduplicates_cumulative_snapshots_without_summing(self):
        saved = []
        u = self.usage(sink=saved.append)
        for n in (100, 100, 120):
            self.assertIsNone(u.accept(payload(n)))
        s = u.summary()
        self.assertEqual((s['duplicates'], len(saved)), (1, 2))
        self.assertEqual(s['latest']['total']['totalTokens'], 120)
        self.assertIsNone(s['latest']['total']['cachedInputTokens'])
        self.assertFalse(s['latest']['presence']['total']['cachedInputTokens'])
        self.assertIsNone(s['response_or_request_count'])

    def test_explicit_thresholds_and_persistence_before_soft_stop(self):
        saved = []
        u = Usage(soft_total=100, soft_output=99, sink=saved.append)
        self.assertEqual(u.accept(payload()), 'soft_usage_stop')
        self.assertEqual(len(saved), 1)
        self.assertEqual(u.summary()['stop']['metric'], 'total.totalTokens')
        for bad in (True, 0, -1, 1.5, '1', 2**63):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Usage(soft_total=bad, soft_output=10)

    def test_output_guard_independent_and_sticky(self):
        u = Usage(soft_total=1000, soft_output=10)
        self.assertEqual(u.accept(payload()), 'soft_usage_stop')
        u.accept(payload(110, 11))
        self.assertEqual(u.summary()['stop']['observed'], 10)
        self.assertEqual(u.summary()['stop']['metric'], 'total.outputTokens')

    def test_exact_ints_required_missing_and_discontinuity(self):
        for bad in (True, 1.0, '1', -1, 2**63):
            p = payload(); p['total']['inputTokens'] = bad
            self.assertEqual(self.usage().accept(p), 'usage_shape')
        self.assertEqual(self.usage().accept({}), 'usage_unavailable')
        u = self.usage(); u.accept(payload())
        self.assertEqual(u.accept(payload(99)), 'usage_discontinuity')

    def test_estimated_last_relationship_is_diagnostic(self):
        p = payload(); p['last'].update(inputTokens=80, outputTokens=5)
        u = self.usage()
        self.assertIsNone(u.accept(p))
        self.assertTrue(u.summary()['latest']['component_relationship_anomaly'])

    def test_retention_64_plus_one_then_no_more_sink_writes(self):
        saved = []; u = self.usage(sink=saved.append)
        for i in range(64): self.assertIsNone(u.accept(payload(100+i)))
        for i in range(100):
            self.assertEqual(u.accept(payload(200+i)), 'usage_retention_limit')
        self.assertEqual(len(saved), 65)
        self.assertEqual(u.summary()['changed_snapshots_retained'], 64)

    def test_unpersisted_post_limit_snapshot_is_not_claimed_durable(self):
        u = self.usage(sink=lambda _: None)
        for i in range(66): u.accept(payload(100+i))
        self.assertFalse(u.summary()['all_changed_snapshots_persisted'])

    def test_sink_failure_and_defensive_copies(self):
        def mutate(s): s['total']['totalTokens'] = 999
        u = self.usage(sink=mutate); u.accept(payload())
        snapshot = u.summary(); snapshot['latest']['total']['totalTokens'] = -1
        self.assertEqual(u.summary()['first']['total']['totalTokens'], 100)
        def fail(s): raise RuntimeError('sensitive error text')
        u = self.usage(sink=fail)
        self.assertEqual(u.accept(payload()), 'usage_persistence_failed')
        self.assertNotIn('sensitive', str(u.summary()))


if __name__ == '__main__': unittest.main()
