#!/usr/bin/env python3
"""Manual synthetic observation qualification. Does not register native hooks."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from account.observation.store import BATCH_LIMIT, EVENT_LIMIT, Store


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--home', type=Path, required=True,
                        help='Explicit existing account home (use a disposable directory for qualification)')
    commands = result.add_subparsers(dest='command', required=True)
    grant = commands.add_parser('grant', help='Opt one exact synthetic project/profile/source into collection')
    grant.add_argument('--project', type=Path, required=True)
    grant.add_argument('--profile', default='default')
    grant.add_argument('--source', default='fixture-v1', help='Synthetic stream identity including its generation')
    grant.add_argument('--start-after', required=True, type=int, help='Current source sequence high-water mark')
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
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.version_info < (3, 11):
        print('{"status":"error","reason":"python_3_11_required"}', file=sys.stderr)
        return 1
    try:
        store = Store(args.home)
        if args.command == 'grant':
            output = store.grant(args.project, profile=args.profile, source=args.source,
                                 start_after=args.start_after, lifetime_seconds=args.lifetime_seconds)
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
        else:
            output = {'purged_registrations': store.prune()}
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 1 if output.get('status') in {'error', 'rejected', 'busy'} else 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print('{"status":"error","reason":"operation_failed"}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
