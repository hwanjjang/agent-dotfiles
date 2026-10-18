"""Bounded, nonpersistent native protocol observation for selected trials.

The caller owns authentication, source/profile release and resource cleanup.
These app-server observations do not authorize evaluator admission or prove
backend model identity, provider billing, or a hard token/request limit.
"""
import json
import os
from pathlib import Path
import selectors
import signal
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


class RoutingObserver:
    """Lossy native first-page metadata; no producer audit or outcome inference."""
    def __init__(self, routing, profile_digest):
        self.catalog = {row['name']: row['slot'] for row in routing['catalog']}
        self.digest, self.profile = routing['catalog_digest'], profile_digest
        self.mode = routing['mode']
        self.buffer, self.waiting = bytearray(), []
        self.scope = None
        self.reason = None
        self.bytes = self.frames = self.events = self.ignored = self.health = self.explicit = 0
        self.reads = {}

    def fail(self, reason):
        self.reason = self.reason or reason

    def bind(self, thread, turn):
        if self.scope not in (None, (thread, turn)):
            self.fail('routing_identity')
        self.scope = (thread, turn)
        for row in self.waiting:
            self._accept(row)
        self.waiting.clear()

    def _accept(self, row):
        event, thread, turn, name, invocation = row
        if thread != self.scope[0] or (event != 'codex.user_prompt' and turn != self.scope[1]):
            self.fail('routing_identity')
        elif event == 'codex.user_prompt':
            self.health += 1
            if self.health != 1:
                self.fail('routing_health')
        elif name not in self.catalog or invocation not in ('implicit', 'explicit'):
            self.fail('routing_catalog')
        elif invocation == 'explicit':
            self.explicit += 1
            if self.mode == 'natural':
                self.fail('routing_explicit')
        else:
            slot = self.catalog[name]
            self.reads[slot] = self.reads.get(slot, 0) + 1

    def feed(self, block):
        self.bytes += len(block)
        if self.reason:
            return
        self.buffer.extend(block)
        try:
            while b'\n' in self.buffer:
                raw, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                if len(raw) > FRAME_LIMIT:
                    raise ValueError()
                value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                if not isinstance(value, dict):
                    raise ValueError()
                self.frames += 1
                fields = value.get('fields', {})
                if not isinstance(fields, dict):
                    raise ValueError()
                event = fields.get('event.name')
                if value.get('target') != 'codex_otel.log_only' or event not in (
                        'codex.user_prompt', 'codex.skill_invocation'):
                    self.ignored += 1
                    continue
                if value.get('level') != 'INFO':
                    raise ValueError()
                self.events += 1
                if self.events > 128:
                    self.fail('routing_limit')
                    break
                row = (event, fields.get('conversation.id'), fields.get('turn.id'),
                       fields.get('skill.name'), fields.get('skill.invocation_type'))
                if self.scope is None:
                    self.waiting.append(row)
                else:
                    self._accept(row)
            if len(self.buffer) > FRAME_LIMIT:
                self.fail('routing_limit')
        except (ValueError, Refusal, UnicodeError, RecursionError, TypeError):
            self.fail('routing_json')
        if self.reason:
            self.buffer.clear()
            self.waiting.clear()

    def finish(self, ready, transport):
        transport = {k: transport.get(k) for k in (
            'stdout_eof', 'stderr_eof', 'process_reaped', 'trailing_bytes', 'pending_records', 'close_mode')} \
            if isinstance(transport, dict) else {}
        complete = transport.get('close_mode') in ('graceful_stdin_eof', 'post_terminal_kill_drained') and all(transport.get(k) is True
            for k in ('stdout_eof', 'stderr_eof', 'process_reaped')) \
            and transport.get('trailing_bytes') == 0 and transport.get('pending_records') == 0 \
            and not self.buffer and not self.waiting
        reason = self.reason or ('routing_health' if self.health != 1 or self.scope is None else
                                 None if ready and complete else 'routing_incomplete')
        return {'version': 1, 'mode': self.mode, 'status': 'blocked' if reason else 'observed',
            'reason': reason, 'catalog_digest': self.digest, 'observer_profile_digest': self.profile,
            'activation': 'unknown' if reason else 'implicit_main_first_page_read' if self.reads
                          else 'observed_none_in_declared_catalog',
            'implicit_reads': [{'slot': k, 'count': v} for k, v in sorted(self.reads.items())],
            'explicit_count': self.explicit, 'health': {'user_prompt_seen': self.health == 1,
                'scope': 'single_initial_turn_thread'},
            'correlation': {'thread_matched': self.scope is not None,
                            'turn_matched': self.scope is not None},
            'transport': {**(transport or {}), 'stderr_bytes': self.bytes, 'stderr_frames': self.frames,
                'accepted_events': self.events, 'ignored_records': self.ignored,
                'projected_records_written': 0, 'receiver_complete': complete,
                'native_written_count': None},
            'evidence_scope': 'receiver_complete_under_trusted_io', 'qualification': 'pending',
            'all_pages_verified': False, 'process_adherence': 'not_assessed', 'outcome': 'not_graded'}


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
        self.routing = None
        self.eof = set()
        self._turn_context = None

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
        elif self.routing is None:
            self.close_result = super().close()
        else:
            self.close_result = self._drain_close()
        return dict(self.close_result)

    def _drain_close(self):
        """Drain opened pipes within cleanup; never restart the observation turn."""
        end = min(time.monotonic()+2, getattr(self, 'cleanup_deadline', float('inf')))
        grace = min(end, time.monotonic()+.5)
        signaled = attempted = grace_expired = False
        signal_error = None

        def signal_owned_group():
            nonlocal signaled, attempted, signal_error
            if attempted:
                return
            attempted = True
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
                signaled = True
            except ProcessLookupError:
                pass
            except OSError:
                signal_error = 'signal_failed'
                self.routing.fail('routing_drain')

        self.deadline = end
        try:
            self.proc.stdin.close()
            # EOF does not establish descendant absence. Never poll/reap this
            # owned leader until its original process group has been signaled.
            while time.monotonic() < end and (self.selector.get_map() or self.pending):
                if time.monotonic() >= grace:
                    grace_expired = True
                    signal_owned_group()
                try:
                    self.pump()
                except Refusal as exc:
                    if str(exc) != 'native_eof' or self.selector.get_map() or self.buffer:
                        raise
                while self.pending:
                    if time.monotonic() >= end:
                        raise Refusal('deadline')
                    event = self.pending.pop(0)
                    if 'method' not in event:
                        raise Refusal('native_response_identity')
                    if self._turn_context is None:
                        raise Refusal('terminal_identity')
                    accept_event(self, event, late=True)
        except (OSError, ValueError, Refusal, TimeoutError, KeyError, TypeError) as exc:
            if self._turn_context is not None:
                result, usage, *_ = self._turn_context
                reason = str(exc) if isinstance(exc, Refusal) and str(exc) in SAFE_REASONS else 'protocol_operation'
                result['status'] = 'blocked'
                if result.get('reason') != reason:
                    result['post_stop_observation' if result.get('reason') else 'reason'] = reason
            self.routing.fail('routing_drain')
        finally:
            signal_owned_group()
            try:
                self.proc.wait(timeout=max(.001, end-time.monotonic()))
            except subprocess.TimeoutExpired:
                self.routing.fail('routing_drain')
            transport = {'stdout_eof': 'stdout' in self.eof, 'stderr_eof': 'stderr' in self.eof,
                'trailing_bytes': len(self.buffer)+len(self.routing.buffer), 'pending_records': len(self.pending),
                'process_reaped': self.proc.returncode is not None,
                'close_mode': 'incomplete' if self.proc.returncode is None or signal_error else
                    'post_terminal_kill_drained' if signaled and (grace_expired or self.proc.returncode == -signal.SIGKILL) else
                    'graceful_stdin_eof' if self.proc.returncode >= 0 else 'incomplete'}
            if self._turn_context is not None:
                result, usage, *_ = self._turn_context
                result['usage'] = usage.summary()
                result.pop('_stopping', None)
            self.selector.close()
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                stream.close()
        return {'process_reaped': transport['process_reaped'], 'exit_code': self.proc.returncode,
                'owned_process_group_kill_sent': signaled, 'group_signal_error': signal_error,
                'escaped_descendants_verified_absent': False, 'routing_drain': transport}

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
                self.eof.add('stdout' if key.fileobj is self.proc.stdout else 'stderr')
                if key.fileobj is self.proc.stdout and self.buffer:
                    raise Refusal('truncated_native_json')
                continue
            self.archive.raw('native_stdout' if key.fileobj is self.proc.stdout else 'native_stderr', block)
            if key.fileobj is not self.proc.stdout:
                if self.routing is not None:
                    self.routing.feed(block)
                continue
            self.buffer.extend(block)
            while b'\n' in self.buffer:
                raw, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                if len(raw) > FRAME_LIMIT:
                    raise Refusal('frame_limit')
                try:
                    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
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


