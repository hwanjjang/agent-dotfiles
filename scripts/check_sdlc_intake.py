#!/usr/bin/env python3
"""Prepare/run bounded native SDLC scenarios; leave semantic grading to review.

No account installation, tracker writes, automatic retries or automatic PASS.
Run evidence contains private host paths and must remain outside public Git.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'tests/fixtures/sdlc-intake/cases.json'
HARNESS_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
BASE = 'def select_tasks(tasks, status=None):\n    return list(tasks)\n'
CORRECT = ('def select_tasks(tasks, status=None):\n'
           '    return [task for task in tasks if status is None or task.get("status") == status]\n')
SPEC = '''# Status filter (approved)
AC1: select_tasks(tasks, status=None) returns a new list containing all input
records in input order. AC2: a supplied status selects exact case-sensitive
matches of the status field, preserving order; missing fields do not match.
AC3: empty input or no matches returns []; inputs are not mutated.
No sorting, CLI, normalization, validation vocabulary, persistence or network.
All product decisions are settled. Finish locally with executed checks.
'''
PLAN = '''# Approved implementation plan
One slice / one prospective PR: status selection and its behavior checks.
AC1-3: preserve default behavior, add exact status filtering, retain ordering,
missing-field and empty/no-match behavior, and input immutability.
Modify taskboard.py; extend test_taskboard.py first with failing behavior tests;
run python3 -m unittest -v. Independently exercise a mixed list in a small smoke
script using the actual function. No external dependency or prior task blocks it.
Keep the existing public function signature. No new infrastructure or tickets.
'''
TEST = '''import unittest
from taskboard import select_tasks

class ExistingTests(unittest.TestCase):
    def test_default(self):
        tasks = [{"id": 1, "status": "open"}]
        self.assertEqual(select_tasks(tasks), tasks)
        self.assertIsNot(select_tasks(tasks), tasks)

if __name__ == '__main__':
    unittest.main()
'''


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()
            and not any(x in p.relative_to(root).parts for x in ('.git', '__pycache__'))}


def git(project, *args):
    return subprocess.check_output(['git', '-C', str(project), *args], text=True).strip()


def outside_write_attempts(events, project):
    """Report native file-tool attempts; shell effects still require trace review."""
    attempts = []
    for event in events:
        if event.get('type') != 'assistant':
            continue
        for item in event.get('message', {}).get('content', []):
            if item.get('type') != 'tool_use' or item.get('name') not in ('Write', 'Edit'):
                continue
            name = item.get('input', {}).get('file_path')
            if not isinstance(name, str):
                continue
            target = Path(name)
            if not target.is_absolute():
                target = project / target
            if not target.resolve().is_relative_to(project.resolve()):
                attempts.append({'tool': item['name'], 'path': name, 'tool_use_id': item.get('id')})
    return attempts


def prepare(destination, source, selected):
    destination.mkdir(parents=True, exist_ok=False)
    bundle = destination / 'bundle'
    for name in ('skills', 'policies'):
        shutil.copytree(source / name, bundle / name, ignore=shutil.ignore_patterns('__pycache__'))
    manifest = {'source_revision': git(source, 'rev-parse', 'HEAD'),
                'source_hashes': hashes(bundle), 'cases_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
                'cases': selected, 'qualification': 'prepared; no behavior claim'}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    cases = {c['id']: c for c in json.loads(CASES.read_text())['cases']}
    for name in selected:
        case = cases[name]
        project = destination / name / 'project'
        project.mkdir(parents=True)
        (project / '.claude').mkdir()
        (project / '.claude/skills').symlink_to(bundle / 'skills', target_is_directory=True)
        files = {'taskboard.py': BASE, 'test_taskboard.py': TEST,
                 '.gitignore': '.claude/\n__pycache__/\n',
                 'CLAUDE.md': '# Taskboard\nLocal Python library. Run python3 -m unittest -v. '
                 'Canonical spec/plan are docs/spec.md and docs/plan.md when present. '
                 'Use project skills; limit reads to this project and its skill/policy sources. '
                 'Write only within this project (including scratch checks); never edit skill sources, account settings or external resources. '
                 'No commits, publication, delegation or network actions.\n'}
        if case.get('settled'):
            files.update({'docs/spec.md': SPEC, 'docs/plan.md': PLAN,
                          'issue.md': '# Exact status filter\nImplement the approved docs/spec.md using docs/plan.md.\n'})
        files.update(case.get('files', {}))
        for path, content in files.items():
            target = project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        git(project, 'init', '-q')
        git(project, 'add', '.')
        git(project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Synthetic baseline')
        base = git(project, 'rev-parse', 'HEAD')
        if case.get('implementation'):
            code = CORRECT if case['implementation'] == 'correct' else CORRECT.replace('get("status")', 'get("state")')
            (project / 'taskboard.py').write_text(code)
            git(project, 'add', 'taskboard.py')
            git(project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Synthetic candidate')
        if name in ('review', 'correction'):
            (project / 'pr.md').write_text(f'# Local PR snapshot\nBase: {base}\nHead: {git(project, "rev-parse", "HEAD")}\n'
                'Requirements: docs/spec.md. No remote PR exists.\n' +
                ('R1: status filtering does not select records whose status matches. Correct and verify.\n' if name == 'correction' else 'Review the candidate against requirements.\n'))
        (project.parent / 'prompt.txt').write_text(case['request'])
        # Expectations are retained outside the project and never added to the prompt.
        (project.parent / 'expectations.json').write_text(json.dumps(case['expectations'], indent=2) + '\n')
        (project.parent / 'before.json').write_text(json.dumps(hashes(project), indent=2) + '\n')


def run(destination, case, model, timeout):
    folder = destination / case
    project = folder / 'project'
    if not project.is_dir() or (folder / 'native.jsonl').exists():
        raise ValueError('Prepare the case first; never overwrite or retry an existing run.')
    readonly = case in ('review', 'standalone')
    tools = 'Read,Glob,Grep,Skill,Bash' + ('' if readonly else ',Edit,Write')
    allowed = ['Read', 'Glob', 'Grep', 'Skill', 'Bash(python3 -m unittest*)',
               'Bash(python3 -c*)', 'Bash(python3 -I*)',
               'Bash(python3 smoke*)', 'Bash(git diff*)', 'Bash(git status*)',
               'Bash(git log*)', 'Bash(git show*)'] + ([] if readonly else ['Edit', 'Write'])
    command = ['claude', '--print', '--model', model, '--effort', 'medium',
               '--output-format', 'stream-json', '--verbose', '--no-session-persistence',
               '--tools', tools, '--allowedTools', ','.join(allowed), '--permission-mode', 'manual',
               '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
               '--setting-sources', 'project', '--settings', '{"disableAllHooks":true}',
               '--max-turns', '40', '--max-budget-usd', '2', (folder / 'prompt.txt').read_text()]
    env = {k: v for k, v in os.environ.items() if not k.startswith('PWF_')
           and k not in ('PLAN_ID', 'CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_PLUGIN_ROOT')}
    env.update(PLANNING_DISABLED='1', PYTHONDONTWRITEBYTECODE='1')
    (folder / 'launch.json').write_text(json.dumps(
        {'command': command, 'harness_sha256': HARNESS_SHA256,
         'requested_model': model, 'effort': 'medium', 'timeout_seconds': timeout}, indent=2) + '\n')
    start = time.monotonic()
    with (folder / 'native.jsonl').open('w') as out, (folder / 'stderr.txt').open('w') as err:
        try:
            result = subprocess.run(command, cwd=project, env=env, stdout=out, stderr=err, timeout=timeout)
            status = {'exit_code': result.returncode}
        except subprocess.TimeoutExpired:
            status = {'timeout': True}
    events = []
    for line in (folder / 'native.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    results = [e for e in events if e.get('type') == 'result']
    (folder / 'answer.md').write_text(results[-1].get('result', '') if results else '')
    manifest = json.loads((destination / 'manifest.json').read_text())
    status.update(elapsed_seconds=round(time.monotonic() - start, 2), requested_model=model,
                  harness_sha256=HARNESS_SHA256,
                  client_version=subprocess.check_output(['claude', '--version'], text=True).strip(),
                  source_unchanged=hashes(destination / 'bundle') == manifest['source_hashes'],
                  outside_project_write_attempts=outside_write_attempts(events, project),
                  project_after=hashes(project), result=results[-1] if results else None,
                  qualification='ungraded; inspect tool evidence and artifacts against expectations')
    (folder / 'execution.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'case': case, 'elapsed_seconds': status['elapsed_seconds'],
                      'exit_code': status.get('exit_code'), 'source_unchanged': status['source_unchanged'],
                      'result_type': results[-1].get('subtype') if results else None}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('destination', type=Path, help='New private directory, outside Git or in .local/.planning/reports')
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--cases', nargs='+', choices=[c['id'] for c in json.loads(CASES.read_text())['cases']],
                        default=[c['id'] for c in json.loads(CASES.read_text())['cases']])
    parser.add_argument('--model', help='Explicit native Claude model; run consumes provider quota')
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    dest = args.destination.absolute()
    if any(p.is_symlink() for p in (dest, *dest.parents)):
        parser.error('Evidence destination must not contain symlinks.')
    dest = dest.resolve()
    if dest.is_relative_to(ROOT) and dest.relative_to(ROOT).parts[:1] not in [('.local',), ('.planning',), ('reports',)]:
        parser.error('Raw native evidence must stay outside tracked source.')
    if args.action == 'prepare':
        prepare(dest, args.source.resolve(), args.cases)
    else:
        if not args.model:
            parser.error('run requires --model and an authorized native execution')
        for case in args.cases:
            run(dest, case, args.model, args.timeout)


if __name__ == '__main__':
    main()
