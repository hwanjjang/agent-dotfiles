# Private observation store

This is the private storage foundation of the [account improvement loop](../../docs/decisions/account-improvement-loop.md).
It implements a local store, a synthetic adapter and a manual maintenance CLI.
The optional [native adapters](native.md) reuse this store with separate
project consent and installer registration. Task feedback and comparative evaluation
remain later work. The [native platform matrix](native.md#native-platform-evidence--2026-10-18)
owns source-bound results and remaining environment, subagent and delivery gaps.
The store never inspects transcripts,
runs models, changes skills, registers hooks or writes installer state.

Use Python 3.11+ on a local POSIX filesystem, matching the [account installer](../README.md).
There are no additional packages. Run the CLI from this maintenance checkout;
`source_snapshot` includes `account/` in a committed bundle but excludes `scripts/`.
Delivering these library files alone does not activate collection.

## Location and ownership

An explicit `--home` selects the account root. No command defaults to the current
account. The store lives at:

```text
<selected-home>/.agents/agent-dotfiles/observations/
├── store.lock                 # Bounded exclusive operation guard
├── grants/<registration>.json # Exact scope, epoch, expiry or minimal tombstone
├── records/<registration>/    # Immutable events or atomic batch/cursor records
└── index.sqlite               # Optional rebuildable event cache
```

The directory is separate from the installer's `bundle/` and `state/`. New store
directories are 0700 and files 0600; existing owned objects with unsafe permissions
are rejected. Descriptor-relative operations reject symlink traversal and special
files. The selected home itself is canonicalized once as the caller's trust root.
The store is not a security boundary against another process controlling the same
user account, changing grants or replacing the whole home. Never add it to Git.

A registration binds one canonical project directory, a selected client, a
profile and an exact source generation. Session and native event IDs are scoped
to that registration and epoch. Subprojects are not implicitly opted in. Different
profiles and sources have separate registrations; revoke each registration to
forget a project completely. The implementation uses one exclusive store guard,
with a one-second wait limit, to serialize capture, import, purge and index rebuild.
Finer-grained concurrency and large-ledger latency qualification are deferred.

## Try the complete flow without touching your account

From the repository root, this creates and cleans up a disposable home and project:

```sh
python3.11 - <<'PY'
import json
from pathlib import Path
import tempfile
from account.observation.store import Store

with tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary).resolve()
    home, project = base / 'home', base / 'project'
    home.mkdir()
    project.mkdir()
    store = Store(home)
    grant = store.grant(project, start_after=0)
    payload = json.dumps({
        'schema_version': 1, 'project_root': str(project),
        'client': 'synthetic', 'profile': 'default', 'source': 'fixture-v1',
        'session_id': 'session-1', 'sequence': 1,
        'source_event_id': 'event-1', 'event_kind': 'tool_end',
        'actor_id': 'parent', 'tool_category': 'shell', 'status': 'failure',
        'output': 'This synthetic output must not be retained.'
    }).encode()
    args = grant['registration_id'], grant['epoch']
    print(store.capture(*args, payload)['status'])  # recorded
    print(store.capture(*args, payload)['status'])  # duplicate
    print(store.rebuild_index())                   # 1
    print(store.revoke(grant['registration_id'])['status'])  # revoked
    print(store.capture(*args, payload)['status'])  # disabled
PY
```

The manual CLI exposes the same operations:

```sh
python3.11 scripts/improvement/observations.py --help
python3.11 scripts/improvement/observations.py --home /path/to/disposable-home \
  grant --project /path/to/synthetic-project --start-after 0
```

`grant` returns `registration_id` and `epoch`. Use them with `capture` or `import`;
these commands consume bounded synthetic JSON or JSONL from stdin. `import`
also requires `--offset` (a byte offset). `events --registration ID` reads accepted
observations; `rebuild-index` creates a cache; `revoke --registration ID` disables
and purges that registration; `prune` removes expired or interrupted-purge data.
Use `--help` on each subcommand for arguments. Input/output is JSON, and diagnostics
contain fixed codes rather than payloads or raw filesystem exceptions. Capture
statuses are `recorded`, `duplicate`, `disabled`, `rejected`, `busy` or `error`;
partial-only imports return `incomplete`. Only `recorded` and `duplicate`
acknowledge durable events. This manual CLI is not a neutral native hook response
adapter. A rejected/error/busy operation exits nonzero. After argument and Python
version validation, operation results (including failures) are JSON on stdout.
Refusal codes include `already_granted`, `source_high_water`,
`source_generation_required` and `registration_id`. `not_found` means a selected
home/project path or registration is missing; check those inputs. Lock contention
returns `busy` with `store_busy`; unexpected storage failures return `error` with
`operation_failed`, without raw exceptions. Run `prune` before re-granting an
expired registration that is still marked active.

## Synthetic input contract

Required fields are `schema_version: 1`, exact `project_root`, `client: synthetic`,
`profile`, `source`, `session_id`, integer `sequence` greater than the grant's
`start_after`, and `event_kind` (`session_start`, `tool_start`, `tool_end` or
`response_end`). The project path must match its canonical registration root.
Optional IDs are `source_event_id`, `actor_id`, `parent_actor_id`, `turn_id` and
`tool_call_id`. IDs use at most 160 ASCII letters, digits, `_ . : @ -`.
Optional metadata is `tool_category` (`shell`, `file`, `mcp`, `other`), `status`
(`success`, `failure`, `pending`, `unknown`) and bounded Unix `occurred_at`.

Other fields are discarded before persistence. Prompts, arguments, output,
assistant text and transcript paths are never retained or dereferenced. Allowed
identity fields must contain opaque identifiers, not user content. The project
path stays in the private grant; events use its digest. Missing actor, timing,
status and manifest information remain explicit gaps. `response_end` never
implies task success; no effective skill exposure or environment revision is
inferred by this synthetic adapter.

A stable source event ID deduplicates within registration/epoch/session. Reusing
it with different normalized content rejects the event. Without a stable ID,
separate callbacks receive separate local IDs and a `possible_duplicate` gap.
Identical text is not event identity. A capture is limited to 16 KiB; an import
to 64 KiB and 128 complete records. Synthetic registrations retain their earlier 4,096-entry read bound and
4,095-record write ceiling, including batch records. Their capture/import path
still scans the ledger and is not covered by the native benchmark. Native
registrations have a separate 16,383-record write ceiling. Native capture uses durable sequence reservations
and direct replay lookup; see [capacity and attribution](capacity.md) for the
10,000-callback qualification and its measured p95 latency (48.16 ms on one
reference run). The ceiling is a resource bound, not a claim that every workload up to it has been qualified.

Imports accept bytes explicitly supplied by the caller; they do not open files
or discover native history. Offsets start at zero for the selected source
**generation**. The caller retains any incomplete trailing line and resumes at
`next_offset`. Complete events and their next cursor share one immutable record.
An unknown schema, malformed record or conflicting ID rejects the entire input
batch without moving the cursor. Replaying the same committed batch is idempotent,
including events without stable IDs. Use a new source generation for rotation or
truncation; arbitrary historical native-file import is not implemented.

## Durability, revocation and retention

An acknowledgment follows temporary write, file sync, atomic replacement and
directory sync. Retries also sync directory entries left by interrupted attempts.
Readers ignore pending files. Fault-injection tests exercise failures before and
after publication, but do not prove hardware/power-loss durability or network
filesystem behavior. The SQLite cache can be deleted and rebuilt; use `events`
for consent-aware reads rather than querying a possibly stale cache directly.

`revoke` first commits an inactive tombstone under the operation guard, then
removes its records, pending files and the derived cache. If deletion is
interrupted, capture/read remain disabled; repeat `revoke` or run `prune` to
finish deletion. The tombstone retains only a registration digest and source
high-water bound, not the project mapping. Copied old-epoch records do not become
visible after regrant. If corruption prevents determining the high-water bound,
revocation still succeeds and the old source cannot be regranted: select a new
source generation. Source identity is caller-owned; a dishonest caller relabeling
history is outside this synthetic adapter's guarantees.

A synthetic regrant creates a new epoch and requires an explicitly declared current
`start_after` at least as high as the retained bound. Queued old-epoch callbacks
remain disabled. Grants expire after at most 30 days; expiry immediately prevents
capture and API reads. Run `prune` for physical cleanup. No background retention
service or scheduler is installed, and no excerpt retention is supported. The
entire registration expires together; rolling retention and experiment holds
remain future work. Native originals, backups and forensic erasure are outside
this store's ownership.

## Verification and next slice

```sh
python3.11 -m unittest discover -s tests -p 'test_observation_store.py' -v
python3.11 -m unittest discover -s tests -p 'test_observation_cli.py' -v
```

Tests use temporary homes and synthetic records. They cover scope isolation,
unknown attribution, allowlisted metadata, deduplication/conflicts, partial batch
retry, concurrent writers, interrupted publication, consent expiry/revocation,
regrant, copied old records, private modes and unsafe filesystem objects.
The [native guide](native.md) documents implemented Claude and Codex delivery and its narrower
qualification. Default installations still collect nothing. Run
`python3.11 -m unittest discover -s tests -p 'test_observation_native.py'` and the
installer tests for native scope, deduplication, neutral delivery and coexistence.
