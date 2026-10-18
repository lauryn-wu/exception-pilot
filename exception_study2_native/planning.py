"""Offline manifests and exact native-template request freezing; no model loading."""
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_continuation.qwen3 import PROFILE
from exception_review.artifacts import freeze, sha
from exception_study2_source_user_pilot.integrity import contract as historical_contract
from exception_study2_source_report.integrity import separate, revision
from . import VERSION, PILOT_BUDGET, BUDGET_POLICY, DECODING
from .design import make_design, historical_plan
from .interface import NativeTokenizer


def contract():
    here=Path(__file__).resolve().parent
    return digest(dict(modules={p.name:sha(p) for p in sorted(here.glob('*.py'))},
        protocol=sha(here.parent/'STUDY2_NATIVE_THINKING_DRAFT_PROTOCOL.md'),
        unchanged_historical_dependencies=historical_contract()))


def fresh(out):
    if any(p.name!='run.lock' for p in out.iterdir()): raise ValueError('Use a fresh output; existing runs must be resumed unchanged')


def design(kind, output, v5_path=None):
    out=separate(output,Path(v5_path).resolve().parent) if v5_path else Path(output).resolve()
    p=historical_plan(v5_path) if v5_path else None
    m=make_design(kind,p)
    with run_lock(out):
        fresh(out)
        if p: freeze(out/'source-v5-plan.json',p)
        frozen=freeze(out/'design.json',dict(m,code_contract=contract(),code_revision=revision()))
        freeze(out/'constraints.json',m['constraints'])
        sample=m['tables'][:4]
        text=['# DRAFT: representative rendered tables','',
              'Metadata below is not added to the model prompt. Row numbers are one-based; header/separator are not data rows.','']
        for t in sample:
            text.extend([f"## {t['world']}: variant {t['variant']}, cue {t['cue_state']}, {t['relation']}",
                         f"Target {t['target_plate']}; recorded {t['expected']}; climate cue {t['pattern']}.",'',t['table'],''])
        (out/'sample-tables.md').write_text('\n'.join(text))
        return frozen


def read_design(root):
    root=Path(root);m=sealed_read(root/'design.json')
    if m['code_contract']!=contract(): raise ValueError('Design code/protocol changed; preserve old design')
    v5=sealed_read(root/'source-v5-plan.json') if (root/'source-v5-plan.json').exists() else None
    expected=make_design(m['design'],v5)
    if any(m[k]!=v for k,v in expected.items()): raise ValueError('Frozen design/manifest identity differs')
    return m


def requests(manifest,tok,cohort,budget):
    if cohort not in ('pilot','main') or type(budget) is not int or budget<1:
        raise ValueError('Explicit cohort and positive integer budget required')
    result=[]
    for c in manifest['cells']:
        if c['cohort']!=cohort:continue
        ids=tok.render(c['prompt'],c['thinking'])
        if len(ids)+budget>32768: raise ValueError('Native context limit exceeded; no automatic truncation')
        request=dict(protocol=VERSION,model=PROFILE,tokenizer=tok.identity,
            prompt=c['prompt'],input_ids=ids,prompt_hash=c['prompt_hash'],input_hash=digest(ids),
            thinking=c['thinking'],decoding=DECODING,seed=c['seed'],budget=budget,budget_policy=BUDGET_POLICY,
            precision='BF16',quantization=None,attention='eager',batch_size=1,
            fresh_prefill=True,expected=c['expected'],cell_id=c['id'])
        result.append(dict(cell=c,request=request,request_hash=digest(request)))
    if len({x['request_hash'] for x in result})!=len(result): raise ValueError('Duplicate scientific request')
    return result


def _prepare(m,tok,loc,out,cohort,budget,review):
    reqs=requests(m,tok,cohort,budget)
    if not reqs: raise ValueError('No requests in the selected cohort')
    p=freeze(out/'plan.json',dict(protocol=VERSION,code_contract=contract(),design=m,
        cohort=cohort,budget_policy=BUDGET_POLICY,budget_review=review,
        requests=reqs,tokenizer=tok.identity,model=PROFILE,decoding=DECODING,budget=budget,
        preparation_revision=revision(),template_mode_switch_validated=True,
        total_input_token_occurrences=sum(len(r['request']['input_ids']) for r in reqs),
        maximum_output_tokens=len(reqs)*budget))
    freeze(out/'locations.json',loc)
    for i,r in enumerate(reqs):
        path=out/'contexts'/f'{i:04d}.txt';path.parent.mkdir(exist_ok=True)
        path.write_text('METADATA OUTSIDE MODEL INPUT\n'+r['cell']['id']+'\n\nEXACT RENDERED INPUT\n'+tok.decode_all(r['request']['input_ids']))
    return p


