"""Additive candidate-first pipeline. No scientific stages or model loader invoked."""
import json
import signal
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.core import source_hash
from exception_study2_v5.runner import Source, bound_source
from exception_study2_v5.review.workflow import blinded_view, read_manifest
from exception_study2_v5_judges.workflow import target_metadata, _separate
from . import VERSION
from .policy import freeze_policy
from .candidates import packet, structural_candidates, merge, extraction, veto
from .decisions import vote, reconcile, finalize
from .journal import Journal
from .providers import HTTPTransport


def source_packets(source):
    packets={}
    for tid,row in source.rows.items():
        if row['task']['arm']!='visible':continue
        view=blinded_view(row); view.pop('rubric')
        task=row['task']
        view.update(target=target_metadata(task),source_table=task['table'],
                    plates=[line.strip('| ').split(' | ')[0] for line in task['table'].splitlines()[2:]])
        packets[tid]=packet(view)
    return packets


def prepare(source, output, config, scope='pilot'):
    src=Source(source,scope=scope);out=Path(output).resolve();_separate(src,out)
    policy=freeze_policy(config); packets=source_packets(src)
    if out.exists() and any(out.iterdir()) and not (out/'review-plan-v2.json').exists():
        raise ValueError('Fresh, separate v2 output directory required')
    with run_lock(out/'locks'):
        if (out/'review-plan-v2.json').exists():
            review=Review(out)
            if review.source_original.binding!=src.binding or review.policy!=policy:raise ValueError('Existing v2 plan differs')
            return review.plan
        revision=subprocess.run(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],
                                check=True,capture_output=True,text=True).stdout.strip()
        freeze(out/'policy-v2.json',policy)
        return freeze(out/'review-plan-v2.json',dict(version=VERSION,protocol=PROTOCOL,
            scientific_source_hash=source_hash(),source=src.binding_at(out),policy_hash=policy['policy_hash'],
            code_revision=revision,scope=scope,packets=packets,case_ids=list(packets),
            source_measurement=src.execution['mode'],planned_minimum_calls=4*len(packets),
            total_request_ceiling=8*len(packets),
            sample_role='exploratory development; never held-out validation',
            blinding='Source prompt/table and saved pre-answer text only; no scored final answers, votes, 2A or 2B.'))

class Review:
    def __init__(self,output):
        self.root=Path(output).resolve();self.plan=sealed_read(self.root/'review-plan-v2.json')
        saved=sealed_read(self.root/'policy-v2.json'); self.policy=freeze_policy(saved['config'])
        if self.policy!={k:v for k,v in saved.items() if k!='artifact_hash'}:raise ValueError('Frozen v2 policy/code/provider changed')
        self.source_original=bound_source(self.plan['source'],self.root);_separate(self.source_original,self.root)
        packets=source_packets(self.source_original)
        if (self.plan['version']!=VERSION or self.plan['protocol']!=PROTOCOL or self.plan['scientific_source_hash']!=source_hash()
            or self.plan['policy_hash']!=self.policy['policy_hash'] or self.plan['packets']!=packets
            or self.plan['case_ids']!=list(packets)):
            raise ValueError('Frozen source/population/view identity changed')
        self.source=SimpleNamespace(case_binding=self.case_binding)
    def case_binding(self,key):
        phase,tid=key.split(':',1)
        if phase not in ('primary','audit'):raise ValueError('Unknown phase')
        p=self.plan['packets'][tid]
        return dict(task_id=key,original_task_id=tid,phase=phase,source_hash=self.source_original.hash,
                    trajectory_hash=p['source_row_hash'],view_hash=digest(p),review_plan_hash=self.plan['artifact_hash'])
    def path(self,tid,name):return self.root/'cases'/digest(tid)/(name+'.json')
    def call(self,journal,tid,phase,judge,role,view):
        entry=journal.call(phase+':'+tid,judge,role,0,view)
        if entry is None:return None
        if any(entry['identity'].get(k)!=v for k,v in self.case_binding(phase+':'+tid).items()):raise ValueError('Operation source mismatch')
        return entry

class DeadlineTransport:
    """POSIX hard live deadline, in addition to shared journal scheduling cutoff.

    No retries; an alarm interruption is terminal/ambiguous in the shared ledger.
    Only the synchronous main-thread CLI is supported for live calls.
    """
    kind='LIVE'
    def __init__(self,journal,transport): self.journal=journal;self.transport=transport
    def __call__(self,provider,request,timeout):
        if threading.current_thread() is not threading.main_thread() or not hasattr(signal,'setitimer'):
            raise RuntimeError('Live deadline requires POSIX main-thread execution')
        if signal.getitimer(signal.ITIMER_REAL)!=(0.,0.):raise RuntimeError('Existing alarm prevents safe deadline ownership')
        remaining=self.journal.wall_seconds-(self.journal.clock.monotonic()-self.journal.started)
        if remaining<=0:raise TimeoutError('V2 wall deadline reached')
        def expired(signum,frame):raise TimeoutError('V2 wall deadline interrupted request; never resend')
        old=signal.signal(signal.SIGALRM,expired)
        try:
            signal.setitimer(signal.ITIMER_REAL,remaining)
            return self.transport(provider,request,min(timeout,remaining))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

