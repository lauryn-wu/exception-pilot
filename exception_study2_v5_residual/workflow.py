"""Additive residual plan, bounded smoke, immutable requests and conservative export."""
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.core import source_hash
from exception_study2_v5.review.workflow import read_manifest
from exception_study2_v5_review_v2 import decisions as old_decisions,candidates as canonical
from exception_study2_v5_review_v2.workflow import DeadlineTransport
from exception_study2_v5_review_v22.decisions import extraction
from . import VERSION
from .history import History
from .policy import freeze_policy,RUBRICS,SCHEMAS
from .planning import build
from .evidence import resolve,new_vote
from .journal import Journal
from .providers import payload,parse_response


def separate(history,out):
    roots=(history.root,history.review.root,history.review.source_original.root)
    if any(out==r or out.is_relative_to(r) or r.is_relative_to(out) for r in roots):
        raise ValueError('Residual output must be separate from historical, salvage and original data')


def prepare(review,salvage,output,config):
    h=History(review,salvage);out=Path(output).resolve();separate(h,out)
    policy=freeze_policy(config);bundle=build(h,policy)
    if out.exists() and any(out.iterdir()) and not (out/'residual-plan.json').exists():raise ValueError('Fresh separate residual directory required')
    with run_lock(out/'locks'):
        if (out/'residual-plan.json').exists():
            r=Review(out)
            if r.history.binding!=h.binding or r.policy!=policy:raise ValueError('Frozen residual inputs/config differ')
            return r.plan
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],text=True).strip()
        freeze(out/'residual-policy.json',policy)
        prior=freeze(out/'prior-evidence.json',dict(history_binding=h.binding,original_salvage=h.side))
        plan=freeze(out/'residual-plan.json',dict(version=VERSION,protocol=PROTOCOL,history=h.binding,
            policy_hash=policy['policy_hash'],scientific_source_hash=source_hash(),prior_evidence_artifact_hash=prior['artifact_hash'],
            code_revision=revision,**bundle))
        freeze(out/'request-preview.json',dict(plan_hash=plan['artifact_hash'],accounting=bundle['accounting'],
            revalidation_changes=bundle['revalidation_changes'],cost=bundle['cost'],requests=bundle['requests']))
        return plan


