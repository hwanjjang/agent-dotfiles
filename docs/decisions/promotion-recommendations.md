# Evidence-bound source-review recommendations

Implemented: the legacy diagnostic gate, native report/committed-source consumer,
and optional same-host held-out receipt verifier. Current-source native
qualification and actual development/held-out comparisons remain pending.
Positive **FAKE synthetic conformance** tests exercise the recommendation branch;
they establish no actual beneficial candidate or unseen-evaluation result.

The [account improvement design](account-improvement-loop.md#source-promotion-and-account-delivery)
owns source acceptance and account delivery. This guide owns the implemented
recommendation inputs and verification boundaries. The
[source-backed workflow](../architecture/native-recommendation-workflow.html)
shows the optional preflight, recorded trials and read-only recommendation path.

## Choose the evidence route

| Entry point | What it verifies | Remaining boundary |
| --- | --- | --- |
| `promotion.py recommend` | Recomputes supplied deterministic development completions and report; binds a caller-supplied diff reference. | Does not inspect Git, admit native records or verify held-out provenance. A favorable arithmetic fixture remains operationally inconclusive. |
| `promotion.py recommend-native` | Recomputes a sealed `NativeBatch`, checks the supplied report, and verifies committed source objects against both frozen arm inventories. | Development evidence alone cannot support a positive recommendation. |
| `recommend-native` with `heldout_record_path` | Additionally verifies the one private manifest, selected trusted-maintainer context receipts, actual remote anchors, held-out batch, exposure and both frozen rules. | This narrow source-review recommendation grants no source acceptance, installation or merge authority. Actual qualifying evidence is still required. |
| `heldout.py run-next` | Verifies the manifest/anchors and records preflight before delegating one ordered launch to the existing serial gate. | This entry point **can launch a native trial**. It requires the existing explicit execution/authentication authorization; it is not a read-only recommendation command. |

The recommendation commands do not launch models, apply patches, mutate Git or
change accounts. The preflight adapter is the separate, explicit execution path;
it adds no executor, credential mechanism or scheduler.

## Legacy diagnostic input

```sh
python3 scripts/improvement/promotion.py recommend < gate-input.json > recommendation.json
```

Input contains exactly `experiment`, `report`, `completions`, `current_spec`, and
`source_diff_digest`. The first four use the
[evaluation accounting contract](evaluation-accounting.md). The last is the
SHA-256 review reference supplied by the caller; this legacy route does not
verify its resulting Git tree. A reviewer must inspect the actual diff separately.

The gate recomputes canonical experiment and report bytes. Boolean/integer/float
substitutions, rehashed forged aggregates and caller eligibility flags cannot
replace that comparison. A stale spec or changed baseline, candidate, grader,
runner, environment, capability, model or budget invalidates the experiment.
Reviewed in-tree producer exports remain development evidence, not native or
held-out provenance.

## Native report and committed-source review

```sh
python3 scripts/improvement/promotion.py recommend-native < native-review-input.json > native-recommendation.json
```

Input contains exactly these fields, with only `heldout_record_path` optional:

| Field | Required value |
| --- | --- |
| `experiment`, `current_spec` | Frozen experiment and matching current spec. |
| `context_path` | Absolute path to the private [native admission context](evaluation-accounting.md#admit-recorded-native-artifact-snapshots). |
| `attempts` | Recorded `trial_id`, `attempt_id`, `attempt_path` references consumed by the existing admission reader. |
| `report_path` | Private JSON report to compare byte-canonically with the recomputed report. |
| `repository` | Absolute local Git repository path; no clone/fetch is performed. |
| `baseline_commit`, `candidate_commit` | Full lowercase 40- or 64-character commit object IDs, not refs, tags or revisions such as `HEAD`. |
| `component_roots` | Sorted, unique, nonoverlapping repository-relative roots, as described below. |
| `heldout_record_path` | Optional absolute private manifest path for the same-host verifier. |

The consumer opens the guarded context and sealed `NativeBatch`, recomputes the
actual report, holds its existing locks/guards, and checks late source/evidence
changes before returning. Positive evidence must begin with an **unscoped**
`development` report of kind `native_artifact_development_comparison`; a declared
held-out schedule cannot stand in for development evidence. The separate held-out
pack cannot reuse a development case or counterpart's canonical `inputs` digest;
changing the execution root or renaming a case ID does not establish separation.
Stable category IDs may repeat when the actual inputs differ. This is exact
input-content separation, not a semantic similarity detector. Caller rows, report
aggregates, claimed success or
`verified: true` are not alternate input authorities. Missing current qualification
stays unavailable; old public proof cannot be relabeled as current-source proof.

`verify_source` checks actual commit type, commit/tree object IDs and raw blob
bytes. It reads **complete** component inventories from both commits and requires
an exact match with the guarded bytes materialized for each arm. The canonical
source delta includes each changed path, old/new modes and raw-byte SHA-256s;
additions/deletions use null for the absent side. Dirty checkout content is not
committed evidence and is not used to construct this delta.

Supported roots are one to eight `skills/<name>`, `policies/...` or `mcp/...`
paths; each must select an existing inventory in at least one arm. Every changed
file must be inside their union. Complete selected arm inventories must contain
one to 64 ordinary `100644` files, each at most 512 KiB and together at most
4 MiB per arm. Executables, symlinks, gitlinks and mode-only candidates are refused:
the current arm contract represents file presence/bytes, not those metadata
semantics. Cross-root changes or partial cherry-picked inventories cannot claim a
tested improvement through this contract. A verified MCP source blob does not
prove a working connection or support on every client/platform.

Git reads use only fixed raw `cat-file` operations and NUL-delimited recursive
`ls-tree`; no shell, filters/textconv, hooks, replacement objects, prompts, fetch
or lazy fetch are requested. Inherited Git configuration/environment overrides
are excluded. Read limits include 64 KiB per commit, 4,096 recursive tree entries,
1 MiB of tree-object data per tree inventory, and the blob limits above. Each
command has a three-second read deadline and a combined stdout/stderr cap. The
native consumer shares a cumulative 12-second Git-read window across two source
verifications: before assessment and again after it. Time spent fetching remote
anchors is excluded from this Git window. `source_read_limit`, `git_unavailable`
and subprocess `TimeoutExpired` become `source_unavailable` and remain inconclusive.
Wrong source objects, unsupported inventory limits/modes, tampering and out-of-scope
changes reject. Owned process-group termination/reap and stream close are
attempted on failure; uncertain group cleanup refuses source verification. These
are bounded local process operations, not a hard end-to-end wall-clock guarantee.

## Same-host evidence manifest

[The same-host protocol](account-improvement-loop.md#same-host-held-out-evaluation)
owns the experiment rules. `heldout.py` implements its selected receipt path on
the existing host/account. It does not provision an external custodian, isolate a
hostile account owner, parse complete session history, generate packs or dispatch
a preparer. Actual preparation remains a separate root-reviewed fresh-context
operation after the candidate is committed and frozen.

Use **one** private immutable JSON manifest with exactly the following keys.
JSON records use closed field sets and canonical digests; private evidence files
are guarded, ordinary single-link `0600` files. The manifest lives in a `0700`
private directory outside the execution root. Keep all actual paths, context IDs,
cases, answers and raw selected receipts out of public Git and public comments.

| Manifest field | Exact content |
| --- | --- |
| `schema_version`, `kind` | `1`, `same_host_heldout_evidence_v1`. |
| `pack_id`, `repository` | Opaque token and absolute local source repository path. |
| `content` | `{path, sha256, pack_digest}` for the private `{cases, checks}` pack; it must exactly match the frozen declared-scope spec. |
| `source` | Exact verified source result: baseline/candidate commits and trees, component roots, canonical changes and `source_diff_digest`. |
| `experiment` | `{experiment_path, spec_path, context_path, report_path, attempts}`. Reports are future outputs; their current bytes are verified when consumed. |
| `contexts` | `{author, preparation, tasks}`. Author is one to eight `{context_id, input_evidence_path, sha256}` refs; preparation is one such ref; tasks are exact scheduled `{trial_id, attempt_id}` pairs. |
| `exposure`, `preflight` | Each is `{path}` to its fixed future output in the same private directory. These are path-only references, avoiding circular future hashes. |
| `freeze` | `{repository, issue_number, comment_id, created_at, body_sha256}` for the actual GitHub freeze comment. This repository is the public `owner/repo`, not the local repository path. |
| `record_digest` | Canonical digest of the manifest without this field. |

The experiment must use the explicit
[`same_host_heldout` scope declaration](evaluation-accounting.md#optional-same-host-scope-declaration).
Its `pack_digest` is `digest({cases, checks})`; declaration alone retains the
evaluator's unverified/not-assessed/null facts. Both comparison contexts must
match baseline/candidate/grader/runtime/model identities, primary metric,
regression margin and promotion rule, with distinct execution roots. At most
64 attempts are accepted. Each declared path must be exactly
`execution_root/trial_id/attempt_id`, with no duplicate attempt path.

An author input receipt has exactly `schema_version: 1`,
`kind: candidate_author_inputs_v1`, `context_id`, `workspace`, `candidate_commit`,
and `materials`. Each material has `{kind, path, sha256}`, with kind one of
`requirements`, `development`, `source`; at most 64 are accepted per author.
Their actual bytes are checked. The pack must be outside each normalized recorded
author workspace. A listed author material cannot resolve to the pack path or have
the pack's SHA-256, even under another filename. This is a selected trusted-host
input inventory, not a parser that establishes all historical model input.

### Selected fresh-preparer evidence

The preparation receipt uses exactly:

```text
schema_version: 1
kind: same_host_fork_none_dispatch_v1
purpose: heldout_preparation
source: {envelope_version: requirements-only-v1, helper_sha256}
input: {requirements, behavior_categories, message_sha256,
        tool_call_evidence_path, tool_call_evidence_sha256}
dispatch: {tool: collaboration.spawn_agent, task_name, fork_turns: none}
returned: {agent_id, tool_result_evidence_path, tool_result_evidence_sha256}
output: {pack_id, pack_digest, grader_digest, schedule_digest,
         metadata_evidence_path, metadata_evidence_sha256}
chronology: {candidate_freeze_anchor,
             pack_creation_evidence_path, pack_creation_evidence_sha256}
receipt_digest
```

Requirements and behavior categories are each one to eight `{path, sha256}`
UTF-8 inputs of at most 8 KiB each. The source-owned `preparation_message` reads
only these selected texts, the opaque pack ID and private destination. It
explicitly excludes candidate patches/author history and requests digest-only
output. The selected tool-call record is exactly
`{tool, arguments: {task_name, fork_turns, message}, observed_at}`; its message
and `fork_turns: none` must match. The tool-return metadata is
`{tool, agent_id, task_name, observed_at}`. Pack creation metadata is
`{agent_id, pack_id, pack_digest, observed_at}`. Agent identities must agree and
be distinct from every author context. The final selected output is **only**
`{pack_id, pack_digest, grader_digest, schedule_digest}`; an extra answer field
refuses. These actual selected observations are reviewed/retained by the trusted
maintainer; an invented fresh-context boolean is not accepted instead.

Chronology checks a remotely created committed-candidate anchor before the
recorded tool dispatch, then pack creation, returned metadata, and the remotely
created pack/schedule freeze. A Git commit date or local timestamp alone is
insufficient. Tool observation timestamps remain selected trusted-host evidence;
this is not an independent absolute-clock or complete absence-of-read audit.
No candidate edit is allowed after freeze.

### Remote anchors and preflight

The two actual issue-comment bodies are canonical JSON. The candidate anchor is
`{kind: committed_candidate_freeze_v1, source}`. The later freeze is exactly
`{kind: same_host_heldout_freeze_v1, pack_id, pack_digest, grader_digest,
schedule_digest, experiment_digest, context_digest, source,
dispatch_receipt_digest, author_receipt_digests}`. Publish only sanitized opaque
identifiers, repository-relative source changes and digests: never cases,
answers, private paths or context records. Posting these comments is an explicit
maintainer operation; the verifier does not publish them.

The verifier calls the fixed read-only
`gh api --hostname github.com --method GET repos/<owner>/<repo>/issues/comments/<id>`.
It validates actual comment ID, issue URL, exact body and digest, and requires
`created_at == updated_at == declared created_at`. Edited, rebound or missing
anchor assessments remain inconclusive, including malformed metadata and a change
during the final refresh. Anchor uncertainty alone cannot reject a candidate; an
independently established development critical/regression rejection remains a
rejection with the held-out uncertainty recorded. Local manifest/receipt tampering
remains invalid and rejects.
It refetches both anchors late, then rechecks the held-out context, batch and
local evidence guards before accepting the assessment. Each lookup has a
five-second bound and 64 KiB combined output limit;
unavailable transport remains inconclusive, without trusting a copied response.
The selected trusted-maintainer boundary is explicit; this is not a signature
against a malicious maintainer or GitHub administrator.

Only for an already authorized frozen trial:

```sh
python3 scripts/improvement/heldout.py run-next \
  --record /absolute/private/heldout-manifest.json \
  --plan /absolute/private/next-trial.json \
  --auth-source /absolute/private/existing-auth.json
```

The adapter verifies source, manifest, selected records and anchors before using
the existing reservation lease. It writes `same_host_preflight_v1` only while
the actual audited prefix is ready and has **zero** reserved initial turns.
That receipt binds `record_digest`, `helper_digest`, fetched `anchor_digest`,
actual `header_digest` and `reserved_initial_turns: 0`. It is stored outside the
execution root. The source-owned wrapper refuses to mint a missing receipt after
launches begin. Its deterministic bytes alone cannot prove that the wrapper was
invoked before launch against a caller writing identical bytes later; chronology
relies on cooperating use of this trusted-host path.
The lease is released before fixed `trial_reservation.run_next`, avoiding
same-lock deadlock. That gate still owns order, launch reservation, cumulative
unknown/failed usage and its unchanged cleanup allowance; the
[accounting contract](evaluation-accounting.md#serial-native-launch-reservations)
owns cost retention and deduplication semantics. This cooperating-host
protocol does not exclude a hostile same-UID caller bypassing the wrapper.

### Exposure and the narrow verified claim

The future exposure ledger has exactly `schema_version: 1`,
`kind: same_host_exposure_v1`, `events`. Up to 256 events are accepted, each
`{context_id, material, phase}`. Material is `pack`, `case`, `answer`, `pack_read`,
`aggregate_feedback`, `candidate_edit` or `unknown_delivery`; phase is
`before_comparison`, `during_comparison` or `after_comparison`.

Known pack/case/answer/read/feedback delivery to an author before or during
comparison makes the held-out result `exposed`. Unknown delivery makes it inconclusive. A candidate
edit invalidates it. Recorded author exposure reclassifies future use as
`development_regression`; post-comparison feedback does not retroactively erase
the previous fixed comparison. Fresh cases are required before a later unseen
claim informed by that feedback.

A successful receipt assessment returns only
`claim: not_supplied_to_recorded_author_context_during_comparison`, with
`trust_boundary: selected_trusted_maintainer_receipts`.
`filesystem_access: unrestricted_or_unknown` and
`unobserved_filesystem_reads: unknown` remain separate facts. Filesystem access
alone is neither proof of delivery nor automatic failure of this narrower
claim. Absence of an event is not proof against unobserved same-account reads or
prior model training exposure.

The held-out `NativeBatch` and report are recomputed and guarded. Complete serial
accounting and recorded client-model observations are required for both arms;
backend model weights remain unattested. The assessment's `verified` describes
this receipt provenance, not necessarily a favorable rule result. The consumer
returns `recommend` only when **both** development and held-out frozen rules are
eligible and required blockers are absent. A failed rule rejects; unavailable
required facts remain inconclusive. No retry-until-benefit loop exists.

## Predeclared arithmetic rules

Freeze one `promotion_rule` before trials:

- `quality_gain_v1`: more candidate passes on the primary metric, within each
  case/variant's regression margin.
- `equal_quality_lower_tokens_v1`: at least as many candidate passes, strictly
  fewer candidate tokens, within each case/variant's regression margin.

Both require paired complete coverage, qualified deterministic graders, known
token usage within the frozen token ceiling, and known aggregate trial latency
within the frozen seconds ceiling. Observed **candidate** critical violations
reject; baseline defects remain visible diagnostics when the candidate fixes
them. Improvements elsewhere cannot cancel a local regression. These are small
sample diagnostic rules, not statistical confidence/non-inferiority tests.

Currency usage is required only for an explicit frozen `amount`/`currency`
ceiling. Unknown currency otherwise adds no rejection. Recorded latency is the
controller's source-owned monotonic setup/task/cleanup duration when available;
distinct attempts are counted once and missing duration stays unknown. It is not provider API latency, a parallel
wall-time measurement or proof of a hard runtime deadline. Token/dollar soft
accounting and actual enforcement remain the existing runner's responsibility.
`evaluate_rule` itself accepts supplied numbers and remains a diagnostic helper.

## CLI refusals and output authority

For either recommendation subcommand, malformed/oversized JSON (over 16 MiB),
duplicate keys, non-finite numbers or missing/extra top-level fields return
`{"status":"rejected","reason":"invalid_gate_input"}` and exit 1. Accepted
outer fields with invalid local nested evidence return a full reject recommendation
and exit 0. The selected source process-limit/unavailability failures above and
unavailable remote anchors do not themselves establish a negative candidate
result. Source process failures yield inconclusive; a missing anchor yields
inconclusive unless an independent development rejection already applies. Usage
errors exit 2. Exit 0 does not mean evidence or promotion passed.
`heldout.py run-next` uses a fixed small refusal envelope and exit 2 for unavailable
preflight, including bounded subprocess failures; command-usage errors are also
handled by argparse.

Native output includes source/report/experiment/context and gate/recommendation
digests, rule reasons and optional held-out assessment. These are reproducible
change-detection references, not signatures. `source_accepted`,
`promotion_eligible`, `merge_authorized`, `install_authorized`, and
`backend_identity_verified` remain **false**, even for a positive recommendation.
Legacy diagnostic output retains its compatible shape. Actual source acceptance
and delivery follow the existing independent PR review and installer workflow.

## Verification status and primary references

[Promotion tests](../../tests/test_improvement_promotion.py) and
[held-out tests](../../tests/test_improvement_heldout.py) cover actual disposable
Git objects, full inventories/raw bytes, report tampering, critical failures,
cost/unknown facts, selected receipt rebinding, final-lookup drift, malformed
remote metadata, preflight ordering and exposure. Separate actual CLI subprocess
conformance exercises recommend/reject/inconclusive using **FAKE** qualification,
lifecycle, usage/clock journals, context/tool receipts and remote metadata.
It makes no real GitHub freeze lookup, preparer dispatch, inference or unseen-pack
claim. The [native walkthrough](../manual/native-recommendation.pdf) and
[editable source](../manual/native-recommendation.json) retain the FAKE labels. Current public qualification stays unavailable. The
[host-dependent fast-exit/drain limit](evaluation-accounting.md#declared-catalog-routing-and-client-model-observations)
and closed catalog/frontmatter grammar remain prerequisites; favorable mock
records cannot waive them. Follow the
[feature recipe](../verification/verify-repository/features/promotion-recommendation.md)
for repeatable checks; actual current-source qualification, actual pack preparation and real comparison results
remain separate completion prerequisites. A separately frozen real source candidate
is not created or evaluated by these synthetic CLI fixtures.

Implementation follows the already accepted same-host design. Primary behavior
was checked on 2026-10-19 against [Git raw object reads](https://git-scm.com/docs/git-cat-file),
[NUL-delimited tree inventory](https://git-scm.com/docs/git-ls-tree),
[GitHub issue-comment metadata](https://docs.github.com/en/rest/issues/comments#get-an-issue-comment)
and [fixed GitHub CLI API invocation](https://cli.github.com/manual/gh_api).
These document transport/object semantics; they do not qualify this local
experiment or establish community consensus about its effectiveness.

The existing [same-host research note](account-improvement-loop.md#same-host-held-out-evaluation)
records limited, partly promotional community discussion about eval and fresh-session
workflows. It is not independent validation or popularity evidence for this verifier.
