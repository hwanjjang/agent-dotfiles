"""Lossy source-mismatch diagnostics from synthetic native envelopes only."""
import json
import unittest

import test_native_trial_qualification as fixtures
import native_trial_qualification as q

SCRIPT = '// @exec: {"yield_time_ms": 30000}\ntext("FIXED_PRIVATE_BODY");\n'


class InputDiagnosticTests(unittest.TestCase):
    def project(self, value, *, call='PRIVATE_CALL_ID', omit=False):
        probe=q.Qualification(SCRIPT, fixtures.CHALLENGE)
        item=dict(type='custom_tool_call', name='exec', call_id=call, input=value)
        if omit:item.pop('input')
        probe.accept(fixtures.event(item),'thread','turn')
        return probe

    def test_identifier_and_script_mismatches_are_independently_visible(self):
        for call, value, identifier, matches in ((None,SCRIPT,False,True),
                ('PRIVATE_CALL_ID','PRIVATE_DIFFERENT_BODY',True,False),
                ('','PRIVATE_DIFFERENT_BODY',False,False)):
            with self.subTest(identifier=identifier,matches=matches):
                result=self.project(value,call=call).summary()
                self.assertEqual(result['reason'],'script_or_call_mismatch')
                self.assertEqual(result['call_id_valid'],identifier)
                self.assertEqual(result['input_matches_expected'],matches)
                self.assertFalse(result['script_exact'])
                self.assertEqual(result['status'],'blocked')

    def test_known_variants_are_diagnostics_only_not_normalized_acceptance(self):
        variants=[(' \n'+SCRIPT+'\t','outer_whitespace_only'),
                  (SCRIPT.replace('\n','\r\n'),'line_endings_only'),
                  (SCRIPT.replace('\n','\r'),'line_endings_only'),
                  (SCRIPT.split('\n',1)[1],'exec_pragma_only'),
                  (SCRIPT.replace('30000','10000'),'exec_pragma_only'),
                  ('// unrelated comment\n'+SCRIPT,'other')]
        for value,variant in variants:
            with self.subTest(variant=variant):
                probe=self.project(value)
                # Even otherwise correct output/final cannot rescue a mismatch.
                for event in fixtures.notifications()[1:]:probe.accept(event,'thread','turn')
                result=probe.summary()
                self.assertEqual(result['input_variant'],variant)
                self.assertEqual(result['reason'],'script_or_call_mismatch')
                self.assertFalse(result['script_exact'])
                self.assertFalse(result['boundary_checks_verified'])
                self.assertEqual(result['status'],'blocked')

    def test_shape_flags_are_bounded_and_never_retain_input_or_ids(self):
        for value,omit in ((None,True),(None,False),({},False),('',False),
                           ('PRIVATE'+('x'*q.MAX_SCRIPT),False)):
            with self.subTest(kind=type(value).__name__,omitted=omit):
                result=self.project(value,omit=omit).summary()
                shape={key.removeprefix('input_shape_'): value for key,value in result.items()
                       if key.startswith('input_shape_')}
                self.assertEqual(shape['present'],not omit)
                self.assertEqual(shape['is_string'],isinstance(value,str))
                self.assertEqual(shape['empty'],value=='')
                self.assertEqual(shape['over_limit'],isinstance(value,str) and len(value)>q.MAX_SCRIPT)
                self.assertTrue(all(type(v) is bool for v in shape.values()))
                self.assertEqual(result['input_variant'],'other')
                text=json.dumps(result)
                for private in ('PRIVATE',fixtures.CHALLENGE,'FIXED_PRIVATE_BODY'):
                    self.assertNotIn(private,text)
                self.assertLess(len(text),2500)

    def test_exact_script_still_requires_original_output_and_final_contract(self):
        probe=q.Qualification(fixtures.SCRIPT,fixtures.CHALLENGE)
        self.assertEqual(probe.summary()['input_variant'],'not_observed')
        for event in fixtures.notifications():probe.accept(event,'thread','turn')
        result=probe.summary()
        self.assertEqual(result['status'],'observed')
        self.assertEqual(result['input_variant'],'exact')
        self.assertTrue(result['input_matches_expected'])
        self.assertTrue(result['call_id_valid'])
        self.assertFalse(result['live_eligible'])

    def test_line_and_pragma_shape_is_finite_scalar_projection(self):
        probe=self.project(SCRIPT.replace('\n','\r\n'))
        result=probe.summary()
        self.assertTrue(result['input_shape_has_crlf'])
        self.assertFalse(result['input_shape_has_bare_cr'])
        self.assertTrue(result['input_shape_leading_exec_pragma'])
        self.assertTrue(all(value is None or type(value) in (bool,int,str)
                            for value in result.values()))


if __name__=='__main__':unittest.main()
