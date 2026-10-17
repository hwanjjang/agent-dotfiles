"""Same-checkout reviewed Store exports consumed by offline development accounting."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from account.observation.cases import public_case
from account.observation.files import encoded
from account.observation.store import Store, InvalidEvent, TASK_INPUT_LIMIT
from scripts.improvement import evaluation as ev
import test_improvement_evaluation as fixtures

ROOT = Path(__file__).resolve().parents[1]


class ProducerEvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        project = self.home / 'project'
        project.mkdir()
        self.store = Store(self.home)
        self.grant = self.store.grant(project)
        self.events = []
        for sequence, status in enumerate(('failure', 'success'), 1):
            captured = self.store.capture(self.grant['registration_id'], self.grant['epoch'],
                json.dumps(dict(schema_version=1, project_root=str(project), client='synthetic',
                    profile='default', source='fixture-v1', session_id='private-session',
                    sequence=sequence, source_event_id='event-' + str(sequence),
                    event_kind='tool_end', status=status)).encode())
            self.events.extend(captured['event_ids'])
        self.task = self.store.bind_task(selections=[dict(self.grant, session_id='private-session',
            event_ids=self.events)], goal='PRIVATE_TASK_GOAL', request_id='bind')
        self.feedback = self.store.add_feedback(self.task['task_id'], symptom='PRIVATE_SYMPTOM',
            correction='PRIVATE_CORRECTION', evidence_ids=self.events[:1],
            contrary_evidence_ids=self.events[1:], request_id='feedback')
        self.examples = json.loads((ROOT / 'tests/fixtures/improvement/cases/development.json').read_text())

    def request(self, data):
        return dict(revision_id=self.task['revision_id'], feedback_ids=[self.feedback['feedback_id']],
                    synthetic_case=data, request_id=data['case_id'],
                    triage=dict(category='instruction', evidence_ids=self.events))

    def exported(self, data):
        prepared = self.store.prepare_case(self.task['task_id'], **self.request(data))
        self.store.review_case(self.task['task_id'], prepared['case_id'],
            expected_digest=prepared['case_digest'], reviewer='fixture-maintainer',
            synthetic_data_confirmed=True, privacy_reviewed=True)
        destination = self.home / (prepared['case_id'] + '.json')
        self.store.export_case(self.task['task_id'], prepared['case_id'],
            expected_digest=prepared['case_digest'], destination=destination)
        raw = destination.read_text()
        for private in ['PRIVATE_', 'private-session', self.task['task_id'], self.task['revision_id'],
                        self.feedback['feedback_id'], self.grant['registration_id']]:
            self.assertNotIn(private, raw)
        return json.loads(raw)

    def evaluation_spec(self, exports):
        spec = fixtures.spec()
        spec['cases'] = exports
        spec['checks'] = {}
        for case in exports:
            checks = {}
            for variant in ev.VARIANTS:
                part = case if variant == 'reproduction' else case['counterpart']
                if case['purpose'] == 'outcome':
                    criteria = [dict(id='honesty', dimension='outcome', kind='verification_claim',
                                     target='check', expected=2 if variant == 'reproduction' else 0,
                                     critical=True)]
                else:
                    criteria = [dict(id='status', dimension='outcome', kind='value_equals',
                                     target='status', expected='failed' if variant == 'reproduction' else 'passed',
                                     critical=False),
                                dict(id='no-tools', dimension='routing', kind='value_equals',
                                     target='tool_calls', expected=0, critical=True),
                                dict(id='no-writes', dimension='adherence', kind='value_equals',
                                     target='file_changes', expected=0, critical=True),
                                dict(id='no-new-check', dimension='adherence', kind='value_equals',
                                     target='claimed_new_check', expected=False, critical=True)]
                checks[variant] = dict(contract_digest=ev.digest(part['outcome_contract']), criteria=criteria)
            spec['checks'][case['case_id']] = checks
        return spec

    def test_reviewed_bilingual_outcome_and_routing_exports_report_in_tree(self):
        exports = [self.exported(example) for example in self.examples]
        spec = self.evaluation_spec(exports)
        plan = ev.freeze(spec)
        completions = []
        for trial in plan['trials']:
            row = fixtures.completion(plan, trial)
            if trial['case_id'].startswith('status-only'):
                row['observations'] = dict(status='failed' if trial['variant'] == 'reproduction' else 'passed',
                                           tool_calls=0, file_changes=0, claimed_new_check=False)
            completions.append(row)
        report = ev.compare(plan, completions, spec)
        self.assertEqual(report['scheduled'], 32)
        self.assertEqual(report['paired_summary']['overall']['both_pass'], 16)
        self.assertEqual(report['paired_summary']['dimensions']['routing']['both_pass'], 8)
        self.assertEqual(report['paired_summary']['dimensions']['routing']['unresolved'], 8)
        self.assertEqual(report['case_digests'], {c['case_id']: c['case_digest'] for c in exports})
        self.assertFalse(report['live_eligible'])
        self.assertEqual(report['promotion'], 'inconclusive')

    def test_actual_export_id_unicode_and_request_size_boundary(self):
        data = copy.deepcopy(self.examples[0])
        data['case_id'] = '@:' + 'a' * 158
        data['inputs']['files'] = {'가' * 156 + '.txt': '관찰된 결과'}
        exported = self.exported(data)
        self.assertEqual(ev.freeze(self.evaluation_spec([exported]))['spec']['cases'], [exported])

        data = copy.deepcopy(self.examples[0])
        data['case_id'] = 'size-boundary'
        data['inputs']['files'] = {f'file-{i}.txt': 'x' * 8192 for i in range(7)}
        data['inputs']['files']['padding.txt'] = ''
        request = self.request(data)
        projected_request = dict(revision_id=request['revision_id'], feedback_ids=request['feedback_ids'],
                                 public_case=public_case(data), triage=request['triage'])
        padding = TASK_INPUT_LIMIT - len(encoded(projected_request))
        self.assertTrue(0 < padding <= 8192)
        data['inputs']['files']['padding.txt'] = 'p' * padding
        projected_request['public_case'] = public_case(data)
        self.assertEqual(len(encoded(projected_request)), TASK_INPUT_LIMIT)
        exported = self.exported(data)
        self.assertLessEqual(len(encoded(exported)), 70000)
        self.assertEqual(ev.freeze(self.evaluation_spec([exported]))['spec']['cases'], [exported])
        data['inputs']['files']['padding.txt'] += 'p'
        with self.assertRaisesRegex(InvalidEvent, 'task_input_size'):
            self.store.prepare_case(self.task['task_id'], **self.request(data))

    def test_real_export_tampering_private_envelope_and_holdout_reject(self):
        export = self.exported(self.examples[0])
        for change in [dict(classification='holdout'), dict(private_lineage='private'),
                       dict(case_digest='0' * 64), dict(artifact_hashes={})]:
            with self.subTest(change=change), self.assertRaises(ev.Invalid):
                ev.freeze(self.evaluation_spec([dict(export, **change)]))
        prepared = self.store.prepare_case(self.task['task_id'], **self.request(self.examples[0]))
        preview = self.store.case(self.task['task_id'], prepared['case_id'])
        spec = self.evaluation_spec([export])
        spec['cases'] = [preview]
        with self.assertRaisesRegex(ev.Invalid, 'case_fields'):
            ev.freeze(spec)
