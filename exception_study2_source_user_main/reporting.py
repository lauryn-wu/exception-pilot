"""Frozen descriptive endpoints; cached preferences are a different interface."""
import json
from collections import Counter,defaultdict
from statistics import mean,median
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_study2_source_user_pilot.parser import parse_reply
from exception_study2_source_report_v2.reporting import WorldBootstrap
from . import CUTS,ANALYSIS,INTERPRETATION
from .execution import state


def fraction(n,d):return dict(numerator=n,denominator=d,estimate=n/d if d else None)


def estimate(bootstrap,values):
    result=bootstrap.estimate(values);interval=result['interval_95']
    result['degenerate_interval']=bool(interval is not None and interval[0]==interval[1])
    result['caveat']=ANALYSIS['bootstrap_caveat'] if result['degenerate_interval'] else None
    return result


def category(score):
    if not score['raw_integrity']:return 'metadata_malformed'
    if not score['complete']:return 'incomplete'
    if not score['valid']:return 'invalid_format'
    if score['correct']:return 'correct'
    return 'MISSING' if score['answer']=='MISSING' else 'wrong_label'


def counts(qs,saved):
    c=Counter(state(saved.get(q['id'])) for q in qs)
    return dict(eligible=len(qs),**{s:c[s] for s in ('returned','never_started','failed','ambiguous')},unavailable=len(qs)-c['returned'])


def source_summary(qs,saved,answers,bootstrap):
    observed=[q for q in qs if q['id'] in answers];correct=sum(answers[q['id']]['correct'] for q in observed)
    return dict(**counts(qs,saved),accuracy=fraction(correct,len(observed)),
        accuracy_bootstrap=estimate(bootstrap,[(q['world'],answers[q['id']]['correct']) for q in observed]),
        categories=dict(Counter(category(answers[q['id']]) for q in observed)),
        answers=dict(Counter(str(answers[q['id']]['answer']) for q in observed)),
        confusion=dict(Counter(q['expected']+'/'+(answers[q['id']]['answer'] or category(answers[q['id']])) for q in observed)),
        generation_length_stops=sum(answers[q['id']]['generation_length_stop'] for q in observed),
        eos=sum(answers[q['id']]['eos_observed'] for q in observed),
        denominator='All returned payloads, including wrong labels, valid MISSING, incomplete, invalid format and malformed metadata. Unavailable operations are coverage only.')


def relation(preference,q):
    cls=preference['preferred_class']
    return 'tie' if cls is None else 'verified' if cls==q['expected'] else 'pattern' if cls==q['pattern'] else 'other'


def comparison(qs,answers,cue,interpretation,bootstrap):
    observed=[q for q in qs if q['id'] in answers]
    rel={q['id']:relation(q['legacy'][cue][interpretation],q) for q in qs}
    cross=Counter(rel[q['id']]+'/'+(category(answers[q['id']]) if q['id'] in answers else 'unavailable') for q in qs)
    metrics={}
    for name,selected in (('uniquely_wrong',{'pattern','other'}),('pattern_preference',{'pattern'})):
        eligible=[q for q in qs if rel[q['id']] in selected];returned=[q for q in eligible if q['id'] in answers]
        n=sum(answers[q['id']]['correct'] for q in returned);unavailable=len(eligible)-len(returned)
        metrics[name]=dict(joint_among_all_returned=fraction(n,len(observed)),conditional_among_preference_returned=fraction(n,len(returned)),
            eligible_preference_cases=len(eligible),returned_preference_cases=len(returned),unavailable_relevant_cases=unavailable,
            joint_eligible_lower_bound=fraction(n,len(qs)),joint_eligible_fraction_bounds=[n/len(qs),(n+unavailable)/len(qs)] if qs else None,
            conditional_eligible_fraction_bounds=[n/len(eligible),(n+unavailable)/len(eligible)] if eligible else None,
            joint_bootstrap=estimate(bootstrap,[(q['world'],answers[q['id']]['correct'] and rel[q['id']] in selected) for q in observed]))
    masses=[q['legacy'][cue][interpretation]['abc_mass'] for q in qs]
    return dict(preference_counts=dict(Counter(rel.values())),exact_ties=sum(v=='tie' for v in rel.values()),
        cross_counts=dict(cross),**metrics,
        abc_mass=dict(count=len(masses),mean=mean(masses) if masses else None,median=median(masses) if masses else None,
            minimum=min(masses) if masses else None,maximum=max(masses) if masses else None),
        interpretation=interpretation,
        note='Different elicitation interfaces. Restricted cached preferences are not generated answers or a matched accuracy advantage. Exact ties have no preferred class. Unavailable cases give bounds, not incorrect outcomes.')


