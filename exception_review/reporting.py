"""Coverage, world-weighted effects, and measured-versus-unmeasured work reports."""
from collections import Counter,defaultdict
from pathlib import Path
from statistics import mean,median
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_continuation.core import read_plan
from .artifacts import Review


def stats(values):
    values=[v for v in values if isinstance(v,(int,float))]
    return dict(observations=len(values),mean_seconds=mean(values) if values else None,median_seconds=median(values) if values else None,range_seconds=[min(values),max(values)] if values else None,status='MEASURED' if values else 'UNMEASURED')


def comparisons(cases,results,initial_only=False):
    if initial_only: cases=[c for c in cases if c['initial_agreement']]
    byid={r['task_id']:r for r in results}; worlds=defaultdict(list)
    for case in cases: worlds[case['world']].append(case)
    names=[('primary_availability_minus_meaning','availability_repair','meaning_control'),('availability_minus_unchanged','availability_repair','unchanged'),('meaning_minus_unchanged','meaning_control','unchanged'),('value_minus_unchanged','value_repair','unchanged')]
    from exception_continuation.analysis import clustered
    answer={}
    for name,left,right in names:
        complete={}; bounds={}; accuracy_worlds={}; readout_worlds={}
        for world,items in worlds.items():
            differences=[]; intervals=[]; all_known=True; readout_differences=[]
            for case in items:
                row=byid.get(case['task_id'],{}); valid=row.get('validation',{}).get('passed') is True and row.get('unchanged_replay_passed') is True
                values=[]
                for arm in (left,right):
                    score=row.get('arms',{}).get(arm,{}).get('score',{})
                    value=int(score['correct']) if valid and score.get('valid') is True and type(score.get('correct')) is bool else None
                    values.append(value)
                if valid:
                    readouts=[row.get('arms',{}).get(arm,{}).get('readout',{}).get('gold_pattern_log_odds') for arm in (left,right)]
                    if all(isinstance(v,(int,float)) for v in readouts): readout_differences.append(readouts[0]-readouts[1])
                a,b=values
                intervals.append(((0 if a is None else a)-(1 if b is None else b),(1 if a is None else a)-(0 if b is None else b)))
                if a is None or b is None: all_known=False
                else: differences.append(a-b)
            bounds[world]=[mean(x[i] for x in intervals) for i in (0,1)]
            if all_known:
                complete[world]=mean(differences); accuracy_worlds[world]=differences
            if len(readout_differences)==len(items): readout_worlds[world]=readout_differences
        answer[name]=dict(accuracy=clustered(accuracy_worlds),readout=clustered(readout_worlds),complete_accuracy_cases=sum(len(v) for v in accuracy_worlds.values()),estimate=mean(complete.values()) if complete else None,complete_worlds=len(complete),planned_worlds=len(worlds),planned_cases=len(cases),world_means=complete,unknown_bounds=[mean(b[i] for b in bounds.values()) for i in (0,1)] if bounds else None,world_bounds=bounds,status='NO_ELIGIBLE_CASES' if not cases else 'NO_COMPLETE_WORLDS' if not complete else 'ESTIMATED',aggregation='mean of within-world paired means; all planned cases required per contrast')
    return answer


def entries(review):
    result=[]
    for path in sorted((review.root/'judge-operations').glob('*/planned.json')):
        record=sealed_read(path)
        for state in ('returned','failed','started'):
            q=path.parent/(state+'.json')
            if q.exists(): record=sealed_read(q); break
        result.append(record)
    return result


