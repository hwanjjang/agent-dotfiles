"""Observed mode metadata must not invent provider unavailability or eligibility."""
import unittest
from reviewer_mode import assess


class ReviewerModeTests(unittest.TestCase):
    def test_empty_modes_and_disabled_auto_accept_require_probe(self):
        self.assertEqual(assess({'available_modes': [], 'auto_accept': False})['decision'], 'probe-required')

    def test_advertised_mode_does_not_verify_effective_execution(self):
        self.assertEqual(assess({'available_modes': ['auto']})['decision'], 'probe-required')

    def test_observed_provider_error_is_concrete_unavailability(self):
        result = assess({'available_modes': [], 'unavailable_reason': '402 usage balance exhausted',
                         'evidence': 'Actual bounded launch failed before review'})
        self.assertEqual(result['decision'], 'unavailable')
        self.assertIn('402', result['reason'])

    def test_unavailability_claim_without_evidence_is_not_accepted(self):
        self.assertEqual(assess({'unavailable_reason': 'Unsupported mode'})['decision'], 'probe-required')

    def test_empty_catalog_can_have_verified_native_equivalent(self):
        result = assess({'available_modes': [], 'effective_mode': 'auto', 'mode_verified': True,
                         'evidence': 'Observed native approval mechanism under existing boundaries'})
        self.assertEqual(result['decision'], 'verified-mode')

    def test_missing_or_unverified_effective_mode_never_passes(self):
        for mode, verified, evidence in [(None, True, 'observed'), ('manual', True, 'observed'),
                                        ('auto', False, 'observed'), ('auto', True, '')]:
            with self.subTest(mode=mode, verified=verified, evidence=evidence):
                self.assertEqual(assess({'effective_mode': mode, 'mode_verified': verified,
                                         'evidence': evidence})['decision'], 'probe-required')

    def test_mode_setting_failure_continues_with_verified_read_only_boundary(self):
        result = assess({'requested_mode': 'auto', 'effective_mode': 'default',
                         'mode_verified': False, 'mode_setting_error': 'auto was not applied',
                         'read_only_verified': True,
                         'read_only_evidence': 'Native Read/Grep/Glob allowlist and immutable source snapshot'})
        self.assertEqual(result['decision'], 'read-only')
        self.assertEqual(result['mode'], 'default')
        self.assertFalse(result['mode_verified'])

    def test_omitted_mode_can_continue_read_only(self):
        result = assess({'read_only_verified': True,
                         'read_only_evidence': 'Observed isolated input and source hash unchanged after review'})
        self.assertEqual(result['decision'], 'read-only')
        self.assertIsNone(result['mode'])

    def test_read_only_claim_without_actual_evidence_does_not_pass(self):
        for verified, evidence in [(False, 'observed'), (True, ''), (True, None)]:
            with self.subTest(verified=verified, evidence=evidence):
                self.assertEqual(assess({'read_only_verified': verified,
                                         'read_only_evidence': evidence})['decision'], 'probe-required')

    def test_explicit_incomplete_read_only_proof_precedes_legacy_mode(self):
        for fields in [{'read_only_verified': False, 'read_only_evidence': ''},
                       {'read_only_verified': True}, {'read_only_evidence': 'observed'}]:
            with self.subTest(fields=fields):
                self.assertEqual(assess(dict(effective_mode='auto', mode_verified=True,
                                             evidence='Observed legacy mode', **fields))['decision'],
                                 'probe-required')

    def test_real_launch_failure_is_not_hidden_by_read_only_isolation(self):
        result = assess({'unavailable_reason': '402 quota exhausted', 'evidence': 'Actual launcher returned402',
                         'read_only_verified': True, 'read_only_evidence': 'Isolated source'})
        self.assertEqual(result['decision'], 'unavailable')

    def test_explicit_incompatible_mechanism_can_be_reported(self):
        result = assess({'unavailable_reason': 'Native mechanism cannot provide required scoped execution',
                         'evidence': 'Inspected native permission contract and bounded probe'})
        self.assertEqual(result['decision'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
