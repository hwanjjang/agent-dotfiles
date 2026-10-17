#!/usr/bin/env python3
"""POSIX account dispatcher, delivered as ~/.agents/bin/planning-hook.py.

AK-authored source adapted under the repository MIT license. Runtime files are
separate pinned upstream assets; this entry point does not install anything.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


CODEX_ROUTES = {
    ("run_sh.py", "session-start.sh"),
    ("run_sh.py", "user-prompt-submit.sh"),
    ("run_sh.py", "pre-compact.sh"),
    ("pre_tool_use.py",),
    ("post_tool_use.py",),
    ("permission_request.py",),
    ("stop.py",),
}
EVENTS = dict(zip(
    [("run_sh.py", "session-start.sh"), ("run_sh.py", "user-prompt-submit.sh"),
     ("run_sh.py", "pre-compact.sh"), ("pre_tool_use.py",), ("post_tool_use.py",),
     ("permission_request.py",), ("stop.py",)],
    ["SessionStart", "UserPromptSubmit", "PreCompact", "PreToolUse", "PostToolUse",
     "PermissionRequest", "Stop"],
))


def project_owns_route(project, host, args):
    if host == "codex":
        # Match the established standalone planning route, not any hook file.
        config = project / ".codex/hooks.json"
        runtime = project / ".codex/hooks/run_sh.py"
        if not config.is_file() or not runtime.is_file():
            return False
        data = json.loads(config.read_text())
        return any(
            ".codex/hooks/" in hook.get("command", "")
            and all(part in hook.get("command", "") for part in args)
            for group in data.get("hooks", {}).get(EVENTS[tuple(args)], [])
            for hook in group.get("hooks", [])
        )
    config = project / ".claude/settings.json"
    if not config.is_file():
        return False
    data = json.loads(config.read_text())
    return any(
        "planning-with-files.sh" in hook.get("command", "")
        for group in data.get("hooks", {}).get("SessionStart", [])
        for hook in group.get("hooks", [])
    )


def main():
    if os.environ.get("PLANNING_DISABLED") == "1":
        return 0
    location = Path(__file__).resolve()
    if location.parent.name != "bin" or location.parent.parent.name != ".agents":
        raise ValueError("Dispatcher requires the documented delivery layout")
    home = location.parents[2]
    if not sys.argv[1:]:
        raise ValueError("Missing host")
    host, *args = sys.argv[1:]
    if not ((host == "codex" and tuple(args) in CODEX_ROUTES)
            or (host == "claude" and args == ["session-start"])):
        raise ValueError("Unsupported hook route")
    raw = sys.stdin.buffer.read()
    payload = json.loads(raw or b"{}")
    if not isinstance(payload, dict):
        raise ValueError("Hook payload must be an object")
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project = Path(cwd).resolve()
    if project_owns_route(project, host, args):
        return 0
    env = os.environ.copy()
    if host == "codex":
        command = [sys.executable, str(home / ".codex/hooks" / args[0]), *args[1:]]
    else:
        command = ["sh", str(home / ".claude/hooks/planning-with-files-dispatch.sh"), "session-start"]
        env["CLAUDE_PLUGIN_ROOT"] = str(home / ".agents/skills/planning-with-files")
    return subprocess.run(command, input=raw, cwd=project, env=env, check=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, AttributeError) as error:
        # Do not expose payloads, account paths or configuration values.
        print(f"Planning hook unavailable: {type(error).__name__}", file=sys.stderr)
        sys.exit(0)
