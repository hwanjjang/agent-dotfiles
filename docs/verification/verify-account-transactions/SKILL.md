---
name: verify-account-transactions
description: Check the account installer's transaction journal, automatic undo, rollback and lock in scripts/account_storage.py with a pinned TLA+ model and a real-code interruption harness. Use before merging a change to those functions, to the receipt-last order or locking in scripts/setup_account.py, or to the documented rollback and recovery behavior.
---

# Verify account transactions

Repository maintenance only; this is not a distributed skill package or an account
installation. Generated with [create-formal-verification-skill](../../../skills/create-formal-verification-skill/SKILL.md);
bring it back in line after unchecked changes with
[maintain-formal-verification-skill](../../../skills/maintain-formal-verification-skill/SKILL.md).
Run every command from the checkout root.

## What it promises

- **P1 Recoverable interruption.** If an install, update or uninstall `--apply`, or a
  `rollback --apply`, stops at any step (killed, or an I/O error, including one during the
  automatic undo), `rollback --apply` for that transaction restores every touched path to
  its pre-transaction content, after any number of interrupted retries. Harm if broken: an
  interrupted install leaves Claude/Codex configuration half-replaced, with the original only
  in a private backup and no supported way back.
- **P2 No clobbering.** Rollback never replaces content the user wrote after the transaction,
  and a refused rollback changes nothing, its journal included. The documented exception
  ([account guide](../../../account/README.md)): while the journal was not `applied`, a
  missing skill directory is the journaled move gap and its original returns. Harm if broken:
  a rollback deletes settings or skills the user changed after installing.

Model invariants: `ChangesAreJournaled` and `NoSpuriousRefusal` (P1), `NoClobber` and
`RefusalChangesNothing` (P2). The harness checks the same four on real files, plus lock refusal.

## Does this change touch covered code?

```sh
python3.11 docs/verification/verify-account-transactions/scripts/run.py --check-sync
```

It is read-only. `out-of-sync` lists covered functions that changed, new functions in
`scripts/account_storage.py` that are neither covered nor excluded, model `@code` references
whose source line moved or changed, and broken assumptions in `scripts/setup_account.py`. It
also lists commits since the sync commit. Any of these means review required, not a bug. Also
read `git diff <sync_commit> -- scripts/account_storage.py scripts/setup_account.py` against
the model; a new writer of journaled paths or a reordered step needs the model even when
`--check-sync` passes.

## Run

Prerequisites: Python 3.11+, Java 11+ (validated with OpenJDK 17) and TLA+ tools v1.7.4,
kept outside Git and checked by sha256. Download only with authority to fetch tools:

```sh
mkdir -p .local/tools/tla2tools-1.7.4
curl -fL -o .local/tools/tla2tools-1.7.4/tla2tools.jar https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
python3.11 docs/verification/verify-account-transactions/scripts/run.py --doctor
python3.11 docs/verification/verify-account-transactions/scripts/run.py .local/verification-runs/fv-001
```

`VERIFY_TLA2TOOLS_JAR` selects another copy with the same hash. Use a new evidence directory
per run; the runner refuses an existing one. A full run takes about 30 s: the base model
with coverage, seven witnesses, five broken variants, the conformance harness on the real
code and on five paired code mutations, and the sync check. For a quick real-code check:
`python3.11 docs/verification/verify-account-transactions/scripts/conformance.py`.

## Read the result

`result.json` records source hashes, tool versions, state counts, coverage, each witness,
variant and mutation outcome, conformance cases and sync status. Raw TLC output stays under
the evidence directory in `tlc/`; it contains local paths, so keep it out of Git.

- **passed:** every check matched `model/expectations.json`. A pass covers the bounds below.
- **failed, base model or conformance:** a property broke. Replay the counterexample step by
  step against the code. A step with no code counterpart, two steps merged that another actor
  could see apart, or an edit while the lock is held means a modeling error: fix the model
  and its `@code` map, never the property. If every step happens in the code, it is a bug:
  report it in the code's words with its harm, and leave product code unchanged unless asked.
  A conformance failure on the real functions is evidence of a bug by itself.