def remaining_judge_counts(review, attempted):
    """Future logical call ranges from frozen cases plus known terminal branches."""
    from .decisions import resolve
    from .boundaries import statement_boundaries
    roles=('initial','adjudicate','draft','verify','revise','reverify')
    counts={role:[0,0] for role in roles}
    slots={(e['identity']['task_id'],e['identity']['role'],e['identity']['judge']) for e in attempted}
    for tid,row in review.source.rows.items():
        votes={j:review.read_case(tid,'detect-'+j)['vote'] if review.case_path(tid,'detect-'+j).exists() else None for j in ('J1','J2','J3')}
        resolution=resolve(votes)
        for j in ('J1','J2'):
            if (tid,'initial',j) not in slots: counts['initial']=[x+1 for x in counts['initial']]
        if resolution['state']!='TERMINAL' and (tid,'adjudicate','J3') not in slots:
            counts['adjudicate'][1]+=1
            counts['adjudicate'][0]+=resolution['resolution_route']=='waiting_adjudication'
        if resolution['state']=='TERMINAL':
            if resolution['decision']!='present': continue
            if not statement_boundaries(row,resolution['span'])['after_statement']['eligible']: continue
        if review.case_path(tid,'edit-result').exists(): continue
        drafts={v:review.read_case(tid,'draft-'+str(v)) if review.case_path(tid,'draft-'+str(v)).exists() else None for v in (0,1)}
        verifiers={v:review.read_case(tid,'verify-'+str(v)) if review.case_path(tid,'verify-'+str(v)).exists() else None for v in (0,1)}
        if drafts[0] is not None and not drafts[0]['usable']: continue
        if verifiers[0] is not None and (not verifiers[0]['usable'] or verifiers[0].get('response',{}).get('source_assertion_concern') is not None or verifiers[0].get('checks',{}).get('passed')): continue
        known_positive=resolution['state']=='TERMINAL'
        for role in roles[2:]:
            if any(t==tid and r==role for t,r,j in slots): continue
            if role=='verify' and drafts[0] is not None and not drafts[0]['mechanical']['passed']: continue
            if role=='reverify' and drafts[1] is not None and (not drafts[1]['usable'] or not drafts[1]['mechanical']['passed']): continue
            definite=(role=='draft' and known_positive or role=='verify' and drafts[0] is not None and drafts[0]['mechanical']['passed'] or role=='revise' and (verifiers[0] is not None or drafts[0] is not None and not drafts[0]['mechanical']['passed']) or role=='reverify' and drafts[1] is not None and drafts[1]['usable'] and drafts[1]['mechanical']['passed'])
            counts[role][1]+=1; counts[role][0]+=bool(definite)
    return counts


