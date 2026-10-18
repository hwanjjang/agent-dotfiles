"""Frozen selected-trial validation; no authentication or process operations.

Inputs are an explicit maintainer manifest, not case-controlled instructions.
Checking never creates an attempt, opens a credential, or runs an executable.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType

if __package__:
    from . import native_trial_results as results
else:
    import native_trial_results as results

SOURCE = Path(__file__).resolve().parent
SOURCE_NAMES = frozenset((
    'native_trial.py', 'native_trial_plan.py', 'native_trial_protocol.py',
    'native_trial_owner.py', 'native_usage.py', 'native_execution.py',
    'native_execution_catalog.py', 'native_execution_command_skills.js',
    'native_isolation.py', 'native_trial_qualification.py', 'native_execution_loader.js',
    'native_trial_results.py', 'trial_reservation.py',
))
PROFILE = 'codex-0.163-macos-arm64-linux-arm64-v1'
PINNED_RUNTIME = {
    'codex': '8813367285524ac798dd96d1b071aea30d58708c7226fd236cd275cf1cfdee31',
    'code_mode_host': '79f123a85dbc61e8f5d0f0c050dfc3f4b81a8305d33a32b41e008b7f6e035698',
    'executor_archive': '9d8ecf2d19d3e184877983902d6c85de48b3888dcb72c382a8a0c975845927fb',
}
LIMITS = {'setup_seconds': 180, 'wall_seconds': 90, 'cleanup_seconds': 45,
          'soft_total_tokens': 131072, 'soft_output_tokens': 4096,
          'retained_bytes': 262144}
MAX_FILES = 64
MAX_FILE_BYTES = 512 * 1024
MAX_INPUT_BYTES = 4 * 1024 * 1024

QUALIFICATION_FILES = {
    ('case', 'fixture.txt'): b'ASSIGNED_REMOTE_FIXTURE',
    ('bundle', 'skills/assigned/SKILL.md'): b'---\nname: assigned\ndescription: Synthetic selected remote qualification skill.\n---\nASSIGNED_REMOTE_SKILL_BODY\n',
    ('bundle', 'skills/assigned/references/details.md'): b'ASSIGNED_REMOTE_SKILL_REFERENCE\n',
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def is_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def token(value):
    return isinstance(value, str) and re.fullmatch('[a-z0-9][a-z0-9_-]{0,63}', value) is not None


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def fields(value, names, reason):
    require(isinstance(value, dict) and set(value) == set(names.split()), reason)


def absolute(value, reason):
    require(isinstance(value, str) and 0 < len(value) <= 4096
            and not any(ord(c) < 32 for c in value), reason)
    require(value.startswith('/') and not value.startswith('//')
            and str(PurePosixPath(value)) == value and '..' not in PurePosixPath(value).parts, reason)
    return Path(value)


def relative(value):
    require(isinstance(value, str) and 0 < len(value) <= 1024
            and not any(ord(c) < 32 for c in value), 'input_path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value
            and all(p not in ('.', '..') for p in path.parts), 'input_path')
    require(path.parts and len(path.parts) <= 16, 'input_path')
    require(not any(p in ('auth.json', '.credentials.json', 'credentials.json', '.env')
                    for p in path.parts), 'input_path')
    return path


def directory(path):
    """Traverse every ancestor without resolving a symlink; caller closes fd."""
    path = absolute(str(path), 'input_unsafe')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_relative(root, name, maximum, reason, *, owner=True, retain=True):
    """Bounded descriptor read with pre/post metadata checks; no raw errors."""
    folder = stream = None
    try:
        folder = directory(root)
        root_info = os.fstat(folder)
        require(not owner or (root_info.st_uid == os.getuid()
                              and not root_info.st_mode & 0o022), reason)
        parts = PurePosixPath(name).parts
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=folder)
            os.close(folder)
            folder = child
            info = os.fstat(folder)
            require(not owner or (info.st_uid == os.getuid() and not info.st_mode & 0o022), reason)
        stream = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        info = os.fstat(stream)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and not info.st_mode & 0o022 and info.st_size <= maximum
                and (not owner or info.st_uid == os.getuid()), reason)
        data = bytearray() if retain else None
        hasher = hashlib.sha256()
        count = 0
        while True:
            block = os.read(stream, min(65536, maximum + 1 - count))
            if not block:
                break
            count += len(block)
            require(count <= maximum, reason)
            hasher.update(block)
            if retain:
                data.extend(block)
        require(stamp(info) == stamp(os.fstat(stream)) and count == info.st_size, reason)
        # Replacing the entry during reading is inconclusive, even if the opened
        # descriptor remains unchanged. This is not a hostile same-UID boundary.
        require(stamp(info) == stamp(os.stat(parts[-1], dir_fd=folder,
                                             follow_symlinks=False)), reason)
        return (bytes(data) if retain else None), hasher.hexdigest()
    except (OSError, ValueError):
        raise Refusal(reason) from None
    finally:
        if stream is not None:
            os.close(stream)
        if folder is not None:
            os.close(folder)


def read_file(path, maximum, reason, *, owner=True, retain=True):
    return read_relative(path.parent, path.name, maximum, reason,
                         owner=owner, retain=retain)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'plan_json')
        result[key] = value
    return result


def check_state(root, trial, attempt):
    fd = child = None
    try:
        fd = directory(root)
        info = os.fstat(fd)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'state_unsafe')
        try:
            child = os.open(trial, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        except FileNotFoundError:
            return
        info = os.fstat(child)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'state_unsafe')
        try:
            os.stat(attempt, dir_fd=child, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise Refusal('attempt_exists')
    except OSError:
        raise Refusal('state_unsafe') from None
    finally:
        if child is not None:
            os.close(child)
        if fd is not None:
            os.close(fd)


@dataclass(frozen=True)
class ValidatedPlan:
    _payload: bytes
    _files: object
    digest: str

    @property
    def data(self):
        return json.loads(self._payload)

    @property
    def files(self):
        return dict(self._files)


def validate_collection(value, mode):
    """Validate optional native delivery without touching outcome files."""
    fields(value, 'schema_version paths max_file_bytes max_total_bytes', 'collection_fields')
    require(type(value['schema_version']) is int and value['schema_version'] == 1,
            'collection_version')
    require(mode == 'trial', 'collection_mode')
    try:
        results._validate(Path('/work/project'), value['paths'],
                          value['max_file_bytes'], value['max_total_bytes'])
    except results._Blocked:
        raise Refusal('collection_declaration') from None
    require(len(value['paths']) <= 8 and len(encoded(value)) <= 4096,
            'collection_declaration')
    return value


def validate_routing(value, selected):
    """Bind a small complete declared catalog; no expected target or case code."""
    fields(value, 'mode observer catalog_scope catalog_digest catalog', 'routing_fields')
    require(value['mode'] in ('natural', 'forced_entrypoint')
            and value['observer'] == 'implicit-stderr-json-v1'
            and value['catalog_scope'] == 'declared_experiment_subset', 'routing_profile')
    rows = value['catalog']
    require(isinstance(rows, list) and 3 <= len(rows) <= 5
            and value['catalog_digest'] == digest(rows), 'routing_catalog')
    names, paths = set(), set()
    for slot, row in enumerate(rows):
        fields(row, 'slot name main_resource main_sha256 description_sha256', 'routing_fields')
        require(type(row['slot']) is int and row['slot'] == slot and token(row['name'])
                and row['name'] not in names and is_digest(row['description_sha256'])
                and is_digest(row['main_sha256']), 'routing_catalog')
        name = str(relative(row['main_resource']))
        require(name.startswith('skills/') and name.endswith('/SKILL.md') and name not in paths,
                'routing_catalog')
        data = selected.get(('bundle', name))
        require(data is not None and hashlib.sha256(data).hexdigest() == row['main_sha256'],
                'routing_catalog')
        try:
            lines = data.decode('utf-8').split('\n')
            require(lines and lines[0] == '---', 'routing_metadata')
            end = lines.index('---', 1)
            metadata = {}
            # Closed inline subset, not a general YAML parser. Unsupported
            # spelling or scalar semantics must not change native discovery.
            for line in lines[1:end]:
                if not line:
                    continue
                require(not any(ord(c) < 32 and c != '\t' for c in line) and
                        not any(c in line for c in ('\x85', '\u2028', '\u2029')),
                        'routing_metadata')
                match = re.fullmatch(
                    r'(name|description|disable-model-invocation|user-invocable):[ \t]+(.+)', line)
                require(match is not None, 'routing_metadata')
                key, raw = match.groups()
                require(key not in metadata, 'routing_metadata')
                require('\t' not in raw, 'routing_metadata')
                raw = raw.strip()
                if key in ('disable-model-invocation', 'user-invocable'):
                    require(raw in ('true', 'false') and
                            (key != 'disable-model-invocation' or raw == 'false'),
                            'routing_metadata')
                    metadata[key] = raw == 'true'
                    continue
                if raw.startswith('"'):
                    text = json.loads(raw)
                else:
                    # Alphabetic-leading plain strings exclude numbers, dates,
                    # flow collections and YAML indicator-led values. Quote
                    # other intended strings using JSON double-quote syntax.
                    require(raw and raw[0].isalpha() and raw.lower() not in
                            ('true', 'false', 'null', 'yes', 'no', 'on', 'off', 'y', 'n')
                            and not any(mark in raw for mark in ('#', '&', '*', '!'))
                            and re.search(r':(?:\s|$)', raw) is None, 'routing_metadata')
                    text = raw
                require(isinstance(text, str) and text and
                        not any(ord(c) < 32 or 127 <= ord(c) <= 159 or
                                c in ('\u2028', '\u2029') for c in text), 'routing_metadata')
                metadata[key] = text
            require(metadata.get('name') == row['name'] and
                    hashlib.sha256(metadata['description'].encode()).hexdigest() ==
                    row['description_sha256'], 'routing_metadata')
        except (ValueError, UnicodeError, KeyError, TypeError):
            raise Refusal('routing_metadata') from None
        names.add(row['name']); paths.add(name)
    require(paths == {name for kind, name in selected if kind == 'bundle'
                      and PurePosixPath(name).name == 'SKILL.md'}, 'routing_catalog')


def load_plan(path):
    """Validate a selected plan and materialize <=4MiB of frozen input bytes.

    Authentication paths are deliberately not part of this schema. Runtime
    identity checks read executables, but never run them or contact Docker.
    """
    path = absolute(str(path), 'plan_path')
    raw, _ = read_file(path, 1024 * 1024, 'plan_file')
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(Refusal('plan_json')))
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal('plan_json') from None
    names = 'schema_version profile mode identity inputs prompt runtime limits sources state_root'
    require(isinstance(value, dict) and type(value.get('schema_version')) is int
            and value['schema_version'] in (1, 2), 'plan_version')
    routed = value['schema_version'] == 2
    if routed:
        names += ' routing'
    fields(value, names + (' collection' if isinstance(value, dict) and 'collection' in value else ''),
           'plan_fields')
    require(value['profile'] == PROFILE and value['mode'] in ('trial', 'qualification'), 'plan_profile')
    require(not routed or value['mode'] == 'trial', 'routing_mode')
    if 'collection' in value:
        validate_collection(value['collection'], value['mode'])
    identity = value['identity']
    fields(identity, 'trial_id binding_digest experiment_digest case_id arm variant repetition attempt_id', 'identity')
    require(all(is_digest(identity[k]) for k in ('trial_id', 'binding_digest', 'experiment_digest'))
            and isinstance(identity['case_id'], str)
            and re.fullmatch('[A-Za-z0-9_.:@-]{1,160}', identity['case_id']) is not None
            and token(identity['attempt_id'])
            and identity['arm'] in ('baseline', 'candidate')
            and identity['variant'] in ('reproduction', 'counterpart')
            and type(identity['repetition']) is int and 0 <= identity['repetition'] <= 99, 'identity')
    require(isinstance(value['prompt'], str) and 0 < len(value['prompt']) <= 8192
            and '\0' not in value['prompt'], 'prompt')
    fields(value['limits'], ' '.join(LIMITS), 'limits')
    require(all(type(value['limits'][k]) is int and 0 < value['limits'][k] <= maximum
                for k, maximum in LIMITS.items())
            and value['limits']['retained_bytes'] >= 65536, 'limits')
    sources = value['sources']
    require(isinstance(sources, dict) and set(sources) == SOURCE_NAMES
            and all(is_digest(v) for v in sources.values()), 'source_fields')
    for name, expected in sources.items():
        _, observed = read_file(SOURCE / name, 2 * 1024 * 1024, 'source_unsafe', retain=False)
        require(observed == expected, 'source_changed')
    runtime = value['runtime']
    fields(runtime, 'codex code_mode_host docker executor_archive hashes image docker_host metadata_digest', 'runtime_fields')
    fields(runtime['hashes'], 'codex code_mode_host docker executor_archive', 'runtime_fields')
    require(all(is_digest(h) for h in runtime['hashes'].values()), 'runtime_fields')
    require(all(runtime['hashes'][k] == v for k, v in PINNED_RUNTIME.items()), 'runtime_pin')
    require(isinstance(runtime['docker_host'], str)
            and runtime['docker_host'].startswith('unix:///'), 'runtime_endpoint')
    absolute(runtime['docker_host'][7:], 'runtime_endpoint')
    require(isinstance(runtime['image'], str) and runtime['image'].startswith('sha256:')
            and is_digest(runtime['image'][7:]), 'runtime_image')
    require(is_digest(runtime['metadata_digest']), 'runtime_metadata')
    for name, expected in runtime['hashes'].items():
        executable = absolute(runtime[name], 'runtime_path')
        _, observed = read_file(executable, 512 * 1024 * 1024, 'runtime_unsafe',
                               owner=False, retain=False)
        require(observed == expected, 'runtime_changed')
    inputs = value['inputs']
    natural = routed and isinstance(value['routing'], dict) and value['routing'].get('mode') == 'natural'
    fields(inputs, 'root files' if natural else 'root entrypoint files', 'input_fields')
    input_root = absolute(inputs['root'], 'input_root')
    entrypoint = None if natural else str(relative(inputs['entrypoint']))
    require(isinstance(inputs['files'], list) and 1 <= len(inputs['files']) <= MAX_FILES, 'input_files')
    selected = {}
    total = 0
    for record in inputs['files']:
        fields(record, 'kind path sha256', 'input_fields')
        require(record['kind'] in ('case', 'bundle') and is_digest(record['sha256']), 'input_fields')
        name = relative(record['path'])
        if record['kind'] == 'case':
            require(name.parts[0] != 'arm' and str(name) != 'transport-canary.txt', 'input_path')
        key = record['kind'], str(name)
        require(key not in selected, 'input_duplicate')
        content, observed = read_relative(input_root / record['kind'], str(name),
                                          MAX_FILE_BYTES, 'input_unsafe')
        require(observed == record['sha256'], 'input_changed')
        total += len(content)
        require(total <= MAX_INPUT_BYTES, 'input_size')
        selected[key] = content
    if routed:
        validate_routing(value['routing'], selected)
    require(natural or ('bundle', entrypoint) in selected, 'entrypoint_missing')
    if value['mode'] == 'qualification':
        require(selected == QUALIFICATION_FILES and entrypoint == 'skills/assigned/SKILL.md', 'qualification_fixture')
    state_root = absolute(value['state_root'], 'state_unsafe')
    check_state(state_root, identity['trial_id'], identity['attempt_id'])
    return ValidatedPlan(encoded(value), MappingProxyType(dict(selected)), digest(value))
