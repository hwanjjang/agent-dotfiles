"""Behavioral checks for manual generation; run in the skill's dependency environment."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

READY = all(importlib.util.find_spec(x) for x in ('reportlab', 'pypdf', 'PIL'))
if READY:
    from PIL import Image
    from pypdf import PdfReader
    path = Path(__file__).resolve().parents[1] / 'skills/screenshot-manual/scripts/build_manual.py'
    spec = importlib.util.spec_from_file_location('build_manual', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


@unittest.skipUnless(READY, 'Install screenshot-manual/requirements.txt in an isolated environment')
class ManualTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        Image.new('RGB', (640, 400), '#dceae4').save(self.root/'screen.png')
        self.data = {'title':'Example manual','scenario':'Use synthetic test data.','steps':[
            {'title':'Open details','instruction':'Select a row.','expected':'Details appear.',
             'caption':'Selected row.','screenshot':'screen.png'},
            {'title':'Close details','instruction':'Press Escape.','expected':'Details close.',
             'caption':'Closed panel.','screenshot':'screen.png'}]}
        self.source, self.output = self.root/'manual.json', self.root/'manual.pdf'

    def run_build(self):
        self.source.write_text(json.dumps(self.data))
        return module.build(self.source, self.output)

    def test_pdf_preserves_steps_images_and_pagination(self):
        self.assertEqual(self.run_build(), 2)
        pages = PdfReader(self.output).pages
        self.assertEqual(len(pages), 2)
        for page, step in zip(pages, self.data['steps']):
            self.assertIn(step['expected'], page.extract_text())
            self.assertEqual(len(page.images), 1)

    def test_missing_screenshot_does_not_publish_partial_pdf(self):
        self.data['steps'][1]['screenshot'] = 'missing.png'
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.run_build()
        self.assertFalse(self.output.exists())

    def test_tall_screenshot_stays_with_its_step(self):
        Image.new('RGB', (400, 1600), '#dceae4').save(self.root/'screen.png')
        self.assertEqual(self.run_build(), 2)
        self.assertEqual(len(PdfReader(self.output).pages), 2)

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'existing artifact')
        with self.assertRaisesRegex(ValueError, 'Output exists'):
            self.run_build()
        self.assertEqual(self.output.read_bytes(), b'existing artifact')

    def test_external_screenshot_path_is_rejected(self):
        self.data['steps'][0]['screenshot'] = '../other.png'
        with self.assertRaisesRegex(ValueError, 'relative'):
            self.run_build()

    def test_missing_font_is_reported_before_non_ascii_render(self):
        self.data['title'] = '사용자 매뉴얼'
        with self.assertRaisesRegex(ValueError, 'Non-ASCII'):
            self.run_build()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