def paired(qs,answers,bootstrap):
    by_task=defaultdict(dict)
    for q in qs:by_task[q['task_id']][q['checkpoint']]=q
    result={}
    for left,right in ((0,256),(0,512),(256,512)):
        eligible=[(v[left],v[right]) for v in by_task.values() if left in v and right in v]
        returned=[(a,b) for a,b in eligible if a['id'] in answers and b['id'] in answers]
        transitions=Counter(('correct' if answers[a['id']]['correct'] else 'incorrect')+'->'+('correct' if answers[b['id']]['correct'] else 'incorrect') for a,b in returned)
        delta=sum(int(answers[b['id']]['correct'])-int(answers[a['id']]['correct']) for a,b in returned)
        result[f'{left}->{right}']=dict(eligible_pairs=len(eligible),returned_pairs=len(returned),unavailable_pairs=len(eligible)-len(returned),
            transitions={name:transitions[name] for name in ('correct->incorrect','incorrect->correct','correct->correct','incorrect->incorrect')},
            paired_accuracy_change=fraction(delta,len(returned)),
            paired_accuracy_change_bootstrap=estimate(bootstrap,[(a['world'],int(answers[b['id']]['correct'])-int(answers[a['id']]['correct'])) for a,b in returned]),
            eligible_task_ids=[a['task_id'] for a,b in eligible],returned_task_ids=[a['task_id'] for a,b in returned])
    return result


def report(c,saved,mode,stats):
    p=c.plan;qs=p['queries'];answers={q['id']:parse_reply(saved[q['id']]['result'],q['expected'],c.tokenizer) for q in qs if state(saved.get(q['id']))=='returned'}
    bootstrap=WorldBootstrap(sorted({q['world'] for q in qs}));grouped={str(k):[q for q in qs if q['checkpoint']==k] for k in CUTS}
    summary={k:source_summary(v,saved,answers,bootstrap) for k,v in grouped.items()}
    preferences={k:{cue:dict(cue_text=v[0]['legacy'][cue]['cue_text'],source_response_reused=True,
        first_class_token=comparison(v,answers,cue,'class_token',bootstrap),
        newline_inclusive_sensitivity=comparison(v,answers,cue,'whole_sequence_sensitivity',bootstrap)) for cue in ('0','1')} for k,v in grouped.items()}
    natural={q['task_id']:q['natural_final_answer'] for q in qs}
    rows=[]
    for q in qs:
        rows.append(dict(**{key:q[key] for key in ('id','origin_query_id','origin_query_hash','task_id','world','variant','checkpoint','expected','pattern','target_plate','source_row_hash','parent_rows','boundary','old_context_hash','prefix_hash','bridge_hash','context_hash','role_boundaries','empty_old_assistant_closed','legacy')},
            operation_status=state(saved.get(q['id'])),raw=saved[q['id']]['result'] if q['id'] in answers else None,
            score=answers.get(q['id']),outcome=category(answers[q['id']]) if q['id'] in answers else 'unavailable'))
    finished=[sealed_read(x) for x in sorted((c.out/'invocations').glob('*/finished.json'))]
    unfinished=len(list((c.out/'invocations').glob('*/started.json')))-len(finished)
    events=[sealed_read(x) for x in sorted((c.out/'timing-main/events').glob('*.json'))]
    generated=[e for e in events if e.get('stage')=='source_user_main_generation']
    count=counts(qs,saved)
    return dict(protocol=p['version'],plan_hash=p['artifact_hash'],code_contract=p['code_contract'],measurement_mode=mode,
        live_main_results_obtained=mode=='LIVE_LOCAL' and bool(answers),inventory=p['inventory'],
        prior_evidence=dict(v1_gate='FAILED',v2_gate='FAILED',v2_present_correct=8,v2_missing_correct=0,
            pilot_plan_hash=p['parent_pilot']['plan_hash'],successful_development_pilot=12,pilot_cumulative_loads=1,pilot_cumulative_calls=12,
            new_pilot_generations=0,original_reruns=0,historical_readout_reruns=0,judge_calls=0),
        source=p['source'],current_legacy_provenance=p['source']['legacy'],
        original_v2_legacy_provenance=c.evidence.origin['source']['legacy'],
        analysis=p['analysis'],counts=count,collection_status='COMPLETE' if count['returned']==332 else 'INCOMPLETE',
        checkpoints=summary,paired=paired(qs,answers,bootstrap),cached_preference_comparisons=preferences,
        natural_final_answers=dict(trajectories=len(natural),valid=sum(v.get('valid') is True for v in natural.values()),
            correct=sum(v.get('correct') is True for v in natural.values()),truncated=sum(v.get('truncated') is True for v in natural.values()),
            answers=dict(Counter(str(v.get('answer')) for v in natural.values())),saved_scores=natural,
            note='One saved natural final-answer measure per trajectory; separate from source readouts and cached class preferences.'),
        cases=rows,exclusions=p['exclusions'],this_invocation=stats,
        executable_now=count['never_started'],unresolved_operations=[q['id'] for q in qs if state(saved.get(q['id']))!='returned'],
        cumulative_dispatches=count['returned']+count['failed']+count['ambiguous'],
        cumulative_dispatch_note='Started operation slots, including ambiguous starts; an ambiguous slot is a possible dispatch and is never resent.',
        cumulative_finished_invocation_calls=sum(v['new_generations'] for v in finished),
        cumulative_call_accounting_complete=unfinished==0 and count['ambiguous']==0,
        cumulative_model_loads=sum(v['model_loads'] for v in finished),cumulative_load_accounting_complete=unfinished==0,
        timing=dict(finished_invocations=len(finished),unfinished_invocations=unfinished,generation_events=len(generated),
            returned_generation_seconds=sum(v.get('elapsed_seconds',0) for v in generated if v.get('status')=='returned'),
            note='Finished-invocation load totals are a lower bound if an invocation was interrupted.'),
        backend_hash=p['backend_hash'],backend_requirements=p['backend'],generation_settings=p['generation_settings'],
        interpretation=INTERPRETATION,next_stage='STOP_REVIEW_MAIN')


