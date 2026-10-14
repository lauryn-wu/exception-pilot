"""Read-only v4 coverage, calibration, conditional readouts and measured timing."""
from collections import defaultdict
from pathlib import Path
from statistics import mean
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_continuation.core import final_score
from exception_continuation.validation import calibration_result
from exception_continuation.analysis import clustered
from exception_review.reporting import stats
from . import PROTOCOL,ESTIMAND
from .core import read_plan
from .journal import operations


def selection_report(output):
    out=Path(output);plan=read_plan(out);saved=operations(out);rows=[];unresolved={}
    for task in plan['tasks']:
        op=saved.get('v4/original/'+task['id'])
        if op is None:continue
        if op['plan_hash']!=plan['plan_hash']:raise ValueError('Partial original plan changed')
        if op['status']!='returned':unresolved[task['id']]=op['status'];continue
        raw=op['result'];rows.append(dict(task=task,raw=raw,score=final_score(raw['text'],raw['stopped'],task['expected'])))
    collection=None
    if (out/'collection-v4.json').exists():
        from .source import Source
        collection=Source(out).collection
    groups={}
    for arm in ('direct','visible'):
        group=[r for r in rows if r['task']['arm']==arm];planned=sum(t['arm']==arm for t in plan['tasks'])
        valid=sum(r['score']['valid'] for r in group);correct=sum(r['score']['correct'] is True for r in group)
        groups[arm]=dict(planned=planned,returned=len(group),valid=valid,invalid=len(group)-valid,
            truncated=sum(r['raw']['finish']=='length' for r in group),missing=planned-len(group),correct=correct,wrong=valid-correct,
            correctness_unknown=planned-valid,accuracy_valid=correct/valid if valid else None,
            accuracy_full_plan_bounds=[correct/planned,(correct+planned-valid)/planned])
    pairs={}
    for r in rows:pairs.setdefault((r['task']['world'],r['task']['variant']),{})[r['task']['arm']]=r
    matched=[key for key,p in pairs.items() if set(p)=={'direct','visible'} and p['direct']['score']['correct'] is True and p['visible']['score']['correct'] is False]
    pattern=[key for key in matched if pairs[key]['visible']['score']['answer']==pairs[key]['visible']['task']['pattern']]
    status=sealed_read(out/'technical-status-v4.json')
    result=dict(protocol=PROTOCOL,phase=plan['phase'],plan_hash=plan['plan_hash'],status='COMPLETE' if collection else 'INCOMPLETE',
        returned_originals=len(rows),planned_originals=len(plan['tasks']),by_arm=groups,unresolved_operations=unresolved,
        technical_same_input_passed=status['technical_same_input_passed'],real_model_status=status['real_model_status'],
        measurement=status['measurement'],calibration=calibration_result(plan,collection) if collection else dict(passed=None,status='PENDING_COMPLETE_COLLECTION'),
        matched_reasoning_errors=dict(planned_pairs=len(plan['tasks'])//2,direct_correct_visible_wrong=len(matched),
            matched_pattern_errors=len(pattern),distinct_pattern_error_worlds=len({w for w,v in pattern})),
        behavioral_replication='PENDING' if status['measurement']!='LIVE' or collection is None else 'PASSED' if calibration_result(plan,collection)['passed'] else 'FAILED',
        study_2b_eligibility=dict(status='PENDING_INDEPENDENT_REVIEW',false_missingness_cases=None,distinct_eligible_worlds=None,
            interpretation='Passing calibration does not establish an eligible 2B cohort. See the separate v4 review report.'),
        next_stage='STOP',interpretation=ESTIMAND)
    write_json(out/'selection-report-v4.json',result)
    return result


