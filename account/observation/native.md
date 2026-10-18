# Opt-in native observations

The adapters record bounded metadata from Claude Code and Codex lifecycle
hooks. They reuse the [private store](README.md), consent epochs and retention.
Collection is disabled by default. Hermes and custom client profiles are not
supported by this collector. The existing installer still supports Codex and
Claude for skills, policies and planning hooks.

## Select a project and register delivery

Use Python 3.11+ on macOS or Linux. Start with a disposable account and project.
For a real account, select its existing home and an explicitly approved project.
The grant allows metadata collection for that exact canonical directory for up
to 30 days; subdirectories, worktrees and other projects need separate consent.
The current installer selects **one Claude or Codex registration per account**, not every
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
five Claude commands in `hook_activation.claude_observation`, or four Codex
commands in `hook_activation.codex_observation`. Use `grant --client codex`
for Codex; selecting that registration switches delivery to Codex alone. Applying the reviewed
plan registers the callback separately from planning; it does not create consent
or grant Codex hook trust. Existing personal settings and planning groups remain.
Hooks execute outside the model sandbox. Close client sessions before applying
and start a fresh session afterward. The host's settings policy may disable hooks;
verify actual delivery before claiming collection works. For Codex, review and
trust the four new exact definitions in native `/hooks`; prior trust of planning
hooks does not activate observation hooks. The installer never changes trust.
Its preview digest identifies its review input and is not Codex
`currentHash`. `doctor --native --client codex` checks effective discovery/trust;
it does not prove all callbacks executed. Downgrading a selected Codex observer to
a revision without the declared adapter capability is rejected; disable delivery
first when that downgrade is intentional.

Normal updates retain the selected epoch, including after expiry or revocation;
they never renew consent. Run `doctor` to check the selected grant and source
ownership. A PASS checks readiness, not native event delivery or complete coverage.
After an authorized native session, inspect records locally:

```sh
python3.11 scripts/improvement/observations.py --home /path/to/account \
  events --registration REGISTRATION_ID
```

To stop and remove collected data, revoke first. The callback then returns
without reading its stdin, even if its installed registration remains.

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

| Callback | Stored kind | Meaning |
| --- | --- | --- |
| SessionStart | session_start | A session callback arrived; no actor identity inferred. |
| PreToolUse | tool_start | A tool was about to run; pending, not proof of execution. |
| PostToolUse | tool_end | A result callback arrived; status stays unknown, not a test-pass claim. |
| PostToolUseFailure (Claude only) | tool_end | Claude reported a tool failure; no error text retained. |
| Stop | response_end | A response boundary, never task completion. |

