"""Exercise selected account routes without touching real account settings."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "account/hooks"
spec = importlib.util.spec_from_file_location("planning_hook", SOURCE / "planning-hook.py")
dispatcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatcher)


class AccountHooksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="account hook test ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.delivery = self.base / "delivered account"
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.entry = self.delivery / ".agents/bin/planning-hook.py"
        self.entry.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE / "planning-hook.py", self.entry)
        runtime = SOURCE / "planning-with-files"
        shutil.copytree(runtime / "codex", self.delivery / ".codex/hooks")
        target = self.delivery / ".claude/hooks/planning-with-files-dispatch.sh"
        target.parent.mkdir(parents=True)
        shutil.copyfile(runtime / "claude/dispatch.sh", target)
        skill = self.delivery / ".agents/skills/planning-with-files"
        shutil.copytree(ROOT / "skills/planning-with-files", skill)
        for client in [".codex", ".claude"]:
            link = self.delivery / client / "skills/planning-with-files"
            link.parent.mkdir(parents=True)
            link.symlink_to(skill, target_is_directory=True)
        # Preserve HOME. Redirect caches and clear ambient task selectors only.
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("PWF_") and k not in {"PLAN_ID", "PLANNING_DISABLED", "CLAUDE_PLUGIN_ROOT"}}
        self.env.update(XDG_CACHE_HOME=str(self.base / "cache"),
                        PYTHON_BIN=sys.executable, PYTHONDONTWRITEBYTECODE="1")

    def run_hook(self, host, *args, raw=None, **env):
        payload = json.dumps({"cwd": str(self.project), "session_id": "synthetic"}) if raw is None else raw
        return subprocess.run([sys.executable, str(self.entry), host, *args],
                              cwd=self.base, env=dict(self.env, **env), input=payload,
                              text=True, capture_output=True, timeout=15)

    def plan(self, name, marker):
        path = self.project / ".planning" / name
        path.mkdir(parents=True)
        (path / "task_plan.md").write_text(f"# {marker}\n\n## Goal\n{marker}\n\n## Phase 1\n**Status:** in_progress\n")
        (path / "progress.md").write_text("Synthetic work has started.\n")
        (path / "findings.md").write_text("Synthetic finding.\n")

    def test_pinned_runtime_hashes_and_dependency_closure(self):
        runtime = SOURCE / "planning-with-files"
        records = json.loads((runtime / "provenance.json").read_text())["files"]
        actual = {str(p.relative_to(runtime)) for p in runtime.rglob("*") if p.is_file()}
        self.assertEqual(actual, set(records) | {"provenance.json"})
        for name, record in records.items():
            self.assertEqual(hashlib.sha256((runtime / name).read_bytes()).hexdigest(), record["sha256"], name)

    def test_every_template_route_is_allowed(self):
        for client in ["codex", "claude"]:
            config = json.loads((SOURCE / f"{client}.example.json").read_text())
            for event, groups in config["hooks"].items():
                for group in groups:
                    for hook in group["hooks"]:
                        route = tuple(hook["command"].split(f'" {client} ')[1].split())
                        if client == "codex":
                            self.assertEqual(dispatcher.EVENTS[route], event)
                        else:
                            self.assertEqual(route, ("session-start",))

    def test_all_routes_without_a_plan_complete(self):
        for route in sorted(dispatcher.CODEX_ROUTES):
            result = self.run_hook("codex", *route)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("unavailable", result.stderr.lower())
        result = self.run_hook("claude", "session-start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / ".planning").exists())

    def test_selected_plan_recovers_in_both_clients_with_space_paths(self):
        self.plan("chosen", "SELECTED_SYNTHETIC_PLAN")
        self.plan("other", "UNRELATED_SYNTHETIC_PLAN")
        for host, route in [("codex", ("run_sh.py", "user-prompt-submit.sh")),
                            ("claude", ("session-start",))]:
            result = self.run_hook(host, *route, PLAN_ID="chosen")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SELECTED_SYNTHETIC_PLAN", result.stdout, result.stderr)
            self.assertNotIn("UNRELATED_SYNTHETIC_PLAN", result.stdout)

    def test_broken_explicit_plan_never_recovers_another(self):
        self.plan("other", "UNRELATED_SYNTHETIC_PLAN")
        for host, route in [("codex", ("run_sh.py", "user-prompt-submit.sh")),
                            ("claude", ("session-start",))]:
            result = self.run_hook(host, *route, PLAN_ID="absent")
            self.assertNotIn("UNRELATED_SYNTHETIC_PLAN", result.stdout)

    def test_opt_out_is_silent(self):
        self.plan("chosen", "SELECTED_SYNTHETIC_PLAN")
        for host, route in [("codex", ("run_sh.py", "session-start.sh")),
                            ("claude", ("session-start",))]:
            result = self.run_hook(host, *route, PLANNING_DISABLED="1")
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_project_route_precedence_is_event_scoped(self):
        self.plan("chosen", "SELECTED_SYNTHETIC_PLAN")
        folder = self.project / ".codex/hooks"
        folder.mkdir(parents=True)
        (folder / "run_sh.py").write_text("# Project owns SessionStart\n")
        config = {"hooks": {"SessionStart": [{"hooks": [{"command": "python3 .codex/hooks/run_sh.py session-start.sh"}]}]}}
        (folder.parent / "hooks.json").write_text(json.dumps(config))
        self.assertEqual(self.run_hook("codex", "run_sh.py", "session-start.sh", PLAN_ID="chosen").stdout, "")
        result = self.run_hook("codex", "run_sh.py", "user-prompt-submit.sh", PLAN_ID="chosen")
        self.assertIn("SELECTED_SYNTHETIC_PLAN", result.stdout)
        folder = self.project / ".claude"
        folder.mkdir()
        config = {"hooks": {"SessionStart": [{"hooks": [{"command": "sh .claude/hooks/planning-with-files.sh session-start"}]}]}}
        (folder / "settings.json").write_text(json.dumps(config))
        self.assertEqual(self.run_hook("claude", "session-start", PLAN_ID="chosen").stdout, "")

    def test_invalid_routes_and_payloads_do_not_launch(self):
        for host, args, raw in [("codex", ("run_sh.py", "../../unexpected.sh"), "{}"),
                                ("claude", ("session-start",), "[]"),
                                ("codex", ("stop.py",), "broken JSON")]:
            result = self.run_hook(host, *args, raw=raw)
            self.assertEqual(result.stdout, "")
            self.assertIn("Planning hook unavailable:", result.stderr)


if __name__ == "__main__":
    unittest.main()
