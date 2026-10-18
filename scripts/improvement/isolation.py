#!/usr/bin/env python3
"""Deterministic Seatbelt canary qualification, never a live-model executor."""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import platform
import secrets
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

LIMIT = 65536
SANDBOX = Path('/usr/bin/sandbox-exec')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounded(command, cwd, timeout=10, limit=LIMIT):
    """Closed environment/descriptors, bounded combined output, kill owned group."""
    if not 0 < timeout <= 30 or not 0 < limit <= LIMIT:
        raise ValueError('Invalid process bounds')
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env={'PATH': '/usr/bin:/bin', 'LANG': 'C',
        'HOME': str(cwd), 'TMPDIR': str(cwd)}, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
    chunks = {process.stdout: bytearray(), process.stderr: bytearray()}
    selector = selectors.DefaultSelector()
    for stream in chunks:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    reason = None
    try:
        while selector.get_map():
            if time.monotonic() - started >= timeout:
                reason = 'timeout'; break
            for key, _ in selector.select(min(.1, timeout)):
                data = os.read(key.fileobj.fileno(), 4096)
                if not data:
                    selector.unregister(key.fileobj); continue
                remaining = limit - sum(map(len, chunks.values()))
                chunks[key.fileobj].extend(data[:remaining])
                if len(data) > remaining:
                    reason = 'output_limit'; break
            if reason:
                break
        if not reason:
            try:
                process.wait(timeout=max(.001, timeout-(time.monotonic()-started)))
            except subprocess.TimeoutExpired:
                reason = 'timeout'
    finally:
        # Always terminate the owned process group, including descendants retaining pipes.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
        selector.close()
        for stream in chunks:
            stream.close()
    return {'exit_code': process.returncode, 'stop_reason': reason,
            'stdout': bytes(chunks[process.stdout]).decode(errors='replace'),
            'stderr': bytes(chunks[process.stderr]).decode(errors='replace'),
            'duration_seconds': round(time.monotonic()-started, 4)}


def profile_for(assigned, runtime, executable, broker_port):
    assigned, runtime, executable = [Path(p).resolve(strict=True) for p in (assigned, runtime, executable)]
    if not assigned.is_dir() or not runtime.is_dir() or not executable.is_file():
        raise ValueError('Invalid runtime paths')
    if type(broker_port) is not int or not 1024 <= broker_port <= 65535:
        raise ValueError('Invalid broker port')
    if assigned == Path('/') or runtime == Path('/') or assigned == runtime or assigned in runtime.parents or runtime in assigned.parents:
        raise ValueError('Overlapping or broad roots')
    q = lambda p: json.dumps(str(p), ensure_ascii=True)
    ancestors = sorted(set(assigned.parents) | set(runtime.parents) | set(executable.parents), key=str)
    return '\n'.join([
        '(version 1)', '(deny default)', '(allow process-fork)', '(allow sysctl-read)',
        '(allow process-exec (subpath '+q(runtime)+') (literal '+q(executable)+'))',
        # dyld requires a literal root read; this does not allow its descendants.
        '(allow file-read* (literal "/") (subpath "/System/Library") (subpath "/usr/lib") '
        '(subpath '+q(runtime)+') (literal '+q(executable)+') (subpath '+q(assigned)+'))',
        '(allow file-read-metadata '+ ' '.join('(literal '+q(p)+')' for p in ancestors)+')',
        '(allow file-write* (subpath '+q(assigned)+') (literal "/dev/null"))',
        '(allow file-read* (literal "/dev/null") (literal "/dev/urandom"))',
        '(allow network-outbound (remote ip "localhost:'+str(broker_port)+'"))',
    ])+'\n'


class MockBroker:
    """One synthetic schema, no upstream connection or real authentication."""
    def __init__(self):
        self.token = secrets.token_hex(24)
        self.expires = time.monotonic()+20
        self.accepted = 0
        self.server = None

    def check(self, method, target, host, authorization, body):
        if method != 'POST' or target != '/v1/responses' or host != '127.0.0.1:'+str(self.server.server_port):
            return 403
        if authorization != 'Bearer '+self.token or time.monotonic() >= self.expires:
            return 403
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            return 400
        if (not isinstance(data, dict) or type(data.get('max_output_tokens')) is not int
                or data != {'model': 'synthetic-model', 'input': 'synthetic fixture', 'max_output_tokens': 1}):
            return 400
        if self.accepted >= 1:
            return 429
        self.accepted += 1
        return 200

    def __enter__(self):
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.connection.settimeout(1)
                try:
                    length = int(self.headers.get('Content-Length', '-1'))
                    if not 0 <= length <= 4096 or self.headers.get('Transfer-Encoding'):
                        status = 413
                    else:
                        body = self.rfile.read(length)
                        status = owner.check('POST', self.path, self.headers.get('Host'), self.headers.get('Authorization'), body)
                    self.send_response(status); self.send_header('Content-Length', '2'); self.end_headers(); self.wfile.write(b'{}')
                except (OSError, ValueError):
                    self.close_connection = True
            def do_GET(self):
                self.send_error(403)
            do_CONNECT = do_GET
        self.server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.token = ''; self.expires = 0
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)


