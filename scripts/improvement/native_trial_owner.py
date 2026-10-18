"""One explicit native-home copy and bounded cleanup; no auth discovery.

The runner supplies paths, verified executable identity, and trusted process
shutdown evidence. This module neither grants authority nor proves that evidence.
Operations require serialized ownership, not a hostile same-UID race boundary.
"""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import stat
import time

AUTH_LIMIT = 1024 * 1024
METADATA_LIMIT = 4 * 1024 * 1024
ENTRY_LIMIT = 4096
DEPTH_LIMIT = 16
ARRAY_LIMIT = 32  # Local finite projection bounds, not upstream schema limits.
STRING_LIMIT = 128


class Refusal(Exception):
    """Fixed reason, optionally with nonsecret partial destination ownership."""
    def __init__(self, reason, owner=None):
        super().__init__(reason)
        self.owner = owner


def _parts(path):
    text = os.fspath(path)
    p = Path(text)
    if (not p.is_absolute() or '..' in p.parts or len(p.parts) < 2
            or str(p) != text):
        raise Refusal('absolute_canonical_path_required')
    return p


def _directory(path):
    p = _parts(path) if str(path) != '/' else Path('/')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in p.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def _identity(s):
    return s.st_dev, s.st_ino, s.st_uid


def _stamp(s):
    return (_identity(s), s.st_mode, s.st_nlink, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns)


def _regular(s, *, private=False, device=None):
    return (stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid()
            and s.st_nlink == 1 and (device is None or s.st_dev == device)
            and (not private or stat.S_IMODE(s.st_mode) == 0o600))


def _root_fd(owner):
    fd = _directory(owner.root)
    s = os.fstat(fd)
    if (_identity(s) != owner.identity or s.st_uid != os.getuid()
            or stat.S_IMODE(s.st_mode) != 0o700):
        os.close(fd)
        raise Refusal('home_identity_or_mode')
    return fd


def _unchanged(fd, name, before):
    if _stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)) != _stamp(before):
        raise Refusal('entry_changed')


