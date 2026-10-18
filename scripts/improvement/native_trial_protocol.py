"""Bounded, nonpersistent native protocol observation for selected trials.

The caller owns authentication, source/profile release and resource cleanup.
These app-server observations do not authorize evaluator admission or prove
backend model identity, provider billing, or a hard token/request limit.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

from native_execution import Refusal, Session, encoded
from native_usage import Usage

FRAME_LIMIT = 65536
STREAM_LIMIT = 1048576


class CounterArchive:
    """Count observed native bytes without retaining values, hashes or previews."""
    def __init__(self):
        self.total = 0
        self.counts = dict.fromkeys(('native_stdout', 'native_stderr', 'native_stdin_attempt'), 0)

    def raw(self, kind, payload):
        if kind not in self.counts:
            raise Refusal('stream_kind')
        self.counts[kind] += len(payload)
        self.total += len(payload)
        if self.total > STREAM_LIMIT:
            raise Refusal('stream_limit')

    def summary(self):
        return {'counted_bytes': self.total, 'byte_counts': dict(self.counts),
                'byte_threshold': STREAM_LIMIT, 'incoming_read_overshoot_bound': 4096,
                'raw_contents_retained': False, 'raw_content_hashes_retained': False,
                'denominator': 'Observed native stdout/stderr and attempted outgoing JSON-RPC frames; OS buffers excluded.'}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal('duplicate_json_key')
        result[key] = value
    return result


class NativeSession(Session):
    """Existing owned Popen/stdio lifecycle with strict nonpersistent parsing."""
    def __init__(self, archive, deadline):
        # Construct before spawning so the owner retains this object even when
        # launch journaling or descriptor registration fails after Popen.
        self.archive, self.deadline = archive, deadline
        self.proc = None
        self.selector = selectors.DefaultSelector()
        self.buffer = bytearray()
        self.pending = []
        self.next_id = 0
        self.close_result = None

    def start(self, argv, cwd, env, on_launch):
        if self.proc is not None or self.close_result is not None:
            raise Refusal('native_already_started')
        if time.monotonic() >= self.deadline:
            raise Refusal('deadline')
        self.proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True, start_new_session=True)
        on_launch(self.proc.pid)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            os.set_blocking(stream.fileno(), False)
        for stream in (self.proc.stdout, self.proc.stderr):
            self.selector.register(stream, selectors.EVENT_READ)

    def close(self):
        if self.close_result is not None:
            return dict(self.close_result)
        if self.proc is None:
            self.selector.close()
            self.close_result = {'process_reaped': True, 'group_signal_error': None,
                                 'owned_process_group_kill_sent': False,
                                 'escaped_descendants': 'unverified'}
        else:
            self.close_result = super().close()
        return dict(self.close_result)

    def send(self, value):
        raw = encoded(value)
        if len(raw) > FRAME_LIMIT:
            raise Refusal('outbound_frame_limit')
        if self.archive.total + len(raw) > STREAM_LIMIT:
            raise Refusal('stream_limit')
        return super().send(value)

    def pump(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Refusal('deadline')
        for key, _ in self.selector.select(min(.05, remaining)):
            block = os.read(key.fd, 4096)
            if not block:
                self.selector.unregister(key.fileobj)
                if key.fileobj is self.proc.stdout and self.buffer:
                    raise Refusal('truncated_native_json')
                continue
            self.archive.raw('native_stdout' if key.fileobj is self.proc.stdout else 'native_stderr', block)
            if key.fileobj is not self.proc.stdout:
                continue
            self.buffer.extend(block)
            while b'\n' in self.buffer:
                raw, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                if len(raw) > FRAME_LIMIT:
                    raise Refusal('frame_limit')
                try:
                    value = json.loads(raw, object_pairs_hook=unique,
                                       parse_constant=lambda _: (_ for _ in ()).throw(Refusal('invalid_number')))
                except (ValueError, UnicodeError, RecursionError):
                    raise Refusal('malformed_native_json') from None
                if not isinstance(value, dict):
                    raise Refusal('malformed_native_message')
                if 'method' in value and 'id' in value:
                    raise Refusal('unexpected_native_server_request')
                if 'id' in value and type(value['id']) is not int:
                    raise Refusal('native_response_identity')
                self.pending.append(value)
            if len(self.buffer) > FRAME_LIMIT:
                raise Refusal('frame_limit')
        if not self.selector.get_map() and not self.pending:
            raise Refusal('native_eof')


SAFE_REASONS = frozenset((
    'auth_mode', 'hooks_not_empty', 'skills_error', 'skill_path', 'host_skill_enabled',
    'selected_model', 'mcp_not_empty', 'model_tool_contract', 'usage_identity',
    'usage_shape', 'usage_unavailable', 'usage_discontinuity', 'usage_retention_limit',
    'usage_persistence_failed', 'model_rerouted', 'terminal_identity', 'terminal_failed',
    'deadline', 'frame_limit', 'outbound_frame_limit', 'stream_limit', 'native_eof',
    'unexpected_native_server_request', 'malformed_native_json', 'duplicate_json_key',
    'invalid_number', 'truncated_native_json', 'malformed_native_message',
    'native_stdin_closed', 'native_response_identity', 'tool_observation',
    'thread_identity', 'turn_identity',
))


def native_id(value):
    return isinstance(value, str) and 0 < len(value) <= 256 \
        and not any(ord(char) < 33 for char in value)


def discovery_row(value, project, kind):
    """Pinned handlers return one row for each requested cwd, even if empty."""
    reason = 'hooks_not_empty' if kind == 'hooks' else 'skills_error'
    data = value.get('data') if isinstance(value, dict) else None
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise Refusal(reason)
    row = data[0]
    if row.get('cwd') != project or not isinstance(row.get(kind), list) \
            or not isinstance(row.get('errors'), list) or row['errors']:
        raise Refusal(reason)
    if kind == 'hooks':
        if not isinstance(row.get('warnings'), list) or row['warnings'] or row['hooks']:
            raise Refusal(reason)
    elif len(row['skills']) > 128:
        raise Refusal(reason)
    return row


def host_skills(value, project, codehome):
    skills = discovery_row(value, project, 'skills')['skills']
    seen = set()
    for skill in skills:
        if not isinstance(skill, dict) or any(not isinstance(skill.get(k), str)
                                              for k in ('name', 'description', 'path', 'scope')) \
                or type(skill.get('enabled')) is not bool:
            raise Refusal('skills_error')
        path = Path(skill['path'])
        if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(codehome):
            raise Refusal('skill_path')
        if str(path) in seen:
            raise Refusal('skills_error')
        seen.add(str(path))
    return skills


def observe(session, *, prompt, project, codehome, metadata_check,
            soft_total, soft_output, usage_sink=None, event_observer=None):
    """Observe one initial turn within the caller's original session deadline.

    event_observer is a trusted fixed qualification projector, not case code.
    It must not persist arbitrary event contents. Its observations occur after
    native dispatch; this callback is not a preventive tool-approval mechanism.
    """
    usage = Usage(soft_total=soft_total, soft_output=soft_output, sink=usage_sink)
    stopping = None
    result = {'status': 'blocked', 'reason': None, 'initial_turn_requests_attempted': 0,
              'initial_turns': 0, 'interrupt_attempted': False, 'terminal_completed': False,
              'auth_chatgpt_observed': False, 'model_requested': 'gpt-6-luna',
              'reasoning_requested': 'low', 'model_identity_verified': False,
              'wire_attempt_count': None, 'billing_usage': None,
              'hard_token_ceiling_enforced': False, 'live_eligible': False,
              'final_answer_count': 0}
    try:
        session.rpc('initialize', {'clientInfo': {'name': 'frozen_native_trial', 'version': '1'},
                                   'capabilities': {'experimentalApi': True}})
        session.send({'method': 'initialized', 'params': {}})
        account = session.rpc('account/read', {'refreshToken': False})
        if not isinstance(account.get('account'), dict) or account['account'].get('type') != 'chatgpt' \
                or account.get('requiresOpenaiAuth') is not True:
            raise Refusal('auth_mode')
        result['auth_chatgpt_observed'] = True
        hooks = session.rpc('hooks/list', {'cwds': [project]})
        discovery_row(hooks, project, 'hooks')
        skills = session.rpc('skills/list', {'cwds': [project], 'forceReload': True})
        for skill in host_skills(skills, project, codehome):
            session.rpc('skills/config/write', {'path': skill['path'], 'enabled': False})
        skills = session.rpc('skills/list', {'cwds': [project], 'forceReload': True})
        if any(skill['enabled'] for skill in host_skills(skills, project, codehome)):
            raise Refusal('host_skill_enabled')
        started = session.rpc('thread/start', {
            'model': 'gpt-6-luna', 'cwd': project, 'approvalPolicy': 'never',
            'ephemeral': True, 'experimentalRawEvents': True,
            'environments': [{'environmentId': 'trial', 'cwd': '/work/project',
                              'runtimeWorkspaceRoots': ['/work/project']}],
            'selectedCapabilityRoots': [{'id': 'selected-arm', 'location': {
                'type': 'environment', 'environmentId': 'trial', 'path': '/runtime/arm'}}],
        })
        if started.get('model') != 'gpt-6-luna':
            raise Refusal('selected_model')
        thread = started.get('thread', {}).get('id')
        if not native_id(thread):
            raise Refusal('thread_identity')
        metadata = metadata_check()
        result['model_metadata'] = metadata
        if metadata.get('status') != 'recognized' or metadata.get('compatibility_match') is not True:
            raise Refusal('model_tool_contract')
        mcp = session.rpc('mcpServerStatus/list', {'threadId': thread, 'detail': 'full', 'limit': 10})
        if not isinstance(mcp, dict) or mcp.get('data') != [] \
                or 'nextCursor' not in mcp or mcp['nextCursor'] is not None:
            raise Refusal('mcp_not_empty')
        result['initial_turn_requests_attempted'] = 1
        started_turn = session.rpc('turn/start', {
            'threadId': thread, 'input': [{'type': 'text', 'text': prompt}],
            'sandboxPolicy': {'type': 'externalSandbox', 'networkAccess': 'restricted'},
            'approvalPolicy': 'never',
        })
        turn = started_turn.get('turn', {}).get('id')
        if not native_id(turn):
            raise Refusal('turn_identity')
        result['initial_turns'] = 1
        while True:
            event = session.until(lambda value: 'method' in value)
            method = event['method']
            params = event.get('params', {})
            if event_observer is not None:
                try:
                    event_observer.accept(event, thread, turn)
                except Exception:
                    raise Refusal('tool_observation') from None
            if method == 'thread/tokenUsage/updated':
                if params.get('threadId') != thread or params.get('turnId') != turn:
                    raise Refusal('usage_identity')
                reason = usage.accept(params.get('tokenUsage'))
                if reason and stopping is None:
                    stopping = reason
                    result['reason'] = reason
                    result['interrupt_attempted'] = True
                    try:
                        session.rpc('turn/interrupt', {'threadId': thread, 'turnId': turn})
                    except Exception:
                        result['interrupt_acknowledged'] = False
                    else:
                        result['interrupt_acknowledged'] = True
                if reason and reason != 'soft_usage_stop':
                    if reason != stopping:
                        result['post_stop_observation'] = reason
                    return result
            elif method == 'model/rerouted':
                raise Refusal('model_rerouted')
            elif method == 'item/completed':
                item = params.get('item', {})
                if params.get('threadId') == thread and params.get('turnId') == turn \
                        and item.get('type') == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
                    result['final_answer_count'] += 1
            elif method == 'turn/completed':
                terminal = params['turn']
                if params.get('threadId') != thread or terminal['id'] != turn:
                    raise Refusal('terminal_identity')
                result['terminal_completed'] = terminal.get('status') == 'completed' and terminal.get('error') is None
                if stopping:
                    return result
                if not result['terminal_completed']:
                    raise Refusal('terminal_failed')
                if usage.latest is None:
                    raise Refusal('usage_unavailable')
                result['status'] = 'completed_ungraded'
                return result
    except Refusal as exc:
        reason = str(exc)
        reason = reason if reason in SAFE_REASONS else 'protocol_refusal'
        result['post_stop_observation' if stopping else 'reason'] = reason
    except TimeoutError:
        result['post_stop_observation' if stopping else 'reason'] = 'deadline'
    except Exception:
        result['post_stop_observation' if stopping else 'reason'] = 'protocol_operation'
    finally:
        result['usage'] = usage.summary()
    return result
