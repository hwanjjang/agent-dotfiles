# Stage deliverable templates

Copy the applicable section into its canonical task file. Replace prompts with actual facts and evidence; remove these authoring instructions. Unresolved required content cannot be marked complete. Reuse an existing authoritative document after checking its content/revision. Preserve dated amendments when intent or design changes.

Follow [artifact retention](../references/artifact-retention.md): `reports/sdlc/TASK/`
paths below are ignored local working records, not commit destinations. Keep maintained
knowledge/tools and selected durable evidence separately. Every artifact/evidence index
records storage class, local path/digest, required consumers, durable handoff location,
CI expiration/retention owner where applicable, and confirmed retrieval status.

Every deliverable begins with:

| Field | Recorded value |
| --- | --- |
| Task / stage / owner | Stable task and stage IDs; actual author role/context |
| Date / revision | Revision or content identity |
| Source / authority | Request reference and authorized scope/endpoint |
| Consumed inputs | Artifact paths with exact revisions/digests and read acknowledgment |
| Acceptance criteria | Applicable observable AC IDs |
| Candidate / base | Actual head/base, or base plus pre-commit candidate file digests |
| Status / decision | Artifact status and separate PROCEED, NEEDS_HUMAN or BLOCKED |
| Reason / evidence / next action | Concrete assessment and durable evidence references |
| Issue update assessment | Material update posted with comment URL, no useful new information, no linked issue, or actual publication blocker |

## Triage: reports/sdlc/TASK/triage.md

- Request/issue and connected PRs; what is requested versus inferred.
- Repository, target branch/base and existing local/remote work.
- Mode, change kind, endpoint and explicit exclusions.
- Observed facts, suspected causes and unknowns.
- Authority source, access/side-effect constraints and stricter local rules.
- Applicable stages and reasons for excluded stages; artifact path mapping.
- Selected execution plan ID/owner and dependency capability records.

## Intent: intent/TASK.md

- Problem and supporting facts; affected users/systems.
- Desired outcome and a few observable acceptance criteria with stable IDs; group related evidence under outcomes rather than implementation steps.
- In scope, out of scope and constraints.
- Task mode and authorized actions/endpoint with source. For pre-merge: scoped implementation/test/smoke/commit/push/PR/CI and code/test/evidence transfer among specified configured accounts/agents; excluded secrets/new accounts/permission changes, merge/auto-merge/queue and production.
- Assumptions, risks and open questions; resolution evidence.
- Intent gate and consumers (spec, builder, reviewer).
- Dated amendment history: source, reason, changed scope/ACs, superseded revision and downstream impact.

## Investigation: reports/sdlc/TASK/investigation.md

- Precise question and observed symptom.
- Sources/code paths and verified facts, separated from hypotheses.
- Reproduction or existing checks: environment, command/procedure, actual result, evidence.
- Root-cause support and counterevidence; uncertainty and missing access.
- Findings with location, evidence, impact, verification, confidence and required/recommended findings.
- Implications for the spec or review-only conclusion.

## Specification: specs/TASK.md