def journal_for(review,live=False,transport=None,max_calls=None,wall_seconds=None,clock=None):
    wall=review.policy['config']['limits']['wall_seconds']
    if wall_seconds is not None:
        if type(wall_seconds) not in (int,float) or not 0<wall_seconds<=wall:raise ValueError('Wall override must tighten frozen limit')
        wall=wall_seconds
    if live and review.source_original.execution['mode']!='LIVE_LOCAL':raise ValueError('Live judging requires real-model originals')
    journal=Journal(review,live,transport,max_calls,wall,clock)
    if live:journal.transport=DeadlineTransport(journal,journal.transport)
    return journal


def _extract(review,journal,tid,phase):
    p=review.plan['packets'][tid]
    entry=review.call(journal,tid,phase,'J1' if phase=='primary' else 'J2','draft' if phase=='primary' else 'verify',p)
    if entry is None:return None
    parsed=entry['parsed']; result=extraction(parsed.get('value'),p,parsed['valid'],parsed.get('reason'))
    return freeze(review.path(tid,phase+'-extraction'),dict(operation_key=entry['key'],operation_hash=entry['artifact_hash'],**result))

def _judge(review,journal,tid,phase,candidates,adjudicate=True,force_j3=False):
    p=review.plan['packets'][tid]; view=dict(p,candidates=candidates)
    votes={}
    if not candidates:return reconcile([],votes)
    for judge in ('J1','J2','J3'):
        if judge=='J3' and (not adjudicate or (not force_j3 and not reconcile(candidates,votes)['needs_j3'])):break
        entry=review.call(journal,tid,phase,judge,'adjudicate' if judge=='J3' else 'initial',view)
        if entry is None:return None
        parsed=entry['parsed']; v=vote(parsed.get('value'),p,candidates,parsed['valid'],parsed.get('reason'))
        votes[judge]=freeze(review.path(tid,phase+'-'+judge),dict(operation_key=entry['key'],operation_hash=entry['artifact_hash'],**v))
    return reconcile(candidates,votes)


def case(review,journal,tid,smoke=False):
    p=review.plan['packets'][tid]
    if not p['original_available']:return finalize(p,[],[],{}, {})
    first=_extract(review,journal,tid,'primary')
    if first is None:return None
    primary=merge(p,[('structural',structural_candidates(p)),('semantic-extractor',first['candidates'])])
    freeze(review.path(tid,'primary-candidates'),dict(candidates=primary))
    primary_votes=_judge(review,journal,tid,'primary',primary,adjudicate=not smoke)
    if primary_votes is None:return None
    # New full-text auditor gets exactly the original packet, never votes or the
    # earlier candidate list. Even obvious already-rejected findings are verified.
    audit=_extract(review,journal,tid,'audit')
    if audit is None:return None
    audited=merge(p,[('negative-audit',audit['candidates'])])
    freeze(review.path(tid,'audit-candidates'),dict(candidates=audited))
    if smoke:return dict(smoke_only=True,complete=False)
    audit_votes=_judge(review,journal,tid,'audit',audited)
    if audit_votes is None:return None
    shared=set(primary_votes['candidates']) & set(audit_votes['candidates'])
    cross_disagreement=any(primary_votes['candidates'][k]['status']!=audit_votes['candidates'][k]['status'] for k in shared)
    if cross_disagreement:
        # Contradictory independent phases also trigger the existing bounded J3
        # slots. Same original evidence, no vote summaries, no new retry identities.
        primary_votes=_judge(review,journal,tid,'primary',primary,force_j3=True)
        if primary_votes is None:return None
        audit_votes=_judge(review,journal,tid,'audit',audited,force_j3=True)
        if audit_votes is None:return None
    all_candidates=merge(p,[('structural',structural_candidates(p)),('semantic-extractor',first['candidates']),('negative-audit',audit['candidates'])])
    resolution=finalize(p,all_candidates,[primary_votes,audit_votes],first,audit)
    resolution['initial_agreement'] &= not cross_disagreement
    return dict(resolution,candidates=all_candidates,extractor=first,negative_audit=audit,
                cross_phase_disagreement=cross_disagreement,
                phases=dict(primary=primary_votes,audit=audit_votes),
                source_row_hash=p['source_row_hash'])


