"""Freeze the one interface and exact saved contexts before any model loading."""
import re
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_review.artifacts import freeze
from exception_continuation.runner import sealed_read
from exception_study2_v5.scoring import checkpoints
from . import VERSION,INTERFACE,PARSER,BUDGET,CUTS,SUFFIX,INVENTORY,BOOTSTRAP_SEED,BOOTSTRAP_SAMPLES
from .integrity import contract,revision,separate
from .prior import prior_evidence
from exception_study2_source_report.tokenizer import Tokenizer,concatenate
from exception_study2_source_report.evidence import Evidence


def missing_prompt(task):
    text=task['prompt'];row=task['target_row'];plate=task['target_plate']
    if text.count(row)!=1 or row.split('|')[1].strip()!=plate:raise ValueError('Target row is not uniquely source-aligned')
    match=re.search(r'\| ([ABC]) \|$',row)
    if not match or match.group(1)!=task['expected']:raise ValueError('Target recorded class differs from metadata')
    start=text.index(row)+match.start(1);end=start+1
    changed=text[:start]+'MISSING'+text[end:]
    audit=dict(source_task_id=task['id'],old_prompt_hash=digest(text),new_prompt_hash=digest(changed),
        old_span=[start,end],old_value=task['expected'],new_value='MISSING',target_plate=plate,
        column='Verified class',only_target_cell_changed=True)
    assert changed[:start]==text[:start] and changed[start+7:]==text[end:]
    return changed,audit


def query(tok,row,k,kind,input_ids=None,expected=None,parents=None,edit=None):
    t=row['task'];original_ids=row['input_ids'] if input_ids is None else input_ids
    if input_ids is not None and k!=0:raise ValueError('Modified-table controls require an empty reasoning prefix')
    prefix=row['raw']['tokens'][:k] if k else []
    suffix=SUFFIX.format(plate=t['target_plate']);suffix_ids,context=concatenate(tok,original_ids+prefix,suffix)
    q=dict(kind=kind,task_id=t['id'],world=t['world'],variant=t['variant'],checkpoint=k,
        expected=expected or t['expected'],pattern=t['pattern'],target_plate=t['target_plate'],
        source_row_hash=row['artifact_hash'],parent_rows=parents or {t['id']:row['artifact_hash']},
        input_ids=original_ids,input_hash=digest(original_ids),prefix_ids=prefix,prefix_hash=digest(prefix),
        suffix=suffix,suffix_ids=suffix_ids,context_ids=context,context_hash=digest(context),
        interface_version=INTERFACE,parser_version=PARSER,budget=BUDGET,capture_at=[],
        cell_edit=edit,natural_final_answer=row['score'] if kind=='main' else None)
    q['query_hash']=digest(q);q['id']='v5/source-report-v2/'+q['query_hash']
    return q


