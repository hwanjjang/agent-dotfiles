# Frozen native trial verification

Scenario ID: `native-trials`. Surfaces: the public `native_trial.py`
`check`/`run`/`recover` CLI and the separate `native_execution.py`
`command-skills-loader` fixture. Run this recipe separately from the browser helper.

Read the [operator guide](../../../native-trials.md) for exact prerequisites,
manifest fields, commands and result meanings, and the
[design contract](../../../decisions/native-trial-execution.md) for ownership and
acceptance rules. The [execution](../../../verification/native-trials.json),
[scoped grading](../../../verification/scoped-grading-integrity.json),
[collection](../../../verification/native-outcome-collection.json) and
[fixed routing](../../../verification/native-routing-observer.json) records share
their recorded source13/profile bindings and a
[provenance companion](../../../verification/native-qualification-provenance.json).
Check every consumed digest; historical results and a working CLI do not qualify
new bytes. Record-binding tests and the offline admission smoke cannot substitute
for a standard production task's observed result and cleanup.
Missing evidence is pending, not pass. Do not reproduce schema or last-run status
in this recipe.

## Prepare and check without authentication

Use Python 3.11+ and an explicitly prepared private frozen manifest. The selected
profile is `codex-0.163-macos-arm64-linux-arm64-v1`; authenticated execution and
recovery additionally require the guide's macOS arm64 host and existing Docker
prerequisites. Neither command installs runtimes, starts a VM, changes context,
activates hooks or discovers credentials. Keep the manifest, selected inputs,
attempt state and raw evidence ignored/private.

```sh
python3 scripts/improvement/native_trial.py --help
python3 scripts/improvement/native_trial.py check --plan /path/to/private-trial-plan.json
```

1. On an unchanged valid fixture, require exit 0, `status=checked`, the expected
   manifest digest, `authentication_opened=false` and `processes_launched=false`.
   Confirm checking created no attempt claim. This reads frozen inputs and
   runtime/source files; it does not establish Docker, authentication or tool routing.
2. In a separate owned synthetic fixture, change one selected input without
   updating its frozen digest. Require exit 2 and `status=refused` before any auth
   copy or launch. Restore only that synthetic fixture and repeat the valid check.
   Preserve both results; never rewrite a production digest to hide drift.
3. Exercise duplicate-attempt refusal with the disposable lifecycle test or a
   previously recorded authorized attempt. Its claim must remain after cleanup;
   checking/running that same trial/attempt must refuse instead of overwriting it.
   Do not invent a new output path to relabel the existing attempt as fresh.

Use focused tests to cover synthetic custody, unknown process state, interrupted
copy, immutable bindings and recovery refusal without real credentials:

```sh
python3 -m unittest discover -s tests -p 'test_native_trial*.py'
python3 -m unittest discover -s tests -p 'test_native_usage.py'
```

Fake Docker/native responses test controller wiring and fixed failures. They do
not prove actual OS restrictions, authentication or current runtime compatibility.

Exercise real controller setup with a validated catalog-only natural plan that
omits `entrypoint`, using fake Docker/extraction only at the external boundary.
Require a deterministic frozen-file write-denial probe, readonly staged inputs,
unchanged prompt/catalog and no authentication or native launch. Add an
earlier-sorting file to a forced plan and require its declared entrypoint to stay
the probe. Wrong readonly facts must still refuse before authentication.

## Execute only the selected authorized scenario

Follow the guide's `run --plan ... --auth-source ...` invocation only within the
existing explicit source/temporary-recipient and model execution scope. An absent
prerequisite stays blocked; this recipe grants no new credential copy or account
access. Before execution, bind the selected source/runtime/image, metadata tuple,
case/arm, attempt and limits. The executor receives selected inputs, not auth,
journals, grading material or another arm. Check the separate outer VM share
boundary; a no-bind container alone does not prove a no-share VM.

Read the private receipt rather than treating exit 0 as task correctness. Require
matching terminal/usage, no stop or capture failure, and completed owned cleanup.
`completed_ungraded` leaves semantic correctness ungraded. Qualification mode
also needs its exact fixed loader/script correlation, closed boundary projections,
remote-only challenge and unchanged known synthetic protected files. Inspect
`qualified_current_profile` only for the exact source-bound attempt that produced
it; do not infer it from the credential-free fixture. `live_eligible` stays false;
request/retry counts, billing and backend identity are not established by usage.

Retain failed/partial attempts and the primary failure separately from cleanup.
A soft usage stop remains stopped even if a later terminal says completed.

## Recover and confirm cleanup

Use the original source/runtime and attempt journal with the guide's
`recover --attempt ...` command. It may inspect and signal exact recorded owned processes and remove owned Docker
resources, but does not recopy credentials,
start native inference or manage VM lifecycle. Require the exact original
identities and prior supervised-shutdown evidence; unresolved launch, changed
ownership or uncertain query must retain refusal/blocked status. A caller flag
cannot establish shutdown.

Require recorded auth/home/control and owned container/volume cleanup, preserving
the attempt claim and receipts. Reconcile any residue before releasing resources;
never use broad recursive deletion to turn uncertainty into success. A
`reconciled` result qualifies cleanup only. The external coordinator owns any VM
stop and independent post-cleanup check; preserve unrelated resources and state.

## Separate credential-free loader

Use the guide's private loader plan and external executor preparation, then:

```sh
python3 scripts/improvement/native_execution.py --help
python3 scripts/improvement/native_execution.py \
  --plan /path/to/private-loader-fixture-plan.json \
  --output /path/to/new-private-fixture-output
```

