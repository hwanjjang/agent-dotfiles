# Shared subagent contracts

Read this before delegating. The main agent owns authority decisions, the artifact index, iteration counters, shared planning files, integration, and completion. Common roles are defined here once; any host registration must reference or be generated from this revision. Metadata in `agents/openai.yaml` is not a subagent registry.

| Role | Work | Boundary and required return |
| --- | --- | --- |
| plan | Specification, architecture, risks, Archify, implementation planning | No implementation-code edits. Return separate stage-ordered Spec/Plan and applicable diagram evidence, assumptions and unresolved decisions. |
| research | Bounded source/API/dependency or failure-path investigation | No product edits. Return verified facts with locations/sources, uncertainty and impact in assigned evidence record. |
| dev | Implementation and corrections | Only assigned files/worktree. No scope/AC changes or self-approval. Return diff, build record, distinct tdd/alternative and additional local-smoke evidence. |
| qa: required PR review | Actual PR/diff and evidence review | Must satisfy ordered provider fallback eligibility in [host adapters](host-adapters.md). Return complete configuration receipt and fixed-schema review; publication only within assigned authority. |

Roles do not mandate a fixed agent count. Main may handle optional planning/research/test design/build directly if delegation adds no value, recording its builder role. The builder cannot become its own reviewer by changing labels. There is no separate independent-verification assignment/report in the revised PR route.

For authorized PR work, apply the [additional-reviewer contract](optional-reviewers.md)
before dispatch: share matching required/additional roles, and launch only uncovered
reviewers. These roles never participate in dev/correction; main publishes each
distinct review once. Required fallback eligibility remains unchanged.

## Dispatch

Use [the assignment/return template](../assets/delegation-receipt.json) as a record, not an executable host configuration. Include:

- Task and unique assignment IDs, stable stage, current iteration/remaining allowance, objective, AC IDs, authority source and limits, including the endpoint and specified configured accounts.
- Stable finding IDs, unresolved findings, author responses, fixes and remaining checks when replacing a reviewer; do not drop earlier findings.
- Exact upstream artifact revisions/digests, repository/worktree, base/head or pre-commit candidate, local instructions. Child acknowledges actually reading the inputs.
- Allowed files/directories/tools, prohibited actions, output paths, dependency/conflict information, verification method, deadline and bounded assignment scope.

Further delegation, commits, publication and push are excluded unless explicitly assigned within existing authority. An explicit pre-merge contract can assign task code/test/evidence transfer among its specified configured personal/team accounts and independent agents; reuse that authority without repeated routine asks. It never grants credential/secret transfer, new accounts or permission-setting changes. At pre-merge, no assignment may merge, enable auto-merge or enter a merge queue. Never put credentials in receipts.

Parallel lanes must have disjoint file ownership or an explicit serialization/coordination agreement. Intentional concurrent test lanes must also use disjoint temporary directories
and fixture-lock namespaces; separate worktrees alone do not isolate shared locks.
Before a full-suite retry, main reconciles the prior process identity, status,
result and cleanup; wait or stop only task-owned processes within authority.
Preserve the first failure and classify dependency, permission and contention
failures separately from product regressions before recording isolated retry results.
Separate worktrees still require integration and verification of the combined candidate. Only main updates shared state; receipt files may be assigned disjoint child-owned paths.

## Accepting results

The return records actual context/provider/model where available; consumed inputs; changed files; outputs/digests; commands and observed outcomes; evidence; findings; assumptions/risks; and a proposed HOTL decision with reason/next action. PR review has an additional mandatory fully verified configuration receipt. Unknown configuration stays unknown.

Main checks output content, allowed scope, evidence references, actual input/candidate freshness, role eligibility and exit criteria. Reject missing, stale, contradictory or unauthorized results; a spawn success or completion sentence does not satisfy a gate. Child PROCEED supplies evidence, never new authority.

Persist receipts under `R/delegations/<assignment-id>.json` and index them. Post-commit records follow the durable PR/task-record rule. Stop affected assignments on cancellation or changed scope; preserve partial work and reject late returns consuming superseded input.

## Recovery and loops

Before re-dispatch, reconcile outstanding assignment IDs, actual host status, outputs, and diffs to avoid duplicate work. An interrupted started attempt counts; resume that same attempt only when its identity and scope are reconciled. A renewed repair/review attempt increments the stable stage counter. Parallel children in one planned assessment share that iteration; children have no private additional allowance.

Agent/provider replacement, a new finding, revised candidate, restart or downstream re-entry cannot reset a stage's maximum 10 attempts. Retry only for a recorded failure/interruption/invalid return/changed input with a concrete next approach. Do not repeatedly review unchanged passing inputs without new cause. Exhaustion blocks that stage and its dependents; return attempts, evidence, remaining gap and recommended decision to AK. Unaffected authorized stages may continue.


## 2026-09-08 amendment

Source: AK's pre-merge and reviewer update. Dispatch now includes endpoint/account boundaries; account labels do not identify actual model providers. PR reviewers must observe the latest GA model of an actual different provider, medium effort and effective auto/full mode under the host contract. Publish only essential concise PR findings/blockers/final readiness; retain full evidence in reports. Children cannot promote merge readiness into merge authority.

## 2026-10-01 review amendment

Use reviewer 1, then reviewer 2 from actual providers different from the builder; if both are unavailable (including inability to run required checks), use an independent same-provider context. Preserve latest GA/medium/auto-or-full configuration and existing permissions. Carry unresolved finding IDs and their evidence, author responses and fixes across assignments. Publish concise Required/Recommended findings. Unselected recommendations end in review records with no follow-up work or tracking. Remove the separate independent-verification duty from PR implementation.

## 2026-10-03 reviewer effort authority amendment

Use [effort authority](state-contract.md#reviewer-effort-authority) and [shared-review records](state-contract.md#shared-review-records) for current selection and receipt requirements. Preserve historical execution settings; do not relabel observations or infer new launch authority.

## 2026-10-15 permission-mode update

Permission-mode settings are optional. A mode-setting/observation failure alone must not stop review: continue under existing permissions with isolation observations/limitations recorded. Record model/effort/independence normally and preserve observed mode values without relabeling them. Optional isolation setup/verification must not trigger fallback or skip. An explicitly required isolation boundary or unavailable required checks still can. See [host execution contract](host-adapters.md#read-only-review-with-optional-mode-settings); this supersedes earlier literal auto/full requirements.

## 2026-10-20 optional isolation update

Enforced read-only isolation is optional for all reviewer roles, including requested models. Prefer restrictions when available; otherwise continue with a review-only assignment and honest unverified status. `read_only_required: true` is an explicit opt-in gate. No source edits, external writes or further delegation are authorized by the review assignment. See the [host contract](host-adapters.md#read-only-review-with-optional-mode-settings).
