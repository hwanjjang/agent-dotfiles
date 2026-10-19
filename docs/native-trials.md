# Frozen native trials: operator guide

The source implements `check`, `run` and guarded `recover` for one pinned native
trial. Retained [execution](verification/native-trials.json),
[scoped grading](verification/scoped-grading-integrity.json),
[collection](verification/native-outcome-collection.json) and
[fixed routing](verification/native-routing-observer.json) records bind the eight
bounded checks to runtime source13 and the admission grader. Their shared
[provenance](verification/native-qualification-provenance.json) preserves original
proof identities and scope; earlier selected records remain in immutable Git.
These records qualify the exact current checkpoint below. Later source changes
require renewed source-bound evidence; historical results cannot be relabeled.
Other hosts and completed natural EN/KO comparisons remain pending.

The [design contract](decisions/native-trial-execution.md) owns the boundary and
acceptance rules. This guide covers operator inputs and result interpretation.
The [controller](../scripts/improvement/native_trial.py) and
[plan validator](../scripts/improvement/native_trial_plan.py) own the exact schema.
These commands do not install account settings, activate hooks, create a VM,
change Docker context, log in, compare arms, grade general tasks or promote changes.

## Startup diagnostics and interruption retention

A failed startup RPC now includes optional `rpc_failure` metadata with a fixed
method, phase, failure kind and standard JSON-RPC code category. Messages, data,
authentication and arbitrary codes are never retained. Existing failure verdicts
remain unchanged; for example `protocol_refusal` can now identify `account/read`
and `internal_error` without storing the provider response. This class identifies
the failed operation, not a proven cause or permission to repeat a model task.
A tolerated `turn/interrupt` RPC failure can also appear here; the primary reason
(such as `soft_usage_stop`) remains authoritative and cannot permit continuation.

