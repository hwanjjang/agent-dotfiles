"""Catch workflow navigation drift while preserving the original catalog."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = json.loads((ROOT / 'docs/map/workflow.json').read_text())
        self.entries = json.loads((ROOT / 'docs/map/catalog.json').read_text())['entries']

    def validate(self):
        build_workflow.validate_workflow(self.workflow, self.entries, ROOT)

    def test_current_navigation_covers_real_stages_and_skills(self):
        self.validate()

    def test_removed_stage_or_wrong_order_is_rejected(self):
        original = copy.deepcopy(self.workflow['stages'])
        self.workflow['stages'].pop(1)
        with self.assertRaisesRegex(ValueError, 'canonical stage set'):
            self.validate()
        self.workflow['stages'] = original
        self.workflow['stages'][0], self.workflow['stages'][1] = original[1], original[0]
        with self.assertRaisesRegex(ValueError, 'stage order'):
            self.validate()

    def test_new_state_stage_requires_navigation_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'routing.md').write_text('Synthetic routing.')
            stages = [s['id'] for s in self.workflow['stages']] + ['independent-verification', 'new-stage']
            (root / 'stages.py').write_text('STAGES = ' + repr(tuple(stages)))
            self.workflow.update(source='routing.md', stage_source='stages.py')
            with self.assertRaisesRegex(ValueError, 'canonical stage set'):
                build_workflow.validate_workflow(self.workflow, self.entries, root)

    def test_unknown_skill_and_missing_trigger_are_rejected(self):
        self.workflow['stages'][0]['steps'][0]['skills'] = ['does-not-exist']
        with self.assertRaisesRegex(ValueError, 'unknown item'):
            self.validate()
        self.workflow['stages'][0]['steps'][0]['skills'] = ['sdlc']
        del self.workflow['triggers']['grill-me']
        with self.assertRaisesRegex(ValueError, 'contextual trigger'):
            self.validate()

    def test_new_skill_needs_a_workflow_or_anytime_home(self):
        entry = copy.deepcopy(next(e for e in self.entries if e['kind'] == 'skill'))
        entry['id'] = 'new-skill'
        self.entries.append(entry)
        with self.assertRaisesRegex(ValueError, 'unmapped skills: new-skill'):
            self.validate()

    def test_render_keeps_original_catalog_and_escapes_navigation(self):
        files = ['catalog.json', 'index.html', 'viewer.template.html']
        before = {f: (ROOT / 'docs/map' / f).read_bytes() for f in files}
        output = build_workflow.build(ROOT)
        self.assertIn('AK SDLC skill map', output)
        self.assertEqual(before, {f: (ROOT / 'docs/map' / f).read_bytes() for f in files})
        catalog = json.loads(before['catalog.json'])
        self.workflow['node_labels']['tdd'] = '</script><img src=x>'
        with patch.object(build_workflow.json, 'loads', side_effect=[catalog, self.workflow]):
            rendered = build_workflow.build(ROOT)
        self.assertEqual(rendered.count('</script>'), 1)
        self.assertNotIn('</script><img src=x>', rendered)
        self.assertIn('&lt;/script&gt;', rendered)

    def test_upstream_ui_assets_remain_identical_to_pinned_source(self):
        import hashlib
        vendor = ROOT / 'docs/map/vendor/super-board'
        provenance = json.loads((vendor / 'provenance.json').read_text())
        for name, record in provenance['files'].items():
            actual = hashlib.sha256((vendor / name).read_bytes()).hexdigest()
            self.assertEqual(actual, record['local_sha256'], name)
            if name != 'layout_sdlc.py':
                self.assertEqual(actual, record['upstream_sha256'], name)
        self.assertEqual(hashlib.sha256((ROOT / 'docs/map/workflow.template.html').read_bytes()).hexdigest(),
                         provenance['template']['sha256'])

    def test_interview_alternatives_are_not_serialized(self):
        catalog = json.loads((ROOT / 'docs/map/catalog.json').read_text())
        data = build_workflow.map_data(self.workflow, catalog)
        branches = [c['chain'] for c in data['categories'] if c['stage'] == 'intent']
        self.assertEqual(branches, [['grill-me'], ['grill-with-docs']])

    def test_explanations_have_reviewed_local_sources(self):
        import hashlib
        manifest = json.loads((ROOT / 'docs/map/skill-explanations.json').read_text())
        rich = {e['id']: e for e in self.entries if 'explanation' in e}
        self.assertEqual(set(rich), {e['id'] for e in self.entries if e['kind'] == 'skill'})
        self.assertEqual(set(rich), {e['id'] for e in manifest['entries']})
        for record in manifest['entries']:
            source = ROOT / rich[record['id']]['source']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                             record['local_skill_sha256'], record['id'] + ': review explanation after source changes')
            for path, digest in record.get('supporting_sources', {}).items():
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                                 digest, record['id'] + ': review explanation after supporting source changes')

    def test_enriched_details_reuse_shared_catalog(self):
        data = build_workflow.map_data(self.workflow, {'entries': self.entries})
        for entry in self.entries:
            if 'explanation' not in entry:
                continue
            detail = data['skills'][entry['id']]
            self.assertEqual(detail['example'], entry['explanation']['example'])
            self.assertEqual(detail['behindTheScenes'], entry['explanation']['flows'])
            self.assertEqual(detail['calls'], entry['explanation']['calls'])

    def test_check_missing_or_stale_output_never_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'docs/map'
            directory.mkdir(parents=True)
            original = directory / 'index.html'
            original.write_text('Original catalog sentinel')
            output = directory / 'workflow.html'
            with patch.object(build_workflow, 'ROOT', root), patch.object(build_workflow, 'build', return_value='new'), patch('sys.argv', ['build_workflow.py', '--check']):
                self.assertEqual(build_workflow.main(), 1)
                self.assertFalse(output.exists())
                output.write_text('stale')
                self.assertEqual(build_workflow.main(), 1)
                self.assertEqual(output.read_text(), 'stale')
            self.assertEqual(original.read_text(), 'Original catalog sentinel')


if __name__ == '__main__':
    unittest.main()
