"""A continuation permission never repairs a failed row or supplies unknown billing."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_trial_reservation as support
from test_trial_reservation import ad, ev, nt, save


class NoTurnContinuationTests(unittest.TestCase):
    setUp=support.GateTests.setUp
    args=support.GateTests.args
    launch=support.GateTests.launch

    def init(self, enabled=True):
        return self.r.initialize(*self.args(),self.s.plans,continue_after_no_turn=enabled)

    def fail_before_turn(self,index=0,**changes):
        folder=self.s.saved[index]/'records'
        def observation(o):
            o.update(status='blocked',reason='protocol_refusal',terminal_completed=False,
                     initial_turn_requests_attempted=0,initial_turns=0,auth_chatgpt_observed=False,
                     rpc_failure={'method':'account/read','phase':'response','kind':'server_error','code':'internal_error'},
                     usage={'first':None,'latest':None,'all_changed_snapshots_persisted':True,'stop':None})
            o.update(changes)
        for label in ('observation','receipt'):
            path=next(folder.glob('*-'+label+'.json'));value=json.loads(path.read_text())
            observation(value if label=='observation' else value['observation'])
            if label=='receipt':value['status']='blocked'
            save(path,value)
        for path in folder.glob('*-usage_snapshot.json'):path.unlink()
        for index,path in enumerate(sorted(folder.iterdir()),1):
            path.rename(folder/(f'{index:03d}-'+path.name.split('-',1)[1]))

    def test_explicit_policy_continues_next_without_rewriting_unknown_failed_row(self):
        self.init();self.fail_before_turn();first=self.launch()
        self.assertEqual(first['status'],'blocked');self.assertTrue(first['next_launch_allowed'])
        self.assertEqual(first['unknown_attempts'],1);self.assertIsNone(first['total_tokens'])
        self.assertEqual(first['admission_tokens'],131072)
        before={str(p):p.read_bytes() for p in (self.s.state/self.s.f.experiment['trials'][0]['trial_id']).rglob('*') if p.is_file()}
        second=self.launch(1)
        self.assertEqual(second['reserved_initial_turns'],2)
        self.assertEqual(second['known_tokens'],160);self.assertIsNone(second['total_tokens'])
        self.assertEqual(second['admission_tokens'],131232)
        self.assertTrue(all(Path(p).read_bytes()==v for p,v in before.items()))
        with self.assertRaises(ValueError):self.launch(1)
        self.assertEqual(self.r.status(*self.args())['reserved_initial_turns'],2)
        f=self.s.f;ctx=ad.load_context(f.experiment,f.spec,f.context_path)
        refs=[{'trial_id':t['trial_id'],'attempt_id':'one','attempt_path':str(self.s.state/t['trial_id']/'one')} for t in f.experiment['trials'][:2]]
        batch=ad.read_attempts(ctx,refs)
        try:report=ev.compare(f.experiment,[],f.spec,native=batch)
        finally:batch.close()
        self.assertEqual(report['counts']['blocked'],1)
        self.assertEqual(report['coverage']['missing'],2)
        self.assertFalse(report['live_eligible'])

    def test_default_still_stops_and_does_not_retry_the_failed_case(self):
        self.init(False);self.fail_before_turn();result=self.launch()
        self.assertFalse(result['next_launch_allowed'])
        with patch.object(nt,'run') as run,self.assertRaises(ValueError):
            self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
        run.assert_not_called()

    def test_possible_turn_or_non_rpc_failure_does_not_authorize_continuation(self):
        self.init();self.fail_before_turn(initial_turn_requests_attempted=1)
        self.assertFalse(self.launch()['next_launch_allowed'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_unknown_or_inconsistent_turn_and_diagnostics_fail_closed(self):
        self.init();self.fail_before_turn(initial_turns=None)
        self.assertFalse(self.launch()['next_launch_allowed'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_cleanup_uncertainty_and_tampered_receipt_stop_before_launch(self):
        self.init();self.fail_before_turn()
        folder=self.s.saved[0]/'records'
        for label in ('cleanup','receipt'):
            path=next(folder.glob('*-'+label+'.json'));value=json.loads(path.read_text())
            (value if label=='cleanup' else value['cleanup'])['complete']=False;save(path,value)
        self.assertFalse(self.launch()['next_launch_allowed'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_persistent_early_failure_retains_each_reserved_row_and_allowance(self):
        self.init()
        for i in range(4):
            self.fail_before_turn(i);result=self.launch(i)
            self.assertEqual(result['unknown_attempts'],i+1)
            self.assertEqual(result['admission_tokens'],(i+1)*131072)
        self.assertFalse(result['next_launch_allowed'])
        self.assertEqual(result['status'],'blocked')
        with self.assertRaises(ValueError):self.launch(3)

    def test_missing_original_receipt_cannot_be_overridden_by_policy(self):
        self.init();self.fail_before_turn()
        next((self.s.saved[0]/'records').glob('*-receipt.json')).unlink()
        self.assertFalse(self.launch()['next_launch_allowed'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_diagnostics_and_failed_turn_state_cannot_be_forged_as_startup(self):
        self.init();self.fail_before_turn(rpc_failure={'method':'turn/start','phase':'response',
            'kind':'server_error','code':'internal_error'})
        self.assertFalse(self.launch()['next_launch_allowed'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_no_turn_allowance_is_charged_before_next_authentication(self):
        from test_trial_reservation import SyntheticSchedule, p
        root=self.root/'bounded';root.mkdir(mode=0o700)
        self.s=SyntheticSchedule(root,dict(model_requests=4,tokens=131232,seconds=1260))
        with patch.object(ad,'ROOT',root),patch.object(p,'PINNED_RUNTIME',self.s.f.runtime['runtime_digests']):
            self.init();self.fail_before_turn();self.launch()
            with patch.object(nt,'run') as run,self.assertRaisesRegex(ValueError,'aggregate_budget'):
                self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
            run.assert_not_called()
            self.assertEqual(self.r.status(*self.args())['reserved_initial_turns'],1)

    def test_late_cleanup_edit_revokes_previously_observed_permission(self):
        self.init();self.fail_before_turn();self.assertTrue(self.launch()['next_launch_allowed'])
        folder=self.s.state/self.s.f.experiment['trials'][0]['trial_id']/'one'/'records'
        path=next(folder.glob('*-cleanup.json'));value=json.loads(path.read_text())
        value['watch_uncertain']=True;save(path,value)
        with patch.object(nt,'run') as run,self.assertRaises(ValueError):
            self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
        run.assert_not_called()


class RoutedNoTurnCostTests(unittest.TestCase):
    def test_early_natural_failure_needs_exact_finalization_but_no_selected_model(self):
        import tempfile
        from test_trial_admission import RoutedAttempts
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();fixture=RoutedAttempts(root);ref=fixture.attempt()
            folder=Path(ref['attempt_path'])/'records'
            manifest=json.loads((Path(ref['attempt_path'])/'manifest.json').read_text())
            routing=nt.protocol.RoutingObserver(manifest['routing'],nt.routing_profile_digest(manifest)).finish(False,{})
            for path in sorted(folder.iterdir()):
                label=path.name.split('-',1)[1][:-5];value=json.loads(path.read_text())
                if label=='usage_snapshot':path.unlink();continue
                if label in ('observation','observation_finalized','receipt'):
                    observation=value['observation'] if label=='receipt' else value
                    observation.update(status='blocked',reason='protocol_refusal',terminal_completed=False,
                        initial_turns=0,initial_turn_requests_attempted=0,auth_chatgpt_observed=False,
                        usage={'first':None,'latest':None,'all_changed_snapshots_persisted':True,'stop':None},
                        rpc_failure={'method':'account/read','phase':'response','kind':'server_error','code':'internal_error'})
                    observation.pop('model_selection',None)
                    if label!='observation':observation['routing_observation']=routing
                    if label=='receipt':value['status']='blocked'
                if label=='routing_observation':value=routing
                save(path,value)
            for index,path in enumerate(sorted(folder.iterdir()),1):
                path.rename(folder/(f'{index:03d}-'+path.name.split('-',1)[1]))
            with patch.object(ad,'ROOT',root):
                ctx=ad.load_context(fixture.experiment,fixture.spec,fixture.context_path)
                row={'trial_id':ref['trial_id'],'attempt_id':ref['attempt_id'],
                     'manifest_digest':ad.p.digest(manifest),'limits':manifest['limits']}
                # Cost facts use the same path binding as a reservation context.
                ctx.data['execution_root']=str(root/'state')
                guard=ad.Guard();facts=ad.read_cost_facts(ctx,row,guard)
                self.assertTrue(facts['no_turn_cleanup_verified'])
                self.assertFalse(facts['complete']);self.assertIsNone(facts['known_tokens'])
                self.assertTrue(guard.check())
                path=next(folder.glob('*-observation_finalized.json'));value=json.loads(path.read_text())
                value['initial_turn_requests_attempted']=1;save(path,value)
                self.assertFalse(ad.read_cost_facts(ctx,row,ad.Guard())['no_turn_cleanup_verified'])
