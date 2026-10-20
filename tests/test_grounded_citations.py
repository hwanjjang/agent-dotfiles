"""Exercise the portable citation CLI through isolated task files."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/grounded-citations/scripts/sources.py'


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / 'task/sources.json'

    def cli(self, *args, expected=0, ledger=True):
        command = [sys.executable, '-B', str(SCRIPT)]
        if ledger:
            command += ['--ledger', str(self.ledger)]
        result = subprocess.run(command + list(args), cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_standalone_task_ledger(self):
        self.cli('add', 'https://example.com/source', '--title', 'Source')
        self.assertEqual(json.loads(self.ledger.read_text())['sources'][0]['id'], 1)
        other = self.root / 'second.json'
        subprocess.run([sys.executable, '-B', str(SCRIPT), '--ledger', str(other), 'list'],
                       cwd=self.root, check=True, capture_output=True)
        self.assertFalse(other.exists())

    def test_missing_ledger_is_rejected_without_creating_global_state(self):
        self.cli('reset', ledger=False, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_sources_are_stable_and_ingest_retains_titles(self):
        data = self.root / 'retrieval.json'
        data.write_text(json.dumps({'results': [
            {'url': 'https://example.com/a#part', 'title': 'A'},
            {'link': 'https://example.com/a/'}, {'url': 'https://example.com/b'}]}))
        self.cli('ingest', str(data))
        self.cli('add', 'https://example.com/a')
        rows = json.loads(self.cli('list', '--json').stdout)
        self.assertEqual([(r['id'], r['title']) for r in rows], [(1, 'A'), (2, '')])

    def test_unsupported_or_credential_urls_do_not_mutate_ledger(self):
        self.cli('add', 'https://example.com/valid')
        before = self.ledger.read_bytes()
        for url in ['file:///private/example', 'javascript:alert(1)', 'https://user:secret@example.com/a']:
            self.cli('add', url, expected=1)
            self.assertEqual(self.ledger.read_bytes(), before)

    def test_quote_must_match_and_evidence_mode_requires_it(self):
        self.cli('add', 'https://example.com/source')
        draft = self.root / 'draft.md'
        draft.write_text('The measured limit is five requests.[1]\n\n## Sources\n\n[1] https://example.com/source\n')
        self.cli('verify', str(draft), '--evidence', expected=1)
        evidence = self.root / 'page.txt'
        evidence.write_text('The measured limit is **five requests**.\n')
        self.cli('quote', '1', '--text', 'The measured limit is ten requests.', '--from', str(evidence), expected=1)
        self.cli('quote', '1', '--text', 'The measured limit is five requests.', '--from', str(evidence))
        self.cli('verify', str(draft), '--evidence', '--strict')

    def test_unknown_and_wrong_url_references_fail(self):
        self.cli('add', 'https://example.com/source')
        draft = self.root / 'draft.md'
        draft.write_text('The result needs a supporting source.[9]\n\n## Sources\n\n[9] https://example.com/other\n')
        self.cli('verify', str(draft), expected=1)
        draft.write_text('The result needs a supporting source.[1]\n\n## Sources\n\n[1] https://example.com/wrong\n')
        self.cli('verify', str(draft), expected=1)

    def test_render_is_idempotent_and_keeps_report_body(self):
        self.cli('add', 'https://example.com/source')
        draft = self.root / 'draft.md'
        draft.write_text('A claim with enough words needs evidence.[1]\n')
        self.cli('render', '--replace-in', str(draft))
        first = draft.read_bytes()
        self.cli('render', '--replace-in', str(draft))
        self.assertEqual(draft.read_bytes(), first)
        self.cli('verify', str(draft), '--strict')

    def test_fenced_sources_example_cannot_hide_claims_or_delete_body(self):
        self.cli('add', 'https://example.com/source')
        page = self.root / 'page.txt'
        page.write_text('The source supports this example sentence.\n')
        self.cli('quote', '1', '--text', page.read_text(), '--from', str(page))
        draft = self.root / 'draft.md'
        body = ('The source supports this example sentence.[1]\n\n'
                '````markdown\n## Sources\n[1] https://example.com/source\n'
                '```\nA nested fence marker stays in this example.\n````\n\n'
                'An unsupported claim appears after the example.[9]\n')
        draft.write_text(body)
        self.cli('verify', str(draft), '--evidence', expected=1)
        self.cli('render', '--replace-in', str(draft))
        self.assertTrue(draft.read_text().startswith(body))
        self.cli('verify', str(draft), '--evidence', expected=1)

    def test_ingest_invalid_later_url_leaves_ledger_unchanged(self):
        payload = self.root / 'retrieval.json'
        payload.write_text(json.dumps([{'url': 'https://example.com/new'},
                                       {'url': 'https://user:secret@example.com/private'}]))
        self.cli('ingest', str(payload), expected=1)
        self.assertFalse(self.ledger.exists())
        self.cli('add', 'https://example.com/original')
        before = self.ledger.read_bytes()
        self.cli('ingest', str(payload), expected=1)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_sources_suffix_citations_are_checked_and_body_is_preserved(self):
        self.cli('add', 'https://example.com/source')
        draft = self.root / 'draft.md'
        for suffix in ['## Appendix\nAppendix claim cites [5] here.\n',
                       'A later paragraph cites [5] here.\n',
                       '```python\nprint("keep this code")\n```\nLater prose cites [5].\n']:
            with self.subTest(suffix=suffix):
                draft.write_text('Claim [1].\n\n## Sources\n\n[1] https://example.com/source\n\n' + suffix)
                self.cli('verify', str(draft), expected=1)
                self.cli('render', '--replace-in', str(draft))
                self.assertIn(suffix, draft.read_text())
                self.assertIn('Claim [1].', draft.read_text())
                self.cli('verify', str(draft), expected=1)
                once = draft.read_bytes()
                self.cli('render', '--replace-in', str(draft))
                self.assertEqual(draft.read_bytes(), once)

    def test_multiline_evidence_render_round_trip(self):
        self.cli('add', 'https://example.com/source')
        quote = 'First line of evidence.\nSecond line mentions [8] in the source.'
        evidence = self.root / 'page.txt'
        evidence.write_text(quote)
        self.cli('quote', '1', '--text', quote, '--from', str(evidence))
        draft = self.root / 'draft.md'
        draft.write_text('First line of evidence.[1]\n')
        self.cli('render', '--style', 'evidence', '--replace-in', str(draft))
        self.cli('verify', str(draft), '--strict', '--evidence')
        once = draft.read_bytes()
        self.cli('render', '--style', 'evidence', '--replace-in', str(draft))
        self.assertEqual(draft.read_bytes(), once)
        self.cli('verify', str(draft), '--strict', '--evidence')

    def test_live_lock_is_not_stolen(self):
        # Use the same helper's bounded lock directly so the test need not sleep.
        import importlib.util
        spec = importlib.util.spec_from_file_location('citation_lock_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.ledger.parent.mkdir()
        lock = self.ledger.with_suffix('.json.lock')
        lock.write_text('another writer')
        with self.assertRaises(SystemExit):
            with module._LedgerLock(self.ledger, timeout=0):
                self.fail('acquired an already held lock')
        self.assertEqual(lock.read_text(), 'another writer')


if __name__ == '__main__':
    unittest.main()
