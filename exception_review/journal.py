"""Atomic append-only judge operations, fixed identities, finite budgets, no resend."""
import json
import os
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from .artifacts import freeze
from .policy import SCHEMAS,RUBRICS
from .providers import HTTPTransport,ENDPOINTS,payload,parse_response,redact,usage_cost

class Clock:
    def monotonic(self): return time.monotonic()
    def utc(self): return datetime.now(timezone.utc).isoformat()

class Journal:
    def __init__(self,review,live=False,transport=None,max_calls=None,wall_seconds=None,clock=None):
        self.review=review; self.policy=review.policy; self.root=review.root/'judge-operations'; self.clock=clock or Clock()
        self.transport=transport; self.live=live; self.wall_seconds=wall_seconds
        self.limit=self.policy['config']['limits']; self.max_calls=max_calls if max_calls is not None else self.limit['max_calls']
        if type(self.max_calls) is not int or self.max_calls<0 or self.max_calls>self.limit['max_calls']: raise ValueError('Invalid invocation request limit')
        if wall_seconds is not None and (not isinstance(wall_seconds,(int,float)) or not 0<wall_seconds<float('inf')): raise ValueError('Finite positive wall limit required')
        if live:
            if not self.policy['config']['live_enabled']: raise ValueError('Live configuration is disabled')
            for j in self.policy['config']['judges'].values():
                if not os.environ.get(ENDPOINTS[j['provider']][2]): raise ValueError('Missing environment credential for '+j['provider'])
            self.transport=transport or HTTPTransport()
        elif isinstance(transport,HTTPTransport): raise ValueError('HTTP transport requires --live')
        if self.transport is not None and getattr(self.transport,'kind',None) not in ('LIVE','MOCK'): raise ValueError('Transport must declare measurement kind')
        if not live and self.transport is not None and self.transport.kind!='MOCK': raise ValueError('Offline requires mocked transport')
        if self.transport is not None:
            freeze(review.root/'judge-execution.json',dict(policy_hash=self.policy['policy_hash'],measurement=self.transport.kind))
        self.started=self.clock.monotonic(); self.invocation=uuid.uuid4().hex
        self.metrics=dict(id=self.invocation,started_utc=self.clock.utc(),attempted=0,returned=0,cached=0,failures=0,provider_seconds=0.,local_seconds=0.,waiting_seconds=0.,stop_reason=None,measurement=self.transport.kind if self.transport is not None else 'OFFLINE')
    def entries(self):
        result=[]
        for p in sorted(self.root.glob('*/planned.json')):
            base=sealed_read(p); parent=p.parent
            for state in ('returned','failed','started'):
                if (parent/(state+'.json')).exists(): base=sealed_read(parent/(state+'.json')); break
            result.append(base)
        return result
    def call(self,tid,judge_name,role,version,view):
        prep=self.clock.monotonic(); j=self.policy['config']['judges'][judge_name]
        kind='detect' if role in ('initial','adjudicate') else 'draft' if role in ('draft','revise') else 'verify'
        request=payload(j,RUBRICS[kind],SCHEMAS[kind],view)
        identity=dict(**self.review.source.case_binding(tid),policy_hash=self.policy['policy_hash'],prompt_hash=digest(RUBRICS[kind]),schema_hash=digest(SCHEMAS[kind]),judge=judge_name,judge_config=j,role=role,edit_version=version,input_hash=digest(view),request=request)
        if redact(request)!=request: raise ValueError('Credential appeared in request data; refusing to persist or send')
        key=digest(identity); directory=self.root/key
        # Slot has one immutable identity even if a caller accidentally changes its view.
        slot=self.root/'slots'/(digest([tid,judge_name,role,version])+'.json')
        freeze(slot,dict(key=key,identity=identity))
        for state in ('returned','failed'):
            path=directory/(state+'.json')
            if path.exists():
                record=sealed_read(path)
                if record['identity']!=identity: raise ValueError('Operation identity changed')
                self.metrics['cached']+=1; self.metrics['local_seconds']+=self.clock.monotonic()-prep
                return record
        if (directory/'started.json').exists():
            record=sealed_read(directory/'started.json')
            record.update(state='failed',finished_utc=self.clock.utc(),elapsed_seconds=None,provider_seconds=None,error=dict(type='AmbiguousInterruptedOperation',message='Terminal unavailable; no resend'),parsed=dict(valid=False,reason='ambiguous_inflight',value=None))
            record=freeze(directory/'failed.json',record); self.metrics['cached']+=1; self.metrics['failures']+=1
            return record
        planned=dict(identity=identity,key=key,state='planned',request=redact(request))
        freeze(directory/'planned.json',planned)
        existing=[e for e in self.entries() if e['state']!='planned']
        used=sum(e.get('accounting',{}).get('estimated_usd') if e.get('accounting',{}).get('estimated_usd') is not None else e.get('reservation_usd',0) for e in existing)
        # Conservative byte-based planning allowance, not a provider billing guarantee.
        input_estimate=len(json.dumps(request,ensure_ascii=False).encode())+2048
        reservation=(input_estimate*j['rates']['input_per_million']+j['max_output_tokens']*j['rates']['output_per_million'])/1e6
        case_calls=sum(e['identity']['task_id']==tid for e in existing)
        stop='OFFLINE' if self.transport is None else 'CASE_CALL_CEILING' if case_calls>=7 else 'REQUEST_BUDGET' if self.metrics['attempted']>=self.max_calls or len(existing)>=self.limit['max_calls'] else 'ESTIMATED_SPEND_BUDGET' if used+reservation>self.limit['max_estimated_usd'] else 'WALL_SCHEDULING_LIMIT' if self.wall_seconds is not None and self.clock.monotonic()-self.started>=self.wall_seconds else None
        self.metrics['local_seconds']+=self.clock.monotonic()-prep
        if stop: self.metrics['stop_reason']=stop; return None
        start=self.clock.monotonic(); started=dict(planned,state='started',started_utc=self.clock.utc(),measurement=self.metrics['measurement'],estimated_input_tokens=input_estimate,reservation_usd=reservation,rates=j['rates'])
        freeze(directory/'started.json',started); self.metrics['attempted']+=1
        start=self.clock.monotonic()
        try:
            response=self.transport(j['provider'],request,self.limit['timeout_seconds'])
        except BaseException as exc:
            elapsed=self.clock.monotonic()-start
            failed=dict(started,state='failed',finished_utc=self.clock.utc(),elapsed_seconds=elapsed,provider_seconds=elapsed,error=redact(dict(type=type(exc).__name__,message=str(exc))),parsed=dict(valid=False,reason='terminal_unavailable_no_retry',value=None))
            record=freeze(directory/'failed.json',failed); self.metrics['failures']+=1; self.metrics['provider_seconds']+=elapsed
            if not isinstance(exc,Exception): raise
            return record
        elapsed=self.clock.monotonic()-start; local=self.clock.monotonic()
        parsed=parse_response(j['provider'],response)
        if parsed['valid'] and parsed['model']!=j['model']:
            parsed.update(valid=False,reason='returned_model_identity_mismatch')
        accounting=usage_cost(j['provider'],parsed.get('usage'),j['rates'])
        record=dict(started,state='returned',finished_utc=self.clock.utc(),elapsed_seconds=elapsed,provider_seconds=elapsed,raw_response=redact(response),parsed=redact(parsed),accounting=accounting)
        record=freeze(directory/'returned.json',record)
        self.metrics['returned']+=1; self.metrics['provider_seconds']+=elapsed; self.metrics['local_seconds']+=self.clock.monotonic()-local
        return record
    def finish(self,stage,scope):
        total=self.clock.monotonic()-self.started
        self.metrics.update(stage=stage,scope=scope,finished_utc=self.clock.utc(),stage_seconds=total,stage_local_seconds=max(0.,total-self.metrics['provider_seconds']-self.metrics['waiting_seconds']),local_seconds_note='local_seconds covers request preparation/parsing; stage_local_seconds also includes alignment, validation, journaling and cache access')
        return freeze(self.review.root/'invocations'/(self.invocation+'.json'),self.metrics)