def run(output,live=False,transport=None,max_calls=None,wall_seconds=None,clock=None,stage='all',case_id=None):
    if stage not in ('all','smoke'):raise ValueError('Choose all or smoke')
    if case_id is not None and stage!='smoke':raise ValueError('case_id is only supported for smoke')
    if stage=='smoke':max_calls=min(max_calls,4) if max_calls is not None else 4
    with run_lock(Path(output)/'locks'):
        review=Review(output)
        ids=review.plan['case_ids']
        selection=None
        if stage=='smoke':
            selection_path=review.root/'smoke-selection-v2.json'
            saved=sealed_read(selection_path) if selection_path.exists() else None
            selected=case_id if case_id is not None else saved['case_id'] if saved else next(
                (t for t in ids if review.plan['packets'][t]['original_available']),None)
            if case_id is not None and (not isinstance(case_id,str) or case_id not in ids):
                raise ValueError('Smoke case_id must identify a visible case in this frozen plan')
            if selected is not None and (selected not in ids or not review.plan['packets'][selected]['original_available']):
                raise ValueError('Smoke case original is unavailable')
            selection=dict(review_plan_hash=review.plan['artifact_hash'],case_id=selected,maximum_calls=4)
            if saved and saved!={**selection,'artifact_hash':digest(selection)}:
                raise ValueError('Smoke case selection is immutable; cannot switch cases in this output directory')
            ids=[selected] if selected is not None else []
        journal=journal_for(review,live,transport,max_calls,wall_seconds,clock)
        if selection is not None:freeze(selection_path,selection)
        report=dict(complete=False,cases={})
        try:
            for tid in ids:
                r=case(review,journal,tid,smoke=stage=='smoke')
                if r is None:break
                if stage!='smoke':freeze(review.path(tid,'resolution'),r)
                report['cases'][tid]=r
            report['complete']=stage=='all' and len(report['cases'])==len(ids)
        finally:
            metrics=journal.finish(stage,review.plan['scope'])
            freeze(review.root/'reports'/(metrics['id']+'.json'),dict(report,metrics=metrics))
    return metrics


def inspect(output):
    """Read-only offline summary, including candidate counts and estimated reservations."""
    r=Review(output); counts={}; total=0
    for tid,p in r.plan['packets'].items():
        cs=merge(p,[('structural',structural_candidates(p))])
        counts[tid]=dict(characters=len(p['pre_answer_text']),statements=len(p['statements']),
            structural_candidates=len(cs),by_event={e:sum(c['event']==e for c in cs) for e in 'AM CPOX'.replace(' ','')},
            false_recorded_reconstructions=sum(c['event'] in ('M','X') and not veto(c)
                and c['mechanical']['target']=='yes' and c['mechanical']['comparison'] in ('missing','differs') for c in cs),
            semantics='NOT TESTED unless separately journaled judges completed',
            resolved=r.path(tid,'resolution').exists())
        total+=len(cs)
    return dict(version=VERSION,review_plan_hash=r.plan['artifact_hash'],cases=counts,
                total_structural_candidates=total,call_range=[r.plan['planned_minimum_calls'],r.plan['total_request_ceiling']],
                policy_limits=r.policy['config']['limits'],note='Candidate counts are not event prevalence or validated semantics.')


def export(output):
    """Offline journal-derived revalidation; never sends or fabricates paid calls."""
    with run_lock(Path(output)/'locks'):
        r=Review(output);journal=journal_for(r,max_calls=0)
        cases={};sidecar={};disagreements=[]
        for tid in r.plan['case_ids']:
            saved=sealed_read(r.path(tid,'resolution')); result=case(r,journal,tid)
            if result is None:raise ValueError('Review incomplete; export never calls providers')
            if saved!={**result,'artifact_hash':digest(result)}:raise ValueError('Resolution differs from journal revalidation')
            events=result['events'];m,o=events['erasure'],events['override']
            stratum=None
            if o['status']=='present':
                stratum='mixed' if m['status']=='present' and m['span'][0]<o['span'][0] else 'clean' if m['status']=='absent' or (m['status']=='present' and m['span'][0]>=o['span'][0]) else 'unknown_erasure_history'
            row=r.source_original.rows[tid]
            cases[tid]=dict(world=row['task']['world'],events=events,source_row_hash=row['artifact_hash'],
                           initial_agreement=result['initial_agreement'],override_stratum=stratum)
            sidecar[tid]=saved
            if not result['initial_agreement']:disagreements.append(tid)
        side=freeze(r.root/'observations-v2.json',dict(version=VERSION,source=r.source_original.binding_at(r.root),
            review_plan_hash=r.plan['artifact_hash'],cases=sidecar,
            note='P and full extraction/judging/reconciliation provenance. Detection does not verify edits.'))
        manifest=freeze(r.root/'annotation-manifest-v5.json',dict(protocol=PROTOCOL,source=r.source_original.binding_at(r.root),
            code_hash=source_hash(),review_plan_hash=r.plan['artifact_hash'],method=VERSION,
            policy_hash=r.policy['policy_hash'],cases=cases,disagreements=disagreements,
            reviews=dict(sidecar='observations-v2.json',artifact_hash=side['artifact_hash']),
            adjudication='Independent conditional J3 on each candidate phase; unresolved preserved',
            blinding=r.plan['blinding']))
        read_manifest(r.root/'annotation-manifest-v5.json',r.source_original)
        return manifest