def timing(review,plan,case_states):
    all_entries=entries(review); attempted=[e for e in all_entries if e['state']!='planned']; groups=defaultdict(list)
    for e in attempted:
        key='/'.join([e['identity']['role'],e['identity']['judge_config']['provider'],str(e['identity']['judge_config']['model']),e['measurement']])
        groups[key] # Include failures as a group with zero completed observations.
        if e['state']=='returned' and e['parsed']['valid'] and e.get('provider_seconds') is not None: groups[key].append(e['provider_seconds'])
    observations={k:stats(v) for k,v in groups.items()}
    counts=Counter(e['identity']['role'] for e in attempted); n=len(review.source.rows)
    ceilings={'initial':2*n,'adjudicate':n,'draft':n,'verify':n,'revise':n,'reverify':n}
    measurements={}; scenarios={}; ranges=remaining_judge_counts(review,attempted)
    for role,ceiling in ceilings.items():
        values=[e['provider_seconds'] for e in attempted if e['identity']['role']==role and e['state']=='returned' and e['parsed']['valid'] and e.get('provider_seconds') is not None and e['measurement']=='LIVE']
        measurements[role]=stats(values)
        minimum,remaining=ranges[role]
        scenarios[role]=dict(attempted=counts[role],planned_maximum=ceiling,remaining_range=[minimum,remaining],remaining_seconds_range=None if not values else [minimum*mean(values),remaining*mean(values)],timing_status='MEASURED_LIVE' if values else 'NOT_YET_MEASURED',routing_caveat='Conditional judge/model routing; pooled serial role mean is provisional')
    invocation_files=sorted((review.root/'invocations').glob('*.json'),key=lambda p:p.stat().st_mtime_ns)
    invocations=[sealed_read(p) for p in invocation_files]
    actual=[e.get('accounting',{}) for e in attempted]
    sampled=[e for e in attempted if e['identity']['task_id'] in plan['case_ids']]
    stage_denominators={'adjudicate':'both initial votes terminal and not initially agreed','draft':'accepted positive with valid after cut','verify':'usable mechanically passing initial draft','revise':'initial editable bundle failed/uncertain semantic or mechanical checks','reverify':'usable mechanically passing revision'}
    branches={role:dict(cases_reached=len({e['identity']['task_id'] for e in sampled if e['identity']['role']==role}),declared_case_denominator=len(plan['case_ids']),terminal_decision_denominator=sum(v!='PENDING_DETECTION' for v in case_states.values()),eligibility_definition=denom) for role,denom in stage_denominators.items()}
    known_charge=sum(a.get('estimated_usd') or 0 for a in actual); unknown=[e for e in attempted if e.get('accounting',{}).get('estimated_usd') is None]
    return dict(concurrency=1,source_case_count=n,scope=plan['scope'],declared_cases=len(plan['case_ids']),maximum_logical_calls=7*n,pilot_ceiling=7*len(plan['case_ids']),cumulative=dict(attempted=len(attempted),returned=sum(e['state']=='returned' for e in attempted),failures=sum(e['state'] in ('failed','started') for e in attempted),invalid_returned=sum(e['state']=='returned' and not e['parsed']['valid'] for e in attempted),cache_hits=sum(i['cached'] for i in invocations),provider_elapsed_seconds=sum(e.get('provider_seconds') or 0 for e in attempted),input_tokens=sum(a.get('input_tokens') or 0 for a in actual),output_tokens=sum(a.get('output_tokens') or 0 for a in actual),billed_reasoning_tokens_reported=sum(a.get('reasoning_tokens') or 0 for a in actual),known_usage_estimated_usd=known_charge,unreconciled_attempts=len(unknown),unreconciled_reservations_usd=sum(e.get('reservation_usd',0) for e in unknown)),this_invocation=invocations[-1] if invocations else None,by_operation_model_measurement=observations,live_role_observations=measurements,remaining_work_scenarios=scenarios,branching=branches,branching_interpretation='Provisional reached-stage frequencies, not eligibility prevalence; budget pauses censor branches. No outcome-based sampling.',remaining_serial_upper_scenario_seconds=sum((s['remaining_seconds_range'] or [0,0])[1] for s in scenarios.values()) if all(s['remaining_seconds_range'] is not None or s['remaining_range'][1]==0 for s in scenarios.values()) else None,remaining_total_status='NOT_YET_MEASURED' if any(s['remaining_range'][1] and s['remaining_seconds_range'] is None for s in scenarios.values()) else 'PROVISIONAL_SERIAL_SCENARIO',billing_note='Configured rate estimates, not a provider billing guarantee; reported output totals already include reasoning. Ambiguous calls may have charges without usage.',setup='Separate from provider latency; this invocation reports local/stage/wait times',rate_table={j:v['rates'] for j,v in review.policy['config']['judges'].items()})


