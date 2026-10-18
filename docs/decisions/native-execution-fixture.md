# Credential-free native executor fixture

The runner in [native_execution.py](../../scripts/improvement/native_execution.py)
prepares one fixed synthetic Codex app-server workflow. It is a reusable
qualification fixture, not a live evaluation or authenticated-provider API.
The current runner adds a fixed post-tool response-deadline scenario. Local
fake-process checks exercise it; actual native qualification is reported separately
below. The earlier source-bound Codex 0.163.0 normal mock predates this extension
and covers only its recorded runtime. A separate historical controller probe
completed before injection and remains unqualified; it was not retried.

## Run and ownership

Use an already authorized, separately isolated executor containing
`/work/project/assigned-capability/skills/assigned/SKILL.md` with the body marker
`ASSIGNED_REMOTE_SKILL_BODY` and `references/details.md` containing
`ASSIGNED_REMOTE_SKILL_REFERENCE`. The capability root is a plain skills folder,
without a plugin manifest. Disabled plugins can otherwise filter that root.

Supply a private JSON plan with `command` (absolute app-server executable plus
`app-server --listen stdio://`), `executor` (absolute stdio transport executable
plus its arguments), `timeout` (at most 180 seconds), and `limit` (at most 262144 bytes).
An optional `scenario` selects `completion` (the default) or
`response-deadline-after-tools`; any other value is refused before archive or
process creation. No endpoint, provider, authentication, environment-variable or model overrides
are accepted. Commands are trusted maintainer inputs, not untrusted case content.
The executor program is not launched directly by this script: the native client
uses its explicit `environments.toml` transport. An argv or its hash does not
establish OS isolation. Review mount/network/ownership separately before use.

```sh
python3 scripts/improvement/native_execution.py \
  --plan /path/to/private-fixture-plan.json \
  --output /path/to/new-private-evidence-directory
```

The runner creates an exclusive evidence directory and temporary HOME/project,
uses `include_local=false`, disables agents/plugins/apps/web/goals, checks empty
host hooks and effective MCP servers, and disables discovered bundled host skills.
Only a local synthetic Responses provider is configured. Ambient account keys and
HOME are not inherited. It never reads an existing authentication file, starts a
VM, creates a container, installs a client or changes real account settings.
The trusted host harness is outside the executor OS boundary.

The fixed synthetic provider permits at most two accepted submission positions:
one code-mode cell and one completion. It counts shape-valid complete POST
bodies before JSON parsing, including malformed JSON and rejected excess bodies.
Rejected HTTP shapes and incomplete bodies are provider errors outside that
submission counter, not inferred model attempts. Its counter is
not a counter for first-party inference, authentication recovery or real retries.
The actual returned tool output must contain the assigned skill body/reference
and disabled-collaboration refusal; echoed prompt text cannot satisfy this check.
The matching thread/turn terminal must complete without error. A zero process
exit is insufficient. Unexpected native server requests are refused.

One deadline covers nonblocking app-server writes and reads, including pipe
backpressure. Active HTTP sockets are closed at the absolute deadline, including
stalled headers and dribbling bodies. Listener and watchdog joins share a
one-second cleanup bound; an unconfirmed stop is reported as incomplete.
Independent cleanup signals only the Popen-owned process group before reaping
its leader,
reaps the direct child, closes local provider listeners and removes owned
HOME/project state. Escaped process groups and external executor resources are
explicitly unverified and remain the caller's responsibility. The fixture never
labels process-group termination as proof that every native helper or remote
process is absent. Cleanup failure preserves the primary failure and receipt;
uncertain harness cleanup retains its temporary root for its owner to inspect.
No broad process scan/kill or externally supplied PID is used.

## Deliberate response deadline

Set `"scenario": "response-deadline-after-tools"` in the private plan to exercise
a negative outcome after the assigned tool workflow. The provider first checks
the second request's actual assigned skill body/reference and disabled-collaboration
outputs. It then records `fault_checkpoint` and withholds the final HTTP response
until the **original** absolute workflow deadline. It creates no new timeout or
retry budget. Prompt echoes, missing evidence and setup timeouts cannot arm it.

