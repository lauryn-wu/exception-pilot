"""Compose the existing immutable Session, atomic writer, lock and debris reader."""
import time
import uuid
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5.journal import Session, OperationUnavailable
from exception_study2_native.recovery import scan, state, quarantine
from exception_study2_source_report.integrity import revision
from . import VERSION
from .planning import Context
from .adapter import Backend


def opid(r):return 'v5/'+VERSION+'/'+r['request_hash']+'/attempt-1'

def binding(c,mode):return dict(protocol=VERSION,plan_hash=c.plan['artifact_hash'],code_contract=c.plan['code_contract'],measurement_mode=mode)


def journal(c):
    path=c.out/'execution.json';ex=sealed_read(path) if path.exists() else None
    mode=ex['measurement_mode'] if ex else 'UNEXECUTED'
    if mode not in ('UNEXECUTED','MOCK','LIVE_LOCAL'):raise ValueError('Unknown execution mode')
    identity=binding(c,mode)
    if ex and (any(ex.get(k)!=v for k,v in identity.items()) or ex['backend_hash']!=digest(ex['backend']) or ex['backend']['tokenizer']!=c.tok.identity):
        raise ValueError('Backend/plan identity changed')
    known={digest(opid(r)):dict(id=opid(r),identity=dict(identity,id=opid(r),request=r['request'],request_hash=r['request_hash'],stage='current_native_generation')) for r in c.requests}
    saved=scan(c,known,identity)
    if saved and not ex:raise ValueError('Missing execution binding')
    current={}
    for r in c.requests:
        op=saved.get(opid(r));current[r['cell']['id']]=op
        if op:
            if any(op.get(k)!=v for k,v in identity.items()) or op['request']!=r['request']:raise ValueError('Cached scientific request mismatch')
            dpath=c.out/'dispatches'/(digest(opid(r))+'.json')
            if op['status']=='returned' and not dpath.exists():raise ValueError('Missing dispatch provenance')
            if dpath.exists():
                d=sealed_read(dpath)
                started=sealed_read(c.out/'invocations'/d['invocation']/'started.json')
                if d['request_hash']!=r['request_hash'] or d['backend_hash']!=ex['backend_hash'] or started['plan_hash']!=c.plan['artifact_hash']:
                    raise ValueError('Dispatch binding differs')
    return current,mode,ex


class ScreenSession(Session):
    def __init__(self,c,mode):self.out=c.out;self.identity=binding(c,mode);self.telemetry=None


def smoke_evidence(c,wanted):
    from .analysis import report
    gate=c.plan['smoke'];smoke=Context(gate['path'])
    current,mode,ex=journal(smoke)
    r=report(smoke,current,{})
    if smoke.plan['artifact_hash']!=gate['plan_hash'] or mode!=wanted or not r['technical_passed']:
        raise ValueError('Technical smoke has not passed with this real/mock model identity; scientific run blocked')
    return dict(plan_hash=smoke.plan['artifact_hash'],execution_hash=ex['artifact_hash'],backend_hash=ex['backend_hash'],
                operations={k:v['artifact_hash'] for k,v in current.items()})


def run(output,live=False,max_new=8,_factory=None):
    from .analysis import report, save_report
    if type(max_new) is not int or max_new<1:raise ValueError('Positive --max-new required')
    if live and _factory:raise ValueError('Cannot mix live and mock')
    with run_lock(output):
        c=Context(output);current,mode,ex=journal(c)
        stats=dict(new_generations=0,model_loads=0,model_load_attempts=0,reused_returns=sum(state(x)=='returned' for x in current.values()))
        if not live and _factory is None:return report(c,current,stats)
        wanted='MOCK' if _factory else 'LIVE_LOCAL'
        if mode not in ('UNEXECUTED',wanted):raise ValueError('Mock/live cache mismatch')
        c.extend_smoke();current,mode,ex=journal(c)
        pending=[r for r in c.requests if state(current[r['cell']['id']])=='never_started']
        if not pending:return save_report(c,current,stats)
        evidence=smoke_evidence(c,wanted) if c.plan['kind']=='screen' else None
        if evidence:freeze(c.out/'smoke-evidence.json',evidence)
        uid=uuid.uuid4().hex;folder=c.out/'invocations'/uid
        freeze(folder/'started.json',dict(binding(c,wanted),revision=revision(),max_new=max_new))
        start=time.perf_counter();status='FAILED'
        try:
            stats['model_load_attempts']=1
            backend=(_factory or Backend)(c.locations['model'],c.tok);stats['model_loads']=1
            if bool(backend.simulated)!=(wanted=='MOCK'):raise ValueError('Mock/live backend mismatch')
            if evidence and digest(backend.identity)!=evidence['backend_hash']:raise ValueError('Backend differs from passing smoke')
            freeze(c.out/'execution.json',dict(binding(c,wanted),backend=backend.identity,backend_hash=digest(backend.identity)))
            session=ScreenSession(c,wanted)
            while stats['new_generations']<max_new:
                c.extend_smoke();current,_,_=journal(c)
                pending=[r for r in c.requests if state(current[r['cell']['id']])=='never_started']
                if not pending:break
                r=pending[0];oid=opid(r)
                def dispatch():
                    freeze(c.out/'dispatches'/(digest(oid)+'.json'),dict(invocation=uid,request_hash=r['request_hash'],backend_hash=digest(backend.identity)))
                    stats['new_generations']+=1
                    print('Dispatching '+r['cell']['id'],flush=True)
                    raw=backend.generate(r['request'])
                    print('Returned '+r['cell']['id'],flush=True)
                    return raw
                try:session.operation(oid,r['request'],dispatch,'current_native_generation')
                except OperationUnavailable as exc:
                    cause=exc.__cause__ or exc
                    freeze(folder/'backend-error.json',dict(operation_id=oid,error_type=type(cause).__name__,message=str(cause)))
                    stats['stopped_after_backend_exception']=r['cell']['id'];break
            status='STOPPED_AFTER_FAILURE' if 'stopped_after_backend_exception' in stats else 'BOUNDED_COMPLETE'
        finally:
            stats['elapsed_seconds']=time.perf_counter()-start
            freeze(folder/'finished.json',dict(binding(c,wanted),status=status,**stats))
        current,_,_=journal(c)
        return save_report(c,current,stats)


def inspect(output):
    from .analysis import report
    c=Context(output);current,_,_=journal(c)
    return report(c,current,dict(new_generations=0,model_loads=0))


def analyze(output):
    from .analysis import save_report
    with run_lock(output):
        c=Context(output);current,_,_=journal(c)
        return save_report(c,current,dict(new_generations=0,model_loads=0))


def recover(output,reason):
    with run_lock(output):
        c=Context(output);_,mode,_=journal(c)
        result=quarantine(c,binding(c,mode),reason);journal(c)
        return dict(result,note='Evidence quarantined only. Ambiguous/failed calls remain held; no retry or replacement authorized.')
