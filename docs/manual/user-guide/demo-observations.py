#!/usr/bin/env python3
"""Run a synthetic observation demonstration in a disposable home only."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,required=True,help='Candidate checkout containing account/observation/store.py')
args=parser.parse_args()
repo=args.repo.resolve(strict=True)
if sys.version_info < (3,11) or not (repo/'account/observation/store.py').is_file():
    parser.error('Python 3.11+ and a checkout containing the observation store are required')
sys.path.insert(0,str(repo))
from account.observation.store import Store
with tempfile.TemporaryDirectory(prefix='observation-demo-') as temporary:
    base=Path(temporary).resolve()
    home,project=base/'home',base/'project'
    home.mkdir();project.mkdir()
    store=Store(home)
    grant=store.grant(project,start_after=0)
    identity=grant['registration_id'],grant['epoch']
    payload=json.dumps(dict(schema_version=1,project_root=str(project),client='synthetic',profile='default',source='fixture-v1',session_id='demo-session',sequence=1,source_event_id='demo-event-1',event_kind='tool_end',actor_id='parent',tool_category='shell',status='failure',output='SYNTHETIC_BODY_NOT_TO_STORE')).encode()
    print('capture:',store.capture(*identity,payload)['status'])
    print('retry:',store.capture(*identity,payload)['status'])
    events=store.events(grant['registration_id'])
    assert len(events)==1 and 'SYNTHETIC_BODY_NOT_TO_STORE' not in json.dumps(events)
    print('events:',len(events),'excluded body retained:',False)
    print('indexed:',store.rebuild_index())
    print('revoke:',store.revoke(grant['registration_id'])['status'])
    print('old epoch:',store.capture(*identity,payload)['status'])
    assert store.events(grant['registration_id'])==[]
print('Disposable account removed. No native hooks or model calls were used.')
