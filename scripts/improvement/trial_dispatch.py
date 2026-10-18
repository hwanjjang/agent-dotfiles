#!/usr/bin/env python3
"""Project a frozen development trial into supervisor-owned dispatch data.

Only executor_input is intended for the executor. Requested runtime and source
identities are declarations, not observed execution. The supervisor owns attempt
reservation, aggregate budget enforcement, materialization and evidence custody.
This module does not execute a trial, admit a receipt or grant live eligibility.
"""
import argparse
import json
import sys

try:
    from . import evaluation as ev
except ImportError:
    import evaluation as ev


def prepare(experiment, current_spec, trial_id, attempt_id):
    """Pure projection; repeated input is deterministic, not a replay reservation."""
    ev.require(ev.keys(experiment, 'schema_version spec spec_digest trials experiment_digest'),
               'experiment_fields')
    frozen = ev.freeze(experiment['spec'])
    ev.require(ev.encoded(experiment) == ev.encoded(frozen), 'experiment_tampered')
    ev.require(ev.digest(current_spec) == frozen['spec_digest'], 'stale_experiment')
    spec = frozen['spec']
    ev.require(spec['identities']['grader'] == ev.source_hash(), 'stale_grader')
    ev.require(ev.sha(trial_id), 'trial_id')
    ev.require(ev.token(attempt_id), 'attempt_id')
    selected = [trial for trial in frozen['trials'] if trial['trial_id'] == trial_id]
    ev.require(len(selected) == 1, 'trial_not_scheduled')
    trial = selected[0]
    case = next(case for case in spec['cases'] if case['case_id'] == trial['case_id'])
    part = case if trial['variant'] == 'reproduction' else case['counterpart']
    # freeze already made detached copies. Never hand the complete spec, grading
    # contract or other arm's identity to the executor through this projection.
    executor_input = part['inputs']
    result = {
        'schema_version': 1,
        'kind': 'development_trial_dispatch',
        'binding': {
            'experiment_digest': frozen['experiment_digest'],
            'trial': trial,
            'attempt_id': attempt_id,
            'source_digest': spec['identities'][trial['arm']],
            # A reference to the whole experiment ceiling, never a new allowance.
            'experiment_budget_digest': ev.digest(spec['budget']),
        },
        'executor_input': executor_input,
        'requested_runtime': spec['runtime'],
        'executor_input_digest': ev.digest(executor_input),
    }
    result['dispatch_digest'] = ev.digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare',))
    parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(ev.MAX_BYTES + 1)
        ev.require(len(raw) <= ev.MAX_BYTES, 'input_limit')
        data = json.loads(raw, object_pairs_hook=ev.no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ev.Invalid('invalid_number')))
        ev.require(ev.keys(data, 'experiment current_spec trial_id attempt_id'), 'dispatch_fields')
        result = prepare(**data)
        sys.stdout.buffer.write(ev.encoded(result))
        return 0
    except (ev.Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        sys.stdout.write('{"status":"rejected","reason":"invalid_dispatch_input"}\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
