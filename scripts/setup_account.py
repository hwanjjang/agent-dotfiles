#!/usr/bin/env python3
"""Manage, diagnose and verify an owned account bundle (POSIX, Python 3.11+)."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from account_storage import (RECEIPT, STATE_DIR, desired, digest, encoded, lock,
                             observed, read, require, rollback, rollback_plan, safe, transact,
                             PRESERVED_SKILLS)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = '.agents/agent-dotfiles/bundle'
BEGIN, END = '<!-- agent-dotfiles:begin -->', '<!-- agent-dotfiles:end -->'
TBEGIN, TEND = '# agent-dotfiles:mcp:begin', '# agent-dotfiles:mcp:end'
CONFIGS = {'.codex/hooks.json', '.claude/settings.json'}
INSTRUCTIONS = {'.codex/AGENTS.md', '.claude/CLAUDE.md', '.hermes/SOUL.md'}


def owned_path(name):
    if '/skills/' in name and Path(name).name in PRESERVED_SKILLS:
        return False
    return (name.startswith(BUNDLE + '/') or name == '.agents/bin/planning-hook.py'
            or name.startswith('.codex/hooks/') or name == '.claude/hooks/planning-with-files-dispatch.sh'
            or re.fullmatch(r'\.(?:agents|codex|claude|hermes)/skills/[a-z0-9-]+', name))


def source_snapshot(repo, revision):
    def git(*args):
        result = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args],
                                capture_output=True, check=True)
        return result.stdout
    require(not revision.startswith('-'), 'Invalid revision')
    sha = git('rev-parse', '--verify', revision + '^{commit}').decode().strip()
    files = {}
    with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', sha))) as archive:
        for member in archive:
            name = member.name
            if not (name.startswith(('skills/', 'policies/', 'account/', 'mcp/', 'tools/', 'docs/'))
                    or name in ('README.md', 'LICENSE')) or member.isdir():
                continue
            require(member.isfile() and not Path(name).is_absolute() and '..' not in Path(name).parts,
                    'Unsupported source path or symlink')
            files[name] = {'data': archive.extractfile(member).read(), 'mode': 0o755 if member.mode & 0o111 else 0o644}
    require('account/instructions.md' in files and 'account/hooks/planning-hook.py' in files,
            'Selected revision has no account source bundle')
    skills = sorted(name.split('/')[1] for name in files if re.fullmatch(r'skills/[^/]+/SKILL.md', name))
    require(skills and not set(skills) & PRESERVED_SKILLS, 'Invalid source skill selection')
    for skill in skills:
        provenance = json.loads(files[f'skills/{skill}/provenance.json']['data'])
        require(set(provenance.get('skill_dependencies', [])) <= set(skills), f'Missing dependencies for {skill}')
    return sha, files, skills


def load_receipt(home):
    raw = read(safe(home, RECEIPT))
    if not raw:
        return {}
    data = json.loads(raw)
    require(data.get('version') == 1 and data.get('home') == str(home), 'Invalid installation receipt')
    for key in ('assets', 'instructions', 'hooks', 'claude_mcp'):
        require(isinstance(data.get(key), dict), f'Invalid receipt: {key}')
    for name in data['assets']:
        require(owned_path(name), 'Receipt owns an unsupported asset')
        safe(home, name)
    require(set(data['instructions']) <= INSTRUCTIONS and set(data['hooks']) <= CONFIGS,
            'Receipt owns an unsupported configuration')
    require(isinstance(data.get('codex_mcp'), str), 'Invalid MCP receipt')
    return data


def replace_block(raw, old, new, begin, end):
    if old:
        require(raw.count(old) == 1, 'Managed instruction/config block changed; reconcile first')
        return raw.replace(old, new, 1)
    require(begin not in raw and end not in raw, 'Unowned or duplicate managed block')
    if not new:
        return raw
    return raw + ('' if not raw or raw.endswith('\n') else '\n') + new


def hook_groups(home, client, files):
    groups = json.loads(files[f'account/hooks/{client}.example.json']['data'])['hooks']
    old = 'python3 "$HOME/.agents/bin/planning-hook.py"'
    runner = shlex.quote(sys.executable) + ' ' + shlex.quote(str(home / '.agents/bin/planning-hook.py'))
    for values in groups.values():
        for group in values:
            for hook in group['hooks']:
                require(hook['command'].startswith(old + ' '), 'Unsupported hook template')
                hook['command'] = runner + hook['command'][len(old):]
    return groups


def remove_groups(config, old):
    hooks = config.get('hooks', {})
    for event, groups in old.items():
        for group in groups:
            require(hooks.get(event, []).count(group) == 1, 'Managed hook changed or duplicated')
            hooks[event].remove(group)
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        config.pop('hooks', None)


def mcp_definitions(files, selection):
    claude, lines = {}, []
    for name in selection:
        require(name in ('github', 'context7', 'playwright'), 'Unknown MCP selection')
        server = json.loads(files[f'mcp/claude-code/{name}.json']['data'])['mcpServers'][name]
        claude[name] = server
        lines.append('[mcp_servers.' + json.dumps(name) + ']')
        if server['type'] == 'stdio':
            lines.extend(k + ' = ' + json.dumps(server[k]) for k in ('command', 'args'))
        else:
            lines.append('url = ' + json.dumps(server['url']))
            headers = dict(server.get('headers', {}))
            auth = headers.pop('Authorization', '')
            match = re.fullmatch(r'Bearer \$\{([A-Z_][A-Z0-9_]*)\}', auth)
            require(match is not None, 'Unsupported MCP credential placeholder')
            lines.append('bearer_token_env_var = ' + json.dumps(match[1]))
            if headers:
                lines.append('[mcp_servers.' + json.dumps(name) + '.http_headers]')
                lines.extend(json.dumps(k) + ' = ' + json.dumps(v) for k, v in headers.items())
    block = TBEGIN + '\n' + '\n'.join(lines) + '\n' + TEND + '\n' if lines else ''
    return claude, block


def check_codex_mcp(raw, block):
    if block:
        require(raw.count(block) == 1, 'Managed Codex MCP block changed')
        actual = tomllib.loads(raw).get('mcp_servers', {})
        expected = tomllib.loads(block).get('mcp_servers', {})
        require(all(actual.get(name) == value for name, value in expected.items()),
                'Managed Codex MCP settings changed outside the marked block')


def legacy_parts(home, path):
    """Retire only exact instruction/hook fragments from an explicit old receipt."""
    if path is None:
        return {}
    data = json.loads(path.read_bytes())
    require(data.get('version') == 1 and data.get('home') == str(home), 'Legacy receipt belongs to another account')
    require(set(data.get('instructions', {})) <= INSTRUCTIONS and set(data.get('hooks', {})) <= CONFIGS,
            'Unsupported legacy configuration paths')
    for block in data.get('instructions', {}).values():
        require(isinstance(block, str) and block.startswith('<!--') and block.endswith('-->\n'),
                'Legacy instruction must be an exact marked block')
    return {k: data.get(k, {}) for k in ('instructions', 'hooks')}


def status(home):
    receipt = load_receipt(home)
    drift = [name for name, value in receipt.get('assets', {}).items()
             if observed(safe(home, name)) != value]
    for name, block in receipt.get('instructions', {}).items():
        if read(safe(home, name)).decode().count(block) != 1:
            drift.append(name)
    for name, events in receipt.get('hooks', {}).items():
        hooks = json.loads(read(safe(home, name)) or b'{}').get('hooks', {})
        if any(hooks.get(event, []).count(group) != 1 for event, groups in events.items() for group in groups):
            drift.append(name)
    if receipt.get('codex_mcp'):
        try:
            check_codex_mcp(read(safe(home, '.codex/config.toml')).decode(), receipt['codex_mcp'])
        except ValueError:
            drift.append('.codex/config.toml')
    if receipt.get('claude_mcp'):
        servers = json.loads(read(safe(home, '.claude.json')) or b'{}').get('mcpServers', {})
        if any(servers.get(k) != v for k, v in receipt['claude_mcp'].items()):
            drift.append('.claude.json')
    return dict(installed=bool(receipt), source_revision=receipt.get('source_revision'),
                hermes=receipt.get('hermes', False), drift=sorted(set(drift)),
                native_activation_verified=False)


def prepare(home, repo, revision='HEAD', action='install', hermes=None, hooks=None,
            mcp=None, legacy=None):
    old = load_receipt(home)
    require(action != 'update' or old, 'No installation receipt; use install')
    require(not legacy or not old, 'Legacy adoption is only available on first install')
    remove = action == 'uninstall'
    require(not remove or old, 'No installation receipt; nothing owned to uninstall')
    sha, files, skills = source_snapshot(repo, revision) if not remove else ('', {}, [])
    hermes = bool(old.get('hermes', False)) if hermes is None else hermes
    hooks = old.get('planning_hooks', True) if hooks is None else hooks
    mcp = old.get('mcp_selection', []) if mcp is None else mcp
    if remove:
        hermes, hooks, mcp = False, False, []
    require(not hermes or shutil.which('hermes') is not None, '--with-hermes requires an installed hermes executable on PATH')
    # Current hook/runtime package has a fixed POSIX layout; do not silently target a different profile.
    for key, rel in [('CODEX_HOME', '.codex'), ('CLAUDE_CONFIG_DIR', '.claude'), ('HERMES_HOME', '.hermes')]:
        if os.environ.get(key) and (key != 'HERMES_HOME' or hermes or old.get('hermes')):
            require(Path(os.environ[key]).expanduser().resolve() == home / rel,
                    f'{key} selects a different profile; this adapter supports default client directories only')
    changes, before, after, conflicts = {}, {}, {}, []
    receipt = dict(version=1, home=str(home), source_revision=sha, hermes=hermes,
                   planning_hooks=hooks, mcp_selection=mcp, assets={}, instructions={}, hooks={},
                   claude_mcp={}, codex_mcp='')

    def change(name, value, owned=True):
        path = safe(home, name)
        actual = observed(path)
        before[name], after[name] = actual, desired(value)
        if actual is not None and not owned:
            conflicts.append(name)
        if actual != after[name]:
            changes[name] = value

    assets = {}
    if not remove:
        # Snapshot, not a link to the mutable checkout; preserve cross-skill/policy paths.
        assets = {BUNDLE + '/' + name: value for name, value in files.items()}
        for skill in skills:
            for client in ('agents', 'claude') + (('hermes',) if hermes else ()):
                name = f'.{client}/skills/{skill}'
                assets[name] = {'link': str(home / BUNDLE / 'skills' / skill)}
        # Runtime expects this compatibility path. Avoid another full Codex skill tree.
        assets['.codex/skills/planning-with-files'] = {'link': str(home / BUNDLE / 'skills/planning-with-files')}
        if hooks:
            assets['.agents/bin/planning-hook.py'] = files['account/hooks/planning-hook.py']
            for name, value in files.items():
                if name.startswith('account/hooks/planning-with-files/codex/'):
                    assets['.codex/hooks/' + Path(name).name] = value
            assets['.claude/hooks/planning-with-files-dispatch.sh'] = files['account/hooks/planning-with-files/claude/dispatch.sh']
    for name in sorted(set(assets) | set(old.get('assets', {}))):
        actual = observed(safe(home, name))
        if name in old.get('assets', {}):
            require(actual == old['assets'][name], f'Managed asset changed: {name}')
        value = assets.get(name)
        change(name, value, name in old.get('assets', {}))
        if value is not None:
            receipt['assets'][name] = desired(value)

    retiring = legacy_parts(home, legacy)
    if retiring:
        conflicts.append('legacy instruction/hook ownership transfer')
    target_instructions = {'.codex/AGENTS.md', '.claude/CLAUDE.md'} | ({'.hermes/SOUL.md'} if hermes else set())
    if remove:
        target_instructions = set()
    if not remove and read(safe(home, '.codex/AGENTS.override.md')).strip():
        raise ValueError('Codex AGENTS.override.md masks global guidance; reconcile it before installation')
    for name in sorted(target_instructions | set(old.get('instructions', {})) | set(retiring.get('instructions', {}))):
        path = safe(home, name)
        raw = read(path).decode()
        retired = retiring.get('instructions', {}).get(name)
        if retired:
            require(raw.count(retired) == 1, 'Legacy instruction changed; reconcile first')
            raw = raw.replace(retired, '', 1)
        # Detect an old marked owner instead of layering a second set of instructions silently.
        require(not re.search(r'<!--\s*(?!agent-dotfiles:)[\w-]+:begin', raw),
                'Existing managed instructions need --legacy-receipt ownership transfer')
        target = str(home / BUNDLE / 'account/instructions.md')
        content = ('@' + target if name == '.claude/CLAUDE.md' and not re.search(r'\s', target)
                   else 'Read and follow ' + json.dumps(target) + ' for shared account instructions.')
        block = BEGIN + '\n' + content + '\n' + END + '\n' if name in target_instructions else ''
        updated = replace_block(raw, old.get('instructions', {}).get(name, ''), block, BEGIN, END)
        change(name, {'data': updated.encode(), 'mode': path.stat().st_mode & 0o777 if path.exists() else 0o600} if updated else None)
        if block:
            receipt['instructions'][name] = block

    for client, name in [('codex', '.codex/hooks.json'), ('claude', '.claude/settings.json')]:
        previous = old.get('hooks', {}).get(name, {})
        retired = retiring.get('hooks', {}).get(name, {})
        if not hooks and not previous and not retired:
            continue
        if client == 'codex' and hooks:
            inline = tomllib.loads(read(safe(home, '.codex/config.toml')).decode()).get('hooks', {})
            require(not any(re.search(r'planning|/hooks/', json.dumps(groups))
                            for groups in inline.values()),
                    'Inline Codex planning hooks need ownership reconciliation')
        path = safe(home, name)
        raw = read(path)
        config = json.loads(raw or b'{}')
        remove_groups(config, previous)
        remove_groups(config, retired)
        groups = hook_groups(home, client, files) if hooks else {}
        for event, additions in groups.items():
            existing = config.setdefault('hooks', {}).setdefault(event, [])
            for group in existing:
                require(not any(re.search(r'planning[-_]with[-_]files|planning-hook|/hooks/(run_sh|pre_tool_use|post_tool_use|permission_request|stop)\.py', h.get('command', ''))
                                for h in group.get('hooks', [])),
                        'Existing planning route needs explicit ownership reconciliation')
            existing.extend(additions)
        if groups:
            receipt['hooks'][name] = groups
        data = raw if json.loads(raw or b'{}') == config else encoded(config)
        change(name, {'data': data, 'mode': path.stat().st_mode & 0o777 if path.exists() else 0o600} if raw or config else None)

    claude, block = mcp_definitions(files, mcp)
    if block or old.get('codex_mcp'):
        name = '.codex/config.toml';path = safe(home, name);raw = read(path).decode()
        check_codex_mcp(raw, old.get('codex_mcp', ''))
        stripped = replace_block(raw, old.get('codex_mcp', ''), '', TBEGIN, TEND)
        existing = tomllib.loads(stripped).get('mcp_servers', {})
        require(not set(existing) & set(mcp), 'Preserved Codex MCP name conflicts with selection')
        updated = replace_block(stripped, '', block, TBEGIN, TEND)
        tomllib.loads(updated)
        change(name, {'data': updated.encode(), 'mode': path.stat().st_mode & 0o777 if path.exists() else 0o600} if updated else None)
        receipt['codex_mcp'] = block
    if claude or old.get('claude_mcp'):
        name = '.claude.json';path = safe(home, name);raw = read(path);config = json.loads(raw or b'{}')
        servers = config.setdefault('mcpServers', {})
        for key, server in old.get('claude_mcp', {}).items():
            require(servers.get(key) == server, 'Managed Claude MCP changed')
            del servers[key]
        require(not set(servers) & set(claude), 'Preserved Claude MCP name conflicts with selection')
        servers.update(claude)
        if not servers:
            config.pop('mcpServers')
        change(name, {'data': encoded(config), 'mode': path.stat().st_mode & 0o777 if path.exists() else 0o600} if raw or config else None)
        receipt['claude_mcp'] = claude
    # Receipt is last so a successful write represents the entire applied candidate.
    change(RECEIPT, None if remove else {'data': encoded(receipt), 'mode': 0o600})
    # Asset takeover never grants permission to replace the source checkout itself.
    source = repo.resolve()
    for name in changes:
        target = safe(home, name)
        for destination in (target, target.resolve()):
            require(not source.is_relative_to(destination) and not destination.is_relative_to(source),
                    'Source and delivery overlap: ' + name)
    prerequisites = [exe for exe in ('codex', 'claude', 'git', 'sh', 'node', 'rg', 'gh') if shutil.which(exe) is None]
    hook_review = [dict(event=event, matcher=group.get('matcher'), command=handler['command'],
                       definition_sha256=digest(encoded(dict(event=event, group=group, handler=handler))))
                   for event, groups in receipt['hooks'].get('.codex/hooks.json', {}).items()
                   for group in groups for handler in group['hooks']]
    plan = dict(version=1, action=action, home=str(home), source_revision=sha,
                hermes=hermes, planning_hooks=hooks, mcp=mcp, skills=skills,
                hook_activation=dict(codex=hook_review, runs_outside_sandbox=True,
                                     trust_persists=True, trust_changed_by_installer=False,
                                     next_action='Review the listed definitions in native /hooks; activate only within explicit authority.'),
                conflicts=sorted(set(conflicts)), missing_executables=prerequisites,
                before=before, after=after, changes=list(changes))
    return plan, changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'update', 'uninstall', 'status', 'rollback', 'doctor'))
    parser.add_argument('--home', type=Path, default=Path.home(), help='Target account; tests use a disposable directory without changing HOME')
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--revision', default='HEAD', help='Committed local Git revision; never fetches or uses dirty worktree files')
    parser.add_argument('--apply', action='store_true', help='Apply the previewed operation; otherwise read-only')
    parser.add_argument('--approve-plan', type=Path, help='Exact previously saved preview required to take over conflicting selected paths')
    parser.add_argument('--legacy-receipt', type=Path, help='Explicit prior v1 receipt: retire only matching instruction/hook fragments')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--with-hermes', dest='hermes', action='store_true', default=None)
    group.add_argument('--without-hermes', dest='hermes', action='store_false')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--with-hooks', dest='hooks', action='store_true', default=None)
    group.add_argument('--without-hooks', dest='hooks', action='store_false')
    parser.add_argument('--mcp', help='Comma-separated opt-in selection: github,context7,playwright; none to remove managed registrations')
    parser.add_argument('--transaction', help='Backup ID for guarded rollback')
    parser.add_argument('--json', action='store_true', help='Machine-readable doctor report')
    parser.add_argument('--native', action='store_true', help='Doctor: query native clients without model requests')
    parser.add_argument('--client', choices=('codex', 'claude'), help='Doctor: select one native/model client')
    parser.add_argument('--model-smoke', action='store_true', help='Doctor: opt in to a real, potentially billable model scenario')
    parser.add_argument('--model', help='Doctor: exact model ID; required for a model smoke, never silently replaced')
    parser.add_argument('--scenario', choices=('spec', 'routing'), default='spec', help='Doctor model scenario: explicit spec or natural skill routing and planning')
    parser.add_argument('--with-paseo', action='store_true', help='Doctor: include optional local Paseo checks')
    parser.add_argument('--evidence-dir', type=Path, help='Doctor model smoke: new private evidence directory')
    parser.add_argument('--timeout', type=int, default=90, help='Doctor subprocess deadline in seconds (1–300)')
    args = parser.parse_args(argv)
    try:
        require(args.action == 'doctor' or not (args.json or args.native or args.client or args.model_smoke
                or args.model or args.with_paseo or args.evidence_dir or args.timeout != 90 or args.scenario != 'spec'),
                'Diagnostic options require the doctor action')
        require(os.name == 'posix', 'Only POSIX accounts are supported')
        home = args.home.expanduser().absolute()
        require(home.exists() and home.is_dir() and not home.is_symlink(), 'Target home must be an existing real directory')
        home = home.resolve()
        if args.action == 'doctor':
            require(not args.apply and not args.approve_plan and not args.legacy_receipt
                    and not args.transaction and args.hermes is None and args.hooks is None
                    and args.mcp is None,
                    'Doctor does not accept installation or mutation flags')
            require(1 <= args.timeout <= 300, 'Timeout must be between 1 and 300 seconds')
            require(not args.model_smoke or (args.client and args.model and args.evidence_dir),
                    'Model smoke requires --client, --model and a new --evidence-dir')
            require(args.model_smoke or not args.model, '--model requires --model-smoke')
            require(args.model_smoke or not args.evidence_dir, '--evidence-dir requires --model-smoke')
            require(args.scenario == 'spec' or (args.model_smoke and not args.with_paseo),
                    'Routing requires --model-smoke and currently supports native clients only')
            from account_doctor import diagnose, render
            result = diagnose(home, native=args.native, client=args.client,
                              model=args.model if args.model_smoke else None,
                              paseo=args.with_paseo, evidence=args.evidence_dir, timeout=args.timeout, scenario=args.scenario)
            print(json.dumps(result, indent=2) if args.json else render(result))
            return 1 if result['status'] in ('fail', 'blocked') else 0
        repo = args.repo.expanduser().resolve()
        require(not repo.is_relative_to(home / BUNDLE) and not (home / BUNDLE).is_relative_to(repo), 'Source and delivery overlap')
        if args.action == 'status':
            require(not args.apply, 'Status is read-only')
            result = status(home)
            print(json.dumps(result, indent=2))
            return 1 if result['drift'] else 0
        if args.action == 'rollback':
            require(args.transaction, 'Rollback requires --transaction')
            if args.apply:
                with lock(home):
                    rollback(home, args.transaction)
            else:
                _, journal = rollback_plan(home, args.transaction)
                print(json.dumps({'action': 'rollback', 'transaction': args.transaction, 'paths': list(journal['originals'])}, indent=2))
            return 0
        mcp = None if args.mcp is None else ([] if args.mcp == 'none' else sorted(set(args.mcp.split(','))))
        def run():
            plan, changes = prepare(home, repo, args.revision, args.action, args.hermes, args.hooks,
                                    mcp, args.legacy_receipt)
            if args.apply:
                require(not plan['conflicts'] or (args.approve_plan and json.loads(args.approve_plan.read_bytes()) == plan),
                        'Conflicts require review of saved preview and --approve-plan with that exact file')
                transaction = transact(home, plan, changes)
                print(json.dumps({'action': args.action, 'changed_paths': len(changes), 'transaction': transaction,
                                  'source_revision': plan['source_revision'], 'missing_executables': plan['missing_executables'],
                                  'native_activation_verified': False}, indent=2))
            else:
                print(json.dumps(plan, indent=2))
        if args.apply:
            with lock(home):
                run()
        else:
            run()
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        # Never print config contents, environment values or subprocess stderr.
        print('Account setup: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
