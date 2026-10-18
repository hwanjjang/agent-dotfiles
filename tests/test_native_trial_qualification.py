"""Synthetic notifications only: no native process, auth, network or executor."""
import copy
import importlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/improvement'))
from native_execution import BOUNDARY_EXPECTED

SCRIPT = 'text("fixed synthetic qualification script");'
CHALLENGE = '0123456789abcdef0123456789abcdef'


def event(item, method='rawResponseItem/completed', thread='thread', turn='turn'):
    return {'method': method, 'params': {'threadId': thread, 'turnId': turn, 'item': item}}


def output():
    lines = ['Script completed', 'Wall time 0.123 seconds (code-mode 0.100 seconds; overhead 0.023 seconds)', 'Output:']
    lines += ['BOUNDARY_CHECK:'+json.dumps({'check': key, 'result': value}) for key, value in BOUNDARY_EXPECTED.items()]
    lines += ['BOUNDARY_COMPLETED', 'REMOTE_CHALLENGE:'+CHALLENGE]
    return [{'type': 'input_text', 'text': '\n'.join(lines)}]


def notifications():
    return [event({'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'synthetic-call', 'input': SCRIPT}),
            event({'type': 'custom_tool_call_output', 'call_id': 'synthetic-call', 'output': output()}),
            event({'type': 'agentMessage', 'id': 'synthetic-final', 'phase': 'final_answer', 'text': CHALLENGE}, 'item/completed')]


class QualificationTests(unittest.TestCase):
    def test_exact_script_correlated_output_and_single_final_are_observed(self):
        Qualification = importlib.import_module('native_trial_qualification').Qualification
        probe = Qualification(SCRIPT, CHALLENGE)
        for value in notifications():
            probe.accept(value, 'thread', 'turn')
        summary = probe.summary()
        self.assertEqual(summary['status'], 'observed')
        self.assertTrue(summary['script_exact'])
        self.assertTrue(summary['boundary_checks_verified'])
        self.assertTrue(summary['challenge_output_match'])
        self.assertTrue(summary['final_match'])
        self.assertFalse(summary['live_eligible'])
        self.assertNotIn(CHALLENGE, json.dumps(summary))
        self.assertNotIn('synthetic-call', json.dumps(summary))


    def project(self, values):
        Qualification = importlib.import_module('native_trial_qualification').Qualification
        probe = Qualification(SCRIPT, CHALLENGE)
        for value in values:
            probe.accept(value, 'thread', 'turn')
        return probe

    def test_partial_catalog_exports_only_bounded_numeric_projection(self):
        values=notifications()[:2]
        projection={'advertised':{'mask':767,'count':9,'unknown':0,'duplicates':0},
                    'callable':{'mask':767,'count':9,'unknown':0,'duplicates':0}}
        def failed(result):
            return [{'type':'input_text','text':'Script failed\nWall time 0.1 seconds\nOutput:\nBOUNDARY_CHECK:'+json.dumps({'check':'catalog','result':result})+'\nScript error:\nError: Boundary check failed: inventory'}]
        values[1]['params']['item']['output']=failed(projection)
        result=self.project(values).summary()
        self.assertEqual(result['catalog_advertised_mask'],767)
        self.assertEqual(result['catalog_callable_count'],9)
        self.assertEqual(result['status'],'blocked')
        projection['advertised']['name']='UNTRUSTED_RAW_CONTENT'
        values[1]['params']['item']['output']=failed(projection)
        result=self.project(values).summary()
        self.assertIsNone(result['catalog_advertised_mask'])
        self.assertNotIn('UNTRUSTED_RAW_CONTENT',json.dumps(result))

    def test_missing_or_reordered_call_output_final_blocks(self):
        for values in (notifications()[1:], notifications()[:1]+notifications()[2:], notifications()[:2],
                       list(reversed(notifications())), [notifications()[2]]+notifications()[:2]):
            with self.subTest(values=[x['params']['item']['type'] for x in values]):
                self.assertEqual(self.project(values).summary()['status'], 'blocked')

    def test_script_identity_namespace_and_call_correlation_are_exact(self):
        for index, field, value in ((0,'input',SCRIPT+' '), (0,'name','exec_command'),
                                     (0,'namespace','untrusted'), (0,'call_id',''),
                                     (1,'call_id','other-call'), (1,'name','other-tool')):
            values=notifications();values[index]['params']['item'][field]=value
            with self.subTest(field=field, index=index):
                self.assertEqual(self.project(values).summary()['status'], 'blocked')

    def test_any_extra_or_unknown_raw_execution_blocks_even_after_success(self):
        for item in ({'type':'function_call','name':'list_agents','namespace':'collaboration','call_id':'extra','arguments':'{}'},
                     {'type':'function_call_output','output':'unsupported call: collaborationlist_agents'},
                     {'type':'local_shell_call'}, {'type':'web_search_call'}, {'type':'tool_search_call'},
                     {'type':'image_generation_call'}, {'type':'future_tool_call'},
                     notifications()[0]['params']['item'], notifications()[1]['params']['item']):
            with self.subTest(kind=item['type']):
                probe=self.project(notifications())
                self.assertEqual(probe.summary()['status'],'observed')
                probe.accept(event(item),'thread','turn')
                self.assertEqual(probe.summary()['status'],'blocked')

    def test_scope_mismatch_never_contributes_evidence(self):
        for index in range(3):
            for field in ('threadId','turnId'):
                values=notifications();values[index]['params'][field]='other'
                self.assertEqual(self.project(values).summary()['reason'],'scope_mismatch')
        probe=self.project(notifications()[:1])
        probe.accept(event(notifications()[1]['params']['item'],thread='other'), 'other','turn')
        self.assertEqual(probe.summary()['reason'],'scope_mismatch')

    def test_failed_cell_or_ambiguous_output_never_passes(self):
        original=output()[0]['text']
        changes=[original.replace('Script completed','Script failed'),
                 original.replace('Script completed','Script running with cell ID synthetic'),
                 original.replace('Script completed','Script terminated'),
                 original.replace('"protected_enoent": 5','"protected_enoent": 4'),
                 original.replace('"ipv4_tcp_errno": 101','"ipv4_tcp_errno": -1'),
                 original.replace('"body": true','"body": 1'),
                 original+'\nBOUNDARY_COMPLETED',
                 original+'\nBOUNDARY_CHECK:{"check":"unknown","result":true}',
                 original+'\nraw unexpected private text',
                 original.replace('"check": "catalog"','"check":"catalog","check":"catalog"')]
        for changed in changes:
            values=notifications();values[1]['params']['item']['output']=changed
            with self.subTest(changed=changes.index(changed)):
                self.assertEqual(self.project(values).summary()['reason'],'boundary_output_invalid')

    def test_scoped_child_write_or_missing_result_cannot_pass(self):
        import copy
        original = output()[0]['text']
        for change in ('success', 'missing'):
            lines = original.splitlines()
            for index, line in enumerate(lines):
                if line.startswith('BOUNDARY_CHECK:'):
                    record = json.loads(line[len('BOUNDARY_CHECK:'):])
                    if record['check'] == 'command':
                        if change == 'success': record['result']['scoped_io']['child']['denied']['installer_receipt']['write_errno'] = 0
                        else: del record['result']['scoped_io']['child']
                        lines[index] = 'BOUNDARY_CHECK:' + json.dumps(record)
            values = notifications(); values[1]['params']['item']['output'] = '\n'.join(lines)
            self.assertEqual(self.project(values).summary()['status'], 'blocked')

    def test_each_boundary_record_missing_or_duplicate_blocks(self):
        original=output()[0]['text'].splitlines()
        for name in BOUNDARY_EXPECTED:
            selected=next(line for line in original if '"check": "'+name+'"' in line)
            for changed in ('\n'.join(line for line in original if line!=selected), '\n'.join(original+[selected])):
                values=notifications();values[1]['params']['item']['output']=changed
                self.assertEqual(self.project(values).summary()['status'],'blocked')

    def test_challenge_must_appear_once_in_correlated_output(self):
        original=output()[0]['text']
        for changed in (original.replace('REMOTE_CHALLENGE:'+CHALLENGE,''),
                        original.replace(CHALLENGE,'f'*32),
                        original+'\nREMOTE_CHALLENGE:'+CHALLENGE,
                        original.replace('REMOTE_CHALLENGE:', 'OTHER_CHALLENGE:')):
            values=notifications();values[1]['params']['item']['output']=changed
            self.assertFalse(self.project(values).summary()['challenge_output_match'])
        values=notifications();values[1]=event({'type':'message','role':'user','content':output()})
        self.assertEqual(self.project(values).summary()['status'],'blocked')

    def test_plain_text_and_native_text_array_supported_but_media_rejected(self):
        values=notifications();values[1]['params']['item']['output']=output()[0]['text']
        self.assertEqual(self.project(values).summary()['status'],'observed')
        for malformed in ([], {'text':output()[0]['text']}, [{'type':'input_image','image_url':'synthetic'}],
                          [{'type':'input_text','text':'x'*65537}]):
            values=notifications();values[1]['params']['item']['output']=malformed
            self.assertEqual(self.project(values).summary()['status'],'blocked')

    def test_one_exact_final_only_and_commentary_is_not_a_final(self):
        for value in (CHALLENGE+'\n', ' '+CHALLENGE, '`'+CHALLENGE+'`', 'incorrect', None):
            values=notifications();values[-1]['params']['item']['text']=value
            self.assertEqual(self.project(values).summary()['status'],'blocked')
        self.assertEqual(self.project(notifications()+[notifications()[-1]]).summary()['status'],'blocked')
        commentary=event({'type':'agentMessage','phase':'commentary','text':'synthetic commentary'},'item/completed')
        self.assertEqual(self.project([commentary]+notifications()).summary()['status'],'observed')
        values=notifications();values[-1]['params']['item']['phase']=None
        self.assertEqual(self.project(values).summary()['status'],'observed')

    def test_retention_is_bounded_and_summary_contains_no_content_or_identity(self):
        probe=self.project(notifications())
        original=probe.summary();original['status']='tampered'
        self.assertEqual(probe.summary()['status'],'observed')
        for _ in range(1000):probe.accept(event({'type':'reasoning','encrypted_content':'private'}),'thread','turn')
        summary=probe.summary()
        self.assertEqual(summary['reason'],'item_limit');self.assertEqual(summary['items_observed'],65)
        self.assertTrue(all(value is None or type(value) in (bool,int,str) for value in summary.values()))
        serialized=json.dumps(summary)
        for raw in (SCRIPT,CHALLENGE,'synthetic-call','private'):
            self.assertNotIn(raw,serialized)
        for flag in ('raw_contents_retained','content_hashes_retained','challenge_value_retained','call_ids_retained',
                     'live_eligible','isolation_qualified','all_routes_qualified'):
            self.assertFalse(summary[flag])

    def test_invalid_constructor_and_malformed_event_fail_safely(self):
        Qualification=importlib.import_module('native_trial_qualification').Qualification
        for script,challenge in (('',CHALLENGE),('x'*32769,CHALLENGE),(SCRIPT,'wrong'),(SCRIPT,CHALLENGE.upper())):
            with self.assertRaises(ValueError):Qualification(script,challenge)
        for value in (None, {'method':'item/completed','params':None},
                      event({'type':None}), {'method':'rawResponseItem/completed','params':{'threadId':'thread','turnId':'turn'}}):
            probe=Qualification(SCRIPT,CHALLENGE);probe.accept(value,'thread','turn')
            self.assertEqual(probe.summary()['status'],'blocked')

    def test_partial_failed_cell_has_only_fixed_diagnostics_and_stays_blocked(self):
        values=notifications()
        lines=['Script failed','Wall time 0.1 seconds','Output:']
        for name in ('catalog','globals_imports','mcp'):
            lines.append('BOUNDARY_CHECK:'+json.dumps({'check':name,'result':BOUNDARY_EXPECTED[name]}))
        lines += ['Script error:','Error: Boundary check failed: command completion']
        values[1]['params']['item']['output']='\n'.join(lines)
        summary=self.project(values).summary()
        self.assertEqual(summary['status'],'blocked')
        self.assertEqual(summary['boundary_header'],'failed')
        self.assertEqual(summary['boundary_record_seen_mask'],7)
        self.assertEqual(summary['boundary_record_matching_mask'],7)
        self.assertEqual(summary['failure_stage'],'command_completion')
        self.assertFalse(summary['boundary_checks_verified'])
        self.assertFalse(summary['challenge_output_match'])
        self.assertFalse(summary['final_match'])

    def test_diagnostic_masks_do_not_promote_unknown_malformed_or_duplicate_records(self):
        valid='BOUNDARY_CHECK:'+json.dumps({'check':'catalog','result':BOUNDARY_EXPECTED['catalog']})
        malformed='BOUNDARY_CHECK:{"check":"catalog","check":"catalog","result":{}}'
        unknown='BOUNDARY_CHECK:'+json.dumps({'check':'private-secret-name','result':True})
        invalid='BOUNDARY_CHECK:'+json.dumps({'check':'catalog','result':{'private-secret-value':True}})
        for body,seen,matching in (([malformed,unknown],0,0),([invalid],1,0),([valid,valid],1,0),([valid],1,1)):
            values=notifications();values[1]['params']['item']['output']='\n'.join(
                ['Script failed','Wall time 0.1 seconds','Output:']+body)
            summary=self.project(values).summary()
            self.assertEqual(summary['status'],'blocked')
            self.assertEqual(summary['boundary_record_seen_mask'],seen)
            self.assertEqual(summary['boundary_record_matching_mask'],matching)
            self.assertNotIn('private-secret',json.dumps(summary))
        summary=self.project(notifications()).summary()
        self.assertEqual(summary['boundary_header'],'completed')
        self.assertEqual(summary['boundary_record_seen_mask'],63)
        self.assertEqual(summary['boundary_record_matching_mask'],63)

    def test_failure_stage_requires_one_exact_native_error_block_and_trusted_label(self):
        for suffix in (['Error: Boundary check failed: skill scope'],
                       ['Script error:','Error: Boundary check failed: private-secret'],
                       ['Script error:','Error: Boundary check failed: skill scope private-secret'],
                       ['Script error:','Error: Boundary check failed: skill scope','Script error:','Error: Boundary check failed: mcp']):
            values=notifications();values[1]['params']['item']['output']='\n'.join(
                ['Script failed','Wall time 0.1 seconds','Output:']+suffix)
            summary=self.project(values).summary()
            self.assertEqual(summary['failure_stage'],'unknown')
            self.assertNotIn('private-secret',json.dumps(summary))
        for source,expected in (('skill scope','skill_scope'),('inventory','inventory'),('remaining exposed routes','remaining_exposed_routes'),('callable tools','callable_tools')):
            values=notifications();values[1]['params']['item']['output']='\n'.join(
                ['Script failed','Wall time 0.1 seconds','Output:','Script error:','Error: Boundary check failed: '+source])
            summary=self.project(values).summary()
            self.assertEqual(summary['failure_stage'],expected)
            self.assertEqual(summary['status'],'blocked')

    def test_unmatched_output_does_not_contribute_diagnostics(self):
        values=notifications();values[1]['params']['item']['call_id']='unmatched'
        summary=self.project(values).summary()
        self.assertEqual(summary['boundary_header'],'other')
        self.assertEqual(summary['boundary_record_seen_mask'],0)
        self.assertEqual(summary['boundary_record_matching_mask'],0)
        self.assertEqual(summary['failure_stage'],'unknown')

    def test_nonexecuting_noise_does_not_replace_raw_evidence(self):
        noise=[{'method':'thread/tokenUsage/updated','params':{}},
               event({'type':'message','content':output()}),
               event({'type':'commandExecution','exitCode':0},'item/completed')]
        self.assertEqual(self.project(noise).summary()['status'],'blocked')
        self.assertEqual(self.project(noise+notifications()).summary()['status'],'observed')


if __name__ == '__main__':
    unittest.main()
