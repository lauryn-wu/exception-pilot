"""Explicit v4 technical/collection stages; no automatic downstream work."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.core import final_score, response_boundaries
from exception_continuation.validation import calibration_result
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry, load_backend
from . import PROTOCOL
from .core import read_plan
from .journal import Session
from .validation import validate

def run(output, technical_only=False, limit_originals=8, complete=False, live_qwen=False,
        mock=False, backend_override=None, clock=None, timed=True):
    if backend_override is None and live_qwen==mock:
        raise ValueError('Choose explicit --live-qwen or --mock')
    if type(limit_originals) is not int or limit_originals < 1: raise ValueError('Positive bounded original count required')
    with run_lock(output) as out:
        plan=read_plan(out); status='FAILED'
        if plan['phase']=='confirmation' and not (complete or technical_only):
            raise ValueError('Confirmation collection must be explicitly requested with --complete')
        telemetry=Telemetry(out/'timing-v4',dict(protocol=PROTOCOL,plan_hash=plan['plan_hash']),clock) if timed else None
        try:
            if backend_override is not None: backend=backend_override
            elif telemetry: backend=load_backend(plan,telemetry,live_qwen,mock)
            else:
                from exception_continuation.backend import MockBackend,LocalBackend
                backend=MockBackend() if mock else LocalBackend(plan['config'])
            session=Session(out,plan,backend,telemetry)
            technical=validate(session)
            if technical_only:
                status='TECHNICAL_COMPLETE'
                return dict(status=status,measurement=technical['measurement'],technical_same_input_passed=True,
                            real_model_status=technical['real_model_status'],next_stage='STOP')
            count=len(plan['tasks']) if complete or (out/'collection-v4.json').exists() else min(limit_originals,len(plan['tasks']))
            rows=[]
            for task in plan['tasks'][:count]:
                ids=backend.prompt(task['prompt'])
                # Originals are uninterrupted; no cue, intervention or judge prompt.
                raw=session.generate('v4/original/'+task['id'],ids,512,stage='original_generation')
                rows.append(dict(task=task,input_ids=ids,input_hash=digest(ids),raw=raw,
                    full_token_ids=ids+raw['tokens'],boundaries=response_boundaries(backend,raw['tokens']),
                    score=final_score(raw['text'],raw['stopped'],task['expected'])))
            if count==len(plan['tasks']):
                collection=freeze(out/'collection-v4.json',dict(protocol=PROTOCOL,plan_hash=plan['plan_hash'],
                    backend_hash=session.backend_hash,technical_same_input_hash=technical['artifact_hash'],rows=rows))
                freeze(out/'calibration-v4.json',dict(protocol=PROTOCOL,collection_hash=collection['artifact_hash'],
                    measurement=technical['measurement'],**calibration_result(plan,collection)))
                status='COMPLETE'
            else:status='PAUSED'
            return dict(status=status,returned_originals=count,planned_originals=len(plan['tasks']),next_stage='STOP',
                        technical_same_input_passed=True,measurement=technical['measurement'])
        finally:
            if telemetry:telemetry.finish(status)
            from .reporting import selection_report,timing_report
            selection_report(out);timing_report(out)
