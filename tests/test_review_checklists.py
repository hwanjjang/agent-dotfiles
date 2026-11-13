"""Run the commands and code that the bundled review checklists tell a reviewer to use."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "code-review-and-quality" / "references"
SECURITY = REFERENCES / "security-checklist.md"
PERFORMANCE = REFERENCES / "performance-checklist.md"
SYNTHETIC_VALUE = "synthetic-value-7f3a-not-a-credential"


def staged_secret_command() -> str:
    for line in SECURITY.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [ ] No secrets in code"):
            match = re.search(r"`(git diff --cached[^`]*)`", line)
            if match:
                return match.group(1)
    raise AssertionError("the security checklist has no staged-secret command")


def web_vitals_snippet() -> str:
    text = PERFORMANCE.read_text(encoding="utf-8")
    for block in re.findall(r"```javascript\n(.*?)```", text, flags=re.S):
        if "web-vitals/attribution" in block:
            return block
    raise AssertionError("the performance checklist has no web-vitals attribution snippet")


class StagedSecretScan(unittest.TestCase):
    def run_scan(self, name: str, content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as repo:
            env = {
                "PATH": os.environ["PATH"],
                "HOME": home,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }
            subprocess.run(["git", "init", "-q", repo], check=True, env=env)
            Path(repo, name).write_text(content, encoding="utf-8")
            subprocess.run(["git", "-C", repo, "add", name], check=True, env=env)
            return subprocess.run(
                ["sh", "-c", staged_secret_command()],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_staged_match_names_the_file_without_printing_the_value(self) -> None:
        result = self.run_scan("settings.py", f'API_KEY = "{SYNTHETIC_VALUE}"\n')
        output = result.stdout + result.stderr
        self.assertNotIn(SYNTHETIC_VALUE, output)
        self.assertIn("settings.py", result.stdout)

    def test_staged_change_without_a_match_prints_nothing(self) -> None:
        result = self.run_scan("notes.txt", "release notes\n")
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.returncode, 0, result.stderr)


class PerformanceExamples(unittest.TestCase):
    def test_lighthouse_example_targets_plain_http_on_localhost(self) -> None:
        text = PERFORMANCE.read_text(encoding="utf-8")
        self.assertIn("npx lighthouse http://localhost:3000", text)
        self.assertNotIn("https://localhost", text)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_web_vitals_snippet_parses_as_one_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory, "snippet.mjs")
            module.write_text(web_vitals_snippet(), encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(module)], capture_output=True, text=True, check=False
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
