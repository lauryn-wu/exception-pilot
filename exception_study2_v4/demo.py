"""Fully synthetic v4 end-to-end smoke test; no weights, network, or real models."""
import argparse
import json
from pathlib import Path
from exception_continuation.backend import MockBackend
from exception_continuation.core import make_plan as scientific_plan
from exception_review.demo import SyntheticJudges
from . import core,runner,readouts
from .review import artifacts,workflow,integration,reporting

class SyntheticBackend(MockBackend):
    identity={'kind':'MOCK_CONDITIONAL_PREFIX_V4_NOT_MODEL_EVIDENCE','special_ids':[0,1000000]}
    def __init__(self):
        plans=[scientific_plan('selection'),scientific_plan('confirmation',selection_lock={'mock':True})]
        self.tasks={t['prompt']:t for p in plans for t in p['tasks']};self.calls=[];self.scores=[]
    def generate(self,ids,budget,capture_at=()):
        self.calls.append(dict(input_ids=list(ids),budget=budget,capture_at=list(capture_at)))
        split=ids.index(1000000);prompt=self.decode(ids[:split]);prefix=self.decode(ids[split+1:]);task=self.tasks.get(prompt)
        if not prefix:
            if task and task['arm']=='direct':text='ANSWER: '+task['expected']
            else:text=self.script[:-1]+(task['pattern'] if task else 'A')
        else:
            # Identical fresh inputs repeat, but differ from uninterrupted suffixes.
            answer=task['expected'] if task and ('is available.' in prefix or 'is '+task['expected']+'.' in prefix) else task['pattern'] if task else 'A'
            text=' A fresh conditional continuation.\nANSWER: '+answer
        tokens=(self.encode(text)+[0])[:budget]
        return dict(tokens=tokens,text=self.decode(tokens),stopped=bool(tokens and tokens[-1]==0),finish='eos' if tokens and tokens[-1]==0 else 'length',
            next_token_logits={str(k):[0.,-1.,-2.] for k in capture_at if k<len(tokens)})
    def score(self,context,candidate):
        self.scores.append((list(context),candidate));tokens=self.encode(candidate)
        label='ABC'.index(candidate.strip());values=[-1.-label*(len(context)%97)/1000 for _ in tokens]
        return dict(tokens=tokens,token_logprobs=values,logprob=sum(values))


def policy_config():
    return dict(policy_name='V4-MOCK-DEMO-NOT-LIVE',live_enabled=False,judges={j:dict(provider='anthropic' if j=='J2' else 'openai',model='synthetic-'+j,max_output_tokens=2048,settings={},contract_verified=False,access_verified=False,rates=dict(input_per_million=1,cached_input_per_million=.1,output_per_million=2,cache_write_per_million=1.25)) for j in ('J1','J2','J3')},limits=dict(max_calls=168,max_estimated_usd=10,timeout_seconds=1))


def demo(output):
    root=Path(output);source=root/'source';review=root/'review';backend=SyntheticBackend()
    core.prepare(source);technical=runner.run(source,technical_only=True,backend_override=backend)
    pause=runner.run(source,backend_override=backend);original_calls=len(backend.calls)
    completed=runner.run(source,complete=True,backend_override=backend)
    artifacts.prepare(source,review,policy_config(),'pilot');r=artifacts.Review(review)
    transport=SyntheticJudges([r.source.rows[t]['task']['prompt'] for t in r.plan('pilot')['case_ids']])
    workflow.run(review,scope='pilot',transport=transport,max_calls=3)
    workflow.run(review,scope='pilot',transport=transport)
    integration.check_tokens(review,'pilot',backend_override=backend);manifest=integration.freeze_edits(review,'pilot')
    fixed=readouts.measure_fixed(source,backend_override=backend)
    integration.freeze_events(source,root/'events',review/'manifests/pilot-statements.json')
    events=integration.measure_events(root/'events',backend_override=backend)
    interventions=integration.intervene(review,'pilot',backend_override=backend)
    report=reporting.report(review,'pilot')
    result=dict(measurement='MOCK',live_model_status='PENDING',technical=technical,pilot=pause,collection=completed,
        generation_calls_at_eight_pause=original_calls,originals_not_resampled=len(backend.calls)==33+48+4*len(manifest['cases']),
        fixed_readout_rows=len(fixed['rows']),event_rows=len(events['rows']),frozen_cases=len(manifest['cases']),
        judge_calls=transport.calls,report_status=report['status'],
        divergent_fresh_controls=sum(r['original_vs_unchanged']['exact_suffix_match'] is False for r in interventions['rows']))
    (root/'smoke-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(demo(a.output),indent=2))