This is not `native_trial fixture`. Require the exact source-bound readonly
`/runtime/qualification.js`, expected ASCII length and selected `/runtime/arm`
body/reference fixture. Inspect actual six closed boundary projections,
disabled-collaboration refusal and matching native terminal. Require unchanged
external known synthetic sentinels and owned helper/executor cleanup from the
coordinator's evidence; the inner receipt alone cannot prove those external facts.
Preserve failure and cleanup uncertainty without a local fallback.

`mock_complete` keeps live/authentication/isolation qualification false. This path
uses a synthetic provider, not real inference; do not convert its submission count
to provider billing or use it as authenticated evidence. Current-profile results,
comparison admission and promotion remain separate from this recipe.

## Scoped grading and installer-state checks

For the fixed credential-free loader, require both direct and explicit child task
read/write/readback plus exact protected grading/other-arm/installer synthetic
read/write/create outcomes. Combine owner-side file existence, excluded mounts,
post-shutdown identity/content and absent created siblings. Missing operations,
child failure or a nonzero exit alone cannot establish denial. Verify exact source
identities and outer cleanup from the linked current scoped record. Host controller
and scorer retain their access; no new account, external operator or environment
is needed. The grader's late source/spec drift tests must block the result while
retaining critical observations; synthetic tests are not actual model outcomes.

## Optional artifact collection

Scenario ID: `native-trials.collection`. Follow the operator guide's trial-only
`collection` declaration and current source inventory. Check a valid private plan
without authentication, then preserve a separate malformed/stale refusal. The
credential-free qualification uses the fixed native task and actual collector;
unit fake-Docker wiring alone cannot establish this path.

Require present and missing observations, unsafe-symlink blocking, and a separate
interrupted native task whose partial file never becomes task success. Inspect
manifest/declaration/source/container bindings, exact path order and byte limits,
false quiescent flag, primary failure and full owned cleanup. Verify shutdown and
known-home purge precede capture, and capture precedes executor removal within the
original deadline. Recovery must never recapture. Reuse selected proof only for
matching source/runtime/profile facts; no authenticated/natural-routing/comparison
claim follows from fixed credential-free execution.

The selected private native bridge supplies the observation projection and its own
receipt. It exercises production setup/cleanup/capture; production `observe`/`finish`
collection gating is unit-tested, not covered end to end by that native fixture.

## Optional routing observation and finalized records

Use the [single routing/model contract](../../../decisions/evaluation-accounting.md#declared-catalog-routing-and-client-model-observations)
for plan catalogs, natural versus forced mode, finalized record order and admission.
Run `test_native_routing.py`, `test_native_routing_metadata.py` and
`test_trial_admission.py` with the existing unit-test runner. These synthetic stream/journal checks cover receiver completion,
healthy-none versus unknown, model selection and source/profile binding; they are
not current native qualification. Before an authorized actual run, preserve the
frozen catalog, exact source/runtime profile and explicit scope. A first-page read
signal is not all-page reading, semantic adherence or outcome correctness. Keep
historical evidence tied to its original bytes; no changed-source proof is implied.

Verify owned-group signaling is attempted before leader reap even after graceful
EOF; EOF alone cannot establish descendant absence. Retain finite signal error
categories and the primary stop reason. Test the macOS exited-group case:
reconciliation requires a reaped owned leader, both drained streams, no pending/trailing records and
process-not-found from a signal-0 probe of the exact original group. A present
group, denied/failed probe, missing EOF, another OS or expired deadline stays
blocked. No destructive signal may be sent after reap. Verify the original error
category and `group_absent_after_reap` reach the canonical cleanup receipt.
Exercise descendant-held pipes, bounded drain/stream failures and unsupported
frontmatter grammar with those focused tests. Also check finite boundary input
diagnostics for invalid call identifiers and known presentation differences;
every non-exact input remains blocked and arbitrary content must stay absent.
Extract the delimited qualification prompt and compare it byte-for-byte with the
canonical loader, including its unchanged pragma and absence of a final LF.
The old/new loader must perform identical synthetic remote operations. The
[source-backed routing workflow](../../../architecture/native-routing-workflow.html)
pins its inspected source revision; its browser checks do not qualify native execution.

Before native qualification, record the execution host OS and retain a fast-exit
stdio check on that host. Follow the accounting contract's host-dependent
signal/cleanup limit: an exited leader with uncertain group signaling remains
unknown even after successful output. A synthetic peer held alive after EOF is
a different path and cannot substitute for that check.

## Working-source qualification checkpoint

The [2026-10-19 checkpoint](https://github.com/hwanjjang/agent-dotfiles/issues/54#issuecomment-6257672901) records the eight bounded
cases, current source identity, failed attempts, recovery and evidence reuse.
All selected receipts have verified owned cleanup and now supply the maintained
qualification references. They do not qualify arbitrary task outcomes,
other hosts, backend identity, candidate benefit or account activation. Historical
manuals and diagrams retain their own source/capture identities.

## Maintained qualification bindings

Run `python3 -m unittest discover -s tests -p test_public_qualification_bindings.py -v`
from the repository root. The checks load current maintained records through the
unchanged reader, reject a rehashed stale source record and reject missing/false
routing falsification. Their experiment/context fixtures are synthetic; no
native execution, credential access or model inference occurs. Later source drift
must remain unqualified; passing these checks never renews native evidence.

An offline CLI smoke with a frozen synthetic schedule and no completions must keep
every scheduled row missing/inconclusive with no fabricated pass. The next actual
full-path check belongs to the first preregistered development row, using the
existing reservation and production lifecycle. Do not populate `observation` or
write a replacement completion receipt to satisfy that check.
