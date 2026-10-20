# Verification, review, and integration evidence

## Classify before creating tests

| Change kind | Required approach |
| --- | --- |
| behavior | Use the single tdd method; retain test-first evidence or the explicit alternative contract below, then separate local functional smoke before commit. |
| refactor | Establish existing passing behavior tests before edit and keep them green; then additional affected local smoke. Never break correct code to manufacture Red. |
| non-executable | Proportionate content/link/schema/format checks. Runtime smoke and artificial TDD are not applicable. |
| configuration | Active skills, prompts, hooks, instructions and CI change behavior even in Markdown. Use tdd or an explicit alternative for relevant behavioral evaluations/executable checks, with separate functional verification; product smoke only when product runtime is affected. |

Mixed changes apply the appropriate checks to each part. Missing credentials/environment/dependencies means blocked or not-run, not not-applicable. Reuse adequate existing scenarios and repository tooling; create only coverage that is missing.

## TDD method and alternative evidence

Read [tdd](../../tdd/SKILL.md) for the method and practical exceptions. It is the
single TDD authority; this section owns only SDLC evidence and integration gates.
This contract supersedes conflicting test-first absolutes in historical imported
policy text. Target-project requirements and essential checks remain binding.

- `verification_mode: tdd` (default for existing records): retain intended `red`,
  `green`, applicable `post-refactor`, then separate `smoke` executions. Declare
  `refactor_performed: false` only when no edits followed Green; otherwise a
  current passing post-change check is required. Omitting that field preserves
  legacy mandatory post-refactor evidence.
- `verification_mode: alternative`: when test-first is impractical under tdd,
  record `tdd_exception.reason`, `attempted`, and `limitation`. Run focused
  `alternative` checks against the real behavior, each tied to a scenario; cover
  every acceptance criterion, then run separate integrated `smoke`. Do not include
  fabricated Red/Green phases or call the result TDD. A reason alone cannot pass.
- A missing required environment, unresolved failure or unobservable promised
  behavior is blocked/not-run, not an alternative success. Review the semantic
  adequacy of the checks; the validator cannot determine whether prose is true.

Refactors and non-executable changes retain their own classification above.
The scope of smoke follows the changed capability: an isolated skill evaluation
can exercise instruction behavior; product runtime checks apply only when affected.

## Intent and side-effect decision rubric

Before writing expected assertions, derive the safety contract from user intent:
identify required retained behavior, observed baseline, optional enhancements,
allowed terminal actions and forbidden side effects. Inspect what an action changes,
including external effects and cleanup. Challenge the test oracle against that
contract before interpreting passing assertions. A green test can encode a wrong
expected action; correct the assertion and behavior rather than repeating it.

Apply the first matching observation below. These are requirement judgments, not
suite statuses: keep every actual test failure and unmet enhancement criterion in
the result record. A safe baseline alone does not complete a required enhancement.

| Observation | Decision | Required interpretation |
| --- | --- | --- |
| `forbidden_effect` | `REJECT` | An effect outside user authority or safety invariants is wrong even when all assertions pass. |
| `unknown_baseline` | `UNVERIFIED` | Observe the baseline before claiming retention or loss; unknown state cannot authorize recovery. |
| `confirmed_baseline_loss` | `RECOVERY_REQUIRED` | A known required baseline was lost; use requirement-defined recovery within existing authority. |
| `accepted_terminal` | `ACCEPT_TERMINAL` | The requested terminal action completed and retained invariants hold; do not reverse or recreate it without authority. |
| `optional_enhancement_failed` | `BASELINE_SAFE_ENHANCEMENT_FAILED` | The optional improvement failed while required baseline remains intact; preserve the baseline and report the failed improvement separately. |
| `conforming` | `ACCEPT` | Required effects and retained invariants agree with intent; still require applicable tests and evidence. |

Independent reviewers challenge their task's user intent and actual observations
before reading expected decisions. Task-specific fixtures are evaluation evidence, not universal required files in
installed skills or other projects.
The executable rubric fixture only checks encoded decisions; it does not demonstrate
that a model follows prose, establish product correctness or replace PR review.