def prepare(design_dir, tokenizer_dir, model_dir, output):
    """Freeze only the provisional pilot. Main cells remain a scientific manifest."""
    loc={k:str(Path(v).resolve()) for k,v in dict(design=design_dir,tokenizer=tokenizer_dir,model=model_dir).items()}
    out=separate(output,*loc.values())
    with run_lock(out):
        fresh(out);m=read_design(loc['design']);tok=NativeTokenizer(loc['tokenizer'])
        return _prepare(m,tok,loc,out,'pilot',PILOT_BUDGET,None)


def pilot_evidence(output):
    """Read immutable raw pilot operations, never a possibly stale analysis.json."""
    from .execution import journal, state
    from .diagnostics import cases, summarize
    c=Context(output,_require_pilot=True)
    saved,current,mode,ex=journal(c)
    if mode not in ('MOCK','LIVE_LOCAL') or any(state(x['operation'])!='returned' for x in current.values()):
        raise ValueError('Main budget requires the complete returned pilot; unresolved failures/interruption/pending work remain blocked')
    rows=cases(c,current)
    return c,dict(pilot_output=str(c.out),plan_hash=c.plan['artifact_hash'],measurement_mode=mode,
        execution_hash=ex['artifact_hash'],budget=c.plan['budget'],decoding=c.plan['decoding'],
        operations={k:v['artifact_hash'] for k,v in sorted(saved.items())},
        cases=[dict(cell_id=x['cell']['id'],request_hash=x['request_hash'],operation_hash=x['operation_hash'],
                    attempt=x['attempt'],token_count=x['score']['token_count'],truncated=x['score']['truncated'],
                    parsing_status=x['score']['parsing_status'],repetition=x['repetition']) for x in rows],
        diagnostics=summarize(rows))


def freeze_main(pilot_output,output,budget,truncation_review,repetition_review,reason):
    """Explicit human budget decision, offline, in a separate immutable main plan."""
    notes=dict(truncation_review=truncation_review,repetition_review=repetition_review,reason=reason)
    if any(not isinstance(x,str) or not x.strip() for x in notes.values()):
        raise ValueError('Explicit truncation review, repetition review and budget rationale required')
    if type(budget) is not int or budget<1: raise ValueError('Explicit positive integer main budget required')
    out=separate(output,pilot_output)
    with run_lock(pilot_output):
        c,evidence=pilot_evidence(pilot_output)
        separate(out,*c.locations.values())
        with run_lock(out):
            fresh(out)
            review=dict(policy=BUDGET_POLICY,pilot=evidence,budget=budget,**notes,revision=revision())
            return _prepare(c.plan['design'],c.tok,c.locations,out,'main',budget,review)


class Context:
    def __init__(self,output,_require_pilot=False):
        self.out=Path(output).resolve();self.plan=sealed_read(self.out/'plan.json');p=self.plan
        if p['protocol']!=VERSION or p['code_contract']!=contract(): raise ValueError('Frozen protocol/code mismatch')
        cohort=p.get('cohort');budget=p.get('budget');review=p.get('budget_review')
        if p.get('budget_policy')!=BUDGET_POLICY or cohort not in ('pilot','main'):
            raise ValueError('Frozen budget policy/cohort identity mismatch')
        if _require_pilot and cohort!='pilot': raise ValueError('Budget review must reference a pilot plan')
        if cohort=='pilot':
            if budget!=PILOT_BUDGET or review is not None: raise ValueError('Pilot budget identity mismatch')
        else:
            if (not isinstance(review,dict) or review.get('policy')!=BUDGET_POLICY or review.get('budget')!=budget
                or any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('truncation_review','repetition_review','reason'))):
                raise ValueError('Main budget review identity mismatch')
            separate(self.out,review['pilot']['pilot_output'])
            parent,evidence=pilot_evidence(review['pilot']['pilot_output'])
            if evidence!=review['pilot'] or parent.plan['design']!=p['design']:
                raise ValueError('Frozen pilot evidence identity mismatch')
        self.locations=sealed_read(self.out/'locations.json');loc=self.locations
        separate(self.out,loc['design'],loc['tokenizer'],loc['model'])
        m=read_design(loc['design']);self.tok=NativeTokenizer(loc['tokenizer'])
        if (m!=p['design'] or self.tok.identity!=p['tokenizer'] or requests(m,self.tok,cohort,budget)!=p['requests']
            or p['model']!=PROFILE or p['decoding']!=DECODING
            or p.get('template_mode_switch_validated') is not True
            or p.get('maximum_output_tokens')!=len(p['requests'])*budget
            or p.get('total_input_token_occurrences')!=sum(len(r['request']['input_ids']) for r in p['requests'])):
            raise ValueError('Scientific request/model/tokenizer/template/cache identity mismatch')
        self.by_cell={r['cell']['id']:r for r in p['requests']}
        expected={f'{i:04d}.txt':'METADATA OUTSIDE MODEL INPUT\n'+r['cell']['id']+'\n\nEXACT RENDERED INPUT\n'+self.tok.decode_all(r['request']['input_ids']) for i,r in enumerate(p['requests'])}
        if {x.name:x.read_text() for x in (self.out/'contexts').iterdir()}!=expected:
            raise ValueError('Readable prompt provenance differs')