def accept_event(session, event, *, late=False):
    # Internal fixed dispatch reused during drain; no case-supplied callback.
    result, usage, thread, turn, event_observer = session._turn_context
    method = event['method']
    params = event.get('params', {})
    if method == 'turn/started' and (params.get('threadId') != thread
            or params.get('turn', {}).get('id') != turn):
        raise Refusal('turn_identity')
    if late and (method == 'turn/started' or any(
            k in params and params[k] != v for k, v in (('threadId', thread), ('turnId', turn)))):
        raise Refusal('turn_identity')
    if event_observer is not None:
        try:
            event_observer.accept(event, thread, turn)
        except Exception:
            raise Refusal('tool_observation') from None
    if method == 'thread/tokenUsage/updated':
        if params.get('threadId') != thread or params.get('turnId') != turn:
            raise Refusal('usage_identity')
        reason = usage.accept(params.get('tokenUsage'))
        if late and reason:
            result['status'] = 'blocked'
            result['post_stop_observation' if result.get('reason') else 'reason'] = reason
            raise Refusal(reason)
        if reason and result.get('_stopping') is None:
            result['_stopping'] = reason
            result['reason'] = reason
            result['interrupt_attempted'] = True
            try:
                if late:
                    raise Refusal('usage_shape')
                session.rpc('turn/interrupt', {'threadId': thread, 'turnId': turn})
            except Exception:
                result['interrupt_acknowledged'] = False
            else:
                result['interrupt_acknowledged'] = True
        if reason and reason != 'soft_usage_stop':
            if reason != result.get('_stopping'):
                result['post_stop_observation'] = reason
            return True
    elif method == 'model/rerouted':
        result['model_selection']['rerouted'] = True
        raise Refusal('model_rerouted')
    elif method == 'item/completed':
        item = params.get('item', {})
        if params.get('threadId') == thread and params.get('turnId') == turn \
                and item.get('type') == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
            result['final_answer_count'] += 1
    elif method == 'turn/completed':
        if late:
            raise Refusal('terminal_identity')
        terminal = params['turn']
        if params.get('threadId') != thread or terminal['id'] != turn:
            raise Refusal('terminal_identity')
        result['terminal_completed'] = terminal.get('status') == 'completed' and terminal.get('error') is None
        if result.get('_stopping'):
            return True
        if not result['terminal_completed']:
            raise Refusal('terminal_failed')
        if usage.latest is None:
            raise Refusal('usage_unavailable')
        result['status'] = 'completed_ungraded'
        return True