The receipt includes `scenario`; this negative case also includes
`fault_observation` with `checkpoint_reached`, `response_withheld`, and
`deadline_reached`. Early cancellation leaves the last field false. Read all three
and the primary reason and cleanup, rather than treating any timeout as successful
injection. The expected CLI result is exit 1 with `status: blocked`; the scenario
never becomes `mock_complete` or live eligible. If native setup or another client
timeout wins before the checkpoint, keep the attempt as an unqualified negative
result instead of retrying or reporting deadline coverage.

This exercises a held provider response, not an external interrupt, deliberate
executor disconnection, detached-child cleanup or upstream cancellation. The
reusable receipt still cannot prove external executor/escaped-resource absence.

## Receipt contract for downstream accounting

Each attempt writes `events.jsonl` and `receipt.json` once. Both are private 0600
files inside a 0700 directory. An existing output directory is rejected; failed
attempts are retained rather than overwritten. The receipt contains:

- schema_version 1, kind `native-remote-fixture`, status `mock_complete` or
  `blocked`, failure reason and actual mock submission count;
- declared model/reasoning and source/component/executable/config hashes;
- bounded native terminal identity/status/error summaries with a digest of the
  full archived terminal when observed;
- wall/archive limits and elapsed time; real token usage is unknown;
- owned cleanup outcomes, external/escaped-resource uncertainty, and the raw
  archive digest and byte count.

`live_eligible`, `authentication_qualified` and `isolation_qualified` are always
false, including `mock_complete`. The latter means this fixed mock protocol
finished; it does not mean all emitted tools or OS boundaries were qualified.
A downstream evaluator must not accept this receipt as live evidence. Digests
bind bytes, not authority or provenance. Future consumers need a runner-owned
archive outside executor mounts and independent source/ownership verification;
a caller-provided success flag or rehashed fabricated archive is insufficient.

The archive cap includes retained base64-framed native stdin/stdout/stderr,
mock request/response bodies, launch/config/terminal events and the final receipt.
8192 bytes are reserved for the receipt. Oversized future summaries produce a
minimal blocked fallback receipt with archive identity, rather than losing the
receipt. Executable/source hashes are computed before creating an archive.
Final provider state is checked after listeners close, so a late excess body
cannot retain an earlier success status. HTTP headers, OS pipe buffers, removed
temporary files and caller reports are excluded. A read can observe a bounded
chunk before refusing to retain it; this is a retained-artifact cap, not a hard
provider token/spend or universal wire-output ceiling. No guessed
`model_max_output_tokens`, required API key, dollar ceiling or development
holdout requirement is introduced. Authentication and live limits need their
own later qualification.

## Current fixed-deadline qualification

On 2026-10-18, one source-bound actual Codex 0.163.0 run of this extension
reached the validated post-tool checkpoint, withheld its final response and
observed the original 15-second deadline. The inner receipt remained
`blocked`, reason `Refusal:deadline`, with exactly two synthetic submissions and
all three `fault_observation` fields true. Inner elapsed time was 15.044446
seconds; the separate supervisor took 19.063896 seconds. Owned listener, native
process and temporary HOME cleanup completed. Independent checks verified the
observed native/helper process identities and exact owned containers, volume and
control directory absent. The reusable receipt itself still leaves external and
escaped-resource cleanup unverified; that separate supervisor evidence applies
only to this attempt.

