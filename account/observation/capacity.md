# Native collector capacity and delivery attribution

Native capture keeps the existing Store as the sole grant, lock and persistence
owner. Immutable event records remain evidence; the optional SQLite index remains
derived and is not part of capture or consent checks. No background service,
queue, batching acknowledgment or new dependency is introduced.

## Sequence reservations and recovery

The grant's `high_water` now reserves native receipt sequence numbers. It does not
claim that every reserved number has a stored event. While holding the same
store-wide guard, capture validates the active epoch and exact process directory
before reading the bounded native envelope,
then directly locates the deterministic record for stable event identity. A replay
must match its stored normalized metadata and epoch; its original attribution is
preserved, and the record directory is synchronized before returning `duplicate`.

A fresh callback uses the reserved sequence span as a conservative upper bound on
record files. Below the ceiling it needs no directory enumeration; at or above
the bound it counts filenames so unused crash reservations do not falsely exhaust
real file capacity. It then durably advances the grant reservation and writes and
synchronizes its immutable record. Only then
does `capture_native()` return `recorded`. A crash before the record leaves a
reservation hole. A crash after record publication can be retried with stable
identity and becomes a duplicate after synchronization. Events without stable
source identity still have possible-duplicate uncertainty. The neutral installed
hook output is never a storage acknowledgment.

Native events include `native_sequence_reservation_gaps_possible`. Callers can
read the active grant's `high_water` and `start_after` alongside its current-epoch
ledger: with one native event per record, `high_water - start_after - event_count`
is the number of reserved positions without a retained event. This is not a count
of all lost host callbacks: callbacks that never reached reservation are unknown.
Sequence gaps never establish a missing model turn, failure or success.

Legacy grants without `native_sequence_version`, and the version-1 pilot, perform
one full validated ledger reconciliation before writing version 2. Migration
reserves at least the existing directory-entry count above `start_after`, covering
legacy pending files with conservative receipt-sequence gaps; it does not invent
events or change source history. Unknown versions, missing/non-integer
frontiers and contradictory replay records refuse capture. Revocation and expiry
are checked before payload/probe reads; revocation remains tombstone-first, and
regrant removes old-epoch evidence before accepting new capture. Synthetic import
identity, cursor and replay behavior retain their original path.

Full-ledger reads/rebuilds still validate historical record bodies. The capture
fast path does not revalidate unrelated history on every callback. Out-of-band
rewriting of valid grant/ledger files by the account owner is not a supported
recovery procedure; restoring an old grant alone can invalidate sequence history.
The optimization does not claim tamper-proof storage or hardware power-loss safety.

The native hard resource ceiling is 16,383 records per registration. Synthetic
capture/import registrations keep the earlier 4,096-entry read bound and
4,095-record write ceiling; their full-ledger scan is not benchmarked here. Filename enumeration
near the ceiling is still O(n), and mutations still serialize on the store guard. The measured
10,000-event workload is a qualification point, not a guarantee for every workload
up to the ceiling. Pending files consume capacity conservatively.

## Bounded environment snapshots

Only native SessionStart and Stop probe the explicitly selected account's installer
receipt and four fixed bundle components: account instructions, execution policy,
communication policy and native adapter. They store capture time, boundary, client
and adapter IDs, delivery revision, receipt digest, aggregate receipt-declared
component fingerprint, actual/declared hashes for the four components, drift and
gaps. No raw configuration, personal path, secret, actor or parent identity is
copied into the snapshot. The manifest is inline in its immutable event, so the
existing consent, retention and purge owner also owns attribution.

The receipt is read twice, at most 512 KiB each time; each component has a 64 KiB
limit. Reads reject symlink traversal, nonregular files, unexpected ownership,
nonprivate receipts, oversized or changed files. The 50 ms probe budget is checked
between local file operations; it is not hard cancellation of an OS read. The
installed callback's separate three-second alarm still bounds the process.