Only bounded session/tool IDs, Codex turn IDs, kind and coarse tool category
survive normalization. Codex has no `PostToolUseFailure` callback; its
`PostToolUse` also follows nonzero shell exits and always retains unknown status.
`apply_patch` becomes the file category. Unified-exec polling can deliver the
original tool end later; hosted tools have no guaranteed hook coverage.
The project path stays in its private grant; records use a project digest. Tool
names become `shell`, `file`, `mcp` or `other`; private MCP names are not retained.
Prompts, tool arguments/results, assistant messages and transcript paths are
discarded and never dereferenced. Raw hook payloads are not written to disk or sent
over the network. Grant validation and exact process working-directory validation precede ledger scans and reading/parsing bounded stdin. The payload cwd is checked again afterward. Moving into a subdirectory or another worktree fails closed until that exact project is separately granted. See the [official hook directory contract](https://code.claude.com/docs/en/hooks#reference-scripts-by-path); the session-start project variable alone is insufficient after a directory change.

Tool callback identity combines registration, epoch, session, event name and tool
ID (plus the explicit turn ID for Codex), so duplicate routes sharing that
scope deduplicate. Codex tool events without a turn ID retain duplicate
uncertainty rather than inventing identity. Start/end/failure callbacks
remain separate. Missing stable IDs, including SessionStart and Stop, retain
`possible_duplicate`; repeated text is not identity. Actor/parent identity, Claude turn identity, source
event time, environment revision, effective skill exposure and task outcome remain
unknown. These records cannot establish a false-success claim without separately
selected feedback or evidence. Not all denied, interrupted or rejected tools emit
the registered callbacks; do not derive task success or a complete failure rate.

The adapter bounds stdin to 128 KiB, uses a three-second process alarm and a
four-second client hook timeout. Claude emits no stdout/stderr; Codex emits
only neutral `{}` JSON because its Stop output contract expects JSON. Neither
returns decisions on success, rejection, disabled consent or handled failure. It never rewrites tools,
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
events and exact-definition trust. Codex fixture and disposable delivery checks
cover normalization, one-client selection, neutral output and revocation. The
following native results are separate from those synthetic checks.

### Native platform evidence — 2026-10-18

| Platform/client | Actual evidence | Remaining limit |
| --- | --- | --- |
| macOS, Codex 0.163.0 / GPT-6-Luna low, corrected runtime | Fresh native turn: SessionStart 1, PreToolUse 3, PostToolUse 3, Stop 1; planning marker present; eleven reviewed definitions trusted | One synthetic task; no delivery-completeness, subagent or environment-exposure claim |
| Linux aarch64, Codex 0.163.0 / GPT-6-Luna low, historical pre-guard | Actual callbacks: session start 1, tool starts 4, tool ends 2, response end 1; planning marker present; eleven definitions trusted | Full fixture blocked by `bwrap: Failed RTM_NEWADDR`; apply_patch failed and intended exit 3 was not reached; sandbox was not weakened |
| Linux aarch64, Claude Code 2.1.302, historical pre-guard | Native initialization and one actual SessionStart record | Existing auth copy was unusable (`loggedIn=false`); model/tool/Stop run was not attempted |

The fresh corrected macOS payload fixture is `edf5b11ca47140602563869a1ff11bbf0c052dac`.
Collector, store, dispatcher and installation-harness hashes match this corrected
candidate; the public [capture manifest](../../docs/manual/codex-observation-capture.json)
records their identity separately from the fixture commit. The native run verifies
the pre-read process-directory guard in its normal granted-project route. Focused
and installed-dispatcher checks separately exercise rejection outside that root.

The earlier macOS fixture `92ced4083df43a79098f220a087ef3a114d3a3b7` and Linux
fixture `c94143ba41b050bd52701a59b1b9f167e17366c9` predate that guard. The Linux
results remain historical partial coverage, not qualification of corrected Linux
runtime. None of these runs automatically qualifies later capacity or attribution
changes. The fresh macOS intentional shell exit 3 still produced unknown observer
tool-end status; nested execution IDs were not joined into per-tool proof. Linux's
unequal start/end counts remain visible instead of being labeled full coverage.

Each test grant was revoked and each disposable installation removed. Post-revoke
neutral output/no-record behavior was checked by direct installed dispatchers,
not another model turn. Owned authentication copies/state and task daemons were
removed; the Linux guest was restored to its stopped state. No persistent host
account collection was activated. WSL, native subagents, parent lineage and
comparative efficacy remain unqualified. The [Codex walkthrough](../../docs/manual/codex-observation.pdf)
shows sanitized results; its images are browser renderings, not terminal captures.

A separate Linux container experiment subsequently passed actual Codex 0.163.0
app-server/command execution and a local synthetic Responses round trip inside an
inspected whole-client Docker boundary (network none, read-only root, nonroot, no
account/auth mounts). Positive file operations and negative filesystem/network
canaries ran in native tools, including a deliberate exit 3. No observation hooks
or trust were enabled, and no real model/provider request occurred. This qualifies
that synthetic transport/tool boundary; it does not replace the earlier approved
live fixture's bubblewrap blocker or qualify observer delivery, subscription
transport, holdout efficacy or promotion.

The versioned input schemas reviewed for Codex CLI 0.163.0 are at
[upstream commit 8308618](https://github.com/openai/codex/tree/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/hooks/schema/generated).
The [stale-green discussion](https://www.reddit.com/r/ChatGPTCoding/comments/1w5y7ph/codex_hooks_give_you_no_exit_status_for_a_shell/)
was inspected with replies on 2026-10-18 (displayed as one month old; exact date
and client version unavailable). The author promotes their tool and reports missing
shell exit status; one reply describes stale output and wrong-package checks, and
the author acknowledges the coverage limitation. These are useful failure cases,
not independent validation of this collector or a reason to copy its permission
rewrites. Community validation of this implementation remains provisional.

The installed callback pins the Python interpreter used by setup. If that executable moves or is removed, reinstall/update with a supported Python 3.11+ interpreter; callbacks may otherwise stop silently. Native re-consent after a corrupt ledger with an unknown frontier is currently unsupported. Do not remove a revocation tombstone to bypass that refusal.
