"""Fixed boundary evidence, local fake processes only; never native/auth/Docker."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/improvement'))
import native_execution as runner


def request():
    return {'model': 'gpt-6-luna', 'stream': True, 'input': [], 'tools': [
        {'type': 'custom', 'name': 'exec', 'description': '\n'.join('### `'+name+'`' for name in [
            'apply_patch', 'exec_command', 'view_image', 'write_stdin', 'list_mcp_resource_templates',
            'list_mcp_resources', 'read_mcp_resource', 'clock__curr_time', 'skills__list', 'skills__read'])},
        {'type': 'function', 'name': 'wait'}]}


class BoundaryTests(unittest.TestCase):
    def test_boundary_capability_root_is_readonly_arm_while_default_is_unchanged(self):
        from unittest.mock import patch
        captured = []
        class Session:
            def __init__(self, *args):
                pass
            def send(self, value):
                pass
            def rpc(self, method, params):
                if method in ('hooks/list', 'skills/list'):
                    return {'data': []}
                if method == 'thread/start':
                    captured.append(copy.deepcopy(params))
                    raise runner.Refusal('synthetic_stop_before_turn')
                return {}
            def close(self):
                return {'process_reaped': True, 'group_signal_error': None}
        for scenario, expected in ((None, '/work/project/assigned-capability'),
                                   ('completion', '/work/project/assigned-capability'),
                                   ('command-skills-boundary', '/runtime/arm')):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as folder:
                options = {} if scenario is None else {'scenario': scenario}
                with patch.object(runner, 'Session', Session), \
                     patch.object(runner.FixtureProvider, 'start', return_value=12345), \
                     patch.object(runner.FixtureProvider, 'close', return_value=True):
                    receipt = runner.run_fixture(Path(folder)/'evidence', [sys.executable],
                                                 [sys.executable], **options)
                self.assertEqual(receipt['status'], 'blocked')
                self.assertEqual(receipt['reason'], 'Refusal:synthetic_stop_before_turn')
                self.assertTrue(receipt['cleanup']['temporary_home_absent'])
                selected = captured[-1]
                self.assertEqual(selected['selectedCapabilityRoots'], [{'id': 'assigned',
                    'location': {'type': 'environment', 'environmentId': 'trial', 'path': expected}}])
                self.assertEqual(selected['environments'], [{'environmentId': 'trial',
                    'cwd': '/work/project', 'runtimeWorkspaceRoots': ['/work/project']}])

    def test_fixed_boundary_scenario_emits_command_and_skills_cell(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = runner.Archive(Path(folder)/'evidence', runner.MAX_BYTES)
            try:
                provider = runner.FixtureProvider(archive, time.monotonic()+5,
                    (Path(folder)/'host-only').as_uri(), scenario='command-skills-boundary')
                result = provider.response(runner.encoded(request())).decode()
                self.assertIn('tools.exec_command', result)
                self.assertIn('skills__read', result)
                self.assertIn('BOUNDARY_CHECK:', result)
                self.assertNotIn('HOST_URI', result)
            finally:
                archive.finish({'status': 'test-only'})




def evidence():
    result = [
        {'type':'function_call_output','call_id':'disabled_agents','output':'unsupported call: collaborationlist_agents'},
        {'type':'custom_tool_call_output','call_id':'fixed_cell','output':[
            {'type':'input_text','text':'BOUNDARY_CHECK:'+json.dumps({'check':name,'result':value})}
            for name,value in runner.BOUNDARY_EXPECTED.items()]+[{'type':'input_text','text':'BOUNDARY_COMPLETED'}]},
    ]
    result[1]['output'][0]['text']='Script completed\nWall time 0.1 seconds\nOutput:\n'+result[1]['output'][0]['text']
    return result


class EvidenceTests(unittest.TestCase):
    def test_scoped_io_has_native_and_child_positive_and_role_denial_predicates(self):
        expected = runner.BOUNDARY_EXPECTED['command']
        self.assertIn('scoped_io', expected)
        for actor in ('direct', 'child'):
            scope = expected['scoped_io'][actor]
            self.assertIs(scope['fixture_read'], True)
            self.assertIs(scope['task_write_readback'], True)
            for role in ('grading', 'other_arm', 'installer_receipt', 'installer_journal'):
                self.assertEqual(scope['denied'][role], {'read_errno': 2, 'write_errno': 2, 'create_errno': 2})

    def test_success_is_typed_and_bound_to_exact_issued_calls(self):
        self.assertEqual(runner.boundary_outputs({'input':evidence()}), runner.BOUNDARY_EXPECTED)

    def test_failed_or_running_native_cell_cannot_be_repaired_by_markers(self):
        for status in ('Script failed', 'Script running with cell ID synthetic', 'Script terminated'):
            inputs=evidence();inputs[1]['output'].insert(0,{'type':'input_text','text':status+'\nWall time 0.1 seconds\nOutput:\n'})
            with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_each_missing_check_fails(self):
        for index in range(len(runner.BOUNDARY_EXPECTED)):
            with self.subTest(index=index):
                inputs=evidence();inputs[1]['output'].pop(index)
                with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_command_protected_access_and_network_ambiguity_fail(self):
        for field,value in [('fixture_read',False),('protected_enoent',4),('traversal_enoent',False),
                            ('symlink_enoent',False),('ipv4_tcp_errno',-1),('ipv4_udp_errno',0),
                            ('ipv6_tcp_errno',None),('ipv6_udp_errno',110),('root_write_errno',0)]:
            with self.subTest(field=field):
                inputs=evidence();row=json.loads(inputs[1]['output'][3]['text'].removeprefix('BOUNDARY_CHECK:'))
                row['result'][field]=value;inputs[1]['output'][3]['text']='BOUNDARY_CHECK:'+json.dumps(row)
                with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_every_scoped_io_predicate_is_required_and_typed(self):
        import copy
        expected = runner.BOUNDARY_EXPECTED['command']['scoped_io']
        for actor in expected:
            mutations = []
            for positive in ('fixture_read', 'task_write_readback'):
                for bad in (False, 1, None):
                    value = copy.deepcopy(expected); value[actor][positive] = bad; mutations.append(value)
            for role in expected[actor]['denied']:
                for operation in ('read_errno', 'write_errno', 'create_errno'):
                    for bad in (0, -1, True, None, '2'):
                        value = copy.deepcopy(expected); value[actor]['denied'][role][operation] = bad; mutations.append(value)
            value = copy.deepcopy(expected); del value[actor]; mutations.append(value)
            for value in mutations:
                inputs = evidence()
                row = json.loads(inputs[1]['output'][3]['text'].removeprefix('BOUNDARY_CHECK:'))
                row['result']['scoped_io'] = value
                inputs[1]['output'][3]['text'] = 'BOUNDARY_CHECK:' + json.dumps(row)
                with self.assertRaises(runner.Refusal):
                    runner.boundary_outputs({'input': inputs})

    def test_skill_foreign_or_traversal_disclosure_fails(self):
        for field in ('body','reference','foreign_refused','traversal_refused'):
            inputs=evidence();row=json.loads(inputs[1]['output'][4]['text'].removeprefix('BOUNDARY_CHECK:'))
            row['result'][field]=False;inputs[1]['output'][4]['text']='BOUNDARY_CHECK:'+json.dumps(row)
            with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_prompt_only_or_other_call_evidence_fails(self):
        inputs=evidence()
        with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':[{'type':'message','content':json.dumps(inputs)}]})
        inputs[1]['call_id']='other_cell'
        with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_duplicate_unknown_or_nonboolean_records_fail(self):
        mutations=[lambda x:x[1]['output'].append(x[1]['output'][0]),
                   lambda x:x.append(copy.deepcopy(x[1])),
                   lambda x:x[1]['output'].append({'type':'input_text','text':'BOUNDARY_COMPLETED'}),
                   lambda x:x[1]['output'].append({'type':'input_text','text':'BOUNDARY_CHECK:{"check":"extra","result":true}'}),
                   lambda x:x[1]['output'].__setitem__(1,{'type':'input_text','text':'BOUNDARY_CHECK:{"check":"globals_imports","result":{"globals_absent":1,"imports_refused":3}}'}),
                   lambda x:x[1]['output'].__setitem__(1,{'type':'input_text','text':'BOUNDARY_CHECK:{"check":"globals_imports","check":"globals_imports","result":{"globals_absent":true,"imports_refused":3}}'})]
        for mutate in mutations:
            inputs=evidence();mutate(inputs)
            with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_dispatch_refusal_must_be_actual_separate_call(self):
        inputs=evidence();inputs[0]['output']='tool completed'
        inputs[1]['output'].append({'type':'input_text','text':'unsupported call: collaborationlist_agents'})
        with self.assertRaises(runner.Refusal):runner.boundary_outputs({'input':inputs})

    def test_missing_duplicate_and_new_catalog_routes_fail(self):
        from native_execution_catalog import boundary_gate,catalog
        for change in ('missing','duplicate','new'):
            data=request()
            if change=='missing':data['tools'][0]['description']=data['tools'][0]['description'].replace('### `skills__read`','')
            else:data['tools'][0]['description']+='\n### `'+('skills__read' if change=='duplicate' else 'unreviewed_tool')+'`'
            with self.assertRaises(ValueError):boundary_gate(catalog(data))

    def test_default_cell_and_receipt_contract_remains_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=runner.Archive(Path(folder)/'evidence',runner.MAX_BYTES)
            try:
                provider=runner.FixtureProvider(archive,time.monotonic()+5,(Path(folder)/'host-only').as_uri())
                first=provider.response(runner.encoded(request())).decode()
                self.assertIn('CELL1_COMPLETED',first);self.assertNotIn('BOUNDARY_CHECK:',first)
                second=request();second['input']=[{'type':'function_call_output','output':'unsupported call: collaborationlist_agents'},
                  {'type':'custom_tool_call_output','output':[{'type':'input_text','text':'CELL1_COMPLETED'},
                    {'type':'input_text','text':json.dumps({'check':'assigned_body','result':{'contents':'ASSIGNED_REMOTE_SKILL_BODY'}})},
                    {'type':'input_text','text':json.dumps({'check':'assigned_reference','result':{'contents':'ASSIGNED_REMOTE_SKILL_REFERENCE'}})}]}]
                provider.response(runner.encoded(second));self.assertTrue(provider.completed);self.assertIsNone(provider.boundary_checks)
            finally:archive.finish({'status':'test-only'})



class ScopedProbeTests(unittest.TestCase):
    def test_rendered_command_runs_the_bounded_child_and_rejects_child_failure(self):
        import shutil, subprocess
        node = shutil.which('node')
        if not node: self.skipTest('Node unavailable: JavaScript template decoding not exercised')
        decoder = "const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');const literal=source.split('const probe = ')[1].split('\\n`;')[0]+'\\n`';process.stdout.write(vm.runInNewContext(literal));"
        decoded = subprocess.run([node, '-e', decoder,
            str(ROOT/'scripts/improvement/native_execution_command_skills.js')],
            capture_output=True, text=True, timeout=3)
        self.assertEqual(decoded.returncode, 0, decoded.stderr)
        prefix = decoded.stdout.split("\nresult['fixture_read']=", 1)[0]
        self.assertNotIn('socket.socket(', prefix)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root/'fixture.txt').write_text('ASSIGNED_REMOTE_FIXTURE')
            prefix = prefix.replace('/work/project', str(root))
            missing = [str(root/'not-mounted'/name) for name in
                       ('host-only', 'history-only', 'credential-only', 'other-arm-only', 'evaluator-only')]
            for fails in (False, True):
                program = prefix + "\nprint(json.dumps(result['scoped_io']))"
                if fails: program = program.replace('child_source=io_source+', "child_source='raise SystemExit(3)'+")
                result = subprocess.run([sys.executable, '-c', program, json.dumps(missing)],
                                        capture_output=True, text=True, timeout=5)
                if fails:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('child_probe_failed', result.stderr)
                else:
                    self.assertEqual((result.returncode, result.stderr), (0, ''))
                    self.assertEqual(json.loads(result.stdout), runner.SCOPED_IO_EXPECTED)
                self.assertFalse((root/'scoped-io-direct').exists())
                self.assertFalse((root/'scoped-io-child').exists())

    def test_actual_python_child_task_io_and_typed_absence_results(self):
        import subprocess
        source = (ROOT/'scripts/improvement/native_execution_command_skills.js').read_text()
        helper = source.split('io_source = """', 1)[1].split('"""', 1)[0]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            fixture = root/'fixture.txt'; fixture.write_text('ASSIGNED_REMOTE_FIXTURE')
            helper = helper.replace('/work/project/fixture.txt', str(fixture))
            targets = {role: str(root/'not-mounted'/role) for role in
                       ('grading', 'other_arm', 'installer_receipt', 'installer_journal')}
            namespace = {}; exec(helper, namespace)
            direct = namespace['check_io'](targets, str(root/'direct-output'))
            command = helper + "\nprint(json.dumps(check_io(json.loads(sys.argv[1]),sys.argv[2])))"
            child = subprocess.run([sys.executable, '-c', command, json.dumps(targets), str(root/'child-output')],
                                   capture_output=True, text=True, timeout=3)
            self.assertEqual((child.returncode, child.stderr), (0, ''))
            self.assertEqual(direct, runner.SCOPED_IO_EXPECTED['direct'])
            self.assertEqual(json.loads(child.stdout), runner.SCOPED_IO_EXPECTED['child'])
            self.assertFalse((root/'direct-output').exists())
            self.assertFalse((root/'child-output').exists())
            # A visible controlled target must record successful forbidden access,
            # not treat success or an unrelated process failure as denial.
            visible = root/'visible'; visible.write_text('SYNTHETIC')
            targets['grading'] = str(visible)
            changed = namespace['check_io'](targets, str(root/'visible-output'))
            self.assertEqual(changed['denied']['grading'], {'read_errno': 0, 'write_errno': 0, 'create_errno': 0})


class FixedCellTests(unittest.TestCase):
    def test_cell_actual_control_flow_with_local_fake_handlers(self):
        import shutil,subprocess
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable: fixed V8 cell control flow not exercised')
        # No native process, shell execution, imports, or network: each handler
        # below is a local synthetic function. vm's import hook always refuses.
        program=r"""