def observe(session, *, prompt, project, codehome, metadata_check,
            soft_total, soft_output, usage_sink=None, event_observer=None):
    """Observe one initial turn within the caller's original session deadline.

    event_observer is a trusted fixed qualification projector, not case code.
    It must not persist arbitrary event contents. Its observations occur after
    native dispatch; this callback is not a preventive tool-approval mechanism.
    """
    usage = Usage(soft_total=soft_total, soft_output=soft_output, sink=usage_sink)
    result = {'status': 'blocked', 'reason': None, 'initial_turn_requests_attempted': 0,
              'initial_turns': 0, 'interrupt_attempted': False, 'terminal_completed': False,
              'auth_chatgpt_observed': False, 'model_requested': 'gpt-6-luna',
              'reasoning_requested': 'low', 'model_identity_verified': False,
              'wire_attempt_count': None, 'billing_usage': None,
              'hard_token_ceiling_enforced': False, 'live_eligible': False,
              'final_answer_count': 0, 'model_selection': {
                  'requested': 'gpt-6-luna', 'observed_thread_start': None,
                  'source': 'thread/start.result.model', 'match': False,
                  'backend_identity_verified': False, 'rerouted': False}}
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
        result['model_selection'].update(observed_thread_start='gpt-6-luna', match=True)
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
        session._turn_context = (result, usage, thread, turn, event_observer)
        if getattr(session, 'routing', None) is not None:
            session.routing.bind(thread, turn)
        while True:
            event = session.until(lambda value: 'method' in value)
            if accept_event(session, event):
                return result
    except Refusal as exc:
        reason = str(exc)
        reason = reason if reason in SAFE_REASONS else 'protocol_refusal'
        result['post_stop_observation' if result.get('_stopping') else 'reason'] = reason
    except TimeoutError:
        result['post_stop_observation' if result.get('_stopping') else 'reason'] = 'deadline'
    except Exception:
        result['post_stop_observation' if result.get('_stopping') else 'reason'] = 'protocol_operation'
    finally:
        result['usage'] = usage.summary()
        result.pop('_stopping', None)
    return result
