"""Fixed loader contract tests; synthetic handlers only, no native or auth."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/improvement'))
import native_execution as runner
from test_native_execution_boundary import request, evidence


class LoaderTests(unittest.TestCase):
    def test_loader_is_fixed_short_source_with_bound_expected_length(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=runner.Archive(Path(folder)/'evidence',runner.MAX_BYTES)
            try:
                provider=runner.FixtureProvider(archive,time.monotonic()+5,'file:///synthetic/inner/host-only',
                    scenario='command-skills-loader',expected_script_bytes=9000)
                response=provider.response(runner.encoded(request())).decode()
                self.assertIn('/runtime/qualification.js',response)
                self.assertIn('9000',response)
                self.assertIn('await eval',response)
                self.assertNotIn('EXPECTED_SCRIPT_BYTES',response)
                self.assertNotIn('/synthetic/inner',response)
                second=request();second['input']=evidence()
                provider.response(runner.encoded(second))
                self.assertTrue(provider.completed)
                self.assertEqual(provider.boundary_checks,runner.BOUNDARY_EXPECTED)
            finally:archive.finish({'status':'synthetic-only'})


    def test_owner_observes_root_before_factory_and_cleanup_can_be_deferred(self):
        import os,shutil
        from unittest.mock import patch
        owners=[];providers=[]
        def on_root(path):
            self.assertEqual(list(path.iterdir()),[])
            st=path.lstat();self.assertEqual(st.st_uid,os.getuid());self.assertEqual(st.st_mode&0o777,0o700)
            owners.append((path,st.st_dev,st.st_ino))
        def start(provider):providers.append(provider);return 12345
        class Session:
            def send(self,value):pass
            def rpc(self,method,params):
                if method in ('hooks/list','skills/list'):return {'data':[]}
                if method=='thread/start':
                    self.selected=params['selectedCapabilityRoots'][0]['location']['path']
                    return {'thread':{'id':'thread'}}
                if method=='mcpServerStatus/list':return {'data':[]}
                if method=='turn/start':return {'turn':{'id':'turn'}}
                return {}
            def until(self,predicate):
                providers[0].response(runner.encoded(request()))
                second=request();second['input']=evidence();providers[0].response(runner.encoded(second))
                return {'method':'turn/completed','params':{'threadId':'thread','turn':{'id':'turn','status':'completed','error':None}}}
            def close(self):return {'process_reaped':True,'group_signal_error':None}
        sessions=[]
        def factory(command,project,env,archive,deadline):
            self.assertEqual(project.parent,owners[0][0]);self.assertTrue(Path(env['CODEX_HOME']).is_dir())
            instance=Session();sessions.append(instance);return instance
        with tempfile.TemporaryDirectory() as folder:
            try:
                with patch.object(runner.FixtureProvider,'start',start),patch.object(runner.FixtureProvider,'close',return_value=True):
                    receipt=runner.run_fixture(Path(folder)/'evidence',[sys.executable],[sys.executable],
                        scenario='command-skills-loader',expected_script_bytes=9000,
                        session_factory=factory,on_temporary_root=on_root,defer_temporary_cleanup=True)
                self.assertEqual(receipt['status'],'mock_complete',receipt)
                self.assertEqual(sessions[0].selected,'/runtime/arm')
                self.assertTrue(receipt['cleanup']['temporary_cleanup_deferred'])
                self.assertTrue(receipt['cleanup']['external_cleanup_pending'])
                self.assertFalse(receipt['cleanup']['temporary_home_absent'])
                self.assertFalse(receipt['outer_protected_canaries_verified'])
                self.assertFalse(receipt['live_eligible']);self.assertFalse(receipt['isolation_qualified'])
                self.assertEqual(Path(receipt['cleanup']['retained_temporary_root']),owners[0][0])
            finally:
                for path,dev,ino in owners:
                    st=path.lstat();self.assertEqual((st.st_dev,st.st_ino),(dev,ino));shutil.rmtree(path)

    def test_callback_failure_preserves_owned_root_before_any_native_launch(self):
        import shutil
        from unittest.mock import patch
        owned=[]
        def stop(path):owned.append((path,path.stat().st_ino));raise RuntimeError('synthetic_owner_refusal')
        with tempfile.TemporaryDirectory() as folder:
            try:
                with patch.object(runner,'Session') as session,patch.object(runner.FixtureProvider,'start') as start:
                    receipt=runner.run_fixture(Path(folder)/'evidence',[sys.executable],[sys.executable],
                        on_temporary_root=stop,defer_temporary_cleanup=True)
                    session.assert_not_called();start.assert_not_called()
                self.assertEqual(receipt['status'],'blocked');self.assertIn('synthetic_owner_refusal',receipt['reason'])
                self.assertTrue(receipt['cleanup']['temporary_cleanup_deferred'])
                self.assertTrue(owned[0][0].is_dir())
            finally:
                for path,ino in owned:
                    self.assertEqual(path.stat().st_ino,ino);shutil.rmtree(path)


    def test_falsey_trusted_factory_does_not_fall_back_to_process_launcher(self):
        from unittest.mock import patch
        class Factory:
            called=False
            def __bool__(self):return False
            def __call__(self,*args):self.called=True;raise RuntimeError('synthetic_factory_stop')
        factory=Factory()
        with tempfile.TemporaryDirectory() as folder,patch.object(runner,'Session',side_effect=AssertionError('unexpected_default_launcher')) as default:
            with patch.object(runner.FixtureProvider,'start',return_value=12345),patch.object(runner.FixtureProvider,'close',return_value=True):
                receipt=runner.run_fixture(Path(folder)/'evidence',[sys.executable],[sys.executable],session_factory=factory)
            self.assertTrue(factory.called)
            default.assert_not_called()
            self.assertIn('synthetic_factory_stop',receipt['reason'])
            self.assertTrue(receipt['cleanup']['temporary_home_absent'])

    def test_length_and_trusted_python_only_options_reject_invalid_input_before_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in (None,True,0,-1,32769,'9000'):
                with self.subTest(value=value),self.assertRaises(ValueError):
                    runner.run_fixture(Path(folder)/'unused',[sys.executable],[sys.executable],
                        scenario='command-skills-loader',expected_script_bytes=value)
                self.assertFalse((Path(folder)/'unused').exists())
            for options in ({'expected_script_bytes':9000},{'session_factory':7},
                            {'on_temporary_root':'callback'},{'defer_temporary_cleanup':'yes'}):
                with self.assertRaises(ValueError):
                    runner.run_fixture(Path(folder)/'unused',[sys.executable],[sys.executable],**options)
                self.assertFalse((Path(folder)/'unused').exists())
        self.assertNotIn('EXPECTED_SCRIPT_BYTES',runner.loader_source(9000))
        self.assertLess(len(runner.loader_source(9000)),1024)

    def test_actual_loader_evaluates_only_complete_ascii_source_in_same_vm(self):
        import shutil,subprocess
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable: fixed loader not exercised')
        program=r"""
