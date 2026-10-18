"""Controller collection contract with fake Docker and actual fixed processes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/improvement'))
import native_trial as trial
from test_native_trial_lifecycle import FakeDocker, fake_extract, synthetic_selected


def snapshot():
    return {'schema_version':1,'kind':'bounded_artifact_snapshot','status':'captured',
            'files':[{'path':'result.txt','status':'present','bytes':2,
                      'sha256':hashlib.sha256(b'OK').hexdigest()}],
            'reason':None,'quiescent_state_verified':False}


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.selected=synthetic_selected(self.root)
        self.selected.data['collection']={'schema_version':1,'paths':['result.txt'],
            'max_file_bytes':65536,'max_total_bytes':262144}
        self.selected.data['sources']['native_trial_results.py']=hashlib.sha256(
            (trial.plan.SOURCE/'native_trial_results.py').read_bytes()).hexdigest()
        self.selected.digest=trial.plan.digest(self.selected.data)
        self.docker=FakeDocker(self.selected); self.trace=[]
        self.capture_response={'exit':0,'stdout':json.dumps(snapshot()),'stderr':'','stop_reason':None}
        self.capture_arguments=[]
        def command(argv, timeout, **kwargs):
            if '-I' in argv:
                self.trace.append('capture')
                self.capture_arguments.append((argv, timeout, kwargs.get('payload')))
                if isinstance(self.capture_response, BaseException): raise self.capture_response
                return self.capture_response
            if argv[3:5]==['rm','-f'] and 'capture' in self.trace:
                self.trace.append('remove')
            return self.docker(argv, timeout, **kwargs)
        self.command=patch.object(trial,'bounded',side_effect=command).start()
        patch.object(trial.native_isolation,'extract_verified',side_effect=fake_extract).start()
        self.addCleanup(patch.stopall)

    def controller(self):
        c=trial.Controller(self.selected); self.addCleanup(c.release); c.setup()
        c.launch_called=c.launch_complete=True
        c.live=Mock(); c.live.proc=Mock()
        c.live.close.side_effect=lambda: (self.trace.append('stopped') or
            {'process_reaped':True,'group_signal_error':None})
        c.home=Mock()
        c.home.cleanup.side_effect=lambda **kwargs: (self.trace.append('purged') or {'home_absent':True})
        c.observation={'status':'completed_ungraded','terminal_completed':True,'initial_turns':1}
        return c

    def test_declared_collection_occurs_after_shutdown_and_purge_before_removal(self):
        c=self.controller()
        cleanup=c.cleanup()
        receipt=c.finish(cleanup, None)
        self.assertIsNotNone(receipt.get('collection'))
        self.assertEqual(receipt['collection']['snapshot'], snapshot())
        self.assertLess(self.trace.index('stopped'), self.trace.index('purged'))
        self.assertLess(self.trace.index('purged'), self.trace.index('capture'))
        self.assertLess(self.trace.index('capture'), self.trace.index('remove'))
        self.assertTrue(cleanup['complete'])
        self.assertEqual(receipt['status'],'completed_ungraded')


    def test_fixed_source_and_minimal_payload_are_invoked_under_isolated_python(self):
        c=self.controller(); frozen_source=c.collection_source
        with patch.object(trial.plan,'read_file',side_effect=AssertionError('must not reread sources')):
            result=c.cleanup()
        argv, timeout, payload=self.capture_arguments[0]
        self.assertIn('/usr/local/bin/python3', argv)
        self.assertEqual(argv[argv.index('-I'):], ['-I','-S','-c',frozen_source,'--root','/work/project'])
        self.assertLessEqual(timeout,5)
        self.assertEqual(json.loads(payload), {key:self.selected.data['collection'][key]
            for key in ('paths','max_file_bytes','max_total_bytes')})
        self.assertTrue(result['complete'])
        envelope=c.collection_result
        self.assertEqual(envelope['manifest_digest'], self.selected.digest)
        self.assertEqual(envelope['collection_digest'], trial.plan.digest(self.selected.data['collection']))
        self.assertEqual(envelope['collector_source_digest'], hashlib.sha256(frozen_source.encode()).hexdigest())
        self.assertFalse(envelope['snapshot']['quiescent_state_verified'])

    def test_changed_collector_source_refuses_before_attempt_creation(self):
        self.selected.data['sources']['native_trial_results.py']='f'*64
        with self.assertRaisesRegex(trial.plan.Refusal,'^collection_source$'):
            trial.Controller(self.selected)
        self.assertEqual(list((self.root/'state').iterdir()), [])

    def test_short_cleanup_budget_skips_capture_and_cleanup_still_completes(self):
        c=self.controller(); c.data['limits']['cleanup_seconds']=24
        result=c.cleanup()
        self.assertNotIn('capture', self.trace)
        self.assertTrue(result['complete'])
        self.assertEqual(c.collection_result['reason'],'collection_budget')
        self.assertEqual(c.finish(result,None)['status'],'blocked')

    def test_uncertain_process_ownership_does_not_capture(self):
        c=self.controller(); c.process_uncertain=True
        result=c.cleanup()
        self.assertNotIn('capture', self.trace)
        self.assertFalse(result['complete'])
        self.assertEqual(c.collection_result['reason'],'collection_preconditions')

    def test_native_home_not_purged_does_not_capture(self):
        c=self.controller(); c.home.cleanup.return_value={'home_absent':False}
        c.home.cleanup.side_effect=None
        result=c.cleanup()
        self.assertNotIn('capture', self.trace)
        self.assertFalse(result['complete'])
        self.assertEqual(c.collection_result['reason'],'collection_preconditions')

    def test_capture_failure_or_interruption_preserves_primary_and_cleans_resources(self):
        c=self.controller(); c.primary='interrupted'
        self.capture_response=KeyboardInterrupt()
        result=c.cleanup(); receipt=c.finish(result,None)
        self.assertTrue(result['complete'])
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        self.assertEqual(receipt['reason'],'interrupted')
        self.assertEqual(receipt['status'],'blocked')
        self.assertEqual(c.collection_result['reason'],'collection_transport')

    def test_expired_capture_subdeadline_does_not_reset_cleanup_deadline(self):
        c=self.controller(); real_command=c.command; saved_deadline=[]
        clock=[100.0]
        def delayed(args, **kwargs):
            result=real_command(args, **kwargs)
            if '-I' in args:
                saved_deadline.append(c.cleanup_deadline)
                clock[0]+=6
            return result
        with patch.object(trial.time,'monotonic',side_effect=lambda:clock[0]), \
             patch.object(c,'command',side_effect=delayed):
            result=c.cleanup()
        self.assertTrue(result['complete'])
        self.assertEqual(c.cleanup_deadline,145.0)
        self.assertEqual(saved_deadline,[145.0])
        self.assertEqual(c.collection_result['status'],'blocked')
        self.assertEqual(c.collection_result['reason'],'collection_transport')
        self.assertLessEqual(self.capture_arguments[0][1],5)

    def test_stale_container_owner_blocks_capture_but_not_owned_cleanup(self):
        c=self.controller(); inspect=c.inspect; seen=[]
        def changed(name, **kwargs):
            value=inspect(name, **kwargs)
            if kwargs.get('timeout') is not None and not seen:
                seen.append(True); value=copy.deepcopy(value); value['Id']='f'*64
            return value
        with patch.object(c,'inspect',side_effect=changed):
            result=c.cleanup()
        self.assertTrue(result['complete'])
        self.assertNotIn('capture', self.trace)
        self.assertEqual(c.collection_result['reason'],'collection_boundary')

    def test_malformed_transport_is_blocked_without_losing_cleanup(self):
        c=self.controller(); self.capture_response['stop_reason']='output_limit'
        result=c.cleanup(); receipt=c.finish(result,None)
        self.assertTrue(result['complete'])
        self.assertEqual(receipt['status'],'blocked')
        self.assertEqual(receipt['reason'],'collection_incomplete')
        self.assertEqual(c.collection_result['snapshot'],None)
        self.assertNotIn('output_limit',json.dumps(receipt))

    def test_observed_missing_is_a_snapshot_not_a_task_success(self):
        value=snapshot()
        value['files']=[{'path':'result.txt','status':'missing','bytes':None,'sha256':None}]
        self.capture_response['stdout']=json.dumps(value)
        c=self.controller(); cleanup=c.cleanup(); receipt=c.finish(cleanup,None)
        self.assertEqual(receipt['status'],'completed_ungraded')
        self.assertEqual(receipt['semantic_task_correctness'],'ungraded')
        self.assertFalse(receipt['selected_task_file_hashes_retained'])

    def test_recovery_never_invokes_the_collector(self):
        c=self.controller(); c.launch_called=c.launch_complete=False; c.live=None; c.home=None
        c.release()
        journal, records=trial.Journal.resume(c.attempt/'records',self.selected.data['limits']['retained_bytes'])
        with patch.object(trial,'supported_host'), \
             patch.object(trial,'read_recovery',return_value=(self.selected.data,records,journal)):
            result=trial.recover(c.attempt)
        self.assertEqual(result['status'],'reconciled')
        self.assertNotIn('capture',self.trace)
        self.assertFalse(self.docker.containers)

    def test_snapshot_validator_rejects_extra_missing_or_fabricated_fields(self):
        declaration=self.selected.data['collection']
        invalid=[]
        for key,value in [('schema_version',True),('kind','other'),('quiescent_state_verified',True),
                          ('reason','agent-says-passed'),('status','passed'),('files',[])]:
            candidate=snapshot(); candidate[key]=value; invalid.append(candidate)
        extra=snapshot(); extra['success']=True; invalid.append(extra)
        duplicate=snapshot(); duplicate['files']*=2; invalid.append(duplicate)
        for key,value in [('path','other.txt'),('status','passed'),('bytes',True),
                          ('bytes',65537),('sha256','not-a-digest')]:
            candidate=snapshot(); candidate['files'][0][key]=value; invalid.append(candidate)
        extra=snapshot(); extra['files'][0]['success']=True; invalid.append(extra)
        missing=snapshot(); missing['files'][0].update(status='missing'); invalid.append(missing)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises((trial.plan.Refusal, ValueError)):
                    trial.validate_snapshot(dict(self.capture_response,stdout=json.dumps(value)),declaration)
        for changes in [{'exit':True},{'exit':1},{'stderr':'UNRETAINED_DIAGNOSTIC'},
                        {'stop_reason':'timeout'},{'stdout':'{}'},
                        {'stdout':'{"schema_version":1,"schema_version":1}'},
                        {'stdout':'{"value":NaN}'}]:
            with self.subTest(changes=changes):
                with self.assertRaises((trial.plan.Refusal,ValueError)):
                    trial.validate_snapshot(dict(self.capture_response,**changes),declaration)

    def test_snapshot_order_total_and_explicit_false_are_enforced(self):
        declaration=copy.deepcopy(self.selected.data['collection'])
        declaration.update(paths=['result.txt','other.txt'], max_total_bytes=3)
        value=snapshot(); second=copy.deepcopy(value['files'][0]); second['path']='other.txt'
        value['files'].append(second)
        result=dict(self.capture_response, stdout=json.dumps(value))
        with self.assertRaises(trial.plan.Refusal): trial.validate_snapshot(result,declaration)
        declaration['max_total_bytes']=4
        self.assertEqual(trial.validate_snapshot(result,declaration),value)
        value['files'].reverse()
        with self.assertRaises(trial.plan.Refusal):
            trial.validate_snapshot(dict(result,stdout=json.dumps(value)),declaration)
        value=snapshot(); value['quiescent_state_verified']=0
        with self.assertRaises(trial.plan.Refusal):
            trial.validate_snapshot(dict(result,stdout=json.dumps(value)),self.selected.data['collection'])

    def test_setup_without_an_observed_turn_cannot_be_collected_as_missing_output(self):
        c=self.controller(); c.observation['initial_turns']=0
        result=c.cleanup()
        self.assertTrue(result['complete'])
        self.assertNotIn('capture',self.trace)
        self.assertIsNone(c.collection_result['snapshot'])
        self.assertEqual(c.finish(result,None)['status'],'blocked')

    def test_collector_blocked_result_remains_blocked(self):
        value=snapshot(); value.update(status='blocked',files=[],reason='unsafe_path')
        self.capture_response.update(exit=1,stdout=json.dumps(value))
        c=self.controller(); result=c.cleanup(); receipt=c.finish(result,None)
        self.assertTrue(result['complete'])
        self.assertEqual(receipt['status'],'blocked')
        self.assertEqual(c.collection_result['reason'],'unsafe_path')

    def test_snapshot_journal_failure_does_not_skip_mandatory_resource_cleanup(self):
        c=self.controller(); save=c.journal.save
        def fail_result(label,*args,**kwargs):
            if label=='collection_result':raise OSError('UNRETAINED_DIAGNOSTIC')
            return save(label,*args,**kwargs)
        with patch.object(c.journal,'save',side_effect=fail_result):
            result=c.cleanup()
        self.assertTrue(result['complete'])
        self.assertTrue(c.capture_failed)
        self.assertFalse(self.docker.containers); self.assertIsNone(self.docker.volume)
        self.assertEqual(c.finish(result,None)['status'],'blocked')


if __name__=='__main__':unittest.main()