## Project verification procedures

Use the [stage routing](skill-routing.md) to resolve a project-local verifier and
feature recipes. Plans link affected feature IDs to scenario IDs and acceptance
criteria; execution uses the verifier’s actual launch, doctor, drive and cleanup.
Keep its results in this contract’s existing candidate-bound evidence records.
A seed map or one qualification journey does not establish full product coverage.
Run the full maintenance audit only when requested or needed to resolve drift;
ordinary changes exercise affected paths plus integrated smoke. Test auto-repair
must preserve expected behavior. A required skipped, unreachable or failed path
remains a gap; never convert it into success by changing assertions.

## Test design and execution

Use [the smoke template](../assets/smoke-scenario.md) before implementation. Map every AC to actual test layers and applicable scenario IDs. Cover success and relevant errors, authorization/boundaries, retries/duplicates, transitions and concurrency. State prerequisite environment/data, actions, observable success, explicit failure, executable command or reproducible procedure, required status, side effects and cleanup. Use approved facilities for external side effects.

For behavior fixes, setup failure is not intended Red. Retain actual executions under the selected verification mode above. Additional smoke verifies integrated functionality/runtime wiring beyond the TDD checks; rerunning the same unit test under a smoke label is insufficient. HTTP 200, process startup or screenshot existence alone does not prove behavior. If smoke reveals a defect, return to the tdd method and renew affected evidence before rerunning smoke.

Before retrying a full suite, reconcile the prior process identity, current
status, result and cleanup. Wait for it or stop only a task-owned process within
existing authority; do not start a competing retry while its state is unknown.
For intentional concurrent lanes, isolate temporary directories and fixture-lock
namespaces even across separate worktrees. Capture the first failure's command,
exit code and output before retrying. Distinguish product/assertion failures from
missing dependencies, permissions and resource/lock contention; a setup failure
is not regression Red. Retain separate retry results and cleanup evidence. A
successful isolated retry does not turn the first failed overlap into a pass.

Before each commit containing applicable implementation changes, verify matching candidate content has passed required tests and additional local smoke. Use a supported local runtime/emulator/database/browser appropriate to the component. Later CI/shared-environment success cannot substitute. Record base and digest of relevant candidate files including new files, then associate the eventual matching commit. Later relevant edits require renewed evidence; document an impact rationale for unchanged reusable checks.

Test results record stable execution/scenario IDs, linked ACs, layer, required/applicability status, actual command/exit code, environment, mocked versus real integration, candidate identity, observed outcome, timestamps and durable sanitized evidence. Use outcomes passed, failed, blocked, not-run, or not-applicable. Check scenario coverage, unique records, result counts and freshness with the state validator. A validator accepting structure cannot confirm truth or semantic sufficiency; the builder and PR reviewer must do that.

## Cleanup, retention, and content checks

Before final verification and commit, apply [artifact retention and commit checks](artifact-retention.md):
separate maintained content from ignored generated output, preserve gate inputs and
selected durable evidence, then verify the cleaned candidate. Record the read-only
checker command and staged snapshot, outgoing range or CI range actually checked,
including documentation-only changes. Exercise forced generated-file additions,
local-only links, staged/unstaged mismatches and add-then-delete outgoing history
when verifying checker implementations; confirm index and worktree immutability on
both success and failure. Missing enforcement remains an explicit gap.

Check that maintained docs and reference assets work in a clean checkout; verification
tools may generate ignored output but must leave tracked content unchanged. Define CI
retention and verify essential evidence remains available after artifact expiration.
Give the PR reviewer actual indexed files/digests and record verified receipt;
local ignored reports alone are not a cross-context or final durable handoff.

## PR review and reviewer fallback

Keep the required review/fallback below and apply the
[additional reviewer selection and sharing rules](optional-reviewers.md). Their attributed
PR comments and findings join this review cycle; their availability does not add a
required gate. Follow that contract for skipped runs and finding-resolution handoff.

