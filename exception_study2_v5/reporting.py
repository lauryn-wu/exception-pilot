"""World-grouped effects, fixed denominators, unknown bounds, independent contrasts."""
from collections import Counter, defaultdict
from statistics import mean
from pathlib import Path
from exception_pilot.core import rng_for
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from . import PROTOCOL, ESTIMAND
from .core import CALIBRATION, COHORT_MIN_WORLDS
from .runner import Source


def clustered(values, confidence=.95):
    means={w:mean(v) for w,v in values.items() if v}
    if not means:return dict(estimate=None,worlds=0,interval=None,confidence=confidence)
    rng=rng_for(PROTOCOL,'bootstrap',981723);xs=list(means.values());n=10000
    boot=sorted(sum(rng.choices(xs,k=len(xs)))/len(xs) for _ in range(n));tail=(1-confidence)/2
    ci=[boot[int(n*tail)],boot[min(n-1,int(n*(1-tail))-1)]]
    return dict(estimate=mean(xs),worlds=len(xs),interval=ci,confidence=confidence,
                world_values=means,degenerate_interval=ci[0]==ci[1],independent_unit='world',bootstrap_samples=n)

def contrasts(cases, observations, left, right, field='correct', confidence=.95):
    by_world=defaultdict(list)
    for c in cases:by_world[c['world']].append(c['task_id'])
    complete={};lower={};upper={};known=0
    for world,ids in by_world.items():
        ds=[];lo=[];hi=[]
        for tid in ids:
            arms=observations.get(tid,{})
            a=arms.get(left,{}).get(field);b=arms.get(right,{}).get(field)
            if a is not None and b is not None:ds.append(float(a)-float(b));known+=1
            if field in ('correct','strict_correct'):
                lo.append((float(a) if a is not None else 0)-(float(b) if b is not None else 1))
                hi.append((float(a) if a is not None else 1)-(float(b) if b is not None else 0))
        if len(ds)==len(ids):complete[world]=ds
        if lo:lower[world]=mean(lo);upper[world]=mean(hi)
    return dict(effect=clustered(complete,confidence),frozen_cases=len(cases),eligible_worlds=len(by_world),
                cases_per_world={w:len(ids) for w,ids in by_world.items()},known_pairs=known,
                complete_world_cases=sum(len(v) for v in complete.values()),
                full_cohort_bounds=[mean(lower.values()),mean(upper.values())] if lower else None,
                denominator='All frozen cases averaged within independent world; point estimate uses complete worlds only')

def outcome_group(planned,rows):
    valid=sum(r['score']['valid'] for r in rows if r['status']=='returned')
    correct=sum(r['score']['correct'] is True for r in rows if r['status']=='returned')
    strict=sum(r['score']['strict_format'] for r in rows if r['status']=='returned')
    return dict(planned=planned,returned=sum(r['raw'] is not None for r in rows),valid=valid,
                correct=correct,wrong=valid-correct,strict_format=strict,
                pattern_wrong=sum(r["score"]["correct"] is False and r["score"]["answer"]==r["task"]["pattern"] for r in rows if r["status"]=="returned"),
                truncated=sum(r['raw'] is not None and r['raw'].get('finish')=='length' for r in rows),
                missing=planned-len(rows),invalid_or_unavailable=len(rows)-valid,
                unknown=planned-valid,accuracy_valid=correct/valid if valid else None,
                accuracy_bounds=[correct/planned,(correct+planned-valid)/planned] if planned else None)

