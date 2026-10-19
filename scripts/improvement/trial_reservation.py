#!/usr/bin/env python3
"""Cooperating trusted-host serial launch gate; no provider hard-cap guarantee."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import stat
import sys

if __package__:
    from . import trial_admission as ad
else:
    sys.modules.setdefault('trial_reservation', sys.modules[__name__])
    import trial_admission as ad
p, nt, ev = ad.p, ad.nt, ad.ev
require, same = ad.require, ad.same
CONTINUATION = 'independent_after_no_turn_v1'
HEADER, RECORDS, LOCK = 'experiment-reservation.json', 'experiment-records', 'experiment.lock'


def context(root, experiment, current_spec, context_path):
    ctx = ad.load_context(experiment, current_spec, context_path)
    require(ctx.data.get('execution_root') == str(p.absolute(str(root), 'execution_root')),
            'execution_root')
    require(ctx.guard.check(), 'context_changed')
    return ctx


class Lease:
    """One non-inheritable stable lock, always acquired before native attempt locks."""
    def __init__(self, ctx, *, create=False):
        self.ctx, self.fd, self.folder = ctx, None, None
        self.root, self.guard = Path(ctx.data['execution_root']), ad.Guard()
        try:
            self.guard.directory(self.root)
            self.folder = p.directory(self.root)
            if create:
                require(not list(os.scandir(self.folder)), 'experiment_exists')
            self.fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK |
                              (os.O_CREAT | os.O_EXCL if create else 0), 0o600, dir_fd=self.folder)
            info = os.fstat(self.fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                    'experiment_lock')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.guard.read(self.root / LOCK, 0, private=True)
            require(p.stamp(info) == p.stamp(os.stat(LOCK, dir_fd=self.folder,
                                                   follow_symlinks=False)), 'experiment_lock')
            if not create:
                self.header = self.guard.json(self.root / HEADER, private=True)
                self.validate_header()
        except BaseException:
            self.close()
            raise

    def close(self):
        for key in ('fd', 'folder'):
            fd = getattr(self, key, None)
            if fd is not None:
                os.close(fd)
                setattr(self, key, None)

    def check(self):
        try:
            return (self.fd is not None and self.ctx.guard.check() and self.guard.check()
                    and p.stamp(os.fstat(self.fd)) == p.stamp(os.stat(
                        LOCK, dir_fd=self.folder, follow_symlinks=False)))
        except (OSError, ValueError):
            return False

    def validate_header(self):
        h, ctx = self.header, self.ctx
        fields = 'schema_version kind experiment_digest spec_digest budget_digest context_digest root_identity lock_identity schedule'
        require(ev.keys(h, fields + (' continuation_policy' if 'continuation_policy' in h else ''))
                and ('continuation_policy' not in h or h['continuation_policy'] == CONTINUATION)
                and type(h['schema_version']) is int and h['schema_version'] == 1
                and h['kind'] == 'serial_native_reservation_v1'
                and h['experiment_digest'] == ctx.experiment['experiment_digest']
                and h['spec_digest'] == ctx.experiment['spec_digest']
                and h['budget_digest'] == ev.digest(ctx.spec['budget'])
                and h['context_digest'] == ctx.digest
                and h['root_identity'] == list(self.guard.dirs[self.root][:3])
                and h['lock_identity'] == [os.fstat(self.fd).st_dev, os.fstat(self.fd).st_ino, os.fstat(self.fd).st_uid], 'reservation_binding')
        rows = h['schedule']
        require(isinstance(rows, list) and 1 <= len(rows) <= 64
                and len(rows) == len(ctx.experiment['trials']), 'reservation_schedule')
        for row, trial in zip(rows, ctx.experiment['trials']):
            require(ev.keys(row, 'trial_id attempt_id manifest_digest limits')
                    and row['trial_id'] == trial['trial_id'] and p.token(row['attempt_id'])
                    and p.is_digest(row['manifest_digest']), 'reservation_schedule')
            p.fields(row['limits'], ' '.join(p.LIMITS), 'reservation_limits')
            require(all(type(v) is int and 0 < v <= p.LIMITS[k]
                        for k, v in row['limits'].items())
                    and row['limits']['retained_bytes'] >= 65536, 'reservation_limits')
        require(self.check(), 'reservation_changed')


def selected(ctx, path):
    selected = p.load_plan(Path(path))
    data, rt = selected.data, ctx.data['runtime']
    ad.bind_manifest(ctx, data)
    require(data['sources'] == rt['source_digests'] and data['profile'] == rt['profile']
            and data['runtime']['hashes'] == rt['runtime_digests']
            and data['runtime']['image'] == rt['image_digest']
            and data['runtime']['metadata_digest'] == rt['metadata_digest'], 'runtime_binding')
    return selected


def reserve_record(header, index):
    row = header['schedule'][index]
    return {'index': index, 'header_digest': ev.digest(header),
            **{k: row[k] for k in ('trial_id', 'attempt_id', 'manifest_digest')}}


def audit(lease):
    """Read every reservation, even when caller completion refs omit attempts."""
    lease.validate_header()
    root, header, ctx, guard = lease.root, lease.header, lease.ctx, ad.Guard()
    guard.directory(root, names=True)
    folder = root / RECORDS
    guard.directory(folder, names=True)
    journal, records = nt.Journal.resume(folder, 262144)
    require(not (set(records) - {'reserve'}), 'reservation_records')
    prefix = records.get('reserve', [])
    require(len(prefix) <= len(header['schedule']), 'reservation_records')
    for file in sorted(folder.iterdir()):
        guard.read(file, 65536, private=True)
    rows = header['schedule'][:len(prefix)]
    allowed = {HEADER, RECORDS, LOCK} | {row['trial_id'] for row in rows}
    require(set(os.listdir(root)) <= allowed, 'unreserved_attempt')
    facts = []
    for index, row in enumerate(rows):
        require(same(prefix[index], reserve_record(header, index)), 'reservation_records')
        trial_dir = root / row['trial_id']
        if trial_dir.exists():
            guard.directory(trial_dir, names=True)
            require(set(os.listdir(trial_dir)) == {row['attempt_id']}, 'unreserved_attempt')
        facts.append(ad.read_cost_facts(ctx, row, guard))
    known = sum(f['known_tokens'] for f in facts if f['known_tokens'] is not None)
    unknown = sum(not f['complete'] for f in facts)
    continuation = header.get('continuation_policy') == CONTINUATION
    resumable = all(f['complete'] or f['no_turn_cleanup_verified'] for f in facts)
    # Admission allowances are not observed/billed usage or provider hard caps.
    admission = sum(max(f['known_tokens'] or 0, row['limits']['soft_total_tokens'])
                    if not f['complete'] else f['known_tokens']
                    for row, f in zip(rows, facts))
    seconds = sum(sum(row['limits'][k] for k in ('setup_seconds', 'wall_seconds', 'cleanup_seconds')) for row in rows)
    exceeded = (len(rows) > ctx.spec['budget']['model_requests'] or seconds > ctx.spec['budget']['seconds']
                or known > ctx.spec['budget']['tokens']
                or (continuation and admission > ctx.spec['budget']['tokens'])
                or any(f['known_tokens'] is not None and f['known_tokens'] > row['limits']['soft_total_tokens']
                       for row, f in zip(rows, facts)))
    require(lease.check() and guard.check(), 'reservation_changed')
    summary = {'status': 'blocked' if unknown or exceeded else 'complete' if len(rows) == len(header['schedule']) else 'ready',
               'next_launch_allowed': (not exceeded and len(rows) < len(header['schedule'])
                                       and (unknown == 0 or (continuation and resumable))),
               'continuation_policy': header.get('continuation_policy'),
               'admission_tokens': admission,
               'scheduled': len(header['schedule']), 'reserved_initial_turns': len(rows),
               'declared_seconds': seconds, 'known_tokens': known, 'unknown_attempts': unknown,
               'total_tokens': None if unknown else known, 'limits_exceeded': exceeded,
               'initial_turn_requests_attempted': [f['initial_turn_requests_attempted'] for f in facts],
               'wire_requests': None, 'billing_usage': None, 'currency_amount': None,
               'hard_provider_cap': False, 'backend_identity_verified': False,
               'live_eligible': False}
    return summary, guard, journal


def initialize(root, experiment, current_spec, context_path, plan_paths, *, continue_after_no_turn=False):
    require(type(continue_after_no_turn) is bool, 'continuation_policy')
    ctx = context(root, experiment, current_spec, context_path)
    require(ctx.qualification_error is None, 'qualification_unavailable')
    require(isinstance(plan_paths, list) and 1 <= len(plan_paths) <= 64
            and len(plan_paths) == len(ctx.experiment['trials']), 'reservation_schedule')
    plans = [selected(ctx, path) for path in plan_paths]
    schedule = []
    for value, trial in zip(plans, ctx.experiment['trials']):
        data = value.data
        require(data['identity']['trial_id'] == trial['trial_id'], 'reservation_order')
        schedule.append({**{k: data['identity'][k] for k in ('trial_id', 'attempt_id')},
                         'manifest_digest': value.digest, 'limits': data['limits']})
    lease = Lease(ctx, create=True)
    try:
        lease.header = {'schema_version': 1, 'kind': 'serial_native_reservation_v1',
                        'experiment_digest': ctx.experiment['experiment_digest'],
                        'spec_digest': ctx.experiment['spec_digest'], 'budget_digest': ev.digest(ctx.spec['budget']),
                        'context_digest': ctx.digest, 'root_identity': list(lease.guard.dirs[lease.root][:3]),
                        'lock_identity': [os.fstat(lease.fd).st_dev, os.fstat(lease.fd).st_ino, os.fstat(lease.fd).st_uid],
                        'schedule': schedule}
        if continue_after_no_turn:
            lease.header['continuation_policy'] = CONTINUATION
        require(lease.check(), 'reservation_changed')
        nt.Journal(lease.root / RECORDS, 262144)
        nt.private_write(lease.root / HEADER, p.encoded(lease.header) + b'\n')
        os.fsync(lease.folder)
        lease.guard.json(lease.root / HEADER, private=True)
        return audit(lease)[0]
    finally:
        lease.close()


def status(root, experiment, current_spec, context_path):
    lease = Lease(context(root, experiment, current_spec, context_path))
    try:
        return audit(lease)[0]
    finally:
        lease.close()


def run_next(root, experiment, current_spec, context_path, plan_path, auth_source):
    p.absolute(str(auth_source), 'auth_source_path')
    ctx = context(root, experiment, current_spec, context_path)
    require(ctx.qualification_error is None, 'qualification_unavailable')
    lease = Lease(ctx)
    try:
        summary, guard, journal = audit(lease)
        require(summary['next_launch_allowed'], 'experiment_blocked_or_complete')
        index = summary['reserved_initial_turns']
        expected = lease.header['schedule'][index]
        chosen = selected(ctx, plan_path)
        require(chosen.digest == expected['manifest_digest'] and same(chosen.data['limits'], expected['limits']), 'reservation_order')
        budget, limits = ctx.spec['budget'], expected['limits']
        seconds = sum(limits[k] for k in ('setup_seconds', 'wall_seconds', 'cleanup_seconds'))
        require(index + 1 <= budget['model_requests'] and summary['declared_seconds'] + seconds <= budget['seconds']
                and summary['admission_tokens'] + limits['soft_total_tokens'] <= budget['tokens'], 'aggregate_budget')
        require(lease.check() and guard.check(), 'reservation_changed')
        journal.save('reserve', reserve_record(lease.header, index))
        reserved, reserved_guard, _ = audit(lease)
        require(reserved['reserved_initial_turns'] == index + 1 and reserved_guard.check()
                and lease.check(), 'reservation_changed')
        # Reservation is durable before the only fixed launch boundary. No retry or refund.
        nt.run(Path(plan_path), auth_source=auth_source, expected_manifest_digest=chosen.digest)
        return audit(lease)[0]
    finally:
        lease.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('initialize', 'status', 'run-next'):
        command = sub.add_parser(name)
        command.add_argument('--root', required=True, type=Path)
        if name == 'initialize':
            command.add_argument('--continue-after-no-turn', action='store_true',
                                 help='Freeze opt-in independent-row continuation after verified startup RPC failure; no retry or success inference')
        if name == 'run-next':
            command.add_argument('--plan', required=True, type=Path)
            command.add_argument('--auth-source', required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(ev.MAX_BYTES + 1)
        require(len(raw) <= ev.MAX_BYTES, 'input_limit')
        data = json.loads(raw, object_pairs_hook=ev.no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ev.Invalid('invalid_number')))
        fields = 'experiment current_spec context_path' + (' plan_paths' if args.command == 'initialize' else '')
        require(ev.keys(data, fields), 'reservation_input')
        fn = {'initialize': initialize, 'status': status, 'run-next': run_next}[args.command]
        extra = {'plan_path': args.plan, 'auth_source': args.auth_source} if args.command == 'run-next' else {}
        if args.command == 'initialize':
            extra['continue_after_no_turn'] = args.continue_after_no_turn
        result = fn(args.root, **data, **extra)
        sys.stdout.buffer.write(ev.encoded(result))
        return 1 if result['status'] == 'blocked' else 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print('{"status":"refused","reason":"reservation_unavailable"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