def write_report(path,value,title):
    path=Path(path); write_json(path.with_suffix('.json'),value)
    lines=['# '+title,'','Status: **'+str(value.get('status','UNKNOWN'))+'**. Mock timings are not live performance evidence.','']
    if 'terminal_state_partition' in value:
        lines += ['## Coverage','','| Disjoint case state | Count |','|---|---:|']
        lines += ['| '+k+' | '+str(v)+' |' for k,v in value['terminal_state_partition'].items()]
        lines += ['',f"Accepted intervention cases: {value['accepted_intervention_cases']}; worlds: {value['accepted_worlds']}. Full source cases: {value['full_source_cases']}; declared scope: {value['planned_scope_cases']}.",'','Judge quality: **UNVALIDATED**. Diagnostic reasons can overlap.','']
    coverage=value.get('intervention_coverage')
    if coverage:
        fields=('planned','attempted','returned','valid','invalid','truncated','missing','unassessed','replay_excluded')
        lines += ['## Intervention arm coverage','','Validity is answer syntax. Replay exclusions overlap these counts; unknown outcomes are not wrong answers.','', '| Arm | '+' | '.join(fields)+' |', '|---|'+'---:|'*len(fields)]
        for arm,counts in coverage['per_arm'].items(): lines.append('| '+arm+' | '+' | '.join(str(counts[k]) for k in fields)+' |')
        lines.append('')
    timing=value.get('timing',value)
    observations=timing.get('by_operation_model_measurement',timing.get('observations',{}))
    lines += ['## Completed timing observations','','| Operation / model / measurement | N | Mean seconds | Median | Range |','|---|---:|---:|---:|---|']
    for name,obs in observations.items():
        lines.append('| '+name+' | '+str(obs['observations'])+' | '+str(obs['mean_seconds'])+' | '+str(obs['median_seconds'])+' | '+str(obs['range_seconds'])+' |')
    remaining=timing.get('remaining_work_scenarios',timing.get('remaining_work',{}))
    lines += ['','## Remaining work','','Serial scenarios only. Unobserved stages remain **NOT YET MEASURED**; they are never zero-duration estimates.','', '| Operation | Remaining count scenario | Estimated seconds | Status |','|---|---|---|---|']
    for name,entry in remaining.items():
        lines.append('| '+name+' | '+str(entry.get('remaining_range',entry.get('remaining_count_scenario')))+' | '+str(entry.get('remaining_seconds_range',entry.get('seconds_scenario')))+' | '+str(entry.get('timing_status',entry.get('status')))+' |')
    lines += ['','The machine-readable JSON includes source identities, individual case states, all denominators, unknown-outcome bounds, rate assumptions, invocation versus cumulative timing, and billing limitations.','','## Complete audit data','','```json',__import__('json').dumps(value,indent=2,ensure_ascii=False),'```','']
    path.with_suffix('.md').write_text('\n'.join(lines))
    return value


def report(output,scope='full'):
    review=Review(output); plan=review.plan(scope); states={}; diagnostics=Counter(); details=[]
    for tid in plan['case_ids']:
        p=review.case_path(tid,'resolution'); resolution=review.read_case(tid,'resolution') if p.exists() else None
        state='PENDING_DETECTION'
        for j in ('J1','J2','J3'):
            q=review.case_path(tid,'detect-'+j)
            if q.exists():
                vote=review.read_case(tid,'detect-'+j)['vote']
                diagnostics['judge_failure']+=not vote['request_valid']
                diagnostics['quote_alignment_failure']+=vote['quote_alignment']=='FAILED'
        if resolution:
            decision=resolution['decision']; diagnostics['initially_agreed']+=resolution['initial_agreement']; diagnostics['adjudicated']+=not resolution['initial_agreement']
            if decision=='absent': state='ACCEPTED_NEGATIVE'
            elif decision=='unresolved': state='UNRESOLVED'
            else:
                from .boundaries import statement_boundaries
                cuts=statement_boundaries(review.source.rows[tid],resolution['span'])
                for name,cut in cuts.items(): diagnostics[name+'_boundary_failure']+=not cut['eligible']
                if not cuts['after_statement']['eligible']: state='PRESENT_AFTER_BOUNDARY_FAILED'
                else:
                    state='PENDING_EDITS'; q=review.case_path(tid,'edit-result')
                    if q.exists():
                        edit=review.read_case(tid,'edit-result')
                        if edit['state']=='EXCLUDED': state='EDIT_EXCLUDED'; diagnostics['edit_failure']+=1
                        else:
                            state='PENDING_TOKEN_CHECK'; token=review.case_path(tid,'token-check')
                            if token.exists():
                                state='READY_TO_FREEZE' if review.read_case(tid,'token-check')['passed'] else 'EDIT_TOKEN_EXCLUDED'
                                diagnostics['edit_token_failure']+=state=='EDIT_TOKEN_EXCLUDED'
        states[tid]=state; details.append(dict(task_id=tid,state=state,resolution=resolution))
    edit_path=review.root/'manifests'/(scope+'-edits.json'); cases=[]; data={'rows':[]}
    if edit_path.exists():
        frozen=sealed_read(edit_path)
        if any(frozen[k]!=v for k,v in review.binding().items()): raise ValueError('Stale frozen edits')
        cases=frozen['cases']
        for case in cases: states[case['task_id']]='FROZEN_ACCEPTED_COHORT'
        p=review.root/'interventions'/scope/'interventions.json'
        if p.exists():
            data=sealed_read(p)
            if data['edit_plan_hash']!=frozen['artifact_hash'] or data['source_hash']!=review.source.hash: raise ValueError('Stale interventions')
        for row in data['rows']:
            diagnostics['replay_failure']+=not row.get('unchanged_replay_passed',False)
            diagnostics['invalid_qwen_answer']+=sum(o.get('score',{}).get('valid') is False for o in row.get('arms',{}).values())
    from .coverage import intervention_coverage
    coverage=intervention_coverage(cases,data['rows'],review.root/'interventions'/scope,review.source.hash,frozen['artifact_hash']) if edit_path.exists() else None
    for d in details: d['state']=states[d['task_id']]
    pending=sum(s.startswith('PENDING') or s=='READY_TO_FREEZE' for s in states.values())
    result=dict(source_hash=review.source.hash,policy_hash=review.policy['policy_hash'],scope=scope,status='INCOMPLETE' if pending else 'COMPLETE',synthetic=plan['synthetic'],planned_scope_cases=len(states),full_source_cases=len(review.source.rows),unreviewed_outside_scope=len(review.source.rows)-len(states),terminal_state_partition=dict(Counter(states.values())),diagnostic_counts_may_overlap=dict(diagnostics),cases=details,intervention_coverage=coverage,accepted_intervention_cases=len(cases),accepted_worlds=len({c['world'] for c in cases}),cohort_status='FROZEN' if edit_path.exists() else 'NOT_FROZEN',primary_and_secondary=comparisons(cases,data['rows']) if edit_path.exists() else None,initially_agreed_only=comparisons(cases,data['rows'],True) if edit_path.exists() else None,judge_annotation_quality='UNVALIDATED',qwen_replay_behavior='PENDING' if plan['synthetic'] else 'See original technical and per-case validations; automated-review implementation does not establish behavior',interpretation='Conditional frozen accepted cohort only; no all-error prevalence or effect claim',timing=timing(review,plan,states))
    return write_report(review.root/'reports'/(scope+'-report'),result,'Study 2 automated review and timing')


