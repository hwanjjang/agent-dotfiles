#!/usr/bin/env python3
"""Local SDLC accounting and evidence gates; never executes artifact instructions."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

STAGES = ('triage', 'intent', 'investigation', 'spec', 'design', 'plan', 'test-design',
          'build', 'self-verification', 'independent-verification', 'pr-review',
          'correction', 'merge', 'completion')
OUTPUTS = {s: [s] for s in STAGES}
OUTPUTS.update({'design': ['design-source', 'design-html', 'design-validation'],
                'test-design': ['test-plan'], 'build': ['build', 'change-record', 'candidate-source'],
                'self-verification': ['self-verification', 'test-results']})
MODES = ('implementation', 'review-only', 'plan-only')
KINDS = ('behavior', 'refactor', 'non-executable', 'configuration')
ENDPOINTS = ('local', 'pr', 'pre-merge', 'main')
LIMIT = 10
REVIEW_WORKFLOW = '2026-10-01'


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def revised_review(state):
    return state.get('review_workflow') == REVIEW_WORKFLOW


def verification_stages(state):
    return ('self-verification',) if revised_review(state) else ('self-verification', 'independent-verification')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def located(root, relative):
    require(nonempty(relative) and not Path(relative).is_absolute(), 'Expected repository-relative path')
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'Path escapes repository')
    return path


def state_path(root, task):
    require(bool(re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,95}', task)), 'Invalid task ID')
    return located(root, f'reports/sdlc/{task}/artifacts.json')


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.sdlc-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise GateError(f'Cannot read JSON {path}: {exc}') from exc


def load(root, task):
    state = read_json(state_path(root, task))
    require(isinstance(state, dict) and state.get('schema_version') == 1 and state.get('task_id') == task,
            'Invalid state identity/schema')
    require(state.get('mode') in MODES and state.get('change_kind') in KINDS
            and state.get('endpoint') in ENDPOINTS, 'Invalid task routing')
    require(state.get('review_workflow') in (None, REVIEW_WORKFLOW), 'Unknown review workflow revision')
    if revised_review(state):
        require(state['mode'] == 'implementation' and state['endpoint'] != 'local',
                'PR review workflow requires a PR implementation route')
        require(state.get('stages', {}).get('independent-verification', {}).get('applicable') is False,
                'Separate independent verification is excluded from the revised PR route')
    require(isinstance(state.get('criteria'), list) and state['criteria']
            and all(nonempty(c) for c in state['criteria']), 'Missing acceptance criteria')
    require(set(state.get('stages', {})) == set(STAGES), 'Invalid stage set')
    for stage in state['stages'].values():
        n = stage.get('iterations_started')
        history = stage.get('history')
        require(type(n) is int and 0 <= n <= LIMIT and stage.get('iteration_limit') == LIMIT,
                'Invalid iteration counter/limit')
        require(isinstance(history, list) and len(history) == n
                and [h.get('iteration') for h in history] == list(range(1, n + 1)),
                'Iteration history disagrees with counter')
        require(stage.get('status') in ('pending', 'running', 'complete', 'blocked', 'stale', 'not-applicable'),
                'Invalid stage status')
        require(type(stage.get('applicable')) is bool, 'Missing applicability')
        require(stage['applicable'] or (stage['status'] == 'not-applicable' and nonempty(stage.get('reason'))),
                'Invalid exclusion record')
        if stage['status'] == 'running':
            require(n > 0 and 'receipt' not in history[-1], 'Invalid running attempt')
        if stage['status'] == 'complete':
            require(n > 0 and history[-1].get('receipt', {}).get('decision') == 'PROCEED',
                    'Complete stage has no successful receipt')
    return state


@contextmanager
def transaction(root, task):
    path = state_path(root, task)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / '.state.lock'
    require(not lock_path.is_symlink(), 'Refuse symlinked state lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield path


def event(state, action, stage=None, **fields):
    state['events'].append({'at': timestamp(), 'action': action, 'stage': stage, **fields})


def initialize(root, task, mode, change_kind, endpoint, criteria):
    require(mode in MODES and change_kind in KINDS and endpoint in ENDPOINTS, 'Invalid task route')
    require(criteria and len(criteria) == len(set(criteria)) and all(nonempty(c) for c in criteria),
            'Unique acceptance criterion IDs required')
    require(mode == 'implementation' or endpoint == 'local', 'Review/plan-only cannot authorize PR/main')
    if mode == 'review-only':
        selected = {'triage', 'intent', 'investigation', 'independent-verification', 'completion'}
    elif mode == 'plan-only':
        selected = {'triage', 'intent', 'investigation', 'spec', 'design', 'plan', 'independent-verification', 'completion'}
    else:
        selected = set(STAGES) - {'correction'}
        if endpoint == 'local': selected -= {'pr-review', 'merge'}
        if endpoint in ('pr', 'pre-merge'): selected -= {'merge'}
        if endpoint != 'local': selected.discard('independent-verification')
    with transaction(root, task) as path:
        require(not path.exists(), 'Task already exists; inspect/resume instead of resetting')
        state = {'schema_version': 1, 'task_id': task, 'mode': mode, 'change_kind': change_kind,
                 'endpoint': endpoint, 'criteria': criteria, 'created_at': timestamp(), 'events': [],
                 'stages': {s: {'applicable': s in selected,
                     'status': 'pending' if s in selected else 'not-applicable',
                     'reason': '' if s in selected else ('No correction requested' if s == 'correction' else f'Excluded by {mode}/{endpoint} route'),
                     'iteration_limit': LIMIT, 'iterations_started': 0, 'history': []} for s in STAGES}}
        if mode == 'implementation' and endpoint != 'local':
            state['review_workflow'] = REVIEW_WORKFLOW
        event(state, 'initialized')
        atomic_json(path, state)
    return state


def inspect(root, task):
    return load(root, task)


def upgrade_review_workflow(root, task, source):
    """Adopt the new PR route explicitly, retaining all historical attempts."""
    require(nonempty(source), 'Workflow update needs the actual instruction source')
    with transaction(root, task) as path:
        state = load(root, task)
        require(state['mode'] == 'implementation' and state['endpoint'] != 'local',
                'Only existing PR tasks use this workflow update')
        if revised_review(state):
            return state
        require(all(r['status'] != 'running' for r in state['stages'].values()),
                'Reconcile running attempts before updating the workflow')
        # Plan now owes user scenarios; downstream receipts need the revised checks.
        invalidate_after(state, 'design')
        state['stages']['independent-verification'].update(applicable=False, status='not-applicable',
            reason=f'Removed by {REVIEW_WORKFLOW} PR workflow; historical evidence retained')
        state['review_workflow'] = REVIEW_WORKFLOW
        event(state, 'review-workflow-upgraded', source=source, revision=REVIEW_WORKFLOW)
        atomic_json(path, state)
    return state


def predecessors(state, stage):
    require(stage in STAGES, 'Unknown stage')
    return [s for s in STAGES[:STAGES.index(stage)] if state['stages'][s]['applicable']]


def required_inputs(state, stage):
    # All prior deliverables are explicit handoff inputs; callers may reference, not duplicate them.
    refs = []
    for s in predecessors(state, stage):
        record = state['stages'][s]
        if record['status'] == 'complete':
            refs.extend(record['history'][-1]['receipt']['outputs'])
    return refs


def check_ref(root, ref):
    require(isinstance(ref, dict) and nonempty(ref.get('kind')), 'Invalid artifact reference')
    path = located(root, ref.get('path'))
    if ref['kind'] == 'candidate-source' and ref.get('absent') is True:
        # A dangling symlink is still a reintroduced source entry; resolve() hides it.
        entry = Path(root).resolve() / ref['path']
        require(ref.get('sha256') is None and not (entry.exists() or entry.is_symlink()),
                f'Deleted source reappeared: {entry}')
        return path
    require(path.is_file() and (ref['kind'] == 'candidate-source' or bool(path.read_bytes().strip())),
            f'Missing/empty artifact: {path}')
    require(re.fullmatch(r'[0-9a-f]{64}', ref.get('sha256', '')) is not None
            and digest(path) == ref['sha256'], f'Stale artifact: {path}')
    return path


def reference_key(ref):
    return ref.get('path'), ref.get('sha256'), ref.get('kind')


def validate_results(data, change_kind, candidate, criteria):
    require(isinstance(data, dict) and data.get('candidate') == candidate, 'Stale test candidate')
    scenarios, runs = data.get('scenarios'), data.get('runs')
    require(isinstance(scenarios, list) and isinstance(runs, list) and runs, 'Missing scenarios/runs')
    ids = [s.get('id') for s in scenarios]
    run_ids = [r.get('id') for r in runs]
    require(all(nonempty(x) for x in ids + run_ids) and len(ids) == len(set(ids))
            and len(run_ids) == len(set(run_ids)), 'Missing or duplicate scenario/run IDs')
    for s in scenarios:
        require(all(nonempty(s.get(k)) for k in ('id', 'requirement', 'environment', 'prerequisites',
                'actions', 'expected', 'failure', 'cleanup')) and type(s.get('required')) is bool,
                'Incomplete smoke scenario')
        require(s['requirement'] in criteria, 'Scenario has unknown acceptance criterion')
    for r in runs:
        require(all(nonempty(r.get(k)) for k in ('id', 'phase', 'candidate', 'command', 'environment', 'observed', 'evidence')),
                'Incomplete execution evidence')
        require(type(r.get('exit_code')) is int and r.get('status') == 'passed', 'Failed/unexecuted required run')
        if r['phase'] == 'red':
            require(r['exit_code'] != 0 and r.get('intended_failure') is True, 'Red must observe the intended failure')
        else:
            require(r['exit_code'] == 0 and r['candidate'] == candidate, 'Failed/stale verification')
        if r['phase'] == 'smoke':
            require(r.get('scenario_id') in ids and r.get('execution_kind') == 'real', 'Unknown or mock-only smoke')
    phases = [r['phase'] for r in runs]
    if change_kind == 'non-executable':
        require(nonempty(data.get('not_applicable_reason')) and 'document' in phases,
                'Document changes require real document checks and an exclusion rationale')
        return
    required_scenarios = [s for s in scenarios if s['required']]
    require(required_scenarios, 'Missing mandatory smoke coverage')
    for s in required_scenarios:
        require(any(r['phase'] == 'smoke' and r.get('scenario_id') == s['id'] for r in runs), 'Required smoke not run')
    require('smoke' in phases, 'Missing extra smoke')
    if change_kind in ('behavior', 'configuration'):
        mode = data.get('verification_mode', 'tdd')
        require(mode in ('tdd', 'alternative'), 'Unknown verification mode')
        if mode == 'tdd':
            require('alternative' not in phases, 'Mixed TDD and alternative claims')
            refactored = data.get('refactor_performed', True)
            require(type(refactored) is bool, 'Refactor applicability must be boolean')
            ordered = ['red', 'green']
            if refactored or 'post-refactor' in phases:
                ordered.append('post-refactor')
            ordered.append('smoke')
            require(all(p in phases for p in ordered), 'Missing TDD evidence')
            require(all(phases.index(a) < phases.index(b) for a, b in zip(ordered, ordered[1:])),
                    'Expected Red -> Green -> applicable post-refactor -> additional smoke')
            focused = {'red', 'green', 'post-refactor'}
        else:
            exception = data.get('tdd_exception')
            require(isinstance(exception, dict) and all(nonempty(exception.get(k))
                    for k in ('reason', 'attempted', 'limitation')), 'Missing TDD exception evidence')
            require(not {'red', 'green', 'post-refactor'}.intersection(phases), 'Alternative is not TDD')
            require('alternative' in phases and all(i < phases.index('smoke')
                    for i, phase in enumerate(phases) if phase == 'alternative'),
                    'Alternative check must precede additional smoke')
            checked = set()
            for run in runs:
                if run['phase'] != 'alternative':
                    continue
                require(run.get('execution_kind') == 'real' and run.get('scenario_id') in ids,
                        'Alternative needs a real scenario check')
                checked.add(next(s['requirement'] for s in scenarios if s['id'] == run['scenario_id']))
            require(set(criteria) <= checked, 'Alternative checks do not cover acceptance criteria')
            focused = {'alternative'}
        # A reused evidence file would let a single execution impersonate two layers.
        method = {r['evidence'] for r in runs if r['phase'] in focused}
        smoke = {r['evidence'] for r in runs if r['phase'] == 'smoke'}
        require(not method.intersection(smoke), 'Focused verification and smoke need distinct retained execution evidence')
    else:
        require('regression' in phases and phases.index('regression') < phases.index('smoke'),
                'Refactor requires regression before extra smoke')


def provider_identity(value):
    # Account/profile aliases must never manufacture provider independence.
    require(nonempty(value), 'Missing actual provider')
    name = value.strip().casefold()
    for prefix, provider in (('codex', 'openai'), ('openai', 'openai'),
                             ('claude', 'anthropic'), ('anthropic', 'anthropic'),
                             ('grok', 'xai'), ('xai', 'xai'), ('x.ai', 'xai'),
                             ('gemini', 'google'), ('google', 'google')):
        if name == prefix or name.startswith(prefix + '-') or name.startswith(prefix + '/'):
            return provider
    return name


def reviewer_effort_authority(root, state, intent_receipt=None):
    """Derive effort only from assessed intent outputs, never reviewer assertions.

    This checks structure and freshness. The main/adapter must authenticate and
    interpret the user instruction before recording an intent authority output.
    """
    if intent_receipt is None:
        intent = state['stages']['intent']
        if intent['status'] != 'complete':
            return 'medium', None
        intent_receipt = intent['history'][-1]['receipt']
    require(intent_receipt.get('decision') == 'PROCEED', 'Effort needs successful intent')
    outputs = intent_receipt.get('outputs', [])
    require(isinstance(outputs, list) and all(isinstance(r, dict) for r in outputs),
            'Invalid intent output references')
    refs = [r for r in outputs
            if r.get('kind') == 'reviewer-effort-authority']
    require(len(refs) <= 1, 'Multiple reviewer effort authorities')
    if not refs:
        return 'medium', None
    ref = refs[0]
    data = read_json(check_ref(root, ref))
    require(isinstance(data, dict) and data.get('task_id') == state['task_id']
            and data.get('authorized_by') == 'AK' and data.get('explicit') is True,
            'Effort authority must bind explicit AK authorization to this task')
    effort = data.get('effort')
    require(effort in ('low', 'medium', 'high', 'xhigh', 'max', 'ultra'),
            'Unknown authorized reviewer effort')
    source = data.get('source')
    require(isinstance(source, dict) and source.get('kind') == 'user-instruction'
            and isinstance(source.get('sha256'), str),
            'Effort authority needs user-instruction source')
    check_ref(root, source)
    return effort, ref


def validate_reviewer_configuration(review, revised=False, expected_effort="medium", effort_authority=None):
    require(isinstance(review, dict), 'Missing review configuration')
    for key in ('author_provider', 'provider', 'author_account', 'account', 'model', 'context_id',
                'builder_context_id', 'model_selection_source', 'model_selection_time'):
        require(nonempty(review.get(key)), f'Missing review {key}')
    author_provider = provider_identity(review['author_provider'])
    if revised:
        slot = review.get('reviewer_slot')
        previous = review.get('unavailable_reviewers')
        require(type(slot) is int and slot in (1, 2, 3), 'Missing reviewer fallback slot')
        require(isinstance(previous, list) and len(previous) == slot - 1,
                'Record each unavailable earlier reviewer before fallback')
        for number, failed in enumerate(previous, 1):
            require(isinstance(failed, dict) and failed.get('slot') == number
                    and all(nonempty(failed.get(k)) for k in ('provider', 'account', 'reason', 'evidence')),
                    'Incomplete unavailable reviewer evidence')
            require(provider_identity(failed['provider']) != author_provider,
                    'Earlier reviewers must be from a different provider')
        if slot < 3:
            require(provider_identity(review['provider']) != author_provider,
                    'First and second reviewers must differ from the author provider')
    else:
        require(provider_identity(review['provider']) != author_provider, 'Same-provider reviewer')
    require(review.get('independent') is True and review['context_id'] != review['builder_context_id']
            and review.get('latest_ga_model_verified') is True, 'Unverified reviewer independence/model')
    shared = review.get('shared_optional_review')
    if shared is not None:
        targets = {'grok': 'xai', 'gemini': 'google'}
        require(isinstance(shared, str) and shared in targets,
                'Unknown shared optional reviewer')
        require(provider_identity(review['provider']) == targets[shared],
                'Shared review must use the additional reviewer provider')
        if effort_authority is None:
            expected_effort = 'high'
    require(review.get('requested_effort') == review.get('effort') == expected_effort
            and review.get('effort_verified') is True, 'Reviewer must resolve verified authorized effort')
    provenance = review.get('reviewer_effort_authority')
    require(provenance is None or (effort_authority is not None and provenance == effort_authority),
            'Review cannot select reviewer effort authority')
    read_only = (review.get('read_only_verified') is True
                 and nonempty(review.get('read_only_evidence')))
    # Isolation is optional unless the assignment explicitly opts in. Never turn
    # an unavailable boundary into a verified claim or weaken other review gates.
    require(type(review.get('read_only_required', False)) is bool,
            'Reviewer read_only_required must be boolean')
    if review.get('read_only_verified') is True:
        require(read_only, 'A verified read-only claim needs actual evidence')
    if review.get('read_only_required') is True:
        require(read_only, 'This assignment requires verified read-only isolation')


def validate_review(review, candidate, revised=False, expected_effort="medium", effort_authority=None):
    validate_reviewer_configuration(review, revised, expected_effort, effort_authority)
    for key in ('head', 'base', 'record_url', 'record_id'):
        require(nonempty(review.get(key)), f'Missing review {key}')
    require(review.get('candidate', review.get('head')) == candidate and review.get('verdict') == 'PASS',
            'Review not current PASS')
    require(isinstance(review.get('findings'), list), 'Missing finding dispositions')
    if revised:
        ids = [f.get('id') for f in review['findings']]
        require(all(nonempty(i) for i in ids) and len(ids) == len(set(ids)), 'Unique stable finding IDs required')
        require(review.get('author_changes_remaining') == [], 'Author-selected changes remain or were not assessed')
    for finding in review['findings']:
        require(all(nonempty(finding.get(k)) for k in ('severity', 'category', 'location', 'finding', 'evidence',
                'impact', 'verification', 'requirement', 'confidence', 'disposition')), 'Incomplete review finding')
        if revised:
            require(finding.get('classification') in ('required', 'recommended')
                    and nonempty(finding.get('author_response'))
                    and finding.get('author_action') in ('applied', 'rebutted', 'not-selected'),
                    'Missing required/recommended classification or author disposition')
            require(finding['classification'] == 'required' or finding['severity'] not in ('BLOCKER', 'HIGH'),
                    'BLOCKER/HIGH findings cannot be recommendations')
            mandatory = finding['classification'] == 'required'
            if finding['author_action'] == 'applied':
                require(finding.get('resolved') is True and nonempty(finding.get('reviewer_resolution')),
                        'Applied change needs reviewer confirmation')
        else:
            mandatory = finding['disposition'] == 'Must Fix' or finding['severity'] in ('BLOCKER', 'HIGH')
        require(not mandatory or (finding.get('resolved') is True and nonempty(finding.get('reviewer_resolution'))),
                'Unresolved Must Fix finding')


def validate_review_handoff(state, review):
    """Keep findings across retries/replacements, including blocked reviewer returns."""
    current = {f.get('id'): f for f in review.get('findings', [])}
    mapping = review.get('legacy_finding_mapping', {})
    require(isinstance(mapping, dict) and all(nonempty(k) and nonempty(v) for k, v in mapping.items()),
            'Map legacy findings to stable IDs with an object of history:position keys')
    for history_index, attempt in enumerate(state['stages']['pr-review']['history'], 1):
        previous_review = attempt.get('receipt', {}).get('review', {})
        previous = previous_review.get('findings', [])
        previous_mapping = previous_review.get('legacy_finding_mapping', {})
        if isinstance(previous_mapping, dict):
            for key, fid in previous_mapping.items():
                require(mapping.get(key) == fid, f'Reviewer handoff changed legacy mapping {key}')
        mapped_ids = set()
        for finding_index, finding in enumerate(previous, 1):
            fid = finding.get('id')
            if not nonempty(fid):
                # History is append-only; one-based positions identify the original record.
                key = f'{history_index}:{finding_index}'
                fid = mapping.get(key)
                require(nonempty(fid), f'Map legacy finding {key} to a stable ID')
            require(fid not in mapped_ids, 'Distinct findings in one attempt need distinct stable IDs')
            mapped_ids.add(fid)
            require(fid in current, f'Reviewer handoff dropped finding {fid}')
            mandatory = (finding.get('classification') == 'required'
                         or finding.get('disposition') == 'Must Fix'
                         or finding.get('severity') in ('BLOCKER', 'HIGH'))
            if mandatory and current[fid].get('classification') != 'required':
                require(nonempty(current[fid].get('reviewer_resolution')), f'Unexplained downgrade of {fid}')


def validate_user_scenarios(data, criteria):
    scenarios = data.get('scenarios') if isinstance(data, dict) else None
    require(isinstance(scenarios, list) and scenarios, 'Planning requires user scenarios')
    ids, covered = set(), set()
    for scenario in scenarios:
        require(isinstance(scenario, dict) and all(nonempty(scenario.get(k)) for k in
                ('id', 'user', 'goal', 'prerequisites', 'expected', 'failure')), 'Incomplete user scenario')
        require(scenario['id'] not in ids, 'Duplicate user scenario ID')
        ids.add(scenario['id'])
        require(isinstance(scenario.get('steps'), list) and scenario['steps']
                and all(nonempty(step) for step in scenario['steps']), 'User scenario needs ordered actions')
        mapped = scenario.get('criteria')
        require(isinstance(mapped, list) and mapped and all(nonempty(c) for c in mapped)
                and set(mapped) <= set(criteria), 'User scenario needs known acceptance criteria')
        covered.update(mapped)
    require(set(criteria) <= covered, 'User scenarios do not cover acceptance criteria')


def validate_documentation(root, data):
    require(isinstance(data, dict) and data.get('checked') is True and nonempty(data.get('summary'))
            and type(data.get('new_feature')) is bool and type(data.get('ux_ui_changed')) is bool
            and isinstance(data.get('updates'), list), 'Missing final documentation/diagram assessment')
    for ref in data['updates']: check_ref(root, ref)
    if data['new_feature'] or data['ux_ui_changed']:
        manual = data.get('manual')
        require(isinstance(manual, dict) and manual.get('render_checked') is True
                and nonempty(manual.get('summary')), 'Screenshot PDF manual needs rendered visual checks')
        check_ref(root, manual.get('source'))
        pdf = check_ref(root, manual.get('pdf'))
        require(pdf.read_bytes().startswith(b'%PDF-'), 'Manual artifact is not a PDF')
        captures = manual.get('screenshots')
        require(isinstance(captures, list) and captures, 'Manual needs actual user scenario screenshots')
        for ref in captures: check_ref(root, ref)


def validate_merge_gate(root, gate, review_receipt):
    require(isinstance(gate, dict), 'Current pre-merge gate receipt required')
    review = review_receipt['review']
    require(gate.get('head') == review['head'] and gate.get('base') == review['base']
            and gate.get('candidate') == review_receipt['candidate'], 'Merge target/head differs from reviewed revision')
    require(all(gate.get(k) is True for k in ('delegated', 'required_ci_passed', 'protections_satisfied',
            'human_requests_resolved', 'remote_state_verified')) and gate.get('production_trigger') == 'none',
            'Merge authority, CI, protections or deployment coupling unresolved')
    require(all(nonempty(gate.get(k)) for k in ('authority_source', 'checked_at', 'remote_record')),
            'Missing current merge observation/authority')
    require(isinstance(gate.get('evidence'), list) and gate['evidence'], 'Missing merge gate evidence')
    for ref in gate['evidence']: check_ref(root, ref)


def validate_premerge_readiness(root, state, gate):
    """Readiness is an observed result, never a grant of main integration authority."""
    require(isinstance(gate, dict), 'Current merge-ready receipt required')
    review_receipt = state['stages']['pr-review']['history'][-1]['receipt']
    review = review_receipt['review']
    require(gate.get('head') == review['head'] and gate.get('base') == review['base']
            and gate.get('candidate') == review_receipt['candidate'], 'Readiness head/base/candidate differs')
    require(all(gate.get(k) is True for k in ('merge_ready', 'push_verified', 'pr_verified', 'mergeable',
            'required_ci_passed', 'protections_satisfied', 'human_requests_resolved', 'remote_state_verified')),
            'PR, push, CI, review requests, protections or mergeability incomplete')
    require(all(gate.get(k) is False for k in ('merge_authorized', 'auto_merge_enabled', 'merge_queue_enqueued')),
            'Pre-merge forbids integration authorization, auto-merge and merge queue')
    require(all(nonempty(gate.get(k)) for k in ('repository', 'pr_url', 'authority_source', 'checked_at',
                                              'remote_record', 'production_trigger')),
            'Missing readiness observation')
    require(gate['production_trigger'] != 'unknown', 'Inspect production coupling before readiness')
    require(isinstance(gate.get('evidence'), list) and gate['evidence'], 'Missing readiness evidence')
    for ref in gate['evidence']: check_ref(root, ref)
    authority_ref = gate.get('authority')
    require(isinstance(authority_ref, dict) and authority_ref.get('kind') == 'pre-merge-authority',
            'Missing scoped pre-merge authority reference')
    authority = read_json(check_ref(root, authority_ref))
    require(authority.get('task_id') == state['task_id'] and authority.get('repository') == gate['repository']
            and authority.get('endpoint') == 'pre-merge' and nonempty(authority.get('source'))
            and authority.get('merge_authorized') is False, 'Authority scope differs from task')
    required_actions = {'implement', 'test', 'smoke', 'commit', 'push', 'pr-create', 'pr-update',
                        'ci-read', 'correct', 'transfer-evidence', 'spawn-reviewer'}
    prohibited = {'merge', 'auto-merge', 'merge-queue', 'production-deploy',
                  'permission-escalation', 'credential-transfer'}
    require(isinstance(authority.get('allowed_actions'), list)
            and required_actions <= set(authority['allowed_actions'])
            and not prohibited.intersection(authority['allowed_actions']), 'Incomplete/conflicting action authority')
    require(isinstance(authority.get('prohibited_actions'), list)
            and prohibited <= set(authority['prohibited_actions']), 'Missing prohibited actions')
    require(isinstance(authority.get('materials'), list)
            and set(authority['materials']) == {'code', 'tests', 'sdlc-evidence'}, 'Invalid material transfer scope')
    accounts = authority.get('accounts')
    require(isinstance(accounts, list) and accounts and all(isinstance(a, dict) and nonempty(a.get('id'))
            and nonempty(a.get('provider')) for a in accounts), 'Missing authorized accounts')
    require(len({a['id'] for a in accounts}) == len(accounts), 'Duplicate authorized account IDs')
    authorized = {a['id']: provider_identity(a['provider']) for a in accounts}
    executions = [review]
    if not revised_review(state):
        verifier_receipt = state['stages']['independent-verification']['history'][-1]['receipt']
        verifier = verifier_receipt['verifier']
        config = verifier.get('configuration')
        effort, effort_authority = reviewer_effort_authority(root, state)
        validate_reviewer_configuration(config, expected_effort=effort, effort_authority=effort_authority)
        require(config['context_id'] == verifier['context_id']
                and config['builder_context_id'] == verifier['builder_context_id'], 'Verifier context differs')
        require(provider_identity(config['author_provider']) == provider_identity(review['author_provider'])
                and config['author_account'] == review['author_account'], 'Verification/review author differs')
        executions.append(config)
    for execution in executions:
        require(authorized.get(execution['author_account']) == provider_identity(execution['author_provider'])
                and authorized.get(execution['account']) == provider_identity(execution['provider']),
                'Execution account/provider outside authority')
    for stage in verification_stages(state):
        require(state['stages'][stage]['history'][-1]['receipt']['candidate'] == gate['candidate'],
                'Readiness evidence candidates differ')


def check_receipt(root, state, stage, receipt):
    require(isinstance(receipt, dict), 'Receipt must be an object')
    require(receipt.get('decision') in ('PROCEED', 'NEEDS_HUMAN', 'BLOCKED'), 'Invalid HOTL decision')
    require(all(nonempty(receipt.get(k)) for k in ('reason', 'authority_source', 'candidate', 'next_action')),
            'Missing decision/authority/candidate context')
    if revised_review(state) and stage == 'pr-review' and receipt.get('review'):
        review = receipt['review']
        require(isinstance(review, dict) and isinstance(review.get('findings'), list), 'Missing review findings')
        ids = [f.get('id') for f in review['findings']]
        require(all(nonempty(i) for i in ids) and len(ids) == len(set(ids)), 'Unique stable finding IDs required')
        validate_review_handoff(state, review)
    if receipt['decision'] != 'PROCEED': return
    refs = receipt.get('outputs')
    inputs = receipt.get('inputs')
    assessment = receipt.get('assessment', {})
    require(isinstance(refs, list) and isinstance(inputs, list), 'Missing artifact references')
    require(set(OUTPUTS[stage]) <= {r.get('kind') for r in refs}, 'Missing stage deliverables')
    require(len({reference_key(r) for r in refs}) == len(refs), 'Duplicate output references')
    require({reference_key(r) for r in required_inputs(state, stage)} <= {reference_key(r) for r in inputs},
            'Required upstream revisions were not consumed')
    require(nonempty(assessment.get('assessor')) and nonempty(assessment.get('summary'))
            and isinstance(assessment.get('criteria'), list) and assessment['criteria']
            and set(assessment['criteria']) <= set(state['criteria']), 'Missing content/acceptance assessment')
    for ref in inputs + refs: check_ref(root, ref)
    if revised_review(state) and stage in ('plan', 'self-verification'):
        kind = 'user-scenarios' if stage == 'plan' else 'documentation'
        matches = [ref for ref in refs if ref['kind'] == kind]
        require(len(matches) == 1, f'Missing {kind} deliverable')
        data = read_json(check_ref(root, matches[0]))
        if stage == 'plan': validate_user_scenarios(data, state['criteria'])
        else: validate_documentation(root, data)
    if stage == 'self-verification':
        result_ref = next(r for r in refs if r['kind'] == 'test-results')
        data = read_json(located(root, result_ref['path']))
        validate_results(data, state['change_kind'], receipt['candidate'], state['criteria'])
        for run in data['runs']:
            evidence = located(root, run['evidence'])
            require(evidence.is_file() and evidence.stat().st_size, 'Missing retained test log')
            require(any(r['path'] == run['evidence'] and r['sha256'] == digest(evidence) for r in refs),
                    'Execution log needs a hashed output reference')
    if stage == 'independent-verification':
        verifier = receipt.get('verifier', {})
        require(verifier.get('independent') is True and nonempty(verifier.get('context_id'))
                and nonempty(verifier.get('builder_context_id'))
                and verifier['context_id'] != verifier['builder_context_id']
                and nonempty(verifier.get('checks')), 'Independent verifier evidence missing')
    if stage == 'intent':
        reviewer_effort_authority(root, state, receipt)
    if stage == 'pr-review':
        effort, effort_authority = reviewer_effort_authority(root, state)
        validate_review(receipt.get('review'), receipt['candidate'], revised_review(state), effort, effort_authority)
    if stage in ('independent-verification', 'pr-review', 'correction', 'merge') and state['mode'] == 'implementation':
        for prior in ('self-verification', 'independent-verification', 'pr-review'):
            if STAGES.index(prior) >= STAGES.index(stage): break
            if not state['stages'][prior]['applicable']: continue
            require(state['stages'][prior]['history'][-1]['receipt']['candidate'] == receipt['candidate'],
                    'Candidate differs from prior verification')
    if stage == 'completion' and state['endpoint'] == 'pre-merge':
        ready_refs = [ref for ref in refs if ref['kind'] == 'merge-ready']
        require(len(ready_refs) == 1, 'Pre-merge completion requires one merge-ready artifact')
        gate = read_json(check_ref(root, ready_refs[0]))
        require(receipt['candidate'] == gate.get('candidate'), 'Completion candidate differs from readiness')
        validate_premerge_readiness(root, state, gate)
    if stage == 'completion':
        require(set(state['criteria']) <= set(assessment['criteria']), 'Completion does not account for all criteria')
        if revised_review(state):
            require(receipt.get('documentation_final_checked') is True
                    and receipt.get('author_changes_remaining') == [],
                    'Final documentation check and author change disposition required')
            require(receipt['candidate'] == state['stages']['pr-review']['history'][-1]['receipt']['candidate'],
                    'Completion differs from reviewed candidate')
    if stage == 'merge':
        require(state['endpoint'] == 'main', 'Only main endpoint can integrate')
        validate_merge_gate(root, receipt.get('merge_gate'), state['stages']['pr-review']['history'][-1]['receipt'])
        merge = receipt.get('merge', {})
        require(merge.get('delegated') is True and merge.get('production_trigger') == 'none'
                and merge.get('protections_satisfied') is True and merge.get('required_ci_passed') is True
                and nonempty(merge.get('base'))
                and merge.get('expected_head') == state['stages']['pr-review']['history'][-1]['receipt']['review']['head']
                and nonempty(merge.get('main_commit')) and nonempty(merge.get('record_url'))
                and merge.get('remote_main_verified') is True, 'Incomplete merge/main receipt')


def check_completed(root, state, stage):
    record = state['stages'][stage]
    if not record['applicable']: return
    require(record['status'] == 'complete', f'Stage {stage} is not complete ({record["status"]})')
    receipt = record['history'][-1]['receipt']
    check_receipt(root, state, stage, receipt)


def invalidate_after(state, stage):
    for following in STAGES[STAGES.index(stage) + 1:]:
        record = state['stages'][following]
        if record['applicable'] and record['status'] in ('complete', 'running', 'blocked'):
            require(record['status'] != 'running', 'Finish/cancel downstream running attempt before upstream re-entry')
            record['status'] = 'stale'
            record['reason'] = f'Upstream stage {stage} re-entered'


def begin(root, task, stage, objective, resolution=None):
    require(stage in STAGES and nonempty(objective), 'Known stage and objective required')
    with transaction(root, task) as path:
        state = load(root, task)
        record = state['stages'][stage]
        require(record['applicable'], 'Stage excluded by task route; do not expand authority')
        if record['history'] and record['history'][-1].get('receipt', {}).get('decision') == 'NEEDS_HUMAN':
            require(nonempty(resolution), 'Human decision unresolved; record actual resolution before continuing')
        require(record['status'] != 'running', 'Attempt already running; reconcile/finish it first')
        require(record['iterations_started'] < LIMIT, 'iteration-limit-reached: no 11th attempt')
        for prior in predecessors(state, stage): check_completed(root, state, prior)
        invalidate_after(state, stage)
        record['iterations_started'] += 1
        record['status'], record['reason'] = 'running', ''
        record['history'].append({'iteration': record['iterations_started'], 'started_at': timestamp(),
                                  'objective': objective, 'resolution': resolution, 'inputs': required_inputs(state, stage)})
        event(state, 'iteration-started', stage, iteration=record['iterations_started'])
        atomic_json(path, state)
    return record


def finish(root, task, stage, receipt):
    require(stage in STAGES, 'Unknown stage')
    with transaction(root, task) as path:
        state = load(root, task)
        record = state['stages'][stage]
        require(record['status'] == 'running', 'No running attempt to finish')
        require(receipt.get('iteration') == record['iterations_started'], 'Receipt belongs to another attempt')
        if receipt.get('decision') == 'PROCEED':
            for prior in predecessors(state, stage): check_completed(root, state, prior)
        check_receipt(root, state, stage, receipt)
        record['history'][-1].update({'finished_at': timestamp(), 'receipt': receipt})
        record['status'] = 'complete' if receipt['decision'] == 'PROCEED' else 'blocked'
        record['reason'] = receipt['reason']
        if record['status'] == 'blocked' and record['iterations_started'] == LIMIT:
            record['reason'] = 'iteration-limit-reached'
        if stage == 'pr-review' and (receipt['decision'] != 'PROCEED' or receipt.get('review', {}).get('findings')):
            state['stages']['correction'].update({'applicable': True, 'status': 'pending',
                                                  'reason': 'Review finding/verification dispositions required'})
        event(state, 'iteration-finished', stage, iteration=record['iterations_started'],
              decision=receipt['decision'], reason=record['reason'])
        atomic_json(path, state)
    return record


def skip(root, task, stage, reason):
    require(nonempty(reason) and stage in STAGES, 'Known stage and exclusion reason required')
    with transaction(root, task) as path:
        state = load(root, task)
        allowed = {'design', 'correction'}
        if state['mode'] != 'implementation': allowed.add('independent-verification')
        if state['change_kind'] == 'non-executable': allowed.add('test-design')
        require(stage in allowed, 'Cannot skip a mandatory stage')
        require(stage != 'correction' or not state['stages'][stage]['applicable'], 'Review dispositions require correction record')
        require(state['stages'][stage]['status'] != 'running', 'Cannot skip a running attempt')
        invalidate_after(state, stage)
        state['stages'][stage].update({'applicable': False, 'status': 'not-applicable', 'reason': reason})
        event(state, 'stage-excluded', stage, reason=reason)
        atomic_json(path, state)
    return state['stages'][stage]


def validate(root, task, stage=None, checkpoint=None, gate=None):
    state = load(root, task)
    require(bool(stage) != bool(checkpoint), 'Choose a stage or checkpoint')
    if stage:
        require(stage in STAGES, 'Unknown stage')
        selected = predecessors(state, stage) + [stage]
    else:
        require(checkpoint in ('pre-commit', 'pre-merge', 'completion'), 'Unknown checkpoint')
        if checkpoint == 'pre-commit':
            require(state['mode'] == 'implementation', 'No implementation commit in this route')
            selected = list(STAGES[:STAGES.index('self-verification') + 1])
        elif checkpoint == 'pre-merge':
            require(state['mode'] == 'implementation' and state['endpoint'] in ('main', 'pre-merge'), 'Integration/readiness endpoint not selected')
            selected = list(STAGES[:STAGES.index('merge')])
        else: selected = list(STAGES)
    for item in selected: check_completed(root, state, item)
    if checkpoint == 'pre-merge':
        review_receipt = state['stages']['pr-review']['history'][-1]['receipt']
        reviewed = review_receipt['candidate']
        if state['endpoint'] == 'pre-merge':
            validate_premerge_readiness(root, state, gate)
        else:
            validate_merge_gate(root, gate, review_receipt)
        for item in verification_stages(state):
            require(state['stages'][item]['history'][-1]['receipt']['candidate'] == reviewed,
                    'Verification and review attest different candidates')
    return {'valid': True, 'task_id': task, 'stage': stage, 'checkpoint': checkpoint,
            'scope': 'Local structure, recorded configuration and digest freshness only; verify authority, meaning and remote state separately.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'begin', 'finish', 'skip', 'validate', 'inspect', 'upgrade-review-workflow'):
        p = subs.add_parser(name)
        p.add_argument('--root', required=True, type=Path)
        p.add_argument('--task', required=True)
        if name == 'upgrade-review-workflow': p.add_argument('--source', required=True)
        if name == 'init':
            p.add_argument('--mode', choices=MODES, required=True)
            p.add_argument('--change-kind', choices=KINDS, required=True)
            p.add_argument('--endpoint', choices=ENDPOINTS, default='local')
            p.add_argument('--criteria', nargs='+', required=True)
        if name in ('begin', 'finish', 'skip'): p.add_argument('--stage', choices=STAGES, required=True)
        if name == 'begin':
            p.add_argument('--objective', required=True)
            p.add_argument('--resolution', help='Actual human decision/source resolving an earlier NEEDS_HUMAN')
        if name == 'finish': p.add_argument('--receipt', type=Path, required=True)
        if name == 'skip': p.add_argument('--reason', required=True)
        if name == 'validate':
            p.add_argument('--gate', type=Path, help='Current merge-gate JSON required for pre-merge')
            group = p.add_mutually_exclusive_group(required=True)
            group.add_argument('--stage', choices=STAGES)
            group.add_argument('--checkpoint', choices=('pre-commit', 'pre-merge', 'completion'))
    args = parser.parse_args()
    try:
        if args.command == 'init': result = initialize(args.root, args.task, args.mode, args.change_kind, args.endpoint, args.criteria)
        elif args.command == 'upgrade-review-workflow': result = upgrade_review_workflow(args.root, args.task, args.source)
        elif args.command == 'begin': result = begin(args.root, args.task, args.stage, args.objective, args.resolution)
        elif args.command == 'finish': result = finish(args.root, args.task, args.stage, read_json(args.receipt))
        elif args.command == 'skip': result = skip(args.root, args.task, args.stage, args.reason)
        elif args.command == 'validate': result = validate(args.root, args.task, args.stage, args.checkpoint, read_json(args.gate) if args.gate else None)
        else: result = inspect(args.root, args.task)
        print(json.dumps({'event': args.command, 'result': result}, indent=2))
    except (GateError, OSError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({'event': args.command, 'error': str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
