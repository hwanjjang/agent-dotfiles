#!/usr/bin/env python3
"""Prepare and check a reviewer's checkout for SDLC PR review.

Subcommands write a host execution profile into a review checkout, build or verify a
hashed evidence bundle, report runtime versions in the environment that runs the
command, check the checkout after the review and remove the profiles. The coordinator
keeps one preparation record per checkout outside that checkout, with the digest of every
file in the checkout read from disk; integrity and removal trust only that record and the
helper's own profile paths, and every command validates the record before it writes. The
integrity check finds drift by a reviewer that cannot write outside its checkout; it is
no boundary against a reviewer with full access. Results are JSON on stdout. Exit codes:
0 passed, 1 failed check, 2 usage error. Python 3.11+, stdlib only. It launches no
reviewer and changes no account settings.
"""
import argparse
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata

MANIFEST = 'MANIFEST.json'
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
# Read-only git queries; the checkout's fsmonitor program and hooks must not run.
GIT = ['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null']
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
PROFILE_PATHS = {relative for relative, _ in PROFILES.values()}
TOOLS = {
    'node': (['node', '--version'], r'v?(\d+)\.(\d+)\.(\d+)'),
    'java': (['java', '-version'], r'version "(?:1\.)?(\d+)(?:\.(\d+))?(?:\.(\d+))?'),
    'python3.11': (['python3.11', '--version'], r'Python (\d+)\.(\d+)\.(\d+)'),
    'bun': (['bun', '--version'], r'(\d+)\.(\d+)\.(\d+)'),
    'deno': (['deno', '--version'], r'deno (\d+)\.(\d+)\.(\d+)'),
}


class Usage(Exception):
    """A rejected argument, reported with exit code 2."""


class Unsafe(Exception):
    """A path that is not plain or passes through a symbolic link."""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def emit(result, code=None):
    print(json.dumps(result, indent=2))
    return (0 if result.get('ok') else 1) if code is None else code


def plain(relative):
    return all(part not in ('', '.', '..') for part in relative.split('/'))


def digest_map(value):
    """Whether value maps plain relative paths to SHA-256 digests."""
    return isinstance(value, dict) and all(
        isinstance(path, str) and plain(path) and isinstance(digest, str) and SHA256.match(digest) for path, digest in value.items())


def well_formed(data, root):
    return (isinstance(data, dict) and data.get('schema_version') == 1 and data.get('checkout') == str(root)
            and digest_map(data.get('placed')) and isinstance(data.get('bundles'), dict)
            and all(isinstance(name, str) and NAME.match(name) and isinstance(entry, dict)
                    and isinstance(entry.get('manifest_sha256'), str) and SHA256.match(entry['manifest_sha256'])
                    and digest_map(entry.get('files')) for name, entry in data['bundles'].items())
            and isinstance(data.get('files'), dict)
            and all(isinstance(path, str) and plain(path) and isinstance(digest, str) for path, digest in data['files'].items())
            and isinstance(data.get('git_link'), str))


def inside(root, relative):
    """Join a plain relative path to the checkout root, refusing symbolic links on the way."""
    if not plain(relative):
        raise Unsafe(f'{relative} is not a plain relative path')
    path = root
    for part in relative.split('/'):
        path = path / part
        if path.is_symlink():
            raise Unsafe(f'{path} is a symbolic link')
    return path


def rev_parse(root, what):
    proc = subprocess.run([*GIT, '-C', str(root), 'rev-parse', what], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ''


def checkout_root(value):
    """The checkout's top directory; git reports paths relative to it."""
    root = Path(value).resolve()
    top = rev_parse(root, '--show-toplevel')
    if not top or Path(top).resolve() != root:
        raise Usage(f'{value} is not the top directory of a git checkout')
    return root


class Record:
    """The coordinator's preparation record for one checkout, kept outside that checkout."""

    def __init__(self, path, root, create=False, expect=None):
        self.path = Path(path).resolve()
        if self.path == root or root in self.path.parents:
            raise Usage('keep the record outside the reviewer checkout')
        if self.path.is_file():
            self.data = json.loads(self.path.read_text())
        elif create:
            self.data = {'schema_version': 1, 'checkout': str(root), 'placed': {}, 'bundles': {}, 'files': {}, 'git_link': 'absent'}
        else:
            raise Usage(f'no record at {path}')
        if expect and sha(self.path) != expect:
            raise Unsafe('the record changed since preparation')
        if not well_formed(self.data, root):
            raise Usage(f'{path} is not a well-formed record (schema 1) for {root}')

    def placed_here(self, path):
        """Whether the helper placed this checkout path: a profile or a file in a bundle."""
        return path in self.data['placed'] or path.startswith(tuple(f'reports/{name}/' for name in self.data['bundles']))

    def unplaced(self, root):
        """Digests of the checkout's files other than those the helper placed."""
        return {path: digest for path, digest in snapshot(root).items() if not self.placed_here(path)}

    def save(self, root=None):
        """Write the record; with root, first snapshot the files the helper did not place and the .git entry."""
        if root is not None:
            self.data['files'], self.data['git_link'] = self.unplaced(root), git_link(root)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2) + '\n')
        return sha(self.path)


