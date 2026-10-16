"""Read-only reanalysis of immutable v2.1 responses. No transport/journal calls."""
from collections import Counter
from pathlib import Path
import hashlib
import json
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.core import source_hash
from exception_study2_v5.review.workflow import read_manifest
from exception_study2_v5_review_v2.workflow import Review as HistoricalReview
from exception_study2_v5_review_v2 import decisions as historical_decisions,candidates as canonical
from exception_study2_v5_review_v2.providers import parse_response,payload
from . import SALVAGE_VERSION
from .policy import EVENTS,LEGACY,code_hash
from .decisions import partial_vote,reconcile,finalize
from .batches import filter_candidates,partition


def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}


def request_view(request):
    messages=request.get('input',request.get('messages'))
    text=messages[0]['content']
    return json.loads(text.split('BEGIN_UNTRUSTED_SOURCE_JSON\n',1)[1].rsplit('\nEND_UNTRUSTED_SOURCE_JSON',1)[0])


def validated_operations(review):
    """Bind raw bodies to saved parser results, exact requests, source and slots."""
    records={}
    for file in sorted((review.root/'judge-operations').glob('*/planned.json')):
        directory=file.parent
        terminal=next((directory/(s+'.json') for s in ('returned','failed') if (directory/(s+'.json')).exists()),None)
        record=sealed_read(terminal or file);ident=record['identity'];key=record['key']
        if key!=digest(ident) or directory.name!=key or record['request']!=ident['request']:raise ValueError('Operation identity mismatch')
        for field,value in review.case_binding(ident['task_id']).items():
            if ident.get(field)!=value:raise ValueError('Operation source binding mismatch')
        judge=ident['judge'];role=ident['role'];kind='detect' if role in ('initial','adjudicate') else 'draft' if role=='draft' else 'verify'
        view=request_view(record['request']);cfg=review.policy['config']['judges'][judge]
        if (ident['judge_config']!=cfg or ident['policy_hash']!=review.policy['policy_hash'] or ident['input_hash']!=digest(view)
            or ident['prompt_hash']!=digest(review.policy['rubrics'][kind]) or ident['schema_hash']!=digest(review.policy['schemas'][kind])
            or record['request']!=payload(cfg,review.policy['rubrics'][kind],review.policy['schemas'][kind],view)):
            raise ValueError('Operation request/policy mismatch')
        slot=sealed_read(review.root/'judge-operations'/'slots'/(digest([ident['task_id'],judge,role,ident['edit_version']])+'.json'))
        if slot!={'key':key,'identity':ident,'artifact_hash':digest(dict(key=key,identity=ident))}:raise ValueError('Operation slot mismatch')
        if terminal and record['state']=='returned':
            parsed=parse_response(cfg['provider'],record['raw_response'])
            if parsed['valid'] and parsed['model']!=cfg['model']:parsed.update(valid=False,reason='returned_model_identity_mismatch')
            if parsed!=record['parsed']:raise ValueError('Raw response and saved parser result differ')
        else:parsed=dict(valid=False,reason=record.get('parsed',{}).get('reason','terminal_unavailable_no_retry'),value=None)
        k=(ident['original_task_id'],ident['phase'],judge,role)
        if k in records:raise ValueError('Duplicate immutable operation slot')
        records[k]=dict(record=record,parsed=parsed,view=view)
    return records


def estimate(cases,judges,size=6):
    """Observed-pool estimates, not permission to combine epochs or spend money."""
    phase_rows=[];repair_rows=[];coverage_cases=[];total_kept=total_excluded=0
    for tid,c in cases.items():
        for phase,data in c['phases'].items():
            kept,excluded=filter_candidates(data['candidates']);batches=partition(kept,size)
            total_kept+=len(kept);total_excluded+=len(excluded)
            phase_rows.append(dict(task_id=tid,phase=phase,kept=len(kept),excluded=len(excluded),batches=len(batches)))
        remaining,_=filter_candidates(c['candidates'])
        unresolved=[x for x in remaining if c['result']['candidate_status'][x['id']]=='uncertain']
        # Recheck both families for unresolved candidates; not a cheaper retry of
        # an old failed slot. Any later use needs a separate authorized new plan.
        repair_rows.append(dict(task_id=tid,remaining_candidates=len(unresolved),batches=len(partition(unresolved,size))))
        for phase in ('primary','audit'):
            extraction=c['extractor' if phase=='primary' else 'auditor']
            if not extraction.get('valid') or extraction['reviewed_all']['status']!='pass' or any(x['status']!='pass' for x in extraction.get('coverage',{}).values()):
                coverage_cases.append(dict(task_id=tid,phase=phase))
    batches=sum(x['batches'] for x in phase_rows);repair=sum(x['batches'] for x in repair_rows);extract_calls=2*len(cases)
    return dict(batch_target=size,phase_candidate_occurrences_kept=total_kept,phase_candidate_occurrences_excluded=total_excluded,
        fresh_v22_observed_pool=dict(extraction_and_audit_calls=extract_calls,verification_batches=batches,
            no_adjudication_calls=extract_calls+2*batches,maximum_with_one_J3_per_batch=extract_calls+3*batches),
        targeted_retrospective_repair_estimate=dict(coverage_calls=len(coverage_cases),verification_batches=repair,
            no_adjudication_calls=len(coverage_cases)+2*repair,maximum_with_one_J3_per_batch=len(coverage_cases)+3*repair),
        phase_counts=phase_rows,repair_counts=repair_rows,coverage_rejudgment_cases=coverage_cases,
        limitations='Observed historical candidate pool only. Fresh extraction can add candidates. Targeted repair is a planning estimate, not an executable mixed-epoch protocol or authorization; no old slot may be retried. Global frozen call/spend limits may stop any future plan sooner.')


