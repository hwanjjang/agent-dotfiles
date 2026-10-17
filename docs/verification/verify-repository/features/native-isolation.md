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
