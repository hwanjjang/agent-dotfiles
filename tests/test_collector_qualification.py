"""The qualification denominator includes real subprocesses and an interrupted attempt."""
import copy
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qualify_collector',ROOT/'scripts/improvement/qualify_collector.py')
qualification=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualification)


class QualificationTests(unittest.TestCase):
    def test_small_run_checks_ledger_instead_of_neutral_stdout(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()) as captured:
            output=Path(temporary).resolve()/'evidence'
            result=qualification.qualify(output,count=8,workers=2,seconds=10)
            self.assertTrue(result['capacity_pass']);self.assertTrue(result['installed_snapshot_verified'])
            self.assertEqual(result['attempts'],8);self.assertEqual(result['durable_records'],8)
            self.assertEqual(result['interrupted_attempt']['returncode'],-9)
            self.assertEqual(result['interrupted_attempt']['records_before_retry'],0)
            self.assertEqual(result['reservation_gap_count'],1)
            self.assertEqual(result['replay']['records_after'],8)
            self.assertEqual(len((output/'callbacks.jsonl').read_text().splitlines()),8)
            self.assertTrue(qualification.capacity_pass(result))
            for field, bad in [('returncode',0), ('records_before_retry',1), ('reservation_after_kill',0)]:
                changed=copy.deepcopy(result);changed['interrupted_attempt'][field]=bad
                self.assertFalse(qualification.capacity_pass(changed), field)
            for field, bad in [('reservation_gap_count',0), ('missing_record_count',1), ('unique_sequence_count',7)]:
                changed=copy.deepcopy(result);changed[field]=bad
                self.assertFalse(qualification.capacity_pass(changed), field)
            for field, bad in [('all_neutral',False), ('attempts',0), ('records_after',9)]:
                changed=copy.deepcopy(result);changed['replay'][field]=bad
                self.assertFalse(qualification.capacity_pass(changed), field)
            import json
            printed=json.loads(captured.getvalue().splitlines()[-1])
            for field in ('latency','replay','interrupted_attempt','reservation_gap_count','source_sha256'):
                self.assertEqual(printed[field],result[field])
            self.assertEqual(result['workload'], 'PostToolUse only; no SessionStart/Stop boundary probes')
