#!/usr/bin/env python3
"""Prepare and check a reviewer's checkout for SDLC PR review.

Subcommands write a host execution profile into a review checkout, build or verify a
hashed evidence bundle, report runtime versions in the environment that runs the
command, check the checkout's integrity after the review and remove the profile.
Results are JSON on stdout. Exit codes: 0 passed, 1 failed check, 2 usage error.
Python 3.11+, stdlib only. It launches no reviewer and changes no account settings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

RECORD = Path('reports/review-workspace.json')
MANIFEST = 'MANIFEST.json'
HEADER = '# Written by the SDLC review_workspace.py helper for a review-only checkout. Remove after the review.\n'
PROFILES = {
    # Workspace-write sandbox with local socket binding and no outbound network: the proxy
    # has no allowed domains. Codex loads it only in a trusted project.
    'codex': ('.codex/config.toml', HEADER + '[sandbox_workspace_write]\nnetwork_access = true\n\n'
              '[features.network_proxy]\nenabled = true\nallow_local_binding = true\n'),
    # Deny rules hold under auto-approve. Grok loads project rules only in a trusted repository.
    'grok': ('.grok/config.toml', HEADER + '[permission]\ndeny = [\n' + ''.join(f'  "{rule}",\n' for rule in (
        'Bash(git push*)', 'Bash(git commit*)', 'Bash(git reset*)', 'Bash(git checkout*)', 'Bash(git switch*)',
        'Bash(git stash*)', 'Bash(git rebase*)', 'Bash(git merge*)', 'Bash(git tag*)', 'Bash(gh *)',
        'Bash(rm *)', 'Bash(sudo *)', 'Bash(curl *)', 'Bash(wget *)', 'Edit', 'Write')) + ']\n'),
}
TOOLS = {
    'node': (['node', '--version'], r'v?(\d+)\.(\d+)\.(\d+)'),
    'java': (['java', '-version'], r'version "(?:1\.)?(\d+)(?:\.(\d+))?(?:\.(\d+))?'),
    'python3.11': (['python3.11', '--version'], r'Python (\d+)\.(\d+)\.(\d+)'),
    'bun': (['bun', '--version'], r'(\d+)\.(\d+)\.(\d+)'),
    'deno': (['deno', '--version'], r'deno (\d+)\.(\d+)\.(\d+)'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def emit(result):
    print(json.dumps(result, indent=2))
    return 0 if result.get('ok') else 1


def git(checkout, *args):
    proc = subprocess.run(['git', '-C', str(checkout), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def load_record(checkout):
    path = Path(checkout) / RECORD
    return json.loads(path.read_text()) if path.is_file() else {'placed': {}, 'bundles': []}


def save_record(checkout, record):
    path = Path(checkout) / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + '\n')


def collisions(names):
    seen, clashes = {}, []
    for name in names:
        key = name.lower()
        if key in seen and seen[key] != name:
            clashes.append([seen[key], name])
        seen.setdefault(key, name)
    return clashes


def bundle(args):
    """Copy evidence files into reports/<name>/ beside a MANIFEST of their digests."""
    pairs = []
    for item in args.file:
        dest, _, src = item.partition('=')
        if not src or Path(dest).is_absolute() or '..' in Path(dest).parts or not Path(src).is_file():
            return emit({'ok': False, 'error': f'expected DEST=SRC with a relative DEST and an existing SRC: {item}'})
        pairs.append((Path(dest).as_posix(), Path(src)))
    names = [dest for dest, _ in pairs]
    clashes = collisions(names + [MANIFEST]) + [[n, n] for n in names if names.count(n) > 1 or n == MANIFEST]
    if clashes:
        return emit({'ok': False, 'error': 'names collide on a case-insensitive file system', 'collisions': clashes})
    target = Path(args.checkout) / 'reports' / args.name
    if target.exists():
        return emit({'ok': False, 'error': f'{target} exists; use a new bundle name'})
    for dest, src in pairs:
        (target / dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target / dest)
    files = {dest: sha(target / dest) for dest in sorted(names)}
    (target / MANIFEST).write_text(json.dumps({'files': files}, indent=2) + '\n')
    record = load_record(args.checkout)
    record['bundles'] = sorted(set(record['bundles']) | {args.name})
    save_record(args.checkout, record)
    return emit({'ok': True, 'bundle': str(target), 'files': len(files), 'manifest_sha256': sha(target / MANIFEST)})


def check_bundle(folder):
    folder = Path(folder)
    if not (folder / MANIFEST).is_file():
        return [f'{folder}: no {MANIFEST}']
    recorded = json.loads((folder / MANIFEST).read_text())['files']
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name != MANIFEST}
    problems = [f'missing {name}' for name in sorted(set(recorded) - actual)]
    problems += [f'unrecorded {name}' for name in sorted(actual - set(recorded))]
    problems += [f'changed {name}' for name in sorted(set(recorded) & actual) if sha(folder / name) != recorded[name]]
    problems += [f'case collision {a} / {b}' for a, b in collisions(sorted(recorded) + [MANIFEST])]
    return problems


def verify_bundle(args):
    problems = check_bundle(args.bundle)
    return emit({'ok': not problems, 'bundle': args.bundle, 'problems': problems})


def profile(args):
    """Write the host's review profile into the checkout and record its digest."""
    relative, content = PROFILES[args.host]
    path = Path(args.checkout) / relative
    if path.exists() and path.read_text() != content:
        return emit({'ok': False, 'error': f'{relative} already exists with other content; review and remove it first'})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    record = load_record(args.checkout)
    record['placed'][relative] = sha(path)
    save_record(args.checkout, record)
    result = {'ok': True, 'host': args.host, 'placed': relative, 'sha256': record['placed'][relative]}
    if args.host == 'grok' and args.check_grok:
        proc = subprocess.run(['grok', 'inspect', '--json'], cwd=args.checkout, capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return emit({**result, 'ok': False, 'error': 'grok inspect --json returned no JSON'})
        result['grok'] = {'projectTrusted': data.get('projectTrusted'), 'rules_loaded': data.get('permissions', {}).get('loaded')}
        if not data.get('projectTrusted') or not data.get('permissions', {}).get('loaded'):
            result.update(ok=False, error='Grok ignores project rules here: the repository is not trusted. '
                          'Trusting it is the user\'s decision (run `grok --trust` in the checkout).')
    return emit(result)


def version_of(name):
    command, pattern = TOOLS[name]
    path = shutil.which(command[0])
    if not path:
        return {'path': None, 'version': None}
    proc = subprocess.run(command, capture_output=True, text=True)
    match = re.search(pattern, proc.stdout + proc.stderr)
    parts = [int(part) for part in match.groups() if part is not None] if match else None
    return {'path': path, 'version': '.'.join(map(str, parts)) if parts else None, 'parts': parts}


def runtimes(args):
    """Report tool versions as resolved in the environment that runs this command."""
    report, ok = {}, True
    wanted = dict(item.split('=', 1) for item in args.min) if args.min else {}
    for name in args.tool or sorted(TOOLS):
        if name not in TOOLS:
            return emit({'ok': False, 'error': f'unknown tool {name}; known: {sorted(TOOLS)}'})
        found = version_of(name)
        if name in wanted:
            need = [int(part) for part in wanted[name].split('.')]
            found['minimum'] = wanted[name]
            found['meets_minimum'] = bool(found['parts']) and found['parts'][:len(need)] >= need
            ok = ok and found['meets_minimum']
        found.pop('parts', None)
        report[name] = found
    return emit({'ok': ok, 'tools': report})


def integrity(args):
    """After the review: same HEAD, no tracked or untracked change but the recorded profile."""
    record = load_record(args.checkout)
    problems = []
    code, head = git(args.checkout, 'rev-parse', 'HEAD')
    if code or head.strip() != args.head:
        problems.append(f'HEAD is {head.strip() or "unreadable"}, expected {args.head}')
    # Files this helper wrote are expected even where the repository does not ignore reports/.
    expected = set(record['placed']) | {RECORD.as_posix()}
    bundles = tuple(f'reports/{name}/' for name in record['bundles'])
    code, status = git(args.checkout, 'status', '--porcelain', '--untracked-files=all')
    if code:
        problems.append('git status failed')
    for line in status.splitlines():
        path = line[3:]
        if not (line.startswith('?? ') and (path in expected or path.startswith(bundles))):
            problems.append(f'unexpected change: {line}')
    for relative, digest in record['placed'].items():
        path = Path(args.checkout) / relative
        if not path.is_file() or sha(path) != digest:
            problems.append(f'placed profile changed or missing: {relative}')
    for name in record['bundles']:
        problems += [f'bundle {name}: {problem}' for problem in check_bundle(Path(args.checkout) / 'reports' / name)]
    return emit({'ok': not problems, 'checkout': args.checkout, 'head': args.head, 'problems': problems})


def remove(args):
    record = load_record(args.checkout)
    problems, removed = [], []
    for relative, digest in list(record['placed'].items()):
        path = Path(args.checkout) / relative
        if path.is_file() and sha(path) != digest:
            problems.append(f'{relative} changed since it was placed; left in place for inspection')
            continue
        if path.is_file():
            path.unlink()
            if not any(path.parent.iterdir()):
                path.parent.rmdir()
        removed.append(relative)
        del record['placed'][relative]
    save_record(args.checkout, record)
    return emit({'ok': not problems, 'removed': removed, 'problems': problems})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('bundle', help='copy evidence into reports/<name>/ with a MANIFEST')
    b.add_argument('--checkout', required=True)
    b.add_argument('--name', required=True)
    b.add_argument('--file', action='append', required=True, metavar='DEST=SRC')
    v = sub.add_parser('verify-bundle', help='check a bundle against its MANIFEST')
    v.add_argument('bundle')
    p = sub.add_parser('profile', help="write the host's review execution profile")
    p.add_argument('--checkout', required=True)
    p.add_argument('--host', required=True, choices=sorted(PROFILES))
    p.add_argument('--check-grok', action='store_true', help='require grok inspect to show trusted, loaded rules')
    r = sub.add_parser('runtimes', help='report tool versions in this environment')
    r.add_argument('--tool', action='append', help=f'one of {sorted(TOOLS)}; repeatable')
    r.add_argument('--min', action='append', metavar='TOOL=VERSION', help='for example node=22.18')
    i = sub.add_parser('integrity', help='check the checkout after the review')
    i.add_argument('--checkout', required=True)
    i.add_argument('--head', required=True)
    x = sub.add_parser('remove', help='remove placed profiles that are unchanged')
    x.add_argument('--checkout', required=True)
    args = parser.parse_args(argv)
    return {'bundle': bundle, 'verify-bundle': verify_bundle, 'profile': profile, 'runtimes': runtimes,
            'integrity': integrity, 'remove': remove}[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
