"""Native isolation receipt must require observed boundary and callback evidence."""
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import copy
import sys
import os
import tarfile
import io
import hashlib
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_isolation',ROOT/'scripts/improvement/native_isolation.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)

def fixture():
    checks={'host':'FileNotFoundError','holdout':'FileNotFoundError','other_arm':'FileNotFoundError',
            'symlink':'FileNotFoundError','docker_socket':'FileNotFoundError','root':{'errno':30},
            'udp_2':{'errno':101},'udp_10':{'errno':101},'child_read_exit':1,
            'fixture':'ASSIGNED_FIXTURE','interfaces':['lo']}
    events=[{'binary_version':'codex-cli 0.163.0','binary_sha256':native.BINARY_SHA256},{'native':{'id':1,'result':{'platformOs':'linux'}}},
            {'native':{'id':2,'result':{'data':[{'skills':[{'name':'transport-fixture','enabled':True}]}]}}},
            {'native':{'id':3,'result':{'exitCode':0,'stdout':'ASSIGNED_FIXTURE\nNATIVE_TOOL_OK\n'}}},
            {'native':{'method':'item/completed','params':{'item':{'type':'commandExecution','id':'call_fixture','status':'failed','exitCode':3}}}},
            {'summary':{'terminal':{'params':{'turn':{'status':'completed'}}},'requests':2,
                        'tool_positive':'TOOL_OK','tool_canaries':checks,'broker_bindings':[['127.0.0.1',12345],['::1',12345,0,0]]}}]
    events.append({'preflight':{'network_2':{'errno':101},'network_10':{'errno':101},'status':['NoNewPrivs:\t1','CapEff:\t0000000000000000','Seccomp:\t2'],'interfaces':['lo']}})
    events[-2]['summary']['broker_bindings'] = [['127.0.0.1',12345],['::1',12345,0,0]]
    events[-2],events[-1]=events[-1],events[-2]
    return events,True


def boundary_fixture(stage, image='sha256:fixture'):
    return {'Image':image,'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],
        'SecurityOpt':['no-new-privileges'],'PidMode':'','PidsLimit':128,'Memory':768*1024*1024,
        'MemorySwap':768*1024*1024,'Runtime':'runc','IpcMode':'private','UTSMode':'','UsernsMode':'','CgroupnsMode':'private',
        'DeviceCgroupRules':None,'DeviceRequests':None,'Sysctls':None,'NanoCpus':1000000000,
        'Tmpfs':{'/work':'rw,nosuid,nodev,size=128m,mode=1777','/tmp':'rw,nosuid,nodev,noexec,size=32m,mode=1777'}},
        'Config':{'User':'65532:65532'},'Mounts':[
        {'Source':str(stage/n),'Destination':'/'+n,'Type':'bind','RW':False,'Propagation':'rprivate'} for n in ['runtime','probe']]}

