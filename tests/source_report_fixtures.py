"""Synthetic source/index fixtures. No pretrained model or historical execution."""
import copy
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_study2_source_report import CANDIDATES,SUFFIX
from exception_study2_source_report.evidence import preference


class Tokens:
    eos_ids={0};special_ids={0,1000000};root=Path('/synthetic-tokenizer')
    identity=dict(profile={'revision':'SYNTHETIC'},files={},eos_ids=[0],special_ids=[0,1000000],candidates=CANDIDATES)
    config={'chat_template_kwargs':{'enable_thinking':False}}
    def __init__(self,*a):pass
    def encode(self,text):
        for c,ids in CANDIDATES.items():
            if text==' '+c+'\n':return list(ids)
        return [1000+ord(c) for c in text]
    def decode_all(self,ids):
        table={0:'<eos>',1000000:'<assistant>',362:' A',425:' B',356:' C',198:'\n'}
        return ''.join(table[i] if i in table else chr(i-1000) for i in ids)
    def decode(self,ids):return self.decode_all([i for i in ids if i not in self.special_ids])
    def prompt(self,text):return self.encode(text)+[1000000]
    def verify_backend(self,backend):
        if backend.get('hardware')!='SYNTHETIC_TEST_ONLY':raise ValueError('Synthetic backend mismatch')


def fixture():
    tok=Tokens();rows={};tasks=[];worlds=[]
    excluded={'staged-v5-011/v1/original/visible','staged-v5-026/v0/original/visible',
              'staged-v5-027/v0/original/visible','staged-v5-059/v1/original/visible'}
    for i in range(60):
        world=f'staged-v5-{i:03d}';worlds.append(dict(id=world))
        for variant in (0,1):
            expected='ABC'[(i+variant)%3];pattern='ABC'[(i+2)%3];plate=f'PLATE{i:03d}'
            line=f'| {plate} | row features | {expected} |'
            prompt='Synthetic fixture table:\n| License plate | Description | Verified class |\n'+line+'\nWrite visible reasoning.'
            tid=f'{world}/v{variant}/original/visible'
            task=dict(id=tid,world=world,variant=variant,framing='original',arm='visible',expected=expected,pattern=pattern,
                      target_plate=plate,target_row=line,prompt=prompt)
            length=300 if tid in excluded else 600;text='r'*length+'\nANSWER: '+expected
            ids=tok.encode(text)+[0];cuts=[]
            for k in sorted({0,128,256,length,length+1}|({512} if length>=512 else set())):
                cuts.append(dict(k=k,char_end=k,token_hash=digest(ids[:k]),text_hash=digest(text[:k]),roundtrip_exact=True))
            row=dict(task=task,input_ids=tok.prompt(prompt),raw=dict(text=text,tokens=ids,stopped=True,finish='eos'),boundaries=cuts,
                     status='returned',score=dict(answer=expected,correct=True,valid=True,outcome='correct',truncated=False))
            row['artifact_hash']=digest(row);rows[tid]=row;tasks.append(task)
    backend=dict(hardware='SYNTHETIC_TEST_ONLY',kind='TEST_ONLY',generation_overrides={'do_sample':False,'num_beams':1,'use_model_defaults':False})
    backend_hash=digest(backend)
    plan=dict(config={'readout_cues':['\nANSWER:','\nFinal answer:']},plan_hash='synthetic-scientific-plan',source_hash='synthetic-scientific-source',selection_lock=None,protocol='SYNTHETIC')
    execution=dict(backend=backend,backend_hash=backend_hash,code_revision='synthetic-historical-revision',artifact_hash='synthetic-execution',mode='LIVE_LOCAL')
    def scope(pilot):
        ts=[t for t in tasks if (int(t['world'][-3:])<4)==pilot]
        s=SimpleNamespace(tasks=ts,rows={t['id']:rows[t['id']] for t in ts},worlds=worlds[:4] if pilot else worlds[4:],plan=plan,execution=execution,
                          technical={'artifact_hash':'synthetic-technical'},binding={'scope':'pilot' if pilot else 'remaining','source_hash':'synthetic-pilot' if pilot else 'synthetic-remaining','plan_hash':plan['plan_hash'],'backend_hash':backend_hash})
        s.binding_at=lambda path:dict(s.binding,path='../originals')
        return s
    evidence=SimpleNamespace(remaining=scope(False),pilot=scope(True),tokenizer=tok,legacy={},
        binding=dict(historical_revision='synthetic-historical-revision',legacy={'legacy_provenance_mode':'SYNTHETIC_FIXTURE'},remaining={'source_hash':'synthetic'}))
    for t in evidence.remaining.tasks:
        for k in (0,256,512):
            for cue in plan['config']['readout_cues']:
                evidence.legacy[digest([t['id'],k,cue])]=dict(status='returned',class_token=preference({'A':-1.,'B':-2.,'C':-3.}),whole_sequence_sensitivity=preference({'A':-1.2,'B':-2.2,'C':-3.2}),original_value_hash='synthetic',candidate_token_mapping=CANDIDATES)
    return evidence


class CountingBackend:
    simulated=True
    def __init__(self,plan,tok):
        self.identity=copy.deepcopy(plan['backend']);self.eos_ids=set(tok.eos_ids);self.special_ids=set(tok.special_ids)
        self.tok=tok;self.queries={q['context_hash']:q for q in plan['calibration']+plan['main']};self.calls=[]
        self.bad_id=None;self.interrupt_id=None
    def generate(self,ids,budget,capture_at=()):
        assert budget==16 and capture_at==()
        q=self.queries[digest(ids)];self.calls.append(q['id'])
        if q['id']==self.interrupt_id:raise KeyboardInterrupt('Synthetic ambiguous interruption')
        text='Verbose explanation: A.' if q['id']==self.bad_id else q['expected']
        tokens=self.tok.encode(text)+[0]
        if len(tokens)>16:tokens=tokens[:16];text=self.tok.decode(tokens)
        stopped=tokens[-1]==0
        return dict(tokens=tokens,text=text,stopped=stopped,finish='eos' if stopped else 'length',next_token_logits={})
    def score(self,*a,**k):raise AssertionError('New source-report workflow must never score candidates')
