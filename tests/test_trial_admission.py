"""Actual local collector with explicitly synthetic native journals; no inference."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.improvement import evaluation as ev, native_trial_results as collector


class ArtifactGradingTests(unittest.TestCase):
    def test_actual_snapshot_digest_is_not_rehashed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'result.bin').write_bytes(b'correct\x00\xff')
            row = collector.collect(root, ['result.bin'])['files'][0]
        criterion = dict(id='bytes', dimension='outcome', kind='artifact_sha256',
                         target='result.bin', expected=hashlib.sha256(b'correct\x00\xff').hexdigest(), critical=True)
        self.assertEqual(ev.grade_check(criterion, {'evidence_kind':'native_artifact_snapshot_v1',
                         'artifacts':{'result.bin':row}}), 'pass')

import copy
import fcntl
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch
from scripts.improvement import trial_admission as ad, native_trial_plan as p, native_usage
nt = ad.nt
from test_improvement_evaluation import spec as legacy_spec


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(ev.encoded(value)); path.chmod(0o600)


class SyntheticAttempts:
    """Synthetic trusted repo/journals; ONLY collector file reads are actual."""
    def __init__(self, root):
        self.root = root
        self.spec = legacy_spec(); self.spec['repetitions'] = 1
        self.spec['identities']['grader'] = ad.native_grader_identity()
        self.spec['runtime'].update(provider='openai', model='gpt-6-luna', client='codex-0.163.0',
                                    adapter=p.PROFILE, reasoning='low')
        self.sources = {n: hashlib.sha256((p.SOURCE/n).read_bytes()).hexdigest() for n in p.SOURCE_NAMES}
        self.runtime = dict(profile=p.PROFILE, source_digests=self.sources, image_digest='sha256:'+'e'*64,
                            metadata_digest='f'*64, runtime_digests={})
        self.executables = {}
        for name in ('codex','code_mode_host','docker','executor_archive'):
            file = root/name; file.write_bytes(b'synthetic executable: '+name.encode())
            self.executables[name] = str(file)
            self.runtime['runtime_digests'][name] = hashlib.sha256(file.read_bytes()).hexdigest()
        arms = {}
        for arm in ev.ARMS:
            folder=root/arm;folder.mkdir();(folder/'skill.md').write_text('synthetic '+arm)
            value={'root':str(folder),'entrypoint':'skill.md', 'files':[{'path':'skill.md','sha256':hashlib.sha256((folder/'skill.md').read_bytes()).hexdigest()}]}
            arms[arm]=value;self.spec['identities'][arm]=ev.digest({k:value[k] for k in ('entrypoint','files')})
        self.spec['identities'].update(runner=ev.digest(self.sources),environment=ev.digest({k:v for k,v in self.runtime.items() if k!='source_digests'}))
        for variants in self.spec['checks'].values():
            for checks in variants.values():
                checks['criteria']=[dict(id='result',dimension='outcome',kind='artifact_sha256',target='result.bin',expected=hashlib.sha256(b'correct\x00\xff').hexdigest(),critical=True)]
        self.experiment=ev.freeze(self.spec)
        declaration=dict(schema_version=1,paths=['result.bin'],max_file_bytes=65536,max_total_bytes=262144)
        self.context={'schema_version':1,'kind':'native_artifact_admission_context_v1','experiment_digest':self.experiment['experiment_digest'],
                      'arms':arms,'runtime':self.runtime,'qualification_refs':{},
                      'collection_by_trial':{t['trial_id']:declaration for t in self.experiment['trials']}}
        common={k:self.runtime[k] for k in ('profile','source_digests','runtime_digests','image_digest')}
        execution={**common,'authenticated':{'status':'qualified_current_profile','qualification':{'boundary_checks_verified':True},'matching_completed_terminal':True},'cleanup':{'automatic_owned_cleanup_complete':True}}
        io={'fixture_read':True,'task_write_readback':True,'denied':{k:{op:2 for op in ('read_errno','write_errno','create_errno')} for k in ('grading','other_arm','installer_receipt','installer_journal')}}
        grading={**common,'grader_source_sha256':ev.source_hash(),
                 'admission_grader_source_digests':ad.native_grader_sources(),'status':'credential_free_scoped_executor_verified',
                 'actual_checks':{'protected_files_exist_outside_mounts_and_unchanged_after_shutdown':True,'scoped_io':{'direct':io,'child':io}},
                 'cleanup':{k:True for k in ('owned_processes_and_groups_absent','owned_containers_absent','owned_volumes_absent')}}
        collection={**common,'status':'credential_free_collection_verified','cases':[dict(case=k,expected_runtime_behavior_observed=True,cleanup_and_fixture_root_absent=True,independent_process_groups_containers_volumes_control_absent=True) for k in ('present-missing','unsafe','interrupted')]}
        for name,record in zip(ad.QUALIFICATIONS,(execution,grading,collection)):
            path=root/ad.QUALIFICATIONS[name];save(path,record)
            self.context['qualification_refs'][name]={'path':ad.QUALIFICATIONS[name],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        self.context_path=root/'context.json';save(self.context_path,self.context)

    def attempt(self, index=0, *, content=b'correct\x00\xff', attempt='one', total=160):
        t=self.experiment['trials'][index]; identity={**t,'attempt_id':attempt,'experiment_digest':self.experiment['experiment_digest']}
        root=self.root/'state'; root.mkdir(exist_ok=True,mode=0o700)
        folder=root/t['trial_id']/attempt;folder.mkdir(parents=True,mode=0o700)
        folder.parent.chmod(0o700);(folder/'coordinator.lock').touch(mode=0o600)
        selected=next(c for c in self.spec['cases'] if c['case_id']==t['case_id']);part=selected if t['variant']=='reproduction' else selected['counterpart']
        files=[dict(kind='case',path=n,sha256=hashlib.sha256(v.encode()).hexdigest()) for n,v in sorted(part['inputs']['files'].items())]
        arm=self.context['arms'][t['arm']];files += [dict(f,kind='bundle') for f in arm['files']]
        manifest=dict(schema_version=1,profile=p.PROFILE,mode='trial',identity=identity,inputs={'root':str(self.root),'entrypoint':'skill.md','files':files},prompt=part['inputs']['request'],
            runtime={**self.executables,'hashes':self.runtime['runtime_digests'],'image':self.runtime['image_digest'],'metadata_digest':self.runtime['metadata_digest'],'docker_host':'unix:///synthetic.sock'},
            limits=p.LIMITS,sources=self.sources,state_root=str(root),collection=self.context['collection_by_trial'][t['trial_id']])
        save(folder/'manifest.json',manifest);digest=p.digest(manifest)
        out=self.root/('output-'+str(index)+'-'+attempt);out.mkdir()
        if content is not None:(out/'result.bin').write_bytes(content)
        snapshot=collector.collect(out,['result.bin'])
        totals=dict.fromkeys(native_usage.FIELDS,0);totals.update(totalTokens=total,inputTokens=100,outputTokens=10)
        snap={'sequence':1,'total':totals,'presence':{'total':dict.fromkeys(native_usage.FIELDS,True)},'cumulative_discontinuity':False}
        usage={'first':snap,'latest':snap,'all_changed_snapshots_persisted':True,'stop':None}
        observation={'status':'completed_ungraded','terminal_completed':True,'initial_turns':1,'initial_turn_requests_attempted':1,'reason':None,'usage':usage,'model_requested':'gpt-6-luna','auth_chatgpt_observed':True}
        cleanup=dict(complete=True,processes_stopped=True,control_absent=True,volume_absent=True,native_home={'home_absent':True,'auth_absent':True},process_query_uncertain=False,watch_uncertain=False,protected_synthetic_files_unchanged_after_shutdown=None)
        collection=dict(manifest_digest=digest,collection_digest=p.digest(manifest['collection']),collector_source_digest=self.sources['native_trial_results.py'],container_id='c'*64,status='captured',reason=None,snapshot=snapshot)
        boundary=dict(docker_settings_verified=True,arm_inventory_exact=True,arm_write_errno=30,mount_write_errno=30,uid=65532,cap_eff='0000000000000000',no_new_privs='1',seccomp='2',loopback_only=True,runtime_digest=nt.EXECUTOR_SHA256)
        for kind in ('case','bundle'):boundary[kind+'_digest']=p.digest([{'path':f['path'],'sha256':f['sha256']} for f in files if f['kind']==kind])
        receipt=dict(status='completed_ungraded',mode='trial',manifest_digest=digest,identity=identity,source_digests=self.sources,runtime_digests=self.runtime['runtime_digests'],image_digest=self.runtime['image_digest'],observation=observation,cleanup=cleanup,collection=collection,capture_failed=False,protected_synthetic_files_unchanged=None)
        entries=[('frozen_binding',dict(manifest_digest=digest,identity=identity,profile=p.PROFILE)),('executor_boundary',boundary),
                 ('container_owner',dict(kind='executor',id='c'*64,name=nt.resource_names(identity)['executor'])),('native_launch_complete',{'pid':999999}),
                 ('usage_snapshot',snap),('observation',observation),('collection_intent',{'collection_digest':p.digest(manifest['collection'])}),('collection_result',collection),('cleanup',cleanup),('receipt',receipt)]
        for i,(label,value) in enumerate(entries,1):save(folder/'records'/f'{i:03d}-{label}.json',value)
        return {'trial_id':t['trial_id'],'attempt_id':attempt,'attempt_path':str(folder)}

    def mutate(self, ref, label, function):
        path=next((Path(ref['attempt_path'])/'records').glob('*-'+label+'.json'))
        value=json.loads(path.read_text());function(value);save(path,value)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.fixture=SyntheticAttempts(self.root)
        self.patch=patch.object(ad,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)

    def report(self, refs, mutate=None):
        f=self.fixture;ctx=ad.load_context(f.experiment,f.spec,f.context_path)
        batch=ad.read_attempts(ctx,refs)
        try:
            if mutate:mutate(batch)
            return ev.compare(f.experiment,[],f.spec,native=batch)
        finally:batch.close()

    def test_actual_good_wrong_missing_and_unsubmitted(self):
        refs=[self.fixture.attempt(0),self.fixture.attempt(1,content=b'wrong'),self.fixture.attempt(2,content=None)]
        r=self.report(refs)
        self.assertEqual(r['counts'],{'pass':1,'fail':2,'blocked':0,'inconclusive':1})
        self.assertEqual(r['coverage']['missing'],1);self.assertEqual(r['paired_summary']['scheduled_pairs'],2)
        self.assertEqual(r['usage']['known_tokens'],480);self.assertIsNone(r['usage']['total_tokens'])
        self.assertEqual(r['dimensions']['routing']['inconclusive'],4)
        self.assertFalse(r['live_eligible']);self.assertFalse(r['quiescent_state_verified'])

    def test_unauthenticated_current_qualification_blocks_but_keeps_usage(self):
        ref=self.fixture.attempt();path=self.root/ad.QUALIFICATIONS['execution']
        value=json.loads(path.read_text());value['authenticated']['status']='unqualified';save(path,value)
        self.fixture.context['qualification_refs']['execution']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        save(self.fixture.context_path,self.fixture.context)
        r=self.report([ref]);self.assertEqual(r['counts']['pass'],0)
        self.assertIn('qualification_unavailable',r['blockers']);self.assertEqual(r['usage']['known_tokens'],160)

    def test_duplicate_same_attempt_does_not_double_charge(self):
        ref=self.fixture.attempt();r=self.report([ref,ref])
        self.assertEqual(r['coverage']['duplicate_trials'],1);self.assertEqual(r['usage']['known_tokens'],160)
        self.assertEqual(r['usage']['known_records'],1);self.assertEqual(r['usage']['submissions'],2)

    def assert_blocked_attempt_accounting(self, report, ref, known_tokens):
        trial=next(row for row in report['trials'] if row['trial_id']==ref['trial_id'])
        self.assertEqual(trial['verdict'],'blocked')
        self.assertEqual(report['counts'],{'pass':0,'fail':0,'blocked':1,'inconclusive':3})
        known=known_tokens is not None
        self.assertEqual(trial['usage']['known_tokens'],known_tokens if known else 0)
        self.assertEqual(trial['usage']['known_records'],int(known))
        self.assertEqual(trial['usage']['unknown'],0 if known else 1)
        self.assertEqual(trial['usage']['total_tokens'],known_tokens)
        self.assertEqual(report['usage']['known_tokens'],known_tokens if known else 0)
        self.assertEqual(report['usage']['unknown'],3 if known else 4)
        self.assertIsNone(report['usage']['total_tokens'])

    def test_missing_capture_or_cleanup_never_passes(self):
        for label,absent,known_tokens in [('collection_result',False,160),
                ('collection_result',True,160),('cleanup',False,160),
                ('cleanup',True,None),('receipt',False,160),('receipt',True,None)]:
            with self.subTest(label=label,absent=absent):
                ref=self.fixture.attempt(attempt=label+('-absent' if absent else '-blocked'))
                if absent:
                    # Keep a valid contiguous synthetic journal while omitting the
                    # required record; do not accidentally test only a sequence gap.
                    folder=Path(ref['attempt_path'])/'records'
                    records=[(path.name.split('-',1)[1],json.loads(path.read_text()))
                             for path in sorted(folder.iterdir())
                             if not path.name.endswith('-'+label+'.json')]
                    for path in folder.iterdir():path.unlink()
                    for index,(name,value) in enumerate(records,1):save(folder/f'{index:03d}-{name}',value)
                else:
                    change=lambda row:row.update(complete=False) if label=='cleanup' else row.update(status='blocked')
                    self.fixture.mutate(ref,label,change)
                    if label!='receipt':
                        key='collection' if label=='collection_result' else 'cleanup'
                        self.fixture.mutate(ref,'receipt',lambda row:change(row[key]))
                self.assert_blocked_attempt_accounting(self.report([ref]),ref,known_tokens)

    def test_late_journal_change_blocks_and_source_flags_are_not_authority(self):
        ref=self.fixture.attempt()
        r=self.report([ref],lambda _:self.fixture.mutate(ref,'collection_result',lambda x:x.update(status='blocked')))
        self.assertEqual(r['counts']['pass'],0)
        with self.assertRaises(ev.Invalid):ev.compare(self.fixture.experiment,[],self.fixture.spec,native={'verified':True})

    def test_active_lock_and_unknown_attempt_remain_blocked_with_unknown_cost(self):
        ref=self.fixture.attempt(); lock=os.open(Path(ref['attempt_path'])/'coordinator.lock',os.O_RDWR)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assert_blocked_attempt_accounting(self.report([ref]),ref,None)
        finally:os.close(lock)
        missing=dict(ref,attempt_path=str(self.root/'absent'))
        r=self.report([missing]);self.assertEqual(r['submitted'],1)
        self.assert_blocked_attempt_accounting(r,missing,None)

    def test_failed_terminal_retains_known_usage(self):
        ref=self.fixture.attempt()
        change=lambda x:x.update(status='blocked',reason='deadline',terminal_completed=False)
        self.fixture.mutate(ref,'observation',change)
        def update(r):change(r['observation']);r['status']='blocked'
        self.fixture.mutate(ref,'receipt',update)
        report=self.report([ref]);self.assertEqual(report['counts']['pass'],0)
        self.assertEqual(report['usage']['known_tokens'],160)

    def test_distinct_attempts_and_unscheduled_reference_are_not_filtered(self):
        one=self.fixture.attempt();two=self.fixture.attempt(attempt='two',total=170)
        bad=dict(one,trial_id='0'*64)
        report=self.report([one,two,bad])
        self.assertEqual(report['submitted'],3);self.assertEqual(report['coverage']['unassigned'],1)
        self.assertEqual(report['usage']['known_tokens'],330);self.assertGreater(report['usage']['unknown'],0)
        self.assertEqual(report['trials'][0]['reason'],'duplicate_completion')

    def test_receipt_snapshot_and_identity_changes_block(self):
        for field in ('manifest_digest','source_digests','identity','collection'):
            with self.subTest(field=field):
                ref=self.fixture.attempt(attempt=field)
                self.fixture.mutate(ref,'receipt',lambda r:r.update({field:None}))
                self.assertEqual(self.report([ref])['counts']['pass'],0)

    def test_unsafe_manifest_and_record_types_block(self):
        for kind in ('symlink','hardlink','mode','fifo'):
            with self.subTest(kind=kind):
                ref=self.fixture.attempt(attempt=kind);path=Path(ref['attempt_path'])/'manifest.json'
                if kind=='mode':path.chmod(0o644)
                elif kind=='hardlink':os.link(path,path.with_name('alias'))
                else:
                    path.unlink()
                    if kind=='symlink':path.symlink_to(self.fixture.context_path)
                    else:os.mkfifo(path,0o600)
                self.assertEqual(self.report([ref])['counts']['pass'],0)

    def test_mutated_context_or_typed_batch_and_mixed_inputs_refuse(self):
        ref=self.fixture.attempt()
        self.assertEqual(self.report([ref],lambda b:b.rows[0]['artifacts'].clear())['counts']['pass'],0)
        f=self.fixture;ctx=ad.load_context(f.experiment,f.spec,f.context_path);batch=ad.read_attempts(ctx,[ref])
        try:
            with self.assertRaises(ev.Invalid):ev.compare(f.experiment,[{}],f.spec,native=batch)
        finally:batch.close()

    def test_cumulative_usage_conflict_stays_unknown(self):
        ref=self.fixture.attempt();self.fixture.mutate(ref,'usage_snapshot',lambda r:r['total'].update(totalTokens=999))
        report=self.report([ref]);self.assertEqual(report['counts']['pass'],0)
        self.assertEqual(report['usage']['known_tokens'],0);self.assertIsNone(report['usage']['total_tokens'])

    def test_unscheduled_owned_attempt_preserves_known_cost(self):
        ref=self.fixture.attempt()
        # A structurally bound own attempt from another frozen schedule remains
        # unassigned, but verified usage is still an actual cost observation.
        new='0'*64;old=Path(ref['attempt_path']);newpath=old.parent.parent/new/ref['attempt_id']
        newpath.parent.mkdir(mode=0o700);old.rename(newpath)
        manifest=json.loads((newpath/'manifest.json').read_text());manifest['identity']['trial_id']=new
        save(newpath/'manifest.json',manifest);digest=p.digest(manifest)
        ref.update(trial_id=new,attempt_path=str(newpath))
        self.fixture.mutate(ref,'frozen_binding',lambda r:r.update(identity=manifest['identity'],manifest_digest=digest))
        self.fixture.mutate(ref,'receipt',lambda r:r.update(identity=manifest['identity'],manifest_digest=digest))
        report=self.report([ref]);self.assertEqual(report['coverage']['unassigned'],1)
        self.assertEqual(report['usage']['known_tokens'],160)

    def test_public_cli_accepts_only_reader_produced_native_batch(self):
        ref=self.fixture.attempt()
        shutil.copytree(p.SOURCE,self.root/'scripts/improvement',ignore=shutil.ignore_patterns('__pycache__'))
        request={'experiment':self.fixture.experiment,'current_spec':self.fixture.spec,
                 'context_path':str(self.fixture.context_path),'attempts':[ref]}
        result=subprocess.run([sys.executable,str(self.root/'scripts/improvement/trial_admission.py'),'report'],
                              input=json.dumps(request),text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertEqual(json.loads(result.stdout)['counts']['pass'],1)

    def test_conflicting_same_attempt_cost_is_unknown(self):
        ref=self.fixture.attempt();f=self.fixture
        second=self.root/'other-state'/ref['trial_id']/ref['attempt_id']
        shutil.copytree(ref['attempt_path'],second);second.parent.parent.chmod(0o700);second.parent.chmod(0o700)
        manifest=json.loads((second/'manifest.json').read_text());manifest['state_root']=str(second.parent.parent)
        save(second/'manifest.json',manifest);digest=p.digest(manifest)
        other=dict(ref,attempt_path=str(second))
        f.mutate(other,'frozen_binding',lambda r:r.update(manifest_digest=digest))
        f.mutate(other,'receipt',lambda r:r.update(manifest_digest=digest))
        r=self.report([ref,other]);self.assertEqual(r['usage']['known_tokens'],0)
        self.assertIsNone(r['usage']['total_tokens']);self.assertEqual(r['coverage']['duplicate_trials'],1)

    def test_late_drift_keeps_critical_failure_and_closed_batch_blocks(self):
        ref=self.fixture.attempt(content=b'wrong');f=self.fixture
        ctx=ad.load_context(f.experiment,f.spec,f.context_path);batch=ad.read_attempts(ctx,[ref])
        original=ev.grade_check
        def change_after(check,evidence):
            result=original(check,evidence)
            if evidence.get('evidence_kind')==ad.KIND and evidence.get('artifacts',{}).get('result.bin'):
                f.mutate(ref,'cleanup',lambda r:r.update(complete=False))
            return result
        try:
            with patch.object(ev,'grade_check',side_effect=change_after):
                report=ev.compare(f.experiment,[],f.spec,native=batch)
            self.assertIn('grading_identity_changed',report['blockers'])
            self.assertEqual(report['critical_violations'],1)
        finally:batch.close()
        self.assertFalse(batch.valid(f.experiment,f.spec))

    def test_distinct_failed_attempts_keep_two_critical_diagnostics(self):
        refs=[self.fixture.attempt(content=b'wrong'),self.fixture.attempt(content=b'wrong',attempt='second')]
        report=self.report(refs)
        self.assertEqual(report['critical_violations'],2)
        self.assertEqual(report['coverage']['duplicate_trials'],1)

    def test_wrong_frozen_provider_cannot_label_openai_native_evidence(self):
        f=self.fixture;f.spec['runtime']['provider']='another-provider';f.experiment=ev.freeze(f.spec)
        declaration=next(iter(f.context['collection_by_trial'].values()))
        f.context.update(experiment_digest=f.experiment['experiment_digest'],
                         collection_by_trial={t['trial_id']:declaration for t in f.experiment['trials']})
        save(f.context_path,f.context)
        with self.assertRaises(ev.Invalid):self.report([f.attempt()])

    def test_each_native_helper_changed_after_freeze_refuses_cli(self):
        ref=self.fixture.attempt()
        copied=self.root/'scripts/improvement'
        shutil.copytree(p.SOURCE,copied,ignore=shutil.ignore_patterns('__pycache__'))
        request={'experiment':self.fixture.experiment,'current_spec':self.fixture.spec,
                 'context_path':str(self.fixture.context_path),'attempts':[ref]}
        for name in ('evaluation.py','trial_admission.py','trial_dispatch.py'):
            with self.subTest(helper=name):
                target=copied/name;original=target.read_bytes()
                try:
                    target.write_bytes(original+b'\n# post-freeze drift\n')
                    result=subprocess.run([sys.executable,str(copied/'trial_admission.py'),'report'],
                        input=json.dumps(request),text=True,capture_output=True,timeout=15)
                    self.assertEqual(result.returncode,1,result.stdout)
                    self.assertEqual(json.loads(result.stdout)['status'],'rejected')
                finally:target.write_bytes(original)

    def test_late_helper_drift_blocks_and_preserves_critical_diagnostic(self):
        copied=self.root/'source-copy';shutil.copytree(p.SOURCE,copied,ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('evaluation.py','trial_admission.py','trial_dispatch.py'):
            with self.subTest(helper=name),patch.object(p,'SOURCE',copied):
                target=copied/name;original_bytes=target.read_bytes()
                ref=self.fixture.attempt(content=b'wrong',attempt=name.replace('.','-'))
                original_grade=ev.grade_check
                def change_after(check,evidence):
                    result=original_grade(check,evidence)
                    if evidence.get('evidence_kind')==ad.KIND and evidence.get('artifacts',{}).get('result.bin'):
                        target.write_bytes(original_bytes+b'\n# during-grade drift\n')
                    return result
                try:
                    with patch.object(ev,'grade_check',side_effect=change_after):report=self.report([ref])
                    self.assertIn('grading_identity_changed',report['blockers'])
                    self.assertEqual(report['critical_violations'],1)
                    self.assertEqual(report['counts']['pass'],0)
                finally:target.write_bytes(original_bytes)

    def test_historical_operator_only_proof_does_not_qualify_native_admission(self):
        f=self.fixture;path=self.root/ad.QUALIFICATIONS['grading']
        proof=json.loads(path.read_text());del proof['admission_grader_source_digests'];save(path,proof)
        f.context['qualification_refs']['grading']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        save(f.context_path,f.context)
        report=self.report([f.attempt()])
        self.assertEqual(report['counts']['pass'],0)
        self.assertIn('qualification_unavailable',report['blockers'])
        self.assertEqual(report['usage']['known_tokens'],160)

    def test_dispatch_supports_native_composite_and_preserves_operator_identity(self):
        f=self.fixture
        request={'experiment':f.experiment,'current_spec':f.spec,
                 'trial_id':f.experiment['trials'][0]['trial_id'],'attempt_id':'dispatch-only'}
        result=subprocess.run([sys.executable,str(p.SOURCE/'trial_dispatch.py'),'prepare'],
                              input=json.dumps(request),text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertEqual(json.loads(result.stdout)['kind'],'development_trial_dispatch')
        for provider,identity,accepted in [('openai',ev.source_hash(),True),
                ('other-provider',ad.native_grader_identity(),False)]:
            spec=copy.deepcopy(f.spec);spec['runtime']['provider']=provider
            spec['identities']['grader']=identity;frozen=ev.freeze(spec)
            args=(frozen,spec,frozen['trials'][0]['trial_id'],'dispatch-only')
            if accepted:self.assertEqual(ad.trial_dispatch.prepare(*args)['kind'],'development_trial_dispatch')
            else:
                with self.assertRaises(ev.Invalid):ad.trial_dispatch.prepare(*args)
