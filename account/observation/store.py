"""Opt-in private observations. No transcript reading, account probes or network IO."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

from .files import BusyStore, Files, ROOT, encoded

EVENT_LIMIT = 16384
BATCH_LIMIT = 65536
MAX_BATCH_EVENTS = 128
MAX_RECORDS = 4096
TOKEN = re.compile(r'[A-Za-z0-9_.:@-]{1,160}\Z')
KEY = re.compile(r'[a-f0-9]{64}\Z')
EPOCH = re.compile(r'[a-f0-9]{32}\Z')
KINDS = {'session_start', 'tool_start', 'tool_end', 'response_end'}


class InvalidEvent(ValueError):
    """Only fixed diagnostic codes belong in messages."""


def require(condition, reason):
    if not condition:
        raise InvalidEvent(reason)


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def token(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def integer(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def decode(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    try:
        return json.loads(body, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(InvalidEvent('invalid_json')))
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidEvent('invalid_json') from None


def normalize(body, grant):
    require(isinstance(body, bytes) and len(body) <= EVENT_LIMIT, 'event_size')
    value = decode(body)
    require(isinstance(value, dict), 'event_object')
    require(type(value.get('schema_version')) is int and value['schema_version'] == 1, 'unknown_schema')
    for field in ('project_root', 'client', 'profile', 'source'):
        require(value.get(field) == grant[field], 'scope_mismatch')
    require(token(value.get('session_id')), 'session_id')
    require(integer(value.get('sequence')) and value['sequence'] > grant['start_after'], 'source_high_water')
    require(isinstance(value.get('event_kind'), str) and value['event_kind'] in KINDS, 'event_kind')
    event = {field: value[field] for field in ('session_id', 'sequence', 'event_kind')}
    event.update(project_id=grant['project_id'], client=grant['client'], profile=grant['profile'],
                 source=grant['source'], registration_id=grant['registration_id'],
                 epoch=grant['epoch'], schema_version=1)
    gaps = ['environment_not_observed', 'task_outcome_not_observed']
    if grant['client'] == 'synthetic':
        gaps.insert(0, 'synthetic_adapter')  # Preserve schema-v1 replay equality.
    else:
        gaps.extend(['native_metadata_only', 'collector_receipt_order_only', 'delivery_completeness_not_observed'])
    for field in ('source_event_id', 'actor_id', 'parent_actor_id', 'turn_id', 'tool_call_id'):
        item = value.get(field)
        require(item is None or token(item), 'invalid_identity')
        event[field] = item
        if item is None:
            gaps.append(field + '_not_observed')
    if event['source_event_id'] is None:
        gaps.append('possible_duplicate')
    for field, allowed in [('tool_category', {'shell', 'file', 'mcp', 'other'}),
                           ('status', {'success', 'failure', 'pending', 'unknown'})]:
        item = value.get(field)
        require(item is None or (isinstance(item, str) and item in allowed), 'invalid_metadata')
        event[field] = item
        if item is None:
            gaps.append(field + '_not_observed')
    occurred = value.get('occurred_at')
    require(occurred is None or (type(occurred) in (int, float)
                                and 0 <= occurred <= 253402300799
                                and math.isfinite(occurred)), 'invalid_time')
    event.update(occurred_at=occurred, manifest=None, gaps=gaps)
    if occurred is None:
        gaps.append('event_time_not_observed')
    identity = [grant['registration_id'], grant['epoch'], event['session_id'], event['source_event_id']]
    event['event_id'] = digest(identity) if event['source_event_id'] else uuid.uuid4().hex
    return event


class Store:
    def __init__(self, home):
        # Canonicalize the caller-selected home only; never read an ambient HOME.
        self.home = Path(home).resolve(strict=True)
        if not self.home.is_dir():
            raise ValueError('account_home_not_directory')
        self.root = self.home.joinpath(*ROOT)

    @contextmanager
    def _locked(self, create=False):
        with Files.open(self.home, create=create) as files:
            with files.guard(create=create):
                yield files

    def grant(self, project, *, profile='default', source='fixture-v1', start_after=0,
              lifetime_seconds=2592000, client='synthetic'):
        project = Path(project).resolve(strict=True)
        require(project.is_dir() and token(profile) and token(source), 'invalid_scope')
        require(integer(start_after), 'source_high_water')
        require(client == 'synthetic' or (client in ('claude', 'codex') and profile == 'default'
                and source == client + '-hooks-v1'), 'unsupported_adapter')
        require(type(lifetime_seconds) in (int, float) and 0 < lifetime_seconds <= 2592000
                and math.isfinite(lifetime_seconds), 'grant_lifetime')
        registration_id = digest([str(project), client, profile, source])
        with self._locked(create=True) as files:
            try:
                previous = files.read(('grants', registration_id + '.json'))
            except FileNotFoundError:
                previous = None
            require(not previous or not previous['active'], 'already_granted')
            require(not previous or previous.get('high_water_known', True), 'source_generation_required')
            if client != 'synthetic' and previous:
                # Native sequence is collector receipt order, not a history cursor.
                start_after = max(start_after, previous['high_water'])
            require(not previous or start_after >= previous['high_water'], 'source_high_water')
            # Any interrupted purge must finish before accepting a new epoch.
            self._delete_evidence(files, registration_id)
            grant = dict(schema_version=1, registration_id=registration_id,
                         epoch=uuid.uuid4().hex, project_root=str(project),
                         project_id=digest(str(project)), client=client,
                         profile=profile, source=source, start_after=start_after,
                         high_water=start_after, active=True, created_at=time.time(),
                         expires_at=time.time() + lifetime_seconds)
            files.write(('grants', registration_id + '.json'), grant)
            return {'registration_id': registration_id, 'epoch': grant['epoch']}

    def _grant(self, files, registration_id, epoch=None):
        require(isinstance(registration_id, str) and KEY.fullmatch(registration_id), 'registration_id')
        grant = files.read(('grants', registration_id + '.json'))
        if (not grant['active'] or grant['expires_at'] <= time.time()
                or (epoch is not None and epoch != grant['epoch'])):
            return None
        require(grant['registration_id'] == registration_id and grant['client'] in ('synthetic', 'claude', 'codex'), 'invalid_grant')
        return grant

    def registration(self, registration_id):
        """Read an active grant for explicit installer selection; never creates it."""
        with self._locked() as files:
            return self._grant(files, registration_id)

    def _records(self, files, grant):
        names = files.names(('records', grant['registration_id']))
        require(len(names) <= MAX_RECORDS, 'store_capacity')
        records = []
        for name in names:
            if not re.fullmatch(r'[a-f0-9]{64}\.json', name):
                continue  # Interrupted pending files never become committed evidence.
            record = files.read(('records', grant['registration_id'], name))
            require(isinstance(record, dict), 'corrupt_record')
            require(record.get('registration_id') == grant['registration_id']
                    and record.get('record_id') == name[:-5]
                    and isinstance(record.get('epoch'), str)
                    and EPOCH.fullmatch(record['epoch'])
                    and type(record.get('schema_version')) is int
                    and record['schema_version'] == 1
                    and integer(record.get('high_water'))
                    and (record.get('next_offset') is None or integer(record['next_offset']))
                    and isinstance(record.get('events'), list)
                    and isinstance(record.get('event_ids'), list), 'corrupt_record')
            if record.get('epoch') != grant['epoch']:
                continue  # Copied records from revoked epochs cannot resurrect.
            require(all(isinstance(event, dict) and token(event.get('event_id'))
                        and event.get('registration_id') == grant['registration_id']
                        and event.get('epoch') == grant['epoch']
                        and integer(event.get('sequence')) for event in record['events']), 'corrupt_record')
            records.append(record)
        return records

    def _capture(self, registration_id, epoch, payload, offset=None, native_stream=None):
        require(isinstance(epoch, str) and EPOCH.fullmatch(epoch), 'epoch')
        with self._locked() as files:
            grant = self._grant(files, registration_id, epoch)
            if grant is None:
                return {'status': 'disabled'}
            require((grant['client'] == 'synthetic') == (native_stream is None), 'adapter_mismatch')
            # Scope is checked before ledger scans or reading hook input.
            if native_stream is not None:
                from .native import validate_process_scope
                validate_process_scope(grant)
            limit = EVENT_LIMIT if offset is None else BATCH_LIMIT
            records = self._records(files, grant)
            existing = {event['event_id']: event for record in records for event in record['events']}
            if native_stream is not None:
                from .native import adapt
                payload = adapt(native_stream, grant, existing.values())
            require(isinstance(payload, bytes) and len(payload) <= limit, 'payload_size')
            if offset is None:
                events = [normalize(payload, grant)]
                record_id = digest(['event', events[0]['event_id']])
                cursor = None
                trailing = 0
            else:
                require(integer(offset), 'import_offset')
                # The source/generation is already fixed by this registration.
                complete_end = payload.rfind(b'\n') + 1
                complete, trailing = payload[:complete_end], len(payload) - complete_end
                record_id = digest([registration_id, epoch, 'batch', offset, hashlib.sha256(complete).hexdigest()])
                replay = next((r for r in records if r['record_id'] == record_id), None)
                if replay:
                    with files.directory(('records', registration_id)) as directory:
                        os.fsync(directory)
                    return dict(status='duplicate', event_ids=replay['event_ids'],
                                next_offset=replay['next_offset'], trailing_bytes=trailing)
                current = max((r['next_offset'] for r in records if r['next_offset'] is not None), default=0)
                require(offset == current, 'cursor_mismatch')
                if not complete:
                    return dict(status='incomplete', event_ids=[], next_offset=current, trailing_bytes=trailing)
                lines = complete.split(b'\n')[:-1]
                require(len(lines) <= MAX_BATCH_EVENTS, 'batch_event_limit')
                events = [normalize(line, grant) for line in lines]
                cursor = offset + complete_end
            fresh = []
            for event in events:
                old = existing.get(event['event_id'])
                require(old is None or old == event, 'identity_conflict')
                if old is None:
                    fresh.append(event)
                    existing[event['event_id']] = event
            if offset is None and not fresh:
                # A previous attempt may have renamed successfully but failed its
                # directory sync. Retry must establish durability before ack.
                with files.directory(('records', registration_id)) as directory:
                    os.fsync(directory)
                return {'status': 'duplicate', 'event_ids': [e['event_id'] for e in events]}
            require(len(records) < MAX_RECORDS - 1, 'store_capacity')
            record = dict(schema_version=1, record_id=record_id, registration_id=registration_id,
                          epoch=epoch, recorded_at=time.time(), events=fresh,
                          event_ids=[e['event_id'] for e in events],
                          high_water=max(event['sequence'] for event in events),
                          next_offset=cursor)
            files.write(('records', registration_id, record_id + '.json'), record)
            result = {'status': 'recorded', 'event_ids': [e['event_id'] for e in events]}
            if offset is not None:
                result.update(next_offset=cursor, trailing_bytes=trailing)
            return result

    def _receive(self, registration_id, epoch, payload, offset=None, native_stream=None):
        try:
            return self._capture(registration_id, epoch, payload, offset, native_stream)
        except FileNotFoundError:
            return {'status': 'disabled'}
        except BusyStore:
            return {'status': 'busy', 'reason': 'store_busy'}
        except InvalidEvent as error:
            return {'status': 'rejected', 'reason': str(error)}
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            # Never log payloads, filesystem paths, or raw exception strings.
            return {'status': 'error', 'reason': 'store_unavailable'}

    def capture(self, registration_id, epoch, payload):
        return self._receive(registration_id, epoch, payload)

    def capture_native(self, registration_id, epoch, stream):
        return self._receive(registration_id, epoch, None, native_stream=stream)

    def import_batch(self, registration_id, epoch, offset, payload):
        if not integer(offset):
            return {'status': 'rejected', 'reason': 'import_offset'}
        return self._receive(registration_id, epoch, payload, offset)

    def events(self, registration_id):
        try:
            with self._locked() as files:
                grant = self._grant(files, registration_id)
                if grant is None:
                    return []
                return [event for record in self._records(files, grant) for event in record['events']]
        except FileNotFoundError:
            return []

    def _delete_evidence(self, files, registration_id):
        files.clear(('records', registration_id))
        # Cache has no authority and may contain other registrations: discard all.
        files.unlink(('index.sqlite',))
        for name in files.names(()):
            if name.startswith('.index-'):
                files.unlink((name,))

    def _revoke(self, files, registration_id):
        require(isinstance(registration_id, str) and KEY.fullmatch(registration_id), 'registration_id')
        grant = files.read(('grants', registration_id + '.json'))
        high_water = grant['high_water']
        high_water_known = grant.get('high_water_known', True)
        if grant['active']:
            try:
                records = self._records(files, grant)
                high_water = max([high_water] + [r['high_water'] for r in records])
            except (OSError, ValueError, TypeError, KeyError, RecursionError):
                # Corruption must not prevent consent revocation. If the old
                # frontier cannot be read, resuming that source is forbidden.
                high_water_known = False
        # Commit revocation first. A crash during deletion cannot make evidence visible.
        tombstone = dict(schema_version=1, registration_id=registration_id,
                         active=False, high_water=high_water, high_water_known=high_water_known)
        files.write(('grants', registration_id + '.json'), tombstone)
        self._delete_evidence(files, registration_id)
        return {'status': 'revoked', 'high_water': high_water if high_water_known else None}

    def revoke(self, registration_id):
        with self._locked() as files:
            return self._revoke(files, registration_id)

    def prune(self):
        with self._locked() as files:
            count = 0
            for name in files.names(('grants',)):
                if not re.fullmatch(r'[a-f0-9]{64}\.json', name):
                    continue
                grant = files.read(('grants', name))
                if not grant['active'] or grant['expires_at'] <= time.time():
                    self._revoke(files, name[:-5])
                    count += 1
            return count

    def rebuild_index(self):
        # Build privately in memory, then persist its single snapshot through the
        # same descriptor-relative, fsynced boundary. Index reads are never consent.
        with self._locked() as files:
            connection = sqlite3.connect(':memory:')
            try:
                connection.execute('CREATE TABLE events (event_id TEXT PRIMARY KEY, registration_id TEXT, event_json TEXT)')
                count = 0
                for name in files.names(('grants',)):
                    if not re.fullmatch(r'[a-f0-9]{64}\.json', name):
                        continue
                    grant = self._grant(files, name[:-5])
                    if grant:
                        for record in self._records(files, grant):
                            for event in record['events']:
                                connection.execute('INSERT INTO events VALUES (?, ?, ?)',
                                                   (event['event_id'], name[:-5], encoded(event).decode()))
                                count += 1
                connection.commit()
                # serialize is available on Python 3.11+ with SQLite serialization.
                body = connection.serialize()
            finally:
                connection.close()
            self._write_index(files, body)
            return count

    @staticmethod
    def _write_index(files, body):
        try:
            target = os.stat('index.sqlite', dir_fd=files.fd, follow_symlinks=False)
            require(stat.S_ISREG(target.st_mode) and target.st_nlink == 1
                    and target.st_uid == os.getuid() and stat.S_IMODE(target.st_mode) == 0o600,
                    'unsafe_index_target')
        except FileNotFoundError:
            pass
        name = '.index-' + uuid.uuid4().hex
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=files.fd)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(body)
                stream.flush()
                os.fsync(fd)
            os.replace(name, 'index.sqlite', src_dir_fd=files.fd, dst_dir_fd=files.fd)
            os.fsync(files.fd)
        finally:
            os.close(fd)
            files.unlink((name,))
