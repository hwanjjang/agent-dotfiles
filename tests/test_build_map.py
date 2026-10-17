"""Behavior checks for public map generation and catalog drift detection."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("build_map", Path(__file__).resolve().parents[1] / "scripts/build_map.py")
build_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_map)


class MapBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "README.md").write_text("# Example\n")
        self.catalog = {
            "schema_version": 1, "title": "Example map", "description": "Public example.",
            "groups": [{"id": "start", "title": "Start", "description": "Read the source."}],
            "entries": [{"id": "overview", "title": "Overview", "kind": "guide", "group": "start",
                         "status": "available", "source": "README.md", "summary": "Overview.",
                         "when": ["Getting started."], "usage": "Read README.md.",
                         "behavior": ["Explains the scope."], "outputs": ["Context."], "tags": ["readme"]}],
            "relationships": []}

    def test_html_in_metadata_stays_data(self):
        self.catalog["entries"][0]["title"] = "</script><b>Example</b>"
        output = build_map.render(self.catalog, build_map.MARKER, self.root)
        self.assertEqual(output.count("</script>"), 1)
        self.assertIn(r"\u003c/script\u003e", output)
        self.assertNotIn("<b>Example</b>", output)

    def test_local_or_escaping_sources_are_rejected(self):
        for path in ("../private.md", ".local/notes.md", "/private/notes.md"):
            with self.subTest(path=path):
                self.catalog["entries"][0]["source"] = path
                with self.assertRaises(ValueError):
                    build_map.validate(self.catalog, self.root)

    def test_credential_bearing_reference_is_rejected(self):
        entry = self.catalog["entries"][0]
        del entry["source"]
        entry.update(kind="reference", status="reference", url="https://example-user:example-password@example.com/map")
        with self.assertRaisesRegex(ValueError, "credentials"):
            build_map.validate(self.catalog, self.root)

    def test_new_skill_cannot_silently_disappear_from_map(self):
        skill = self.root / "skills/example/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: example\ndescription: Synthetic example.\n---\n")
        with self.assertRaisesRegex(ValueError, "unmapped reusable content: skills/example/SKILL.md"):
            build_map.validate(self.catalog, self.root)

    def test_check_rejects_stale_generated_html(self):
        directory = self.root / "docs/map"
        directory.mkdir(parents=True)
        catalog_path = directory / "catalog.json"
        catalog_path.write_text(json.dumps(self.catalog))
        (directory / "viewer.template.html").write_text("<html>" + build_map.MARKER + "</html>\n")
        with patch.object(build_map, "ROOT", self.root):
            with patch("sys.argv", ["build_map.py"]):
                self.assertEqual(build_map.main(), 0)
            with patch("sys.argv", ["build_map.py", "--check"]):
                self.assertEqual(build_map.main(), 0)
            self.catalog["entries"][0]["summary"] = "Changed behavior."
            catalog_path.write_text(json.dumps(self.catalog))
            before = {p: p.read_bytes() for p in directory.iterdir()}
            with patch("sys.argv", ["build_map.py", "--check"]):
                self.assertEqual(build_map.main(), 1)
            self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, before)

    def test_check_rejects_missing_output_without_creating_it(self):
        directory = self.root / "docs/map"
        directory.mkdir(parents=True)
        (directory / "catalog.json").write_text(json.dumps(self.catalog))
        (directory / "viewer.template.html").write_text(build_map.MARKER)
        before = {p: p.read_bytes() for p in directory.iterdir()}
        with patch.object(build_map, "ROOT", self.root):
            with patch("sys.argv", ["build_map.py", "--check"]):
                self.assertEqual(build_map.main(), 1)
        self.assertFalse((directory / "index.html").exists())
        self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
