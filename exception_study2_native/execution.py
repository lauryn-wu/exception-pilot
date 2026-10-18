"""Immutable attempts using the existing journal primitive; explicit retries only."""
import time
import uuid
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5.journal import Session, OperationUnavailable
from .recovery import scan, state, summary as recovery_summary, needs_recovery, quarantine
from exception_study2_source_report.integrity import revision
from . import VERSION, STOP, BUDGET_POLICY
from .planning import Context
from .interface import NativeBackend

NAMESPACE='v5/native-thinking-draft-v2/'+BUDGET_POLICY+'/'


def opid(request,n): return NAMESPACE+request['request_hash']+'/attempt-'+str(n)


def binding(c,mode):
    return dict(protocol=VERSION,plan_hash=c.plan['artifact_hash'],code_contract=c.plan['code_contract'],measurement_mode=mode)


def journal(c):
    path=c.out/'execution.json';ex=sealed_read(path) if path.exists() else None
    mode=ex['measurement_mode'] if ex else 'UNEXECUTED'
    if mode not in ('UNEXECUTED','MOCK','LIVE_LOCAL'): raise ValueError('Missing/invalid execution binding')
    if ex and any(ex.get(k)!=v for k,v in binding(c,mode).items()): raise ValueError('Execution identity mismatch')
    if ex and (ex['backend_hash']!=digest(ex['backend']) or ex['backend']['tokenizer']!=c.plan['tokenizer']):
        raise ValueError('Frozen backend/tokenizer identity differs')
    current={};known=set();authorizations={}
    for path in (c.out/'retry-authorizations').glob('*.json'):
        auth=sealed_read(path)
        key=(auth['cell_id'],auth['attempt'])
        if key in authorizations or auth['plan_hash']!=c.plan['artifact_hash'] or auth['cell_id'] not in c.by_cell:
            raise ValueError('Invalid retry authorization')
        if type(auth['attempt']) is not int or auth['attempt']<2:raise ValueError('Invalid retry attempt number')
        authorizations[key]=auth
    registry={}
    for cell,r in c.by_cell.items():
        attempts=[n for name,n in authorizations if name==cell]
        if attempts and max(attempts)>len(attempts)+1:raise ValueError('Nonconsecutive retry authorization')
        for n in range(1,len(attempts)+2):
            oid=opid(r,n)
            registry[digest(oid)]=dict(id=oid,identity=dict(binding(c,mode),id=oid,request=r['request'],
                request_hash=r['request_hash'],stage='native_generation'))
    saved=scan(c,registry,binding(c,mode))
    if saved and ex is None:raise ValueError('Missing execution binding')
    used=set()
    for cell,r in c.by_cell.items():
        n=1;last=None
        while True:
            oid=opid(r,n);known.add(oid);op=saved.get(oid)
            if op:
                if any(op.get(k)!=v for k,v in binding(c,mode).items()) or op['request']!=r['request'] or op['stage']!='native_generation':
                    raise ValueError('Exact scientific request differs from cached operation')
                path=c.out/'dispatches'/(digest(oid)+'.json')
                if op['status']=='returned' and not path.exists(): raise ValueError('Returned attempt lacks dispatch provenance')
                if path.exists():
                    d=sealed_read(path)
                    if d['operation_id']!=oid or d['request_hash']!=r['request_hash'] or d['backend_hash']!=ex['backend_hash']:
                        raise ValueError('Dispatch scientific identity differs')
                    started=sealed_read(c.out/'invocations'/d['invocation']/'started.json')
                    if started['plan_hash']!=c.plan['artifact_hash'] or cell not in started['cell_ids']:
                        raise ValueError('Dispatch invocation binding differs')
            if (cell,n+1) not in authorizations:
                current[cell]=dict(attempt=n,operation=op);break
            auth=authorizations[(cell,n+1)];used.add((cell,n+1))
            if not op or state(op) not in ('failed','ambiguous') or auth['prior_operation_hash']!=op['artifact_hash'] or not auth['reason'].strip():
                raise ValueError('Retry must reference an immutable failed/ambiguous attempt, never a returned answer')
            last=op;n+=1
    if set(authorizations)!=used or set(saved)-known: raise ValueError('Orphan/cross-protocol attempt or retry authorization')
    return saved,current,mode,ex


class NativeSession(Session):
    def __init__(self,c,mode):
        self.out=c.out;self.identity=binding(c,mode);self.telemetry=None


