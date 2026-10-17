#!/usr/bin/env python3
"""Pure source-review recommendations; never merges, installs or launches trials.

The arithmetic rule can qualify a synthetic example. Operational eligibility is
unavailable until independently verified live/holdout evidence has a real backend.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__:
    from . import evaluation as ev
else:
    import evaluation as ev

RULES = ('quality_gain_v1', 'equal_quality_lower_tokens_v1')


def evaluate_rule(experiment, report):
    """Calculate frozen diagnostic criteria only; this is not evidence validation.

Only recommend() binds these values to verified input records. Even an eligible
arithmetic result has no operational authority and cannot be used as a receipt.
"""
    spec = experiment['spec']
    rejected, missing = [], []
    if spec['promotion_rule'] not in RULES:
        missing.append('unsupported_rule')
    if report['critical_violations']:
        rejected.append('critical_violation')
    if any(report['counts'][v] for v in ('blocked', 'inconclusive')) or report['coverage']['unassigned']:
        missing.append('trial_coverage_incomplete')
    if report['qualification']['status'] != 'qualified':
        missing.append('unqualified_grader')
    metric = spec['primary_metric']
    arms = {}
    for arm in ev.ARMS:
        trials = [t for t in report['trials'] if t['arm'] == arm]
        values = [t['dimensions'][metric] for t in trials]
        if not values or any(v not in ('pass', 'fail') for v in values):
            missing.append('primary_metric_incomplete')
        arms[arm] = {'scheduled': len(trials), 'pass': values.count('pass')}
    if arms['baseline']['scheduled'] != arms['candidate']['scheduled']:
        missing.append('unpaired_trials')
    benefit = arms['candidate']['pass'] - arms['baseline']['pass']
    for case in spec['cases']:
        for variant in ev.VARIANTS:
            subset = [t for t in report['trials'] if t['case_id'] == case['case_id'] and t['variant'] == variant]
            passes = {arm: sum(t['dimensions'][metric] == 'pass' for t in subset if t['arm'] == arm) for arm in ev.ARMS}
            if passes['baseline'] - passes['candidate'] > spec['regression_margin'] * spec['repetitions']:
                rejected.append('case_regression')
    # These versioned rules declare token and aggregate latency ceilings. Dollar
    # usage is neither required nor inferred. Request limits remain runner-owned.
    if spec['promotion_rule'] in RULES:
        tokens = report['usage']['total_tokens']
        if tokens is None:
            missing.append('usage_unknown')
        elif tokens > spec['budget']['tokens']:
            rejected.append('token_budget_exceeded')
        if 'amount' in spec['budget']:
            amount = report['usage'].get('currency_amount')
            if amount is None:
                missing.append('declared_currency_usage_unknown')
            elif amount > spec['budget']['amount']:
                rejected.append('declared_currency_budget_exceeded')
        if report['latency']['unknown']:
            missing.append('latency_unknown')
        elif report['latency']['known_total_ms'] > spec['budget']['seconds'] * 1000:
            rejected.append('time_budget_exceeded')
    arm_tokens = {}
    for arm in ev.ARMS:
        values = [t['usage']['total_tokens'] for t in report['trials'] if t['arm'] == arm]
        arm_tokens[arm] = None if any(v is None for v in values) else sum(values)
    if not missing:
        if spec['promotion_rule'] == 'quality_gain_v1' and benefit <= 0:
            rejected.append('target_benefit_not_observed')
        elif spec['promotion_rule'] == 'equal_quality_lower_tokens_v1':
            if benefit < 0 or arm_tokens['candidate'] >= arm_tokens['baseline']:
                rejected.append('target_benefit_not_observed')
    return {'scope': 'synthetic_rule_diagnostic',
            'verdict': 'reject' if rejected else 'inconclusive' if missing else 'eligible',
            'reasons': sorted(set(rejected + missing)), 'primary_metric': metric,
            'observed_pass_gain': benefit, 'arms': arms, 'arm_tokens': arm_tokens,
            'promotion_eligible': False}


def recommend(*, experiment, report, completions, current_spec, source_diff_digest):
    """Recompute a #26 report and return a bounded recommendation without effects."""
    reasons, outcome, metrics = [], 'inconclusive', None
    review = {'source_diff_digest': source_diff_digest if ev.sha(source_diff_digest) else None, 'report_digest': None,
              'experiment_digest': None, 'baseline': None, 'candidate': None}
    try:
        ev.require(ev.sha(source_diff_digest), 'source_diff_digest')
        ev.require(isinstance(report, dict) and ev.sha(report.get('report_digest')), 'report_digest')
        ev.require(experiment == ev.freeze(experiment['spec']), 'experiment_integrity')
        spec = experiment['spec']
        review.update(report_digest=report['report_digest'], experiment_digest=experiment['experiment_digest'],
                      baseline=spec['identities']['baseline'], candidate=spec['identities']['candidate'])
        if (ev.digest(current_spec) != experiment['spec_digest']
                or spec['identities']['grader'] != ev.source_hash()):
            outcome, reasons = 'reject', ['stale_experiment']
        elif report != ev.compare(experiment, completions, spec):
            outcome, reasons = 'reject', ['report_evidence_mismatch']
        else:
            metrics = evaluate_rule(experiment, report)
            reasons = list(metrics['reasons'])
            if metrics['verdict'] == 'reject':
                outcome = 'reject'
            # A digest or self-described receipt is not a trusted execution or
            # custody verifier. No input parameter can waive these current gaps.
            reasons.extend(['live_evidence_verifier_unavailable',
                            'independent_holdout_custody_unavailable',
                            'development_cases_only'])
    except (ev.Invalid, KeyError, TypeError, ValueError, RecursionError):
        outcome, reasons = 'reject', ['invalid_gate_input']
    result = {'schema_version': 1, 'evidence_kind': 'development_promotion_recommendation',
              'recommendation': outcome, 'reasons': sorted(set(reasons)),
              'rule_result': metrics, 'review': review, 'promotion_eligible': False,
              'merge_authorized': False, 'install_authorized': False,
              'gate_digest': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    result['recommendation_digest'] = ev.digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('recommend',))
    parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(ev.MAX_BYTES + 1)
        ev.require(len(raw) <= ev.MAX_BYTES, 'input_limit')
        data = json.loads(raw, object_pairs_hook=ev.no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ev.Invalid('invalid_number')))
        ev.require(ev.keys(data, 'experiment report completions current_spec source_diff_digest'), 'gate_fields')
        result = recommend(**data)
        sys.stdout.buffer.write(ev.encoded(result))
        return 0
    except (ev.Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        sys.stdout.write('{"status":"rejected","reason":"invalid_gate_input"}\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
