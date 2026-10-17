"""Regression tests for the PR workflow; run directly with Python's unittest."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

import sdlc_state as s


def reviewer(slot=1, provider='anthropic'):
    return dict(author_provider='openai', provider=provider, author_account='builder',
                account='reviewer', model='fixture-model', context_id='review-context',
                builder_context_id='build-context', independent=True,
                model_selection_source='fixture catalog', model_selection_time='2026-10-01',
                latest_ga_model_verified=True, requested_effort='medium', effort='medium',
                effort_verified=True, requested_mode='auto', mode='auto', mode_verified=True,
                reviewer_slot=slot, unavailable_reviewers=[
                    dict(slot=i, provider='anthropic', account=f'reviewer-{i}',
                         reason='Required check could not run', evidence=f'observation-{i}')
                    for i in range(1, slot)])


def finding(fid='R1', classification='required', resolved=True):
    return dict(id=fid, classification=classification, severity='MEDIUM', category='Bug',
                location='app.py:1', finding='Expected result missing', evidence='Reproduction',
                impact='Wrong result', verification='Scenario S1', requirement='AC1',
                confidence='High', disposition='Applied', author_action='applied',
                author_response='Fixed and tested', resolved=resolved,
                reviewer_resolution='Confirmed fix' if resolved else '')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def state(self, endpoint='pre-merge'):
        return s.initialize(self.root, 'task', 'implementation', 'non-executable', endpoint, ['AC1'])

    def ref(self, name, value, kind=None):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        return dict(kind=kind or name, path=name, sha256=s.digest(path))

    def test_pr_route_omits_independent_verification(self):
        state = self.state()
        self.assertFalse(state['stages']['independent-verification']['applicable'])
        self.assertEqual(state['review_workflow'], '2026-10-01')

    def test_local_route_does_not_gain_new_management(self):
        state = self.state('local')
        self.assertNotIn('review_workflow', state)

    def test_first_and_second_reviewers_must_differ_from_builder(self):
        for slot in (1, 2):
            with self.subTest(slot=slot):
                s.validate_reviewer_configuration(reviewer(slot), revised=True)
                with self.assertRaises(s.GateError):
                    s.validate_reviewer_configuration(reviewer(slot, 'openai'), revised=True)

    def test_fallback_requires_two_prior_unavailable_reviewers(self):
        config = reviewer(3, 'codex-team')
        s.validate_reviewer_configuration(config, revised=True)
        config['unavailable_reviewers'].pop()
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)

    def test_fallback_cannot_use_builder_context_or_provider_alias_trick(self):
        config = reviewer(3, 'openai')
        config['context_id'] = config['builder_context_id']
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)
        config = reviewer(3, 'openai')
        config['unavailable_reviewers'][0]['provider'] = 'codex-personal'
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)

    def test_second_reviewer_requires_recorded_reason_and_evidence(self):
        config = reviewer(2)
        config['unavailable_reviewers'][0]['evidence'] = ''
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(config, revised=True)

    def test_required_finding_cannot_be_left_unresolved(self):
        review = dict(reviewer(), head='head', base='base', candidate='candidate',
                      record_url='https://example.test/review', record_id='1', verdict='PASS',
                      findings=[finding(resolved=False)], author_changes_remaining=[])
        with self.assertRaises(s.GateError):
            s.validate_review(review, 'candidate', revised=True)
        review['findings'][0] = finding()
        s.validate_review(review, 'candidate', revised=True)

    def test_unselected_recommendation_needs_no_followup_record(self):
        f = finding(classification='recommended', resolved=False)
        f.update(author_action='not-selected', author_response='Outside this change',
                 disposition='Not selected')
        review = dict(reviewer(), head='head', base='base', candidate='candidate',
                      record_url='https://example.test/review', record_id='1', verdict='PASS',
                      findings=[f], author_changes_remaining=[])
        s.validate_review(review, 'candidate', revised=True)

    def test_handoff_cannot_drop_findings_or_silently_downgrade_required(self):
        state = self.state()
        previous = finding(resolved=False)
        state['stages']['pr-review']['history'] = [dict(receipt=dict(review=dict(findings=[previous])))]
        with self.assertRaises(s.GateError):
            s.validate_review_handoff(state, dict(findings=[]))
        downgraded = finding(classification='recommended', resolved=False)
        with self.assertRaises(s.GateError):
            s.validate_review_handoff(state, dict(findings=[downgraded]))
        s.validate_review_handoff(state, dict(findings=[finding()]))

    def upgraded_legacy_review(self, fid=None, severity='HIGH', disposition='Must Fix'):
        state = self.state()
        state.pop('review_workflow')
        old = finding(resolved=False)
        old.pop('classification')
        if fid is None:
            old.pop('id')
        else:
            old['id'] = fid
        old.update(severity=severity, disposition=disposition)
        stage = state['stages']['pr-review']
        stage.update(status='blocked', iterations_started=1,
                     history=[dict(iteration=1, receipt=dict(decision='BLOCKED', review=dict(findings=[old])))])
        s.atomic_json(s.state_path(self.root, 'task'), state)
        upgraded = s.upgrade_review_workflow(self.root, 'task', 'AK workflow adoption')
        self.assertEqual(upgraded['stages']['pr-review']['history'], stage['history'])
        self.assertEqual(upgraded['stages']['pr-review']['iterations_started'], 1)
        return upgraded

    def test_legacy_mapping_requires_actual_carried_finding(self):
        state = self.upgraded_legacy_review()
        for mapping in ('mapped', {}, {'1:1': 'OLD-1'}):
            with self.subTest(mapping=mapping), self.assertRaises(s.GateError):
                s.validate_review_handoff(state, dict(findings=[], legacy_finding_mapping=mapping))

    def test_legacy_required_cannot_be_silently_downgraded(self):
        for severity, disposition in (('HIGH', 'Advisory'), ('MEDIUM', 'Must Fix')):
            with self.subTest(severity=severity, disposition=disposition):
                # Use separate task fixtures for the two legacy Required definitions.
                if s.state_path(self.root, 'task').exists():
                    s.state_path(self.root, 'task').unlink()
                state = self.upgraded_legacy_review('OLD-1', severity, disposition)
                downgraded = finding('OLD-1', 'recommended', resolved=False)
                downgraded.update(author_action='not-selected', author_response='No change selected')
                review = dict(reviewer(), head='head', base='base', candidate='candidate',
                              record_url='https://example.test/review', record_id='1', verdict='PASS',
                              findings=[downgraded], author_changes_remaining=[])
                s.validate_review(review, 'candidate', revised=True)
                with self.assertRaises(s.GateError):
                    s.validate_review_handoff(state, review)
                downgraded['reviewer_resolution'] = 'Reproduction disproved the old severity; advisory only'
                s.validate_review_handoff(state, review)

    def test_mapped_legacy_required_needs_reviewer_resolution(self):
        state = self.upgraded_legacy_review()
        current = finding('OLD-1', resolved=False)
        review = dict(reviewer(), head='head', base='base', candidate='candidate',
                      record_url='https://example.test/review', record_id='1', verdict='PASS',
                      findings=[current], author_changes_remaining=[], legacy_finding_mapping={'1:1': 'OLD-1'})
        s.validate_review_handoff(state, review)
        with self.assertRaises(s.GateError):
            s.validate_review(review, 'candidate', revised=True)
        current.update(resolved=True, reviewer_resolution='Reproduced fix and regression checks')
        s.validate_review_handoff(state, review)
        s.validate_review(review, 'candidate', revised=True)
        state['stages']['pr-review']['history'].append(dict(iteration=2, receipt=dict(review=copy.deepcopy(review))))
        # Later replacements must retain both the mapped ID and its mapping.
        review['legacy_finding_mapping'] = {'1:1': 'NEW-1'}
        review['findings'].append(finding('NEW-1'))
        with self.assertRaises(s.GateError):
            s.validate_review_handoff(state, review)

    def test_planning_requires_user_scenarios_and_acceptance_mapping(self):
        data = dict(scenarios=[dict(id='S1', user='Reader', goal='Read results',
                    prerequisites='Document available', steps=['Open document'],
                    expected='Results visible', failure='Missing document is reported', criteria=['AC1'])])
        s.validate_user_scenarios(data, ['AC1'])
        data['scenarios'][0]['steps'] = []
        with self.assertRaises(s.GateError):
            s.validate_user_scenarios(data, ['AC1'])

    def test_feature_manual_requires_pdf_source_and_screenshot_references(self):
        data = dict(checked=True, summary='User guide updated', new_feature=True,
                    ux_ui_changed=False, updates=[], manual=None)
        with self.assertRaises(s.GateError):
            s.validate_documentation(self.root, data)
        data['manual'] = dict(source=self.ref('manual.md', b'User instructions', 'manual-source'),
            pdf=self.ref('manual.pdf', b'%PDF-1.7\nfixture', 'manual-pdf'),
            screenshots=[self.ref('screen.png', b'fixture image', 'manual-screenshot')],
            render_checked=True, summary='Rendered and inspected all pages')
        s.validate_documentation(self.root, data)
        data['manual']['screenshots'] = []
        with self.assertRaises(s.GateError):
            s.validate_documentation(self.root, data)

    def test_nonfeature_documentation_audit_needs_no_product_manual(self):
        s.validate_documentation(self.root, dict(checked=True, summary='No user flow changed',
            new_feature=False, ux_ui_changed=False, updates=[], manual=None))

    def test_upgrade_preserves_history_and_counters(self):
        state = self.state()
        state.pop('review_workflow')
        stage = state['stages']['independent-verification']
        stage.update(applicable=True, status='blocked', reason='Old verifier unavailable',
                     iterations_started=2, history=[dict(iteration=i, receipt=dict(decision='BLOCKED')) for i in (1, 2)])
        s.atomic_json(s.state_path(self.root, 'task'), state)
        upgraded = s.upgrade_review_workflow(self.root, 'task', 'AK request 2026-10-01')
        self.assertFalse(upgraded['stages']['independent-verification']['applicable'])
        self.assertEqual(upgraded['stages']['independent-verification']['history'], stage['history'])
        self.assertEqual(upgraded['stages']['independent-verification']['iterations_started'], 2)

    def test_legacy_reviewer_rules_remain_available_for_history(self):
        s.validate_reviewer_configuration(reviewer())
        with self.assertRaises(s.GateError):
            s.validate_reviewer_configuration(reviewer(3, 'openai'))

    def test_upgrade_rejects_running_attempt_and_preserves_budget(self):
        state = self.state()
        state.pop('review_workflow')
        s.atomic_json(s.state_path(self.root, 'task'), state)
        s.begin(self.root, 'task', 'triage', 'Initial attempt')
        with self.assertRaises(s.GateError):
            s.upgrade_review_workflow(self.root, 'task', 'AK instruction')
        for i in range(1, 11):
            if i > 1: s.begin(self.root, 'task', 'triage', 'Retry with recorded evidence')
            s.finish(self.root, 'task', 'triage', dict(iteration=i, decision='BLOCKED',
                reason='Fixture unavailable', authority_source='fixture', candidate='c', next_action='Reassess'))
        s.upgrade_review_workflow(self.root, 'task', 'AK instruction')
        with self.assertRaisesRegex(s.GateError, 'iteration-limit-reached'):
            s.begin(self.root, 'task', 'triage', 'Forbidden attempt 11')

    def cli(self, command, *args, success=True):
        result = subprocess.run([sys.executable, str(Path(s.__file__)), command,
            '--root', str(self.root), '--task', 'task', *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0 if success else 2, result.stdout + result.stderr)
        return json.loads(result.stdout if success else result.stderr)

    def test_cli_premerge_smoke_without_independent_verification(self):
        self.cli('init', '--mode', 'implementation', '--change-kind', 'non-executable',
                 '--endpoint', 'pre-merge', '--criteria', 'AC1')
        self.cli('skip', '--stage', 'design', '--reason', 'No structural change in fixture')
        self.cli('skip', '--stage', 'test-design', '--reason', 'Content-only fixture')
        self.cli('begin', '--stage', 'independent-verification', '--objective', 'Excluded', success=False)

        def receipt(stage, extra_outputs=(), **fields):
            state = s.load(self.root, 'task')
            number = state['stages'][stage]['iterations_started']
            refs = [self.ref(f'{stage}-{number}.txt', b'Fixture stage evidence', stage), *extra_outputs]
            return dict(iteration=number, decision='PROCEED', reason='Fixture evidence assessed',
                authority_source='test fixture only', candidate='candidate', next_action='Next fixture stage',
                inputs=s.required_inputs(state, stage), outputs=refs,
                assessment=dict(assessor='test', summary='Fixture checked', criteria=['AC1']), **fields)

        def finish(stage, value, success=True):
            self.ref('receipt.json', value)
            self.cli('finish', '--stage', stage, '--receipt', str(self.root/'receipt.json'), success=success)

        for stage in ('triage', 'intent', 'investigation', 'spec', 'plan', 'build', 'self-verification'):
            self.cli('begin', '--stage', stage, '--objective', 'Exercise CLI contract')
            extra = []
            if stage == 'plan':
                finish(stage, receipt(stage), success=False)
                extra.append(self.ref('scenarios.json', dict(scenarios=[dict(id='S1', user='Reader',
                    goal='Read fixture', prerequisites='Fixture available', steps=['Open fixture'],
                    expected='Text visible', failure='Missing text reported', criteria=['AC1'])]), 'user-scenarios'))
            if stage == 'build':
                extra.extend([self.ref('change.diff', b'+Updated fixture', 'change-record'),
                              self.ref('source.md', b'Updated fixture', 'candidate-source')])
            if stage == 'self-verification':
                log = self.ref('content-check.txt', b'Fixture content checked', 'execution-log')
                data = dict(candidate='candidate', scenarios=[], not_applicable_reason='Content-only fixture',
                    runs=[dict(id='doc1', phase='document', candidate='candidate', command='fixture content check',
                        environment='isolated temp directory', observed='Fixture text matches', evidence=log['path'],
                        exit_code=0, status='passed')])
                extra.extend([log, self.ref('results.json', data, 'test-results'),
                    self.ref('docs.json', dict(checked=True, summary='No product/manual change in fixture',
                        new_feature=False, ux_ui_changed=False, updates=[], manual=None), 'documentation')])
            finish(stage, receipt(stage, extra))

        self.cli('validate', '--checkpoint', 'pre-commit')
        self.cli('begin', '--stage', 'pr-review', '--objective', 'First reviewer unavailable after finding')
        blocked = receipt('pr-review', review=dict(findings=[finding(resolved=False)]))
        blocked.update(decision='BLOCKED', reason='Reviewer cannot complete required check')
        finish('pr-review', blocked)
        self.cli('begin', '--stage', 'pr-review', '--objective', 'Independent fallback reviews carried finding')
        review = dict(reviewer(3, 'openai'), candidate='candidate', head='head', base='base', verdict='PASS',
                      record_url='https://example.test/pr/1#review', record_id='fixture-review',
                      mode='default', requested_mode='auto', mode_verified=False,
                      read_only_verified=True, read_only_evidence='Observed isolated read-only fixture execution',
                      findings=[], author_changes_remaining=[])
        finish('pr-review', receipt('pr-review', review=review), success=False)
        review['findings'] = [finding()]
        finish('pr-review', receipt('pr-review', review=review))
        self.cli('begin', '--stage', 'correction', '--objective', 'Confirm finding disposition')
        finish('correction', receipt('correction'))

        authority = json.loads((Path(s.__file__).parent.parent/'assets/pre-merge-authority.json').read_text())
        authority.update(task_id='task', repository='fixture/repo', source='Test fixture authority',
            accounts=[dict(id='builder', provider='openai'), dict(id='reviewer', provider='openai')])
        gate = json.loads((Path(s.__file__).parent.parent/'assets/merge-ready.json').read_text())
        for key in ('merge_ready', 'push_verified', 'pr_verified', 'mergeable', 'required_ci_passed',
                    'protections_satisfied', 'human_requests_resolved', 'remote_state_verified'):
            gate[key] = True
        gate.update(head='head', base='base', candidate='candidate', repository='fixture/repo',
            pr_url='https://example.test/pr/1', authority_source='Fixture only', checked_at='2026-10-01',
            remote_record='fixture-observation', production_trigger='none',
            authority=self.ref('authority.json', authority, 'pre-merge-authority'),
            evidence=[self.ref('observation.txt', b'Test fixture observation only', 'observation')])
        gate_ref = self.ref('ready.json', gate, 'merge-ready')
        self.cli('validate', '--checkpoint', 'pre-merge', '--gate', str(self.root/'ready.json'))
        for key in ('merge_authorized', 'auto_merge_enabled', 'merge_queue_enqueued'):
            unsafe = copy.deepcopy(gate)
            unsafe[key] = True
            self.ref('unsafe.json', unsafe)
            self.cli('validate', '--checkpoint', 'pre-merge', '--gate', str(self.root/'unsafe.json'), success=False)
        self.cli('begin', '--stage', 'merge', '--objective', 'Forbidden integration', success=False)
        self.cli('begin', '--stage', 'completion', '--objective', 'Final documentation and readiness')
        finish('completion', receipt('completion', [gate_ref]), success=False)
        finish('completion', receipt('completion', [gate_ref], documentation_final_checked=True,
                                     author_changes_remaining=[]))
        self.cli('validate', '--checkpoint', 'completion')
        (self.root/'source.md').write_text('Late unreviewed change')
        self.cli('validate', '--checkpoint', 'completion', success=False)


if __name__ == '__main__':
    unittest.main()
