"""SYNTHETIC selected receipts/clock/journals, real disposable Git and serial gate."""
import copy
import hashlib
import io
import contextlib
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.improvement import heldout, promotion as gate, trial_reservation as reservation
import test_improvement_promotion as native_fixture
from test_trial_admission import RoutedAttempts, save
from test_trial_reservation import SyntheticSchedule
ad, ev = reservation.ad, reservation.ev
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FakeHeldout:
    def __init__(self, execute=True, *, dev_held=False, overlap=None):
        self.base = native_fixture.NativePromotionTests(); self.base.setUp()
        self.root = self.base.root; self.comments = {}; self.source = self.base.source()
        self.author = self.root/'author'; self.author.mkdir()
        self.area = self.root/'private'; self.area.mkdir(mode=0o700)
        self.overlap = overlap
        self.dev = self.schedule('dev',dev_held); self.held = self.schedule('held',True)
        self.pinned = patch.object(ad.p,'PINNED_RUNTIME',self.dev.f.runtime['runtime_digests']); self.pinned.start()
        for s in (self.dev,self.held): reservation.initialize(s.state,s.f.experiment,s.f.spec,s.f.context_path,s.plans)
        self.score(self.dev)
        f = self.held.f; self.pack = self.area/'pack.json'; save(self.pack,{k:f.spec[k] for k in ('cases','checks')})
        self.record = self.area/'manifest.json'; self.preflight = self.area/'preflight.json'
        self.report = self.area/'report.json'; self.exposure = self.area/'exposure.json'
        req=self.area/'requirements.txt';req.write_text('SYNTHETIC requirements only.');req.chmod(0o600)
        cat=self.area/'categories.txt';cat.write_text('SYNTHETIC behavior categories only.');cat.chmod(0o600)
        self.author_receipt=self.area/'author.json'
        save(self.author_receipt,dict(schema_version=1,kind='candidate_author_inputs_v1',context_id='author',
            workspace=str(self.author),candidate_commit=self.source['candidate_commit'],materials=[]))
        self.candidate_anchor=self.anchor(11,'2026-10-18T01:00:00Z',dict(kind='committed_candidate_freeze_v1',source=self.source))
        message='Prepare a fresh held-out pack from these requirements and behavior categories only. Do not inspect candidate patches or author history. Keep cases and answers private; return only pack_id, pack_digest, grader_digest and schedule_digest.\n'+ev.encoded(dict(pack_id='synthetic-pack',pack_path=str(self.pack),requirements=[req.read_text()],behavior_categories=[cat.read_text()])).decode()
        call=self.area/'call.json';returned=self.area/'returned.json';metadata=self.area/'metadata.json';created=self.area/'created.json'
        output=dict(pack_id='synthetic-pack',pack_digest=ev.digest({k:f.spec[k] for k in ('cases','checks')}),
            grader_digest=f.spec['identities']['grader'],schedule_digest=ev.digest(f.experiment['trials']))
        save(call,dict(tool='collaboration.spawn_agent',arguments=dict(task_name='fresh_pack',fork_turns='none',message=message),observed_at='2026-10-18T01:01:00Z'))
        save(returned,dict(tool='collaboration.spawn_agent',agent_id='new-preparer',task_name='fresh_pack',observed_at='2026-10-18T01:03:00Z'))
        save(metadata,output);save(created,dict(agent_id='new-preparer',pack_id='synthetic-pack',pack_digest=output['pack_digest'],observed_at='2026-10-18T01:02:00Z'))
        self.dispatch=self.area/'dispatch.json'
        receipt=dict(schema_version=1,kind='same_host_fork_none_dispatch_v1',purpose='heldout_preparation',
            source=dict(envelope_version='requirements-only-v1',helper_sha256=sha(heldout.__file__)),
            input=dict(requirements=[dict(path=str(req),sha256=sha(req))],behavior_categories=[dict(path=str(cat),sha256=sha(cat))],
                message_sha256=hashlib.sha256(message.encode()).hexdigest(),tool_call_evidence_path=str(call),tool_call_evidence_sha256=sha(call)),
            dispatch=dict(tool='collaboration.spawn_agent',task_name='fresh_pack',fork_turns='none'),
            returned=dict(agent_id='new-preparer',tool_result_evidence_path=str(returned),tool_result_evidence_sha256=sha(returned)),
            output={**output,'metadata_evidence_path':str(metadata),'metadata_evidence_sha256':sha(metadata)},
            chronology=dict(candidate_freeze_anchor=self.candidate_anchor,pack_creation_evidence_path=str(created),pack_creation_evidence_sha256=sha(created)))
        receipt['receipt_digest']=ev.digest(receipt);save(self.dispatch,receipt)
        save(self.exposure,dict(schema_version=1,kind='same_host_exposure_v1',events=[]))
        self.exp=self.area/'experiment.json';self.spec=self.area/'spec.json';save(self.exp,f.experiment);save(self.spec,f.spec)
        self.m=dict(schema_version=1,kind='same_host_heldout_evidence_v1',pack_id='synthetic-pack',repository=str(self.base.repo),
            content=dict(path=str(self.pack),sha256=sha(self.pack),pack_digest=output['pack_digest']),source=self.source,
            experiment=dict(experiment_path=str(self.exp),spec_path=str(self.spec),context_path=str(f.context_path),report_path=str(self.report),attempts=self.refs(self.held)),
            contexts=dict(author=[dict(context_id='author',input_evidence_path=str(self.author_receipt),sha256=sha(self.author_receipt))],
                preparation=dict(context_id='new-preparer',input_evidence_path=str(self.dispatch),sha256=sha(self.dispatch)),
                tasks=[{k:r[k] for k in ('trial_id','attempt_id')} for r in self.refs(self.held)]),
            exposure=dict(path=str(self.exposure)),preflight=dict(path=str(self.preflight)))
        payload=self.freeze_payload();self.m['freeze']=self.anchor(12,'2026-10-18T01:04:00Z',payload)
        self.m['record_digest']=ev.digest(self.m);save(self.record,self.m)
        if execute:
            save(self.preflight,dict(schema_version=1,kind='same_host_preflight_v1',record_digest=self.m['record_digest'],helper_digest=sha(heldout.__file__),
                anchor_digest=ev.digest(self.comments[12]),header_digest=ev.digest(json.loads((self.held.state/reservation.HEADER).read_text())),reserved_initial_turns=0))
            self.score(self.held);self.refresh()

    def schedule(self,name,held):
        overlap = self.overlap
        class Fixed(RoutedAttempts):
            def __init__(self,root):
                super().__init__(root);self.spec['promotion_rule']='quality_gain_v1'
                if held:
                    for c in self.spec['cases']:
                        if name=='held':
                            old=c['case_id']
                            if overlap!='identity':c['case_id']='held-'+old
                            self.spec['checks'][c['case_id']]=self.spec['checks'].pop(old)
                            if overlap!='content':
                                for part in (c,c['counterpart']):part['inputs']['request']+=' Separate synthetic heldout task.'
                        c['classification']='same_host_heldout';c['case_digest']=ev.digest({k:v for k,v in c.items() if k!='case_digest'})
                    self.spec['evaluation_scope']=dict(kind='same_host_heldout',pack_digest=ev.digest({k:self.spec[k] for k in ('cases','checks')}))
        folder=self.root/name;folder.mkdir(mode=0o700)
        with patch('test_trial_reservation.SyntheticAttempts',Fixed): result=SyntheticSchedule(folder)
        for t,saved in zip(result.f.experiment['trials'],result.saved):
            for path in (saved/'records').glob('*-receipt.json'):
                r=json.loads(path.read_text());r['controller_timing']=dict(clock='monotonic_ns',scope='controller_setup_task_cleanup',elapsed_ms=10);save(path,r)
            if t['arm']=='baseline':
                for path in (saved/'records').glob('*.json'):
                    r=json.loads(path.read_text())
                    if path.name.endswith('-collection_result.json'):r['snapshot']['files'][0]['sha256']='f'*64
                    if path.name.endswith('-receipt.json'):r['collection']['snapshot']['files'][0]['sha256']='f'*64
                    save(path,r)
        return result

    def refs(self,s):
        return [dict(trial_id=t['trial_id'],attempt_id='one',attempt_path=str(s.state/t['trial_id']/'one')) for t in s.f.experiment['trials']]

    def score(self,s):
        with patch.object(ad.nt,'run',side_effect=s.run):
            for plan in s.plans: reservation.run_next(s.state,s.f.experiment,s.f.spec,s.f.context_path,plan,Path('/synthetic-not-opened/auth.json'))

    def report_for(self,s):
        ctx=ad.load_context(s.f.experiment,s.f.spec,s.f.context_path);batch=ad.read_attempts(ctx,self.refs(s))
        try:return ev.compare(s.f.experiment,[],s.f.spec,native=batch)
        finally:batch.close()

    def refresh(self): save(self.report,self.report_for(self.held))
    def freeze_payload(self):
        f=self.held.f
        return dict(kind='same_host_heldout_freeze_v1',pack_id='synthetic-pack',pack_digest=ev.digest({k:f.spec[k] for k in ('cases','checks')}),
            experiment_digest=f.experiment['experiment_digest'],schedule_digest=ev.digest(f.experiment['trials']),grader_digest=f.spec['identities']['grader'],
            context_digest=ev.digest(f.context),source=self.source,dispatch_receipt_digest=json.loads(self.dispatch.read_text())['receipt_digest'],
            author_receipt_digests=[sha(self.author_receipt)])
    def anchor(self,number,created,body):
        text=ev.encoded(body).decode();self.comments[number]=dict(id=number,created_at=created,updated_at=created,body=text,issue_url='https://api.github.com/repos/example/public/issues/56')
        return dict(repository='example/public',issue_number=56,comment_id=number,created_at=created,body_sha256=hashlib.sha256(text.encode()).hexdigest())
    def recommend(self):
        path=self.area/'development-report.json';save(path,self.report_for(self.dev));f=self.dev.f
        with patch.object(heldout,'_comment',side_effect=lambda ref:self.comments[ref['comment_id']]):
            return gate.recommend_native(experiment=f.experiment,current_spec=f.spec,context_path=str(f.context_path),attempts=self.refs(self.dev),
                report_path=str(path),repository=str(self.base.repo),baseline_commit=self.source['baseline_commit'],candidate_commit=self.source['candidate_commit'],
                component_roots=self.source['component_roots'],heldout_record_path=str(self.record))
    def close(self): self.pinned.stop();self.base.doCleanups()