Supervisor interruption preserves attempted/started turn counts and already
observed usage in the blocked observation before the existing collection and
cleanup path runs. After a started turn, declared collection can now run within
the original cleanup budget, after owned processes stop and temporary auth is
removed, before the executor is removed. Pressing Ctrl-C can therefore still wait
for that bounded collection. It never upgrades an interrupted result to completed. The
[serial contract](decisions/evaluation-accounting.md#continue-untouched-rows-after-a-verified-startup-failure)
owns optional independent-row continuation; possible turn start or uncertain
cleanup cannot use it.

These changes invalidate the previous runtime/grader identities. Their local
protocol, lifecycle and CLI checks are conformance evidence; actual qualification,
production interruption and comparison on the changed source remain pending.
The checkpoint below records the prior qualified bytes and is not renewed by
these changes.

## Current qualification checkpoint — 2026-10-19

All eight fixed checks ran afresh on source commit `2f50e00` and passed: one
authenticated boundary, four authenticated routing controls and three
credential-free collection/interruption controls. Runtime source13 identity is
`42c0035b3c649b8c85e4c21b1c9900bcb781048cf284c8f409b24da1bd4a4eef`.
The unchanged admission reader accepts the selected execution, scoped-grading,
collection and routing records for that source. Each observation retains its
original manifest, canonical receipt, reviewed private-helper hashes and custody
audit. All owned temporary authentication and control resources were removed,
and the dedicated validation VM was stopped.

Five earlier renewal failures remain unchanged, including one with unknown
usage. A later pass does not erase those failures or establish reliability.
The corrections address bounded macOS exit settling and unambiguous prompt
copying; exact input, output, challenge and cleanup predicates remain enforced.
This completes the fixed executor qualification, not candidate comparison,
backend-model attestation or account installation.

## Historical qualification checkpoint — 2026-10-19

The [source-bound checkpoint](https://github.com/hwanjjang/agent-dotfiles/issues/54#issuecomment-6257672901) records all eight planned
bounded checks passing: one authenticated boundary, four authenticated fixed
routing cells and three credential-free collection/interruption cases. Runtime
source13 identity is
`96432af6d5eb5c60a42b7a04fb9fb7ae13e5be832128e9cc00cd7a8a0ddf677a`.
At this checkpoint the tested code was a local candidate based on main `484e9d9`.

Failed attempts remain preserved, including one process-query cleanup failure
resolved through separately verified owned recovery before a fresh check. The
original failed receipt was not changed. At that checkpoint, six observations
retained their original reviewed private-helper revisions under unchanged relevant
conditions; only the two corrected prompt cases had fresh observations. Credential-free checks keep
the private-bridge limits below; they do not exercise full public `observe`/`finish`.
PR #71 merged the identical runtime at `5be8753`. At that historical checkpoint,
the maintained records projected those observations without another native/model
call. That renewal did not establish a production task outcome, candidate benefit, backend
model identity or account activation.

## Selected evidence and current limits

The [execution record](verification/native-trials.json) selects the authenticated
boundary receipt and verified cleanup for its recorded source/profile. The
[provenance companion](verification/native-qualification-provenance.json) binds
all eight original manifests, canonical receipts, reviewed private helpers,
source/runtime identities and custody observations associated by the trusted
coordinator with each original evidence location. The custody audit's fixed
all-true content hash can repeat; distinct manifest, receipt, journal and metadata
digests identify cases. It is not a case-unique or independently signed audit.
All eight selected observations are fresh after the final source change.
No earlier source success or failed receipt is relabeled.

Execution, grading and collection records point to their exact preceding Git
revision and file digest. That revision preserves historical V7/V8/V9/V10 and
12-source evidence under its original source bindings. The
[screenshot manual](manual/native-trials.pdf), [editable source](manual/native-trials.json)
and [workflow diagram](architecture/native-trial-workflow.html) retain their own
historical source/capture provenance; they do not attest the current records.

Credential-free evidence is a private-coordinator attestation around the public
fixed fixture, whose own result remains `mock_complete` or `blocked`. It does not
exercise production `observe`/`finish`, authorize inference, or establish a task
outcome. Metadata hashes identify retained proof, not a reproducible public
orchestration command or protection against a hostile same-account owner.

## Scoped grading integrity

The [retained scoped evidence](verification/scoped-grading-integrity.json) verifies
actual task read/write/readback and known protected grading, other-arm and synthetic
installer receipt/journal read/write/create probes through a native command and an
explicit Python child. The owner creates those eight synthetic protected files
outside executor mounts and checks identity/content plus absence of new sibling
files after owned shutdown. ENOENT is supported by actual owner-side existence and
observed mount exclusion; a failed child or missing probe is not denial evidence.

The local controller/scorer and same-account maintainer retain normal access.
These probes cover remote task/result-producer paths, not hostile whole-account
containment. No real account state, credentials or model inference is used.
The existing fixed native fixture returned `mock_complete`; a private coordinator
separately checked the outer boundary, owned cleanup and restored VM state.
Current selected bridge receipts retain no raw native contents. Earlier archive
and process-query failures remain in their original evidence/history; later PASS
results do not change them. This is not a new public CLI status.

The evaluator also rechecks frozen source/spec identities after grading. Drift
blocks verdicts while preserving already observed critical counts as diagnostics.
Public cases remain development data. For unseen-by-author evaluation use the
[same-host protocol](decisions/account-improvement-loop.md#same-host-held-out-evaluation).
Historical manuals/diagrams retain their capture/source provenance; they do not
establish current authenticated qualification or these additional predicates.

## Offline artifact admission

The [admission contract](decisions/evaluation-accounting.md#admit-recorded-native-artifact-snapshots)
connects exact recorded artifact collections to the existing evaluator through
`trial_admission.py report`. A `completed_ungraded` receipt alone is insufficient:
the reader checks frozen attempt, dispatch, source, collection and maintained
qualification bindings. The maintained records now satisfy the unchanged
qualification checks for their recorded source/profile. A later
[partial development pilot](https://github.com/hwanjjang/agent-dotfiles/issues/27#issuecomment-6261300514)
exercised the normal production reservation, observation, collection, cleanup and
admission path for three rows. Its full schedule remains two pass, one fail, one
cleanup-blocked and four missing. Later physical cleanup preserved the original
blocked receipt; neither the complete comparison nor the interrupted production
path was validated. The current fixed qualification does not complete that pilot.
The reader does not execute or recover trials; preserve failed attempts and
unknown costs.

Matching artifact bytes do not establish routing, exposure or general task
correctness. The [routing and client-model contract](decisions/evaluation-accounting.md#declared-catalog-routing-and-client-model-observations)
now defines optional arm catalogs, finalized receiver records and persisted
client-model admission. The four fixed receiver cases have fresh current-source
observations bound by the maintained routing record; general routing
effectiveness remains pending. The [serial reservation contract](decisions/evaluation-accounting.md#serial-native-launch-reservations)
coordinates scheduled launches and audits every reserved attempt. Freeze the
whole development schedule before execution and use its first standard production
row to verify `observe` → cleanup/collection → `finish` → admission. This avoids a
duplicate live smoke; that row counts only in its original frozen schedule.
Missing rows remain in the denominator. Comparisons remain separate work and
backend identity remains unknown.

## Prepare a frozen plan

Keep plans, credentials, selected inputs and attempt journals private. Public
examples below use placeholder absolute paths; substitute reviewed local paths.
There is no plan-generation or automatic runtime-download command.

`run` and `recover` require Python 3.11+, macOS arm64, the main thread and no
preexisting process alarm. The profile is
`codex-0.163-macos-arm64-linux-arm64-v1`: pinned host Codex/code-mode binaries,
a verified Linux arm64 executor archive, an explicit existing Docker Unix socket
and an already available image digest. Review the outer VM and host-share state
separately. An executor container without bind mounts is not proof that its VM
has no host shares.

A version-1 plan requires the fields below, with optional `collection`. A version-2
trial plan additionally requires `routing`; version 1 rejects that field.

| Field | Required content |
| --- | --- |
| `schema_version`, `profile`, `mode` | `1` for the original plan or `2` for a routed trial, the supported profile, and `trial` or `qualification` (version 1 only). |
| `identity` | Frozen `trial_id`, `binding_digest`, `experiment_digest`, `case_id`, `arm`, `variant`, `repetition`, and a fresh `attempt_id`. Digests bind the selected inventory; names do not establish custody. |
| `inputs` | Absolute `root`, bundle-relative `entrypoint` (omitted for natural routing), and explicit `files` records containing `kind` (`case` or `bundle`), relative `path` and `sha256`. |
| `prompt` | The selected bounded task text. Qualification mode uses the controller's fixed challenge workflow. |
| `runtime` | Absolute `codex`, `code_mode_host`, `docker`, `executor_archive` paths, their `hashes`, image digest, `docker_host` and frozen `metadata_digest`. |
| `limits` | Every limit named below, explicitly supplied. |
| `sources` | Exact source filename-to-SHA256 mapping required by `SOURCE_NAMES` in the validator. Missing, extra or changed sources refuse. |
| `state_root` | Existing private, current-owner 0700 directory for new trial/attempt state. |
| `collection` (optional) | Trial-only fixed artifact declaration described below. Qualification mode rejects it. |
| `routing` (required in version 2) | Trial-only catalog and mode from the [authoritative routing contract](decisions/evaluation-accounting.md#declared-catalog-routing-and-client-model-observations). Natural mode omits the plan entrypoint; qualification mode rejects routing. |

Inputs are limited to 64 files, 512 KiB per file and 4 MiB total. Unsafe paths,
symlink traversal, duplicates, changed bytes and an existing attempt are refused.
Qualification mode accepts only the validator's fixed synthetic fixture; arbitrary
trial inputs cannot be relabeled as that qualification. The selected bundle is
staged at readonly `/runtime/arm`; editable case files live at `/work/project`.
The executor does not receive the credential or journal.

For natural routing, setup probes write denial on the lexicographically first
frozen bundle file. This probe leaves the task prompt and declared catalog
unchanged. Explicit-entrypoint plans continue probing their declared file.

The required limits may be reduced but not exceed `setup_seconds=180`,
`wall_seconds=90`, `cleanup_seconds=45`, `soft_total_tokens=131072`,
`soft_output_tokens=4096`, and `retained_bytes=262144` (minimum retained bytes:
65536). Setup, observation and cleanup have distinct bounds. Token guards act on
observed usage after use and can overshoot; they are not hard provider request,
output-token or spending limits. One initial turn does not mean one wire request.

## Declare bounded output collection

For `mode: "trial"`, add an explicit declaration before freezing the plan:

```json
"collection": {
  "schema_version": 1,
  "paths": ["result.txt", "missing.txt"],
  "max_file_bytes": 65536,
  "max_total_bytes": 262144
}
```

The native path accepts 1-8 unique relative paths, at most 160 characters and 16 parts
each. Credential names, `.env` names, traversal and unsafe file types/links refuse
or block capture. Bounds can be reduced. Include `native_trial_results.py` in the
exact `sources` inventory; the current inventory has thirteen files including
`trial_reservation.py`. Historical 11/12-source manifests do not validate it. The standalone collector supports a wider 64-path domain, while native
receipt size/cleanup policy deliberately limits collection to 8.

After owned host shutdown and known native-home purge, the controller re-inspects
the owned executor and runs the frozen collector with isolated Python. It captures
only declared paths under `/work/project`, before removing the executor. Capture
requires at least 25 seconds left in the original cleanup budget, gets at most 5,
and reserves 20 for mandatory cleanup. Short/expired budgets, uncertain shutdown,
unpurged home or changed ownership block collection; they do not reset the clock
or skip cleanup. No new native turn or case-provided code is run by the collector.

`collection` in the receipt binds the manifest, declaration, collector source and
actual owned container to a closed snapshot. Each file is either `present` with
`bytes` and `sha256`, or observed `missing` with null size/hash. Read/race/unsafe/
oversize/transport failures block the entire capture; no partial rows are salvaged.
`selected_task_file_hashes_retained` explicitly distinguishes these declared file
hashes from the supervisor's unretained raw native contents.

Every snapshot keeps `quiescent_state_verified:false`. A captured missing file is
not evidence that capture failed, and a captured present file is not task success.
The interrupted native check actually retained the file written before the stop;
its native task remained blocked. Evaluator admission must require the matching
completed turn, acceptable stop/usage state and owned cleanup as well as a valid
snapshot. `completed_ungraded` still means ungraded. Recovery only reconciles
owned residue and never recaptures outputs.

The [selected collection record](verification/native-outcome-collection.json)
retains its exact current 13-source/runtime binding and three credential-free cases:
present/missing, unsafe symlink and interrupted native task. The fixed task wrote
the artifact through a real native tool call, not coordinator materialization.
An actual turn/start acknowledgment was counted and correlated to its terminal;
no author-supplied success flag replaced it. The private bridge supplies the
observation projection and its own coordinator receipt; it calls production
setup/cleanup/capture, while production `observe`/`finish` collection gates have
unit-test coverage only. The existing native fixture's
`mock_complete`/`blocked` result and the outer private attestation stay distinct.
These three controls made no model calls or authentication reads/copies.
Current-source authenticated boundary/routing qualification is separately complete;
the actual comparative evaluation remains pending.

See the [collection flow](architecture/native-outcome-workflow.html) and
[screenshot walkthrough](manual/native-outcome-collection.pdf) for this sequence.

## Check without launching

```sh
python3 scripts/improvement/native_trial.py check \
  --plan /path/to/private-trial-plan.json
```

`check` reads selected input/source/executable bytes and validates existing state
and hashes. It does not read the authentication source, create an attempt, launch
a process or contact Docker. A `checked` result includes the manifest digest,
`authentication_opened=false` and `processes_launched=false`. It does not check
Docker availability, live authentication, native registry behavior or cleanup.
Freeze and review the exact plan and sources before moving to execution; do not
rewrite digests merely to suppress a drift refusal.

## Run one explicitly authorized attempt

For a plan whose `state_root` is the frozen reservation root, use
[`trial_reservation.py run-next`](decisions/evaluation-accounting.md#serial-native-launch-reservations).
The direct command below is outside that gate: it does not enforce its aggregate
allowance or take its experiment lock. Do not use it to bypass an outstanding
reservation. Existing recovery is for owned cleanup only; it does not retry a
reserved task, refund its allowance or make missing cost complete.

```sh
python3 scripts/improvement/native_trial.py run \
  --plan /path/to/private-trial-plan.json \
  --auth-source /path/to/explicitly-authorized-auth.json
```

The authentication path is a separate required argument, never a plan field.
The owner must authorize that exact source and temporary recipient. The source
must be a current-owner regular, one-link, exact-0600 file of at most 1 MiB.
The controller makes one guarded temporary file copy without parsing or retaining
its contents or hash. It does not obtain new credentials or use Keychain.

The trusted host native client holds that copy outside the isolated executor.
A fresh owned home, selected remote environment, source-bound metadata check and
fixed capability restrictions precede the single model turn. In qualification
mode, a fixed short loader reads readonly `/runtime/qualification.js`; the closed
output and remote challenge predicates must also match. These observations are
not a preventive approval gate or proof of natural model routing.

Read the private receipt and cleanup facts, not just the process exit code:

| Status | Meaning |
| --- | --- |
| `completed_ungraded` | Trial terminal/usage and owned cleanup met the controller checks; semantic task correctness remains ungraded. |
| `qualified_current_profile` | That particular qualification attempt additionally met its fixed current-profile predicates. See the selected evidence for the exercised profile and its source bindings. |
| `blocked` | Failure, stop, missing evidence or cleanup uncertainty; preserve the attempt. |
| `refused` | Categorical validation or operation refusal. Do not retry by replacing the original evidence. |

The controller returns exit 0 for accepted operation statuses, 1 for a blocked
result and 2 for a caught refusal. Receipts retain fixed typed identities, numeric
usage and cleanup facts. Optional collection adds only explicitly declared file
metadata/hashes; raw native prompts/tool contents and general answers are not retained. The recorded retention denominator excludes frozen inputs and temporary
native state. `live_eligible` remains false; provider request/retry counts and
billing usage remain unknown, and backend model identity is not verified.

Routed cleanup records include the finite `group_signal_error_code` category rather than
OS error messages. On macOS an already-exited, unreaped group can return
`permission_denied`. The routed session reconciles that case only after reaping
its owned leader, draining both streams with no buffered records, and observing
that a non-destructive signal-0 probe of the exact original group returns
process-not-found. The receipt retains the original error category and
`group_absent_after_reap=true`; EOF alone or another permission error never
supplies that proof. No destructive signal is sent after leader reap.

The qualification prompt places its tags directly against the exact loader
input, leaving no delimiter-adjacent newline to copy. It explicitly preserves
the exec pragma and excludes a terminal newline. Only the loader asset's final
LF is omitted; its statements and pragma parameters remain unchanged.

Boundary qualification exports finite input diagnostics (`call_id_valid`,
`input_matches_expected`, `input_variant` and boolean `input_shape_*` flags) to
distinguish call identity from known whitespace, line-ending or exec-pragma differences.
These labels never normalize acceptance: the requested script must still match
exactly. Raw inputs, correlation identifiers and their hashes are not retained.

## Process-query failure diagnosis

The cleanup record includes `process_query_diagnostic`: `null` when no query
failed, otherwise the first failure's `phase` (`launch`, `watch`, or `cleanup`),
queried `pid`, and finite `reason`. Reasons distinguish `deadline`, `timeout`,
`output_limit`, `control_stopped`, `exit_status`, `stderr`, `field_count`,
`identity`, `executable_not_absolute`, and unexpected `operation` failure.
No raw process output, executable path, error text or model content is added.
The public refusal remains `process_query`.

A macOS owned-process reproduction confirmed that an exited but unreaped child
can return a nonabsolute executable field; after its parent reaps it, the exact
query reports absence. This is a plausible explanation for the retained pilot
failure, not a proven historical cause: that failed query's output was not saved.
Apple's [process formatting source](https://github.com/apple-oss-distributions/adv_cmds/blob/6bed8737a34dbb54782a18f47dccf933a9967a12/ps/print.c)
also has nonabsolute fallbacks, so this category alone does not establish a zombie.

During macOS cleanup only, an already recorded owner whose executable field
is temporarily nonabsolute may be queried again within the original two-second
query bound and cleanup deadline. That record never authorizes a signal or
counts as absence. A fresh strict query must establish absence or return a
process for the existing ownership check. Persistent ambiguity and every other
query error still fail closed. Launch, watcher and unrecorded-process queries
do not use this settling wait.

Once a query fails, later successful queries do not erase its diagnostic or
clear `process_query_uncertain`. Existing ownership, watcher, auth-purge and
recovery guards remain in force. A real owned-child reproduction fails before
the correction and passes after reaping occurs during the bounded wait. These
checks do not by themselves renew authenticated qualification, repair an original
blocked result, or complete the EN/KO comparison.

## Recover exact owned residue

```sh
python3 scripts/improvement/native_trial.py recover \
  --attempt /path/to/private-state/TRIAL_DIGEST/ATTEMPT_ID
```

Use the original source/runtime bytes and journal. Recovery takes the coordinator
lock, checks recorded identities and reconciles only exact owned residue. It can
invoke bounded process/resource checks and Docker cleanup, but does not copy
authentication, launch native inference, start/stop a VM or repair account state.
An unresolved launch, missing prior shutdown proof, changed ownership or uncertain
process query refuses recovery. There is no caller flag to assert success.

Unconfirmed shutdown retains the temporary credential/home. Do not delete that
state blindly or erase a failed attempt to make a retry appear fresh. Preserve the
receipt, reconcile ownership, and retain unresolved status when safe cleanup
cannot be proved. `reconciled` describes cleanup, not a successful trial.

## Separate credential-free loader fixture

Use [native_execution.py](../scripts/improvement/native_execution.py), not a
`native_trial fixture` command. The older default workflow and its historical
results are documented in the [fixture guide](decisions/native-execution-fixture.md).
The new `command-skills-loader` scenario has its own source and qualification scope.

Its private JSON plan accepts `command` and `executor` argv, `timeout` (at most
180 seconds), `limit` (at most 262144 bytes),
`scenario: "command-skills-loader"`, and `expected_script_bytes` (1–32768).
The latter is the exact ASCII byte length of the frozen script that the separately
owned executor exposes at readonly `/runtime/qualification.js`; length alone is
not source identity. No arbitrary JavaScript, authentication or provider override
is accepted in this CLI plan.

```sh
python3 scripts/improvement/native_execution.py \
  --plan /path/to/private-loader-fixture-plan.json \
  --output /path/to/new-private-fixture-output
```

The external owner must stage and bind the fixed
[boundary cell](../scripts/improvement/native_execution_command_skills.js), plain
skill body/reference fixture at `/runtime/arm`, selected case files and known
synthetic protected sentinels before launch. The
[loader](../scripts/improvement/native_execution_loader.js) reads the fixed path,
requires a completed zero-exit command with no continuing session and exact ASCII
length, then evaluates it. The fixture requires actual closed boundary records,
disabled-collaboration refusal and a matching completed native terminal; prompt
text or a zero wrapper exit cannot substitute.

This path uses a local synthetic Responses provider and no real inference or
authentication. Its two synthetic submissions are not provider retry accounting.
The public runner emits `mock_complete` or `blocked`, never the private bridge
status `coordinator_attested_credential_free_profile` (or historical
`qualified_credential_free_profile`). A `mock_complete` receipt keeps
`live_eligible`, `authentication_qualified` and
`isolation_qualified` false. The caller must separately verify readonly source
custody, external protected files and owned executor/helper cleanup; inner
sentinel checks cover only the fixture's own temporary files. Trusted Python
integration can defer temporary cleanup until the external owner has stopped
helpers; that option is not exposed in the JSON CLI. Pending external cleanup
must not be presented as a fully cleaned successful qualification.

Current-profile actual qualification and later evaluator admission remain separate
work. Neither receipt type activates an account or establishes a baseline/candidate
improvement. Keep historical results bound to their original source and topology.