class OrchestrationTests(unittest.TestCase):
    def exercise(self, root, failure=None):
        root=root.resolve()
        state={'removed':False,'commands':[]}
        def result(stdout='',exit=0,reason=None):return {'stdout':stdout,'stderr':'synthetic failure' if exit else '', 'exit':exit,'stop_reason':reason}
        def docker(cmd,*args,**kwargs):
            state['commands'].append(cmd);op=cmd[3]
            if op=='image':return result(json.dumps([{'Architecture':'arm64','Os':'linux','Id':'sha256:fixture'}]))
            if op=='create':
                state['name']=cmd[cmd.index('--name')+1];state['label']=cmd[cmd.index('--label')+1]
                state['stage']=Path(next(x.split('src=')[1].split(',')[0] for x in cmd if 'dst=/runtime' in x)).parent
                self.assertEqual((state['stage']/'probe').stat().st_mode & 0o777,0o755)
                for p in (state['stage']/'probe').iterdir():self.assertEqual(p.stat().st_mode & 0o777,0o644)
                if failure=='create':return result(exit=1)
                if failure=='timeout':return result(exit=-9,reason='timeout')
                return result('a'*64+'\n')
            if op=='inspect':
                info=boundary_fixture(state['stage']);info['Config']['Labels']=dict([state['label'].split('=',1)])
                info.update(Id='a'*64,Name='/'+state['name'],State={'ExitCode':0,'Running':False,'OOMKilled':False})
                if failure=='boundary-cleanup':info['HostConfig']['NetworkMode']='host'
                return result(json.dumps([info]))
            if op=='start':
                return result(('[]\n' if failure=='malformed' else '{bad json\n') if failure in ('malformed','malformed-json') else ''.join(json.dumps(x)+'\n' for x in fixture()[0]))
            if op=='ps':return result('' if state['removed'] or failure in ('create','timeout') else 'a'*64+'\n')
            if op=='rm':
                if failure in ('cleanup','boundary-cleanup'):return result(exit=1)
                state['removed']=True;return result('a'*64+'\n')
            raise AssertionError(cmd)
        def extract(archive,destination):
            if failure=='precreate':raise ValueError('synthetic_archive_failure')
            destination.mkdir()
        old=os.umask(0o077)
        try:
            with patch.object(native,'run',side_effect=docker),patch.object(native,'extract_verified',side_effect=extract):
                receipt=native.qualify(root/'evidence','fixture',root/'archive',root)
        finally:os.umask(old)
        self.assertEqual((root/'evidence').stat().st_mode & 0o777,0o700)
        self.assertEqual((root/'evidence/receipt.json').stat().st_mode & 0o777,0o600)
        return receipt,state
    def test_success_and_private_receipt_under_restrictive_umask(self):
        with tempfile.TemporaryDirectory() as t:
            r,s=self.exercise(Path(t));self.assertEqual(r['status'],'pass');self.assertTrue(r['cleanup_complete'])
            self.assertFalse(s['stage'].exists())
    def test_precreate_and_create_failures_cleanup(self):
        for failure in ('precreate','create'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
                r,s=self.exercise(Path(t),failure);self.assertEqual(r['status'],'blocked');self.assertTrue(r['cleanup_complete'])
                self.assertFalse(list(Path(t).glob('native-isolation-*')))
    def test_cleanup_failure_preserves_primary_reason_and_owned_staging(self):
        with tempfile.TemporaryDirectory() as t:
            r,s=self.exercise(Path(t),'boundary-cleanup');self.assertEqual(r['reason'],'container_boundary_mismatch')
            self.assertEqual(r['cleanup_reason'],'container_cleanup_failed');self.assertFalse(r['native_client_qualified'])
            self.assertTrue(Path(r['retained_staging']).exists());self.assertEqual(r['status'],'blocked')
    def test_unconfirmed_timedout_create_cannot_claim_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            r,s=self.exercise(Path(t),'timeout');self.assertFalse(r['cleanup_complete']);self.assertEqual(r['status'],'blocked')
            self.assertEqual(r['cleanup_reason'],'create_outcome_uncertain');self.assertTrue(Path(r['retained_staging']).exists())
    def test_malformed_native_json_never_qualifies_or_escapes_with_traceback(self):
        for failure in ('malformed','malformed-json'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
                r,s=self.exercise(Path(t),failure);self.assertFalse(r['native_client_qualified']);self.assertTrue(r['cleanup_complete'])
    def test_cleanup_failure_revokes_otherwise_successful_qualification(self):
        with tempfile.TemporaryDirectory() as t:
            r,s=self.exercise(Path(t),'cleanup');self.assertEqual(r['status'],'blocked')
            self.assertFalse(r['native_client_qualified']);self.assertFalse(r['cleanup_complete'])
            self.assertTrue(Path(r['retained_staging']).exists())
    def test_cleanup_never_removes_another_owners_container(self):
        commands=[]
        def checked(cmd):
            commands.append(cmd)
            if cmd[3]=='ps':return 'a'*64+'\n'
            if cmd[3]=='inspect':return json.dumps([{'Id':'a'*64,'Name':'/other','Config':{'Labels':{'agent-dotfiles.native-isolation':'other'}}}])
            raise AssertionError('Unowned removal attempted')
        with patch.object(native,'checked',side_effect=checked):
            with self.assertRaisesRegex(ValueError,'cleanup_ownership_mismatch'):
                native.cleanup_owned(['docker','--context','fixture'],'owned')
        self.assertFalse(any(cmd[3]=='rm' for cmd in commands))

class NativeIsolationTests(unittest.TestCase):
    def test_observed_native_synthetic_path_qualifies(self):
        self.assertTrue(native.evaluate(*fixture()))
    def test_no_boundary_or_missing_native_tool_never_qualifies(self):
        events,_=fixture();self.assertFalse(native.evaluate(events,False))
        self.assertFalse(native.evaluate([x for x in events if x.get('native',{}).get('method')!='item/completed'],True))
    def test_missing_or_failed_canary_is_not_denial_evidence(self):
        events,boundary=fixture();del events[-1]['summary']['tool_canaries']['holdout']
        self.assertFalse(native.evaluate(events,boundary))
        events,boundary=fixture();events[-1]['summary']['tool_canaries']['udp_10']={'errno':111}
        self.assertFalse(native.evaluate(events,boundary))
    def test_turn_completion_does_not_establish_tool_exit_or_mock_requests(self):
        events,boundary=fixture();events[4]['native']['params']['item']['exitCode']=0
        self.assertFalse(native.evaluate(events,boundary))
        events,boundary=fixture();events[-1]['summary']['requests']=1
        self.assertFalse(native.evaluate(events,boundary))
    def test_inspected_boundary_rejects_expanded_mounts_network_and_capabilities(self):
        stage=Path('/owned')
        info=boundary_fixture(stage)
        self.assertTrue(native.verify_boundary(info,stage,'sha256:fixture'))
        for key,value in [('NetworkMode','host'),('CapAdd',['SYS_ADMIN']),('Privileged',True),('ReadonlyRootfs',False),('PidMode','host')]:
            changed=copy.deepcopy(info);changed['HostConfig'][key]=value
            self.assertFalse(native.verify_boundary(changed,stage,'sha256:fixture'),key)
        changed=copy.deepcopy(info);changed['Mounts'].append({'Source':'/home','Destination':'/home'})
        self.assertFalse(native.verify_boundary(changed,stage,'sha256:fixture'))
        changed=copy.deepcopy(info);changed['Mounts'][0]['RW']=True
        self.assertFalse(native.verify_boundary(changed,stage,'sha256:fixture'))
    def test_changed_native_binary_is_not_qualified(self):
        events,boundary=fixture();events[0]['binary_sha256']='0'*64
        self.assertFalse(native.evaluate(events,boundary))
    def test_fixed_invocation_has_no_secret_or_host_socket_delivery(self):
        args=native.container_args('fixture','owned',Path('/staging'))
        self.assertIn('--pull',args);self.assertIn('never',args);self.assertNotIn('--env',args)
        self.assertEqual(args.count('--mount'),2);self.assertNotIn('docker.sock',' '.join(args))
    def test_tcp_errno_seccomp_and_mock_bindings_are_observed(self):
        for field in ('network_2','network_10'):
            events,_=fixture();events[-2]['preflight'][field]={'errno':None}
            self.assertFalse(native.evaluate(events,True))
        events,_=fixture();events[-2]['preflight']['status']=['CapEff:\t0000000000000000','NoNewPrivs:\t1','Seccomp:\t0']
        self.assertFalse(native.evaluate(events,True))
        events,_=fixture();events[-1]['summary']['broker_bindings'][1][0]='::'
        self.assertFalse(native.evaluate(events,True))
        self.assertFalse(native.evaluate([[],None],True))
    def test_expanded_runtime_namespace_devices_swap_or_image_rejected(self):
        stage=Path('/owned');info=boundary_fixture(stage)
        for key,value in [('Runtime','alternate'),('IpcMode','host'),('UTSMode','host'),('UsernsMode','host'),
                          ('CgroupnsMode','host'),('DeviceCgroupRules',['a']),('DeviceRequests',[{}]),
                          ('Sysctls',{'kernel.shmmax':'123'}),('MemorySwap',-1)]:
            changed=copy.deepcopy(info);changed['HostConfig'][key]=value
            self.assertFalse(native.verify_boundary(changed,stage,'sha256:fixture'),key)
        self.assertFalse(native.verify_boundary(info,stage,'sha256:other'))
    def test_archive_replacement_cannot_change_extracted_payload(self):
        with tempfile.TemporaryDirectory() as t:
            archive=Path(t)/'archive.tar';replacement=Path(t)/'replacement.tar'
            def make(path,content):
                with tarfile.open(path,'w') as tf:
                    for name,body in [('bin/codex',b'fixture'),('extra',content)]:
                        m=tarfile.TarInfo(name);m.size=len(body);tf.addfile(m,io.BytesIO(body))
            make(archive,b'verified');make(replacement,b'swapped')
            expected=native.file_hash(archive);original_open=tarfile.open
            def swapping_open(*args,**kwargs):
                archive.write_bytes(replacement.read_bytes())
                return original_open(*args,**kwargs)
            with patch.object(native,'ARCHIVE_SHA256',expected),patch.object(native,'BINARY_SHA256',hashlib.sha256(b'fixture').hexdigest()),patch.object(tarfile,'open',side_effect=swapping_open):
                native.extract_verified(archive,Path(t)/'runtime')
            self.assertEqual((Path(t)/'runtime/extra').read_bytes(),b'verified')
    def test_wrong_archive_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive=Path(temporary)/'not-official';archive.write_bytes(b'not the official package')
            with self.assertRaisesRegex(ValueError,'unsupported_archive_digest'):
                native.extract_verified(archive,Path(temporary)/'runtime')
            self.assertFalse((Path(temporary)/'runtime').exists())
    def test_timeout_and_output_limit_stop_the_transport_client(self):
        result=native.run([sys.executable,'-c','import time; print("started",flush=True); time.sleep(10)'],timeout=.2)
        self.assertEqual(result['stop_reason'],'timeout');self.assertIn('started',result['stdout'])
        result=native.run([sys.executable,'-c','print("x"*100000)'],limit=100)
        self.assertEqual(result['stop_reason'],'output_limit');self.assertLessEqual(len(result['stdout'])+len(result['stderr']),100)
if __name__=='__main__':unittest.main()