PROBE = r'''
import errno, http.client, json, os, pathlib, socket, subprocess, sys
m=json.loads(sys.argv[1]); checks={"started": True}
p=pathlib.Path(m["assigned"])
checks["fixture_read"]=p.joinpath("fixture").read_text()=="synthetic fixture"
p.joinpath("result").write_text("synthetic result")
checks["output_write"]=p.joinpath("result").read_text()=="synthetic result"
for name,path in m["protected"].items():
 try: pathlib.Path(path).read_bytes(); checks[name]=False
 except OSError as exc: checks[name]=exc.errno in (errno.EPERM,errno.EACCES)
child=subprocess.run([sys.executable,"-I","-S","-c","import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()",m["protected"]["other_arm"]],capture_output=True,timeout=2)
checks["child_read_denied"]=child.returncode!=0 and (b"Operation not permitted" in child.stderr or b"Permission denied" in child.stderr)
for name,family,kind,address in m["denied_network"]:
 s=socket.socket(family,kind);s.settimeout(.5)
 try:
  if kind==socket.SOCK_DGRAM:s.sendto(b"synthetic",tuple(address))
  else:s.connect(address if family==socket.AF_UNIX else tuple(address))
  checks[name]=False
 except OSError as exc: checks[name]=exc.errno in (errno.EPERM,errno.EACCES)
 finally:s.close()
def request(method="POST",target="/v1/responses",body=None,token=None,host=None):
 c=http.client.HTTPConnection("127.0.0.1",m["broker_port"],timeout=2)
 headers={"Authorization":"Bearer "+(m["token"] if token is None else token),"Host":host or "127.0.0.1:"+str(m["broker_port"])}
 c.request(method,target,json.dumps(body if body is not None else {"model":"synthetic-model","input":"synthetic fixture","max_output_tokens":1}),headers)
 r=c.getresponse();status=r.status;r.read();c.close();return status
checks["broker_reject_destination"]=request(host="outside.invalid")==403
checks["broker_reject_fields"]=request(body={"url":"https://outside.invalid"})==400
checks["broker_reject_capability"]=request(token="wrong")==403
checks["broker_reject_connect"]=request(method="CONNECT",target="outside.invalid:443")==403
checks["broker_mock_allowed"]=request()==200
checks["broker_budget_exhausted"]=request()==429
print(json.dumps(checks))
'''


