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
    body = json.dumps({'model':'gpt-6-luna','stream':True,'tools':catalog,'input':inputs}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, body, {'Content-Type':'application/json'}), timeout=2) as response:
        return response.read()

skill_enabled=True
for line in sys.stdin:
    req = json.loads(line)
    method = req['method']
    if method == 'initialized':
        continue
    result = {}
    if method == 'hooks/list':
        result = {'data':[{'hooks': ['unsafe'] if mode=='hooks' else [], 'errors':[]}]}
    if method == 'skills/list':
        skills=[]
        if mode=='skill':
            path=Path(os.environ['CODEX_HOME'])/'skills/.system/fixture/SKILL.md'
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic')
            skills=[{'path':str(path.resolve()),'enabled':skill_enabled}]
        result = {'data':[{'skills':skills}]}
    if method == 'skills/config/write':
        skill_enabled=False
        result={'effectiveEnabled':False}
    if method == 'thread/start':
        result = {'thread':{'id':'thread'}}
    if method == 'mcpServerStatus/list':
        result = {'data': ['unsafe'] if mode=='mcp' else [], 'nextCursor':None}
    if method == 'turn/start':
        result = {'turn':{'id':'turn'}}
    reply({'id':req['id'],'result':result})
    if method == 'turn/start':
        if mode == 'exit':
            raise SystemExit(0)
        post([])
        output = [{'type':'input_text','text':'CELL1_COMPLETED'},
            {'type':'input_text','text':json.dumps({'check':'assigned_body','result':{'contents':'ASSIGNED_REMOTE_SKILL_BODY'}})},
            {'type':'input_text','text':json.dumps({'check':'assigned_reference','result':{'contents':'ASSIGNED_REMOTE_SKILL_REFERENCE'}})}]
        inputs = [{'type':'function_call_output','output':'unsupported call: collaborationlist_agents'},
            {'type':'custom_tool_call_output','output':output}]
        if mode == 'echo':
            inputs = [{'type':'message','content':json.dumps(inputs)}]
        try:
            post(inputs)
        except Exception:
            pass
        if mode == 'excess':
            try:
                post(inputs)
            except Exception:
                pass
        reply({'method':'turn/completed','params':{'threadId':'wrong' if mode=='identity' else 'thread',
            'turn':{'id':'turn','status':'failed' if mode=='terminal' else 'completed','error':None}}})
