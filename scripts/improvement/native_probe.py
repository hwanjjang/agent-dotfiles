"""Fixed synthetic workload; invoked only inside the verified outer container."""
import pathlib,json,os,socket,subprocess,threading,http.server,time,queue,signal,hashlib
P=pathlib.Path('/work'); C=P/'codex';C.mkdir(); W=P/'project';W.mkdir();(W/'fixture.txt').write_text('ASSIGNED_FIXTURE')
protected=json.loads(pathlib.Path('/probe/manifest.json').read_text())
canary={}
for label,path in list(protected.items())+[('docker_socket','/var/run/docker.sock')]:
 try:pathlib.Path(path).read_bytes();canary[label]='UNEXPECTED_READ'
 except OSError as e:canary[label]=type(e).__name__
(W/'escape').symlink_to(protected['host'])
try:(W/'escape').read_bytes();canary['symlink']='UNEXPECTED_READ'
except OSError as e:canary['symlink']=type(e).__name__
try:pathlib.Path('/root-write-canary').write_text('x');canary['root_write']='UNEXPECTED_WRITE'
except OSError as e:canary['root_write']={'type':type(e).__name__,'errno':e.errno}
for fam,ip in [(socket.AF_INET,'192.0.2.1'),(socket.AF_INET6,'2001:db8::1')]:
 s=socket.socket(fam,socket.SOCK_STREAM);s.settimeout(.2)
 try:s.connect((ip,443));canary['network_'+str(fam)]='UNEXPECTED_CONNECT'
 except OSError as e:canary['network_'+str(fam)]={'type':type(e).__name__,'errno':e.errno}
 finally:s.close()
