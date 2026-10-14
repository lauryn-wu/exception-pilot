"""Conditional arm contrasts and judge reports; no cross-path replay fields."""
from collections import Counter,defaultdict
from pathlib import Path
from statistics import mean
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_continuation.analysis import clustered
from exception_review.reporting import stats,entries,remaining_judge_counts,timing
from .artifacts import Review
from .. import PROTOCOL,ESTIMAND


def comparisons(cases,results,initial_only=False):
    if initial_only:cases=[c for c in cases if c['initial_agreement']]
    byid={r['task_id']:r for r in results};worlds=defaultdict(list)
    for case in cases:worlds[case['world']].append(case)
    names=[('primary_availability_minus_meaning','availability_repair','meaning_control'),('availability_minus_unchanged','availability_repair','unchanged'),('meaning_minus_unchanged','meaning_control','unchanged'),('value_minus_unchanged','value_repair','unchanged')]
    answer={}
    for name,left,right in names:
        complete={};bounds={};accuracy_worlds={};readout_worlds={}
        for world,items in worlds.items():
            differences=[];intervals=[];readout_differences=[]
            for case in items:
                row=byid.get(case['task_id'],{});values=[];preferences=[]
                for arm in (left,right):
                    obs=row.get('arms',{}).get(arm,{});score=obs.get('score',{})
                    valid=obs.get('arm_input_valid') is True and obs.get('prefix_text_preserved') is True
                    value=int(score['correct']) if valid and score.get('valid') is True and type(score.get('correct')) is bool else None
                    values.append(value)
                    preferences.append(obs.get('readout',{}).get('gold_pattern_log_odds') if obs.get('arm_input_valid') is True and obs.get('conditional_readout_valid') is True else None)
                if all(isinstance(v,(int,float)) for v in preferences):readout_differences.append(preferences[0]-preferences[1])
                a,b=values;intervals.append(((0 if a is None else a)-(1 if b is None else b),(1 if a is None else a)-(0 if b is None else b)))
                if a is not None and b is not None:differences.append(a-b)
            bounds[world]=[mean(x[i] for x in intervals) for i in (0,1)]
            if len(differences)==len(items):complete[world]=mean(differences);accuracy_worlds[world]=differences
            if len(readout_differences)==len(items):readout_worlds[world]=readout_differences
        answer[name]=dict(accuracy=clustered(accuracy_worlds),readout=clustered(readout_worlds),complete_accuracy_cases=sum(len(v) for v in accuracy_worlds.values()),estimate=mean(complete.values()) if complete else None,complete_worlds=len(complete),planned_worlds=len(worlds),planned_cases=len(cases),world_means=complete,unknown_bounds=[mean(b[i] for b in bounds.values()) for i in (0,1)] if bounds else None,world_bounds=bounds,status='NO_ELIGIBLE_CASES' if not cases else 'NO_COMPLETE_WORLDS' if not complete else 'ESTIMATED',aggregation='mean of within-world paired means; all planned cases required per contrast',interpretation=ESTIMAND)
    return answer


def write_report(path,value,title):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    write_json(path.with_suffix('.json'),value)
    path.with_suffix('.md').write_text('# '+title+'\n\n'+ESTIMAND+'\n\nMock results are not live model evidence.\n\n```json\n'+__import__('json').dumps(value,indent=2,ensure_ascii=False)+'\n```\n')
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
        p=review.root/'interventions-v4'/scope/'interventions-v4.json'
        if p.exists():
            data=sealed_read(p)
            if data['edit_plan_hash']!=frozen['artifact_hash'] or data['source_hash']!=review.source.hash: raise ValueError('Stale interventions')
        for row in data['rows']:
            diagnostics['arm_input_failure']+=sum(o.get('arm_input_valid') is False for o in row.get('arms',{}).values())
            diagnostics['invalid_qwen_answer']+=sum(o.get('score',{}).get('valid') is False for o in row.get('arms',{}).values())
    from .coverage import intervention_coverage
    coverage=intervention_coverage(cases,data['rows'],review.root/'interventions-v4'/scope,review.source.hash,frozen['artifact_hash']) if edit_path.exists() else None
    for d in details: d['state']=states[d['task_id']]
    pending=sum(s.startswith('PENDING') or s=='READY_TO_FREEZE' for s in states.values())
    intervention_status='NOT_FROZEN' if not edit_path.exists() else 'NOT_RUN' if 'status' not in data else data['status']
    result=dict(intervention_status=intervention_status,source_hash=review.source.hash,policy_hash=review.policy['policy_hash'],scope=scope,status='INCOMPLETE' if pending else 'COMPLETE',synthetic=plan['synthetic'],planned_scope_cases=len(states),full_source_cases=len(review.source.rows),unreviewed_outside_scope=len(review.source.rows)-len(states),terminal_state_partition=dict(Counter(states.values())),diagnostic_counts_may_overlap=dict(diagnostics),cases=details,intervention_coverage=coverage,accepted_intervention_cases=len(cases),accepted_worlds=len({c['world'] for c in cases}),cohort_status='FROZEN' if edit_path.exists() else 'NOT_FROZEN',primary_and_secondary=comparisons(cases,data['rows']) if edit_path.exists() else None,initially_agreed_only=comparisons(cases,data['rows'],True) if edit_path.exists() else None,judge_annotation_quality='UNVALIDATED',technical_same_input_passed=review.source.technical['technical_same_input_passed'],fresh_prefix_control='unchanged',real_model_status='PENDING' if plan['synthetic'] else review.source.technical['real_model_status'],interpretation=ESTIMAND,protocol=PROTOCOL,timing=timing(review,plan,states))
    return write_report(review.root/'reports'/(scope+'-report'),result,'Study 2 v4 conditional-prefix review and timing')
