# Opt-in Claude observations

The first native adapter records bounded metadata from Claude Code's ordinary
hooks. It reuses the [private store](README.md), consent epochs and retention.
It is disabled by default. Codex, Hermes and custom Claude profiles are not
supported by this collector. The existing installer still supports Codex and
Claude for skills, policies and planning hooks.

## Select a project and register delivery

Use Python 3.11+ on macOS or Linux. Start with a disposable account and project.
For a real account, select its existing home and an explicitly approved project.
The grant allows metadata collection for that exact canonical directory for up
to 30 days; subdirectories, worktrees and other projects need separate consent.
The current installer selects **one Claude registration per account**, not every
grant in the store. Grant creation alone does not install or run a hook.

```sh
python3.11 scripts/improvement/observations.py --home /path/to/account \
  grant --client claude --project /path/to/project

# Substitute the returned registration_id. Review both plans before --apply.
sh scripts/setup-account.sh install --home /path/to/account \
  --observation-registration REGISTRATION_ID
# Use update when the account already has an installation receipt.
sh scripts/setup-account.sh update --home /path/to/account \
  --observation-registration REGISTRATION_ID
```

The installer uses a committed source revision; uncommitted adapter files cannot
be installed. Preview includes the selected project, epoch and expiry plus all
five Claude commands in `hook_activation.claude_observation`. Applying the reviewed
plan registers the callback separately from planning; it does not create consent
or grant Codex hook trust. Existing personal settings and planning groups remain.
Hooks execute outside the model sandbox. Close client sessions before applying
and start a fresh session afterward. The host's settings policy may disable hooks;
verify actual delivery before claiming collection works.

Normal updates retain the selected epoch, including after expiry or revocation;
they never renew consent. Run `doctor` to check the selected grant and source
ownership. A PASS checks readiness, not native event delivery or complete coverage.
After an authorized native session, inspect records locally:

```sh
python3.11 scripts/improvement/observations.py --home /path/to/account \
  events --registration REGISTRATION_ID
```

To stop and remove collected data, revoke first. The callback then returns
silently without reading its stdin, even if its installed registration remains.

```sh
python3.11 scripts/improvement/observations.py --home /path/to/account \
  revoke --registration REGISTRATION_ID
sh scripts/setup-account.sh update --home /path/to/account \
  --observation-registration none
# Add --apply to the reviewed update to remove only owned observation delivery.
```

Removing delivery alone preserves records and consent. Uninstall and guarded
rollback also preserve the observation store; use `revoke`/`prune` for its cleanup.
Regranting creates a new epoch; explicitly select it through the installer again.
Queued callbacks with the previous epoch remain disabled. Native sequence numbers
are local receipt order, allocated under the store lock, not source history offsets;
the retained frontier is carried forward automatically. Synthetic `capture` and
`import` reject native registrations. No transcript import or history scan exists.

## What is observable

| Claude callback | Stored kind | Meaning |
| --- | --- | --- |
| SessionStart | session_start | A session callback arrived; no actor identity inferred. |
| PreToolUse | tool_start | A tool was about to run; pending, not proof of execution. |
| PostToolUse | tool_end | A result callback arrived; status stays unknown, not a test-pass claim. |
| PostToolUseFailure | tool_end | Claude reported a tool failure; no error text retained. |
| Stop | response_end | A response boundary, never task completion. |

Only bounded session/tool IDs, kind and coarse tool category survive normalization.
The project path stays in its private grant; records use a project digest. Tool
names become `shell`, `file`, `mcp` or `other`; private MCP names are not retained.
Prompts, tool arguments/results, assistant messages and transcript paths are
discarded and never dereferenced. Raw hook payloads are not written to disk or sent
over the network. Grant validation precedes reading/parsing the bounded stdin.

Tool callback identity combines registration, epoch, session, event name and tool
ID, so duplicate routes sharing that scope deduplicate. Start/end/failure callbacks
remain separate. Missing stable IDs, including SessionStart and Stop, retain
`possible_duplicate`; repeated text is not identity. Actor/parent/turn, source
event time, environment revision, effective skill exposure and task outcome remain
unknown. These records cannot establish a false-success claim without separately
selected feedback or evidence. Not all denied, interrupted or rejected tools emit
the registered callbacks; do not derive task success or a complete failure rate.

The adapter bounds stdin to 128 KiB, uses a three-second process alarm and a
four-second client hook timeout, and emits no stdout/stderr or decisions on normal
success, rejection, disabled consent or handled failure. It never rewrites tools,
approves permissions, injects context or requests continuation. Slow storage,
malformed/oversized input, contention and crashes can lose callbacks. There is no
background retry or delivery-loss counter; completeness is explicitly unknown.
The existing 4,095-record cap and ledger scan remain. This is a bounded pilot,
not the design's 10,000-event/p95 latency qualification.

## Qualification and references

On 2026-10-18, Claude Code 2.1.302 with actual `claude-haiku-5-5` exercised all five
callback types (six records) using synthetic files and a disposable installation
selected with `--settings`. The existing Claude authentication was used; this was
not a hermetic evaluation account. Both the planning recovery marker and observation
events appeared. An intentional missing-file Read produced the failure callback.
Stored records excluded file content/paths; owned files had no drift. The selected
grant was revoked and the disposable installation removed afterward. No persistent
real-account registration was changed. Linux native-client execution, subagents,
Paseo and Codex observation are not qualified by this run.

[The verification recipe](../../docs/verification/verify-repository/features/native-observation.md)
owns repeatable checks. [The improvement design](../../docs/decisions/account-improvement-loop.md)
owns later task feedback, isolated comparison and promotion; none is implied by
successful event capture.

This is original MIT-licensed repository code, not imported hook middleware.
The [Claude hook reference](https://code.claude.com/docs/en/hooks), inspected
2026-10-18, defines event fields, failure gaps and hook behavior. The
[Codex hook reference](https://learn.chatgpt.com/docs/hooks) documents its separate
events and exact-definition trust; it needs independent adapter qualification.
The [stale-green discussion](https://www.reddit.com/r/ChatGPTCoding/comments/1w5y7ph/codex_hooks_give_you_no_exit_status_for_a_shell/)
was inspected with replies on 2026-10-18 (displayed as one month old; exact date
and client version unavailable). The author promotes their tool and reports missing
shell exit status; one reply describes stale output and wrong-package checks, and
the author acknowledges the coverage limitation. These are useful failure cases,
not independent validation of this collector or a reason to copy its permission
rewrites. Community validation of this implementation remains provisional.
