"""Local fake app-server: protocol testing only, never real native qualification."""
import json
import os
from pathlib import Path
import sys
import time
import tomllib
import urllib.request

mode = sys.argv[1] if len(sys.argv) > 1 else 'success'
if mode == 'silent':
    time.sleep(10)
if mode == 'malformed':
    print('{malformed', flush=True)
    time.sleep(10)
if mode == 'flood':
    sys.stdout.write('x'*200000)
    sys.stdout.flush()
    time.sleep(10)
if mode == 'truncated':
    sys.stdout.write('{"unfinished":')
    sys.stdout.flush()
    raise SystemExit(0)
config = tomllib.loads((Path(os.environ['CODEX_HOME'])/'config.toml').read_text())
assert config['model_providers']['fixture']['requires_openai_auth'] is False
assert not any(k in os.environ for k in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'XAI_API_KEY'))
assert not (Path(os.environ['CODEX_HOME'])/'auth.json').exists()
assert tomllib.loads((Path(os.environ['CODEX_HOME'])/'environments.toml').read_text())['include_local'] is False
url = config['model_providers']['fixture']['base_url']+'/responses'
nested = ['apply_patch','exec_command','view_image','write_stdin','list_mcp_resources','list_mcp_resource_templates','read_mcp_resource','clock__curr_time','skills__list','skills__read']
catalog = [{'name':'exec','type':'custom','description':'\n'.join('### `'+x+'`' for x in nested)}, {'name':'wait','type':'function'}]

def reply(message):
    print(json.dumps(message), flush=True)

def post(inputs):
    body = json.dumps({'model':'unexpected' if mode=='model' else 'gpt-6-luna','stream':True,'tools':catalog,'input':inputs}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, body, {'Content-Type':'application/json'}), timeout=2) as response:
        return response.read()

skill_enabled=True
thread_id='t'*5000 if mode=='long-identities' else 'thread'
turn_id='u'*5000 if mode=='long-identities' else 'turn'
for line in sys.stdin:
    req = json.loads(line)
    method = req['method']
    if method == 'initialized':
        continue
    if mode=='server-request':
        reply({'id':'server','method':'unexpected','params':{}})
        time.sleep(10)
    if mode=='rpc-error':
        reply({'id':req['id'],'error':{'code':-1,'message':'synthetic'}})
        continue
    result = {}
    if method == 'hooks/list':
        result = {'data':[{'hooks': ['unsafe'] if mode=='hooks' else [], 'errors':[]}]}
    if method == 'skills/list':
        skills=[]
        if mode in ('skill','skill-enabled','skill-outside'):
            base=Path(os.environ['HOME']) if mode=='skill-outside' else Path(os.environ['CODEX_HOME'])
            path=base/'skills/.system/fixture/SKILL.md'
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic')
            skills=[{'path':str(path.resolve()),'enabled':skill_enabled}]
        result = {'data':[{'skills':skills}]}
    if method == 'skills/config/write':
        skill_enabled=mode=='skill-enabled'
        result={'effectiveEnabled':False}
    if method == 'thread/start':
        result = {'thread':{'id':thread_id}}
    if method == 'mcpServerStatus/list':
        result = {'data': ['unsafe'] if mode=='mcp' else [], 'nextCursor':None}
    if method == 'turn/start':
        result = {'turn':{'id':turn_id}}
    reply({'id':req['id'],'result':result})
    if method == 'turn/start':
        if mode == 'exit':
            raise SystemExit(0)
        try:
            post([{'type':'message','content':'HOST_STARTUP_INSTRUCTION_CANARY'}] if mode=='host-marker' else [])
        except Exception:
            pass
        output = [{'type':'input_text','text':'CELL1_COMPLETED'},
            {'type':'input_text','text':json.dumps({'check':'assigned_body','result':{'contents':'ASSIGNED_REMOTE_SKILL_BODY'}})},
            {'type':'input_text','text':json.dumps({'check':'assigned_reference','result':{'contents':'ASSIGNED_REMOTE_SKILL_REFERENCE'}})}]
        inputs = [{'type':'function_call_output','output':'unsupported call: collaborationlist_agents'},
            {'type':'custom_tool_call_output','output':output}]
        if mode == 'echo':
            inputs = [{'type':'message','content':json.dumps(inputs)}]
        if mode == 'missing-assigned':
            output[1]['text']=json.dumps({'check':'assigned_body','result':{'contents':'WRONG'}})
        try:
            post(inputs)
        except Exception:
            pass
        if mode == 'excess':
            try:
                post(inputs)
            except Exception:
                pass
        reply({'method':'turn/completed','params':{'threadId':'wrong' if mode=='identity' else thread_id,
            'turn':{'id':turn_id,'status':'failed' if mode in ('terminal','large-error') else 'completed','error':{'message':'x'*20000} if mode=='large-error' else None}}})
