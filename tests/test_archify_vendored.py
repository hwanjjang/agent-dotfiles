"""The vendored Archify package: its recorded identity agrees across the repository, and every
documented diagram type has a bundled example that its own validator accepts."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/archify'
TYPES = ('architecture', 'workflow', 'sequence', 'dataflow', 'lifecycle', 'erd', 'class', 'tree', 'timeline', 'waterfall')


class VendoredArchifyTests(unittest.TestCase):
    def test_recorded_identity_agrees_everywhere(self):
        provenance = json.loads((SKILL / 'provenance.json').read_text())
        package = json.loads((SKILL / 'package.json').read_text())
        release = json.loads((SKILL / 'skill-release.json').read_text())
        frontmatter = (SKILL / 'SKILL.md').read_text().split('---')[1]
        declared = re.search(r'^\s+version: "([^"]+)"', frontmatter, re.M).group(1)
        self.assertRegex(provenance['revision'], r'^[0-9a-f]{40}$')
        self.assertRegex(provenance['tree'], r'^[0-9a-f]{40}$')
        self.assertEqual(provenance['release'], 'v' + package['version'])
        self.assertEqual(package['version'], release['version'])
        self.assertEqual(declared, '.'.join(package['version'].split('.')[:2]))
        registry = {entry['id']: entry for entry in json.loads((ROOT / 'tools/registry.json').read_text())['entries']}
        self.assertEqual(registry['archify']['revision'], provenance['revision'])
        explanations = json.loads((ROOT / 'docs/map/skill-explanations.json').read_text())['entries']
        self.assertEqual(next(e for e in explanations if e['id'] == 'archify')['adopted_revision'], provenance['revision'])
        catalog = (ROOT / 'docs/map/catalog.json').read_text()
        self.assertIn(f"tt-a1i/archify/blob/{provenance['revision']}/archify/SKILL.md", catalog)
        self.assertEqual(provenance['adaptations'], [])

    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for the bundled renderer')
    def test_bundled_examples_validate_for_every_documented_type(self):
        for kind in TYPES:
            examples = sorted((SKILL / 'examples').glob(f'*.{kind}.json'))
            with self.subTest(kind):
                self.assertTrue(examples, f'no bundled {kind} example')
                for example in examples:
                    result = subprocess.run(['node', str(SKILL / 'bin/archify.mjs'), 'validate', kind, str(example), '--json'],
                                            cwd=ROOT, capture_output=True, text=True, timeout=120)
                    self.assertEqual(result.returncode, 0, f'{example.name}: {result.stdout[-400:]}{result.stderr[-400:]}')
                    self.assertTrue(json.loads(result.stdout)['ok'], example.name)


if __name__ == '__main__':
    unittest.main()
