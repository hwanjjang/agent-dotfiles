"""Native callback recovery and bounded delivery attribution in disposable homes."""
import io
import json
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from account.observation.files import Files
from account.observation.store import Store


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve(); self.project = self.home/'project'; self.project.mkdir()
        self.store = Store(self.home)
        context = patch('account.observation.native.Path.cwd', return_value=self.project)
        context.start(); self.addCleanup(context.stop)
        self.grant = self.store.grant(self.project, client='codex', source='codex-hooks-v1')
        self.rid, self.epoch = self.grant['registration_id'], self.grant['epoch']

    def capture(self, number=1, **changes):
        row = dict(cwd=str(self.project), session_id='session', turn_id='turn',
                   hook_event_name='PostToolUse', tool_name='Bash', tool_use_id=f'tool-{number}')
        row.update(changes)
        return self.store.capture_native(self.rid, self.epoch, io.BytesIO(json.dumps(row).encode()))

    def test_capture_and_replay_do_not_scan_historical_record_bodies(self):
        self.assertEqual(self.capture()['status'], 'recorded')
        with patch.object(self.store, '_records', side_effect=AssertionError('full ledger scan')):
            self.assertEqual(self.capture()['status'], 'duplicate')
            self.assertEqual(self.capture(2)['status'], 'recorded')

    def test_reserved_capacity_below_ceiling_does_not_enumerate_directory(self):
        self.capture()
        with patch.object(Files, 'names', side_effect=AssertionError('unnecessary enumeration')):
            self.assertEqual(self.capture(2)['status'], 'recorded')
            self.assertEqual(self.capture(2)['status'], 'duplicate')

    def test_legacy_pending_entries_reserve_conservative_capacity_before_capture(self):
        with self.store._locked() as files:
            for n in range(2): files.write(('records', self.rid, f'.pending-legacy-{n}'), {})
        self.assertEqual(self.capture()['status'], 'recorded')
        self.assertEqual(self.store.events(self.rid)[0]['sequence'], 3)
        with patch('account.observation.store.MAX_RECORDS', 4):
            self.assertEqual(self.capture(2), {'status':'rejected', 'reason':'store_capacity'})
            self.assertEqual(self.capture()['status'], 'duplicate')

    def test_prior_sequence_frontier_reconciles_pending_entries_before_fast_path(self):
        with self.store._locked() as files:
            path = ('grants', self.rid + '.json'); grant = files.read(path)
            grant['native_sequence_version'] = 1; files.write(path, grant)
            for n in range(2): files.write(('records', self.rid, f'.pending-prior-{n}'), {})
        self.assertEqual(self.capture()['status'], 'recorded')
        self.assertEqual(self.store.events(self.rid)[0]['sequence'], 3)
        self.assertEqual(self.store.registration(self.rid)['native_sequence_version'], 2)

    def test_reservation_gaps_do_not_permanently_consume_real_file_capacity(self):
        original = Files.write
        def fail_record(files, path, value):
            if path[0] == 'records': raise OSError('injected before record')
            return original(files, path, value)
        with patch('account.observation.store.MAX_RECORDS', 2):
            with patch.object(Files, 'write', fail_record):
                for _ in range(2): self.assertEqual(self.capture()['status'], 'error')
            self.assertEqual(self.capture()['status'], 'recorded')
            self.assertEqual(self.capture(2), {'status':'rejected', 'reason':'store_capacity'})
        self.assertEqual(self.store.events(self.rid)[0]['sequence'], 3)

    def test_interrupted_reservation_leaves_gap_and_never_acks_missing_record(self):
        original = Files.write
        def fail_record(files, path, value):
            if path[0] == 'records': raise OSError('injected before record')
            return original(files, path, value)
        with patch.object(Files, 'write', fail_record):
            self.assertEqual(self.capture()['status'], 'error')
        self.assertEqual(self.store.events(self.rid), [])
        self.assertEqual(self.capture()['status'], 'recorded')
        self.assertEqual(self.store.events(self.rid)[0]['sequence'], 2)

    def test_published_record_retry_is_duplicate_after_interrupted_reply(self):
        original = Files.write
        def interrupt(files, path, value):
            original(files, path, value)
            if path[0] == 'records': raise OSError('injected after durable record')
        with patch.object(Files, 'write', interrupt):
            self.assertEqual(self.capture()['status'], 'error')
        self.assertEqual(self.capture()['status'], 'duplicate')
        self.assertEqual(len(self.store.events(self.rid)), 1)

    def test_legacy_frontier_migrates_once_and_malformed_marker_refuses(self):
        for n in range(3): self.capture(n)
        with self.store._locked() as files:
            path = ('grants', self.rid+'.json'); g = files.read(path)
            g.pop('native_sequence_version', None); g['high_water'] = 0; files.write(path, g)
        self.assertEqual(self.capture(3)['status'], 'recorded')
        self.assertEqual(max(e['sequence'] for e in self.store.events(self.rid)), 4)
        with self.store._locked() as files:
            g = files.read(path); g['native_sequence_version'] = 999; files.write(path, g)
        self.assertEqual(self.capture(4)['status'], 'rejected')

    def test_replay_changed_metadata_is_conflict(self):
        self.capture()
        self.assertEqual(self.capture(tool_name='apply_patch'), {'status':'rejected', 'reason':'identity_conflict'})

    def test_malformed_frontier_never_reuses_sequence(self):
        self.capture()
        with self.store._locked() as files:
            path=('grants',self.rid+'.json');g=files.read(path);g['high_water']=None;files.write(path,g)
        self.assertEqual(self.capture(2), {'status':'rejected','reason':'invalid_native_frontier'})

    def test_corrupt_replay_record_never_acknowledges(self):
        self.capture()
        with self.store._locked() as files:
            name=files.names(('records',self.rid))[0];path=('records',self.rid,name)
            record=files.read(path);record['events'][0]['sequence']=999;files.write(path,record)
        self.assertNotEqual(self.capture()['status'],'duplicate')

    def test_capacity_refusal_is_explicit_and_retains_prior_record(self):
        self.capture()
        with patch('account.observation.store.MAX_RECORDS',2):
            self.assertEqual(self.capture(2), {'status':'rejected','reason':'store_capacity'})
            self.assertEqual(self.capture()['status'],'duplicate')
        self.assertEqual(len(self.store.events(self.rid)),1)


class ProcessConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve(); self.project = self.home/'project'; self.project.mkdir()
        self.store = Store(self.home)
        self.grant = self.store.grant(self.project, client='codex', source='codex-hooks-v1')
        self.root = Path(__file__).resolve().parents[1]
        self.processes = []; self.addCleanup(self.cleanup_processes)

    def cleanup_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill(); process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None: stream.close()

    def process(self, body, *args):
        process = subprocess.Popen([sys.executable, '-c',
            "import sys; sys.path.insert(0,sys.argv[1]); " + body,
            str(self.root), str(self.home), self.grant['registration_id'], self.grant['epoch'], *args],
            cwd=self.project, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.processes.append(process); return process

    def capture_code(self):
        return ("import io,json; from pathlib import Path; from account.observation.store import Store; "
                "payload=json.dumps(dict(cwd=str(Path.cwd()),session_id='concurrent',turn_id='turn',"
                "hook_event_name='PostToolUse',tool_name='Bash',tool_use_id='same')).encode(); "
                "print(json.dumps(Store(sys.argv[2]).capture_native(sys.argv[3],sys.argv[4],io.BytesIO(payload))))")

    def collect(self, process):
        out, err = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, err); self.assertEqual(err,b'')
        return json.loads(out)

    def wait_file(self, path):
        deadline = time.monotonic()+3
        while not path.exists() and time.monotonic()<deadline: time.sleep(.005)
        self.assertTrue(path.exists(), 'bounded subprocess rendezvous')

    def test_concurrent_process_stable_id_records_once(self):
        processes = [self.process(self.capture_code()) for _ in range(8)]
        results = [self.collect(p)['status'] for p in processes]
        self.assertEqual(results.count('recorded'), 1)
        self.assertEqual(results.count('duplicate'), 7)
        self.assertEqual(len(self.store.events(self.grant['registration_id'])), 1)

    def test_revoke_during_inflight_capture_purges_and_prevents_post_tombstone_records(self):
        ready, release, revoking = [self.home/name for name in ('ready','release','revoking')]
        gate = """
import time
from pathlib import Path
from account.observation.files import Files
original = Files.write
def paused(files, path, value):
 if path[0] == 'records':
  Path(sys.argv[5]).touch()
  deadline=time.monotonic()+3
  while not Path(sys.argv[6]).exists():
   if time.monotonic()>deadline: raise TimeoutError('rendezvous expired')
   time.sleep(.005)
 return original(files,path,value)
Files.write=paused
"""
        capture = self.process(gate+self.capture_code(), str(ready), str(release))
        self.wait_file(ready)
        revoke = self.process("import json; from pathlib import Path; from account.observation.store import Store; "
                              "Path(sys.argv[5]).touch(); print(json.dumps(Store(sys.argv[2]).revoke(sys.argv[3])))", str(revoking))
        self.wait_file(revoking)
        self.assertIsNone(capture.poll()); release.touch()
        burst = [self.process(self.capture_code()) for _ in range(4)]
        self.assertEqual(self.collect(capture)['status'], 'recorded')
        self.assertEqual(self.collect(revoke)['status'], 'revoked')
        for process in burst: self.assertIn(self.collect(process)['status'], ('recorded','duplicate','disabled'))
        self.assertEqual(self.store.events(self.grant['registration_id']), [])
        self.assertIsNone(self.store.registration(self.grant['registration_id']))
        self.assertEqual(self.collect(self.process(self.capture_code()))['status'], 'disabled')
        self.assertEqual(self.store.events(self.grant['registration_id']), [])


