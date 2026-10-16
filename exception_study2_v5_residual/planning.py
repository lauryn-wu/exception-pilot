"""Freeze residual evidence, exact requests and spending estimates before dispatch."""
from collections import Counter
import json
import math
from exception_pilot.core import digest
from exception_study2_v5_review_v22.batches import filter_candidates,partition
from .evidence import historical_evidence,source_resolution
from .providers import payload
from .policy import RUBRICS,SCHEMAS


def request(history,policy,tids,judge,kind,view,why,refs):
    config=policy['config']['judges'][judge]
    sources={tid:dict(source_row_hash=history.packets[tid]['source_row_hash'],packet_hash=digest(history.packets[tid]),
                     prior_case_hash=digest(history.cases[tid])) for tid in tids}
    binding=dict(task_ids=tids,judge=judge,kind=kind,candidate_refs=refs,sources=sources,
        history_binding_hash=digest(history.binding),policy_hash=policy['policy_hash'])
    rid='r-'+digest(binding)[:24];ids=list(refs)
    wire=payload(config,RUBRICS[kind],SCHEMAS[kind],view)
    byte_count=len(json.dumps(wire,ensure_ascii=False).encode())
    rates=config['rates'];low_output=256+350*len(ids) if kind=='detect' else 1500
    low_output=min(low_output,config['max_output_tokens'])
    return dict(id=rid,binding=binding,judge=judge,provider=config['provider'],kind=kind,
        role='initial' if kind=='detect' else 'verify',candidate_ids=ids,why=why,view=view,request=wire,
        cost=dict(input_token_low_estimate=math.ceil(byte_count/4),input_token_reservation=byte_count+2048,
            output_token_low_estimate=low_output,output_token_cap=config['max_output_tokens'],
            low_estimate_usd=(math.ceil(byte_count/4)*rates['input_per_million']+low_output*rates['output_per_million'])/1e6,
            reservation_usd=((byte_count+2048)*rates['input_per_million']+config['max_output_tokens']*rates['output_per_million'])/1e6))


