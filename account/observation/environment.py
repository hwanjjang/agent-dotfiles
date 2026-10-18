"""Bounded delivery snapshots, never claims about effective model exposure."""
import hashlib
import os
import re
import stat
import time

from .files import encoded

RECEIPT = ('.agents', 'agent-dotfiles', 'state', 'installed.json')
BUNDLE = ('.agents', 'agent-dotfiles', 'bundle')
COMPONENTS = {'instructions': 'account/instructions.md',
              'execution_policy': 'policies/execution.md',
              'communication_policy': 'policies/communication.md',
              'native_adapter': 'account/observation/native.py'}
RECEIPT_LIMIT = 512 * 1024
COMPONENT_LIMIT = 64 * 1024
PROBE_SECONDS = .05


class Unavailable(ValueError):
    pass


def snapshot(home, grant, boundary):
    """Probe only an already consent-checked native session/response boundary.

    The byte limits are hard read caps; the time budget is checked between local
    regular-file operations, not an OS I/O cancellation guarantee. The enclosing
    installed callback retains its separate process deadline.
    """
    from .store import decode
    started = time.monotonic()
    result = dict(schema_version=1, observed_at=time.time(), boundary=boundary,
                  client=grant['client'], adapter=grant['source'], status='unavailable',
                  source_revision=None, receipt_sha256=None, delivery_sha256=None,
                  component_hashes={}, drift='unknown', effective_exposure_exact=False,
                  gaps=['effective_exposure_not_observed', 'unprobed_components',
                        'project_overrides_not_observed', 'mid_interval_changes_not_excluded'])

    def budget():
        if time.monotonic() - started > PROBE_SECONDS:
            raise Unavailable('environment_probe_budget')

    def read(parts, limit, private=False):
        budget()
        fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in parts[:-1]:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = child
            child = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                before = os.fstat(child)
                if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                        or before.st_nlink != 1 or before.st_size > limit
                        or (private and stat.S_IMODE(before.st_mode) != 0o600)):
                    raise Unavailable('environment_probe_unsafe_or_oversized')
                with os.fdopen(child, 'rb', closefd=False) as stream:
                    body = stream.read(limit + 1)
                after = os.fstat(child)
                if (len(body) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                        != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                    raise Unavailable('environment_changed_during_probe')
            finally:
                os.close(child)
        finally:
            os.close(fd)
        budget()
        return body

    try:
        raw = read(RECEIPT, RECEIPT_LIMIT, private=True)
        receipt = decode(raw)
        if (not isinstance(receipt, dict) or receipt.get('version') != 1
                or receipt.get('home') != str(home)
                or not isinstance(receipt.get('source_revision'), str)
                or re.fullmatch(r'[a-f0-9]{40}(?:[a-f0-9]{24})?', receipt['source_revision']) is None
                or not isinstance(receipt.get('assets'), dict) or len(receipt['assets']) > 4096):
            raise Unavailable('environment_receipt_invalid')
        declared = {}
        for name, value in receipt['assets'].items():
            if not isinstance(name, str) or not name.startswith('/'.join(BUNDLE) + '/'):
                continue  # Symlinks/entry points are outside the component probe.
            relative = name[len('/'.join(BUNDLE)) + 1:]
            if (not re.fullmatch(r'[A-Za-z0-9_./-]{1,256}', relative)
                    or any(part in ('', '.', '..') for part in relative.split('/'))
                    or not isinstance(value, dict) or not isinstance(value.get('sha256'), str)
                    or re.fullmatch(r'[a-f0-9]{64}', value['sha256']) is None):
                raise Unavailable('environment_receipt_invalid')
            declared[relative] = value['sha256']
        hashes = {}
        for label, relative in COMPONENTS.items():
            observed = hashlib.sha256(read(BUNDLE + tuple(relative.split('/')), COMPONENT_LIMIT)).hexdigest()
            hashes[label] = {'observed_sha256': observed, 'delivered_sha256': declared.get(relative)}
        if read(RECEIPT, RECEIPT_LIMIT, private=True) != raw:
            raise Unavailable('environment_changed_during_probe')
        budget()
        result.update(status='observed', source_revision=receipt['source_revision'],
                      receipt_sha256=hashlib.sha256(raw).hexdigest(),
                      delivery_sha256=hashlib.sha256(encoded(declared)).hexdigest(),
                      component_hashes=hashes,
                      drift='detected' if any(v['observed_sha256'] != v['delivered_sha256']
                                              for v in hashes.values()) else 'not_detected_in_probed_components')
    except Unavailable as error:
        result['gaps'].append(str(error))
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        result['gaps'].append('environment_probe_unavailable')
    result['elapsed_ms'] = round((time.monotonic()-started)*1000, 3)
    return result
