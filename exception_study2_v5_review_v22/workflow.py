"""Versioned batching over the existing v5 source and shared no-retry journal."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.core import source_hash
from exception_study2_v5.runner import Source,bound_source
from exception_study2_v5.review.workflow import read_manifest
from exception_study2_v5_judges.workflow import _separate
from exception_study2_v5_review_v2.workflow import source_packets,DeadlineTransport
from exception_study2_v5_review_v2.candidates import structural_candidates,merge
from . import VERSION
from .policy import freeze_policy
from .journal import Journal
from .providers import payload
from .decisions import extraction,partial_vote,reconcile,finalize
from .batches import freeze_batches,filter_candidates,partition


def prepare(source,output,config,scope='pilot'):
    src=Source(source,scope=scope);out=Path(output).resolve();_separate(src,out)
    policy=freeze_policy(config);packets=source_packets(src)
    if out.exists() and any(out.iterdir()) and not (out/'review-plan-v22.json').exists():raise ValueError('Fresh separate v2.2 output required')
    with run_lock(out/'locks'):
        if (out/'review-plan-v22.json').exists():
            r=Review(out)
            if r.source_original.binding!=src.binding or r.policy!=policy:raise ValueError('Frozen v2.2 plan differs')
            return r.plan
        revision=subprocess.run(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True,text=True).stdout.strip()
        freeze(out/'policy-v22.json',policy)
        return freeze(out/'review-plan-v22.json',dict(version=VERSION,protocol=PROTOCOL,source=src.binding_at(out),
            scientific_source_hash=source_hash(),policy_hash=policy['policy_hash'],code_revision=revision,scope=scope,
            packets=packets,case_ids=list(packets),source_measurement=src.execution['mode'],
            global_request_ceiling=policy['config']['limits']['max_calls'],batch_target=policy['config']['batch_size'],
            note='Fresh v2.2 policy, not continuation of historical v2.1 requests. Batch requests freeze after extraction and before any verification dispatch.',
            blinding='Original prompt/table and pre-answer text only; no final outcomes, other votes or intervention results.'))


class Review:
    def __init__(self,output):
        self.root=Path(output).resolve();self.plan=sealed_read(self.root/'review-plan-v22.json')
        saved=sealed_read(self.root/'policy-v22.json');self.policy=freeze_policy(saved['config'])
        if self.policy!={k:v for k,v in saved.items() if k!='artifact_hash'}:raise ValueError('Frozen v2.2 policy/code changed')
        self.source_original=bound_source(self.plan['source'],self.root);_separate(self.source_original,self.root)
        packets=source_packets(self.source_original)
        if (self.plan['version']!=VERSION or self.plan['protocol']!=PROTOCOL or self.plan['scientific_source_hash']!=source_hash()
            or self.plan['policy_hash']!=self.policy['policy_hash'] or self.plan['packets']!=packets or self.plan['case_ids']!=list(packets)):
            raise ValueError('Frozen v2.2 source/population changed')
        self.source=SimpleNamespace(case_binding=self.case_binding)
    def case_binding(self,key):
        unit,tid=key.split(':',1);phase,batch=unit.split('/',1)
        if phase not in ('primary','audit'):raise ValueError('Unknown phase')
        if batch!='extract':
            bundle=sealed_read(self.path(tid,phase+'-batches'))
            matches=[b for b in bundle['batches'] if b['id']==batch]
            if len(matches)!=1:raise ValueError('Unknown/unfrozen batch')
            batch_hash=digest(matches[0])
        else:batch_hash=None
        p=self.plan['packets'][tid]
        return dict(task_id=key,original_task_id=tid,phase=phase,batch_id=batch,batch_hash=batch_hash,
            source_hash=self.source_original.hash,trajectory_hash=p['source_row_hash'],view_hash=digest(p),review_plan_hash=self.plan['artifact_hash'])
    def path(self,tid,name):return self.root/'cases'/digest(tid)/(name+'.json')
    def call(self,journal,tid,phase,unit,judge,role,view):
        entry=journal.call(phase+'/'+unit+':'+tid,judge,role,0,view)
        if entry is not None and any(entry['identity'].get(k)!=v for k,v in self.case_binding(phase+'/'+unit+':'+tid).items()):raise ValueError('Operation binding differs')
        return entry


def journal_for(review,live=False,transport=None,max_calls=None,wall_seconds=None,clock=None):
    wall=review.policy['config']['limits']['wall_seconds']
    if wall_seconds is not None:
        if type(wall_seconds) not in (int,float) or not 0<wall_seconds<=wall:raise ValueError('Wall override must tighten frozen limit')
        wall=wall_seconds
    if live and review.source_original.execution['mode']!='LIVE_LOCAL':raise ValueError('Live judging requires real-model originals')
    j=Journal(review,live,transport,max_calls,wall,clock)
    if live:j.transport=DeadlineTransport(j,j.transport)
    return j


def extract_phase(r,j,tid,phase):
    p=r.plan['packets'][tid];judge='J1' if phase=='primary' else 'J2';role='draft' if phase=='primary' else 'verify'
    entry=r.call(j,tid,phase,'extract',judge,role,p)
    if entry is None:return None
    parsed=entry['parsed'];result=extraction(parsed.get('value'),p,parsed['valid'],parsed.get('reason'))
    return freeze(r.path(tid,phase+'-extraction'),dict(operation_key=entry['key'],operation_hash=entry['artifact_hash'],**result))


def verify_phase(r,j,tid,phase,candidates,force_ids=()):
    p=r.plan['packets'][tid]
    source_ref=dict(review_plan_hash=r.plan['artifact_hash'],source_hash=r.source_original.hash,source_row_hash=p['source_row_hash'])
    bundle=freeze(r.path(tid,phase+'-batches'),freeze_batches(p,candidates,phase,source_ref,r.policy,r.policy['config']['batch_size']))
    results=[];judges=r.policy['config']['judges']
    for batch in bundle['batches']:
        votes={};cs=batch['candidates'];force=bool(set(force_ids)&{c['id'] for c in cs})
        for judge in ('J1','J2','J3'):
            if judge=='J3' and not (force or reconcile(cs,votes,judges)['needs_j3']):break
            if payload(judges[judge],r.policy['rubrics']['detect'],r.policy['schemas']['detect'],batch['view'])!=batch['requests'][judge]:raise ValueError('Frozen request changed')
            entry=r.call(j,tid,phase,batch['id'],judge,'adjudicate' if judge=='J3' else 'initial',batch['view'])
            if entry is None:return None
            parsed=entry['parsed'];v=partial_vote(parsed.get('value'),p,cs,parsed['valid'],parsed.get('reason'))
            votes[judge]=freeze(r.path(tid,phase+'/'+batch['id']+'-'+judge),dict(operation_key=entry['key'],operation_hash=entry['artifact_hash'],**v))
        results.append(reconcile(cs,votes,judges))
    combined=dict(candidates={k:v for result in results for k,v in result['candidates'].items()},
        initial_agreement=all(x['initial_agreement'] for x in results),adjudicated=any(x['adjudicated'] for x in results))
    return dict(combined,batch_ids=[b['id'] for b in bundle['batches']],excluded=bundle['excluded'])


def case(r,j,tid):
    p=r.plan['packets'][tid]
    if not p['original_available']:return finalize(p,[],[],{}, {})
    ex=extract_phase(r,j,tid,'primary')
    if ex is None:return None
    paths=[('structural',structural_candidates(p)),('semantic-extractor',ex['candidates'])]
    primary_cs=merge(p,paths);primary=verify_phase(r,j,tid,'primary',primary_cs)
    if primary is None:return None
    audit=extract_phase(r,j,tid,'audit')
    if audit is None:return None
    audit_paths=[('negative-audit',audit['candidates'])];audit_cs=merge(p,audit_paths)
    checked=verify_phase(r,j,tid,'audit',audit_cs)
    if checked is None:return None
    shared=set(primary['candidates'])&set(checked['candidates'])
    conflicts=[k for k in shared if {primary['candidates'][k]['status'],checked['candidates'][k]['status']}=={'present','absent'}]
    if conflicts:
        primary=verify_phase(r,j,tid,'primary',primary_cs,conflicts)
        if primary is None:return None
        checked=verify_phase(r,j,tid,'audit',audit_cs,conflicts)
        if checked is None:return None
    cs,excluded=filter_candidates(merge(p,paths+audit_paths))
    result=finalize(p,cs,[primary,checked],ex,audit)
    return dict(result,extractor=ex,negative_audit=audit,phases=dict(primary=primary,audit=checked),
                candidates=cs,excluded=excluded,source_row_hash=p['source_row_hash'])


def run(output,live=False,transport=None,max_calls=None,wall_seconds=None,clock=None):
    with run_lock(Path(output)/'locks'):
        r=Review(output);j=journal_for(r,live,transport,max_calls,wall_seconds,clock);report=dict(complete=False,cases={})
        try:
            for tid in r.plan['case_ids']:
                result=case(r,j,tid)
                if result is None:break
                freeze(r.path(tid,'resolution-v22'),result);report['cases'][tid]=result
            report['complete']=len(report['cases'])==len(r.plan['case_ids'])
        finally:
            metrics=j.finish('v22-review',r.plan['scope']);freeze(r.root/'reports'/(metrics['id']+'.json'),dict(report,metrics=metrics))
    return metrics


def inspect(output):
    r=Review(output);cases={}
    for tid,p in r.plan['packets'].items():
        cs=merge(p,[('structural',structural_candidates(p))]);kept,excluded=filter_candidates(cs)
        cases[tid]=dict(structural_candidates=len(cs),kept=len(kept),excluded=len(excluded),initial_projected_batches=len(partition(kept,r.policy['config']['batch_size'])),resolved=r.path(tid,'resolution-v22').exists())
    return dict(version=VERSION,cases=cases,limits=r.policy['config']['limits'],note='Projection excludes unknown semantic extraction/audit additions. No calls or model loading.')


def export(output):
    with run_lock(Path(output)/'locks'):
        r=Review(output);j=journal_for(r,max_calls=0);cases={};sidecar={}
        for tid in r.plan['case_ids']:
            saved=sealed_read(r.path(tid,'resolution-v22'));result=case(r,j,tid)
            if result is None or saved!={**result,'artifact_hash':digest(result)}:raise ValueError('Incomplete or non-reproducible journal resolution')
            events=result['events'];m,o=events['erasure'],events['override'];stratum=None
            if o['status']=='present':stratum='mixed' if m['status']=='present' and m['span'][0]<o['span'][0] else 'clean' if m['status']=='absent' or (m['status']=='present' and m['span'][0]>=o['span'][0]) else 'unknown_erasure_history'
            cases[tid]=dict(world=r.plan['packets'][tid]['world'],events=events,source_row_hash=r.plan['packets'][tid]['source_row_hash'],initial_agreement=result['initial_agreement'],override_stratum=stratum)
            sidecar[tid]=saved
        side=freeze(r.root/'observations-v22.json',dict(version=VERSION,source=r.source_original.binding_at(r.root),cases=sidecar,review_plan_hash=r.plan['artifact_hash']))
        manifest=freeze(r.root/'annotation-manifest-v5.json',dict(protocol=PROTOCOL,source=r.source_original.binding_at(r.root),code_hash=source_hash(),
            review_plan_hash=r.plan['artifact_hash'],method=VERSION,policy_hash=r.policy['policy_hash'],cases=cases,
            disagreements=[t for t,c in cases.items() if not c['initial_agreement']],reviews=dict(sidecar='observations-v22.json',artifact_hash=side['artifact_hash']),
            blinding=r.plan['blinding'],adjudication='Independent provider-family support; conditional single J3 slot per immutable batch. No edit verification.'))
        read_manifest(r.root/'annotation-manifest-v5.json',r.source_original);return manifest
