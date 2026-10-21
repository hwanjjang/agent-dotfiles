"""Account-local, guarded file transactions. Never follows destination symlinks."""
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import tempfile
import uuid
from contextlib import contextmanager

STATE_DIR = '.agents/agent-dotfiles/state'
RECEIPT = STATE_DIR + '/installed.json'
PRESERVED_SKILLS = {'paseo', 'paseo-advisor', 'paseo-committee', 'paseo-handoff', 'paseo-help', 'paseo-plugin'}


INSTRUCTION_ENTRIES = ('.codex/AGENTS.md', '.claude/CLAUDE.md', '.hermes/SOUL.md')


def managed_target(name, home=None):
    """Finite config destinations plus the selected payload namespaces.

    An instruction file that a client entry links to is accepted only while that link exists.
    """
    if re.fullmatch(r'\.(?:agents|codex|claude|hermes)/skills/[a-z0-9-]+', name):
        return Path(name).name not in PRESERVED_SKILLS
    return (name.startswith('.agents/agent-dotfiles/bundle/')
            or name.startswith('.codex/hooks/')
            or name in {RECEIPT, '.agents/bin/planning-hook.py', '.agents/bin/observation-hook.py',
                        '.claude/hooks/planning-with-files-dispatch.sh', '.codex/hooks.json',
                        '.claude/settings.json', '.codex/config.toml', '.claude.json', *INSTRUCTION_ENTRIES}
            or (home is not None and name in linked_instruction_files(home)))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(home, name):
    rel = Path(name)
    require(not rel.is_absolute() and '..' not in rel.parts and str(rel) == name
            and name not in ('', '.'), 'Invalid account-relative path')
    path = home / rel
    for parent in path.parents:
        if parent == home:
            break
        require(not parent.is_symlink() and (not parent.exists() or parent.is_dir()),
                f'Unsafe parent for {name}')
    return path


def observed(path):
    if path.is_symlink():
        return {'link': os.readlink(path)}
    if not path.exists():
        return None
    if path.is_file():
        return {'sha256': digest(path.read_bytes()), 'mode': path.stat().st_mode & 0o777}
    require(path.is_dir(), 'Unsupported account file type')
    # Symlink entries are fingerprints of links, never their external targets.
    tree = {}
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in sorted(dirs + files):
            item = Path(root) / name
            key = str(item.relative_to(path))
            tree[key] = ({'directory': True, 'mode': item.stat().st_mode & 0o777}
                         if item.is_dir() and not item.is_symlink() else observed(item))
    return {'tree': digest(encoded(tree)), 'mode': path.stat().st_mode & 0o777}


def instruction_path_allowed(rel):
    """A Markdown file outside the installer's payload, state, skills and hook trees."""
    parts = Path(rel).parts
    return (rel.endswith('.md') and 'skills' not in parts
            and not rel.startswith(('.agents/agent-dotfiles/', '.codex/hooks/', '.claude/hooks/')))


def instruction_storage(home, name):
    """Account-relative file holding an instruction entry: itself, or the one file its link names.

    Only one in-account link level to a regular Markdown file is followed. Opening the entry must
    reach the same file as the lexical path (the kernel applies `..` after a link inside the link's
    target and fails on a missing or non-directory component), so an edit never lands on a file the
    client does not open, leaves the account, crosses another link or touches the payload.
    """
    path = safe(home, name)
    if not path.is_symlink():
        return name
    target = Path(os.path.normpath(path.parent / os.readlink(path)))
    require(target.is_relative_to(home) and target != home, 'Instruction link leaves the account')
    try:
        opened, named = os.stat(path), os.lstat(target)
    except OSError:
        opened = named = None
    # What a client opens through the link, resolved by the kernel, must be the regular file named here.
    require(opened is not None and stat.S_ISREG(named.st_mode) and os.path.samestat(opened, named),
            'Instruction link must name one regular file in the account')
    rel = target.relative_to(home).as_posix()
    safe(home, rel)
    require(rel in INSTRUCTION_ENTRIES or rel.endswith('.md'), 'Instruction link must name a Markdown file')
    require(rel in INSTRUCTION_ENTRIES or instruction_path_allowed(rel), 'Instruction link names a protected path')
    return rel


def linked_instruction_files(home):
    """Files that an existing, valid instruction link currently names."""
    found = set()
    for name in INSTRUCTION_ENTRIES:
        try:
            if safe(home, name).is_symlink():
                found.add(instruction_storage(home, name))
        except ValueError:
            continue
    return found


def read(path):
    require(not path.is_symlink(), 'Refusing to edit a symlinked configuration file')
    require(not path.exists() or path.is_file(), 'Expected a regular configuration file')
    return path.read_bytes() if path.exists() else b''


def write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.agent-dotfiles-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)


