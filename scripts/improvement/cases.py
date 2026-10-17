#!/usr/bin/env python3
"""Prepare, explicitly review and locally export synthetic development cases."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from account.observation.files import BusyStore
from account.observation.store import TASK_INPUT_LIMIT, InvalidEvent, Store, decode, require


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--home', type=Path, required=True)
    commands = result.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'show', 'review', 'export'):
        command = commands.add_parser(name)
        command.add_argument('--task', required=True)
        if name != 'prepare':
            command.add_argument('--case', dest='case_id', required=True)
        if name in {'review', 'export'}:
            command.add_argument('--digest', required=True)
        if name == 'review':
            command.add_argument('--reviewer', required=True)
            command.add_argument('--confirm-synthetic', action='store_true')
            command.add_argument('--confirm-privacy-review', action='store_true')
        if name == 'export':
            command.add_argument('--output', type=Path, required=True,
                                 help='New absolute output filename in an existing directory; no overwrite')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.version_info < (3, 11):
        print('{"status":"error","reason":"python_3_11_required"}', file=sys.stderr)
        return 1
    try:
        store = Store(args.home)
        if args.command == 'prepare':
            raw = sys.stdin.buffer.read(TASK_INPUT_LIMIT + 1)
            require(len(raw) <= TASK_INPUT_LIMIT, 'case_size')
            body = decode(raw)
            require(isinstance(body, dict) and set(body) == {
                'revision_id', 'feedback_ids', 'synthetic_case', 'request_id'}, 'case_input_fields')
            output = store.prepare_case(args.task, **body)
        elif args.command == 'show':
            output = store.case(args.task, args.case_id)
        elif args.command == 'review':
            output = store.review_case(args.task, args.case_id, expected_digest=args.digest,
                                      reviewer=args.reviewer, synthetic_data_confirmed=args.confirm_synthetic,
                                      privacy_reviewed=args.confirm_privacy_review)
        else:
            output = store.export_case(args.task, args.case_id, expected_digest=args.digest,
                                      destination=args.output)
    except InvalidEvent as error:
        output = dict(status='rejected', reason=str(error))
    except BusyStore:
        output = dict(status='busy', reason='store_busy')
    except FileExistsError:
        output = dict(status='rejected', reason='export_exists')
    except FileNotFoundError:
        output = dict(status='rejected', reason='not_found')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        output = dict(status='error', reason='operation_failed')
    print(json.dumps(output, sort_keys=True, allow_nan=False))
    return 1 if output['status'] in {'rejected', 'error', 'busy', 'insufficient'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
