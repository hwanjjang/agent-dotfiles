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
                 and not any(part.casefold() in _FORBIDDEN or part.casefold().startswith('.env.')
                             for part in path.parts)
                 and len(path.parts) <= 16 and name not in seen,
                 'invalid_declaration')
        seen.add(name)


def _walk(start, parts, identities, observed=None):
    """Walk with at most two temporary descriptors; retain identities, not fds."""
    current = os.dup(start)
    prefix = ()
    try:
        for name in parts:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=current)
            try:
                identity = _directory_identity(os.fstat(child))
                try:
                    entry = os.stat(name, dir_fd=current, follow_symlinks=False)
                except OSError:
                    raise _Blocked('changed') from None
                _require(identity == _directory_identity(entry), 'changed')
                prefix += (name,)
                if prefix in identities:
                    _require(identities[prefix] == identity, 'changed')
                else:
                    identities[prefix] = identity
            except BaseException:
                os.close(child)
                raise
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise
    finally:
        if observed is not None:
            observed.add(prefix)


def _root(root, identities, *, recheck=False):
    descriptor = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _walk(descriptor, root.parts[1:], identities)
    except OSError:
        raise _Blocked('changed' if recheck else 'unsafe_root') from None
    finally:
        os.close(descriptor)


def _check_entries(root, root_fd, root_entries, entries, parents):
    descriptor = _root(root, root_entries, recheck=True)
    try:
        _require(_directory_identity(os.fstat(descriptor)) ==
                 _directory_identity(os.fstat(root_fd)), 'changed')
    finally:
        os.close(descriptor)
    # Replay each observed parent from the retained root without following any
    # intermediate link. Closing ancestors does not remove their identity checks.
    for parts in parents:
        try:
            descriptor = _walk(root_fd, parts, entries)
        except OSError:
            raise _Blocked('changed') from None
        os.close(descriptor)


def collect(root, paths, *, max_file_bytes=MAX_FILE_BYTES,
            max_total_bytes=MAX_TOTAL_BYTES):
    """Return closed observations for declared files, or a fixed blocked reason.

    Missing is an observed ENOENT inside a checked root. Other errors invalidate
    the entire capture; partial observations cannot be mistaken for a good run.
    Paths and bounds are trusted declarations, never task-supplied commands.
    Writable task outputs are intentional: owner, type and before/after mode
    identity are checked; this is not the immutable source-reader mode policy.
    """
    root_fd = None
    root_entries, entries, parents = {}, {}, set()
    try:
        _validate(root, paths, max_file_bytes, max_total_bytes)
        _require(all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK'))
                 and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd,
                 'unsupported_platform')
        root_fd = _root(root, root_entries)
        owner = os.fstat(root_fd).st_uid
        _require(owner == os.getuid(), 'unsafe_root')
        rows, used = [], 0
        for name in paths:
            parent = descriptor = None
            parts = PurePosixPath(name).parts
            try:
                try:
                    parent = _walk(root_fd, parts[:-1], entries, parents)
                    descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                         dir_fd=parent)
                except OSError as error:
                    if error.errno == errno.ENOENT:
                        _check_entries(root, root_fd, root_entries, entries, parents)
                        rows.append({'path': name, 'status': 'missing', 'bytes': None, 'sha256': None})
                        continue
                    raise _Blocked('unsafe_path' if error.errno in (errno.ELOOP, errno.ENOTDIR)
                                   else 'read_error') from None
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
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                if parent is not None:
                    os.close(parent)
            _check_entries(root, root_fd, root_entries, entries, parents)
            used += count
            rows.append({'path': name, 'status': 'present', 'bytes': count,
                         'sha256': hasher.hexdigest()})
        _check_entries(root, root_fd, root_entries, entries, parents)
        return _result(rows)
    except _Blocked as error:
        return _result(reason=str(error))
    except (OSError, ValueError, OverflowError):
        return _result(reason='read_error')
    finally:
        if root_fd is not None:
            os.close(root_fd)


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