class Review:
    def __init__(self,output):
        self.root=Path(output).resolve();self.plan=sealed_read(self.root/'residual-plan.json')
        saved=sealed_read(self.root/'residual-policy.json');self.policy=freeze_policy(saved['config'])
        if self.policy!={k:v for k,v in saved.items() if k!='artifact_hash'}:raise ValueError('Residual policy/code changed')
        self.history=History(self.plan['history']['review'],self.plan['history']['salvage']);separate(self.history,self.root)
        if self.plan['history']!=self.history.binding:raise ValueError('Frozen residual historical evidence changed')
        prior=sealed_read(self.root/'prior-evidence.json')
        if (prior['artifact_hash']!=self.plan['prior_evidence_artifact_hash'] or prior['original_salvage']!=self.history.side
            or prior['history_binding']!=self.history.binding):raise ValueError('Prior evidence changed')
        bundle=build(self.history,self.policy)
        if (self.plan['version']!=VERSION or self.plan['protocol']!=PROTOCOL or self.plan['scientific_source_hash']!=source_hash()
            or self.plan['policy_hash']!=self.policy['policy_hash'] or any(self.plan.get(k)!=v for k,v in bundle.items())):
            raise ValueError('Residual population, requests or source binding changed')
        self.requests={r['id']:r for r in self.plan['requests']}
        self.source=SimpleNamespace(case_binding=self.case_binding)
    def case_binding(self,rid):
        if rid not in self.requests:raise ValueError('Unplanned residual request (no J3 or new slots)')
        req=self.requests[rid]
        return dict(task_id=rid,original_task_ids=req['binding']['task_ids'],request_id=rid,
            source_hash=self.history.review.source_original.hash,source_bindings=req['binding']['sources'],
            review_plan_hash=self.plan['artifact_hash'],prior_evidence_hash=self.plan['prior_evidence_hash'],
            residual_request_hash=digest(req))
    def identity(self,req):
        j=self.policy['config']['judges'][req['judge']]
        wire=payload(j,RUBRICS[req['kind']],SCHEMAS[req['kind']],req['view'])
        if wire!=req['request'] or req['judge'] not in ('J1','J2'):raise ValueError('Frozen request differs / J3 forbidden')
        return dict(**self.case_binding(req['id']),policy_hash=self.policy['policy_hash'],
            prompt_hash=digest(RUBRICS[req['kind']]),schema_hash=digest(SCHEMAS[req['kind']]),
            judge=req['judge'],judge_config=j,role=req['role'],edit_version=0,input_hash=digest(req['view']),request=wire)
    def entry(self,req):
        ident=self.identity(req);key=digest(ident);root=self.root/'judge-operations'
        slot=root/'slots'/(digest([req['id'],req['judge'],req['role'],0])+'.json')
        directory=root/key
        if not slot.exists():
            if directory.exists():raise ValueError('Operation without immutable slot')
            return None
        saved=sealed_read(slot)
        if saved!={'key':key,'identity':ident,'artifact_hash':digest(dict(key=key,identity=ident))}:raise ValueError('Residual journal slot changed')
        for state in ('returned','failed'):
            if not (directory/(state+'.json')).exists():continue
            record=sealed_read(directory/(state+'.json'))
            if record['identity']!=ident or record['key']!=key or record['request']!=req['request']:raise ValueError('Residual journal source mismatch')
            if state=='returned':
                parsed=parse_response(req['provider'],record['raw_response'])
                if parsed['valid'] and parsed['model']!=ident['judge_config']['model']:parsed.update(valid=False,reason='returned_model_identity_mismatch')
                if parsed!=record['parsed']:raise ValueError('Residual raw response/parse mismatch')
            elif record['parsed'].get('valid') is not False:raise ValueError('Failed operation cannot contain a valid vote')
            return record
        return None


def inspect(output):
    r=Review(output)
    entries={req['id']:r.entry(req) for req in r.plan['requests']}
    return dict(version=VERSION,plan_hash=r.plan['artifact_hash'],accounting=r.plan['accounting'],cost=r.plan['cost'],
        revalidation_changes=r.plan['revalidation_changes'],smoke_request_ids=r.plan['smoke_request_ids'],
        requests=[dict(id=q['id'],task_ids=q['binding']['task_ids'],judge=q['judge'],provider=q['provider'],kind=q['kind'],
            candidate_ids=q['candidate_ids'],why=q['why'],cost=q['cost'],state=entries[q['id']]['state'] if entries[q['id']] else 'unattempted_or_ambiguous') for q in r.plan['requests']],
        note='Read-only inspection. Exact wire payloads are in request-preview.json. Missing/ambiguous calls are never negative votes.')


def run(output,stage='smoke',live=False,authorization=None,transport=None,max_calls=None,wall_seconds=None,clock=None):
    if stage not in ('smoke','review'):raise ValueError('Unknown stage')
    with run_lock(Path(output)/'locks'):
        r=Review(output)
        ids=r.plan['smoke_request_ids'] if stage=='smoke' else list(r.requests)
        limit=min(len(ids),r.policy['config']['limits']['max_calls'])
        if max_calls is not None:
            if type(max_calls) is not int or not 0<=max_calls<=limit:raise ValueError('Invocation limit must tighten frozen stage maximum')
            limit=max_calls
        if live:
            if authorization!=r.plan['artifact_hash']:raise ValueError('Separate paid '+stage+' authorization must name the exact plan hash')
            if r.history.review.source_original.execution['mode']!='LIVE_LOCAL':raise ValueError('Live review requires real original source')
            if not r.policy['config']['live_enabled']:raise ValueError('Offline frozen configuration; prepare a new authorized live plan')
            freeze(r.root/'authorizations'/(stage+'.json'),dict(plan_hash=authorization,stage=stage,request_ids=ids,
                lifetime_max_calls=len(ids),retries=0,note='Explicit operator authorization; smoke does not authorize full review'))
        wall=r.policy['config']['limits']['wall_seconds']
        if wall_seconds is not None:
            if type(wall_seconds) not in (int,float) or not 0<wall_seconds<=wall:raise ValueError('Wall override must tighten frozen limit')
            wall=wall_seconds
        journal=Journal(r,live,transport,limit,wall,clock)
        if live:journal.transport=DeadlineTransport(journal,journal.transport)
        try:
            for rid in ids:
                req=r.requests[rid];r.identity(req)
                # Validate cached raw evidence before the shared journal can reuse it.
                r.entry(req)
                entry=journal.call(rid,req['judge'],req['role'],0,req['view'])
                if entry is None:break
                r.entry(req)
        finally:metrics=journal.finish('residual-'+stage,'frozen-residual')
    return metrics