class AttributionTests(unittest.TestCase):
    setUp = CapacityTests.setUp
    capture = CapacityTests.capture
    def receipt(self, revision='a'*40):
        import hashlib
        from account.observation.environment import COMPONENTS
        assets = {}
        for name in COMPONENTS.values():
            path=self.home/'.agents/agent-dotfiles/bundle'/name
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'synthetic component')
            assets['.agents/agent-dotfiles/bundle/'+name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':420}
        path=self.home/'.agents/agent-dotfiles/state/installed.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'version':1,'home':str(self.home),'source_revision':revision,'assets':assets,
                                   'instructions':{'private':'SECRET_NOT_RETAINED'}}));path.chmod(0o600)
        return path

    def test_boundary_snapshot_retains_only_delivery_identity_and_component_hashes(self):
        self.receipt();self.capture(hook_event_name='SessionStart')
        event=self.store.events(self.rid)[0];manifest=event['manifest']
        self.assertEqual(manifest['status'],'observed');self.assertEqual(manifest['source_revision'],'a'*40)
        self.assertEqual(manifest['boundary'],'session_start');self.assertFalse(manifest['effective_exposure_exact'])
        self.assertTrue(manifest['component_hashes']);self.assertIn('mid_interval_changes_not_excluded',manifest['gaps'])
        text=json.dumps(manifest);self.assertNotIn(str(self.home),text);self.assertNotIn('SECRET_NOT_RETAINED',text)

    def test_missing_and_midturn_drift_never_reuse_start_snapshot(self):
        receipt=self.receipt();self.capture(hook_event_name='SessionStart')
        self.capture(2)
        mid=next(e for e in self.store.events(self.rid) if e['event_kind']=='tool_end')
        self.assertIsNone(mid['manifest']);self.assertIn('environment_boundary_not_observed',mid['gaps'])
        receipt.unlink();self.capture(hook_event_name='Stop')
        stop=next(e for e in self.store.events(self.rid) if e['event_kind']=='response_end')
        self.assertEqual(stop['manifest']['status'],'unavailable');self.assertIsNone(stop['manifest']['source_revision'])

    def test_changed_component_is_drift_and_receipt_changes_refresh_at_end(self):
        from account.observation.environment import COMPONENTS
        self.receipt();self.capture(hook_event_name='SessionStart')
        self.receipt('b'*40)
        (self.home/'.agents/agent-dotfiles/bundle'/next(iter(COMPONENTS.values()))).write_bytes(b'changed')
        self.capture(hook_event_name='Stop')
        stop=next(e for e in self.store.events(self.rid) if e['event_kind']=='response_end')['manifest']
        self.assertEqual(stop['source_revision'],'b'*40);self.assertEqual(stop['drift'],'detected')
        self.assertFalse(stop['effective_exposure_exact'])

    def test_oversize_receipt_is_gap_not_capture_failure(self):
        path=self.receipt();path.write_bytes(b'x'*(512*1024+1))
        self.assertEqual(self.capture(hook_event_name='SessionStart')['status'],'recorded')
        self.assertEqual(self.store.events(self.rid)[0]['manifest']['status'],'unavailable')

    def test_budget_and_receipt_symlink_refuse_without_stale_identity(self):
        from account.observation import environment
        path=self.receipt()
        with patch.object(environment.time,'monotonic',side_effect=[0,1,1]):
            manifest=environment.snapshot(self.home,{'client':'codex','source':'codex-hooks-v1'},'session_start')
        self.assertEqual(manifest['status'],'unavailable');self.assertIsNone(manifest['receipt_sha256'])
        original=path.with_name('external.json');path.rename(original);path.symlink_to(original)
        self.capture(hook_event_name='SessionStart')
        self.assertEqual(self.store.events(self.rid)[0]['manifest']['status'],'unavailable')

    def test_mid_probe_receipt_change_discards_partial_identity(self):
        from account.observation import environment
        path=self.receipt();original=environment.hashlib.sha256;changed=[]
        def change(body):
            if not changed:
                changed.append(True);data=json.loads(path.read_text());data['source_revision']='c'*40
                path.write_text(json.dumps(data))
            return original(body)
        with patch.object(environment.hashlib,'sha256',side_effect=change):
            manifest=environment.snapshot(self.home,{'client':'codex','source':'codex-hooks-v1'},'session_start')
        self.assertEqual(manifest['status'],'unavailable');self.assertIsNone(manifest['source_revision'])
        self.assertIn('environment_changed_during_probe',manifest['gaps'])

    def test_revoked_grant_never_probes_environment(self):
        self.receipt();self.store.revoke(self.rid)
        with patch('account.observation.environment.snapshot',side_effect=AssertionError('no probe')):
            self.assertEqual(self.capture(hook_event_name='SessionStart')['status'],'disabled')


if __name__ == '__main__': unittest.main()
