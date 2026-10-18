#!/usr/bin/env python3
"""Offline trusted-host artifact admission. No inference, recovery or account access.

Repository qualification records and private supervisor journals are trusted inputs,
not signatures against a hostile same-UID owner. JSON flags cannot admit evidence.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

if __package__:
    from . import evaluation as ev, native_trial_plan as p
    # The maintained controller uses script-local absolute imports.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import native_trial as nt
    finally:
        sys.path.pop(0)
    from . import native_usage, trial_dispatch
else:
    # Keep the typed batch identity when evaluation imports this CLI module.
    sys.modules.setdefault('trial_admission', sys.modules[__name__])
    import evaluation as ev, native_trial as nt, native_trial_plan as p
    import native_usage, trial_dispatch

ROOT = Path(__file__).resolve().parents[2]
KIND = 'native_artifact_snapshot_v1'
QUALIFICATIONS = {'execution': 'docs/verification/native-trials.json',
                  'grading': 'docs/verification/scoped-grading-integrity.json',
                  'collection': 'docs/verification/native-outcome-collection.json'}

ROUTING_QUALIFICATION = 'docs/verification/native-routing-observer.json'


def supported_native_runtime(runtime):
    return same({k: runtime.get(k) for k in
                 ('provider', 'model', 'client', 'adapter', 'reasoning')}, {
        'provider': 'openai', 'model': 'gpt-6-luna', 'client': 'codex-0.163.0',
        'adapter': p.PROFILE, 'reasoning': 'low'})


def native_grader_sources():
    """Fixed native admission dependencies; not a configurable signing inventory."""
    return {name: p.read_file(p.SOURCE / name, 2 * 1024 * 1024,
                             'grader_source_unsafe', retain=False)[1]
            for name in ('evaluation.py', 'trial_admission.py', 'trial_dispatch.py')}


def native_grader_identity():
    return ev.digest(native_grader_sources())


def require(value, reason):
    ev.require(value, reason)


def same(left, right):
    return ev.encoded(left) == ev.encoded(right)


class Guard:
    """Bound reads and remember exact file/directory identities for final recheck."""
    def __init__(self):
        self.files, self.dirs, self.used = {}, {}, 0

    def read(self, path, maximum=1048576, *, private=False, retain=True, owner=True):
        path = p.absolute(str(path), 'unsafe_path')
        raw, digest = p.read_file(path, maximum, 'unsafe_file', owner=owner, retain=retain)
        info = path.lstat()
        require(not private or stat.S_IMODE(info.st_mode) == 0o600, 'private_mode')
        previous = self.files.get(path)
        identity = (digest, p.stamp(info), maximum, owner)
        require(previous is None or previous == identity, 'evidence_changed')
        self.files[path] = identity
        if retain:
            self.used += len(raw)
            require(self.used <= ev.MAX_BYTES, 'read_limit')
        return raw, digest

    def json(self, path, *, private=False):
        raw, _ = self.read(path, private=private)
        return json.loads(raw, object_pairs_hook=ev.no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ev.Invalid('invalid_number')))

    def directory(self, path, names=False):
        fd = p.directory(path)
        try:
            info = os.fstat(fd)
            require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'directory_owner')
            listing = None
            if names:
                items = []
                with os.scandir(fd) as iterator:
                    for item in iterator:
                        require(len(items) < 4096, 'record_limit')
                        items.append(item.name)
                listing = tuple(sorted(items))
            value = (info.st_dev, info.st_ino, info.st_uid, listing)
            require(path not in self.dirs or self.dirs[path] == value, 'directory_changed')
            self.dirs[path] = value
        finally:
            os.close(fd)

    def check(self):
        try:
            for path, (digest, stamp, maximum, owner) in self.files.items():
                _, current = p.read_file(path, maximum, 'evidence_changed', owner=owner, retain=False)
                require(current == digest and p.stamp(path.lstat()) == stamp, 'evidence_changed')
            for path, expected in list(self.dirs.items()):
                self.directory(path, names=expected[3] is not None)
            return True
        except (OSError, ValueError):
            return False


def model_selection(value, model):
    require(same(value, dict(requested=model, observed_thread_start=model,
        source='thread/start.result.model', match=True, rerouted=False,
        backend_identity_verified=False)), 'model_selection_unavailable')
    return model


def routing_projection(value, routing, profile):
    fixed = dict(version=1, mode=routing['mode'], status='observed', reason=None,
        catalog_digest=routing['catalog_digest'], observer_profile_digest=profile,
        health={'user_prompt_seen': True, 'scope': 'single_initial_turn_thread'},
        correlation={'thread_matched': True, 'turn_matched': True},
        evidence_scope='receiver_complete_under_trusted_io', qualification='pending',
        all_pages_verified=False, process_adherence='not_assessed', outcome='not_graded')
    require(ev.keys(value, ' '.join(fixed) + ' activation implicit_reads explicit_count transport')
            and same({k: value[k] for k in fixed}, fixed), 'routing_unavailable')
    transport = value['transport']
    complete = dict(stdout_eof=True, stderr_eof=True, process_reaped=True, trailing_bytes=0,
        pending_records=0, projected_records_written=1, receiver_complete=True, native_written_count=None)
    counters = ('stderr_bytes', 'stderr_frames', 'accepted_events', 'ignored_records')
    require(ev.keys(transport, ' '.join(complete) + ' close_mode ' + ' '.join(counters))
            and same({k: transport[k] for k in complete}, complete)
            and transport['close_mode'] in ('graceful_stdin_eof', 'post_terminal_kill_drained')
            and all(ev.integer(transport[k], 0, nt.protocol.STREAM_LIMIT) for k in counters), 'routing_transport')
    rows = value['implicit_reads']
    require(isinstance(rows, list) and len(rows) <= len(routing['catalog'])
            and ev.integer(value['explicit_count'], 0, 127)
            and (routing['mode'] != 'natural' or value['explicit_count'] == 0), 'routing_counts')
    slots = []
    for row in rows:
        require(ev.keys(row, 'slot count') and ev.integer(row['slot'], 0, len(routing['catalog'])-1)
                and ev.integer(row['count'], 1, 127), 'routing_counts')
        slots.append(row['slot'])
    require(slots == sorted(set(slots)) and transport['accepted_events'] ==
            1 + value['explicit_count'] + sum(r['count'] for r in rows) <= 128
            and transport['stderr_bytes'] >= transport['stderr_frames']
            and transport['stderr_frames'] == transport['accepted_events'] + transport['ignored_records']
            and value['activation'] == ('implicit_main_first_page_read' if rows else
                                       'observed_none_in_declared_catalog'), 'routing_counts')
    return {'native.routing.none': not rows, **{'native.routing.implicit_read.' + row['name']:
            row['slot'] in slots for row in routing['catalog']}}


def qualify_routing(record, context):
    require(ev.keys(record, 'schema_version kind profile source_digests runtime_digests image_digest admission_grader_source_digests observer_profile_digest catalog_normalization fixture_routing assigned_slot cases falsification')
            and type(record['schema_version']) is int and record['schema_version'] == 1
            and record['kind'] == 'native_routing_observer_qualification_v1'
            and same(record['admission_grader_source_digests'], native_grader_sources())
            and record['catalog_normalization'] == 'inline-frontmatter-unique-slot-name-resource-v1'
            and same(record['falsification'], {'false_marker_no_activation': True}), 'routing_unqualified')
    route = record['fixture_routing']
    p.fields(route, 'mode observer catalog_scope catalog_digest catalog', 'routing_fixture')
    require(route['mode'] == 'natural' and route['observer'] == 'implicit-stderr-json-v1'
            and route['catalog_scope'] == 'declared_experiment_subset'
            and isinstance(route['catalog'], list) and 3 <= len(route['catalog']) <= 5
            and route['catalog_digest'] == p.digest(route['catalog']), 'routing_fixture')
    for slot, row in enumerate(route['catalog']):
        require(ev.keys(row, 'slot name main_resource main_sha256 description_sha256')
                and type(row['slot']) is int and row['slot'] == slot and p.token(row['name'])
                and str(p.relative(row['main_resource'])).startswith('skills/')
                and row['main_resource'].endswith('/SKILL.md')
                and ev.sha(row['main_sha256']) and ev.sha(row['description_sha256']), 'routing_fixture')
    require(all(len({r[k] for r in route['catalog']}) == len(route['catalog']) for k in ('name', 'main_resource'))
            and ev.integer(record['assigned_slot'], 0, len(route['catalog'])-1), 'routing_fixture')
    profile = nt.routing_profile_digest({'routing': route, 'sources': context.data['runtime']['source_digests']})
    require(record['observer_profile_digest'] == profile and isinstance(record['cases'], list)
            and len(record['cases']) == 4 and {r['kind'] for r in record['cases']} ==
            {'assigned_main', 'list_only', 'reference_only', 'failed_main'}, 'routing_unqualified')
    for row in record['cases']:
        require(ev.keys(row, 'kind execution_kind routing_observation model_selection cleanup')
                and row['execution_kind'] == 'actual_native_codex' and cleanup_complete(row['cleanup']), 'routing_unqualified')
        model_selection(row['model_selection'], context.spec['runtime']['model'])
        projection = routing_projection(row['routing_observation'], route, profile)
        selected = [r['slot'] for r in route['catalog'] if projection['native.routing.implicit_read.' + r['name']]]
        require(selected == ([record['assigned_slot']] if row['kind'] == 'assigned_main' else []), 'routing_unqualified')


class NativeContext:
    def __init__(self, experiment, spec, data, guard):
        self.experiment, self.spec, self.data = copy.deepcopy((experiment, spec, data))
        self.guard, self.qualification_error = guard, None
        self.digest = ev.digest(data)


def load_context(experiment, current_spec, context_path):
    require(same(experiment, ev.freeze(experiment['spec'])) and
            ev.digest(current_spec) == experiment['spec_digest'], 'stale_experiment')
    require(current_spec['identities']['grader'] == native_grader_identity(), 'stale_grader')
    require(supported_native_runtime(current_spec['runtime']), 'unsupported_native_runtime')
    guard = Guard()
    for name in native_grader_sources():
        guard.read(p.SOURCE / name, 2 * 1024 * 1024, retain=False)
    data = guard.json(context_path, private=True)
    require((ev.keys(data, 'schema_version kind experiment_digest arms runtime qualification_refs collection_by_trial')
             or ev.keys(data, 'schema_version kind experiment_digest arms runtime qualification_refs collection_by_trial execution_root'))
            and type(data['schema_version']) is int and data['schema_version'] == 1
            and data['kind'] == 'native_artifact_admission_context_v1'
            and data['experiment_digest'] == experiment['experiment_digest'], 'context_fields')
    if 'execution_root' in data:
        guard.directory(p.absolute(data['execution_root'], 'execution_root'))
    rt = data['runtime']
    require(ev.keys(rt, 'profile source_digests runtime_digests image_digest metadata_digest')
            and rt['profile'] == p.PROFILE and isinstance(rt['source_digests'], dict)
            and set(rt['source_digests']) == p.SOURCE_NAMES
            and all(ev.sha(h) for h in rt['source_digests'].values())
            and ev.keys(rt['runtime_digests'], 'codex code_mode_host docker executor_archive')
            and all(ev.sha(h) for h in rt['runtime_digests'].values())
            and ev.sha(rt['metadata_digest']) and isinstance(rt['image_digest'], str)
            and rt['image_digest'].startswith('sha256:')
            and ev.sha(rt['image_digest'][7:]), 'runtime_fields')
    for name, digest in rt['source_digests'].items():
        require(guard.read(p.SOURCE / name, retain=False)[1] == digest, 'source_changed')
    require(current_spec['identities']['runner'] == ev.digest(rt['source_digests'])
            and current_spec['identities']['environment'] == ev.digest({k: v for k, v in rt.items() if k != 'source_digests'}), 'source_mapping')
    require(isinstance(data['arms'], dict) and set(data['arms']) == set(ev.ARMS), 'arm_fields')
    layouts = []
    for arm, value in data['arms'].items():
        routed = 'routing' in value
        keys = ('entrypoint', 'files', 'routing') if routed else ('entrypoint', 'files')
        require(ev.keys(value, 'root ' + ' '.join(keys)) and isinstance(value['files'], list)
                and 1 <= len(value['files']) <= p.MAX_FILES, 'arm_fields')
        root = p.absolute(value['root'], 'arm_root')
        paths, selected, total = [], {}, 0
        for row in value['files']:
            require(ev.keys(row, 'path sha256') and ev.sha(row['sha256']), 'arm_file')
            name = str(p.relative(row['path'])); paths.append(name)
            raw, observed = guard.read(root / name, p.MAX_FILE_BYTES)
            require(observed == row['sha256'], 'arm_changed')
            total += len(raw); selected['bundle', name] = raw
        if routed:
            p.validate_routing(value['routing'], selected)
        natural = routed and value['routing']['mode'] == 'natural'
        require(paths == sorted(set(paths)) and total <= p.MAX_INPUT_BYTES
                and (value['entrypoint'] is None if natural else value['entrypoint'] in paths)
                and current_spec['identities'][arm] == ev.digest({k: value[k] for k in keys}), 'arm_mapping')
        layouts.append({**{k: value['routing'][k] for k in ('mode', 'observer', 'catalog_scope')},
            'catalog': [{k: r[k] for k in ('slot', 'name', 'main_resource')} for r in value['routing']['catalog']]} if routed else None)
    require(same(*layouts), 'catalog_layout')
    require(isinstance(data['collection_by_trial'], dict) and set(data['collection_by_trial']) == {t['trial_id'] for t in experiment['trials']}, 'collection_inventory')
    for trial in experiment['trials']:
        declaration = data['collection_by_trial'][trial['trial_id']]
        p.validate_collection(declaration, 'trial')
        criteria = current_spec['checks'][trial['case_id']][trial['variant']]['criteria']
        require(all(c['target'] in declaration['paths'] for c in criteria if c['kind'] == 'artifact_sha256'), 'collection_targets')
    context = NativeContext(experiment, current_spec, data, guard)
    try:
        locations = {**QUALIFICATIONS, **({'routing': ROUTING_QUALIFICATION} if layouts[0] is not None else {})}
        require(set(data['qualification_refs']) == set(locations), 'qualification_fields')
        records = {}
        for name, location in locations.items():
            ref = data['qualification_refs'][name]
            require(ev.keys(ref, 'path sha256') and ref['path'] == location and ev.sha(ref['sha256']), 'qualification_authority')
            record = guard.json(ROOT / location)
            require(guard.files[ROOT / location][0] == ref['sha256'] and
                    same(record['source_digests'], rt['source_digests']) and
                    same(record['runtime_digests'], rt['runtime_digests']) and
                    record['image_digest'] == rt['image_digest'] and record['profile'] == rt['profile'], 'qualification_changed')
            records[name] = record
        if 'routing' in records:
            qualify_routing(records['routing'], context)
        execution, grading, collection = (records[k] for k in QUALIFICATIONS)
        require(execution['authenticated']['status'] == 'qualified_current_profile'
                and execution['authenticated']['qualification']['boundary_checks_verified'] is True
                and execution['authenticated']['matching_completed_terminal'] is True
                and execution['cleanup']['automatic_owned_cleanup_complete'] is True, 'authentication_unqualified')
        require(grading['grader_source_sha256'] == ev.source_hash()
                and same(grading['admission_grader_source_digests'], native_grader_sources())
                and grading['status'] == 'credential_free_scoped_executor_verified'
                and grading['actual_checks']['protected_files_exist_outside_mounts_and_unchanged_after_shutdown'] is True
                and all(grading['cleanup'][k] is True for k in ('owned_processes_and_groups_absent', 'owned_containers_absent', 'owned_volumes_absent')), 'grading_unqualified')
        for actor in ('direct', 'child'):
            scope = grading['actual_checks']['scoped_io'][actor]
            require(scope['fixture_read'] is True and scope['task_write_readback'] is True
                    and all(scope['denied'][target][op] == 2 for target in
                        ('grading', 'other_arm', 'installer_receipt', 'installer_journal')
                        for op in ('read_errno', 'write_errno', 'create_errno')), 'grading_unqualified')
        require(collection['status'] == 'credential_free_collection_verified'
                and {r['case'] for r in collection['cases']} == {'present-missing', 'unsafe', 'interrupted'}
                and len(collection['cases']) == 3
                and all(r['expected_runtime_behavior_observed'] is True
                        and r['cleanup_and_fixture_root_absent'] is True
                        and r['independent_process_groups_containers_volumes_control_absent'] is True
                        for r in collection['cases']), 'collection_unqualified')
    except (OSError, ValueError, KeyError, TypeError):
        context.qualification_error = 'qualification_unavailable'
    return context


def _one(records, name):
    require(len(records.get(name, [])) == 1, 'journal_cardinality')
    return records[name][0]


def _usage(observation, records):
    """Unknown is not zero; only consistent persisted cumulative observations count."""
    try:
        usage, snapshots = observation['usage'], records.get('usage_snapshot', [])
        require(1 <= len(snapshots) <= 65 and same(snapshots[-1], usage['latest'])
                and same(snapshots[0], usage['first']) and usage['all_changed_snapshots_persisted'] is True,
                'usage_unavailable')
        previous = None
        for snapshot in snapshots:
            total = snapshot['total']
            require(set(total) == set(native_usage.FIELDS) and
                    all(type(v) is int and 0 <= v <= native_usage.MAX_INT for v in total.values())
                    and all(snapshot['presence']['total'][k] is True for k in native_usage.FIELDS)
                    and snapshot['cumulative_discontinuity'] is False
                    and (previous is None or all(total[k] >= previous[k] for k in native_usage.FIELDS)), 'usage_unavailable')
            previous = total
        return copy.deepcopy(previous)
    except (KeyError, TypeError, ValueError):
        return None


class NativeBatch:
    def __init__(self, context):
        self.context, self.rows, self.attempts, self.locks = context, [], [], []
        self.guard = Guard()
        self.seal, self.closed = None, False
        self.execution = self.execution_lease = self.execution_guard = None
        self.execution_error = False

    def close(self):
        for fd in reversed(self.locks):
            os.close(fd)
        self.locks.clear()
        if self.execution_lease is not None:
            self.execution_lease.close()
        self.closed = True

    @staticmethod
    def grader_identity():
        return native_grader_identity()

    def valid(self, experiment, spec):
        return (not self.closed and same(experiment, self.context.experiment) and same(spec, self.context.spec)
                and self.seal == ev.digest([self.rows, self.attempts, self.execution])
                and self.context.digest == ev.digest(self.context.data)
                and self.context.guard.check() and self.guard.check() and not self.execution_error
                and (self.execution_lease is None or (self.execution_lease.check()
                     and self.execution_guard.check())))

    def observed_models_complete(self):
        expected = {t['trial_id'] for t in self.context.experiment['trials']}
        return (self.context.qualification_error is None and len(self.rows) == len(expected)
                and {r['trial_id'] for r in self.rows} == expected and self.valid(self.context.experiment, self.context.spec)
                and all(r['status'] == 'completed' and i.get('observed_client_model') == self.context.spec['runtime']['model']
                        for r, i in zip(self.rows, self.attempts)))

    def usage(self, rows, missing):
        selected = {ev.digest(r) for r in rows}
        attempts = {}
        for row, info in zip(self.rows, self.attempts):
            if ev.digest(row) in selected:
                attempts.setdefault(info['key'], []).append(info)
        known, unknown = [], missing
        for group in attempts.values():
            counters = [g['counters'] for g in group]
            if (counters[0] is not None and all(same(counters[0], c) for c in counters)
                    and len({(g['manifest_digest'], g['receipt_digest']) for g in group}) == 1):
                known.append(counters[0]['totalTokens'])
            else:
                unknown += 1
        return {'known_tokens': sum(known), 'known_records': len(known), 'unknown': unknown,
                'total_tokens': sum(known) if unknown == 0 else None, 'currency_amount': None,
                'currency_reason': 'not_observed', 'attempts': len(attempts),
                'submissions': len(rows), 'wire_requests': None, 'billing_usage': None}


def bind_manifest(ctx, manifest):
    identity = manifest['identity']
    selected = trial_dispatch.prepare(ctx.experiment, ctx.spec, identity['trial_id'], identity['attempt_id'])
    trial = selected['binding']['trial']
    require(same(identity, {**trial, 'attempt_id': identity['attempt_id'], 'experiment_digest': ctx.experiment['experiment_digest']})
            and manifest['mode'] == 'trial', 'trial_binding')
    arm = ctx.data['arms'][trial['arm']]
    inputs = selected['executor_input']
    files = [{'kind': 'case', 'path': name, 'sha256': hashlib.sha256(value.encode()).hexdigest()} for name, value in sorted(inputs['files'].items())]
    files += [dict(f, kind='bundle') for f in arm['files']]
    routed = 'routing' in arm
    natural = routed and arm['routing']['mode'] == 'natural'
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == (2 if routed else 1)
            and ('routing' in manifest) == routed
            and same(manifest.get('routing'), arm.get('routing'))
            and ev.keys(manifest['inputs'], 'root files' if natural else 'root entrypoint files')
            and (natural or manifest['inputs']['entrypoint'] == arm['entrypoint'])
            and manifest['prompt'] == inputs['request']
            and sorted(manifest['inputs']['files'], key=lambda f: (f['kind'], f['path'])) == sorted(files, key=lambda f: (f['kind'], f['path']))
            and len(files) <= p.MAX_FILES and sum(len(v.encode()) for v in inputs['files'].values())
                + sum(ctx.guard.files[Path(arm['root']) / r['path']][1][5] for r in arm['files']) <= p.MAX_INPUT_BYTES, 'input_binding')
    require(same(manifest['collection'], ctx.data['collection_by_trial'][identity['trial_id']]), 'collection_binding')
    if 'execution_root' in ctx.data:
        require(manifest['state_root'] == ctx.data['execution_root'], 'execution_root')
    return trial, files


def cleanup_complete(cleanup):
    return (cleanup['complete'] is True and cleanup['processes_stopped'] is True
            and cleanup['control_absent'] is True and cleanup['volume_absent'] is True
            and cleanup['native_home']['home_absent'] is True and cleanup['native_home']['auth_absent'] is True
            and cleanup['process_query_uncertain'] is False and cleanup['watch_uncertain'] is False
            and cleanup.get('protected_synthetic_files_unchanged_after_shutdown') in (None, True))


def _read_attempt(batch, ref, row, info, *, cost_only=False, expected_manifest_digest=None, expected_limits=None):
    ctx, guard = batch.context, batch.guard
    path = p.absolute(ref['attempt_path'], 'attempt_path')
    guard.directory(path)
    lock = os.open(path / 'coordinator.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == 0o600, 'coordinator_lock')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(lock); raise
    batch.locks.append(lock)
    manifest = guard.json(path / 'manifest.json', private=True)
    identity, rt = manifest['identity'], ctx.data['runtime']
    require(expected_manifest_digest is None or p.digest(manifest) == expected_manifest_digest, 'reserved_manifest_changed')
    require(expected_limits is None or same(manifest['limits'], expected_limits), 'reservation_limits')
    require(identity['trial_id'] == ref['trial_id'] and identity['attempt_id'] == ref['attempt_id']
            and path == Path(manifest['state_root']) / ref['trial_id'] / ref['attempt_id'], 'attempt_binding')
    require(manifest['sources'] == rt['source_digests'] and manifest['profile'] == rt['profile']
            and manifest['runtime']['hashes'] == rt['runtime_digests']
            and manifest['runtime']['image'] == rt['image_digest']
            and manifest['runtime']['metadata_digest'] == rt['metadata_digest'], 'runtime_binding')
    for name, expected in rt['runtime_digests'].items():
        p.relative(Path(manifest['runtime'][name]).name)  # Never admit credential filenames.
        require(guard.read(manifest['runtime'][name], 512 * 1024**2, retain=False, owner=False)[1] == expected, 'runtime_changed')
    folder = path / 'records'; guard.directory(folder, names=True)
    require(type(manifest['limits']['retained_bytes']) is int
            and 65536 <= manifest['limits']['retained_bytes'] <= 262144, 'record_limit')
    _, records = nt.Journal.resume(folder, manifest['limits']['retained_bytes'])
    ordered = sorted(folder.iterdir())
    for record in ordered:
        guard.read(record, 65536, private=True)
    receipt = _one(records, 'receipt')
    digest = p.digest(manifest)
    require(receipt['manifest_digest'] == digest and same(receipt['identity'], identity)
            and same(_one(records, 'frozen_binding'), {'manifest_digest': digest, 'identity': identity, 'profile': rt['profile']}), 'receipt_binding')
    observation, cleanup = _one(records, 'observation'), _one(records, 'cleanup')
    if 'routing' in manifest:
        observation = _one(records, 'observation_finalized')
        require(same(observation['routing_observation'], _one(records, 'routing_observation')), 'routing_capture')
        labels = [f.name.split('-', 1)[1][:-5] for f in ordered]
        sequence = ['observation', 'cleanup', 'routing_observation', 'observation_finalized', 'receipt']
        require(all(labels.count(k) == 1 for k in sequence) and
                [labels.index(k) for k in sequence] == sorted(labels.index(k) for k in sequence), 'finalization_order')
    require(same(observation, receipt['observation']) and same(cleanup, receipt['cleanup'])
            and same(receipt['source_digests'], rt['source_digests'])
            and same(receipt['runtime_digests'], rt['runtime_digests'])
            and receipt['image_digest'] == rt['image_digest'], 'receipt_changed')
    info.update(manifest_digest=digest, receipt_digest=guard.files[path / 'records' / next(f.name for f in ordered if f.name.endswith('-receipt.json'))][0],
                counters=_usage(observation, records),
                initial_turn_requests_attempted=observation.get('initial_turn_requests_attempted')
                    if type(observation.get('initial_turn_requests_attempted')) is int
                    and observation['initial_turn_requests_attempted'] in (0, 1) else None)
    trial, files = bind_manifest(ctx, manifest)
    require(receipt['mode'] == 'trial', 'trial_binding')
    row['binding_digest'] = trial['binding_digest']
    observed_model = model_selection(observation['model_selection'], ctx.spec['runtime']['model']) if 'model_selection' in observation else None
    require('routing' not in manifest or observed_model is not None, 'model_selection_unavailable')
    boundary = _one(records, 'executor_boundary')
    for kind in ('case', 'bundle'):
        expected = p.digest([{'path': f['path'], 'sha256': f['sha256']} for f in files if f['kind'] == kind])
        require(boundary[kind + '_digest'] == expected, 'materialization_binding')
    require(boundary['docker_settings_verified'] is True and boundary['arm_inventory_exact'] is True
            and boundary['arm_write_errno'] in (13, 30) and boundary['mount_write_errno'] == 30
            and boundary['uid'] == 65532 and boundary['cap_eff'] == '0000000000000000'
            and boundary['no_new_privs'] == '1' and boundary['seccomp'] == '2'
            and boundary['loopback_only'] is True and boundary['runtime_digest'] == nt.EXECUTOR_SHA256, 'boundary_unverified')
    if cost_only:
        labels = [f.name.split('-', 1)[1][:-5] for f in ordered]
        sequence = ['native_launch_complete', 'observation', 'cleanup', 'receipt']
        require(all(labels.count(k) == 1 for k in sequence)
                and [labels.index(k) for k in sequence] == sorted(labels.index(k) for k in sequence), 'cost_order')
        info['cost_bound'] = True
        info['complete'] = (observation['status'] == 'completed_ungraded'
            and observation['terminal_completed'] is True and observation['reason'] is None
            and type(observation['initial_turns']) is int and observation['initial_turns'] == 1
            and info['initial_turn_requests_attempted'] == 1 and observation['usage']['stop'] is None
            and observation['model_requested'] == ctx.spec['runtime']['model']
            and observation['auth_chatgpt_observed'] is True and cleanup_complete(cleanup)
            and receipt['protected_synthetic_files_unchanged'] in (None, True))
        return
    declaration = ctx.data['collection_by_trial'][ref['trial_id']]
    collection = _one(records, 'collection_result')
    require(same(manifest['collection'], declaration) and same(collection, receipt['collection'])
            and collection['manifest_digest'] == digest and collection['collection_digest'] == p.digest(declaration)
            and collection['collector_source_digest'] == rt['source_digests']['native_trial_results.py']
            and same(_one(records, 'collection_intent'), {'collection_digest': p.digest(declaration)}), 'collection_binding')
    owners = [r for r in records.get('container_owner', []) if r.get('kind') == 'executor']
    require(len(owners) == 1 and owners[0]['id'] == collection['container_id']
            and owners[0]['name'] == nt.resource_names(identity)['executor'], 'container_binding')
    labels = [f.name.split('-', 1)[1][:-5] for f in ordered]
    sequence = ['native_launch_complete', 'observation', 'collection_intent', 'collection_result', 'cleanup', 'receipt']
    require(all(labels.count(k) == 1 for k in sequence) and [labels.index(k) for k in sequence] == sorted(labels.index(k) for k in sequence), 'collection_order')
    require(ctx.qualification_error is None, 'qualification_unavailable')
    require(receipt['status'] == 'completed_ungraded' and receipt['capture_failed'] is False
            and observation['status'] == 'completed_ungraded' and observation['terminal_completed'] is True
            and observation['initial_turns'] == 1 and type(observation['initial_turns']) is int
            and observation['initial_turn_requests_attempted'] == 1 and observation['reason'] is None
            and observation['usage']['stop'] is None and observation['model_requested'] == ctx.spec['runtime']['model']
            and ctx.spec['runtime']['model'] == 'gpt-6-luna' and observation['auth_chatgpt_observed'] is True,
            'native_incomplete')
    require(cleanup_complete(cleanup) and receipt['protected_synthetic_files_unchanged'] in (None, True), 'cleanup_incomplete')
    require(info['counters'] is not None and collection['status'] == 'captured', 'collection_unavailable')
    snapshot = nt.validate_snapshot({'exit': 0, 'stop_reason': None, 'stderr': '', 'stdout': json.dumps(collection['snapshot'])}, declaration)
    require(snapshot['status'] == 'captured', 'collection_unavailable')
    projection = {}
    if 'routing' in manifest:
        projection = routing_projection(observation['routing_observation'], manifest['routing'], nt.routing_profile_digest(manifest))
    row.update(status='completed', artifacts={r['path']: r for r in snapshot['files']}, observations=projection)
    info.update(reason=None, observed_client_model=observed_model)


def read_cost_facts(context, row, guard):
    """Read bound attempt cost independently of artifact success; no lifecycle calls."""
    batch = NativeBatch(context)
    batch.guard = guard
    info = {}
    ref = {k: row[k] for k in ('trial_id', 'attempt_id')}
    ref['attempt_path'] = str(Path(context.data['execution_root']) / row['trial_id'] / row['attempt_id'])
    try:
        _read_attempt(batch, ref, {}, info, cost_only=True, expected_manifest_digest=row['manifest_digest'],
                      expected_limits=row['limits'])
        require(guard.check(), 'cost_changed')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        info['complete'] = False
    finally:
        batch.close()
    counters = info.get('counters') if info.get('cost_bound') else None
    return {'known_tokens': counters['totalTokens'] if counters is not None else None,
            'complete': info.get('complete') is True and counters is not None,
            'initial_turn_requests_attempted': info.get('initial_turn_requests_attempted'),
            'receipt_digest': info.get('receipt_digest')}


def read_attempts(context, refs):
    require(type(context) is NativeContext and isinstance(refs, list) and len(refs) <= 64, 'attempt_refs')
    batch = NativeBatch(context)
    try:
        if 'execution_root' in context.data:
            if __package__:
                from . import trial_reservation as reservation
            else:
                import trial_reservation as reservation
            try:
                batch.execution_lease = reservation.Lease(context)
                batch.execution, batch.execution_guard, _ = reservation.audit(batch.execution_lease)
            except (OSError, ValueError, KeyError, TypeError, RecursionError):
                batch.execution_error = True
                batch.execution = {'status': 'unavailable', 'total_tokens': None}
                if batch.execution_lease is not None:
                    batch.execution_lease.close()
                    batch.execution_lease = None
        cache = {}
        for ref in refs:
            require(ev.keys(ref, 'trial_id attempt_id attempt_path') and ev.sha(ref['trial_id']) and p.token(ref['attempt_id']), 'attempt_ref')
            row = {'trial_id': ref['trial_id'], 'attempt_id': ref['attempt_id'], 'experiment_digest': context.experiment['experiment_digest'], 'binding_digest': '',
                   'status': 'blocked', 'model': context.spec['runtime']['model'], 'evidence_kind': KIND,
                   'artifacts': {}, 'observations': {}, 'usage': None, 'latency_ms': None}
            info = {'key': ev.digest([ref['trial_id'], ref['attempt_id']]), 'attempt_id': ref['attempt_id'],
                    'manifest_digest': None, 'receipt_digest': None, 'counters': None,
                    'initial_turn_requests_attempted': None, 'reason': 'attempt_unavailable'}
            key = ev.digest(ref)
            if key in cache:
                previous_row, previous_info = cache[key]
                batch.rows.append(copy.deepcopy(previous_row)); batch.attempts.append(copy.deepcopy(previous_info))
                continue
            try:
                _read_attempt(batch, ref, row, info)
            except (OSError, ValueError, KeyError, TypeError, RecursionError):
                pass  # Closed blocked projection; never expose paths or raw error strings.
            batch.rows.append(row); batch.attempts.append(info)
            cache[key] = (row, info)
        batch.seal = ev.digest([batch.rows, batch.attempts, batch.execution])
        return batch
    except BaseException:
        batch.close(); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('report',)); parser.parse_args()
    batch = None
    try:
        raw = sys.stdin.buffer.read(ev.MAX_BYTES + 1); require(len(raw) <= ev.MAX_BYTES, 'input_limit')
        data = json.loads(raw, object_pairs_hook=ev.no_duplicates)
        require(ev.keys(data, 'experiment current_spec context_path attempts'), 'report_fields')
        ctx = load_context(data['experiment'], data['current_spec'], data['context_path'])
        batch = read_attempts(ctx, data['attempts'])
        sys.stdout.buffer.write(ev.encoded(ev.compare(data['experiment'], [], data['current_spec'], native=batch)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print('{"status":"rejected","reason":"invalid_admission_input"}'); return 1
    finally:
        if batch is not None: batch.close()


if __name__ == '__main__':
    raise SystemExit(main())
