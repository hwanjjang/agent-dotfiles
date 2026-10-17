# Host discovery and eligible execution

This package provides portable instructions and local state validation, not an orchestration service, native agent profiles, or an alternate-provider launcher. Discover the actual host before claiming delegation works. Do not copy one host's invocation syntax into another.

## Capability receipt

Record host/version, inspected tool or CLI help/catalog source and timestamp, actual tool/launcher name, authenticated provider options, available model selection, isolation/permissions, concurrency, result retrieval and cancellation/resume support. Record adapter/source revision and limitations. A profile name alone proves none of these.

For Codex, inspect the exposed delegation tools and their schema or installed CLI's documented capability. For Claude Code, inspect its exposed agent/delegation tools or installed CLI's documented capability. Use the supported call with the common bounded assignment; retain actual execution identity and return evidence. Do not assume a `provider` field, a particular model enum, or cross-provider access exists.

If a native mechanism exposes only one provider, changing its role or model name does not produce another provider. An external provider may be used only through an available authenticated launcher whose supported configuration, isolation, permissions and actual provider can be verified. Do not install profiles, authenticate accounts or elevate permissions as an implicit fallback.

If required file/tool boundaries cannot be represented, use supported isolation; otherwise report the unsupported boundary. Do not silently omit restrictions. Missing optional delegation permits main-agent fallback for non-independent duties; an unavailable PR reviewer triggers the next eligible reviewer; exhaustion leaves review incomplete.

## Required PR reviewer selection

The additional Grok/Gemini list has its own [optional-review contract](optional-reviewers.md),
including shared-assignment selection, model/effort defaults and non-blocking skip behavior. The selection
and mandatory provider/model/effort receipts below govern the existing required
reviewer. Existing permissions and read-only isolation apply to all reviewers; mode configuration is optional.

At review creation:

