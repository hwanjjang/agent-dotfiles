"""Read-only account diagnostics; native and model execution are explicit opt-ins."""
import json
import os
from pathlib import Path
import re
import shutil

from account_storage import observed, read, safe
from setup_account import BUNDLE, load_receipt, status


def check(ident, outcome, message, action=''):
    return dict(id=ident, status=outcome, message=message, action=action)


def diagnose(home, *, native=False, client=None, model=None, paseo=False, evidence=None, timeout=90, scenario='spec'):
    result = dict(schema_version=1, scope='model' if model else 'native' if native else 'offline',
                  evidence_kind='account_qualification',
                  comparison=dict(status='not_run', promotion_eligible=False),
                  status='pass', source_revision=None, checks=[], model_execution_verified=False,
                  native_activation_verified=False)
    checks = result['checks']
    try:
        receipt = load_receipt(home)
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        checks.append(check('installation', 'fail', 'Installation receipt is invalid or unsafe.',
                            'Inspect the local receipt and restore it from a trusted backup.'))
        return finish(result)
    if not receipt:
        checks.append(check('installation', 'fail', 'No owned installation was found.',
                            'Preview setup-account.sh install before applying it.'))
        return finish(result)
    result['source_revision'] = receipt.get('source_revision')
    checks.append(check('installation', 'pass', 'An owned installation receipt is present.'))
    try:
        drift = status(home)['drift']
        checks.append(check('owned-content', 'fail' if drift else 'pass',
                            f'{len(drift)} owned paths or fragments differ from their receipt.',
                            'Reconcile local edits before updating; do not force overwrite.' if drift else ''))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        checks.append(check('owned-content', 'fail', 'Owned files or settings could not be validated.',
                            'Inspect malformed settings or unsafe paths locally.'))
    skills = sorted(Path(name).name for name in receipt['assets']
                    if re.fullmatch(r'\.agents/skills/[a-z0-9-]+', name))
    checks.append(check('skill-selection', 'pass' if skills else 'fail', f'{len(skills)} owned skills are selected.'))
    for host, directory in [('codex', '.codex'), ('claude', '.claude')]:
        if client and host != client:
            checks.append(check(host + '.client', 'skipped', 'Client-specific readiness was not selected.'))
            continue
        issues = []
        for skill in skills:
            expected = home / BUNDLE / 'skills' / skill
            # Codex normally discovers .agents/skills; any old same-name aliases must agree.
            for folder in ('.agents', directory):
                path = safe(home, folder + '/skills/' + skill)
                if folder == directory and host == 'codex' and not path.exists() and not path.is_symlink():
                    continue
                if not path.is_symlink() or path.resolve() != expected or not (expected / 'SKILL.md').is_file():
                    issues.append(skill)
        checks.append(check(host + '.skill-paths', 'fail' if issues else 'pass',
                            f'{len(set(issues))} selected skills have missing or conflicting source paths.',
                            'Reconcile same-name overrides; keep one source per skill.' if issues else ''))
        executable = shutil.which(host)
        checks.append(check(host + '.executable', 'pass' if executable else 'blocked',
                            'Client executable is available.' if executable else 'Client executable is missing.',
                            '' if executable else 'Install this client through its supported host package manager.'))
        variable = 'CODEX_HOME' if host == 'codex' else 'CLAUDE_CONFIG_DIR'
        selected = os.environ.get(variable)
        if selected and Path(selected).expanduser().resolve() != home / directory:
            checks.append(check(host + '.profile', 'fail', 'A nondefault client profile selects another account.',
                                'Run the check in the intended default profile; custom profiles are unsupported.'))
    try:
        override = read(safe(home, '.codex/AGENTS.override.md')).strip()
        checks.append(check('codex.instructions', 'fail' if override else 'pass',
                            'Global AGENTS.override.md masks the installed entry point.' if override
                            else 'No global instruction override masks the installed entry point.',
                            'Reconcile AGENTS.override.md explicitly.' if override else ''))
        for name, block in receipt['instructions'].items():
            raw = read(safe(home, name)).decode()
            foreign = re.search(r'<!--\s*(?!agent-dotfiles:)[\w-]+:begin', raw)
            valid = raw.count(block) == 1 and not foreign
            checks.append(check('instructions.' + name.split('/')[0][1:], 'pass' if valid else 'fail',
                                'Exactly one installed instruction block, without another managed owner.' if valid
                                else 'Instruction ownership is missing, changed or duplicated.',
                                '' if valid else 'Retire the previous managed fragment using its exact receipt.'))
        for name in ('.codex/hooks.json', '.claude/settings.json'):
            config = json.loads(read(safe(home, name)) or b'{}')
            expected = receipt['hooks'].get(name, {})
            extra = 0
            for event, groups in config.get('hooks', {}).items():
                for group in groups:
                    if group in expected.get(event, []):
                        continue
                    if re.search(r'planning[-_]with[-_]files|planning-hook|flyingcorp-hook', json.dumps(group)):
                        extra += 1
            checks.append(check('hooks.' + name.split('/')[0][1:], 'fail' if extra else 'pass',
                                f'{extra} competing account planning hook groups found.',
                                'Reconcile the previous hook owner; do not run both routes.' if extra else ''))
        # Inline Codex hooks are another active configuration source.
        import tomllib
        inline = tomllib.loads(read(safe(home, '.codex/config.toml')).decode()).get('hooks', {})
        if inline and receipt.get('planning_hooks') and re.search(r'planning|/hooks/', json.dumps(inline)):
            checks.append(check('codex.inline-hooks', 'fail', 'Inline planning hooks compete with the installed route.',
                                'Keep one owned planning registration per event.'))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, UnicodeError):
        checks.append(check('configuration', 'fail', 'Instruction or hook configuration is malformed or unsafe.',
                            'Inspect the local files; their contents are intentionally excluded from this report.'))
    checks.append(check('mcp.connection', 'skipped', 'Configuration ownership is checked; MCP authentication is not exercised.'))
    if native or model or paseo:
        if home != Path.home().resolve():
            checks.append(check('native.target', 'blocked', 'Native checks cannot target another account using --home.',
                                'Run the command on the target account without overriding HOME.'))
        elif any(x['status'] in ('fail', 'blocked') for x in checks):
            checks.append(check('native.prerequisites', 'blocked', 'Repair offline findings before running client processes.'))
        else:
            from account_native import native_checks
            if native:
                checks.extend(native_checks(home, receipt, skills, client, timeout))
            if model:
                from account_model_check import model_checks
                checks.extend(model_checks(home, receipt, client, model, paseo, evidence, timeout, scenario))
                result['model_execution_verified'] = any(x['id'] == 'model.native' and x['status'] == 'pass' for x in checks)
            elif paseo:
                from account_model_check import paseo_health
                checks.extend(paseo_health(timeout))
    else:
        checks.append(check('native', 'skipped', 'Native discovery and hook trust were not checked. Use --native.'))
    if not model:
        checks.append(check('model', 'skipped', 'No real model task ran. Use --model-smoke with an exact model and private evidence directory.'))
    return finish(result)


