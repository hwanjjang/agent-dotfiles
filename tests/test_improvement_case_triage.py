"""Evidence-bound caller triage and exact publication refusals."""
import json
import os
from pathlib import Path
import unittest
from unittest import mock
import test_improvement_cases as cases
from account.observation.store import InvalidEvent
from account.observation.files import UnsafeStore, export_new


class TriageTests(unittest.TestCase):
    setUp = cases.CaseTests.setUp
    prepare = cases.CaseTests.prepare
    review = cases.CaseTests.review
    export = cases.CaseTests.export

    def test_categories_are_distinct_and_never_create_exportable_cases(self):
        for category in ['environment', 'auth', 'grader', 'unknown']:
            with self.subTest(category=category):
                result=self.prepare(triage=dict(category=category,evidence_ids=self.evidence_ids))
                self.assertEqual(result,dict(status='insufficient' if category=='unknown' else 'blocked',
                                             reason='triage_'+category))
        self.assertEqual(len(list((self.store.root/'tasks'/self.task['task_id']).glob('*.json'))),2)

    def test_reference_must_belong_to_revision_and_selected_feedback(self):
        with self.assertRaisesRegex(InvalidEvent,'case_triage_evidence'):
            self.prepare(triage=dict(category='instruction',evidence_ids=['unselected']))
        unlinked=self.store.add_feedback(self.task['task_id'],symptom='x',correction='y',request_id='unlinked')
        with self.assertRaisesRegex(InvalidEvent,'case_triage_evidence'):
            self.prepare(feedback_ids=[unlinked['feedback_id']])

    def test_missing_or_unknown_outcome_is_not_failed_tool_but_routing_is_eligible(self):
        # A normalized native unknown status must never be interpreted as failure.
        original=self.store._records
        for status in ['success','unknown']:
            def records(files,grant):
                rows=original(files,grant)
                for row in rows:
                    for event in row['events']: event['status']=status
                return rows
            with self.subTest(status=status),mock.patch.object(self.store,'_records',side_effect=records):
                self.assertEqual(self.prepare(),dict(status='insufficient',reason='failed_tool_evidence_missing'))
                data=cases.synthetic_case();data['purpose']='routing'
                self.assertEqual(self.prepare(synthetic_case=data,request_id=status)['status'],'prepared')

    def test_validation_precedes_insufficiency(self):
        weak=self.store.add_feedback(self.task['task_id'],symptom='x',evidence_ids=self.evidence_ids,request_id='weak')
        with self.assertRaisesRegex(InvalidEvent,'request_id'):
            self.prepare(feedback_ids=[weak['feedback_id']],request_id='')
        with self.assertRaisesRegex(InvalidEvent,'case_fields'):
            self.prepare(feedback_ids=[weak['feedback_id']],synthetic_case={})
        for triage in [None,{},dict(category='other',evidence_ids=self.evidence_ids),
                       dict(category='instruction',evidence_ids=[]),
                       dict(category='instruction',evidence_ids=self.evidence_ids*2)]:
            with self.subTest(triage=triage),self.assertRaisesRegex(InvalidEvent,'case_triage'):
                self.prepare(triage=triage)

    def test_private_triage_is_rechecked_and_not_exported(self):
        case=self.prepare();self.review(case)
        self.assertEqual(self.store.case(self.task['task_id'],case['case_id'])['triage'],
                         dict(category='instruction',evidence_ids=self.evidence_ids))
        self.export(case)
        raw=(self.output/'case.json').read_text()
        self.assertNotIn('triage',raw)
        self.assertNotIn(self.evidence_ids[0],raw)
        path=self.store.root/'tasks'/self.task['task_id']/(case['case_id']+'.json')
        row=json.loads(path.read_text());row['triage']['category']='environment';path.write_text(json.dumps(row))
        with self.assertRaisesRegex(InvalidEvent,'triage_environment'):self.export(case,self.output/'second.json')
        del row['triage'];path.write_text(json.dumps(row))
        with self.assertRaisesRegex(InvalidEvent,'case_triage'):self.review(case)

    def test_exact_export_boundaries_and_case_alias_when_supported(self):
        case=self.prepare();self.review(case)
        with self.assertRaisesRegex(UnsafeStore,'export_path$'):self.export(case,Path('relative.json'))
        with self.assertRaisesRegex(UnsafeStore,'export_private_store'):
            self.export(case,self.store.root/'not-a-record.json')
        alias=self.store.root.parent/'OBSERVATIONS'
        if alias.exists() and alias.samefile(self.store.root):
            with self.assertRaisesRegex(UnsafeStore,'export_private_store'):
                self.export(case,alias/'alias.json')
        link=self.home/'link';link.symlink_to(self.output)
        with self.assertRaisesRegex(UnsafeStore,'export_path_symlink'):self.export(case,link/'case.json')
        self.export(case)
        with self.assertRaises(FileExistsError):self.export(case)

    def test_cleanup_failure_does_not_replace_publication_failure(self):
        target=self.output/'existing.json';target.write_text('keep')
        with mock.patch('account.observation.files.os.unlink',side_effect=OSError('cleanup failed')):
            with self.assertRaises(FileExistsError):export_new(target,{'synthetic':True})
        self.assertEqual(target.read_text(),'keep')
