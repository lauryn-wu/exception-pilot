"""Separate explicit stages, immutable originals, fresh technical evidence per run."""
from contextlib import contextmanager
from pathlib import Path
import os
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_continuation.backend import MockBackend
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry, load_backend
from . import PROTOCOL, BUDGET
from .core import read_plan
from .journal import Session, operations, OperationUnavailable
from .validation import validate, require_technical
from .scoring import final_score, validate_raw, boundaries, raw_metadata

class V5MockBackend(MockBackend):
    # The legacy character fixture terminates with token zero. Keep this adapter local.
    eos_ids = {0}

@contextmanager
def model_session(output, plan, live_qwen=False, mock=False, backend_override=None, binding=None):
    out = Path(output)
    telemetry = Telemetry(out/'timing-v5', dict(protocol=PROTOCOL, plan_hash=plan['plan_hash']))
    status = 'FAILED'
    try:
        if backend_override is not None:
            backend = backend_override
        else:
            if live_qwen == mock:
                raise ValueError('Choose explicit --live-qwen or --mock')
            backend = V5MockBackend() if mock else load_backend(plan, telemetry, live_qwen, False)
        session = Session(out, plan, backend, telemetry, binding)
        yield session
        status = 'COMPLETE'
    finally:
        telemetry.finish(status)

def technical(output, **mode):
    with run_lock(output) as out:
        plan = read_plan(out)
        if mode.get('live_qwen'):
            from .staging import require_design_confirmation
            require_design_confirmation(out)
        with model_session(out, plan, **mode) as session:
            return validate(session)

def collect(output, batch='pilot', **mode):
    with run_lock(output) as out:
        plan = read_plan(out)
        execution = sealed_read(out/'execution-v5.json')
        gate = require_technical(out, plan, execution)  # Before model loading; never auto-validate.
        if batch not in ('pilot','remaining'): raise ValueError('Choose pilot or explicitly approved remaining batch')
        Source(out, complete=False, scope='all')  # Verify existing originals BEFORE any new call.
        if mode.get('live_qwen'):
            from .staging import require_design_confirmation
            require_design_confirmation(out)
        if batch == 'remaining':
            from .staging import require_approval
            require_approval(out)
        tasks = plan['tasks'][:32] if batch == 'pilot' else plan['tasks'][32:]
        with model_session(out, plan, **mode) as session:
            for task in tasks:
                row_path = out/'originals-v5'/(digest(task['id'])+'.json')
                if row_path.exists():
                    continue  # Source() verifies the cache against the immutable journal below.
                ids = session.backend.prompt(task['prompt'])
                row = dict(task=task, input_ids=ids, input_hash=digest(ids), raw=None, boundaries=[],
                           validation_error=None, score=final_score('',False,task['expected'],task['arm']))
                try:
                    raw = session.generate('v5/original/'+task['id'], ids, BUDGET, stage='original_generation')
                    row['raw'] = raw
                    validate_raw(raw, session.backend, BUDGET)
                    row.update(boundaries=boundaries(session.backend,raw),
                               score=final_score(raw['text'],raw['stopped'],task['expected'],task['arm']), status='returned')
                except OperationUnavailable:
                    row.update(status='unavailable',validation_error='failed_or_ambiguous_no_resend')
                except (ValueError,KeyError,TypeError) as exc:
                    row.update(status='invalid_return',validation_error=str(exc))
                saved = operations(out)['v5/original/'+task['id']]
                row.update(**raw_metadata(row['raw'],ids),
                           operation_hash=saved['artifact_hash'],plan_hash=plan['plan_hash'],backend_hash=session.backend_hash,
                           technical_hash=gate['artifact_hash'])
                freeze(row_path,row)
        source = Source(out, complete=False, scope='all')
        if len(source.rows)==len(plan['tasks']):
            freeze(out/'collection-v5.json',dict(protocol=PROTOCOL,plan_hash=plan['plan_hash'],source_binding=source.hash,
                  row_hashes={tid:r['artifact_hash'] for tid,r in source.rows.items()}))
        return dict(protocol=PROTOCOL, status='COMPLETE' if len(source.rows)==len(plan['tasks']) else 'PAUSED',
                    recorded_originals=len(source.rows), planned_originals=len(plan['tasks']),
                    measurement=source.execution['mode'], next_stage='STOP',
                    offline_summary='Run the separate summary command explicitly')

