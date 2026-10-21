# Host discovery and eligible execution

This package provides portable instructions and local state validation, not an orchestration service, native agent profiles, or an alternate-provider launcher. Discover the actual host before claiming delegation works. Do not copy one host's invocation syntax into another.

## Capability receipt

Record host/version, inspected tool or CLI help/catalog source and timestamp, actual tool/launcher name, authenticated provider options, available model selection, isolation/permissions, concurrency, result retrieval and cancellation/resume support. Record adapter/source revision and limitations. A profile name alone proves none of these.

For Codex, inspect the exposed delegation tools and their schema or installed CLI's documented capability. For Claude Code, inspect its exposed agent/delegation tools or installed CLI's documented capability. Use the supported call with the common bounded assignment; retain actual execution identity and return evidence. Do not assume a `provider` field, a particular model enum, or cross-provider access exists.

If a native mechanism exposes only one provider, changing its role or model name does not produce another provider. An external provider may be used only through an available authenticated launcher whose supported configuration and actual provider can be verified, with available permission/isolation observations recorded. Do not install profiles, authenticate accounts or elevate permissions as an implicit fallback.

If explicitly required file/tool boundaries cannot be represented, report the gap. Read-only isolation is otherwise optional: prefer supported restrictions and continue with recorded limitations when unavailable. Missing optional delegation permits main-agent fallback for non-independent duties; an unavailable PR reviewer triggers the next eligible reviewer; exhaustion leaves review incomplete.

## Required PR reviewer selection

The additional Grok/Gemini list has its own [optional-review contract](optional-reviewers.md),
including shared-assignment selection, model/effort defaults and non-blocking skip behavior. The selection
and mandatory provider/model/effort receipts below govern the existing required
reviewer. Existing authority applies to all reviewers; enforced read-only isolation and mode configuration are optional.

At review creation:

