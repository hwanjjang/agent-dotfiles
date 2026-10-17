# Slice 1 independent review

Reviewer: delegated store_review agent, using code-review-and-quality. Scope: local source `account/observation/files.py`, `account/observation/store.py`, and `tests/test_observation_store.py`; CLI, documentation, native hooks and account deployment are excluded. Baseline HEAD: `ed1da039fdac3da7639f6d9d361f564ad2dffb92`; reviewed work is an uncommitted, concurrently updated candidate. Requirements: slice-1-contract.md and the account improvement loop proposal.

## Findings and resolution

1. Required — `normalize` called `math.isfinite` before bounding an integer timestamp. A valid JSON integer `10**1000`, well below payload limit, raised uncaught OverflowError. Independently reproduced in a disposable home. Parent changed the order to range-check before floating conversion. Covered by the final passing test run.
2. Required — Directory creation retried after a failed parent fsync skipped the missing durability step when mkdir returned FileExistsError. Parent changed create paths to fsync parent after both creation and existing-entry cases. Independently checked a persistent observation-root fsync failure: capture and retry both return error after correction.
3. Required — `import_batch(..., offset=None, payload=single_json)` takes the internal single-event sentinel path and returns recorded, violating the integer import-offset contract. Independently reproduced and reported; fixed by integer validation before dispatch; covered by the final passing test run.
4. Known issue already under correction at assignment — Duplicate event and batch replay acknowledgment did not resync the record directory after a previous post-rename directory fsync failure. Both branches now sync. Fault tests now target post-publication failure; the final run passes.
5. Parent-identified hardening — Revocation should remain effective when ledger inspection fails. Implemented inactive tombstone with high_water_known=false after ledger errors; same-source regrant refuses source_generation_required. Minimal record envelopes are validated before stale-epoch filtering. Independently verified malformed array, null and empty-object ledgers all revoke, purge and block source reuse.

## Inspected properties

- Active grant and epoch checked before payload JSON decode; opted-out paths do not create state.
- Stable IDs include registration (project/client/profile/source), epoch and session; conflicting normalized content rejects, missing IDs retain explicit duplication uncertainty.
- Allowlist drops prompt, argument, output and transcript content, and unknown identity/outcome/manifest evidence stays unknown.
- Atomic batch contains normalized events and next offset. SQLite remains rebuildable, not consent or cursor authority.
- Exclusive POSIX flock serializes capture, import, revocation and index operations. Descriptor-relative nofollow operations, private modes and hard-link checks protect owned files.
- Inactive tombstones and epoch filtering prevent copied old records becoming current evidence; interrupted purge is recoverable.
- No external dependencies, model/network calls or live account writes in reviewed modules.

## Verification limits

Used only temporary synthetic homes/projects. No hardware power-loss proof, throughput qualification, native adapter behavior or adversarial same-user rewriting of consent controls was tested. Concurrent implementation means the final candidate hashes and last test run must be recorded below before a verdict.

## Final evidence and verdict

Independent command: `python3.11 -m unittest discover -s tests -p test_observation_store.py -v`; 34 tests passed in 1.255 seconds on 2026-10-17. Additional independent disposable probes cover persistent observation-root directory-fsync failure and malformed ledger JSON shapes (`[]`, `null`, `{}`).

Reviewed candidate SHA-256 identities:

- `account/observation/files.py`: `85e67e1d7048036b368d4055177e0adf290679e942626b07e959fa0b027324d4`
- `account/observation/store.py`: `1dd197a26a12a9e16ad2a4cd14b42d025b7b6eff9d52205e765e5e5f5eb364fd`
- `tests/test_observation_store.py`: `fc1201a21af54f027ff2df199a43859f1356db734468620f189db84ea1aa3d0c`

**Verdict: approve within assigned local synthetic-store scope.** No unresolved blocking findings remain in the identified source candidate. The test worker may add further malformed-envelope regression cases after this snapshot; the integrator owns final complete-suite execution and CLI/documentation qualification. This review is not permission to commit, publish or activate native account collection.
