"""Real local fake processes exercise the runner, not native/executor isolation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
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

if __name__=='__main__':unittest.main()
