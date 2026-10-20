"""Optional isolation must not stall reviewers or weaken unrelated review gates."""
import unittest
from reviewer_mode import assess
import sdlc_state as s
from test_reviewer_effort import reviewer

class OptionalIsolationTests(unittest.TestCase):
    def test_argon_without_enforced_isolation_can_be_dispatched(self):
        observation = dict(effective_mode='request-review', mode_verified=True,
                           read_only_verified=False, read_only_evidence='')
        self.assertEqual(assess(observation)['decision'], 'existing-permissions')
        config = dict(reviewer(), provider='google', model='gemini-4-argon-medium',
                      mode='request-review', requested_mode=None, mode_verified=True,
                      read_only_verified=False, read_only_evidence='')
        s.validate_reviewer_configuration(config, revised=True)
        for change in [dict(effort_verified=False), dict(context_id='build-context'),
                       dict(provider='openai'), dict(latest_ga_model_verified=False)]:
            with self.subTest(change=change), self.assertRaises(s.GateError):
                s.validate_reviewer_configuration(dict(config, **change), revised=True)

    def test_explicit_opt_in_still_needs_boundary_evidence(self):
        config = dict(reviewer(), read_only_required=True, read_only_verified=False)
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)
        self.assertEqual(assess(config)['decision'], 'probe-required')
        verified = dict(config, read_only_verified=True, read_only_evidence='Observed native tool restriction')
        s.validate_reviewer_configuration(verified, revised=True)
        self.assertEqual(assess(verified)['decision'], 'read-only')

    def test_optional_does_not_make_unproved_verified_claim_true(self):
        config = dict(reviewer(), read_only_required=False, read_only_verified=True, read_only_evidence='')
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)
        self.assertEqual(assess(dict(unavailable_reason='quota exhausted', evidence='actual launch402'))['decision'], 'unavailable')

if __name__ == '__main__':
    unittest.main()
