#!/usr/bin/env python3
"""Fixed credential-free Codex remote-executor fixture; no live-provider API."""
import argparse
import base64
import datetime
import hashlib
import http.server
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid

try:
    from .native_execution_catalog import boundary_gate, catalog, gate
except ImportError:
    from native_execution_catalog import boundary_gate, catalog, gate

SOURCE = Path(__file__).resolve().parent
PIN = '83086188ae0614bd882818ff1aa23f3194962012'
MAX_BYTES = 262144
RESERVE = 8192


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


class Refusal(RuntimeError):
    pass


class Archive:
    """Exclusive private archive; cap covers stored events + reserved receipt bytes."""
    def __init__(self, path, limit):
        self.path = Path(path)
        self.path.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.limit = limit
        self.used = 0
        self.lock = threading.Lock()
        self.events = self.path/'events.jsonl'
        self.stream = self.events.open('xb')
        self.events.chmod(0o600)

    def record(self, kind, value):
        line = encoded({'kind': kind, 'value': value})
        with self.lock:
            if self.used+len(line) > self.limit-RESERVE:
                raise Refusal('archive_limit')
            self.stream.write(line)
            self.stream.flush()
            self.used += len(line)

    def raw(self, kind, payload):
        self.record(kind, {'base64': base64.b64encode(payload).decode()})

    def finish(self, receipt):
        with self.lock:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()
            receipt['archive'] = {'sha256': sha(self.events), 'event_bytes': self.used,
                'limit_bytes': self.limit, 'receipt_reserve_bytes': RESERVE,
                'denominator': 'Retained base64-framed protocol events plus final receipt; excludes HTTP headers, OS pipe buffers, removed temporary files and caller reports.'}
            raw = encoded(receipt)
            if len(raw) > RESERVE:
                # Preserve a durable, fail-closed receipt even if a future
                # summary field accidentally exceeds the reserved allowance.
                receipt = {'schema_version': 1, 'kind': 'native-remote-fixture',
                    'status': 'blocked', 'reason': 'receipt_summary_exceeded_reserve',
                    'attempt_id': str(receipt.get('attempt_id', 'unknown'))[:128],
                    'live_eligible': False, 'authentication_qualified': False,
                    'isolation_qualified': False, 'archive': receipt['archive'],
                    'oversized_summary_sha256': hashlib.sha256(raw).hexdigest(),
                    'cleanup': {'details': 'unknown; oversized summary refused'}}
                raw = encoded(receipt)
            path = self.path/'receipt.json'
            with path.open('xb') as stream:
                path.chmod(0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        return receipt


class Session:
    """One POSIX process group, nonblocking stdin/stdout/stderr, one deadline."""
    def __init__(self, argv, cwd, env, archive, deadline):
        self.archive, self.deadline = archive, deadline
        self.proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.buffer = bytearray()
        self.pending = []
        self.next_id = 0
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            os.set_blocking(stream.fileno(), False)
        for stream in (self.proc.stdout, self.proc.stderr):
            self.selector.register(stream, selectors.EVENT_READ)

    def pump(self):
        remaining = self.deadline-time.monotonic()
        if remaining <= 0:
            raise Refusal('deadline')
        for key, _ in self.selector.select(min(.05, remaining)):
            data = os.read(key.fd, 4096)
            if not data:
                self.selector.unregister(key.fileobj)
                if key.fileobj is self.proc.stdout and self.buffer:
                    raise Refusal('truncated_native_json')
                continue
            self.archive.raw('native_stdout' if key.fileobj is self.proc.stdout else 'native_stderr', data)
            if key.fileobj is self.proc.stdout:
                self.buffer.extend(data)
                while b'\n' in self.buffer:
                    raw, _, rest = self.buffer.partition(b'\n')
                    self.buffer = bytearray(rest)
                    try:
                        value = json.loads(raw)
                    except (ValueError, UnicodeError) as exc:
                        raise Refusal('malformed_native_json') from exc
                    if not isinstance(value, dict):
                        raise Refusal('malformed_native_message')
                    if 'method' in value and 'id' in value:
                        raise Refusal('unexpected_native_server_request')
                    self.pending.append(value)
        # Leave the Popen leader unreaped until close() signals its owned
        # process group, preventing reuse of that PID before killpg.
        if not self.selector.get_map() and not self.pending:
            raise Refusal('native_eof')

    def send(self, value):
        raw = encoded(value)
        self.archive.raw('native_stdin_attempt', raw)
        offset = 0
        while offset < len(raw):
            if time.monotonic() >= self.deadline:
                raise Refusal('deadline')
            try:
                offset += os.write(self.proc.stdin.fileno(), raw[offset:])
            except BlockingIOError:
                self.pump()
            except BrokenPipeError as exc:
                raise Refusal('native_stdin_closed') from exc

    def until(self, predicate):
        while True:
            for i, value in enumerate(self.pending):
                if predicate(value):
                    return self.pending.pop(i)
            self.pump()

    def rpc(self, method, params):
        self.next_id += 1
        identity = self.next_id
        self.send({'id': identity, 'method': method, 'params': params})
        value = self.until(lambda v: v.get('id') == identity)
        if 'error' in value or 'result' not in value:
            raise Refusal('native_rpc_error:'+method)
        return value['result']

    def close(self):
        # Group ownership comes from this Popen(start_new_session=True), never a receipt PID.
        signal_error = None
        signaled = False
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
            signaled = True
        except ProcessLookupError:
            pass
        except OSError as exc:
            # Some hosts refuse signaling an already-exited unreaped group.
            # Preserve that uncertainty, but still reap our own child and
            # close descriptors; never fall back to another PID/group.
            signal_error = type(exc).__name__+':'+str(exc)[:160]
        try:
            self.proc.wait(timeout=2)
            reaped = True
        except subprocess.TimeoutExpired:
            reaped = False
        self.selector.close()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            stream.close()
        return {'process_reaped': reaped, 'exit_code': self.proc.returncode,
                'owned_process_group_kill_sent': signaled,
                'group_signal_error': signal_error,
                'escaped_descendants_verified_absent': False}


def actual_outputs(request):
    for item in request.get('input', []):
        if item.get('type') in ('function_call_output', 'custom_tool_call_output'):
            value = item.get('output', [])
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                for part in value:
                    if isinstance(part, dict) and isinstance(part.get('text'), str):
                        yield part['text']


# Fixed remote task/result producer and one explicit child; local coordinator
# and scorer retain normal same-account access outside this execution boundary.
SCOPED_IO_EXPECTED = {actor: {
    'fixture_read': True, 'task_write_readback': True,
    'denied': {role: {'read_errno': 2, 'write_errno': 2, 'create_errno': 2}
               for role in ('grading', 'other_arm', 'installer_receipt', 'installer_journal')},
} for actor in ('direct', 'child')}
INSTALLER_CANARIES = (
    'account/.agents/agent-dotfiles/state/installed.json',
    'account/.agents/agent-dotfiles/state/transactions/synthetic/journal.json',
)

BOUNDARY_EXPECTED = {
    'catalog': {name: {'mask': 1023, 'count': 10, 'unknown': 0, 'duplicates': 0}
                for name in ('advertised', 'callable')},
    'globals_imports': {'globals_absent': True, 'imports_refused': 3},
    'mcp': {'resources_empty': True, 'templates_empty': True, 'foreign_server_refused': True},
    'command': {'fixture_read': True, 'protected_enoent': 5, 'traversal_enoent': True,
                'symlink_enoent': True, 'ipv4_tcp_errno': 101, 'ipv4_udp_errno': 101,
                'ipv6_tcp_errno': 101, 'ipv6_udp_errno': 101, 'root_write_errno': 30,
                'scoped_io': SCOPED_IO_EXPECTED},
    'skills': {'count': 1, 'body': True, 'reference': True,
               'foreign_refused': True, 'traversal_refused': True},
    'remaining': {'patch_refused': True, 'image_refused': True, 'stdin_refused': True},
}


def boundary_outputs(request):
    """Accept only unique closed records from the two exact issued call IDs.

    Script headers may surround native text blocks, but prompt/call source and
    outputs from a different call cannot satisfy a boundary predicate.
    """
    calls = {}
    for item in request.get('input', []):
        if not isinstance(item, dict) or item.get('type') not in ('function_call_output', 'custom_tool_call_output'):
            continue
        identity = item.get('call_id')
        if identity not in ('fixed_cell', 'disabled_agents') or identity in calls:
            raise Refusal('boundary_output_identity')
        expected_type = 'custom_tool_call_output' if identity == 'fixed_cell' else 'function_call_output'
        if item['type'] != expected_type:
            raise Refusal('boundary_output_type')
        output = item.get('output')
        if isinstance(output, str):
            calls[identity] = output.splitlines()
        elif isinstance(output, list) and output and all(isinstance(x, dict) and x.get('type') == 'input_text' and isinstance(x.get('text'), str) for x in output):
            calls[identity] = [line for x in output for line in x['text'].splitlines()]
        else:
            raise Refusal('boundary_output_shape')
    if set(calls) != {'fixed_cell', 'disabled_agents'} or calls['disabled_agents'] != ['unsupported call: collaborationlist_agents']:
        raise Refusal('boundary_dispatch_refusal_missing')
    if not calls['fixed_cell'] or calls['fixed_cell'][0] != 'Script completed':
        raise Refusal('boundary_cell_not_completed')
    checks = {}
    terminal = 0
    def unique(pairs):
        value = {}
        for key, entry in pairs:
            if key in value:
                raise Refusal('boundary_duplicate_json_key')
            value[key] = entry
        return value
    for line in calls['fixed_cell']:
        if line == 'BOUNDARY_COMPLETED':
            terminal += 1
        elif line.startswith('BOUNDARY_CHECK:'):
            value = json.loads(line[len('BOUNDARY_CHECK:'):], object_pairs_hook=unique)
            if not isinstance(value, dict) or set(value) != {'check', 'result'}:
                raise Refusal('boundary_record_shape')
            name = value['check']
            if not isinstance(name, str) or name not in BOUNDARY_EXPECTED or name in checks:
                raise Refusal('boundary_record_identity')
            # Canonical serialization deliberately distinguishes true from 1.
            if encoded(value['result']) != encoded(BOUNDARY_EXPECTED[name]):
                raise Refusal('boundary_predicate_failed:'+name)
            checks[name] = value['result']
    if terminal != 1 or set(checks) != set(BOUNDARY_EXPECTED):
        raise Refusal('boundary_evidence_missing')
    return checks


def loader_source(expected_script_bytes):
    """Render only the fixed loader; the owner binds the readonly ASCII file.

    A length check detects truncation, not content identity or OS immutability.
    No caller-provided JavaScript or filename is accepted. Remove only the final
    asset LF so the exact tool input has no ambiguous terminal newline.
    """
    if type(expected_script_bytes) is not int or not 1 <= expected_script_bytes <= 32768:
        raise ValueError('invalid_expected_script_bytes')
    return (SOURCE/'native_execution_loader.js').read_text().replace(
        'EXPECTED_SCRIPT_BYTES', str(expected_script_bytes)).removesuffix('\n')


def _fixture_scenario(scenario, expected_script_bytes):
    if scenario not in ('completion', 'command-skills-boundary', 'command-skills-loader'):
        raise ValueError('unsupported_fixture_scenario')
    if scenario == 'command-skills-loader':
        if type(expected_script_bytes) is not int or not 1 <= expected_script_bytes <= 32768:
            raise ValueError('invalid_expected_script_bytes')
    elif expected_script_bytes is not None:
        raise ValueError('unexpected_script_length')


class FixtureProvider:
    """Exactly one fixed tool cell then final message; no upstream or credential input."""
    def __init__(self, archive, deadline, host_uri, *, scenario='completion', expected_script_bytes=None):
        _fixture_scenario(scenario, expected_script_bytes)
        self.expected_script_bytes = expected_script_bytes
        self.scenario = scenario
        self.boundary_checks = None
        self.archive, self.deadline, self.host_uri = archive, deadline, host_uri
        self.requests = 0
        self.error = None
        self.completed = False
        self.lock = threading.Lock()
        self.servers = []
        self.threads = []
        self.connections = set()
        self.connection_lock = threading.Lock()
        self.closing = threading.Event()
        self.watchdog = None

    def response(self, raw):
        with self.lock:
            self.requests += 1  # Failed/rejected submissions remain in the denominator.
            self.archive.raw('mock_request', raw)
            if self.requests > 2:
                raise Refusal('mock_request_limit')
            data = json.loads(raw)
            if data.get('model') != 'gpt-6-luna' or data.get('stream') is not True:
                raise Refusal('unexpected_mock_model_or_stream')
            if any(marker in raw.decode() for marker in ('HOST_STARTUP_INSTRUCTION_CANARY', 'HOST_PROJECT_INSTRUCTION_CANARY')):
                raise Refusal('host_instruction_marker_exposed')
            (boundary_gate if self.scenario != 'completion' else gate)(catalog(data))
            if self.requests == 1:
                if self.scenario == 'command-skills-loader':
                    code = loader_source(self.expected_script_bytes)
                else:
                    cell = 'native_execution_command_skills.js' if self.scenario == 'command-skills-boundary' else 'native_execution_cell.js'
                    code = (SOURCE/cell).read_text().replace('HOST_URI', json.dumps(self.host_uri))
                items = [{'type': 'function_call', 'namespace': 'collaboration', 'name': 'list_agents',
                          'call_id': 'disabled_agents', 'arguments': '{}'},
                         {'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'fixed_cell', 'input': code}]
            else:
                if self.scenario != 'completion':
                    self.boundary_checks = boundary_outputs(data)
                else:
                    outputs = list(actual_outputs(data))
                    # Only actual returned tool output, never prompt/source-text matches.
                    if 'unsupported call: collaborationlist_agents' not in outputs or 'CELL1_COMPLETED' not in outputs:
                        raise Refusal('fixture_tool_output_missing')
                    checks = {}
                    for line in outputs:
                        if line.startswith('{'):
                            obj = json.loads(line)
                            if 'check' in obj:
                                checks[obj['check']] = obj['result']
                    for name, marker in [('assigned_body', 'ASSIGNED_REMOTE_SKILL_BODY'), ('assigned_reference', 'ASSIGNED_REMOTE_SKILL_REFERENCE')]:
                        if marker not in checks.get(name, {}).get('contents', ''):
                            raise Refusal('assigned_skill_evidence_missing')
                self.completed = True
                items = [{'id': 'done', 'type': 'message', 'role': 'assistant', 'status': 'completed',
                          'content': [{'type': 'output_text', 'text': 'REMOTE_FIXTURE_COMPLETE', 'annotations': []}]}]
            events = [{'type': 'response.created', 'response': {'id': 'fixture_'+str(self.requests)}}]
            events += [{'type': 'response.output_item.done', 'output_index': i, 'item': item} for i, item in enumerate(items)]
            events += [{'type': 'response.completed', 'response': {'id': 'fixture_'+str(self.requests), 'status': 'completed', 'output': items}}]
            body = ''.join('event: '+e['type']+'\ndata: '+json.dumps(e)+'\n\n' for e in events).encode()
            self.archive.raw('mock_response', body)
            return body

    def start(self):
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def setup(self):
                # This is before request-line/header parsing. The watchdog
                # also closes active sockets at the absolute deadline, so
                # dribbling bytes cannot renew the overall allowance.
                self.request.settimeout(max(.01, owner.deadline-time.monotonic()))
                super().setup()
            def do_POST(self):
                body = b''
                status = 400
                try:
                    length = int(self.headers.get('Content-Length', '-1'))
                    if self.path != '/v1/responses' or self.headers.get('Transfer-Encoding') or not 0 <= length <= MAX_BYTES:
                        raise Refusal('mock_http_shape')
                    if time.monotonic() >= owner.deadline:
                        raise Refusal('deadline')
                    raw = self.rfile.read(length)
                    if time.monotonic() >= owner.deadline or owner.closing.is_set():
                        raise Refusal('deadline')
                    if len(raw) != length:
                        raise Refusal('mock_truncated_body')
                    body = owner.response(raw)
                    status = 200
                except Exception as exc:
                    owner.error = type(exc).__name__+':'+str(exc)[:160]
                try:
                    self.send_response(status)
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Connection', 'close')
                    if status == 200:
                        self.send_header('Content-Type', 'text/event-stream')
                    self.end_headers()
                    if body:
                        self.wfile.write(body)
                except OSError:
                    pass  # Closed by deadline/cleanup; primary error retained.
                self.close_connection = True
            def do_GET(self):
                self.send_response(405)
                self.send_header('Content-Length', '0')
                self.end_headers()
        class Server(http.server.HTTPServer):
            timeout = .05
            def get_request(self):
                connection, address = super().get_request()
                with owner.connection_lock:
                    if owner.closing.is_set():
                        connection.close()
                        raise OSError('listener closing')
                    owner.connections.add(connection)
                return connection, address
            def close_request(self, request):
                try:
                    super().close_request(request)
                finally:
                    with owner.connection_lock:
                        owner.connections.discard(request)
            def handle_error(self, *args):
                owner.error = owner.error or 'mock_http_handler_error'
        class V6(Server):
            address_family = socket.AF_INET6
            def server_bind(self):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                super().server_bind()
        try:
            self.servers.append(Server(('127.0.0.1', 0), Handler))
            port = self.servers[0].server_port
            self.servers.append(V6(('::1', port), Handler))
            for server in self.servers:
                thread = threading.Thread(target=self.serve, args=(server,), daemon=True)
                thread.start()
                self.threads.append(thread)
            self.watchdog = threading.Thread(target=self.expire, daemon=True)
            self.watchdog.start()
            return port
        except Exception:
            self.close()
            raise

    def serve(self, server):
        while not self.closing.is_set():
            try:
                server.handle_request()
            except (OSError, ValueError):
                if not self.closing.is_set():
                    self.error = self.error or 'mock_listener_error'
                break

    def expire(self):
        if not self.closing.wait(max(0, self.deadline-time.monotonic())):
            self.error = self.error or 'deadline'
            self.stop_connections()

    def stop_connections(self):
        self.closing.set()
        with self.connection_lock:
            for connection in self.connections:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()

    def close(self):
        # Never call HTTPServer.shutdown(): a stalled handler can make that
        # call wait forever. Close active sockets and bound all thread joins.
        self.stop_connections()
        for server in self.servers:
            server.server_close()
        deadline = time.monotonic()+1
        threads = self.threads+([self.watchdog] if self.watchdog else [])
        for thread in threads:
            thread.join(max(0, deadline-time.monotonic()))
        return all(not thread.is_alive() for thread in threads)


PROFILE = '''model="gpt-6-luna"
model_reasoning_effort="low"
model_provider="fixture"
approval_policy="never"
web_search="disabled"
check_for_update_on_startup=false
cli_auth_credentials_store="file"
[features]
image_generation=false
apps=false
plugins=false
memories=false
multi_agent=false
multi_agent_v2=false
code_mode=false
code_mode_host=true
goals=false
[agents]
enabled=false
[model_providers.fixture]
name="Synthetic fixture"
base_url="http://127.0.0.1:PORT/v1"
wire_api="responses"
requires_openai_auth=false
supports_websockets=false
request_max_retries=0
stream_max_retries=0
stream_idle_timeout_ms=10000
'''


def run_fixture(destination, command, executor, *, timeout=30, limit=MAX_BYTES, scenario='completion',
                expected_script_bytes=None, session_factory=None, defer_temporary_cleanup=False,
                on_temporary_root=None):
    """Trusted caller supplies exact executable argv; this does not create an OS boundary.

    No endpoint/auth overrides, retries, installation, containers or VM lifecycle.
    Caller owns executor isolation and independently verified escaped-child cleanup.
    Trusted Python-only session_factory uses Session's positional constructor
    contract and must retain ownership before a failing launch. Deferred cleanup
    retains the fixture root for that owner; mock_complete alone never proves
    external cleanup. on_temporary_root captures ownership immediately after
    fresh-root creation, before provider setup or native launch. These trusted
    extensions cannot be supplied through the JSON CLI.
    """
    if os.name != 'posix' or not 0 < timeout <= 180 or type(limit) is not int or not RESERVE+4096 <= limit <= MAX_BYTES:
        raise ValueError('unsupported_platform_or_bounds')
    _fixture_scenario(scenario, expected_script_bytes)
    if session_factory is not None and not callable(session_factory):
        raise ValueError('invalid_session_factory')
    if type(defer_temporary_cleanup) is not bool:
        raise ValueError('invalid_deferred_cleanup')
    if on_temporary_root is not None and not callable(on_temporary_root):
        raise ValueError('invalid_temporary_root_callback')
    for argv in (command, executor):
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and '\x00' not in x for x in argv):
            raise ValueError('invalid_argv')
        if not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file():
            raise ValueError('absolute_executable_required')
    identities = {'host_executable_sha256': sha(command[0]), 'executor_program_sha256': sha(executor[0]),
                  'runner_sha256': sha(__file__), 'catalog_sha256': sha(SOURCE/'native_execution_catalog.py'),
                  'cell_sha256': sha(SOURCE/({'completion': 'native_execution_cell.js',
                    'command-skills-boundary': 'native_execution_command_skills.js',
                    'command-skills-loader': 'native_execution_loader.js'}[scenario]))}
    if scenario == 'command-skills-loader':
        identities['rendered_cell_sha256'] = hashlib.sha256(loader_source(expected_script_bytes).encode()).hexdigest()
    archive = Archive(destination, limit)
    start = time.monotonic()
    deadline = start+timeout
    session = provider = None
    temporary = None
    protected = {}
    receipt = {'schema_version': 1, 'kind': 'native-remote-fixture', 'status': 'blocked',
        'attempt_id': str(uuid.uuid4()),
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reason': None, 'live_eligible': False, 'authentication_qualified': False,
        'isolation_qualified': False, 'source_revision': PIN,
        'model': {'declared': 'gpt-6-luna', 'reasoning': 'low', 'actual_inference': False},
        'identities': identities,
        'limits': {'wall_seconds': timeout, 'mock_submissions': 2, 'archive_bytes': limit,
                   'generated_token_ceiling': None, 'dollar_ceiling': None},
        'usage': {'tokens': None, 'reason': 'Synthetic provider; no actual inference or real usage.'},
        'cleanup': {'executor_resources': 'external_owner_unverified', 'escaped_descendants': 'unverified'}}
    if scenario != 'completion':
        receipt['scenario'] = scenario
        receipt['boundary_checks'] = None
    if scenario == 'command-skills-loader':
        receipt['expected_script_bytes'] = expected_script_bytes
        receipt['protected_canary_scope'] = 'inner_fixture_only_outer_owner_required'
        receipt['outer_protected_canaries_verified'] = False
    try:
        temporary = Path(tempfile.mkdtemp(prefix='native-fixture-')).resolve()
        if on_temporary_root is not None:
            on_temporary_root(temporary)
        root = temporary
        home = root/'home'
        project = root/'project'
        codehome = home/'.codex'
        codehome.mkdir(parents=True, mode=0o700)
        project.mkdir(mode=0o700)
        (home/'AGENTS.md').write_text('HOST_STARTUP_INSTRUCTION_CANARY\n')
        (project/'AGENTS.md').write_text('HOST_PROJECT_INSTRUCTION_CANARY\n')
        sentinel = root/'host-only'
        sentinel.write_text('synthetic host-only canary')
        protected = {}
        if scenario != 'completion':
            for name in ('history-only', 'credential-only', 'other-arm-only', 'evaluator-only', *INSTALLER_CANARIES):
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('synthetic protected canary')
            # Valid one-pixel PNG, not a malformed-image denial probe.
            (root/'host-only.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYPgPAAEDAQAIicLsAAAAAElFTkSuQmCC'))
            for name in ('host-only', 'history-only', 'credential-only', 'other-arm-only', 'evaluator-only', 'host-only.png', *INSTALLER_CANARIES):
                path = root/name
                info = path.stat()
                protected[path] = (path.read_bytes(), info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)
        provider = FixtureProvider(archive, deadline, sentinel.as_uri(), scenario=scenario,
                                   expected_script_bytes=expected_script_bytes)
        port = provider.start()
        profile = PROFILE.replace('PORT', str(port))
        environments = 'default="trial"\ninclude_local=false\n[[environments]]\nid="trial"\nprogram='+json.dumps(executor[0])+'\nargs='+json.dumps(executor[1:])+'\n'
        (codehome/'config.toml').write_text(profile)
        (codehome/'environments.toml').write_text(environments)
        archive.record('launch', {'command': command, 'executor': executor,
            'profile': profile, 'environments': environments})
        receipt['identities']['profile_sha256'] = hashlib.sha256(profile.encode()).hexdigest()
        receipt['identities']['environments_sha256'] = hashlib.sha256(environments.encode()).hexdigest()
        env = {'HOME': str(home), 'CODEX_HOME': str(codehome), 'LANG': 'C.UTF-8',
               'PATH': str(Path(command[0]).parent)+':/usr/bin:/bin'}
        factory = Session if session_factory is None else session_factory
        session = factory(command, project, env, archive, deadline)
        session.rpc('initialize', {'clientInfo': {'name': 'remote_fixture', 'version': '1'}, 'capabilities': {'experimentalApi': True}})
        session.send({'method': 'initialized', 'params': {}})
        hooks = session.rpc('hooks/list', {'cwds': [str(project)]})
        if any(d.get('hooks') or d.get('errors') for d in hooks['data']):
            raise Refusal('host_hooks_not_empty')
        skills = session.rpc('skills/list', {'cwds': [str(project)], 'forceReload': True})
        for row in skills['data']:
            for skill in row['skills']:
                path = Path(skill['path']).resolve()
                if not path.is_relative_to(codehome):
                    raise Refusal('unexpected_host_skill_path')
                session.rpc('skills/config/write', {'path': str(path), 'enabled': False})
        skills = session.rpc('skills/list', {'cwds': [str(project)], 'forceReload': True})
        if any(s['enabled'] for row in skills['data'] for s in row['skills']):
            raise Refusal('host_skill_enabled')
        thread = session.rpc('thread/start', {'model': 'gpt-6-luna', 'cwd': str(project), 'approvalPolicy': 'never',
            'ephemeral': True, 'environments': [{'environmentId': 'trial', 'cwd': '/work/project', 'runtimeWorkspaceRoots': ['/work/project']}],
            'selectedCapabilityRoots': [{'id': 'assigned', 'location': {'type': 'environment', 'environmentId': 'trial', 'path': '/runtime/arm' if scenario != 'completion' else '/work/project/assigned-capability'}}]})['thread']['id']
        mcp = session.rpc('mcpServerStatus/list', {'threadId': thread, 'detail': 'full', 'limit': 10})
        if mcp['data'] or mcp.get('nextCursor'):
            raise Refusal('host_mcp_not_empty')
        turn = session.rpc('turn/start', {'threadId': thread, 'input': [{'type': 'text', 'text': 'Execute the fixed synthetic fixture.'}],
            'sandboxPolicy': {'type': 'externalSandbox', 'networkAccess': 'restricted'}, 'approvalPolicy': 'never'})['turn']['id']
        terminal = session.until(lambda x: x.get('method') == 'turn/completed')
        archive.record('terminal', terminal)
        t = terminal['params']['turn']
        if terminal['params']['threadId'] != thread or t['id'] != turn:
            raise Refusal('terminal_identity_mismatch')
        error = t.get('error')
        receipt['terminal'] = {'status': str(t['status'])[:64],
            'thread_id': str(thread)[:128], 'turn_id': str(turn)[:128],
            'error': None if error is None else {'preview': encoded(error).decode()[:160],
                'sha256': hashlib.sha256(encoded(error)).hexdigest()},
            'sha256': hashlib.sha256(encoded(terminal)).hexdigest(),
            'full_value': 'retained in events.jsonl'}
        if t['status'] != 'completed' or t.get('error') or not provider.completed or provider.error:
            raise Refusal('native_or_fixture_incomplete')
        if sentinel.read_text() != 'synthetic host-only canary':
            raise Refusal('host_canary_changed')
        if scenario != 'completion':
            receipt['boundary_checks'] = provider.boundary_checks
        receipt['status'] = 'mock_complete'
    except (Exception, KeyboardInterrupt) as exc:
        receipt['reason'] = type(exc).__name__+':'+str(exc)[:240]
    finally:
        safe_to_remove = session is None
        if session:
            try:
                receipt['cleanup']['harness'] = session.close()
                safe_to_remove = receipt['cleanup']['harness']['process_reaped'] and not receipt['cleanup']['harness'].get('group_signal_error')
            except Exception as exc:
                receipt['cleanup']['harness_error'] = type(exc).__name__+':'+str(exc)[:160]
        if provider:
            try:
                receipt['cleanup']['listeners_closed'] = provider.close()
            except Exception as exc:
                receipt['cleanup']['listener_error'] = type(exc).__name__+':'+str(exc)[:160]
                receipt['cleanup']['listeners_closed'] = False
            # Snapshot final state after handlers are stopped, not at terminal
            # arrival: late excess submissions must invalidate earlier success.
            receipt['mock_submissions_observed'] = provider.requests
            receipt['provider_error'] = provider.error
            if provider.error or provider.requests != 2 or not provider.completed:
                receipt['status'] = 'blocked'
                receipt['reason'] = receipt['reason'] or 'final_mock_protocol_incomplete'
            safe_to_remove = safe_to_remove and receipt['cleanup']['listeners_closed']
        else:
            receipt['mock_submissions_observed'] = 0
        if scenario != 'completion':
            # Check after owned process/listener shutdown, before deleting our
            # fixtures. A terminal event cannot hide a subsequent mutation.
            try:
                unchanged = len(protected) == 6 + len(INSTALLER_CANARIES) and all(
                    not path.is_symlink() and path.read_bytes() == value
                    and (path.stat().st_ino, path.stat().st_mode, path.stat().st_mtime_ns, path.stat().st_ctime_ns)
                        == (inode, mode, mtime, ctime)
                    for path, (value, inode, mode, mtime, ctime) in protected.items())
                unchanged = unchanged and all(not Path(str(path)+'.new').exists()
                    and not Path(str(path)+'.new').is_symlink() for path in protected)
            except OSError:
                unchanged = False
            receipt['protected_canaries_unchanged'] = unchanged
            if not unchanged:
                receipt['status'] = 'blocked'
                receipt['reason'] = receipt['reason'] or 'protected_canary_changed'
        if temporary:
            if defer_temporary_cleanup:
                receipt['cleanup']['temporary_cleanup_deferred'] = True
                receipt['cleanup']['external_cleanup_pending'] = True
            if safe_to_remove and not defer_temporary_cleanup:
                try:
                    shutil.rmtree(temporary)
                except Exception as exc:
                    receipt['cleanup']['temporary_error'] = type(exc).__name__+':'+str(exc)[:160]
            receipt['cleanup']['temporary_home_absent'] = not temporary.exists()
            if temporary.exists():
                receipt['cleanup']['retained_temporary_root'] = str(temporary)
        if not safe_to_remove or receipt['cleanup'].get('harness', {}).get('group_signal_error') or receipt['cleanup'].get('listeners_closed') is False or (not defer_temporary_cleanup and receipt['cleanup'].get('temporary_home_absent') is False):
            receipt['status'] = 'blocked'
            receipt['reason'] = receipt['reason'] or 'owned_cleanup_incomplete'
        receipt['elapsed_seconds'] = round(time.monotonic()-start, 6)
    return archive.finish(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path, help='Private JSON with command and executor argv; never credentials')
    parser.add_argument('--output', required=True, type=Path, help='New exclusive private evidence directory')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if set(plan)-{'command', 'executor', 'timeout', 'limit', 'scenario', 'expected_script_bytes'}:
        parser.error('Unknown plan fields; live/auth/provider overrides are unsupported')
    result = run_fixture(args.output, **plan)
    print(json.dumps({'status': result['status'], 'live_eligible': False, 'reason': result['reason']}))
    return 0 if result['status'] == 'mock_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
