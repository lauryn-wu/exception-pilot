"""Disposable full-sequence readouts. No answer generation, original interruption or future tokens."""
import math
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.backend import readout
from exception_review.artifacts import freeze
from exception_continuation.runner import sealed_read
from .runner import Source, bound_source, model_session
from .scoring import checkpoints
from .journal import OperationUnavailable
from . import PROTOCOL

def score(session, op_id, input_ids, prefix_ids, task, cue):
    request=dict(input_ids=input_ids,prefix_ids=prefix_ids,gold=task['expected'],pattern=task['pattern'],cue_text=cue)
    def perform():
        value=readout(session.backend,**request)
        for label,s in value['scores'].items():
            if (not s['tokens'] or len(s['tokens'])!=len(s['token_logprobs'])
                    or not all(math.isfinite(x) and x<=0 for x in s['token_logprobs'])
                    or not math.isclose(sum(s['token_logprobs']),s['logprob'],rel_tol=1e-10,abs_tol=1e-10)):
                raise ValueError('Incomplete/invalid full candidate likelihood')
        value.update(preferred_class=max('ABC',key=lambda c:value['scores'][c]['logprob']),
                     context_ids=input_ids+prefix_ids+value['cue_ids'])
        return value
    return session.operation(op_id,request,perform,'candidate_readout')

def prepare_measurements(source_path, output, annotation_manifest=None, scope='pilot', events_only=False):
    source=Source(source_path,scope=scope); annotations=None
    if events_only and not annotation_manifest:raise ValueError('Event-only measurements require frozen annotations')
    if annotation_manifest:
        from .review.workflow import read_manifest
        annotations=read_manifest(annotation_manifest,source)
    rows=[]; computes={}
    for tid,row in source.rows.items():
        if row['task']['arm']!='visible': continue
        cuts=checkpoints(row,annotations['cases'][tid]['events'] if annotations else None) if row['status']=='returned' else [
            dict(name='original',eligible=False,k=None,reason=row['status'])]
        if events_only:cuts=[c for c in cuts if c['name'].split('/')[0] in ('acknowledgment','erasure','conflict','override')]
        for cut in cuts:
            cut['computations']=[]
            if not cut['eligible']: continue
            for ci,cue in enumerate(source.plan['config']['readout_cues']):
                key=digest([tid,cut['k'],cue]);cut['computations'].append(key)
                computes[key]=dict(task_id=tid,world=row['task']['world'],source_row_hash=row['artifact_hash'],k=cut['k'],cue_index=ci,cue_text=cue)
        rows.append(dict(task_id=tid,world=row['task']['world'],source_row_hash=row['artifact_hash'],checkpoints=cuts))
    out=Path(output)
    if out.exists() and any(out.iterdir()) and not (out/'measurement-plan-v5.json').exists():
        raise ValueError('Fresh measurement output required')
    with run_lock(out):
        return freeze(out/'measurement-plan-v5.json',dict(protocol=PROTOCOL,source=source.binding_at(out),
            layout='events_only' if events_only else 'combined' if annotations else 'fixed_only',
            annotations_hash=annotations['artifact_hash'] if annotations else None, rows=rows,computations=computes,
            ceiling_candidate_sequences=3*len(computes),generated_answers=0))

def measure(output, **mode):
    with run_lock(output) as out:
        plan=sealed_read(out/'measurement-plan-v5.json');source=bound_source(plan['source'],out); results={}
        with model_session(out,source.plan,binding={'measurement_plan':plan['artifact_hash']},**mode) as session:
            if session.backend_hash!=source.execution['backend_hash']:raise ValueError('Backend changed')
            for key,c in plan['computations'].items():
                row=source.rows[c['task_id']];prefix=row['raw']['tokens'][:c['k']]
                if session.backend.encode(session.backend.decode(prefix))!=prefix:raise ValueError('Prefix roundtrip changed')
                try:
                    value=score(session,'v5/readout/'+key,row['input_ids'],prefix,row['task'],c['cue_text'])
                    results[key]=dict(status='returned',world=row['task']['world'],source_row_hash=row['artifact_hash'],value=value)
                except OperationUnavailable as exc:results[key]=dict(status='unavailable',reason=str(exc))
        value=freeze(out/'measurements-v5.json',dict(plan_hash=plan['artifact_hash'],results=results,
                      measurement='MOCK' if session.backend.simulated else 'LIVE'))
        from .reporting import trajectory_report
        freeze(out/'trajectory-summary-v5.json',trajectory_report(source,plan,value))
        return value
