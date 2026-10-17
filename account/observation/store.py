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
TASK_INPUT_LIMIT = 65536
TASK_RECORD_LIMIT = 131072
MAX_TASKS = 256
MAX_TASK_RECORDS = 128
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


def feedback_text(value, *, optional=False):
    require(optional and value is None or isinstance(value, str)
            and bool(value.strip()) and len(value.encode('utf-8')) <= 8192, 'feedback_text')
    return value


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
        require(client == 'synthetic' or (client == 'claude' and profile == 'default'
                and source == 'claude-hooks-v1'), 'unsupported_adapter')
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
        require(grant['registration_id'] == registration_id and grant['client'] in ('synthetic', 'claude'), 'invalid_grant')
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

    def _task_records(self, files, task_id, *, active=True):
        require(isinstance(task_id, str) and KEY.fullmatch(task_id), 'task_id')
        names = files.names(('tasks', task_id))
        require(len(names) <= MAX_TASK_RECORDS, 'task_capacity')
        records = []
        for name in names:
            if not re.fullmatch(r'[a-f0-9]{64}\.json', name):
                continue
            row = files.read(('tasks', task_id, name), TASK_RECORD_LIMIT)
            require(isinstance(row, dict) and row.get('schema_version') == 1
                    and row.get('task_id') == task_id and row.get('record_id') == name[:-5]
                    and row.get('kind') in {'task', 'feedback'}
                    and integer(row.get('sequence')) and isinstance(row.get('registrations'), list)
                    and 0 < len(row['registrations']) <= 16, 'corrupt_task')
            for ref in row['registrations']:
                require(isinstance(ref, dict) and isinstance(ref.get('registration_id'), str)
                        and KEY.fullmatch(ref['registration_id'])
                        and isinstance(ref.get('epoch'), str)
                        and EPOCH.fullmatch(ref['epoch']), 'corrupt_task')
                if active:
                    try:
                        grant = self._grant(files, ref.get('registration_id'), ref['epoch'])
                    except FileNotFoundError:
                        grant = None
                    require(grant is not None, 'task_inactive')
            records.append(row)
        records.sort(key=lambda row: row['sequence'])
        require(len({r['sequence'] for r in records}) == len(records), 'corrupt_task')
        return records

    def _task_retry(self, files, task_id, rows, kind, request_id, request):
        require(token(request_id), 'request_id')
        require(len(encoded(request)) <= TASK_INPUT_LIMIT, 'task_input_size')
        ident = digest([kind, request_id])
        previous = next((r for r in rows if r['record_id'] == ident), None)
        if previous:
            require(previous['request_hash'] == digest(request), 'request_conflict')
            # A prior rename may have succeeded before directory fsync failed.
            with files.directory(('tasks', task_id)) as directory:
                os.fsync(directory)
        return ident, previous

    @staticmethod
    def _task_receipt(row, status):
        if row['kind'] == 'task':
            return dict(status=status, task_id=row['task_id'], revision_id=row['record_id'])
        return dict(status=status, task_id=row['task_id'], feedback_id=row['record_id'],
                    revision_id=row['revision_id'], evidence_status=row['evidence_status'])

    def _select_task_events(self, files, selections):
        require(isinstance(selections, list) and 0 < len(selections) <= 16, 'task_selections')
        resolved, registrations, selected_ids = [], {}, set()
        for selection in selections:
            require(isinstance(selection, dict) and set(selection) <= {
                'registration_id', 'epoch', 'session_id', 'actor_id', 'event_ids',
                'start_sequence', 'end_sequence'}, 'task_selection')
            registration, epoch = selection.get('registration_id'), selection.get('epoch')
            require(isinstance(epoch, str) and EPOCH.fullmatch(epoch), 'epoch')
            grant = self._grant(files, registration, epoch)
            require(grant is not None, 'task_inactive')
            session, actor = selection.get('session_id'), selection.get('actor_id')
            require(token(session) and (actor is None or token(actor)), 'task_selection')
            events = [e for r in self._records(files, grant) for e in r['events']
                      if e['session_id'] == session and (actor is None or e['actor_id'] == actor)]
            if 'event_ids' in selection:
                ids = selection['event_ids']
                require('start_sequence' not in selection and 'end_sequence' not in selection
                        and isinstance(ids, list) and 0 < len(ids) <= 128
                        and all(token(i) for i in ids) and len(set(ids)) == len(ids), 'task_selection')
                events = [e for e in events if e['event_id'] in ids]
                require({e['event_id'] for e in events} == set(ids), 'event_not_selected')
                basis = 'explicit_event_ids'
            else:
                start, end = selection.get('start_sequence'), selection.get('end_sequence')
                require(integer(start) and integer(end) and start <= end, 'task_interval')
                events = [e for e in events if start <= e['sequence'] <= end]
                basis = 'synthetic_receipt_interval'
            require(bool(events), 'empty_selection')
            selected_ids.update(e['event_id'] for e in events)
            require(len(selected_ids) <= 128, 'task_event_limit')
            # An overlapping selection cannot duplicate the selected event.
            already = {e['event_id'] for s in resolved for e in s['events']}
            events = [e for e in events if e['event_id'] not in already]
            if events:
                resolved.append(dict(registration_id=registration, epoch=epoch, session_id=session,
                    basis=basis, events=[{key: e[key] for key in (
                        'event_id', 'sequence', 'actor_id', 'parent_actor_id', 'turn_id', 'gaps')}
                        for e in sorted(events, key=lambda e: (e['sequence'], e['event_id']))]))
            registrations[registration] = dict(registration_id=registration, epoch=epoch)
        return resolved, list(registrations.values())

    def bind_task(self, *, selections, goal, request_id, task_id=None):
        """Append an immutable explicit selection; no current-task or history discovery."""
        feedback_text(goal)
        require(token(request_id), 'request_id')
        request = dict(selections=selections, goal=goal, task_id=task_id)
        require(len(encoded(request)) <= TASK_INPUT_LIMIT, 'task_input_size')
        selected_task = task_id or digest(['task', request_id])
        with self._locked() as files:
            rows = self._task_records(files, selected_task)
            require(task_id is None or bool(rows), 'task_not_found')
            ident, previous = self._task_retry(files, selected_task, rows, 'task', request_id, request)
            if previous:
                return self._task_receipt(previous, 'duplicate')
            resolved, registrations = self._select_task_events(files, selections)
            require(len(rows) < MAX_TASK_RECORDS - 1, 'task_capacity')
            require(bool(rows) or len(files.names(('tasks',))) < MAX_TASKS, 'task_capacity')
            row = dict(schema_version=1, kind='task', task_id=selected_task, record_id=ident,
                       sequence=len(rows) + 1, request_hash=digest(request), goal=goal,
                       registrations=registrations, selections=resolved)
            require(len(encoded(row)) <= TASK_RECORD_LIMIT, 'task_record_size')
            files.write(('tasks', selected_task, ident + '.json'), row)
            return self._task_receipt(row, 'recorded')

    def add_feedback(self, task_id, *, symptom, correction=None, evidence_ids=None,
                     contrary_evidence_ids=None, suspected_cause=None, confidence='unknown',
                     author='user', request_id, revision_id=None):
        """Record selected feedback as an observation, never a verified diagnosis."""
        for value, optional in [(symptom, False), (correction, True), (suspected_cause, True)]:
            feedback_text(value, optional=optional)
        require(token(author), 'feedback_author')
        require(revision_id is None or token(revision_id), 'task_revision')
        require(confidence in {'unknown', 'low', 'medium', 'high'}, 'feedback_confidence')
        evidence_ids = [] if evidence_ids is None else evidence_ids
        contrary_evidence_ids = [] if contrary_evidence_ids is None else contrary_evidence_ids
        for ids in (evidence_ids, contrary_evidence_ids):
            require(isinstance(ids, list) and len(ids) <= 128 and all(token(i) for i in ids)
                    and len(set(ids)) == len(ids), 'feedback_evidence')
        request = dict(symptom=symptom, correction=correction, evidence_ids=evidence_ids,
                       contrary_evidence_ids=contrary_evidence_ids, suspected_cause=suspected_cause,
                       confidence=confidence, author=author, revision_id=revision_id)
        with self._locked() as files:
            rows = self._task_records(files, task_id)
            require(bool(rows), 'task_not_found')
            ident, previous = self._task_retry(files, task_id, rows, 'feedback', request_id, request)
            if previous:
                return self._task_receipt(previous, 'duplicate')
            revisions = [r for r in rows if r['kind'] == 'task']
            revision = next((r for r in revisions if r['record_id'] == revision_id), None) if revision_id is not None else revisions[-1]
            require(revision is not None, 'task_revision')
            selected = {e['event_id'] for s in revision['selections'] for e in s['events']}
            require(set(evidence_ids + contrary_evidence_ids) <= selected, 'evidence_not_selected')
            require(len(rows) < MAX_TASK_RECORDS - 1, 'task_capacity')
            row = dict(request, schema_version=1, kind='feedback', task_id=task_id,
                       record_id=ident, sequence=len(rows) + 1, request_hash=digest(request),
                       registrations=revision['registrations'],
                       evidence_status='reported_correction' if correction else 'insufficient_claim_evidence')
            row['revision_id'] = revision['record_id']
            require(len(encoded(row)) <= TASK_RECORD_LIMIT, 'task_record_size')
            files.write(('tasks', task_id, ident + '.json'), row)
            return self._task_receipt(row, 'recorded')

    def task(self, task_id):
        try:
            with self._locked() as files:
                rows = self._task_records(files, task_id)
                if not rows:
                    return {'status': 'disabled'}
                return dict(status='ok', task_id=task_id,
                            revisions=[r for r in rows if r['kind'] == 'task'],
                            feedback=[r for r in rows if r['kind'] == 'feedback'])
        except FileNotFoundError:
            return {'status': 'disabled'}
        except InvalidEvent as error:
            if str(error) == 'task_inactive':
                return {'status': 'disabled'}
            raise

    def _delete_tasks(self, files, registration_id):
        try:
            task_ids = files.names(('tasks',))
        except (OSError, ValueError):
            # An unsafe tasks root has no trustworthy lineage. Unlink links,
            # never follow them, and discard only this owned private subtree.
            files.clear(('tasks',))
            return
        for task_id in task_ids:
            try:
                # No writer is active under this guard. Pending content can
                # reference a registration absent from the committed revisions.
                for name in files.names(('tasks', task_id)):
                    if name.startswith('.pending-'):
                        files.unlink(('tasks', task_id, name))
                    else:
                        require(bool(re.fullmatch(r'[a-f0-9]{64}\.json', name)), 'corrupt_task')
                rows = self._task_records(files, task_id, active=False)
                remove = not rows or any(ref['registration_id'] == registration_id
                                         for row in rows for ref in row['registrations'])
            except (OSError, ValueError, TypeError, KeyError, RecursionError):
                # Unknown lineage cannot justify retaining private task bytes.
                # Valid unrelated tasks are checked individually and preserved.
                remove = True
            if remove:
                files.clear(('tasks', task_id))

    def _delete_evidence(self, files, registration_id):
        try:
            files.clear(('records', registration_id))
            self._delete_tasks(files, registration_id)
        finally:
            # Even an interrupted physical purge must discard the derived cache.
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
