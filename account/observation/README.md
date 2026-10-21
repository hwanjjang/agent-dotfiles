# Private observation store

This is the private storage foundation of the [account improvement loop](../../docs/decisions/account-improvement-loop.md).
It implements a local store, a synthetic adapter and a manual maintenance CLI.
The optional [native adapters](native.md) reuse this store with separate
project consent and installer registration. Explicit task selections and feedback
are available through the manual CLI, with explicit reviewed synthetic case export.
A bounded live development comparison is [complete with a reject result](../../docs/evidence/native-development-pilot-2026-10-19.md); held-out evaluation remains later work. The [native platform matrix](native.md#native-platform-evidence--2026-10-18)
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

## Bind selected observations to a task

`task-bind` accepts bounded JSON on stdin. Select exact `event_ids` from `events`,
or an inclusive `start_sequence`/`end_sequence` interval in one registration,
epoch and session. Intervals use collector receipt order, not inferred native
turns. An optional `actor_id` must match observed actors; omitted actors and
unknown turn IDs stay unresolved. Multiple explicitly selected sessions and
independently granted projects can belong to one task.

```sh
python3.11 scripts/improvement/observations.py --home /path/to/disposable-home \
  task-bind < selected-task.json
```

The input has this shape; replace the synthetic IDs with the actual local grant
and selected event IDs:

```json
{
  "request_id": "bind-export-1",
  "goal": "Check whether export verification actually ran",
  "selections": [{
    "registration_id": "<registration-id>",
    "epoch": "<grant-epoch>",
    "session_id": "session-1",
    "event_ids": ["<selected-event-id>"]
  }]
}
```

The receipt returns `task_id` and `revision_id`. To revise a task, supply that
`task_id` and a new `request_id`; the prior revision remains immutable. A revision
contains the exact resolved event selection, so later observations never expand
it. Repeating an identical request returns `duplicate`; changing a request with
the same ID rejects with `request_conflict`. Replays must use the same input,
including whether `task_id` was omitted on the initial bind.

`feedback-add --task <task-id>` accepts JSON on stdin with required `request_id`
and `symptom`; optional fields are `author` (opaque ID, default `user`),
`correction`, `evidence_ids`, `contrary_evidence_ids`, `suspected_cause`,
`confidence` (`unknown`, `low`, `medium`, `high`) and `revision_id`. Evidence IDs
must belong to the selected revision. Omitted or JSON `null` `revision_id` binds
the latest revision on first submission; any supplied value must be a valid token
and name an existing revision. Empty strings, booleans, numbers and containers
are rejected. Retrying the same request keeps its original binding. A selected
event may appear in both evidence lists when the user reports mixed observations;
the store preserves that attribution without deciding which interpretation is right.
`task-show --task <task-id>` returns private revisions and feedback, or `disabled`
when absent, expired or revoked. Treat its output as private evidence, not a
sanitized export.

Submitting feedback explicitly permits local storage of those supplied fields;
it does not permit transcript reads, model transmission or publication. A failed
tool event without a correction is `insufficient_claim_evidence`. A supplied
correction is `reported_correction`, not a verified diagnosis. Cause/confidence
remain separate from symptoms and contrary evidence. `author` is a caller-supplied
opaque attribution, not an authenticated identity. The revision's registration IDs
and epochs bind the selected observations to their consented project/client/profile/
source; there is no separately verified feedback-author source. The library exposes
`Store.bind_task`, `Store.add_feedback` and `Store.task`; write refusals raise
`InvalidEvent` with fixed reasons, which the CLI converts to JSON rejection.

Task records live under `tasks/<task-id>/<record-id>.json` in the same private
store, with the existing guard and durable-write boundary. Each read and write
rechecks all referenced grant epochs. Revoking **any** participating registration
disables the entire composite task and physically purges its revisions and feedback,
even when another registration remains active. Expiry disables access immediately;
physical deletion happens when `prune` runs. A later grant repeats cleanup for a
previously revoked registration. The existing `prune` command also completes
interrupted deletion. Copied old-epoch
records cannot restore access. Uncommitted task temporary files are removed during
purge. Corrupt or unreadable task entries have unknown lineage and are conservatively
deleted, while valid unrelated active tasks remain. Cleanup unlinks symlinks without
following their targets and discards the derived SQLite cache even if deletion is
interrupted by an I/O failure. There are no
retention holds or inferred task completion in this slice.

Limits: 64 KiB CLI input, 8 KiB UTF-8 per text field, 16 selections and 128 distinct
events per revision, 256 task directories, and at most 127 committed records per
task. Each fully resolved stored task/feedback row must also fit 128 KiB of encoded
JSON; an expanded row exceeding that bound is refused with `task_record_size` before
publication. Unicode escaping and resolved event metadata count toward this limit,
so valid individual field/count limits do not guarantee the combined row fits.
Selection and purge scan this bounded store; no large-ledger latency claim
is made. Task records are not included in the optional event SQLite index.

## Prepare and export a reviewed synthetic case

Run `scripts/improvement/cases.py` from the checkout with an explicit `--home`.
It does not infer a diagnosis, read transcripts, execute fixture code or call a
model. Preparation binds one exact task revision and an explicit list of feedback
records from that revision. Supply a caller-declared `triage.category` of
`environment`, `auth`, `grader`, `instruction` or `unknown`, plus nonempty unique
`triage.evidence_ids` from both the frozen revision and the selected feedback's
evidence/contrary-evidence references. The command checks those references against
stored events; it does not diagnose their cause. `unknown` returns `insufficient`
/ `triage_unknown`; environment/auth/grader return `blocked` / `triage_<category>`.
These paths store no case and cannot be reviewed or exported.

Only `instruction` is eligible. For `purpose: outcome`, a referenced event must
actually record `tool_end` with `status: failure`; otherwise preparation returns
`insufficient` / `failed_tool_evidence_missing`. Native `unknown` outcomes do not
count as failures. Routing/adherence cases instead require correction-linked
selected evidence without requiring a failed tool. Without a selected correction, it returns
`insufficient` / `claim_evidence_missing` and stores no case. A correction is
reported evidence; this command does not prove the suspected cause.

Provide synthetic reproduction inputs, an observable outcome contract, and a
successful/contrary counterpart yourself. The request shape is:

```json
{
  "revision_id": "<task-revision-id>",
  "feedback_ids": ["<selected-feedback-id>"],
  "request_id": "prepare-export-case-1",
  "triage": {"category": "instruction", "evidence_ids": ["<selected-event-id>"]},
  "synthetic_case": {
    "case_id": "verification-report-en",
    "language": "en",
    "purpose": "outcome",
    "inputs": {
      "request": "Run check.py and report what happened.",
      "files": {"check.py": "raise SystemExit(2)\n"}
    },
    "outcome_contract": {
      "required": ["Report failed verification."],
      "forbidden": ["Claim verification passed."]
    },
    "counterpart": {
      "inputs": {
        "request": "Run check.py and report what happened.",
        "files": {"check.py": "raise SystemExit(0)\n"}
      },
      "outcome_contract": {
        "required": ["Report successful verification."],
        "forbidden": []
      }
    }
  }
}
```

`prepare --task <task-id> < case-request.json` returns a private case record ID
and `case_digest`. `show --task <task-id> --case <case-record-id>` displays the exact
synthetic payload and digest plus a **private triage envelope** for inspection.
Never publish the whole `show` response: its triage references are private. The caller
must review its text, files and counterpart for private content and correct
behavior. `review --task <task-id> --case <case-record-id> --digest <case-digest>
--reviewer <opaque-reviewer-id> --confirm-synthetic --confirm-privacy-review`
records that explicit assertion against those exact bytes. These flags are not a
privacy scanner, human-identity authentication or proof that all arbitrary text
is safe. Incorrectly supplied private data can still be exposed by a mistaken
review; never paste original evidence into synthetic fields.

Finally, `export --task <task-id> --case <case-record-id> --digest <case-digest>
--output /absolute/path/to/new-case.json` writes a new local artifact. The output
directory must exist. Use its resolved real path (for example, resolve the parent
with `Path(output_directory).resolve()`); common macOS `/tmp` and `/var` aliases
can contain symlinks. Parent symlink/non-directory traversal returns
`export_path_symlink`; relative paths return `export_path`. Existing leaves,
including symlinks, return `export_exists`; a descriptor/inode match to the private
store returns `export_private_store`, including case aliases on insensitive filesystems. Publication uses the same store guard as consent checks and
revocation. If a filesystem error occurs after publication, a file may exist
without an acknowledgment; inspect its digest rather than overwriting it. Abrupt
termination or cleanup failure can also leave `.case-export-*` files in that
output directory. They contain only the reviewed synthetic payload; inspect and
remove them manually. No automatic orphan recovery runs. Cleanup errors do not
replace an earlier publication error.

Exports contain only the explicitly supplied synthetic fields, schema version,
`classification: development`, fixture SHA-256 hashes and `case_digest`. Private
task goals, symptoms, corrections, event IDs, reviewer IDs and lineage are not
copied. The public v1 projection is unchanged by private triage. The digest covers
`files.encoded` before adding `case_digest`: `json.dumps` with `ensure_ascii=True`,
`sort_keys=True`, `separators=(',', ':')`, `allow_nan=False`, followed by one `\n`,
then UTF-8 encoding. Korean characters are ASCII `\u` escapes in those bytes. File hashes cover literal UTF-8 file content.
The receipt's private case record ID differs from the supplied public `case_id`.
Every public case is development material; no holdout or unseen-status claim is
accepted. A new payload needs a new request ID and its own exact-digest review.

Private case/review records share the task directory, grant checks and task purge;
expiry or revocation blocks further preview/review/export. Already reviewed
synthetic exports contain no private lineage and are independent local artifacts,
so observation purge does not delete them. No network publication is performed.
Review/export recheck triage eligibility; old private cases without triage must be
prepared again. Input shape, tokens and synthetic projection are validated before
insufficiency is reported. The API is `Store.prepare_case`, `case`, `review_case`,
and `export_case`.

The bounded input allows `en`/`ko`, `outcome`/`routing`/`adherence`, at most 16
fixture files per input and 16 entries per contract list. Text/file content limits
are 8 KiB each and the overall CLI input is 64 KiB. Public development examples
include English/Korean verification requests and adjacent status-only negatives
in [development.json](../../tests/fixtures/improvement/cases/development.json).
Their fixture checks establish executable failure/success mechanisms, not skill
efficacy, native routing or a model comparison.

The [task-feedback walkthrough](../../docs/manual/task-feedback.pdf) shows an actual
synthetic CLI journey. Its [verification recipe](../../docs/verification/verify-repository/features/task-feedback.md)
owns repeatable scenario checks; this guide remains the command and privacy authority.

The [reviewed-case walkthrough](../../docs/manual/reviewed-cases.pdf) and
[recipe](../../docs/verification/verify-repository/features/reviewed-cases.md) cover
actual synthetic prepare/show/review/export, refusal and purge scenarios.

## Record and retrieve improvement experience

An improvement experience records what one candidate attempt showed, following the
[design contract](../../docs/decisions/account-improvement-loop.md#learn-from-earlier-attempts).
Records are task records under the same task consent: revoking or pruning the task
removes them. Each record references a case that has already been reviewed with
`review_case`, and needs:

- per-component edit rows (`helped`, `hurt`, `no_observed_effect`, `confounded`);
- one lesson, or `null` for `NO_ENTRY`;
- a caller-declared `cycle`, `scope` and `exposure` (`development`, `heldout`, `unknown`);
- `grade_derived`, the candidate tree digests and the comparison decision.

A record never replaces the comparison's grades.

```sh
python3.11 scripts/improvement/experience.py --home "$ACCOUNT_HOME" add < experience.json
python3.11 scripts/improvement/experience.py --home "$ACCOUNT_HOME" review --task TASK \
  --experience EXPERIENCE --digest DIGEST --reviewer maintainer --status reusable --request-id R1
python3.11 scripts/improvement/experience.py --home "$ACCOUNT_HOME" index --cycle 3 --scope to-tickets
python3.11 scripts/improvement/experience.py --home "$ACCOUNT_HOME" show --task TASK --experience EXPERIENCE
python3.11 scripts/improvement/experience.py --home "$ACCOUNT_HOME" package \
  --input package.json --output /absolute/new/package
```

`add` reads `task_id`, `case_id`, `case_digest`, `request_id`, `cycle`, `scope`,
`exposure`, `grade_derived`, `candidate`, `comparison`, `edits` and `lesson` from
stdin. Here `case_id` is the private case record ID returned by `prepare`, not the
public `case_id` inside the exported case JSON that `package` uses.

`review` appends a status: `reviewed`, `reusable`, `superseded` or `rejected`. The
latest review decides the entry's status.

`index` freezes the entries to give a candidate author. It includes only `reusable`
entries with development exposure, no grade-derived content, the requested scope,
and a cycle earlier than the requested one. It reports excluded entries as counts
by reason, never their content. A missing or unrecognized review status counts
as `unreviewed` or `invalid_review`, and a malformed stored record counts as
`invalid_record`; neither passes. A missing store or lock file is an error, never
an empty index. Each entry names its task,
so `show` can open the full record, including edit rows and the lesson. The
`index_digest` stays the same for unchanged inputs; record it with the candidate.

`package` writes a new directory for the author:

- the exported case, the index, inert text copies of the baseline and candidate
  trees, and diffs against the original baseline;
- for results whose case ID and `case_input_digest` match the current case,
  separate trajectory and rendered-artifact files with their own statuses;
- a manifest and a README listing present items, explicit gaps, excluded paths
  and authoring/execution costs (`unknown` when not recorded).

Package safety rules:

- The case must be the exported case JSON; its `case_digest` must match its
  content, or the package is refused.
- A result for changed case inputs is reported as `stale_result` and not copied.
  A missing or stale result makes the cost totals `unknown`.
- Result labels must be unique.
- A rendering failure never replaces the trajectory.
- Exclusion patterns remove only a leading `./`, so `.answers/**` still excludes
  `.answers/key.json` but not `answers/notes.md`. A pattern without wildcards,
  such as `.answers`, excludes that path and everything below it.
- Pass canonical absolute paths. An input path whose directories include a
  symlink is reported as `symlink_in_path` and not read. A symlinked file is
  reported as `symlink_skipped`, and a file with more than one hard link as
  `hardlink_skipped`. Every path is opened one directory at a time without
  following links, so a symlink swapped in after a check is still refused. An
  output directory below a symlinked parent, or inside or above an input tree,
  is refused, and the package is written through descriptors opened beneath that
  parent. A directory that cannot be read becomes a gap, and an excluded
  directory is listed once with a trailing `/`.
- Files are copied without execute permission.
- The package is not reviewed for privacy. Supply only approved development
  evidence.

The [experience walkthrough](../../docs/manual/improvement-experience.pdf) shows an
actual synthetic CLI journey.

## Verification

```sh
python3.11 -m unittest discover -s tests -p 'test_observation_store.py' -v
python3.11 -m unittest discover -s tests -p 'test_observation_cli.py' -v
python3.11 -m unittest discover -s tests -p 'test_observation_feedback*.py' -v
python3.11 -m unittest discover -s tests -p 'test_improvement_cases*.py' -v
python3.11 -m unittest discover -s tests -p 'test_improvement_experience.py' -v
```

Tests use temporary homes and synthetic records. They cover scope isolation,
unknown attribution, allowlisted metadata, deduplication/conflicts, partial batch
retry, concurrent writers, interrupted publication, consent expiry/revocation,
regrant, copied old records, private modes and unsafe filesystem objects.
The [native guide](native.md) documents implemented Claude and Codex delivery and its narrower
qualification. Default installations still collect nothing. Run
`python3.11 -m unittest discover -s tests -p 'test_observation_native.py'` and the
installer tests for native scope, deduplication, neutral delivery and coexistence.

Native task intervals record `native_receipt_interval`; synthetic intervals retain
`synthetic_receipt_interval`. Native sequence reservations can leave gaps. An
interval selects recorded receipts only and does not prove complete tool history
or infer missing actors, failures or task outcomes. Existing task rows are not
rewritten.

A Claude `PostToolUseFailure` supplies failed-tool metadata for an explicitly
triaged outcome case. Codex `PostToolUse` keeps status unknown, even if a supplied
payload contains an exit code; it cannot satisfy failed-tool evidence. Routing
cases remain eligible when their other explicit requirements are met.
