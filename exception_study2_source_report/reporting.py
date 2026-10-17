"""Offline source accuracy and class-token preferences, with world-clustered pairs."""
from collections import Counter,defaultdict
from statistics import mean,median
from pathlib import Path
import random
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from . import CUTS,BOOTSTRAP_SEED,BOOTSTRAP_SAMPLES
from .execution import state,parsed,gate,worklist


class WorldBootstrap:
    def __init__(self,worlds):
        self.worlds=list(worlds);rng=random.Random(BOOTSTRAP_SEED)
        self.draws=[rng.choices(self.worlds,k=len(self.worlds)) for _ in range(BOOTSTRAP_SAMPLES)]

    def estimate(self,values):
        groups=defaultdict(list)
        for world,value in values:groups[world].append(float(value))
        sums={w:sum(v) for w,v in groups.items()};counts={w:len(v) for w,v in groups.items()}
        observed=sum(counts.values());est=sum(sums.values())/observed if observed else None
        boot=[]
        if observed:
            for draw in self.draws:
                n=sum(counts.get(w,0) for w in draw)
                if n:boot.append(sum(sums.get(w,0) for w in draw)/n)
        boot.sort()
        interval=[boot[int(.025*len(boot))],boot[min(len(boot)-1,int(.975*len(boot)))]] if boot else None
        return dict(estimate=est,observations=observed,observed_worlds=len(groups),planned_worlds=len(self.worlds),
            interval_95=interval,bootstrap_nonempty_draws=len(boot),unit='world',seed=BOOTSTRAP_SEED,
            replicates=BOOTSTRAP_SAMPLES,method='Ratio of summed outcomes to available observations in resampled world blocks; common draws across cues/checkpoints.')


def relation(preference,q):
    c=preference['preferred_class']
    return 'tie' if c is None else 'verified' if c==q['expected'] else 'pattern' if c==q['pattern'] else 'other'


def joint(qs,answers,cue,interpretation):
    observed=[];counts=Counter();confirmed_wrong=confirmed_pattern=0;wrong_total=pattern_total=wrong_observed=pattern_observed=0
    unavail_wrong=unavail_pattern=0
    for q in qs:
        p=q['legacy'][cue][interpretation];r=relation(p,q);a=answers.get(q['id'])
        wrong=r in ('pattern','other');pattern=r=='pattern'
        wrong_total+=wrong;pattern_total+=pattern
        category='unavailable' if a is None else 'correct' if a['correct'] else a['category']
        counts[r+'/'+category]+=1
        if a is not None:
            observed.append(q);wrong_observed+=wrong;pattern_observed+=pattern
            confirmed_wrong+=bool(a['correct'] and wrong);confirmed_pattern+=bool(a['correct'] and pattern)
        else:unavail_wrong+=wrong;unavail_pattern+=pattern
    def fractions(n,total,measured,unavailable):
        return dict(confirmed=n,all_eligible=len(qs),observed_confirmations_per_eligible=n/len(qs) if qs else None,
            eligible_fraction_bounds=[n/len(qs),(n+unavailable)/len(qs)] if qs else None,
            among_returned=n/len(observed) if observed else None,returned_denominator=len(observed),
            conditional_eligible_preference_cases=total,conditional_returned_preference_cases=measured,
            conditional_fraction_among_returned=n/measured if measured else None,
            unavailable_relevant_cases=unavailable,note='Unavailable source measurements are not incorrect. Eligible fractions are lower bounds until relevant source returns are complete; exact preference ties excluded from wrong/pattern cases.')
    return dict(counts=dict(counts),source_correct_preference_wrong=fractions(confirmed_wrong,wrong_total,wrong_observed,unavail_wrong),
        source_correct_preference_pattern=fractions(confirmed_pattern,pattern_total,pattern_observed,unavail_pattern))


