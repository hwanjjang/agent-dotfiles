"""Actual reviewed-case CLI path, independent of native/model execution."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_improvement_cases as cases

CLI = Path(__file__).resolve().parents[1] / 'scripts/improvement/cases.py'


class CaseCliTests(unittest.TestCase):
    setUp = cases.CaseTests.setUp
    def test_cli_prepare_preview_review_export_and_refusals(self):
        def call(*args, body=None, expected=0):
            result=subprocess.run([sys.executable,str(CLI),'--home',str(self.home),*args],
                input=None if body is None else json.dumps(body).encode(),capture_output=True,timeout=10)
            self.assertEqual(result.returncode,expected,result.stderr)
            self.assertEqual(result.stderr,b'')
            return json.loads(result.stdout)
        request=dict(revision_id=self.task['revision_id'],feedback_ids=[self.feedback['feedback_id']],
                     synthetic_case=cases.synthetic_case(),request_id='cli')
        case=call('prepare','--task',self.task['task_id'],body=request)
        common=['--task',self.task['task_id'],'--case',case['case_id']]
        preview=call('show',*common)
        self.assertNotIn('PRIVATE_',json.dumps(preview))
        self.assertEqual(call('export',*common,'--digest',case['case_digest'],
            '--output',str(self.output/'case.json'),expected=1)['reason'],'case_not_reviewed')
        call('review',*common,'--digest',case['case_digest'],'--reviewer','maintainer',
             '--confirm-synthetic','--confirm-privacy-review')
        call('export',*common,'--digest',case['case_digest'],'--output',str(self.output/'case.json'))
        data=json.loads((self.output/'case.json').read_text())
        self.assertEqual(data['case_digest'],case['case_digest'])
        call('prepare','--task',self.task['task_id'],body=dict(request,private_evidence='no'),expected=1)