def fixed_timing_report(output):
    from .workloads import fixed_workload
    out=Path(output); work=fixed_workload(out)
    records=[sealed_read(p) for p in (out/'timing-sidecar/fixed-2a/events').glob('*.json')]
    groups=defaultdict(list)
    for entry in records:
        if entry.get('status')=='returned': groups[entry['stage']+'/'+entry['measurement']].append(entry['elapsed_seconds'])
    remaining={}
    for stage,counts in work['counts'].items():
        lookup='candidate_sequence_scoring' if stage.startswith('candidate_') else stage
        values=groups.get(lookup+'/LIVE',[])
        remaining[stage]=dict(counts,status='PROVISIONAL_SERIAL' if values else 'NOT_YET_MEASURED',
                             seconds_scenario=[n*mean(values) for n in counts['remaining_count_scenario']] if values else None)
    invocations=sorted([sealed_read(p) for p in (out/'timing-sidecar/fixed-2a/invocations').glob('*.json')],key=lambda i:i['finished_utc'])
    return write_report(out/'timing-sidecar/fixed-2a-report',dict(status='COMPLETE' if work.get('completed') else 'INCOMPLETE',
        workload=work,remaining_work=remaining,observations={k:stats(v) for k,v in groups.items()},
        actual_timed_calls={stage:dict(attempted=sum(e.get('stage')==stage and e.get('status') in ('returned','failed') for e in records),
                                      returned=sum(e.get('stage')==stage and e.get('status')=='returned' for e in records),
                                      failed=sum(e.get('stage')==stage and e.get('status')=='failed' for e in records))
                            for stage in ('unchanged_replay','candidate_sequence_scoring')},
        cache_hits=sum(e.get('status')=='cache_hit' for e in records),
        failures=sum(e.get('status')=='failed' for e in records),
        input_tokens=sum(e.get('input_tokens') or 0 for e in records if e.get('status')=='returned'),
        output_tokens=sum(e.get('output_tokens') or 0 for e in records if e.get('status')=='returned'),
        this_invocation=invocations[-1] if invocations else None,invocations=invocations,
        hardware_software_precision=[e['identity'] for e in records if e.get('stage')=='backend_identity'],
        full_study_total=None,note='Delegates the unchanged fixed-2A algorithm. Legacy caches reduce remaining work even without measured durations; unmeasured time is not zero.'),
        'Fixed-2A replay and candidate-sequence timing')


