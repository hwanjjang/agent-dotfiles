#!/bin/sh
# Host-neutral entry point: select a local Python >=3.11; never download a runtime.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${AGENT_DOTFILES_PYTHON:-}" ]; then
    "$AGENT_DOTFILES_PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' || {
        echo 'AGENT_DOTFILES_PYTHON must select Python 3.11 or newer.' >&2; exit 2;
    }
    exec "$AGENT_DOTFILES_PYTHON" "$script_dir/setup_account.py" "$@"
fi
for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
        exec "$candidate" "$script_dir/setup_account.py" "$@"
    fi
done
echo 'Install Python 3.11+ and Git, then rerun setup-account.sh.' >&2
exit 2
