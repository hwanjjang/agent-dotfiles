"""Classify observed reviewer mode evidence without changing or launching anything."""
import json
import sys


def assess(observation):
    """Catalog metadata alone establishes neither eligibility nor unavailability.

    Evidence is an adapter-supplied receipt reference or observed contract/result;
    this helper does not independently authenticate that evidence or a full review.
    """
    evidence = observation.get('evidence')
    has_evidence = isinstance(evidence, str) and bool(evidence.strip())
    reason = observation.get('unavailable_reason')
    if isinstance(reason, str) and reason.strip() and has_evidence:
        return {'decision': 'unavailable', 'reason': reason}
    if (observation.get('read_only_verified') is True
            and isinstance(observation.get('read_only_evidence'), str)
            and observation['read_only_evidence'].strip()):
        return {'decision': 'read-only', 'mode': observation.get('effective_mode'),
                'mode_verified': observation.get('mode_verified') is True}
    if 'read_only_verified' in observation or 'read_only_evidence' in observation:
        return {'decision': 'probe-required',
                'reason': 'Explicit read-only boundary proof is incomplete.'}
    if (observation.get('effective_mode') in ('auto', 'full')
            and observation.get('mode_verified') is True and has_evidence):
        return {'decision': 'verified-mode', 'mode': observation['effective_mode']}
    return {'decision': 'probe-required',
            'reason': 'Verify a read-only boundary under existing permissions; mode configuration is optional.'}


def main():
    observation = json.load(sys.stdin)
    if not isinstance(observation, dict):
        raise ValueError('Expected an observation object')
    print(json.dumps(assess(observation)))


if __name__ == '__main__':
    main()