class Source:
    """Read-only source adapter; verifies originals and genuine technical journals."""
    def __init__(self, output, complete=True, scope='pilot'):
        self.root=Path(output).resolve(); self.plan=read_plan(self.root)
        if scope not in ('pilot','remaining','all'): raise ValueError('Unknown source snapshot scope')
        self.scope=scope
        self.tasks=self.plan['tasks'][:32] if scope=='pilot' else self.plan['tasks'][32:] if scope=='remaining' else self.plan['tasks']
        self.worlds=self.plan['worlds'][:4] if scope=='pilot' else self.plan['worlds'][4:] if scope=='remaining' else self.plan['worlds']
        self.execution=sealed_read(self.root/'execution-v5.json')
        self.technical=require_technical(self.root,self.plan,self.execution)
        saved=operations(self.root); self.rows={}
        for task in self.tasks:
            path=self.root/'originals-v5'/(digest(task['id'])+'.json')
            if not path.exists(): continue
            row=sealed_read(path); op=saved.get('v5/original/'+task['id'])
            if (not op or row['task']!=task or row['plan_hash']!=self.plan['plan_hash']
                or row['backend_hash']!=self.execution['backend_hash'] or row['technical_hash']!=self.technical['artifact_hash']
                or row['operation_hash']!=op['artifact_hash'] or op['source_hash']!=self.plan['source_hash']
                or op['backend_hash']!=self.execution['backend_hash'] or op['plan_hash']!=self.plan['plan_hash']
                or op['request']!=dict(input_ids=row['input_ids'],context_hash=digest(row['input_ids']),budget=BUDGET,capture_at=[],fresh_prefill=True)
                or row['input_hash']!=digest(row['input_ids'])):
                raise ValueError('Original source/request/identity mismatch')
            if op['status']=='returned' and row['raw']!=op['result']:
                raise ValueError('Saved raw original differs from operation')
            if any(row.get(k)!=v for k,v in raw_metadata(row['raw'],row['input_ids']).items()):
                raise ValueError('Original token fingerprints/lengths changed')
            if row['status']=='returned':
                if row['score']!=final_score(row['raw']['text'],row['raw']['stopped'],task['expected'],task['arm']):
                    raise ValueError('Original scoring changed')
                from .reconstruction import validate_boundaries
                validate_boundaries(row)
            self.rows[task['id']]=row
        if complete and len(self.rows)!=len(self.tasks):
            raise ValueError('Complete attempted batch snapshot required for downstream analyses/review')
        self.hash=digest(dict(plan=self.plan['plan_hash'],execution=self.execution['artifact_hash'],technical=self.technical['artifact_hash'],
                              originals={tid:r['artifact_hash'] for tid,r in self.rows.items()}))
        self.binding=dict(scope=scope,source_hash=self.hash,plan_hash=self.plan['plan_hash'],backend_hash=self.execution['backend_hash'])
        if scope=='all' and (self.root/'collection-v5.json').exists():
            saved_collection=sealed_read(self.root/'collection-v5.json')
            if saved_collection['source_binding']!=self.hash:
                raise ValueError('Collection source binding changed')

    def binding_at(self, directory):
        return dict(self.binding, path=os.path.relpath(self.root, Path(directory).resolve()))

def binding_identity(binding):
    return {k:v for k,v in binding.items() if k!='path'}

def bound_source(binding, directory):
    path=Path(binding['path'])
    if path.is_absolute(): raise ValueError('Staged source bindings must be relative')
    source=Source(Path(directory)/path,scope=binding['scope'])
    if source.binding!=binding_identity(binding): raise ValueError('Frozen source binding changed')
    return source
