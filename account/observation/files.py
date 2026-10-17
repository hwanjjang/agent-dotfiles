"""Small POSIX private-file boundary; all descendants use directory descriptors."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import time
import uuid

ROOT = ('.agents', 'agent-dotfiles', 'observations')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class UnsafeStore(ValueError):
    pass


class BusyStore(TimeoutError):
    pass


def check_private(fd, directory=False):
    info = os.fstat(fd)
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if (not expected(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or (not directory and info.st_nlink != 1)):
        raise UnsafeStore('unsafe_store_object')


def export_new(destination, value):
    """Publish a new local artifact without following links or replacing a file.

    The caller holds the observation guard through this operation. The existing
    destination directory is explicit; no directory is created or traversed by link.
    """
    path = Path(destination)
    if not path.is_absolute() or any(part in {'.', '..'} for part in path.parts):
        raise UnsafeStore('export_path')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    temporary = '.case-export-' + uuid.uuid4().hex
    try:
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = child
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(encoded(value)); stream.flush(); os.fsync(fd)
            # Hard-link publication is atomic and refuses every existing target,
            # including symlinks; no overwrite race is possible.
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
        finally:
            os.close(fd)
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)
    finally:
        os.close(parent)


class Files:
    def __init__(self, fd):
        self.fd = fd

    @classmethod
    @contextmanager
    def open(cls, home, create=False):
        fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for index, name in enumerate(ROOT):
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                    # Retry also syncs an entry left by an interrupted mkdir.
                    os.fsync(fd)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                if index == len(ROOT) - 1:
                    check_private(fd, directory=True)
            yield cls(fd)
        finally:
            os.close(fd)

    @contextmanager
    def directory(self, path=(), create=False):
        fd = os.dup(self.fd)
        try:
            for name in path:
                if not name or '/' in name or name in {'.', '..'}:
                    raise UnsafeStore('unsafe_store_path')
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                    os.fsync(fd)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                check_private(fd, directory=True)
            yield fd
        finally:
            os.close(fd)

    @contextmanager
    def guard(self, create=False, timeout=1.0):
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open('store.lock', flags | (os.O_CREAT if create else 0), 0o600, dir_fd=self.fd)
        try:
            check_private(fd)
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise BusyStore('store_busy') from None
                    time.sleep(0.01)
            yield
        finally:
            os.close(fd)

    def read(self, path, limit=1048576):
        with self.directory(path[:-1]) as parent:
            fd = os.open(path[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                check_private(fd)
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    body = stream.read(limit + 1)
                if len(body) > limit:
                    raise UnsafeStore('oversized_store_record')
                return json.loads(body)
            finally:
                os.close(fd)

    def write(self, path, value):
        with self.directory(path[:-1], create=True) as parent:
            try:
                info = os.stat(path[-1], dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise UnsafeStore('unsafe_store_target')
            except FileNotFoundError:
                pass
            temporary = '.pending-' + uuid.uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    stream.write(encoded(value))
                    stream.flush()
                    os.fsync(fd)
                os.replace(temporary, path[-1], src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                os.close(fd)
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass

    def names(self, path):
        try:
            with self.directory(path) as parent:
                return sorted(os.listdir(parent))
        except FileNotFoundError:
            return []

    def unlink(self, path):
        try:
            with self.directory(path[:-1]) as parent:
                os.unlink(path[-1], dir_fd=parent)
                os.fsync(parent)
        except FileNotFoundError:
            pass

    def clear(self, path):
        """Remove an owned subtree by descriptors, including unsafe leaf links.

        Cleanup must not depend on readable JSON or private modes. Directory
        descriptors and O_NOFOLLOW keep links from redirecting deletion outside
        the owned tree; ordinary reads still enforce the stricter private modes.
        """
        if not path or any(not isinstance(name, str) or not name or '/' in name
                           or name in {'.', '..'} for name in path):
            raise UnsafeStore('unsafe_store_path')

        def remove(parent, name):
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=parent)
                    try:
                        for entry in os.listdir(child):
                            remove(child, entry)
                        os.fsync(child)
                    finally:
                        os.close(child)
                    os.rmdir(name, dir_fd=parent)
                else:
                    os.unlink(name, dir_fd=parent)
                os.fsync(parent)
            except FileNotFoundError:
                pass

        try:
            with self.directory(path[:-1]) as parent:
                remove(parent, path[-1])
        except FileNotFoundError:
            pass
