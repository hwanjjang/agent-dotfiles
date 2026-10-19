"""Recommendation policy tests; synthetic eligible rules never authorize delivery."""
import copy
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import unittest
import json
import subprocess
import sys
from pathlib import Path
from scripts.improvement import evaluation as ev
from scripts.improvement import promotion as gate
import test_improvement_evaluation as fixture


class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.spec=fixture.spec();self.spec['promotion_rule']='quality_gain_v1'
        # Noncritical wrong outputs allow testing benefit/regression separately.
        for v in ev.VARIANTS:
            self.spec['checks']['verification-en'][v]['criteria'][0]['critical']=False
        self.spec['budget']={'model_requests':16,'tokens':1000,'seconds':180}
        self.plan=ev.freeze(self.spec)
        self.rows=[]
        for t in self.plan['trials']:
            row=fixture.completion(self.plan,t,usage={'input_tokens':2,'output_tokens':1})
            if t['arm']=='baseline':
                row['observations']['check']['claim']='unavailable'
            self.rows.append(row)
        self.report=ev.compare(self.plan,self.rows,self.spec)
        self.diff=hashlib.sha256(b'synthetic reviewed diff').hexdigest()

    def recommend(self,**changes):
        args=dict(experiment=self.plan,report=self.report,completions=self.rows,
                  current_spec=self.spec,source_diff_digest=self.diff)
        args.update(changes)
        return gate.recommend(**args)

    def test_positive_rule_fixture_stays_operationally_inconclusive(self):
        metrics=gate.evaluate_rule(self.plan,self.report)
        self.assertEqual(metrics['verdict'],'eligible')
        self.assertEqual(metrics['scope'],'synthetic_rule_diagnostic')
        result=self.recommend()
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertFalse(result['promotion_eligible']);self.assertFalse(result['merge_authorized'])
        self.assertFalse(result['install_authorized'])
        self.assertIn('independent_holdout_custody_unavailable',result['reasons'])
        self.assertEqual(result['review']['candidate'],self.spec['identities']['candidate'])

    def test_candidate_fix_of_baseline_critical_defect_does_not_reject(self):
        for v in ev.VARIANTS:
            self.spec['checks']['verification-en'][v]['criteria'][0]['critical']=True
        self.plan=ev.freeze(self.spec)
        rows=[]
        for t in self.plan['trials']:
            row=fixture.completion(self.plan,t,usage={'input_tokens':2,'output_tokens':1})
            if t['arm']=='baseline':row['observations']['check']['claim']='unavailable'
            rows.append(row)
        report=ev.compare(self.plan,rows,self.spec)
        result=self.recommend(report=report,completions=rows)
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertEqual(result['rule_result']['verdict'],'eligible')
        self.assertEqual(result['rule_result']['reasons'],[])
        self.assertEqual(result['rule_result']['critical_violations_by_arm'],{'baseline':4,'candidate':0})
        self.assertNotIn('critical_violation',result['reasons'])
        self.assertFalse(result['promotion_eligible'])

    def test_critical_failure_rejects_higher_aggregate_gain(self):
        # Candidate improves overall outcomes but has one critical failure.
        for v in ev.VARIANTS:
            checks=self.spec['checks']['verification-en'][v]['criteria']
            checks[0]['critical']=True
            checks.append({'id':'artifact','dimension':'outcome','kind':'artifact_sha256',
                           'target':'result','expected':hashlib.sha256(b'right').hexdigest(),'critical':False})
        self.plan=ev.freeze(self.spec)
        self.rows=[fixture.completion(self.plan,t,usage={'input_tokens':1,'output_tokens':1},
                   artifacts={'result':'right' if t['arm']=='candidate' else 'wrong'}) for t in self.plan['trials']]
        victim=next(row for t,row in zip(self.plan['trials'],self.rows) if t['arm']=='candidate')
        victim['observations']['check']['claim']='unavailable'
        self.report=ev.compare(self.plan,self.rows,self.spec)
        self.assertEqual(self.report['arms']['candidate']['pass'],3)
        self.assertEqual(self.report['arms']['baseline']['pass'],0)
        self.assertEqual(self.report['critical_violations'],1)
        self.assertEqual(self.recommend()['recommendation'],'reject')
        self.assertIn('critical_violation',self.recommend()['reasons'])
        self.assertEqual(self.recommend()['rule_result']['reasons'],['critical_violation'])
        self.assertEqual(self.recommend()['rule_result']['critical_violations_by_arm'],{'baseline':0,'candidate':1})

    def test_current_identity_case_budget_or_rule_change_rejects(self):
        for field in self.spec['identities']:
            changed=copy.deepcopy(self.spec);changed['identities'][field]='e'*64
            self.assertIn('stale_experiment',self.recommend(current_spec=changed)['reasons'])
        changed=copy.deepcopy(self.spec);changed['budget']['tokens']+=1
        self.assertEqual(self.recommend(current_spec=changed)['recommendation'],'reject')
        changed=copy.deepcopy(self.spec);changed['promotion_rule']='equal_quality_lower_tokens_v1'
        self.assertIn('stale_experiment',self.recommend(current_spec=changed)['reasons'])
        changed=copy.deepcopy(self.spec);changed['cases'][0]['inputs']['request']+=' changed'
        self.assertEqual(self.recommend(current_spec=changed)['recommendation'],'reject')

    def test_rehashed_forged_summary_or_live_receipt_never_passes(self):
        for field,value in [('critical_violations',0),('live_eligible',True),('holdout_custody',{'qualified':True})]:
            bad=copy.deepcopy(self.report);bad[field]=value
            if field=='critical_violations':bad['counts']['pass']=999
            bad['report_digest']=ev.digest({k:v for k,v in bad.items() if k!='report_digest'})
            result=self.recommend(report=bad)
            self.assertEqual(result['recommendation'],'reject')
            self.assertIn('report_evidence_mismatch',result['reasons'])

    def test_canonical_report_type_tampering_rejects(self):
        for field,value in [('critical_violations',False),('scheduled',8.0)]:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.report);changed[field]=value
                result=self.recommend(report=changed)
                self.assertEqual(result['recommendation'],'reject')
                self.assertIn('report_evidence_mismatch',result['reasons'])
        changed=copy.deepcopy(self.plan);changed['schema_version']=True
        self.assertEqual(self.recommend(experiment=changed)['recommendation'],'reject')

    def test_missing_and_unknown_cost_are_inconclusive(self):
        rows=self.rows[:-1];report=ev.compare(self.plan,rows,self.spec)
        self.assertEqual(self.recommend(report=report,completions=rows)['recommendation'],'inconclusive')
        rows=copy.deepcopy(self.rows);rows[0]['usage']=None
        report=ev.compare(self.plan,rows,self.spec)
        self.assertIn('usage_unknown',gate.evaluate_rule(self.plan,report)['reasons'])

    def test_regression_and_cost_fail_closed(self):
        rows=copy.deepcopy(self.rows)
        for row in rows:row['usage']={'input_tokens':1000,'output_tokens':1000}
        report=ev.compare(self.plan,rows,self.spec)
        self.assertIn('token_budget_exceeded',gate.evaluate_rule(self.plan,report)['reasons'])
        rows=[fixture.completion(self.plan,t,usage={'input_tokens':1,'output_tokens':1}) for t in self.plan['trials']]
        for t,row in zip(self.plan['trials'],rows):
            if t['arm']=='candidate':row['observations']['check']['claim']='unavailable'
        report=ev.compare(self.plan,rows,self.spec)
        self.assertIn('case_regression',gate.evaluate_rule(self.plan,report)['reasons'])
        self.assertEqual(gate.evaluate_rule(self.plan,report)['verdict'],'reject')

    def test_efficiency_rule_and_no_benefit(self):
        self.spec['promotion_rule']='equal_quality_lower_tokens_v1';self.plan=ev.freeze(self.spec)
        rows=[fixture.completion(self.plan,t,usage={'input_tokens':5 if t['arm']=='baseline' else 2,'output_tokens':1}) for t in self.plan['trials']]
        report=ev.compare(self.plan,rows,self.spec)
        self.assertEqual(gate.evaluate_rule(self.plan,report)['verdict'],'eligible')
        for row in rows:row['usage']={'input_tokens':1,'output_tokens':1}
        report=ev.compare(self.plan,rows,self.spec)
        self.assertIn('target_benefit_not_observed',gate.evaluate_rule(self.plan,report)['reasons'])

    def test_dollars_are_required_only_when_explicitly_frozen(self):
        self.assertNotIn('declared_currency_usage_unknown',gate.evaluate_rule(self.plan,self.report)['reasons'])
        self.spec['budget'].update(amount=1,currency='USD');self.plan=ev.freeze(self.spec)
        rows=[fixture.completion(self.plan,t,usage={'input_tokens':1,'output_tokens':1}) for t in self.plan['trials']]
        report=ev.compare(self.plan,rows,self.spec)
        self.assertIn('declared_currency_usage_unknown',gate.evaluate_rule(self.plan,report)['reasons'])

    def test_unknown_rule_refuses(self):
        self.spec['promotion_rule']='anything';self.plan=ev.freeze(self.spec)
        self.rows=[fixture.completion(self.plan,t) for t in self.plan['trials']]
        self.report=ev.compare(self.plan,self.rows,self.spec)
        self.assertIn('unsupported_rule',self.recommend()['reasons'])


    def test_current_grader_source_drift_rejects_unchanged_spec(self):
        historical=copy.deepcopy(self.spec);historical['identities']['grader']='f'*64
        plan=ev.freeze(historical)
        # Experiment and current_spec agree; only the installed grader differs.
        result=self.recommend(experiment=plan,current_spec=historical)
        self.assertEqual(result['recommendation'],'reject')
        self.assertEqual(result['reasons'],['stale_experiment'])

    def cli(self,raw):
        return subprocess.run([sys.executable,str(Path(gate.__file__)),'recommend'],input=raw,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)

    def test_cli_parser_refusal_shape_and_exit_one(self):
        request=dict(experiment=self.plan,report=self.report,completions=self.rows,
                     current_spec=self.spec,source_diff_digest=self.diff)
        valid=json.dumps(request).encode()
        duplicate=valid[:-1]+b', "source_diff_digest": "'+self.diff.encode()+b'"}'
        extras=json.dumps(dict(request,extra=True)).encode()
        missing=json.dumps({k:v for k,v in request.items() if k!='report'}).encode()
        for raw in [duplicate,valid+b' '*ev.MAX_BYTES,extras,missing,b'{"x":NaN}',
                    b'{"x":Infinity}',b'{"x":-Infinity}',b'{bad',b'[]']:
            with self.subTest(prefix=raw[:40]):
                p=self.cli(raw);self.assertEqual(p.returncode,1)
                self.assertEqual(json.loads(p.stdout),{'status':'rejected','reason':'invalid_gate_input'})
                self.assertEqual(p.stderr,b'')

    def test_cli_nested_refusal_is_complete_recommendation_with_exit_zero(self):
        request=dict(experiment={},report=self.report,completions=self.rows,
                     current_spec=self.spec,source_diff_digest=self.diff)
        p=self.cli(json.dumps(request).encode());self.assertEqual(p.returncode,0)
        result=json.loads(p.stdout);self.assertEqual(result['recommendation'],'reject')
        self.assertEqual(result['reasons'],['invalid_gate_input'])
        self.assertFalse(result['promotion_eligible']);self.assertFalse(result['merge_authorized'])
        self.assertFalse(result['install_authorized']);self.assertIn('recommendation_digest',result)


