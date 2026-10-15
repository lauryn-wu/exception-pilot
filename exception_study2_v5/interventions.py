"""Two separately frozen families; independent arm generation and likelihood journals."""
import json
import re
from pathlib import Path
from exception_pilot.core import digest, rng_for
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.integration import TokenizerOnly
from . import PROTOCOL, ARMS, BUDGET
from .core import source_hash
from .runner import Source, bound_source, model_session
from .scoring import boundary, final_score, validate_raw
from .readouts import score
from .journal import OperationUnavailable
from .review.workflow import read_manifest
from .review.rubric import EDIT_CHECKS, EDIT_RUBRIC

REPLACEMENTS=set(ARMS)-{'unchanged'}

def prepare_edits(source_path, annotations, output, family, scope='pilot'):
    if family not in ('M','O'):raise ValueError('Choose M or O independently')
    source=Source(source_path,scope=scope);ann=read_manifest(annotations,source);cases={}
    for tid,case in ann['cases'].items():
        event=case['events']['erasure' if family=='M' else 'override']
        if event['status']!='present':continue
        row=source.rows[tid];cut=boundary(row,event['span'][1],'after')
        cases[tid]=dict(world=row['task']['world'],source_row_hash=row['artifact_hash'],event=event,cut=cut,override_stratum=case['override_stratum'],
            initial_agreement=case['initial_agreement'],draft=dict(author='',status='unreviewed',reason='',
                replacements={arm:'' for arm in ARMS if arm!='unchanged'}))
    out=Path(output)
    if out.exists() and any(out.iterdir()) and not (out/'edit-preparation-v5.json').exists():raise ValueError('Fresh edit directory required')
    with run_lock(out):
        plan=freeze(out/'edit-preparation-v5.json',dict(protocol=PROTOCOL,family=family,source=source.binding_at(out),
                    code_hash=source_hash(),annotations_hash=ann['artifact_hash'],cases=cases,rubric=EDIT_RUBRIC))
        templates={
            'draft-template.json':dict(preparation_hash=plan['artifact_hash'],cases={tid:c['draft'] for tid,c in cases.items()}),
            'verification-template.json':dict(preparation_hash=plan['artifact_hash'],reviewer='',cases={tid:dict(
                draft_hash='',status='unreviewed',reason='',checks={c:False for c in EDIT_CHECKS}) for tid in cases})}
        for name,data in templates.items():
            if not (out/name).exists():
                with (out/name).open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
    return plan

def build_texts(row,event,cut,draft):
    if not cut['eligible'] or cut['k']>=BUDGET:raise ValueError('No eligible remaining-budget boundary')
    start,end=event['span'];old=event['text'];prefix=row['raw']['text'][:cut['char_end']]
    replacements=draft['replacements']
    if prefix[start:end]!=old or set(replacements)!=REPLACEMENTS:raise ValueError('Exact same span and three edits required')
    if any(not isinstance(s,str) or not s.strip() or s==old for s in replacements.values()) or len(set(replacements.values()))!=3:
        raise ValueError('Three genuinely different nonempty replacements required')
    blind=replacements['value_blind'];meaning=replacements['meaning_control'];explicit=replacements['explicit_value']
    if re.search(r'(?<!\w)[ABC](?!\w)',blind):raise ValueError('Value-blind repair contains a class label')
    gold=row['task']['expected']
    if not re.search(r'(?<!\w)'+gold+r'(?!\w)',explicit):raise ValueError('Explicit repair lacks verified class')
    if not re.search(r'(?<!\w)'+gold+r'(?!\w)',old) and re.search(r'(?<!\w)'+gold+r'(?!\w)',meaning):
        raise ValueError('Meaning control introduces the correct value')
    line_start=prefix.rfind('\n',0,start)+1
    line_end=prefix.find('\n',end);line_end=len(prefix) if line_end<0 else line_end
    in_table=prefix[line_start:line_end].lstrip().startswith('|')
    if in_table:
        if '|' in old or '\n' in old or any('|' in s or '\n' in s for s in replacements.values()):
            raise ValueError('Use a single verified-cell span and form-preserving cell replacements')
    texts={'unchanged':prefix,**{arm:prefix[:start]+text+prefix[end:] for arm,text in replacements.items()}}
    return texts,'table_cell' if in_table else 'prose'

