---
name: create-verification-skill
description: Create and qualify a project-local verification skill and feature map when an application lacks repeatable user-facing checks across its UI, CLI, API or library interfaces.
---

# Create a project verification skill

Input: target checkout, requested surfaces and an authorized test environment.
Output: one project-local `verify-<app>` skill, feature recipes and real qualification
evidence. Use existing tests and tools first. This creates verification procedures;
[tdd](../tdd/SKILL.md) remains the implementation method. Follow shared
[evidence](../../policies/evidence.md) and [security](../../policies/security.md) policies.

## Discover the target

Read the target's instructions, run commands and existing tests. Establish:

- User surfaces and entry points: UI, CLI/TUI, API or public library calls.
- Build/start commands, expected revision, fixtures, authentication and services.
- Available driving tools and observable outputs, including stored side effects.
- Isolation: owned processes, ports, profiles, data and accounts. One owner drives
  a shared instance; parallel runs need separate mutable resources.

Ask only for material facts the checkout cannot establish. A broken startup or
missing required capability is a reported blocker. Repair product/setup code only
within the task's authority; generating a verifier does not authorize unrelated
fixes, account installation, production access or publication.

## Write one local source

Use the target's existing verification location and host-supported skill layout.
If native discovery is unavailable, keep a documented source path and report
manual loading; do not claim that a file is installed. Thin client entry points
may refer to the same source. Do not overwrite an existing verifier or local
settings blindly. The collection's repository-only example is documented in the
[adoption note](../../docs/decisions/verification.md).

Write a focused SKILL.md with actual target commands and these responsibilities:

- **Launch:** reach a usable state from disposable data, including migrations and
  seeds; state the expected revision and teardown. For short-lived tools, build
  once and run each journey in an isolated process/session.
- **Doctor:** read-only checks for the owned instance, expected build, usable data
  and access. An open port or HTTP success alone is not application readiness.
- **Drive:** exercise real user entry points using observed stable handles, roles
  and accessible names, commands or public APIs. Avoid internal setters as proof.
- **Evidence:** record feature/scenario ID, input state, action, observed outcome,
  side effects and candidate identity. Use the destination's existing evidence
  contract; do not create a competing result schema. Keep raw captures local.
- **Cleanup:** stop only owned processes and reset owned fixtures even after a
  failed attempt. Keep proof artifacts outside disposable state and retain them.
- **Helpers:** include scripts only where they remove repeated work; document
  prerequisites and invocation, and actually run any new helper.

For browser tooling or before/after claims, read the relevant part of
[verification tools](references/verification-tools.md). Choose the available
capability; no particular MCP server is required.

## Seed the feature map

Create `features/README.md` and one file per user-facing feature. Start with the
most important observable journeys (upstream suggests 3–5, not a required count).
Declare the coverage boundary and unmapped surfaces; a seed is not a complete audit.
Use the [example index](references/feature-map-example/README.md) as a shape, not
as executable tooling: its Notes app and control-notes commands are illustrative.

Keep stable feature and scenario IDs, user purpose, all known entry points,
preconditions, action/expected-result pairs and gotchas. Link existing tests and
manual sections instead of repeating their content. A missing fixture or unreachable
path stays explicit; do not weaken the expected result or substitute another entry
point. Keep implementation details in code and obtain source citations during audits.
If a visual map is useful, derive its view from the maintained feature source rather
than authoring a second feature inventory.

## Qualify and hand off

Follow the new instructions end to end: launch, doctor, drive at least one mapped
journey, capture evidence and clean up. Confirm evidence still exists after cleanup.
Correct failures within scope and rerun affected steps; do not repeat an unchanged
failed attempt. If prerequisites or authority prevent execution, deliver a labeled
draft with the exact gap. One successful journey qualifies that path, not the whole
map or other clients/environments.

Report the source path, coverage, actual tools/environment, observed checks,
cleanup and limitations. Link [maintain-verification-skill](../maintain-verification-skill/SKILL.md)
for future drift checks. Under SDLC, the coordinator owns acceptance and completion;
these recipes supply execution. Screenshot-manual may consume sanitized captures,
but PDF correctness still needs its own inspection. Schedule nothing implicitly.

Source and local adaptations: [provenance](provenance.json). [MIT license](LICENSE).
