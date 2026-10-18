"""Serial control with actual local files/processes; native lifecycle stays synthetic."""
import copy
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.improvement import trial_admission as ad, evaluation as ev
from test_trial_admission import SyntheticAttempts, save
nt, p = ad.nt, ad.p


class ReservationTests(unittest.TestCase):
    def test_changed_reserved_manifest_stops_before_controller(self):
        selected = type('Selected', (), {'digest': 'a'*64})()
        with patch.object(nt.plan, 'load_plan', return_value=selected), patch.object(nt, 'Controller') as controller:
            with self.assertRaisesRegex(nt.plan.Refusal, 'reserved_manifest_changed'):
                nt.run(Path('/synthetic/plan'), auth_source=Path('/synthetic/auth'),
                       expected_manifest_digest='b'*64)
            controller.assert_not_called()


class SyntheticSchedule:
    """Existing synthetic journal factory, moved out of the not-yet-run state root."""
    def __init__(self, root, budget=None):
        self.f = f = SyntheticAttempts(root)
        f.spec['budget'] = budget or dict(model_requests=4, tokens=600000, seconds=1260)
        f.experiment = ev.freeze(f.spec)
        declaration = next(iter(f.context['collection_by_trial'].values()))
        self.state = root/'state'; self.state.mkdir(mode=0o700)
        f.context.update(experiment_digest=f.experiment['experiment_digest'], execution_root=str(self.state),
                         collection_by_trial={t['trial_id']:declaration for t in f.experiment['trials']})
        save(f.context_path, f.context)
        self.plans, self.saved = [], []
        for i, t in enumerate(f.experiment['trials']):
            ref = f.attempt(i); folder = Path(ref['attempt_path'])
            m = json.loads((folder/'manifest.json').read_text()); inputs = root/('input-'+str(i))
            part = ad.trial_dispatch.prepare(f.experiment, f.spec, t['trial_id'], 'one')['executor_input']
            for name, text in part['files'].items():
                path=inputs/'case'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            for item in f.context['arms'][t['arm']]['files']:
                path=inputs/'bundle'/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(Path(f.context['arms'][t['arm']]['root'])/item['path'],path)
            m['inputs']['root']=str(inputs); save(folder/'manifest.json',m);digest=p.digest(m)
            f.mutate(ref,'frozen_binding',lambda r:r.update(manifest_digest=digest))
            f.mutate(ref,'collection_result',lambda r:r.update(manifest_digest=digest))
            def fix(r):r.update(manifest_digest=digest);r['collection']['manifest_digest']=digest
            f.mutate(ref,'receipt',fix)
            plan=root/('plan-'+str(i)+'.json');save(plan,m);self.plans.append(str(plan))
            target=root/('saved-'+str(i));folder.rename(target);folder.parent.rmdir();self.saved.append(target)

    def run(self, path, *, auth_source, expected_manifest_digest):
        m=json.loads(Path(path).read_text());assert p.digest(m)==expected_manifest_digest
        i=self.plans.index(str(path));t=m['identity'];target=self.state/t['trial_id']/t['attempt_id']
        target.parent.mkdir(mode=0o700);shutil.copytree(self.saved[i],target)
        return {'status':'untrusted return dictionary ignored'}


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.s=SyntheticSchedule(self.root)
        self.r=importlib.import_module('scripts.improvement.trial_reservation')
        for obj, name, value in [(ad,'ROOT',self.root),(p,'PINNED_RUNTIME',self.s.f.runtime['runtime_digests'])]:
            patcher=patch.object(obj,name,value);patcher.start();self.addCleanup(patcher.stop)

    def args(self):
        f=self.s.f;return (self.s.state,f.experiment,f.spec,f.context_path)

    def init(self):return self.r.initialize(*self.args(),self.s.plans)

    def launch(self,index=0):
        with patch.object(nt,'run',side_effect=self.s.run):
            return self.r.run_next(*self.args(),self.s.plans[index],Path('/never/open/auth.json'))

    def test_reserve_before_fixed_run_and_account_omitted_completion(self):
        self.init()
        def fixed(path,**kw):
            record=next((self.s.state/self.r.RECORDS).glob('*-reserve.json'))
            self.assertEqual(json.loads(record.read_text())['index'],0)
            self.assertEqual(json.loads(Path(path).read_text())['limits']['cleanup_seconds'],45)
            return self.s.run(path,**kw)
        with patch.object(nt,'run',side_effect=fixed):
            summary=self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        self.assertEqual(summary['known_tokens'],160);self.assertEqual(summary['declared_seconds'],315)
        ctx=ad.load_context(self.s.f.experiment,self.s.f.spec,self.s.f.context_path)
        batch=ad.read_attempts(ctx,[])
        try:report=ev.compare(self.s.f.experiment,[],self.s.f.spec,native=batch)
        finally:batch.close()
        self.assertEqual(report['execution_accounting']['known_tokens'],160)
        self.assertEqual(report['coverage']['missing'],4)
        self.assertNotIn('aggregate_launch_reservation_unavailable',report['blockers'])

    def test_header_allocation_cannot_differ_from_reserved_manifest(self):
        self.init();path=self.s.state/self.r.HEADER;h=json.loads(path.read_text())
        h['schedule'][0]['limits']['soft_total_tokens']=1;save(path,h)
        with patch.object(nt,'run') as run, self.assertRaisesRegex(ValueError,'^reservation_order$'):
            self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        run.assert_not_called()

    def test_real_process_lock_refuses_second_launch_and_is_not_inherited(self):
        self.init()
        code='import fcntl,os,sys; f=open(sys.argv[1],"r+"); fcntl.flock(f,fcntl.LOCK_EX); print("held",flush=True); sys.stdin.readline()'
        child=subprocess.Popen([sys.executable,'-c',code,str(self.s.state/self.r.LOCK)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'held')
            with patch.object(nt,'run') as run, self.assertRaises(OSError):
                self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
            run.assert_not_called()
        finally:child.communicate('\n',timeout=5)
        lease=self.r.Lease(ad.load_context(self.s.f.experiment,self.s.f.spec,self.s.f.context_path))
        try:self.assertFalse(os.get_inheritable(lease.fd))
        finally:lease.close()

    def test_real_crashed_process_never_refunds_outstanding_reservation(self):
        self.init()
        code='''import os,sys,json,fcntl
from pathlib import Path
from scripts.improvement import trial_reservation as r
root=Path(sys.argv[1]);fd=os.open(root/r.LOCK,os.O_RDWR);fcntl.flock(fd,fcntl.LOCK_EX)
h=json.loads((root/r.HEADER).read_text());j,_=r.nt.Journal.resume(root/r.RECORDS,262144)
j.save('reserve',r.reserve_record(h,0));os._exit(23)
'''
        child=subprocess.run([sys.executable,'-c',code,str(self.s.state)],capture_output=True,timeout=10)
        self.assertEqual(child.returncode,23,child.stderr)
        status=self.r.status(*self.args());self.assertEqual(status['reserved_initial_turns'],1)
        self.assertEqual(status['declared_seconds'],315);self.assertEqual(status['unknown_attempts'],1)
        self.assertIsNone(status['total_tokens'])
        with patch.object(nt,'run') as run,self.assertRaises(ValueError):self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
        run.assert_not_called()

    def test_replay_skip_and_second_attempt_do_not_launch(self):
        self.init()
        with self.assertRaises(ValueError):self.launch(1)
        self.launch()
        with patch.object(nt,'run') as run,self.assertRaises(ValueError):
            self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        run.assert_not_called();self.assertEqual(self.r.status(*self.args())['reserved_initial_turns'],1)

    def test_unknown_usage_cleanup_and_failed_terminal_preserve_subtotals(self):
        self.init();self.launch();trial=self.s.f.experiment['trials'][0]
        ref=dict(trial_id=trial['trial_id'],attempt_id='one',attempt_path=str(self.s.state/trial['trial_id']/'one'))
        change=lambda o:o.update(status='blocked',reason='interrupted',terminal_completed=False)
        self.s.f.mutate(ref,'observation',change)
        def receipt(r):change(r['observation']);r['status']='blocked'
        self.s.f.mutate(ref,'receipt',receipt)
        state=self.r.status(*self.args());self.assertEqual(state['known_tokens'],160)
        self.assertEqual(state['unknown_attempts'],1);self.assertIsNone(state['total_tokens'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_complete_native_bad_capture_is_cost_not_task_success(self):
        self.init();folder=self.s.saved[0]
        for label in ['collection_result','receipt']:
            path=next((folder/'records').glob('*-'+label+'.json'));row=json.loads(path.read_text())
            if label=='receipt':row['status']='blocked';row['collection']['status']='blocked'
            else:row['status']='blocked'
            save(path,row)
        result=self.launch();self.assertEqual(result['known_tokens'],160);self.assertEqual(result['status'],'ready')
        self.assertEqual(self.launch(1)['reserved_initial_turns'],2)

    def test_stale_budget_spec_and_current_qualification_refuse_before_launch(self):
        self.init();self.launch()
        for field,value in [('model_requests',1),('seconds',315),('tokens',131231)]:
            with self.subTest(field=field):
                # Frozen-input tampering is not a way to replenish or change a budget.
                spec=copy.deepcopy(self.s.f.spec);spec['budget'][field]=value
                with self.assertRaisesRegex(ValueError,'^stale_experiment$'):self.r.run_next(self.s.state,self.s.f.experiment,spec,self.s.f.context_path,self.s.plans[1],Path('/never/open/auth.json'))
        path=self.root/ad.QUALIFICATIONS['execution'];data=json.loads(path.read_text());data['authenticated']['status']='unqualified';save(path,data)
        with patch.object(nt,'run') as run,self.assertRaisesRegex(ValueError,'^qualification_unavailable$'):self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
        run.assert_not_called()

    def test_partial_journal_and_natural_binding_defense_fail_closed(self):
        self.init();folder=self.s.state/self.r.RECORDS;save(folder/'001-reserve.json',{'partial':True})
        with patch.object(nt,'run') as run,self.assertRaisesRegex(ValueError,'^reservation_records$'):self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        run.assert_not_called()
        ctx=ad.load_context(self.s.f.experiment,self.s.f.spec,self.s.f.context_path)
        m=json.loads(Path(self.s.plans[0]).read_text());m['routing']={'mode':'natural'}
        # load_plan's closed schema is the primary launch-path refusal.
        invalid=self.root/'natural-plan.json';save(invalid,m)
        with self.assertRaisesRegex(ValueError,'^plan_fields$'):p.load_plan(invalid)
        # Direct binding checks only this additional defense-in-depth guard.
        with self.assertRaisesRegex(ValueError,'^natural_admission_unavailable$'):ad.bind_manifest(ctx,m)

    def test_late_ledger_change_invalidates_report_and_retains_costs(self):
        self.init();self.launch();f=self.s.f;ctx=ad.load_context(f.experiment,f.spec,f.context_path)
        batch=ad.read_attempts(ctx,[])
        try:
            path=next((self.s.state/self.r.RECORDS).glob('*-reserve.json'));value=json.loads(path.read_text());value['index']=99;save(path,value)
            self.assertFalse(batch.valid(f.experiment,f.spec))
            self.assertEqual(batch.execution['known_tokens'],160)
        finally:batch.close()

    def test_replaced_stable_lock_is_not_a_new_allowance(self):
        self.init();lock=self.s.state/self.r.LOCK;backup=self.root/'original-lock';lock.rename(backup)
        lock.touch(mode=0o600)
        try:
            with self.assertRaises(ValueError):self.r.status(*self.args())
        finally:lock.unlink();backup.rename(lock)

    def test_real_pre_auth_plan_replacement_preserves_reservation(self):
        self.init();original=nt.run
        def changed(path,**kwargs):
            value=json.loads(Path(path).read_text());value['prompt']='changed synthetic input';save(Path(path),value)
            return original(path,**kwargs)
        with patch.object(nt.plan,'PINNED_RUNTIME',self.s.f.runtime['runtime_digests']), patch.object(nt,'Controller') as controller, patch.object(nt,'run',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'reserved_manifest_changed'):
                self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        controller.assert_not_called()
        self.assertEqual(self.r.status(*self.args())['unknown_attempts'],1)

    def test_fsync_failure_leaves_no_launch_and_no_refund(self):
        self.init()
        with patch.object(nt.os,'fsync',side_effect=OSError('synthetic fsync failure')),patch.object(nt,'run') as run:
            with self.assertRaises(OSError):self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        run.assert_not_called();self.assertEqual(self.r.status(*self.args())['reserved_initial_turns'],1)

    def test_actual_frozen_budget_boundaries(self):
        cases=[('turns',dict(model_requests=1,tokens=600000,seconds=1260),1),
               ('time',dict(model_requests=4,tokens=600000,seconds=315),1),
               ('tokens',dict(model_requests=4,tokens=131072,seconds=1260),1),
               ('token-exact',dict(model_requests=4,tokens=131232,seconds=1260),2),
               ('under',dict(model_requests=4,tokens=131071,seconds=1260),0)]
        for name,budget,count in cases:
            with self.subTest(name=name):
                root=self.root/name;root.mkdir(mode=0o700);s=SyntheticSchedule(root,budget)
                args=(s.state,s.f.experiment,s.f.spec,s.f.context_path)
                with patch.object(ad,'ROOT',root),patch.object(p,'PINNED_RUNTIME',s.f.runtime['runtime_digests']),patch.object(nt,'run',side_effect=s.run) as run:
                    self.r.initialize(*args,s.plans)
                    for i in range(count):self.r.run_next(*args,s.plans[i],Path('/never/open/auth.json'))
                    with self.assertRaisesRegex(ValueError,'aggregate_budget'):self.r.run_next(*args,s.plans[count],Path('/never/open/auth.json'))
                    self.assertEqual(run.call_count,count)
                    self.assertEqual(self.r.status(*args)['reserved_initial_turns'],count)

    def test_unknown_usage_and_overshoot_never_replenish(self):
        self.init();self.launch();t=self.s.f.experiment['trials'][0]
        folder=self.s.state/t['trial_id']/'one'/'records'
        originals={path:path.read_bytes() for path in folder.iterdir()}
        for label in ('usage_snapshot','cleanup'):
            with self.subTest(label=label):
                path=next(folder.glob('*-'+label+'.json'));value=json.loads(path.read_text())
                if label=='usage_snapshot':value['total']['totalTokens']=999
                else:value['complete']=False
                save(path,value)
                state=self.r.status(*self.args());self.assertIsNone(state['total_tokens'])
                self.assertEqual(state['unknown_attempts'],1)
                with patch.object(nt,'run') as run,self.assertRaises(ValueError):self.r.run_next(*self.args(),self.s.plans[1],Path('/never/open/auth.json'))
                run.assert_not_called()
                for path,data in originals.items():path.write_bytes(data)
        for label in ('usage_snapshot','observation','receipt'):
            path=next(folder.glob('*-'+label+'.json'));value=json.loads(path.read_text())
            if label=='usage_snapshot':value['total']['totalTokens']=131073
            else:
                usage=value['usage'] if label=='observation' else value['observation']['usage']
                for k in ('first','latest'):usage[k]['total']['totalTokens']=131073
            save(path,value)
        state=self.r.status(*self.args());self.assertEqual(state['known_tokens'],131073)
        self.assertTrue(state['limits_exceeded'])
        with self.assertRaises(ValueError):self.launch(1)

    def test_durable_record_is_revalidated_before_launch(self):
        self.init();original=nt.Journal.save
        def corrupt(journal,label,value,**kwargs):
            path=original(journal,label,value,**kwargs)
            if label=='reserve':save(path,{'corrupt':True})
            return path
        with patch.object(nt.Journal,'save',new=corrupt),patch.object(nt,'run') as run:
            with self.assertRaises(ValueError):self.r.run_next(*self.args(),self.s.plans[0],Path('/never/open/auth.json'))
        run.assert_not_called()

    def test_mutable_caller_budget_never_replaces_frozen_context_budget(self):
        root=self.root/'mutable';root.mkdir(mode=0o700)
        s=SyntheticSchedule(root,dict(model_requests=4,tokens=131071,seconds=1260))
        args=(s.state,s.f.experiment,s.f.spec,s.f.context_path);original=self.r.selected
        def mutate(ctx,path):
            result=original(ctx,path);s.f.spec['budget']['tokens']=600000;return result
        with patch.object(ad,'ROOT',root),patch.object(p,'PINNED_RUNTIME',s.f.runtime['runtime_digests']):
            self.r.initialize(*args,s.plans)
            with patch.object(self.r,'selected',side_effect=mutate),patch.object(nt,'run') as run:
                with self.assertRaisesRegex(ValueError,'aggregate_budget'):self.r.run_next(*args,s.plans[0],Path('/never/open/auth.json'))
            run.assert_not_called()


    def test_cost_audit_hashes_each_runtime_once_then_finally_for_two_rows(self):
        self.init();self.launch();self.launch(1)
        paths={Path(value) for value in self.s.f.executables.values()}
        counts=dict.fromkeys(paths,0);original=p.read_file
        def counted(path,*args,**kwargs):
            if Path(path) in counts:counts[Path(path)]+=1
            return original(path,*args,**kwargs)
        with patch.object(p,'read_file',side_effect=counted):result=self.r.status(*self.args())
        self.assertEqual(result['known_tokens'],320);self.assertEqual(result['unknown_attempts'],0)
        self.assertEqual(counts,dict.fromkeys(paths,2),
            'Each runtime needs one first full hash and one unconditional final full hash, independent of cost-row count')

    def test_cost_audit_final_guard_rejects_late_runtime_source_and_record_bytes(self):
        self.init();self.launch();self.launch(1)
        copied=self.root/'source-copy';shutil.copytree(p.SOURCE,copied,ignore=shutil.ignore_patterns('__pycache__'))
        first=self.s.f.experiment['trials'][0]
        receipt=next((self.s.state/first['trial_id']/'one'/'records').glob('*-receipt.json'))
        targets=(Path(self.s.f.executables['codex']),copied/'native_usage.py',receipt)
        original=ad.read_cost_facts
        with patch.object(p,'SOURCE',copied):
            for target in targets:
                with self.subTest(target=target.name):
                    before=target.read_bytes();calls=0
                    def changed(*args,**kwargs):
                        nonlocal calls
                        facts=original(*args,**kwargs);calls+=1
                        if calls==2:target.write_bytes(before+b'\n')
                        return facts
                    try:
                        with patch.object(ad,'read_cost_facts',side_effect=changed):
                            with self.assertRaisesRegex(ValueError,'^reservation_changed$'):
                                self.r.status(*self.args())
                        self.assertEqual(calls,2)
                    finally:target.write_bytes(before)