def human(r):
    lines=['# Fixed source-user main readout','',
        f"Mode: {r['measurement_mode']}; collection: {r['collection_status']}; next: STOP_REVIEW_MAIN.",
        'Prior development pilot: 12/12 exact correct EOS replies. V1/V2 remain FAILED. No new pilot calls.',
        'Coverage: '+json.dumps(r['counts']), 'This invocation: '+json.dumps(r['this_invocation']),
        'Started operation slots: '+str(r['cumulative_dispatches'])+'; calls in finished invocations: '+str(r['cumulative_finished_invocation_calls'])+'; model loads: '+str(r['cumulative_model_loads']),
        r['cumulative_dispatch_note'],
        'Timing: '+json.dumps(r['timing']), 'Current legacy provenance: '+json.dumps(r['current_legacy_provenance']),'',r['interpretation'],'',
        '## Source recovery by checkpoint','', '| k | Correct / returned | Eligible | Unavailable | Categories |', '|---|---|---|---|---|']
    for k,s in r['checkpoints'].items():
        f=s['accuracy'];lines.append(f"| {k} | {f['numerator']}/{f['denominator']} | {s['eligible']} | {s['unavailable']} | {json.dumps(s['categories'])} |")
        lines.append('Bootstrap: '+json.dumps(s['accuracy_bootstrap']))
    lines+=['','## Within-trajectory paired changes','']
    for key,p in r['paired'].items():lines.append(key+': '+json.dumps({k:v for k,v in p.items() if not k.endswith('_task_ids')}))
    lines+=['','## Cached preference diagnostics (different interfaces)','',
        'First-class-token scores/A/B/C mass are primary. Newline-inclusive scores are sensitivity only; no unlike probability-magnitude comparison.',
        'Both cues use the same single source response. Exact ties are neither uniquely correct nor uniquely wrong.']
    for k,cues in r['cached_preference_comparisons'].items():
        for cue,value in cues.items():lines.append(f'Checkpoint {k}, cue {cue}: '+json.dumps(value))
    lines+=['','## Saved natural final answers (112 unique trajectories)','',json.dumps({k:v for k,v in r['natural_final_answers'].items() if k!='saved_scores'}),
        '', '## Preserved exclusions','',json.dumps(r['exclusions']), '', '## All source replies','']
    for row in r['cases']:
        lines.append(json.dumps(row,ensure_ascii=False))
    lines+=['','STOP_REVIEW_MAIN. No automatic intervention, query variant or later experiment.','']
    return '\n'.join(lines)


def save_report(c,value):
    import os
    from tempfile import NamedTemporaryFile
    write_json(c.out/'report.json',value)
    with NamedTemporaryFile('w',dir=c.out,delete=False,suffix='.tmp') as f:
        f.write(human(value));f.flush();os.fsync(f.fileno());name=f.name
    os.replace(name,c.out/'report.md');return value
