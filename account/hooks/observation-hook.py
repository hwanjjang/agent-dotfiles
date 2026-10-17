#!/usr/bin/env python3
"""Delivered observation callback: bounded local metadata, client-neutral output."""
from pathlib import Path
import signal
import sys


def deadline(*_):
    raise TimeoutError('observation_deadline')


def main():
    # Old Claude invocations keep their silent three-argument contract. Codex
    # needs neutral JSON even if consent/input fails before the event is read.
    codex = len(sys.argv) == 4 and sys.argv[3] == 'codex'
    sys.dont_write_bytecode = True
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(3)
    try:
        location = Path(__file__).resolve()
        if location.parent.name != 'bin' or location.parent.parent.name != '.agents' or not (len(sys.argv) == 3 or codex):
            return 0
        home = location.parents[2]
        sys.path.insert(0, str(home / '.agents/agent-dotfiles/bundle'))
        from account.observation.store import Store
        Store(home).capture_native(sys.argv[1], sys.argv[2], sys.stdin.buffer)
    except Exception:
        # Callback failures never inject model instructions or change permissions.
        pass
    finally:
        signal.alarm(0)
        if codex:
            print('{}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
