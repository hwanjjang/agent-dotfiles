"""Fixed, lossy qualification of one trusted native boundary script.

The caller owns script selection, exclusive challenge placement, raw-event
availability, terminal/usage checks, OS isolation and cleanup. This observer does
not launch anything, retain raw notifications, or grant evaluation admission.
"""
import json
import re

try:
    from .native_execution import BOUNDARY_EXPECTED, encoded
except ImportError:
    from native_execution import BOUNDARY_EXPECTED, encoded

MAX_ITEMS = 64
MAX_TEXT = 65536
MAX_SCRIPT = 32768
_WALL = re.compile(r'Wall time [0-9]+\.[0-9]+ seconds(?: \(code-mode [0-9]+\.[0-9]+ seconds; overhead -?[0-9]+\.[0-9]+ seconds\))?')


def _identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 128


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _without_exec_pragma(script):
    header, newline, body = script.partition('\n')
    if not newline or not header.startswith('// @exec:'):
        return script
    try:
        options = json.loads(header[len('// @exec:'):], object_pairs_hook=_unique)
        if (isinstance(options, dict) and set(options) <= {'yield_time_ms', 'max_output_tokens'}
                and all(type(value) is int and 0 <= value <= 2147483647 for value in options.values())):
            return body
    except (ValueError, RecursionError):
        pass
    return script


def _input_diagnostics(value, expected, present):
    """Bounded comparison labels only; never alter exact acceptance."""
    string = isinstance(value, str)
    shape = dict(observed=True, present=present, is_string=string,
                 empty=string and not value, over_limit=string and len(value) > MAX_SCRIPT,
                 has_crlf=False, has_bare_cr=False, outer_whitespace=False, leading_exec_pragma=False)
    if not string or shape['over_limit']:
        return 'other', shape
    shape.update(has_crlf='\r\n' in value, has_bare_cr='\r' in value.replace('\r\n', ''),
                 outer_whitespace=value != value.strip(), leading_exec_pragma=value.startswith('// @exec:'))
    if value == expected:
        variant = 'exact'
    elif value.strip() == expected.strip():
        variant = 'outer_whitespace_only'
    elif value.replace('\r\n', '\n').replace('\r', '\n') == expected.replace('\r\n', '\n').replace('\r', '\n'):
        variant = 'line_endings_only'
    elif _without_exec_pragma(value) == _without_exec_pragma(expected):
        variant = 'exec_pragma_only'
    else:
        variant = 'other'
    return variant, shape


def _lines(output):
    if isinstance(output, str):
        text = output
    elif isinstance(output, list) and 0 < len(output) <= MAX_ITEMS and all(
            isinstance(part, dict) and part.get('type') == 'input_text'
            and isinstance(part.get('text'), str) for part in output):
        if sum(len(part['text']) for part in output) > MAX_TEXT:
            raise ValueError('output_limit')
        text = '\n'.join(part['text'] for part in output)
    else:
        raise ValueError('output_shape')
    if len(text) > MAX_TEXT:
        raise ValueError('output_limit')
    return text.splitlines()


# Bit positions follow the six shared fixed records, never observed names.
_CHECKS = tuple(BOUNDARY_EXPECTED)
_STAGES = {name: name.replace(' ', '_') for name in (
    'inventory', 'callable tools', 'globals', 'import', 'mcp', 'command completion',
    'command boundary', 'skill inventory', 'skill resource', 'skill contents',
    'skill scope', 'remaining exposed routes')}


