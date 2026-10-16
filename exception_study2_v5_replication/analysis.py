"""Prespecified world-level summaries; eligibility and longitudinal pairing explicit."""
from collections import Counter,defaultdict
from pathlib import Path
from statistics import mean
from exception_review.artifacts import freeze
from exception_study2_v5.runner import Source
from exception_study2_v5.reporting import clustered,trajectory_report,outcome_group,contrasts
from . import VERSION,ANALYSIS
from .integrity import read_amendment,tree,archive_ref
from .workflow import verify_copy
from .readouts import read_data

CUTS=ANALYSIS['checkpoints']


def grouped(values,planned,eligible=None):
    by_world=defaultdict(list)
    for task,value in values:
        if value is not None:by_world[task['world']].append(value)
    result=clustered(by_world)
    result.update(planned_trajectories=len(planned),planned_worlds=len({t['world'] for t in planned}),
        observed_trajectories=sum(len(v) for v in by_world.values()),observed_per_world={w:len(v) for w,v in by_world.items()},
        missing_trajectories=len(planned)-sum(len(v) for v in by_world.values()),
        eligible_trajectories=eligible,weighting='Mean available matched variants within each world, then equal world weights; incomplete worlds identified by observed_per_world.')
    return result


def preference_events(series,task):
    """Observed temporal order, deduplicated cut aliases; gaps never imply recovery.

    Positive observed events survive other gaps. Absence requires every eligible
    checkpoint returned. Reversal: observed verified then pattern in a continuous
    observed segment; recovery: later verified in that segment. A third class may
    intervene. Also expose literal adjacent verified→pattern transition counts.
    """
    verified=task['expected'];pattern=task['pattern'];seen=False;overridden=False
    reversal=False;recovery=False;previous=None;pairs=0;transitions=0;missing=False
    for value in series:
        if value is None:missing=True;seen=False;overridden=False;previous=None;continue
        cls=value['preferred_class']
        if previous is not None:
            pairs+=1;transitions+=previous==verified and cls==pattern
        if seen and cls==pattern:reversal=True;overridden=True
        if overridden and cls==verified:recovery=True
        seen|=cls==verified;previous=cls
    return dict(reversal=True if reversal else None if missing else False,
        recovery=True if recovery else None if missing else False,
        adjacent_pairs=pairs,adjacent_verified_to_pattern=transitions,missing_eligible_readout=missing)


def behavioral(source):
    groups={};cases=[];obs={}
    for framing in ('original','lookup'):
        groups[framing]={}
        for arm in ('direct','visible'):
            tasks=[t for t in source.tasks if t['framing']==framing and t['arm']==arm]
            rows=[source.rows[t['id']] for t in tasks if t['id'] in source.rows]
            groups[framing][arm]=outcome_group(len(tasks),rows)
        for t in source.tasks:
            if t['framing']!=framing or t['arm']!='visible':continue
            key=t['world']+'/'+str(t['variant'])+'/'+framing
            cases.append(dict(task_id=key,world=t['world'],framing=framing));obs[key]={}
            for arm in ('direct','visible'):
                tid=t['world']+'/v'+str(t['variant'])+'/'+framing+'/'+arm;r=source.rows.get(tid)
                obs[key][arm]=r['score'] if r and r['status']=='returned' else {}
    return dict(by_condition=groups,
        visible_minus_direct={f:contrasts([c for c in cases if c['framing']==f],obs,'visible','direct') for f in ('original','lookup')},
        worlds=len(source.worlds),planned_originals=len(source.tasks),independent_unit='world')


