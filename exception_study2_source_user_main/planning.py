"""Freeze the authoritative 332 origins, verified contexts, prior evidence and analysis."""
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5.scoring import checkpoints
from exception_study2_source_report.tokenizer import Tokenizer
from exception_study2_source_report_v2.planning import query as origin_query
from exception_study2_source_user_pilot.rendering import bridge
from . import VERSION,INTERFACE,RENDERER,PARSER,MESSAGE,BUDGET,NAMESPACE,CUTS,EXCLUDED,INVENTORY,ANALYSIS,INTERPRETATION
from .integrity import contract,revision,separate,artifact_files
from .evidence import Evidence,raw_join_evidence
from .rendering import append_prefix


def verified_origins(e):
    source=e.remaining;tok=e.tokenizer;main=[];excluded=[]
    if [w['id'] for w in source.worlds]!=[f'staged-v5-{i:03d}' for i in range(4,60)]:
        raise ValueError('Required fixed 56-world population differs')
    tasks=[t for t in source.tasks if t['framing']=='original' and t['arm']=='visible']
    if len(tasks)!=112:raise ValueError('Exactly 112 original-visible trajectories required')
    for t in tasks:
        row=source.rows[t['id']]
        if row['status']!='returned':raise ValueError('Required original trajectory unavailable')
        cuts={c['name']:c for c in checkpoints(row)}
        for k in CUTS:
            cut=cuts['fixed/'+str(k)]
            if not cut['eligible']:
                excluded.append(dict(task_id=t['id'],world=t['world'],source_row_hash=row['artifact_hash'],checkpoint=k,
                    reason=cut['reason'],original_tokens=len(row['raw']['tokens']),natural_final_answer=row['score']))
                continue
            q=origin_query(tok,row,k,'main');q['boundary']=cut;q['legacy']={}
            for i,cue in enumerate(source.plan['config']['readout_cues']):
                key=digest([t['id'],k,cue]);old=e.legacy.get(key)
                if old is None or old['status']!='returned':raise ValueError('Required saved cue join unavailable; no backfill')
                q['legacy'][str(i)]=dict(computation_id=key,cue_text=cue,**old)
            q.pop('id');q.pop('query_hash');q['query_hash']=digest(q);q['id']='v5/source-report-v2/'+q['query_hash'];main.append(q)
    if (main!=e.origin['main'] or excluded!=e.origin['exclusions'] or len(main)!=332
        or [(x['task_id'],x['checkpoint']) for x in excluded]!=[(tid,512) for tid in EXCLUDED]):
        raise ValueError('Authoritative 332 origins/664 joins/four exclusions differ; population cannot shrink')
    if {str(k):sum(q['checkpoint']==k for q in main) for k in CUTS}!=INVENTORY['checkpoints']:
        raise ValueError('Checkpoint inventory differs')
    return main,excluded


def make_plan(e,raw_values):
    origins,excluded=verified_origins(e);tok=e.tokenizer;bridges={};queries=[]
    for origin in origins:
        row=e.remaining.rows[origin['task_id']];t=row['task'];tid=t['id']
        if tid not in bridges:
            # The unchanged pilot builder receives ORIGINAL input IDs, never a saved reasoning prefix.
            bridges[tid]=bridge(tok,t['prompt'],t['target_plate'],row['input_ids'])
        q=dict(origin_query=origin,origin_query_id=origin['id'],origin_query_hash=origin['query_hash'],
            **{k:origin[k] for k in ('task_id','world','variant','checkpoint','expected','pattern','target_plate','source_row_hash','parent_rows','boundary','natural_final_answer','legacy')},
            original_user_prompt=t['prompt'],interface_version=INTERFACE,parser_version=PARSER,budget=BUDGET,capture_at=[],
            **append_prefix(tok,row,origin,bridges[tid]))
        q['query_hash']=digest(q);q['id']=NAMESPACE+q['query_hash'];queries.append(q)
    if len({q['id'] for q in queries})!=332 or len(bridges)!=112:raise ValueError('Duplicate or incomplete main contexts')
    return dict(version=VERSION,code_contract=contract(),interface_version=INTERFACE,renderer_version=RENDERER,
        parser_version=PARSER,message_template=MESSAGE,inventory=INVENTORY,analysis=ANALYSIS,interpretation=INTERPRETATION,
        parent_pilot=e.pilot_binding,origin_plan_hash=e.origin['artifact_hash'],source=e.binding,
        backend=e.origin['backend'],backend_hash=e.origin['backend_hash'],tokenizer=tok.identity,
        generation_settings=e.origin['generation_settings'],historical_revision=e.origin['source']['historical_revision'],
        queries=queries,exclusions=excluded,legacy_raw_evidence_hash=digest(raw_values),
        planned_input_token_occurrences=sum(len(q['context_ids']) for q in queries),
        source_rows={tid:e.remaining.rows[tid]['artifact_hash'] for tid in bridges},
        new_pilot_generations=0,original_generations=0,historical_readout_reruns=0,judge_calls=0,interventions=0,
        next_stage='STOP_REVIEW_MAIN')