@dataclass(frozen=True)
class NativeHome:
    root: Path
    identity: tuple

    def cleanup(self, *, processes_stopped, codex_executable, deadline):
        """Remove only this fresh home, after trusted runner shutdown evidence.

        Known auth is purged before other residue. Partial cleanup is possible;
        unknown entries, aliases, ownership or deadline retain remaining state.
        """
        result = {'status': 'incomplete', 'reason': None, 'auth_absent': None,
                  'home_absent': False, 'aliases_removed': 0}
        if processes_stopped is not True:
            result['reason'] = 'process_shutdown_unconfirmed'
            return result
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            result['reason'] = 'cleanup_deadline_invalid'
            return result
        parent = fd = None
        entries = 0
        alias_parent = None

        def budget(depth=0):
            if time.monotonic() >= deadline:
                raise Refusal('cleanup_deadline')
            if depth > DEPTH_LIMIT or entries > ENTRY_LIMIT:
                raise Refusal('cleanup_entry_limit')

        def walk(directory, relative=()):
            nonlocal entries, alias_parent
            budget(len(relative))
            # scandir is consumed under an entry budget instead of listdir's
            # unbounded allocation for an unexpectedly large native directory.
            with os.scandir(directory) as iterator:
                for item in iterator:
                    entries += 1
                    budget(len(relative))
                    name = item.name
                    s = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if s.st_uid != self.identity[2] or s.st_dev != self.identity[0]:
                        raise Refusal('cleanup_entry_owner_or_device')
                    if stat.S_ISDIR(s.st_mode):
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        try:
                            if _identity(os.fstat(child)) != _identity(s):
                                raise Refusal('cleanup_directory_changed')
                            walk(child, relative+(name,))
                        finally:
                            os.close(child)
                        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
                        if _identity(current) != _identity(s) or not stat.S_ISDIR(current.st_mode):
                            raise Refusal('cleanup_directory_changed')
                        os.rmdir(name, dir_fd=directory)
                    elif _regular(s, device=self.identity[0]):
                        _unchanged(directory, name, s)
                        os.unlink(name, dir_fd=directory)
                    elif stat.S_ISLNK(s.st_mode):
                        shape = (len(relative) == 3 and relative[:2] == ('tmp', 'arg0-macos')
                                 and re.fullmatch(r'codex-arg0[A-Za-z0-9]{6}', relative[2])
                                 and name in ('applypatch', 'apply_patch'))
                        if (not shape or s.st_nlink != 1 or result['aliases_removed'] >= 2
                                or (alias_parent is not None and alias_parent != relative)):
                            raise Refusal('cleanup_unknown_alias')
                        target = os.readlink(name, dir_fd=directory)
                        if target != os.fspath(_parts(codex_executable)):
                            raise Refusal('cleanup_alias_target')
                        _unchanged(directory, name, s)
                        if os.readlink(name, dir_fd=directory) != target:
                            raise Refusal('cleanup_alias_changed')
                        os.unlink(name, dir_fd=directory)  # Never dereference target.
                        alias_parent = relative
                        result['aliases_removed'] += 1
                    else:
                        raise Refusal('cleanup_unknown_entry')

        try:
            budget()
            root = _parts(self.root)
            parent = _directory(root.parent)
            try:
                s = os.stat(root.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                result.update(status='complete', reason=None, auth_absent=True, home_absent=True)
                return result
            if _identity(s) != self.identity:
                raise Refusal('home_identity_or_mode')
            fd = _root_fd(self)
            try:
                auth = os.stat('auth.json', dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                result['auth_absent'] = True
            else:
                if not _regular(auth, private=True, device=self.identity[0]):
                    raise Refusal('cleanup_auth_unsafe')
                _unchanged(fd, 'auth.json', auth)
                os.unlink('auth.json', dir_fd=fd)
                result['auth_absent'] = True
            walk(fd)
            budget()
            current = os.stat(root.name, dir_fd=parent, follow_symlinks=False)
            if _identity(current) != self.identity or not stat.S_ISDIR(current.st_mode):
                raise Refusal('cleanup_root_changed')
            os.rmdir(root.name, dir_fd=parent)
            result.update(status='complete', reason=None, home_absent=True)
        except Refusal as exc:
            result['reason'] = str(exc)
        except (OSError, TypeError, ValueError):
            result['reason'] = 'cleanup_inspection_failed'
        finally:
            for descriptor in (fd, parent):
                if descriptor is not None:
                    os.close(descriptor)
        return result


def copy_native_home(source_file, destination_home):
    """Copy one explicit 0600, one-link file; never interpret or hash its bytes."""
    source = _parts(source_file)
    destination = _parts(destination_home)
    source_parent = source_fd = parent = root_fd = target_fd = None
    owner = None
    try:
        source_parent = _directory(source.parent)
        source_fd = os.open(source.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source_parent)
        before = os.fstat(source_fd)
        if not _regular(before, private=True) or not 0 < before.st_size <= AUTH_LIMIT:
            raise Refusal('source_type_owner_mode_or_size')
        parent = _directory(destination.parent)
        if os.fstat(parent).st_uid != os.getuid():
            raise Refusal('destination_parent_owner')
        os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        info = os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        owner = NativeHome(destination, _identity(info))
        root_fd = _root_fd(owner)
        target_fd = os.open('auth.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=root_fd)
        if not _regular(os.fstat(target_fd), private=True, device=owner.identity[0]):
            raise Refusal('new_file_mode')
        total = 0
        while True:
            block = os.read(source_fd, min(65536, AUTH_LIMIT-total+1))
            if not block:
                break
            total += len(block)
            if total > AUTH_LIMIT:
                raise Refusal('source_grew_past_limit')
            remaining = memoryview(block)
            while remaining:
                n = os.write(target_fd, remaining)
                if n <= 0:
                    raise Refusal('short_write')
                remaining = remaining[n:]
        if total != before.st_size or _stamp(os.fstat(source_fd)) != _stamp(before):
            raise Refusal('source_changed_during_copy')
        target = os.fstat(target_fd)
        if not _regular(target, private=True, device=owner.identity[0]) or target.st_size != total:
            raise Refusal('destination_changed_during_copy')
        _unchanged(root_fd, 'auth.json', target)
        check_root = _root_fd(owner)
        os.close(check_root)
        os.fsync(target_fd)
        os.fsync(root_fd)
        return owner
    except BaseException as exc:
        # A caller's deadline exception or KeyboardInterrupt can arrive after
        # partial bytes exist. Custody must survive those exceptions too; this
        # copy never launches a process, so its exact owned home can be cleaned.
        if owner is not None:
            try:
                if target_fd is not None:
                    closing, target_fd = target_fd, None
                    os.close(closing)
                cleanup = owner.cleanup(processes_stopped=True, codex_executable='/unused-codex',
                                        deadline=time.monotonic()+5)
                if cleanup['status'] != 'complete':
                    raise Refusal('copy_failed_cleanup_unconfirmed')
            except BaseException:
                # Cleanup itself may be interrupted. Return only a fixed reason
                # and the original identity so the runner can reconcile custody.
                raise Refusal('copy_failed_cleanup_unconfirmed', owner) from None
        if isinstance(exc, Refusal):
            raise exc from None
        reason = 'copy_os_error' if isinstance(exc, OSError) else 'copy_interrupted'
        raise Refusal(reason) from None
    finally:
        for fd in (target_fd, root_fd, parent, source_fd, source_parent):
            if fd is not None:
                os.close(fd)


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError('nonfinite')


def _selectors(row):
    values, states = {}, {}

    def enum(key, allowed, *, required=False, aliases=None):
        if key not in row:
            values[key] = None
            states[key] = 'missing_required' if required else 'defaulted'
        elif row[key] is None:
            values[key] = None
            states[key] = 'malformed' if required else 'null'
        elif type(row[key]) is not str:
            values[key] = None; states[key] = 'malformed'
        else:
            normalized = (aliases or {}).get(row[key], row[key])
            values[key] = normalized if normalized in allowed else None
            states[key] = 'explicit' if normalized in allowed else 'unrecognized'

    enum('shell_type', {'unified_exec', 'disabled'}, required=True,
         aliases={s: 'unified_exec' for s in ('default', 'local', 'shell_command')})
    enum('tool_mode', {'direct', 'code_mode', 'code_mode_only'})
    enum('apply_patch_tool_type', {'freeform'})
    enum('multi_agent_version', {'disabled', 'v1', 'v2'})
    for key in ('supports_search_tool', 'use_responses_lite'):
        if key not in row:
            values[key] = False; states[key] = 'defaulted'
        elif type(row[key]) is bool:
            values[key] = row[key]; states[key] = 'explicit'
        else:
            values[key] = None; states[key] = 'malformed'
    for key, known, default in (
            ('input_modalities', {'text': 1, 'image': 2, 'audio': 4}, 3),
            ('experimental_supported_tools', {'send_user_message_async': 1, 'clock': 2}, None)):
        values[key] = default
        if key not in row:
            states[key] = 'defaulted' if default is not None else 'missing_required'
            continue
        raw = row[key]
        if (type(raw) is not list or len(raw) > ARRAY_LIMIT
                or any(type(v) is not str or len(v.encode('utf-8')) > STRING_LIMIT for v in raw)):
            values[key] = None; states[key] = 'malformed'
            continue
        unique = set(raw)
        unknown = sum(v not in known for v in raw)
        duplicates = len(raw)-len(unique)
        mask = sum(known[v] for v in unique if v in known)
        values[key] = mask if key == 'input_modalities' else {
            'known_mask': mask, 'unknown_count': unknown,
            'duplicate_count': duplicates, 'total_count': len(raw)}
        states[key] = 'unrecognized' if unknown else ('malformed' if duplicates else 'explicit')
    return values, states


def project_model_metadata(owner, requested_model):
    """Finite disk-cache compatibility only, never runtime catalog proof.

    The runner compares compatibility's canonical digest with its frozen plan.
    Missing or unknown selectors never teach a new acceptable expectation.
    """
    result = {'status': 'read_refused', 'match_count': 0, 'cache_read_bytes': 0,
              'provenance': 'owned_native_home_disk_cache',
              'runtime_registry_qualified': False, 'compatibility': None}
    fd = cache_fd = None
    try:
        if (type(requested_model) is not str
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', requested_model)):
            raise Refusal('model_identifier')
        fd = _root_fd(owner)
        cache_fd = os.open('models_cache.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        before = os.fstat(cache_fd)
        if (not _regular(before, device=owner.identity[0])
                or stat.S_IMODE(before.st_mode) & 0o7022
                or not 0 < before.st_size <= METADATA_LIMIT):
            raise Refusal('cache_type_owner_mode_or_size')
        chunks = []
        total = 0
        while True:
            block = os.read(cache_fd, min(65536, METADATA_LIMIT-total+1))
            if not block:
                break
            total += len(block)
            if total > METADATA_LIMIT:
                raise Refusal('cache_size')
            chunks.append(block)
        if total != before.st_size or _stamp(os.fstat(cache_fd)) != _stamp(before):
            raise Refusal('cache_changed')
        _unchanged(fd, 'models_cache.json', before)
        check_root = _root_fd(owner)
        os.close(check_root)
        result['cache_read_bytes'] = total
        document = json.loads(b''.join(chunks), object_pairs_hook=_strict_object, parse_constant=_nonfinite)
        models = document.get('models') if type(document) is dict else None
        if type(models) is not list or len(models) > 1000:
            result['status'] = 'schema_unknown'
            return result
        matches = [row for row in models if type(row) is dict and row.get('slug') == requested_model]
        result['match_count'] = len(matches)
        if len(matches) != 1:
            result['status'] = 'model_missing_or_duplicate'
            return result
        values, states = _selectors(matches[0])
        result['compatibility'] = {'schema_version': 1, 'model': requested_model,
                                   'selectors': values, 'field_states': states}
        if any(s in ('missing_required', 'malformed', 'unrecognized') for s in states.values()):
            result['status'] = 'capability_unknown'
        elif values['shell_type'] == 'disabled':
            result['status'] = 'disabled'
        elif values['tool_mode'] not in ('code_mode', 'code_mode_only'):
            result['status'] = 'unsupported_tool_mode'
        else:
            result['status'] = 'recognized'
    except FileNotFoundError:
        result['status'] = 'cache_unavailable'
    except (ValueError, UnicodeError, RecursionError):
        result['status'] = 'schema_unknown'
    except (OSError, Refusal, TypeError):
        result['status'] = 'read_refused'
    finally:
        for descriptor in (cache_fd, fd):
            if descriptor is not None:
                os.close(descriptor)
    return result
