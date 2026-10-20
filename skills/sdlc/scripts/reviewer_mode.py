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
    if type(observation.get('read_only_required', False)) is not bool:
        return {'decision': 'probe-required',
                'reason': 'read_only_required must be a boolean; correct the assignment.'}
    if (observation.get('read_only_verified') is True
            and isinstance(observation.get('read_only_evidence'), str)
            and observation['read_only_evidence'].strip()):
        return {'decision': 'read-only', 'mode': observation.get('effective_mode'),
                'mode_verified': observation.get('mode_verified') is True}
    if observation.get('read_only_verified') is True:
        return {'decision': 'probe-required',
                'reason': 'A verified read-only claim needs actual evidence.'}
    if observation.get('read_only_required') is True:
        return {'decision': 'probe-required',
                'reason': 'This assignment explicitly requires verified read-only isolation.'}
    if (observation.get('effective_mode') in ('auto', 'full')
            and observation.get('mode_verified') is True and has_evidence):
        return {'decision': 'verified-mode', 'mode': observation['effective_mode']}
    return {'decision': 'existing-permissions',
            'mode': observation.get('effective_mode'),
            'mode_verified': observation.get('mode_verified') is True,
            'read_only_verified': False,
            'reason': 'Read-only isolation and mode configuration are optional; record limitations and continue within review scope.'}


def main():
    observation = json.load(sys.stdin)
    if not isinstance(observation, dict):
        raise ValueError('Expected an observation object')
    print(json.dumps(assess(observation)))


if __name__ == '__main__':
    main()
