"""Offline authority regressions, portable beside the installed validator."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sdlc_state as s

def reviewer():
    return dict(author_provider='openai', provider='anthropic', author_account='fixture-builder',
                account='fixture-reviewer', model='offline-model', context_id='review-context',
                builder_context_id='build-context', independent=True,
                model_selection_source='offline catalog fixture', model_selection_time='2026-10-03',
                latest_ga_model_verified=True, requested_effort='high', effort='high',
                effort_verified=True, requested_mode='auto', mode='auto', mode_verified=True,
                reviewer_slot=1, unavailable_reviewers=[])



class EffortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = s.initialize(self.root, 'effort', 'implementation', 'non-executable', 'pre-merge', ['AC1'])

    def ref(self, name, value, kind):
        path = self.root / name
        path.write_text(json.dumps(value))
        return dict(kind=kind, path=name, sha256=s.digest(path))

    def authority(self, **changes):
        source = self.ref('user.json', {'instruction': 'Offline fixture: AK explicitly selects high for effort'}, 'user-instruction')
        data = dict(task_id='effort', authorized_by='AK', explicit=True, effort='high', source=source)
        data.update(changes)
        ref = self.ref('effort.json', data, 'reviewer-effort-authority')
        self.state['stages']['intent'].update(status='complete', history=[dict(receipt=dict(decision='PROCEED', outputs=[ref]))])
        return ref

    def check(self, config):
        effort, authority = s.reviewer_effort_authority(self.root, self.state)
        s.validate_reviewer_configuration(config, True, effort, authority)

    def legacy(self):
        # A task initialized before the high default records no reviewer_effort_default.
        self.state.pop('reviewer_effort_default', None)

    def test_new_task_records_high_default(self):
        self.assertEqual(self.state.get('reviewer_effort_default'), 'high')
        self.assertEqual(s.reviewer_effort_authority(self.root, self.state), ('high', None))

    def test_new_task_expects_high(self):
        self.check(dict(reviewer(), requested_effort='high', effort='high'))
        with self.assertRaises(s.GateError):
            self.check(dict(reviewer(), requested_effort='medium', effort='medium'))

    def test_legacy_task_keeps_medium(self):
        self.legacy()
        self.check(dict(reviewer(), requested_effort='medium', effort='medium'))
        with self.assertRaises(s.GateError):
            self.check(dict(reviewer(), requested_effort='high', effort='high'))

    def test_authority_overrides_default_on_new_and_legacy(self):
        for legacy in (False, True):
            for effort in ('low', 'medium', 'high'):
                with self.subTest(legacy=legacy, effort=effort):
                    if legacy:
                        self.legacy()
                    ref = self.authority(effort=effort)
                    self.check(dict(reviewer(), requested_effort=effort, effort=effort, reviewer_effort_authority=ref))

    def test_only_the_high_default_can_be_recorded(self):
        for value, effort in (('low', 'low'), ('medium', 'medium'), (None, 'medium'), (['high'], 'high')):
            self.state['reviewer_effort_default'] = value
            with self.subTest(value=value), self.assertRaises(s.GateError):
                self.check(dict(reviewer(), requested_effort=effort, effort=effort))

    def test_default_and_explicit_high(self):
        self.check(reviewer())
        ref = self.authority()
        self.check(dict(reviewer(), requested_effort='high', effort='high', reviewer_effort_authority=ref))

    def test_shared_reviewer_uses_high_once(self):
        for legacy in (False, True):
            if legacy:
                self.legacy()
            for provider, role in [('xai', 'grok'), ('grok', 'grok'),
                                   ('google', 'gemini'), ('gemini', 'gemini')]:
                with self.subTest(legacy=legacy, provider=provider):
                    shared = dict(reviewer(), provider=provider, shared_optional_review=role,
                                  requested_effort='high', effort='high')
                    self.check(shared)
                    with self.assertRaises(s.GateError):
                        self.check(dict(shared, requested_effort='medium', effort='medium'))
        # Old receipts are not retroactively reclassified as shared reviews.
        self.check(dict(reviewer(), provider='xai', requested_effort='medium', effort='medium'))

    def test_shared_role_requires_matching_provider(self):
        for provider, role in [('anthropic', 'grok'), ('xai', 'gemini'),
                               ('google', 'grok'), ('antigravity', 'gemini'),
                               ('xai', 'unknown'), ('xai', ['grok'])]:
            with self.subTest(provider=provider, role=role), self.assertRaises(s.GateError):
                self.check(dict(reviewer(), provider=provider, shared_optional_review=role))

    def test_shared_review_honors_explicit_effort_and_existing_gates(self):
        authority = self.authority(effort='low')
        shared = dict(reviewer(), provider='xai', shared_optional_review='grok',
                      requested_effort='low', effort='low', reviewer_effort_authority=authority,
                      read_only_verified=True, read_only_evidence='Offline tool/isolation fixture')
        self.check(shared)
        for change in ({'requested_effort':'high', 'effort':'high'},
                       {'effort_verified':False}, {'latest_ga_model_verified':False},
                       {'context_id':'build-context'}, {'read_only_required':True, 'read_only_verified':False},
                       {'author_provider':'grok'}, {'reviewer_slot':2}):
            with self.subTest(change=change), self.assertRaises(s.GateError):
                self.check(dict(shared, **change))

    def test_review_cannot_grant_or_replace_authority(self):
        # Each review asks for the effort the task's default does not give it.
        for legacy, effort in ((False, 'medium'), (True, 'high')):
            if legacy:
                self.legacy()
            for extra in ({}, {'authorized_effort':effort}, {'expected_effort':effort}, {'effort_authorized':True}):
                with self.subTest(legacy=legacy, extra=extra), self.assertRaises(s.GateError):
                    self.check(dict(reviewer(), requested_effort=effort, effort=effort, **extra))
        ref = self.authority()
        with self.assertRaises(s.GateError):
            self.check(dict(reviewer(), requested_effort='high', effort='high', reviewer_effort_authority=dict(ref, path='other.json')))

    def test_invalid_authority_and_source(self):
        for changes in ({'task_id':'other'}, {'authorized_by':'reviewer'}, {'explicit':False}, {'effort':'invented'},
                        {'source':dict(kind='commentary', path='user.json', sha256='0'*64)},
                        {'source':dict(kind='user-instruction', path='../escape', sha256='0'*64)}):
            self.authority(**changes)
            with self.subTest(changes=changes), self.assertRaises(s.GateError): self.check(reviewer())
        self.authority()
        (self.root/'user.json').write_text('changed')
        with self.assertRaises(s.GateError): self.check(reviewer())
        self.authority()
        (self.root/'user.json').unlink()
        with self.assertRaises(s.GateError): self.check(reviewer())
        self.authority()
        (self.root/'effort.json').write_text('{"effort": "ultra"}')
        with self.assertRaises(s.GateError): self.check(reviewer())
        self.authority()
        self.state['stages']['intent']['history'][-1]['receipt']['outputs'] *= 2
        with self.assertRaises(s.GateError): self.check(reviewer())

    def test_malformed_authority(self):
        for value in ([], {}, dict(task_id='effort', authorized_by='AK', explicit=True,
                                   effort='high', source=None),
                      dict(task_id='effort', authorized_by='AK', explicit=True, effort='high',
                           source=dict(kind='user-instruction', path='user.json', sha256=None))):
            ref = self.ref('malformed.json', value, 'reviewer-effort-authority')
            self.state['stages']['intent'].update(status='complete', history=[dict(receipt=dict(decision='PROCEED', outputs=[ref]))])
            with self.subTest(value=value), self.assertRaises(s.GateError): self.check(reviewer())

    def test_legacy_verifier_readiness_uses_same_authority(self):
        self.authority()
        self.state.pop('review_workflow')
        config = dict(reviewer(), requested_effort='high', effort='high')
        review = dict(config, head='head', base='base')
        self.state['stages']['pr-review']['history'] = [dict(receipt=dict(candidate='candidate', review=review))]
        self.state['stages']['self-verification']['history'] = [dict(receipt=dict(candidate='candidate'))]
        self.state['stages']['independent-verification']['history'] = [dict(receipt=dict(candidate='candidate', verifier=dict(
            configuration=config, context_id=config['context_id'], builder_context_id=config['builder_context_id'])))]
        authority = json.loads((Path(s.__file__).parent.parent/'assets/pre-merge-authority.json').read_text())
        authority.update(task_id='effort', repository='offline/repo', source='Offline fixture',
            accounts=[dict(id=config['author_account'],provider='openai'),dict(id=config['account'],provider='anthropic')])
        gate = json.loads((Path(s.__file__).parent.parent/'assets/merge-ready.json').read_text())
        for key in ('merge_ready','push_verified','pr_verified','mergeable','required_ci_passed',
                    'protections_satisfied','human_requests_resolved','remote_state_verified'):
            gate[key]=True
        gate.update(head='head', base='base', candidate='candidate', repository='offline/repo',
            pr_url='https://example.test/offline/pr', authority_source='Offline fixture', checked_at='2026-10-03',
            remote_record='offline-record', production_trigger='none',
            authority=self.ref('premerge.json',authority,'pre-merge-authority'),
            evidence=[self.ref('observation.json',{'fixture':'offline only'},'observation')])
        s.validate_premerge_readiness(self.root,self.state,gate)
        old=copy.deepcopy(self.state)
        for change in ({'effort':'medium'},{'requested_effort':'medium'},{'effort_verified':False},
                       {'account':'unapproved-account'}):
            self.state['stages']['independent-verification']['history'][-1]['receipt']['verifier']['configuration']=dict(config,**change)
            with self.subTest(change=change), self.assertRaises(s.GateError):
                s.validate_premerge_readiness(self.root,self.state,gate)
        self.state=old

    def test_observation_and_unrelated_configuration(self):
        self.authority()
        valid = dict(reviewer(), requested_effort='high', effort='high')
        for change in ({'effort':'medium'}, {'requested_effort':'medium'}, {'effort_verified':False},
                       {'latest_ga_model_verified':False}, {'context_id':'build-context'}, {'provider':'openai'},
                       {'account':''},
                       {'reviewer_slot':3, 'provider':'openai', 'unavailable_reviewers':[]}):
            with self.subTest(change=change), self.assertRaises(s.GateError): self.check(dict(valid, **change))

    def test_mode_optional_with_verified_read_only_boundary(self):
        for mode, requested in [(None, None), ('default', 'auto'), ('plan', None)]:
            with self.subTest(mode=mode):
                self.check(dict(reviewer(), mode=mode, requested_mode=requested, mode_verified=False,
                                read_only_verified=True,
                                read_only_evidence='Observed native read-only tools and immutable source snapshot'))
        config = reviewer()
        for key in ('mode', 'requested_mode', 'mode_verified'):
            config.pop(key)
        self.check(dict(config, read_only_verified=True, read_only_evidence='Observed read-only boundary'))

    def test_read_only_claim_requires_evidence_and_preserves_other_gates(self):
        self.check(dict(reviewer(), read_only_verified=False, read_only_evidence=''))
        self.check(dict(reviewer(), mode=None, requested_mode=None, mode_verified=False))
        for changes in ({'read_only_required':True, 'read_only_verified':False},
                        {'read_only_verified':True, 'read_only_evidence':''}):
            with self.subTest(changes=changes), self.assertRaises(s.GateError):
                self.check(dict(reviewer(), **changes))
        readonly = dict(reviewer(), mode='default', requested_mode='auto', mode_verified=False,
                        read_only_verified=True, read_only_evidence='Observed source isolation and read-only toolset')
        self.check(readonly)
        for changes in ({'effort_verified':False}, {'provider':'openai'}, {'context_id':'build-context'},
                        {'latest_ga_model_verified':False}):
            with self.subTest(changes=changes), self.assertRaises(s.GateError):
                self.check(dict(readonly, **changes))

    def test_latest_intent_and_history_preserved(self):
        ref = self.authority(effort='medium')
        medium = dict(reviewer(), requested_effort='medium', effort='medium')
        old = copy.deepcopy(self.state)
        self.check(medium)
        self.assertEqual(self.state, old)
        self.state['stages']['intent']['history'].append(dict(receipt=dict(decision='PROCEED', outputs=[])))
        self.check(reviewer())
        with self.assertRaises(s.GateError): self.check(medium)
        self.state['stages']['intent']['history'].pop()
        self.state['stages']['intent']['status']='stale'
        with self.assertRaises(s.GateError): self.check(dict(medium, reviewer_effort_authority=ref))


if __name__ == '__main__':
    unittest.main()