Supply upstream artifact index, intent/spec/plan revisions, request/ACs, policy, exact base/head and diff, builder self-verification, user scenarios, documentation/manual and test/smoke evidence. Do not seed the reviewer with the expected conclusion. PR review challenges acceptance, actual behavior, evidence and the change; there is no separate independent-verification stage or report in the revised PR route.

PR review uses [host eligibility](host-adapters.md), then checks requirements, normal/error behavior, retries/concurrency, security/data, external effects, coverage, architecture, documentation, operation and rollback. Passing CI or smoke does not replace review.

Use the review method through [stage-to-skill routing](skill-routing.md), inside
each selected reviewer context. Include its resolved source with the review inputs;
method invocation is not another reviewer assignment. This contract owns the
required receipt and finding lifecycle; the focused skill owns inspection technique.

Finding schema:

`Severity | Category | Location | Finding | Evidence | Impact | Reproduction/Verification | Related requirement/policy | Confidence | Disposition`

Severity is BLOCKER, HIGH, MEDIUM, LOW, or NIT. BLOCKER/HIGH are Must Fix; lower-severity requirement or policy violations are also Must Fix. Recommended findings may be left unselected with a concise reason in the review record. Do not create follow-up issues, owners, reminders or separate tracking. Include NITs, if useful, under Recommended. Review verdicts are PASS, CHANGES_REQUIRED, or NEEDS_HUMAN, distinct from stage HOTL decisions. PASS requires no unresolved mandatory finding or missing mandatory verification.

