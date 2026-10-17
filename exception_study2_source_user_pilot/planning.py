"""Freeze exactly twelve append-only contexts; preparation never accesses weights."""
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_source_report.tokenizer import Tokenizer
from . import VERSION,INTERFACE,PARSER,NAMESPACE,BUDGET,MESSAGE,INVENTORY,LIMITATION
from .integrity import contract,revision,separate,artifact_files
from .parent import Parent,locations
from .rendering import bridge


def make_plan(parent,tok):
    queries=[]
    for case in parent.cases:
        origin=case['query'];old=origin['input_ids']+origin['prefix_ids']
        if origin['checkpoint']!=0 or origin['prefix_ids']:raise ValueError('Only k=0 empty prefixes permitted')
        q=dict(origin_query_id=origin['id'],origin_query_hash=origin['query_hash'],origin_query=origin,
            origin_operation_hash=case['operation']['artifact_hash'],original_user_prompt=parent.prompts[origin['id']],
            **{k:origin[k] for k in ('task_id','kind','world','variant','target_plate','expected','parent_rows','source_row_hash','cell_edit')},
            checkpoint=0,interface_version=INTERFACE,parser_version=PARSER,budget=BUDGET,capture_at=[],
            **bridge(tok,parent.prompts[origin['id']],origin['target_plate'],old))
        q['query_hash']=digest(q);q['id']=NAMESPACE+q['query_hash'];queries.append(q)
    if len(queries)!=12 or len({q['id'] for q in queries})!=12:raise ValueError('Exactly twelve distinct pilot queries required')
    return dict(version=VERSION,code_contract=contract(),interface_version=INTERFACE,parser_version=PARSER,
        message_template=MESSAGE,inventory=INVENTORY,main_planned=0,queries=queries,parent=parent.summary,
        backend=parent.plan['backend'],backend_hash=parent.plan['backend_hash'],tokenizer=tok.identity,
        generation_settings=parent.plan['generation_settings'],historical_revision=parent.plan['source']['historical_revision'],
        source_rows={tid:row['artifact_hash'] for tid,row in parent.sources.items()},
        planned_input_token_occurrences=sum(len(q['context_ids']) for q in queries),
        criterion='All twelve returned answers must have intact raw metadata, terminal EOS, exact whole-response label format and the predeclared source value.',
        interpretation=LIMITATION,original_generations=0,historical_readout_reruns=0,judge_calls=0,interventions=0,
        next_stage_on_completion='STOP_AFTER_PILOT')


def context_text(q,tok):
    meta={k:q[k] for k in ('id','origin_query_id','world','variant','target_plate','expected','old_context_hash','bridge_hash','context_hash','role_boundaries')}
    return json.dumps(meta,indent=2,ensure_ascii=False)+'\n\nEXACT DECODED MODEL CONTEXT (including control tokens):\n'+tok.decode_all(q['context_ids'])


def prepare(parent,output,originals=None,tokenizer_dir=None):
    loc=locations(parent,originals,tokenizer_dir)
    pp=sealed_read(Path(loc['parent'])/'source-report-plan.json')
    out=separate(output,*loc.values(),pp['backend']['config']['model_dir'])
    with run_lock(out):
        if any(p.name!='run.lock' for p in out.iterdir()):raise ValueError('Output exists; inspect/resume the SAME output; never resample')
        tok=Tokenizer(loc['tokenizer']);evidence=Parent(loc['parent'],loc['originals'],tok)
        plan=freeze(out/'pilot-plan.json',make_plan(evidence,tok));freeze(out/'locations.json',loc)
        # Byte copies preserve parent identity. One parent package only, no historical experiment copies.
        for name in evidence.files:
            target=out/'parent-evidence'/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write((evidence.root/name).read_bytes())
        for tid,row in evidence.sources.items():
            freeze(out/'source-evidence'/(digest(tid)+'.json'),row)
        for i,q in enumerate(plan['queries']):
            target=out/'contexts'/f'{i:02d}.txt';target.parent.mkdir(exist_ok=True)
            with target.open('x') as stream:stream.write(context_text(q,tok))
        freeze(out/'preparation.json',dict(plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],
            extension_revision=revision(),real_tokenizer_serialization_validated=True,model_loads=0,inference_calls=0))
        return plan


class Context:
    def __init__(self,output):
        self.out=Path(output).resolve();self.plan=sealed_read(self.out/'pilot-plan.json');p=self.plan
        if p.get('version')!=VERSION or p.get('code_contract')!=contract():raise ValueError('Pilot code/protocol identity mismatch')
        self.locations=sealed_read(self.out/'locations.json');loc=self.locations
        separate(self.out,loc['parent'],loc['originals'],loc['tokenizer'],p['backend']['config']['model_dir'])
        self.tokenizer=Tokenizer(loc['tokenizer']);self.parent=Parent(loc['parent'],loc['originals'],self.tokenizer)
        if {k:v for k,v in p.items() if k!='artifact_hash'}!=make_plan(self.parent,self.tokenizer):
            raise ValueError('Pilot source/rendering/model/plan identity mismatch')
        if artifact_files(self.out/'parent-evidence')!=self.parent.files:raise ValueError('Immutable parent snapshot differs')
        rows={q.name:sealed_read(q) for q in (self.out/'source-evidence').glob('*.json')}
        if rows!={digest(k)+'.json':v for k,v in self.parent.sources.items()}:raise ValueError('Source audit snapshot differs')
        expected={f'{i:02d}.txt':context_text(q,self.tokenizer) for i,q in enumerate(p['queries'])}
        if {q.name:q.read_text() for q in (self.out/'contexts').iterdir()}!=expected:raise ValueError('Readable contexts differ')
        prep=sealed_read(self.out/'preparation.json')
        if prep['plan_hash']!=p['artifact_hash'] or prep['code_contract']!=contract() or prep['real_tokenizer_serialization_validated'] is not True:
            raise ValueError('Offline serialization preparation evidence missing')
        self.queries={q['id']:q for q in p['queries']}