def run(output,scope,live_qwen=False,max_new=16,_factory=None):
    from .analysis import report
    if scope not in ('pilot','main') or type(max_new) is not int or max_new<1: raise ValueError('Explicit cohort and positive max-new required')
    with run_lock(output):
        c=Context(output)
        if scope!=c.plan['cohort']: raise ValueError('Scope differs from frozen cohort: main requires a separate freeze-main budget review')
        saved,current,mode,ex=journal(c)
        selected=[r for r in c.plan['requests'] if r['cell']['cohort']==scope]
        stats=dict(scope=scope,model_loads=0,model_load_attempts=0,new_calls=0,reused=sum(state(current[r['cell']['id']]['operation'])=='returned' for r in selected))
        work=[r for r in selected if state(current[r['cell']['id']]['operation'])=='never_started'][:max_new]
        if not live_qwen and _factory is None: return report(c,current,stats)
        if live_qwen and _factory is not None: raise ValueError('Cannot combine fake and live mode')
        wanted='MOCK' if _factory else 'LIVE_LOCAL'
        if mode not in ('UNEXECUTED',wanted): raise ValueError('MOCK/LIVE cache separation')
        if scope=='main' and c.plan['budget_review']['pilot']['measurement_mode']!=wanted:
            raise ValueError('MOCK/LIVE pilot evidence separation; synthetic results cannot authorize a live main run')
        if not work: return report(c,current,stats)
        invocation=uuid.uuid4().hex;folder=c.out/'invocations'/invocation
        freeze(folder/'started.json',dict(binding(c,wanted),revision=revision(),cell_ids=[r['cell']['id'] for r in work],max_new=max_new))
        start=time.perf_counter();status='FAILED'
        try:
            stats['model_load_attempts']=1
            backend=(_factory or NativeBackend)(c.locations['model'],c.tok);stats['model_loads']=1
            if bool(backend.simulated)!=(wanted=='MOCK'): raise ValueError('Real/fake backend mismatch')
            freeze(c.out/'execution.json',dict(binding(c,wanted),backend=backend.identity,backend_hash=digest(backend.identity)))
            session=NativeSession(c,wanted)
            for r in work:
                cell=r['cell']['id'];oid=opid(r,current[cell]['attempt'])
                def perform():
                    freeze(c.out/'dispatches'/(digest(oid)+'.json'),dict(operation_id=oid,invocation=invocation,
                        backend_hash=digest(backend.identity),request_hash=r['request_hash'],revision=revision()))
                    stats['new_calls']+=1
                    return backend.generate(r['request'])
                try: session.operation(oid,r['request'],perform,'native_generation')
                except OperationUnavailable:
                    stats['stopped_after_backend_exception']=cell;break
            status='STOPPED' if 'stopped_after_backend_exception' in stats else 'BOUNDED_INVOCATION_COMPLETE'
        finally:
            freeze(folder/'finished.json',dict(binding(c,wanted),**stats,status=status,elapsed_seconds=time.perf_counter()-start))
        _,current,_,_=journal(c)
        return report(c,current,stats)


def retry(output,cell_id,reason):
    if not reason.strip(): raise ValueError('Explicit retry reason required')
    with run_lock(output):
        c=Context(output);_,current,_,_=journal(c)
        if needs_recovery(c):raise ValueError('Run explicit recover before authorizing a retry of interrupted writes')
        if cell_id not in current: raise ValueError('Unknown cell ID')
        x=current[cell_id];op=x['operation']
        if state(op) not in ('failed','ambiguous'): raise ValueError('Only failed/interrupted attempts can be explicitly retried; returned outcomes are final')
        return freeze(c.out/'retry-authorizations'/(digest([cell_id,x['attempt']+1])+'.json'),
            dict(plan_hash=c.plan['artifact_hash'],cell_id=cell_id,attempt=x['attempt']+1,
                 prior_operation_hash=op['artifact_hash'],reason=reason,revision=revision()))


def inspect(output):
    """Read-only: no run.lock creation, analysis write, quarantine, model load or dispatch."""
    from .analysis import report
    c=Context(output);_,current,_,_=journal(c)
    return report(c,current,dict(model_loads=0,new_calls=0,reused=0,scope='inspection'),write=False)


def analyze(output):
    from .analysis import report
    with run_lock(output):
        c=Context(output);_,current,_,_=journal(c)
        return report(c,current,dict(model_loads=0,new_calls=0,reused=0,scope='analysis'))


def recover(output,reason):
    with run_lock(output):
        c=Context(output);_,_,mode,_=journal(c)
        result=quarantine(c,binding(c,mode),reason)
        journal(c)
        return dict(result,journal_recovery=recovery_summary(c))