def summarize(source,plan,data):
    lookup={r['task_id']:r for r in plan['rows']};computed=data['results'];cues={};agreement={}
    for cue_index,cue in enumerate(source.plan['config']['readout_cues']):
        framings={}
        for framing in ('original','lookup'):
            tasks=[t for t in source.tasks if t['arm']=='visible' and t['framing']==framing]
            values={};eligibility={};events={};missing_originals=[]
            for task in tasks:
                tid=task['id'];row=source.rows[tid];cuts={c['name']:c for c in lookup[tid]['checkpoints']}
                values[tid]={};eligibility[tid]={};temporal={}
                if row['status']!='returned':missing_originals.append(tid)
                for name in CUTS:
                    cut=cuts.get(name,dict(eligible=False,reason='original_unavailable'))
                    eligibility[tid][name]=dict(eligible=cut['eligible'],reason=cut.get('reason'))
                    value=None
                    if cut['eligible']:
                        key=cut['computations'][cue_index];r=computed.get(key,{})
                        value=r['value'] if r.get('status')=='returned' else None
                        temporal[cut['k']]=value
                    values[tid][name]=value
                events[tid]=preference_events([v for k,v in sorted(temporal.items())],task) if temporal else dict(
                    reversal=None,recovery=None,adjacent_pairs=0,adjacent_verified_to_pattern=0,missing_eligible_readout=True)
            levels={};changes={};deltas=defaultdict(dict);complete=[]
            for task in tasks:
                v=values[task['id']]
                if all(v[n] is not None for n in CUTS):complete.append(task)
                if v['fixed/0'] is not None and v['pre_answer'] is not None:
                    deltas[task['world']][task['variant']]=v['pre_answer']['gold_pattern_log_odds']-v['fixed/0']['gold_pattern_log_odds']
            for name in CUTS:
                pairs=[];xs=[];eligible=0
                for t in tasks:
                    v=values[t['id']];eligible+=eligibility[t['id']][name]['eligible']
                    if v[name] is not None:
                        xs.append((t,v[name]['gold_pattern_log_odds']))
                        if v['fixed/0'] is not None:pairs.append((t,v[name]['gold_pattern_log_odds']-v['fixed/0']['gold_pattern_log_odds']))
                levels[name]=grouped(xs,tasks,eligible)
                levels[name]['eligibility_reasons']=dict(Counter(eligibility[t['id']][name]['reason'] for t in tasks if not eligibility[t['id']][name]['eligible']))
                changes[name]=grouped(pairs,tasks,eligible)
            cohort={name:grouped([(t,values[t['id']][name]['gold_pattern_log_odds']) for t in complete],tasks,len(complete)) for name in CUTS}
            outcome={}
            for label in ('correct','wrong','unknown'):
                selected=[t for t in tasks if source.rows[t['id']]['score']['outcome']==label]
                pairs=[(t,values[t['id']]['pre_answer']['gold_pattern_log_odds']-values[t['id']]['fixed/0']['gold_pattern_log_odds'])
                       for t in selected if values[t['id']]['fixed/0'] is not None and values[t['id']]['pre_answer'] is not None]
                outcome[label]=dict(pre_answer_change=grouped(pairs,selected),
                    reversals=grouped([(t,events[t['id']]['reversal']) for t in selected],selected))
            event_summary={}
            for field in ('reversal','recovery'):
                # Recovery is additionally reported conditional on observed reversal.
                selected=tasks if field=='reversal' else [t for t in tasks if events[t['id']]['reversal'] is True]
                event_summary[field]=dict(world_rate=grouped([(t,events[t['id']][field]) for t in selected],selected),
                    yes=sum(events[t['id']][field] is True for t in selected),no=sum(events[t['id']][field] is False for t in selected),
                    unknown=sum(events[t['id']][field] is None for t in selected))
            event_summary['adjacent_pairs']=sum(v['adjacent_pairs'] for v in events.values())
            event_summary['adjacent_verified_to_pattern']=sum(v['adjacent_verified_to_pattern'] for v in events.values())
            event_summary['per_trajectory']=events
            full={w:list(v.values()) for w,v in deltas.items() if set(v)=={0,1}}
            framings[framing]=dict(primary_pre_answer_minus_initial=dict(estimate=clustered(full),complete_worlds=len(full),
                planned_worlds=len(source.worlds),planned_pairs=len(tasks),complete_pairs=sum(len(x) for x in deltas.values())),
                checkpoint_levels=levels,paired_changes_from_initial=changes,
                complete_checkpoint_cohort=dict(task_ids=[t['id'] for t in complete],levels=cohort),
                preference_events=event_summary,by_final_answer=outcome,unavailable_originals=missing_originals,
                caution='Cross-sectional checkpoint means can use different populations. Paired changes use the same trajectory at initial and current; the complete-checkpoint cohort uses one fixed population.')
        cues[str(cue_index)]=dict(cue=cue,framing=framings)
    for framing in ('original','lookup'):
        tasks=[t for t in source.tasks if t['arm']=='visible' and t['framing']==framing];agreement[framing]={}
        for name in CUTS:
            xs=[];differences=[];eligible=0
            for t in tasks:
                cut=next((c for c in lookup[t['id']]['checkpoints'] if c['name']==name),None)
                if not cut or not cut['eligible']:continue
                eligible+=1;rs=[computed.get(k,{}) for k in cut['computations']]
                if len(rs)!=2 or any(r.get('status')!='returned' for r in rs):continue
                a,b=[r['value'] for r in rs];xs.append((t,a['preferred_class']==b['preferred_class']))
                differences.append((t,b['gold_pattern_log_odds']-a['gold_pattern_log_odds']))
            agreement[framing][name]=dict(agreement=grouped(xs,tasks,eligible),
                disagreements=sum(not v for t,v in xs),paired_cue_log_odds_difference=grouped(differences,tasks,eligible))
    return dict(legacy_v5=trajectory_report(source,plan,data),cues=cues,cue_agreement=agreement,behavioral=behavioral(source),
        planned_readouts=len(plan['computations']),readout_statuses=dict(Counter(r.get('status','unattempted') for r in computed.values())),
        generated_answers=0,independent_unit='world',definition=ANALYSIS)


def analyze(output,pilot_readouts=None):
    out=Path(output).resolve();a=read_amendment(out);verify_copy(out,a)
    remaining=Source(out/'originals',scope='remaining');plan,data=read_data(remaining,out/'readouts-remaining-v1')
    original_pilot=Source(out/a['original_source']['path'],scope='pilot')
    pilot_result=dict(provenance='Previously examined four-world pilot; not untouched validation data.',behavioral=behavioral(original_pilot),readouts='NOT_PROVIDED')
    if pilot_readouts:
        path=Path(pilot_readouts).resolve()
        ref=next((r for r in a['archives'] if (out/r['path']).resolve()==path),None)
        if ref is None or tree(path)!=ref['files']:raise ValueError('Pilot readouts must be frozen as a preserved archive at preparation')
        pp,pd=read_data(original_pilot,path);pilot_result['readouts']=summarize(original_pilot,pp,pd)
    result=dict(version=VERSION,amendment_hash=a['artifact_hash'],post_pilot_amendment=True,
        remaining_56=summarize(remaining,plan,data),examined_pilot_4=pilot_result,pooled_60=None,
        measurement_plan_hash=plan['artifact_hash'],provenance='Prespecified remaining worlds, replication workflow approved after examining the pilot. No Study 2B eligibility claim.',next_stage='STOP')
    # Versioned snapshots permit analysis during an interrupted measurement run
    # without overwriting an earlier partial report.
    from exception_pilot.core import digest
    return freeze(out/'analysis-v1'/(digest(result)+'.json'),result)
