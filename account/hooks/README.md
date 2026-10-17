# Selected planning hook source

Purpose: retain selected-plan recovery and progress reminders without duplicate
project/account execution. These files are source assets, not active registrations.
The supplied account templates target POSIX Codex and Claude Code layouts. No
Windows, Hermes or plugin-mode account integration is claimed.

## Source layout and intended delivery

| Source | Destination relative to account home |
| --- | --- |
| `planning-hook.py` | `.agents/bin/planning-hook.py` |
| `planning-with-files/codex/*` | `.codex/hooks/*` |
| `planning-with-files/claude/dispatch.sh` | `.claude/hooks/planning-with-files-dispatch.sh` |
| Repository `skills/planning-with-files/` | `.agents/skills/planning-with-files/` |
| Link to that delivered skill | `.codex/skills/planning-with-files` and `.claude/skills/planning-with-files` |

Preserve the upstream [LICENSE](planning-with-files/LICENSE) with delivered runtime
assets. [Provenance](planning-with-files/provenance.json) records every selected
upstream file and hash. Shared skill code is not copied into this source directory.
The dispatcher is AK-authored MIT source, adapted with a fixed route allowlist,
payload validation, effective project working directory and child exit propagation.

`codex.example.json` and `claude.example.json` contain only proposed registrations.
A future installer must merge the selected entries into the client's hook settings,
resolve supported paths and interpreter, and remove only the replaced owned route.
Do not overwrite entire settings files or register both plugin and standalone hooks.
The dispatcher suppresses the recognized project route; it cannot discover every
third-party plugin registration. Inspect the client's effective hook list too.

Codex uses seven lifecycle events. Claude's account template supplies SessionStart
only; the adopted skill owns its activation-scoped hooks. Do not copy all plugin
events into account settings alongside those skill hooks. Both routes honor
`PLANNING_DISABLED=1`. Plan binding and recovery behavior remain owned by
[planning-with-files](../../skills/planning-with-files/SKILL.md).

Prerequisites: Python 3.9+, POSIX shell and the adopted skill's shell utilities.
Templates use `python3`; validate its actual interpreter on the destination.
The current templates assume default client directories; custom client homes need
an explicit adapter. Never change the real home to test this package.

## Verify before activation

Run the repository's isolated tests with
`python3 -m unittest discover -s tests -p 'test_account_hooks.py'`.
They use disposable delivery layouts, synthetic plans and isolated caches.
Then, on an authorized target client, inspect effective registrations, confirm the
delivered source revision, and exercise session recovery and each claimed event.
Test project/account overlap and opt-out. JSON parsing or a direct script run alone
does not establish native hook activation or user-facing model behavior.

References: [Claude hooks](https://code.claude.com/docs/en/hooks),
[Codex hooks](https://learn.chatgpt.com/docs/hooks), and the
[pinned upstream Codex guide](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/docs/codex.md).
