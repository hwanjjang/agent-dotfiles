# Artifact retention and commit checks

Use this contract during planning, output-path selection, cleanup, final verification,
and evidence handoff. Follow the target repository's documented retention policy;
link that policy from its AGENTS.md. This is a portable workflow contract, not an
installed Git hook or checker. Record missing enforcement as a gap, not a passed check.

## Separate maintained content from generated state

| Content | Destination and retention |
| --- | --- |
| Maintained architecture and operational knowledge | Tracked `docs/architecture/` or `docs/operations/`, or the repository's established equivalent; keep links and reproduction commands usable in a clean checkout. |
| Maintained user manual source, delivered PDF and selected scenario screenshots | Tracked documentation or the established durable documentation store; link the delivered version from the PR/docs and keep editable source and screenshot provenance. These are maintained deliverables, not disposable generated reports. |
| Reusable verification programs | Tracked `scripts/verification/` or the existing test suite; write results to ignored output paths, never over tracked fixtures or reference assets. |
| Selected dated evidence and required reference screenshots/diagram provenance | Tracked `docs/evidence/` or an authorized durable evidence store. Keep source/version, exact candidate, commands, result, content identity, and required assets together. Preserve only material needed to reproduce or assess the decision. |
| Generated state, stage drafts, raw logs, browser captures, repeated runs | Local ignored `/reports/` (including `reports/sdlc/TASK/`) and `/.archify/`; use scoped task/run directories. Keep active gate inputs until their consumers and handoff are complete. |

Authored intent/spec/plan documents may remain in their established tracked locations.
Do not commit every generated stage receipt just because the next stage must read it.
The artifact index and iteration history remain local state; preserve their content
identity and required records in the authorized handoff when another context needs them.
A copy under docs/evidence must be deliberately selected and explained, not a renamed
dump of reports. Preserve historical source documents as historical records.

When migrating tracked reports, classify and move maintained material, reference assets,
and tools first. Update links, manifests, reproduction commands and CI upload paths.
Then untrack remaining generated files while preserving local bytes and Git history;
ignore `/reports/` and `/.archify/`. Never use blanket deletion or rewrite history to
achieve a clean checkout. Verify tracked documents resolve without local reports.

## Evidence availability and handoff

Define CI artifact expiration explicitly in the target workflow and retention policy:
which outputs are uploaded, retention duration, owner, and where essential evidence
survives expiration. An expiring CI download URL is not the sole durable record.
Keep required decisions, PR review findings and verdicts,
acceptance results, exact head/base or file digests, commands/environment, required
reference images and reproduction/provenance data in selected tracked evidence or an
authorized durable task/PR/store record for the lifetime required by that repository.
Verify recipients can retrieve it; record location and content identity. Sanitize secrets
and personal data. Preserve full required structured findings and configuration receipts,
not just a PASS summary. Bulky repeat logs may expire once required evidence is retained.

For transfer to a PR reviewer, provide the actual indexed input files and
matching digests through an authorized scoped bundle or durable store; the receiver
materializes local files under the task root and revalidates them. The state CLI still
requires real local files for its file references. Do not replace them with URL strings,
empty placeholders, or weaker gates. Neither ignored status nor a retention summary
proves eligible PR review occurred.

Before final handoff, confirm selected durable records survive both removal of the
local reports directory and expiry of disposable CI artifacts. A promised future upload
is not evidence. If required access or retention is unavailable, report the gap and keep
the dependent readiness gate incomplete. Post-commit review/post-merge records belong
in authorized durable task/PR storage tied to the exact revision; do not create recursive
evidence-only commits that invalidate their own candidate identity.

## Cleanup before final verification and commit

1. Inspect status and proposed file changes. Classify maintained docs/tools, selected
   evidence, and generated output; preserve other contributors' work.
2. Move/update maintained material and references, set ignored output paths and CI
   retention, and remove generated files from the proposed commit without deleting local
   files. Preserve active state, raw inputs needed by verification, and required provenance.
   Remove disposable task-owned scratch only when its consumers no longer need it and
   removal is authorized. Do not use broad clean/reset commands.
3. Run final checks and applicable smoke on the cleaned candidate. Confirm tools leave
   tracked content unchanged. Revalidate evidence freshness after relevant changes.
4. Stage only intended changes and run the repository's read-only content checker against
   the actual index. Resolve failures explicitly, re-stage intentionally, and rerun affected
   checks. Working-tree success does not prove the staged candidate passes.

## One read-only checker, three entry points

When implementing or auditing repository enforcement, require the same checker from
pre-commit, pre-push, and CI, including documentation-only changes. Its explicit input
mode determines the snapshot; it must not delete, rewrite, stage files, or modify the
index. Hooks only select inputs and return results. Verify both success and failure leave
index and working files unchanged. Do not silently install hooks as a side effect of
using this skill; wire them only within the authorized task.

- **Pre-commit:** inspect staged/index bytes and paths, not working files. Reject forced
  additions below `/reports/` or `/.archify/`. Resolve maintained-document links against
  the index snapshot so untracked/local-only targets and staged/unstaged mismatches fail.
- **Pre-push:** derive the actual outgoing commit set from pushed refs and remote state;
  inspect every outgoing commit and its own tree, not just HEAD or a combined diff.
  A generated file added in one outgoing commit and removed in a later one still fails.
  Handle new branches and multiple updated refs explicitly; report unresolved ranges
  rather than claiming a clean final tree proves history is clean.
- **CI:** run the same checker against the PR/push commit range and relevant snapshots,
  with enough history/ref information to establish the range. Check maintained-document
  links against the corresponding committed tree, independently of runner-local output.
  No path filter may omit documentation-only changes.

Keep checker path/commands, range selection, and observed results in verification
records. If the target repository lacks this checker or wiring, record that limitation
and implement it only when in scope. Skill prose and the SDLC state validator do not
provide Git enforcement. Preserve existing test, self-verification, eligible PR
review, freshness and authority gates regardless of checker success.
