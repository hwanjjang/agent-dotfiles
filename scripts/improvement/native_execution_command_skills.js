// @exec: {"yield_time_ms": 30000, "max_output_tokens": 3000}
// Fixed synthetic boundary probe. The caller must separately establish remote OS
// isolation, protected fixture existence/unchanged bytes, and resource cleanup.
const allowed = ['apply_patch','exec_command','view_image','write_stdin','list_mcp_resource_templates','list_mcp_resources','read_mcp_resource','clock__curr_time','skills__list','skills__read'];
function projection(names) {
  let mask=0, unknown=0; const seen=new Set();
  for(const name of names){ const bit=allowed.indexOf(name); if(bit<0)unknown++;else mask|=1<<bit;seen.add(name); }
  return {mask,count:names.length,unknown,duplicates:names.length-seen.size};
}
function emit(check,result){text('BOUNDARY_CHECK:'+JSON.stringify({check,result}));}
function requireTrue(ok,name){if(!ok)throw Error('Boundary check failed: '+name);}
function decoded(value){if(typeof value==='string'){try{return JSON.parse(value);}catch{}}return value;}
function errorText(value){return typeof value==='string'?value:JSON.stringify(value);}
async function denied(fn,pattern){let value;try{value=await fn();}catch(e){value=String(e);}return pattern.test(errorText(value));}
const advertised=projection(ALL_TOOLS.map(x=>x.name));
const callable=projection(Object.keys(tools));
emit('catalog',{advertised,callable});
requireTrue([advertised,callable].every(x=>x.mask===1023&&x.count===10&&x.unknown===0&&x.duplicates===0),'inventory');
requireTrue(allowed.every(name=>typeof tools[name]==='function'),'callable tools');
const globals=['process','require','fetch','Deno','Bun','XMLHttpRequest','WebSocket','console','Atomics','SharedArrayBuffer','WebAssembly'];
requireTrue(globals.every(k=>typeof globalThis[k]==='undefined'),'globals');
let imports=0;
for(const spec of ['node:fs',HOST_URI,'https://example.invalid/fixture']){
  let refused=false;try{await import(spec);}catch(e){refused=/unsupported import/i.test(String(e));}
  requireTrue(refused,'import');imports++;
}
emit('globals_imports',{globals_absent:true,imports_refused:imports});
const resources=decoded(await tools.list_mcp_resources({}));
const templates=decoded(await tools.list_mcp_resource_templates({}));
const missing=await denied(()=>tools.read_mcp_resource({server:'qualification-missing-server',uri:HOST_URI}),/unknown MCP server/);
requireTrue(Array.isArray(resources.resources)&&resources.resources.length===0&&Array.isArray(templates.resourceTemplates)&&templates.resourceTemplates.length===0&&missing,'mcp');
emit('mcp',{resources_empty:true,templates_empty:true,foreign_server_refused:true});
// Shell quoting is fixed here; no caller-supplied JavaScript or shell input.
const hostPath=decodeURIComponent(HOST_URI.replace(/^file:\/\//,''));
const parent=hostPath.slice(0,hostPath.lastIndexOf('/'));
const protectedPaths=['host-only','history-only','credential-only','other-arm-only','evaluator-only'].map(x=>parent+'/'+x);
const probe = `import errno,json,os,pathlib,socket,subprocess,sys
paths=json.loads(sys.argv[1]); result={}
# This producer and its explicit child share the existing remote boundary.
# The trusted local coordinator/scorer are not contained by this probe.
io_source = """import errno,json,os,pathlib,sys
def check_io(targets, output):
 result={'fixture_read':pathlib.Path('/work/project/fixture.txt').read_text()=='ASSIGNED_REMOTE_FIXTURE'}
 marker=b'SYNTHETIC_ASSIGNED_TASK_OUTPUT'
 with open(output,'xb') as stream:stream.write(marker)
 try:result['task_write_readback']=pathlib.Path(output).read_bytes()==marker
 finally:pathlib.Path(output).unlink()
 denied={}
 for role,path in targets.items():
  row={}
  for operation in ('read','write','create'):
   flags={'read':os.O_RDONLY,'write':os.O_WRONLY|os.O_TRUNC,'create':os.O_CREAT|os.O_EXCL|os.O_WRONLY}[operation]
   name=path+'.new' if operation=='create' else path
   try:
    fd=os.open(name,flags,0o600);os.close(fd);value=0
   except OSError as error:value=error.errno
   row[operation+'_errno']=value
  denied[role]=row
 result['denied']=denied
 return result
"""
exec(io_source)
parent=str(pathlib.PurePosixPath(paths[0]).parent)
targets={'grading':parent+'/evaluator-only','other_arm':parent+'/other-arm-only',
 'installer_receipt':parent+'/account/.agents/agent-dotfiles/state/installed.json',
 'installer_journal':parent+'/account/.agents/agent-dotfiles/state/transactions/synthetic/journal.json'}
direct=check_io(targets,'/work/project/scoped-io-direct')
child_source=io_source+"\\nprint(json.dumps(check_io(json.loads(sys.argv[1]),sys.argv[2]),separators=(',',':')))"
child=subprocess.run([sys.executable,'-c',child_source,json.dumps(targets),'/work/project/scoped-io-child'],
 capture_output=True,text=True,timeout=3)
if child.returncode!=0 or child.stderr or len(child.stdout)>4096:raise RuntimeError('child_probe_failed')
result['scoped_io']={'direct':direct,'child':json.loads(child.stdout)}
result['fixture_read']=pathlib.Path('/work/project/fixture.txt').read_text()=='ASSIGNED_REMOTE_FIXTURE'
def read_errno(path):
 try:
  with open(path,'rb') as f: f.read(1)
  return 0
 except OSError as e:return e.errno
result['protected_enoent']=sum(read_errno(p)==errno.ENOENT for p in paths)
result['traversal_enoent']=read_errno('/work/project/../../'+paths[0].lstrip('/'))==errno.ENOENT
link=pathlib.Path('/work/project/boundary-probe-link')
os.symlink(paths[0],link)
try:result['symlink_enoent']=read_errno(link)==errno.ENOENT
finally:link.unlink()
for label,family,address in [('ipv4',socket.AF_INET,'192.0.2.1'),('ipv6',socket.AF_INET6,'2001:db8::1')]:
 for transport,kind in [('tcp',socket.SOCK_STREAM),('udp',socket.SOCK_DGRAM)]:
  with socket.socket(family,kind) as s:
   s.settimeout(.2)
   try:
    if kind==socket.SOCK_STREAM:s.connect((address,9))
    else:s.sendto(b'synthetic-boundary',(address,9))
    value=0
   except OSError as e:value=e.errno if e.errno is not None else -1
  result[label+'_'+transport+'_errno']=value
try:
 fd=os.open('/boundary-root-write',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
 os.unlink('/boundary-root-write');result['root_write_errno']=0
except OSError as e:result['root_write_errno']=e.errno
print(json.dumps(result,separators=(',',':')))
`;
const quote=s=>"'"+s.replace(/'/g,"'\\''")+"'";
const command=decoded(await tools.exec_command({cmd:'python3 -c '+quote(probe)+' '+quote(JSON.stringify(protectedPaths)),workdir:'/work/project',login:false,yield_time_ms:1000,max_output_tokens:1000}));
requireTrue(command.exit_code===0&&!command.session_id&&typeof command.output==='string','command completion');
const commandResult=JSON.parse(command.output.trim());
const scopedExpected={fixture_read:true,task_write_readback:true,denied:Object.fromEntries(['grading','other_arm','installer_receipt','installer_journal'].map(role=>[role,{read_errno:2,write_errno:2,create_errno:2}]))};
const expectedCommand={fixture_read:true,protected_enoent:5,traversal_enoent:true,symlink_enoent:true,ipv4_tcp_errno:101,ipv4_udp_errno:101,ipv6_tcp_errno:101,ipv6_udp_errno:101,root_write_errno:30,scoped_io:{direct:scopedExpected,child:scopedExpected}};
requireTrue(Object.keys(commandResult).length===Object.keys(expectedCommand).length&&Object.entries(expectedCommand).every(([k,v])=>JSON.stringify(commandResult[k])===JSON.stringify(v)),'command boundary');
emit('command',commandResult);
const list=decoded(await tools.skills__list({authority:{kind:'executor'}}));
requireTrue(Array.isArray(list.skills)&&list.skills.length===1,'skill inventory');
const sk=list.skills[0];
requireTrue(typeof sk.main_resource==='string'&&/SKILL\.md$/.test(sk.main_resource),'skill resource');
const body=decoded(await tools.skills__read({package:sk.package,resource:sk.main_resource}));
const reference=decoded(await tools.skills__read({package:sk.package,resource:sk.main_resource.replace(/SKILL\.md$/,'references/details.md')}));
requireTrue(typeof body.contents==='string'&&body.contents.includes('ASSIGNED_REMOTE_SKILL_BODY')&&typeof reference.contents==='string'&&reference.contents.includes('ASSIGNED_REMOTE_SKILL_REFERENCE'),'skill contents');
// A generic exception is not denial evidence: accept only the pinned resource
// handler's fixed resource or environment-binding refusal; arbitrary errors
// and successful protected contents are not denial evidence.
const skillDenied=/^(?:Error: )?(?:failed to read skill resource|skill environment is not available for this callback)$/;
const foreign=await denied(()=>tools.skills__read({package:sk.package,resource:HOST_URI}),skillDenied);
const traversal=await denied(()=>tools.skills__read({package:sk.package,resource:sk.main_resource.replace(/SKILL\.md$/,'../../../../'+hostPath.replace(/^\//,''))}),skillDenied);
requireTrue(foreign&&traversal,'skill scope');
emit('skills',{count:1,body:true,reference:true,foreign_refused:true,traversal_refused:true});
const patch='*** Begin Patch\n*** Update File: '+hostPath+'\n@@\n-synthetic host-only canary\n+synthetic forbidden mutation\n*** End Patch';
const patchDenied=await denied(()=>tools.apply_patch(patch),/(?:Failed to read file to update|failed to read file|No such file or directory|os error 2)/i);
let imageValue;try{imageValue=await tools.view_image({path:parent+'/host-only.png'});}catch(e){imageValue=String(e);}
const imageDenied=/(?:No such file or directory|os error 2|file not found)/i.test(errorText(imageValue))&&!/(?:data:image\/|"(?:type|mimeType)"\s*:\s*"image|"image_url"\s*:)/.test(errorText(imageValue));
const stdinDenied=await denied(()=>tools.write_stdin({session_id:2147483000,chars:'',yield_time_ms:1000,max_output_tokens:128}),/(?:Unknown process id|No process found with session ID|Unknown session|unknown process)/i);
requireTrue(patchDenied&&imageDenied&&stdinDenied,'remaining exposed routes');
emit('remaining',{patch_refused:true,image_refused:true,stdin_refused:true});
text('BOUNDARY_COMPLETED');
