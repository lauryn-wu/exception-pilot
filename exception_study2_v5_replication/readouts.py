"""Fixed-only remaining-world readouts; original v5 planning/scoring remain intact."""
import math
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.runner import Source,binding_identity
from exception_study2_v5 import readouts as v5
from exception_study2_v5.scoring import checkpoints
from .integrity import read_amendment,operation_tree,revision
from .workflow import verify_copy,require_approval


def expected_plan(source,out):
    rows=[];computes={}
    for tid,row in source.rows.items():
        if row['task']['arm']!='visible':continue
        cuts=checkpoints(row) if row['status']=='returned' else [dict(name='original',eligible=False,k=None,reason=row['status'])]
        for cut in cuts:
            cut['computations']=[]
            if cut['eligible']:
                for ci,cue in enumerate(source.plan['config']['readout_cues']):
                    key=digest([tid,cut['k'],cue]);cut['computations'].append(key)
                    computes[key]=dict(task_id=tid,world=row['task']['world'],source_row_hash=row['artifact_hash'],k=cut['k'],cue_index=ci,cue_text=cue)
        rows.append(dict(task_id=tid,world=row['task']['world'],source_row_hash=row['artifact_hash'],checkpoints=cuts))
    return dict(protocol=PROTOCOL,source=source.binding_at(out),layout='fixed_only',annotations_hash=None,
        rows=rows,computations=computes,ceiling_candidate_sequences=3*len(computes),generated_answers=0)


def prepare(output):
    out=Path(output).resolve();a=read_amendment(out);require_approval(out,a);verify_copy(out,a)
    src=Source(out/'originals',scope='remaining');target=out/'readouts-remaining-v1'
    plan=v5.prepare_measurements(src.root,target,scope='remaining')
    if {k:v for k,v in plan.items() if k!='artifact_hash'}!=expected_plan(src,target):raise ValueError('Fixed measurement plan changed')
    if {r['task_id'] for r in plan['rows']}!=set(a['remaining_visible_ids']):raise ValueError('All 224 remaining visible trajectories required')
    freeze(out/'replication-readouts.json',dict(amendment_hash=a['artifact_hash'],measurement_plan_hash=plan['artifact_hash'],
        source=src.binding_at(out),pilot_readouts_recomputed=0,generated_answers=0,next_stage='STOP_EXPLICIT_MEASUREMENT'))
    return plan


def measure(output,live_qwen=False,mock=False,backend_override=None):
    out=Path(output).resolve();a=read_amendment(out);require_approval(out,a);verify_copy(out,a)
    target=out/'readouts-remaining-v1'
    existing=sealed_read(target/'measurement-plan-v5.json')
    # Reuse v5's immutable preparation to rederive/validate every cut and computation.
    if prepare(out)!=existing:raise ValueError('Measurement plan changed')
    ref=sealed_read(out/'replication-readouts.json')
    if ref['amendment_hash']!=a['artifact_hash'] or ref['measurement_plan_hash']!=existing['artifact_hash']:
        raise ValueError('Replication readout binding changed')
    if not live_qwen and not mock and backend_override is None:
        return dict(planned_readouts=len(existing['computations']),candidate_sequences=existing['ceiling_candidate_sequences'],inference_calls=0,next_stage='STOP')
    execution=target/'execution-v5.json'
    if execution.exists() and sealed_read(execution)['code_revision']!=revision():
        raise ValueError('Measurement Git revision changed; preserve existing execution identity')
    if live_qwen and (mock or backend_override is not None):raise ValueError('Choose one execution mode')
    source=Source(out/'originals',scope='remaining')
    if (live_qwen and source.execution['mode']!='LIVE_LOCAL') or (mock and source.execution['mode']!='MOCK'):
        raise ValueError('Readout execution mode differs from original backend')
    if backend_override is not None and (backend_override.identity!=source.execution['backend']
        or ('MOCK' if backend_override.simulated else 'LIVE_LOCAL')!=source.execution['mode']):
        raise ValueError('Readout backend identity mismatch')
    return v5.measure(target,live_qwen=live_qwen,mock=mock,backend_override=backend_override)


