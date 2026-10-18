# Deterministic evaluation accounting

Status: offline synthetic comparison and trusted offline native artifact admission
are implemented. Current native admission remains blocked until maintained
qualification records match the frozen sources and include current authenticated
qualification. Cooperating-host serial launch reservations, recorded client-model selection and
declared-catalog routing admission are implemented; actual comparisons and same-host held-out evaluation remain incomplete. This is the bounded accounting slice of the
[account improvement design](account-improvement-loop.md#comparative-evaluation-contract).
The evaluator and admission reader do not launch agents or execute trace commands.
The separate serial gate below can invoke one explicitly authorized native trial;
none of these commands performs Git or installer actions.

## Usage and frozen contract

Run from a source checkout with Python 3.11 or later:

```sh
python3 scripts/improvement/evaluation.py qualify
python3 scripts/improvement/evaluation.py freeze < spec.json > frozen.json
python3 scripts/improvement/evaluation.py report < report-input.json > report.json
```

`freeze(spec)` accepts exactly `cases`, `checks`, `identities`, `runtime`, `budget`,
`repetitions`, `seed`, `primary_metric`, `regression_margin`, and `promotion_rule`,
plus optional `evaluation_scope` described below.
`report` input is exactly `experiment` (the frozen output), `current_spec`, and
`completions` (a list). Reuse the saved inventory after interruption; this module
never retries work. Write regrades to a separate artifact, retaining the original.
A fresh grader source hash requires a new frozen experiment and explicitly linked
regrade, not silently relabeling the old report. `freeze` deliberately permits a
historical grader identity so old inventories can be reconstructed and reported
as stale; it does not authorize collecting fresh results under that identity.
For a new synthetic collection, use the current `evaluation.py` source hash; native
admission uses the composite identity below. Frozen payload
comparison uses canonical JSON bytes, distinguishing booleans, integers and floats.

- Cases consume the in-tree reviewed Store export v1 shape: `case_id`, `language`, `purpose`,
  `inputs`, `outcome_contract`, `counterpart`, `schema_version`, `classification`,
  `artifact_hashes`, `case_digest`. The ordinary route requires `development`; the optional scope below accepts a
  declared same-host pack without certifying its custody or lack of exposure. A
  renamed public fixture cannot become verified unseen evidence. Fixture hashes and the whole export digest
  are recomputed. Case IDs accept the export token alphabet `[A-Za-z0-9_.:@-]`
  at lengths 1–160; file paths use the export limit of 160 Unicode characters,
  not UTF-8 bytes, and reject backslashes and empty, `.` or `..` segments.
  Canonical JSON uses sorted keys, ASCII escapes, compact separators and a final
  newline; file-content hashes use UTF-8 bytes. No private lineage or arbitrary
  export fields are accepted.
- `checks[case_id][reproduction|counterpart]` contains `contract_digest` and a list
  of `criteria`. Each criterion has `id`, `dimension`, `kind`, `target`, `expected`,
  `critical`. Trusted maintainers must review the mapping from the prose contract
  to these executable criteria. A matching hash does not prove semantic coverage.
- Supported kinds are `artifact_sha256` (literal UTF-8 artifact content),
  `value_equals` (typed structured observation), and `verification_claim` (observed
  exit code versus structured claim, optionally requiring an exact expected exit).
  Missing evidence stays inconclusive. Arbitrary prose cannot be judged by these
  checks; it requires another qualified grader. No LLM judge is implemented.
- Dimensions are `outcome`, `routing`, `adherence`, `exposure`, `mcp_static`,
  `mcp_tool`, `mcp_task`. Every case variant needs an outcome criterion. Unobserved
  routing stays inconclusive even when its outcome passes. Value checks measure
  supplied fields; they do not establish authentic native selection.
- `identities` requires SHA-256 strings for `baseline`, `candidate`, `runner`,
  `grader`, `environment`. For synthetic input, the grader identity is the hash of `evaluation.py`.
  Native admission uses the fixed composite identity described below.
  `runtime` freezes `provider`, `model`, `client`, `adapter`, `reasoning`,
  `tool_versions` (map), and `capabilities` (list). Hashes are consistency checks,
  not custody, attestation or proof of execution.
- `budget` requires nonnegative integer `model_requests` and `tokens`, and positive
  integer `seconds`. Optional `amount` requires `currency`; a dollar cap is not
  mandatory. This module freezes these ceilings but makes no submissions or timing
  enforcement claim. The serial gate below implements initial-turn/phase-time
  reservations and post-use soft-token checks, not provider hard ceilings.

Every reproduction and its successful/contrary counterpart is scheduled for both
baseline and candidate, repeated as declared. The seed randomizes arm order within
pairs. The frozen digest covers the complete spec and trial inventory. Trial IDs
and binding digests bind case, contract, arm, repetition and full frozen context.
Any changed current spec or grader source invalidates all corresponding results.

A synthetic completion contains exactly `trial_id`, `experiment_digest`, `binding_digest`,
`status`, `model`, `evidence_kind`, `artifacts`, `observations`, `usage`,
`latency_ms`. Status is `completed`, `error`, `timeout`, `blocked`, or `cancelled`.
The original `evaluation.py report` accepts only `evidence_kind: synthetic` for
diagnostic grading; its three-argument library contract is unchanged.
Artifacts map names to literal strings. Observations map criterion targets to JSON
values; a verification observation is `{"exit_code": 2, "claim": "failed"}`.
Claims are `passed`, `failed`, or `unavailable`. Unknown exit code is `null`.
Usage is `null` or `{"input_tokens": 123, "output_tokens": 45}`. Latency is an
integer number of milliseconds or `null`. Unknown usage never becomes zero.


## Optional same-host scope declaration

A frozen spec may add exactly `evaluation_scope: {"kind": "same_host_heldout",
"pack_digest": "<sha256>"}`. Its digest must equal the evaluator's canonical
`digest({"cases": spec["cases"], "checks": spec["checks"]})`; selected case
classification must be `same_host_heldout`. Without this field, the existing
`development` schema and three-argument comparison behavior remain unchanged.
Extra claims such as `unseen: true`, a mismatched pack or held-out classification
without the declaration reject. Scope drift invalidates the frozen experiment.

Reports label this **declaration**, not verification:
`classification=same_host_heldout_declared`,
`development_exposure=not_assessed`, `holdout_custody=null`, and
`same_host_heldout_unverified` remains a blocker. Evidence kinds are
`deterministic_same_host_heldout_declared_comparison` or
`native_artifact_same_host_heldout_declared_comparison` for their respective routes.
No case generation, context separation or unseen-by-author certification happens
here; `live_eligible=false` and promotion remains inconclusive. Actual case
preparation, frozen EN/KO runs and the [same-host protocol](account-improvement-loop.md#same-host-held-out-evaluation)
remain separate work.

## In-tree reviewed producer

The producer from [PR #35](https://github.com/hwanjjang/agent-dotfiles/pull/35)
and evaluator from [PR #36](https://github.com/hwanjjang/agent-dotfiles/pull/36)
are integrated in this checkout. The [Store guide](../../account/observation/README.md#prepare-and-export-a-reviewed-synthetic-case)
owns consent, task/feedback lineage, evidence-bound caller triage, exact-digest
review and detached export. Supply the exported file to `freeze`, never the private
case preview or triage envelope. Public v1 fields remain unchanged. The
[integration tests](../../tests/test_improvement_integration.py) exercise the actual
Store export and evaluator together, including English/Korean cases and boundary
inputs. No second private state owner or producer copy is introduced.

Historical PR36 compatibility evidence used out-of-tree producer `5adfbf9`;
its dated manual/capture receipt remains in Git history at `a8fa3b1` and cannot
establish the current integration. Current same-checkout verification is a separate run. Neither
integration nor deterministic operator checks establish actual model execution.

The local CLI accepts at most 16 MiB of JSON input and bounds completion count,
but expanded per-completion checks can produce much larger output and memory use.
There is no output-size cap. Keep inputs small and inspect duplicate counts; this
is a local diagnostic command, not a service or arbitrary-input execution endpoint.

## Selected-trial execution input

The [frozen-trial preparation guide](frozen-trial-dispatch.md) describes the pure
adapter for selecting one request/files payload and supervisor binding. It reuses
this frozen inventory and does not admit real evidence, execute trials or change
this evaluator's eligibility rules.

## Admit recorded native artifact snapshots

```sh
python3 scripts/improvement/trial_admission.py report \
  < /path/to/private-admission-input.json \
  > /path/to/new-private-admission-report.json
```

The separate reader accepts exactly `experiment`, `current_spec`, `context_path`
and `attempts` on stdin (at most 16 MiB). Reuse the frozen inventory. It does not
launch or recover trials, read authentication, contact Docker or execute trace
commands. `attempts` contains at most 64 explicit `trial_id`, `attempt_id` and
private `attempt_path` references. Preserve failed, duplicate and unassigned attempts.
Exit 0 means a report was produced, not that its trials passed; malformed top-level
input returns exit 1 with `status=rejected`.

The private context requires version 1 and kind
`native_artifact_admission_context_v1`, with the required fields below and optional
`execution_root` for the [serial gate](#serial-native-launch-reservations):

| Field | Binding |
| --- | --- |
| `schema_version`, `kind`, `experiment_digest` | Version, typed context and the saved frozen inventory. |
| `arms` | Each baseline/candidate root, entrypoint, sorted relative file/SHA-256 inventory and optional routing catalog described below. |
| `runtime` | Supported profile, exact source digests, Codex/code-mode/Docker/executor-archive digests, image and metadata digests. |
| `qualification_refs` | Exact maintained execution, scoped-grading and collection record paths/digests; routed contexts additionally require the fixed routing-observer record. |
| `collection_by_trial` | Explicit validated collection declaration for every scheduled trial, covering each artifact criterion. |

The [reader source](../../scripts/improvement/trial_admission.py) owns nested fields
and limits; no context generator or caller qualification flag exists. Map actual
frozen files and maintained [execution](../verification/native-trials.json),
[scoped grading](../verification/scoped-grading-integrity.json) and
[collection](../verification/native-outcome-collection.json) evidence. Hashes bind
consistency; they do not establish execution or repair missing qualification.
For native experiments, `identities.grader` is the canonical digest of the fixed
three-file map returned by `trial_admission.native_grader_sources()`:
`evaluation.py`, `trial_admission.py` and `trial_dispatch.py`. Use
`trial_admission.native_grader_identity()` when freezing that identity. It is
checked before admission and after grading; changes between invocations require
an explicitly linked re-freeze/regrade. The original synthetic identity stays the
single evaluator-file hash.

In the report, `qualification.grader_digest` also remains the hash of
`evaluation.py` alone: it identifies the calibrated evaluator operators, not the
native admission composite. Compare that field with the operator source hash;
use native `identities.grader` for the three-helper frozen identity.

The maintained scoped grading record must additionally bind
`admission_grader_source_digests` to that exact three-file map. Its existing
`grader_source_sha256` still names the evaluator operator source; historical
records must not be relabeled as renewed composite qualification. A missing
mapping blocks native admission. This is a fixed dependency binding, not a
caller-defined inventory or a proof against hostile host modification.

The supported declared tuple is OpenAI, GPT-6-Luna, Codex 0.163.0, the pinned
native profile and low reasoning. Declared selection is not backend attestation.

Private context, manifest and journal files require current-owner regular no-follow
files with exact 0600 mode; attempt/journal directories require private ownership and modes. The reader
holds each coordinator lock nonblockingly, validates manifest, dispatch, journal
sequence, collection intent/result, source and cleanup bindings, and rechecks
identities through grading. Active writers, evidence drift and missing qualification
block admission. Maintained collection evidence covers its recorded prior source
set; current reservation, model-selection and routing sources have not renewed native qualification. Preserve recoverable
attempt costs when outcome admission is blocked.

Artifact criteria on this route admit recorded snapshots. Present SHA-256 values are compared
directly to the expected digest; observed missing files fail that criterion.
Absent, unsafe or blocked capture stays blocked. Hashes are never reconstructed
as text or relabeled as synthetic content. Matching bytes do not prove routing,
exposure, general semantic correctness or quiescent final state.

Native reports use `native_artifact_development_comparison`. Internally, the typed
reader adds native-only `attempt_id` to the completion projection; callers cannot
submit that projection as JSON to bypass admission. Duplicate submissions remain
visible but charge one source attempt once. Distinct and failed attempts retain
observed cumulative usage; conflicting receipts, missing usage and discontinuities
leave the affected cost unknown. Known tokens are a subtotal, never a complete
budget when coverage is missing. Wire requests, billing usage and currency remain
unobserved. Selected-model evidence follows the bound client projection described below; it
does not verify backend identity. An optional `execution_root`
adds the separate reservation audit described below.

Native `latency_ms`, when present and valid, comes from the source-bound
`controller_timing` receipt: `clock=monotonic_ns`,
`scope=controller_setup_task_cleanup`, and a nonnegative integer `elapsed_ms`.
The report labels it `source_guarded_controller_setup_task_cleanup`. It spans
controller setup, task observation and cleanup; it is not provider response
latency or a wire-attempt measure. Missing timing remains unknown. Negative,
malformed or wrong-scope timing blocks that attempt's admission; caller timings
cannot replace the bound receipt. This observed duration does not refund the
serial gate's permanent declared phase-time reservation.

The controller, scorer and same-account maintainer are trusted local owners.
These guards do not contain a malicious same-UID host. Remote protected-file
checks retain their own source-bound scope. `live_eligible` stays false and
promotion inconclusive, even when an artifact criterion passes. Current-source
qualification, real comparisons and same-host held-out evaluation remain distinct
requirements; this component does not complete issue #26.

## Declared-catalog routing and client-model observations

The [source-backed workflow](../architecture/native-routing-workflow.html) shows
serial execution, receiver finalization and separate offline grading at its pinned
revision. This section owns the current operator contract.

A routed trial uses plan `schema_version: 2`; version 1 rejects `routing`.
The required version-2 `routing` object contains exactly `mode`, `observer`,
`catalog_scope`, `catalog_digest` and `catalog`. The fixed observer is
`implicit-stderr-json-v1`; scope is `declared_experiment_subset`, not the entire
account catalog. Three to five ordered catalog rows contain `slot`, `name`,
`main_resource`, `main_sha256` and `description_sha256`. Slots start at zero;
names and `skills/.../SKILL.md` paths are unique. The catalog covers every selected
bundle `SKILL.md`, binds its exact bytes and inline name/description frontmatter,
and hashes the normalized description. Missing, duplicate, unsupported metadata
or unlisted skill files refuse; this is a deliberately narrow frontmatter parser.

`mode=natural` omits `inputs.entrypoint` from the native plan. The controller sends
the task prompt without a forced read instruction, and native discovery chooses
from the selected catalog. `forced_entrypoint` retains the explicit entrypoint
and forced-read wrapper; it is not natural selection. Qualification-mode plans
cannot add routing. Files remain frozen under readonly `/runtime/arm`; this field
adds no executor authority, tool route or extra turn.

In the offline context, each routed arm adds this same `routing` object; its
`entrypoint` is explicitly null for natural mode. Both arms must use the same
mode, observer, scope and slot/name/resource layout. Each arm's complete catalog,
file digests and entrypoint are included in its own frozen arm identity. A changed
body or description therefore changes that arm's identity while slot semantics
remain comparable. No expected winning skill or grader target is passed in this
catalog. The operator is responsible for a reviewed task prompt; accepting a
natural declaration does not prove the author avoided every hint.

The receiver projects only native `codex.user_prompt` health and correlated
`codex.skill_invocation` metadata. An implicit main-file **first-page read** is
`implicit_main_first_page_read`. With healthy scope, complete receiver drain and
no qualifying reads, the result is `observed_none_in_declared_catalog`. A list-only,
reference-only or failed-main-read observation cannot establish this signal.
Explicit invocation in natural mode, missing health, identity drift, malformed or
incomplete transport stays blocked/unknown. It is not evidence of semantic
adherence, complete skill pagination, outcome success or producer-side losslessness.

After cleanup and owned transport shutdown, the journal must contain exactly one
of each record in order: `observation`, `cleanup`, `routing_observation`,
`observation_finalized`, `receipt`. The finalized observation must equal the
receipt observation and its routing projection must equal the separate routing
record. Require stdout/stderr EOF, reaped process, no trailing bytes/pending
records, and one persisted projection. `receiver_complete_under_trusted_io` is
this receiver boundary; `native_written_count=null`, `all_pages_verified=false`,
`process_adherence=not_assessed` and `outcome=not_graded` remain explicit.

Routed contexts require the exact maintained path
`docs/verification/native-routing-observer.json` in `qualification_refs.routing`.
That record is not currently available as qualified public evidence. It must bind
current source/runtime/image and the three-source admission grader, observer
profile, normalized catalog, four actual native cases (assigned main, list only,
reference only, failed main), cleanup and false-marker falsification. A caller
flag or synthetic qualification fixture cannot substitute. Existing historical
execution/collection proofs also require renewal for changed sources.

Only qualified, bound projections expose typed criterion targets
`native.routing.none` and `native.routing.implicit_read.<catalog-name>` to the
existing `value_equals` grader. A healthy none may pass an absence criterion or
fail an expected-read criterion independently of artifact outcome. It does not
become an inconclusive observation merely because the expected skill was not read.

Model selection is a separate exact journal projection: requested model,
`thread/start.result.model`, match, reroute and backend-verification flags must
agree with the frozen tuple. Missing, mismatched or rerouted selection cannot
satisfy routed admission. When every scheduled row has qualified complete bound
model facts, the report uses `selection_evidence=persisted_thread_start_client_model`
and removes only `explicit_observed_model_projection_unavailable`. Otherwise it
retains the older source-guarded/no-export label and blocker. Neither path attests
server weights: `backend_identity_verified=false`, live eligibility and promotion
stay unavailable. Current implementation has offline fake-journal verification;
actual current-source native routing/admission and EN/KO comparisons remain pending.

## Serial native launch reservations

The [serial gate](../../scripts/improvement/trial_reservation.py) coordinates one
frozen experiment within one `execution_root` and context among cooperating
trusted-host callers. Its allowance and `execution_accounting` cover that root,
not every root that might reuse the same experiment digest. Creating a different
root or context creates another allowance that this gate cannot detect. Preserve
and report those costs with the original scope; do not hide a failed run or select
the best result by resetting the scope. It does not provide a hard provider
request, token or spending cap. Current real execution remains
blocked until source-bound qualification is renewed; fixed-stub verification is
not native qualification or natural-routing evidence. The
[workflow diagram](../architecture/native-experiment-workflow.html) shows the
reservation, audit and refusal paths; this section owns the operator contract.

Use Python 3.11+ and a frozen native admission context whose optional
`execution_root` names an existing, empty, current-owner 0700 directory. Every
selected plan must use that same `state_root`. The context and private files keep
the admission ownership rules above; the current runner source inventory includes
`trial_reservation.py`. Supply one frozen plan for every scheduled trial, in the
saved inventory order, with its exact attempt identity and limits.

```sh
python3 scripts/improvement/trial_reservation.py initialize \
  --root /path/to/private-experiment < /path/to/private-initialize-input.json
python3 scripts/improvement/trial_reservation.py status \
  --root /path/to/private-experiment < /path/to/private-experiment-input.json
python3 scripts/improvement/trial_reservation.py run-next \
  --root /path/to/private-experiment \
  --plan /path/to/next-frozen-plan.json \
  --auth-source /path/to/explicitly-authorized-auth.json \
  < /path/to/private-experiment-input.json
```

All stdin objects contain exactly `experiment`, `current_spec` and `context_path`;
`initialize` additionally requires ordered `plan_paths`. The CLI does not accept
caller success flags. `initialize` validates qualifications and plans, then writes
an exclusive header and journal without launching a process or opening auth.
`status` audits existing records. Only `run-next` calls the native runner, using
the separate explicit authentication source and the guide's existing execution
authority. These commands do not start a VM, change Docker context or install
account settings. There is no automatic loop or automatic retry. Plans for this
frozen root must use `run-next`; direct `native_trial.py run` is outside the gate and does not
acquire its experiment lock or enforce its aggregate allowance. Recovery remains
cleanup-only and does not complete, retry or refund a reserved task.

One stable nonblocking experiment lock is acquired before native attempt locks
and held through the launch and its cleanup. The gate durably records the next
scheduled reservation before the launch boundary; the runner rechecks its exact
reserved manifest digest before auth or execution. A wrong-order or changed plan,
busy lock, exhausted allowance or incomplete prior attempt prevents that launch.
A reserved slot is permanent: crash, refusal, interruption and recovery do not
refund it or reset the schedule. Preserve blocked state and original receipts.

The frozen `model_requests` allowance counts reserved **initial turns**, not HTTP
requests or provider retries. Each reservation permanently charges the declared
`setup_seconds + wall_seconds + cleanup_seconds` against `budget.seconds`; this
is declared phase-time accounting, not measured provider time or refunded elapsed
time. Before another turn, known cumulative usage plus the next plan's
`soft_total_tokens` must fit the remaining token allowance. Observed overshoot,
unknown or incomplete prior evidence stops further launches. Token checks are
post-use soft observations and may overshoot; wire requests, billing and currency
remain unknown. Do not describe this as a hard provider budget.

| Status | Meaning |
| --- | --- |
| `ready` | Existing reservations have complete bound cost/cleanup facts and another scheduled slot remains; not a task-quality verdict. |
| `complete` | All scheduled slots have complete bound facts within the recorded limits; not native qualification, grading success or promotion. |
| `blocked` | A reserved attempt is unknown/incomplete or a recorded allowance is exceeded. Known usage may still be retained. |
| `refused` | Input, ownership, qualification, order or operation validation refused. Preserve prior state. |

The CLI exits 0 for `ready`/`complete`, 1 for `blocked`, and 2 for caught refusal.
`reserved_initial_turns` counts durable reservations; the separate
`initial_turn_requests_attempted` list records observed per-attempt facts and may
contain unknowns. Neither is a provider wire-request count. `unknown_attempts`
includes incomplete attempts even when some tokens are known, so inspect status
alongside `known_tokens` and nullable `total_tokens`.

When the admission context includes `execution_root`, `trial_admission.py report`
locks and audits **every reservation**, independently of supplied completion
references. Its `execution_accounting` retains this audit; omitting an attempt
cannot remove its reserved allowance, known spend or uncertainty. The ordinary
`usage` field still describes submitted evidence, so do not sum the two views.
An unavailable or blocked audit cannot enable eligibility. Contexts without
`execution_root` retain offline admission behavior and its unavailable-reservation
blocker. All reports keep `live_eligible=false`; current-source qualification, real
comparisons and same-host held-out evaluation remain separate requirements.

## Report and trust limits

Both report routes retain every scheduled trial, all submitted completion digests, unknown
or malformed submissions, duplicate completions, paired per-case results, separate
dimension and arm counts, critical failures, missing coverage, latency and known
usage. Duplicate submissions block the trial and retain all submitted digests and check
rows. Critical violations count each distinct completion digest once per trial
(including native attempt identity for admitted rows);
resubmitting an identical failing row cannot inflate that count. Distinct failing
completions remain counted, and neither can replace a failed result. Synthetic
submitted usage, including duplicate or unassigned submissions, remains in cost
accounting; native usage follows the source-attempt deduplication above.
Unknown/missing usage makes
the total unknown; `known_tokens` is only a subtotal. Dollar cost is unobserved.
The existing `pairs` field retains one baseline/candidate row per case, variant and
repetition. `paired_summary` adds `scheduled_pairs`, `overall`, `dimensions` and
`primary_metric` (the frozen dimension name). Each tally contains `improved`
(fail to pass), `regressed` (pass to fail), `both_pass`, `both_fail`, and `unresolved`
(either arm blocked or inconclusive). All five counts sum to `scheduled_pairs`,
including missing, duplicate, terminal-error, stale and unqualified trials.
Dimensions use their own verdicts; the primary metric refers to its dimension,
not the aggregate outcome. A passing outcome does not resolve unknown routing.
Dimensions with no defined criteria are unmeasured and also appear as unresolved;
inspect the frozen criteria and trial checks to distinguish them from lost evidence.
A primary metric with no criteria is accepted but remains entirely unresolved.
A definite failed criterion takes precedence over another missing criterion in the
same arm: that arm remains failed, and its pair is classified from that verdict.
These are descriptive development counts, not statistical significance,
non-inferiority estimates or evidence of improved model performance.

The grader calibrates its current implementation against known-good, wrong,
subtle artifact error, fabricated success, missing and injected-data examples.
A failed calibration makes grading inconclusive. Calibration covers these closed
operators, not every possible task or an independent safety qualification. Traces
are data and cannot supply grading commands or override the frozen criteria.

`live_eligible` is always false and `promotion` is always inconclusive. The original
synthetic report uses `deterministic_development_comparison`; native admission uses
the separate evidence kind above. No caller flag, account-doctor result or mock
isolation receipt establishes qualification. The [revised design](account-improvement-loop.md#same-host-held-out-evaluation)
requires context separation and exposure records, not an external custodian.
No full issue-26 acceptance or actual comparative result is claimed by this slice.
The [implementation handoff](account-improvement-loop.md#implementation-handoff-and-evidence-boundaries)
links collection (#54), protected grading (#55) and their admission consumer (#26).

The [Anthropic evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
(accessed 2026-10-18) distinguishes trials, observable outcomes and grader
calibration. This implementation follows the already accepted repository design;
it introduces no external runtime or new billing framework. See
[test coverage](../../tests/test_improvement_evaluation.py) and the
[implementation](../../scripts/improvement/evaluation.py).