def behavioral_report(output):
    source=Source(output,complete=False);plan=source.plan;groups={};pairs=defaultdict(dict)
    for framing in ('original','lookup'):
        groups[framing]={}
        for arm in ('direct','visible'):
            rows=[r for r in source.rows.values() if r['task']['framing']==framing and r['task']['arm']==arm]
            groups[framing][arm]=outcome_group(sum(t['framing']==framing and t['arm']==arm for t in plan['tasks']),rows)
    all_pairs=[]
    for task in plan['tasks']:
        key=task['world']+'/'+str(task['variant'])+'/'+task['framing']
        row=source.rows.get(task['id']);pairs[key][task['arm']]=row
        if task['arm']=='visible':all_pairs.append(dict(task_id=key,world=task['world'],framing=task['framing']))
    obs={};matched=[];pattern=[]
    for key,rows in pairs.items():
        obs[key]={arm:(row['score'] if row and row['status']=='returned' else {}) for arm,row in rows.items()}
        if obs[key].get('direct',{}).get('correct') is True and obs[key].get('visible',{}).get('correct') is False:
            matched.append(key)
            if obs[key]['visible']['answer']==rows['visible']['task']['pattern']:pattern.append(key)
    effects={f:{field:contrasts([c for c in all_pairs if c['framing']==f],obs,'visible','direct',field) for field in ('correct','strict_correct')} for f in ('original','lookup')}
    interaction={}
    for w in plan['worlds']:
        ds=[]
        for variant in (0,1):
            values=[]
            for framing in ('lookup','original'):
                p=obs[w['id']+'/'+str(variant)+'/'+framing]
                a=p.get('visible',{}).get('correct');b=p.get('direct',{}).get('correct')
                if a is not None and b is not None:values.append(int(a)-int(b))
            if len(values)==2:ds.append(values[0]-values[1])
        if len(ds)==2:interaction[w['id']]=ds
    primary_pattern=[p for p in pattern if p.endswith('/original')]
    error_worlds={p.rsplit('/',2)[0] for p in primary_pattern}
    complete=len(source.rows)==len(plan['tasks'])
    passed=complete and groups['original']['direct']['correct']>=CALIBRATION['min_direct_correct'] and len(primary_pattern)>=CALIBRATION['min_matched_pattern_errors'] and len(error_worlds)>=CALIBRATION['min_error_worlds']
    result=dict(protocol=PROTOCOL,phase=plan['phase'],source=source.binding,measurement=source.execution['mode'],
        status='COMPLETE' if complete else 'INCOMPLETE',by_condition=groups,visible_minus_direct=effects,
        lookup_minus_original_reasoning_effect=clustered(interaction),
        matched_errors=len(matched),matched_pattern_errors=len(pattern),original_matched_pattern_errors=len(primary_pattern),
        original_pattern_error_worlds=len(error_worlds),
        calibration=dict(passed=passed if plan['phase']=='selection' else None,
                         thresholds=CALIBRATION if plan['phase']=='selection' else None,
                         status='NOT_APPLICABLE_CONFIRMATION' if plan['phase']=='confirmation' else
                         'PENDING_COMPLETE_COLLECTION' if not complete else 'PASSED' if passed else 'FAILED'),
        behavioral_replication='PENDING_REAL_MODEL' if source.execution['mode']=='MOCK' else 'DESCRIPTIVE_V5_DATA',
        annotation_eligibility='SEPARATE_REVIEW_REQUIRED',next_stage='STOP',interpretation=ESTIMAND)
    write_json(Path(output)/'behavioral-summary-v5.json',result);return result

def annotation_report(source,manifest):
    families={};events={};both=[];strata=defaultdict(Counter)
    for event in ('acknowledgment','erasure','conflict','override','miscopy'):
        events[event]=dict(Counter(c['events'][event]['status'] for c in manifest['cases'].values()))
    for family,event in (('M','erasure'),('O','override')):
        cases=[tid for tid,c in manifest['cases'].items() if c['events'][event]['status']=='present']
        worlds={source.rows[tid]['task']['world'] for tid in cases}
        clean=[tid for tid in cases if manifest['cases'][tid]['override_stratum']=='clean']
        clean_worlds={source.rows[tid]['task']['world'] for tid in clean}
        families[family]=dict(cases=len(cases),worlds=len(worlds),clean_cases=len(clean) if family=='O' else None,
            clean_worlds=len(clean_worlds) if family=='O' else None,planned_visible=len(manifest['cases']),
            subtypes=dict(Counter(manifest['cases'][tid]['events'][event]['subtype'] for tid in cases)),
            coverage_status='SUFFICIENT_MINIMUM_COVERAGE' if len(clean_worlds if family=='O' else worlds)>=COHORT_MIN_WORLDS else 'INSUFFICIENT_COVERAGE')
        for tid in cases:
            row=source.rows[tid];strata[family][row['score']['outcome']]+=1
    for tid,c in manifest['cases'].items():
        if all(c['events'][e]['status']=='present' for e in ('erasure','override')):both.append(tid)
    return dict(events=events,families=families,both_family_cases=len(both),both_family_worlds=len({source.rows[t]['task']['world'] for t in both}),
                outcome_strata={k:dict(v) for k,v in strata.items()},disagreements=len(manifest['disagreements']),
                override_strata=dict(Counter(c['override_stratum'] for c in manifest['cases'].values() if c['override_stratum'])),
                interpretation='Observational semantic annotations; negatives, uncertainties and correct-answer cases retained')

