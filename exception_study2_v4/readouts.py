"""Fresh conditional sequence likelihoods at fixed or frozen original-token cuts."""
from collections import defaultdict
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.backend import readout
from exception_continuation.core import eligible_cuts
from exception_continuation.analysis import clustered
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry, load_backend
from . import PROTOCOL, ESTIMAND
from .source import Source
from .journal import Session, OperationUnavailable

def saved_cut(row,k):
    if k==0 and row['raw']['tokens']:
        return dict(k=0,char_end=0,prefix='',roundtrip_exact=True)
    return next((c for c in row['boundaries'] if c['k']==k and c['roundtrip_exact']),None)

def measure_cut(session,row,k,cues,namespace):
    cut=saved_cut(row,k)
    result=dict(k=k,checkpoint_eligible=cut is not None,conditional_readout_valid=False,
                readout_returned=False,failed_or_unavailable_reason=None,readouts={},cue_failures={})
    if cut is None:
        result['failed_or_unavailable_reason']='no_exact_pre_answer_saved_token_boundary';return result
    ids=row['raw']['tokens'][:k]; backend=session.backend
    if backend.encode(cut.get('prefix',row['raw']['text'][:cut['char_end']]))!=ids:
        result.update(checkpoint_eligible=False,failed_or_unavailable_reason='saved_prefix_roundtrip_failed');return result
    for ci,cue in enumerate(cues):
        req=dict(input_ids=row['input_ids'],prefix_ids=ids,gold=row['task']['expected'],pattern=row['task']['pattern'],cue_text=cue)
        try:
            value=session.operation(f'{namespace}/{k}/cue{ci}',req,lambda req=req:readout(backend,**req),'candidate_readout')
            result['readouts'][str(ci)]=value
        except OperationUnavailable as exc:result['cue_failures'][str(ci)]=str(exc)
    result['readout_returned']=result['conditional_readout_valid']='0' in result['readouts']
    if result['conditional_readout_valid']:result['readout']=result['readouts']['0']
    else:result['failed_or_unavailable_reason']=result['cue_failures'].get('0','primary_readout_unavailable')
    return result

def summarize_fixed(plan,measurements):
    tasks={t['id']:t for t in plan['tasks']};coverage={k:dict(planned=0,checkpoint_eligible=0,readout_returned=0,unavailable_reasons={}) for k in plan['checkpoints']}
    primary=defaultdict(dict);means=defaultdict(lambda:defaultdict(dict));sensitivity=defaultdict(lambda:defaultdict(list));strata=defaultdict(lambda:defaultdict(list))
    for row in measurements['rows']:
        t=tasks[row['task_id']]; cuts={c['k']:c for c in row['cuts']}
        for k,c in cuts.items():
            n=coverage[k];n['planned']+=1;n['checkpoint_eligible']+=c['checkpoint_eligible'];n['readout_returned']+=c['conditional_readout_valid']
            if c['conditional_readout_valid']:
                value=c['readout']['gold_pattern_log_odds'];means[k][t['world']][t['variant']]=value
                for ci,r in c['readouts'].items():
                    if ci!='0':sensitivity[f'cue{ci}/k{k}'][t['world']].append(r['gold_pattern_log_odds']-value)
                strata[f"{row['original_outcome']}/k{k}"][t['world']].append(value)
            else:
                reason=c['failed_or_unavailable_reason'];n['unavailable_reasons'][reason]=n['unavailable_reasons'].get(reason,0)+1
        if all(cuts[k]['conditional_readout_valid'] for k in (0,64)):
            primary[t['world']][t['variant']]=cuts[64]['readout']['gold_pattern_log_odds']-cuts[0]['readout']['gold_pattern_log_odds']
    complete=lambda d:{w:list(v.values()) for w,v in d.items() if set(v)=={0,1}}
    return dict(protocol=PROTOCOL,coverage={str(k):v for k,v in coverage.items()},primary_64_minus_0=clustered(complete(primary)),
        checkpoint_means={str(k):clustered(complete(v)) for k,v in means.items()},cue_sensitivity={k:clustered(v) for k,v in sensitivity.items()},
        by_final_outcome_descriptive={k:clustered(v) for k,v in strata.items()},interpretation=ESTIMAND,
        no_original_suffix_reconstruction_required=True)

def measure_fixed(output,live_qwen=False,mock=False,backend_override=None,clock=None):
    with run_lock(output) as out:
        source=Source(out); target=out/'fixed-v4';telemetry=Telemetry(target/'timing-v4',dict(protocol=PROTOCOL,source_hash=source.hash),clock);status='FAILED'
        try:
            backend=backend_override or load_backend(source.plan,telemetry,live_qwen,mock)
            if digest(backend.identity)!=source.execution['backend_hash']:raise ValueError('Source backend changed')
            session=Session(target,source.plan,backend,telemetry,dict(source_binding=source.hash))
            rows=[]
            for tid,row in source.rows.items():
                cuts=[]
                for k in source.plan['checkpoints']:
                    cues=source.plan['config']['readout_cues'] if k in source.plan['config']['cue_check_checkpoints'] else source.plan['config']['readout_cues'][:1]
                    cuts.append(measure_cut(session,row,k,cues,'v4/fixed/'+tid))
                outcome='correct' if row['score']['correct'] is True else 'wrong' if row['score']['valid'] else 'invalid'
                rows.append(dict(task_id=tid,trajectory_hash=digest(row),original_outcome=outcome,cuts=cuts))
            value=freeze(target/'measurements-v4.json',dict(protocol=PROTOCOL,source_hash=source.hash,rows=rows,measurement='MOCK' if backend.simulated else 'LIVE'))
            freeze(target/'summary-v4.json',dict(measurements_hash=value['artifact_hash'],**summarize_fixed(source.plan,value)))
            status='COMPLETE';return value
        finally:
            telemetry.finish(status)
            from .reporting import timing_report
            timing_report(target)