def snapshot(root):
    """Digest of every file and symbolic link under the checkout, read from disk; the top .git entry is skipped.

    Git's own view can be bent from inside the checkout (skip-worktree, assume-unchanged, clean
    filters), so file contents and executable bits are read directly. An unreadable folder fails
    the walk rather than hiding what it holds."""
    def fail(error):
        raise error

    digests = {}
    for directory, folders, files in os.walk(root, onerror=fail):
        here = Path(directory)
        if here == root:
            folders[:] = [name for name in folders if name != '.git']
            files = [name for name in files if name != '.git']
        for name in files + [folder for folder in folders if (here / folder).is_symlink()]:
            path = here / name
            if path.is_symlink():
                digest = 'link:' + os.readlink(path)
            elif path.is_file():
                digest = sha(path) + (' +x' if path.stat().st_mode & 0o111 else '')
            else:
                digest = 'special'
            digests[path.relative_to(root).as_posix()] = digest
    return digests


def git_link(root):
    """The checkout's .git entry: a worktree link file by digest, or the kind of entry."""
    path = root / '.git'
    if path.is_symlink():
        return 'link:' + os.readlink(path)
    return sha(path) if path.is_file() else 'directory' if path.is_dir() else 'absent'


def conflicts(names):
    """Name pairs that share a path ignoring case and Unicode normalization, or need a file and a folder at one path."""
    folded = [unicodedata.normalize('NFD', unicodedata.normalize('NFD', name).casefold()) for name in names]
    return [[names[i], names[j]] for i in range(len(names)) for j in range(i + 1, len(names))
            if folded[i] == folded[j] or folded[j].startswith(folded[i] + '/') or folded[i].startswith(folded[j] + '/')]


def bundle(args):
    """Copy evidence files into reports/<name>/ beside a MANIFEST and record their digests."""
    root = checkout_root(args.checkout)
    record = Record(args.record, root, create=True)
    if not NAME.match(args.name):
        raise Usage(f'use a plain bundle name such as review-bundle, not {args.name!r}')
    pairs = []
    for item in args.file:
        dest, _, src = item.partition('=')
        if not plain(dest) or not src or not Path(src).is_file():
            raise Usage(f'expected DEST=SRC with a plain relative DEST and an existing SRC file, not {item!r}')
        pairs.append((dest, Path(src)))
    names = [dest for dest, _ in pairs]
    clashes = conflicts(names + [MANIFEST])
    if clashes:
        return emit({'ok': False, 'collisions': clashes,
                     'error': 'names collide ignoring case or Unicode normalization, or need a file and a folder at one path'})
    target = inside(root, f'reports/{args.name}')
    if target.exists():
        return emit({'ok': False, 'error': f'{target} exists; use a new bundle name'})
    destinations = [(inside(root, f'reports/{args.name}/{dest}'), src) for dest, src in pairs]
    target.mkdir(parents=True)
    try:
        for path, src in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, path)
        files = {dest: sha(target / dest) for dest in sorted(names)}
        (target / MANIFEST).write_text(json.dumps({'files': files}, indent=2) + '\n')
    except OSError:
        shutil.rmtree(target)
        raise
    problems = check_bundle(target)
    if problems:
        shutil.rmtree(target)
        return emit({'ok': False, 'error': 'the written bundle does not verify on this file system', 'problems': problems})
    record.data['bundles'][args.name] = {'manifest_sha256': sha(target / MANIFEST), 'files': files}
    return emit({'ok': True, 'bundle': str(target), 'files': len(files), 'record_sha256': record.save(root)})


