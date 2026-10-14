"""Single HTTP attempts. No SDK, automatic retries, redirects, tools, or history."""
import http.client
import json
import os
from .policy import UNTRUSTED

ENDPOINTS={'openai':('api.openai.com','/v1/responses','OPENAI_API_KEY'), 'anthropic':('api.anthropic.com','/v1/messages','ANTHROPIC_API_KEY')}


def loads(text):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('duplicate JSON key')
            result[k]=v
        return result
    def invalid(x): raise ValueError('nonfinite JSON number')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid)


def payload(judge,rubric,schema,view):
    source='BEGIN_UNTRUSTED_SOURCE_JSON\n'+json.dumps(view,ensure_ascii=False,allow_nan=False)+'\nEND_UNTRUSTED_SOURCE_JSON'
    system=UNTRUSTED+'\n'+rubric
    if judge['provider']=='openai':
        return dict(model=judge['model'],store=False,stream=False,instructions=system,input=[dict(role='user',content=source)],max_output_tokens=judge['max_output_tokens'],text={'format':dict(type='json_schema',name='study2_review',strict=True,schema=schema)},**judge['settings'])
    settings=dict(judge['settings']); effort=settings.pop('effort',None)
    output_config={'format':dict(type='json_schema',schema=schema)}
    if effort is not None: output_config['effort']=effort
    return dict(model=judge['model'],system=system,messages=[dict(role='user',content=source)],max_tokens=judge['max_output_tokens'],stream=False,output_config=output_config,**settings)


def redact(value):
    secrets=[os.environ.get(v) for _,_,v in ENDPOINTS.values() if os.environ.get(v)]
    if isinstance(value,str):
        for secret in secrets: value=value.replace(secret,'[REDACTED]')
        return value
    if isinstance(value,dict): return {k:redact(v) for k,v in value.items() if k.lower() not in ('authorization','x-api-key','api_key')}
    if isinstance(value,list): return [redact(v) for v in value]
    return value

class HTTPTransport:
    kind='LIVE'
    def __call__(self,provider,request,timeout):
        host,path,env=ENDPOINTS[provider]; key=os.environ[env]
        headers={'Content-Type':'application/json'}
        if provider=='openai': headers['Authorization']='Bearer '+key
        else: headers.update({'x-api-key':key,'anthropic-version':'2023-06-01'})
        conn=http.client.HTTPSConnection(host,timeout=timeout)
        try:
            conn.request('POST',path,body=json.dumps(request,ensure_ascii=False,allow_nan=False).encode(),headers=headers)
            response=conn.getresponse(); body=response.read().decode('utf-8')
            return dict(status=response.status,body=body,request_id=response.getheader('x-request-id') or response.getheader('request-id'))
        finally: conn.close()


def parse_response(provider,response):
    out=dict(valid=False,reason=None,value=None,usage=None,model=None,response_id=None,request_id=response.get('request_id'))
    try:
        body=loads(response['body']); out.update(usage=body.get('usage'),model=body.get('model'),response_id=body.get('id'))
        if response['status']!=200:
            out['reason']='HTTP_'+str(response['status']); return out
        if provider=='openai':
            if body.get('status')!='completed': out['reason']='incomplete_or_failed_response'; return out
            content=[c for item in body.get('output',[]) if item.get('type')=='message' for c in item.get('content',[])]
            if any(c.get('type')=='refusal' for c in content): out['reason']='refusal'; return out
            texts=[c['text'] for c in content if c.get('type')=='output_text']
        else:
            if body.get('stop_reason')!='end_turn': out['reason']='stop_reason_'+str(body.get('stop_reason')); return out
            texts=[c['text'] for c in body.get('content',[]) if c.get('type')=='text']
        if len(texts)!=1 or not texts[0].strip(): out['reason']='empty_or_multiple_output_blocks'; return out
        out.update(value=loads(texts[0]),valid=True)
    except (ValueError,TypeError,KeyError,AttributeError): out['reason']='malformed_response'
    return out


def usage_cost(provider,usage,rates):
    if not isinstance(usage,dict): return dict(input_tokens=None,output_tokens=None,reasoning_tokens=None,estimated_usd=None)
    inp=usage.get('input_tokens'); output=usage.get('output_tokens')
    if type(inp) is not int or type(output) is not int: return dict(input_tokens=inp,output_tokens=output,reasoning_tokens=None,estimated_usd=None)
    if provider=='openai':
        cached=usage.get('input_tokens_details',{}).get('cached_tokens',0)
        reasoning=usage.get('output_tokens_details',{}).get('reasoning_tokens',0)
        cost=(inp-cached)*rates['input_per_million']+cached*rates['cached_input_per_million']+output*rates['output_per_million']
        writes=0
    else:
        cached=usage.get('cache_read_input_tokens',0); writes=usage.get('cache_creation_input_tokens',0)
        reasoning=usage.get('output_tokens_details',{}).get('thinking_tokens')
        cost=inp*rates['input_per_million']+cached*rates['cached_input_per_million']+writes*rates['cache_write_per_million']+output*rates['output_per_million']
    return dict(input_tokens=inp,output_tokens=output,reasoning_tokens=reasoning,cached_input_tokens=cached,cache_write_input_tokens=writes,estimated_usd=cost/1e6,reasoning_accounting='Output total includes billed reasoning; do not add reasoning twice')
