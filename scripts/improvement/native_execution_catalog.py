"""Offline parser for official Responses and Responses-Lite native inventories."""
import re

def catalog(request):
    roots=[]
    def walk(items, namespace=None):
        for item in items:
            if not isinstance(item,dict):raise ValueError('malformed tool')
            if item.get('type')=='namespace':
                walk(item.get('tools',[]), item['name'])
            else:
                roots.append({'namespace':namespace or 'functions','name':item['name'],'type':item['type'],'description':item.get('description','')})
    walk(request.get('tools',[]))
    for item in request.get('input',[]):
        if isinstance(item,dict) and item.get('type')=='additional_tools':walk(item.get('tools',[]))
    result={}
    for item in roots:
        identity=(item['namespace'],item['name'])
        if identity in result and result[identity]!=item:raise ValueError('conflicting tool definitions')
        result[identity]=item
    nested=[]
    for item in result.values():
        if (item['namespace'],item['name'])==('functions','exec'):
            nested=re.findall(r'^### `([^`]+)`',item['description'],re.MULTILINE)
    return {'root':list(result.values()),'nested':nested}

ROOT_ALLOWED={('functions','exec'),('functions','wait'),('functions','request_user_input'),('functions','request_user_input_async'),('clock','sleep')}
NESTED_ALLOWED={'apply_patch','exec_command','view_image','write_stdin','list_mcp_resource_templates','list_mcp_resources','read_mcp_resource','clock__curr_time','skills__list','skills__read'}
def gate(c):
    root={(v['namespace'],v['name']) for v in c['root']}
    if not {('functions','exec'),('functions','wait')}<=root:raise ValueError('code-mode entrypoint missing')
    if root-ROOT_ALLOWED:raise ValueError('unaudited root routes: '+repr(sorted(root-ROOT_ALLOWED)))
    if set(c['nested'])-NESTED_ALLOWED:raise ValueError('unaudited nested routes')
    if not {'exec_command','apply_patch','view_image','write_stdin'}<=set(c['nested']):raise ValueError('required nested route missing')
    return True
