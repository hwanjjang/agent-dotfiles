"""Selected tasks and feedback through the consent-aware public Store interface."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from account.observation.files import Files
from account.observation.store import InvalidEvent, Store


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.project = self.home / 'project'; self.project.mkdir()
        self.store = Store(self.home)
        self.grant = self.store.grant(self.project)
        self.first = self.event(1, 'one')
        self.second = self.event(2, 'two')

    def event(self, sequence, session, grant=None, project=None):
        grant, project = grant or self.grant, project or self.project
        result = self.store.capture(grant['registration_id'], grant['epoch'], json.dumps(dict(
            schema_version=1, project_root=str(project), client='synthetic',
            profile='default', source='fixture-v1', session_id=session,
            sequence=sequence, source_event_id=f'e-{sequence}', event_kind='tool_end',
            status='failure')).encode())
        self.assertEqual(result['status'], 'recorded', result)
        return result['event_ids'][0]

    def selection(self, session='one', ids=None, grant=None):
        return dict(**(grant or self.grant), session_id=session,
                    event_ids=ids or [self.first])

    def bind(self, **changes):
        args = dict(selections=[self.selection()], goal='Check the export', request_id='bind-1')
        args.update(changes)
        return self.store.bind_task(**args)

    def feedback(self, task_id, **changes):
        args = dict(symptom='Command failed', correction=None, evidence_ids=[self.first],
                    contrary_evidence_ids=[], suspected_cause=None, confidence='unknown',
                    author='user', request_id='feedback-1')
        args.update(changes)
        return self.store.add_feedback(task_id, **args)

    def test_selected_multisession_task_does_not_expand_and_keeps_unknown_actors(self):
        receipt = self.bind(selections=[self.selection(), self.selection('two', [self.second])])
        self.event(3, 'one')
        view = self.store.task(receipt['task_id'])
        selections = view['revisions'][0]['selections']
        self.assertEqual({e['event_id'] for s in selections for e in s['events']}, {self.first, self.second})
        self.assertTrue(all(e['actor_id'] is None for s in selections for e in s['events']))
        self.assertTrue(all(e['turn_id'] is None for s in selections for e in s['events']))

    def test_interval_resolves_once_and_duplicate_retries_do_not_expand_it(self):
        selection = dict(self.grant, session_id='one', start_sequence=1, end_sequence=9)
        first = self.bind(selections=[selection])
        self.event(3, 'one')
        retry = self.bind(selections=[selection])
        self.assertEqual(retry['status'], 'duplicate')
        self.assertEqual(first['revision_id'], retry['revision_id'])
        events = self.store.task(first['task_id'])['revisions'][0]['selections'][0]['events']
        self.assertEqual([e['event_id'] for e in events], [self.first])

    def test_idempotency_conflicts_and_immutable_revisions(self):
        first = self.bind()
        before = {p: p.read_bytes() for p in self.store.root.rglob('tasks/**/*.json')}
        self.assertEqual(self.bind()['status'], 'duplicate')
        with self.assertRaisesRegex(InvalidEvent, 'request_conflict'):
            self.bind(goal='Changed')
        second = self.bind(task_id=first['task_id'], request_id='bind-2',
                           selections=[self.selection('two', [self.second])])
        self.assertNotEqual(first['revision_id'], second['revision_id'])
        self.assertEqual(len(self.store.task(first['task_id'])['revisions']), 2)
        for path, body in before.items():
            self.assertEqual(path.read_bytes(), body)

    def test_feedback_is_not_a_diagnosis_and_binds_exact_revision(self):
        task = self.bind()
        feedback = self.feedback(task['task_id'])
        self.assertEqual(feedback['evidence_status'], 'insufficient_claim_evidence')
        self.bind(task_id=task['task_id'], request_id='bind-2')
        self.assertEqual(self.feedback(task['task_id'])['feedback_id'], feedback['feedback_id'])
        corrected = self.feedback(task['task_id'], request_id='feedback-2',
                                  correction='The assistant said checks passed; they did not.')
        self.assertEqual(corrected['evidence_status'], 'reported_correction')
        rows = self.store.task(task['task_id'])['feedback']
        self.assertEqual(rows[0]['revision_id'], task['revision_id'])
        self.assertIsNone(rows[0]['suspected_cause'])
        self.assertNotIn('verified_diagnosis', rows[1])
        with self.assertRaisesRegex(InvalidEvent, 'evidence_not_selected'):
            self.feedback(task['task_id'], request_id='feedback-3', evidence_ids=[self.second])

    def test_scope_and_actor_failures(self):
        for selection in [self.selection('wrong'), self.selection(ids=[self.second]),
                          dict(self.selection(), actor_id='invented'),
                          dict(self.selection(), epoch='0' * 32),
                          dict(self.selection(), registration_id='f' * 64)]:
            with self.subTest(selection=selection), self.assertRaises((InvalidEvent, FileNotFoundError)):
                self.bind(selections=[selection])
        self.assertFalse((self.store.root / 'tasks').exists())

    def test_cross_project_requires_each_grant_and_revoke_purges_whole_task(self):
        other = self.home / 'other'; other.mkdir()
        grant = self.store.grant(other)
        event = self.event(1, 'one', grant, other)
        task = self.bind(selections=[self.selection(), self.selection(ids=[event], grant=grant)])
        self.feedback(task['task_id'], correction='PRIVATE_CORRECTION_SENTINEL')
        self.store.revoke(grant['registration_id'])
        self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
        self.assertEqual(len(self.store.events(self.grant['registration_id'])), 2)
        for p in self.store.root.rglob('*'):
            if p.is_file(): self.assertNotIn(b'PRIVATE_CORRECTION_SENTINEL', p.read_bytes())

    def test_expiry_and_copied_old_records_cannot_resurrect(self):
        task = self.bind()
        directory = self.store.root / 'tasks' / task['task_id']
        copies = {p.name: p.read_bytes() for p in directory.iterdir()}
        with mock.patch('account.observation.store.time.time', return_value=10**12):
            self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
            self.store.prune()
        renewed = self.store.grant(self.project, start_after=2)
        self.assertNotEqual(renewed['epoch'], self.grant['epoch'])
        directory.mkdir(mode=0o700)
        for name, body in copies.items():
            p = directory / name; p.write_bytes(body); p.chmod(0o600)
        self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')

    def test_interrupted_purge_is_disabled_and_prune_finishes(self):
        task = self.bind()
        original = Files.clear
        def interrupted(files, path):
            if path[0] == 'tasks': raise OSError('simulated interruption')
            return original(files, path)
        with mock.patch.object(Files, 'clear', interrupted), self.assertRaises(OSError):
            self.store.revoke(self.grant['registration_id'])
        self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
        self.store.prune()
        self.assertFalse((self.store.root / 'tasks' / task['task_id']).exists())

    def test_feedback_racing_revoke_cannot_survive(self):
        task = self.bind(); start = threading.Barrier(2)
        def feedback():
            start.wait()
            try: return self.feedback(task['task_id'])
            except (InvalidEvent, FileNotFoundError): return None
        def revoke():
            start.wait(); return self.store.revoke(self.grant['registration_id'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(feedback), pool.submit(revoke)
            a.result(timeout=5); b.result(timeout=5)
        self.assertEqual(self.store.task(task['task_id'])['status'], 'disabled')
        self.assertFalse((self.store.root / 'tasks' / task['task_id']).exists())

    def test_oversized_content_and_unknown_fields_reject(self):
        with self.assertRaises(InvalidEvent): self.bind(goal='x' * 8193)
        with self.assertRaises(InvalidEvent): self.bind(selections=[dict(self.selection(), transcript_path='/private')])
        task = self.bind()
        with self.assertRaises(InvalidEvent): self.feedback(task['task_id'], correction='x' * 8193)

    def test_purge_removes_orphaned_partial_task_writes(self):
        # A killed writer can leave private bytes without a committed task record.
        orphan = self.store.root / 'tasks' / ('a' * 64)
        orphan.mkdir(parents=True, mode=0o700)
        orphan.parent.chmod(0o700)
        pending = orphan / '.pending-interrupted'
        pending.write_text('PRIVATE_PARTIAL_FEEDBACK'); pending.chmod(0o600)
        self.store.revoke(self.grant['registration_id'])
        self.assertFalse(orphan.exists())

    def test_published_write_retry_acknowledges_same_revision(self):
        original = Files.write
        def publish_then_interrupt(files, path, value):
            original(files, path, value)
            if path[0] == 'tasks': raise OSError('interrupted acknowledgment')
        with mock.patch.object(Files, 'write', publish_then_interrupt), self.assertRaises(OSError):
            self.bind()
        retried = self.bind()
        self.assertEqual(retried['status'], 'duplicate')
        self.assertEqual(len(self.store.task(retried['task_id'])['revisions']), 1)

    def test_unknown_task_and_unsafe_task_directory_do_not_follow_symlinks(self):
        self.assertEqual(self.store.task('f' * 64), {'status': 'disabled'})
        task = self.bind()
        outside = self.home / 'untouched'; outside.mkdir()
        directory = self.store.root / 'tasks' / task['task_id']
        for path in directory.iterdir(): path.unlink()
        directory.rmdir(); directory.symlink_to(outside)
        with self.assertRaises(OSError): self.store.task(task['task_id'])
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
