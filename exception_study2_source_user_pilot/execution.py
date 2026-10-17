"""Independent pilot execution: preflight, one load, durable no-resend operations."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry,load_backend
from exception_study2_v5.journal import Session,OperationUnavailable,V5TimedBackend
from exception_study2_v5_replication.integrity import operation_tree
from . import VERSION,NAMESPACE,BUDGET
from .integrity import revision,separate,sha,artifact_files
from .planning import Context
STAGE='source_user_pilot_generation'


def identity(plan,mode):
    return dict(protocol=VERSION,plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],
        backend_hash=plan['backend_hash'],measurement_mode=mode)


def request(q,plan):
    return dict(query_hash=q['query_hash'],origin_query_id=q['origin_query_id'],origin_query_hash=q['origin_query_hash'],
        origin_operation_hash=q['origin_operation_hash'],input_ids=q['context_ids'],context_hash=q['context_hash'],
        old_context_hash=q['old_context_hash'],bridge_hash=q['bridge_hash'],bridge_ids=q['bridge_ids'],
        parent_rows=q['parent_rows'],source_row_hash=q['source_row_hash'],interface_version=q['interface_version'],
        parser_version=q['parser_version'],budget=BUDGET,capture_at=[],generation_settings=plan['generation_settings'])


def state(op):
    if op is None or op['status']=='planned':return 'never_started'
    return 'ambiguous' if op['status']=='started' else op['status']


def journal(c):
    path=c.out/'execution-content.json';ex=sealed_read(path) if path.exists() else None
    saved=operation_tree(c.out);mode=ex['measurement_mode'] if ex else 'UNEXECUTED'
    if mode not in ('UNEXECUTED','MOCK','LIVE_LOCAL'):raise ValueError('Unknown execution mode')
    binding=identity(c.plan,mode)
    if ex and {k:v for k,v in ex.items() if k!='artifact_hash'}!=binding:raise ValueError('Pilot execution identity mismatch')
    if saved and ex is None:raise ValueError('Cache lacks pilot execution identity')
    for opid,op in saved.items():
        if not opid.startswith(NAMESPACE) or opid not in c.queries:raise ValueError('Cross-version or unplanned operation forbidden')
        req=request(c.queries[opid],c.plan)
        if any(op.get(k)!=v for k,v in binding.items()) or op['request']!=req or op['stage']!=STAGE:
            raise ValueError('Cached request/backend/source identity mismatch')
        path=c.out/'operation-execution'/(digest(opid)+'.json')
        if op['status']=='returned' and not path.exists():raise ValueError('Returned operation lacks dispatch provenance')
        if path.exists():
            provenance=sealed_read(path)
            if (provenance['operation_id']!=opid or provenance['request_hash']!=digest(req)
                or provenance['execution_content_hash']!=ex['artifact_hash'] or not provenance['extension_revision']
                or provenance['historical_revision']!=c.plan['historical_revision']):
                raise ValueError('Pilot dispatch provenance differs')
    return saved,mode


class PilotSession(Session):
    # Inherit only the generic immutable operation primitive, never a v1/v2 runner/session.
    def __init__(self,c,backend,telemetry,mode,stats):
        self.out=c.out;self.plan=c.plan;self.identity=identity(c.plan,mode)
        self.execution=freeze(self.out/'execution-content.json',self.identity)
        self.backend=V5TimedBackend(backend,telemetry);self.telemetry=telemetry;self.stats=stats

    def generate_query(self,q):
        req=request(q,self.plan)
        def perform():
            freeze(self.out/'operation-execution'/(digest(q['id'])+'.json'),dict(operation_id=q['id'],
                request_hash=digest(req),execution_content_hash=self.execution['artifact_hash'],
                extension_revision=revision(),historical_revision=self.plan['historical_revision'],invocation=self.telemetry.invocation))
            self.stats['new_generations']+=1
            return self.backend.generate(q['context_ids'],BUDGET,capture_at=())
        return self.operation(q['id'],req,perform,STAGE)


def stats_for(saved):
    return dict(model_loads=0,model_load_attempts=0,new_generations=0,
        reused_child_returns=sum(state(o)=='returned' for o in saved.values()),
        prior_v2_returns=12,prior_v2_generations_rerun=0,main_calls=0,extension_revision=revision())


def run(output,live_qwen=False,_backend_factory=None):
    from .reporting import report,save_report
    with run_lock(output):
        c=Context(output);saved,old_mode=journal(c);stats=stats_for(saved)
        work=[q for q in c.plan['queries'] if state(saved.get(q['id']))=='never_started']
        if not live_qwen and _backend_factory is None:return save_report(c,report(c,saved,old_mode,stats))
        if live_qwen and _backend_factory is not None:raise ValueError('Mock factory cannot be combined with live mode')
        mode='MOCK' if _backend_factory is not None else 'LIVE_LOCAL'
        if old_mode!='UNEXECUTED' and mode!=old_mode:raise ValueError('MOCK/LIVE caches cannot mix')
        if not work:return save_report(c,report(c,saved,old_mode,stats))
        t=Telemetry(c.out/'timing-pilot',dict(protocol=VERSION,plan_hash=c.plan['artifact_hash'],extension_revision=revision()))
        freeze(c.out/'invocations'/t.invocation/'started.json',dict(plan_hash=c.plan['artifact_hash'],
            measurement_mode=mode,executable_ids=[q['id'] for q in work],extension_revision=revision()))
        status='FAILED'
        try:
            stats['model_load_attempts']=1
            factory=_backend_factory or (lambda p,t:load_backend(p,t,True,False))
            backend=factory(c.parent.source.plan,t);stats['model_loads']=1
            if backend.identity!=c.plan['backend'] or digest(backend.identity)!=c.plan['backend_hash']:
                raise ValueError('Loaded backend identity differs; no pilot generation dispatched')
            if mode=='LIVE_LOCAL' and backend.simulated:raise ValueError('Live mode requires the original real backend')
            if set(backend.eos_ids)!=set(c.plan['tokenizer']['eos_ids']):raise ValueError('Loaded backend EOS differs')
            session=PilotSession(c,backend,t,mode,stats)
            for q in work:
                try:session.generate_query(q)
                except OperationUnavailable as exc:
                    stats['stopped_after_exception']=dict(operation_id=q['id'],error_type=type(exc.__cause__).__name__)
                    break
                # Returned wrong/malformed/length payloads are measured outcomes; collect the rest.
            saved,_=journal(c)
            status='COMPLETE' if all(state(saved.get(q['id']))=='returned' for q in c.plan['queries']) else 'STOPPED'
        finally:
            t.finish(status)
            freeze(c.out/'invocations'/t.invocation/'finished.json',dict(stats,status=status,measurement_mode=mode,plan_hash=c.plan['artifact_hash']))
        return save_report(c,report(c,saved,mode,stats))


def inspect(output):
    from .reporting import report
    with run_lock(output):
        c=Context(output);saved,mode=journal(c)
        return report(c,saved,mode,stats_for(saved))


def archive(output,archive_path):
    import os
    import tarfile
    from .reporting import report,save_report
    with run_lock(output):
        c=Context(output);saved,mode=journal(c)
        target=separate(archive_path,c.out,c.locations['parent'],c.locations['originals'],c.locations['tokenizer'],c.plan['backend']['config']['model_dir'])
        if target.exists():raise FileExistsError('Archive already exists; never overwrite it')
        save_report(c,report(c,saved,mode,stats_for(saved)))
        files=artifact_files(c.out);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:
            with tarfile.open(fileobj=stream,mode='w:gz') as tar:
                for name in files:tar.add(c.out/name,arcname=str(Path(c.out.name)/name),recursive=False)
            stream.flush();os.fsync(stream.fileno())
        return dict(archive=str(target),sha256=sha(target),plan_hash=c.plan['artifact_hash'],model_loads=0,inference_calls=0)
