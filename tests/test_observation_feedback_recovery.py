"""Feedback recovery, persisted bounds, and explicit revision input regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_observation_feedback as fixtures
from account.observation.files import encoded, UnsafeStore
from account.observation.store import InvalidEvent, Store


class FeedbackRecoveryTests(unittest.TestCase):
    setUp = fixtures.FeedbackTests.setUp
    event = fixtures.FeedbackTests.event
    selection = fixtures.FeedbackTests.selection
    bind = fixtures.FeedbackTests.bind
    feedback = fixtures.FeedbackTests.feedback

    def test_corrupt_task_entries_cannot_block_revoke_or_prune_and_index_cleanup(self):
        # Corruption belongs to an unrelated active grant, so cleanup must not
        # infer safe lineage from a partially parsed row and retain private bytes.
        for damage in ['invalid_json', 'duplicate_sequence', 'missing_registration',
                       'oversized', 'too_many_entries', 'symlink', 'non_private', 'nested']:
            for operation in ['revoke', 'prune']:
                with self.subTest(damage=damage, operation=operation), tempfile.TemporaryDirectory() as tmp:
                    home = Path(tmp).resolve(); project = home/'project'; project.mkdir()
                    other = home/'other'; other.mkdir(); store = Store(home)
                    with mock.patch('account.observation.store.time.time', return_value=100):
                        target = store.grant(project, lifetime_seconds=1)
                        live = store.grant(other, lifetime_seconds=1000)
                        def bind(grant, root, request):
                            event = store.capture(grant['registration_id'], grant['epoch'], json.dumps(dict(
                                schema_version=1, project_root=str(root), client='synthetic', profile='default',
                                source='fixture-v1', session_id='one', sequence=1, source_event_id='event',
                                event_kind='tool_end')).encode())
                            return store.bind_task(selections=[dict(grant,session_id='one',event_ids=event['event_ids'])],
                                                   goal='PRIVATE_GOAL', request_id=request)
                        doomed=bind(target,project,'doomed'); keep=bind(live,other,'keep'); bad=bind(live,other,'bad')
                        store.rebuild_index()
                    directory=store.root/'tasks'/bad['task_id']; row=next(directory.glob('*.json'))
                    outside=home/'outside';outside.mkdir(); sentinel=outside/'sentinel';sentinel.write_text('DO NOT TOUCH')
                    if damage=='invalid_json':row.write_text('{broken PRIVATE_DATA')
                    elif damage=='duplicate_sequence':
                        extra=directory/('f'*64+'.json');data=json.loads(row.read_text());data['record_id']='f'*64;extra.write_bytes(encoded(data));extra.chmod(0o600)
                    elif damage=='missing_registration':
                        data=json.loads(row.read_text());data['registrations']=[{'epoch':live['epoch']}];row.write_bytes(encoded(data))
                    elif damage=='oversized':row.write_bytes(b'PRIVATE_DATA'*14000)
                    elif damage=='too_many_entries':
                        for i in range(130):(directory/f'unknown-{i}').write_text('PRIVATE_DATA')
                    elif damage=='symlink':
                        row.unlink();directory.rmdir();directory.symlink_to(outside,target_is_directory=True)
                    elif damage=='non_private':directory.chmod(0o755)
                    elif damage=='nested':
                        nested=directory/'unknown-directory';nested.mkdir();(nested/'private').write_text('PRIVATE_DATA')
                        (nested/'link').symlink_to(outside,target_is_directory=True)
                    with mock.patch('account.observation.store.time.time', return_value=102):
                        if operation=='revoke':self.assertEqual(store.revoke(target['registration_id'])['status'],'revoked')
                        else:self.assertEqual(store.prune(),1)
                        self.assertEqual(store.task(keep['task_id'])['status'],'ok')
                        self.assertFalse((store.root/'tasks'/doomed['task_id']).exists())
                        self.assertFalse(directory.exists() or directory.is_symlink())
                        self.assertFalse((store.root/'index.sqlite').exists())
                        self.assertEqual(sentinel.read_text(),'DO NOT TOUCH')
                        self.assertEqual(len(store.events(live['registration_id'])),1)
                        store.grant(project,start_after=1)

    def test_resolved_large_unicode_task_refuses_before_publishing_unreadable_row(self):
        selections=[]
        for session in range(16):
            name=f's{session}-'+'s'*150
            start=3+session*8
            for sequence in range(start,start+8):
                payload=dict(schema_version=1,project_root=str(self.project),client='synthetic',profile='default',
                    source='fixture-v1',session_id=name,sequence=sequence,source_event_id=f'long-{sequence}',
                    event_kind='tool_end',actor_id='a'*160,parent_actor_id='p'*160,turn_id='t'*160)
                self.assertEqual(self.store.capture(self.grant['registration_id'],self.grant['epoch'],json.dumps(payload).encode())['status'],'recorded')
            selections.append(dict(self.grant,session_id=name,start_sequence=start,end_sequence=start+7))
        with self.assertRaisesRegex(InvalidEvent,'task_record_size'):
            self.bind(selections=selections,goal='😀'*2048)
        self.assertFalse((self.store.root/'tasks').exists())
        # The same 128-event selection with a small goal remains readable.
        result=self.bind(selections=selections,goal='Check export')
        self.assertEqual(self.store.task(result['task_id'])['status'],'ok')
        payload.update(sequence=131,source_event_id='long-131')
        self.assertEqual(self.store.capture(self.grant['registration_id'],self.grant['epoch'],json.dumps(payload).encode())['status'],'recorded')
        with self.assertRaisesRegex(InvalidEvent,'task_event_limit'):
            self.bind(request_id='too-many-events',selections=selections[:-1]+[dict(selections[-1],end_sequence=131)])

    def test_cleanup_rejects_traversal_before_examining_target(self):
        with self.store._locked() as files:
            with mock.patch('account.observation.files.os.stat',side_effect=AssertionError('unsafe target examined')):
                with self.assertRaises(UnsafeStore):files.clear(('..',))

    def test_revision_id_requires_none_or_valid_token_and_overlap_is_explicit(self):
        task=self.bind()
        for index,value in enumerate(['',0,False,[],{},'has space']):
            with self.subTest(value=value), self.assertRaisesRegex(InvalidEvent,'task_revision'):
                self.feedback(task['task_id'],request_id=f'invalid-{index}',revision_id=value)
        self.assertEqual(self.store.task(task['task_id'])['feedback'],[])
        accepted=self.feedback(task['task_id'],revision_id=None,evidence_ids=[self.first],contrary_evidence_ids=[self.first])
        row=self.store.task(task['task_id'])['feedback'][0]
        self.assertEqual(accepted['revision_id'],task['revision_id'])
        self.assertEqual(row['evidence_ids'],row['contrary_evidence_ids'])

    def test_new_registration_in_later_revision_purges_whole_task(self):
        task=self.bind();other=self.home/'other';other.mkdir();grant=self.store.grant(other)
        event=self.event(1,'one',grant,other)
        self.bind(task_id=task['task_id'],request_id='revision-2',selections=[self.selection(ids=[event],grant=grant)])
        self.feedback(task['task_id'],evidence_ids=[event])
        self.store.revoke(grant['registration_id'])
        self.assertEqual(self.store.task(task['task_id'])['status'],'disabled')
        self.assertFalse((self.store.root/'tasks'/task['task_id']).exists())
        self.assertEqual(len(self.store.events(self.grant['registration_id'])),2)

    def test_overlapping_selections_deduplicate_and_invalid_intervals_refuse(self):
        result=self.bind(selections=[self.selection(),dict(self.grant,session_id='one',start_sequence=1,end_sequence=2)])
        row=self.store.task(result['task_id'])['revisions'][0]
        self.assertEqual(sum(len(s['events']) for s in row['selections']),1)
        for selection in [dict(self.grant,session_id='one'),dict(self.grant,session_id='one',start_sequence=2,end_sequence=1)]:
            with self.assertRaisesRegex(InvalidEvent,'task_interval'):
                self.bind(request_id='invalid-interval',selections=[selection])


if __name__=='__main__':unittest.main()
