"""Fixed design and exact request freezing; tokenizer-only, always offline."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_study2_native.planning import fresh, contract as native_contract
from exception_study2_source_report.integrity import separate, revision
from . import VERSION, SEED, BUDGET, MODEL, REVISION, SAMPLER, ENGINE, RUNTIME, SAMPLING_OPTIONS
from .design import make_design
from .adapter import Tokenizer


def contract():
    here=Path(__file__).parent
    return digest(dict(modules={p.name:sha(p) for p in sorted(here.glob('*.py'))},
        assets=sha(here/'assets.json'),protocol=sha(here.parent/'STUDY2_CURRENT_QWEN_SCREEN_V1.md'),
        reused_native_contract=native_contract()))


def smoke_design():
    prompts=['A catalog records object ZX9 as class B. What class is recorded for ZX9?',
             'The sequence is A, B, C. Which letter is second?']
    from exception_study2_native import FINAL_INSTRUCTION
    cells=[]
    for i,prompt in enumerate(prompts):
        for thinking in (False,True):
            text=prompt+'\n'+FINAL_INSTRUCTION
            cells.append(dict(id=f'smoke-{i}/thinking-{int(thinking)}',world=f'smoke-{i}',block=i,
                thinking=thinking,prompt=text,prompt_hash=digest(text),seed=SEED+i,
                expected='B',pattern=None,variant=0,relation='technical',wording='technical',cohort='smoke'))
    return dict(protocol=VERSION,kind='smoke',cells=cells,counts=dict(responses=8,maximum_output_tokens=8*256),
        note='Four fresh technical responses, then four exact-token-prefix continuations. No semantic calibration. No sampled-suffix equivalence claim.')


def request(cell,tok,budget):
    ids=tok.render(cell['prompt'],cell['thinking']);rendered=tok.decode_all(ids)
    args=dict(enable_thinking=cell['thinking'],preserve_thinking=True)
    if cell['thinking']:args['reasoning_effort']='medium'
    if len(ids)+budget>min(tok.context_limit,ENGINE['max_model_len']):raise ValueError('Context cap exceeded')
    r=dict(protocol=VERSION,model=MODEL,model_revision=REVISION,tokenizer=tok.identity,runtime=RUNTIME,
        input_ids=ids,input_hash=digest(ids),rendered_input=rendered,prompt=cell['prompt'],prompt_hash=cell['prompt_hash'],
        thinking=cell['thinking'],effort='medium' if cell['thinking'] else None,template_args=args,
        sampler=SAMPLER,sampling_options=SAMPLING_OPTIONS,engine=ENGINE,seed=cell['seed'],budget=budget,
        eos_ids=sorted(tok.eos_ids),cell_id=cell['id'],expected=cell['expected'],prefix_token_ids=[])
    return dict(cell=cell,request=r,request_hash=digest(r))


def design(output):
    from exception_study2_native.shortcuts import audit_shortcuts
    m=make_design()
    with run_lock(output):
        out=Path(output);fresh(out)
        d=freeze(out/'design.json',dict(m,code_contract=contract(),code_revision=revision()))
        freeze(out/'shortcut-audit.json',dict(audit_shortcuts(m['tables']),design_hash=d['artifact_hash']))
        return dict(design_hash=d['artifact_hash'],**m['counts'])


def prepare(output,tokenizer_dir,model_dir,design_dir=None,smoke=None,technical=False):
    inputs=[tokenizer_dir,model_dir]+([design_dir] if design_dir else [])+([smoke] if smoke else [])
    out=separate(output,*inputs);tok=Tokenizer(tokenizer_dir)
    if technical:
        if design_dir or smoke:raise ValueError('Separate technical prompts only')
        m=smoke_design();kind='smoke';gate=None;budget=256
    else:
        if not design_dir or not smoke:raise ValueError('Supply frozen design and separate smoke run')
        m=sealed_read(Path(design_dir)/'design.json');expected=make_design()
        if m['code_contract']!=contract() or any(m.get(k)!=v for k,v in expected.items()):raise ValueError('Frozen design changed')
        smoke_context=Context(smoke)
        if smoke_context.plan['kind']!='smoke' or smoke_context.tok.identity!=tok.identity:raise ValueError('Wrong smoke identity')
        gate=dict(path=str(Path(smoke).resolve()),plan_hash=smoke_context.plan['artifact_hash'])
        kind='screen';budget=BUDGET
    reqs=[request(c,tok,budget) for c in m['cells']]
    with run_lock(out):
        fresh(out)
        p=freeze(out/'plan.json',dict(protocol=VERSION,kind=kind,code_contract=contract(),code_revision=revision(),
            model=MODEL,model_revision=REVISION,tokenizer=tok.identity,runtime=RUNTIME,engine=ENGINE,sampler=SAMPLER,
            design=m,requests=reqs,smoke=gate,planned_responses=8 if technical else 384,
            maximum_output_tokens=8*256 if technical else 384*BUDGET,
            total_input_token_occurrences=sum(len(r['request']['input_ids']) for r in reqs)))
        freeze(out/'locations.json',dict(model=str(Path(model_dir).resolve()),tokenizer=str(Path(tokenizer_dir).resolve())))
    return dict(plan_hash=p['artifact_hash'],planned_responses=p['planned_responses'],maximum_output_tokens=p['maximum_output_tokens'],
                input_tokens=p['total_input_token_occurrences'],model_loads=0)


class Context:
    def __init__(self,output):
        self.out=Path(output).resolve();self.plan=sealed_read(self.out/'plan.json');p=self.plan
        if p['protocol']!=VERSION or p['code_contract']!=contract():raise ValueError('Protocol/code changed; preserve frozen run')
        self.locations=sealed_read(self.out/'locations.json');separate(self.out,*[self.locations[k] for k in ('model','tokenizer')])
        self.tok=Tokenizer(self.locations['tokenizer'])
        m=smoke_design() if p['kind']=='smoke' else make_design()
        if p['kind'] not in ('screen','smoke') or any(p['design'].get(k)!=v for k,v in m.items()):raise ValueError('Manifest changed')
        budget=256 if p['kind']=='smoke' else BUDGET
        expected=[request(c,self.tok,budget) for c in m['cells']]
        if (expected!=p['requests'] or p['tokenizer']!=self.tok.identity or p['model']!=MODEL or
            p['model_revision']!=REVISION or p['engine']!=ENGINE or p['sampler']!=SAMPLER or p['runtime']!=RUNTIME or
            p['planned_responses']!=(8 if p['kind']=='smoke' else 384) or
            p['maximum_output_tokens']!=(8*256 if p['kind']=='smoke' else 384*BUDGET) or
            p['total_input_token_occurrences']!=sum(len(r['request']['input_ids']) for r in expected)):
            raise ValueError('Exact request/model/cache identity mismatch')
        self.requests=list(expected)
        if (self.out/'smoke-prefixes.json').exists():
            if p['kind']!='smoke':raise ValueError('Unexpected prefix operations in science screen')
            prefix=sealed_read(self.out/'smoke-prefixes.json');wanted=self.prefix_plan()
            if wanted is None or any(prefix.get(k)!=v for k,v in wanted.items()):raise ValueError('Saved smoke prefix binding differs')
            self.requests+=prefix['requests']
        self.by_cell={r['cell']['id']:r for r in self.requests}

    def prefix_plan(self):
        from exception_study2_v5.journal import operations
        from .execution import opid
        saved=operations(self.out);reqs=[];bindings={}
        for r in self.plan['requests']:
            op=saved.get(opid(r))
            if not op or op['status']!='returned':return None
            if op['request']!=r['request'] or op['plan_hash']!=self.plan['artifact_hash']:raise ValueError('Smoke source mismatch')
            tokens=op['result'].get('tokens',[])
            if len(tokens)<2 or any(type(x) is not int for x in tokens):return None
            k=min(8,len(tokens)-1);prefix=tokens[:k]
            if any(x in self.tok.eos_ids for x in prefix):return None
            q=dict(r['request']);cell=dict(r['cell'],id=r['cell']['id']+'/saved-prefix')
            ids=q['input_ids']+prefix
            q.update(cell_id=cell['id'],input_ids=ids,input_hash=digest(ids),rendered_input=self.tok.decode_all(ids),
                prefix_token_ids=prefix,budget=q['budget']-k,
                prefix_source=dict(operation_hash=op['artifact_hash'],original_request_hash=r['request_hash'],length=k))
            reqs.append(dict(cell=cell,request=q,request_hash=digest(q)));bindings[r['cell']['id']]=op['artifact_hash']
        return dict(plan_hash=self.plan['artifact_hash'],source_operations=bindings,requests=reqs)

    def extend_smoke(self):
        if self.plan['kind']!='smoke' or len(self.requests)>4:return
        p=self.prefix_plan()
        if p:
            freeze(self.out/'smoke-prefixes.json',p)
            self.requests+=p['requests'];self.by_cell={r['cell']['id']:r for r in self.requests}
