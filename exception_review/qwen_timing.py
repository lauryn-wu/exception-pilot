"""Opt-in bounded selection collection, delegating the complete legacy replay gate."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation import runner
from exception_continuation.core import read_plan,CHECKPOINTS,response_boundaries,final_score
from exception_continuation.validation import calibration_result
from .artifacts import freeze
from .telemetry import Telemetry,TimedBackend,operation_stage,load_backend

class TimedSession(runner.Session):
    def __init__(self,out,plan,backend,telemetry):
        self.telemetry=telemetry
        super().__init__(out,plan,TimedBackend(backend,telemetry))
    def operation(self,op_id,request,fn):
        cached=(self.out/'operations'/(digest(op_id)+'.json')).exists()
        self.backend.stage=operation_stage(op_id)
        result=super().operation(op_id,request,fn)
        if cached: self.telemetry.record(stage=operation_stage(op_id),status='cache_hit',measurement='CACHE',operation_id=op_id)
        return result


def collect_selection(output,limit_originals=8,complete=False,live_qwen=False,mock=False,backend_override=None,clock=None):
    if backend_override is None and live_qwen==mock: raise ValueError('Separate explicit --live-qwen or --mock required')
    if type(limit_originals) is not int or limit_originals<1: raise ValueError('Positive original-operation limit required')
    with run_lock(output) as out:
        plan=read_plan(out)
        if plan['phase']!='selection': raise ValueError('Bounded timing is selection/development only')
        telemetry=Telemetry(out/'timing-sidecar',{'plan_hash':plan['plan_hash']},clock)
        status='FAILED'
        try:
            backend=backend_override or load_backend(plan,telemetry,live_qwen,mock)
            telemetry.binding['backend_hash']=digest(backend.identity)
            session=TimedSession(out,plan,backend,telemetry)
            path=out/'validation.json'
            if path.exists():
                validation=runner.sealed_read(path)
                if not validation['passed'] or validation['plan_hash']!=plan['plan_hash'] or validation['backend_hash']!=session.backend_hash: raise ValueError('Technical validation FAILED or changed; STOP')
                telemetry.record(stage='technical_validation',measurement='CACHE',status='cache_hit')
            else:
                with telemetry.span('technical_stage_wall',measurement='MOCK' if backend.simulated else 'LIVE'): validation=runner.validate(session)
            count=len(plan['tasks']) if complete or (out/'collection.json').exists() else min(limit_originals,len(plan['tasks']))
            rows=[]
            for task in plan['tasks'][:count]:
                ids=backend.prompt(task['prompt'])
                raw=session.generate('trajectory/'+task['id'],ids,plan['config']['max_new_tokens'],capture_at=CHECKPOINTS)
                rows.append(dict(task=task,input_ids=ids,raw=raw,boundaries=response_boundaries(backend,raw['tokens']),score=final_score(raw['text'],raw['stopped'],task['expected'])))
            if count==len(plan['tasks']):
                result=freeze(out/'collection.json',dict(plan_hash=plan['plan_hash'],backend_hash=session.backend_hash,validation_hash=validation['artifact_hash'],rows=rows))
                freeze(out/'calibration.json',dict(collection_hash=result['artifact_hash'],mode='SIMULATED' if backend.simulated else 'LIVE_LOCAL',**calibration_result(plan,result)))
                status='COMPLETE'
            else: status='INCOMPLETE'
            return dict(status=status,completed_originals=count,planned_originals=len(plan['tasks']),calibration_available=status=='COMPLETE',next_stage='STOP_AND_INSPECT')
        finally:
            telemetry.finish(status)
            from .reporting import qwen_timing_report
            qwen_timing_report(output)