def _diagnostics(output):
    """Lossy partial facts, never an alternate acceptance path."""
    header, seen, matching, stage = 'other', 0, 0, 'unknown'
    try:
        lines = _lines(output)
    except ValueError:
        return header, seen, matching, stage
    if lines and lines[0] in ('Script completed', 'Script failed'):
        header = 'completed' if lines[0] == 'Script completed' else 'failed'
    counts = dict.fromkeys(_CHECKS, 0)
    stages = []
    # Only inspect the native body if its fixed header structure is recognized.
    if len(lines) < 3 or not _WALL.fullmatch(lines[1]) or lines[2] != 'Output:':
        return header, seen, matching, stage
    for index, line in enumerate(lines[3:], 3):
        if line.startswith('BOUNDARY_CHECK:'):
            try:
                record = json.loads(line[len('BOUNDARY_CHECK:'):], object_pairs_hook=_unique,
                                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid_number')))
                if not isinstance(record, dict) or set(record) != {'check', 'result'}:
                    continue
                name = record['check']
                if not isinstance(name, str) or name not in _CHECKS:
                    continue
                bit = 1 << _CHECKS.index(name)
                counts[name] += 1
                seen |= bit
                if counts[name] == 1 and encoded(record['result']) == encoded(BOUNDARY_EXPECTED[name]):
                    matching |= bit
                else:
                    matching &= ~bit  # Duplicate/inconsistent records are not a matching check.
            except (ValueError, TypeError, RecursionError, OverflowError):
                continue
        elif line == 'Script error:' and index+1 < len(lines):
            following = lines[index+1]
            # Pinned code_mode/mod.rs emits this separate error block. Only
            # exact trusted requireTrue names qualify; no arbitrary error text.
            for name, value in _STAGES.items():
                if following == 'Error: Boundary check failed: '+name:
                    stages.append(value)
                    break
            else:
                stages.append('unknown')
    if header == 'failed' and len(stages) == 1:
        stage = stages[0]
    return header, seen, matching, stage


def _catalog_projection(output):
    """Keep bounded counters only, including when the strict inventory refuses."""
    try:
        lines = _lines(output)
        if len(lines) < 3 or lines[0] not in ('Script completed', 'Script failed') or not _WALL.fullmatch(lines[1]) or lines[2] != 'Output:':
            return None
        records = []
        for line in lines[3:]:
            if not line.startswith('BOUNDARY_CHECK:'):
                continue
            row = json.loads(line[len('BOUNDARY_CHECK:'):], object_pairs_hook=_unique)
            if isinstance(row, dict) and row.get('check') == 'catalog':
                if set(row) != {'check', 'result'}:
                    return None
                records.append(row['result'])
        if len(records) != 1 or not isinstance(records[0], dict) or set(records[0]) != {'advertised', 'callable'}:
            return None
        for projection in records[0].values():
            if not isinstance(projection, dict) or set(projection) != {'mask', 'count', 'unknown', 'duplicates'}:
                return None
            if not all(type(v) is int and 0 <= v <= (1023 if k == 'mask' else 256) for k, v in projection.items()):
                return None
        return records[0]
    except (ValueError, TypeError, RecursionError, OverflowError):
        return None


def _boundary(output, challenge):
    lines = _lines(output)
    if len(lines) < 3 or lines[0] != 'Script completed' or not _WALL.fullmatch(lines[1]) or lines[2] != 'Output:':
        raise ValueError('cell_header')
    checks = set()
    completed = challenge_count = 0
    match = False
    for line in lines[3:]:
        if not line:
            continue
        if line == 'BOUNDARY_COMPLETED':
            completed += 1
        elif line.startswith('REMOTE_CHALLENGE:'):
            challenge_count += 1
            value = line[len('REMOTE_CHALLENGE:'):]
            match = bool(re.fullmatch('[0-9a-f]{32}', value)) and value == challenge
        elif line.startswith('BOUNDARY_CHECK:'):
            record = json.loads(line[len('BOUNDARY_CHECK:'):], object_pairs_hook=_unique,
                                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid_number')))
            if not isinstance(record, dict) or set(record) != {'check', 'result'}:
                raise ValueError('record_shape')
            name = record['check']
            if not isinstance(name, str) or name not in BOUNDARY_EXPECTED or name in checks:
                raise ValueError('record_identity')
            if encoded(record['result']) != encoded(BOUNDARY_EXPECTED[name]):
                raise ValueError('record_predicate')
            checks.add(name)
        else:
            raise ValueError('unexpected_output')
    if checks != set(BOUNDARY_EXPECTED) or completed != 1 or challenge_count != 1 or not match:
        raise ValueError('boundary_incomplete')


class Qualification:
    """Observe one exact custom exec call; export only finite facts.

    Expected script/challenge and correlation IDs are held transiently in memory.
    No content, ID, prompt, challenge, hash, error text or exception is exported.
    Callers must provide native experimental raw events: high-level display items
    alone cannot attest to the executed script or repair missing raw evidence.
    """
    def __init__(self, script, challenge):
        if not isinstance(script, str) or not 0 < len(script) <= MAX_SCRIPT:
            raise ValueError('qualification_script_shape')
        if not isinstance(challenge, str) or not re.fullmatch('[0-9a-f]{32}', challenge):
            raise ValueError('qualification_challenge_shape')
        self._script = script
        self._challenge = challenge
        self._scope = None
        self._call = None
        self._reason = None
        self._items = self._calls = self._outputs = self._finals = self._unexpected = 0
        self._script_exact = self._boundary_verified = self._challenge_match = self._final_match = False
        self._catalog = None
        self._call_id_valid = self._input_matches_expected = False
        self._input_variant = 'not_observed'
        self._input_shape = dict.fromkeys(('observed', 'present', 'is_string', 'empty', 'over_limit',
            'has_crlf', 'has_bare_cr', 'outer_whitespace', 'leading_exec_pragma'), False)
        self._header, self._seen_mask, self._matching_mask, self._stage = 'other', 0, 0, 'unknown'

    def _fail(self, reason):
        if self._reason is None:
            self._reason = reason

    def accept(self, event, thread, turn):
        if self._reason is not None:
            return
        if not isinstance(event, dict):
            self._fail('event_shape')
            return
        method = event.get('method')
        if method not in ('rawResponseItem/completed', 'item/completed'):
            return
        self._items += 1
        if self._items > MAX_ITEMS:
            self._fail('item_limit')
            return
        if not _identifier(thread) or not _identifier(turn):
            self._fail('scope_shape')
            return
        if self._scope is None:
            self._scope = (thread, turn)
        params = event.get('params')
        if self._scope != (thread, turn) or not isinstance(params, dict) or params.get('threadId') != thread or params.get('turnId') != turn:
            self._fail('scope_mismatch')
            return
        item = params.get('item')
        if not isinstance(item, dict) or not isinstance(item.get('type'), str):
            self._fail('item_shape')
            return
        kind = item['type']
        if method == 'item/completed':
            # Native display items can duplicate nested executions already
            # represented by the exact raw outer script. They are not evidence.
            if kind == 'agentMessage':
                phase = item.get('phase')
                if phase == 'commentary':
                    return
                if phase not in (None, 'final_answer'):
                    self._fail('final_shape')
                    return
                self._finals += 1
                self._final_match = item.get('text') == self._challenge
                if self._finals != 1 or not self._boundary_verified or not self._final_match:
                    self._fail('final_mismatch_or_order')
            return
        if kind == 'custom_tool_call':
            self._calls += 1
            if self._calls != 1 or self._finals or item.get('name') != 'exec' or item.get('namespace') not in (None, 'functions'):
                self._unexpected += 1
                self._fail('unexpected_call')
            else:
                self._call_id_valid = _identifier(item.get('call_id'))
                self._input_matches_expected = item.get('input') == self._script
                self._input_variant, self._input_shape = _input_diagnostics(
                    item.get('input'), self._script, 'input' in item)
                if not self._call_id_valid or not self._input_matches_expected:
                    self._fail('script_or_call_mismatch')
                else:
                    self._call = item['call_id']
                    self._script_exact = True
        elif kind == 'custom_tool_call_output':
            self._outputs += 1
            if self._outputs != 1 or self._call is None or self._finals or item.get('call_id') != self._call or item.get('name') not in (None, 'exec'):
                self._fail('output_identity_or_order')
                return
            self._catalog = _catalog_projection(item.get('output'))
            self._header, self._seen_mask, self._matching_mask, self._stage = _diagnostics(item.get('output'))
            try:
                _boundary(item.get('output'), self._challenge)
            except (ValueError, TypeError, RecursionError, OverflowError):
                self._fail('boundary_output_invalid')
            else:
                self._boundary_verified = self._challenge_match = True
        elif kind not in ('message', 'reasoning', 'compaction', 'compaction_summary'):
            self._unexpected += 1
            self._fail('unexpected_raw_item')

    def summary(self):
        observed = (self._reason is None and self._calls == self._outputs == self._finals == 1
                    and self._script_exact and self._boundary_verified and self._challenge_match and self._final_match)
        return {'schema_version': 1, 'status': 'observed' if observed else 'blocked',
                'reason': None if observed else self._reason or 'evidence_incomplete',
                'items_observed': self._items, 'custom_tool_calls': self._calls,
                'matched_tool_outputs': int(self._boundary_verified), 'tool_outputs_observed': self._outputs,
                'final_messages': self._finals, 'unexpected_items': self._unexpected,
                'boundary_header': self._header, 'boundary_record_seen_mask': self._seen_mask,
                'boundary_record_matching_mask': self._matching_mask, 'failure_stage': self._stage,
                **{'catalog_'+role+'_'+field: self._catalog[role][field] if self._catalog else None
                   for role in ('advertised', 'callable') for field in ('mask', 'count', 'unknown', 'duplicates')},
                'call_id_valid': self._call_id_valid, 'input_matches_expected': self._input_matches_expected,
                'input_variant': self._input_variant,
                **{'input_shape_'+name: value for name, value in self._input_shape.items()},
                'script_exact': self._script_exact, 'boundary_checks_verified': self._boundary_verified,
                'challenge_output_match': self._challenge_match, 'final_match': self._final_match,
                'raw_contents_retained': False, 'content_hashes_retained': False,
                'challenge_value_retained': False, 'call_ids_retained': False,
                'live_eligible': False, 'isolation_qualified': False, 'all_routes_qualified': False}
