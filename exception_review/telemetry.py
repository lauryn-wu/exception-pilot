"""Non-mutating versioned telemetry; completed GPU wall time, never extra inference."""
from contextlib import contextmanager
import platform
import uuid
from pathlib import Path
from .journal import Clock
from .artifacts import freeze

TELEMETRY_VERSION='study2-timing-sidecar-v1'

class Telemetry:
    def __init__(self,root,binding,clock=None):
        self.root=Path(root); self.binding=binding; self.clock=clock or Clock(); self.invocation=uuid.uuid4().hex; self.events=[]
        self.start=self.clock.monotonic(); self.started_utc=self.clock.utc()
    def record(self,**data):
        value=dict(version=TELEMETRY_VERSION,invocation=self.invocation,**self.binding,**data)
        self.events.append(value)
        freeze(self.root/'events'/(self.invocation+'-'+str(len(self.events))+'.json'),value)
        return value
    @contextmanager
    def span(self,stage,measurement='LIVE',**metadata):
        start=self.clock.monotonic(); utc=self.clock.utc(); status='returned'
        try: yield
        except BaseException:
            status='failed'; raise
        finally: self.record(stage=stage,measurement=measurement,status=status,started_utc=utc,finished_utc=self.clock.utc(),elapsed_seconds=self.clock.monotonic()-start,**metadata)
    def finish(self,status):
        return freeze(self.root/'invocations'/(self.invocation+'.json'),dict(version=TELEMETRY_VERSION,**self.binding,invocation=self.invocation,started_utc=self.started_utc,finished_utc=self.clock.utc(),elapsed_seconds=self.clock.monotonic()-self.start,status=status,python=platform.python_version(),platform=platform.platform()))


def operation_stage(op):
    if op.startswith('technical/'): return 'technical_validation'
    if op.startswith('trajectory/'): return 'original_generation'
    if op.startswith('edit/') and op.endswith('/continuation'): return 'edited_continuation'
    if '/reference' in op: return 'event_reference' if op.startswith('event/') else 'intervention_reference'
    if 'readout' in op: return 'candidate_readout'
    if op.startswith('event/') and '/replay/' in op: return 'event_validation'
    if 'replay' in op: return 'unchanged_replay'
    return 'other'

class TimedBackend:
    def __init__(self,backend,telemetry): self.backend=backend; self.telemetry=telemetry; self.stage='other'; self.operation_id=None
    def __getattr__(self,name): return getattr(self.backend,name)
    def sync(self):
        torch=getattr(self.backend,'torch',None)
        if torch is not None and str(self.backend.model.device).startswith('cuda'): torch.cuda.synchronize(self.backend.model.device)
    def measured(self,stage,fn,inputs,outputs=None):
        self.sync(); start=self.telemetry.clock.monotonic(); utc=self.telemetry.clock.utc()
        try:
            result=fn(); self.sync()
        except BaseException:
            self.telemetry.record(stage=stage,operation_id=self.operation_id,measurement='MOCK' if self.simulated else 'LIVE',status='failed',started_utc=utc,finished_utc=self.telemetry.clock.utc(),elapsed_seconds=self.telemetry.clock.monotonic()-start,input_tokens=inputs,output_tokens=None); raise
        self.telemetry.record(stage=stage,operation_id=self.operation_id,measurement='MOCK' if self.simulated else 'LIVE',status='returned',started_utc=utc,finished_utc=self.telemetry.clock.utc(),elapsed_seconds=self.telemetry.clock.monotonic()-start,input_tokens=inputs,output_tokens=len(result['tokens']) if outputs is None else outputs)
        return result
    def generate(self,ids,budget,capture_at=()): return self.measured(self.stage,lambda:self.backend.generate(ids,budget,capture_at=capture_at),len(ids))
    def score(self,context,candidate): return self.measured('candidate_sequence_scoring',lambda:self.backend.score(context,candidate),len(context),len(self.backend.encode(candidate)))


def load_backend(plan,telemetry,live=False,mock=False):
    from exception_continuation.backend import MockBackend,LocalBackend
    if live==mock: raise ValueError('Choose --mock or explicit --live-qwen')
    if mock: return MockBackend()
    # Scoped timing wrappers call the original loader functions once with identical
    # arguments. They restore every binding on exit and never affect generation.
    from unittest.mock import patch
    from exception_continuation import qwen3
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    def wrap(stage,fn):
        def timed(*a,**kw):
            with telemetry.span(stage): return fn(*a,**kw)
        return timed
    original_to=torch.nn.Module.to
    depth=[0]
    def transfer(module,*a,**kw):
        if depth[0]: return original_to(module,*a,**kw)
        depth[0]+=1
        try:
            with telemetry.span('device_transfer'):
                result=original_to(module,*a,**kw)
                if str(getattr(module,'device','')).startswith('cuda'): torch.cuda.synchronize(module.device)
                return result
        finally: depth[0]-=1
    with telemetry.span('backend_initialization_total'):
        with patch.object(qwen3,'verify_local_snapshot',wrap('file_verification',qwen3.verify_local_snapshot)), patch.object(AutoTokenizer,'from_pretrained',wrap('tokenizer_initialization',AutoTokenizer.from_pretrained)), patch.object(AutoModelForCausalLM,'from_pretrained',wrap('model_loading_cpu',AutoModelForCausalLM.from_pretrained)), patch.object(torch.nn.Module,'to',transfer):
            backend=LocalBackend(plan['config'])
    telemetry.record(stage='backend_identity',measurement='LIVE',status='metadata',identity=backend.identity)
    return backend
