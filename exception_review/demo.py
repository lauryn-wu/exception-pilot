"""Reproducible CPU-only example. Every judge and model response is synthetic."""
import argparse
import json
from pathlib import Path
from exception_continuation import runner
from exception_continuation.backend import MockBackend
from . import artifacts,workflow,integration,reporting
from .policy import ARMS,CRITERIA

class SyntheticJudges:
    kind='MOCK'
    def __init__(self,prompts): self.prompts=prompts; self.calls=0
    def __call__(self,provider,request,timeout):
        self.calls+=1
        content=request.get('input',request.get('messages'))[0]['content']
        view=json.loads(content.split('BEGIN_UNTRUSTED_SOURCE_JSON\n')[1].rsplit('\nEND_UNTRUSTED_SOURCE_JSON',1)[0])
        schema=request.get('text',{}).get('format',request.get('output_config',{}).get('format'))['schema']
        prompt=view['original_prompt']; first=prompt==self.prompts[0]; reject=prompt==self.prompts[1]
        claim='Its verified class is missing.'
        if 'decision' in schema['properties']:
            positive=not (first and request['model']=='synthetic-J2')
            value=dict(decision='present' if positive else 'absent',claim_quote=claim if positive else None,anchor_quote=claim if positive else None,reason='SYNTHETIC fixture')
        elif 'edit_quote' in schema['properties']:
            value=dict(edit_quote=claim,replacements=dict(availability_repair='Its verified class is available.'+(' The class is encoded by alphabet position.' if first and 'fixed_edit_quote' not in view else ''),meaning_control='Its class is difficult to infer.' if reject else 'Its verified class is unavailable.',value_repair='Its verified class is '+view['target_value']+'.'),reason='SYNTHETIC draft')
        else:
            value=dict(source_assertion_concern=None,replacements={a:{c:dict(status='pass',reason='SYNTHETIC criterion result') for c in CRITERIA} for a in ARMS})
            if 'encoded' in view['proposed_bundle']['replacements']['availability_repair']: value['replacements']['availability_repair']['no_extra_hints_or_instructions']=dict(status='fail',reason='Remove the implicit answer hint')
            if reject: value['replacements']['meaning_control']['semantic_role']=dict(status='fail',reason='Difficulty is not false absence')
        if provider=='openai': body=dict(model=request['model'],id='synthetic-response',status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])],usage=dict(input_tokens=100,output_tokens=40))
        else: body=dict(model=request['model'],id='synthetic-message',stop_reason='end_turn',content=[dict(type='text',text=json.dumps(value))],usage=dict(input_tokens=100,output_tokens=40))
        return dict(status=200,request_id='SYNTHETIC',body=json.dumps(body))


def demo(output):
    root=Path(output); source=root/'source'; review=root/'review'
    runner.prepare(source,'selection'); runner.collect(source,backend_override=MockBackend())
    cfg=dict(policy_name='SYNTHETIC-DEMO-NOT-LIVE',live_enabled=False,judges={j:dict(provider='anthropic' if j=='J2' else 'openai',model='synthetic-'+j,max_output_tokens=2048,settings={},contract_verified=False,access_verified=False,rates=dict(input_per_million=1,cached_input_per_million=.1,output_per_million=2,cache_write_per_million=1.25)) for j in ('J1','J2','J3')},limits=dict(max_calls=168,max_estimated_usd=10,timeout_seconds=1))
    artifacts.prepare(source,review,cfg,'pilot'); r=artifacts.Review(review)
    tr=SyntheticJudges([r.source.rows[t]['task']['prompt'] for t in r.plan('pilot')['case_ids']])
    workflow.run(review,scope='pilot',transport=tr,max_calls=3)
    workflow.run(review,scope='pilot',transport=tr)
    integration.check_tokens(review,'pilot',mock=True); integration.freeze_edits(review,'pilot')
    integration.freeze_events(source,root/'answer-events'); integration.measure_events(root/'answer-events',mock=True)
    integration.freeze_events(source,root/'statement-events',review/'manifests/pilot-statements.json'); integration.measure_events(root/'statement-events',mock=True)
    integration.intervene(review,'pilot',mock=True)
    result=reporting.report(review,'pilot')
    return dict(synthetic=True,output=str(root),judge_calls_this_demo=tr.calls,accepted_cases=result['accepted_intervention_cases'],status=result['status'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True); args=parser.parse_args()
    print(json.dumps(demo(args.output),indent=2))
