#!/usr/bin/env python3
"""Snapshot declared artifact metadata and hashes; never execute task content.

The trusted caller owns source, root, trial identity and process lifecycle.
Descriptor checks establish bounded per-file byte snapshots, not quiescent or
atomic final state, independent custody, task correctness or evaluation admission.
"""
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

MAX_FILES = 64
MAX_PATH = 160
MAX_FILE_BYTES = 65536
MAX_TOTAL_BYTES = 262144
MAX_INPUT_BYTES = 16384
_FORBIDDEN = frozenset(('auth.json', '.credentials.json', 'credentials.json',
                        '.env', 'transport-canary.txt'))


class _Blocked(Exception):
    pass


def _result(files=None, reason=None):
    return {'schema_version': 1, 'kind': 'bounded_artifact_snapshot',
            'status': 'blocked' if reason else 'captured',
            'files': [] if reason else files, 'reason': reason,
            'quiescent_state_verified': False}


def _require(condition, reason):
    if not condition:
        raise _Blocked(reason)


def _directory_identity(info):
    return info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode


def _file_identity(info):
    return (_directory_identity(info), info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _validate(root, paths, maximum, total):
    _require(isinstance(root, Path) and root.is_absolute() and root.anchor == '/'
             and '..' not in root.parts and len(str(root)) <= 4096
             and not any(ord(char) < 32 or ord(char) == 127 for char in str(root)),
             'invalid_declaration')
    _require(type(paths) is list and 1 <= len(paths) <= MAX_FILES,
             'invalid_declaration')
    _require(type(maximum) is int and 1 <= maximum <= MAX_FILE_BYTES
             and type(total) is int and 1 <= total <= MAX_TOTAL_BYTES,
             'invalid_declaration')
    seen = set()
    for name in paths:
        _require(type(name) is str and 0 < len(name) <= MAX_PATH
                 and not any(ord(char) < 32 or ord(char) == 127 for char in name)
                 and '\\' not in name, 'invalid_declaration')
        path = PurePosixPath(name)
        _require(bool(path.parts) and not path.is_absolute() and str(path) == name
                 and all(part not in ('.', '..') for part in path.parts)
                 and not any(part in _FORBIDDEN or part.startswith('.env.') for part in path.parts)
                 and len(path.parts) <= 16 and name not in seen,
                 'invalid_declaration')
        seen.add(name)


def _open_directory(parent, name, opened, entries, reason):
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=parent)
    except OSError as error:
        if error.errno == errno.ENOENT and reason == 'unsafe_path':
            raise
        raise _Blocked(reason) from None
    opened.append(descriptor)
    identity = _directory_identity(os.fstat(descriptor))
    entries.append((parent, name, identity))
    return descriptor


def _check_entries(entries):
    for parent, name, expected in entries:
        try:
            actual = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except OSError:
            raise _Blocked('changed') from None
        _require(_directory_identity(actual) == expected, 'changed')


def collect(root, paths, *, max_file_bytes=MAX_FILE_BYTES,
            max_total_bytes=MAX_TOTAL_BYTES):
    """Return closed observations for declared files, or a fixed blocked reason.

    Missing is an observed ENOENT inside a checked root. Other errors invalidate
    the entire capture; partial observations cannot be mistaken for a good run.
    Paths and bounds are trusted declarations, never task-supplied commands.
    """
    opened, entries = [], []
    try:
        _validate(root, paths, max_file_bytes, max_total_bytes)
        _require(all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK'))
                 and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd,
                 'unsupported_platform')
        root_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(root_fd)
        for part in root.parts[1:]:
            root_fd = _open_directory(root_fd, part, opened, entries, 'unsafe_root')
        owner = os.fstat(root_fd).st_uid
        _require(owner == os.getuid(), 'unsafe_root')
        rows, used = [], 0
        for name in paths:
            parent = root_fd
            parts = PurePosixPath(name).parts
            try:
                for part in parts[:-1]:
                    parent = _open_directory(parent, part, opened, entries, 'unsafe_path')
                descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     dir_fd=parent)
            except OSError as error:
                if error.errno == errno.ENOENT:
                    _check_entries(entries)
                    rows.append({'path': name, 'status': 'missing', 'bytes': None, 'sha256': None})
                    continue
                raise _Blocked('unsafe_path' if error.errno in (errno.ELOOP, errno.ENOTDIR)
                               else 'read_error') from None
            opened.append(descriptor)
            before = os.fstat(descriptor)
            _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                     and before.st_uid == owner, 'unsafe_file')
            _require(0 <= before.st_size <= max_file_bytes
                     and used + before.st_size <= max_total_bytes, 'size_limit')
            count, hasher = 0, hashlib.sha256()
            while True:
                data = os.read(descriptor, min(65536, max_file_bytes + 1 - count))
                if not data:
                    break
                count += len(data)
                _require(count <= max_file_bytes and used + count <= max_total_bytes,
                         'size_limit')
                hasher.update(data)
            after = os.fstat(descriptor)
            try:
                entry = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            except OSError:
                raise _Blocked('changed') from None
            _require(_file_identity(before) == _file_identity(after) == _file_identity(entry)
                     and count == before.st_size, 'changed')
            _check_entries(entries)
            used += count
            rows.append({'path': name, 'status': 'present', 'bytes': count,
                         'sha256': hasher.hexdigest()})
        _check_entries(entries)
        return _result(rows)
    except _Blocked as error:
        return _result(reason=str(error))
    except (OSError, ValueError, OverflowError):
        return _result(reason='read_error')
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'invalid_input')
        result[key] = value
    return result


def main(argv=None):
    """Trusted root argument, bounded JSON stdin; no lifecycle or raw evidence."""
    arguments = sys.argv[1:] if argv is None else argv
    try:
        _require(arguments == [] or (len(arguments) == 2 and arguments[0] == '--root'),
                 'invalid_input')
        root = Path(arguments[1] if arguments else '/work/project')
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        _require(len(raw) <= MAX_INPUT_BYTES, 'invalid_input')
        value = json.loads(raw, object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(_Blocked('invalid_input')))
        _require(type(value) is dict and {'paths'} <= set(value)
                 <= {'paths', 'max_file_bytes', 'max_total_bytes'}, 'invalid_input')
        result = collect(root, **value)
    except (_Blocked, ValueError, TypeError, UnicodeError, RecursionError):
        result = _result(reason='invalid_input')
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=True) + '\n')
    return int(result['status'] == 'blocked')


if __name__ == '__main__':
    raise SystemExit(main())
