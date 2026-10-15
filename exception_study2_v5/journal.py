"""Independent v5 model journal: immutable request/start/terminal files, no resend."""
from pathlib import Path
import subprocess
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.telemetry import TimedBackend
from . import PROTOCOL

class V5TimedBackend(TimedBackend):
    """Record malformed returned payloads without losing them to length telemetry."""
    def measured(self,stage,fn,inputs,outputs=None):
        self.sync();start=self.telemetry.clock.monotonic();utc=self.telemetry.clock.utc()
        metadata=dict(stage=stage,operation_id=self.operation_id,measurement='MOCK' if self.simulated else 'LIVE',
                      started_utc=utc,input_tokens=inputs)
        try:
            result=fn();self.sync()
        except BaseException:
            self.telemetry.record(**metadata,status='failed',finished_utc=self.telemetry.clock.utc(),
                                  elapsed_seconds=self.telemetry.clock.monotonic()-start,output_tokens=None)
            raise
        tokens=result.get('tokens') if isinstance(result,dict) else None
        count=outputs if outputs is not None else len(tokens) if isinstance(tokens,list) else None
        self.telemetry.record(**metadata,status='returned',finished_utc=self.telemetry.clock.utc(),
                              elapsed_seconds=self.telemetry.clock.monotonic()-start,output_tokens=count)
        return result

class OperationUnavailable(RuntimeError): pass

def operations(output):
    entries = {}
    for path in sorted((Path(output)/'operations-v5').glob('*/request.json')):
        request = sealed_read(path)
        if request['id'] in entries: raise ValueError('Duplicate v5 operation ID')
        if (path.parent.name != digest(request['id']) or not request['id'].startswith('v5/')
                or request['request_hash'] != digest(request['request']) or request['status'] != 'planned'):
            raise ValueError('Malformed v5 request identity')
        states = {n:sealed_read(path.parent/(n+'.json')) for n in ('started','failed','returned') if (path.parent/(n+'.json')).exists()}
        if ('failed' in states and 'returned' in states) or any(n in states for n in ('failed','returned')) and 'started' not in states:
            raise ValueError('Contradictory v5 terminal operation states')
        for state,entry in states.items():
            if entry.get('status') != state or any(entry.get(k)!=v for k,v in request.items() if k not in ('artifact_hash','status')):
                raise ValueError('Terminal v5 request identity differs')
        entries[request['id']] = states.get('returned',states.get('failed',states.get('started',request)))
    return entries

class Session:
    def __init__(self, output, plan, backend, telemetry=None, binding=None):
        self.out, self.plan = Path(output), plan
        self.backend_hash = digest(backend.identity)
        self.identity = dict(protocol=PROTOCOL, plan_hash=plan['plan_hash'], source_hash=plan['source_hash'],
                             backend_hash=self.backend_hash, **(binding or {}))
        mode = 'MOCK' if backend.simulated else 'LIVE_LOCAL'
        selected = plan['selection_lock']
        if selected and (selected['backend_hash'] != self.backend_hash or selected['mode'] != mode):
            raise ValueError('Confirmation backend differs from selected model')
        revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip()
        self.execution = freeze(self.out/'execution-v5.json', dict(**self.identity, mode=mode, backend=backend.identity, code_revision=revision))
        self.telemetry = telemetry
        self.backend = V5TimedBackend(backend, telemetry) if telemetry else backend
        for op in operations(output).values():
            if any(op.get(k) != v for k,v in self.identity.items()):
                raise ValueError('Journal source/backend/manifest changed')

    def operation(self, op_id, request, fn, stage):
        if not op_id.startswith('v5/'):
            raise ValueError('Separate v5 operation namespace required')
        path = self.out/'operations-v5'/digest(op_id)
        identity = dict(**self.identity, id=op_id, request=request, request_hash=digest(request), stage=stage)
        freeze(path/'request.json', dict(identity, status='planned'))
        if self.telemetry:
            self.backend.stage, self.backend.operation_id = stage, op_id
        for state in ('returned','failed','started'):
            p = path/(state+'.json')
            if p.exists():
                old = sealed_read(p)
                if any(old.get(k) != v for k,v in identity.items()): raise ValueError('Operation request identity changed')
                if self.telemetry: self.telemetry.record(stage=stage, operation_id=op_id, status='cache_hit', measurement='CACHE')
                if state != 'returned': raise OperationUnavailable('Terminal/ambiguous operation; no resend: '+op_id)
                return old['result']
        freeze(path/'started.json', dict(identity, status='started'))
        try:
            result = fn()
        except BaseException as exc:
            freeze(path/'failed.json', dict(identity, status='failed', error_type=type(exc).__name__))
            if not isinstance(exc, Exception): raise
            raise OperationUnavailable('Terminal/ambiguous operation; no resend: '+op_id) from exc
        freeze(path/'returned.json', dict(identity, status='returned', result=result))
        return result

    def generate(self, op_id, ids, budget, capture_at=(), stage='technical_same_input'):
        request = dict(input_ids=ids, context_hash=digest(ids), budget=budget, capture_at=list(capture_at), fresh_prefill=True)
        return self.operation(op_id, request, lambda:self.backend.generate(ids,budget,capture_at=capture_at), stage)