def context_text(q,tok):
    metadata={k:q[k] for k in ('id','origin_query_id','task_id','checkpoint','expected','target_plate','old_context_hash','prefix_hash','bridge_hash','context_hash','role_boundaries','empty_old_assistant_closed')}
    return ('AUDIT METADATA ONLY — NOT PART OF MODEL INPUT\n'+json.dumps(metadata,ensure_ascii=False,indent=2)
        +'\n\nEXACT DECODED MODEL INPUT STARTS BELOW\n'+tok.decode_all(q['context_ids']))


def resolve_locations(pilot,originals,readouts,tokenizer_dir):
    return {k:str(Path(v).resolve()) for k,v in dict(pilot=pilot,originals=originals,readouts=readouts,tokenizer=tokenizer_dir).items()}


def prepare(pilot,originals,readouts,tokenizer_dir,output):
    loc=resolve_locations(pilot,originals,readouts,tokenizer_dir)
    pp=sealed_read(Path(loc['pilot'])/'pilot-plan.json')
    out=separate(output,*loc.values(),pp['backend']['config']['model_dir'])
    with run_lock(out):
        if any(p.name!='run.lock' for p in out.iterdir()):raise ValueError('Output exists; inspect/resume the SAME output, never resample')
        tok=Tokenizer(loc['tokenizer']);e=Evidence(loc['pilot'],loc['originals'],loc['readouts'],tok)
        values=raw_join_evidence(e,loc['readouts']);p=freeze(out/'main-plan.json',make_plan(e,values))
        freeze(out/'locations.json',loc);freeze(out/'legacy-values.json',dict(values=values,source=e.binding))
        freeze(out/'pilot-snapshot-manifest.json',dict(files=e.snapshot_files,scientific_identity=e.pilot_binding['immutable_manifest_hash']))
        for name in e.snapshot_files:
            target=out/'pilot-evidence'/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write((e.root/name).read_bytes())
        for tid in p['source_rows']:freeze(out/'source-evidence'/(digest(tid)+'.json'),e.remaining.rows[tid])
        for i,q in enumerate(p['queries']):
            path=out/'contexts'/f'{i:03d}.txt';path.parent.mkdir(exist_ok=True)
            with path.open('x') as f:f.write(context_text(q,tok))
        freeze(out/'preparation.json',dict(plan_hash=p['artifact_hash'],code_contract=p['code_contract'],extension_revision=revision(),
            real_tokenizer_contexts_validated=332,distinct_original_bridge_validations=112,model_loads=0,inference_calls=0))
        return p


class Context:
    def __init__(self,output):
        self.out=Path(output).resolve();self.plan=sealed_read(self.out/'main-plan.json');p=self.plan
        if p.get('version')!=VERSION or p.get('code_contract')!=contract():raise ValueError('Main code/protocol identity mismatch')
        self.locations=sealed_read(self.out/'locations.json');loc=self.locations
        separate(self.out,loc['pilot'],loc['originals'],loc['readouts'],loc['tokenizer'],p['backend']['config']['model_dir'])
        self.tokenizer=Tokenizer(loc['tokenizer']);self.evidence=Evidence(loc['pilot'],loc['originals'],loc['readouts'],self.tokenizer)
        values=raw_join_evidence(self.evidence,loc['readouts'])
        if {k:v for k,v in p.items() if k!='artifact_hash'}!=make_plan(self.evidence,values):
            raise ValueError('Frozen main source/joins/context/backend/analysis identity mismatch')
        manifest=sealed_read(self.out/'pilot-snapshot-manifest.json')
        if (manifest['scientific_identity']!=p['parent_pilot']['immutable_manifest_hash']
            or artifact_files(self.out/'pilot-evidence')!=manifest['files']
            or {n:h for n,h in manifest['files'].items() if n not in ('report.json','report.md')}!=p['parent_pilot']['immutable_manifest']):
            raise ValueError('Immutable pilot snapshot differs')
        raw=sealed_read(self.out/'legacy-values.json')
        if raw['values']!=values or raw['source']!=p['source']:raise ValueError('Frozen historical readout values differ')
        rows={x.name:sealed_read(x) for x in (self.out/'source-evidence').glob('*.json')}
        if rows!={digest(tid)+'.json':self.evidence.remaining.rows[tid] for tid in p['source_rows']}:
            raise ValueError('Main source-row audit snapshot differs')
        if {x.name:x.read_text() for x in (self.out/'contexts').iterdir()}!={f'{i:03d}.txt':context_text(q,self.tokenizer) for i,q in enumerate(p['queries'])}:
            raise ValueError('Readable main contexts differ')
        prep=sealed_read(self.out/'preparation.json')
        if prep['plan_hash']!=p['artifact_hash'] or prep['code_contract']!=contract() or prep.get('real_tokenizer_contexts_validated')!=332:
            raise ValueError('All-context offline tokenizer preparation missing')
        self.queries={q['id']:q for q in p['queries']}