def make_plan(evidence,prior=None):
    tok=evidence.tokenizer;source=evidence.remaining;main=[];cal=[];exclusions=[];eligible={str(k):0 for k in CUTS}
    prior=prior if prior is not None else prior_evidence(None,tok)
    if prior['available'] and (prior['backend_hash']!=source.execution['backend_hash']
        or prior['source_binding']!={k:evidence.binding[k] for k in ('remaining','pilot','historical_execution_hash')}):
        raise ValueError('V2 source/backend does not match the failed v1 run')
    tasks=[t for t in source.tasks if t['framing']=='original' and t['arm']=='visible']
    if [w['id'] for w in source.worlds]!=[f'staged-v5-{i:03d}' for i in range(4,60)]:raise ValueError('Required 56-world population differs')
    for t in tasks:
        row=source.rows[t['id']]
        if row['status']!='returned':raise ValueError('Required original trajectory unavailable: '+t['id'])
        cuts={c['name']:c for c in checkpoints(row)}
        for k in CUTS:
            cut=cuts['fixed/'+str(k)]
            if not cut['eligible']:
                exclusions.append(dict(task_id=t['id'],world=t['world'],source_row_hash=row['artifact_hash'],checkpoint=k,
                    reason=cut['reason'],original_tokens=len(row['raw']['tokens']),natural_final_answer=row['score']))
                continue
            prefix=row['raw']['tokens'][:k];text=tok.decode_all(prefix)
            if (digest(prefix)!=cut['token_hash'] or digest(text)!=cut['text_hash']
                or text!=row['raw']['text'][:cut['char_end']] or any(i in tok.special_ids for i in prefix)
                or tok.encode(text)!=prefix):raise ValueError('Saved exact prefix boundary/hash differs: '+t['id'])
            q=query(tok,row,k,'main');q['boundary']=cut;q['legacy']={}
            for ci,cue in enumerate(source.plan['config']['readout_cues']):
                key=digest([t['id'],k,cue]);old=evidence.legacy.get(key)
                if old is None or old['status']!='returned':raise ValueError('Required saved legacy cue entry unavailable: '+key)
                q['legacy'][str(ci)]=dict(computation_id=key,cue_text=cue,**old)
            # The full query, including joins and exact boundary, is content bound.
            q.pop('id');q.pop('query_hash');q['query_hash']=digest(q);q['id']='v5/source-report-v2/'+q['query_hash']
            main.append(q);eligible[str(k)]+=1
    pilot=evidence.pilot
    if [w['id'] for w in pilot.worlds]!=[f'staged-v5-{i:03d}' for i in range(4)]:raise ValueError('Required four-world calibration population differs')
    for w in pilot.worlds:
        rows=sorted((r for r in pilot.rows.values() if r['task']['world']==w['id'] and r['task']['framing']=='original' and r['task']['arm']=='visible'),key=lambda r:r['task']['variant'])
        if len(rows)!=2 or [r['task']['variant'] for r in rows]!=[0,1]:raise ValueError('Both pilot variants required')
        changed=[];audits=[]
        for row in rows:
            cal.append(query(tok,row,0,'calibration_present'))
            text,audit=missing_prompt(row['task']);changed.append(text);audits.append(audit)
        if changed[0]!=changed[1]:raise ValueError('Pilot MISSING controls are not byte-identical across label variants')
        parents={r['task']['id']:r['artifact_hash'] for r in rows}
        cal.append(query(tok,rows[0],0,'calibration_missing',tok.prompt(changed[0]),'MISSING',parents,
                         dict(prompt=changed[0],variant_edits=audits,variants_byte_identical=True)))
    if {q['expected'] for q in cal if q['kind']=='calibration_present'}!=set('ABC'):raise ValueError('Present controls must cover all three classes')
    inventory=dict(trajectories=len(tasks),eligible_by_checkpoint=eligible,main=len(main),legacy_entries=sum(len(q['legacy']) for q in main),
        excluded=len(exclusions),calibration_present=sum(q['kind']=='calibration_present' for q in cal),
        calibration_missing=sum(q['kind']=='calibration_missing' for q in cal),calibration=len(cal),
        maximum_generations=len(cal)+len(main),maximum_output_tokens=(len(cal)+len(main))*BUDGET)
    if inventory!=INVENTORY:raise ValueError('Audited inventory mismatch; live execution blocked. Expected '+str(INVENTORY)+'; observed '+str(inventory)+'; exclusions '+str(exclusions))
    if len({q['id'] for q in cal+main})!=344:raise ValueError('Duplicate source-report operations')
    settings=dict(budget=BUDGET,capture_at=[],batch_size=1,precision='bfloat16',quantization=None,
        enable_thinking=False,attention='eager',generation_overrides=source.execution['backend']['generation_overrides'],fresh_prefill=True)
    return dict(version=VERSION,code_contract=contract(),prior_v1=prior,interface_version=INTERFACE,parser_version=PARSER,suffix_template=SUFFIX,
        checkpoints=list(CUTS),inventory=inventory,source=evidence.binding,backend=source.execution['backend'],
        backend_hash=source.execution['backend_hash'],tokenizer=tok.identity,generation_settings=settings,
        calibration_gate='All 12 payloads must be well-formed and their first quoted fields complete, valid and correct; EOS is not required after a completed field. Unresolved operations block main.',
        analysis=dict(primary='Source accuracy among all returned replies; unavailable operations excluded with eligible coverage.',
            legacy='First class-token logprob only; newline-inclusive sequence scores are labeled sensitivity.',
            ties='Exact equal maxima: tied_classes retained, no preferred class; ties are neither correct nor wrong preferences.',
            bootstrap_seed=BOOTSTRAP_SEED,bootstrap_samples=BOOTSTRAP_SAMPLES,sampling_unit='world',
            pairs='Same eligible trajectory at both cuts; same world draws preserve variants, checkpoints, and cues.',
            interpretation='Explicit source recoverability; the model may reread the table. Not uninterrupted retention or a causal mechanism.'),
        calibration=cal,main=main,exclusions=exclusions,planned_input_token_occurrences=sum(len(q['context_ids']) for q in cal+main),
        original_generations=0,original_readout_reruns=0,judge_calls=0,interventions=0)


def prepare(originals,readouts,tokenizer_dir,output,v1_output=None):
    out=separate(output,originals,readouts,tokenizer_dir,*([v1_output] if v1_output else []))
    with run_lock(out):
        if any(p.name not in ('run.lock',) for p in out.iterdir()):
            raise ValueError('Output already contains a plan/cache. Use inspect or run with the SAME output; never prepare another run to resample.')
        tok=Tokenizer(tokenizer_dir);evidence=Evidence(originals,readouts,tok)
        value=make_plan(evidence,prior_evidence(v1_output,tok))
        locations=dict(originals=str(Path(originals).resolve()),readouts=str(Path(readouts).resolve()),tokenizer=str(Path(tokenizer_dir).resolve()),v1_output=str(Path(v1_output).resolve()) if v1_output else None)
        plan=freeze(out/'source-report-plan.json',value)
        freeze(out/'locations.json',locations)
        freeze(out/'preparation.json',dict(plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],
            extension_revision=revision(),historical_revision=evidence.remaining.execution['code_revision'],model_loads=0,inference_calls=0))
        return plan


class Context:
    def __init__(self,output):
        self.out=Path(output).resolve();self.plan=sealed_read(self.out/'source-report-plan.json')
        if self.plan.get('version')!=VERSION or self.plan['code_contract']!=contract():
            raise ValueError('Source-report code/protocol identity mismatch. Preserve cache; do not silently rebuild or resample.')
        loc=sealed_read(self.out/'locations.json');self.locations=loc
        separate(self.out,loc['originals'],loc['readouts'],loc['tokenizer'],*([loc['v1_output']] if loc.get('v1_output') else []))
        self.tokenizer=Tokenizer(loc['tokenizer']);self.evidence=Evidence(loc['originals'],loc['readouts'],self.tokenizer)
        if {k:v for k,v in self.plan.items() if k!='artifact_hash'}!=make_plan(self.evidence,prior_evidence(loc.get('v1_output'),self.tokenizer)):
            raise ValueError('Source/context/query/model/plan identity mismatch; live execution blocked')
        self.queries={q['id']:q for q in self.plan['calibration']+self.plan['main']}