def summarize_events(plan,data):
    tasks={t['id']:t for t in plan['tasks']};coverage=defaultdict(lambda:dict(planned=0,checkpoint_eligible=0,readout_returned=0,unavailable_reasons={}))
    values=defaultdict(lambda:defaultdict(dict));changes=defaultdict(dict)
    for row in data['rows']:
        t=tasks[row['task_id']];cuts={c['event']:c for c in row['cuts']}
        for name,c in cuts.items():
            n=coverage[name];n['planned']+=1;n['checkpoint_eligible']+=c['checkpoint_eligible'];n['readout_returned']+=c['conditional_readout_valid']
            if c['conditional_readout_valid']:values[name][t['world']][t['variant']]=c['readout']['gold_pattern_log_odds']
            else:
                reason=c['failed_or_unavailable_reason'];n['unavailable_reasons'][reason]=n['unavailable_reasons'].get(reason,0)+1
        if all(cuts.get(n,{}).get('conditional_readout_valid') for n in ('before_statement','after_statement')):
            changes[t['world']][t['variant']]=cuts['after_statement']['readout']['gold_pattern_log_odds']-cuts['before_statement']['readout']['gold_pattern_log_odds']
    complete=lambda d:{w:list(v.values()) for w,v in d.items() if set(v)=={0,1}}
    return dict(protocol=PROTOCOL,secondary=True,coverage=dict(coverage),checkpoint_means={n:clustered(complete(v)) for n,v in values.items()},
        after_minus_before_statement=clustered(complete(changes)),interpretation='Conditional readouts of different text prefixes; not evidence the statement caused an internal-state transition.')


def timing_report(output,event_outputs=None):
    from .workloads import workload
    out=Path(output);records=[sealed_read(p) for p in (out/'timing-v4/events').glob('*.json')]
    invocations=sorted([sealed_read(p) for p in (out/'timing-v4/invocations').glob('*.json')],key=lambda x:x['finished_utc'])
    groups=defaultdict(list)
    for e in records:
        if e.get('status')=='returned' and 'elapsed_seconds' in e:groups[e['stage']+'/'+e['measurement']].append(e['elapsed_seconds'])
    work=workload(output,event_outputs)
    live_means={k.split('/')[0]:mean(v) for k,v in groups.items() if k.endswith('/LIVE') and v}
    def estimates(value):
        if isinstance(value,dict):
            result={k:estimates(v) for k,v in value.items()}
            counts=result.get('counts',{})
            if 'originals' in result:counts.update(result['originals'])
            for stage,c in counts.items():
                measured=live_means.get('candidate_sequence_scoring' if stage=='candidate_sequences' else stage)
                c['remaining_seconds_scenario']=None if measured is None else [n*measured for n in c['remaining_count_scenario']]
                c['timing_status']='NOT_YET_MEASURED_LIVE' if measured is None else 'PROVISIONAL_SERIAL_LIVE'
            return result
        if isinstance(value,list):return [estimates(v) for v in value]
        return value
    result=dict(protocol=PROTOCOL,status=invocations[-1]['status'] if invocations else 'NOT_RUN',
        observations={k:stats(v) for k,v in groups.items()},invocations=invocations,this_invocation=invocations[-1] if invocations else None,
        cache_hits=sum(e.get('status')=='cache_hit' for e in records),failures=sum(e.get('status')=='failed' for e in records),
        completed_generation_input_tokens=sum(e.get('input_tokens') or 0 for e in records if e.get('status')=='returned' and e['stage'] in ('technical_same_input','original_generation','edited_continuation')),
        completed_generated_output_tokens=sum(e.get('output_tokens') or 0 for e in records if e.get('status')=='returned' and e['stage'] in ('technical_same_input','original_generation','edited_continuation')),
        completed_candidate_context_tokens=sum(e.get('input_tokens') or 0 for e in records if e.get('status')=='returned' and e['stage']=='candidate_sequence_scoring'),
        completed_candidate_scored_tokens=sum(e.get('output_tokens') or 0 for e in records if e.get('status')=='returned' and e['stage']=='candidate_sequence_scoring'),
        completed_candidate_forward_tokens=sum((e.get('input_tokens') or 0)+(e.get('output_tokens') or 0) for e in records if e.get('status')=='returned' and e['stage']=='candidate_sequence_scoring'),
        token_accounting='Generation outputs exclude teacher-forced candidate tokens. Candidate forward inputs include context and candidate; counts are token occurrences, not unique text tokens.',
        measured_sequence_calls=sum(e['stage']=='candidate_sequence_scoring' and e.get('status')=='returned' for e in records),
        workload=estimates(work),full_study_live_total_seconds=None,
        setup='Only explicitly measured loader/file verification/transfer spans are included. Downloads are not measured.',
        interpretation='MOCK time is not live performance evidence; unobserved live stages remain unmeasured. Cached operations create no new inference samples.')
    write_json(out/'timing-report-v4.json',result)
    return result
