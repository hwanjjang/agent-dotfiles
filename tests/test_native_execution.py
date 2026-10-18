"""Real local fake processes exercise the runner, not native/executor isolation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import subprocess
import shutil
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/improvement'))
import native_execution as runner
FAKE = ROOT/'tests/fixtures/native_execution_fake.py'


class RunnerTests(unittest.TestCase):
    def exercise(self, folder, mode='success', **kwargs):
        path=Path(folder)/mode
        result=runner.run_fixture(path,[sys.executable,str(FAKE),mode],[sys.executable,'-c','pass'],timeout=kwargs.pop('timeout',3),**kwargs)
        self.assertEqual(result,json.loads((path/'receipt.json').read_text()))
        self.assertFalse(result['live_eligible'])
        self.assertFalse(result['authentication_qualified'])
        self.assertFalse(result['isolation_qualified'])
        if result['cleanup']['harness'].get('group_signal_error'):
            self.assertFalse(result['cleanup']['temporary_home_absent'])
            self.assertEqual(result['status'],'blocked')
            # These local fake modes spawn no children. The runner correctly
            # retains unknown group cleanup; this fixture owner removes only
            # its freshly returned synthetic root after the child is reaped.
            self.assertIn(mode,('exit','truncated'))
            shutil.rmtree(result['cleanup']['retained_temporary_root'])
        else:
            self.assertTrue(result['cleanup']['temporary_home_absent'])
        self.assertTrue(result['cleanup']['listeners_closed'])
        self.assertTrue(result['cleanup']['harness']['process_reaped'])
        self.assertEqual((path/'receipt.json').stat().st_mode & 0o777,0o600)
        self.assertEqual((path/'events.jsonl').stat().st_size,result['archive']['event_bytes'])
        self.assertLessEqual(sum(p.stat().st_size for p in path.iterdir()),result['archive']['limit_bytes'])
        return result

    def test_success_requires_mock_evidence_and_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            r=self.exercise(folder)
            self.assertEqual(r['status'],'mock_complete')
            self.assertEqual(r['mock_submissions_observed'],2)
            self.assertEqual(r['terminal']['status'],'completed')
            self.assertIsNone(r['usage']['tokens'])

    def test_failure_receipts_survive_zero_exit_and_cleanup(self):
        for mode,reason in [('exit','native_eof'),('malformed','malformed_native_json'),('identity','terminal_identity_mismatch'),
                            ('terminal','native_or_fixture_incomplete'),('echo','native_or_fixture_incomplete'),
                            ('hooks','host_hooks_not_empty'),('mcp','host_mcp_not_empty')]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                r=self.exercise(folder,mode)
                self.assertEqual(r['status'],'blocked')
                self.assertIn(reason,r['reason'])

    def test_timeout_and_output_limit_retain_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            start=time.monotonic()
            r=self.exercise(folder,'silent',timeout=.2)
            self.assertIn('deadline',r['reason'])
            self.assertLess(time.monotonic()-start,3)
            r=self.exercise(folder,'flood',limit=20000)
            self.assertIn('archive_limit',r['reason'])

    def test_exclusive_archive_prevents_attempt_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            self.exercise(folder)
            receipt=(Path(folder)/'success/receipt.json').read_bytes()
            with self.assertRaises(FileExistsError):self.exercise(folder)
            self.assertEqual(receipt,(Path(folder)/'success/receipt.json').read_bytes())

    def test_no_ambient_secrets_forwarded(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic-must-not-forward'}):
            self.assertEqual(self.exercise(folder)['status'],'mock_complete')

    def test_backpressure_shares_process_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=runner.Archive(Path(folder)/'a',runner.MAX_BYTES)
            start=time.monotonic()
            s=runner.Session([sys.executable,'-c','import time;time.sleep(10)'],folder,{},archive,start+.2)
            try:
                with self.assertRaisesRegex(runner.Refusal,'deadline'):s.send({'payload':'x'*150000})
            finally:
                cleanup=s.close();archive.finish({'cleanup':cleanup})
            self.assertTrue(cleanup['process_reaped'])
            self.assertLess(time.monotonic()-start,2)

    def test_provider_refuses_echoed_fixture_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            r=self.exercise(folder,'echo')
            self.assertEqual(r['mock_submissions_observed'],2)
            self.assertIn('fixture_tool_output_missing',r['provider_error'])

    def test_discovered_skill_under_canonical_temporary_home(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);actual=root/'real';actual.mkdir()
            alias=root/'alias';alias.symlink_to(actual,target_is_directory=True)
            owned=actual/'owned';owned.mkdir()
            with patch.object(runner.tempfile,'mkdtemp',return_value=str(alias/'owned')):
                r=self.exercise(folder,'skill')
            self.assertEqual(r['status'],'mock_complete',r['reason'])

    def test_excess_submission_retained_and_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            r=self.exercise(folder,'excess')
            self.assertEqual(r['status'],'blocked')
            self.assertEqual(r['mock_submissions_observed'],3)
            self.assertIn('mock_request_limit',r['provider_error'])

    def test_cleanup_error_preserves_failure_and_attempt(self):
        original=runner.Session.close
        def failed_close(session):
            original(session)
            raise OSError('synthetic cleanup failure')
        with tempfile.TemporaryDirectory() as folder,patch.object(runner.Session,'close',failed_close):
            r=runner.run_fixture(Path(folder)/'receipt',[sys.executable,str(FAKE),'terminal'],[sys.executable,'-c','pass'],timeout=3)
            self.assertIn('native_or_fixture_incomplete',r['reason'])
            self.assertIn('synthetic cleanup failure',r['cleanup']['harness_error'])
            self.assertTrue(r['cleanup']['listeners_closed'])
            retained=Path(r['cleanup']['retained_temporary_root'])
            self.assertTrue(retained.exists())
            import shutil
            shutil.rmtree(retained)

    def test_invalid_config_has_no_attempt_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'never'
            with self.assertRaises(ValueError):runner.run_fixture(dest,['relative'],['relative'])
            self.assertFalse(dest.exists())

    def test_absolute_http_deadline_keeps_receipt_for_stalled_or_dribbling_peer(self):
        # Peer is outside the fake client's process group, so killing that client
        # cannot accidentally make a blocked HTTP handler look bounded.
        code = '''
import json,socket,sys,threading,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1]);import native_execution as r
original=r.FixtureProvider.start;peers=[]
def start(owner):
 port=original(owner);peer=socket.create_connection(('127.0.0.1',port));peers.append(peer)
 def dribble():
  try:
   if sys.argv[4]=='body':peer.sendall(b'POST /v1/responses HTTP/1.1\\r\\nContent-Length: 10000\\r\\n\\r\\n')
   for byte in (b'POST /v1/responses HTTP/1.1\\r\\nX-Slow: '+b'x'*500 if sys.argv[4]=='headers' else b'x'*500):
    if sys.argv[4]=='stall':break
    peer.sendall(bytes([byte]));time.sleep(.03)
  except OSError:pass
 threading.Thread(target=dribble,daemon=True).start();return port
try:
 with patch.object(r.FixtureProvider,'start',start):
  result=r.run_fixture(Path(sys.argv[3]),[sys.executable,sys.argv[2],'silent'],[sys.executable,'-c','pass'],timeout=.2)
 assert result['status']=='blocked' and result['cleanup']['listeners_closed']
 print('receipt retained after '+sys.argv[4])
finally:
 for p in peers:p.close()
'''
        for mode in ('stall','headers','body'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                start=time.monotonic()
                result=subprocess.run([sys.executable,'-c',code,str(ROOT/'scripts/improvement'),str(FAKE),str(Path(folder)/'attempt'),mode],capture_output=True,text=True,timeout=3)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertLess(time.monotonic()-start,2)
                self.assertTrue((Path(folder)/'attempt/receipt.json').is_file())

    def test_large_terminal_error_retains_bounded_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.exercise(folder,'large-error')
            self.assertEqual(result['status'],'blocked')
            self.assertLessEqual((Path(folder)/'large-error/receipt.json').stat().st_size,runner.RESERVE)

    def test_terminal_identity_summary_is_bounded_but_comparison_is_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.exercise(folder,'long-identities')
            self.assertEqual(result['status'],'mock_complete')
            self.assertEqual(len(result['terminal']['thread_id']),128)
            self.assertEqual(len(result['terminal']['sha256']),64)

    def test_signal_error_still_reaps_and_retains_owned_root(self):
        original=runner.os.killpg
        def signal_error(pid,sig):
            original(pid,sig)
            raise PermissionError('synthetic ambiguous group signal')
        with tempfile.TemporaryDirectory() as folder,patch.object(runner.os,'killpg',signal_error):
            result=runner.run_fixture(Path(folder)/'attempt',[sys.executable,str(FAKE),'success'],[sys.executable,'-c','pass'],timeout=3)
            self.assertEqual(result['status'],'blocked')
            self.assertTrue(result['cleanup']['harness']['process_reaped'])
            self.assertIn('ambiguous',result['cleanup']['harness']['group_signal_error'])
            root=Path(result['cleanup']['retained_temporary_root'])
            self.assertTrue(root.exists())
            shutil.rmtree(root)  # This fake has no children and real kill succeeded.

    def test_receipt_fallback_preserves_failure_and_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=runner.Archive(Path(folder)/'attempt',runner.MAX_BYTES)
            archive.record('example',{'retained':True})
            result=archive.finish({'status':'mock_complete','untrusted':'x'*20000})
            self.assertEqual(result['status'],'blocked')
            self.assertEqual(result['reason'],'receipt_summary_exceeded_reserve')
            self.assertFalse(result['live_eligible'])
            self.assertTrue((Path(folder)/'attempt/receipt.json').is_file())

    def test_identity_hash_failure_leaves_no_archive(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(runner,'sha',side_effect=OSError('synthetic unreadable executable')):
            dest=Path(folder)/'attempt'
            with self.assertRaises(OSError):runner.run_fixture(dest,[sys.executable],[sys.executable])
            self.assertFalse(dest.exists())

    def test_late_provider_failure_cannot_keep_success_status(self):
        original=runner.FixtureProvider.close
        def late(owner):
            # Deterministic race boundary: late accepted handler state before
            # final listener close, after terminal success was selected.
            owner.requests=3;owner.error='Refusal:mock_request_limit'
            return original(owner)
        with tempfile.TemporaryDirectory() as folder,patch.object(runner.FixtureProvider,'close',late):
            result=self.exercise(folder)
            self.assertEqual(result['status'],'blocked')
            self.assertEqual(result['mock_submissions_observed'],3)

    def test_eof_does_not_reap_leader_before_owned_group_kill(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=runner.Archive(Path(folder)/'attempt',runner.MAX_BYTES)
            session=runner.Session([sys.executable,'-c','pass'],folder,{},archive,time.monotonic()+2)
            try:
                with patch.object(session.proc,'poll',side_effect=AssertionError('premature leader reap')):
                    with self.assertRaisesRegex(runner.Refusal,'native_eof'):session.until(lambda value:False)
            finally:
                result=session.close();archive.finish({'cleanup':result})
            self.assertTrue(result['process_reaped'])

    def test_negative_guards_preserve_blocked_attempts(self):
        modes={'server-request':'unexpected_native_server_request','rpc-error':'native_rpc_error','truncated':'truncated_native_json','skill-enabled':'host_skill_enabled','skill-outside':'unexpected_host_skill_path','missing-assigned':'assigned_skill_evidence_missing','host-marker':'host_instruction_marker_exposed','model':'unexpected_mock_model_or_stream'}
        for mode,reason in modes.items():
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                result=self.exercise(folder,mode)
                self.assertEqual(result['status'],'blocked')
                self.assertIn(reason,str(result['reason'])+str(result.get('provider_error')))

if __name__=='__main__':unittest.main()
