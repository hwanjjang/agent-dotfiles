---
name: maintain-verification-skill
description: Audit or repair an existing project verification skill and feature map against source and real user journeys when verification instructions may have drifted.
---

# Maintain a project verification skill

Input: an existing project-local verifier, requested coverage and authorized test
environment. Output: an evidence-backed audit, or verified repairs when authorized.
Read the target's instructions and verifier. Follow shared [evidence](../../policies/evidence.md)
and [security](../../policies/security.md) policies. This is not a mandatory audit
on every edit and does not add an SDLC stage.

## Scope and ownership

Locate the verifier and its feature index. If several targets remain plausible,
resolve the target before driving; if none exists, point to
[create-verification-skill](../create-verification-skill/SKILL.md).
An audit-only request does not authorize edits. Repairs are confined to the selected
verifier, feature recipes and owned harness helpers. Product regressions are findings,
not permission to change product code or rewrite expectations to match broken behavior.
PRs, issues, installation and production actions require existing task authority.

## Audit and exercise

1. Compare the index with its feature files and current user-facing surfaces.
   Identify missing/dead/duplicate entries and cite actual source for suspected
   drift. Keep an explicit requested subset; do not infer completeness from an
   incomplete seed map or silently drop unreachable features.
2. Read source per feature. Return user behavior, source entry points, suspected
   drift and one concise live recipe. Work directly unless useful delegation is
   authorized; independent read-only source checks may run in parallel. Reviewers
   do not manipulate a shared application session.
3. Reconcile recipes, then run the target's launch/doctor/drive instructions. A full
   audit exercises every mapped feature and the entry points claimed by its recipes;
   a subset report names both covered and untested paths. Source review alone does
   not establish runtime coverage. One coordinator drives shared state; independent
   sessions require isolated ports, profiles, accounts and data.
4. Recheck doctor after surprising behavior or a new session. Reset a wedged UI
   instead of repeatedly clicking. Preserve failed-attempt evidence and clean up
   owned residue. A documented prerequisite that is unavailable is blocked/not-run,
   not a verified feature. Missing prerequisite documentation is also map drift.
5. Classify findings: **document drift**, **harness gap**, or **product regression**.
   For authorized repairs, preserve intended assertions and user paths. A locator
   repair is justified only when the intended behavior still exists. Never turn a
   required failure green by deleting assertions, skipping tests or lowering the
   requirement. Use [tool guidance](../create-verification-skill/references/verification-tools.md)
   when considering automated test repair.
6. Re-drive affected recipes after repairs; reuse unaffected evidence only when
   candidate/environment relevance is established. A failed repair with the same
   cause is a blocker until new evidence supports another attempt. Finish teardown
   and confirm proof artifacts survive, including on failure.

## Report

State scope, candidate, feature/scenario IDs, actual tools and results, evidence,
cleanup, unresolved findings and untested paths. Keep run notes in the target's
ignored artifact area. Do not copy private raw evidence into public documentation.

- **clean:** all requested source/live coverage completed, no correction needed.
- **findings:** audit completed with actionable drift/gaps/regressions; no repair
  authorized. Keep any failing feature outcome explicit.
- **changed:** authorized verifier repairs were exercised successfully; name any
  remaining product failures separately. This is not a product readiness verdict.
- **blocked:** required coverage or safe repair could not finish; identify the
  attempted path and concrete unmet prerequisite. Completed partial evidence stays valid.

A subset clean result never means the whole application is verified. Publication
is separate from these outcomes. Under SDLC, feed results to its existing evidence
contract; update linked manual sections when their user steps changed.

Source and local adaptations: [provenance](provenance.json). [MIT license](LICENSE).