Unavailable, malformed, oversized, changed or over-budget probes store an explicit
unavailable manifest with no partial source identity. Tool callbacks receive no
cached manifest. A changed receipt at a later boundary is sampled anew. Probe
results always set `effective_exposure_exact=false`: unprobed files, project
overrides, model settings, client versions and intervening mid-turn edits remain
unknown. Equal start/end hashes cannot exclude a change between them. Historical
synthetic imports do not borrow today's receipt.

## Reproduce qualification

From a checkout, select a new ignored evidence directory:

```sh
python3 scripts/improvement/qualify_collector.py \
  --output .local/collector-qualification --count 10000 --workers 4 --seconds 120
```

The script creates only a disposable synthetic account and project under that new
directory. It verifies the copied runtime bytes, invokes the installed dispatcher
in 10,000 separate subprocesses, records per-callback timings, and independently
checks all expected event IDs and unique sequences. Four concurrent worker threads
each launch actual callback processes; this is not import-batch throughput. A real
SIGKILL after a durable reservation precedes the run, and twenty callback replays
must leave the record count unchanged. The evidence directory retains the
synthetic interrupted reservation, ledger, runtime hashes and measurements.

The process budget bounds the main capture phase; setup, independent ledger checks
and bounded replay add measured overhead. Missing records, timeout/failed callbacks
and incomplete runs remain in the denominator. No live native model session,
authentication, field hook scheduling, cold-cache or power-loss test is implied.

On 2026-10-18, the final frozen runtime completed 10,000 callback subprocesses
with four writers on Darwin 25.6.0 arm64 / Python 3.14.7. All 10,000 expected
records and unique sequences were independently verified. Twenty replays retained
10,000 records; the killed reservation left one explicit sequence gap. No callback
attempt timed out or returned malformed neutral output.

| Measurement | Final frozen run |
| --- | ---: |
| Capture wall time | 90.11 seconds |
| Capture throughput | 110.98 callbacks/second |
| Median callback latency | 33.15 ms |
| p95 callback latency | 48.16 ms |
| Maximum callback latency | 94.48 ms |
| Last 1,000 callbacks p95 | 48.10 ms |
| Twenty replay callbacks p95 | 31.36 ms |
| Total capture/check/replay time | 91.76 seconds |

Capacity/recovery and the proposed p95 under 50 ms target passed this one
reference-host synthetic run after the review corrections. This is not a
cross-host latency guarantee. The preceding version-2 run measured p95 48.04 ms
(89.57 seconds capture), before separating the synthetic ceiling and strengthening
the qualification predicate. That result remains historical. The
preceding version-1 candidate passed capacity but missed the target at p95
64.71 ms (103.79 seconds capture); an earlier candidate before its corruption
guard measured 62.99 ms. Both remain historical evidence. The final version-2
run includes the exact-process pre-read guard and the conservative capacity bound.
Raw per-callback timings, the reference environment and exact runtime hashes are
retained in ignored evidence. Only one final run was taken after each source correction;
no repeated runs were selected to hide slower results. The timings include actual
process startup and four-writer contention for PostToolUse only. The benchmark
contains no SessionStart/Stop boundary probes, whose snapshot reads hold the same
store lock; it does not qualify mixed-boundary workload latency or native scheduling,
model execution, cold caches or hardware power-loss durability.

## Design references

The existing private-file protocol retains file and directory synchronization.
[Python's OS documentation](https://docs.python.org/3.14/library/os.html) describes
atomic rename and `fsync`; [SQLite's atomic-commit explanation](https://www.sqlite.org/atomiccommit.html)
illustrates why durable commit requires more than an atomic filename change.
These primary sources were checked on 2026-10-18; no SQLite service or external
implementation was adopted. Earlier repository research and the measured quadratic
callback path motivated this bounded reservation design. Community evidence does
not establish this repository-specific optimization as a generally preferred
pattern; its selection rests on the existing ownership contract and qualification.
