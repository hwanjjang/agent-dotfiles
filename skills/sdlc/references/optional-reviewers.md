# Additional optional PR reviewers

Source: AK's 2026-10-15 instruction. Apply to authorized SDLC PR work, in addition
to the existing required review and its provider fallback chain.

| Reviewer | Model target | Reasoning effort | Role |
| --- | --- | --- | --- |
| Grok | Grok 4.7 | high | Optional PR review only |
| Gemini | Gemini 3.8 | high | Optional PR review only |

Attempt both reviews for the current candidate when available, including when the
required reviewer has already returned PASS. Neither is a fallback slot or a
substitute for the required review. Run the two independently; failure of one does
not skip the other. Parallel execution is optional when the host supports isolation.
They remain additional contexts even if a required reviewer shares their provider.
Each assignment shares the candidate's current PR-review attempt and stage budget;
it does not create a new counter or reset an existing one.

## Selection and boundaries

Use the host's already configured authenticated launchers and current model catalog.
Resolve the named target to the actual model provider, full model ID and variant,
and observe high effort. A catalog may encode high in the model ID rather than a
separate effort setting; retain evidence of that mapping. Do not silently substitute
a different version or lower effort. If the target/configuration cannot be resolved
or verified, skip that optional review with the observed reason.

For these two additional contexts only, the named model and high effort override
the required review's latest-GA and intent-derived effort rules. Keep the required
review configuration and state receipts unchanged. Other host discovery, existing
permission and read-only isolation requirements still apply; permission-mode configuration is optional. If mode setup fails, continue with verified read-only execution under the existing permissions rather than skipping for that reason.

Use a separate context from the builder and every other reviewer. Grok and Gemini
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

The main agent publishes each completed review as an attributed PR comment using
the actual reviewer/model/effort and reviewed head. Group findings under **Required /
Recommended** with reviewer-prefixed stable IDs (for example `GROK-1`, `GEM-1`),
locations, evidence and requested action;
publish a concise clean-review result when there are no findings. Do not call a
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
Before readiness, each optional assignment must have returned or have a recorded
skip. Stop only task-owned timed-out runs within existing authority; retain partial
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
Do not place optional configurations in the mandatory `review` receipt or invent
`reviewer_slot` values for them. The state CLI validates the existing required review;
the main agent is responsible for attempting, recording and publishing these extras.

Optional availability, verdicts and publication failures do not by themselves block
readiness or replace required-review PASS. Unresolved Required findings, missing
required verification and author-selected pending fixes retain their existing gates.