class HeldoutTests(unittest.TestCase):
    def setUp(self):self.f=FakeHeldout();self.addCleanup(self.f.close)
    def test_positive_synthetic_conformance_is_bounded_recommendation(self):
        result=self.f.recommend();self.assertEqual(result['recommendation'],'recommend')
        self.assertEqual(result['heldout']['claim'],'not_supplied_to_recorded_author_context_during_comparison')
        self.assertEqual(result['heldout']['unobserved_filesystem_reads'],'unknown')
        for key in ('source_accepted','promotion_eligible','merge_authorized','install_authorized'):self.assertIs(result[key],False)
    def test_remote_body_edit_or_wrong_issue_cannot_qualify(self):
        for key,value in [('body','forged'),('updated_at','2026-10-18T01:05:00Z'),('issue_url','https://api.github.com/repos/example/public/issues/99')]:
            old=self.f.comments[12][key];self.f.comments[12][key]=value
            result=self.f.recommend();self.assertEqual(result['recommendation'],'inconclusive')
            self.assertIn('heldout_anchor_changed',result['reasons']);self.f.comments[12][key]=old
    def test_scoped_development_is_not_development_evidence(self):
        other=FakeHeldout(dev_held=True)
        try:
            result=other.recommend()
            self.assertEqual(result['recommendation'],'reject')
            self.assertIn('development_scope_required',result['reasons'])
        finally:other.close()

    def test_heldout_input_reuse_rejects_but_category_identity_may_repeat(self):
        for overlap in ('identity','content'):
            with self.subTest(overlap=overlap):
                other=FakeHeldout(overlap=overlap)
                try:
                    result=other.recommend()
                    if overlap=='content':
                        self.assertEqual(result['recommendation'],'reject')
                        self.assertIn('heldout_cases_overlap',result['reasons'])
                    else:self.assertEqual(result['recommendation'],'recommend')
                finally:other.close()

    def test_remote_missing_malformed_and_late_changes_are_inconclusive(self):
        old=self.f.comments[12]
        for value in (None,[],{},dict(old,body=None),{k:v for k,v in old.items() if k!='issue_url'}):
            with self.subTest(value=value):
                self.f.comments[12]=value;result=self.f.recommend()
                self.assertEqual(result['recommendation'],'inconclusive')
                self.assertIn('heldout_anchor_changed',result['reasons'])
        self.f.comments[12]=old
        original=heldout._anchor;calls=0
        def late(ref,payload):
            nonlocal calls
            calls+=1
            if calls==4:self.f.comments[12]=dict(old,body='edited during refresh')
            return original(ref,payload)
        with patch.object(heldout,'_anchor',side_effect=late):
            result=self.f.recommend();self.assertEqual(result['recommendation'],'inconclusive')
            self.assertIn('heldout_anchor_changed',result['reasons'])
        self.f.comments[12]=old

    def test_remote_unknown_does_not_erase_independent_development_failure(self):
        for trial,ref in zip(self.f.dev.f.experiment['trials'],self.f.refs(self.f.dev)):
            if trial['arm']=='candidate':
                self.f.dev.f.mutate(ref,'collection_result',lambda row:row['snapshot']['files'][0].update(sha256='f'*64))
                self.f.dev.f.mutate(ref,'receipt',lambda row:row['collection']['snapshot']['files'][0].update(sha256='f'*64))
        original=self.f.comments[12]
        for remote in (None,dict(original,body='edited remote record')):
            self.f.comments[12]=remote;result=self.f.recommend()
            self.assertEqual(result['recommendation'],'reject')
            self.assertIn('critical_violation',result['reasons'])
            self.assertIn('heldout_anchor_changed',result['reasons'])
            self.assertEqual(result['heldout']['status'],'inconclusive')

    def test_malformed_local_anchor_remains_invalid(self):
        self.f.m['freeze']['body_sha256']='0'*64
        self.f.m['record_digest']=ev.digest({k:v for k,v in self.f.m.items() if k!='record_digest'})
        save(self.f.record,self.f.m)
        result=self.f.recommend();self.assertEqual(result['recommendation'],'reject')
        self.assertEqual(result['heldout']['status'],'invalid')

    def test_before_comparison_exposure_is_counted(self):
        for material,status in [('answer','exposed'),('unknown_delivery','inconclusive')]:
            save(self.f.exposure,dict(schema_version=1,kind='same_host_exposure_v1',events=[dict(context_id='author',material=material,phase='before_comparison')]))
            result=self.f.recommend();self.assertEqual(result['recommendation'],'inconclusive')
            self.assertEqual(result['heldout']['status'],status)
            self.assertEqual(result['heldout']['future_classification'],'development_regression')

    def test_known_pack_copy_in_author_materials_is_exposure(self):
        alias=self.f.author/'requirements-copy.json';alias.write_bytes(self.f.pack.read_bytes());alias.chmod(0o600)
        receipt=json.loads(self.f.author_receipt.read_text())
        receipt['materials']=[dict(kind='requirements',path=str(alias),sha256=sha(alias))]
        save(self.f.author_receipt,receipt)
        self.f.m['contexts']['author'][0]['sha256']=sha(self.f.author_receipt)
        self.f.m['record_digest']=ev.digest({k:v for k,v in self.f.m.items() if k!='record_digest'})
        save(self.f.record,self.f.m)
        result=self.f.recommend();self.assertEqual(result['recommendation'],'inconclusive')
        self.assertEqual(result['heldout']['status'],'exposed')
        self.assertEqual(result['heldout']['future_classification'],'development_regression')

    def test_workspace_alias_cannot_hide_pack_containment(self):
        alias=self.f.root/'workspace-alias';alias.symlink_to(self.f.area,target_is_directory=True)
        receipt=json.loads(self.f.author_receipt.read_text());receipt['workspace']=str(alias)
        save(self.f.author_receipt,receipt);m=copy.deepcopy(self.f.m)
        m['contexts']['author'][0]['sha256']=sha(self.f.author_receipt)
        m['record_digest']=ev.digest({k:v for k,v in m.items() if k!='record_digest'});save(self.f.record,m)
        with patch.object(heldout,'_comment',side_effect=lambda ref:self.f.comments[ref['comment_id']]),self.assertRaisesRegex(ValueError,'heldout_author'):
            heldout._prepare(str(self.f.record),self.f.source)

    def test_last_model_observation_cannot_hide_exposure_drift(self):
        original=ad.NativeBatch.observed_models_complete
        def late(batch):
            result=original(batch)
            if batch.context.data.get('execution_root')==str(self.f.held.state):
                self.f.exposure.write_bytes(self.f.exposure.read_bytes()+b' ')
            return result
        with patch.object(ad.NativeBatch,'observed_models_complete',late):
            result=self.f.recommend();self.assertNotEqual(result['recommendation'],'recommend')

    def test_source_is_rechecked_after_synchronous_assessment(self):
        original=heldout.assess
        oid=self.f.source['candidate_commit'];obj=self.f.base.repo/'.git'/'objects'/oid[:2]/oid[2:]
        def late(*args):
            result=original(*args);obj.write_bytes(b'corrupt owned synthetic object');return result
        with patch.object(heldout,'assess',side_effect=late):
            result=self.f.recommend();self.assertNotEqual(result['recommendation'],'recommend')

    def test_run_next_cli_subprocess_failure_is_bounded_refusal(self):
        with patch('sys.argv',['heldout.py','run-next','--record','/synthetic/record','--plan','/synthetic/plan','--auth-source','/synthetic/auth']),patch.object(heldout,'run_next',side_effect=subprocess.TimeoutExpired(['git'],1)),contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(heldout.main(),2)
        self.assertEqual(json.loads(stdout.getvalue()),dict(status='refused',reason='heldout_preflight_unavailable'))

    def test_missing_preflight_unknown_delivery_and_known_exposure_block(self):
        receipt=self.f.preflight.read_bytes();self.f.preflight.unlink();self.assertNotEqual(self.f.recommend()['recommendation'],'recommend');self.f.preflight.write_bytes(receipt);self.f.preflight.chmod(0o600)
        for material in ('unknown_delivery','answer','candidate_edit'):
            save(self.f.exposure,dict(schema_version=1,kind='same_host_exposure_v1',events=[dict(context_id='author',material=material,phase='during_comparison')]))
            result=self.f.recommend();self.assertNotEqual(result['recommendation'],'recommend')
            self.assertEqual(result['heldout']['status'],{'unknown_delivery':'inconclusive','answer':'exposed','candidate_edit':'invalid'}[material])
    def test_rebound_dispatch_still_enforces_closed_fresh_digest_only_input(self):
        originals={path:path.read_bytes() for path in self.f.area.iterdir() if path.is_file()}
        for fault,reason in [('fork','heldout_dispatch'),('call','heldout_fresh_context'),('output','heldout_metadata_only'),('workspace','heldout_author')]:
            d=json.loads(self.f.dispatch.read_text());m=copy.deepcopy(self.f.m)
            if fault=='fork':d['dispatch']['fork_turns']='all'
            if fault=='call':
                path=Path(d['input']['tool_call_evidence_path']);value=json.loads(path.read_text());value['arguments']['fork_turns']='all'
                save(path,value);d['input']['tool_call_evidence_sha256']=sha(path)
            if fault=='output':
                path=Path(d['output']['metadata_evidence_path']);value=json.loads(path.read_text());value['answer']='not digest-only'
                save(path,value);d['output']['metadata_evidence_sha256']=sha(path)
            if fault=='workspace':
                value=json.loads(self.f.author_receipt.read_text());value['workspace']=str(self.f.area);save(self.f.author_receipt,value)
                m['contexts']['author'][0]['sha256']=sha(self.f.author_receipt)
            d['receipt_digest']=ev.digest({k:v for k,v in d.items() if k!='receipt_digest'});save(self.f.dispatch,d)
            m['contexts']['preparation']['sha256']=sha(self.f.dispatch);m['record_digest']=ev.digest({k:v for k,v in m.items() if k!='record_digest'});save(self.f.record,m)
            with patch.object(heldout,'_comment',side_effect=lambda ref:self.f.comments[ref['comment_id']]):
                with self.assertRaisesRegex(ValueError,reason):heldout._prepare(str(self.f.record),self.f.source)
            for path,raw in originals.items():path.write_bytes(raw)
    def test_late_exposure_drift_invalidates_prior_positive(self):
        original=gate.evaluate_rule;calls=0
        def change(*args):
            nonlocal calls
            result=original(*args);calls+=1
            if calls==2:self.f.exposure.write_bytes(self.f.exposure.read_bytes()+b' ')
            return result
        with patch.object(gate,'evaluate_rule',side_effect=change):self.assertNotEqual(self.f.recommend()['recommendation'],'recommend')
    def test_final_remote_lookup_cannot_hide_late_local_mutation(self):
        original=heldout._anchor;calls=0
        def change(*args):
            nonlocal calls
            result=original(*args);calls+=1
            if calls==4:self.f.exposure.write_bytes(self.f.exposure.read_bytes()+b' ')
            return result
        with patch.object(heldout,'_anchor',side_effect=change):self.assertNotEqual(self.f.recommend()['recommendation'],'recommend')
    def test_transport_subprocess_error_is_inconclusive(self):
        with patch.object(ad.nt,'bounded',side_effect=subprocess.TimeoutExpired(['gh'],5)),patch('shutil.which',return_value='/synthetic/gh'):
            with self.assertRaises(heldout.Unavailable):heldout._comment(self.f.m['freeze'])
    def test_wrong_declared_attempt_is_rejected_before_preflight(self):
        self.f.m['experiment']['attempts'][0]['trial_id']='other'
        self.f.m['record_digest']=ev.digest({k:v for k,v in self.f.m.items() if k!='record_digest'});save(self.f.record,self.f.m)
        with patch.object(heldout,'_comment',side_effect=lambda ref:self.f.comments[ref['comment_id']]):
            with self.assertRaisesRegex(ValueError,'heldout_tasks'):heldout._prepare(str(self.f.record),self.f.source)
    def test_released_feedback_reclassifies_future_use(self):
        save(self.f.exposure,dict(schema_version=1,kind='same_host_exposure_v1',events=[dict(context_id='author',material='answer',phase='after_comparison')]))
        result=self.f.recommend();self.assertEqual(result['heldout']['future_classification'],'development_regression')
    def test_actual_fixed_gh_get_contract_and_transport_failure(self):
        response=dict(exit=0,stop_reason=None,stderr='',stdout=json.dumps(self.f.comments[12]))
        with patch.object(ad.nt,'bounded',return_value=response) as run,patch('shutil.which',return_value='/synthetic/gh'):
            self.assertEqual(heldout._comment(self.f.m['freeze']),self.f.comments[12])
        argv=run.call_args.args[0];self.assertIn('GET',argv);self.assertIn('github.com',argv);self.assertNotIn('POST',argv)
    def test_remote_nonobject_and_execution_root_receipt_refuse(self):
        with patch.object(heldout,'_comment',return_value=[]):
            with self.assertRaisesRegex(ValueError,'heldout_anchor'):heldout._anchor(self.f.m['freeze'],{})
        nested=self.f.held.state/'private';nested.mkdir(mode=0o700);m=copy.deepcopy(self.f.m)
        m['preflight']['path']=str(nested/'preflight.json');m['exposure']['path']=str(nested/'exposure.json')
        m['record_digest']=ev.digest({k:v for k,v in m.items() if k!='record_digest'});record=nested/'manifest.json';save(record,m)
        with patch.object(heldout,'_comment',side_effect=lambda ref:self.f.comments[ref['comment_id']]):
            with self.assertRaisesRegex(ValueError,'heldout_area'):heldout._prepare(str(record),self.f.source)
    def test_preflight_must_precede_reservation_and_calls_only_fixed_gate(self):
        other=FakeHeldout(execute=False)
        try:
            with patch.object(heldout,'_comment',side_effect=lambda ref:other.comments[ref['comment_id']]),patch.object(ad.nt,'run',side_effect=other.held.run) as run:
                heldout.run_next(str(other.record),other.held.plans[0],Path('/synthetic-not-opened/auth.json'))
                self.assertEqual(run.call_count,1);self.assertTrue(other.preflight.exists())
                other.preflight.unlink()
                with self.assertRaises(ValueError):heldout.run_next(str(other.record),other.held.plans[1],Path('/synthetic-not-opened/auth.json'))
                self.assertEqual(run.call_count,1)
        finally:other.close()


if __name__=='__main__':unittest.main()
