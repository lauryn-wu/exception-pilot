"""Prepare blinded packets, reconcile independent reviewers, freeze source-bound decisions."""
import copy
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from .. import PROTOCOL
from ..core import source_hash, COHORT_MIN_WORLDS
from ..runner import Source, bound_source
from ..scoring import marker_start
from .rubric import EVENTS, STATUSES, RUBRIC, CERTIFICATES, OVERRIDE_CERTIFICATES

def blinded_view(row):
    text=row['raw']['text'] if row['raw'] and row['status']=='returned' else ''
    marker=marker_start(text)
    return dict(task_id=row['task']['id'], source_prompt=row['task']['prompt'],
                pre_answer_text=text if marker is None else text[:marker],
                original_available=row['status']=='returned', rubric=RUBRIC)

def empty_decision():
    return dict(status='unreviewed',span=None,text=None,anchor=None,subtype=None,rationale='',certificates={})

def prepare_review(source_path, output):
    source=Source(source_path); out=Path(output)
    if out.exists() and any(out.iterdir()) and not (out/'review-plan-v5.json').exists():
        raise ValueError('Fresh review directory required')
    views={tid:blinded_view(row) for tid,row in source.rows.items() if row['task']['arm']=='visible'}
    plan=dict(protocol=PROTOCOL,source=source.binding,code_hash=source_hash(),rubric=RUBRIC,
              views=views,reviewer_slots=['reviewer_1','reviewer_2'],adjudication='third independent reviewer only on disagreement')
    with run_lock(out):
        sealed=freeze(out/'review-plan-v5.json',plan)
        for slot in plan['reviewer_slots']:
            path=out/(slot+'-template.json')
            if not path.exists():
                template=dict(review_plan_hash=sealed['artifact_hash'],reviewer='',cases={tid:{e:empty_decision() for e in EVENTS} for tid in views})
                with path.open('x') as f:json.dump(template,f,indent=2,ensure_ascii=False);f.write('\n')
    return sealed

def anchor(text,start,end):
    return dict(before=text[max(0,start-40):start],after=text[end:end+40])

def validate_decisions(view, decisions):
    if set(decisions)!=set(EVENTS):raise ValueError('All semantic events and miscopy must be reviewed independently')
    text=view['pre_answer_text']
    for event,d in decisions.items():
        if set(d)!=set(empty_decision()) or d['status'] not in STATUSES or not str(d['rationale']).strip():
            raise ValueError('Incomplete event decision')
        if not view['original_available'] and d['status']!='invalid':raise ValueError('Unavailable source is invalid, never absent')
        if d['status']!='present':
            if any(d[k] is not None for k in ('span','text','anchor','subtype')):raise ValueError('Non-present decisions may not invent spans')
            continue
        a,b=d['span']
        if (type(a) is not int or type(b) is not int or not 0<=a<b<=len(text) or text[a:b]!=d['text']
                or d['anchor']!=anchor(text,a,b)):
            raise ValueError('Exact Unicode source span/anchor mismatch')
        anchored=d['anchor']['before']+d['text']+d['anchor']['after']
        if text.count(anchored)!=1:raise ValueError('Anchor must uniquely identify the statement')
        required=set(CERTIFICATES) | (set(OVERRIDE_CERTIFICATES) if event=='override' else set())
        if set(d['certificates'])!=required or not all(v is True for v in d['certificates'].values()):
            raise ValueError('Explicit semantic/first-occurrence certifications required')
        allowed={'erasure':('prose_absence','table_unknown'),'miscopy':('source_value_miscopy',)}.get(event,(event,))
        if d['subtype'] not in allowed:raise ValueError('Wrong event subtype')
    if decisions['override']['status']=='present':
        ack=decisions['acknowledgment']
        if ack['status']!='present' or ack['span'][1]>decisions['override']['span'][0]:
            raise ValueError('Override requires a prior correct explicit acknowledgment')
    return decisions

def decision_key(d):
    return {k:v for k,v in d.items() if k not in ('rationale','certificates')}