def results(r):
    cases=copy.deepcopy(r.plan['cases']);pending=[];new_audits={};discoveries=[]
    for req in r.plan['requests']:
        entry=r.entry(req)
        if entry is None:pending.append(req['id']);continue
        parsed=entry['parsed']
        if req['kind']=='detect':
            refs=req['binding']['candidate_refs'];value=parsed.get('value');audits={}
            rows=value.get('decisions',[]) if isinstance(value,dict) else []
            unknown_ids=[d.get('candidate_id') for d in rows if isinstance(d,dict) and isinstance(d.get('candidate_id'),str) and d['candidate_id'] not in refs]
            for tid in req['binding']['task_ids']:
                c=cases[tid];packet=c['packet'];lookup={x['id']:x for x in c['candidates']}
                keys=[ref['candidate_id'] for ref in refs.values() if ref['task_id']==tid]
                cs=[lookup[key] for key in keys];local=copy.deepcopy(parsed)
                if isinstance(value,dict) and isinstance(value.get('decisions'),list):
                    mapped=[]
                    for d in rows:
                        wire=d.get('candidate_id') if isinstance(d,dict) else None
                        if isinstance(wire,str) and wire in refs and refs[wire]['task_id']==tid:
                            mapped.append(dict(d,candidate_id=refs[wire]['candidate_id']))
                    local['value']=dict(value,decisions=mapped)
                votes=new_vote(local,packet,cs);audits[tid]=votes
                for key,d in votes['decisions'].items():
                    c['prior_evidence'][key].append(dict(epoch='residual-v1',judge=req['judge'],provider=req['provider'],
                        model=r.policy['config']['judges'][req['judge']]['model'],request_id=req['id'],
                        operation_key=entry['key'],operation_hash=entry['artifact_hash'],decision=d))
            new_audits[req['id']]=dict(cases=audits,unknown_ids=unknown_ids,
                unassigned_items=[d for d in rows if not isinstance(d,dict) or not isinstance(d.get('candidate_id'),str) or d['candidate_id'] not in refs])
        else:
            tid=req['binding']['task_ids'][0];c=cases[tid];packet=c['packet']
            ex=extraction(parsed.get('value'),packet,parsed['valid'],parsed.get('reason'))
            if ex.get('valid'):
                for event,info in ex['reported_coverage'].items():
                    if info['detected']=='no' and any(x['event']==event for x in ex['candidates']):
                        ex['coverage'][event]={'status':'uncertain','reason':'Detected=no contradicts returned event candidates'}
            new_audits[req['id']]=ex
            field='extractor' if req['judge']=='J1' else 'auditor';effective=copy.deepcopy(c[field])
            effective['valid']=ex.get('valid',False)
            effective['reviewed_all']=ex.get('reviewed_all',dict(status='uncertain',reason='Fresh coverage unavailable'))
            for e in req['view']['coverage_events']:
                effective['coverage'][e]=ex.get('coverage',{}).get(e,dict(status='uncertain',reason='Fresh coverage incomplete'))
            if ex.get('valid'):
                effective['corrections']=list({digest(x):x for x in effective.get('corrections',[])+ex['corrections']}.values())
                known={x['id'] for x in c['original_candidates']}
                for candidate in canonical.merge(packet,[('residual-coverage',ex['candidates'])]):
                    if candidate['id'] not in known:
                        discoveries.append(dict(task_id=tid,request_id=req['id'],candidate=candidate,operation_key=entry['key']))
                        effective['coverage'][candidate['event']]=dict(status='uncertain',reason='New candidate outside frozen population; separate approved plan required')
            c[field]=effective
    final={}
    for tid,c in cases.items():
        resolutions={key:resolve(es) for key,es in c['prior_evidence'].items()}
        phase=dict(candidates={key:dict(status=d['status'],prior_ack_ids=d['prior_ack_ids'],initial_agreement=d['status']!='uncertain',adjudicated=False)
                              for key,d in resolutions.items()},initial_agreement=all(d['status']!='uncertain' for d in resolutions.values()),adjudicated=False)
        outcome=old_decisions.finalize(c['packet'],c['candidates'],[phase],c['extractor'],c['auditor'])
        for d in list(outcome['events'].values())+[outcome['substitution']]:d['rationale']='AUDIT-INFORMED RESIDUAL REVIEW. '+d['rationale']
        final[tid]=dict(outcome=outcome,resolutions=resolutions,evidence=c['prior_evidence'],effective_coverage=dict(primary=c['extractor'],audit=c['auditor']),
            supported_P_evidence=[x for x in c['candidates'] if x['event']=='P' and resolutions[x['id']]['status']=='present'])
    return dict(cases=final,pending_requests=pending,new_response_audits=new_audits,new_candidate_discoveries=discoveries,
        automatic_J3_calls=0,primary_failure_families=['M','O'],observational_diagnostic='P',
        provenance='Audit-informed hybrid historical/residual review, not independent confirmation. No edit semantic verification or intervention approval.')


