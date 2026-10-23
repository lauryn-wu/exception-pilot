"""Single-attempt API dispatch with immutable journals and conservative resume."""
import os
import time
import uuid
from datetime import datetime, timezone
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.providers import HTTPTransport, redact
from exception_study2_v5.journal import Session, OperationUnavailable
from exception_study2_native.recovery import scan, state, quarantine
from exception_study2_source_report.integrity import revision
from . import VERSION
from .planning import Context
from .parsing import infrastructure_error
STAGE = 'gpt_matched_explanation'


def utc():
    return datetime.now(timezone.utc).isoformat()


def opid(r):
    return 'v5/' + VERSION + '/' + r['request_hash'] + '/attempt-1'


def binding(c, mode):
    return dict(protocol=VERSION, plan_hash=c.plan['artifact_hash'], code_contract=c.plan['code_contract'],
                source_binding_hash=digest(c.plan['source']), measurement_mode=mode)


def journal(c):
    path = c.out/'execution.json'; ex = sealed_read(path) if path.exists() else None
    mode = ex['measurement_mode'] if ex else 'UNEXECUTED'
    if mode not in ('UNEXECUTED','MOCK','LIVE_API'): raise ValueError('Unknown GPT execution mode')
    identity = binding(c, mode)
    if ex and ex != dict(identity, artifact_hash=digest(identity)):
        raise ValueError('GPT execution binding differs')
    known = {digest(opid(r)):dict(id=opid(r), identity=dict(identity, id=opid(r), request=r['request'],
                   request_hash=r['request_hash'], stage=STAGE)) for r in c.requests}
    saved = scan(c, known, identity)
    if saved and not ex: raise ValueError('Missing GPT execution binding')
    for dirname in ('dispatches','responses'):
        for p in (c.out/dirname).glob('*'):
            if p.is_symlink() or not p.is_file() or p.suffix != '.json' or p.stem not in known:
                raise ValueError('Unknown GPT ' + dirname + ' artifact')
    current = {}
    for r in c.requests:
        oid = opid(r); op = saved.get(oid); current[r['cell']['id']] = op
        if op and (any(op.get(k) != v for k,v in identity.items()) or op['request'] != r['request']):
            raise ValueError('Cached GPT identity differs')
        path = c.out/'dispatches'/(digest(oid)+'.json')
        response_path = c.out/'responses'/(digest(oid)+'.json')
        if state(op) == 'returned' and not path.exists(): raise ValueError('Missing dispatch provenance')
        if path.exists():
            d = sealed_read(path); start = sealed_read(c.out/'invocations'/d['invocation']/'started.json')
            if d['request_hash'] != r['request_hash'] or any(start.get(k) != v for k,v in identity.items()):
                raise ValueError('GPT dispatch/invocation differs')
        if response_path.exists():
            response = sealed_read(response_path)
            if not path.exists() or response['operation_id'] != oid or response['request_hash'] != r['request_hash']:
                raise ValueError('Orphan raw response')
            if state(op) == 'never_started': raise ValueError('Raw response without a held dispatch')
            if state(op) == 'returned' and response['raw'] != op['result']:
                raise ValueError('Raw response differs from journal')
        elif state(op) == 'returned':
            raise ValueError('Missing raw response sidecar')
    return current, mode


class APISession(Session):
    def __init__(self, c, mode):
        self.out = c.out; self.identity = binding(c, mode); self.telemetry = None


class InfrastructureFailure(RuntimeError): pass


def run(output, live=False, max_new=192, _transport=None):
    from .analysis import report, save_report
    if type(max_new) is not int or not 1 <= max_new <= 192: raise ValueError('--max-new must be 1..192')
    if live and _transport is not None: raise ValueError('Cannot mix live and mock execution')
    with run_lock(output):
        c = Context(output); current, mode = journal(c)
        stats = dict(new_dispatches=0, newly_returned=0, cached=sum(state(x)=='returned' for x in current.values()))
        if not live and _transport is None: return report(c, current, stats)
        wanted = 'MOCK' if _transport is not None else 'LIVE_API'
        if mode not in ('UNEXECUTED',wanted): raise ValueError('Mock/live caches cannot mix')
        pending = [r for r in c.requests if state(current[r['cell']['id']]) == 'never_started']
        if not pending: return save_report(c, current, stats)  # No transport/key access on completed resume.
        if _transport is not None and getattr(_transport,'kind',None) != 'MOCK': raise ValueError('Mock transport required')
        if live and not os.environ.get('OPENAI_API_KEY'): raise ValueError('Set OPENAI_API_KEY in this shell; never save it in the repository')
        transport = _transport if _transport is not None else HTTPTransport()
        freeze(c.out/'execution.json', binding(c, wanted))
        uid = uuid.uuid4().hex; folder = c.out/'invocations'/uid
        freeze(folder/'started.json', dict(binding(c,wanted), revision=revision(), max_new=max_new, started_utc=utc()))
        start = time.perf_counter(); status = 'INTERRUPTED'
        try:
            session = APISession(c,wanted)
            for r in pending[:max_new]:
                oid = opid(r)
                def dispatch():
                    freeze(c.out/'dispatches'/(digest(oid)+'.json'), dict(invocation=uid, request_hash=r['request_hash']))
                    stats['new_dispatches'] += 1
                    print('Dispatching ' + r['cell']['id'], flush=True)
                    began = utc(); tick = time.perf_counter()
                    response = transport('openai', r['request']['payload'], 180)
                    # Transport never includes request authorization headers. Defensive redaction only for accidental echoes.
                    safe = redact(response)
                    raw = dict(response=safe, requested_model=r['request']['payload']['model'], started_utc=began,
                               finished_utc=utc(), elapsed_seconds=time.perf_counter()-tick, redacted=safe != response)
                    freeze(c.out/'responses'/(digest(oid)+'.json'), dict(operation_id=oid, request_hash=r['request_hash'], raw=raw))
                    failure = infrastructure_error(raw)
                    if failure: raise InfrastructureFailure(failure)
                    print('Returned ' + r['cell']['id'], flush=True)
                    return raw
                try:
                    session.operation(oid, r['request'], dispatch, STAGE); stats['newly_returned'] += 1
                except OperationUnavailable as exc:
                    cause = exc.__cause__ or exc
                    freeze(folder/'error.json', dict(operation_id=oid, error_type=type(cause).__name__, message=redact(str(cause))))
                    stats['stopped_after_failure'] = r['cell']['id']; break
            status = 'STOPPED_AFTER_FAILURE' if 'stopped_after_failure' in stats else 'BOUNDED_COMPLETE'
        finally:
            stats['elapsed_seconds'] = time.perf_counter()-start
            freeze(folder/'finished.json', dict(binding(c,wanted), status=status, finished_utc=utc(), **stats))
        current, _ = journal(c)
        return save_report(c, current, stats)


def inspect(output):
    from .analysis import report
    with run_lock(output):
        c = Context(output); current, _ = journal(c)
        return report(c, current, dict(new_dispatches=0))


def analyze(output):
    from .analysis import save_report
    with run_lock(output):
        c = Context(output); current, _ = journal(c)
        return save_report(c, current, dict(new_dispatches=0))


def recover(output, reason):
    with run_lock(output):
        c = Context(output); _, mode = journal(c)
        result = quarantine(c, binding(c,mode), reason); journal(c)
        return dict(result, note='Quarantine only. Failed/ambiguous calls remain held; no retries or promotion.')