def freeze_edits(output,drafts,verification,tokenizer_dir=None,backend_override=None):
    out=Path(output);prep=sealed_read(out/'edit-preparation-v5.json');source=bound_source(prep['source'],out)
    if prep['code_hash']!=source_hash():raise ValueError('Edit code changed')
    draft=json.loads(Path(drafts).read_text());verified=json.loads(Path(verification).read_text())
    if (draft['preparation_hash']!=prep['artifact_hash'] or verified['preparation_hash']!=prep['artifact_hash']
            or set(draft['cases'])!=set(prep['cases']) or set(verified['cases'])!=set(prep['cases']) or not verified['reviewer']):
        raise ValueError('Complete source-bound drafts and independent verification required')
    backend=backend_override or TokenizerOnly(source,tokenizer_dir or source.plan['config']['model_dir'])
    if digest(backend.identity)!=source.execution['backend_hash']:raise ValueError('Tokenizer/backend identity mismatch')
    cases=[];excluded=[]
    for tid,c in prep['cases'].items():
        row=source.rows[tid];d=draft['cases'][tid];v=verified['cases'][tid]
        if not d['author'] or d['author']==verified['reviewer'] or v['draft_hash']!=digest(d):
            raise ValueError('Verification must bind the exact draft and use an independent reviewer')
        if d['status'] not in ('proposed','excluded') or v['status'] not in ('accepted','excluded','uncertain','invalid'):
            raise ValueError('Unreviewed edits cannot freeze')
        if not d['reason'] or not v['reason']:raise ValueError('Draft and verification justifications required')
        if d['status']=='excluded' or v['status']!='accepted':
            excluded.append(dict(task_id=tid,reason=d['reason']+'; '+v['reason'],status=v['status']));continue
        if set(v['checks'])!=set(EDIT_CHECKS) or any(x is not True for x in v['checks'].values()):
            raise ValueError('Every independent semantic/structure check must pass')
        try:
            texts,form=build_texts(row,c['event'],c['cut'],d)
            ids={arm:backend.encode(text) for arm,text in texts.items()}
            for arm,text in texts.items():
                if backend.decode(ids[arm])!=text or any(t in backend.special_ids for t in ids[arm]):raise ValueError('Exact text/token roundtrip failed')
                if backend.decode(row['input_ids']+ids[arm])!=backend.decode(row['input_ids'])+text:raise ValueError('Prompt/prefix concatenation changed')
            k=c['cut']['k']
            if ids['unchanged']!=row['raw']['tokens'][:k]:raise ValueError('Unchanged original token identity failed')
        except (ValueError,KeyError,TypeError) as exc:
            excluded.append(dict(task_id=tid,reason=str(exc),status='token_or_structure_failure'));continue
        order=source.plan['arm_orders'][tid][prep['family']]
        cases.append(dict(task_id=tid,world=row['task']['world'],framing=row['task']['framing'],family=prep['family'],
            source_row_hash=row['artifact_hash'],event=c['event'],original_k=k,budget=BUDGET-k,form=form,
            texts=texts,prefix_ids=ids,order=order,token_length_deltas={a:len(t)-k for a,t in ids.items()},
            override_stratum=c['override_stratum'],initial_agreement=c['initial_agreement'],
            initial_outcome=row['score']['outcome'],draft=d,verification=v))
    with run_lock(out):
        freeze(out/'edit-drafts-v5.json',draft);freeze(out/'edit-verification-v5.json',verified)
        return freeze(out/'intervention-manifest-v5.json',dict(protocol=PROTOCOL,source=source.binding_at(out),code_hash=source_hash(),
            family=prep['family'],preparation_hash=prep['artifact_hash'],cases=cases,excluded=excluded,
            primary='value_blind-minus-meaning_control',budget_convention='2048-original_k',
            frozen_worlds=sorted({c['world'] for c in cases})))