def check_bundle(folder, expected=None):
    """Compare a bundle with the coordinator's recorded digests, or else with its own MANIFEST."""
    folder = Path(folder)
    entries = {p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file() or p.is_symlink()}
    links = sorted(name for name, p in entries.items() if p.is_symlink())
    if links:
        return [f'symbolic link {name}' for name in links]
    if MANIFEST not in entries:
        return [f'no {MANIFEST}']
    problems = []
    if expected is None:
        try:
            recorded = json.loads(entries[MANIFEST].read_text())['files']
        except (ValueError, KeyError, TypeError):
            recorded = None
        if not digest_map(recorded):
            return [f'{MANIFEST} does not map file names to SHA-256 digests']
    else:
        recorded = expected['files']
        if sha(entries[MANIFEST]) != expected['manifest_sha256']:
            problems.append(f'{MANIFEST} changed')
    actual = set(entries) - {MANIFEST}
    problems += [f'missing {name}' for name in sorted(set(recorded) - actual)]
    problems += [f'unrecorded {name}' for name in sorted(actual - set(recorded))]
    problems += [f'changed {name}' for name in sorted(set(recorded) & actual) if sha(entries[name]) != recorded[name]]
    problems += [f'names collide: {a} / {b}' for a, b in conflicts(sorted(recorded) + [MANIFEST])]
    return problems


def verify_bundle(args):
    problems = check_bundle(args.bundle)
    return emit({'ok': not problems, 'bundle': args.bundle, 'problems': problems})


def profile(args):
    """Write the host's review profile into the checkout and record its digest."""
    root = checkout_root(args.checkout)
    record = Record(args.record, root, create=True)
    relative, content = PROFILES[args.host]
    path = inside(root, relative)
    if path.exists() and path.read_text() != content:
        return emit({'ok': False, 'error': f'{relative} already exists with other content; review and remove it first'})
    path.parent.mkdir(exist_ok=True)
    path.write_text(content)
    record.data['placed'][relative] = sha(path)
    result = {'ok': True, 'host': args.host, 'placed': relative, 'record_sha256': record.save(root)}
    if args.host == 'grok' and args.check_grok:
        proc = subprocess.run(['grok', 'inspect', '--json'], cwd=root, capture_output=True, text=True)
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
        return {'path': None, 'version': None, 'parts': None}
    proc = subprocess.run([path, *command[1:]], capture_output=True, text=True)
    match = re.search(pattern, proc.stdout + proc.stderr)
    parts = [int(part) for part in match.groups() if part is not None] if match else None
    return {'path': path, 'version': '.'.join(map(str, parts)) if parts else None, 'parts': parts}


def runtimes(args):
    """Report tool versions as resolved here; named tools must exist and meet any minimum."""
    minimums = {}
    for item in args.min or []:
        tool, _, version = item.partition('=')
        if not re.fullmatch(r'\d+(\.\d+)*', version):
            raise Usage(f'expected TOOL=VERSION such as node=22.18, not {item!r}')
        minimums[tool] = [int(part) for part in version.split('.')]
    named = list(dict.fromkeys((args.tool or []) + list(minimums)))
    unknown = sorted(set(named) - set(TOOLS))
    if unknown:
        raise Usage(f'unknown tools {unknown}; known: {sorted(TOOLS)}')
    report, ok = {}, True
    for name in named or sorted(TOOLS):
        found = version_of(name)
        parts = found.pop('parts')
        if name in minimums:
            want = minimums[name]
            found['minimum'] = '.'.join(map(str, want))
            found['meets_minimum'] = parts is not None and (parts + [0] * len(want))[:len(want)] >= want
        if name in named:
            ok = ok and found['path'] is not None and found.get('meets_minimum', True)
        report[name] = found
    return emit({'ok': ok, 'tools': report})


