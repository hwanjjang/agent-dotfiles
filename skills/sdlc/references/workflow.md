# Routes, artifacts, and stage execution

Use the target repository's established artifact paths, recording the mapping once. Defaults are `intent/<task-id>.md`, `specs/<task-id>.md`, `plans/<task-id>.md`, and `reports/sdlc/<task-id>/` (`R/`). Spec and Plan are distinct documents, even for concise implementation tasks. Keep authored intent/spec/plan and maintained knowledge version-controlled in authorized commits; generated stage drafts, state and run outputs under `R/` remain ignored local files. Before choosing paths or committing, follow [artifact retention and commit checks](artifact-retention.md). Select required durable evidence for handoff independently of expiring CI artifacts; no gate is waived because its working files are ignored.

## Route selection

Apply the revised workflow to authorized PR tasks. Do not create state, issue/PR tracking or extra lifecycle management for non-PR work unless AK asks. The local/review-only/plan-only routes below remain compatibility and explicitly requested options.

| Mode | Work and endpoint |
| --- | --- |
| review-only | Triage → review intent → investigation and applicable existing checks → independent assessment when warranted → findings/completion. Exclude implementation, product specification, runtime smoke invented solely for process, PR creation, issue mutation, and merge unless scope is amended. |
| plan-only | Triage → intent → investigation → spec → applicable design → plan → independent assessment when warranted → completion. Test strategy may be specified, but do not claim execution or implementation evidence. |
| implementation | Triage → intent → investigation → spec → applicable design → plan with user scenarios → test-design → build → self-verification and applicable PDF manual → iterative authorized PR review/correction → final documentation check → authorized merge → completion. Stop at local or PR when that is the delegated endpoint; pre-merge completes after verified review/correction and CI with merge explicitly excluded. |

Record exclusions in the artifact index with a reason. Independent assessment is selected initially for review-only and plan-only; a bounded non-implementation task may explicitly skip it with a rationale. The revised PR implementation route excludes the separate independent-verification stage; self-verification and actual PR review remain required. A stage that runs owes its own real deliverable. Do not invent a phase solely to fill a matrix. Clarify changed scope through a dated intent amendment and assess its downstream impact.

## Skill methods

Use [stage-to-skill routing](skill-routing.md) for preparation, investigation,
design, task planning, implementation, verification and correction. This is the
single routing table; skill methods do not create competing stage records.

## Proportionate scope and evidence

Use a few observable outcomes that cover the requested behavior; there is no fixed
criterion count. Spec and plan detail should resolve the actual decisions and
failure paths, not expand every template prompt into new acceptance work. Link
adequate existing checks to the outcome they prove and renew only affected evidence.
Essential authority, transaction-safety and critical-capability evidence remains
required. Reuse is conditional on relevant scope, candidate freshness and sufficient
coverage; it never waives a required gate.

| Evidence observation | Decision | Application |
| --- | --- | --- |
| `adequate-existing` | `REUSE` | Identify the check and explain coverage/freshness. |
| `authority` | `RETAIN` | Verify the authorized action and endpoint. |
| `transaction-safety` | `RETAIN` | Verify relevant effects, failure and recovery boundaries. |
| `critical-capability` | `RETAIN` | Establish the capability on which the promised outcome depends. |
| `unsupported` | `CONSTRAIN_OR_BLOCK` | Narrow the promised behavior within authority, or report the missing capability. |
| `unrelated` | `OMIT` | Do not add verification unrelated to the scoped outcome. |

For strategy skills and deterministic tools, consume the existing host's scheduling,
briefing, notification and execution contracts. Additional infrastructure needs an
explicit request. Before runtime integration of source-derived work, identify the
intended source authority and assess method coverage and exceptions; follow the
repository's source-review guidance rather than inventing author rules or defaults.

## Endpoint contract

The endpoint records the actual delegation, not inferred authority from issue text. Existing `local`, `pr` and `main` meanings remain unchanged: local ends without remote PR actions, PR follows the established stop-at-PR contract, and main requires separately delegated integration authority. `pre-merge` is a stronger readiness obligation than merely creating a PR, with no merge action.

For an explicitly delegated pre-merge task, record the repository/branch/PR scope and specified configured personal/team accounts and independent agents in intent. That contract covers scoped implementation, applicable tests/additional smoke, commits, push, PR creation/updates, CI and review/correction, plus task code/test/evidence transfers needed among those accounts/agents. Continue without repeated routine approval. It excludes secrets, unrelated disclosures, new accounts, permission-setting mutations and production actions. Use authenticated GitHub MCP or `gh` as available; missing access is a capability gap rather than permission to change settings.

