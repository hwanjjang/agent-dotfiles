# Local state and receipt contract

Run the helper using `python3 <resolved-skill>/scripts/sdlc_state.py`. It uses only the Python standard library and POSIX file locking (macOS/Linux). It never runs commands from receipts, launches a provider, accesses GitHub, or authorizes external operations. Return code 0 means the requested local operation passed; 2 means a structured error. The CLI prints JSON. Its observations are local checks of records; it cannot prove a model's claims, actual remote state, or host enforcement.

## Commands

```sh
python3 <skill>/scripts/sdlc_state.py init --root <repo> --task issue-123 \
  --mode implementation --change-kind behavior --endpoint main --criteria AC1 AC2
python3 <skill>/scripts/sdlc_state.py inspect --root <repo> --task issue-123
python3 <skill>/scripts/sdlc_state.py begin --root <repo> --task issue-123 \
  --stage triage --objective 'Identify issue scope and current repository state'
python3 <skill>/scripts/sdlc_state.py finish --root <repo> --task issue-123 \
  --stage triage --receipt <filled-receipt.json>
python3 <skill>/scripts/sdlc_state.py validate --root <repo> --task issue-123 --stage triage
python3 <skill>/scripts/sdlc_state.py skip --root <repo> --task issue-123 \
  --stage design --reason 'No architecture or flow change; verified against spec'
python3 <skill>/scripts/sdlc_state.py validate --root <repo> --task issue-123 --checkpoint pre-commit
python3 <skill>/scripts/sdlc_state.py validate --root <repo> --task issue-123 \
  --checkpoint pre-merge --gate <current-merge-gate.json>
python3 <skill>/scripts/sdlc_state.py validate --root <repo> --task issue-123 --checkpoint completion
```

Replace angle-bracket paths; these examples are syntax, not commands to run literally. `init` rejects an existing task. Resume via `inspect`, not reinitialization. Choose mode `review-only`, `plan-only`, or `implementation`; non-implementation modes require local endpoint. Change kinds are `behavior`, `refactor`, `non-executable`, `configuration`. Endpoint is an intent constraint, not proof of authority.