1. Record actual implementation author provider/context and contributing authors. Assign reviewer 1 and reviewer 2 from providers different from the builder. When both cannot proceed, permit reviewer 3 from the builder provider in a separate context. For mixed-provider authorship record independence from the contributing author contexts.
2. Inspect available authenticated alternate providers and current model catalogs. Select the latest generally available model of the actual selected provider. Use authoritative provider information with date/source when catalog data cannot establish recency. Do not substitute a remembered or preview model or infer recency from an account/profile label.
3. Prefer a configured eligible review provider. Otherwise use documented review-evaluation quality, then provider identifier order as a tie-breaker.
4. Before dispatch, reconcile the roster using [one assignment per reviewer](optional-reviewers.md#one-assignment-per-reviewer), including any required fallback. Resolve and observe the selected effort under that contract and the intent authority; the ordinary default remains `medium`. Permission-mode configuration is optional. Prefer a supported session setting within existing permissions; if it is omitted, unsupported, mismatched or fails, continue with a verified read-only boundary as described below. Do not change global settings or escalate access to satisfy a mode label. Keep the author branch read-only and generated checks isolated.
5. Inspect resolved settings, execute the reviewer and preserve a receipt containing author/reviewer providers and contexts, exact model, effort, mode, selection source/timestamp, host/tool configuration, isolation, base/head, actual review record ID, scope, findings and verdict.

A personal/team account label is not a model provider. Resolve the executing provider and model even when a named profile is used. If required selection/execution or a required check cannot be performed, retain the exact gap and try the next reviewer. Permit the author provider only after both earlier alternate-provider reviewers cannot proceed. Never label the builder context independent or silently weaken required configuration. Pin verified settings for the correction cycle; recheck availability and record changes before replacement execution.

## Read-only review with optional mode settings

Mode selection is an optional convenience, not a review eligibility gate. A missing catalog, null/default mode, failed inheritance or mismatch between requested and observed mode does not by itself make the provider unavailable. Continue in read-only review under the existing permissions. A session-only setting that narrows access (for example native plan/read-only mode) is allowed; no new account, authentication, global permission edit, bypass flag or access escalation is implied.

Verify the review boundary before dispatch using supported read-only tool restrictions or an isolated non-writable input checkout combined with existing tool/network restrictions. Input immutability alone does not prevent external writes: boundary evidence must cover available tools, network/external mutations and source integrity. Give checks that generate files a separate scratch location. Exclude source editing, commits/pushes, external messages, production/provider mutations and further delegation; main publishes findings. Retain actual launcher/tool/isolation observations and confirm source hashes after the return. A prompt-only promise is not verification. If safe read-only execution cannot be established, record that concrete isolation failure and use the reviewer fallback/optional skip rules.

New configuration receipts use `read_only_verified: true` plus nonempty `read_only_evidence` referencing the observed boundary. Record `requested_mode`, observed `mode` and `mode_verified` honestly; modes may be omitted/null/default, and an unverified mode stays unverified. A mode-setting error is diagnostic, not an `unavailable_reason`. Real authentication/quota/launch failures and inability to perform required checks still advance the existing fallback chain.

## Incomplete mode discovery

Do not spend repeated attempts obtaining an auto/full label. Inspect the native contract only as needed to establish the read-only boundary, then launch a bounded review with existing permissions. For example Grok may continue with its observed default mode and native Read/Grep/Glob-only tools; a Gemini wrapper that only exposes bypass permissions should be replaced by an existing native read-only/plan launcher when available, rather than enabling bypass.

The read-only [mode assessment helper](../scripts/reviewer_mode.py) accepts an observation object on stdin. `read_only_verified: true` and nonempty `read_only_evidence` produce `read-only`, independently of mode fields. Verified auto/full evidence still produces the historical `verified-mode` outcome for old callers without the new fields. Explicitly incomplete read-only fields produce `probe-required` before that legacy classification. A real `unavailable_reason` with observed `evidence` remains `unavailable`; otherwise the helper returns `probe-required` to establish isolation, not to force mode configuration. The helper trusts adapter evidence; it neither launches a provider nor proves a review PASS.

## Validation claims

Skill discovery in both hosts, a local CLI smoke pass, and an actual delegated assignment are different results. Verify each claimed capability independently with real returned artifacts and receipts. Cross-provider review and automatic PR/main integration require authorized integration tests in a dedicated repository disconnected from production. Without those tests report them unverified; do not infer operational readiness from installed files or schema checks.


## Account and GitHub contract

An explicit pre-merge assignment covers scoped code, tests and task evidence transfer among the personal/team accounts and independent agents specified by that assignment, using already configured authenticated paths. Do not repeatedly ask for routine transfer or PR approval already covered by the contract. It does not authorize new accounts, credential/secret transfer, unrelated repository disclosure or permission-setting changes. Inspect actual capabilities without printing tokens. Missing capability is reported; do not broaden access as a fallback.

Use available authenticated GitHub MCP tools or `gh` for the authorized PR and CI operations. Tool choice does not change the endpoint. At pre-merge, merge, auto-merge and merge-queue entry are forbidden even when the account supports them. Keep remote comments concise and preserve detailed receipts in linked reports.

## 2026-09-08 amendment

Source: AK's reviewer and pre-merge contract update. Superseded: latest GA flagship coding/reasoning, maximum supported effort and auto-only mode. The active requirement is latest GA model of the actual other provider, observed medium effort and effective auto or full mode within existing permissions. Profile/account names never establish provider identity or permission grants.

## 2026-10-01 fallback amendment

The different-provider requirement now applies to reviewer slots 1 and 2. Slot 3 may use the same provider as the builder after recording both prior unavailability reasons and evidence. Keep its context separate from the builder and the author branch read-only. `reviewer_slot` and ordered `unavailable_reviewers` in the [configuration receipt](../assets/reviewer-configuration.json) record selection, not invented execution. An unavailable configured reviewer may be recorded from a real capability/availability observation without launching a doomed review.

Inability to run required checks advances the chain just like a rate limit. Carry unresolved finding IDs, author responses, fixes, remaining checks and existing evidence to the replacement. If the final reviewer cannot complete required work, report incomplete review. These fallbacks do not authorize new accounts, permission changes, production actions or unconfigured external providers.

## 2026-10-03 reviewer effort authority amendment

Use [effort authority](state-contract.md#reviewer-effort-authority) and [shared-review records](state-contract.md#shared-review-records) for current selection and receipt requirements. Preserve historical execution settings; do not relabel observations or infer new launch authority.
