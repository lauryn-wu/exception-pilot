"""Worklist before weight loading; inherited immutable no-resend operations."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry,load_backend
from exception_study2_v5.journal import Session,OperationUnavailable,V5TimedBackend
from exception_study2_v5_replication.integrity import operation_tree
from . import VERSION,BUDGET
from .integrity import revision
from .planning import Context
from .parser import parse_reply


def content_identity(plan,mode):
    return dict(protocol=VERSION,plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],
        backend_hash=plan['backend_hash'],measurement_mode=mode)


def request(q,plan):
    return dict(query_hash=q['query_hash'],input_ids=q['context_ids'],context_hash=q['context_hash'],
        source_row_hash=q['source_row_hash'],parent_rows=q['parent_rows'],prefix_hash=q['prefix_hash'],
        suffix_ids=q['suffix_ids'],interface_version=q['interface_version'],checkpoint=q['checkpoint'],
        budget=BUDGET,capture_at=[],generation_settings=plan['generation_settings'])


def journal(context):
    out=context.out;path=out/'execution-content.json';execution=sealed_read(path) if path.exists() else None
    saved=operation_tree(out)
    mode=execution['measurement_mode'] if execution else 'LIVE_LOCAL'
    identity=content_identity(context.plan,mode)
    if execution and {k:v for k,v in execution.items() if k!='artifact_hash'}!=identity:
        raise ValueError('Source-report execution content/backend identity changed')
    if saved and execution is None:raise ValueError('Operation cache lacks execution content identity')
    for op_id,op in saved.items():
        q=context.queries.get(op_id)
        if q is None:raise ValueError('Unplanned source-report operation')
        req=request(q,context.plan)
        if (any(op.get(k)!=v for k,v in identity.items()) or op['request']!=req
            or op['stage']!='source_report_generation'):raise ValueError('Cached source-report request/identity mismatch')
        provenance=out/'operation-execution'/(digest(op_id)+'.json')
        if op['status']=='returned' and not provenance.exists():raise ValueError('Returned operation lacks dispatch provenance')
        if provenance.exists():
            p=sealed_read(provenance)
            if (p['operation_id']!=op_id or p['request_hash']!=digest(req) or p['execution_content_hash']!=execution['artifact_hash']
                or not p['extension_revision'] or p['historical_revision']!=context.plan['source']['historical_revision']):
                raise ValueError('Operation dispatch provenance differs')
    return saved,mode


def state(op):
    if op is None or op['status']=='planned':return 'never_started'
    return 'ambiguous' if op['status']=='started' else op['status']


def parsed(context,saved):
    return {q['id']:parse_reply(saved[q['id']]['result'],q['expected'],context.tokenizer)
            for q in context.queries.values() if state(saved.get(q['id']))=='returned'}


def gate(context,saved,answers):
    ids=[q['id'] for q in context.plan['calibration']]
    bad=[i for i in ids if state(saved.get(i)) in ('failed','ambiguous') or i in answers and not answers[i]['correct']]
    if bad:return dict(status='FAILED',blocked_main=True,failed_or_unresolved=bad)
    pending=[i for i in ids if state(saved.get(i))!='returned']
    return dict(status='PENDING' if pending else 'PASSED',blocked_main=bool(pending),pending=pending)


def worklist(context,saved,answers,calibration_only=False):
    g=gate(context,saved,answers)
    cal=[q for q in context.plan['calibration'] if state(saved.get(q['id']))=='never_started']
    main=[q for q in context.plan['main'] if state(saved.get(q['id']))=='never_started']
    executable=[] if g['status']=='FAILED' else cal if g['status']=='PENDING' or calibration_only else main
    return dict(gate=g,executable=executable,main_after_gate=main if g['status']=='PENDING' and not calibration_only else [])


class SourceSession(Session):
    def __init__(self,context,backend,telemetry,mode,stats):
        self.out=context.out;self.plan=context.plan;self.identity=content_identity(self.plan,mode)
        self.execution=freeze(self.out/'execution-content.json',self.identity)
        self.backend_hash=self.plan['backend_hash'];self.telemetry=telemetry;self.backend=V5TimedBackend(backend,telemetry)
        self.stats=stats;self.context=context;self.invocation=telemetry.invocation;self.actual_revision=revision()

    def short_generation(self,q):
        req=request(q,self.plan)
        def perform():
            # Written after the durable started marker and immediately before dispatch.
            freeze(self.out/'operation-execution'/(digest(q['id'])+'.json'),dict(operation_id=q['id'],
                request_hash=digest(req),execution_content_hash=self.execution['artifact_hash'],
                extension_revision=self.actual_revision,historical_revision=self.plan['source']['historical_revision'],
                invocation=self.invocation))
            self.stats['new_generations']+=1
            return self.backend.generate(q['context_ids'],BUDGET,capture_at=())
        return self.operation(q['id'],req,perform,'source_report_generation')


def terminal(context,op_id):
    folder=context.out/'operations-v5'/digest(op_id)
    return next(sealed_read(folder/(s+'.json')) for s in ('returned','failed','started','request') if (folder/(s+'.json')).exists())


def run(output,live_qwen=False,calibration_only=False,_backend_factory=None):
    from .reporting import report,save_report
    with run_lock(output):
        context=Context(output);saved,old_mode=journal(context);answers=parsed(context,saved)
        work=worklist(context,saved,answers,calibration_only)
        stats=dict(model_loads=0,model_load_attempts=0,new_generations=0,reused_returns=sum(state(o)=='returned' for o in saved.values()),
                   extension_revision=revision(),calibration_only=calibration_only)
        if not live_qwen and _backend_factory is None:
            return save_report(context,report(context,saved,stats,old_mode))
        if live_qwen and _backend_factory is not None:raise ValueError('Test backend injection cannot be combined with live mode')
        mode='MOCK' if _backend_factory is not None else 'LIVE_LOCAL'
        if saved and mode!=old_mode:raise ValueError('Cannot mix mock and live caches')
        if not work['executable']:
            return save_report(context,report(context,saved,stats,old_mode))
        telemetry=Telemetry(context.out/'timing-source-report',dict(protocol=VERSION,plan_hash=context.plan['artifact_hash'],extension_revision=revision()))
        freeze(context.out/'invocations'/telemetry.invocation/'started.json',dict(plan_hash=context.plan['artifact_hash'],
            code_contract=context.plan['code_contract'],extension_revision=revision(),historical_revision=context.plan['source']['historical_revision'],
            measurement_mode=mode,executable_ids=[q['id'] for q in work['executable']],model_load_intended=True))
        status='FAILED'
        try:
            stats['model_load_attempts']=1
            factory=_backend_factory or (lambda plan,t:load_backend(plan,t,True,False))
            backend=factory(context.evidence.remaining.plan,telemetry);stats['model_loads']=1
            if backend.identity!=context.plan['backend'] or digest(backend.identity)!=context.plan['backend_hash']:
                raise ValueError('Loaded backend differs from the original scientific identity; no generation dispatched')
            if mode=='LIVE_LOCAL' and backend.simulated:raise ValueError('Live mode requires the original real backend')
            if set(backend.eos_ids)!=set(context.plan['tokenizer']['eos_ids']):raise ValueError('Loaded backend EOS identity differs')
            session=SourceSession(context,backend,telemetry,mode,stats)
            def execute(queries):
                for q in queries:
                    try:session.short_generation(q)
                    except OperationUnavailable as exc:
                        # The journal has already preserved this failure. Stop
                        # dispatching so one runtime fault cannot consume the rest
                        # of the worklist; resume skips this terminal operation.
                        stats['stopped_after_exception']=dict(operation_id=q['id'],
                            error_type=type(exc.__cause__).__name__ if exc.__cause__ is not None else type(exc).__name__)
                        return
                    finally:saved[q['id']]=terminal(context,q['id'])
            # One model load covers calibration and main. Raw returns are durable
            # before parsing. Invalid returned replies never authorize resampling.
            if work['gate']['status']=='PENDING':execute(work['executable'])
            answers=parsed(context,saved);g=gate(context,saved,answers)
            if g['status']=='PASSED' and not calibration_only:
                execute([q for q in context.plan['main'] if state(saved.get(q['id']))=='never_started'])
            status='COMPLETE' if all(state(saved.get(i))=='returned' for i in context.queries) else 'STOPPED'
        finally:
            telemetry.finish(status)
            freeze(context.out/'invocations'/telemetry.invocation/'finished.json',dict(stats,status=status,measurement_mode=mode,plan_hash=context.plan['artifact_hash']))
        return save_report(context,report(context,saved,stats,mode))


def inspect(output):
    from .reporting import report
    with run_lock(output):
        c=Context(output);saved,mode=journal(c)
        return report(c,saved,dict(model_loads=0,model_load_attempts=0,new_generations=0,
            reused_returns=sum(state(o)=='returned' for o in saved.values()),extension_revision=revision()),mode)


def analyze(output):
    from .reporting import report,save_report
    with run_lock(output):
        c=Context(output);saved,mode=journal(c)
        return save_report(c,report(c,saved,dict(model_loads=0,model_load_attempts=0,new_generations=0,
            reused_returns=sum(state(o)=='returned' for o in saved.values()),extension_revision=revision()),mode))
