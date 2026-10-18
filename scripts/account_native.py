"""Local native-client probes. Sends no user turn or model request."""
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import tempfile
import threading
import time

from account_doctor import check
from setup_account import BUNDLE


class ProtocolError(Exception):
    pass


class JsonProcess:
    def __init__(self, command, cwd, env, timeout):
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.messages = []
        self.writer = None
        self.queue = queue.Queue()
        self.process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, start_new_session=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        total = 0
        try:
            while True:
                line = self.process.stdout.readline(1024 * 1024 + 1)
                total += len(line)
                if not line:
                    break
                if len(line) > 1024 * 1024 or total > 8 * 1024 * 1024:
                    break
                try:
                    self.queue.put(json.loads(line))
                except ValueError:
                    continue
        finally:
            self.queue.put(None)

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError('process deadline exceeded')
        return remaining

    def send(self, row):
        self.remaining()
        body = (json.dumps(row) + '\n').encode('utf-8')
        if len(body) > 1024 * 1024:
            raise ProtocolError('input frame limit exceeded')
        errors = []

        def write():
            try:
                remaining = memoryview(body)
                while remaining:
                    written = os.write(self.process.stdin.fileno(), remaining)
                    if not written:
                        raise OSError('client input closed')
                    remaining = remaining[written:]
            except (OSError, ValueError) as error:
                errors.append(error)

        # Anonymous pipes cannot be selected portably on Windows. The owned
        # process is killed by close() on timeout, releasing a blocked writer.
        self.writer = threading.Thread(target=write, daemon=True)
        self.writer.start()
        self.writer.join(timeout=self.remaining())
        if self.writer.is_alive():
            raise ProtocolError('process deadline exceeded while sending')
        if errors:
            raise ProtocolError('client input closed or rejected') from errors[0]
        self.remaining()

    def receive(self, predicate, timeout=None):
        end = min(self.deadline, time.monotonic() + (self.remaining() if timeout is None else timeout))
        while time.monotonic() < end:
            try:
                row = self.queue.get(timeout=max(.01, end - time.monotonic()))
            except queue.Empty as error:
                raise ProtocolError('timeout') from error
            if row is None:
                raise ProtocolError('client exited or output limit exceeded')
            self.messages.append(row)
            if not isinstance(row, dict):
                raise ProtocolError('malformed protocol object')
            if predicate(row):
                return row
        raise ProtocolError('timeout')

    def call(self, ident, method, params):
        self.send(dict(id=ident, method=method, params=params))
        row = self.receive(lambda r: r.get('id') == ident)
        if 'error' in row:
            raise ProtocolError('native method unsupported or rejected')
        if not isinstance(row.get('result'), dict):
            raise ProtocolError('malformed method result')
        return row['result']

    def close(self):
        cleanup_deadline = max(self.deadline, time.monotonic()) + 1
        remaining = max(0, self.deadline - time.monotonic())
        try:
            os.killpg(self.process.pid, signal.SIGTERM if remaining else signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=min(3, remaining) if remaining else 1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Bounded reap is cleanup, not another execution allowance.
            self.process.wait(timeout=1)
        if self.writer is not None:
            self.writer.join(timeout=max(0, cleanup_deadline-time.monotonic()))
        self.reader.join(timeout=min(1, max(0, self.deadline-time.monotonic())))
        self.process.stdin.close()
        self.process.stdout.close()


def probe_environment(project, cache):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('PWF_') and k not in {'PLAN_ID', 'PLANNING_DISABLED', 'CLAUDE_PLUGIN_ROOT',
                                                    'CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT'}}
    env.update(PLAN_ID='account-doctor', PWF_PLAN_ROOT=str(project), XDG_CACHE_HOME=str(cache),
               PYTHONDONTWRITEBYTECODE='1')
    return env


def fixture(project):
    plan = project / '.planning/account-doctor'
    plan.mkdir(parents=True)
    (plan / 'task_plan.md').write_text('# ACCOUNT_DOCTOR_SELECTED_PLAN\n\n## Phase 1\nStatus: in_progress\n')
    (plan / 'progress.md').write_text('Synthetic setup verification only.\n')
    (plan / 'findings.md').write_text('No personal project data.\n')