- **failed, variant, mutation or witness:** the check can no longer fail, or a situation is no
  longer reached. Treat it as a verification defect, not a pass.
- **failed, state counts differ:** the model or bounds changed. Update `expectations.json`
  only after reviewing why.
- **blocked:** a prerequisite is missing. It is not a pass.
- **out-of-sync:** see the previous section.

## Update for an intended change

Mirror the code change into the model first, one atomic file-system effect per action, and
refresh the `@code file:line text` comments. Add a broken variant and a paired
`code_mutation` in `expectations.json` for any new guard. Add a harness family when a new
fault point or path kind appears. Rerun until the variants and mutations fail again and the
witnesses are reached, then record the new counts. Change a property only when the change
says the promise changed on purpose, and cite that evidence. Recompute the function hashes
with `run.py`'s `function_hashes` and update the record below. Move `sync_commit` only after
the change is merged and you have confirmed that the verification describes the code at
that commit.

## Coverage record

<!-- coverage-record -->
```json
{
  "sync_commit": "4130e059e4a3d1d08e86cd4a90980edfed4d9c7f",
  "covered": {
    "scripts/account_storage.py": {
      "functions": {
        "observed": "a11a8a526dc31467",
        "encoded": "6eea9bfa6195be88",
        "write": "76a4da193f97af59",
        "_below": "fd67dda2c54f2bde",
        "_shelf": "2afe18eb38e1eaa6",
        "_entry": "989882e7561766c5",
        "_put_below": "011579edc8c271fb",
        "_put_file_below": "a12b205eb4c7d6d9",
        "put": "23457a514b25c39d",
        "_put_file": "baf99592360733cc",
        "desired": "e06c09ec7cbcb8f3",
        "lock": "869859d465eb2851",
        "capture": "46702d4b84cd366b",
        "restore": "ba9e347515ff4543",
        "transact": "733ae413bb1e491e",
        "rollback_plan": "bc7f783db369e6fc",
        "rollback": "163b5c38b3567c1c"
      },
      "excluded": [
        "_caseless",
        "_through_real_directories",
        "digest",
        "instruction_path_allowed",
        "instruction_storage",
        "linked_instruction_files",
        "managed_target",
        "read",
        "require",
        "safe"
      ]
    }
  },
  "assumptions": [
    "scripts/setup_account.py: prepare emits the receipt as its last change",
    "scripts/setup_account.py: rollback and the applying run() execute only inside `with lock(home)`"
  ],
  "tool": {
    "tla2tools": "1.7.4",
    "sha256": "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
  }
}
```

Model paths, in `setup_account.prepare` order: `.agents/skills/tdd` (an unowned directory
replaced by a link), `.claude/settings.json` (a file) and the receipt. The undo in `transact`
walks them in reverse order. `rollback` walks the journal, stored with sorted keys, in
reverse: settings, skill, receipt. The harness uses the same three paths.

## Bounds and limits

Verified in the model: one transaction, up to two kills, two I/O errors and one later user
edit or deletion between commands, with any number of rollback retries. The harness drives
the real functions in synthetic homes at every replace, unlink, symlink, temp-file creation
and copy step they make, with simulated kills, injected errors, twelve real process exits and
a lock held by a second process.

Not covered: power loss or an OS crash (`write` does not fsync the parent directory); edits
by other programs while a command holds the lock (documented: close clients during apply);
several transactions and their rollback order; previews and conflict approval beyond the
receipt-last order; path safety (`safe`, `managed_target`, instruction links); bundle trees
larger than one link; cross-device renames; Hermes paths; Linux and WSL (only macOS was run);
and CI, which does not run this check. After an uncaught interruption, finding the
transaction ID means listing `.agents/agent-dotfiles/state/transactions/`.

## Evidence and cleanup

The runner works on copies inside the evidence directory and checks that the tracked sources
did not change. Harness homes are temporary directories removed after each case. Nothing
else needs cleanup. Publish only a sanitized summary.