Route implementation through all applicable stages up to verified PR review/correction. Then enter the existing completion stage and produce a `merge-ready` output/receipt following the state contract. It records `merge_authorized: false`, current actual head/base, current CI/check and PR review evidence, resolved Must Fix findings, actual PR state, and remaining assumptions/risks. Merge is not-applicable; never invoke merge, enable auto-merge or enter a merge queue. Inspect whether automation is already armed/queued before claiming the PR will remain unmerged. A later request to merge requires an explicit authority amendment and refreshed evidence, not reinterpretation of the readiness receipt.

## Issue workflow integration

For authorized PR work, assess the linked issue at every applicable stage under
the [shared issue workflow policy](../../../policies/issue-workflow.md). Record
the published update URL, no useful new information, no linked issue, or the actual
publication blocker in the stage receipt. Main is the policy's coordinator for
this task. Keep non-PR work within the existing intake scope; this integration
does not require new tracking for local work. The shared policy owns issue update
triggers, publication safety, handoff and closure rules.

PR comments group concise findings into Required and Recommended, plus execution
blockers and final readiness with evidence links. Keep full schemas, model settings
and logs in task reports. Unselected recommendations end in the review record;
do not create follow-up tasks or tracking. Readiness and production-coupling
assessment inform the human handoff without authorizing or executing production.

## Deliverable handoff

The [stage templates](../assets/stage-deliverables.md) define minimum content. Record owner, status, input revisions/digests, output digests, evidence, acceptance coverage, authority source, and HOTL decision in the artifact index. Consumers read those inputs rather than rely on inherited conversation.

| Stable stage ID | Deliverable and next consumer |
| --- | --- |
| triage | `R/triage.md`: source, mode, repository/base, existing changes, facts, limits, applicability → intent. |
| intent | Canonical intent: problem, outcome, scope/exclusions, constraints, observable AC IDs, source/authority, risks/questions, revision/gate → investigation/spec and final assessment. |
| investigation | `R/investigation.md`: question, facts versus hypotheses, code/source locations, checks/results, unknowns, implications → spec or review-only completion. |
| spec | Canonical spec: requirements, interfaces/data, security/UX, normal/failure behavior, observability/migration, alternatives and verification strategy → design/plan/review. |
| design | `R/design/`: selected architect/arena design and rationale, plus applicable Archify JSON and delivered HTML with deterministic, browser, visual-review evidence and spec/code traceability → plan/review. |
| plan | Canonical plan plus user-scenarios JSON: user, goal, prerequisites, steps, expected/failure results, AC mapping; file operations, ordered work/dependencies, test commands, migration/rollback, blast radius, risks/rejected alternative/proof → builder/reviewer. |
| test-design | `R/test-plan.md` and introduced test sources: AC-to-layer/scenario map, prerequisites, expected/failure outcomes, applicability and cleanup → build/self-verification. |
| build | Actual code/tests/docs diff plus `R/build.md`: plan mapping, candidate identity, deviations, tdd or explicitly justified alternative evidence → self-verification. |
| self-verification | `R/self-verification.md`, `R/test-results.json`, `R/documentation.json` and applicable screenshot PDF manual/source, retained execution evidence: distinct test/smoke outcomes, candidate/environment, counts/commands/exit codes, eligibility → PR review. |
| independent-verification (legacy) | Historical stage ID retained for existing records; excluded from the revised PR route. No separate report or execution is required. |
| pr-review | Actual authorized PR review/comment plus `R/pr-review.md` index: stable record ID/URL, exact head/base, eligible configuration receipt, findings/verdict → corrections/merge. |
| correction | Revisioned finding-response/re-review records, corrective diff, renewed affected checks and reviewer resolution → merge. Skip with reason when no correction is needed. |
| merge | Pre-merge gate and durable post-merge receipt: expected head/base, CI/review IDs, authority, actual merge/main result and required checks → completion. |
| completion | Authorized durable PR/task record, or `R/completion.md` locally: AC outcomes, artifact index, changes/tests/review, endpoint result, risks and deployment handoff → AK. Pre-merge also requires the `merge-ready` output and receipt with `merge_authorized: false`. |

