# Native isolation qualification

Scenario ID: `native-isolation`. Surface: the public Python verifier and an
existing, explicitly selected Docker host. User goal: qualify a synthetic native
client/tool workflow before adding any live provider connection.

Follow the [qualification guide](../../../decisions/evaluation-isolation-pilot.md#linux-native-synthetic-qualification)
for the authoritative prerequisites, pinned dependencies and command. This recipe
is separate from the browser helper; it never requires account credentials or
hook activation. Missing prerequisites are blocked, not a reason to broaden mounts
or change host policy.

1. Run the maintained CLI with the verified archive, existing image/context,
   Docker-visible staging parent and a new ignored evidence directory.
2. Read `receipt.json`: require pass, native-client qualification, actual native
   initialization/discovery/tool/turn evidence, all selected canaries and completed
   cleanup. Live transport and promotion must remain false.
3. Exercise the failure path using a small synthetic file as the archive and
   another new output directory. Require blocked status and completed cleanup;
   no container should execute with an unverified archive.
4. Confirm no owned container or staging child remains after either run. If
   removal failed, retain evidence and resolve the exact owned resource before
   reporting qualification. Preserve existing images, contexts and VM state.

Keep receipts and native traces private. Bind them to the current runner/probe,
image and binary identities. A completed mock turn is insufficient without the
native tool outcome and denial checks; fabricated mock token counts are not model
usage. This recipe does not qualify live subscription authentication, grader or
holdout custody, routing efficacy, promotion, Windows/WSL, or every container
escape class. The [walkthrough](../../../manual/native-isolation.pdf) shows how to
find this guide; its screenshot is not execution evidence.

Run the focused native isolation tests for malformed records, exact ownership
cleanup, uncertain timed-out creation, archive replacement and umask 077. In the
actual receipt, verify image ID and namespace/resource settings; in the preflight
record, require seccomp mode 2 and TCP errno 101 for both IP families. A constant
zero is not a provider traffic measurement. Retain primary and cleanup reasons
separately; uncertain cleanup must never qualify the run.

## Reusable executor fixture

Follow the [fixture guide](../../../decisions/native-execution-fixture.md) for
`native_execution.py`; do not substitute its receipt for the container verifier's
isolation receipt. Use a new evidence directory for every attempt. Inspect the
actual terminal, skill outputs and retained submission count. `mock_complete`
always leaves live/authentication/isolation qualification false. Exercise the
public CLI's fake-process success and terminal-error paths, and run
`test_native_execution.py` for malformed/oversized output, deadlines, excess
submissions and cleanup failure. A CLI exit zero alone is insufficient.

The [two-page fixture walkthrough](../../../manual/native-execution.pdf) and
[editable source](../../../manual/native-execution.json) show actual browser-rendered
CLI/result summaries, not terminal or real-model captures. The source-bound actual
native mock covers selected routes only; its separate supervisor verified owned
containers, volume and PIDs absent. Do not infer escaped-resource cleanup from
the reusable runner's process-group cleanup or replay a historical native run
without its explicit ownership and runtime prerequisites.
