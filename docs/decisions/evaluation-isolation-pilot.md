# Isolation qualification pilots

Status: macOS Python canaries and Linux native **synthetic** qualification. The
[improvement-loop design](account-improvement-loop.md) owns evaluation requirements.
Neither verifier qualifies live provider transport, comparative evaluation or
promotion. These pilot commands do not enable real model execution. The separate
[frozen native-trial runner](../native-trials.md) has its own selected source-bound
authenticated qualification; its evidence does not broaden these pilots.
No credentials, account settings or real session history are used by these pilots.

## macOS Python canaries

Run on macOS with Python 3.11+ and an existing `/usr/bin/sandbox-exec`:

```sh
mkdir -p .local/isolation
python3.11 scripts/improvement/isolation.py .local/isolation/new-run
python3.11 -m unittest discover -s tests -p 'test_improvement_isolation.py'
```

Choose a new private/ignored evidence directory. The command never reuses one,
installs dependencies, starts a VM, requests a model or falls back to an
unsandboxed process. Unsupported platforms or a canary that never starts are
`blocked`, not evidence that access was denied. Exit zero means only the selected
synthetic canaries passed. Private receipts/profile files contain local paths.

The runner wraps an isolated Python process and its synchronous Python child in
Seatbelt. Its profile defaults to deny and allows read access to the selected
Python runtime, system libraries and assigned fixture, with writes only in the
fresh assigned directory and `/dev/null`. Literal `/` reads are required for this
host's loader; metadata reads cover only exact ancestors needed to resolve runtime
and fixture paths. This permits root directory enumeration and those ancestors'
metadata, not their descendants' contents. The profile does not permit general
home reads, arbitrary shell binaries or host IPC.

Positive checks read a synthetic assigned fixture and write an externally checked
result. Negative checks require actual permission errors for synthetic home/history,
other-arm, evaluator and holdout sentinels, including parent/symlink traversal and
a Python child. These are synthetic files, never existing private files. The receipt
records whether the output-directory sentinel actually lies under the current home;
a run outside the home does not establish that location-specific probe.

Harmless listeners on separate IPv4/IPv6 loopback ports, UDP and a Unix socket
provide negative network probes. Client permission errors and empty server queues
are checked independently. DNS resolver operations, non-loopback routes and native
Read/Bash/MCP/hooks remain unqualified; do not infer them from Python probes.

A parent-side **mock** endpoint accepts one bounded, exact synthetic inference
request. It rejects other destinations, CONNECT, unrecognized body fields, invalid
capabilities and a second accepted request; tests also cover expiry and strict
integer fields. It has no upstream forwarding code, real authentication or provider
schema claim. Seatbelt accepts `localhost:PORT` rather than a numeric loopback IP,
so the allowed port covers both loopback families. Binding the IPv4 mock does not
establish exclusive identity of every service reachable at that port; authenticated
broker endpoint ownership remains a live-transport blocker.

Subprocesses inherit a small explicit environment, closed extra descriptors and no
stdin. Combined captured output is capped at 64 KiB; execution is capped at 30
seconds (10 by default). Cleanup kills the owned process group, closes listeners
and removes temporary sentinels. Detached children that create another process
group and hard CPU/memory limits are not qualified. This runner accepts only its
fixed canary program, so it cannot be used as a general untrusted-code executor.

