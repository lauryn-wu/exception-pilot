"""Independent explanation queue using the existing immutable journal and lock."""
import os
import sys
import time
import uuid
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5.journal import Session, OperationUnavailable
from exception_study2_native.recovery import scan, state, quarantine
from exception_study2_source_report.integrity import revision, separate
from exception_study2_current.adapter import Backend
from . import VERSION, ENVIRONMENT
from .planning import Context

STAGE = 'matched_explicit_explanation'


def opid(r):
    return 'v5/' + VERSION + '/' + r['request_hash'] + '/attempt-1'


def binding(c, mode):
    return dict(protocol=VERSION, plan_hash=c.plan['artifact_hash'], code_contract=c.plan['code_contract'],
                source_binding_hash=digest(c.source.binding), measurement_mode=mode,
                runtime_environment=ENVIRONMENT)


def journal(c):
    path = c.out/'execution.json'; ex = sealed_read(path) if path.exists() else None
    mode = ex['measurement_mode'] if ex else 'UNEXECUTED'
    if mode not in ('UNEXECUTED', 'MOCK', 'LIVE_LOCAL'):
        raise ValueError('Unknown execution mode')
    identity = binding(c, mode)
    if ex and (any(ex.get(k) != v for k, v in identity.items()) or ex['backend_hash'] != digest(ex['backend'])
               or ex['backend_hash'] != c.plan['backend_hash']):
        raise ValueError('Explanation execution identity differs from source compatibility lock')
    known = {digest(opid(r)): dict(id=opid(r), identity=dict(identity, id=opid(r), request=r['request'],
                request_hash=r['request_hash'], stage=STAGE)) for r in c.requests}
    saved = scan(c, known, identity)
    if saved and not ex:
        raise ValueError('Missing execution binding')
    # Reject orphan dispatches rather than allowing a journal bypass.
    if any(p.stem not in known for p in (c.out/'dispatches').glob('*.json')):
        raise ValueError('Unknown dispatch outside explanation plan')
    current = {}
    for r in c.requests:
        op = saved.get(opid(r)); current[r['cell']['id']] = op
        if not op:
            continue
        if any(op.get(k) != v for k, v in identity.items()) or op['request'] != r['request']:
            raise ValueError('Cached explanation identity differs')
        path = c.out/'dispatches'/(digest(opid(r))+'.json')
        if op['status'] == 'returned' and not path.exists():
            raise ValueError('Missing dispatch provenance')
        if path.exists():
            d = sealed_read(path); started = sealed_read(c.out/'invocations'/d['invocation']/'started.json')
            if (d['request_hash'] != r['request_hash'] or d['backend_hash'] != ex['backend_hash']
                    or any(started.get(k) != v for k, v in identity.items())):
                raise ValueError('Dispatch/invocation binding differs')
    return current, mode, ex


class ExplanationSession(Session):
    def __init__(self, c, mode):
        self.out = c.out; self.identity = binding(c, mode); self.telemetry = None


def run(output, live=False, max_new=96, tokenizer_dir=None, model_dir=None, _factory=None):
    from .analysis import report, save_report
    if type(max_new) is not int or not 1 <= max_new <= 96:
        raise ValueError('--max-new must be 1..96; total remains fixed at 96')
    if live and _factory:
        raise ValueError('Cannot mix live and mock execution')
    with run_lock(output):
        c = Context(output, tokenizer_dir, model_dir); current, mode, ex = journal(c)
        stats = dict(new_dispatches=0, newly_returned=0, cached_explanation_responses=sum(state(x)=='returned' for x in current.values()),
                     historical_controls_reused=192, model_loads=0, model_load_attempts=0)
        if not live and _factory is None:
            return report(c, current, stats)
        wanted = 'MOCK' if _factory else 'LIVE_LOCAL'
        if mode not in ('UNEXECUTED', wanted):
            raise ValueError('Mock/live caches cannot mix')
        pending = [r for r in c.requests if state(current[r['cell']['id']]) == 'never_started']
        if not pending:
            return save_report(c, current, stats)
        separate(c.out, c.model_dir, c.tokenizer_dir)
        if 'vllm' in sys.modules and os.environ.get('VLLM_USE_FLASHINFER_SAMPLER') != '0':
            raise ValueError('vLLM was imported before the required sampler workaround; start a fresh process')
        os.environ.update(ENVIRONMENT)  # BEFORE the unchanged Backend imports vLLM.
        uid = uuid.uuid4().hex; folder = c.out/'invocations'/uid
        freeze(folder/'started.json', dict(binding(c, wanted), revision=revision(), max_new=max_new,
                                          model_path=str(c.model_dir), tokenizer_path=str(c.tokenizer_dir)))
        start = time.perf_counter(); status = 'FAILED'
        try:
            stats['model_load_attempts'] = 1
            backend = (_factory or Backend)(c.model_dir, c.tok); stats['model_loads'] = 1
            if bool(backend.simulated) != (wanted == 'MOCK'):
                raise ValueError('Mock/live backend differs')
            if digest(backend.identity) != c.plan['backend_hash']:
                raise ValueError('Backend differs from archived passing smoke; stop, no new smoke or generation authorized')
            freeze(c.out/'execution.json', dict(binding(c, wanted), backend=backend.identity, backend_hash=digest(backend.identity)))
            session = ExplanationSession(c, wanted)
            for r in pending[:max_new]:
                oid = opid(r)
                def dispatch():
                    freeze(c.out/'dispatches'/(digest(oid)+'.json'), dict(invocation=uid, request_hash=r['request_hash'],
                                                                      backend_hash=digest(backend.identity)))
                    stats['new_dispatches'] += 1
                    print('Dispatching ' + r['cell']['id'], flush=True)
                    raw = backend.generate(r['request'])
                    print('Returned ' + r['cell']['id'], flush=True)
                    return raw
                try:
                    session.operation(oid, r['request'], dispatch, STAGE)
                    stats['newly_returned'] += 1
                except OperationUnavailable as exc:
                    cause = exc.__cause__ or exc
                    freeze(folder/'backend-error.json', dict(operation_id=oid, error_type=type(cause).__name__, message=str(cause)))
                    stats['stopped_after_backend_exception'] = r['cell']['id']
                    break
            status = 'STOPPED_AFTER_FAILURE' if 'stopped_after_backend_exception' in stats else 'BOUNDED_COMPLETE'
        finally:
            stats['elapsed_seconds'] = time.perf_counter()-start
            freeze(folder/'finished.json', dict(binding(c, wanted), status=status, **stats))
        current, _, _ = journal(c)
        return save_report(c, current, stats)


def inspect(output, tokenizer_dir=None):
    from .analysis import report
    c = Context(output, tokenizer_dir); current, _, _ = journal(c)
    return report(c, current, dict(new_dispatches=0, model_loads=0))


def analyze(output, tokenizer_dir=None):
    from .analysis import save_report
    with run_lock(output):
        c = Context(output, tokenizer_dir); current, _, _ = journal(c)
        return save_report(c, current, dict(new_dispatches=0, model_loads=0))


def recover(output, reason, tokenizer_dir=None):
    with run_lock(output):
        c = Context(output, tokenizer_dir); _, mode, _ = journal(c)
        result = quarantine(c, binding(c, mode), reason); journal(c)
        return dict(result, note='Quarantine only. Failed/ambiguous attempts stay held. No resend, promotion, or replacement.')