def summary(qs,answers,cue,bootstrap):
    returned=[q for q in qs if q['id'] in answers];confusion=Counter();categories=Counter()
    for q in returned:
        a=answers[q['id']];confusion[q['expected']+'/'+(a['answer'] or 'INVALID_'+a['category'])]+=1;categories[a['category']]+=1
    preferences=Counter(relation(q['legacy'][cue]['class_token'],q) for q in qs)
    mass=[q['legacy'][cue]['class_token']['abc_mass'] for q in qs]
    return dict(eligible=len(qs),returned=len(returned),unavailable=len(qs)-len(returned),
        coverage=len(returned)/len(qs) if qs else None,
        source_accuracy=bootstrap.estimate([(q['world'],answers[q['id']]['correct']) for q in returned]),
        source_accuracy_denominator='All returned replies, including invalid, verbose, MISSING and truncated. Unavailable operations excluded.',
        source_confusion=dict(confusion),source_return_categories=dict(categories),class_token_preference=dict(preferences),
        class_token_abc_mass=dict(count=len(mass),mean=mean(mass) if mass else None,median=median(mass) if mass else None,
            minimum=min(mass) if mass else None,maximum=max(mass) if mass else None),
        class_token_joint=joint(qs,answers,cue,'class_token'),
        newline_inclusive_sensitivity=joint(qs,answers,cue,'whole_sequence_sensitivity'))


def report(context,saved,stats,mode):
    plan=context.plan;answers=parsed(context,saved);g=gate(context,saved,answers);work=worklist(context,saved,answers)
    worlds=sorted({q['world'] for q in plan['main']});bootstrap=WorldBootstrap(worlds)
    grouped={str(k):[q for q in plan['main'] if q['checkpoint']==k] for k in CUTS}
    checkpoints={k:{cue:summary(qs,answers,cue,bootstrap) for cue in ('0','1')} for k,qs in grouped.items()}
    rows=[];sensitivity={}
    for q in plan['main']:
        a=answers.get(q['id']);rows.append(dict(operation_id=q['id'],task_id=q['task_id'],source_row_hash=q['source_row_hash'],
            world=q['world'],variant=q['variant'],checkpoint=q['checkpoint'],expected=q['expected'],pattern=q['pattern'],
            context_hash=q['context_hash'],source_report=a,operation_status=state(saved.get(q['id'])),
            natural_final_answer=q['natural_final_answer'],legacy=q['legacy']))
    for k,qs in grouped.items():
        pairs=[(q['legacy']['0']['class_token'],q['legacy']['1']['class_token']) for q in qs]
        sensitivity[k]=dict(contexts=len(qs),unique_preference_agreements=sum(a['preferred_class'] is not None and a['preferred_class']==b['preferred_class'] for a,b in pairs),
            unique_preference_disagreements=sum(a['preferred_class'] is not None and b['preferred_class'] is not None and a['preferred_class']!=b['preferred_class'] for a,b in pairs),
            contexts_with_ties=sum(a['preferred_class'] is None or b['preferred_class'] is None for a,b in pairs),
            source_query_repeated_for_second_cue=False)
    by_task=defaultdict(dict)
    for q in plan['main']:by_task[q['task_id']][q['checkpoint']]=q
    paired={}
    for left,right in ((0,256),(0,512),(256,512)):
        eligible=[(v[left],v[right]) for v in by_task.values() if left in v and right in v]
        observed=[(a,b) for a,b in eligible if a['id'] in answers and b['id'] in answers]
        key=f'{left}->{right}'
        paired[key]=dict(eligible_trajectories=len(eligible),returned_pairs=len(observed),unavailable_pairs=len(eligible)-len(observed),
            eligible_task_ids=[a['task_id'] for a,b in eligible],returned_task_ids=[a['task_id'] for a,b in observed],
            source_accuracy_change=bootstrap.estimate([(a['world'],int(answers[b['id']]['correct'])-int(answers[a['id']]['correct'])) for a,b in observed]),
            per_cue={})
        for cue in ('0','1'):
            def indicator(q):return int(answers[q['id']]['correct'] and relation(q['legacy'][cue]['class_token'],q) in ('pattern','other'))
            paired[key]['per_cue'][cue]=dict(source_correct_wrong_preference_change=bootstrap.estimate([(a['world'],indicator(b)-indicator(a)) for a,b in observed]))
    calibration=[dict(operation_id=q['id'],kind=q['kind'],world=q['world'],expected=q['expected'],
        operation_status=state(saved.get(q['id'])),source_report=answers.get(q['id'])) for q in plan['calibration']]
    def counts(qs):
        c=Counter(state(saved.get(q['id'])) for q in qs)
        return dict(planned=len(qs),**{s:c[s] for s in ('returned','never_started','failed','ambiguous')})
    finished=[sealed_read(p) for p in sorted((context.out/'invocations').glob('*/finished.json'))]
    events=[sealed_read(p) for p in sorted((context.out/'timing-source-report/events').glob('*.json'))]
    generation=[e for e in events if e.get('stage')=='source_report_generation' and e.get('status')=='returned']
    unfinished=len(list((context.out/'invocations').glob('*/started.json')))-len(finished)
    backend=plan['backend'];model_dir=backend.get('config',{}).get('model_dir')
    requirements=dict(model_dir=model_dir,model_directory_present=bool(model_dir and Path(model_dir).is_dir()),
        missing_model_files=[n for n in backend.get('files',{}) if not model_dir or not (Path(model_dir)/n).is_file()],
        required_hardware=backend['hardware'],required_device=backend.get('device'),
        required_versions={k:backend.get(k) for k in ('python','torch','transformers','tokenizers','cuda','cudnn')},
        model_weight_bytes_checked=False,cuda_initialized=False,
        note='Offline metadata and file-presence inspection only. Original model bytes and full backend identity are checked by the existing loader only when there is executable live work.')
    natural_rows={q['task_id']:q['natural_final_answer'] for q in plan['main']}
    natural=dict(trajectories=len(natural_rows),answers=dict(Counter(str(v.get('answer')) for v in natural_rows.values())),
        correct=sum(v.get('correct') is True for v in natural_rows.values()),
        valid=sum(v.get('valid') is True for v in natural_rows.values()),
        truncated=sum(v.get('truncated') is True for v in natural_rows.values()),
        note='Unique original trajectories, not checkpoint queries. These are saved natural final answers, not new source-report results or conditional class preferences.')
    return dict(protocol=plan['version'],plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],
        measurement_mode=mode,live_results_obtained=mode=='LIVE_LOCAL' and bool(answers),inventory=plan['inventory'],
        source=plan['source'],legacy_provenance_mode=plan['source']['legacy']['legacy_provenance_mode'],
        backend_hash=plan['backend_hash'],required_hardware=plan['backend']['hardware'],model_profile=plan['tokenizer']['profile'],
        backend_requirements=requirements,natural_final_answers=natural,
        calibration_gate=g,calibration=calibration,counts=dict(calibration=counts(plan['calibration']),main=counts(plan['main']),all=counts(list(context.queries.values()))),
        executable_now=len(work['executable']),main_conditional_on_calibration=len(work['main_after_gate']),
        this_invocation=stats,cumulative_backend_loads=sum(v['model_loads'] for v in finished),
        cumulative_backend_loads_complete=unfinished==0,
        cumulative_load_note='Finished-invocation sum; a lower bound if unfinished invocations exist.',
        timing=dict(recorded_finished_invocations=len(finished),returned_generation_events=len(generation),
            returned_generation_seconds=sum(e.get('elapsed_seconds',0) for e in generation),
            generated_output_tokens=sum(e.get('output_tokens') or 0 for e in generation),
            unfinished_invocations=unfinished),
        main_checkpoint_summaries=checkpoints,paired_changes=paired,cue_sensitivity=sensitivity,main_contexts=rows,
        exclusions=plan['exclusions'],analysis_contract=plan['analysis'],natural_answer_note='Saved natural final answer is separate from checkpoint conditional class preference.',
        interpretation='Correct source reporting establishes recovery under this explicit same-assistant query. The model may reread the table. It does not establish uninterrupted retention, deliberate overriding, an endogenous causal mechanism, or novelty. Source accuracy and legacy probabilities are different measurements.',
        next_stage='STOP')