def _below(home, name, create):
    """File descriptor of the directory holding `name`, opened below `home` one component at a time
    without following a link, so a directory replaced by a link after the path checks fails here."""
    fd = None
    try:
        fd = os.open(home, _DIRECTORY)
        for part in Path(name).parts[:-1]:
            try:
                child = os.open(part, _DIRECTORY, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o777, dir_fd=fd)
                child = os.open(part, _DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except OSError as error:
        if fd is not None:
            os.close(fd)
        raise ValueError(f'Unsafe parent for {name}') from error


def _entry(parent, leaf):
    try:
        return os.lstat(leaf, dir_fd=parent)
    except FileNotFoundError:
        return None


def _put_below(home, name, value, displaced):
    try:
        parent = _below(home, name, create=value is not None)
    except ValueError:
        if value is None and not (home / name).parent.exists():
            return
        raise
    leaf = Path(name).name
    try:
        moved = False
        info = _entry(parent, leaf)
        if info is not None and stat.S_ISDIR(info.st_mode):
            require(displaced is not None and observed(displaced) is None,
                    'Directory replacement requires an unused journaled displacement')
            os.replace(leaf, displaced, src_dir_fd=parent)
            moved = True
        try:
            _put_file_below(parent, leaf, value)
        except Exception:
            if moved and _entry(parent, leaf) is None:
                os.replace(displaced, leaf, dst_dir_fd=parent)
            raise
    finally:
        os.close(parent)


def _put_file_below(parent, leaf, value):
    if value is None:
        try:
            os.unlink(leaf, dir_fd=parent)
        except FileNotFoundError:
            pass
        return
    tmp = '.agent-dotfiles-' + uuid.uuid4().hex
    try:
        if 'link' in value:
            os.symlink(value['link'], tmp, dir_fd=parent)
        else:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0), 0o600, dir_fd=parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(value['data'])
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), value['mode'])
        os.replace(tmp, leaf, src_dir_fd=parent, dst_dir_fd=parent)
    finally:
        if _entry(parent, tmp) is not None:
            os.unlink(tmp, dir_fd=parent)


def put(path, value, displaced=None, home=None):
    """Replace `path` with `value`. With `home`, nothing below it is reached through a link."""
    if home is not None:
        return _put_below(home, path.relative_to(home).as_posix(), value, displaced)
    moved = False
    if path.is_dir() and not path.is_symlink():
        # The journal names this private location before the directory moves.
        require(displaced is not None and observed(displaced) is None,
                'Directory replacement requires an unused journaled displacement')
        os.replace(path, displaced)
        moved = True
    try:
        _put_file(path, value)
    except Exception:
        if moved and not path.exists() and not path.is_symlink():
            os.replace(displaced, path)
        raise
    # Retain the original under the private transaction directory for recovery.


def _put_file(path, value):
    if value is None:
        if path.exists() or path.is_symlink():
            path.unlink()
    elif 'link' in value:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / ('.agent-dotfiles-' + uuid.uuid4().hex)
        try:
            tmp.symlink_to(value['link'], target_is_directory=True)
            os.replace(tmp, path)
        finally:
            if tmp.is_symlink():
                tmp.unlink()
    else:
        write(path, value['data'], value['mode'])


def desired(value):
    if value is None or 'link' in value:
        return value
    return {'sha256': digest(value['data']), 'mode': value['mode']}


@contextmanager
def lock(home):
    folder = safe(home, STATE_DIR)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not folder.is_symlink(), 'Unsafe state directory')
    path = safe(home, STATE_DIR + '/lock')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as error:
        raise ValueError('Another account transaction is active') from error
    finally:
        os.close(fd)


def capture(path, destination):
    if path.is_symlink():
        return {'kind': 'link', 'value': os.readlink(path)}
    if not path.exists():
        return {'kind': 'absent'}
    if path.is_dir():
        shutil.copytree(path, destination, symlinks=True)
        return {'kind': 'directory'}
    shutil.copyfile(path, destination)
    os.chmod(destination, 0o600)
    return {'kind': 'file', 'mode': path.stat().st_mode & 0o777}


def restore(path, entry, saved, expected, home=None):
    if entry['kind'] == 'directory':
        displaced = saved.parent / entry['displaced']
        require(observed(displaced) == expected, 'Displaced original changed or missing')
        put(path, None, home=home)
        # If interrupted between unlink and rename, the journal still owns both paths.
        if home is None:
            os.replace(displaced, path)
        else:
            parent = _below(home, path.relative_to(home).as_posix(), create=True)
            try:
                os.replace(displaced, path.name, dst_dir_fd=parent)
            finally:
                os.close(parent)
    elif entry['kind'] == 'file':
        put(path, {'data': saved.read_bytes(), 'mode': entry['mode']}, home=home)
    else:
        put(path, {'link': entry['value']} if entry['kind'] == 'link' else None, home=home)


