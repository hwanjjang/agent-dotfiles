"""Explicit, bounded native/Paseo model scenario checks with private evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from account_doctor import check
from account_native import JsonProcess, ProtocolError, fixture, probe_environment
from account_storage import observed
from setup_account import BUNDLE

PAYLOAD = ('account/instructions.md', 'policies/communication.md', 'policies/execution.md',
           'policies/evidence.md', 'policies/security.md', 'skills/to-spec/SKILL.md')


def run(command, project, env, timeout, folder, label, stdin=None):
    with (folder / (label + '.stdout')).open('w') as stdout, (folder / (label + '.stderr')).open('w') as stderr:
        process = subprocess.Popen(command, cwd=project, env=env, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        try:
            if stdin is not None:
                process.stdin.write(stdin)
                process.stdin.close()
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
            code = 'timeout'
    return code, (folder / (label + '.stdout')).read_text(errors='replace')


def json_rows(text):
    rows = []
    for line in text.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def model_identity(rows, client, requested):
    """Verify client-observed identity; requesting a model alone is insufficient."""
    if client == 'claude':
        initialized = {r.get('model') for r in rows if r.get('type') == 'system' and r.get('subtype') == 'init'}
        used = {name for r in rows if r.get('type') == 'result' for name in r.get('modelUsage', {})}
        verified = initialized == {requested} and used == {requested}
    else:
        initialized = {r['result'].get('model') for r in rows if r.get('id') == 2 and 'result' in r}
        used = {r.get('params', {}).get('toModel') for r in rows if r.get('method') == 'model/rerouted'}
        completed = any(r.get('method') == 'turn/completed' and
                        r.get('params', {}).get('turn', {}).get('status') == 'completed' for r in rows)
        verified = initialized == {requested} and not (used - {requested}) and completed
    return dict(model_identity_verified=verified, initialized_models=sorted(x for x in initialized if x),
                observed_models=sorted(x for x in used if x),
                model_identity_basis='usage records' if client == 'claude' else 'thread model and turn reroute events')


def response_schema(routing=False):
    def obj(properties):
        return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
    strings = dict(type='array', items=dict(type='string'))
    props = dict(scenario=dict(type='string'), acceptance=strings,
                 examples=dict(type='array', items=obj(dict(argv=strings, stdout=dict(type='string'),
                               stderr=dict(type='string'), exit_code=dict(type='integer')))),
                 verification_executed=dict(type='boolean'), remaining_decisions=strings)
    if routing:
        props['tasks'] = dict(type='array', items=obj(dict(id=dict(type='string'), title=dict(type='string'),
                            acceptance=strings, depends_on=strings, verification=dict(type='string'))))
    return obj(props)


def codex_model_run(model, prompt, project, env, timeout, folder, schema=None):
    """Use the native app-server so identity/reroutes belong to the executed turn."""
    process = JsonProcess(['codex', 'app-server', '--stdio'], project, env, timeout)
    answer, code = '', 'provider-error'
    deadline = time.monotonic() + timeout
    try:
        process.call(1, 'initialize', dict(clientInfo=dict(name='account_doctor', version='1.0')))
        process.send(dict(method='initialized', params={}))
        started = process.call(2, 'thread/start', dict(model=model, cwd=str(project), ephemeral=True,
                               approvalPolicy='never', sandbox='read-only', allowProviderModelFallback=False))
        if started.get('model') != model:
            raise ProtocolError('model mismatch; no turn sent')
        thread = started['thread']['id']
        params = dict(threadId=thread, effort='low', input=[dict(type='text', text=prompt)])
        if schema:
            params['outputSchema'] = schema
        process.call(3, 'turn/start', params)
        completed = process.receive(lambda r: r.get('method') == 'turn/completed'
                                    and r.get('params', {}).get('threadId') == thread,
                                    max(.01, deadline - time.monotonic()))
        code = 0 if completed['params']['turn']['status'] == 'completed' else 'provider-error'
        answer = codex_final_answer(process.messages)
    except ProtocolError:
        code = 'protocol-error'
    finally:
        process.close()
        (folder / 'native.stdout').write_text(''.join(json.dumps(r) + '\n' for r in process.messages))
        (folder / 'answer.json').write_text(answer)
    return code, (folder / 'native.stdout').read_text()


def codex_final_answer(rows):
    messages = [r['params']['item'] for r in rows if r.get('method') == 'item/completed'
                and r.get('params', {}).get('item', {}).get('type') == 'agentMessage']
    final = [item['text'] for item in messages if item.get('phase') == 'final_answer']
    return final[-1] if final else messages[-1]['text'] if messages else ''


def codex_session_recovered(rows, home):
    return any(r.get('method') == 'hook/completed' and
               (run := r.get('params', {}).get('run', {})).get('eventName') == 'sessionStart'
               and run.get('status') == 'completed'
               and run.get('sourcePath') == str(home / '.codex/hooks.json')
               and any('ACCOUNT_DOCTOR_SELECTED_PLAN' in entry.get('text', '') for entry in run.get('entries', []))
               for r in rows)


def score(answer, tool_output, marker, sources):
    """Grade concrete CLI observations; echoed skill names alone never establish use."""
    try:
        match = re.search(r'```(?:json)?\s*(.*?)```', answer, re.S)
        data = json.loads(match.group(1) if match else answer)
    except (TypeError, ValueError):
        return dict(valid_json=False, passed=False)
    expected = [(['Ada'], 'Hello, Ada!\n', '', 0), ([], '', 'Usage: hello NAME\n', 2),
                ([''], '', 'Usage: hello NAME\n', 2), (['Ada', 'Lin'], '', 'Usage: hello NAME\n', 2)]
    if not isinstance(data, dict):
        return dict(valid_json=False, passed=False)
    examples = data.get('examples', [])
    valid_examples = isinstance(examples, list) and len(examples) == len(expected) and all(
        any(isinstance(row, dict) and (row.get('argv'), row.get('stdout'), row.get('stderr'), row.get('exit_code')) == value
            for row in examples) for value in expected)
    read_sources = all(content[:180] in tool_output for content in sources.values())
    result = dict(valid_json=True, scenario_read=data.get('scenario') == marker,
                  skill_and_policies_read=read_sources, cli_examples_correct=valid_examples,
                  acceptance_present=isinstance(data.get('acceptance'), list) and bool(data['acceptance'])
                  and all(isinstance(x, str) and re.match(r'AC[0-9]+:', x) for x in data['acceptance']),
                  no_false_test_claim=data.get('verification_executed') is False,
                  no_scope_expansion=data.get('remaining_decisions') == [])
    result['passed'] = all(result.values())
    return result


def successful_tool_output(rows, client):
    outputs = []
    if client == 'codex':
        for row in rows:
            item = row.get('item', row.get('params', {}).get('item', {}))
            if (row.get('type') == 'item.completed' and item.get('type') == 'command_execution' and item.get('exit_code') == 0
                    or row.get('method') == 'item/completed' and item.get('type') == 'commandExecution' and item.get('exitCode') == 0):
                outputs.append(item.get('aggregated_output', item.get('aggregatedOutput', '')))
    else:
        for row in rows:
            if row.get('type') != 'user':
                continue
            for block in row.get('message', {}).get('content', []):
                if isinstance(block, dict) and block.get('type') == 'tool_result' and not block.get('is_error'):
                    content = block.get('content', '')
                    text = content if isinstance(content, str) else json.dumps(content)
                    # Claude Read adds line-number/tab gutters; compare source bytes
                    # after removing only that presentation prefix, not inner tabs.
                    outputs.append(re.sub(r'^\d+\t', '', text, flags=re.M))
    return '\n'.join(outputs)


def source_readback_matches(quotes, sources, *, lines=None):
    """Accept known bundle-relative spellings without relaxing the content check."""
    if not isinstance(quotes, dict):
        return False
    for name, content in sources.items():
        values = [quotes[key] for key in (name, 'bundle/' + name) if key in quotes]
        expected = '\n'.join(content.splitlines()[:lines]) if lines else content[:180]
        if not values or any(value != expected for value in values):
            return False
    return True


def plan_is_verifiable(data):
    """Require acceptance coverage and an executable dependency order."""
    if not isinstance(data, dict) or not isinstance(data.get('tasks'), list) or not data['tasks']:
        return False
    acceptance = {text.split(':', 1)[0] for text in data.get('acceptance', []) if isinstance(text, str)}
    seen, covered = set(), set()
    for task in data['tasks']:
        if not isinstance(task, dict):
            return False
        ident, refs, deps = task.get('id'), task.get('acceptance'), task.get('depends_on')
        if (not isinstance(ident, str) or not ident or ident in seen
                or not isinstance(refs, list) or not refs or not all(isinstance(x, str) for x in refs)
                or not isinstance(deps, list) or not all(isinstance(x, str) for x in deps)
                or not set(deps) <= seen or not set(refs) <= acceptance
                or not isinstance(task.get('title'), str) or not task['title'].strip()
                or not isinstance(task.get('verification'), str) or not task['verification'].strip()):
            return False
        seen.add(ident); covered.update(refs)
    return bool(acceptance) and covered == acceptance


def routing_sources_loaded(events, client, sources, home):
    output = successful_tool_output(events, client)
    loaded = {r.get('tool_use_result', {}).get('commandName') for r in events
              if r.get('type') == 'user' and isinstance(r.get('tool_use_result'), dict)
              and r['tool_use_result'].get('success') is True}
    for name, source in sources.items():
        if source[:180] in output:
            continue
        skill = name.split('/')[1]
        body = re.sub(r'\A---\n.*?\n---\n', '', source, count=1, flags=re.S).strip()
        injected = False
        for row in events:
            if row.get('type') != 'user' or not isinstance(row.get('message'), dict):
                continue
            for block in row['message'].get('content', []):
                text = block.get('text', '') if isinstance(block, dict) else ''
                prefix = 'Base directory for this skill: '
                if text.startswith(prefix) and body in text:
                    path = Path(text.splitlines()[0][len(prefix):])
                    injected |= path.resolve() == home / BUNDLE / 'skills' / skill
        if client != 'claude' or skill not in loaded or not injected:
            return False
    return True


def paseo_health(timeout):
    if not shutil.which('paseo'):
        return [check('paseo.connection', 'blocked', 'Optional Paseo executable is missing.', 'Install/connect Paseo, or omit --with-paseo.')]
    if os.environ.get('PASEO_HOST'):
        return [check('paseo.connection', 'blocked', 'Remote PASEO_HOST is unsupported for local account verification.',
                      'Run on the target daemon host with its default local connection.')]
    try:
        result = subprocess.run(['paseo', 'daemon', 'status', '--json'], capture_output=True, text=True, timeout=timeout)
        data = json.loads(result.stdout)
        # A successful status command alone does not establish an available daemon.
        state = data.get('status', data)
        available = result.returncode == 0 and (data.get('localDaemon') == 'running' and data.get('connectedDaemon') == 'reachable'
                    or data.get('running') is True or state == 'running'
                    or isinstance(state, dict) and state.get('running') is True)
        return [check('paseo.connection', 'pass' if available else 'blocked',
                      'Local Paseo daemon is available.' if available else 'Local Paseo daemon availability was not established.',
                      '' if available else 'Run paseo daemon status --json locally and inspect its reported topology.')]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [check('paseo.connection', 'blocked', 'Optional local Paseo probe failed.', 'Inspect local daemon connectivity.')]


def model_checks(home, receipt, client, model, paseo, evidence, timeout, scenario='spec'):
    requested = evidence.expanduser().absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        return [check('model.evidence', 'fail', 'Symlinked evidence destinations are unsupported.')]
    folder = requested.resolve()
    repo = Path(__file__).resolve().parents[1]
    relative = folder.relative_to(repo).parts if folder.is_relative_to(repo) else None
    if relative is not None and (not relative or relative[0] not in ('.local', '.planning', 'reports')):
        return [check('model.evidence', 'fail', 'Raw model evidence must stay in an ignored directory or outside the checkout.')]
    try:
        folder.parent.mkdir(parents=True, exist_ok=True)
        folder.mkdir(mode=0o700)
    except OSError:
        return [check('model.evidence', 'fail', 'Evidence directory must be new and writable; existing runs are never overwritten.')]
    selected = PAYLOAD + (('skills/planning-and-task-breakdown/SKILL.md',) if scenario == 'routing' else ())
    sources = {name: (home / BUNDLE / name).read_text() for name in selected}
    before = {name: observed(home / BUNDLE / name) for name in selected}
    manifest = dict(client=client, requested_model=model, source_revision=receipt['source_revision'],
                    files={name: hashlib.sha256(content.encode()).hexdigest() for name, content in sources.items()},
                    scenario=scenario, model_prompt_sent=False, hook_trust_bypass=False, retries=0)
    (folder / 'input.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rows = []
    with tempfile.TemporaryDirectory(prefix='account-model-check-') as temp:
        project = Path(temp)
        marker = 'ACCOUNT_SPEC_' + uuid.uuid4().hex
        requirements = ('Scenario: ' + marker + '\nExactly one nonempty NAME to hello prints Hello, NAME! followed by one newline on stdout, '
                        'empty stderr and exit 0. Missing NAME, empty NAME or more than one argument prints exactly Usage: hello NAME '
                        'followed by one newline on stderr, empty stdout and exit 2. No files, network, implementation, tickets or publication. '
                        'All decisions are settled.\n')
        (project / 'requirements.md').write_text(requirements)
        fixture(project)
        # The synthetic plan is settled; native hooks can recover it without
        # requesting additional work or selecting any real project plan.
        plan = project / '.planning/account-doctor/task_plan.md'
        plan.write_text(plan.read_text().replace('in_progress', 'complete'))
        fixture_before = observed(project)
        files = [home / BUNDLE / name for name in selected]
        prompt = ('Use the installed to-spec skill to produce an inline JSON specification for requirements.md. '
                  'This is an authorized setup test of installed public repository instructions, with synthetic data. '
                  'Read requirements.md and these exact installed files using read-only tools: ' + ', '.join(map(str, files)) + '. '
                  'Do not read other account files, credentials, history or personal memory. Do not write files, execute the proposed CLI, '
                  'start SDLC tracking, delegate, browse or publish. Do not ask questions. Return ONLY JSON with keys: scenario '
                  '(only the Scenario value on the FIRST line of requirements.md, excluding later lines), acceptance (list of strings beginning AC1:, AC2:, etc.), '
                  'examples (exactly four objects with argv, stdout, stderr, exit_code for ["Ada"], [], [""], ["Ada","Lin"]), '
                  'verification_executed (false: proposed checks have not run), remaining_decisions (empty list). '
                  'Keep the response below 500 words. Finish at the specification. Read every listed source so the tool trace proves use.')
        if scenario == 'routing':
            prompt = ('Turn requirements.md into a behavior specification, then dependency-ordered vertical implementation slices '
                      'with concrete verification. Choose relevant installed workflows yourself. This authorized account setup test '
                      'uses only synthetic data and installed public repository guidance. Do not implement, write files, publish, '
                      'delegate, browse or start PR lifecycle tracking. Read only requirements.md and relevant installed public '
                      'instructions/skills; do not read credentials, personal memory or session history. '
                      'All decisions are settled; no questions are needed. Return only JSON: scenario (Scenario value on the FIRST '
                      'line only), acceptance (strings beginning AC1:, AC2:, etc.), examples (four objects with argv, stdout, stderr, '
                      'exit_code for ["Ada"], [], [""], ["Ada","Lin"]), verification_executed (false), remaining_decisions ([]), '
                      'tasks (ordered objects with id, title, acceptance [AC IDs], depends_on [earlier task IDs], verification '
                      '[a concrete check described as a string]). Cover every acceptance criterion. Stop after specification and plan.')
        (folder / 'prompt.txt').write_text(prompt)
        (folder / 'requirements.md').write_text(requirements)
        env = probe_environment(project, folder / 'cache')
        if client == 'claude':
            command = ['claude', '--print', '--model', model, '--output-format', 'stream-json',
                       '--verbose', '--no-session-persistence', '--tools', 'Read,Skill' if scenario == 'routing' else 'Read',
                       '--allowedTools', 'Read,Skill' if scenario == 'routing' else 'Read',
                       '--permission-mode', 'manual', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                       '--setting-sources', 'user', '--max-turns', '8' if scenario == 'routing' else '4', '--max-budget-usd', '0.50', prompt]
            if scenario == 'routing':
                command[1:1] = ['--json-schema', json.dumps(response_schema(True))]
        try:
            code, stdout = (codex_model_run(model, prompt, project, env, timeout, folder,
                                           response_schema(True) if scenario == 'routing' else None) if client == 'codex'
                            else run(command, project, env, timeout, folder, 'native'))
            manifest['model_prompt_sent'] = True
            events = json_rows(stdout)
            if client == 'codex':
                answer = (folder / 'answer.json').read_text() if (folder / 'answer.json').exists() else ''
            else:
                results = [x for x in events if x.get('type') == 'result']
                answer = results[-1].get('result', '') if results else ''
                if results and isinstance(results[-1].get('structured_output'), dict):
                    answer = json.dumps(results[-1]['structured_output'])
                if results and results[-1].get('is_error'):
                    code = 'provider-error'
                (folder / 'answer.json').write_text(answer)
            required_sources = {name: text for name, text in sources.items() if name.startswith('skills/')} if scenario == 'routing' else sources
            grade = score(answer, successful_tool_output(events, client), marker, required_sources)
            if scenario == 'routing':
                grade['skill_and_policies_read'] = routing_sources_loaded(events, client, required_sources, home)
                grade['passed'] = all(value for key, value in grade.items() if key != 'passed')
                try:
                    match = re.search(r'```(?:json)?\s*(.*?)```', answer, re.S)
                    data = json.loads(match.group(1) if match else answer)
                except ValueError:
                    data = None
                grade['plan_verifiable'] = plan_is_verifiable(data)
                grade['passed'] = grade['passed'] and grade['plan_verifiable']
            grade.update(model_identity(events, client, model))
            fixture_unchanged = observed(project) == fixture_before
            # Client/cache files are allowed only under the designated evidence cache.
            grade['fixture_unchanged'] = fixture_unchanged
            grade['installed_sources_unchanged'] = before == {name: observed(home / BUNDLE / name) for name in selected}
            grade['passed'] = (grade['passed'] and grade['model_identity_verified'] and fixture_unchanged
                               and grade['installed_sources_unchanged'] and code == 0)
            grade['exit_code'] = code
            if client == 'codex' and receipt['hooks'].get('.codex/hooks.json'):
                recovered = codex_session_recovered(events, home)
                rows.append(check('native.codex.session-start', 'pass' if recovered else 'blocked',
                                  'Native SessionStart recovered the synthetic selected plan.' if recovered
                                  else 'Actual turn did not prove selected-plan recovery.'))
            (folder / 'grade.json').write_text(json.dumps(grade, indent=2) + '\n')
            outcome = 'pass' if grade['passed'] else 'blocked' if code != 0 else 'fail'
            quota = any('weekly limit' in str(x.get('result', '')).lower() for x in events if x.get('type') == 'result')
            rows.append(check('model.native', outcome, 'Installed-skill model scenario passed.' if outcome == 'pass'
                              else 'Provider weekly quota prevents model execution.' if quota
                              else 'Actual model scenario did not pass; inspect private grade and native logs.',
                              '' if outcome == 'pass' else 'Resolve provider/quota/tool failures or scenario findings; no automatic retry occurs.'))
            if paseo and outcome == 'pass':
                rows.extend(paseo_model(client, model, prompt, project, env, folder, timeout, marker, sources))
            elif paseo:
                rows.append(check('model.paseo', 'blocked', 'Native model check did not pass; optional Paseo request was not sent.'))
        except (OSError, ValueError, subprocess.SubprocessError):
            rows.append(check('model.native', 'blocked', 'Model process failed; retained evidence is incomplete.',
                              'Inspect private evidence; do not infer a passing model evaluation.'))
    (folder / 'input.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return rows


def paseo_model(client, model, prompt, project, env, folder, timeout, marker, sources):
    health = paseo_health(timeout)
    if health[0]['status'] != 'pass':
        return health
    # Workspace and agent IDs must come from this invocation; never touch unrelated sessions.
    workspace = agent = None
    rows = []
    fixture_before = observed(project)
    source_before = {name: observed(Path.home() / BUNDLE / name) for name in sources}
    try:
        code, raw = run(['paseo', 'workspace', 'create', '--isolation', 'local', '--path', str(project), '--json'],
                        project, env, timeout, folder, 'paseo-workspace')
        data = json.loads(raw)
        workspace = data.get('workspaceId') or data.get('workspace', {}).get('id')
        if code or not workspace:
            raise ValueError('workspace creation not established')
        # The CLI currently summarizes tool output. An exact, independently graded
        # source readback supplements that limited timeline; it is not a full audit.
        excerpt = ('first eight lines (include blank lines, exclude the final newline)' if client == 'claude'
                   else 'first 180 characters')
        prompt += (' Also include source_quotes: an object mapping each listed repository-relative source path '
                   'to its exact ' + excerpt + ' read from the installed file (preserve internal newlines). '
                   'The word limit excludes source_quotes.')
        command = ['paseo', 'run', '--background', '--workspace', workspace, '--provider', client + '/' + model,
                   '--mode', 'auto' if client == 'codex' else 'plan', '--thinking', 'low',
                   '--title', 'Account setup smoke', '--json', prompt]
        code, raw = run(command, project, env, timeout, folder, 'paseo-create')
        data = json.loads(raw)
        agent = data.get('agentId') or data.get('agent', {}).get('id')
        if code or not agent:
            raise ValueError('agent creation not established')
        (folder / 'paseo-owned.json').write_text(json.dumps(dict(workspace_id=workspace, agent_id=agent, requested_model=model), indent=2) + '\n')
        code, _ = run(['paseo', 'wait', agent, '--timeout', str(timeout), '--json'], project, env, timeout + 5, folder, 'paseo-wait')
        _, raw = run(['paseo', 'logs', agent, '--json'], project, env, timeout, folder, 'paseo-logs')
        _, inspection = run(['paseo', 'inspect', agent, '--json'], project, env, timeout, folder, 'paseo-inspect')
        identity = json.loads(inspection)
        # CLI versions may expose title-cased inspect keys. Accept known shapes only.
        observed_model = identity.get('Model', identity.get('model'))
        observed_provider = identity.get('Provider', identity.get('provider'))
        decoder = json.JSONDecoder()
        candidates = []
        for match in re.finditer(r'\{', raw):
            try:
                value, _ = decoder.raw_decode(raw[match.start():])
                if isinstance(value, dict) and value.get('scenario') == marker:
                    candidates.append(value)
            except ValueError:
                continue
        answer = candidates[-1] if candidates else {}
        quotes = answer.get('source_quotes', {})
        valid_quotes = source_readback_matches(quotes, sources, lines=8 if client == 'claude' else None)
        # Use only observed readback bytes, never substitute source bytes for missing evidence.
        grade = score(json.dumps(answer), '\n'.join(v for v in quotes.values() if isinstance(v, str))
                      if isinstance(quotes, dict) else '', marker, sources)
        grade.update(source_readback_exact=valid_quotes, observed_model=observed_model, observed_provider=observed_provider,
                     source_read_proof='exact model readback plus summarized shell trace; not a complete tool audit')
        grade['fixture_unchanged'] = observed(project) == fixture_before
        grade['installed_sources_unchanged'] = source_before == {name: observed(Path.home() / BUNDLE / name) for name in sources}
        read_trace = '[Shell]' in raw if client == 'codex' else all(
            '[Read] ' + str(Path.home() / BUNDLE / name) in raw for name in sources)
        grade['read_trace_present'] = read_trace
        grade['passed'] = (grade['passed'] and valid_quotes and code == 0 and observed_model == model
                           and observed_provider == client and read_trace
                           and grade['fixture_unchanged'] and grade['installed_sources_unchanged'])
        (folder / 'paseo-grade.json').write_text(json.dumps(grade, indent=2) + '\n')
        rows.append(check('model.paseo', 'pass' if grade['passed'] else 'fail',
                          'Paseo model, scenario and exact installed-source readback passed.' if grade['passed']
                          else 'Paseo scenario, source readback or actual model identity did not pass.',
                          '' if grade['passed'] else 'Inspect private grade/timeline; summary output alone is insufficient.'))
    except (OSError, ValueError, subprocess.SubprocessError):
        rows.append(check('model.paseo', 'blocked', 'Optional Paseo model execution was not established.',
                          'Inspect private creation/connection evidence; never blindly retry uncertain creation.'))
    finally:
        cleanup = True
        if agent:
            code, _ = run(['paseo', 'archive', agent, '--json'], project, env, timeout, folder, 'paseo-archive-agent')
            cleanup &= code == 0
        if workspace:
            code, _ = run(['paseo', 'workspace', 'archive', workspace, '--json'], project, env, timeout, folder, 'paseo-archive-workspace')
            cleanup &= code == 0
            if code == 0:
                # Local workspace creation implicitly registers this unique temporary
                # project. Remove its empty registry entry as part of owned teardown.
                try:
                    code, raw = run(['paseo', 'project', 'ls', '--json'], project, env, timeout, folder, 'paseo-projects')
                    projects = json.loads(raw)
                    if code or not isinstance(projects, list):
                        raise ValueError('project list unavailable')
                    for entry in projects:
                        if Path(entry.get('path', '')).resolve() == project.resolve():
                            ident = entry.get('projectId')
                            if not ident:
                                raise ValueError('project identity unavailable')
                            code, _ = run(['paseo', 'project', 'delete', ident, '--json'], project, env, timeout, folder, 'paseo-delete-project')
                            cleanup &= code == 0
                except (OSError, ValueError, subprocess.SubprocessError):
                    cleanup = False
        if not cleanup:
            rows.append(check('paseo.cleanup', 'fail', 'Owned Paseo cleanup failed.', 'Archive only the IDs retained in this run.'))
    return rows