def trajectory_report(source,plan,data):
    primary=defaultdict(dict);secondary=defaultdict(lambda:defaultdict(dict));coverage=defaultdict(Counter);sensitivity=defaultdict(lambda:defaultdict(list));outcome=defaultdict(lambda:defaultdict(list))
    for item in plan['rows']:
        tid=item['task_id'];row=source.rows[tid];task=row['task'];values={}
        for cut in item['checkpoints']:
            key=cut['name'];coverage[key]['planned']+=1;coverage[key]['eligible']+=cut['eligible']
            vals=[]
            for computation in cut.get('computations',[]):
                r=data['results'].get(computation,{})
                vals.append(r['value']['gold_pattern_log_odds'] if r.get('status')=='returned' else None)
            if vals and vals[0] is not None:
                values[key]=vals[0];coverage[key]['returned']+=1
                if len(vals)>1 and vals[1] is not None:sensitivity[key][task['world']].append(vals[1]-vals[0])
            else:coverage[key][cut.get('reason') or 'readout_unavailable']+=1
        if 'fixed/0' in values and 'pre_answer' in values:
            delta=values['pre_answer']-values['fixed/0'];primary[task['framing']][(task['world'],task['variant'])]=delta
            outcome[row['score']['outcome']][task['world']].append(delta)
        for key,val in values.items():secondary['checkpoint/'+task['framing']+'/'+key][task['world']][task['variant']]=val
        for event in ('acknowledgment','erasure','conflict','override'):
            if all(event+'/'+s in values for s in ('before','after')):
                secondary['event_delta/'+task['framing']+'/'+event][task['world']][task['variant']]=values[event+'/after']-values[event+'/before']
    def complete(d):return {w:list(v.values()) for w,v in d.items() if set(v)=={0,1}}
    longitudinal={}
    for f in ('original','lookup'):
        d=defaultdict(dict)
        for (w,v),x in primary[f].items():d[w][v]=x
        longitudinal[f]=dict(estimate=clustered(complete(d)),complete_pairs=len(primary[f]),planned_pairs=len(source.plan['worlds'])*2,
                             complete_worlds=len(complete(d)))
    return dict(primary_original_pre_answer_minus_initial=longitudinal['original'],lookup_secondary=longitudinal['lookup'],
        coverage={k:dict(v) for k,v in coverage.items()},secondary={k:clustered(complete(v)) for k,v in secondary.items()},
        cue_sensitivity={k:clustered(v) for k,v in sensitivity.items()},outcome_strata={k:clustered(v) for k,v in outcome.items()},
        unique_readouts=len(plan['computations']),candidate_sequence_ceiling=3*len(plan['computations']),generated_answers=0,interpretation=ESTIMAND)

def intervention_report(manifest,data):
    cases=manifest['cases'];obs={};coverage={a:Counter() for a in ('unchanged','meaning_control','value_blind','explicit_value')}
    for r in data['rows']:
        obs[r['task_id']]={}
        for arm,v in r['arms'].items():
            score=v.get('score',{}) if v['status']=='returned' else {}
            obs[r['task_id']][arm]={**score,'preference':v.get('readouts',{}).get('0',{}).get('gold_pattern_log_odds')}
            coverage[arm][v['status']]+=1;coverage[arm]['valid']+=score.get('valid',False)
            coverage[arm]['truncated']+=v.get('raw',{}).get('finish')=='length'
            coverage[arm]['preference_returned']+='0' in v.get('readouts',{})
    contrasts_list=[('primary','value_blind','meaning_control'),('blind_minus_unchanged','value_blind','unchanged'),
                    ('meaning_minus_unchanged','meaning_control','unchanged'),('explicit_minus_unchanged','explicit_value','unchanged'),
                    ('explicit_minus_blind','explicit_value','value_blind')]
    def summarize(cohort):
        return {name:{field:contrasts(cohort,obs,a,b,field,.975 if name=='primary' else .95)
                for field in ('correct','strict_correct','preference')} for name,a,b in contrasts_list}
    primary_cases=[c for c in cases if c['override_stratum']=='clean'] if manifest['family']=='O' else cases
    strata={}
    for label in sorted({c['initial_outcome'] for c in cases}):strata['outcome/'+label]=summarize([c for c in cases if c['initial_outcome']==label])
    for label in ('original','lookup'):strata['framing/'+label]=summarize([c for c in cases if c['framing']==label])
    if manifest['family']=='O':
        for label in ('clean','mixed','unknown_erasure_history'):strata['override/'+label]=summarize([c for c in cases if c['override_stratum']==label])
    strata['initial_agreement_only']=summarize([c for c in primary_cases if c['initial_agreement']])
    return dict(family=manifest['family'],frozen_cases=len(cases),excluded=manifest['excluded'],
        coverage={a:{**dict(v),'planned':len(cases),'missing':len(cases)-sum(v[s] for s in ('returned','unavailable','invalid_return','unattempted'))} for a,v in coverage.items()},
        primary_cohort='clean_overrides' if manifest['family']=='O' else 'all_eligible_erasure',
        status='INSUFFICIENT_COVERAGE' if len({c['world'] for c in primary_cases})<COHORT_MIN_WORLDS else 'DESCRIPTIVE_ESTIMATES_AVAILABLE',
        comparisons=summarize(primary_cases),strata=strata,
        multiplicity='97.5% intervals for each family primary accuracy contrast (Bonferroni for two); preference secondary. No automatic significance claim.',
        interpretation=ESTIMAND)

def timing_report(output):
    events=[sealed_read(p) for p in Path(output).rglob('timing-v5/events/*.json')]
    groups=defaultdict(list);tokens=defaultdict(Counter)
    for e in events:
        if e.get('status')!='returned' or 'elapsed_seconds' not in e:continue
        key=e['measurement']+'/'+e['stage'];groups[key].append(e['elapsed_seconds'])
        tokens[key]['input_occurrences']+=e.get('input_tokens') or 0;tokens[key]['output_occurrences']+=e.get('output_tokens') or 0
    return dict(observed={k:dict(calls=len(v),seconds=sum(v),mean_seconds=mean(v),tokens=dict(tokens[k])) for k,v in groups.items()},
                live_full_runtime=None,interpretation='MOCK timing is not live performance. Candidate outputs are teacher-forced tokens, not generated answers.')
