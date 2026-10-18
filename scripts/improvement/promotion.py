#!/usr/bin/env python3
"""Pure source-review recommendations; never merges, installs or launches trials.

The arithmetic rule can qualify a synthetic example. Operational eligibility is
unavailable until independently verified live/holdout evidence has a real backend.
"""
import argparse
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import time
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
    critical_by_arm = {arm: sum(t['critical_violations'] for t in report['trials']
                                if t['arm'] == arm) for arm in ev.ARMS}
    if critical_by_arm['candidate']:
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
            'critical_violations_by_arm': critical_by_arm,
            'promotion_eligible': False}


def recommend(*, experiment, report, completions, current_spec, source_diff_digest):
    """Recompute a #26 report and return a bounded recommendation without effects."""
    reasons, outcome, metrics = [], 'inconclusive', None
    review = {'source_diff_digest': source_diff_digest if ev.sha(source_diff_digest) else None, 'report_digest': None,
              'experiment_digest': None, 'baseline': None, 'candidate': None}
    try:
        ev.require(ev.sha(source_diff_digest), 'source_diff_digest')
        ev.require(isinstance(report, dict) and ev.sha(report.get('report_digest')), 'report_digest')
        ev.require(ev.encoded(experiment) == ev.encoded(ev.freeze(experiment['spec'])), 'experiment_integrity')
        spec = experiment['spec']
        review.update(report_digest=report['report_digest'], experiment_digest=experiment['experiment_digest'],
                      baseline=spec['identities']['baseline'], candidate=spec['identities']['candidate'])
        if (ev.digest(current_spec) != experiment['spec_digest']
                or spec['identities']['grader'] != ev.source_hash()):
            outcome, reasons = 'reject', ['stale_experiment']
        elif ev.encoded(report) != ev.encoded(ev.compare(experiment, completions, spec)):
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


def _admission():
    if __package__:
        from . import trial_admission
    else:
        import trial_admission
    return trial_admission


