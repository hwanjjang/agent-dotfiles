# SDLC intake verification — 2026-10-18

The new entry explicitly loads intake and routing before selecting work. Native
Sonnet 5.5 runs exercised that path and reused adequate artifacts. This is a
bounded qualification of intake, not a claim that the full SDLC always succeeds.
The [recipe](verify-repository/features/sdlc-intake.md),
[fixtures](../../tests/fixtures/sdlc-intake/cases.json) and
[run identities](sdlc-intake-runs.json) make the observations reproducible.
Raw traces, absolute paths and session data remain private.

## Comparison and actual actions

Claude Code 2.1.302, `claude-sonnet-5-5`, medium effort, fresh contexts on a local
Python library. Baseline and candidate used the same nine requests, skill bundle
layout and execution allowlist. Baseline preceded the entry edits; candidate
source hashes are retained in the run index. Process success was never treated
as behavioral PASS. Results below are manual trace/artifact assessments.

| Case | Baseline | Candidate assessment |
| --- | --- | --- |
| Vague | Asked consequential questions; no implementation | Passed intake boundary: read intake/routing, inspected code, returned unanswered decisions; repeat also made no edits |
| Large | Wrote spec/plan without loading focused planning skill | Passed planning handoff: invoked planning-and-task-breakdown, produced three dependent tasks and one justified PR boundary; fixture does not prove multi-PR decomposition |
| Blocked | Reported absent canonical dependency; no edits | Passed: identified same unavailable contract and stopped dependent build without inventing vocabulary |
| Ready | Implemented correct behavior with test-first and smoke, but skipped focused method loading | Failed original write boundary: loaded tdd and implemented/tested correctly, but wrote one placeholder scratch file above project; clean fresh repeat passed with only two planned source/test files changed |
| Review | Found wrong field; no edits | Passed: loaded review method, found wrong-field defect against actual diff; repeat preserved read-only boundary |
| Correction | Fixed wrong field and ran checks | Passed local correction: read tdd, showed two failing tests before fix, six passing after and real function smoke; explicitly did not claim independent review |
| Resume | Reused implementation and added missing checks | Passed reuse/outcome: code unchanged, seven tests and real smoke; focused tdd method was not loaded in original; repeat read it and used alternative evidence plus mutation check |
| Done | Reused correct code and added coverage | Passed reuse/outcome: code unchanged, seven tests and smoke; no fabricated Red; denied mutation attempt retained as not run |
| Standalone | Answered directly without lifecycle state | Passed: no SDLC lifecycle initialization or project edits |

These are separate selection, method-execution and outcome observations, not a
nine-out-of-nine pass claim. Review editing tools were unavailable: unchanged
files demonstrate that configured boundary, not unrestricted model restraint.
Original candidate elapsed times ranged from 5.96 to 33.38 seconds; baseline
6.31 to 41.07 seconds. These single samples do not establish speed improvement.
All compared bundle hashes remained unchanged.

## Connected fresh-session smoke

Four independent native sessions consumed actual earlier output, rather than
only a seeded resume fixture:

1. Supplied the consequential product decisions to a vague task. The agent invoked
   to-spec and planning-and-task-breakdown and wrote spec/plan without code changes.
2. Copied that actual project into a fresh context. The agent invoked tdd, reused
   spec/plan byte-for-byte, showed four failing tests before implementation and
   seven passing afterwards, and wrote a handoff.
3. Another context inspected the resulting real diff and handoff read-only. It
   loaded code-review-and-quality and verification; its test command was denied
   by the harness. It returned a **static-only** review, not eligible PR PASS.
4. A separate continuation changed one approved decision to case-insensitive
   matching. It revised affected spec/plan, implementation and tests, preserving
   default/order/missing-field/non-mutation behavior. Nine tests passed.

The connected build omitted the additional smoke because its plan incorrectly
said the library needed none, and the static reviewer accepted that rationale.
This is a retained verification-method gap, not a successful full lifecycle.
The parent subsequently ran the actual function and suites in eight candidate,
repeat and connected projects, including the changed-scope project; all passed.
That independent observer check confirms output behavior but does not retroactively
turn the omitted native smoke or static-only review into a completed gate.

## Failures, scope and retained evidence

Earlier Haiku 5.5 pilots sometimes skipped linked references and selected methods.
Adding an explicit entry-point read improved observed reference loading, but
Haiku still skipped focused method execution. Sonnet was then evaluated explicitly;
no claim is made that the change works equally across models. Early harness runs
denied inline Python smoke; later comparisons used the corrected allowlist.
All failures and earlier runs remain in private evidence, with no overwritten retry.

The scratch-path violation motivated recording native Write/Edit attempts outside
the fixture. This detects observed attempts; the runner is **not an OS sandbox**,
and allowed shell commands are not adversarial isolation. Use only maintained
synthetic inputs. The failed run remains failed even though its repeat passed.

The change keeps existing specification, decomposition, synchronization and
resumption methods. Its model behavior remains advisory. Live URL fetching,
tracker synchronization, remote interruption recovery, multiple PR slicing,
all clients/providers and account installation are not qualified by these local
fixtures. The actual task's issue/PR updates and readbacks provide evidence only
for those exercised operations. No global classifier, extra agent, new state
schema, or account installation was introduced.

Offline runner checks cover evidence preservation, source mutation observation,
timeout classification, outside-write reporting and a real Git review diff.
Repository/SDLC regression and map checks are required separately; final results
and independent review belong to the linked PR, not these historical run claims.
The [manual](../manual/sdlc-intake.pdf) illustrates actual observed responses;
both rendered pages were visually inspected. No universal reliability claim is made.