def transact(home, plan, changes):
    require(all(managed_target(name, home) for name in changes), 'Unsupported transaction destination')
    for name, expected in plan['before'].items():
        require(observed(safe(home, name)) == expected, f'Account changed since preview: {name}')
    if not changes:
        return None
    ident = uuid.uuid4().hex
    folder = safe(home, STATE_DIR + '/transactions/' + ident)
    folder.mkdir(parents=True, mode=0o700)
    originals = {}
    for index, name in enumerate(changes):
        originals[name] = capture(safe(home, name), folder / str(index))
        originals[name]['saved'] = str(index)
        if originals[name]['kind'] == 'directory':
            originals[name]['displaced'] = 'displaced-' + str(index)
    journal = dict(version=1, home=str(home), status='pending', before=plan['before'],
                   after=plan['after'], originals=originals)
    write(folder / 'journal.json', encoded(journal))
    done = []
    try:
        for name, value in changes.items():
            # Detect changes between preview and each write, including the receipt.
            require(observed(safe(home, name)) == plan['before'][name], f'Concurrent change: {name}')
            done.append(name)
            entry = originals[name]
            displaced = folder / entry['displaced'] if entry['kind'] == 'directory' else None
            put(safe(home, name), value, displaced=displaced, home=home)
        for name in changes:
            require(observed(safe(home, name)) == plan['after'][name], f'Post-write mismatch: {name}')
        for name, expected in plan['before'].items():
            # Inputs that were fingerprinted but not changed, such as instruction links, must still be as previewed.
            require(name in changes or observed(safe(home, name)) == expected, f'Concurrent change: {name}')
        journal['status'] = 'applied'
        write(folder / 'journal.json', encoded(journal))
    except Exception as error:
        failures = []
        for name in reversed(done):
            try:
                actual = observed(safe(home, name))
                if actual == plan['before'][name]:
                    continue
                require(actual == plan['after'][name], 'Concurrent change during recovery')
                entry = originals[name]
                restore(safe(home, name), entry, folder / entry['saved'], plan['before'][name], home=home)
            except Exception:
                failures.append(name)
        journal['status'] = 'recovery-required' if failures else 'rolled-back'
        write(folder / 'journal.json', encoded(journal))
        raise ValueError(f'Transaction failed ({type(error).__name__}); {journal["status"]}; backup {ident}') from error
    return ident


def rollback_plan(home, ident):
    require(len(ident) == 32 and all(c in '0123456789abcdef' for c in ident), 'Invalid transaction ID')
    folder = safe(home, STATE_DIR + '/transactions/' + ident)
    journal = json.loads(read(safe(home, STATE_DIR + '/transactions/' + ident + '/journal.json')))
    require(journal.get('version') == 1 and journal.get('home') == str(home)
            and journal.get('status') in ('applied', 'pending', 'recovery-required', 'rolling-back'), 'Transaction cannot be rolled back')
    for name, entry in journal['originals'].items():
        require(managed_target(name, home), 'Unsupported rollback destination')
        path = safe(home, name)
        require(entry['saved'].isdigit(), 'Invalid backup reference')
        saved = folder / entry['saved']
        actual = observed(path)
        states = [journal['before'][name], journal['after'][name]]
        if entry['kind'] == 'directory':
            require(entry.get('displaced') == 'displaced-' + entry['saved'],
                    'Missing or invalid journaled displacement')
            displaced = observed(folder / entry['displaced'])
            if displaced is not None:
                require(displaced == journal['before'][name], 'Displaced original changed')
                if journal['status'] != 'applied':
                    states.append(None)  # Only a journaled in-progress operation may own a gap.
            if actual != journal['before'][name]:
                require(displaced == journal['before'][name], 'Displaced original missing')
        require(actual in states, f'Rollback would overwrite later changes: {name}')
        if entry['kind'] in ('file', 'directory'):
            require(observed(saved) is not None, 'Missing backup')
            # Backup file permissions are private; compare its content, not storage mode.
            original = dict(observed(saved))
            original['mode'] = journal['before'][name]['mode']
            require(original == journal['before'][name], 'Backup content changed')
    return folder, journal


def rollback(home, ident):
    folder, journal = rollback_plan(home, ident)
    journal['status'] = 'rolling-back'
    write(folder / 'journal.json', encoded(journal))
    for name, entry in reversed(list(journal['originals'].items())):
        path = safe(home, name)
        actual = observed(path)
        if actual == journal['before'][name]:
            continue
        gap = (actual is None and entry['kind'] == 'directory'
               and observed(folder / entry['displaced']) == journal['before'][name])
        require(actual == journal['after'][name] or gap, f'Concurrent rollback change: {name}')
        restore(path, entry, folder / entry['saved'], journal['before'][name], home=home)
        require(observed(path) == journal['before'][name], f'Rollback mismatch: {name}')
    journal['status'] = 'rolled-back'
    write(folder / 'journal.json', encoded(journal))