def qualify(output_directory, *, timeout=10):
    """Record exact local canaries; a passing result never enables native/model trials."""
    output = Path(output_directory).absolute()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    receipt = {'schema_version': 1, 'evidence_kind': 'isolation_canary_qualification',
        'status': 'blocked', 'native_client_qualified': False, 'live_transport_qualified': False,
        'promotion_eligible': False, 'transport': 'synthetic_mock_only',
        'unsupported': ['native_client_and_native_read', 'live_provider_authentication', 'Linux',
                        'independent_holdout_custody', 'DNS_resolver', 'resource_memory_cpu_limits',
                        'detached_descendant_cleanup', 'loopback_broker_port_identity'],
        'runner_sha256': file_hash(__file__), 'probe_sha256': hashlib.sha256(PROBE.encode()).hexdigest(),
        'environment': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()},
        'checks': {}}
    home_canary = output/'synthetic-home-canary'
    try:
        if platform.system() != 'Darwin' or not SANDBOX.is_file():
            receipt['reason'] = 'seatbelt_unavailable'
            return receipt
        with tempfile.TemporaryDirectory(prefix='isolated-canary-') as temporary, MockBroker() as broker:
            root = Path(temporary).resolve();assigned=root/'assigned';assigned.mkdir(mode=0o700)
            protected={}
            for name in ['host_home','host_history','other_arm','holdout','evaluator']:
                path=root/name;path.write_text('synthetic secret');protected[name]=str(path)
            home_canary.write_text('synthetic secret');home_canary.chmod(0o600)
            protected['host_home']=str(home_canary)
            receipt['canary_layout']={'home_canary_under_actual_home':home_canary.is_relative_to(Path.home().resolve()),
                                     'content':'synthetic sentinels only; no actual history/authentication read'}
            (assigned/'fixture').write_text('synthetic fixture')
            (assigned/'escape').symlink_to(root/'holdout')
            protected['symlink_escape']=str(assigned/'escape')
            protected['parent_traversal']=str(assigned/'..'/'other_arm')
            sockets=[];denied=[]
            try:
                for name,family,kind,address in [('ipv4_denied',socket.AF_INET,socket.SOCK_STREAM,('127.0.0.1',0)),
                        ('ipv6_denied',socket.AF_INET6,socket.SOCK_STREAM,('::1',0)),
                        ('udp_denied',socket.AF_INET,socket.SOCK_DGRAM,('127.0.0.1',0)),
                        ('unix_denied',socket.AF_UNIX,socket.SOCK_STREAM,str(root/'listener.sock'))]:
                    sock=socket.socket(family,kind);sockets.append(sock);sock.bind(address)
                    if kind==socket.SOCK_STREAM:sock.listen(2)
                    sock.setblocking(False)
                    denied.append([name,family,kind,sock.getsockname()])
                executable=Path(sys.executable).resolve();runtime=Path(sys.base_prefix).resolve()
                profile=profile_for(assigned,runtime,executable,broker.server.server_port)
                (output/'profile.sb').write_text(profile);(output/'profile.sb').chmod(0o600)
                receipt.update(profile_sha256=hashlib.sha256(profile.encode()).hexdigest(),
                    executable_sha256=file_hash(executable), executable=str(executable), runtime=str(runtime))
                manifest={'assigned':str(assigned),'protected':protected,'denied_network':denied,
                          'broker_port':broker.server.server_port,'token':broker.token}
                result=bounded([str(SANDBOX),'-p',profile,str(executable),'-I','-S','-c',PROBE,json.dumps(manifest)],assigned,timeout)
                receipt['process']=result
                if result['exit_code']==0 and not result['stop_reason']:
                    try:
                        receipt['checks']=json.loads(result['stdout'])
                    except ValueError:
                        receipt['reason']='invalid_probe_output'
                    else:
                        receipt['checks']['broker_accepted_once']=broker.accepted==1
                        receipt['checks']['external_output_observed']=(assigned/'result').read_text()=='synthetic result'
                        for row,sock in zip(denied,sockets):
                            try:
                                if row[2]==socket.SOCK_STREAM:connection,_=sock.accept();connection.close()
                                else:sock.recvfrom(100)
                                receipt['checks'][row[0]+'_server_empty']=False
                            except BlockingIOError:receipt['checks'][row[0]+'_server_empty']=True
                        receipt['status']='pass' if receipt['checks'] and all(v is True for v in receipt['checks'].values()) else 'fail'
                else:
                    receipt['reason']='probe_did_not_complete'
            finally:
                for sock in sockets:sock.close()
        receipt['cleanup']='owned temporary files and listeners closed; process group killed'
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        receipt['reason']=type(exc).__name__
    finally:
        home_canary.unlink(missing_ok=True)
        receipt['receipt_sha256']=digest(receipt)
        target=output/'receipt.json';target.write_text(json.dumps(receipt,indent=2)+'\n');target.chmod(0o600)
    return receipt


def run_trial(frozen_trial, isolation_receipt, broker_capability=None):
    """Fail-closed consumer contract. Canary evidence cannot authorize a live trial."""
    receipt=dict(isolation_receipt);identity=receipt.pop('receipt_sha256',None)
    if identity != digest(receipt) or receipt.get('runner_sha256') != file_hash(__file__):
        raise ValueError('Receipt identity mismatch')
    if receipt.get('schema_version') != 1 or receipt.get('evidence_kind') != 'isolation_canary_qualification':
        raise ValueError('Unsupported receipt schema')
    if receipt.get('environment') != {'system':platform.system(), 'release':platform.release(), 'machine':platform.machine()}:
        raise ValueError('Environment identity mismatch')
    if frozen_trial.get('isolation_receipt_sha256') != identity or frozen_trial.get('profile_sha256') != receipt.get('profile_sha256'):
        raise ValueError('Frozen trial boundary mismatch')
    return {'status':'blocked','reason':'native_client_and_live_transport_unqualified',
            'model_requests':0,'promotion_eligible':False,'isolation_receipt_sha256':identity}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='New private evidence directory; no implicit parent creation')
    args=parser.parse_args()
    result=qualify(args.output)
    print(json.dumps({'status':result['status'],'evidence_kind':result['evidence_kind'],
                      'native_client_qualified':False,'live_transport_qualified':False}))
    return 0 if result['status']=='pass' else 1

if __name__=='__main__':
    raise SystemExit(main())