The supervisor retained 195,537 of 262,144 bytes, including its outer JSON plus
the inner archive/receipt. This is distinct from the inner 220,000-byte cap.
The denominator excludes frozen inputs, HTTP headers, bounded process queries,
OS buffers, removed temporary state and later analysis. It is not a wire/token
ceiling. The executor used a readonly owned volume without host bind mounts,
network-none and the declared nonroot/capability/seccomp restrictions.
The dedicated VM's actual mount table was checked before this invocation;
configuration alone is insufficient. In the inspected Colima 0.10.3 source,
`mounts: []` selects the default home share; explicit `--mount none` disables it.
Check generated configuration and actual guest mounts separately before releasing
a fixture, following [the pinned mount implementation](https://github.com/abiosoft/colima/blob/00f6c297e92a82c04a4ab507db0a61435650d7e8/environment/vm/lima/yaml.go).

This is targeted provider-response deadline evidence, not an external interrupt,
executor-disconnect, active-shell cancellation, normal final completion,
authentication, model inference or full-route qualification. The older failed
controller injection below remains `NOT_INJECTED`; this new fixed scenario does
not rewrite it. Twenty-six focused local checks and a separate three-case public
CLI fake-process smoke cover current default/deadline/refusal behavior. The
[deadline walkthrough](../manual/native-deadline.json) and its capture receipt
bind actual current source hashes and sanitized results.

## Evidence and sources

The normal native and old controller results in this section are historical
pre-extension evidence. They are not a fresh qualification of changed runner
bytes. Current extension checks and their limits are recorded in the
[deadline walkthrough](../manual/native-deadline.json).


The design follows the maintained
[app-server lifecycle](https://learn.chatgpt.com/docs/app-server) and pinned
[exec-server implementation](https://github.com/openai/codex/tree/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/exec-server).
The official current docs were checked 2026-10-18; 0.163 behavior is bound to the
pinned source, since current documentation can drift. Native prototype evidence
showed disabled agents must include `[agents] enabled=false` and
`multi_agent_v2=false`, and that plain capability-root discovery works with
plugins disabled. This runner preserves those choices. On 2026-10-18, one renewed actual native
qualification of the corrected runtime completed two synthetic submissions and one code-mode cell with a
matching completed terminal. It verified assigned executor skill list/body/
reference reads, disabled collaboration dispatch, V8/catalog restrictions, empty
host hooks and effective MCP inventory, missing-server refusal, bundled host
skill disable/reload, and host/remote instruction markers. The existing Linux
image and readonly named runtime volume were inspected; synthetic OS preflights
confirmed the expected user, capabilities, no-new-privileges, seccomp, root-write
and network restrictions. This image differs from the historical prototypes.

A separate bounded supervisor observed native/helper parent and process-start
identities, then confirmed its exact owned containers, volume and processes
absent. Its evidence supplements the current inner receipt's external-cleanup
unknowns for this attempt only. The supervisor is a private qualification harness,
not part of the reusable runner's cleanup API. Total elapsed time was 8.621 seconds.
The supervisor retained 198,689 of 262,144 bytes: outer command, identity and
cleanup JSON plus the inner event archive and receipt. This total is distinct
from the inner runner's 220,000-byte limit. The inner event archive contained
164,740 bytes and its receipt 2,230 bytes (166,970 bytes combined). The supervisor
denominator excludes frozen sources, HTTP headers, bounded control-plane
process queries, OS buffers, removed temporary files and later analysis.
No real inference or authentication was used. Deliberate executor
disconnect and other command/patch/image/stdin route probes were not repeated in
this run; their historical results are not a fresh all-route qualification.

A separate controller-deadline probe observed the first response but did not
observe an owned helper before completion and did not inject its planned stop. The native
turn completed; the supervisor correctly retained a partial result with
`expected_native_deadline_not_observed`. Its 198,505 retained bytes and 8.205
seconds are attempt evidence, not deadline qualification. No retry followed.
Independent checks found both attempts' owned resources absent and no process
with the exact helper executable. The earlier pre-correction native result is
preserved separately and is not reused as current-runtime proof.

[The focused manual](../manual/native-execution.json) provides editable steps and
[the rendered walkthrough](../manual/native-execution.pdf) shows sanitized actual
CLI/mock evidence. [Capture provenance](../manual/native-execution-capture.json)
binds the runtime component hashes. Any
runtime change requires renewed relevant checks. Twenty focused local tests
exercise fake-process failures, HTTP deadline stalls/dribbles, bounded terminal
receipts, late submissions, privacy guards, backpressure and cleanup; those
results remain distinct from the actual native mock qualification.

Community validation remains limited and this selection is provisional on that
axis. A [firsthand report opened 2026-10-02](https://github.com/openai/codex/issues/50374)
observed executor selection changing during desktop Remote Control continuation
with CLI 0.157.1 and separate Linux containers. That is a different client path
and version from this fixed 0.163 API fixture; the report has no visible
independent corroboration and does not establish a defect here or community
consensus. Its limitation supports retaining route-specific qualification rather
than extrapolating the mock result to other clients.
