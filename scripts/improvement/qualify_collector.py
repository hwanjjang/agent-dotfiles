#!/usr/bin/env python3
"""Bounded synthetic installed-callback benchmark; never opens the real account."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from account.observation.store import Store, digest


def summary(values):
    values = sorted(values)
    if not values: return {'count': 0}
    return dict(count=len(values), min_ms=values[0], median_ms=statistics.median(values),
                p95_ms=values[min(len(values)-1, int(.95*len(values)))], max_ms=values[-1])


def qualify(output, count=10000, workers=4, seconds=120):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    home=output/'home'; home.mkdir(mode=0o700); project=output/'project'; project.mkdir(mode=0o700)
    store=Store(home); grant=store.grant(project, client='codex', source='codex-hooks-v1')
    rid, epoch=grant['registration_id'], grant['epoch']
    bundle=home/'.agents/agent-dotfiles/bundle'; bundle.mkdir(parents=True)
    shutil.copytree(ROOT/'account', bundle/'account', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    callback=home/'.agents/bin/observation-hook.py'; callback.parent.mkdir()
    shutil.copy2(ROOT/'account/hooks/observation-hook.py', callback)
    source_names=['account/observation/'+n for n in ('store.py','native.py','environment.py','files.py')]
    source_names += ['account/hooks/observation-hook.py', 'scripts/improvement/qualify_collector.py']
    report=dict(reference=dict(system=platform.system(), release=platform.release(), machine=platform.machine(),
                               python=platform.python_version()),
                source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names},
                target_callbacks=count, workers=workers, wall_budget_seconds=seconds,
                latency_target_p95_ms=50, native_model_session=False, import_batches=0,
                percentile='sorted index floor(0.95*n), capped to last',
                account='disposable synthetic account only')
    for name, expected in report['source_sha256'].items():
        if name.startswith('account/'):
            if hashlib.sha256((bundle/name).read_bytes()).hexdigest() != expected:
                raise ValueError('installed fixture differs from source snapshot')
    report['installed_snapshot_verified'] = True
    def payload(number):
        return json.dumps(dict(cwd=str(project), session_id='capacity-session', turn_id='capacity-turn',
                               hook_event_name='PostToolUse', tool_name='Bash', tool_use_id=f'tool-{number}')).encode()
    command=[sys.executable,str(callback),rid,epoch,'codex']
    # Real process death after fsynced reservation, before an immutable record.
    crash_code='''import os,signal,sys
sys.path.insert(0,sys.argv[4])
from account.observation.files import Files
from account.observation.store import Store
original=Files.write
def interrupted(self,path,value):
 original(self,path,value)
 if path[0]=='grants' and value.get('high_water',0)>0:os.kill(os.getpid(),signal.SIGKILL)
Files.write=interrupted
Store(sys.argv[1]).capture_native(sys.argv[2],sys.argv[3],sys.stdin.buffer)
'''
    crash=subprocess.run([sys.executable,'-c',crash_code,str(home),rid,epoch,str(ROOT)],input=payload(0),
                         capture_output=True,cwd=project,timeout=5)
    report['interrupted_attempt']={'returncode':crash.returncode,'records_before_retry':len(store.events(rid)),
                                  'reservation_after_kill':store.registration(rid)['high_water']}
    start=time.monotonic(); deadline=start+seconds; counter=iter(range(count)); lock=threading.Lock(); rows=[]
    log=(output/'callbacks.jsonl').open('w')
    def worker():
        while time.monotonic()<deadline:
            with lock:
                number=next(counter,None)
            if number is None:return
            began=time.perf_counter()
            try:
                result=subprocess.run(command,input=payload(number),capture_output=True,cwd=project,
                                      timeout=max(.01,min(5,deadline-time.monotonic())))
                status='neutral' if result.returncode==0 and result.stdout==b'{}\n' and not result.stderr else 'callback_error'
            except subprocess.TimeoutExpired:
                status='timeout'
            row={'number':number,'status':status,'ms':(time.perf_counter()-began)*1000}
            with lock:
                rows.append(row); log.write(json.dumps(row)+'\n'); log.flush()
                if len(rows)%1000==0:print(json.dumps({'callbacks':len(rows),'elapsed_seconds':time.monotonic()-start}),flush=True)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(lambda _:worker(),range(workers)))
    finally:log.close()
    report['capture_seconds']=time.monotonic()-start
    report['attempts']=len(rows); report['statuses']=dict(collections.Counter(r['status'] for r in rows))
    report['latency']=summary([r['ms'] for r in rows])
    report['last_1000_latency']=summary([r['ms'] for r in rows[-1000:]])
    events=store.events(rid); actual={e['event_id'] for e in events}
    expected={digest([rid,epoch,'capacity-session',digest(['PostToolUse','capacity-turn',f'tool-{r["number"]}'])]) for r in rows}
    report['durable_records']=len(events); report['missing_record_count']=len(expected-actual)
    report['unexpected_record_count']=len(actual-expected)
    report['unique_sequence_count']=len({e['sequence'] for e in events})
    report['reservation_high_water']=store.registration(rid)['high_water']
    report['reservation_gap_count']=report['reservation_high_water']-len(events)
    replay=[]
    if rows:
        for n in range(min(20,len(rows))):
            began=time.perf_counter(); result=subprocess.run(command,input=payload(rows[n]['number']),capture_output=True,cwd=project,timeout=5)
            replay.append({'ms':(time.perf_counter()-began)*1000,'neutral':result.returncode==0 and result.stdout==b'{}\n'})
    report['replay']={'attempts':len(replay),'all_neutral':all(r['neutral'] for r in replay),
                      'latency':summary([r['ms'] for r in replay]),'records_after':len(store.events(rid))}
    report['capacity_pass']=(len(rows)==count and len(events)==count and not expected-actual and not actual-expected
                             and report['unique_sequence_count']==count and report['replay']['records_after']==count
                             and report['statuses']=={'neutral':count})
    report['latency_target_pass']=report['capacity_pass'] and report['latency']['p95_ms']<50
    report['limitations']=['Synthetic installed callbacks, not native host scheduling or model execution',
                           'No power-loss test, cold-cache control or hardware fsync guarantee',
                           'Neutral callback output is not a persistence acknowledgment; ledger independently checked',
                           'Retained synthetic grant, records and interrupted reservation under selected evidence output']
    report['total_seconds']=time.monotonic()-start
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('attempts','durable_records','capacity_pass','latency_target_pass','total_seconds')}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--count',type=int,default=10000)
    parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    parser.add_argument('--seconds',type=int,default=120)
    args=parser.parse_args()
    if not 1<=args.count<=10000 or not 1<=args.seconds<=600:parser.error('count 1..10000; seconds 1..600')
    result=qualify(args.output.resolve(),args.count,args.workers,args.seconds)
    sys.exit(0 if result['capacity_pass'] else 1)
