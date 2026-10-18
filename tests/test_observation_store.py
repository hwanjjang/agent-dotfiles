"""Qualify synthetic observations in temporary homes, without live account data."""

import json
import concurrent.futures
import fcntl
import os
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest
from unittest import mock

from account.observation.store import Store


class ObservationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="observation qualification ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.root = self.home / ".agents/agent-dotfiles/observations"
        self.store = Store(self.home)

    def grant(self, **options):
        return self.store.grant(self.project, **options)

    def payload(self, **changes):
        event = dict(schema_version=1, project_root=str(self.project),
                     client="synthetic", profile="default", source="fixture-v1",
                     session_id="session-a", sequence=1,
                     source_event_id="event-a", event_kind="session_start")
        event.update(changes)
        return json.dumps(event).encode()

    def capture(self, grant, **changes):
        return self.store.capture(grant["registration_id"], grant["epoch"],
                                  self.payload(**changes))

    def events(self, grant):
        return self.store.events(grant["registration_id"])

    def fail_record_directory_sync(self, grant):
        """Fail publication fsync, allowing newly hardened ancestor fsyncs."""
        info = (self.root / "records" / grant["registration_id"]).stat()
        target = (info.st_dev, info.st_ino)
        original = os.fsync
        def fail_target(fd):
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) == target:
                raise OSError("synthetic record publication durability failure")
            return original(fd)
        return mock.patch("account.observation.files.os.fsync", side_effect=fail_target)

    def test_opted_out_capture_neither_parses_nor_creates_account_state(self):
        self.assertEqual(list(self.home.iterdir()), [])
        result = self.store.capture("f" * 64, "f" * 32, b"not JSON")
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_unknown_registration_does_not_parse_payload_in_existing_store(self):
        self.grant()
        result = self.store.capture("f" * 64, "f" * 32, b"not JSON")
        self.assertEqual(result["status"], "disabled")

    def test_allowlist_discards_content_and_keeps_observation_gaps(self):
        grant = self.grant()
        marker = "SYNTHETIC_PRIVATE_CONTENT_NOT_FOR_STORAGE"
        result = self.capture(grant, prompt=marker, arguments={"body": marker},
                              output=marker, transcript_path=marker)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(len(result["event_ids"]), 1)
        records = self.events(grant)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["session_id"], "session-a")
        self.assertIsNone(record["actor_id"])
        self.assertIsNone(record["manifest"])
        self.assertTrue(record["gaps"])
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(marker.encode(), path.read_bytes(), str(path))

    def test_response_end_does_not_imply_task_success(self):
        grant = self.grant()
        self.assertEqual(self.capture(grant, event_kind="response_end")["status"], "recorded")
        record = self.events(grant)[0]
        self.assertIn(record.get("status"), (None, "unknown"))
        self.assertNotIn(record.get("task_status"), ("success", "complete", "completed"))

    def test_exact_stable_id_retry_deduplicates_and_conflict_rejects(self):
        grant = self.grant()
        first = self.capture(grant)
        retry = self.capture(grant)
        self.assertEqual(first["status"], "recorded")
        self.assertEqual(retry["status"], "duplicate")
        self.assertEqual(first["event_ids"], retry["event_ids"])
        conflict = self.capture(grant, event_kind="tool_start")
        self.assertEqual(conflict["status"], "rejected")
        self.assertEqual(len(self.events(grant)), 1)

    def test_discarded_content_does_not_change_stable_id_identity(self):
        grant = self.grant()
        self.capture(grant, prompt="synthetic first prompt")
        self.assertEqual(self.capture(grant, prompt="synthetic changed prompt")["status"], "duplicate")
        self.assertEqual(len(self.events(grant)), 1)

    def test_synthetic_replay_remains_compatible_with_slice_one_records(self):
        grant = self.grant(); self.capture(grant)
        record_path, = (self.root / 'records' / grant['registration_id']).glob('*.json')
        record = json.loads(record_path.read_text())
        # Original schema-v1 records put the adapter gap first. Keep their bytes'
        # logical content replayable when introducing another adapter.
        gaps = record['events'][0]['gaps']
        gaps.remove('synthetic_adapter'); gaps.insert(0, 'synthetic_adapter')
        record_path.write_text(json.dumps(record))
        self.assertEqual(self.capture(grant)['status'], 'duplicate')

    def test_missing_stable_id_is_retained_with_duplicate_uncertainty(self):
        grant = self.grant()
        event = json.loads(self.payload())
        del event["source_event_id"]
        payload = json.dumps(event).encode()
        results = [self.store.capture(grant["registration_id"], grant["epoch"], payload)
                   for _ in range(2)]
        self.assertTrue(all(result["status"] == "recorded" for result in results))
        self.assertNotEqual(results[0]["event_ids"], results[1]["event_ids"])
        self.assertEqual(len(self.events(grant)), 2)
        for record in self.events(grant):
            self.assertIn("possible_duplicate", record["gaps"])

    def test_project_profile_source_registration_boundaries(self):
        grant = self.grant()
        other_project = self.base / "other project"
        other_project.mkdir()
        for changes in ({"project_root": str(other_project)}, {"profile": "other"},
                        {"source": "other"}, {"client": "codex"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.capture(grant, **changes)["status"], "rejected")
        second = self.grant(profile="other")
        third = self.store.grant(other_project)
        self.assertEqual(self.capture(grant)["status"], "recorded")
        self.assertEqual(self.capture(second, profile="other")["status"], "recorded")
        self.assertEqual(self.capture(third, project_root=str(other_project))["status"], "recorded")
        self.assertEqual(len({grant["registration_id"], second["registration_id"],
                              third["registration_id"]}), 3)
        self.assertEqual([len(self.events(g)) for g in (grant, second, third)], [1, 1, 1])
        self.assertNotEqual(self.events(grant)[0]["project_id"],
                            self.events(third)[0]["project_id"])

    def test_session_and_child_identity_are_not_conflated(self):
        grant = self.grant()
        self.assertEqual(self.capture(grant, actor_id="parent")["status"], "recorded")
        self.assertEqual(self.capture(grant, session_id="session-b", actor_id="child",
                                     parent_actor_id="parent")["status"], "recorded")
        records = {record["session_id"]: record for record in self.events(grant)}
        self.assertEqual(set(records), {"session-a", "session-b"})
        self.assertEqual(records["session-b"]["actor_id"], "child")
        self.assertEqual(records["session-b"]["parent_actor_id"], "parent")

    def test_invalid_and_oversized_events_are_rejected_without_content_in_reason(self):
        grant = self.grant()
        marker = "SYNTHETIC_INVALID_CONTENT"
        samples = [marker.encode(), self.payload(schema_version=2),
                   self.payload(sequence=True), self.payload(sequence=0),
                   self.payload(occurred_at=float("nan")),
                   self.payload(occurred_at=float("inf")), self.payload(event_kind="unknown"),
                   self.payload(prompt=marker * 1000)]
        for payload in samples:
            with self.subTest(size=len(payload)):
                result = self.store.capture(grant["registration_id"], grant["epoch"], payload)
                self.assertEqual(result["status"], "rejected")
                self.assertNotIn(marker, json.dumps(result))
        self.assertEqual(self.events(grant), [])

    def test_batch_partial_line_retry_and_continuation_are_atomic(self):
        grant = self.grant()
        first = self.payload() + b"\n"
        second = self.payload(sequence=2, source_event_id="event-b") + b"\n"
        partial = first + second[:17]
        args = (grant["registration_id"], grant["epoch"])
        result = self.store.import_batch(*args, 0, partial)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["next_offset"], len(first))
        self.assertEqual(result["trailing_bytes"], 17)
        retry = self.store.import_batch(*args, 0, partial)
        self.assertEqual(retry["status"], "duplicate")
        self.assertEqual(retry["next_offset"], len(first))
        self.assertEqual(len(self.events(grant)), 1)
        self.store.rebuild_index()
        reopened = Store(self.home)
        result = reopened.import_batch(*args, len(first), second)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["next_offset"], len(first + second))
        self.assertEqual(len(reopened.events(grant["registration_id"])), 2)

    def test_bad_batch_cannot_commit_prefix_or_advance_cursor(self):
        grant = self.grant()
        first = self.payload() + b"\n"
        bad = self.payload(sequence=2, source_event_id="event-b", schema_version=99) + b"\n"
        args = (grant["registration_id"], grant["epoch"])
        self.assertEqual(self.store.import_batch(*args, 0, first + bad)["status"], "rejected")
        self.assertEqual(self.events(grant), [])
        corrected = self.payload(sequence=2, source_event_id="event-b") + b"\n"
        self.assertEqual(self.store.import_batch(*args, 0, first + corrected)["status"], "recorded")
        self.assertEqual(len(self.events(grant)), 2)

    def test_batch_retry_with_changed_normalized_content_rejects(self):
        grant = self.grant()
        args = (grant["registration_id"], grant["epoch"])
        original = self.payload() + b"\n"
        self.assertEqual(self.store.import_batch(*args, 0, original)["status"], "recorded")
        changed = self.payload(event_kind="response_end") + b"\n"
        self.assertEqual(self.store.import_batch(*args, 0, changed)["status"], "rejected")
        self.assertEqual(len(self.events(grant)), 1)
        self.assertEqual(self.events(grant)[0]["event_kind"], "session_start")

    def test_empty_and_partial_only_batches_do_not_move_cursor(self):
        grant = self.grant()
        args = (grant["registration_id"], grant["epoch"])
        for payload in (b"", self.payload()):
            result = self.store.import_batch(*args, 0, payload)
            self.assertEqual(result["next_offset"], 0)
            self.assertEqual(result["trailing_bytes"], len(payload))
            self.assertEqual(self.events(grant), [])
        self.assertEqual(self.store.import_batch(*args, 0, self.payload() + b"\n")["status"], "recorded")

    def test_batch_limits_and_noncontiguous_cursor_reject(self):
        grant = self.grant()
        args = (grant["registration_id"], grant["epoch"])
        for offset, payload in ((10, self.payload() + b"\n"), (0, b"x" * 65537),
                                (0, (self.payload() + b"\n") * 129)):
            self.assertEqual(self.store.import_batch(*args, offset, payload)["status"], "rejected")
        self.assertEqual(self.events(grant), [])

    def test_import_rejects_non_integer_offsets_without_falling_back_to_capture(self):
        grant = self.grant()
        args = (grant["registration_id"], grant["epoch"])
        for offset in (None, True, False, -1):
            with self.subTest(offset=offset):
                result = self.store.import_batch(*args, offset, self.payload())
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["reason"], "import_offset")
                self.assertEqual(self.events(grant), [])

    def test_concurrent_independent_writers_preserve_every_acknowledged_event(self):
        grant = self.grant()
        def write(number):
            store = Store(self.home)
            return store.capture(grant["registration_id"], grant["epoch"],
                                 self.payload(sequence=number + 1, source_event_id=f"event-{number}"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(write, range(18)))
        self.assertTrue(all(result["status"] == "recorded" for result in results), results)
        self.assertEqual(len(self.events(grant)), 18)
        self.assertEqual(self.store.rebuild_index(), 18)

    def test_revoke_purges_payload_and_regrant_excludes_old_sequences(self):
        grant = self.grant()
        marker = "synthetic-sensitive-session"
        self.assertEqual(self.capture(grant, session_id=marker, sequence=12)["status"], "recorded")
        self.store.rebuild_index()
        self.store.revoke(grant["registration_id"])
        self.assertEqual(self.events(grant), [])
        self.assertEqual(self.capture(grant, sequence=13)["status"], "disabled")
        self.assertEqual(self.store.rebuild_index(), 0)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(marker.encode(), path.read_bytes(), str(path))
        with self.assertRaises(ValueError):
            self.grant(start_after=11)
        renewed = self.grant(start_after=12)
        self.assertNotEqual(renewed["epoch"], grant["epoch"])
        self.assertEqual(self.capture(renewed, sequence=12)["status"], "rejected")
        self.assertEqual(self.capture(renewed, sequence=13)["status"], "recorded")
        self.assertEqual(self.capture(grant, sequence=14)["status"], "disabled")
        self.assertEqual(len(self.events(renewed)), 1)

    def test_corrupt_ledger_cannot_block_revocation_or_reuse_unknown_frontier(self):
        for variant in ("invalid-json", "array", "null", "empty-object", "missing-epoch"):
            with self.subTest(corruption=variant):
                source = "fixture-corruption-" + variant
                grant = self.grant(source=source)
                marker = "synthetic-corrupt-ledger-session"
                self.capture(grant, source=source, sequence=7, session_id=marker)
                self.store.rebuild_index()
                record_dir = self.root / "records" / grant["registration_id"]
                record = next(record_dir.glob("*.json"))
                damaged = json.loads(record.read_bytes())
                del damaged["epoch"]
                bodies = {"invalid-json": b'{"incomplete": "' + marker.encode(),
                          "array": b"[]", "null": b"null", "empty-object": b"{}",
                          "missing-epoch": json.dumps(damaged).encode()}
                record.write_bytes(bodies[variant])
                result = self.store.revoke(grant["registration_id"])
                self.assertEqual(result["status"], "revoked")
                self.assertIsNone(result["high_water"])
                self.assertEqual(self.events(grant), [])
                self.assertEqual(self.capture(grant, source=source, sequence=8)["status"], "disabled")
                self.assertFalse(record_dir.exists())
                for path in self.root.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(marker.encode(), path.read_bytes())
                with self.assertRaisesRegex(ValueError, "source_generation_required"):
                    self.grant(source=source, start_after=1000)
                new_source = source + "-generation-2"
                renewed = self.grant(source=new_source)
                self.assertEqual(self.capture(renewed, source=new_source)["status"], "recorded")

    def test_concurrent_capture_and_revoke_leave_no_stale_epoch_evidence(self):
        grant = self.grant()
        start = threading.Barrier(5, timeout=3)
        revoked = threading.Event()
        def writer(number):
            store = Store(self.home)
            args = (grant["registration_id"], grant["epoch"])
            start.wait()
            before = store.capture(*args, self.payload(sequence=number + 1,
                                                      source_event_id=f"racing-{number}"))
            self.assertTrue(revoked.wait(timeout=3))
            after = store.capture(*args, self.payload(sequence=number + 10,
                                                     source_event_id=f"after-{number}"))
            return before, after
        def revoker():
            start.wait()
            result = Store(self.home).revoke(grant["registration_id"])
            revoked.set()
            return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            writers = [pool.submit(writer, number) for number in range(4)]
            revoke = pool.submit(revoker)
            self.assertEqual(revoke.result(timeout=5)["status"], "revoked")
            results = [future.result(timeout=5) for future in writers]
        for before, after in results:
            self.assertIn(before["status"], ("recorded", "disabled"))
            self.assertEqual(after["status"], "disabled")
        self.assertEqual(self.events(grant), [])
        self.assertEqual(self.store.rebuild_index(), 0)

    def test_private_directory_and_file_modes(self):
        grant = self.grant()
        self.capture(grant)
        self.store.rebuild_index()
        for path in [self.root] + list(self.root.rglob("*")):
            expected = 0o700 if path.is_dir() else 0o600
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), expected, str(path))

    def test_symlinked_account_parent_is_rejected_without_external_writes(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.home / ".agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.grant()
        self.assertEqual(list(outside.iterdir()), [])

    def test_lock_contention_is_bounded_and_does_not_accept_an_event(self):
        grant = self.grant()
        with (self.root / "store.lock").open("r+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            start = time.monotonic()
            result = self.capture(grant)
            elapsed = time.monotonic() - start
        self.assertEqual(result["status"], "busy")
        self.assertLess(elapsed, 3)
        self.assertEqual(self.events(grant), [])

    def test_interrupted_replace_leaves_no_committed_event_or_cursor(self):
        grant = self.grant()
        args = (grant["registration_id"], grant["epoch"])
        payload = self.payload() + b"\n"
        with mock.patch("account.observation.files.os.replace", side_effect=OSError("synthetic interruption")):
            self.assertEqual(self.store.import_batch(*args, 0, payload)["status"], "error")
        reopened = Store(self.home)
        self.assertEqual(reopened.events(grant["registration_id"]), [])
        result = reopened.import_batch(*args, 0, payload)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["next_offset"], len(payload))
        self.assertEqual(len(reopened.events(grant["registration_id"])), 1)

    def test_file_fsync_failure_does_not_publish_event(self):
        grant = self.grant()
        original = os.fsync
        def fail_file_fsync(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("synthetic file fsync failure")
            return original(fd)
        with mock.patch("account.observation.files.os.fsync", side_effect=fail_file_fsync):
            self.assertEqual(self.capture(grant)["status"], "error")
        self.assertEqual(Store(self.home).events(grant["registration_id"]), [])
        self.assertEqual(self.capture(grant)["status"], "recorded")

    def test_failed_directory_fsync_has_recoverable_idempotent_retry(self):
        grant = self.grant()
        # Create the directory first, so the fault is after record publication.
        self.capture(grant)
        with self.fail_record_directory_sync(grant):
            result = self.capture(grant, source_event_id="event-b", sequence=2)
            self.assertEqual(result["status"], "error")
            self.assertEqual(len(self.events(grant)), 2)
        retry = self.capture(grant, source_event_id="event-b", sequence=2)
        self.assertEqual(retry["status"], "duplicate")
        self.assertEqual(len(Store(self.home).events(grant["registration_id"])), 2)

    def test_duplicate_retry_cannot_acknowledge_while_directory_fsync_still_fails(self):
        grant = self.grant()
        self.capture(grant)
        with self.fail_record_directory_sync(grant):
            self.assertEqual(self.capture(grant, source_event_id="event-b", sequence=2)["status"], "error")
            self.assertEqual(len(self.events(grant)), 2)
            self.assertEqual(self.capture(grant, source_event_id="event-b", sequence=2)["status"], "error")
        self.assertEqual(self.capture(grant, source_event_id="event-b", sequence=2)["status"], "duplicate")

    def test_interrupted_purge_keeps_revocation_effective_and_can_resume(self):
        grant = self.grant()
        self.capture(grant, sequence=7, session_id="synthetic-purge-residue")
        self.store.rebuild_index()
        original = os.unlink
        def interrupt_record_unlink(name, *args, **kwargs):
            if str(name).endswith(".json"):
                raise OSError("synthetic interruption after revocation")
            return original(name, *args, **kwargs)
        with mock.patch("account.observation.files.os.unlink", side_effect=interrupt_record_unlink):
            with self.assertRaises(OSError):
                self.store.revoke(grant["registration_id"])
        reopened = Store(self.home)
        self.assertEqual(reopened.events(grant["registration_id"]), [])
        self.assertEqual(self.capture(grant, sequence=8)["status"], "disabled")
        reopened.revoke(grant["registration_id"])
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"synthetic-purge-residue", path.read_bytes())
        with self.assertRaises(ValueError):
            self.grant(start_after=6)
        renewed = self.grant(start_after=7)
        self.assertEqual(self.capture(renewed, sequence=8)["status"], "recorded")

    def test_batch_replay_cannot_acknowledge_while_directory_fsync_still_fails(self):
        grant = self.grant()
        self.capture(grant)
        args = (grant["registration_id"], grant["epoch"], 0,
                self.payload(sequence=2, source_event_id="event-b") + b"\n")
        with self.fail_record_directory_sync(grant):
            self.assertEqual(self.store.import_batch(*args)["status"], "error")
            self.assertEqual(len(self.events(grant)), 2)
            self.assertEqual(self.store.import_batch(*args)["status"], "error")
        self.assertEqual(self.store.import_batch(*args)["status"], "duplicate")
        self.assertEqual(len(self.events(grant)), 2)

    def test_fifo_lock_is_refused_without_blocking(self):
        grant = self.grant()
        lock = self.root / "store.lock"
        lock.unlink()
        os.mkfifo(lock, 0o600)
        start = time.monotonic()
        result = self.capture(grant)
        self.assertEqual(result["status"], "error")
        self.assertLess(time.monotonic() - start, 1)

    def test_oversized_integer_time_is_rejected_in_capture_and_import(self):
        grant = self.grant()
        payload = self.payload(occurred_at=10 ** 1000)
        args = (grant["registration_id"], grant["epoch"])
        self.assertEqual(self.store.capture(*args, payload)["status"], "rejected")
        self.assertEqual(self.store.import_batch(*args, 0, payload + b"\n")["status"], "rejected")
        self.assertEqual(self.events(grant), [])

    def test_index_rebuild_refuses_symlink_without_touching_target(self):
        grant = self.grant()
        self.capture(grant)
        outside = self.base / "unrelated-file"
        outside.write_bytes(b"synthetic unrelated content")
        index = self.root / "index.sqlite"
        index.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.store.rebuild_index()
        self.assertTrue(index.is_symlink())
        self.assertEqual(outside.read_bytes(), b"synthetic unrelated content")
        self.assertEqual(len(self.events(grant)), 1)

    def test_copied_old_epoch_and_uncommitted_pending_files_do_not_resurrect(self):
        grant = self.grant()
        self.capture(grant)
        record_dir = self.root / "records" / grant["registration_id"]
        old_records = {path.name: path.read_bytes() for path in record_dir.glob("*.json")}
        self.assertTrue(old_records)
        self.store.revoke(grant["registration_id"])
        renewed = self.grant(start_after=1)
        self.capture(renewed, sequence=2, source_event_id="event-b")
        for name, body in old_records.items():
            path = record_dir / name
            path.write_bytes(body)
            path.chmod(0o600)
        pending = record_dir / ".pending-synthetic-interruption"
        pending.write_bytes(b"incomplete JSON from interrupted writer")
        pending.chmod(0o600)
        reopened = Store(self.home)
        records = reopened.events(renewed["registration_id"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["epoch"], renewed["epoch"])
        self.assertEqual(reopened.rebuild_index(), 1)

    def test_expiry_disables_capture_and_prune_purges_evidence(self):
        with mock.patch("account.observation.store.time.time", return_value=1000):
            grant = self.grant(lifetime_seconds=30)
            self.capture(grant, session_id="synthetic-expiring-session")
        with mock.patch("account.observation.store.time.time", return_value=1031):
            self.assertEqual(self.capture(grant, sequence=2)["status"], "disabled")
            self.assertEqual(self.events(grant), [])
            self.store.prune()
        self.assertEqual(self.events(grant), [])
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"synthetic-expiring-session", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