def export(output):
    with run_lock(Path(output)/'locks'):
        r=Review(output);data=results(r)
        if data['pending_requests']:raise ValueError('Unattempted/ambiguous frozen requests; export blocked (no implicit calls)')
        side=freeze(r.root/'residual-observations.json',dict(version=VERSION,plan_hash=r.plan['artifact_hash'],history=r.history.binding,**data))
        cases={}
        for tid,c in data['cases'].items():
            outcome=c['outcome'];events=outcome['events'];m,o=events['erasure'],events['override'];stratum=None
            if o['status']=='present':stratum='mixed' if m['status']=='present' and m['span'][0]<o['span'][0] else 'clean' if m['status']=='absent' or (m['status']=='present' and m['span'][0]>=o['span'][0]) else 'unknown_erasure_history'
            cases[tid]=dict(world=r.plan['cases'][tid]['packet']['world'],events=events,
                source_row_hash=r.plan['cases'][tid]['packet']['source_row_hash'],initial_agreement=outcome['initial_agreement'],override_stratum=stratum)
        manifest=freeze(r.root/'annotation-manifest-v5-residual.json',dict(protocol=PROTOCOL,
            source=r.history.review.source_original.binding_at(r.root),code_hash=source_hash(),method=VERSION,
            review_plan_hash=r.plan['artifact_hash'],policy_hash=r.policy['policy_hash'],cases=cases,
            reviews=dict(sidecar='residual-observations.json',artifact_hash=side['artifact_hash']),
            disagreements=[t for t,c in cases.items() if not c['initial_agreement']],
            primary_failure_families=['M','O'],supporting_annotations=['A','C','X'],
            retrospective_provenance=dict(independent_validation=False,audit_informed=True,history=r.history.binding),
            blinding='Unchanged full source text; no prior votes, final outcomes or intervention results sent to judges.',
            adjudication='None. Valid cross-provider disagreement remains uncertain. No edit certification.'))
        read_manifest(r.root/'annotation-manifest-v5-residual.json',r.history.review.source_original)
        return manifest
