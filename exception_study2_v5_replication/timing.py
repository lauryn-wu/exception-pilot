"""Read measured pilot telemetry only; extrapolations never count as benchmarks."""
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from exception_continuation.runner import sealed_read
from exception_study2_v5.runner import Source
from .integrity import operation_tree


def estimate(source_path,pilot_readouts=None,hourly_rate=None):
    if hourly_rate is not None and (hourly_rate<0 or not __import__('math').isfinite(hourly_rate)):raise ValueError('Finite nonnegative hourly rate required')
    source=Source(source_path,scope='pilot');ops=operation_tree(source.root);groups=defaultdict(list);seen=set();loads=[]
    for p in sorted(source.root.glob('timing-v5/events/*.json')):
        e=sealed_read(p)
        if e.get('measurement')!='LIVE' or e.get('status')!='returned':continue
        if e['stage']=='backend_initialization_total':loads.append(e['elapsed_seconds'])
        if e['stage']!='original_generation':continue
        op_id=e['operation_id'];op=ops.get(op_id);tid=op_id.removeprefix('v5/original/')
        if tid not in source.rows or not op or op['status']!='returned' or op_id in seen:raise ValueError('Pilot timing not uniquely source-bound')
        r=source.rows[tid]
        if e['output_tokens']!=len(r['raw']['tokens']) or e['input_tokens']!=len(r['input_ids']):raise ValueError('Pilot timing token counts differ')
        seen.add(op_id);groups[r['task']['arm']].append(e)
    stats={arm:dict(calls=len(es),seconds=sum(x['elapsed_seconds'] for x in es),
        output_tokens=sum(x['output_tokens'] for x in es),input_tokens=sum(x['input_tokens'] for x in es)) for arm,es in groups.items()}
    generation=sum(v['seconds']*14 for v in stats.values()) if all(stats.get(a,{}).get('calls')==16 for a in ('direct','visible')) else None
    readout=None;scoring=[];scoring_counts=Counter()
    if pilot_readouts:
        from .readouts import read_data
        plan,data=read_data(source,pilot_readouts)
        for p in sorted(Path(pilot_readouts).glob('timing-v5/events/*.json')):
            e=sealed_read(p)
            if e.get('measurement')=='LIVE' and e.get('status')=='returned' and e.get('stage')=='candidate_sequence_scoring':
                key=e.get('operation_id','').removeprefix('v5/readout/')
                if key not in data['results'] or data['results'][key]['status']!='returned':raise ValueError('Scoring timing is not source-bound')
                scoring.append(e);scoring_counts[key]+=1
        readout=dict(planned=len(plan['computations']),returned=sum(r['status']=='returned' for r in data['results'].values()),
            timed_candidate_sequences=len(scoring),timed_seconds=sum(x['elapsed_seconds'] for x in scoring))
    # Full scoring timing must contain all three candidate sequences per operation.
    measurement=None
    if readout and readout['returned']==readout['planned'] and readout['timed_candidate_sequences']==3*readout['returned'] and all(scoring_counts[k]==3 for k in plan['computations']):
        measurement=14*readout['timed_seconds']
    load=mean(loads) if loads else None
    total=generation+measurement+2*load if all(x is not None for x in (generation,measurement,load)) else None
    return dict(hardware=source.execution['backend'].get('hardware'),mode=source.execution['mode'],
        measured_pilot_originals=stats,measured_loader_seconds=loads,pilot_readouts=readout,
        remaining_originals=448,visible_trajectories=224,output_token_ceiling=917504,
        maximum_readouts=2688,maximum_candidate_sequences=8064,generated_measurement_answers=0,edited_continuations=0,
        pilot_matched_generation_seconds=generation,pilot_matched_scoring_seconds=measurement,
        mean_loader_seconds=load,total_two_invocation_seconds=total,
        hourly_rate_assumption=hourly_rate,generation_only_cost=None if hourly_rate is None or generation is None else hourly_rate*generation/3600,
        total_cost=None if hourly_rate is None or total is None else hourly_rate*total/3600,
        limitations='Four examined worlds are a small timing sample. 14x same-condition pilot work is an extrapolation, not a bound. Missing readout timing stays unknown; no fabricated measurement benchmark. Same exact original backend required, batch one BF16 eager Transformers, no quantization, no new technical inference. Storage and idle time extra.')