def _git(repository, operation, oid, deadline, limit):
    """Fixed raw object reads; bounded streams and one shared source-read deadline."""
    ev.require(isinstance(oid, str) and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', oid), 'source_object')
    commands = {'type': ['cat-file', '-t'], 'commit': ['cat-file', 'commit'],
                'blob': ['cat-file', 'blob'], 'tree_object': ['cat-file', 'tree'],
                'tree': ['ls-tree', '-r', '-t', '-z', '--full-tree']}
    ev.require(operation in commands and time.monotonic() < deadline, 'source_read_limit')
    executable = shutil.which('git', path=os.defpath)
    ev.require(executable is not None, 'git_unavailable')
    env = dict(PATH=os.defpath, LC_ALL='C', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS='1',
               GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    argv = [executable, '--no-pager', '--no-replace-objects', '--no-optional-locks',
            '-C', str(repository), '-c', 'core.hooksPath=' + os.devnull,
            '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never',
            *commands[operation], oid]
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, start_new_session=True, close_fds=True)
    streams = {process.stdout: bytearray(), process.stderr: bytearray()}
    stop = min(deadline, time.monotonic() + 3)
    try:
        with selectors.DefaultSelector() as selector:
            for stream in streams:
                os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                ev.require(time.monotonic() < stop, 'source_read_limit')
                for key, _ in selector.select(min(.05, max(.001, stop-time.monotonic()))):
                    raw = os.read(key.fd, 65536)
                    if not raw: selector.unregister(key.fileobj); continue
                    ev.require(sum(map(len, streams.values())) + len(raw) <= limit, 'source_read_limit')
                    streams[key.fileobj].extend(raw)
            process.wait(timeout=max(.001, stop-time.monotonic()))
        ev.require(process.returncode == 0 and not streams[process.stderr], 'source_read_failed')
        return bytes(streams[process.stdout])
    finally:
        uncertain = False
        try:
            if process.poll() is None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                except OSError:
                    uncertain = True
                    try: process.kill()
                    except ProcessLookupError: pass
            process.wait(timeout=2)
        finally:
            for stream in streams: stream.close()
        ev.require(not uncertain, 'source_cleanup_uncertain')


def _object_hash(raw, kind, oid):
    return hashlib.new('sha1' if len(oid) == 40 else 'sha256',
        kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def _tree(repository, commit, deadline):
    ev.require(_git(repository, 'type', commit, deadline, 128) == b'commit\n', 'source_commit')
    raw = _git(repository, 'commit', commit, deadline, 65536)
    ev.require(_object_hash(raw, 'commit', commit) == commit, 'source_object')
    first = raw.split(b'\n', 1)[0]
    ev.require(first.startswith(b'tree '), 'source_commit')
    tree = first[5:].decode('ascii'); p = _admission().p
    rows, trees = {}, {tree}
    raw = _git(repository, 'tree', tree, deadline, 1048576)
    ev.require(raw.endswith(b'\0') and len(raw.split(b'\0')) <= 4097, 'source_tree_limit')
    for row in raw[:-1].split(b'\0'):
        metadata, name = row.split(b'\t', 1); mode, kind, oid = metadata.decode('ascii').split(' ')
        name = name.decode('utf-8'); p.relative(name)
        ev.require(len(name.encode()) <= 1024 and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', oid), 'source_tree')
        ev.require(name not in rows and (mode, kind) in (('040000','tree'), ('100644','blob'),
            ('100755','blob'), ('120000','blob'), ('160000','commit')), 'source_tree')
        rows[name] = (mode, oid)
        if kind == 'tree': trees.add(oid)
    total = 0
    for oid in trees:
        raw = _git(repository, 'tree_object', oid, deadline, 1048576)
        total += len(raw)
        ev.require(total <= 1048576 and _object_hash(raw, 'tree', oid) == oid, 'source_tree')
    return tree, {name: value for name, value in rows.items() if value[0] != '040000'}


def verify_source(context, *, repository, baseline_commit, candidate_commit, component_roots, _deadline=None):
    """Bind complete committed portable components to the already guarded arm bytes."""
    ad = _admission(); p = ad.p
    repository = p.absolute(repository, 'source_repository')
    def identity():
        fd = p.directory(repository)
        try: return os.fstat(fd).st_dev, os.fstat(fd).st_ino
        finally: os.close(fd)
    before = identity(); deadline = min(_deadline, time.monotonic() + 12) if _deadline is not None else time.monotonic() + 12
    ev.require(type(context) is ad.NativeContext and context.digest == ev.digest(context.data), 'source_context')
    ev.require(isinstance(component_roots, list) and 1 <= len(component_roots) <= 8
               and all(isinstance(r, str) for r in component_roots)
               and component_roots == sorted(set(component_roots)), 'source_roots')
    for root in component_roots:
        path = p.relative(root)
        ev.require(len(path.parts) >= 2 and path.parts[0] in ('skills','policies','mcp')
            and (path.parts[0] != 'skills' or len(path.parts) == 2)
            and not any(root.startswith(other + '/') for other in component_roots if other != root), 'source_roots')
    selected = lambda name: any(name == r or name.startswith(r + '/') for r in component_roots)
    base_tree, baseline = _tree(repository, baseline_commit, deadline)
    candidate_tree, candidate = _tree(repository, candidate_commit, deadline)
    changed = sorted(n for n in set(baseline) | set(candidate) if baseline.get(n) != candidate.get(n))
    ev.require(changed and all(selected(n) for n in changed)
        and all(any(n == r or n.startswith(r + '/') for n in set(baseline) | set(candidate))
                for r in component_roots), 'source_scope')
    inventories, cache = {}, {}
    for arm, tree in zip(ev.ARMS, (baseline, candidate)):
        rows = {n: v for n, v in tree.items() if selected(n)}
        ev.require(1 <= len(rows) <= p.MAX_FILES and all(v[0] == '100644' for v in rows.values()), 'source_metadata')
        value = context.data['arms'][arm]; expected = {r['path']: r['sha256'] for r in value['files']}
        keys = ('entrypoint', 'files', 'routing') if 'routing' in value else ('entrypoint', 'files')
        ev.require(ev.digest({k: value[k] for k in keys}) == context.spec['identities'][arm], 'source_arm')
        ev.require(set(rows) == set(expected), 'source_inventory')
        total = 0; inventories[arm] = {}
        for name, (_, oid) in sorted(rows.items()):
            if oid not in cache:
                raw = _git(repository, 'blob', oid, deadline, p.MAX_FILE_BYTES)
                ev.require(_object_hash(raw, 'blob', oid) == oid, 'source_object')
                cache[oid] = raw
            raw = cache[oid]; total += len(raw)
            digest = hashlib.sha256(raw).hexdigest()
            ev.require(total <= p.MAX_INPUT_BYTES and digest == expected[name]
                and context.guard.read(Path(value['root']) / name, p.MAX_FILE_BYTES)[1] == digest, 'source_arm')
            inventories[arm][name] = digest
    # File presence/bytes are represented; executable/symlink metadata is not.
    changes = [dict(path=n, old_mode=baseline.get(n, (None,))[0],
        new_mode=candidate.get(n, (None,))[0], old_blob_sha256=inventories['baseline'].get(n),
        new_blob_sha256=inventories['candidate'].get(n)) for n in changed]
    ev.require(identity() == before and context.guard.check(), 'source_changed')
    return dict(baseline_commit=baseline_commit,candidate_commit=candidate_commit,
        baseline_tree=base_tree,candidate_tree=candidate_tree,component_roots=list(component_roots),
        source_diff_digest=ev.digest(changes),changes=changes)


def _source_unavailable(error):
    return (isinstance(error, subprocess.TimeoutExpired) or
            isinstance(error, ValueError) and str(error) in ('source_read_limit', 'git_unavailable'))


def recommend_native(*, experiment, current_spec, context_path, attempts, report_path,
                     repository, baseline_commit, candidate_commit, component_roots, heldout_record_path=None):
    """Recompute a sealed native report and verify committed source; never deploy."""
    ad = _admission(); guard = ad.Guard(); batch = None
    outcome, reasons, metrics, review, gate_digest = 'inconclusive', [], None, {}, None
    assessment = None; source = None; source_remaining = 0
    try:
        gate_digest = guard.read(Path(__file__).resolve(), retain=False)[1]
        supplied = guard.json(report_path, private=True)
        ctx = ad.load_context(experiment, current_spec, context_path)
        batch = ad.read_attempts(ctx, attempts)
        report = ev.compare(experiment, [], current_spec, native=batch)
        frozen_inputs = ev.digest([experiment, current_spec]); deadline = time.monotonic() + 12
        if ('evaluation_scope' in current_spec or report.get('classification')!='development'
                or report.get('evidence_kind')!='native_artifact_development_comparison'):
            outcome, reasons = 'reject', ['development_scope_required']
        elif not ad.same(supplied, report):
            outcome, reasons = 'reject', ['report_evidence_mismatch']
        else:
            try:
                source = verify_source(ctx, repository=repository, baseline_commit=baseline_commit,
                    candidate_commit=candidate_commit, component_roots=component_roots, _deadline=deadline)
            except (OSError, ValueError, KeyError, TypeError, UnicodeError, subprocess.SubprocessError) as error:
                source = None
                outcome, reasons = ('inconclusive', ['source_unavailable']) if _source_unavailable(error) else ('reject', ['source_verification_failed'])
            if source is not None:
                review = dict(source=source, report_digest=report['report_digest'],
                    experiment_digest=experiment['experiment_digest'], admission_context_digest=ctx.digest,
                    baseline=ctx.spec['identities']['baseline'], candidate=ctx.spec['identities']['candidate'])
                metrics = evaluate_rule(experiment, report)
                metrics['scope'] = 'source_guarded_native_rule_diagnostic'
                reasons = metrics['reasons'] + report['blockers'] + ['same_host_heldout_unverified']
                if metrics['verdict'] == 'reject': outcome = 'reject'
                source_remaining = deadline - time.monotonic()
        if heldout_record_path is not None and metrics is not None:
            if __package__:
                from . import heldout
            else:
                import heldout
            assessment = heldout.assess(heldout_record_path,batch,report,source)
            if assessment['status']=='invalid':outcome='reject'
            elif assessment['status']=='verified':
                if assessment['rule_result']['verdict']=='reject':outcome='reject'
                elif metrics['verdict']=='eligible' and assessment['rule_result']['verdict']=='eligible':outcome='recommend'
                if outcome=='recommend':
                    reasons=[r for r in reasons if r not in ('diagnostic_only','same_host_heldout_unimplemented','same_host_heldout_unverified')]
            reasons += assessment['reasons']
        if source is not None:
            # The second source check follows remote assessment. Preserve the
            # remaining Git/read budget without charging remote transport time.
            try:
                ev.require(source_remaining > 0, 'source_read_limit')
                again = verify_source(ctx, repository=repository, baseline_commit=baseline_commit,
                    candidate_commit=candidate_commit, component_roots=component_roots,
                    _deadline=time.monotonic() + source_remaining)
                ev.require(ad.same(source, again), 'source_changed')
            except (OSError, ValueError, KeyError, TypeError, UnicodeError, subprocess.SubprocessError) as error:
                if not _source_unavailable(error):raise
                if outcome != 'reject':outcome = 'inconclusive'
                reasons.append('source_unavailable')
        if (not guard.check() or not ctx.guard.check() or not batch.guard.check()
                or frozen_inputs != ev.digest([experiment, current_spec])
                or (not batch.valid(experiment, current_spec) and not batch.execution_error)):
            outcome, reasons = 'reject', reasons + ['native_evidence_changed']
        elif batch.execution_error:
            reasons.append('native_evidence_unavailable')
        # Never turn a source-guarded development report into held-out evidence.
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError, subprocess.SubprocessError):
        outcome, reasons = 'reject', ['invalid_native_gate_input']
    finally:
        if batch is not None: batch.close()
    result = dict(schema_version=1,evidence_kind='native_source_review_recommendation',
        recommendation=outcome,reasons=sorted(set(reasons)),rule_result=metrics,review=review,
        source_accepted=False,promotion_eligible=False,merge_authorized=False,install_authorized=False,
        backend_identity_verified=False,gate_digest=gate_digest)
    if assessment is not None:result['heldout']=assessment
    result['recommendation_digest'] = ev.digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('recommend', 'recommend-native'))
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(ev.MAX_BYTES + 1)
        ev.require(len(raw) <= ev.MAX_BYTES, 'input_limit')
        data = json.loads(raw, object_pairs_hook=ev.no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ev.Invalid('invalid_number')))
        fields = ('experiment report completions current_spec source_diff_digest' if args.command == 'recommend' else
                  'experiment current_spec context_path attempts report_path repository baseline_commit candidate_commit component_roots')
        ev.require(ev.keys(data, fields) or (args.command=='recommend-native' and ev.keys(data,fields+' heldout_record_path')), 'gate_fields')
        result = recommend(**data) if args.command == 'recommend' else recommend_native(**data)
        sys.stdout.buffer.write(ev.encoded(result))
        return 0
    except (ev.Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        sys.stdout.write('{"status":"rejected","reason":"invalid_gate_input"}\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