def integrity(args):
    """After the review: every file as recorded except the helper's own, then the same .git entry, top and HEAD.

    Everything is read from disk before git runs, and git runs only rev-parse, so no filter, hook or
    fsmonitor program from the checkout's configuration can run first and restore the files."""
    root = Path(args.checkout).resolve()
    record = Record(args.record, root, expect=args.expect_record_sha256)
    placed, bundles = record.data['placed'], record.data['bundles']
    before, now, link = record.data['files'], record.unplaced(root), git_link(root)
    allowed = lambda path: any(fnmatchcase(path, pattern) for pattern in args.allow or [])
    problems = [f'{"added" if path not in before else "removed" if path not in now else "changed"}: {path}'
                for path in sorted(before.keys() | now.keys()) if before.get(path) != now.get(path) and not allowed(path)]
    for relative, digest in placed.items():
        path = inside(root, relative)
        if not path.is_file() or sha(path) != digest:
            problems.append(f'placed file changed or missing: {relative}')
    for name, expected in bundles.items():
        problems += [f'bundle {name}: {problem}' for problem in check_bundle(inside(root, f'reports/{name}'), expected)]
    if link != record.data['git_link']:
        problems.append('the .git entry of the checkout changed')
    top = rev_parse(root, '--show-toplevel')
    if not top or Path(top).resolve() != root:
        problems.append(f'{root} is no longer the top directory of a git checkout')
    head = rev_parse(root, 'HEAD')
    if head != args.head:
        problems.append(f'HEAD is {head or "unreadable"}, expected {args.head}')
    return emit({'ok': not problems, 'checkout': str(root), 'head': args.head, 'problems': problems})


def remove(args):
    """Delete the helper's own profiles when unchanged; leave every other path alone."""
    root = checkout_root(args.checkout)
    record = Record(args.record, root, expect=args.expect_record_sha256)
    removed, absent, problems = [], [], []
    for relative, digest in list(record.data['placed'].items()):
        if relative not in PROFILE_PATHS:
            problems.append(f'{relative} is not a helper profile; left in place')
            continue
        path = inside(root, relative)
        if path.exists() and sha(path) != digest:
            problems.append(f'{relative} changed since it was placed; left in place for inspection')
            continue
        if path.exists():
            path.unlink()
            if not any(path.parent.iterdir()):
                path.parent.rmdir()
            removed.append(relative)
        else:
            absent.append(relative)
        del record.data['placed'][relative]
    return emit({'ok': not problems, 'removed': removed, 'absent': absent, 'problems': problems,
                 'record_sha256': record.save()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)

    def prepared(name, text):
        command = sub.add_parser(name, help=text)
        command.add_argument('--checkout', required=True)
        command.add_argument('--record', required=True, help='preparation record JSON, kept outside the checkout')
        return command

    b = prepared('bundle', 'copy evidence into reports/<name>/ with a MANIFEST')
    b.add_argument('--name', required=True, help='plain folder name such as review-bundle')
    b.add_argument('--file', action='append', required=True, metavar='DEST=SRC')
    v = sub.add_parser('verify-bundle', help='check a bundle against its own MANIFEST')
    v.add_argument('bundle')
    p = prepared('profile', "write the host's review execution profile")
    p.add_argument('--host', required=True, choices=sorted(PROFILES))
    p.add_argument('--check-grok', action='store_true', help='require grok inspect to show trusted, loaded rules')
    r = sub.add_parser('runtimes', help='report tool versions in this environment')
    r.add_argument('--tool', action='append', help=f'one of {sorted(TOOLS)}; fails when missing; repeatable')
    r.add_argument('--min', action='append', metavar='TOOL=VERSION', help='for example node=22.18; repeatable')
    i = prepared('integrity', 'check the checkout after the review')
    i.add_argument('--head', required=True)
    i.add_argument('--expect-record-sha256', help='record digest reported by the last preparation step')
    i.add_argument('--allow', action='append', metavar='GLOB',
                   help="paths the review may add, change or remove, such as '*__pycache__/*'; repeatable")
    x = prepared('remove', "remove the helper's unchanged profiles")
    x.add_argument('--expect-record-sha256', help='record digest reported by the last preparation step')
    args = parser.parse_args(argv)
    handler = {'bundle': bundle, 'verify-bundle': verify_bundle, 'profile': profile, 'runtimes': runtimes,
               'integrity': integrity, 'remove': remove}[args.command]
    try:
        return handler(args)
    except Usage as error:
        return emit({'ok': False, 'error': str(error)}, code=2)
    except (Unsafe, OSError, ValueError) as error:
        return emit({'ok': False, 'error': str(error)})


if __name__ == '__main__':
    sys.exit(main())
