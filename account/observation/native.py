"""Claude hook metadata adapter v1. No tool arguments, output or transcript IO."""
from pathlib import Path

from .files import encoded
from .store import decode, digest, require, token

PAYLOAD_LIMIT = 131072
EVENTS = {'SessionStart': 'session_start', 'PreToolUse': 'tool_start',
          'PostToolUse': 'tool_end', 'PostToolUseFailure': 'tool_end', 'Stop': 'response_end'}


def validate_process_scope(grant):
    require(grant['client'] == 'claude' and grant['profile'] == 'default'
            and grant['source'] == 'claude-hooks-v1', 'unsupported_adapter')
    require(str(Path.cwd().resolve(strict=True)) == grant['project_root'], 'project_scope')


def adapt(stream, grant, existing):
    raw = stream.read(PAYLOAD_LIMIT + 1)
    require(isinstance(raw, bytes) and len(raw) <= PAYLOAD_LIMIT, 'payload_size')
    value = decode(raw)
    require(isinstance(value, dict), 'event_object')
    cwd = value.get('cwd')
    require(isinstance(cwd, str) and len(cwd) <= 4096 and Path(cwd).is_absolute(), 'project_scope')
    require(str(Path(cwd).resolve(strict=True)) == grant['project_root'], 'project_scope')
    name = value.get('hook_event_name')
    require(isinstance(name, str) and name in EVENTS, 'unsupported_event')
    session = value.get('session_id')
    require(token(session), 'session_id')
    tool = value.get('tool_use_id') if name in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure') else None
    require(tool is None or token(tool), 'tool_call_id')
    identity = digest([name, tool]) if tool else None
    existing = list(existing)
    previous = next((event for event in existing if identity is not None
                     and event['session_id'] == session and event['source_event_id'] == identity), None)
    sequence = previous['sequence'] if previous else max(
        (event['sequence'] for event in existing), default=grant['start_after']) + 1
    category = None
    if name in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure'):
        tool_name = value.get('tool_name')
        require(isinstance(tool_name, str) and len(tool_name) <= 256, 'tool_name')
        category = ('shell' if tool_name == 'Bash' else 'file' if tool_name in
                    {'Read', 'Write', 'Edit', 'Glob', 'Grep'} else 'mcp' if tool_name.startswith('mcp__') else 'other')
    event = dict(schema_version=1, project_root=grant['project_root'], client=grant['client'],
                 profile=grant['profile'], source=grant['source'], session_id=session,
                 sequence=sequence, source_event_id=identity, tool_call_id=tool,
                 event_kind=EVENTS[name], tool_category=category,
                 status='failure' if name == 'PostToolUseFailure' else 'pending' if name == 'PreToolUse' else 'unknown')
    # PostToolUse proves a callback occurred, not that a shell command/test passed.
    # Session IDs do not establish actor identity. No inferred parent, turn or time.
    return encoded(event)
