"""Deterministic boundaries; no account authentication or provider requests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('isolation',ROOT/'scripts/improvement/isolation.py')
isolation=importlib.util.module_from_spec(spec);spec.loader.exec_module(isolation)


class IsolationTests(unittest.TestCase):
    def test_bounded_timeout_terminates_started_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=isolation.bounded([sys.executable,'-I','-S','-c','import time; print("started",flush=True); time.sleep(10)'],tmp,timeout=.2)
        self.assertEqual(result['stop_reason'],'timeout')
        self.assertIn('started',result['stdout'])
        self.assertLess(result['duration_seconds'],2)

    def test_output_overflow_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=isolation.bounded([sys.executable,'-I','-S','-c','print("x"*100000)'],tmp,limit=128)
        self.assertEqual(result['stop_reason'],'output_limit')
        self.assertLessEqual(len(result['stdout'])+len(result['stderr']),128)

    def test_closed_environment_does_not_forward_credentials(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'SYNTHETIC_SECRET':'do not forward'}):
            result=isolation.bounded([sys.executable,'-I','-S','-c','import os; print(os.environ.get("SYNTHETIC_SECRET","absent"))'],tmp)
        self.assertEqual(result['stdout'].strip(),'absent')

    def test_profile_has_no_general_home_network_read_allow(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=isolation.profile_for(tmp,sys.base_prefix,sys.executable,43123)
        self.assertIn('(deny default)',profile)
        self.assertIn('(remote ip "localhost:43123")',profile)
        self.assertNotIn('(allow file-read*)',profile)
        self.assertNotIn('(allow network*)',profile)
        self.assertNotIn('(allow mach-lookup)',profile)

    def test_broad_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):isolation.profile_for(tmp,'/',sys.executable,43123)

    def test_mock_shape_budget_and_expiry(self):
        with isolation.MockBroker() as b:
            host='127.0.0.1:'+str(b.server.server_port)
            payload=json.dumps({'model':'synthetic-model','input':'synthetic fixture','max_output_tokens':1}).encode()
            auth='Bearer '+b.token
            self.assertEqual(b.check('CONNECT','/v1/responses',host,auth,payload),403)
            self.assertEqual(b.check('POST','/v1/responses','other.invalid',auth,payload),403)
            bad=json.dumps({'model':'synthetic-model','input':'synthetic fixture','max_output_tokens':True}).encode()
            self.assertEqual(b.check('POST','/v1/responses',host,auth,bad),400)
            self.assertEqual(b.check('POST','/v1/responses',host,auth,payload),200)
            self.assertEqual(b.check('POST','/v1/responses',host,auth,payload),429)
            b.expires=time.monotonic()-1
            self.assertEqual(b.check('POST','/v1/responses',host,auth,payload),403)

    def receipt(self):
        r={'schema_version':1,'evidence_kind':'isolation_canary_qualification','runner_sha256':isolation.file_hash(isolation.__file__),
           'profile_sha256':'a'*64,'environment':{'system':platform.system(),'release':platform.release(),'machine':platform.machine()}}
        r['receipt_sha256']=isolation.digest(r)
        return r

    def test_canary_receipt_never_enables_live_execution(self):
        r=self.receipt();trial={'profile_sha256':r['profile_sha256'],'isolation_receipt_sha256':r['receipt_sha256']}
        with patch.object(isolation,'bounded',side_effect=AssertionError('must not execute')):
            result=isolation.run_trial(trial,r,{'live_token':'synthetic'})
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['model_requests'],0)

    def test_changed_receipt_and_frozen_profile_rejected(self):
        r=self.receipt();trial={'profile_sha256':r['profile_sha256'],'isolation_receipt_sha256':r['receipt_sha256']}
        bad=dict(r);bad['profile_sha256']='b'*64
        with self.assertRaises(ValueError):isolation.run_trial(trial,bad)
        trial['profile_sha256']='b'*64
        with self.assertRaises(ValueError):isolation.run_trial(trial,r)

    def test_other_environment_rejected(self):
        r=self.receipt();r['environment']['release']='different';r.pop('receipt_sha256');r['receipt_sha256']=isolation.digest(r)
        trial={'profile_sha256':r['profile_sha256'],'isolation_receipt_sha256':r['receipt_sha256']}
        with self.assertRaises(ValueError):isolation.run_trial(trial,r)

    @unittest.skipUnless(platform.system()=='Darwin' and isolation.SANDBOX.exists(),'Seatbelt qualification requires macOS')
    def test_actual_canaries_and_no_reuse_of_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'evidence';r=isolation.qualify(out)
            self.assertEqual(r['status'],'pass',r)
            self.assertFalse(r['native_client_qualified']);self.assertFalse(r['live_transport_qualified'])
            self.assertTrue(r['checks']['fixture_read']);self.assertTrue(r['checks']['child_read_denied'])
            self.assertTrue(r['checks']['broker_mock_allowed']);self.assertTrue(r['checks']['unix_denied_server_empty'])
            with self.assertRaises(FileExistsError):isolation.qualify(out)

if __name__=='__main__':unittest.main()
