"""Native tool canaries against synthetic files intentionally outside the mounts."""
import pathlib,socket,os,json,subprocess
checks={}; protected=json.loads(pathlib.Path('/probe/manifest.json').read_text())
for name,path in list(protected.items())+[('symlink','/work/project/escape'),('docker_socket','/var/run/docker.sock')]:
 try:pathlib.Path(path).read_bytes();checks[name]='UNEXPECTED_READ'
 except OSError as e:checks[name]=type(e).__name__
try:pathlib.Path('/forbidden-root-write').write_text('x');checks['root']='UNEXPECTED_WRITE'
except OSError as e:checks['root']={'errno':e.errno}
for fam,ip in [(socket.AF_INET,'192.0.2.1'),(socket.AF_INET6,'2001:db8::1')]:
 s=socket.socket(fam,socket.SOCK_DGRAM)
 try:s.sendto(b'SYNTHETIC_CANARY',(ip,53));checks['udp_'+str(fam)]='UNEXPECTED_SEND'
 except OSError as e:checks['udp_'+str(fam)]={'errno':e.errno}
 finally:s.close()
child=subprocess.run(['python3','-c','from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())',protected['host']],capture_output=True,text=True)
checks['child_read_exit']=child.returncode;checks['fixture']=pathlib.Path('fixture.txt').read_text();checks['interfaces']=os.listdir('/sys/class/net')
assert all(v not in ('UNEXPECTED_READ','UNEXPECTED_WRITE','UNEXPECTED_SEND') for v in checks.values() if isinstance(v,str))
assert child.returncode!=0 and checks['interfaces']==['lo']
pathlib.Path('native-tool-canaries.json').write_text(json.dumps(checks));print('NATIVE_TOOL_CANARIES '+json.dumps(checks));raise SystemExit(3)