Publish an actual PR review/comment only within the authorized workflow and link its stable ID/URL in `R/pr-review.md`. Publish concise findings grouped under **Required / Recommended**, execution blockers and a final readiness result. Include each stable finding ID, location, problem and requested action. Keep full schemas, model receipts and repeated logs in linked reports. Use the [issue workflow integration](workflow.md#issue-workflow-integration) for stage issue records; keep detailed code review results on the PR. Local output is not a published review; tool success and absent replies are not PASS. Separately honor repository approval requirements and unresolved human change requests.

The author responds to every finding with an application decision, evidence-based rebuttal or a reason for leaving a recommendation unselected. Only reviewer resolution can close/downgrade a Must Fix finding; escalate unresolved disagreement. The author applies selected changes, renews affected tests/smoke, pushes and requests reviewer examination of the changed candidate. Repeat until the reviewer returns PASS and the author has no remaining selected changes. Preserve old receipts and record reuse rationale for unaffected evidence. Re-entry consumes the applicable stage's remaining iteration allowance.

## Pre-merge readiness and integration gates

At the explicit `pre-merge` endpoint, implementation, applicable TDD/additional smoke, commit/push, PR updates, CI, eligible PR review and necessary corrections proceed within the initial contract. Verify actual current PR head and target base, current required CI/check IDs, review coverage and resolved Must Fix findings. If head/base changed, refresh affected evidence before claiming readiness. Keep the PR unmerged and inspect existing auto-merge/queue state; readiness cannot be claimed while an automatic merge is armed or queued. Report and resolve that conflict within actual authority before completion.

Use the existing completion stage to produce a `merge-ready` output with a receipt containing `merge_authorized: false`, source PR/record, exact head/base, current checks, review/self-verification references and no unresolved mandatory findings. Follow the executable [state contract](state-contract.md) for fields. This is no new stage and does not consume or imply a merge iteration. The merge stage remains not-applicable at this endpoint. Never merge, enable auto-merge or enter a merge queue; no permission changes or production execution are authorized. Note production coupling and any later merge/deployment decision in the handoff.

For an independently authorized main endpoint, validate all applicable current artifacts and exact candidate/base, self-verification, eligible PR-review PASS, resolved Must Fix findings, required CI and repository protections. Confirm main integration is delegated. Refresh integration evidence if base changes, follow merge queue/method, bind direct merge to expected head, and never bypass protections or force-push around gates.

Inspect workflows and external deployment linkage before merge. Human-owned production deployment is outside this default route; unresolved coupling stops the triggering action. For uncertain external execution, read actual state before retrying to avoid duplicate commits/PRs/merges.

After authorized merge, verify PR state, resulting remote main commit and required main checks. Keep pre-merge and actual post-merge receipts in authorized durable PR/task storage without rewriting the candidate they attest. Complete with AC outcomes and references, changed files, actual test/smoke scenarios/results, review status, endpoint/main state, assumptions, risks and human deployment handoff.


## 2026-09-08 amendment

Source: AK requested verified pre-merge completion and essential PR comments only. The new endpoint uses completion with merge-ready evidence and explicitly withholds merge authority, while local/PR/main routes retain their meanings. Full review evidence remains mandatory in reports; concise publication reduces duplicate PR noise without weakening review or CI gates. Reviewer selection follows the updated host contract: latest GA actual other-provider model, observed medium effort, effective auto/full mode.

## 2026-10-01 fallback, handoff and documentation rules

This amendment supersedes older mandatory different-provider-only, separate independent-verification and PR-comment exclusions. Reviewers 1 and 2 each use an actual provider different from the builder; they may share an alternate provider but must be distinct reviewer assignments. If reviewer 1 cannot proceed, use reviewer 2. If both cannot proceed, use a separate independent context from the builder's provider. Preserve current model/effort/mode and permission requirements from [host adapters](host-adapters.md).

Rate limits, access/tool failures, unavailable required configuration and inability to perform required checks trigger the next reviewer. Record the reason and observation for each unavailable reviewer. Transfer completed checks, remaining checks and available evidence so the replacement can finish the review. Never use replacement to evade a valid finding. If all eligible reviewers are unavailable, retain the incomplete result and report the actual gap; do not manufacture PASS. Replacement does not reset iteration counters.

Assign stable finding IDs from the first review. Each replacement receives all unresolved IDs, classifications, original evidence, author responses, fixes and current head/base. Retain resolved dispositions for traceability. Replacement reviews cannot silently drop a finding or downgrade Required; resolution/downgrade needs reviewer rationale. The author selects work, but only reviewer resolution closes a Required finding. Recommendations left unselected are complete as review records, without follow-up management.

Plan user scenarios are mandatory and drive test/smoke coverage and manual steps. For new features or UX/UI changes, use actual implementation screenshots to update the user manual and deliver an editable source and PDF. For API/CLI-only features, show actual calls/usage and results. Discover/read the installed PDF or document skill when producing the artifact; render and inspect every page, check text/links and remove secrets/personal data from captures. A screenshot's existence or a PDF signature alone does not verify its contents.

Before final readiness, check affected README, API, operations and user documentation plus diagrams. Update required content, rerun affected checks and have final changes reviewed. Self-verification retains a hashed documentation assessment and maintained manual assets; completion confirms the final check. No additional management is introduced for work without a PR.

## 2026-10-03 reviewer effort authority amendment

Use [effort authority](state-contract.md#reviewer-effort-authority) and [shared-review records](state-contract.md#shared-review-records) for current selection and receipt requirements. Preserve historical execution settings; do not relabel observations or infer new launch authority.

## 2026-10-15 permission-mode update

Permission-mode settings are optional. A mode-setting/observation failure alone must not stop review: continue under existing permissions with isolation observations/limitations recorded. Record model/effort/independence normally and preserve observed mode values without relabeling them. Optional isolation setup/verification must not trigger fallback or skip. An explicitly required isolation boundary or unavailable required checks still can. See [host execution contract](host-adapters.md#read-only-review-with-optional-mode-settings); this supersedes earlier literal auto/full requirements.

## 2026-10-20 optional isolation update

Enforced read-only isolation is optional for all reviewer roles, including requested models. Prefer restrictions when available; otherwise continue with a review-only assignment and honest unverified status. `read_only_required: true` is an explicit opt-in gate. No source edits, external writes or further delegation are authorized by the review assignment. See the [host contract](host-adapters.md#read-only-review-with-optional-mode-settings).