Use [to-spec's content contract](../../to-spec/SKILL.md#content-contract) for the
canonical specification; do not maintain a separate SDLC spec template here.
The stage handoff records its path/revision, consumed intent/investigation
revisions, unresolved decisions and readiness under the existing receipt contract.

## Design: reports/sdlc/TASK/design/

- Selected design and rationale; record architect/arena use or a justified exclusion under [skill routing](../references/skill-routing.md).
- Diagram type and decision it supports; source JSON and delivered HTML identities.
- Mapping from diagram elements to spec requirements and actual code evidence.
- Resolved Archify contract/version and commands used.
- Separate deterministic validation/delivery results, browser evidence and visual-review observations.
- Changes required or verified outcome; dated design amendments after implementation drift.

## Plan: plans/TASK.md

- Intent/spec/design consumed revisions.
- Mandatory user scenarios: stable ID, user, goal, prerequisites, ordered steps, expected results and relevant failure paths; map to ACs/tests and manual sections. Retain a user-scenarios output using [the JSON template](user-scenarios.json).
- Files to add/change/delete and why; boundaries that must stay intact.
- Ordered implementation steps, dependencies and owner.
- Existing adequate checks to reuse with coverage/freshness rationale; missing tests to write/run, expected Red cause or justified alternative, additional local smoke, checks and artifact verification.
- Migration, rollback and blast radius.
- What could break; riskiest part; rejected alternative and reason; proof of correctness.
- Parallel lanes, if any: disjoint files, dependencies/conflicts and combined-candidate verification.
- Cleanup before final verification/commit; maintained document/tool destinations,
  ignored output paths, selected evidence and CI retention/retrieval plan.
- Shared read-only checker path, staged/outgoing/CI commands and range selection;
  missing wiring and whether implementation is in scope.
- Remaining decisions, risks and stage gate.

## Test design: reports/sdlc/TASK/test-plan.md

| AC | Layer / scenario ID | Required or justified exclusion | Expected observable behavior | Failure condition | Existing/new test |
| --- | --- | --- | --- | --- | --- |
| Record actual criterion | Record actual test layer | Record applicability | Record assertion | Record explicit failure | Link source/procedure |

- Change classification, selected verification mode and test-first sequence or justified alternative. For alternative mode, record `tdd_exception.reason`, `attempted` and `limitation`, scenario-linked coverage and separate smoke evidence under [the verification contract](../references/verification.md#tdd-method-and-alternative-evidence).
- Scenario prerequisites/environment/data, actions, expected/failure results, command/procedure and cleanup (use smoke template where applicable).
- Relevant normal, error, authorization, boundary, retry/duplicate, transition and concurrency coverage; reasons for exclusions.
- Known capability/environment gaps marked blocked/not-run.

## Build: reports/sdlc/TASK/build.md

- Plan-step-to-diff mapping and changed files with purpose.
- Candidate identity and author/provider/context.
- Deviations, reasons and upstream amendments.
- Actual execution IDs/results/evidence under the selected tdd or alternative verification mode; applicable post-change checks and refactor/non-executable rationale.
- Documentation/observability updates; applicable user manual source, screenshots and rendered PDF; remaining risks.

## Self verification: reports/sdlc/TASK/self-verification.md

- Exact tested candidate/base, environment and dependencies.
- Focused verification/regression executions distinct from additional local functional smoke and other checks.
- Scenario required/total/executed/pass/fail/blocked/not-run/not-applicable counts, consistent with machine-readable results.
- Commands/procedures, timestamps, exit codes, actual observations and durable evidence.
- Mock boundaries versus actual integration; failures and corrections.
- Acceptance coverage, semantic assessment, freshness and pre-commit eligibility.
- Link local machine-readable test-results.json in the validator's supported format.
- Cleanup outcome, preserved gate inputs, tracked-file status before/after tools,
  actual index checker result, outgoing/CI range results when applicable, and gaps.
- Selected durable evidence, retention/expiry, and verified recipient access; preserve
  the complete required verification/review receipts beyond disposable artifact expiry.

## Documentation assessment: reports/sdlc/TASK/documentation.json

- Required self-verification output in the PR route; use [the JSON template](documentation.json).
- Check affected user/API/operations docs, README and diagrams; explain updates or why none are needed.
- New features or UX/UI changes require actual scenario screenshots, editable manual source and a rendered/visually checked PDF in maintained documentation storage.
- Include hashed references to updated maintained documents and manual assets; verify clean-checkout/durable access.
- Final completion confirms this assessment is still current; late changes require renewed affected verification and review.

The independent-verification stage is historical only in the revised PR route; no separate deliverable is required.

## PR review: reports/sdlc/TASK/pr-review.md

- Actual PR review/comment URL and stable record ID; publication status.
- Exact reviewed base/head and consumed upstream revisions.
- Author/reviewer providers and contexts, exact latest GA reviewer model, observed effort under [current selection](../references/optional-reviewers.md#one-assignment-per-reviewer), verified read-only boundary/evidence, optional honest requested/observed permission mode, host/isolation.
- Current model-selection source/timestamp and actual execution receipt; profile/account labels separately from actual provider identity.
- Reviewer slot, unavailable earlier reviewers and actual failure evidence; received finding IDs, author responses/fixes and remaining checks.
- Review scope/lenses and fixed-schema findings:

`ID | Required/Recommended | Severity | Category | Location | Finding | Evidence | Impact | Reproduction/Verification | Related requirement/policy | Confidence | Author response/selection | Reviewer resolution`

- PASS, CHANGES_REQUIRED or NEEDS_HUMAN with evidence; actual repository approval status separately.
- Concise Required/Recommended PR comments plus blockers/final readiness; full evidence/configuration in this report.
- Unselected recommendations end here; no follow-up issue, owner, reminder or separate tracking.
- PASS plus no remaining author-selected changes before completion.

## Correction and re-review: revisioned review record

- Finding ID, author acceptance/rebuttal or unselected recommendation reason, supporting evidence; preserve IDs across reviewer replacements.
- Corrective diff/candidate, affected upstream artifacts and test/smoke reruns.
- Reviewer examination/resolution and updated verdict on exact revision.
- Unresolved Must Fix items and human decisions; never author-only closure.
- Evidence reused with explicit unchanged-scope rationale and relevant stage iterations consumed.

## Merge: authorized durable PR/task record

- Pre-merge expected head/base, authority source and endpoint.
- Current artifact validation/content assessment, self-verification, review record/verdict, finding resolution and CI/check IDs.
- Repository protections, merge method/queue and deployment-coupling assessment.
- Actual merge operation/result, stable record ID and resulting main commit.
- Remote PR/main readback and required post-merge checks.
- Uncertain-result reconciliation before any retry.

## Pre-merge readiness output within completion

- Output kind: `merge-ready`; no new stage and no merge execution.
- Receipt: `merge_authorized: false`, following the current state contract.
- Authorized scope/account/agent contract source and explicit endpoint.
- Actual current PR/head/base and timestamp/readback source.
- Current required CI/check IDs, outcomes and tested integration identity.
- Self-verification and eligible PR review receipts, resolved Must Fix findings and latest verdict.
- Actual unmerged state and auto-merge/queue status; no automatic integration enabled or queued.
- Production coupling, assumptions, unresolved risks and later human decision; no execution.
- Concise final ready/not-ready PR result with durable evidence references.

## Completion: durable task record or reports/sdlc/TASK/completion.md

- Outcome per AC and complete artifact/evidence index.
- Changed files and reasons; actual test/smoke scenarios/results and limitations.
- Self-verification and PR review state; final documentation/diagram check and no remaining author-selected changes.
- Actual authorized endpoint reached, PR/main commit when applicable.
- Assumptions and unresolved risks; unselected recommendations remain in the review record without separate management.
- Human deployment handoff; no claim of production deployment or observation performed by this workflow.
- Durable decisions/evidence index, recipient retrieval check, CI expiration and owner;
  report any required evidence that would disappear with local files or expired artifacts.
- For no-write advisory work: explicitly label inline artifacts unpersisted.

## Exhausted stage report

- Stable task/stage, objective and iterations 1 through 10.
- Each attempted approach, observed result and evidence references.
- Remaining gap, risk, dependency impact and `iteration-limit-reached` BLOCKED status.
- Recommended human decision; independent unaffected work that may continue.
- No automatic counter reset, nominal stage rename or attempt 11.


## Template amendment — 2026-09-08

Source: AK's pre-merge, reviewer and PR communication update. Superseded: maximum-effort/auto-only reviewer prompts. Current prompts require latest GA actual other-provider model, observed medium effort and effective auto/full mode. Pre-merge completion retains merge-ready evidence with merge_authorized false and never asks for a fictitious merge receipt.

## Template amendment — 2026-10-01

Use the current PR route: required user scenarios, documentation/manual evidence, self-verification then iterative PR review without a separate independent-verification report. Follow ordered reviewer fallback with stable finding handoff. PR comments contain Required/Recommended findings; unselected recommendations receive no follow-up tracking.

## 2026-10-03 reviewer effort authority amendment

Use [effort authority](../references/state-contract.md#reviewer-effort-authority) and [shared-review records](../references/state-contract.md#shared-review-records) for current selection and receipt requirements. Preserve historical execution settings; do not relabel observations or infer new launch authority.
