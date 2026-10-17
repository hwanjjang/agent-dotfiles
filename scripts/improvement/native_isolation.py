#!/usr/bin/env python3
"""Qualify only a fixed synthetic Codex workflow inside an existing Docker host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import uuid

ARCHIVE_SHA256='9d8ecf2d19d3e184877983902d6c85de48b3888dcb72c382a8a0c975845927fb'
BINARY_SHA256='8a96f66d059d653e68bfd5f3c79337e6f1d7d170d80bf705eb7d0249b34c0ece'
IMAGE='python@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83'
SOURCE=Path(__file__).resolve().parent
LIMIT=2_000_000


def file_hash(path):
    with open(path,'rb') as stream:
        result=hashlib.sha256()
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
        return result.hexdigest()


def run(command,timeout=15,limit=LIMIT):
    """Bound transport output and owned client lifetime; container cleanup is separate."""
    p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       close_fds=True,start_new_session=True)
    output={p.stdout:bytearray(),p.stderr:bytearray()};selector=selectors.DefaultSelector()
    for stream in output:os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ)
    deadline=time.monotonic()+timeout;reason=None
    try:
        while selector.get_map():
            if time.monotonic()>=deadline:reason='timeout';break
            for key,_ in selector.select(.1):
                data=os.read(key.fileobj.fileno(),4096)
                if not data:selector.unregister(key.fileobj);continue
                remaining=limit-sum(map(len,output.values()));output[key.fileobj].extend(data[:remaining])
                if len(data)>remaining:reason='output_limit';break
            if reason:break
        if not reason:
            try:p.wait(timeout=max(.01,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:reason='timeout'
    finally:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait();selector.close()
        for stream in output:stream.close()
    return {'exit':p.returncode,'stop_reason':reason,'stdout':output[p.stdout].decode(errors='replace'),
            'stderr':output[p.stderr].decode(errors='replace')}


def checked(command,timeout=15):
    result=run(command,timeout)
    if result['exit'] or result['stop_reason']:raise RuntimeError('docker_command_failed: '+result['stderr'][:1000])
    return result['stdout']


def evaluate(events,boundary):
    """A terminal turn alone is insufficient; require actual native tools and denials."""
    if not boundary:return False
    try:
        summaries=[x['summary'] for x in events if 'summary' in x]
        identities=[x for x in events if 'binary_version' in x]
        if len(summaries)!=1 or len(identities)!=1:return False
        if identities[0]['binary_version']!='codex-cli 0.163.0' or identities[0]['binary_sha256']!=BINARY_SHA256:return False
        s=summaries[0];checks=s['tool_canaries'];replies={x['native']['id']:x['native'].get('result',{}) for x in events if 'id' in x.get('native',{})}
        commands=[x['native']['params']['item'] for x in events if x.get('native',{}).get('method')=='item/completed' and x['native']['params']['item']['type']=='commandExecution']
        return (s['terminal']['params']['turn']['status']=='completed' and s['requests']==2
            and s['tool_positive']=='TOOL_OK' and s['dual_family_broker'] is True and s['live_model_calls']==0
            and replies[1]['platformOs']=='linux' and replies[3]['exitCode']==0
            and 'NATIVE_TOOL_OK' in replies[3]['stdout']
            and any(k['name']=='transport-fixture' and k['enabled'] is True for row in replies[2]['data'] for k in row['skills'])
            and len(commands)==1 and commands[0]['id']=='call_fixture' and commands[0]['status']=='failed' and commands[0]['exitCode']==3
            and all(checks[k]=='FileNotFoundError' for k in ['host','holdout','other_arm','symlink','docker_socket'])
            and checks['root']['errno']==30 and checks['udp_2']['errno']==101 and checks['udp_10']['errno']==101
            and checks['child_read_exit']!=0 and checks['fixture']=='ASSIGNED_FIXTURE' and checks['interfaces']==['lo'])
    except (KeyError,TypeError,ValueError):return False


def container_args(context,name,stage):
    return ['docker','--context',context,'create','--name',name,'--label','agent-dotfiles.native-isolation=true',
        '--pull','never','--network','none','--read-only','--user','65532:65532','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--pids-limit','128','--memory','768m','--cpus','1',
        '--tmpfs','/work:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777',
        '--mount',f'type=bind,src={stage}/runtime,dst=/runtime,readonly',
        '--mount',f'type=bind,src={stage}/probe,dst=/probe,readonly','--workdir','/work',IMAGE,
        'python3','/probe/native_probe.py']


def verify_boundary(info,stage):
    h=info['HostConfig'];mounts=info['Mounts']
    expected={(str(stage/'runtime'),'/runtime'),(str(stage/'probe'),'/probe')}
    return (h['NetworkMode']=='none' and h['ReadonlyRootfs'] is True and h['Privileged'] is False
        and h['CapDrop']==['ALL'] and h['SecurityOpt']==['no-new-privileges'] and h['PidMode']==''
        and info['Config']['User']=='65532:65532' and h['PidsLimit']==128 and h['Memory']==768*1024*1024
        and h['NanoCpus']==1_000_000_000 and len(mounts)==2
        and {(m['Source'],m['Destination']) for m in mounts}==expected
        and all(m['Type']=='bind' and m['RW'] is False and m['Propagation']=='rprivate' for m in mounts)
        and h['Tmpfs']=={'/work':'rw,nosuid,nodev,size=128m,mode=1777','/tmp':'rw,nosuid,nodev,noexec,size=32m,mode=1777'}
        and not h.get('CapAdd') and not h.get('Devices') and not h.get('PortBindings'))


def extract_verified(archive,destination):
    if file_hash(archive)!=ARCHIVE_SHA256:raise ValueError('unsupported_archive_digest')
    with tarfile.open(archive) as stream:
        members=stream.getmembers()
        for m in members:
            path=Path(m.name)
            if path.is_absolute() or '..' in path.parts or not (m.isfile() or m.isdir()):raise ValueError('unsafe_archive_member')
        stream.extractall(destination,members=members,filter='data')
    if file_hash(destination/'bin/codex')!=BINARY_SHA256:raise ValueError('unexpected_binary_digest')


def qualify(output,context,archive,staging_parent):
    """Never install, start a VM, pull an image, authenticate, or enable live trials."""
    output=Path(output).absolute();output.mkdir(mode=0o700,parents=False,exist_ok=False)
    receipt={'schema_version':1,'evidence_kind':'native_synthetic_isolation_qualification','status':'blocked',
        'native_client_qualified':False,'live_transport_qualified':False,'promotion_eligible':False,
        'transport':'linux_container_synthetic_mock_only','model_requests':0,'runner_sha256':file_hash(__file__),
        'source_sha256':{n:file_hash(SOURCE/n) for n in ['native_probe.py','native_tool_canary.py']},
        'archive_sha256':ARCHIVE_SHA256,'binary_sha256':BINARY_SHA256,'image':IMAGE,'checks':{},'cleanup_complete':False}
    stage=None;created=False;name='agent-native-isolation-'+uuid.uuid4().hex;docker=['docker','--context',context]
    try:
        parent=Path(staging_parent).absolute()
        if parent!=parent.resolve() or not parent.is_dir() or ',' in str(parent):raise ValueError('invalid_staging_parent')
        if not context or context.startswith('-'):raise ValueError('explicit_docker_context_required')
        image=json.loads(checked(docker+['image','inspect',IMAGE]))[0]
        if image['Architecture']!='arm64' or image['Os']!='linux':raise ValueError('linux_arm64_image_required')
        stage=Path(tempfile.mkdtemp(prefix='native-isolation-',dir=parent))
        # Container uid only needs traversal; evidence remains private outside the mounts.
        stage.chmod(0o755);(stage/'probe').mkdir();(stage/'protected').mkdir(mode=0o700)
        extract_verified(archive,stage/'runtime')
        for n in ['native_probe.py','native_tool_canary.py']:shutil.copyfile(SOURCE/n,stage/'probe'/n)
        protected={}
        for n in ['host','holdout','other_arm']:
            p=stage/'protected'/n;p.write_text('SYNTHETIC_UNMOUNTED_'+n);protected[n]=str(p)
        (stage/'probe/manifest.json').write_text(json.dumps(protected))
        args=container_args(context,name,stage);receipt['command']=args
        created=True;checked(args)
        info=json.loads(checked(docker+['inspect',name]))[0]
        boundary=verify_boundary(info,stage);receipt['boundary']=info['HostConfig'];receipt['mounts']=info['Mounts']
        if not boundary:raise ValueError('container_boundary_mismatch')
        result=run(docker+['start','-a',name],timeout=60)
        (output/'native.jsonl').write_text(result['stdout']);(output/'native.stderr').write_text(result['stderr'])
        final=json.loads(checked(docker+['inspect',name]))[0]
        events=[json.loads(l) for l in result['stdout'].splitlines()]
        receipt['checks']={'native_synthetic_workflow':evaluate(events,boundary),
            'container_exit_zero':final['State']['ExitCode']==0 and not final['State']['Running'],
            'not_oom_killed':not final['State'].get('OOMKilled',True),'bounded_transport_completed':not result['stop_reason']}
        receipt['native_summary']=next((x['summary'] for x in events if 'summary'in x),None)
        receipt['status']='pass' if all(receipt['checks'].values()) else 'fail'
        receipt['native_client_qualified']=receipt['status']=='pass'
    except (OSError,ValueError,KeyError,RuntimeError,tarfile.TarError) as exc:
        receipt['reason']=str(exc)[:1500]
    finally:
        if created:
            removal=run(docker+['rm','-f',name]);receipt['cleanup_complete']=removal['exit']==0 and not removal['stop_reason']
        else:receipt['cleanup_complete']=True
        # Keep owned staging if removal failed: a surviving container must not observe reuse.
        if stage and receipt['cleanup_complete']:shutil.rmtree(stage)
        if not receipt['cleanup_complete']:receipt['status']='blocked';receipt['native_client_qualified']=False;receipt['reason']='container_cleanup_failed';receipt['retained_staging']=str(stage)
        receipt['receipt_sha256']=hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest()
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        for p in output.iterdir():p.chmod(0o600)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='Fresh private evidence directory; parent must exist')
    parser.add_argument('--context',required=True,help='Existing Docker context; no implicit VM start')
    parser.add_argument('--codex-archive',type=Path,required=True,help='Official pinned 0.163.0 linux arm64 musl package')
    parser.add_argument('--staging-parent',type=Path,required=True,help='Existing Docker-visible directory for fresh owned staging')
    args=parser.parse_args();r=qualify(args.output,args.context,args.codex_archive,args.staging_parent)
    print(json.dumps({k:r[k] for k in ['status','evidence_kind','native_client_qualified','live_transport_qualified','promotion_eligible','cleanup_complete']},indent=2))
    return 0 if r['status']=='pass' else 1

if __name__=='__main__':raise SystemExit(main())