def qwen_timing_report(output,event_outputs=None):
    from .workloads import aggregate_events,records_at
    out=Path(output); plan=read_plan(out); records=records_at(out); groups=defaultdict(list)
    for e in records:
        if e.get('status')=='returned': groups[e['stage']+'/'+e['measurement']].append(e['elapsed_seconds'])
    ops=[sealed_read(p) for p in (out/'operations').glob('*.json')]
    original=[o for o in ops if o['id'].startswith('trajectory/') and o['status']=='returned']
    n=len(plan['tasks']); visible=sum(t['arm']=='visible' for t in plan['tasks'])
    fixed=fixed_timing_report(out); events=aggregate_events(out,event_outputs)
    event_groups=defaultdict(list)
    for requested in events['plans']:
        for e in records_at(requested['output']):
            if e.get('status')=='returned': event_groups[e['stage']+'/'+e['measurement']].append(e['elapsed_seconds'])
    scenarios={'original_generation':[n-len(original),n-len(original)],
               'intervention_reference':[0,visible],'intervention_replay':[0,visible],
               'edited_continuation':[0,4*visible],'candidate_sequence_scoring_interventions':[0,12*visible]}
    remaining={}
    for stage,counts in scenarios.items():
        lookup='candidate_sequence_scoring' if stage.startswith('candidate_') else 'unchanged_replay' if stage=='intervention_replay' else stage
        samples=groups.get(lookup+'/LIVE',[])
        remaining[stage]=dict(remaining_count_scenario=counts,status='PROVISIONAL_SERIAL' if samples else 'NOT_YET_MEASURED',seconds_scenario=[c*mean(samples) for c in counts] if samples else None)
    remaining.update(fixed['remaining_work'])
    for stage,counts in events['counts'].items():
        lookup='candidate_sequence_scoring' if stage.startswith('candidate_') else stage
        samples=event_groups.get(lookup+'/LIVE',[])
        remaining[stage]=dict(counts,status='PROVISIONAL_SERIAL' if samples else 'NOT_YET_MEASURED',seconds_scenario=[c*mean(samples) for c in counts['remaining_count_scenario']] if samples else None)
    invocations=sorted([sealed_read(p) for p in (out/'timing-sidecar/invocations').glob('*.json')],key=lambda x:x['finished_utc'])
    result=dict(status='COMPLETE' if (out/'collection.json').exists() else 'INCOMPLETE',planned_originals=n,returned_originals=len(original),behavioral_calibration_available=(out/'collection.json').exists(),technical_validation=sealed_read(out/'validation.json')['passed'] if (out/'validation.json').exists() else 'PENDING',timing_version='study2-timing-sidecar-v1',observations={k:stats(v) for k,v in groups.items()},this_invocation=invocations[-1] if invocations else None,cumulative_input_tokens=sum(e.get('input_tokens') or 0 for e in records if e.get('status')=='returned'),cumulative_output_tokens=sum(e.get('output_tokens') or 0 for e in records if e.get('status')=='returned'),cache_hits=sum(e.get('status')=='cache_hit' for e in records),failures=sum(e.get('status')=='failed' for e in records),remaining_work=remaining,fixed_2a=fixed,event_workloads=events,event_observations={k:stats(v) for k,v in event_groups.items()},setup={s:stats(groups.get(s+'/LIVE',[])) for s in ('download_setup','file_verification','tokenizer_initialization','model_loading_cpu','device_transfer','backend_initialization_total')},hardware_software_precision=[e['identity'] for e in records if e.get('stage')=='backend_identity'],full_study_total=None,note='Collection cumulative timing excludes nested fixed-2A and requested event timing, which are reported separately. Unknown stages remain unmeasured. Two event directories require independent references, not twice the whole runtime. Interventions remain conditional scenarios; use their model-timing-report for frozen cohort counts. No stages are automatically launched.')
    return write_report(out/'timing-sidecar/report',result,'Qwen timing (no automatic next stage)')