def intervene(output, **mode):
    with run_lock(output) as out:
        manifest=sealed_read(out/'intervention-manifest-v5.json');source=bound_source(manifest['source'],out)
        if manifest['code_hash']!=source_hash():raise ValueError('Intervention code changed')
        rows=[]
        if not manifest['cases']:
            value=freeze(out/'interventions-v5.json',dict(manifest_hash=manifest['artifact_hash'],rows=[],
                measurement=source.execution['mode'],status='ZERO_ELIGIBLE_CASES',gpu_calls=0))
            from .reporting import intervention_report
            freeze(out/'intervention-summary-v5.json',intervention_report(manifest,value))
            return value
        with model_session(out,source.plan,binding={'manifest_hash':manifest['artifact_hash']},**mode) as session:
            if session.backend_hash!=source.execution['backend_hash']:raise ValueError('Source backend changed')
            for case in manifest['cases']:
                row=source.rows[case['task_id']];arms={}
                if case['source_row_hash']!=row['artifact_hash'] or case['budget']!=BUDGET-case['original_k']:
                    raise ValueError('Frozen original/budget mismatch')
                for arm in case['order']:
                    prefix=case['prefix_ids'][arm];result=dict(status='unattempted',readouts={})
                    if (session.backend.encode(case['texts'][arm])!=prefix or session.backend.decode(prefix)!=case['texts'][arm]
                            or any(t in session.backend.special_ids for t in prefix)):
                        raise ValueError('Frozen arm token identity changed')
                    op='v5/intervene/'+manifest['family']+'/'+case['task_id']+'/'+arm
                    # Sequence readouts and continuations fail independently. No readout tokens enter generation.
                    for ci,cue in enumerate(source.plan['config']['readout_cues']):
                        try:result['readouts'][str(ci)]=score(session,op+'/cue'+str(ci),row['input_ids'],prefix,row['task'],cue)
                        except OperationUnavailable as exc:result.setdefault('readout_failures',{})[str(ci)]=str(exc)
                    try:
                        raw=session.generate(op+'/continuation',row['input_ids']+prefix,case['budget'],stage='edited_continuation')
                        result.update(raw=raw,status='returned')
                        validate_raw(raw,session.backend,case['budget'])
                        result.update(full_text=case['texts'][arm]+raw['text'],
                                      context_hash=digest(row['input_ids']+prefix),fresh_prefill=True,
                                      input_length=len(row['input_ids'])+len(prefix),output_length=len(raw['tokens']))
                        result['score']=final_score(case['texts'][arm]+raw['text'],raw['stopped'],row['task']['expected'])
                        if arm=='unchanged':
                            result['original_suffix_agreement']=raw['tokens']==row['raw']['tokens'][case['original_k']:]
                            result['original_suffix_agreement_gating']=False
                    except OperationUnavailable as exc:result.update(status='unavailable',reason=str(exc))
                    except (ValueError,KeyError,TypeError) as exc:result.update(status='invalid_return',reason=str(exc))
                    arms[arm]=result
                rows.append(dict(task_id=case['task_id'],world=case['world'],source_row_hash=row['artifact_hash'],arms=arms))
        value=freeze(out/'interventions-v5.json',dict(manifest_hash=manifest['artifact_hash'],rows=rows,
                      measurement='MOCK' if session.backend.simulated else 'LIVE'))
        from .reporting import intervention_report
        freeze(out/'intervention-summary-v5.json',intervention_report(manifest,value))
        return value
