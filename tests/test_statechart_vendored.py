"""The vendored statechart package: its recorded identity agrees across the repository, its files match
the recorded upstream digests, and with TLC available the launcher reports a small model's verdicts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/statechart'
LAUNCHER = SKILL / 'scripts/statechart'
TLA2TOOLS = os.environ.get('TLA2TOOLS', '')

SPEC = """---- MODULE Pay ----
EXTENDS Naturals
VARIABLES balance, charged
vars == <<balance, charged>>
Init == balance = 10 /\\ charged = 0
Charge == charged = 0 /\\ balance >= 5 /\\ balance' = balance - 5 /\\ charged' = charged + 1
Retry == charged > 0 /\\ charged < 3 /\\ balance' = balance - 5 /\\ charged' = charged + 1
Done == charged = 3 /\\ UNCHANGED vars
Next == Charge \\/ Retry \\/ Done
NonNegative == balance >= 0
AtMostThree == charged <= 3
====
"""


class VendoredStatechartTests(unittest.TestCase):
    def test_recorded_identity_agrees_everywhere(self):
        provenance = json.loads((SKILL / 'provenance.json').read_text())
        revision = provenance['revision']
        self.assertRegex(revision, r'^[0-9a-f]{40}$')
        self.assertEqual(provenance['adaptations'], [])
        registry = {entry['id']: entry for entry in json.loads((ROOT / 'tools/registry.json').read_text())['entries']}
        self.assertEqual(registry['statechart']['revision'], revision)
        explanations = json.loads((ROOT / 'docs/map/skill-explanations.json').read_text())['entries']
        self.assertEqual(next(e for e in explanations if e['id'] == 'statechart')['adopted_revision'], revision)
        self.assertIn(f'cursor/plugins/blob/{revision}/pstack/skills/statechart/SKILL.md',
                      (ROOT / 'docs/map/catalog.json').read_text())
        self.assertIn(revision, (ROOT / 'docs/decisions/statechart.md').read_text())
        self.assertIn(revision[:7], (ROOT / 'docs/upstream/README.md').read_text())

    def test_vendored_files_match_the_recorded_digests(self):
        recorded = json.loads((SKILL / 'provenance.json').read_text())['files']
        actual = {str(path.relative_to(SKILL)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(SKILL.rglob('*')) if path.is_file() and path != SKILL / 'provenance.json'}
        self.assertEqual(sorted(actual), sorted(recorded), 'the vendored file set differs from the record')
        changed = sorted(name for name in actual if actual[name] != recorded[name])
        self.assertEqual(changed, [], 'vendored files must stay byte-identical to the pinned upstream')
        self.assertTrue(os.access(LAUNCHER, os.X_OK), 'the launcher must stay executable')

    # Without TLA2TOOLS the command would install Java and TLC with mise over the network, so skip.
    @unittest.skipUnless(TLA2TOOLS and Path(TLA2TOOLS).is_file(), 'set TLA2TOOLS to a tla2tools.jar')
    def test_small_model_reports_its_verdicts(self):
        probe = subprocess.run([str(LAUNCHER)], capture_output=True, text=True, timeout=60)
        if probe.returncode == 127:
            self.skipTest(probe.stderr.strip())
        with tempfile.TemporaryDirectory() as scratch:
            work = Path(scratch)
            (work / 'Pay.tla').write_text(SPEC)
            cases = {'broken': ('NonNegative', 1), 'holding': ('AtMostThree', 0)}
            for name, (rule, code) in cases.items():
                with self.subTest(name):
                    (work / f'{name}.cfg').write_text(f'INIT Init\nNEXT Next\nINVARIANT {rule}\n')
                    out = work / f'out-{name}'
                    result = subprocess.run([str(LAUNCHER), str(work / 'Pay.tla'), '--config', str(work / f'{name}.cfg'),
                                             '--out', str(out)], capture_output=True, text=True, timeout=300,
                                            env=dict(os.environ, TLA2TOOLS=TLA2TOOLS))
                    self.assertEqual(result.returncode, code, result.stderr[-800:])
                    report = (out / 'report.md').read_text()
                    chart = (out / 'chart.mmd').read_text().splitlines()
                    if code:
                        self.assertIn('## NonNegative breaks', report)
                        self.assertIn('The shortest path has 3 steps', report)
                        self.assertIn('  class s3 breaks', chart)
                    else:
                        self.assertIn('## Rules that hold', report)
                        self.assertIn('AtMostThree', report)
                        self.assertFalse([line for line in chart if line.strip().endswith(' breaks')], chart)


if __name__ == '__main__':
    unittest.main()