const vm=require('vm'),fs=require('fs');
const mode=process.argv[1];
const names=['apply_patch','exec_command','view_image','write_stdin','list_mcp_resource_templates','list_mcp_resources','read_mcp_resource','clock__curr_time','skills__list','skills__read'];
const rows=[];
const scoped={fixture_read:true,task_write_readback:true,denied:Object.fromEntries(['grading','other_arm','installer_receipt','installer_journal'].map(role=>[role,{read_errno:2,write_errno:2,create_errno:2}]))};
const command={fixture_read:true,protected_enoent:5,traversal_enoent:true,symlink_enoent:true,ipv4_tcp_errno:101,ipv4_udp_errno:101,ipv6_tcp_errno:101,ipv6_udp_errno:101,root_write_errno:30,scoped_io:{direct:structuredClone(scoped),child:structuredClone(scoped)}};
if(mode==='allowed-write')command.scoped_io.direct.task_write_readback=false;
if(mode==='child-denial')command.scoped_io.child.denied.installer_receipt.write_errno=0;
if(mode==='child-missing')delete command.scoped_io.child;
if(mode==='protected')command.protected_enoent=4;
if(mode==='network')command.ipv4_tcp_errno=-1;
const handlers={
 apply_patch:async()=> 'Failed to read file to update: No such file or directory',
 exec_command:async()=>({exit_code:mode==='exit'?1:0,output:JSON.stringify(command)}),
 view_image:async()=>{throw Error('No such file or directory');},
 write_stdin:async()=>{throw Error('Unknown process id: 2147483000');},
 list_mcp_resource_templates:async()=>({resourceTemplates:[]}),
 list_mcp_resources:async()=>({resources:mode==='mcp'?['unexpected']:[]}),
 read_mcp_resource:async()=>{throw Error('unknown MCP server');},
 clock__curr_time:async()=>{throw Error('must not be called');},
 skills__list:async()=>({skills:[{package:'synthetic',main_resource:'skill://synthetic/SKILL.md'}]}),
 skills__read:async(args)=>{
  if(args.resource==='skill://synthetic/SKILL.md')return {contents:'ASSIGNED_REMOTE_SKILL_BODY'};
  if(args.resource==='skill://synthetic/references/details.md')return {contents:'ASSIGNED_REMOTE_SKILL_REFERENCE'};
  if(mode==='skill-disclosure')return {contents:'synthetic protected canary'};
  if(mode==='ambiguous-error')throw Error('transport disconnected');
  if(mode==='environment-denial')throw Error('skill environment is not available for this callback');
  throw Error('failed to read skill resource');
 }
};
if(mode==='extra')handlers.unknown_tool=async()=>({});
if(mode==='nonfunction')handlers.clock__curr_time=7;
if(mode==='patch')handlers.apply_patch=async()=> 'Success. Updated the following files';
if(mode==='image')handlers.view_image=async()=>({image_url:'data:image/png;base64,synthetic'});
if(mode==='image-with-error')handlers.view_image=async()=>({image_url:'data:image/png;base64,synthetic',error:'No such file or directory'});
if(mode==='stdin')handlers.write_stdin=async()=>({exit_code:0,output:''});
const context=vm.createContext({ALL_TOOLS:names.map(name=>({name})),tools:handlers,text:x=>rows.push(x)});
for(const key of ['process','require','fetch','Deno','Bun','XMLHttpRequest','WebSocket','console','Atomics','SharedArrayBuffer','WebAssembly'])context[key]=undefined;
if(mode==='global')context.process={};
const source=fs.readFileSync(process.argv[2],'utf8').replaceAll('HOST_URI',JSON.stringify('file:///synthetic/protected/host-only'));
(async()=>{try{
 const cell=new vm.SourceTextModule(source,{context,importModuleDynamically:()=>{throw Error('Unsupported import in exec');}});
 await cell.link(()=>{throw Error('No static imports');});await cell.evaluate({timeout:1000});
 console.log(JSON.stringify({completed:true,rows}));
}catch(e){console.log(JSON.stringify({completed:false,rows,error:String(e)}));}})();
"""
        for mode in ('success','protected','network','exit','mcp','skill-disclosure','ambiguous-error','environment-denial','extra','patch','image','image-with-error','stdin','global','nonfunction','allowed-write','child-denial','child-missing'):
            with self.subTest(mode=mode):
                result=subprocess.run([node,'--experimental-vm-modules','-e',program,mode,str(ROOT/'scripts/improvement/native_execution_command_skills.js')],capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                observed=json.loads(result.stdout)
                self.assertEqual(observed['completed'],mode in ('success','environment-denial'),observed)
                if mode=='success':
                    inputs=evidence();inputs[1]['output']=[{'type':'input_text','text':x} for x in observed['rows']]
                    inputs[1]['output'][0]['text']='Script completed\nWall time 0.1 seconds\nOutput:\n'+inputs[1]['output'][0]['text']
                    self.assertEqual(runner.boundary_outputs({'input':inputs}),runner.BOUNDARY_EXPECTED)


class FixtureBoundaryLifecycleTests(unittest.TestCase):
    """Exercise the implemented guard through real local fake-client transport."""
    def run_boundary(self, mode):
        from unittest.mock import patch
        providers, temporary_roots = [], []
        provider_class = runner.FixtureProvider

        def capture_provider(*args, **kwargs):
            provider = provider_class(*args, **kwargs)
            providers.append(provider)
            return provider

        with tempfile.TemporaryDirectory() as folder:
            with patch.object(runner, 'FixtureProvider', side_effect=capture_provider):
                receipt = runner.run_fixture(
                    Path(folder)/'evidence',
                    command=[sys.executable, __file__, '--fake', mode],
                    executor=[sys.executable], timeout=10,
                    scenario='command-skills-boundary',
                    on_temporary_root=temporary_roots.append)
            self.assertEqual(receipt['terminal']['status'], 'completed')
            self.assertEqual(receipt['mock_submissions_observed'], 2)
            self.assertFalse(receipt['live_eligible'])
            self.assertFalse(receipt['authentication_qualified'])
            self.assertTrue(receipt['cleanup']['harness']['process_reaped'])
            self.assertIsNone(receipt['cleanup']['harness']['group_signal_error'])
            self.assertTrue(receipt['cleanup']['listeners_closed'])
            self.assertTrue(receipt['cleanup']['temporary_home_absent'])
            self.assertEqual(len(temporary_roots), 1)
            self.assertFalse(temporary_roots[0].exists())
            self.assertEqual(len(providers), 1)
            provider = providers[0]
            self.assertTrue(all(server.socket.fileno() == -1 for server in provider.servers))
            self.assertTrue(all(not thread.is_alive() for thread in provider.threads))
            if provider.watchdog is not None:
                self.assertFalse(provider.watchdog.is_alive())
            return receipt

    def test_fake_boundary_success_preserves_protected_files_and_cleans(self):
        receipt = self.run_boundary('success')
        self.assertEqual(receipt['status'], 'mock_complete')
        self.assertTrue(receipt['protected_canaries_unchanged'])
        self.assertEqual(receipt['boundary_checks'], runner.BOUNDARY_EXPECTED)

    def test_missing_boundary_output_blocks_despite_completed_terminal(self):
        receipt = self.run_boundary('missing')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertTrue(receipt['protected_canaries_unchanged'])
        self.assertIsNotNone(receipt['provider_error'])

    def test_protected_mutation_blocks_despite_complete_boundary_and_terminal(self):
        receipt = self.run_boundary('mutation')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertFalse(receipt['protected_canaries_unchanged'])
        self.assertEqual(receipt['reason'], 'protected_canary_changed')
        self.assertEqual(receipt['boundary_checks'], runner.BOUNDARY_EXPECTED)


def fake_client(mode):
    # Local process fixture; it deliberately synthesizes evidence, never claims
    # to execute the JavaScript or to provide native/OS boundary qualification.
    import os,tomllib,urllib.request
    config=tomllib.loads((Path(os.environ['CODEX_HOME'])/'config.toml').read_text())
    assert config['model_providers']['fixture']['requires_openai_auth'] is False
    assert not (Path(os.environ['CODEX_HOME'])/'auth.json').exists()
    url=config['model_providers']['fixture']['base_url']+'/responses'
    def reply(value):print(json.dumps(value),flush=True)
    def post(data):
        with urllib.request.urlopen(urllib.request.Request(url,runner.encoded(data),{'Content-Type':'application/json'}),timeout=2) as result:return result.read()
    for line in sys.stdin:
        rpc=json.loads(line);method=rpc['method']
        if method=='initialized':continue
        result={}
        if method=='hooks/list':result={'data':[{'hooks':[],'errors':[]}]}
        elif method=='skills/list':result={'data':[{'skills':[]}]}
        elif method=='thread/start':result={'thread':{'id':'synthetic-thread'}}
        elif method=='mcpServerStatus/list':result={'data':[],'nextCursor':None}
        elif method=='turn/start':result={'turn':{'id':'synthetic-turn'}}
        reply({'id':rpc['id'],'result':result})
        if method=='turn/start':
            try:
                post(request());data=request();data['input']=evidence()
                if mode=='missing':data['input'][1]['output'].pop(3)
                if mode=='mutation':
                    root=Path(os.environ['HOME']).parent;(root/'history-only').write_text('synthetic forbidden mutation')
                post(data)
            except Exception:pass
            reply({'method':'turn/completed','params':{'threadId':'synthetic-thread','turn':{'id':'synthetic-turn','status':'completed','error':None}}})

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fake':fake_client(sys.argv[2])
    else:unittest.main()
