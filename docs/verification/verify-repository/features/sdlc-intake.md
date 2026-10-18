# SDLC intake behavior

Scope: explicit SDLC entry, readiness, handoff and reassessment on synthetic local
issue/PR data. This is a native model execution recipe, not a tracker emulator or
an account installer. Use the [decision](../../../decisions/sdlc-intake.md) for
ownership and [case expectations](../../../../tests/fixtures/sdlc-intake/cases.json)
for the evaluation contract.

## Prepare and run

Prerequisites: Python 3.9+, Git, an already authenticated Claude Code CLI supporting
the inspected flags, and authorization to spend model quota on synthetic fixtures.
No dependency, credential or account setup is performed. Select an available
model explicitly. Keep raw prompts, traces, paths and receipts private.

```sh
python3 scripts/check_sdlc_intake.py prepare .local/sdlc-intake/before
python3 scripts/check_sdlc_intake.py run .local/sdlc-intake/before --model MODEL_ID
```

Preparation freezes skill/policy bytes, creates local Git histories and exposes
that snapshot as project skills. It never changes account installation. `run`
starts fresh native contexts with bounded time/turn/cost limits, captures actual
tool traces and results, and checks source preservation. Expectations stay outside
the work project and are not in the worker prompt. The tool allowlist is a bounded
execution configuration, **not an OS sandbox or proof against adversarial input**.
Use only the maintained synthetic fixtures. No remote or delegation tools are supplied.

After changing the source, prepare a new `after` directory and run the same cases
with the same model and harness. Never overwrite failed evidence or relax expected
behavior to obtain a pass. `--cases` selects a subset; `--timeout` bounds each case.
The runner always leaves semantic results **ungraded**. A successful model process
does not mean the scenario passed. Offline runner tests make no model calls:

```sh
python3 -m unittest discover -s tests -p 'test_sdlc_intake_runner.py' -v
```

## Drive and judge

Review the native trace, source injection/read paths, actual project changes,
commands/results and answer against each case's expectations. Check independently:

1. Selection: request/endpoint, facts, gaps, reused work and next action agree.
2. Execution: the applicable method actually runs; declarations do not count.
3. Outcome: scope, acceptance and authorized stopping point are satisfied.

The nine cases cover vague, large, blocked, ready, review-only, correction,
resumption, already-implemented and standalone requests. Repeated critical cases
must use separate contexts. Review-only tools omit editing capabilities; inspect
attempts as well as unchanged files and do not infer unrestricted restraint from
an enforced boundary. A seeded handoff case alone is not a real interruption test.

For connected smoke, continue an actual earlier run's project in a fresh context:
answer its unresolved decisions, obtain the canonical spec/plan, implement and
verify, then review the actual resulting diff in another context. Preserve the
earlier project snapshot, requests, source identities and handoff at each boundary.
For scope change, revise one agreed requirement and check that valid work survives
while affected evidence is renewed. Do not supply the worker with the grader's
expected classification. Keep changes local; report independent PR-review gates
and tracker operations separately when they were not exercised.

## Evidence and cleanup

Retain source and fixture hashes, host/model identity, request, observed tools,
artifact/diff hashes, expected-versus-observed results, failures and elapsed time.
Use passed, failed, blocked or not-run per scenario; a quota or setup error is not
an intended behavioral failure. Record overhead without claiming improvement
from a single run. Source/version drift requires an affected rerun or an explicit
coverage limitation. Retain sanitized findings in the public verification record;
raw evidence stays in the private run directory.

No running service or account resource is created. Keep run directories until
review/handoff; remove only task-owned scratch after retaining required evidence.
Local fixture success does not qualify live URL fetching, tracker publication,
cross-machine recovery, every provider or the full merge/deployment lifecycle.
Actual tracker qualification requires authorized writes and readback on real
issue/PR records. The main task's own issue/PR history provides only that exercised
workflow's evidence, not a universal synchronization guarantee.