def model_timing_report(output):
    """Frozen event/intervention plan counts, including measured scoring/replay stages."""
    out=Path(output)
    event=(out/'event-plan.json').exists()
    reference=sealed_read(out/'event-plan.json' if event else out/'edit-plan-reference.json')
    from .artifacts import Source
    source=Source(reference['source_path'])
    if reference['source_hash']!=source.hash: raise ValueError('Model timing source changed')
    plans=reference['rows'] if event else reference['manifest']['cases']
    expected={}
    if event:
        for row in plans:
            tid=row['task_id']; ks={c['k'] for c in row['cuts'] if c['eligible']}
            if ks: expected[f'event/{tid}/reference']='event_reference'
            for k in ks:
                expected[f'event/{tid}/replay/{k}']='event_validation'
                expected[f'event/{tid}/readout/{k}']='candidate_readout'
    else:
        for case in plans:
            tid=case['task_id']
            expected[f'branch-validation/{tid}/reference']='intervention_reference'
            expected[f'branch-validation/{tid}/replay']='unchanged_replay'
            for arm in case['texts']:
                expected[f'edit/{tid}/{arm}/continuation']='edited_continuation'
                expected[f'edit/{tid}/{arm}/readout']='candidate_readout'
    ops={o['id']:o for o in [sealed_read(p) for p in (out/'model-operations').glob('*.json')]}
    observations=defaultdict(list); records=[sealed_read(p) for p in (out/'timing-sidecar/events').glob('*.json')]
    for entry in records:
        if entry.get('status')=='returned': observations[entry['stage']+'/'+entry['measurement']].append(entry['elapsed_seconds'])
    ceilings=Counter(expected.values()); unattempted=Counter(stage for op,stage in expected.items() if op not in ops)
    ceilings['candidate_sequence_scoring']=3*ceilings.pop('candidate_readout',0)
    unattempted['candidate_sequence_scoring']=3*unattempted.pop('candidate_readout',0)
    remaining={}
    for stage,ceiling in ceilings.items():
        values=observations.get(stage+'/LIVE',[])
        remaining[stage]=dict(planned_maximum=ceiling,remaining_count_scenario=[0,unattempted[stage]],seconds_scenario=[0,unattempted[stage]*mean(values)] if values else None,status='PROVISIONAL_SERIAL' if values else 'NOT_YET_MEASURED')
    invocations=sorted([sealed_read(p) for p in (out/'timing-sidecar/invocations').glob('*.json')],key=lambda x:x['finished_utc'])
    result=dict(source_hash=source.hash,status='SEE_PER_OPERATION_GATES',kind='events' if event else 'interventions',frozen_plan_cases=len(plans),planned_operation_ceiling=len(expected),observations={k:stats(v) for k,v in observations.items()},remaining_work=remaining,this_invocation=invocations[-1] if invocations else None,attempted=len(ops),returned=sum(o['status']=='returned' for o in ops.values()),terminal_unavailable=sum(o['status']!='returned' for o in ops.values()),cache_hits=sum(e.get('status')=='cache_hit' for e in records),input_tokens=sum(e.get('input_tokens') or 0 for e in records if e.get('status')=='returned'),output_tokens=sum(e.get('output_tokens') or 0 for e in records if e.get('status')=='returned'),hardware_software_precision=[e['identity'] for e in records if e.get('stage')=='backend_identity'],full_study_total=None,note='Frozen-plan conditional ceilings: replay failures can prevent downstream operations permanently. No terminal request is retried. Candidate counts are three complete sequences per readout, not generated answer frequencies. Completed per-sequence timings may include work from a later failed aggregate readout. Mock time is not live time.')
    return write_report(out/'timing-sidecar/report',result,'Study 2 event/intervention timing')