def validate_value(value,row,c):
    if (value['candidate_texts']!={x:' '+x+'\n' for x in 'ABC'} or value['cue_text']!=c['cue_text']
        or set(value['scores'])!=set('ABC') or set(value['normalized'])!=set('ABC')):
        raise ValueError('Candidate sequences or cue changed')
    context=row['input_ids']+row['raw']['tokens'][:c['k']]+value['cue_ids']
    if value['context_ids']!=context or value['context_hash']!=digest(context):raise ValueError('Readout context changed')
    for v in value['scores'].values():
        if (not v['tokens'] or len(v['tokens'])!=len(v['token_logprobs'])
            or not all(math.isfinite(x) and x<=0 for x in v['token_logprobs'])
            or not math.isclose(sum(v['token_logprobs']),v['logprob'],rel_tol=1e-10,abs_tol=1e-10)):
            raise ValueError('Invalid complete candidate likelihood')
    scores={k:v['logprob'] for k,v in value['scores'].items()};top=max(scores.values())
    z=top+math.log(sum(math.exp(v-top) for v in scores.values()));task=row['task']
    if (not math.isclose(value['candidate_log_mass'],z,abs_tol=1e-10)
        or not math.isclose(value['gold_pattern_log_odds'],scores[task['expected']]-scores[task['pattern']],abs_tol=1e-10)
        or value['preferred_class']!=max('ABC',key=scores.get)
        or any(not math.isclose(value['normalized'][k],math.exp(v-z),rel_tol=1e-10,abs_tol=1e-10) for k,v in scores.items())):
        raise ValueError('Derived probabilities or verified-pattern log odds changed')


def read_data(source,folder):
    """Read genuine journal evidence, including partial runs, without resending it."""
    folder=Path(folder);plan=sealed_read(folder/'measurement-plan-v5.json')
    expected=expected_plan(source,folder)
    # Historical readout folders can be relocated; check binding identity and all
    # scientific fields while leaving their original relative path bytes untouched.
    actual={k:v for k,v in plan.items() if k!='artifact_hash'}
    if (binding_identity(actual['source'])!=source.binding
        or any(actual.get(k)!=v for k,v in expected.items() if k!='source')):
        raise ValueError('Readout plan/source/checkpoints changed')
    saved=operation_tree(folder);results={};exec_path=folder/'execution-v5.json'
    execution=sealed_read(exec_path) if exec_path.exists() else None
    identity=dict(protocol=PROTOCOL,plan_hash=source.plan['plan_hash'],source_hash=source.plan['source_hash'],
                  backend_hash=source.execution['backend_hash'],measurement_plan=plan['artifact_hash'])
    if execution and (any(execution.get(k)!=v for k,v in identity.items()) or execution['backend']!=source.execution['backend']
        or execution.get('mode')!=source.execution['mode']):
        raise ValueError('Measurement execution/backend mismatch')
    if set(saved)-{'v5/readout/'+k for k in plan['computations']}:raise ValueError('Unplanned readout operation')
    for key,c in plan['computations'].items():
        op=saved.get('v5/readout/'+key);row=source.rows[c['task_id']]
        if op is None:results[key]=dict(status='unattempted');continue
        if execution is None or any(op.get(k)!=v for k,v in identity.items()):raise ValueError('Readout operation identity changed')
        req=dict(input_ids=row['input_ids'],prefix_ids=row['raw']['tokens'][:c['k']],gold=row['task']['expected'],pattern=row['task']['pattern'],cue_text=c['cue_text'])
        if op['request']!=req:raise ValueError('Readout request/source changed')
        if op['status']=='returned':
            validate_value(op['result'],row,c)
            results[key]=dict(status='returned',world=row['task']['world'],source_row_hash=row['artifact_hash'],value=op['result'])
        else:results[key]=dict(status='unavailable',journal_status=op['status'])
    path=folder/'measurements-v5.json'
    if path.exists():
        data=sealed_read(path)
        if data['plan_hash']!=plan['artifact_hash'] or set(data['results'])!=set(results):raise ValueError('Measurement summary plan changed')
        for key,r in results.items():
            d=data['results'][key]
            if d['status']!=r['status'] or r['status']=='returned' and d!=r:raise ValueError('Measurement summary differs from immutable operations')
    return plan,dict(results=results,plan_hash=plan['artifact_hash'],measurement=source.execution['mode'])
