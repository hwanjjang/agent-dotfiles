"""Recommendation policy tests; synthetic eligible rules never authorize delivery."""
import copy
import hashlib
import unittest
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

    def test_current_identity_case_budget_or_rule_change_rejects(self):
        for field in self.spec['identities']:
            changed=copy.deepcopy(self.spec);changed['identities'][field]='e'*64
            self.assertIn('stale_experiment',self.recommend(current_spec=changed)['reasons'])
        changed=copy.deepcopy(self.spec);changed['budget']['tokens']+=1
        self.assertEqual(self.recommend(current_spec=changed)['recommendation'],'reject')
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

    def test_unknown_rule_and_changed_grader_refuse(self):
        self.spec['promotion_rule']='anything';self.plan=ev.freeze(self.spec)
        self.rows=[fixture.completion(self.plan,t) for t in self.plan['trials']]
        self.report=ev.compare(self.plan,self.rows,self.spec)
        self.assertIn('unsupported_rule',self.recommend()['reasons'])


if __name__=='__main__':unittest.main()