1. Record actual implementation author provider/context and contributing authors. Assign reviewer 1 and reviewer 2 from providers different from the builder. When both cannot proceed, permit reviewer 3 from the builder provider in a separate context. For mixed-provider authorship record independence from the contributing author contexts.
2. Inspect available authenticated alternate providers and current model catalogs. Select the latest generally available model of the actual selected provider. Use authoritative provider information with date/source when catalog data cannot establish recency. Do not substitute a remembered or preview model or infer recency from an account/profile label.
3. Prefer a configured eligible review provider. Otherwise use documented review-evaluation quality, then provider identifier order as a tie-breaker.
4. Before dispatch, reconcile the roster using [one assignment per reviewer](optional-reviewers.md#one-assignment-per-reviewer), including any required fallback. Resolve and observe the selected effort under that contract and the intent authority; the ordinary default remains `medium`. Permission-mode configuration is optional. Prefer a supported session setting within existing permissions; if it is omitted, unsupported, mismatched or fails, continue under existing permissions with honest isolation observations as described below. Do not change global settings or escalate access to satisfy a mode label. Instruct the reviewer not to edit the author branch; use isolated generated checks when available.
5. Inspect resolved settings, execute the reviewer and preserve a receipt containing author/reviewer providers and contexts, exact model, effort, mode, selection source/timestamp, host/tool configuration, isolation, base/head, actual review record ID, scope, findings and verdict.

A personal/team account label is not a model provider. Resolve the executing provider and model even when a named profile is used. If required selection/execution or a required check cannot be performed, retain the exact gap and try the next reviewer. Permit the author provider only after both earlier alternate-provider reviewers cannot proceed. Never label the builder context independent or silently weaken required configuration.

## Read-only review with optional mode settings

Permission-mode configuration and enforced read-only isolation are optional.
Prefer a supported session restriction, but proceed under existing permissions
when setup, observation or enforcement is unavailable. This applies to required,
additional and explicitly requested reviewers. Do not block, skip, substitute a
model or repeatedly probe solely to obtain isolation proof. Session settings may
narrow access; do not change global permissions, authenticate new accounts or
escalate privileges to satisfy this preference.

Give the reviewer a bounded review-only assignment: inspect and return findings;
no source edits, commits/pushes, external messages/publication, production/provider
mutations or further delegation. Main publishes findings within its authority.
Prefer immutable scoped input and separate scratch for generated checks, retain
actual tool/launcher observations, and compare source hashes after the return.
Inspect available tool/action records alongside the findings; the reviewer's final
self-report alone does not establish which actions ran. Retain relevant observed
effects and record unavailable or incomplete action records as evidence limitations.
These checks record what happened; a prompt or immutable copy alone must not be
reported as verified tool/network isolation. Missing proof is a recorded limitation,
not reviewer unavailability. Reject source-changing results and reconcile only
task-owned effects within existing authority.

Receipts default to `read_only_required: false`. Record `read_only_verified: false`
and available evidence/limitations when isolation is absent or unverified. A true
verified claim still needs actual evidence covering the claimed boundary. Only an
assignment explicitly opting in with `read_only_required: true` makes verified
read-only boundary evidence a prerequisite. Set this opt-in only for an explicit
user choice or applicable repository requirement, never merely the adapter's
preference. Requested/observed mode fields may be
omitted/null/default and must reflect actual observations. Authentication, quota,
launch failures and inability to perform required checks still use the existing
fallback chain.

## Incomplete mode discovery

An empty wrapper mode catalog or inheritance error is a configuration diagnostic,
not proof that its provider is unavailable. Reuse an observed working route through
corrections; refresh when the host, launcher, model, account, restrictions or an
actual execution failure changes that evidence. Missing reviewer self-observation
does not invalidate independently evidenced host settings. Record requested,
host-observed and self-reported values separately; unknown values stay unknown.

Personal launcher exceptions stay in local authorization records. They do not
establish required/shared-review eligibility or override host/repository limits.
After an automatic approval rejection, retain its reason and retry only with new
trusted evidence or a narrower authorized action; changing tools does not bypass
that rejection. An unresolved refusal is a reported review gap.

Do not spend repeated attempts obtaining a mode label or optional isolation
proof. Prefer an available native plan/read-only launcher when useful, or continue
through an existing authenticated route with observed limitations.

The [mode assessment helper](../scripts/reviewer_mode.py) accepts an observation
object on stdin. Verified boundary evidence returns `read-only`; observed legacy
auto/full evidence returns `verified-mode`. Otherwise it returns
`existing-permissions` with `read_only_verified: false`. `probe-required` is
reserved for an explicit `read_only_required: true` without proof, or a claimed
verified boundary without evidence, or a malformed nonboolean
`read_only_required` value. A real launch failure with evidence still
returns `unavailable`. This helper does not launch reviewers or prove a PASS.

## Validation claims

Skill discovery in both hosts, a local CLI smoke pass, and an actual delegated assignment are different results. Verify each claimed capability independently with real returned artifacts and receipts. Cross-provider review and automatic PR/main integration require authorized integration tests in a dedicated repository disconnected from production. Without those tests report them unverified; do not infer operational readiness from installed files or schema checks.


## Account and GitHub contract

An explicit pre-merge assignment covers scoped code, tests and task evidence transfer among the personal/team accounts and independent agents specified by that assignment, using already configured authenticated paths. Do not repeatedly ask for routine transfer or PR approval already covered by the contract. It does not authorize new accounts, credential/secret transfer, unrelated repository disclosure or permission-setting changes. Inspect actual capabilities without printing tokens. Missing capability is reported; do not broaden access as a fallback.

Before transferring review inputs, identify the actual provider and configured
account/destination, exact head/base, file manifest, review purpose and trusted
authority covering that payload and destination in the existing assignment/evidence.
Send only the needed diff, source and verification; exclude secrets, account settings
and unrelated content. Reuse earlier approval only while its task, destination and
disclosure limits still apply. A profile name or this contract supplies no new
transfer authority.

Use available authenticated GitHub MCP tools or `gh` for the authorized PR and CI operations. Tool choice does not change the endpoint. At pre-merge, merge, auto-merge and merge-queue entry are forbidden even when the account supports them. Keep remote comments concise and preserve detailed receipts in linked reports.

## 2026-09-08 amendment

Source: AK's reviewer and pre-merge contract update. Superseded: latest GA flagship coding/reasoning, maximum supported effort and auto-only mode. The active requirement is latest GA model of the actual other provider, observed medium effort and effective auto or full mode within existing permissions. Profile/account names never establish provider identity or permission grants.

## 2026-10-01 fallback amendment

The different-provider requirement now applies to reviewer slots 1 and 2. Slot 3 may use the same provider as the builder after recording both prior unavailability reasons and evidence. Keep its context separate from the builder and the author branch read-only. `reviewer_slot` and ordered `unavailable_reviewers` in the [configuration receipt](../assets/reviewer-configuration.json) record selection, not invented execution. An unavailable configured reviewer may be recorded from a real capability/availability observation without launching a doomed review.

Inability to run required checks advances the chain just like a rate limit. Carry unresolved finding IDs, author responses, fixes, remaining checks and existing evidence to the replacement. If the final reviewer cannot complete required work, report incomplete review. These fallbacks do not authorize new accounts, permission changes, production actions or unconfigured external providers.

## 2026-10-03 reviewer effort authority amendment

Use [effort authority](state-contract.md#reviewer-effort-authority) and [shared-review records](state-contract.md#shared-review-records) for current selection and receipt requirements. Preserve historical execution settings; do not relabel observations or infer new launch authority.
