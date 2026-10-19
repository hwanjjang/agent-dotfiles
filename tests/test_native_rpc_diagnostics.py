"""RPC metadata is useful without preserving provider messages or changing verdicts."""
import json
import time
import unittest
from unittest.mock import patch
from test_native_trial_protocol import FakeSession, protocol


class RpcDiagnosticsTests(unittest.TestCase):
    def session(self, response):
        s = protocol.NativeSession(protocol.CounterArchive(), time.monotonic()+2)
        self.addCleanup(s.selector.close)
        s.send = lambda _: None
        s.until = lambda predicate: response
        return s

    def test_error_method_and_standard_class_without_raw_error(self):
        s=self.session({'id':1,'error':{'code':-32603,'message':'SECRET_PROVIDER_MESSAGE',
                                      'data':{'auth':'SECRET_AUTH'}}})
        with self.assertRaises(protocol.Refusal):s.rpc('account/read',{'refreshToken':False})
        self.assertEqual(s.rpc_failure, {'method':'account/read','phase':'response',
                         'kind':'server_error','code':'internal_error'})
        self.assertNotIn('SECRET',json.dumps(s.rpc_failure))

    def test_missing_result_and_unrecognized_method_or_code_are_bounded(self):
        for method,response,expected in [
            ('initialize',{'id':1},('initialize','missing_result','none')),
            ('PRIVATE_METHOD',{'id':1,'error':{'code':1337,'message':'PRIVATE'}},('other','server_error','other')),
            ('account/read',{'id':1,'error':'PRIVATE'},('account/read','server_error','other')),
        ]:
            with self.subTest(method=method,response=response):
                s=self.session(response)
                with self.assertRaises(protocol.Refusal):s.rpc(method,{})
                self.assertEqual(tuple(s.rpc_failure[k] for k in ('method','kind','code')),expected)
                self.assertNotIn('PRIVATE',json.dumps(s.rpc_failure))

    def test_rpc_timeout_identifies_phase_without_exception_text(self):
        s=self.session({})
        def timeout(_):raise TimeoutError('SECRET')
        s.until=timeout
        with self.assertRaises(TimeoutError):s.rpc('initialize',{})
        self.assertEqual(s.rpc_failure,{'method':'initialize','phase':'await_response',
                         'kind':'timeout','code':'none'})

    def test_observer_keeps_original_reason_and_never_retries(self):
        s=FakeSession([])
        s.rpc_failure={'method':'account/read','phase':'response','kind':'server_error','code':'internal_error'}
        original=s.rpc
        def fail(method,params):
            if method=='account/read':
                s.calls.append((method,params))
                raise protocol.Refusal('native_rpc_error:account/read')
            return original(method,params)
        s.rpc=fail
        result=protocol.observe(s,prompt='SECRET_PROMPT',project='/synthetic',codehome='/synthetic/.codex',
            metadata_check=lambda:{},soft_total=100,soft_output=10)
        self.assertEqual(result['reason'],'protocol_refusal')
        self.assertEqual(result['rpc_failure'],s.rpc_failure)
        self.assertEqual(result['initial_turn_requests_attempted'],0)
        self.assertEqual(sum(m=='account/read' for m,_ in s.calls),1)
        self.assertNotIn('SECRET',json.dumps(result))

    def test_arbitrary_session_metadata_is_not_copied(self):
        s=FakeSession([])
        s.rpc_failure={'method':'SECRET','kind':'SECRET','phase':'SECRET','code':'SECRET'}
        s.rpc=lambda *args: (_ for _ in ()).throw(protocol.Refusal('SECRET'))
        result=protocol.observe(s,prompt='x',project='/synthetic',codehome='/synthetic/.codex',
            metadata_check=lambda:{},soft_total=100,soft_output=10)
        self.assertNotIn('SECRET',json.dumps(result))
        self.assertNotIn('rpc_failure',result)
