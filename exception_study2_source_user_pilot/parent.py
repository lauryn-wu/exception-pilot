"""Authenticate failed v2 evidence read-only; never execute a parent workflow."""
import json
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.runner import Source
from exception_study2_source_report_v2 import execution as v2_read
from exception_study2_source_report_v2.planning import query, missing_prompt
from . import PARENT_PLAN, PARENT_ARTIFACTS_HASH, V1_CONTRACT, V2_CONTRACT
from .integrity import artifact_files


def locations(parent,originals=None,tokenizer_dir=None):
    parent=Path(parent).resolve();loc=sealed_read(parent/'locations.json')
    return dict(parent=str(parent),originals=str(Path(originals or loc['originals']).resolve()),
        tokenizer=str(Path(tokenizer_dir or loc['tokenizer']).resolve()))


class Parent:
    def __init__(self,root,originals,tok):
        self.root=Path(root).resolve();self.plan=sealed_read(self.root/'source-report-plan.json');p=self.plan
        if p['artifact_hash']!=PARENT_PLAN or p['version']!='study2-source-report-v2' or p['code_contract']!=V2_CONTRACT:
            raise ValueError('Exact failed parent v2 plan/contract required')
        prior=p['prior_v1']
        if (prior.get('v1_code_contract')!=V1_CONTRACT or not prior.get('available')
            or prior.get('original_parser_gate',{}).get('status')!='FAILED' or prior.get('valid_v1_calibration')!=0):
            raise ValueError('Preserved v1 failure provenance differs')
        tok.verify_backend(p['backend'])
        if tok.identity!=p['tokenizer'] or digest(p['backend'])!=p['backend_hash']:
            raise ValueError('Parent tokenizer/backend identity differs')
        if p['generation_settings']!=dict(budget=16,capture_at=[],batch_size=1,precision='bfloat16',quantization=None,
            enable_thinking=False,attention='eager',generation_overrides={'do_sample':False,'num_beams':1,'use_model_defaults':False},fresh_prefill=True):
            raise ValueError('Parent generation settings differ')
        c=SimpleNamespace(out=self.root,plan=p,queries={q['id']:q for q in p['calibration']+p['main']},tokenizer=tok)
        self.saved,mode=v2_read.journal(c);answers=v2_read.parsed(c,self.saved);g=v2_read.gate(c,self.saved,answers)
        if (mode!='LIVE_LOCAL' or len(p['calibration'])!=12 or len(p['main'])!=332
            or set(self.saved)!={q['id'] for q in p['calibration']}
            or any(v2_read.state(o)!='returned' for o in self.saved.values()) or g['status']!='FAILED'):
            raise ValueError('Require twelve LIVE_LOCAL returns, FAILED verdict, and no parent main records, including request-only')
        historical=json.loads((self.root/'report.json').read_text())
        if (historical['plan_hash']!=PARENT_PLAN or historical['measurement_mode']!='LIVE_LOCAL'
            or historical['calibration_gate']!=g
            or {r['operation_id']:r['source_report'] for r in historical['calibration']}!=answers):
            raise ValueError('Original parent report and immutable journal verdict disagree')
        self.source=Source(originals,scope='pilot')
        if (self.source.binding!=p['source']['pilot'] or self.source.execution['backend']!=p['backend']
            or self.source.execution['artifact_hash']!=p['source']['historical_execution_hash']
            or self.source.technical['artifact_hash']!=p['source']['technical_hash']):
            raise ValueError('Parent source/technical/backend bindings differ')
        self.prompts={};self.sources={};expected=[]
        for i in range(4):
            world=f'staged-v5-{i:03d}'
            rows=[self.source.rows[f'{world}/v{v}/original/visible'] for v in (0,1)]
            changed=[];audits=[]
            for row in rows:
                if row['status']!='returned' or tok.prompt(row['task']['prompt'])!=row['input_ids']:
                    raise ValueError('Saved source prompt cannot be reconstructed')
                q=query(tok,row,0,'calibration_present');expected.append(q)
                self.prompts[q['id']]=row['task']['prompt'];self.sources[row['task']['id']]=row
                text,audit=missing_prompt(row['task']);changed.append(text);audits.append(audit)
            if changed[0]!=changed[1]:raise ValueError('Two variant prompts must collapse to one MISSING control')
            q=query(tok,rows[0],0,'calibration_missing',tok.prompt(changed[0]),'MISSING',
                {r['task']['id']:r['artifact_hash'] for r in rows},
                dict(prompt=changed[0],variant_edits=audits,variants_byte_identical=True))
            expected.append(q);self.prompts[q['id']]=changed[0]
        if p['calibration']!=expected:raise ValueError('Exact ordered parent controls/source/edit bindings differ')
        self.cases=[]
        for q in expected:
            score=answers[q['id']];raw=self.saved[q['id']]['result']
            if q['kind']=='calibration_present':
                if not score['correct'] or score['metadata_errors']:raise ValueError('Expected eight parent present successes')
            else:
                if (score['correct'] or score['field_complete'] or score['metadata_errors']
                    or not score['generation_length_stop'] or score['token_count']!=16
                    or not raw['text'].startswith(q['target_plate']+' |')):
                    raise ValueError('Expected four incomplete parent MISSING row copies')
            self.cases.append(dict(query=q,operation=self.saved[q['id']],score=score))
        self.files=artifact_files(self.root)
        if digest(self.files)!=PARENT_ARTIFACTS_HASH:
            raise ValueError('Parent contained-artifact identity differs from the authenticated failed run')
        # Validate every sealed parent artifact as well as its container/file digest.
        for name in self.files:
            if name.endswith('.json') and name!='report.json':sealed_read(self.root/name)
        self.summary=dict(plan_hash=PARENT_PLAN,code_contract=V2_CONTRACT,v1_code_contract=V1_CONTRACT,
            measurement_mode=mode,parent_v2_calibration_gate=g,returned=12,present_correct=8,missing_correct=0,
            parent_main_records=0,original_v1_gate=prior['original_parser_gate'],
            artifact_sha256=self.files,source_binding=self.source.binding)
