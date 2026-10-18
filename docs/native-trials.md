# Frozen native trials: operator guide

The source implements `check`, `run` and guarded `recover` for one pinned native
trial. **Selected V9/V10 evidence renews credential-free and authenticated qualification
for the recorded corrected sources on 2026-10-18.** Those results apply only to
their recorded source, runtime and environment; other hosts and comparative
evaluation remain unqualified.

The [design contract](decisions/native-trial-execution.md) owns the boundary and
acceptance rules. This guide covers operator inputs and result interpretation.
The [controller](../scripts/improvement/native_trial.py) and
[plan validator](../scripts/improvement/native_trial_plan.py) own the exact schema.
These commands do not install account settings, activate hooks, create a VM,
change Docker context, log in, compare arms, grade general tasks or promote changes.

## Selected evidence and current limits

The [selected evidence record](verification/native-trials.json) owns the sanitized
V9/V10 source/profile bindings and results, with previous V7/V8 evidence preserved.
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

## Next consumer: evaluation

The [implementation handoff](decisions/account-improvement-loop.md#implementation-handoff-and-evidence-boundaries)
tracks bounded task-result collection and trusted evaluator admission separately.
The current receipt does not contain general task answers/artifacts and must not
be treated as a graded completion or relabeled as synthetic comparison evidence.
The development pilot's identity requirement covers observed native-client model
selection and reroute checks; it does not change this runner's explicit unknown
backend identity or qualify natural routing.

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

A version-1 plan accepts exactly these fields:

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
usage and cleanup facts, not raw native prompts, tool contents, answers or their
hashes. The recorded retention denominator excludes frozen inputs and temporary
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