New PR implementation tasks use `review_workflow: "2026-10-01"`. New tasks also record `reviewer_effort_default: "high"` (see [reviewer effort authority](#reviewer-effort-authority)); do not add or edit it by hand. The historical 14 stage IDs remain readable, but independent-verification is excluded in this route. Do not initialize or manage non-PR work unless AK asks.

State lives at `reports/sdlc/<task>/artifacts.json` in the ignored local reports tree; paths may not escape the target root. Follow [artifact retention](artifact-retention.md) to retain required evidence and transfer real files with matching digests to other contexts. Ignore status does not waive any file or gate check. This helper does not enforce Git content, outgoing commit history or CI retention; use the repository's separate read-only checker for those concerns. Task IDs use lowercase letters, digits, hyphens and underscores. Do not edit counters by hand. The main agent is the sole writer; flock and atomic replacement prevent concurrent helper writes from losing updates. Record actual assignment identities in the stage objective/receipts and [delegation records](../assets/delegation-receipt.json).

## Iterations and route changes

Every applicable stage has a separate `iteration_limit: 10`, `iterations_started`, and numbered `history`. `begin` reserves one iteration before work. Ordinary reads/tests within that bounded attempt do not start another iteration; a new corrective assessment does. A started attempt remains counted after interruption. `finish` it with BLOCKED and the interruption/reconciliation result before replacing it. A later `begin` after NEEDS_HUMAN requires `--resolution` containing the actual human decision/source; it is not a request to invent approval. No command resets an exhausted counter.

Beginning an upstream stage again marks affected completed/blocked downstream stages stale, preserving their histories and counters. Finish/cancel a downstream running attempt before upstream re-entry. Use the same task/stage IDs. Changed scope does not replenish counters. An exhausted stage requires reporting the gap to AK, not silently minting a new task.

Design can be skipped with a rationale. For non-executable changes, test-design can be skipped; self-verification still requires document checks. Legacy/non-implementation routes remain readable. The revised PR route excludes independent-verification at initialization; it is not a missing gate or report. Correction is initially excluded. Any failed PR-review attempt or findings automatically activate it. Perform actual fixes through build and renewed checks/review; after the latest PR review passes, run the correction stage to assess the finding dispositions and corrective evidence, then reach the authorized endpoint. Each build/review re-entry consumes that stage's own allowance. Do not skip correction when required findings remain.

## Filled receipt

Start from [receipt.json](../assets/receipt.json). Required fields:

- `iteration`: the exact running iteration number.
- `decision`: PROCEED, NEEDS_HUMAN, or BLOCKED; plus nonempty `reason`, `authority_source`, `candidate`, `next_action`.
- For PROCEED, `inputs` contains the exact latest output references from **all applicable upstream stages**; use inspect to gather them and actually read them. Extra relevant input refs are allowed.
- `outputs`: references with `kind`, repository-relative `path`, and lowercase SHA-256 of the actual bytes. Empty, missing, escaping or changed files fail. Hash with Python `hashlib.sha256(Path(path).read_bytes()).hexdigest()` after generating the artifact.
- `assessment`: actual assessor identity, content-assessment summary, and known acceptance `criteria` IDs. A summary is required but its truth must be independently assessed. Completion accounts for every criterion, including explicit limitations where relevant.

Required output kinds by stage:

| Stage | Output kinds |
| --- | --- |
| triage, intent, investigation, spec | The stage name |
| plan | plan; plus user-scenarios in the revised PR route |
| design | design-source, design-html, design-validation |
| test-design | test-plan |
| build | build, change-record (actual diff/versioned change reference), candidate-source (actual source/test file snapshots) |
| self-verification | self-verification, test-results, hashed execution-log references; plus documentation in the revised PR route |
| independent-verification (legacy) | independent-verification; excluded in revised PR tasks |
| pr-review | pr-review |
| correction | correction |
| merge | merge |
| completion | completion |

For build, include a `candidate-source` reference for every relevant changed source/test/configuration file; this hashes actual implementation bytes in addition to the retained diff. Empty source files are allowed. For a deleted file use `kind: candidate-source`, its relative path, `absent: true`, and `sha256: null`; its reappearance invalidates the receipt. The verifier checks the snapshot file set against the actual diff, since the helper cannot discover omitted changes itself. Do not use a prose report as a source-file snapshot.

Output content follows [stage deliverables](../assets/stage-deliverables.md), not just the kind label. The CLI validates shape, existence, freshness and required kinds. A verifier must still examine minimum content, acceptance consistency and actual behavior. Receipts with BLOCKED/NEEDS_HUMAN retain limitations without pretending that missing outputs passed.

`candidate` consistently identifies the tested source content. It can be an exact commit or a source-tree digest with an explicit file-set/commit mapping recorded in the build report. Do not include mutable execution ledgers in the source identity. Before a commit exists use a content digest, then verify that the committed source is identical and retain that mapping. Do not rewrite historical test evidence to claim tests were executed on a later commit. All applicable self-verification and PR-review receipts must attest the same candidate (legacy verification receipts retain their original contract); `review.head` separately records the exact current PR SHA.

## Test results and legacy verification

Use [test-results.json](../assets/test-results.json) and the [smoke scenario template](../assets/smoke-scenario.md). Results contain the candidate, scenario definitions, and ordered runs. Each scenario has ID, known requirement ID, required boolean, environment, prerequisites, actions, expected/failure outcomes and cleanup. Each run has unique ID, phase, candidate, command, integer exit code, environment, observed result, retained evidence path, execution kind and status.

For a passing receipt, every listed run has status `passed` meaning its expected assertion was observed. Red must have nonzero exit code and `intended_failure: true`; other runs must exit 0 on the final candidate. Behavior/configuration consumes the [verification mode contract](verification.md#tdd-method-and-alternative-evidence): default `tdd` requires ordered `red`, `green`, applicable `post-refactor`, then `smoke`. Explicit `alternative` requires a complete `tdd_exception`, real scenario-linked alternative runs covering every AC, then separate smoke; it cannot contain TDD phases. Refactor requires `regression` then `smoke`. Non-executable changes require `document` runs and `not_applicable_reason`, without fake smoke. Preserve failed earlier rounds in stage history; do not erase them from evidence.

Required smoke scenarios need real runs (`execution_kind: real`) with observable outcomes. Mocks cannot satisfy integrated smoke. Focused verification and smoke must have different execution IDs and retained evidence files. Every run's evidence file is also a hashed output reference in the self-verification receipt. Use actual context-specific test commands; no universal test framework is installed.

Only legacy independent-verification receipts additionally contain `verifier`: `independent: true`, `context_id`, different `builder_context_id`, and `checks` describing independently executed/inspected work. This is a record of actual execution, not a switch that creates a verifier.

## PR review and merge

PR receipts include `review` with author_provider, provider, model, context_id, independent, model_selection_source/time, latest_ga_model_verified, requested_effort, effort, effort_verified, requested_mode, mode, mode_verified, candidate, head, base, verdict, findings, record_url and record_id. Reviewer slots 1 and 2 use a provider different from the author; slot 3 may use the author provider after both prior reviewers cannot proceed. In all cases context differs from the builder; requested/effective effort follows intent authority and the [shared-review default](#shared-review-records) (otherwise medium) and permission-mode configuration is optional; isolation defaults to optional (`read_only_required: false`), with actual verified status and evidence/limitations recorded. Requested/observed mode fields may be omitted, null or default and must reflect actual observations. PASS has no unresolved Must Fix. Findings have severity/category/location/finding/evidence/impact/verification/requirement/confidence/disposition and reviewer_resolution when required. For revised PR tasks, use stable finding `id`, `classification` (required/recommended), `author_action` (applied/rebutted/not-selected) and nonempty `author_response`. PASS additionally requires `author_changes_remaining: []`; applied changes need reviewer confirmation, Required findings need reviewer resolution, and unselected recommendations need no follow-up record. See [review policy](verification.md) for semantics and provider selection. Native tool/profile names are not proof.

Pre-merge additionally requires [merge-gate.json](../assets/merge-gate.json), freshly populated from actual repository/provider observations. Head/base match the reviewed SHAs, candidate matches tested content, authority and protections are satisfied, required CI passed, human requests resolved, production_trigger is `none`, and remote_state_verified is true. Include authority source, timestamp, remote record and hashed retained observation evidence. **Refresh this immediately before mutation**; the helper does not fetch GitHub or detect remote drift by itself. Pass expected head to the actual merge API/tool and honor merge queue protections.

Merge completion receipts retain `merge_gate` and `merge`: delegated, production_trigger, protections_satisfied, required_ci_passed, base, expected_head, main_commit, record_url, and remote_main_verified. Verify actual remote state and required main checks before recording them. Keep authoritative post-commit/post-merge records in authorized PR/task storage; local snapshot files are indexes/evidence, not replacements for posting. Do not commit receipts recursively into the candidate they attest.

## 2026-09-08 — Pre-merge readiness and reviewer amendment

Source: AK authorized the pre-merge contract and reviewer latest GA model / medium / auto-or-full. This supersedes the old maximum-effort, flagship and auto-only receipt requirements. Existing schema-1 tasks, endpoint meanings and 14 stage counters are retained. This dated amendment is historical where superseded by the 2026-10-01 PR workflow below. Existing reviewer records remain readable history but must be renewed to satisfy the current gate; do not relabel unexecuted settings or reset task history.

`init --endpoint pre-merge` selects the implementation route with merge excluded. `local`, `pr`, `main` retain their meanings; review-only/plan-only still require local. The existing completion stage requires exactly one additional output of kind `merge-ready`, referencing a JSON document based on [merge-ready.json](../assets/merge-ready.json). There is no new stage or counter.

Run `validate --checkpoint pre-merge --gate <fresh-merge-ready.json>` on this endpoint to assess readiness without main authority. `finish --stage completion` and `validate --checkpoint completion` recheck the persisted merge-ready JSON and its hashed evidence/authority. Completion candidate must match the tested/reviewed candidate. `begin --stage merge` is rejected. Never enqueue, enable auto-merge, call a direct main integration API or push main from this route. The helper itself executes none of these actions; the host must honor the boundary too.

The readiness JSON records exact head/base/candidate, repository, PR URL, push/PR verification, mergeable, passed required CI, satisfied protections, resolved human requests, observed remote state, checked_at, remote_record and hashed evidence. `merge_ready` must be true; `merge_authorized`, `auto_merge_enabled` and `merge_queue_enqueued` must be false. `production_trigger` must be inspected and known: coupling may be recorded because no integration runs here. A future actual merge still requires separately authorized production handling as applicable.

`authority` is a hashed `pre-merge-authority` reference to the explicitly approved [authority contract](../assets/pre-merge-authority.json), with matching task/repository/endpoint, source, allowed actions/materials, prohibited actions and exact configured account IDs mapped to actual providers. The template is not authorization. Read and verify this contract before dispatch or external publication/transfer. Only code, tests and SDLC evidence within the approved task are covered; no credentials, new account enrollment or permission escalation. Routine stage transitions/retries within that scope do not need another question. Auto-review/sandbox controls remain effective.

For new PR reviewer receipts use [reviewer-configuration.json](../assets/reviewer-configuration.json): actual author_provider/provider, separate author_account/account, different builder_context_id/context_id, latest_ga_model_verified, requested_effort=effort=the intent-derived value (the task's recorded default when intent selects none), effort_verified=true, optional read_only_required=false and honest read_only_verified/evidence, optional honest requested/observed mode and mode_verified fields, actual model-selection source/time, model ID and the existing head/base/candidate/finding/record fields. Account aliases do not establish different providers. Codex/OpenAI account variants normalize to openai and Claude/Anthropic variants to anthropic. The adapter must resolve other aliases to their actual provider identity before writing receipts.

For legacy pre-merge independent verification only, `verifier.configuration` contains the same verified reviewer configuration fields (not a PR verdict); its context and builder IDs must match the verifier envelope. Readiness verifies both verification and PR-review accounts against the initial authority, the same implementation author, and matching candidates. One eligible independent worker may perform both duties with separate outputs. Requested/effective settings and model recency are recorded claims requiring actual adapter evidence, not catalog lookup by this CLI.

Remote freshness is explicitly observational: the helper does not query GitHub, make an old snapshot current, or detect unrecorded remote movement. Re-observe head/base, CI, mergeability, auto-merge/queue and protections immediately before marking ready and again before any later authorized merge. Source or referenced evidence changes fail hash validation; upstream re-entry invalidates downstream status without resetting counters. A successful old readiness receipt is not durable permission to merge.

Concise Required/Recommended findings, blockers and final readiness are posted in PR comments; detailed structured evidence remains in reports. No per-command or per-iteration commentary spam is required. Updating this source does not change already installed account snapshots.

## 2026-10-01 PR workflow and compatibility

New implementation tasks with pr/pre-merge/main endpoints use this revision. Do not introduce new state management for non-PR work unless AK explicitly asks. Historical local/advisory routes remain unchanged for compatibility. To adopt the revision for an existing PR task, reconcile all running attempts first, then run:

```sh
python3 <skill>/scripts/sdlc_state.py upgrade-review-workflow --root <repo> --task <id> --source <actual-AK-instruction-reference>
```

This operation excludes independent-verification and marks affected plan/downstream evidence stale while preserving every historical attempt and counter. It is idempotent for already updated tasks. Do not hand-edit state, reset budgets or call old reports new evidence. Prior findings lacking IDs need an explicit `legacy_finding_mapping` object in the new review record, for example `{"1:2": "LEGACY-2"}` maps the second finding in the first PR-review history entry to stable ID `LEGACY-2` (both positions are one-based). Map every finding without an ID and retain each mapped ID in the current findings. Distinct findings within one historical attempt need distinct IDs; repeated observations across attempts may share an ID. Later reviewers must preserve previously recorded mappings. Legacy `Must Fix` disposition or `BLOCKER`/`HIGH` severity remains Required during handoff: reclassification needs reviewer rationale, and retained Required findings need reviewer-confirmed resolution before PASS.

### Plan scenarios

A revised plan receipt requires exactly one `user-scenarios` output referencing JSON based on [user-scenarios.json](../assets/user-scenarios.json). Each scenario has a unique ID, user, goal, prerequisites, ordered nonempty steps, expected and failure results, and known acceptance criteria IDs. Together scenarios cover the criteria. Inspect their actual content and connect scenario IDs to tests and manual sections; structural validation cannot establish meaningful coverage.

### Documentation and manual

Self-verification requires exactly one `documentation` JSON output based on [documentation.json](../assets/documentation.json): `checked: true`, an actual assessment summary, booleans `new_feature` and `ux_ui_changed`, and an `updates` array of hashed maintained-document references. Assess affected manuals, README/API/operations docs and diagrams.

When either feature/UI flag is true, `manual` contains hashed `source` and `pdf` references, a nonempty `screenshots` reference array, `render_checked: true`, and a summary of actual rendering/visual checks. Deliver maintained source, PDF and actual usage screenshots; API/CLI features use actual calls/usage/results. If neither applies, manual may be null with the assessment explaining applicability. The CLI checks referenced bytes and PDF signature; it does not render the PDF, inspect screenshots or prove that feature classification is correct. Use the actual artifact skill and review the content.

Completion requires `documentation_final_checked: true` and `author_changes_remaining: []`, attesting the same reviewed candidate. Late changes require renewed affected verification and PR review. Keep review/manual records durable per the retention contract.

### Reviewer fallback and finding handoff

This schema describes the required reviewer. Record [additional optional
reviews](optional-reviewers.md) separately in the PR-review index, including skipped
outcomes and publication references. Separate optional-only runs do not become
mandatory reviewer receipts; shared roles use the [shared-review record](#shared-review-records)
below. Consolidate actual findings into the required review/correction record. A
Required finding arriving after PASS suspends readiness: renew the required review
with that stable ID and reviewer resolution. The CLI cannot observe late optional
returns; main must reconcile all returned/skipped assignments before readiness.

Reviewer configuration adds `reviewer_slot` (1, 2 or 3) and `unavailable_reviewers`, an ordered array for every earlier slot. Each entry records `slot`, actual `provider`, configured `account`, concrete `reason` and availability/failure `evidence`. Slots 1 and 2 must differ from the author provider. Slot 3 may share it but always requires a separate context. Both earlier slots must have genuine unavailable observations; profile aliases do not create provider independence.

Inability to execute required checks advances to the next reviewer just like rate limits or unavailable tools/configuration. Transfer available evidence and remaining checks; exhausting all reviewers remains incomplete rather than PASS. Existing latest-GA/authorized-effort and authority requirements still apply; enforced read-only isolation is optional unless explicitly required. No new accounts or permission changes are authorized.

Every finding, including findings returned in a blocked review, has a stable ID. Subsequent reviews retain those findings and their author responses/fixes; silent removal or unexplained Required downgrading fails handoff validation. Publish concise Required/Recommended comments and retain full evidence. The builder selects changes, applies/verifies/pushes, and repeats until review PASS and no selected work remains. Unselected recommendations end in the review record without follow-up tracking.

Revised pre-merge readiness validates self-verification plus PR review and the authorized executing accounts; it has no dependency on an independent-verification receipt. Old receipts and counters are preserved, not retroactively relabeled. The CLI remains a local checker: it cannot publish issue comments, run a reviewer, observe remote freshness or authorize external actions. Use the [issue workflow integration](workflow.md#issue-workflow-integration) for stage issue records.

Mode discovery evidence must distinguishunknown metadata from verified execution and concrete unavailability. Preserve the raw host permission mechanism and observation reference alongside the receipt. An empty catalog does not justify fallback by itself, and an unknown effective mode never satisfies `mode_verified`. See [incomplete mode discovery](host-adapters.md#incomplete-mode-discovery).

## Reviewer effort authority

Without an override or a new shared-review selection, the task's recorded default applies: `init` records `reviewer_effort_default: "high"`, and a state without the field (created before 2026-10-30) keeps `medium`, so existing schema-1 histories remain valid under their recorded configuration. Any other recorded value rejects the gate. The main/host adapter first authenticates and interprets an explicit task-scoped AK user instruction. Only then may the latest successful, complete persisted intent receipt include one additional output of kind `reviewer-effort-authority`. No new CLI command, launch setting or permission grant is introduced. Structural checks do not authenticate a user: a JSON flag or source-kind label alone is not authorization.

That hashed, repository-relative JSON has this exact required structure (extra fields grant no authority):

```json
{
  "task_id": "the-current-task",
  "authorized_by": "AK",
  "explicit": true,
  "effort": "high",
  "source": {
    "kind": "user-instruction",
    "path": "tasks/the-current-task/user-instruction.md",
    "sha256": "the-actual-64-lowercase-hex-source-hash"
  }
}
```

Recognized values are `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; a value's recognition does not establish actual host support. Both authority and source must exist, remain nonempty and match their recorded hashes without escaping the repository. Missing or invalid source, multiple outputs, wrong task, non-AK/nonexplicit authorization, and unknown effort reject the gate. Intent submission itself checks this structure; the latest successful complete intent selects the value, never arbitrary review fields such as `authorized_effort` or `expected_effort`.

For every active PR review and legacy verifier readiness check, `requested_effort` and the actually observed `effort` must both equal the derived value (with the shared default below when applicable) and `effort_verified` must be true. The optional review field `reviewer_effort_authority` is null/absent by default or repeats the exact consumed output reference; it cannot select another artifact or create an override. Preserve model/provider, independence, fallback, account and authority checks; isolation enforcement is optional unless explicitly required. If the host cannot resolve/observe the authorized value, use the existing unavailable-reviewer path without relabeling it.

Revalidating a current review rechecks the nested instruction source hash. Changing authority requires assessed intent re-entry through existing begin/finish operations, which invalidates downstream stages without rewriting history or resetting counters. Earlier literal-medium amendments are superseded for current authority resolution only; historical receipts remain unchanged.

## Shared-review records

The [additional-reviewer contract](optional-reviewers.md#one-assignment-per-reviewer)
owns selection and reuse. For a newly selected shared run, set
`review.shared_optional_review` to `grok` or `gemini` in the existing required
receipt. The validator checks its actual provider (`xai` or `google`), using
known provider aliases, and expects high effort unless the consumed explicit
intent authority selects another effort. A launcher such as `antigravity` does
not identify a model provider; resolve it through the host. Unknown/mismatched
roles are rejected. This selection is a policy default, not fabricated user
instruction evidence or a new fallback slot.

Keep the required context, candidate, exact head/base, model, slot, findings and
publication reference. The additional-review index links to that same receipt
and records `shared`; it is not a second independent verdict or comment. Isolation is optional for required and additional roles alike. Explicit
effort overrides, model/independence checks, unavailable-provider records
and fresh PASS evidence remain mandatory.

Absent/null `shared_optional_review` preserves the existing effort behavior. Do
not rewrite old receipts or attach this field to a completed medium run to claim
high execution. Reusing an earlier valid result is recorded in the additional
index with its actual settings and remaining limitations. The validator checks
recorded configuration; the host still owns dispatch deduplication and must verify
that a reused result covers the current candidate and required scope.

## 2026-10-15 optional permission-mode/read-only fallback (historical; superseded 2026-10-20)

The 2026-10-15 policy made permission-mode configuration optional. Its isolation
prerequisite and legacy-mode-only compatibility gate were superseded on
2026-10-20 below. Historical receipts retain their actual recorded observations;
the validator does not rewrite them. See the [current execution evidence contract](host-adapters.md#read-only-review-with-optional-mode-settings).

Read-only evidence must cover tool and network/external-write boundaries as well as input integrity; an immutable source copy alone is insufficient when external mutations remain unrestricted. The local validator checks the evidence claim and shape, not actual host enforcement. Retain launcher/tool observations and executed-operation/source-hash evidence.

## 2026-10-20 optional reviewer isolation

AK made enforced read-only isolation optional. New templates default
`read_only_required: false`; absent/unverified isolation and missing/default mode
settings do not block review. Record actual `read_only_verified` and evidence or
limitations without inventing proof. A true verified claim requires nonempty
evidence; `read_only_required: true` explicitly opts into that gate. Other
provider/model/effort/independence, candidate, findings and authority checks remain.
The validator does not rewrite historical receipts or claim host enforcement.
