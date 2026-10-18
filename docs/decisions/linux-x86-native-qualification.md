# Ubuntu x86_64 native qualification

Recorded: 2026-10-18. Task: [issue 22](https://github.com/hwanjjang/agent-dotfiles/issues/22).
Executed source: `7ada8e20c4f0f7a0e04b585d6d1820dad8fa0a16`.
The [native platform matrix](../../account/observation/native.md#native-platform-evidence--2026-10-18)
owns advertised collection coverage. This note records one additional host run;
it does not replace the historical aarch64 evidence or qualify later source.

## Host and execution boundary

Ubuntu 24.04.4 LTS, Linux 6.8.0-142-generic x86_64, glibc 2.39 and Python 3.12.3.
The maintainer selected this host instead of an additional Ubuntu VM and excluded
WSL. Three disjoint disposable account/project lanes ran in parallel. Only existing
file authentication was copied with mode 0600. No new login, real-account
collector activation, global permission change or prerequisite installation ran.
Native configuration probes are distinguished from actual model invocations.

| Surface | Client and actual model | Bounded invocation count |
| --- | --- | --- |
| Claude | Claude Code 2.1.302, first-party `claude-haiku-5-5`, low effort requested | Three parents, one native child |
| Codex | Codex 0.163.0, OpenAI `gpt-6-luna`, observed low effort | Three parents, one native child |
| Optional Paseo | Paseo 0.11.2, Codex 0.163.0, `gpt-6-luna`, observed low effort | Three parent turns across two owned agents |

Claude used restricted fixture access, explicit Read/Write and fixture Bash
allowances, no permission prompts, and an empty strict MCP configuration.
Codex used workspace-write, network disabled and approval policy never. Paseo
used its discovered auto mode; native context confirmed workspace-write,
network disabled and on-request approvals. No full-access or hook-trust bypass
was used. Native Hooks UI reviewed/trusted the eleven installed Codex definitions.

## Normal execution and planning

| Scenario | Native evidence | Collector counts |
| --- | --- | --- |
| Claude baseline | Synthetic Read/Write, deliberate Bash exit 3 and missing-file Read; planning marker recovered | SessionStart 1, tool starts 4, tool ends 4, Stop 1 |
| Codex baseline | Exact synthetic read/write command exit 0 and separate deliberate exit 3; planning marker in SessionStart hook entries | SessionStart 1, tool starts 2, tool ends 2, Stop 1 |
| Paseo baseline | Synthetic read/write exit 0, deliberate exit 3; six additional owned-instruction reads/listings, including two initially incorrect relative paths | SessionStart 1, tool starts 8, tool ends 8, Stop 1 |

Claude's two PostToolUseFailure callbacks have failure status. Successful Claude
tool ends and all Codex/Paseo tool ends remain unknown in the collector even when
the native trace independently records the exit. The initial Paseo baseline did
not receive the selected planning environment and does not qualify recovery.
The corrected launch supplied `PLAN_ID` and `PWF_PLAN_ROOT`; process environment
and native messages independently confirmed planning recovery. The baseline was
not repeated.

## Interruption

- Claude: after the actual start marker, SIGINT produced a native interruption
  error; the CLI itself exited 0. Only SessionStart and one tool start arrived.
  No finish marker was observed before cleanup and no owned shell survivor was
  found. Exact shell exit remains unknown.
- Codex: `turn/interrupt` after the start marker produced native turn status
  `interrupted`. The bounded command continued and wrote its finish marker. Only
  SessionStart and one tool start arrived; final process exit and PostToolUse/Stop
  remain unobserved. The script's PID was a sandbox namespace PID and was never
  treated as the corresponding host PID; host identity checks rejected that match.
- Paseo's first attempt returned stoppedCount 0 because the tool yielded and the
  model finished its turn before cancellation. Its process later exited 0; the
  attempt is retained as an unsuccessful interruption test. Its tool start also
  had no PostToolUse although the turn reached Stop. One corrected turn
  kept the tool call waiting, returned stoppedCount 1 and recorded native
  `turn_aborted` with reason `interrupted`. The process continued and its native
  CommandExecution result recorded exit 0 after 22.172848391 seconds. That session
  added SessionStart 1, tool starts 2 and tool ends 1, without Stop. One preceding
  owned-instruction read accounts for the paired tool; the interrupted tool's end
  remains missing.

Turn cancellation therefore does not establish process termination. Missing
callbacks do not imply completion or success, and a CLI exit is not the shell exit.

## Native children and collection limits

Each direct client created exactly one native child that read the synthetic marker.
Claude's Agent call, forwarded child Read `parent_tool_use_id` and child agent ID
provided explicit native linkage. The forwarded child response identified Haiku
5.5. The child scenario added SessionStart 1, tool starts 2, tool ends 2 and Stop 1.

Codex emitted native subagent activity and an actual child command with exit 0.
The child's native session metadata explicitly named the parent's thread and
depth 1. The parent-scoped collector scenario added SessionStart 1, tool starts 3,
tool ends 3 and Stop 1. No records used the child's own session ID. A separate
child SessionStart/Stop delivery claim is unsupported.

All collector actor/parent values remained null across all three lanes. Native
thread/tool lineage is separate evidence and was not imported or inferred into
those fields. The adapter still does not register SubagentStart/SubagentStop.
Paseo-managed agent ownership also does not establish provider-created lineage.

Final ledgers contained 18 Claude records (3 starts, 7 tool starts, 6 tool ends,
2 stops), 16 Codex records (3 starts, 6 tool starts, 5 tool ends, 2 stops), and
24 Paseo records (2 starts, 11 tool starts, 9 tool ends, 2 stops). Checked stored
metadata excluded synthetic contents, fixture paths, prompts and raw commands.
This is bounded capture evidence, not complete delivery or exact exposure.

## Preparation, regression checks and cleanup

The discovered Codex built-in permission profile `:workspace` passed the offline
canary: workspace write, outside EROFS 30, IPv4/IPv6 EPERM 1 and deliberate exit 3.
Plain `codex sandbox` had defaulted to read-only despite a legacy configuration
value; a guessed named profile was rejected. A temporary-directory helper-alias
warning was resolved by relocating only the disposable Codex home. Old grants
were revoked before replacement. A local harness import error was corrected
before model execution. These preparation failures are not native task failures.
Native doctor also refused an explicit other-home probe; running discovery from
the isolated account context respected that guard.

One focused run passed 202 unique existing tests across 15 modules, with no
failures, errors or skips. It covered observation, setup, doctor, native task
metadata and the small subprocess qualifier. It did not repeat the separate
10,000-callback benchmark. Deterministic tests are separate from the model runs.

All selected grants were revoked, purging 18/16/24 records respectively. Direct
old-epoch callbacks returned neutral output with zero records. Temporary
credentials, owned installations/projects and owned processes were removed.
Both owned Paseo agents were hard-deleted; their registry files were absent.
The owned workspace was archived and project registry entry removed. The owned
Codex daemon and residual owned process loop were stopped. Unrelated workspaces
were preserved. Original account configuration hashes and symlink targets matched
their initial snapshot. These checks establish scoped runtime cleanup, not
forensic erasure or absence from every secondary client/daemon history store.

Raw evidence and credential-free detailed receipts remain private; no credentials
or raw session captures are part of this public note. Existing screenshot PDFs
retain their historical source bindings. The remaining supported claim is
bounded native execution and observed child relationships on this host; collector
actor/parent binding, complete interruption delivery, WSL and task efficacy remain
unqualified. PR review and tracker closure are separate from this local run.