def codex_checks(home, receipt, skills, project, env, timeout):
    rows = []
    process = JsonProcess(['codex', 'app-server', '--stdio'], project, env, timeout)
    try:
        process.call(1, 'initialize', dict(clientInfo=dict(name='account_doctor', version='1.0')))
        process.send(dict(method='initialized', params={}))
        data = process.call(2, 'skills/list', dict(cwds=[str(project)], forceReload=True))['data'][0]
        found = {x['name']: x for x in data['skills'] if x.get('enabled')}
        missing = [name for name in skills if name not in found or
                   Path(found[name]['path']).resolve() != home / BUNDLE / 'skills' / name / 'SKILL.md']
        rows.append(check('native.codex.skills', 'fail' if missing or data['errors'] else 'pass',
                          f'{len(skills) - len(missing)}/{len(skills)} skills resolve to the owned bundle; '
                          f'{len(data["errors"])} native discovery errors.',
                          'Inspect conflicting skill paths or client errors locally.' if missing or data['errors'] else ''))
        if not receipt['hooks'].get('.codex/hooks.json'):
            rows.append(check('native.codex.hooks', 'skipped', 'Planning hooks were not selected.'))
            return rows
        try:
            hooks = process.call(3, 'hooks/list', dict(cwds=[str(project)]))['data'][0]
        except ProtocolError:
            rows.append(check('native.codex.hooks', 'blocked', 'This Codex cannot expose effective hook trust.',
                              'Use /hooks in a supported Codex client; no trust bypass is performed.'))
            return rows
        expected = [(event[0].lower() + event[1:], h['command'])
                    for event, groups in receipt['hooks']['.codex/hooks.json'].items()
                    for group in groups for h in group['hooks']]
        bad, untrusted, disabled = 0, 0, 0
        for event, command in expected:
            matches = [h for h in hooks['hooks'] if h['eventName'] == event and h.get('command') == command
                       and Path(h['sourcePath']) == home / '.codex/hooks.json']
            if len(matches) != 1:
                bad += 1
                continue
            disabled += not matches[0]['enabled']
            untrusted += matches[0]['trustStatus'] not in ('trusted', 'managed')
        outcome = 'fail' if bad or disabled or hooks['errors'] else 'blocked' if untrusted else 'pass'
        rows.append(check('native.codex.hooks', outcome,
                          f'{len(expected)} owned hooks: {bad} missing/duplicate, {disabled} disabled, '
                          f'{untrusted} need trust review.',
                          'Open Codex /hooks and review/trust the installed definitions, then rerun doctor.'
                          if untrusted else 'Inspect /hooks for missing/disabled registrations.' if outcome == 'fail' else ''))
    finally:
        process.close()
    return rows


def claude_checks(home, receipt, skills, project, env, timeout):
    process = JsonProcess(['claude', '--print', '--input-format', 'stream-json', '--output-format', 'stream-json',
                           '--include-hook-events', '--verbose', '--no-session-persistence', '--tools', '',
                           '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--setting-sources', 'user'],
                          project, env, timeout)
    try:
        process.send(dict(type='control_request', request_id='account-doctor', request=dict(subtype='initialize')))
        response = process.receive(lambda r: r.get('type') == 'control_response')['response']
        if response.get('subtype') != 'success':
            raise ProtocolError('initialization rejected')
        found = {x['name'] for x in response['response']['commands']}
        missing = set(skills) - found
        rows = [check('native.claude.skills', 'fail' if missing else 'pass',
                      f'{len(skills) - len(missing)}/{len(skills)} native skill commands discovered; source paths checked offline.',
                      'Inspect /skills and client version locally.' if missing else '')]
        if not receipt['hooks'].get('.claude/settings.json'):
            rows.append(check('native.claude.session-start', 'skipped', 'Planning hooks were not selected.'))
            return rows
        def completed(row):
            return row.get('type') == 'system' and row.get('subtype') == 'hook_response' and row.get('hook_event') == 'SessionStart'
        matches = [r for r in process.messages if completed(r)]
        if not matches:
            try:
                matches = [process.receive(completed, min(timeout, 10))]
            except ProtocolError:
                pass
        valid = any(r.get('outcome') == 'success' and r.get('exit_code') == 0
                    and 'ACCOUNT_DOCTOR_SELECTED_PLAN' in (r.get('stdout', '') + r.get('output', '')) for r in matches)
        rows.append(check('native.claude.session-start', 'pass' if valid else 'blocked',
                          'Native SessionStart recovered the synthetic selected plan.' if valid
                          else 'Native selected-plan recovery was not observed.',
                          '' if valid else 'Inspect /hooks and the client version; direct script execution is not native proof.'))
        return rows
    finally:
        process.close()


def native_checks(home, receipt, skills, client, timeout):
    rows = []
    with tempfile.TemporaryDirectory(prefix='account-doctor-') as temp:
        project = Path(temp)
        fixture(project)
        env = probe_environment(project, project / 'cache')
        for host in ([client] if client else ['codex', 'claude']):
            try:
                rows.extend((codex_checks if host == 'codex' else claude_checks)(home, receipt, skills, project, env, timeout))
            except (ProtocolError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                rows.append(check('native.' + host, 'blocked', 'Native probe unavailable (' + type(error).__name__ + ').',
                                  'Check the installed client version, writable native state and host permissions.'))
    return rows
