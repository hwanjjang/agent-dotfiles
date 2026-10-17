"""Native isolation receipt must require observed boundary and callback evidence."""
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import copy
import sys
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
                        'tool_positive':'TOOL_OK','tool_canaries':checks,'dual_family_broker':True,'live_model_calls':0}}]
    return events,True

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
    def test_turn_completion_does_not_establish_tool_exit_or_live_requests(self):
        events,boundary=fixture();events[4]['native']['params']['item']['exitCode']=0
        self.assertFalse(native.evaluate(events,boundary))
        events,boundary=fixture();events[-1]['summary']['live_model_calls']=1
        self.assertFalse(native.evaluate(events,boundary))
    def test_inspected_boundary_rejects_expanded_mounts_network_and_capabilities(self):
        stage=Path('/owned')
        h={'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],
           'SecurityOpt':['no-new-privileges'],'PidMode':'','PidsLimit':128,'Memory':768*1024*1024,
           'NanoCpus':1000000000,'Tmpfs':{'/work':'rw,nosuid,nodev,size=128m,mode=1777','/tmp':'rw,nosuid,nodev,noexec,size=32m,mode=1777'}}
        info={'HostConfig':h,'Config':{'User':'65532:65532'},'Mounts':[
            {'Source':'/owned/'+n,'Destination':'/'+n,'Type':'bind','RW':False,'Propagation':'rprivate'} for n in ['runtime','probe']]}
        self.assertTrue(native.verify_boundary(info,stage))
        for key,value in [('NetworkMode','host'),('CapAdd',['SYS_ADMIN']),('Privileged',True),('ReadonlyRootfs',False),('PidMode','host')]:
            changed=copy.deepcopy(info);changed['HostConfig'][key]=value
            self.assertFalse(native.verify_boundary(changed,stage),key)
        changed=copy.deepcopy(info);changed['Mounts'].append({'Source':'/home','Destination':'/home'})
        self.assertFalse(native.verify_boundary(changed,stage))
        changed=copy.deepcopy(info);changed['Mounts'][0]['RW']=True
        self.assertFalse(native.verify_boundary(changed,stage))
    def test_changed_native_binary_is_not_qualified(self):
        events,boundary=fixture();events[0]['binary_sha256']='0'*64
        self.assertFalse(native.evaluate(events,boundary))
    def test_fixed_invocation_has_no_secret_or_host_socket_delivery(self):
        args=native.container_args('fixture','owned',Path('/staging'))
        self.assertIn('--pull',args);self.assertIn('never',args);self.assertNotIn('--env',args)
        self.assertEqual(args.count('--mount'),2);self.assertNotIn('docker.sock',' '.join(args))
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
