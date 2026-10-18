# Frozen native trials: operator guide

The source implements `check`, `run` and guarded `recover` for one pinned native
trial. Historical V9/V10 credential-free and authenticated results apply only to
their recorded sources. The [12-source collection evidence](verification/native-outcome-collection.json)
records current credential-free native collection and the fixed scoped grading
probes. The earlier [grading record](verification/scoped-grading-integrity.json)
retains its own 11-source provenance; changed sources have not renewed authenticated
qualification. Other hosts, natural routing and comparative evaluation
remain unqualified.

The [design contract](decisions/native-trial-execution.md) owns the boundary and
acceptance rules. This guide covers operator inputs and result interpretation.
The [controller](../scripts/improvement/native_trial.py) and
[plan validator](../scripts/improvement/native_trial_plan.py) own the exact schema.
These commands do not install account settings, activate hooks, create a VM,
change Docker context, log in, compare arms, grade general tasks or promote changes.

## Selected evidence and current limits

The [selected evidence record](verification/native-trials.json) owns the sanitized
historical V9/V10 source/profile bindings and results, with previous V7/V8 evidence preserved.
V9's private Python bridge called the
public `native_execution.run_fixture` API and received `mock_complete`. The bridge
combined that result with outer protected-sentinel and cleanup checks; its private
coordinator independently checked owned resources and VM stop. The selected
`coordinator_attested_credential_free_profile` status is this private attestation, **not a
status emitted by the public `native_execution` CLI**. The evidence record names
and hashes the private bridge, coordinator, release and receipt artifacts without
publishing their paths or contents. Those hashes identify retained evidence;
they do not make the private orchestration a reproducible public command.

That selected targeted mock observed all six closed boundary projections,
actual disabled-collaboration refusal and unchanged external synthetic protected
files. Matching-source V10 authenticated Luna/low evidence observed the exact short
loader, six boundary projections, remote-only challenge and owned cleanup. Both
attempts verified protected synthetic files unchanged after process shutdown.
Neither result qualifies later changed source bytes, natural routing, every future
tool route or comparative evaluation. Preserve historical failures and renew
affected checks on drift. The
[screenshot manual](manual/native-trials.pdf), [editable source](manual/native-trials.json)
and [workflow diagram](architecture/native-trial-workflow.html) retain their own
source/capture provenance.

## Scoped grading integrity

The [current scoped evidence](verification/scoped-grading-integrity.json) verifies
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
The first attempt hit the unchanged archive cap and remains blocked. The corrected
bridge removed duplicate synthetic HTTP-body retention while retaining raw native
events within the same combined cap. It is not a new public CLI status.

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
qualification bindings. Current qualification has not been renewed for the
reservation sources, so real admission remains blocked. The reader does
not execute or recover trials; preserve failed attempts and unknown costs.

Matching artifact bytes do not establish natural routing, exposure or general task
correctness. Source-guarded protocol evidence is not an exported selected-model
observation. The [serial reservation contract](decisions/evaluation-accounting.md#serial-native-launch-reservations)
now coordinates scheduled launches and audits every reserved attempt. Explicit
observed-model export and actual comparisons remain separate work. Backend identity remains unknown.

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

A version-1 plan requires these fields; only `collection` is optional:

| Field | Required content |
| --- | --- |
| `schema_version`, `profile`, `mode` | `1`, the supported profile, and `trial` or `qualification`. |
| `identity` | Frozen `trial_id`, `binding_digest`, `experiment_digest`, `case_id`, `arm`, `variant`, `repetition`, and a fresh `attempt_id`. Digests bind the selected inventory; names do not establish custody. |
| `inputs` | Absolute `root`, bundle-relative `entrypoint`, and explicit `files` records containing `kind` (`case` or `bundle`), relative `path` and `sha256`. |
| `prompt` | The selected bounded task text. Qualification mode uses the controller's fixed challenge workflow. |
| `runtime` | Absolute `codex`, `code_mode_host`, `docker`, `executor_archive` paths, their `hashes`, image digest, `docker_host` and frozen `metadata_digest`. |
| `limits` | Every limit named below, explicitly supplied. |
| `sources` | Exact source filename-to-SHA256 mapping required by `SOURCE_NAMES` in the validator. Missing, extra or changed sources refuse. |
| `state_root` | Existing private, current-owner 0700 directory for new trial/attempt state. |
| `collection` (optional) | Trial-only fixed artifact declaration described below. Qualification mode rejects it. |

Inputs are limited to 64 files, 512 KiB per file and 4 MiB total. Unsafe paths,
symlink traversal, duplicates, changed bytes and an existing attempt are refused.
Qualification mode accepts only the validator's fixed synthetic fixture; arbitrary
trial inputs cannot be relabeled as that qualification. The selected bundle is
staged at readonly `/runtime/arm`; editable case files live at `/work/project`.
The executor does not receive the credential or journal.

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
exact `sources` inventory; old 11-source manifests do not validate this 12-source
runner. The standalone collector supports a wider 64-path domain, while native
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
retains exact current 12-source, runtime and three credential-free cases:
present/missing, unsafe symlink and interrupted native task. The fixed task wrote
the artifact through a real native tool call, not coordinator materialization.
An actual turn/start acknowledgment was counted and correlated to its terminal;
no author-supplied success flag replaced it. The private bridge supplies the
observation projection and its own coordinator receipt; it calls production
setup/cleanup/capture, while production `observe`/`finish` collection gates have
unit-test coverage only. The existing native fixture's
`mock_complete`/`blocked` result and the outer private attestation stay distinct.
There were no model calls or authentication reads/copies. Current-source
authenticated renewal, natural routing and comparative admission remain pending.

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