The CLI is stage-aware; future reports are not prerequisites for an earlier gate. Pre-commit requires applicable design/build/self-verification evidence, not a nonexistent PR review. Pre-merge requires current self-verification and PR review. Completion at main requires actual merge evidence. Completion at pre-merge requires current merge-ready evidence but no merge execution or post-merge artifact.

## Planning and diagram dependencies

Resolve `planning-with-files` and `archify` from the host's loaded skill catalog or actual user/repository discovery paths; record resolved paths and version/content identity. Read their SKILL.md before use. Never assume a user's absolute path, silently download a replacement, or claim a missing dependency ran.

SDLC owns task routing. Use planning-with-files as the execution notebook: one named plan ID, main as writer, canonical intent/spec/plan references, concise discoveries and checks. Children return receipts; they do not maintain competing notebooks. Follow its selected-plan initialization/resume protocol but use this workflow's 10-per-stage limit. Do not install dependency lifecycle hooks as an incidental task action. On resume reconcile actual diff, outstanding assignments, artifact freshness, and existing counters before new work. Do not access session history unless authorized.

Archify applies to ordinary development and high-risk structure/flow changes; select architecture, workflow, sequence, dataflow, or state views that aid a real design decision. For a small change unrelated to structure or flow, record a reasoned skip. Follow installed `validate`, `deliver`, and `visual-check` contracts; distinguish artifact checks, browser execution, and perceptual review. If required capability is unavailable, preserve partial design and report the missing gate. Refresh diagrams when the implementation changes the design.

## Freshness and persistence

Preserve previous receipts when requirements, candidate files, tests, or base change. Record what became stale and why; renew affected work rather than repeat unaffected passing checks. Pre-commit identity includes base plus digests of relevant changed and new files. Associate the eventual commit with matching tested content.

Keep raw working evidence local for active consumers. Preserve selected required evidence, complete required review findings and receipts in durable tracked evidence or authorized task/PR storage with stable references and content identity, sanitized of secrets and personal data. Explicitly define CI retention; temporary files and expiring CI artifacts alone are not a final handoff. Before final verification and commit, perform the retention contract's cleanup and check the actual staged candidate; before push check every actual outgoing commit. Missing checker wiring is a reported enforcement gap, not a passing check. Post-commit reviews and post-merge receipts belong in authorized durable external records tied to the exact commit, not another commit that recursively invalidates itself. Do not write directly to main to record completion.

For explicit no-write advisory work, provide artifacts inline as unpersisted and honor the limit. Before later implementation, persist and reconcile them; do not claim the earlier inline response passed persisted development gates.


## 2026-09-08 amendment

Source: AK requested an explicit pre-merge endpoint with initial scoped implementation/account/PR authority, current review and CI evidence, and concise PR comments. The completion stage now supports merge-ready handoff with merge_authorized false; existing stage IDs, per-stage counters and local/PR/main endpoint meanings are preserved.

## 2026-10-01 PR workflow

Planning owes user scenarios using [the scenario artifact](../assets/user-scenarios.json), covering acceptance criteria and feeding tests and the manual. Self-verification owes a [documentation assessment](../assets/documentation.json). For new features or UX/UI changes, retain editable manual source, a rendered and visually checked PDF, and actual screenshots from the implemented scenarios. For API/CLI features, capture actual usage/results. Include these maintained deliverables in the reviewed change; do not leave them solely in ignored reports.

Use the [review fallback and finding handoff](verification.md) for each review/correction cycle. A reviewer unable to perform required checks hands available evidence and unresolved findings to the next reviewer. Required findings cannot be waived by the author. The builder records its selection and response for every finding, applies selected changes, reruns affected checks and pushes. Repeat until reviewer PASS and no selected change remains, within existing stage budgets. Unselected recommendations remain only as review results.

Also attempt the [optional Grok 4.7 high and Gemini 3.8 high reviews](optional-reviewers.md)
and publish their attributed PR comments. They review only; availability failures
are recorded skips and do not replace or expand the required-review fallback gate.

Before final readiness, inspect all affected documents and diagrams and update them where necessary. A late document/code change goes through renewed affected verification and review. Completion records the final document check and no remaining author-selected changes. The separate independent-verification stage is excluded; its ID/history remain for compatibility. Use `upgrade-review-workflow` when adopting this revision for an existing PR task, preserving all history and counters. No additional workflow management is introduced for non-PR work.
