"""Recommendation policy tests; synthetic eligible rules never authorize delivery."""
import copy
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


if __name__=='__main__':unittest.main()