def build(history,policy):
    cases={};requests=[];counts=Counter();changes=[];needed={'openai':[],'anthropic':[]}
    old_judges=history.review.policy['config']['judges'];new_judges=policy['config']['judges']
    for judge in ('J1','J2'):
        if any(new_judges[judge][field]!=old_judges[judge][field] for field in ('provider','model')):
            raise ValueError('Residual review must preserve exact historical J1/J2 model/provider identities')
    for index,(tid,c) in enumerate(history.cases.items()):
        packet=history.packets[tid];kept,excluded=filter_candidates(c['candidates']);evidence={};resolutions={}
        for cand in kept:
            key=cand['id'];evidence[key]=historical_evidence(packet,c,cand,old_judges)
            resolutions[key]=source_resolution(packet,cand,evidence[key]);prior=c['result']['candidate_status'][key]
            current=resolutions[key]['status'];counts['retained_'+current]+=1
            if prior!=current:changes.append(dict(task_id=tid,candidate_id=key,previous=prior,current=current,reason=resolutions[key]['reason']))
            if resolutions[key]['genuine_disagreement']:counts['deferred_genuine_disagreement']+=1
            if resolutions[key]['deferred_source_witness']:
                counts['deferred_source_witness']+=1
                counts['source_witness_provider_decisions_avoided']+=len(resolutions[key]['required_providers'])
            if resolutions[key]['dispatch_providers']:counts['candidates_needing_new_judgments']+=1
            counts['provider_decisions_needed']+=len(resolutions[key]['dispatch_providers'])
            for provider in resolutions[key]['dispatch_providers']:
                # Sorting coordinates only; actual source span stays in candidate.
                needed[provider].append(dict(id=tid+'::'+key,span=[index,cand['span'][0]],task_id=tid,candidate=cand))
        for excluded_row in excluded:counts['excluded_'+c['result']['candidate_status'][excluded_row['candidate']['id']]]+=1
        obligations=[]
        for phase,ex in [('primary',c['extractor']),('audit',c['auditor'])]:
            events=[e for e,status in ex.get('coverage',{}).items() if status['status']!='pass']
            if not ex.get('valid') or ex.get('reviewed_all',{}).get('status')!='pass':events=list(policy['schemas']['verify']['properties']['coverage']['properties'])
            if events:obligations.append(dict(phase=phase,judge='J1' if phase=='primary' else 'J2',events=events,
                historical_flags=ex,reason='Historical coverage incomplete/failed; no reinterpretation of old explanations'))
        cases[tid]=dict(packet=packet,original_candidates=c['candidates'],candidates=kept,excluded=excluded,
            prior_evidence=evidence,resolutions=resolutions,coverage_obligations=obligations,
            extractor=c['extractor'],auditor=c['auditor'],prior_case_hash=digest(c))
    # Pool residuals by provider, without padding with resolved decisions. Every
    # source retains its full independent packet; wire IDs cannot alias across cases.
    for judge,provider in [('J1','openai'),('J2','anthropic')]:
        if 0<len(needed[provider])<4:
            raise ValueError('Fewer than four residual items for provider: a separately specified smaller-batch protocol is required; never pad with resolved items')
        for batch in partition(needed[provider],policy['config']['batch_size']):
            tids=list(dict.fromkeys(x['task_id'] for x in batch));views=[];refs={};reasons={}
            for tid in tids:
                cs=[]
                for item in batch:
                    if item['task_id']!=tid:continue
                    cand=item['candidate'];key=cand['id'];wire_id=item['id'];resolution=cases[tid]['resolutions'][key]
                    refs[wire_id]=dict(task_id=tid,candidate_id=key,span=cand['span'])
                    cs.append(dict(cand,id=wire_id,source_candidate_id=key))
                    reasons[wire_id]=dict(reason=resolution['reason'],missing_provider=provider,
                        retained_provider_support={p:pos['status'] for p,pos in resolution['providers'].items()})
                views.append(dict(task_id=tid,source=history.packets[tid],candidates=cs))
            requests.append(request(history,policy,tids,judge,'detect',dict(cases=views),reasons,refs))
    for tid,c in cases.items():
        for obligation in c['coverage_obligations']:
            requests.append(request(history,policy,[tid],obligation['judge'],'verify',
                dict(history.packets[tid],coverage_events=obligation['events']),obligation,{}))
    # Smoke is a fixed subset of real plan slots, not a new four-call allowance.
    smoke=[]
    for provider,kind in [('openai','detect'),('anthropic','detect'),('openai','verify'),('anthropic','verify')]:
        found=next((r['id'] for r in requests if r['provider']==provider and r['kind']==kind and r['id'] not in smoke),None)
        if found:smoke.append(found)
    for r in requests:
        if len(smoke)>=min(4,len(requests)):break
        if r['id'] not in smoke:smoke.append(r['id'])
    counts.update(original_candidates=history.report['distinct_candidates'],
        historical_resolved=sum(history.report['historical_candidate_counts'].get(s,0) for s in ('present','absent')),
        salvage_resolved=sum(history.report['retrospective_candidate_counts'].get(s,0) for s in ('present','absent')),
        salvage_unresolved=history.report['retrospective_candidate_counts']['uncertain'],
        mechanically_excluded=sum(len(c['excluded']) for c in cases.values()),retained=sum(len(c['candidates']) for c in cases.values()),
        verification_requests=sum(r['kind']=='detect' for r in requests),coverage_requests=sum(r['kind']=='verify' for r in requests),total_requests=len(requests),
        openai_decisions_needed=len(needed['openai']),anthropic_decisions_needed=len(needed['anthropic']))
    cost=dict(minimum_calls_to_attempt_complete_plan=len(requests),maximum_calls=len(requests),automatic_J3_calls=0,
        smoke_maximum_calls=len(smoke),smoke_request_ids=smoke,
        low_estimate_usd=sum(r['cost']['low_estimate_usd'] for r in requests),
        reservation_upper_estimate_usd=sum(r['cost']['reservation_usd'] for r in requests),
        smoke_low_estimate_usd=sum(r['cost']['low_estimate_usd'] for r in requests if r['id'] in smoke),
        smoke_reservation_upper_estimate_usd=sum(r['cost']['reservation_usd'] for r in requests if r['id'] in smoke),
        rates={j:new_judges[j]['rates'] for j in ('J1','J2')},
        assumptions='Saved historical rates, no caching discount. Low estimate: JSON bytes/4 input, 256+350 tokens per candidate batch or 1500 coverage output. Upper: shared journal reservation (JSON bytes+2048 input, full output cap). Not a billing guarantee; failures/budget stops can end before completion. Zero calls without separate authorization.',
        global_call_ceiling=policy['config']['limits']['max_calls'],global_estimated_spend_ceiling=policy['config']['limits']['max_estimated_usd'])
    if len(requests)>policy['config']['limits']['max_calls'] or cost['reservation_upper_estimate_usd']>policy['config']['limits']['max_estimated_usd']:
        raise ValueError('Frozen limits cannot cover conservative residual plan reservations')
    return dict(cases=cases,requests=requests,accounting=dict(counts),revalidation_changes=changes,cost=cost,
        smoke_request_ids=smoke,prior_evidence_hash=digest(history.side),
        provenance='Audit-informed residual repair combining historical and future evidence; not independent confirmation. Historical files are never rewritten.')