def freeze_annotations(output, first, second, adjudication=None):
    out=Path(output);plan=sealed_read(out/'review-plan-v5.json');source=bound_source(plan['source'])
    reviews=[json.loads(Path(p).read_text()) for p in (first,second)]
    ids=[r['reviewer'].strip() for r in reviews]
    if not all(ids) or len(set(ids))!=2:raise ValueError('Two independent named reviewers required')
    for review in reviews:
        if review['review_plan_hash']!=plan['artifact_hash'] or set(review['cases'])!=set(plan['views']):
            raise ValueError('Review source binding/population mismatch')
        for tid,d in review['cases'].items():validate_decisions(plan['views'][tid],d)
    adjud=json.loads(Path(adjudication).read_text()) if adjudication else None
    cases={}; disagreements=[]
    for tid,view in plan['views'].items():
        a,b=[r['cases'][tid] for r in reviews]
        agrees=all(decision_key(a[e])==decision_key(b[e]) for e in EVENTS)
        chosen=a
        if not agrees:
            disagreements.append(tid)
            if (not adjud or not adjud.get('reviewer','').strip() or adjud['reviewer'] in ids
                or adjud.get('review_plan_hash')!=plan['artifact_hash'] or tid not in adjud['cases']):
                raise ValueError('Disagreement requires independent third-review adjudication: '+tid)
            chosen=validate_decisions(view,adjud['cases'][tid])
        m,o=chosen['erasure'],chosen['override']
        stratum=('mixed' if m['status']=='present' and m['span'][0]<o['span'][0] else
                 'clean' if m['status']=='absent' or (m['status']=='present' and m['span'][0]>=o['span'][0]) else 'unknown_erasure_history') if o['status']=='present' else None
        cases[tid]=dict(events=chosen,initial_agreement=agrees,override_stratum=stratum,
                       source_row_hash=source.rows[tid]['artifact_hash'])
    if adjud and set(adjud['cases'])!=set(disagreements):raise ValueError('Adjudication must cover exactly disputed cases')
    with run_lock(out):
        for i,r in enumerate(reviews):freeze(out/f'independent-review-{i+1}-v5.json',r)
        if adjud:freeze(out/'adjudication-v5.json',adjud)
        return freeze(out/'annotation-manifest-v5.json',dict(protocol=PROTOCOL,source=source.binding,code_hash=source_hash(),
            review_plan_hash=plan['artifact_hash'],reviews=reviews,adjudication=adjud,cases=cases,disagreements=disagreements,
            blinding='Original prompt and pre-answer text only; no final outcomes/readouts/intervention results'))

def read_manifest(path,source=None):
    value=sealed_read(path);source=source or bound_source(value['source'])
    if value['source']!=source.binding or value['code_hash']!=source_hash():raise ValueError('Annotation source/code changed')
    expected={tid for tid,r in source.rows.items() if r['task']['arm']=='visible'}
    if set(value['cases'])!=expected:raise ValueError('Every visible response must be reviewed')
    for tid,case in value['cases'].items():
        validate_decisions(blinded_view(source.rows[tid]),case['events'])
        if case['source_row_hash']!=source.rows[tid]['artifact_hash']:raise ValueError('Annotation row changed')
    return value

def freeze_lock(source_path, annotations, output, decision_file):
    source=Source(source_path);manifest=read_manifest(annotations,source)
    from ..reporting import behavioral_report, annotation_report
    report=behavioral_report(source.root); coverage=annotation_report(source,manifest)
    if source.plan['phase']!='selection' or not report['calibration']['passed']:raise ValueError('Selection calibration failed or incomplete')
    decisions=json.loads(Path(decision_file).read_text())
    if (set(decisions)!={'reviewer','rationale','criteria_unchanged','no_selection_on_2a_or_interventions','families'}
        or not decisions['reviewer'] or not decisions['rationale'] or decisions['criteria_unchanged'] is not True
        or decisions['no_selection_on_2a_or_interventions'] is not True or set(decisions['families'])!={'M','O'}):
        raise ValueError('Explicit selection-stage decisions and unchanged-criteria certification required')
    for family in ('M','O'):
        if type(decisions['families'][family]) is not bool:raise ValueError('Explicit boolean family decisions required')
        n=coverage['families'][family]['clean_worlds' if family=='O' else 'worlds']
        if decisions['families'][family] and n<COHORT_MIN_WORLDS:raise ValueError('Insufficient independently reviewed worlds for '+family)
    return freeze(Path(output),dict(protocol=PROTOCOL,source=source.binding,code_hash=source_hash(),
          annotations_hash=manifest['artifact_hash'],coverage=coverage,decisions=decisions,
          backend_hash=source.execution['backend_hash'],mode=source.execution['mode']))

def validate_lock(source,path):
    value=sealed_read(path)
    if value['protocol']!=PROTOCOL or value['source']!=source.binding or value['code_hash']!=source_hash():
        raise ValueError('Selection protocol lock differs')
    return value
