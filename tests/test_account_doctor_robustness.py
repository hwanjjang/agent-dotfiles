"""Failure accounting and process boundaries; fake client transports only."""
import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import account_model_check as model
import account_native as native
import setup_account as setup
from account_doctor import check


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.home=self.root/'home';self.home.mkdir()
        self.project=self.root/'project';self.project.mkdir();(self.project/'requirements.md').write_text('Synthetic')
        self.folder=self.root/'evidence'
        self.sources={name:'Synthetic source '+name for name in model.PAYLOAD}
        for name,body in self.sources.items():
            path=self.home/setup.BUNDLE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        self.receipt={'source_revision':'a'*40,'hooks':{}}

    def test_missing_source_is_structured_and_never_attempted(self):
        (self.home/setup.BUNDLE/model.PAYLOAD[-1]).unlink()
        with patch.object(model,'codex_model_run') as run:
            rows=model.model_checks(self.home,self.receipt,'codex','cheap',False,self.folder,1)
        self.assertEqual(rows[0]['id'],'model.prerequisites');self.assertEqual(rows[0]['status'],'blocked');run.assert_not_called()
        self.assertFalse(json.loads((self.folder/'input.json').read_text())['model_attempted'])

    def test_malformed_protocol_preserves_attempt_before_client_call(self):
        def malformed(*args):
            manifest=json.loads((self.folder/'input.json').read_text())
            self.assertTrue(manifest['model_attempted']);self.assertIsNone(manifest['model_prompt_sent'])
            raise KeyError('synthetic malformed response')
        with patch.object(model,'codex_model_run',side_effect=malformed):
            rows=model.model_checks(self.home,self.receipt,'codex','cheap',False,self.folder,1)
        self.assertEqual(rows[-1]['id'],'model.native');self.assertEqual(rows[-1]['status'],'blocked')
        self.assertTrue(json.loads((self.folder/'input.json').read_text())['model_attempted'])

    def test_single_jsonprocess_deadline_covers_multiple_calls(self):
        script='import sys,json,time\nfor line in sys.stdin:\n r=json.loads(line); time.sleep(.16); print(json.dumps({"id":r["id"],"result":{}}),flush=True)'
        started=time.monotonic();p=native.JsonProcess([sys.executable,'-I','-S','-c',script],self.project,{},.25)
        try:
            p.call(1,'initialize',{})
            with self.assertRaises(native.ProtocolError):p.call(2,'thread/start',{})
        finally:p.close()
        self.assertLess(time.monotonic()-started,.65)

    def test_jsonprocess_deadline_includes_stdin_backpressure(self):
        p=native.JsonProcess([sys.executable,'-I','-S','-c','import time; time.sleep(1.5)'],self.project,{},.2)
        started=time.monotonic()
        try:
            with self.assertRaises(native.ProtocolError):p.send({'prompt':'x'*262144})
        finally:p.close()
        self.assertLess(time.monotonic()-started,.8)
        self.assertIsNotNone(p.process.returncode)
        self.assertFalse(p.writer.is_alive())

    def test_jsonprocess_output_limit_is_structured(self):
        p=native.JsonProcess([sys.executable,'-I','-S','-c','print("x"*1048577,flush=True)'],self.project,{},1)
        try:
            with self.assertRaises(native.ProtocolError):p.receive(lambda _:True)
        finally:p.close()

    def paseo(self,fake):
        self.folder.mkdir()
        with patch.object(model,'run',side_effect=fake),patch.object(model,'paseo_health',return_value=[check('paseo.connection','pass','Synthetic')]),patch.object(model.Path,'home',return_value=self.home):
            return model.paseo_model('codex','cheap','prompt',self.project,{},self.folder,1,'marker',self.sources)

    def test_uncertain_workspace_creation_records_cleanup_block(self):
        rows=self.paseo(lambda *args,**kwargs:('timeout',''))
        self.assertTrue(any(r['id']=='paseo.cleanup' and r['status']=='blocked' for r in rows))
        state=json.loads((self.folder/'paseo-owned.json').read_text())
        self.assertEqual(state['workspace_state'],'uncertain');self.assertEqual(state['requested_mode'],'auto')

    def test_uncertain_agent_creation_keeps_known_cleanup_and_reports_gap(self):
        calls=[]
        def fake(command,*args,**kwargs):
            calls.append(command)
            if command[1:3]==['workspace','create']:return 0,'{"workspaceId":"owned-workspace"}'
            if command[1]=='run':return 'timeout','not JSON'
            return 0,'[]'
        rows=self.paseo(fake)
        self.assertTrue(any(r['id']=='paseo.cleanup' and r['status']=='blocked' for r in rows))
        self.assertIn(['paseo','workspace','archive','owned-workspace','--json'],calls)
        self.assertFalse(any(c[1:3]==['project','delete'] for c in calls))

    def test_cleanup_error_does_not_skip_later_owned_step(self):
        calls=[]
        def fake(command,*args,**kwargs):
            calls.append(command)
            if command[1:3]==['workspace','create']:return 0,'{"workspaceId":"owned-workspace"}'
            if command[1]=='run':return 0,'{"agentId":"owned-agent"}'
            if command[1]=='archive':raise OSError('synthetic failure')
            if command[1:3]==['project','ls']:return 0,'[]'
            return 0,'{}'
        rows=self.paseo(fake)
        self.assertTrue(any(r['id']=='paseo.cleanup' and r['status']=='fail' for r in rows))
        self.assertIn(['paseo','workspace','archive','owned-workspace','--json'],calls)
        self.assertFalse(any(r['id']=='model.native' for r in rows))

    def test_run_timeout_escalates_and_retains_partial_evidence(self):
        self.folder.mkdir()
        class Process:
            pid=12345
            def __init__(self):self.waits=0
            def wait(self,timeout):
                self.waits+=1
                if self.waits<3:raise subprocess.TimeoutExpired('synthetic',timeout)
                return -9
        p=Process()
        with patch.object(model.subprocess,'Popen',return_value=p),patch.object(model.os,'killpg') as kill:
            code,raw=model.run(['synthetic'],self.project,{},1,self.folder,'native')
        self.assertEqual(code,'timeout')
        self.assertEqual([c.args for c in kill.call_args_list],[(12345,signal.SIGTERM),(12345,signal.SIGKILL)])
        self.assertTrue((self.folder/'native.stdout').exists())

    def test_malformed_codex_thread_response_retains_structured_failure(self):
        self.folder.mkdir()
        class Process:
            messages=[]
            def __init__(self,*args):pass
            def send(self,*args):pass
            def close(self):pass
            def call(self,ident,method,params):
                return {'model':'cheap','thread':{}} if method=='thread/start' else {}
        with patch.object(model,'JsonProcess',Process):
            code,_=model.codex_model_run('cheap','prompt',self.project,{},1,self.folder)
        self.assertEqual(code,'protocol-error');self.assertTrue((self.folder/'native.stdout').exists())

    def test_model_grade_wiring_for_exit_integrity_routing_and_session_start(self):
        planning='skills/planning-and-task-breakdown/SKILL.md'
        path=self.home/setup.BUNDLE/planning;path.parent.mkdir(parents=True);path.write_text('Synthetic planning source')
        for index,(scenario,exit_code,mutate,valid_plan) in enumerate([
                ('spec',0,False,True),('spec',1,False,True),('spec',0,True,True),('routing',0,False,False)]):
            with self.subTest(scenario=scenario,exit_code=exit_code,mutate=mutate):
                folder=self.root/('grade-'+str(index))
                def fake(model_id,prompt,project,env,timeout,evidence,schema=None):
                    marker=(project/'requirements.md').read_text().splitlines()[0].split()[1]
                    answer={'scenario':marker,'acceptance':['AC1: greeting'],'verification_executed':False,'remaining_decisions':[],
                            'examples':[dict(argv=a,stdout=o,stderr=e,exit_code=c) for a,o,e,c in
                            [(['Ada'],'Hello, Ada!\n','',0),([],'','Usage: hello NAME\n',2),([''],'','Usage: hello NAME\n',2),(['Ada','Lin'],'','Usage: hello NAME\n',2)]]}
                    if scenario=='routing':answer['tasks']=[]
                    (evidence/'answer.json').write_text(json.dumps(answer))
                    names=model.PAYLOAD+((planning,) if scenario=='routing' else ())
                    output='\n'.join((self.home/setup.BUNDLE/n).read_text() for n in names)
                    events=[{'id':2,'result':{'model':'cheap'}},{'method':'turn/completed','params':{'turn':{'status':'completed'}}},
                            {'type':'item.completed','item':{'type':'command_execution','exit_code':0,'aggregated_output':output}},
                            {'method':'hook/completed','params':{'run':{'eventName':'sessionStart','status':'completed',
                             'sourcePath':str(self.home/'.codex/hooks.json'),'entries':[{'text':'ACCOUNT_DOCTOR_SELECTED_PLAN'}]}}}]
                    if mutate:(self.home/setup.BUNDLE/model.PAYLOAD[0]).write_text('Changed synthetic content')
                    return exit_code,'\n'.join(json.dumps(row) for row in events)
                receipt=dict(self.receipt,hooks={'.codex/hooks.json':{'SessionStart':[]}})
                with patch.object(model,'codex_model_run',side_effect=fake):
                    rows=model.model_checks(self.home,receipt,'codex','cheap',False,folder,1,scenario)
                grade=json.loads((folder/'grade.json').read_text())
                self.assertEqual(grade['passed'],exit_code==0 and not mutate and valid_plan)
                self.assertEqual([r['status'] for r in rows if r['id']=='native.codex.session-start'],['pass'])
                if mutate:self.assertFalse(grade['installed_sources_unchanged'])
                if scenario=='routing':self.assertFalse(grade['plan_verifiable'])
                manifest=json.loads((folder/'input.json').read_text());self.assertTrue(manifest['model_attempted'])

    def test_paseo_exception_cannot_add_contradictory_native_row(self):
        def fake(*args):
            (self.folder/'answer.json').write_text('{}')
            return 0,''
        with patch.object(model,'codex_model_run',side_effect=fake), \
                patch.object(model,'score',return_value={'passed':True}), \
                patch.object(model,'model_identity',return_value={'model_identity_verified':True}), \
                patch.object(model,'paseo_model',side_effect=OSError('synthetic cleanup failure')):
            rows=model.model_checks(self.home,self.receipt,'codex','cheap',True,self.folder,1)
        self.assertEqual([r['status'] for r in rows if r['id']=='model.native'],['pass'])
        self.assertEqual([r['status'] for r in rows if r['id']=='model.paseo'],['blocked'])

    def test_claude_native_recovery_requires_successful_marker_event(self):
        for outcome in ['success','error']:
            class Process:
                def __init__(self,*args):
                    self.messages=[{'type':'system','subtype':'hook_response','hook_event':'SessionStart',
                                    'outcome':outcome,'exit_code':0,'stdout':'ACCOUNT_DOCTOR_SELECTED_PLAN'}]
                def send(self,*args):pass
                def close(self):pass
                def receive(self,*args):
                    return {'response':{'subtype':'success','response':{'commands':[{'name':'to-spec'}]}}}
            with patch.object(native,'JsonProcess',Process):
                rows=native.claude_checks(self.home,{'hooks':{'.claude/settings.json':{'SessionStart':[]}}},['to-spec'],self.project,{},1)
            self.assertEqual(rows[0]['status'],'pass')
            self.assertEqual(rows[1]['status'],'pass' if outcome=='success' else 'blocked')

    def test_cli_rejects_incompatible_model_flags(self):
        for args in [['doctor','--model','cheap'],['doctor','--timeout','0'],
                     ['doctor','--model-smoke','--client','codex','--model','cheap','--evidence-dir',str(self.folder),'--scenario','routing','--with-paseo']]:
            with self.subTest(args=args),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(setup.main(args+['--home',str(self.home)]),2)

if __name__=='__main__':unittest.main()
