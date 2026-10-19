"""Exact qualification presentation; local synthetic files and Node handlers only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/improvement'))
import native_execution as execution
import native_trial as trial
import native_trial_qualification as qualification


class PresentationTests(unittest.TestCase):
    def test_canonical_loader_removes_only_one_final_lf(self):
        asset=(execution.SOURCE/'native_execution_loader.js').read_text()
        self.assertTrue(asset.endswith('\n'))
        for size in (1,9000,32768):
            rendered=asset.replace('EXPECTED_SCRIPT_BYTES',str(size))
            self.assertEqual(execution.loader_source(size),rendered[:-1])
            self.assertTrue(execution.loader_source(size).startswith(
                '// @exec: {"yield_time_ms": 30000, "max_output_tokens": 3000}\n'))

    def test_prompt_delimited_input_roundtrips_without_acceptance_normalization(self):
        for credential_free in (False,True):
            with self.subTest(credential_free=credential_free),tempfile.TemporaryDirectory() as folder:
                controller=trial.Controller.__new__(trial.Controller)
                controller.control=Path(folder).resolve()
                controller.selected=SimpleNamespace(files=trial.plan.QUALIFICATION_FILES)
                controller.data={'inputs':{'entrypoint':'skills/assigned/SKILL.md'}}
                controller.protected={};controller.journal=Mock();controller.checked=Mock()
                prompt=controller.prepare_qualification(credential_free=credential_free)
                opening='<qualification-exec-input>\n';closing='\n</qualification-exec-input>'
                self.assertEqual(prompt.count(opening),1)
                copied=prompt.split(opening,1)[1].split(closing,1)[0]
                expected=execution.loader_source(len(controller.qualification_source))
                self.assertEqual(copied,expected)
                self.assertFalse(copied.endswith('\n'))
                self.assertIn('Retain the first // @exec: pragma line verbatim',prompt)
                self.assertIn('no final newline',prompt)
                controller.checked.assert_not_called()
                self.assertTrue(controller.verify_protected())
                challenge='0'*32
                for value,matches in ((copied,True),(copied+'\n',False)):
                    observer=qualification.Qualification(expected,challenge)
                    event={'method':'rawResponseItem/completed','params':{'threadId':'thread','turnId':'turn',
                        'item':{'type':'custom_tool_call','name':'exec','call_id':'call','input':value}}}
                    observer.accept(event,'thread','turn')
                    result=observer.summary()
                    self.assertEqual(result['script_exact'],matches)
                    if not matches:self.assertEqual(result['reason'],'script_or_call_mismatch')

    def test_old_and_canonical_loader_have_identical_node_remote_and_eval_behavior(self):
        node=shutil.which('node')
        if node is None:self.skipTest('Node unavailable')
        body='text("SYNTHETIC_BODY");const r=await tools.exec_command({cmd:"synthetic-nested"});text(r.output);'
        old=(execution.SOURCE/'native_execution_loader.js').read_text().replace('EXPECTED_SCRIPT_BYTES',str(len(body)))
        new=execution.loader_source(len(body))
        program=r'''
const vm=require('vm'),fs=require('fs');const data=JSON.parse(fs.readFileSync(0,'utf8'));
(async()=>{const results=[];for(const source of data.sources){const calls=[],rows=[];
const context=vm.createContext({text:value=>rows.push(value),tools:{exec_command:async args=>{
calls.push(args);if(args.cmd==='cat /runtime/qualification.js')return {exit_code:0,output:data.body};
if(args.cmd==='synthetic-nested')return {exit_code:0,output:'SYNTHETIC_RESULT'};
throw Error('unexpected synthetic command');}}});
const cell=new vm.SourceTextModule(source,{context});await cell.link(()=>{throw Error('unexpected import')});
await cell.evaluate({timeout:1000});results.push({calls,rows});}console.log(JSON.stringify(results));})();
'''
        result=subprocess.run([node,'--experimental-vm-modules','-e',program],
            input=json.dumps({'sources':[old,new],'body':body}),text=True,capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        observations=json.loads(result.stdout)
        self.assertEqual(observations[0],observations[1])
        self.assertEqual(observations[1]['rows'],['SYNTHETIC_BODY','SYNTHETIC_RESULT'])
        self.assertEqual([call['cmd'] for call in observations[1]['calls']],
            ['cat /runtime/qualification.js','synthetic-nested'])


if __name__=='__main__':unittest.main()