class NativePromotionTests(unittest.TestCase):
    """Real disposable Git objects; native journals/qualification remain FAKE."""
    def setUp(self):
        from test_trial_admission import RoutedAttempts, save
        from scripts.improvement import trial_admission as ad
        self.ad, self.save = ad, save
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); evidence = self.root/'evidence'; evidence.mkdir()
        self.f = RoutedAttempts(evidence); self.repo = self.root/'repo'; self.repo.mkdir()
        self.git('init','-q'); self.commits = []
        for arm in ev.ARMS:
            for row in self.f.context['arms'][arm]['files']:
                path = self.repo/row['path']; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((Path(self.f.context['arms'][arm]['root'])/row['path']).read_bytes())
            self.commits.append(self.commit())
        self.roots = ['skills/first','skills/second','skills/third']
        self.f.spec.update(promotion_rule='quality_gain_v1',budget=dict(model_requests=4,tokens=600000,seconds=1260))
        self.f.experiment = ev.freeze(self.f.spec)
        declaration = next(iter(self.f.context['collection_by_trial'].values()))
        self.f.context.update(experiment_digest=self.f.experiment['experiment_digest'],
            collection_by_trial={t['trial_id']:declaration for t in self.f.experiment['trials']})
        save(self.f.context_path,self.f.context)
        self.refs = [self.f.attempt(i) for i in range(len(self.f.experiment['trials']))]
        self.report_path = self.root/'report.json'
        patcher = patch.object(ad,'ROOT',evidence); patcher.start(); self.addCleanup(patcher.stop)
        self.refresh()

    def git(self,*args):
        env = dict(PATH=os.defpath,HOME=str(self.root),GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
        result = subprocess.run([shutil.which('git',path=os.defpath),'-C',str(self.repo),
            '-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',
            '-c','commit.gpgsign=false',*args],env=env,capture_output=True,timeout=10,check=True)
        return result.stdout.decode().strip()

    def commit(self):
        self.git('add','--all'); self.git('commit','-qm','Synthetic component fixture')
        return self.git('rev-parse','HEAD')

    def refresh(self):
        ctx = self.ad.load_context(self.f.experiment,self.f.spec,self.f.context_path)
        batch = self.ad.read_attempts(ctx,self.refs)
        try: self.report = ev.compare(self.f.experiment,[],self.f.spec,native=batch)
        finally: batch.close()
        self.save(self.report_path,self.report)

    def args(self):
        return dict(experiment=self.f.experiment,current_spec=self.f.spec,context_path=str(self.f.context_path),
            attempts=self.refs,report_path=str(self.report_path),repository=str(self.repo),
            baseline_commit=self.commits[0],candidate_commit=self.commits[1],component_roots=self.roots)

    def recommend(self,**changes):
        args = self.args(); args.update(changes); return gate.recommend_native(**args)

    def source(self,**changes):
        args = self.args(); args.update(changes)
        ctx = self.ad.load_context(self.f.experiment,self.f.spec,self.f.context_path)
        return gate.verify_source(ctx,**{k:args[k] for k in
            ('repository','baseline_commit','candidate_commit','component_roots')})

    def test_actual_committed_delta_and_unknown_latency_are_inconclusive(self):
        result = self.recommend()
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertIn('latency_unknown',result['reasons'])
        self.assertIn('same_host_heldout_unverified',result['reasons'])
        self.assertEqual(result['review']['source']['baseline_commit'],self.commits[0])
        self.assertEqual([r['path'] for r in result['review']['source']['changes']],
                         [r+'/SKILL.md' for r in self.roots])
        for key in ('source_accepted','promotion_eligible','merge_authorized','install_authorized'):
            self.assertIs(result[key],False)

    def test_second_source_check_follows_assessment_without_charging_remote_wait(self):
        from scripts.improvement import heldout
        source=self.source();clock=[100.0];events=[];deadlines=[]
        def verify(*args,**kwargs):
            events.append('source');deadlines.append(kwargs['_deadline']);clock[0]+=2
            return source
        def assess(*args):
            events.append('assessment');clock[0]+=20
            return dict(status='inconclusive',reasons=['heldout_unavailable'])
        with patch.object(gate,'time',SimpleNamespace(monotonic=lambda:clock[0])),patch.object(gate,'verify_source',side_effect=verify),patch.object(heldout,'assess',side_effect=assess):
            self.recommend(heldout_record_path='/synthetic/never-read')
        self.assertEqual(events,['source','assessment','source'])
        self.assertEqual(deadlines,[112.0,132.0])

    def test_source_resource_failures_are_inconclusive_at_both_checks(self):
        source=self.source()
        for error in (ev.Invalid('source_read_limit'),ev.Invalid('git_unavailable'),subprocess.TimeoutExpired(['git'],1)):
            for late in (False,True):
                with self.subTest(reason=type(error).__name__+str(error),late=late):
                    with patch.object(gate,'verify_source',side_effect=[source,error] if late else error):
                        result=self.recommend()
                    self.assertEqual(result['recommendation'],'inconclusive')
                    self.assertIn('source_unavailable',result['reasons'])
        for late in (False,True):
            with patch.object(gate,'verify_source',side_effect=[source,ev.Invalid('source_object')] if late else ev.Invalid('source_object')):
                result=self.recommend()
            self.assertEqual(result['recommendation'],'reject')
            self.assertNotIn('source_unavailable',result['reasons'])

    def test_missing_results_are_inconclusive_and_batch_is_closed(self):
        self.refs = []; self.refresh()
        reader = self.ad.read_attempts; batches = []
        def observe(*args):
            value = reader(*args); batches.append(value); return value
        with patch.object(self.ad,'read_attempts',side_effect=observe): result = self.recommend()
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertIn('trial_coverage_incomplete',result['reasons']); self.assertTrue(batches[0].closed)

    def test_arithmetic_gain_cannot_bypass_missing_heldout_or_reservation(self):
        for trial,ref in zip(self.f.experiment['trials'],self.refs):
            if trial['arm']=='baseline':
                self.f.mutate(ref,'collection_result',lambda r:r['snapshot']['files'][0].update(sha256='f'*64))
                def fix(r): r['collection']['snapshot']['files'][0]['sha256']='f'*64
                self.f.mutate(ref,'receipt',fix)
        self.refresh(); result = self.recommend()
        self.assertEqual(result['rule_result']['observed_pass_gain'],2)
        self.assertEqual(result['rule_result']['verdict'],'inconclusive')
        self.assertIn('latency_unknown',result['reasons'])
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertIn('same_host_heldout_unverified',result['reasons'])
        self.assertIn('aggregate_launch_reservation_unavailable',result['reasons'])

    def test_native_candidate_critical_failure_rejects_with_unknown_latency(self):
        for trial,ref in zip(self.f.experiment['trials'],self.refs):
            if trial['arm']=='candidate':
                self.f.mutate(ref,'collection_result',lambda r:r['snapshot']['files'][0].update(sha256='f'*64))
                def fix(r): r['collection']['snapshot']['files'][0]['sha256']='f'*64
                self.f.mutate(ref,'receipt',fix)
        self.refresh(); result = self.recommend()
        self.assertEqual(result['recommendation'],'reject')
        self.assertIn('critical_violation',result['reasons'])

    def test_forged_report_or_source_arm_never_passes(self):
        bad = copy.deepcopy(self.report); bad['counts']['pass']=999; self.save(self.report_path,bad)
        self.assertIn('report_evidence_mismatch',self.recommend()['reasons'])
        self.save(self.report_path,self.report)
        path = Path(self.f.context['arms']['candidate']['root'])/'skills/first/SKILL.md'
        path.write_bytes(path.read_bytes()+b'changed')
        self.assertEqual(self.recommend()['recommendation'],'reject')

    def test_full_commit_ids_type_and_scope_are_required(self):
        tree = self.git('rev-parse','HEAD^{tree}')
        for values in [dict(candidate_commit='HEAD'),dict(candidate_commit=self.commits[1][:12]),
                       dict(candidate_commit=tree),dict(candidate_commit='f'*40),
                       dict(component_roots=['skills']),dict(component_roots=['skills/first']),
                       dict(component_roots=self.roots[::-1]),dict(component_roots=['../skills']),
                       dict(component_roots=['skills/first','skills/first/SKILL.md'])]:
            with self.subTest(values=values),self.assertRaises(ValueError): self.source(**values)

    def add_policy_roots(self, count):
        """Extend the complete frozen inventories, without faking Git objects."""
        names = [f'policies/policy-{i:02d}.md' for i in range(count)]
        for arm in ev.ARMS:
            value = self.f.context['arms'][arm]
            for name in names:
                raw = b'Synthetic shared policy\n'
                path = Path(value['root']) / name
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
                value['files'].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest()))
            value['files'].sort(key=lambda row:row['path'])
            self.f.spec['identities'][arm] = ev.digest({k:value[k] for k in ('entrypoint','files','routing')})
            for row in value['files']:
                path = self.repo / row['path']; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((Path(value['root']) / row['path']).read_bytes())
            self.commits[ev.ARMS.index(arm)] = self.commit()
        self.roots = sorted(self.roots + names)
        self.f.experiment = ev.freeze(self.f.spec)
        declaration = next(iter(self.f.context['collection_by_trial'].values()))
        self.f.context.update(experiment_digest=self.f.experiment['experiment_digest'],
            collection_by_trial={t['trial_id']:declaration for t in self.f.experiment['trials']})
        self.save(self.f.context_path,self.f.context)

    def test_complete_skill_and_policy_inventory_can_exceed_eight_roots(self):
        self.add_policy_roots(12)
        source = self.source()
        self.assertEqual(len(source['component_roots']),15)
        self.assertEqual(len(source['changes']),3)
        with self.assertRaisesRegex(ValueError,'source_inventory'):
            self.source(component_roots=self.roots[1:])

    def test_root_capacity_matches_existing_sixty_four_file_inventory(self):
        self.add_policy_roots(61)
        self.assertEqual(len(self.source()['component_roots']),64)
        with self.assertRaisesRegex(ValueError,'source_roots'):
            self.source(component_roots=sorted(self.roots + ['policies/unselected.md']))

    def test_complete_component_inventory_and_outside_delta_required(self):
        extra = self.repo/'skills/first/references/extra.md'; extra.parent.mkdir(); extra.write_text('synthetic')
        extra_commit = self.commit()
        with self.assertRaises(ValueError): self.source(candidate_commit=extra_commit)
        extra.unlink(); (self.repo/'outside.txt').write_text('synthetic untested delta')
        with self.assertRaises(ValueError): self.source(candidate_commit=self.commit())

    def test_metadata_only_or_symlink_changes_are_not_tested_source(self):
        file = self.repo/'skills/first/SKILL.md'; file.chmod(0o755)
        with self.assertRaises(ValueError): self.source(candidate_commit=self.commit())
        file.unlink(); file.symlink_to('../../second/SKILL.md')
        with self.assertRaises(ValueError): self.source(candidate_commit=self.commit())

    def test_dirty_checkout_and_git_override_environment_do_not_change_objects(self):
        expected = self.source(); (self.repo/'skills/first/SKILL.md').write_text('DIRTY')
        with patch.dict(os.environ,{'GIT_DIR':'/missing','GIT_WORK_TREE':'/missing',
                'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'core.pager','GIT_CONFIG_VALUE_0':'false'}):
            self.assertEqual(self.source(),expected)
        with self.assertRaises(ValueError): self.source(baseline_commit=self.commits[1])

    def test_source_and_report_late_drift_invalidate_even_after_arithmetic(self):
        source = self.source()
        with patch.object(gate,'verify_source',side_effect=[source,subprocess.TimeoutExpired('fixed',1)]):
            result=self.recommend();self.assertEqual(result['recommendation'],'inconclusive')
            self.assertIn('source_unavailable',result['reasons'])
        original = gate.evaluate_rule
        for name in ('report','arm'):
            with self.subTest(name=name):
                def mutate(*args):
                    value = original(*args)
                    path = self.report_path if name=='report' else Path(self.f.context['arms']['candidate']['root'])/'skills/first/SKILL.md'
                    path.write_bytes(path.read_bytes()+b' '); return value
                with patch.object(gate,'evaluate_rule',side_effect=mutate):
                    self.assertEqual(self.recommend()['recommendation'],'reject')
                self.save(self.report_path,self.report)

    def test_raw_binary_blob_hashes_are_never_decoded(self):
        for arm,raw in zip(ev.ARMS,(b'\xff\x00baseline',b'\xfe\x00candidate')):
            value = self.f.context['arms'][arm]
            name = 'skills/first/references/' + ('old.bin' if arm=='baseline' else 'new.bin')
            if arm=='candidate': (self.repo/'skills/first/references/old.bin').unlink()
            path = Path(value['root'])/name; path.parent.mkdir(); path.write_bytes(raw)
            value['files'].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest()))
            value['files'].sort(key=lambda r:r['path'])
            self.f.spec['identities'][arm] = ev.digest({k:value[k] for k in ('entrypoint','files','routing')})
            for row in value['files']:
                target = self.repo/row['path']; target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((Path(value['root'])/row['path']).read_bytes())
            self.commits[ev.ARMS.index(arm)] = self.commit()
        self.f.experiment = ev.freeze(self.f.spec)
        declaration = next(iter(self.f.context['collection_by_trial'].values()))
        self.f.context.update(experiment_digest=self.f.experiment['experiment_digest'],
            collection_by_trial={t['trial_id']:declaration for t in self.f.experiment['trials']})
        self.save(self.f.context_path,self.f.context)
        rows = {r['path']:r for r in self.source()['changes']}
        old,new = (rows['skills/first/references/'+n+'.bin'] for n in ('old','new'))
        self.assertEqual(old['old_blob_sha256'],hashlib.sha256(b'\xff\x00baseline').hexdigest())
        self.assertEqual(new['new_blob_sha256'],hashlib.sha256(b'\xfe\x00candidate').hexdigest())
        self.assertIsNone(old['new_mode']); self.assertIsNone(new['old_blob_sha256'])

    def test_actual_raw_reader_cap_reaps_owned_process_and_deadline_refuses(self):
        oid = self.git('rev-parse','HEAD:skills/first/SKILL.md'); processes = []
        original = gate.subprocess.Popen
        def observe(*args,**kwargs):
            process = original(*args,**kwargs); processes.append(process); return process
        with patch.object(gate.subprocess,'Popen',side_effect=observe),self.assertRaises(ValueError):
            gate._git(self.repo,'blob',oid,gate.time.monotonic()+3,5)
        self.assertIsNotNone(processes[0].poll()); self.assertTrue(processes[0].stdout.closed)
        with self.assertRaises(ValueError): gate._git(self.repo,'blob',oid,gate.time.monotonic()-1,1000)

    def test_current_public_proof_is_not_replaced_by_fixture_claim(self):
        with patch.object(self.ad,'ROOT',Path(self.ad.__file__).resolve().parents[2]):
            self.refresh(); result = self.recommend()
        self.assertEqual(result['recommendation'],'inconclusive')
        self.assertIn('qualification_unavailable',result['reasons'])

    def test_native_cli_closed_inputs_and_real_git_path(self):
        run = subprocess.run([sys.executable,str(Path(gate.__file__)),'recommend-native'],
            input=ev.encoded(dict(self.args(),verified=True)),capture_output=True,timeout=10)
        self.assertEqual(run.returncode,1)
        self.assertEqual(json.loads(run.stdout),{'status':'rejected','reason':'invalid_gate_input'})


if __name__=='__main__':unittest.main()
