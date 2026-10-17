"""Account-local, guarded file transactions. Never follows destination symlinks."""
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import tempfile
import uuid
from contextlib import contextmanager

STATE_DIR = '.agents/agent-dotfiles/state'
RECEIPT = STATE_DIR + '/installed.json'
PRESERVED_SKILLS = {'paseo', 'paseo-advisor', 'paseo-committee', 'paseo-handoff', 'paseo-help', 'paseo-plugin'}


def managed_target(name):
    """Finite config destinations plus the selected payload namespaces."""
    if re.fullmatch(r'\.(?:agents|codex|claude|hermes)/skills/[a-z0-9-]+', name):
        return Path(name).name not in PRESERVED_SKILLS
    return (name.startswith('.agents/agent-dotfiles/bundle/')
            or name.startswith('.codex/hooks/')
            or name in {RECEIPT, '.agents/bin/planning-hook.py',
                        '.claude/hooks/planning-with-files-dispatch.sh', '.codex/AGENTS.md',
                        '.claude/CLAUDE.md', '.hermes/SOUL.md', '.codex/hooks.json',
                        '.claude/settings.json', '.codex/config.toml', '.claude.json'})


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


def put(path, value):
    displaced = None
    if path.is_dir() and not path.is_symlink():
        # Keep the original directory intact until its replacement is in place.
        displaced = path.parent / ('.agent-dotfiles-displaced-' + uuid.uuid4().hex)
        os.replace(path, displaced)
    try:
        _put_file(path, value)
    except Exception:
        if displaced is not None and not path.exists() and not path.is_symlink():
            os.replace(displaced, path)
        raise
    else:
        if displaced is not None:
            shutil.rmtree(displaced)


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


def restore(path, entry, saved):
    if entry['kind'] == 'directory':
        put(path, None)
        shutil.copytree(saved, path, symlinks=True)
    elif entry['kind'] == 'file':
        put(path, {'data': saved.read_bytes(), 'mode': entry['mode']})
    else:
        put(path, {'link': entry['value']} if entry['kind'] == 'link' else None)


def transact(home, plan, changes):
    require(all(managed_target(name) for name in changes), 'Unsupported transaction destination')
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
    journal = dict(version=1, home=str(home), status='pending', before=plan['before'],
                   after=plan['after'], originals=originals)
    write(folder / 'journal.json', encoded(journal))
    done = []
    try:
        for name, value in changes.items():
            # Detect changes between preview and each write, including the receipt.
            require(observed(safe(home, name)) == plan['before'][name], f'Concurrent change: {name}')
            done.append(name)
            put(safe(home, name), value)
        for name in changes:
            require(observed(safe(home, name)) == plan['after'][name], f'Post-write mismatch: {name}')
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
                restore(safe(home, name), entry, folder / entry['saved'])
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
            and journal.get('status') in ('applied', 'pending', 'recovery-required'), 'Transaction cannot be rolled back')
    for name, entry in journal['originals'].items():
        require(managed_target(name), 'Unsupported rollback destination')
        path = safe(home, name)
        require(observed(path) in (journal['before'][name], journal['after'][name]),
                f'Rollback would overwrite later changes: {name}')
        require(entry['saved'].isdigit(), 'Invalid backup reference')
        saved = folder / entry['saved']
        if entry['kind'] in ('file', 'directory'):
            require(observed(saved) is not None, 'Missing backup')
            # Backup file permissions are private; compare its content, not storage mode.
            original = dict(observed(saved))
            original['mode'] = journal['before'][name]['mode']
            require(original == journal['before'][name], 'Backup content changed')
    return folder, journal


def rollback(home, ident):
    folder, journal = rollback_plan(home, ident)
    for name, entry in reversed(list(journal['originals'].items())):
        path = safe(home, name)
        actual = observed(path)
        if actual == journal['before'][name]:
            continue
        require(actual == journal['after'][name], f'Concurrent rollback change: {name}')
        restore(path, entry, folder / entry['saved'])
        require(observed(path) == journal['before'][name], f'Rollback mismatch: {name}')
    journal['status'] = 'rolled-back'
    write(folder / 'journal.json', encoded(journal))
