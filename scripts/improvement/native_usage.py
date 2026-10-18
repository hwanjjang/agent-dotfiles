"""Bounded app-server aggregates, not billing or wire counts.

Caller must first match thread/turn identity. Guards are explicitly declared,
post-use thresholds; this module cannot authorize, interrupt or launch a turn.
"""
import copy
import time

FIELDS = ('totalTokens', 'inputTokens', 'cachedInputTokens',
          'cacheWriteInputTokens', 'outputTokens', 'reasoningOutputTokens')
LIMIT = 64
MAX_INT = 2**63 - 1


class Usage:
    def __init__(self, *, soft_total, soft_output, sink=None):
        if any(type(n) is not int or not 0 < n <= MAX_INT for n in (soft_total, soft_output)):
            raise ValueError('usage_budget_shape')
        self.soft_total = soft_total
        self.soft_output = soft_output
        self.sink = sink
        self.start = time.monotonic()
        self.notifications = self.duplicates = self.changed_snapshots = 0
        self.first = self.latest = self.stop = None
        self.persisted = True
        self.sink_snapshots = 0
        self.retention_exhausted = False

    def accept(self, payload):
        """Project one already identity-matched payload; return a stop reason."""
        self.notifications += 1
        malformed = False

        def integer(value):
            nonlocal malformed
            if type(value) is not int or not 0 <= value <= MAX_INT:
                malformed = True
                return None
            return value

        if not isinstance(payload, dict):
            payload = {}
            malformed = True
        snapshot = {
            'sequence': self.notifications,
            'elapsed_ms': int((time.monotonic() - self.start) * 1000),
            'presence': {}, 'provenance': 'app_server_aggregate_not_billing',
            'provider_detail_presence': 'unknown',
            'last_origin': 'not_discriminated_by_notification',
            'cumulative_discontinuity': False,
            'component_relationship_anomaly': False,
        }
        for section in ('total', 'last'):
            raw = payload.get(section)
            if raw is not None and not isinstance(raw, dict):
                malformed = True
            raw = raw if isinstance(raw, dict) else {}
            snapshot['presence'][section] = {key: key in raw for key in FIELDS}
            counters = {key: integer(raw[key]) if key in raw else None for key in FIELDS}
            snapshot[section] = counters
            n, i, o = (counters[k] for k in ('totalTokens', 'inputTokens', 'outputTokens'))
            if all(x is not None for x in (n, i, o)) and n != i + o:
                snapshot['component_relationship_anomaly'] = True
            for child, parent in (('cachedInputTokens', 'inputTokens'),
                                  ('cacheWriteInputTokens', 'inputTokens'),
                                  ('reasoningOutputTokens', 'outputTokens')):
                if (counters[child] is not None and counters[parent] is not None
                        and counters[child] > counters[parent]):
                    snapshot['component_relationship_anomaly'] = True
        snapshot['modelContextWindow'] = (
            integer(payload['modelContextWindow'])
            if payload.get('modelContextWindow') is not None else None)
        if self.latest:
            snapshot['cumulative_discontinuity'] = any(
                snapshot['total'][key] is not None and self.latest['total'][key] is not None
                and snapshot['total'][key] < self.latest['total'][key] for key in FIELDS)

        def projection(s):
            return {key: s[key] for key in ('total', 'last', 'presence', 'modelContextWindow')}

        duplicate = self.latest is not None and projection(snapshot) == projection(self.latest)
        snapshot['duplicate_snapshot'] = duplicate
        reason = None
        if malformed:
            reason = 'usage_shape'
        elif any(snapshot['total'][key] is None for key in ('totalTokens', 'outputTokens')):
            reason = 'usage_unavailable'
        elif snapshot['cumulative_discontinuity']:
            reason = 'usage_discontinuity'
        elif self.retention_exhausted or (not duplicate and self.changed_snapshots >= LIMIT):
            reason = 'usage_retention_limit'
        if duplicate:
            self.duplicates += 1
        elif self.changed_snapshots < LIMIT:
            self.changed_snapshots += 1
        self.latest = snapshot
        if self.first is None:
            self.first = snapshot
        # The sink receives 64 changed snapshots plus one terminal overflow,
        # before the caller can act on the returned stop. Later calls cannot
        # cause further writes, even when the caller ignores that stop.
        if not duplicate and self.retention_exhausted:
            self.persisted = False
        if not duplicate and self.sink is not None and not self.retention_exhausted:
            self.sink_snapshots += 1
            try:
                self.sink(copy.deepcopy(snapshot))
            except Exception:
                self.persisted = False
                reason = 'usage_persistence_failed'
        if not duplicate and self.notifications - self.duplicates > LIMIT:
            self.retention_exhausted = True
        if self.stop is None:
            if reason:
                self.stop = {'reason': reason, 'sequence': self.notifications,
                             'metric': None, 'threshold': None, 'observed': None}
            else:
                for metric, threshold in (('totalTokens', self.soft_total),
                                          ('outputTokens', self.soft_output)):
                    observed = snapshot['total'][metric]
                    if observed >= threshold:
                        self.stop = {'reason': 'soft_usage_stop', 'sequence': self.notifications,
                                     'metric': 'total.' + metric, 'threshold': threshold,
                                     'observed': observed}
                        break
        return reason or (self.stop['reason'] if self.stop else None)

    def summary(self):
        """Return an independent numeric snapshot, not authority or billing."""
        return copy.deepcopy({
            'notifications': self.notifications, 'duplicates': self.duplicates,
            'changed_snapshots_retained': self.changed_snapshots,
            'first': self.first, 'latest': self.latest, 'stop': self.stop,
            'snapshot_limit': LIMIT, 'sink_configured': self.sink is not None,
            'all_changed_snapshots_persisted': self.sink is not None and self.persisted,
            'reported_total_soft_guard': self.soft_total,
            'reported_output_soft_guard': self.soft_output,
            'coverage': ('Observed app-server snapshots only; failed/in-flight work '
                         'and upstream detail presence unknown.'),
            'response_or_request_count': None, 'billing_usage': None,
            'sink_snapshots': self.sink_snapshots,
            'retention_exhausted': self.retention_exhausted,
        })