canary['status']=[l for l in pathlib.Path('/proc/self/status').read_text().splitlines() if l.startswith(('NoNewPrivs:','CapEff:','Seccomp:'))]
canary['interfaces']=os.listdir('/sys/class/net');canary['pid1']=pathlib.Path('/proc/1/comm').read_text().strip();canary['fixture_read']=(W/'fixture.txt').read_text()
print(json.dumps({'preflight':canary}),flush=True)
assert all(v!='UNEXPECTED_READ' and v!='UNEXPECTED_CONNECT' and v!='UNEXPECTED_WRITE' for v in canary.values())
assert canary['interfaces']==['lo'];assert any(l.startswith('CapEff:') and l.endswith('0000000000000000') for l in canary['status'])
requests=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  n=int(self.headers.get('Content-Length','-1'))
  if self.path!='/v1/responses' or n<0 or n>200000 or len(requests)>=4:self.send_error(403);return
  raw=self.rfile.read(n);data=json.loads(raw)
  if data.get('model')!='synthetic-model' or data.get('stream') is not True:self.send_error(403);return
  requests.append(data)
  print(json.dumps({'request_number':len(requests),'model':data.get('model'),'keys':sorted(data),'tool_names':[x.get('name',x.get('type')) for x in data.get('tools',[])],'input_types':[x.get('type') for x in data.get('input',[])]}),flush=True)
  msg={'id':'msg_'+str(len(requests)),'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'NATIVE_CONTAINER_MOCK_OK','annotations':[]}]}
  events=[{'type':'response.created','response':{'id':'resp_'+str(len(requests))}},{'type':'response.output_item.added','output_index':0,'item':dict(msg,content=[])},{'type':'response.output_text.delta','item_id':msg['id'],'output_index':0,'content_index':0,'delta':'NATIVE_CONTAINER_MOCK_OK'},{'type':'response.output_item.done','output_index':0,'item':msg},{'type':'response.completed','response':{'id':'resp_'+str(len(requests)),'status':'completed','output':[msg],'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}}]
  if len(requests)==1:
   assert any(t.get('name')=='exec_command' for t in data.get('tools',[]))
   call={'id':'fc_fixture','type':'function_call','name':'exec_command','call_id':'call_fixture','arguments':json.dumps({'cmd':'python3 /probe/native_tool_canary.py','login':False,'workdir':'/work/project','max_output_tokens':2000,'yield_time_ms':1000})}
   events=[{'type':'response.created','response':{'id':'resp_tool'}},{'type':'response.output_item.added','output_index':0,'item':call},{'type':'response.output_item.done','output_index':0,'item':call},{'type':'response.completed','response':{'id':'resp_tool','status':'completed','output':[call],'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}}]
  payload=''.join('event: '+x['type']+'\ndata: '+json.dumps(x)+'\n\n' for x in events).encode();self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
class V6(http.server.ThreadingHTTPServer):
 address_family=socket.AF_INET6
 def server_bind(self):self.socket.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1);super().server_bind()
s4=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);port=s4.server_port;s6=V6(('::1',port),Handler)
for s in (s4,s6):threading.Thread(target=s.serve_forever,daemon=True).start()
(C/'config.toml').write_text(f'''model="synthetic-model"
model_provider="fixture"
approval_policy="never"
web_search="disabled"
check_for_update_on_startup=false
[model_providers.fixture]
name="Synthetic transport"
base_url="http://127.0.0.1:{port}/v1"
wire_api="responses"
requires_openai_auth=false
supports_websockets=false
request_max_retries=0
stream_max_retries=0
stream_idle_timeout_ms=10000
''')
S=C/'skills'/'transport-fixture';S.mkdir(parents=True);(S/'SKILL.md').write_text('---\nname: transport-fixture\ndescription: Return the synthetic transport fixture acknowledgement.\n---\nRead fixture.txt in the assigned project.\n')
env={k:v for k,v in os.environ.items() if k in ['PATH','LANG']};env['CODEX_HOME']=str(C)
p=subprocess.Popen(['/runtime/bin/codex','app-server','--listen','stdio://'],env=env,cwd=W,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
Q=queue.Queue();lines=[]
def reader(stream,kind):
 for line in stream:
  lines.append((kind,line));
  if sum(len(x[1]) for x in lines)>500000:os.killpg(p.pid,signal.SIGKILL);return
  if kind=='stdout':
   try:Q.put(json.loads(line))
   except ValueError:pass
  else:print(json.dumps({'stderr':line.strip()}),flush=True)
for st,k in [(p.stdout,'stdout'),(p.stderr,'stderr')]:threading.Thread(target=reader,args=(st,k),daemon=True).start()
def send(method,params,i=None):
 o={'method':method,'params':params}
 if i is not None:o['id']=i
 p.stdin.write(json.dumps(o)+'\n');p.stdin.flush()
def until(pred,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  x=Q.get(timeout=max(.1,end-time.monotonic()));print(json.dumps({'native':x}),flush=True)
  if pred(x):return x
 raise TimeoutError()
def rpc(i,method,params):
 send(method,params,i);x=until(lambda x:x.get('id')==i)
 if 'error' in x:raise RuntimeError(x)
 return x['result']
try:
 print(json.dumps({'binary_version':subprocess.check_output(['/runtime/bin/codex','--version'],text=True,env=env).strip(),'binary_sha256':hashlib.sha256(pathlib.Path('/runtime/bin/codex').read_bytes()).hexdigest()}),flush=True)
 rpc(1,'initialize',{'clientInfo':{'name':'isolated_transport_fixture','version':'0.1'},'capabilities':{'experimentalApi':True}});send('initialized',{})
 rpc(2,'skills/list',{'cwds':[str(W)],'forceReload':True})
 policy={'type':'externalSandbox','networkAccess':'restricted'}
 rpc(3,'command/exec',{'command':['python3','-c','from pathlib import Path; p=Path("fixture.txt"); print(p.read_text()); Path("tool-positive.txt").write_text("TOOL_OK"); print("NATIVE_TOOL_OK")'],'cwd':str(W),'sandboxPolicy':policy,'timeoutMs':5000,'outputBytesCap':10000})
 thread=rpc(4,'thread/start',{'model':'synthetic-model','cwd':str(W),'approvalPolicy':'never','ephemeral':True})['thread']['id']
 rpc(5,'turn/start',{'threadId':thread,'input':[{'type':'text','text':'Return the synthetic fixture acknowledgement.'}],'sandboxPolicy':policy,'approvalPolicy':'never'})
 terminal=until(lambda x:x.get('method')=='turn/completed',20)
 print(json.dumps({'summary':{'terminal':terminal,'requests':len(requests),'tool_positive':(W/'tool-positive.txt').read_text(),'tool_canaries':json.loads((W/'native-tool-canaries.json').read_text()),'dual_family_broker':True,'live_model_calls':0}}),flush=True)
finally:
 os.killpg(p.pid,signal.SIGTERM)
 try:p.wait(3)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 for s in (s4,s6):s.shutdown();s.server_close()