def human(value):
    import json
    def compact(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True)
    def rate(x):return 'unavailable' if x is None else f'{x:.6g}'
    lines=['# Source-report measurement v1','',
        f"Mode: {value['measurement_mode']}; calibration: {value['calibration_gate']['status']}; legacy evidence: {value['legacy_provenance_mode']}.",
        f"Plan: `{value['plan_hash']}`. Backend: `{value['backend_hash']}`.",
        f"Source hashes: {compact(value['source'])}",
        f"Inventory: {compact(value['inventory'])}",
        f"Operations: {compact(value['counts'])}",
        f"This invocation: {compact(value['this_invocation'])}",
        f"Cumulative backend loads: {value['cumulative_backend_loads']} (complete accounting: {value['cumulative_backend_loads_complete']}). {value['cumulative_load_note']}",
        f"Timing: {compact(value['timing'])}",
        f"Backend requirements: {compact(value['backend_requirements'])}",
        '', '## Calibration (pilot worlds only)', '',
        '| World | Control | Expected | Operation | Reply category | Correct |',
        '|---|---|---|---|---|---|']
    for c in value['calibration']:
        a=c['source_report']
        lines.append(f"| {c['world']} | {c['kind']} | {c['expected']} | {c['operation_status']} | {a['category'] if a else 'unavailable'} | {a['correct'] if a else 'unavailable'} |")
    lines+=['', '## Main results', '',
        '| Prefix | Cue | Returned / eligible | Correct / returned | MISSING | Truncated | ABC mass mean |',
        '|---|---|---:|---:|---:|---:|---:|']
    for k,items in value['main_checkpoint_summaries'].items():
        for cue,s in items.items():
            n=s['returned'];correct=round(s['source_accuracy']['estimate']*n) if n else 0
            lines.append(f"| {k} | {cue} | {n}/{s['eligible']} | {correct}/{n} | {s['source_return_categories'].get('MISSING',0)} | {s['source_return_categories'].get('truncated',0)} | {rate(s['class_token_abc_mass']['mean'])} |")
    lines+=['', 'Unavailable measurements are excluded from accuracy and reported as coverage; invalid/truncated returned replies count as incorrect.',
        'Both legacy cues reuse the same single source reply. Preferences use class-token log probabilities; newline-inclusive values are sensitivity only.',
        '', '## Joint outcomes', '',
        'Each fraction is confirmed source-correct / denominator. Eligible fractions are lower bounds while relevant source results are unavailable.', '',
        '| Prefix | Cue | Wrong preference: all eligible | Wrong preference: returned conditional | Pattern: all eligible | Pattern: returned conditional |',
        '|---|---|---:|---:|---:|---:|']
    for k,items in value['main_checkpoint_summaries'].items():
        for cue,s in items.items():
            a=s['class_token_joint']['source_correct_preference_wrong'];b=s['class_token_joint']['source_correct_preference_pattern']
            lines.append(f"| {k} | {cue} | {a['confirmed']}/{a['all_eligible']} | {a['confirmed']}/{a['conditional_returned_preference_cases']} | {b['confirmed']}/{b['all_eligible']} | {b['confirmed']}/{b['conditional_returned_preference_cases']} |")
    lines+=['', 'Zero denominators mean unavailable, not zero accuracy. Exact preference ties are separate. Detailed confusion, preference and joint counts:', '']
    for k,items in value['main_checkpoint_summaries'].items():
        for cue,s in items.items():
            lines.append(f"- Prefix {k}, cue {cue}: confusion={compact(s['source_confusion'])}; categories={compact(s['source_return_categories'])}; preference={compact(s['class_token_preference'])}; joint={compact(s['class_token_joint']['counts'])}; source accuracy 95% interval={compact(s['source_accuracy']['interval_95'])}.")
    lines+=['', '## Paired changes', '',
        'Identical eligible trajectories at both cuts; both replies must be returned. Common world-block bootstrap draws preserve variants, checkpoints and cues.', '',
        '| Cuts | Returned / eligible pairs | Source accuracy change | 95% interval |', '|---|---:|---:|---|']
    for name,p in value['paired_changes'].items():
        lines.append(f"| {name} | {p['returned_pairs']}/{p['eligible_trajectories']} | {rate(p['source_accuracy_change']['estimate'])} | {compact(p['source_accuracy_change']['interval_95'])} |")
        for cue,s in p['per_cue'].items():
            lines.append(f"| {name}, cue {cue}: source-correct/wrong-preference change | {p['returned_pairs']}/{p['eligible_trajectories']} | {rate(s['source_correct_wrong_preference_change']['estimate'])} | {compact(s['source_correct_wrong_preference_change']['interval_95'])} |")
    lines+=['',f"Cue sensitivity: {compact(value['cue_sensitivity'])}",
        f"Saved natural final answers (separate): {compact(value['natural_final_answers'])}",
        '', '## Excluded contexts', '']
    lines += [f"- {x['task_id']}, fixed/{x['checkpoint']}: {x['reason']}." for x in value['exclusions']]
    lines+=['',value['interpretation'],'',
        'See report.json for every source context, exact denominators/bounds, complete ABC mass statistics, and labeled newline-inclusive sensitivity.',
        'STOP. No original generations, old readout reruns, judges or Study 2B are invoked.','']
    return '\n'.join(lines)


def save_report(context,value):
    write_json(context.out/'report.json',value)
    # Human output is derived and replaceable; immutable model operations are authoritative.
    from tempfile import NamedTemporaryFile
    import os
    with NamedTemporaryFile('w',dir=context.out,delete=False,prefix='report-',suffix='.tmp') as f:
        f.write(human(value));f.flush();os.fsync(f.fileno());name=f.name
    os.replace(name,context.out/'report.md')
    return value