Receipts bind the runner/probe, actual profile, executable and OS identity by digest.
`run_trial()` rejects changed receipt, frozen profile or environment identities, and
**always returns blocked with zero model requests**: a canary receipt cannot enable
live execution. Digests provide consistency, not signatures, custody or independent
review. Runtime dependency-tree freezing, whole-client native-tool checks, model
broker authentication/budgets and complete descendant cleanup belong to the next
qualification slice. These probes do not establish same-account secrecy. The planned
[same-host held-out protocol](account-improvement-loop.md#same-host-held-out-evaluation)
uses context separation and exposure tracking without an external custodian.

## Evidence and source limits

The macOS arm64 / Darwin 25.6.0 pilot used Python 3.14.7 on 2026-10-18. Initial
strict profiles failed before process startup and were preserved as blocked. A
numeric loopback profile was rejected by Seatbelt; the corrected localhost rule
and minimal loader/ancestor rules allowed the actual canaries to execute. A later
run passed the selected file/child/network/mock checks. No native client or live
provider request was performed.

The installed `sandbox-exec` help established `-p` invocation. The current
[SRT Seatbelt source](https://github.com/anthropics/sandbox-runtime/blob/main/src/sandbox/macos-sandbox-utils.ts)
was inspected as a profile reference on 2026-10-18; no implementation was copied or
dependency installed. The accepted design records the broader primary/community
research. These local canaries validate this narrow profile on this host; they do
not establish universal sandbox safety or community effectiveness.


## Linux native synthetic qualification

Use this verifier before connecting a real model to an isolated executor. It runs
an unmodified, pinned Codex client and its tools inside an existing Docker host.
It does not install clients, pull images, start a VM, authenticate, enable hooks,
or change account settings. It never mounts a home, history, credentials,
evaluator, holdout, other arm, or Docker socket into the container.

Prerequisites: Python 3.12+, an accessible existing Docker context, the official
Codex 0.163.0 linux-arm64 musl package, and the pinned linux/arm64 Python image
already present. Obtain the package from the
[official release](https://github.com/openai/codex/releases/tag/rust-v0.163.0).
The verifier copies the archive into a private open temporary file, verifies that
copy, and extracts from the same object. It checks the extracted binary digest before execution;
it rejects other versions and architectures. The pinned image is
`python@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83`.
Dependency download and VM lifecycle remain explicit operator actions.

Choose an existing staging parent visible at the same path to the Docker daemon.
For a remote context or a VM, use a deliberately configured shared directory; do
not broaden host mounts to make a failed preflight pass. The verifier creates a
fresh owned child and binds only its extracted runtime and fixed probes, readonly.
A remote daemon must be trusted: local Docker inspection cannot prove an adversarial
daemon follows its own reported configuration.

```sh
mkdir -p .local/isolation
python3.12 scripts/improvement/native_isolation.py .local/isolation/native-new-run \
  --context validation \
  --codex-archive /path/to/codex-package-aarch64-unknown-linux-musl.tar.gz \
  --staging-parent /path/to/docker-visible-staging
```

Use a new ignored/private output directory each time. Exit zero means the selected
synthetic workflow passed. A wrong archive, missing image/daemon or incomplete
native execution is blocked or failed, never evidence that access was denied.
Inspect `receipt.json` for the reason; do not retry with broader permissions.

The outer container has network `none`, a readonly root, nonroot uid/gid, all
capabilities dropped, no-new-privileges, and PID/memory/CPU limits. Only bounded
`/work` and `/tmp` tmpfs paths are writable. The verifier inspects the actual Docker
configuration before startup, including exact image ID, `runc`, private IPC/cgroup
namespaces, default private UTS/user namespace mode, no added devices or sysctls,
and swap disabled by a memory-swap limit equal to memory. The probe also requires
observed seccomp filter mode 2, no-new-privileges and zero effective capabilities.
This qualifies those observed fields, not every daemon/kernel security property.
The whole native process and descendants share this
boundary. It uses the official app-server `externalSandbox` contract on
`command/exec` and `turn/start`, avoiding a redundant inner namespace sandbox;
that API field alone does not establish isolation.

The actual workflow initializes Codex, lists skills, reads/writes a fixture through
`command/exec`, starts an ephemeral thread, and consumes a local Responses stream.
The mock requests a native `exec_command` that repeats file/child/network canaries
and exits with 3. Verification requires the observed native failed tool outcome,
a second HTTP request, and a completed turn. These distinct outcomes must not be
collapsed into a success inferred from process exit alone. The requested model is
`synthetic-model`; mock token usage is not real usage or model-quality evidence.

Synthetic sentinels outside the mounts remain unreachable, including symlink and
child-process attempts; root writes return EROFS, and both IPv4/IPv6 TCP preflight
and native-tool UDP egress must return ENETUNREACH (a timeout is not denial proof). Only loopback is visible. The mock owns both loopback address families
on one port; its bound addresses and accepted request count are observed. It has
no upstream implementation and accepts only the synthetic model. The receipt
labels live requests structurally disabled by network-none and the fixed mock;
it does not present a literal zero as measured provider traffic.
Its placement inside the executor is suitable only for this credential-free test.
An authenticated production broker must remain outside that executor and receive
its own qualified transport and budget enforcement.

The receipt distinguishes `native_client_qualified: true` on a passing Linux
synthetic run from `live_transport_qualified: false` and `promotion_eligible: false`.
It includes source/image/binary identities and cleanup status. This new receipt
cannot enable the existing macOS `run_trial()` consumer. Digests are consistency
checks, not signatures or independent custody. Native routing efficacy, live
inference, complete malicious-process escape resistance and promotion remain
outside this qualification.

The parent caps transport output and wall time; the container caps memory, CPUs and
PIDs. Cleanup queries the unique per-run ownership label, checks each exact
container ID, name and label, and only then removes it. Successful removal deletes
the owned staging child. Cleanup failure keeps the primary failure reason, records
a separate cleanup reason, blocks qualification and retains staging. If create
times out or transport output is cut off, a daemon could finish creation after the
bounded cleanup query: the receipt explicitly reports uncertain cleanup and keeps
staging even when that query is empty. Inspect only the receipt's exact ownership
label before later operator cleanup; never remove other runs' containers. Probe
files have explicit container-readable modes even when the operator uses umask 077. Existing images, Docker contexts and VM
state are unchanged by the verifier. Keep receipts and raw native records private.

### Verified scope and sources

The maintained CLI passed on 2026-10-18 using Codex 0.163.0 in linux/arm64 Docker
29.5.2 on an existing macOS-hosted guest. Initialization, native skill discovery,
positive fixture operations, two mock HTTP requests, observed tool exit 3, denied
file/child/IPv4/IPv6 canaries, turn completion and cleanup were checked. A wrong
archive produced blocked status with cleanup complete. This is a Linux container
qualification, not a Windows/WSL or live provider claim.

The [app-server reference](https://learn.chatgpt.com/docs/app-server) documents
`externalSandbox` for an already isolated process. The
[container guidance](https://learn.chatgpt.com/docs/agent-approvals-security)
recognizes an outer Docker boundary when an inner sandbox is unavailable.
The matching native schema and source are pinned to
[Codex 0.163.0](https://github.com/openai/codex/tree/83086188ae0614bd882818ff1aa23f3194962012).
No upstream implementation was copied; the verifier and synthetic protocol fixture
are local adaptations of the documented APIs.

A separate macOS whole-client Seatbelt attempt stopped at managed-preferences
synchronization before HTTP. A [firsthand report from 2026-10-01](https://github.com/openai/codex/issues/50072)
describes the same startup dependency for noninteractive isolated users, with a
different launch context. It is not proof of an identical cause or an adopted fix.
Community evidence for this exact container workflow remains limited; selection is
provisional with respect to community validation and rests on the documented
contract plus the actual scoped checks above.

The review correction was separately rerun with umask 077, exact image/runtime/
namespace/swap checks, observed seccomp mode and TCP errno checks. The original
qualification records remain historical. This PR adds both the macOS Python
canary lane and the Linux native synthetic lane relative to its base.

Boundary flag semantics were checked against Docker's [run reference](https://docs.docker.com/reference/cli/docker/container/run/),
[seccomp guidance](https://docs.docker.com/engine/security/seccomp/) and
[resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
on 2026-10-18. These configuration checks and the local smoke establish this
fixed workflow only, not general container escape resistance.

## Reusable remote-executor fixture

The separate [native executor fixture](native-execution-fixture.md) extracts the
fixed app-server/mock protocol for an already isolated executor. It does not
create or qualify its caller's OS boundary. Its guide owns the receipt, ownership
and cleanup contract; its two-page walkthrough distinguishes local fake-process
checks from one actual source-bound native mock. Neither verifier supplies live
provider authentication or comparison evidence.
