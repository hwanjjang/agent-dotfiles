# Model-Agnostic AI-Native SDLC Playbook

- **Status:** Adopted 2026-09-05 as the operating guideline for all tasks AK assigns.
- **Source:** Provided directly by AK on 2026-09-05. Verbatim Korean original preserved at
  [`sources/2026-08-21-model-agnostic-ai-native-sdlc-playbook.ko.md`](./sources/2026-08-21-model-agnostic-ai-native-sdlc-playbook.ko.md)
  (based on Anthropic's [AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook), adapted to be model-agnostic).
  The source file is kept in Korean as an intentional exception to the English-artifact rule: it is AK's authoritative input, and translation could introduce drift. This file is the normative English artifact; later dated amendments in this normative file supersede the corresponding historical source rules; for other unresolved conflicts, ask AK.

## Current modular routing and verification amendment — 2026-10-17

The [stage-to-skill routing](../skill-routing.md) owns skill selection within
existing stages. The collection's [tdd skill](../../../tdd/SKILL.md) owns testing
methods and practical exceptions; the [verification contract](../verification.md#tdd-method-and-alternative-evidence)
owns SDLC evidence and integrated smoke. These supersede conflicting test-first
absolutes below, including historical originals. Explicit alternatives need real
coverage and honest limits; unavailable required checks remain blocked. Existing
authority, reviewer independence, iteration limits and endpoint gates still apply.

The collection's [to-spec skill](../../../to-spec/SKILL.md) owns specification
method and content, replacing the embedded spec checklist and conflicting
historical source wording. SDLC owns its stage inputs, canonical artifact location,
receipt and readiness decision; it does not maintain a second specification method.

The collection's [PR workflow policy](../../../../policies/pr-workflow.md) owns
review and merge boundaries. It supersedes the historical one-task/one-PR
equation below and in the preserved source; task ownership is not a PR count.

## Core principle

The center of the SDLC is not any model or agent harness. It is the loop

`Intent → Spec → Plan → Build → Verify → Review → Merge → Deploy → Observe → Intent`

where every stage produces an explicit, revision-identified artifact that the next stage reads. Maintained documents and selected evidence are version-controlled or durably retained; generated working state remains local under the retention amendment below. Models (Claude, Codex, Grok, etc.) are interchangeable workers; harnesses are execution environments; Git/issue-tracker/CI plus the artifacts are the system. The workflow must never depend on a specific model, API, or UI (Rule 10).

Distinguish **instruction** from **enforcement**: `AGENTS.md`, skills, and prompts say "behave this way" (advisory); CI, hooks, sandbox, and branch protection say "nothing else is possible" (deterministic). Anything that must hold is enforced deterministically, not just prompted (Rule 5).

## Repository conventions

- `AGENTS.md` is the vendor-neutral single source of truth (invariants, architecture boundaries, commands, conventions, required verification, forbidden actions, Done definition, pointers to detailed policies). This matches this repository's existing Tooling SSOT Policy.
- Vendor directories (`.claude/`, `.codex/`, `.grok/`, …) are adapters only; never put business or architecture rules in them.
- Stage artifacts live in the repo: `intent/<ID>.md`, `specs/<ID>.md`, `plans/<ID>.md`; policies under `agent/policies/`.
- One source of truth per artifact type (business issue → tracker; code change → PR; intent/spec/plan → git; incident → incident system), cross-linked by IDs.

## Stage gates

1. **Intent** — every meaningful change starts from a normalized `intent.md` (Problem, Desired Outcome, Affected users/systems, Constraints, Out of Scope, Acceptance Criteria, Risks, Open Questions, Source ID). The owner (AK) approves it: first human gate. No build without intent (Rule 1).
2. **Spec** — use the method selected in [stage routing](../skill-routing.md); assess the canonical specification and its receipt before the applicable downstream stage.
3. **Plan** — no coding before an approved `plan.md` for non-trivial changes (Rule 2): files to change/add/delete, order, dependencies, tests, migration, rollback, risks, blast radius; and answer explicitly: what could this break, what is the riskiest part, what alternative was rejected, how will the implementation be proven.
4. **Build** — 1 task = 1 agent session = 1 worktree = 1 branch = 1 PR. Agents write to branches, never main (Rule 6). Do not run two agents on overlapping files without coordination; split large features via a dependency graph.
5. **Self-verification** — a builder may not declare "done" without feedback from tests/build/runtime/browser (Rule 3): unit → integration → lint/typecheck → build → runtime → artifact comparison. Bug fixes follow reproduce → failing test → confirm failure → fix → pass → regression tests. UI changes verify via a browser/screenshot loop.
6. **Independent verification** — separate builder and verifier (Rule 4): at minimum a fresh context, for important changes a different model. The verifier runs, inspects, tests, challenges, and reports — it does not fix and ideally has no write access.
7. **Review** — deterministic CI plus AI reviewers with split lenses (correctness/regression; security/abuse; intent/spec/architecture/scope), then human review. The PR-authoring model is never the sole reviewer; prefer cross-model review. Assign models to roles by measured eval performance ("best model × role"), not by name.
8. **Fix loop** — the author agent accepts/rejects each finding, fixes accepted ones, explains rejections; reviewers re-review the changed diff; reviewers do not edit the author's branch (generator/critic separation).
9. **Human gate** — humans review intent fit, risk acceptability, architecture direction, assumptions, evidence, and production impact — not every generated line.
10. **Deploy** — agents may prepare production but never authorize it (Rule 7); production release sits behind an explicit human gate.

## Review comment schema

AI review findings use a fixed schema, not free-form comments: Severity (BLOCKER/HIGH/MEDIUM/LOW/NIT), Category (Bug/Security/Architecture/Spec/Test/Performance), Location (file+line), Finding, Evidence, Why this matters, How to reproduce, Related policy/spec, Confidence (High/Medium/Low). Low-confidence + low-severity findings may be suppressed; the goal is to reduce, not inflate, what humans must read.

## Governance

Layered controls, from advisory to hard: (1) AGENTS.md/skills → guidance; (2) tool allowlist → capability; (3) sandbox → execution boundary; (4) hooks/policy → action control; (5) CI → artifact verification; (6) branch protection → repository control; (7) production approval → deployment boundary.

Autonomy levels are explicit: A0 read-only, A1 plan, A2 local edit+test, A3 branch push+PR, A4 auto-fix PR comments, A5 staging deploy, A6 production preparation, A7 pre-approved runbooks. Production deploy stays behind a human gate.

Agents use their own identities (not human credentials) and leave an audit trail: agent, harness, model/version, task ID, base/result commits, tools invoked, tests executed, approvals, policy violations, PR, deployment. Record decision summaries, evidence, and action logs — not private chain-of-thought.

## Configuration is code

Changes to `AGENTS.md`, `CLAUDE.md`, skills, hooks, prompts, MCP config, tool permissions, agent definitions, model choice, reasoning level, or harness version are production-behavior changes: run agent evals (representative tasks, pass/regression comparison) before merging.

Every incident becomes knowledge (Rule 8): root cause → fix → regression test → agent eval → policy/AGENTS update if required. A review comment that recurs is promoted into `AGENTS.md`, a policy, or a deterministic check (Rule 9).

## Adoption path

Start simple and add structure only as needed: Phase 1 developer + single agent + PR + human; Phase 2 add a different-model reviewer; Phase 3 add an independent verifier and split correctness/security reviewers; Phase 4 orchestrated parallel builders with cross-model review; Phase 5 close the monitoring→incident→intent loop. Do not build multi-agent frameworks ahead of demonstrated need.

## AK's three emphasized amendments to the Anthropic original

1. `AGENTS.md` as a vendor-neutral source of truth.
2. Separate the generating model from the final verifying model.
3. Deterministic enforcement (CI, sandbox, branch protection) ranks above prompt instructions as a control.


## 2026-09-06 — HOTL execution amendment

Source: AK requested the HOTL SDLC skill, autonomous stage decisions through authorized main integration, distinct stage artifacts, cross-provider PR review, and at most 10 iterations per stage; AK then authorized implementing that design. This amendment applies to tasks explicitly using or legitimately routed to the shared SDLC skill. It does not grant external authority merely by installation.

**Superseded within this scope:** stage gates 1 and 3 no longer require a fresh routine human approval when intent and plan match already delegated authority. Stage gate 7's routine human review and gate 9's routine human waiting become stage-level PROCEED / NEEDS_HUMAN / BLOCKED decisions. Gate 7's cross-model preference was replaced by a mandatory different model provider for PR review, freshly verified latest GA flagship coding/reasoning model, maximum supported effort, and host auto execution within existing permissions. **Reviewer selection superseded on 2026-09-08:** apply the [reviewer and pre-merge amendment](#2026-09-08--pre-merge-endpoint-reviewer-configuration-and-pr-communication) below. Named profiles must be resolved and verified; unavailable eligible review remains incomplete.

Artifacts, independent verification, CI, unresolved human requests, and stricter target-repository rules remain mandatory. Interpret Build gate 4 as one task-owned branch/worktree/PR with bounded collaborating roles where appropriate; coordinate disjoint files and verify the combined candidate. Verifiers do not edit the builder's branch. Separate Spec, Plan, self-verification, independent-verification and PR-review outputs are required for their applicable stages. Post-commit/post-merge receipts belong in durable authorized PR/task records linked to the exact candidate, not recursive evidence-only commits.

For behavior changes and bug fixes, perform intended Red -> Green -> Refactor with tests green -> additional local smoke -> commit. For pure refactors retain behavior tests without fabricating Red. Non-executable documentation receives content checks rather than fake runtime smoke; active agent configuration requires relevant behavioral evaluations.

Each stable task stage receives its own maximum of 10 total iterations including the first. Workflow totals may exceed 10. Stop early on success or an earlier authority/capability blocker; replacements, retries, resume, replan and stage re-entry share the same stage counter. No 11th attempt. On exhaustion preserve evidence, stop dependent work, and report the unresolved decision to AK. This supersedes dependency-level three-strike retry guidance for the SDLC route without weakening earlier safety stops.

The autonomy list above is descriptive, not a ceiling or a grant: authorized main integration may proceed automatically when current evidence, independent review and repository protections pass. Verify actual production coupling before merge. Production deployment remains human-owned and excluded; a merge that triggers it requires resolving that authority conflict before execution. Review-only and plan-only requests keep their established endpoints. The full role/workflow procedures live in the shared skill; this policy remains the normative source.


## 2026-09-08 — Pre-merge endpoint, reviewer configuration and PR communication

Source: AK requested an implementation endpoint immediately before merge, latest GA review models from the actual other provider, medium reasoning effort, auto/full mode, and essential concise PR comments. This amendment governs the shared skill route and preserves existing local, PR and main endpoint meanings, separate verification, artifact requirements, per-stage iteration limits and stricter target-repository controls.

**Superseded reviewer selection:** the 2026-09-06 amendment's flagship coding/reasoning restriction, maximum supported effort and auto-only mode. At review time verify the latest generally available model of an actual provider different from the implementation author's, observe medium reasoning effort and effective auto or full execution mode, and preserve the source/timestamp and actual execution receipt. Named personal/team accounts or profiles do not establish model provider identity. Missing eligible configuration remains an incomplete review gate; do not mutate permission settings or silently elevate privileges to satisfy mode selection. Keep the author's branch read-only and reviewer-generated tests isolated.

**Pre-merge authority contract:** when AK explicitly delegates a scoped task through pre-merge, record that initial contract in intent. It covers implementation, applicable tests and additional smoke, commits, branch push, PR creation/updates, CI, independent verification/review/corrections, and necessary scoped code/test/evidence transfers among the specified already configured personal/team accounts and independent agents. Do not request routine authorization again for those covered steps. It excludes secrets, unrelated disclosures, new accounts, permission-setting mutations and production actions. Use available authenticated GitHub MCP or gh capabilities without treating tooling as expanded authority.

**Readiness endpoint:** complete the existing completion stage with current merge-ready evidence and a receipt recording merge_authorized false. Verify the actual current head/base, required CI, independent verification, eligible review PASS and resolved Must Fix findings. Keep merge not-applicable: do not merge, enable auto-merge or enter a merge queue. Inspect and resolve/report already armed automatic integration before declaring the PR safely waiting for a human. Readiness is not merge authorization; a later integration request requires an authority amendment and refreshed evidence. Production coupling is assessed and reported without triggering deployment. No post-merge receipt is required for work that must remain unmerged.

**PR communication:** publish only essential concise actionable Must Fix findings, blockers and a final readiness result with durable evidence links. Preserve detailed finding schemas, configuration receipts, test logs and Recommended/NIT follow-up in task reports instead of repeatedly posting them to the PR. This changes the remote presentation of the earlier fixed-schema rule, not the requirement to retain complete structured findings and actual review evidence.


## 2026-09-30 — Maintained documents, generated reports, and commit checks

Source: AK requested applying a prior artifact-retention workflow
to the shared SDLC skill and user installation. Follow the portable
[artifact retention contract](../artifact-retention.md) for storage, cleanup and checks.
This amendment supersedes blanket version-control requirements for generated stage
reports; it does not weaken stage artifacts, local digest validation, independent
verification, eligible review, authority boundaries or evidence handoff.

Maintain documents in docs/architecture or docs/operations, reusable tools in
scripts/verification or existing tests, and selected dated evidence in docs/evidence
or an authorized durable store, following equivalent target-repository conventions.
Keep reports and .archify generated output ignored. Preserve reference assets,
reproduction data and required provenance. When untracking generated files, preserve
local files and Git history. Essential evidence must survive CI artifact expiry.

Clean up the proposed changes before final verification and commit; never discard
required gate inputs as cleanup. Repository enforcement uses one read-only checker
from pre-commit (index), pre-push (every actual outgoing commit), and CI (matching
range/snapshots), including docs-only changes. Reject generated files and maintained
links to local-only targets, including staged/unstaged mismatches and add-then-delete
history. Hooks must not mutate files or the index. Installing this skill does not wire
that checker; missing enforcement is reported separately from observed verification.

## 2026-10-01 — PR review loop, fallback, scenarios and user documentation

Source: AK's explicit workflow update and subsequent clarifications in the SDLC discussion. This amendment supersedes earlier separate independent-verification gates for PR implementation, different-provider-only review with no fallback, exclusion of Recommended items from PR comments, and follow-up management of unselected recommendations. Retain existing authority/production boundaries, actual evidence requirements and the maximum 10 attempts per stable stage.

At every applicable stage, assess whether the linked issue needs a material update; post concise findings, decisions, plan changes, blockers, verification results or completion when useful. Do not post duplicates or manufacture issues to satisfy this step.

Planning must produce user scenarios with user/goal, prerequisites, ordered actions, expected results and relevant failure paths, mapped to acceptance criteria and tests. New features or UX/UI changes require an updated user manual with actual scenario screenshots, editable source and a rendered/visually checked PDF in maintained documentation storage. API/CLI-only features use actual usage/results captures.

Remove the separate independent-verification stage and report from the PR implementation route. After self-verification, review the PR in an independent context. Reviewer 1 and reviewer 2 each use a provider different from the implementation agent. If reviewer 1 cannot proceed, use reviewer 2. If both cannot proceed, use an independent reviewer of the implementation provider. Rate limits, access/tool/configuration problems and inability to perform required checks advance the chain; findings or disagreement do not. Preserve actual latest GA model selection, medium effort and effective auto/full execution within existing permissions. If all reviewers cannot complete required work, report incomplete review without PASS.

Carry stable finding IDs, unresolved findings, available evidence, author responses and fixes across reviewer replacements. Publish clear, concise Required and Recommended PR comments. The author assesses each finding, selects changes, implements and verifies them, then pushes. Required findings need reviewer-confirmed resolution or justified reviewer reclassification. Repeat review/correction until PASS and no author-selected changes remain. Unselected recommendations end in the review record: no separate issue, owner, reminder or follow-up tracking.

Before completion, check affected user/API/operations documentation, README and diagrams, update what is needed, and renew affected verification/review after changes. Do not introduce lifecycle or review management for non-PR work unless AK explicitly asks. Historical records remain readable; adopting this revision preserves stage counters/history and invalidates affected evidence rather than relabeling old executions.

## 2026-10-03 reviewer effort authority amendment

Default reviewer effort remains medium. An explicit task-scoped AK instruction may override it through the latest successful intent output described in [the state contract](../state-contract.md#reviewer-effort-authority). This supersedes literal medium requirements in earlier amendments; preserve their historical execution records. Resolve and observe the authorized value without relabeling runtime evidence. Unsupported host effort leaves review incomplete; no account, permission or launch authority is added.

## 2026-10-15 additional optional PR reviewers

Source: AK requested Grok 4.7 high and Gemini 3.8 high as additional review-only
contexts with PR comments, skipping limits/outages. Follow the
[optional-review contract](../optional-reviewers.md). Its pinned model/high settings
supersede latest-GA/intent-derived effort only for these optional contexts. Preserve
the required review/fallback gate; optional unavailability is not a readiness block.
Main publishes attributed results; the builder implements all selected fixes.

## 2026-10-15 optional reviewer permission-mode configuration

Source: AK requested that permission-mode setup be optional and that reviewers continue read-only if it cannot be set. This supersedes previous mandatory auto/full mode requirements. Required and optional reviewers may use an omitted, default or unverified mode when read-only isolation under existing permissions is verified and recorded. Session-only restrictions may narrow access; no global permission edits, bypass/escalation or new accounts are granted. A mode-setting failure alone is not reviewer unavailability. Model/effort/independence, required checks, finding resolution, authority and integration gates remain unchanged. Use the [host contract](../host-adapters.md#read-only-review-with-optional-mode-settings) and retain actual execution and source-integrity evidence.

## Public distribution scope amendment

This package is reusable workflow source, not standing permission to publish issue
comments, push branches, merge, deploy, transfer task data, or change accounts.
External writes require authorization in the current task. Existing authorization
remains valid; do not ask again for routine actions within it. This amendment
supersedes personal standing-authority language in historical source material.
Use the user's language and the destination repository's artifact conventions.
Historical model names are preferences to verify, not claims of host availability.
The screenshot-manual skill provides the required screenshot/PDF production path;
archify provides diagram production. Both keep generated evidence local by default.
