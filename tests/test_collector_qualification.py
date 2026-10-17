"""The qualification denominator includes real subprocesses and an interrupted attempt."""
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
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            output=Path(temporary).resolve()/'evidence'
            result=qualification.qualify(output,count=8,workers=2,seconds=10)
            self.assertTrue(result['capacity_pass']);self.assertTrue(result['installed_snapshot_verified'])
            self.assertEqual(result['attempts'],8);self.assertEqual(result['durable_records'],8)
            self.assertEqual(result['interrupted_attempt']['returncode'],-9)
            self.assertEqual(result['interrupted_attempt']['records_before_retry'],0)
            self.assertEqual(result['reservation_gap_count'],1)
            self.assertEqual(result['replay']['records_after'],8)
            self.assertEqual(len((output/'callbacks.jsonl').read_text().splitlines()),8)
