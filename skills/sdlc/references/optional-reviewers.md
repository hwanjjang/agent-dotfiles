# Additional optional PR reviewers

Source: AK's 2026-10-15 instruction, amended 2026-10-17: when the required and
additional reviewer are the same, run once and share the result. Apply to
authorized SDLC PR work. Required reviewer eligibility and fallback still apply.

| Reviewer | Model target | Reasoning effort | Role |
| --- | --- | --- | --- |
| Grok | Grok 4.7 | high | Additional review, or shared with required review |
| Gemini | Gemini 3.8 | high | Additional review, or shared with required review |

## One assignment per reviewer

Resolve the required and additional roster before dispatch, and reconcile it again
when required fallback changes. Match the actual model provider, not account,
launcher or role labels: Grok is xAI; Gemini is Google. An effort difference alone
is not a reason to create another reviewer.

- When a required reviewer also covers a listed provider, use one independent
  assignment for both roles. Keep the required review's latest-GA model and all
  its eligibility/coverage checks. The shared run defaults to **high**; explicit
  task-scoped effort authority takes precedence. Do not launch required Grok
  medium plus additional Grok high for the same candidate.
- Attempt only additional providers not covered by that required assignment.
  Distinct reviewers remain independent; an optional failure does not skip the
  other provider. Parallel execution remains optional.
- If that reviewer is already running or has returned, inspect its context,
  actual settings, exact head/base, scope and evidence before reusing it. Complete
  missing required checks in the same independent context when possible. Never
  relabel medium as high, count one result as two independent opinions, or rerun
  an unchanged passing review merely to satisfy an additional role's preset.
- A shared review must meet every required gate; an optional-only permission
  exception or partial review cannot become required PASS. If it cannot proceed,
  retain its findings and advance the required fallback. Record the failed
  additional attempt too instead of retrying the same unavailable reviewer.

For example: required Claude plus additional Grok/Gemini are distinct assignments.
If Claude is unavailable and required fallback selects Grok, share that Grok review
and attempt only Gemini separately. Both roles link to one context, verdict and
publication record; a shared failure is still a required-review failure.

Assignments share the candidate's current PR-review attempt and stage budget;
sharing roles creates neither another counter nor a reset.

## Selection and boundaries

Use the host's already configured authenticated launchers and current model catalog.
Resolve the named target to the actual model provider, full model ID and variant,
and observe high effort. A catalog may encode high in the model ID rather than a
separate effort setting; retain evidence of that mapping. Do not silently substitute
a different version or lower effort. If the target/configuration cannot be resolved
or verified, skip that optional review with the observed reason.

For separate additional assignments, use the table's named model/high defaults.
For a shared assignment, apply the selection above and record its actual model;
do not claim that a different pinned optional model was run. The
[state contract](state-contract.md#shared-review-records) defines the one required
receipt and additional-role reference. Other host discovery, permission and
read-only isolation requirements still apply; permission-mode configuration is
optional. If mode setup fails, continue with verified read-only execution under
existing permissions rather than skipping for that reason.

Use a separate context from the builder and other distinct reviewers; shared roles
use the same reviewer context. Grok and Gemini
must not participate in implementation or correction in this SDLC workflow. Give
them the current PR URL, exact head/base and diff, requirements, applicable policy,
self-verification evidence and unresolved finding/response history. Their task is
to inspect and return review findings, evidence and a verdict. No source edits,
implementation, commits, pushes, merge, permission changes or further delegation.
Run authorized checks only in isolated scratch when they would write files.
Keep the author worktree read-only and verify tool/network/external-write restrictions;
immutable input alone is insufficient. Use supported read-only tools or an isolated
input checkout combined with existing restrictions. Verify the boundary before launch; otherwise skip for unverifiable
isolation. Deny requests to implement or write sources and send suggested fixes to
the builder. Reject and report a result that changed reviewed sources; recover only
task-owned effects within existing authority, preserving other contributors' work.

## Results, comments and corrections

The main agent publishes each distinct completed review once as an attributed PR comment using
the actual reviewer/model/effort and reviewed head. Group findings under **Required /
Recommended** with reviewer-prefixed stable IDs (for example `GROK-1`, `GEM-1`),
locations, evidence and requested action;
publish a concise clean-review result when there are no findings. Name both roles
when sharing a result; do not duplicate its comment. Do not call a
partial/failed run PASS. Reviewer agents return results to main rather than writing
to GitHub themselves. Read current comments before posting to avoid duplicates.
If publication fails, retain the result and record the failure; do not claim it was
posted. Reconcile current remote comments before one bounded retry. Report any
undelivered optional comment in the handoff. Include unpublished findings in the
consolidated review anyway. Failed required/consolidated publication retains the
existing incomplete required-review gate.

The builder assesses every finding, applies selected fixes, verifies and pushes.
Preserve the existing finding schema and response rules. Deduplicate matching
findings while retaining every originating ID and reviewer attribution. Feed all
findings into the required review/correction record; an optional origin does not
waive a Required finding. Every Required finding is retained in `R/pr-review.md`
and the correction record. If it arrives after required-review PASS, suspend readiness
and renew the required review with that ID and its reviewer resolution before
claiming readiness again. A builder rebuttal follows the existing escalation path.
Renew affected reviews after changes, within the existing stage iteration budget.
If an optional originator cannot re-review, the required independent reviewer may
resolve its finding with explicit rationale and evidence. The builder cannot close
it alone. Unselected recommendations receive no follow-up tracking.

## Skip and records

Skip on an observed rate/quota limit, service outage, authentication/tool failure,
deadline exceeded without a complete return, or unavailable/unverifiable model,
effort or read-only isolation. Mode selection or observation failures alone are not skip reasons. Give each assignment a bounded deadline at dispatch.
Before readiness, each additional target must have a returned review, a reference
to its shared required review, or a recorded skip. Stop only task-owned timed-out
runs within existing authority; retain partial
findings. A late returned Required finding triggers the same readiness reassessment.
Record target, attempted
configuration, timestamp, exact reason and observation. Do not repeatedly retry the
same failure or wait for quota reset. An observed change in availability permits a
later bounded attempt within the same stage budget. No new accounts, authentication
or permission changes are authorized to obtain an optional review.

Keep completed, partial and skipped outcomes in the PR-review index and durable
handoff. Include context, actual model/configuration, head/base, findings and the
published comment URL/ID when present. Mention skipped targets and reasons once in
the consolidated PR review/readiness comment; a skip is neither PASS nor a finding.
Separate optional-only configurations stay outside the mandatory `review` receipt;
do not invent `reviewer_slot` values. A shared result uses the actual required slot
and the [shared-review record](state-contract.md#shared-review-records), with one
finding/disposition history. The CLI checks receipt eligibility, not launcher calls;
main is responsible for deduplicating dispatch and publication.

Optional availability, verdicts and publication failures do not by themselves block
readiness or replace required-review PASS. Unresolved Required findings, missing
required verification and author-selected pending fixes retain their existing gates.
