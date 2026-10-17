"""Reviewed synthetic exports never implicitly copy private task evidence."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import unittest
from unittest import mock

from account.observation.store import Store, InvalidEvent


def synthetic_case():
    return dict(case_id='verification-report-en', language='en', purpose='outcome',
        inputs=dict(request='Report whether verification ran.',
                    files={'check.py': 'raise SystemExit(2)\n'}),
        outcome_contract=dict(required=['Report failed verification.'], forbidden=['Claim checks passed.']),
        counterpart=dict(inputs=dict(request='Report whether verification ran.',
                                    files={'check.py': 'raise SystemExit(0)\n'}),
                         outcome_contract=dict(required=['Report successful verification.'], forbidden=[])))


class CaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.project = self.home / 'project'; self.project.mkdir()
        self.output = self.home / 'exports'; self.output.mkdir()
        self.store = Store(self.home); self.grant = self.store.grant(self.project)
        event = self.store.capture(self.grant['registration_id'], self.grant['epoch'], json.dumps(dict(
            schema_version=1, project_root=str(self.project), client='synthetic', profile='default',
            source='fixture-v1', session_id='private-session', sequence=1, source_event_id='event',
            event_kind='tool_end', status='failure')).encode())
        self.task = self.store.bind_task(selections=[dict(self.grant, session_id='private-session',
            event_ids=event['event_ids'])], goal='PRIVATE_TASK_GOAL', request_id='bind')
        self.feedback = self.store.add_feedback(self.task['task_id'], symptom='PRIVATE_SYMPTOM',
            correction='PRIVATE_CORRECTION', suspected_cause='PRIVATE_CAUSE',
            evidence_ids=event['event_ids'], request_id='feedback')

    def prepare(self, **changes):
        args = dict(revision_id=self.task['revision_id'], feedback_ids=[self.feedback['feedback_id']],
                    synthetic_case=synthetic_case(), request_id='case')
        args.update(changes)
        return self.store.prepare_case(self.task['task_id'], **args)

    def review(self, case, **changes):
        args=dict(expected_digest=case['case_digest'], reviewer='maintainer',
                  synthetic_data_confirmed=True, privacy_reviewed=True)
        args.update(changes)
        return self.store.review_case(self.task['task_id'], case['case_id'], **args)

    def export(self, case, destination=None):
        return self.store.export_case(self.task['task_id'], case['case_id'],
            expected_digest=case['case_digest'], destination=destination or self.output/'case.json')

    def test_export_requires_review_and_excludes_private_lineage(self):
        case=self.prepare()
        with self.assertRaisesRegex(InvalidEvent,'case_not_reviewed'): self.export(case)
        self.review(case); self.export(case)
        raw=(self.output/'case.json').read_text(); data=json.loads(raw)
        for private in ['PRIVATE_',self.task['task_id'],self.task['revision_id'],
                        self.feedback['feedback_id'],self.grant['registration_id'],'private-session']:
            self.assertNotIn(private,raw)
        self.assertEqual(data['classification'],'development')
        self.assertEqual(data['inputs'],synthetic_case()['inputs'])
        self.assertEqual(data['counterpart'],synthetic_case()['counterpart'])
        self.assertTrue(data['artifact_hashes'])

    def test_missing_correction_is_insufficient_without_case_writes(self):
        weak=self.store.add_feedback(self.task['task_id'],symptom='Command failed',request_id='weak')
        result=self.prepare(feedback_ids=[weak['feedback_id']])
        self.assertEqual(result['status'],'insufficient')
        self.assertEqual(result['reason'],'claim_evidence_missing')

    def test_revision_and_feedback_are_frozen_not_latest(self):
        case=self.prepare()
        changed=self.store.bind_task(selections=[dict(self.grant,session_id='private-session',
            start_sequence=1,end_sequence=1)],goal='later',request_id='later',task_id=self.task['task_id'])
        with self.assertRaisesRegex(InvalidEvent,'case_feedback_revision'):
            self.prepare(revision_id=changed['revision_id'],request_id='wrong')
        self.review(case); self.export(case)

    def test_review_digest_flags_and_changed_case_do_not_reuse_approval(self):
        case=self.prepare()
        with self.assertRaisesRegex(InvalidEvent,'case_digest_mismatch'):
            self.review(case,expected_digest='0'*64)
        with self.assertRaisesRegex(InvalidEvent,'case_review_required'):
            self.review(case,privacy_reviewed=False)
        self.review(case)
        changed=synthetic_case();changed['inputs']['request']='Changed synthetic request'
        second=self.prepare(synthetic_case=changed,request_id='second')
        self.assertNotEqual(case['case_digest'],second['case_digest'])
        with self.assertRaisesRegex(InvalidEvent,'case_not_reviewed'): self.export(second)
        with self.assertRaisesRegex(InvalidEvent,'request_conflict'):
            self.prepare(synthetic_case=changed)

    def test_revoke_blocks_export_purges_private_cases_but_preserves_detached_export(self):
        case=self.prepare(); self.review(case); self.export(case)
        self.store.revoke(self.grant['registration_id'])
        with self.assertRaises((InvalidEvent,FileNotFoundError)):
            self.export(case,self.output/'after.json')
        self.assertFalse((self.output/'after.json').exists())
        self.assertTrue((self.output/'case.json').exists())
        self.assertFalse((self.store.root/'tasks'/self.task['task_id']).exists())

    def test_expired_grant_blocks_review_and_export(self):
        case=self.prepare();self.review(case)
        with mock.patch('account.observation.store.time.time',return_value=10**12):
            with self.assertRaises(InvalidEvent): self.review(case)
            with self.assertRaises(InvalidEvent): self.export(case)

    def test_input_whitelist_and_public_holdout_claims_reject(self):
        for change in [dict(classification='holdout'),dict(lineage='private'),dict(task_goal='secret')]:
            with self.subTest(change=change),self.assertRaises(InvalidEvent):
                self.prepare(synthetic_case=dict(synthetic_case(),**change))
        for filename in ['../secret','/absolute','dir/../../secret','x\\y']:
            data=synthetic_case();data['inputs']['files']={filename:'fake'}
            with self.subTest(filename=filename),self.assertRaises(InvalidEvent): self.prepare(synthetic_case=data)

    def test_symlink_and_existing_output_refuse_without_overwrite(self):
        case=self.prepare();self.review(case)
        outside=self.home/'unrelated';outside.write_text('untouched')
        (self.output/'link.json').symlink_to(outside)
        with self.assertRaises((OSError,ValueError)):self.export(case,self.output/'link.json')
        link=self.home/'export-link';link.symlink_to(self.output)
        with self.assertRaises((OSError,ValueError)):self.export(case,link/'case.json')
        self.export(case)
        with self.assertRaises((OSError,ValueError)):self.export(case)
        self.assertEqual(outside.read_text(),'untouched')

    def test_tampered_stored_public_payload_cannot_pass_old_digest(self):
        case=self.prepare();self.review(case)
        path=self.store.root/'tasks'/self.task['task_id']/(case['case_id']+'.json')
        row=json.loads(path.read_text());row['public_case']['inputs']['request']='tampered'
        path.write_text(json.dumps(row));path.chmod(0o600)
        with self.assertRaisesRegex(InvalidEvent,'case_digest_mismatch'):self.export(case)

    def test_export_and_revocation_share_one_guard(self):
        from account.observation.files import export_new
        case=self.prepare(); self.review(case)
        entered=threading.Event(); revoke_started=threading.Event(); revoked=threading.Event()
        def controlled_export(destination,value):
            entered.set(); self.assertTrue(revoke_started.wait(2))
            self.assertFalse(revoked.wait(.05))
            export_new(destination,value)
        def revoke():
            self.assertTrue(entered.wait(2));revoke_started.set()
            self.store.revoke(self.grant['registration_id']);revoked.set()
        with mock.patch('account.observation.store.export_new',side_effect=controlled_export):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                exported=pool.submit(self.export,case);deleted=pool.submit(revoke)
                exported.result(3);deleted.result(3)
        self.assertTrue((self.output/'case.json').exists())
        self.assertTrue(revoked.is_set())

    def test_development_examples_reproduce_failure_and_success_counterparts(self):
        from account.observation.cases import public_case
        path=Path(__file__).parent/'fixtures/improvement/cases/development.json'
        examples=json.loads(path.read_text())
        self.assertEqual({(r['language'],r['purpose']) for r in examples},
                         {('en','outcome'),('ko','outcome'),('en','routing'),('ko','routing')})
        for example in examples:
            public_case(example)
            if example['purpose']=='outcome':
                for files,code in [(example['inputs']['files'],2),(example['counterpart']['inputs']['files'],0)]:
                    result=subprocess.run([sys.executable,'-c',files['check.py']],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,code)
                    self.assertEqual(result.stdout,b'verification failed\n' if code else b'verification passed\n')


if __name__=='__main__': unittest.main()
