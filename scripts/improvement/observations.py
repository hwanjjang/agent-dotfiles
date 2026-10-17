#!/usr/bin/env python3
"""Manage private observation grants and synthetic imports; never registers hooks."""
import argparse
import json
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from account.observation.store import BATCH_LIMIT, EVENT_LIMIT, TASK_INPUT_LIMIT, InvalidEvent, Store, decode, require
from account.observation.files import BusyStore


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--home', type=Path, required=True,
                        help='Explicit existing account home (use a disposable directory for qualification)')
    commands = result.add_subparsers(dest='command', required=True)
    grant = commands.add_parser('grant', help='Opt one exact project/client/profile/source into collection')
    grant.add_argument('--project', type=Path, required=True)
    grant.add_argument('--client', choices=('synthetic', 'claude'), default='synthetic')
    grant.add_argument('--profile', default='default')
    grant.add_argument('--source', help='Synthetic stream generation; native Claude uses claude-hooks-v1')
    grant.add_argument('--start-after', type=int, help='Required synthetic source high-water mark; native receipt order is automatic')
    grant.add_argument('--lifetime-seconds', type=int, default=2592000)
    for name in ('capture', 'import', 'events', 'revoke'):
        command = commands.add_parser(name)
        command.add_argument('--registration', required=True)
        if name in ('capture', 'import'):
            command.add_argument('--epoch', required=True)
        if name == 'import':
            command.add_argument('--offset', type=int, required=True)
    commands.add_parser('rebuild-index')
    commands.add_parser('prune')
    commands.add_parser('task-bind', help='Bind explicit event selections; bounded JSON on stdin')
    for name in ('feedback-add', 'task-show'):
        command = commands.add_parser(name)
        command.add_argument('--task', required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.version_info < (3, 11):
        print('{"status":"error","reason":"python_3_11_required"}', file=sys.stderr)
        return 1
    try:
        store = Store(args.home)
        if args.command == 'grant':
            if args.client == 'synthetic' and args.start_after is None:
                raise InvalidEvent('source_high_water_required')
            if args.client != 'synthetic' and args.start_after is not None:
                raise InvalidEvent('native_sequence_is_automatic')
            source = args.source or ('fixture-v1' if args.client == 'synthetic' else 'claude-hooks-v1')
            output = store.grant(args.project, profile=args.profile, source=source,
                                 start_after=args.start_after or 0, lifetime_seconds=args.lifetime_seconds,
                                 client=args.client)
        elif args.command == 'capture':
            output = store.capture(args.registration, args.epoch, sys.stdin.buffer.read(EVENT_LIMIT + 1))
        elif args.command == 'import':
            output = store.import_batch(args.registration, args.epoch, args.offset,
                                        sys.stdin.buffer.read(BATCH_LIMIT + 1))
        elif args.command == 'events':
            output = {'events': store.events(args.registration)}
        elif args.command == 'revoke':
            output = store.revoke(args.registration)
        elif args.command == 'rebuild-index':
            output = {'indexed_events': store.rebuild_index()}
        elif args.command in {'task-bind', 'feedback-add'}:
            raw = sys.stdin.buffer.read(TASK_INPUT_LIMIT + 1)
            require(len(raw) <= TASK_INPUT_LIMIT, 'task_input_size')
            body = decode(raw)
            allowed = ({'selections', 'goal', 'request_id', 'task_id'} if args.command == 'task-bind'
                       else {'symptom', 'correction', 'evidence_ids', 'contrary_evidence_ids',
                             'suspected_cause', 'confidence', 'author', 'request_id', 'revision_id'})
            required = {'selections', 'goal', 'request_id'} if args.command == 'task-bind' else {'symptom', 'request_id'}
            require(isinstance(body, dict) and required <= set(body) <= allowed, 'task_input_fields')
            output = store.bind_task(**body) if args.command == 'task-bind' else store.add_feedback(args.task, **body)
        elif args.command == 'task-show':
            output = store.task(args.task)
        else:
            output = {'purged_registrations': store.prune()}
    except InvalidEvent as error:
        output = {'status': 'rejected', 'reason': str(error)}
    except BusyStore:
        output = {'status': 'busy', 'reason': 'store_busy'}
    except FileNotFoundError:
        output = {'status': 'rejected', 'reason': 'not_found'}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, sqlite3.Error):
        output = {'status': 'error', 'reason': 'operation_failed'}
    try:
        message = json.dumps(output, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        output = {'status': 'error', 'reason': 'operation_failed'}
        message = json.dumps(output, sort_keys=True)
    print(message)
    return 1 if output.get('status') in {'error', 'rejected', 'busy'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