def finish(result):
    native = [row for row in result['checks'] if row['id'].startswith('native.')]
    clients = {row['id'].split('.')[1] for row in native
               if row['id'].split('.')[1] in ('codex', 'claude')}
    result['native_activation_by_client'] = {
        client: any(row['id'] == f'native.{client}.session-start' and row['status'] == 'pass'
                    for row in native)
                and all(row['status'] == 'pass' for row in native
                        if row['id'].startswith(f'native.{client}'))
        for client in sorted(clients)}
    result['native_activation_verified'] = bool(clients) and all(result['native_activation_by_client'].values())
    statuses = {x['status'] for x in result['checks']}
    result['status'] = 'fail' if 'fail' in statuses else 'blocked' if 'blocked' in statuses else 'pass'
    return result


def render(result):
    lines = [f"Account doctor: {result['status'].upper()} ({result['scope']})",
             'Source revision: ' + str(result['source_revision'])]
    for row in result['checks']:
        lines.append(f"[{row['status'].upper()}] {row['id']}: {row['message']}")
        if row['action']:
            lines.append('  Next: ' + row['action'])
    lines.append('Coverage is limited to the listed checks; skipped checks are not passes.')
    lines.append('Comparative evaluation: NOT RUN; this report cannot establish improvement or qualify promotion.')
    return '\n'.join(lines)
