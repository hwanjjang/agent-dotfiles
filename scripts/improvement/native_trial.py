"""Explicit frozen native-trial controller; no import-time runtime actions."""
import json
import argparse
import fcntl
import base64
import hashlib
import os
from pathlib import Path
import platform
import re
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import native_trial_plan as plan
import native_execution
import native_isolation
import native_trial_protocol as protocol
from native_trial_owner import NativeHome, copy_native_home, project_model_metadata

LABEL = 'agent-dotfiles.native-trial'
EXECUTOR_SHA256 = '8a96f66d059d653e68bfd5f3c79337e6f1d7d170d80bf705eb7d0249b34c0ece'
DIRECT_PROFILE = native_execution.PROFILE.split('[model_providers.fixture]')[0].replace(
    'model_provider="fixture"', 'model_provider="openai"').replace(
    'cli_auth_credentials_store="file"',
    'cli_auth_credentials_store="file"\nforced_login_method="chatgpt"')


def private_write(path, payload):
    """Write an exclusively created supervisor file; no arbitrary overwrite."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def supported_host():
    plan.require(sys.version_info >= (3, 11), 'python_311_required')
    plan.require(sys.platform == 'darwin' and platform.machine() == 'arm64', 'unsupported_host')
    plan.require(threading.current_thread() is threading.main_thread(), 'main_thread_required')
    plan.require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'existing_alarm')


class PhaseClock:
    """Bound setup/observation blocking calls without replacing an ambient alarm."""
    def __enter__(self):
        self.previous = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self.expired)
        return self

    @staticmethod
    def expired(*_):
        raise plan.Refusal('deadline')

    def arm(self, deadline):
        signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))

    def cancel(self):
        signal.setitimer(signal.ITIMER_REAL, 0)

    def __exit__(self, *_):
        self.cancel()
        signal.signal(signal.SIGALRM, self.previous)


def fixed_failure(exc):
    # Never let arbitrary exception strings (including native diagnostics) enter
    # retained records. Expanded detail belongs in finite module projections.
    if isinstance(exc, plan.Refusal) and str(exc) in (
            'deadline', 'capture_limit', 'executor_setup', 'image_identity',
            'resource_exists', 'container_boundary', 'qualification_fixture',
            'native_owner', 'archive_changed', 'archive_bound', 'archive_unsafe',
            'control_command_failed', 'resource_inspect', 'volume_identity'):
        return str(exc)
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return 'interrupted'
    return 'operation'


class Journal:
    """Bound fixed-schema records, retaining separate cleanup/final reserves.

    The caller supplies only supervisor-owned projections. This byte accountant
    does not sanitize arbitrary native events and must never receive them.
    """
    def __init__(self, path, limit):
        if type(limit) is not int or not 65536 <= limit <= 262144:
            raise plan.Refusal('capture_budget')
        self.path = path
        parent = plan.directory(path.parent)
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent)
        finally:
            os.close(parent)
        info = path.lstat()
        self.identity = info.st_dev, info.st_ino, info.st_uid
        self.limit = limit
        self.used = 0
        self.index = 0
        self.lock = threading.Lock()

    @classmethod
    def resume(cls, path, limit):
        """Read bounded private immutable prior records; do not reset capacity."""
        folder = plan.directory(path)
        records = {}
        total = 0
        try:
            info = os.fstat(folder)
            plan.require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'recovery_records')
            with os.scandir(folder) as iterator:
                names = []
                for item in iterator:
                    plan.require(len(names) < 4096, 'recovery_records')
                    names.append(item.name)
            for index, name in enumerate(sorted(names), 1):
                match = re.fullmatch(r'([0-9]{3,4})-([a-z][a-z0-9_]{0,63})\.json', name)
                plan.require(match is not None and int(match[1]) == index, 'recovery_records')
                raw, _ = plan.read_relative(path, name, min(limit, 65536), 'recovery_records')
                entry = os.stat(name, dir_fd=folder, follow_symlinks=False)
                plan.require(stat.S_IMODE(entry.st_mode) == 0o600, 'recovery_records')
                total += len(raw)
                plan.require(total <= limit, 'recovery_records')
                value = json.loads(raw, object_pairs_hook=protocol.unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(plan.Refusal('recovery_records')))
                plan.require(isinstance(value, dict), 'recovery_records')
                records.setdefault(match[2], []).append(value)
            result = cls.__new__(cls)
            result.path, result.limit = path, limit
            result.identity = info.st_dev, info.st_ino, info.st_uid
            result.used, result.index = total, len(names)
            result.lock = threading.Lock()
            return result, records
        finally:
            os.close(folder)

    def save(self, label, value, *, cleanup=False, final=False):
        if not isinstance(label, str) or re.fullmatch('[a-z][a-z0-9_]{0,63}', label) is None:
            raise plan.Refusal('capture_label')
        raw = plan.encoded(value) + b'\n'
        with self.lock:
            ceiling = self.limit if final else self.limit - 16384 if cleanup else self.limit - 32768
            if self.used + len(raw) > ceiling:
                raise plan.Refusal('capture_limit')
            folder = plan.directory(self.path)
            try:
                info = os.fstat(folder)
                if (info.st_dev, info.st_ino, info.st_uid) != self.identity \
                        or stat.S_IMODE(info.st_mode) != 0o700:
                    raise plan.Refusal('capture_identity')
                self.index += 1
                name = f'{self.index:03d}-{label}.json'
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=folder)
                # Account the full attempted record once it exists. A partial
                # write/fsync failure cannot replenish retained-byte capacity.
                self.used += len(raw)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.fsync(folder)
                return self.path / name
            finally:
                os.close(folder)


def remove_control(root, identity, deadline):
    """Remove a bound fresh control tree after native-home cleanup.

    Only same-owner/device directories and one-link regular files are admitted.
    This helper has no alias exception: the native-home owner handles its own
    two source-qualified aliases before this outer cleanup is considered.
    """
    folder = plan.directory(root)
    parent = None
    count = 0
    root_device = os.fstat(folder).st_dev

    def short_stamp(info):
        return info.st_dev, info.st_ino, info.st_uid, info.st_mode

    def visit(fd, depth):
        nonlocal count
        if depth > 16:
            raise plan.Refusal('control_bound')
        for name in os.listdir(fd):
            count += 1
            if count > 4096 or time.monotonic() >= deadline:
                raise plan.Refusal('control_bound')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if info.st_uid != os.getuid() or info.st_dev != root_device:
                raise plan.Refusal('control_owner')
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if short_stamp(os.fstat(child)) != short_stamp(info):
                        raise plan.Refusal('control_changed')
                    # These are same-owner private staging directories, not
                    # native-home state. Restore owner traversal/removal rights
                    # through the already verified descriptor before walking.
                    os.fchmod(child, 0o700)
                    info = os.fstat(child)
                    visit(child, depth + 1)
                finally:
                    os.close(child)
                if short_stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)) != short_stamp(info):
                    raise plan.Refusal('control_changed')
                os.rmdir(name, dir_fd=fd)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                if plan.stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)) != plan.stamp(info):
                    raise plan.Refusal('control_changed')
                os.unlink(name, dir_fd=fd)
            else:
                raise plan.Refusal('control_type')

    try:
        info = os.fstat(folder)
        if (info.st_dev, info.st_ino, info.st_uid) != tuple(identity) \
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise plan.Refusal('control_identity')
        visit(folder, 0)
        parent = plan.directory(root.parent)
        info = os.stat(root.name, dir_fd=parent, follow_symlinks=False)
        if (info.st_dev, info.st_ino, info.st_uid) != tuple(identity):
            raise plan.Refusal('control_changed')
        os.rmdir(root.name, dir_fd=parent)
    finally:
        os.close(folder)
        if parent is not None:
            os.close(parent)


def bounded(argv, timeout, *, limit=12000, env=None, payload=None):
    """Bound a trusted control command; return transient output only.

    Output is never automatically journaled. The caller parses a fixed fact
    projection. Every stream and the owned unreaped process group is closed.
    """
    process = subprocess.Popen(argv, stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                               close_fds=True, env=env)
    selector = None
    chunks = {process.stdout: bytearray(), process.stderr: bytearray()}
    reason = None
    try:
        selector = selectors.DefaultSelector()
        for stream in chunks:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        position = 0
        if payload is not None:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE)
        deadline = time.monotonic() + timeout
        count = 0
        reason = None
        while selector.get_map():
            if time.monotonic() >= deadline:
                reason = 'timeout'
                break
            for key, _ in selector.select(min(.05, max(.001, deadline-time.monotonic()))):
                if key.fileobj is process.stdin:
                    if position == len(payload):
                        selector.unregister(process.stdin)
                        process.stdin.close()
                        continue
                    try:
                        position += os.write(key.fd, memoryview(payload)[position:position+65536])
                    except BlockingIOError:
                        pass
                    except BrokenPipeError:
                        reason = 'stdin_closed'
                        break
                else:
                    block = os.read(key.fd, 4096)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    keep = min(len(block), limit-count)
                    chunks[key.fileobj].extend(block[:keep])
                    count += keep
                    if keep < len(block):
                        reason = 'output_limit'
                        break
            if reason:
                break
        if reason is None:
            try:
                process.wait(timeout=max(.001, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                reason = 'timeout'
    finally:
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                reason = reason or 'group_signal_uncertain'
        process.wait(timeout=2)
        if selector is not None:
            selector.close()
        for stream in chunks:
            stream.close()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    return {'exit': process.returncode, 'stop_reason': reason,
            'stdout': chunks[process.stdout].decode(errors='replace'),
            'stderr': chunks[process.stderr].decode(errors='replace')}


def parse_process_query(result, pid):
    if result.get('exit') == 1 and not result.get('stdout', '').strip() \
            and not result.get('stderr', '').strip() and not result.get('stop_reason'):
        return None
    if result.get('exit') != 0 or result.get('stop_reason') or result.get('stderr', '').strip():
        raise plan.Refusal('process_query')
    parts = result.get('stdout', '').strip().split(None, 8)
    try:
        if len(parts) != 9:
            raise ValueError()
        actual, parent, group = (int(v) for v in parts[:3])
        if actual != pid or actual <= 0 or parent < 0 or group <= 0 or not parts[8].startswith('/'):
            raise ValueError()
    except (TypeError, ValueError):
        raise plan.Refusal('process_query') from None
    return {'pid': actual, 'ppid': parent, 'pgid': group,
            'start': ' '.join(parts[3:8]), 'exe': parts[8]}


def child_inventory(result):
    """An empty failed query is the only admitted no-child result."""
    if result.get('stop_reason') or result.get('stderr', '').strip():
        raise plan.Refusal('child_inventory')
    raw = result.get('stdout', '')
    if result.get('exit') == 1 and not raw.strip():
        return []
    values = raw.split()
    if result.get('exit') != 0 or not 0 < len(values) <= 8 \
            or any(not v.isascii() or not v.isdecimal() or int(v) <= 0 for v in values) \
            or len(set(values)) != len(values):
        raise plan.Refusal('child_inventory')
    return [int(v) for v in values]


def same_process(saved, current):
    return current is not None and all(saved.get(key) == current.get(key)
                                       for key in ('pid', 'pgid', 'start', 'exe'))


def owned_native_child(child, parent, runtime):
    """Only the two source-qualified direct children of the owned app-server."""
    return isinstance(child, dict) and parent.get('exe') == runtime['codex'] \
        and child.get('exe') in (runtime['code_mode_host'], runtime['docker']) \
        and type(child.get('pid')) is int and child['pid'] > 0 \
        and child.get('ppid') == parent['pid'] and child.get('pgid') == child['pid']


def resource_names(identity):
    suffix = hashlib.sha256(plan.encoded(identity)).hexdigest()[:24]
    executor = 'agent-dotfiles-trial-' + suffix
    return {'executor': executor, 'stage': executor + '-stage', 'volume': executor + '-runtime'}


def claim_attempt(selected):
    """Persist an exclusive attempt name; cleanup never deletes this claim."""
    data = selected.data
    root = Path(data['state_root'])
    root_fd = plan.directory(root)
    trial_fd = None
    identity = data['identity']
    try:
        info = os.fstat(root_fd)
        plan.require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'state_unsafe')
        try:
            os.mkdir(identity['trial_id'], 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        trial_fd = os.open(identity['trial_id'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                           dir_fd=root_fd)
        info = os.fstat(trial_fd)
        plan.require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'state_unsafe')
        try:
            os.mkdir(identity['attempt_id'], 0o700, dir_fd=trial_fd)
        except FileExistsError:
            raise plan.Refusal('attempt_exists') from None
        os.fsync(trial_fd)
        os.fsync(root_fd)
    finally:
        os.close(root_fd)
        if trial_fd is not None:
            os.close(trial_fd)
    attempt = root / identity['trial_id'] / identity['attempt_id']
    private_write(attempt / 'manifest.json', plan.encoded(data) + b'\n')
    return attempt


def owned_container(info, name, binding, expected_id=None):
    return isinstance(info, dict) and info.get('Name', '').lstrip('/') == name \
        and info.get('Config', {}).get('Labels', {}).get(LABEL) == binding \
        and plan.is_digest(info.get('Id')) \
        and (expected_id is None or info['Id'] == expected_id)


def container_boundary(info, *, names, image, binding, stage=False):
    """Inspect actual Docker settings; an argv alone is not a boundary proof."""
    try:
        name = names['stage' if stage else 'executor']
        host, mounts = info['HostConfig'], info['Mounts']
        memory = (256 if stage else 768) * 1024**2
        return owned_container(info, name, binding) and info['Image'] == image \
            and info['Config']['User'] == ('0:0' if stage else '65532:65532') \
            and host['NetworkMode'] == 'none' and host['ReadonlyRootfs'] is True \
            and host['Privileged'] is False and host['CapDrop'] == ['ALL'] \
            and host['SecurityOpt'] == ['no-new-privileges'] \
            and not any(host.get(k) for k in ('Binds', 'CapAdd', 'Devices', 'DeviceRequests',
                                            'DeviceCgroupRules', 'Sysctls', 'PortBindings')) \
            and host['PidMode'] == '' and host['IpcMode'] == 'private' \
            and host['CgroupnsMode'] == 'private' and host['UTSMode'] == '' \
            and host['UsernsMode'] == '' and host['Runtime'] == 'runc' \
            and host['Memory'] == memory and host['MemorySwap'] == memory \
            and host['PidsLimit'] == (64 if stage else 128) and host['NanoCpus'] == 1000000000 \
            and len(mounts) == 1 and mounts[0]['Type'] == 'volume' \
            and mounts[0]['Name'] == names['volume'] and mounts[0]['Destination'] == '/runtime' \
            and mounts[0]['RW'] is stage \
            and host['Tmpfs'] == ({'/tmp': 'rw,nosuid,nodev,noexec,size=32m,mode=1777'} if stage else {
                '/work': 'rw,nosuid,nodev,size=128m,mode=1777',
                '/tmp': 'rw,nosuid,nodev,noexec,size=32m,mode=1777'})
    except (KeyError, TypeError, AttributeError):
        return False


MATERIALIZE = r'''
import base64,hashlib,json,os,pathlib,sys
v=json.load(sys.stdin); root=pathlib.Path('/work/project');root.mkdir(mode=0o700)
for name in ('/work/codex','/work/home'):pathlib.Path(name).mkdir(mode=0o700)
actual=[]
for item in v['case']:
 p=pathlib.PurePosixPath(item['path'])
 assert not p.is_absolute() and '..' not in p.parts
 data=base64.b64decode(item['bytes'],validate=True)
 target=root.joinpath(*p.parts);target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(data)
 actual.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest()})
bundle=[]
expected_files=set(v['bundle_paths']); expected_dirs=set()
for name in expected_files:
 for parent in pathlib.PurePosixPath(name).parents:
  if str(parent)!='.':expected_dirs.add(str(parent))
actual_files=set();actual_dirs=set();entries=0
for folder,dirs,files in os.walk('/runtime/arm',followlinks=False):
 for name in dirs+files:
  entries+=1;assert entries<=128
  p=pathlib.Path(folder)/name;assert not p.is_symlink()
  relative=str(p.relative_to('/runtime/arm'))
  if p.is_dir():actual_dirs.add(relative)
  else:assert p.is_file();actual_files.add(relative)
assert actual_files==expected_files and actual_dirs==expected_dirs
for name in sorted(v['bundle_paths']):
 p=pathlib.PurePosixPath(name); assert not p.is_absolute() and '..' not in p.parts
 data=pathlib.Path('/runtime/arm').joinpath(*p.parts).read_bytes()
 bundle.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest()})
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def write_errno(path):
 try:
  with open(path,'ab') as f:pass
  return 0
 except OSError as e:return e.errno
status=dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
print(json.dumps({'uid':os.getuid(),'cap_eff':status['CapEff'].strip(),
 'no_new_privs':status['NoNewPrivs'].strip(),'seccomp':status['Seccomp'].strip(),
 'loopback_only':os.listdir('/sys/class/net')==['lo'],
 'case_digest':digest(sorted(actual,key=lambda x:x['path'])),
 'bundle_digest':digest(bundle),'arm_inventory_exact':True,'arm_write_errno':write_errno('/runtime/arm/'+v['entrypoint']),
 'mount_write_errno':write_errno('/runtime/mount-readonly-probe'),
 'runtime_script_verified':(hashlib.sha256(pathlib.Path('/runtime/qualification.js').read_bytes()).hexdigest()==v['runtime_script_sha256']) if v['runtime_script_sha256'] is not None else None,
 'runtime_digest':hashlib.sha256(pathlib.Path('/runtime/bin/codex').read_bytes()).hexdigest()}))
'''


class Controller:
    """One selected attempt; all external actions are explicit method calls."""
    def __init__(self, selected):
        self.lock_fd = None
        try:
            self.initialize(selected)
        except BaseException:
            self.release()
            raise

    def initialize(self, selected):
        self.selected = selected
        self.data = selected.data
        self.runtime = self.data['runtime']
        self.names = resource_names(self.data['identity'])
        self.attempt = claim_attempt(selected)
        self.lock_fd = os.open(self.attempt / 'coordinator.lock', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.journal = Journal(self.attempt / 'records', self.data['limits']['retained_bytes'])
        self.control = self.attempt / 'control'
        self.control.mkdir(mode=0o700)
        info = self.control.lstat()
        self.control_identity = info.st_dev, info.st_ino, info.st_uid
        self.env = {'HOME': str(self.control), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
        self.docker = [self.runtime['docker'], '--host', self.runtime['docker_host']]
        self.deadline = time.monotonic() + self.data['limits']['setup_seconds']
        self.cleanup_deadline = None
        self.ids = {}
        self.begun = set()
        self.volume_begun = False
        self.volume_owner = None
        self.home = None
        self.live = None
        self.launch_called = False
        self.launch_complete = False
        self.seen = {}
        self.process_lock = threading.Lock()
        self.watch_stop = threading.Event()
        self.watcher = None
        self.process_uncertain = False
        self.watch_error = False
        self.watch_diagnostic = None
        self.auth_copy_attempted = False
        self.auth_copy_succeeded = False
        self.observation = None
        self.challenge = None
        self.protected = {}
        self.qualification = None
        self.qualification_source = None
        self.primary = None
        self.capture_failed = False
        self.archive = None
        self.journal.save('control_owner', {'identity': list(self.control_identity)})
        self.journal.save('frozen_binding', {'manifest_digest': selected.digest,
                                           'identity': self.data['identity'],
                                           'profile': self.data['profile']})

    def command(self, args, *, cleanup=False, payload=None, timeout=15):
        deadline = self.cleanup_deadline if cleanup else self.deadline
        if deadline is None or time.monotonic() >= deadline:
            raise plan.Refusal('cleanup_deadline' if cleanup else 'deadline')
        result = bounded(self.docker + args, min(timeout, max(.01, deadline-time.monotonic())),
                         env=self.env, payload=payload)
        # Do not retain argv, arbitrary Docker diagnostics or native traffic.
        try:
            self.journal.save('control_command', {'exit': result['exit'], 'bound': result['stop_reason']},
                              cleanup=cleanup)
        except Exception:
            self.capture_failed = True
            if not cleanup:
                raise
        return result

    def checked(self, args, *, cleanup=False, payload=None):
        result = self.command(args, cleanup=cleanup, payload=payload)
        if result['exit'] != 0 or result['stop_reason']:
            raise plan.Refusal('control_command_failed')
        return result['stdout']

    def inspect(self, name, *, cleanup=False):
        shape = '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},' \
                '"Config":{"User":{{json .Config.User}},"Labels":{{json .Config.Labels}}},' \
                '"HostConfig":{{json .HostConfig}},"Mounts":{{json .Mounts}}}'
        result = self.command(['inspect', '--format', shape, name], cleanup=cleanup)
        if result['exit'] == 1 and not result['stop_reason'] \
                and result['stdout'].strip() in ('', '[]') and 'no such object' in result['stderr'].lower():
            return None
        if result['exit'] or result['stop_reason']:
            raise plan.Refusal('resource_inspect')
        return json.loads(result['stdout'])

    def setup(self):
        image = json.loads(self.checked(['image', 'inspect', '--format',
            '{"Id":{{json .Id}},"Architecture":{{json .Architecture}},"Os":{{json .Os}}}',
            self.runtime['image']]))
        plan.require(image == {'Id': self.runtime['image'], 'Architecture': 'arm64', 'Os': 'linux'}, 'image_identity')
        for name in (self.names['executor'], self.names['stage']):
            plan.require(self.inspect(name) is None, 'resource_exists')
        volume = self.command(['volume', 'inspect', self.names['volume']])
        plan.require(volume['exit'] == 1 and not volume['stop_reason']
                     and 'no such volume' in volume['stderr'].lower(), 'resource_exists')
        self.journal.save('resource_absence_preflight', {'containers_absent': True, 'volume_absent': True})
        staged = self.control / 'runtime'
        staged.mkdir(mode=0o700)
        # Verify/copy a bounded archive into owned state before the existing
        # source-bound extractor copies and hashes its private input object.
        raw_archive = self.control / 'executor.tar.gz'
        source = Path(self.runtime['executor_archive'])
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        hasher = hashlib.sha256()
        total = 0
        try:
            info = os.fstat(fd)
            plan.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'archive_unsafe')
            with raw_archive.open('xb') as target:
                while True:
                    block = os.read(fd, 65536)
                    if not block:
                        break
                    total += len(block)
                    plan.require(total <= 512 * 1024**2 and time.monotonic() < self.deadline, 'archive_bound')
                    hasher.update(block)
                    target.write(block)
            plan.require(plan.stamp(info) == plan.stamp(os.fstat(fd)), 'archive_changed')
        finally:
            os.close(fd)
        plan.require(hasher.hexdigest() == self.runtime['hashes']['executor_archive'], 'archive_changed')
        native_isolation.extract_verified(raw_archive, staged)
        if self.qualification_source is not None:
            private_write(staged / 'qualification.js', self.qualification_source)
            (staged / 'qualification.js').chmod(0o444)
        arm = staged / 'arm'
        arm.mkdir(mode=0o700)
        for (kind, name), content in self.selected.files.items():
            if kind != 'bundle':
                continue
            target = arm / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            private_write(target, content)
            target.chmod(0o444)
        for folder in sorted((p for p in arm.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            folder.chmod(0o555)
        arm.chmod(0o555)
        private_write(staged / 'mount-readonly-probe', b'SYNTHETIC_READONLY_MOUNT_PROBE')
        (staged / 'mount-readonly-probe').chmod(0o666)
        self.volume_begun = True
        self.journal.save('volume_create_intent', {'name': self.names['volume']})
        self.checked(['volume', 'create', '--label', LABEL+'='+self.selected.digest, self.names['volume']])
        volume = json.loads(self.checked(['volume', 'inspect', self.names['volume']]))
        plan.require(isinstance(volume, list) and len(volume) == 1, 'volume_identity')
        volume = volume[0]
        plan.require(volume.get('Name') == self.names['volume']
                     and volume.get('Labels', {}).get(LABEL) == self.selected.digest
                     and isinstance(volume.get('CreatedAt'), str) and volume['CreatedAt'], 'volume_identity')
        self.volume_owner = {key: volume[key] for key in ('Name', 'CreatedAt', 'Labels')}
        self.journal.save('volume_owner', self.volume_owner)
        self.create_container(stage=True)
        self.checked(['cp', str(staged)+'/.', self.ids['stage']+':/runtime'])
        self.checked(['rm', '-f', self.ids['stage']])
        self.create_container(stage=False)
        payload = {'case': [{'path': name, 'bytes': base64.b64encode(content).decode('ascii')}
                            for (kind, name), content in sorted(self.selected.files.items()) if kind == 'case'],
                   'bundle_paths': sorted(name for kind, name in self.selected.files if kind == 'bundle'),
                   'entrypoint': self.data['inputs']['entrypoint'],
                   'runtime_script_sha256': hashlib.sha256(self.qualification_source).hexdigest()
                       if self.qualification_source is not None else None}
        facts = json.loads(self.checked(['exec', '-i', self.ids['executor'], 'python3', '-c', MATERIALIZE],
                                        payload=plan.encoded(payload)))
        def input_digest(kind):
            return plan.digest([{'path': name, 'sha256': hashlib.sha256(content).hexdigest()}
                                for (role, name), content in sorted(self.selected.files.items()) if role == kind])
        expected = {'uid': 65532, 'cap_eff': '0000000000000000', 'no_new_privs': '1', 'seccomp': '2',
                    'loopback_only': True, 'case_digest': input_digest('case'),
                    'bundle_digest': input_digest('bundle'), 'arm_inventory_exact': True, 'arm_write_errno': facts.get('arm_write_errno'),
                    'mount_write_errno': 30,
                    'runtime_script_verified': True if self.qualification_source is not None else None,
                    'runtime_digest': EXECUTOR_SHA256}
        plan.require(type(facts.get('arm_write_errno')) is int and facts['arm_write_errno'] in (13, 30)
                     and plan.encoded(facts) == plan.encoded(expected), 'executor_setup')
        self.journal.save('executor_boundary', {'docker_settings_verified': True, **facts})

    def create_container(self, *, stage):
        key = 'stage' if stage else 'executor'
        name = self.names[key]
        self.begun.add(key)
        self.journal.save('container_create_intent', {'name': name})
        memory = '256m' if stage else '768m'
        args = ['create', '--name', name, '--label', LABEL+'='+self.selected.digest, '--pull', 'never',
                '--network', 'none', '--read-only', '--user', '0:0' if stage else '65532:65532',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64' if stage else '128',
                '--memory', memory, '--memory-swap', memory, '--cpus', '1', '--ipc', 'private',
                '--cgroupns', 'private', '--runtime', 'runc',
                '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777']
        if not stage:
            args += ['--tmpfs', '/work:rw,nosuid,nodev,size=128m,mode=1777']
        args += ['--mount', 'type=volume,src='+self.names['volume']+',dst=/runtime,volume-nocopy'+('' if stage else ',readonly'),
                 self.runtime['image'], 'python3', '-c', 'import time;time.sleep(240)']
        self.checked(args)
        info = self.inspect(name)
        plan.require(container_boundary(info, names=self.names, image=self.runtime['image'],
                                        binding=self.selected.digest, stage=stage), 'container_boundary')
        self.ids[key] = info['Id']
        self.journal.save('container_owner', {'kind': key, 'name': name, 'id': info['Id']})
        self.checked(['start', info['Id']])

    def prepare_qualification(self, *, credential_free=False):
        """Prepare the fixed case; credential_free is for a trusted outer owner.

        The public fixture CLI remains native_execution.py. Its outer owner
        must bind its own harness and establish shutdown/protected-file custody.
        """
        expected = plan.QUALIFICATION_FILES
        plan.require(self.selected.files == expected and self.data['inputs']['entrypoint'] ==
                     'skills/assigned/SKILL.md', 'qualification_fixture')
        protected = self.control / 'protected'
        protected.mkdir(mode=0o700)
        for name in ('host-only', 'history-only', 'credential-only', 'other-arm-only', 'evaluator-only'):
            payload = b'synthetic host-only canary' if name == 'host-only' else b'synthetic protected canary'
            target = protected / name
            private_write(target, payload)
            info = target.lstat()
            self.protected[target] = (plan.stamp(info), payload)
        target = protected / 'host-only.png'
        payload = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYPgPAAEDAQAIicLsAAAAAElFTkSuQmCC')
        private_write(target, payload)
        self.protected[target] = (plan.stamp(target.lstat()), payload)
        self.challenge = None if credential_free else secrets.token_hex(16)
        script = (plan.SOURCE / 'native_execution_command_skills.js').read_text().replace(
            'HOST_URI', json.dumps((protected / 'host-only').as_uri()))
        if not credential_free:
            script += "\nconst challengeResult=decoded(await tools.exec_command({cmd:'cat /work/project/transport-canary.txt',workdir:'/work/project',login:false,yield_time_ms:1000,max_output_tokens:128}));\nrequireTrue(challengeResult.exit_code===0&&!challengeResult.session_id&&typeof challengeResult.output==='string','challenge command');\ntext('REMOTE_CHALLENGE:'+challengeResult.output.trim());\n"
        self.qualification_source = script.encode('ascii')
        loader = native_execution.loader_source(len(self.qualification_source))
        from native_trial_qualification import Qualification
        self.qualification = None if credential_free else Qualification(loader, self.challenge)
        self.journal.save('qualification_preconditions', {'protected_files': len(self.protected),
            'known_existing_synthetic_only': True, 'challenge_remote_only': not credential_free,
            'challenge_value_or_hash_retained': False})
        return 'Use the selected remote executor. Run exactly one exec call with the following exact JavaScript, without changes or additional calls. Then return only the 32-character REMOTE_CHALLENGE value printed by that call. Do not infer it.\n\n' + loader

    def deliver_challenge(self):
        """Deliver the in-memory value only after the remote executor exists."""
        plan.require(isinstance(self.challenge, str) and len(self.challenge) == 32, 'qualification_fixture')
        program = "import pathlib,sys;p=pathlib.Path('/work/project/transport-canary.txt');f=p.open('xb');f.write(sys.stdin.buffer.read(32));f.close()"
        self.checked(['exec', '-i', self.ids['executor'], 'python3', '-c', program],
                     payload=self.challenge.encode('ascii'))

    def verify_protected(self):
        if not self.protected:
            return None
        try:
            for path, (stamp, payload) in self.protected.items():
                raw, _ = plan.read_file(path, 4096, 'protected_changed')
                plan.require(plan.stamp(path.lstat()) == stamp and raw == payload, 'protected_changed')
            return True
        except Exception:
            return False

    def process(self, pid, *, cleanup=False, watch=False):
        try:
            # Supervision must not inherit the model observation expiry. Each
            # query still has its own two-second bound; actual query failures
            # remain uncertainty. Cleanup stops/drains the watcher before close.
            deadline = time.monotonic()+2 if watch else (self.cleanup_deadline if cleanup else self.deadline)
            plan.require(deadline is not None and time.monotonic() < deadline, 'process_deadline')
            result = bounded(['/bin/ps', '-p', str(pid), '-o', 'pid=,ppid=,pgid=,lstart=,comm='],
                             min(2, max(.01, deadline-time.monotonic())), limit=2048, env=self.env)
            return parse_process_query(result, pid)
        except Exception:
            self.process_uncertain = True
            raise plan.Refusal('process_query') from None

    def watch(self):
        stage, parent_pid, child_pid, child_kind = 'start', None, None, None
        try:
            while not self.watch_stop.is_set():
                with self.process_lock:
                    parents = [dict(v) for v in self.seen.values() if v['exe'] == self.runtime['codex']]
                for saved in parents:
                    if self.watch_stop.is_set():
                        return
                    stage, parent_pid, child_pid, child_kind = 'parent_query', saved['pid'], None, None
                    current = self.process(saved['pid'], watch=True)
                    if self.watch_stop.is_set():
                        return
                    if current is None:
                        continue
                    plan.require(same_process(saved, current), 'parent_changed')
                    stage = 'child_inventory'
                    children = child_inventory(bounded(['/usr/bin/pgrep', '-P', str(saved['pid'])],
                        2, limit=1024, env=self.env))
                    if self.watch_stop.is_set():
                        return
                    for pid in children:
                        if self.watch_stop.is_set():
                            return
                        stage, child_pid = 'child_query', pid
                        child = self.process(pid, watch=True)
                        if self.watch_stop.is_set():
                            return
                        if child is None:
                            continue
                        child_kind = 'transport' if child['exe'] == self.runtime['docker'] else (
                            'helper' if child['exe'] == self.runtime['code_mode_host'] else 'other')
                        stage = 'child_owner'
                        # The pinned native transport spawns the configured
                        # Docker program directly in its own process group.
                        # The code-mode host is the other qualified child.
                        plan.require(owned_native_child(child, saved, self.runtime), 'child_owner')
                        with self.process_lock:
                            previous = self.seen.get(pid)
                            if previous is not None:
                                plan.require(same_process(previous, child), 'helper_changed')
                            else:
                                plan.require(len(self.seen) < 4, 'process_inventory')
                                self.journal.save('process_owner', child)
                                self.seen[pid] = child
                self.watch_stop.wait(.05)
        except Exception as exc:
            self.watch_error = True
            reason = str(exc) if isinstance(exc, plan.Refusal) and str(exc) in (
                'process_query', 'parent_changed', 'child_inventory', 'child_owner',
                'helper_changed', 'process_inventory', 'capture_limit') else 'operation'
            self.watch_diagnostic = {'stage': stage, 'parent_pid': parent_pid, 'child_pid': child_pid,
                                     'child_kind': child_kind, 'reason': reason}
            try:
                self.journal.save('watch_failure', self.watch_diagnostic)
            except Exception:
                self.capture_failed = True

    def on_launch(self, pid):
        # NativeSession already owns its unreaped Popen before this callback.
        info = self.process(pid)
        plan.require(info is not None and info['ppid'] == os.getpid()
                     and info['pgid'] == pid and info['exe'] == self.runtime['codex'], 'native_owner')
        self.journal.save('process_owner', info)
        self.seen[pid] = info
        self.journal.save('native_launch_complete', {'pid': pid, 'owner_digest': plan.digest(info)})
        self.launch_complete = True
        self.watcher = threading.Thread(target=self.watch, daemon=True)
        self.watcher.start()

    def metadata(self):
        value = project_model_metadata(self.home, 'gpt-6-luna')
        value['compatibility_match'] = value.get('status') == 'recognized' \
            and plan.digest(value.get('compatibility')) == self.runtime['metadata_digest']
        self.journal.save('model_metadata', value)
        return value

    def observe(self, auth_source, *, qualification=None, prompt=None, clock=None):
        # Start the observation clock before touching any credential bytes.
        self.deadline = time.monotonic() + self.data['limits']['wall_seconds']
        if clock is not None:
            clock.arm(self.deadline)
        home = self.control / 'home'
        home.mkdir(mode=0o700)
        project = self.control / 'project'
        project.mkdir(mode=0o700)
        self.journal.save('auth_copy_intent', {'attempted': True})
        self.auth_copy_attempted = True
        try:
            self.home = copy_native_home(auth_source, home / '.codex')
        except Exception as exc:
            self.home = getattr(exc, 'owner', None)
            if self.home is not None:
                self.journal.save('native_home_owner', {'identity': list(self.home.identity)})
            raise
        self.auth_copy_succeeded = True
        self.journal.save('native_home_owner', {'identity': list(self.home.identity)})
        codehome = self.home.root
        private_write(codehome / 'config.toml', DIRECT_PROFILE.encode())
        transport = self.docker + ['exec', '-i', '--env', 'CODEX_HOME=/work/codex',
            '--env', 'HOME=/work/home', self.ids['executor'],
            '/runtime/bin/codex', 'exec-server', '--listen', 'stdio']
        environment = 'default="trial"\ninclude_local=false\n[[environments]]\nid="trial"\nprogram=' \
            + json.dumps(transport[0]) + '\nargs=' + json.dumps(transport[1:]) + '\n'
        private_write(codehome / 'environments.toml', environment.encode())
        env = {'HOME': str(home), 'CODEX_HOME': str(codehome), 'LANG': 'C.UTF-8',
               'PATH': str(Path(self.runtime['codex']).parent) + ':/usr/bin:/bin'}
        self.archive = protocol.CounterArchive()
        self.live = protocol.NativeSession(self.archive, self.deadline)
        self.journal.save('native_launch_intent', {'executable': self.runtime['codex'], 'launch': 1})
        self.launch_called = True
        self.live.start([self.runtime['codex'], 'app-server', '--listen', 'stdio://'],
                        str(project), env, self.on_launch)
        if prompt is None:
            entrypoint = '/runtime/arm/' + self.data['inputs']['entrypoint']
            prompt = 'Use only the selected remote executor. First read the selected arm entrypoint at ' \
                + json.dumps(entrypoint) + '. Then perform this task:\n' + self.data['prompt']
        self.observation = protocol.observe(self.live, prompt=prompt, project=str(project), codehome=str(codehome),
            metadata_check=self.metadata, soft_total=self.data['limits']['soft_total_tokens'],
            soft_output=self.data['limits']['soft_output_tokens'],
            usage_sink=lambda value: self.journal.save('usage_snapshot', value), event_observer=qualification)
        self.journal.save('observation', self.observation)
        return self.observation

    def cleanup(self):
        """Reconcile owned processes before auth; resource failures stay separate."""
        self.cleanup_deadline = time.monotonic() + self.data['limits']['cleanup_seconds']
        result = {'complete': False, 'processes_stopped': False, 'process_absence': [],
                  'containers_absent': [], 'volume_absent': not self.volume_begun,
                  'native_home': None, 'control_absent': False, 'errors': []}
        # Stop owner discovery before terminating the native parent. Otherwise
        # an already-recorded child can be reparented during our own shutdown.
        self.watch_stop.set()
        if self.watcher is not None:
            self.watcher.join(min(3, max(0, self.cleanup_deadline-time.monotonic())))
        alive = self.watcher is not None and self.watcher.is_alive()
        close = None
        if self.live is not None:
            try:
                close = self.live.close()
                result['native_reaped'] = close.get('process_reaped') is True
                result['group_signal_uncertain'] = bool(close.get('group_signal_error'))
            except Exception:
                result['errors'].append('native_close')
        result['watch_uncertain'] = self.watch_error or alive
        result['watch_diagnostic'] = getattr(self, 'watch_diagnostic', None)
        result['process_query_uncertain'] = self.process_uncertain
        process_failure = False
        with getattr(self, 'process_lock', threading.Lock()):
            saved_processes = list(self.seen.values())
        for saved in saved_processes:
            try:
                current = self.process(saved['pid'], cleanup=True)
                if current is not None:
                    plan.require(same_process(saved, current) and saved['pgid'] == saved['pid']
                                 and saved['exe'] in (self.runtime['codex'], self.runtime['code_mode_host'], self.runtime['docker']),
                                 'cleanup_process_owner')
                    os.killpg(saved['pgid'], signal.SIGKILL)
                    until = min(self.cleanup_deadline, time.monotonic()+2)
                    while time.monotonic() < until and self.process(saved['pid'], cleanup=True) is not None:
                        time.sleep(.05)
                    plan.require(self.process(saved['pid'], cleanup=True) is None, 'process_present')
                result['process_absence'].append({'pid': saved['pid'], 'absent': True})
            except Exception:
                process_failure = True
                result['errors'].append('process_cleanup')
        result['process_query_uncertain'] = self.process_uncertain
        result['processes_stopped'] = bool((getattr(self, 'recovery_prior_shutdown', False) or not self.launch_called or
            (self.launch_complete and self.live is not None and self.live.proc is not None
             and close and close.get('process_reaped') is True and not close.get('group_signal_error')))
            and not process_failure and not self.process_uncertain and not result['watch_uncertain'])
        # Check protected bytes only after owned process shutdown, while the
        # control tree still exists. Qualification consumes this captured fact.
        result['protected_synthetic_files_unchanged_after_shutdown'] = (
            self.verify_protected() if result['processes_stopped'] and getattr(self, 'protected', {}) else None)
        # Absence must be observed without following a replacement link.
        parent_fd = None
        try:
            parent_fd = plan.directory(self.control.parent)
            try:
                os.stat(self.control.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                result['control_absent'] = True
        except Exception:
            result['errors'].append('control_inspection')
        finally:
            if parent_fd is not None:
                os.close(parent_fd)
        # Purge known auth before other residue even when Docker cleanup fails.
        if self.home is not None and not result['control_absent']:
            try:
                result['native_home'] = self.home.cleanup(processes_stopped=result['processes_stopped'],
                    codex_executable=self.runtime['codex'], deadline=self.cleanup_deadline)
            except Exception:
                result['errors'].append('native_home_cleanup')
        for key in ('executor', 'stage'):
            if key not in self.begun:
                continue
            try:
                info = self.inspect(self.names[key], cleanup=True)
                if info is not None:
                    # A create-without-completion may reconcile only the unique
                    # exact frozen label/name. Never adopt another task's object.
                    plan.require(owned_container(info, self.names[key], self.selected.digest,
                                                 self.ids.get(key)), 'cleanup_container_owner')
                    self.checked(['rm', '-f', info['Id']], cleanup=True)
                plan.require(self.inspect(self.names[key], cleanup=True) is None, 'container_present')
                result['containers_absent'].append(key)
            except Exception:
                result['errors'].append('container_cleanup')
        if self.volume_begun:
            try:
                value = self.command(['volume', 'inspect', self.names['volume']], cleanup=True)
                if value['exit'] == 0 and not value['stop_reason']:
                    rows = json.loads(value['stdout'])
                    plan.require(isinstance(rows, list) and len(rows) == 1, 'volume_shape')
                    info = rows[0]
                    plan.require(self.volume_owner is not None and all(
                        info.get(k) == self.volume_owner[k] for k in ('Name', 'CreatedAt', 'Labels')), 'volume_owner')
                    self.checked(['volume', 'rm', self.names['volume']], cleanup=True)
                    value = self.command(['volume', 'inspect', self.names['volume']], cleanup=True)
                plan.require(value['exit'] == 1 and not value['stop_reason']
                             and 'no such volume' in value['stderr'].lower(), 'volume_absence')
                result['volume_absent'] = True
            except Exception:
                result['errors'].append('volume_cleanup')
        home_clear = result['control_absent'] or self.home is None or (isinstance(result['native_home'], dict)
                                          and result['native_home'].get('home_absent') is True)
        if result['processes_stopped'] and home_clear and not result['control_absent']:
            try:
                remove_control(self.control, self.control_identity, self.cleanup_deadline)
                result['control_absent'] = True
            except Exception:
                result['errors'].append('control_cleanup')
        elif not result['processes_stopped'] or not home_clear:
            result['errors'].append('home_retained')
        result['complete'] = not result['errors'] and result['processes_stopped'] \
            and result['volume_absent'] and result['control_absent']
        try:
            self.journal.save('cleanup', result, cleanup=True)
        except Exception:
            self.capture_failed = True
            result['complete'] = False
            result['errors'].append('cleanup_capture')
        return result

    def finish(self, cleanup, protected):
        observed = self.observation or {}
        qualification = self.qualification.summary() if self.qualification is not None else None
        good = self.primary is None and cleanup.get('complete') is True and not self.capture_failed \
            and observed.get('status') == 'completed_ungraded'
        if self.data['mode'] == 'qualification':
            good = good and protected is True and qualification is not None \
                and qualification.get('status') == 'observed'
        receipt = {
            'schema_version': 1, 'kind': 'frozen-native-trial',
            'status': ('qualified_current_profile' if self.data['mode'] == 'qualification'
                       else 'completed_ungraded') if good else 'blocked',
            'reason': self.primary or observed.get('reason') or (None if good else
                'cleanup_incomplete' if not cleanup.get('complete') else
                'qualification_incomplete' if self.data['mode'] == 'qualification' else 'observation_incomplete'),
            'manifest_digest': self.selected.digest, 'identity': self.data['identity'],
            'profile': self.data['profile'], 'source_digests': self.data['sources'],
            'runtime_digests': self.runtime['hashes'], 'image_digest': self.runtime['image'],
            'mode': self.data['mode'], 'limits': self.data['limits'],
            'auth_copy_attempted': self.auth_copy_attempted, 'auth_copy_succeeded': self.auth_copy_succeeded,
            'observation': self.observation, 'qualification': qualification,
            'protected_synthetic_files_unchanged': protected, 'cleanup': cleanup,
            'native_streams': self.archive.summary() if self.archive is not None else None,
            'capture_failed': self.capture_failed, 'retained_bytes_before_receipt': self.journal.used,
            'retained_bytes_limit': self.data['limits']['retained_bytes'],
            'retention_denominator': 'Attempt fixed-schema JSON records including final receipt; excludes declared frozen manifest/source inputs, lock, transient removed runtime state and OS buffers.',
            'supervisor_raw_native_contents_or_hashes_retained': False, 'challenge_value_or_hash_retained': False,
            'native_generated_state_absent': cleanup.get('control_absent') is True,
            'actual_inference': 'observed_native_completion' if observed.get('terminal_completed') else 'unknown',
            'model_identity_verified': False, 'wire_attempt_count': None, 'billing_usage': None,
            'live_eligible': False, 'semantic_task_correctness': 'ungraded',
            'all_future_routes_qualified': False, 'natural_routing_qualified': False,
            'external_vm_stop_performed': False, 'escaped_descendants_verified_absent': False,
        }
        self.journal.save('receipt', receipt, final=True)
        return receipt

    def release(self):
        if getattr(self, 'lock_fd', None) is not None:
            os.close(self.lock_fd)
            self.lock_fd = None


def run(path, *, auth_source=None, fixture=False):
    if fixture and auth_source is not None:
        raise plan.Refusal('fixture_auth_forbidden')
    selected = plan.load_plan(path)
    if fixture:
        raise plan.Refusal('credential_free_fixture_is_separate')
    if auth_source is None:
        raise plan.Refusal('auth_source_required')
    plan.absolute(str(auth_source), 'auth_source_path')
    supported_host()
    controller = Controller(selected)
    protected = None
    try:
        with PhaseClock() as clock:
            try:
                clock.arm(controller.deadline)
                prompt = controller.prepare_qualification() if selected.data['mode'] == 'qualification' else None
                controller.setup()
                if selected.data['mode'] == 'qualification':
                    controller.deliver_challenge()
                controller.observe(auth_source, qualification=controller.qualification, prompt=prompt, clock=clock)
            except BaseException as exc:
                controller.primary = fixed_failure(exc)
            finally:
                clock.cancel()
                cleanup = controller.cleanup()
                protected = cleanup.get('protected_synthetic_files_unchanged_after_shutdown')
        return controller.finish(cleanup, protected)
    finally:
        controller.release()


def read_recovery(attempt):
    """Bind original source/runtime/journal without reopening case/auth inputs."""
    attempt = plan.absolute(str(attempt), 'recovery_path')
    fd = plan.directory(attempt)
    try:
        info = os.fstat(fd)
        plan.require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'recovery_owner')
    finally:
        os.close(fd)
    raw, _ = plan.read_file(attempt / 'manifest.json', 1024*1024, 'recovery_manifest')
    data = json.loads(raw, object_pairs_hook=protocol.unique,
        parse_constant=lambda _: (_ for _ in ()).throw(plan.Refusal('recovery_manifest')))
    plan.require(isinstance(data, dict) and data.get('schema_version') == 1 and data.get('profile') == plan.PROFILE,
                 'recovery_manifest')
    identity = data.get('identity', {})
    plan.require(plan.is_digest(identity.get('trial_id')) and plan.token(identity.get('attempt_id')),
                 'recovery_manifest')
    expected = plan.absolute(data.get('state_root'), 'recovery_manifest') / identity['trial_id'] / identity['attempt_id']
    plan.require(expected == attempt, 'recovery_path')
    sources = data.get('sources')
    plan.require(isinstance(sources, dict) and set(sources) == plan.SOURCE_NAMES, 'recovery_sources')
    for name, expected_digest in sources.items():
        _, actual = plan.read_file(plan.SOURCE / name, 2*1024**2, 'recovery_sources', retain=False)
        plan.require(plan.is_digest(expected_digest) and actual == expected_digest, 'recovery_sources')
    runtime = data.get('runtime')
    plan.fields(runtime, 'codex code_mode_host docker executor_archive hashes image docker_host metadata_digest', 'recovery_runtime')
    plan.fields(runtime['hashes'], 'codex code_mode_host docker executor_archive', 'recovery_runtime')
    plan.require(all(runtime['hashes'].get(k) == v for k, v in plan.PINNED_RUNTIME.items()), 'recovery_runtime')
    for name, expected_digest in runtime['hashes'].items():
        executable = plan.absolute(runtime[name], 'recovery_runtime')
        _, actual = plan.read_file(executable, 512*1024**2, 'recovery_runtime', owner=False, retain=False)
        plan.require(actual == expected_digest, 'recovery_runtime')
    plan.require(isinstance(runtime['docker_host'], str) and runtime['docker_host'].startswith('unix:///'), 'recovery_runtime')
    plan.absolute(runtime['docker_host'][7:], 'recovery_runtime')
    limits = data.get('limits')
    plan.fields(limits, ' '.join(plan.LIMITS), 'recovery_manifest')
    plan.require(all(type(limits[k]) is int and 0 < limits[k] <= bound for k, bound in plan.LIMITS.items())
                 and limits['retained_bytes'] >= 65536, 'recovery_manifest')
    lock = os.open(attempt / 'coordinator.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(lock)
        plan.require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                     and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600, 'recovery_lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise plan.Refusal('coordinator_running') from None
        journal, records = Journal.resume(attempt / 'records', limits['retained_bytes'])
        journal.coordinator_lock = lock
        return data, records, journal
    except BaseException:
        os.close(lock)
        raise


def recover(attempt):
    """Finish residue cleanup only after independently rechecking bound owners.

    Missing launch completion or missing prior complete process supervision is
    unresolved. No caller flag can waive it. No auth copy, native launch, model
    call, broad process scan, package action or VM lifecycle occurs here.
    """
    supported_host()
    data, records, journal = read_recovery(attempt)
    try:
        launches = records.get('native_launch_intent', [])
        completions = records.get('native_launch_complete', [])
        prior = records.get('cleanup', [])
        if launches and (len(launches) != 1 or len(completions) != 1
                or not prior or prior[-1].get('processes_stopped') is not True
                or prior[-1].get('watch_uncertain') is not False
                or prior[-1].get('process_query_uncertain') is not False):
            raise plan.Refusal('recovery_launch_unresolved')
        plan.require(bool(launches) == bool(completions), 'recovery_launch_unresolved')
        selected = type('RecoveryBinding', (), {'data': data, 'digest': plan.digest(data)})()
        bindings = records.get('frozen_binding', [])
        plan.require(len(bindings) == 1 and bindings[0] == {
            'manifest_digest': selected.digest, 'identity': data['identity'], 'profile': data['profile']}, 'recovery_binding')
        owners = records.get('control_owner', [])
        plan.require(len(owners) == 1 and isinstance(owners[0].get('identity'), list)
                     and len(owners[0]['identity']) == 3 and all(type(v) is int for v in owners[0]['identity']), 'recovery_control')
        controller = Controller.__new__(Controller)
        controller.selected, controller.data, controller.runtime = selected, data, data['runtime']
        controller.attempt = plan.absolute(str(attempt), 'recovery_path')
        controller.control = controller.attempt / 'control'
        controller.control_identity = tuple(owners[0]['identity'])
        controller.env = {'HOME': str(controller.attempt), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
        controller.journal = journal
        controller.names = resource_names(data['identity'])
        controller.docker = [data['runtime']['docker'], '--host', data['runtime']['docker_host']]
        controller.live, controller.watcher = None, None
        controller.launch_called = bool(launches)
        controller.launch_complete = bool(completions)
        controller.recovery_prior_shutdown = bool(launches)
        controller.seen = {}
        for owner in records.get('process_owner', []):
            plan.fields(owner, 'pid ppid pgid start exe', 'recovery_process')
            plan.require(type(owner['pid']) is int and owner['pid'] > 0
                         and owner['pid'] == owner['pgid'] and type(owner['ppid']) is int
                         and owner['exe'] in (controller.runtime['codex'], controller.runtime['code_mode_host'], controller.runtime['docker'])
                         and isinstance(owner['start'], str) and len(owner['start']) <= 64
                         and owner['pid'] not in controller.seen, 'recovery_process')
            controller.seen[owner['pid']] = owner
        plan.require(len(controller.seen) <= 4, 'recovery_process')
        native_owners = [o for o in controller.seen.values() if o['exe'] == controller.runtime['codex']]
        plan.require(len(native_owners) == (1 if launches else 0), 'recovery_process')
        if native_owners:
            plan.require(all(o['exe'] == controller.runtime['codex'] or
                             o['ppid'] == native_owners[0]['pid'] for o in controller.seen.values()), 'recovery_process')
        if launches:
            plan.require(launches[0] == {'executable': controller.runtime['codex'], 'launch': 1}
                         and any(o['exe'] == controller.runtime['codex'] and o['pid'] == completions[0].get('pid')
                                 and plan.digest(o) == completions[0].get('owner_digest')
                                 for o in controller.seen.values()), 'recovery_launch_owner')
        else:
            plan.require(not controller.seen, 'recovery_launch_unresolved')
        controller.process_lock = threading.Lock()
        controller.watch_stop = threading.Event()
        controller.process_uncertain = controller.watch_error = controller.capture_failed = False
        controller.begun, controller.ids = set(), {}
        for value in records.get('container_create_intent', []):
            key = next((k for k in ('stage', 'executor') if controller.names[k] == value.get('name')), None)
            plan.require(key is not None and key not in controller.begun, 'recovery_container')
            controller.begun.add(key)
        for value in records.get('container_owner', []):
            key = value.get('kind')
            plan.require(key in controller.begun and key not in controller.ids and value.get('name') == controller.names[key]
                         and plan.is_digest(value.get('id')), 'recovery_container')
            controller.ids[key] = value['id']
        volume = records.get('volume_owner', [])
        intents = records.get('volume_create_intent', [])
        plan.require(len(volume) <= 1 and len(intents) <= 1, 'recovery_volume')
        controller.volume_begun = bool(intents)
        controller.volume_owner = volume[0] if volume else None
        if volume:
            plan.require(volume[0].get('Name') == controller.names['volume']
                         and volume[0].get('Labels', {}).get(LABEL) == selected.digest, 'recovery_volume')
        homes = records.get('native_home_owner', [])
        plan.require(len(homes) <= 1, 'recovery_home')
        controller.home = None
        if homes:
            identity = homes[0].get('identity')
            plan.require(isinstance(identity, list) and len(identity) == 3
                         and all(type(v) is int for v in identity), 'recovery_home')
            controller.home = NativeHome(controller.control / 'home/.codex', tuple(identity))
        elif records.get('auth_copy_intent'):
            # A crash during the copy can leave an unrecorded destination. Never
            # guess its inode or let outer tree cleanup bypass the home owner.
            raise plan.Refusal('recovery_home_unresolved')
        try:
            journal.save('recovery_intent', {'native_launch': False, 'auth_copy': False}, cleanup=True)
        except Exception:
            controller.capture_failed = True
        if not controller.control.exists():
            # Still reconcile owned Docker/process resources; the absence of the
            # path alone never supplies process shutdown evidence.
            controller.control_missing = True
        result = controller.cleanup()
        journal.save('recovery_receipt', {'status': 'reconciled' if result['complete'] else 'blocked',
            'cleanup': result, 'new_native_auth_model_actions': False, 'external_vm_stop_performed': False}, final=True)
        return {'status': 'reconciled' if result['complete'] else 'blocked', 'cleanup_complete': result['complete']}
    finally:
        if journal is not None and getattr(journal, 'coordinator_lock', None) is not None:
            os.close(journal.coordinator_lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit pinned frozen Codex trial; no installation or VM lifecycle.')
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check', help='Read selected frozen inputs/runtime identities; no auth or process launch.')
    check.add_argument('--plan', required=True, type=Path)
    execute = commands.add_parser('run', help='Run one frozen attempt with one explicit temporary auth copy.')
    execute.add_argument('--plan', required=True, type=Path)
    execute.add_argument('--auth-source', required=True, type=Path)
    recovery = commands.add_parser('recover', help='Reconcile exact prior owned residue without auth copy or native launch.')
    recovery.add_argument('--attempt', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            selected = plan.load_plan(args.plan)
            result = {'status': 'checked', 'manifest_digest': selected.digest,
                      'authentication_opened': False, 'processes_launched': False}
        elif args.command == 'recover':
            result = recover(args.attempt)
        else:
            receipt = run(args.plan, auth_source=args.auth_source)
            result = {'status': receipt['status'], 'manifest_digest': receipt['manifest_digest'],
                      'cleanup_complete': receipt['cleanup']['complete'], 'live_eligible': False}
        print(plan.encoded(result).decode('ascii'))
        return 0 if result['status'] in ('checked', 'completed_ungraded', 'qualified_current_profile', 'reconciled') else 1
    except Exception as exc:
        # CLI refusals are deliberately categorical; do not print raw failures.
        reason = str(exc) if isinstance(exc, plan.Refusal) and re.fullmatch('[a-z][a-z0-9_]{0,63}', str(exc)) else 'operation'
        print(plan.encoded({'status': 'refused', 'reason': reason}).decode('ascii'))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