def analyze(input_path,output):
    # Validate separation before creating even an output lock.
    review=HistoricalReview(input_path);out=Path(output).resolve()
    roots=(review.root,review.source_original.root)
    if any(out==r or out.is_relative_to(r) or r.is_relative_to(out) for r in roots):raise ValueError('Separate salvage output required')
    with run_lock(out/'locks'):return _analyze(input_path,out)


def _analyze(input_path,output):
    review=HistoricalReview(input_path)
    if review.plan['version']!='study2-review-v2.1':raise ValueError('Salvage is explicitly for v2.1')
    out=Path(output).resolve();roots=(review.root,review.source_original.root)
    if any(out==r or out.is_relative_to(r) or r.is_relative_to(out) for r in roots):raise ValueError('Separate salvage output required')
    if out.exists() and any(p.name!='locks' for p in out.iterdir()) and not (out/'salvage-report.json').exists():raise ValueError('Fresh salvage output required')
    before={str(r):snapshot(r) for r in roots}
    old_manifest=read_manifest(review.root/'annotation-manifest-v5.json',review.source_original)
    old_observations=sealed_read(review.root/'observations-v2.json');ops=validated_operations(review)
    judges=review.policy['config']['judges'];operation_audit=[];cases={};coverage_failures=[];old_errors=Counter();recovered=Counter();semantic_errors=Counter()
    for tid in review.plan['case_ids']:
        p=review.plan['packets'][tid];phase_results=[];phases={};extracts={}
        all_paths=[]
        for phase in ('primary','audit'):
            exop=ops.get((tid,phase,'J1' if phase=='primary' else 'J2','draft' if phase=='primary' else 'verify'))
            if exop:
                if exop['view']!=p:raise ValueError('Extraction source packet changed')
                parsed=exop['parsed'];ex=canonical.extraction(parsed.get('value'),p,parsed['valid'],parsed.get('reason'))
            else:ex=canonical.extraction(None,p,False,'missing_extraction_operation')
            extracts[phase]=ex
            for event,status in ex.get('coverage',{}).items():
                if status['status']!='pass':coverage_failures.append(dict(task_id=tid,phase=phase,event=event,**status))
            paths=[('semantic-extractor' if phase=='primary' else 'negative-audit',ex['candidates'])]
            if phase=='primary':paths.insert(0,('structural',canonical.structural_candidates(p)))
            cs=canonical.merge(p,paths);all_paths.extend(paths);votes={}
            for judge in ('J1','J2','J3'):
                role='adjudicate' if judge=='J3' else 'initial';op=ops.get((tid,phase,judge,role))
                if not op:continue
                if op['view']!=dict(p,candidates=cs):raise ValueError('Historical candidate packet changed')
                parsed=op['parsed'];v=partial_vote(parsed.get('value'),p,cs,parsed['valid'],parsed.get('reason'),historical=True)
                prior=historical_decisions.vote(parsed.get('value'),p,cs,parsed['valid'],parsed.get('reason'))
                old_errors[prior['reason'] or 'valid_envelope']+=1
                v['operation_key']=op['record']['key'];v['operation_hash']=op['record']['artifact_hash'];votes[judge]=v
                audit=dict(task_id=tid,phase=phase,judge=judge,model=judges[judge]['model'],provider=judges[judge]['provider'],
                    operation_key=v['operation_key'],operation_hash=v['operation_hash'],raw_body_sha256=hashlib.sha256(op['record'].get('raw_response',{}).get('body','').encode()).hexdigest(),
                    historical_batch_valid=prior['valid'],historical_batch_error=prior['reason'],**v['audit'])
                recovered['unique_schema_valid_decision_items']+=len(v['audit']['schema_valid_ids'])
                recovered['conclusive_decision_items']+=len(v['audit']['conclusive_ids'])
                if not prior['valid']:
                    recovered['schema_valid_items_recovered_from_invalid_batches']+=len(v['audit']['schema_valid_ids'])
                    recovered['conclusive_items_recovered_from_invalid_batches']+=len(v['audit']['conclusive_ids'])
                recovered['missing_decision_items']+=len(v['audit']['missing_ids'])
                for d in v['decisions'].values():
                    for reason in d['validation_errors']:semantic_errors[reason]+=1
                operation_audit.append(audit)
            combined=reconcile(cs,votes,judges);phase_results.append(combined)
            phases[phase]=dict(candidates=cs,votes=votes,reconciliation=combined)
        cs=canonical.merge(p,all_paths)
        result=finalize(p,cs,phase_results,extracts['primary'],extracts['audit'])
        # Retrospective labels never alter the original manifest/certificates.
        for decision in list(result['events'].values())+[result['substitution']]:decision['rationale']='RETROSPECTIVE SENSITIVITY ANALYSIS. '+decision['rationale']
        cases[tid]=dict(candidates=cs,extractor=extracts['primary'],auditor=extracts['audit'],phases=phases,result=result,source_row_hash=p['source_row_hash'])
    counts={e:dict(Counter((c['result']['substitution'] if e=='P' else c['result']['events'][LEGACY[e]])['status'] for c in cases.values())) for e in EVENTS}
    recovered_unique={(a['task_id'],key) for a in operation_audit if not a['historical_batch_valid'] for key in a['conclusive_ids']}
    recovered['distinct_candidates_with_recovered_conclusive_items']=len(recovered_unique)
    statuses=Counter(s for c in cases.values() for s in c['result']['candidate_status'].values())
    previous=Counter(s for c in old_observations['cases'].values() for s in c['candidate_status'].values())
    existence={e:sum(c['result']['existence_evidence'][e]['status']=='supported' for c in cases.values()) for e in EVENTS}
    causes=Counter(reason for c in cases.values() for v in c['result']['combined']['candidates'].values() if v['status']=='uncertain' for reason in v['causes'])
    provenance=dict(version=SALVAGE_VERSION,retrospective=True,independent_validation=False,sensitivity_only=True,
        source_review_plan_hash=review.plan['artifact_hash'],source_policy_hash=review.policy['policy_hash'],original_manifest_hash=old_manifest['artifact_hash'],
        original_observations_hash=old_observations['artifact_hash'],original_code_revision=review.plan['code_revision'],salvage_code_hash=code_hash(),
        source=review.source_original.binding_at(out),policy='Per-item partial recovery, unchanged historical coverage flags and semantic checks; require cross-provider family support. Missing data is not disagreement. No automated relabeling from explanation prose.',
        historical_source_tree_hashes={str(r):digest(v) for r,v in ((r,before[str(r)]) for r in roots)})
    report=dict(provenance=provenance,trajectories=len(cases),distinct_candidates=sum(len(c['candidates']) for c in cases.values()),
        historical_candidate_counts=dict(previous),retrospective_candidate_counts=dict(statuses),decision_recovery=dict(recovered),
        historical_response_failures=dict(old_errors),remaining_decision_issues=dict(semantic_errors),remaining_candidate_causes=dict(causes),
        raw_response_summary=dict(operations=len(ops),provider_parsed_valid=sum(o['parsed']['valid'] for o in ops.values()),
            verification_responses=len(operation_audit),incomplete_responses=sum(bool(a['missing_ids']) for a in operation_audit),
            duplicate_ids=sum(len(a['duplicate_ids']) for a in operation_audit),unknown_ids=sum(len(a['unknown_ids']) for a in operation_audit),
            malformed_items=sum(len(a['malformed_items']) for a in operation_audit)),
        coverage_failures=coverage_failures,strict_event_counts=counts,supported_existence_counts=existence,
        note='Supported existence is NOT first-occurrence certification; counts retain unknowns. Historical coverage fail is never promoted from its explanation.',
        additional_call_estimates=estimate(cases,judges),paid_calls=0)
    side=freeze(out/'retrospective-observations.json',dict(provenance=provenance,cases=cases))
    manifest_cases={}
    for tid,c in cases.items():
        events=c['result']['events'];m,o=events['erasure'],events['override'];stratum=None
        if o['status']=='present':stratum='mixed' if m['status']=='present' and m['span'][0]<o['span'][0] else 'clean' if m['status']=='absent' or (m['status']=='present' and m['span'][0]>=o['span'][0]) else 'unknown_erasure_history'
        manifest_cases[tid]=dict(world=review.plan['packets'][tid]['world'],events=events,source_row_hash=c['source_row_hash'],initial_agreement=c['result']['initial_agreement'],override_stratum=stratum)
    alt=freeze(out/'annotation-manifest-v5-retrospective.json',dict(protocol=PROTOCOL,source=review.source_original.binding_at(out),code_hash=source_hash(),
        review_plan_hash=review.plan['artifact_hash'],method=SALVAGE_VERSION,retrospective_provenance=provenance,cases=manifest_cases,
        reviews=dict(sidecar='retrospective-observations.json',artifact_hash=side['artifact_hash']),disagreements=[t for t,c in manifest_cases.items() if not c['initial_agreement']],
        blinding=review.plan['blinding'],adjudication='No new judgments: saved evidence only; not an independently validated scientific result.'))
    read_manifest(out/'annotation-manifest-v5-retrospective.json',review.source_original)
    report['alternative_manifest_hash']=alt['artifact_hash'];report['alternative_manifest_validates']=True
    freeze(out/'operation-audit.json',dict(provenance=provenance,operations=operation_audit))
    after={str(r):snapshot(r) for r in roots}
    if before!=after:raise ValueError('Historical/source files changed during salvage')
    report['source_and_historical_files_byte_identical']=True
    return freeze(out/'salvage-report.json',report)
