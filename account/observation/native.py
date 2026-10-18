"""Client-specific hook metadata adapters v1. No tool arguments, output or transcript IO."""
from pathlib import Path

from .files import encoded
from .store import decode, digest, require, token

PAYLOAD_LIMIT = 131072
EVENTS = {'SessionStart': 'session_start', 'PreToolUse': 'tool_start',
          'PostToolUse': 'tool_end', 'Stop': 'response_end'}
CLIENT_EVENTS = {'claude': dict(EVENTS, PostToolUseFailure='tool_end'), 'codex': EVENTS}


def validate_process_scope(grant):
    client = grant['client']
    require(client in CLIENT_EVENTS and grant['profile'] == 'default'
            and grant['source'] == client + '-hooks-v1', 'unsupported_adapter')
    require(str(Path.cwd().resolve(strict=True)) == grant['project_root'], 'project_scope')


def envelope(stream, grant):
    client = grant['client']
    events = CLIENT_EVENTS[client]
    raw = stream.read(PAYLOAD_LIMIT + 1)
    require(isinstance(raw, bytes) and len(raw) <= PAYLOAD_LIMIT, 'payload_size')
    value = decode(raw)
    require(isinstance(value, dict), 'event_object')
    cwd = value.get('cwd')
    require(isinstance(cwd, str) and len(cwd) <= 4096 and Path(cwd).is_absolute(), 'project_scope')
    require(str(Path(cwd).resolve(strict=True)) == grant['project_root'], 'project_scope')
    name = value.get('hook_event_name')
    require(isinstance(name, str) and name in events, 'unsupported_event')
    session = value.get('session_id')
    require(token(session), 'session_id')
    tool = value.get('tool_use_id') if name in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure') else None
    require(tool is None or token(tool), 'tool_call_id')
    turn = value.get('turn_id') if client == 'codex' and name != 'SessionStart' else None
    require(turn is None or token(turn), 'turn_id')
    # Codex's turn identity avoids conflating a reused tool ID across turns.
    if client == 'codex':
        identity = digest([name, turn, tool]) if tool and turn else None
    else:
        identity = digest([name, tool]) if tool else None
    category = None
    if name in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure'):
        tool_name = value.get('tool_name')
        require(isinstance(tool_name, str) and len(tool_name) <= 256, 'tool_name')
        category = ('shell' if tool_name == 'Bash' else 'file' if tool_name in
                    ({'apply_patch'} if client == 'codex' else {'Read', 'Write', 'Edit', 'Glob', 'Grep'}) else 'mcp' if tool_name.startswith('mcp__') else 'other')
    event = dict(schema_version=1, project_root=grant['project_root'], client=grant['client'],
                 profile=grant['profile'], source=grant['source'], session_id=session,
                 source_event_id=identity, tool_call_id=tool,
                 event_kind=events[name], tool_category=category,
                 status='failure' if name == 'PostToolUseFailure' else 'pending' if name == 'PreToolUse' else 'unknown')
    if client == 'codex':
        event['turn_id'] = turn
    # PostToolUse proves a callback occurred, not that a shell command/test passed.
    # Session IDs do not establish actor identity. No inferred parent or time; only Codex's explicit turn ID is retained.
    return event


def adapt(stream, grant, existing):
    """Legacy adapter interface; Store uses the bounded envelope directly."""
    event = envelope(stream, grant)
    existing = list(existing)
    previous = next((old for old in existing if event['source_event_id'] is not None
                     and old['session_id'] == event['session_id']
                     and old['source_event_id'] == event['source_event_id']), None)
    event['sequence'] = previous['sequence'] if previous else max(
        (old['sequence'] for old in existing), default=grant['start_after']) + 1
    return encoded(event)