const vm=require('vm'),fs=require('fs');const mode=process.argv[1];const rows=[];
const body='text(ALL_TOOLS.length);const next=await tools.exec_command({cmd:"synthetic-next"});text(next.output);let denied=false;try{await import("node:fs")}catch(e){denied=String(e).includes("unsupported import")}if(!denied)throw Error("import unexpectedly permitted");text("LOADER_BODY_COMPLETE");';
let reads=0,nested=0;
const tools={exec_command:async args=>{
 if(args.cmd==='cat /runtime/qualification.js'){
  reads++;
  let r={exit_code:0,output:body};
  if(mode==='bad-exit')r.exit_code=1;
  if(mode==='missing-exit')delete r.exit_code;
  if(mode==='session-zero')r.session_id=0;
  if(mode==='running')r.session_id=7;
  if(mode==='truncated')r.output=body.slice(0,-1);
  if(mode==='syntax')r.output=body.slice(0,-1)+'!';
  if(mode==='nonascii')r.output=body.slice(0,-1)+'é';
  if(mode==='malformed-json')return '{invalid';
  return mode==='json'?JSON.stringify(r):r;
 }
 if(args.cmd!=='synthetic-next')throw Error('Unexpected command');
 nested++;return {exit_code:0,output:'synthetic-result'};
}};
const context=vm.createContext({tools,ALL_TOOLS:[{name:'exec_command'}],text:value=>rows.push(value)});
context.process=undefined;context.require=undefined;context.console=undefined;
const source=fs.readFileSync(process.argv[2],'utf8').replace('EXPECTED_SCRIPT_BYTES',String(body.length));
(async()=>{try{
 const cell=new vm.SourceTextModule(source,{context,importModuleDynamically:()=>{throw Error('unsupported import in exec');}});
 await cell.link(()=>{throw Error('No imports');});await cell.evaluate({timeout:1000});
 console.log(JSON.stringify({complete:true,rows,reads,nested}));
}catch(e){console.log(JSON.stringify({complete:false,rows,reads,nested}));}})();
"""
        for mode in ('object','json','bad-exit','missing-exit','session-zero','running','truncated','syntax','nonascii','malformed-json'):
            with self.subTest(mode=mode):
                result=subprocess.run([node,'--experimental-vm-modules','-e',program,mode,
                    str(ROOT/'scripts/improvement/native_execution_loader.js')],capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr);observed=json.loads(result.stdout)
                self.assertEqual(observed['reads'],1)
                self.assertEqual(observed['complete'],mode in ('object','json'))
                if observed['complete']:
                    self.assertEqual(observed['rows'],[1,'synthetic-result','LOADER_BODY_COMPLETE'])
                    self.assertEqual(observed['nested'],1)
                else:
                    self.assertEqual(observed['rows'],[]);self.assertEqual(observed['nested'],0)


if __name__=='__main__':unittest.main()
