"""Offline v5 acceptance: synthetic text, deterministic fake logits, blocked network/model loader."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import unittest
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.backend import MockBackend, LocalBackend
from exception_continuation import core as old
from exception_study2_v4.core import source_hash as v4_hash
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import core,runner,scoring,readouts,interventions,reporting,workloads
from exception_study2_v5.journal import Session,operations,OperationUnavailable
from exception_study2_v5.review import workflow
from exception_study2_v5.review.rubric import EVENTS,CERTIFICATES,OVERRIDE_CERTIFICATES,EDIT_CHECKS

class Fake(MockBackend):
    """Synthetic fixtures only; no behavioral evidence."""
    def __init__(self):
        super().__init__();self.identity={'kind':'SYNTHETIC_V5_TEST_ONLY','version':1};self.calls=[];self.scores=[];self.eos_ids={0}
        self.fail_generation=False;self.fail_score=False
    def generate(self,ids,budget,capture_at=()):
        self.calls.append((list(ids),budget,tuple(capture_at)))
        text=self.decode(ids);prompt=self.decode(ids[:ids.index(1000000)])
        if '| License plate |' not in prompt:return super().generate(ids,budget,capture_at)
        if self.fail_generation:raise RuntimeError('synthetic generation failure')
        target=[line for line in prompt.splitlines() if line.startswith('| ')][-1]
        gold=target.split('|')[-2].strip()
        # The four same-climate peers have the most frequent label.
        labels=[line.split('|')[-2].strip() for line in prompt.splitlines() if line.startswith('| ')][1:-1]
        pattern=max('ABC',key=labels.count)
        suffix=ids[ids.index(1000000)+1:]
        if suffix:
            prefix=self.decode(suffix)
            answer=pattern if ('MISSING' in prefix or 'unavailable' in prefix or 'prefer' in prefix) else gold
            script='\nANSWER: '+answer
        elif old.INSTRUCTIONS['direct'] in prompt:script='ANSWER: '+gold
        else:
            missing=('The target verified class is MISSING.\n' if gold in ('A','B') else '')
            script=(f'The target verified class is {gold}.\n'+missing+
                f'The recorded {gold} conflicts with the peer pattern {pattern}.\n'+
                f'Therefore prefer class {pattern} over recorded class {gold}.\n**ANSWER: {pattern}**')
        tokens=(self.encode(script)+[0])[:budget]
        return dict(tokens=tokens,text=self.decode(tokens),stopped=tokens[-1]==0,finish='eos' if tokens[-1]==0 else 'length',next_token_logits={str(k):[0.,-1.,-2.] for k in capture_at if k<len(tokens)})
    def score(self,context,candidate):
        self.scores.append((list(context),candidate))
        if self.fail_score:raise RuntimeError('synthetic scoring failure')
        return super().score(context,candidate)

def decision(text,quote,event,subtype=None):
    if quote is None:return dict(status='absent',span=None,text=None,anchor=None,subtype=None,rationale='Independently reviewed: absent.',certificates={})
    a=text.index(quote);b=a+len(quote)
    cert=set(CERTIFICATES)|(set(OVERRIDE_CERTIFICATES) if event=='override' else set())
    return dict(status='present',span=[a,b],text=quote,anchor=workflow.anchor(text,a,b),subtype=subtype or event,
                rationale='Synthetic fixture reviewed against the source table.',certificates={k:True for k in cert})

def annotations_for(view):
    text=view['pre_answer_text'];lines=text.splitlines()
    found={
      'acknowledgment':next((s for s in lines if re.fullmatch(r'The target verified class is [ABC]\.',s)),None),
      'erasure':next((s for s in lines if 'MISSING' in s),None),
      'conflict':next((s for s in lines if 'conflicts' in s),None),
      'override':next((s for s in lines if s.startswith('Therefore prefer')),None),'miscopy':None}
    # This is a fixture author, NOT a production keyword detector.
    return {e:decision(text,q,e,'prose_absence' if e=='erasure' else None) for e,q in found.items()}

def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2));return Path(path)

def reviewed(source,out):
    plan=workflow.prepare_review(source,out)
    cases={tid:annotations_for(v) for tid,v in plan['views'].items()}
    a=dump(Path(out)/'one.json',dict(review_plan_hash=plan['artifact_hash'],reviewer='independent_1',cases=cases))
    b=dump(Path(out)/'two.json',dict(review_plan_hash=plan['artifact_hash'],reviewer='independent_2',cases=cases))
    workflow.freeze_annotations(out,a,b)
    return Path(out)/'annotation-manifest-v5.json'

def edits(source,ann,out,family,backend):
    prep=interventions.prepare_edits(source,ann,out,family);source_obj=runner.Source(source)
    drafts={};verified={}
    for tid,c in prep['cases'].items():
        gold=source_obj.rows[tid]['task']['expected'];pattern=source_obj.rows[tid]['task']['pattern']
        replacements=(dict(meaning_control='The target verified class is unavailable.',value_blind='The target verified class is recorded in the source table.',explicit_value=f'The target verified class is {gold}, as recorded.') if family=='M' else
            dict(meaning_control=f'Thus prefer class {pattern} instead of the recorded class {gold}.',value_blind='The peer pattern does not override the recorded target value.',explicit_value=f'The peer pattern does not override recorded class {gold}.'))
        draft=dict(author='edit_author',status='proposed',reason='Synthetic controlled edit.',replacements=replacements)
        drafts[tid]=draft;verified[tid]=dict(draft_hash=digest(draft),status='accepted',reason='Independent synthetic verification.',checks={k:True for k in EDIT_CHECKS})
    a=dump(Path(out)/'draft.json',dict(preparation_hash=prep['artifact_hash'],cases=drafts))
    b=dump(Path(out)/'verified.json',dict(preparation_hash=prep['artifact_hash'],reviewer='independent_verifier',cases=verified))
    return interventions.freeze_edits(out,a,b,backend_override=backend)

class Offline(unittest.TestCase):
    def setUp(self):
        def forbidden(*a,**kw):raise AssertionError('Network/model loader forbidden during offline tests')
        self.network=patch.object(socket.socket,'connect',forbidden);self.network.start()
        self.connect=patch('socket.create_connection',forbidden);self.connect.start()
        self.loader=patch.object(LocalBackend,'__init__',forbidden);self.loader.start()
        self.addCleanup(self.network.stop);self.addCleanup(self.connect.stop);self.addCleanup(self.loader.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def run_source(self,complete=True):
        out=self.root/'source';core.prepare(out);b=Fake();runner.technical(out,backend_override=b);runner.collect(out,complete=complete,backend_override=b);return out,b

class DesignTests(Offline):
    def test_counts_balance_and_fresh_worlds(self):
        old_plates={i['id'] for phase in ('selection','confirmation') for w in old.make_plan(phase,selection_lock={'fixture':True})['worlds'] for i in w['items']}
        sets=[]
        for phase,n in [('selection',12),('confirmation',48)]:
            p=core.make_plan(phase,selection_lock={'fixture':True} if phase=='confirmation' else None)
            self.assertEqual(len(p['worlds']),n);self.assertEqual(len(p['tasks']),n*8)
            self.assertEqual(p,core.make_plan(phase,selection_lock=p['selection_lock']))
            plates={i['id'] for w in p['worlds'] for i in w['items']};self.assertEqual(len(plates),n*10);self.assertFalse(plates & old_plates);sets.append(plates)
            counts={}
            for w in p['worlds']:
                counts[tuple(w['roles']),w['climate']]=counts.get((tuple(w['roles']),w['climate']),0)+1
                self.assertEqual(w['order'][-1],w['target'])
                self.assertEqual(sum(i['climate']==w['climate'] for i in w['items']),5)
                cells=[t for t in p['tasks'] if t['world']==w['id']]
                self.assertEqual({(t['variant'],t['framing'],t['arm']) for t in cells},{(v,f,a) for v in (0,1) for f in ('original','lookup') for a in ('direct','visible')})
            self.assertEqual(set(counts.values()),{n//12})
        self.assertFalse(sets[0]&sets[1])
    def test_matched_prompts_change_only_question_instruction_or_cell(self):
        p=core.make_plan();cells={(t['variant'],t['framing'],t['arm']):t for t in p['tasks'][:8]}
        for v in (0,1):
            for a in ('direct','visible'):
                old_t=cells[v,'original',a];look=cells[v,'lookup',a]
                self.assertEqual(old_t['table'],look['table'])
                self.assertEqual(old_t['prompt'].replace(old.QUESTION,core.LOOKUP.format(plate=old_t['target_plate'])),look['prompt'])
            self.assertEqual(cells[v,'original','direct']['prompt'].replace(old.INSTRUCTIONS['direct'],old.INSTRUCTIONS['visible']),cells[v,'original','visible']['prompt'])
        x,y=cells[0,'original','direct'],cells[1,'original','direct']
        self.assertEqual(x['prompt'].replace(x['target_row'],y['target_row']),y['prompt'])
    def test_v4_and_all_previous_files_preserved(self):
        baseline=json.loads((core.ROOT/'audits/study2-v5/preservation-baseline.json').read_text())
        self.assertEqual(v4_hash(),core.V4_HASH)
        for name,sha in baseline['files'].items():self.assertEqual(hashlib.sha256((core.ROOT/name).read_bytes()).hexdigest(),sha,name)
    def test_cap_envelope_and_source_identity(self):
        p=core.make_plan();self.assertEqual(p['scientific_budget'],2048);self.assertEqual(p['config']['max_new_tokens'],512)
        cfg=core.config();cfg['model']['max_new_tokens']=2048
        with self.assertRaises(ValueError):core.make_plan(configuration=cfg)
        cfg=core.config();cfg['scientific_budget']=512
        with self.assertRaises(ValueError):core.make_plan(configuration=cfg)
    def test_strict_tolerant_unknown_parser(self):
        for text in ('ANSWER: A','**ANSWER: A**','ANSWER: **A**','**ANSWER:** A','**ANSWER:** **A**'):
            self.assertTrue(scoring.final_score(text,True,'A')['correct'])
        for text in ('**ANSWER: A','ANSWER: A**','I think A','ANSWER: D','ANSWER: A\nMore prose'):
            self.assertIsNone(scoring.final_score(text,True,'A')['correct'])
        self.assertIsNone(scoring.final_score('ANSWER: A',False,'A')['correct'])
        self.assertFalse(scoring.final_score('ANSWER: B',True,'A')['correct'])
        self.assertFalse(scoring.final_score('prose\nANSWER: A',True,'A','direct')['strict_format'])
        self.assertTrue(scoring.final_score('prose\nANSWER: A',True,'A')['strict_format'])
    def test_workload_exact_ceilings(self):
        w=workloads.report();self.assertEqual(w['selection']['originals'],96);self.assertEqual(w['confirmation']['originals'],384)
        self.assertEqual(w['selection']['study_2a']['max_candidate_sequences'],4032)
        self.assertEqual(w['confirmation']['family_O']['max_edited_continuations'],768)

class OperationTests(Offline):
    def test_no_implicit_gate_or_model_load(self):
        core.prepare(self.root/'source')
        with self.assertRaises(FileNotFoundError):runner.collect(self.root/'source',backend_override=Fake())
    def test_failed_gate_blocks_scientific_calls(self):
        out=self.root/'source';core.prepare(out);b=Fake()
        original=b.generate
        def bad(ids,budget,capture_at=()):
            r=original(ids,budget,capture_at)
            if capture_at and len(b.calls)%2:r['tokens'][0]+=1
            return r
        b.generate=bad
        with self.assertRaises(ValueError):runner.technical(out,backend_override=b)
        n=len(b.calls)
        with self.assertRaises(ValueError):runner.collect(out,backend_override=b)
        self.assertEqual(len(b.calls),n)
    def test_bounded_pilot_and_explicit_complete(self):
        out,b=self.run_source(False);source=runner.Source(out,complete=False)
        self.assertEqual(len(source.rows),32);self.assertEqual(len({r['task']['world'] for r in source.rows.values()}),4)
        saved=operations(out);orig=[v for k,v in saved.items() if k.startswith('v5/original/')]
        self.assertTrue(all(x['request']['budget']==2048 and not x['request']['capture_at'] for x in orig))
        self.assertEqual(len([x for x in b.calls if x[1]==2048]),32)
        with self.assertRaises(ValueError):runner.Source(out)
        runner.collect(out,complete=True,backend_override=b);self.assertEqual(len(runner.Source(out).rows),96)
        n=len(b.calls);runner.collect(out,complete=True,backend_override=b);self.assertEqual(n,len(b.calls))
    def test_failed_and_ambiguous_operations_never_retry(self):
        out=self.root/'journal';p=core.make_plan();b=Fake();s=Session(out,p,b)
        with self.assertRaises(OperationUnavailable):s.operation('v5/broken',{},lambda:(_ for _ in ()).throw(RuntimeError()),'test')
        with self.assertRaises(OperationUnavailable):s.operation('v5/broken',{},lambda:self.fail('resent'),'test')
        req=dict(**s.identity,id='v5/ambiguous',request={},request_hash=digest({}),stage='test')
        d=out/'operations-v5'/digest('v5/ambiguous');freeze(d/'request.json',dict(req,status='planned'));freeze(d/'started.json',dict(req,status='started'))
        with self.assertRaises(OperationUnavailable):s.operation('v5/ambiguous',{},lambda:self.fail('resent'),'test')
    def test_backend_and_source_mismatch_refused(self):
        out,b=self.run_source(False);changed=Fake();changed.identity['version']=2
        with self.assertRaises(ValueError):runner.collect(out,backend_override=changed)
        cfg=core.config();cfg['model']['model_dir']='/different'
        with self.assertRaises(ValueError):core.prepare(out,configuration=cfg)
    def test_failed_originals_unknown_and_preserved(self):
        out=self.root/'source';core.prepare(out);b=Fake();runner.technical(out,backend_override=b);b.fail_generation=True
        runner.collect(out,backend_override=b);src=runner.Source(out,complete=False)
        self.assertTrue(all(r['status']=='unavailable' and r['score']['correct'] is None for r in src.rows.values()))
        n=len(b.calls);runner.collect(out,backend_override=b);self.assertEqual(n,len(b.calls))
    def test_raw_eos_truncation_invalid(self):
        b=Fake();raw=dict(tokens=b.encode('ANSWER: A')+[0],text='ANSWER: A',stopped=True,finish='eos');scoring.validate_raw(raw,b,2048)
        raw['finish']='length'
        with self.assertRaises(ValueError):scoring.validate_raw(raw,b,2048)
        raw=dict(tokens=[65]*2048,text='A'*2048,stopped=False,finish='length');scoring.validate_raw(raw,b,2048)
        raw['tokens'].pop()
        with self.assertRaises(ValueError):scoring.validate_raw(raw,b,2048)

class SemanticTests(Offline):
    def test_positive_negative_fixtures_both_families(self):
        positives=[('The target verified class is MISSING.','erasure','prose_absence'),
                   ('?','erasure','table_unknown'),('B','miscopy','source_value_miscopy')]
        for quote,event,subtype in positives:
            view=dict(pre_answer_text=quote,original_available=True);ds={e:decision(quote,None,e) for e in EVENTS};ds[event]=decision(quote,quote,event,subtype)
            workflow.validate_decisions(view,ds)
        negatives=['If the target were missing, infer A.','The target is not missing.','Another vehicle is unknown.',
                   'Prediction is uncertain.','Verified C conflicts with pattern A.','C is an exception; retain C.']
        for text in negatives:
            ds={e:decision(text,None,e) for e in EVENTS};workflow.validate_decisions(dict(pre_answer_text=text,original_available=True),ds)
            self.assertEqual(ds['override']['status'],'absent');self.assertEqual(ds['erasure']['status'],'absent')
    def test_override_not_conflict_and_requires_prior_ack(self):
        text='The target verified class is C.\nTherefore prefer class A over recorded class C.'
        ds=annotations_for(dict(pre_answer_text=text));workflow.validate_decisions(dict(pre_answer_text=text,original_available=True),ds)
        ds['acknowledgment']=decision(text,None,'acknowledgment')
        with self.assertRaises(ValueError):workflow.validate_decisions(dict(pre_answer_text=text,original_available=True),ds)
    def test_first_occurrence_certification_and_unique_anchor(self):
        text='The target verified class is MISSING.';ds={e:decision(text,None,e) for e in EVENTS};ds['erasure']=decision(text,text,'erasure','prose_absence')
        ds['erasure']['certificates']['first_eligible_occurrence']=False
        with self.assertRaises(ValueError):workflow.validate_decisions(dict(pre_answer_text=text,original_available=True),ds)
        ds['erasure']['certificates']['first_eligible_occurrence']=True;ds['erasure']['anchor']['after']='wrong'
        with self.assertRaises(ValueError):workflow.validate_decisions(dict(pre_answer_text=text,original_available=True),ds)
    def test_outcome_blinding_bold_marker_and_no_marker(self):
        for text in ('visible\nANSWER: A','visible\n**ANSWER: A**'):
            row=dict(task=dict(id='t',prompt='source table'),raw=dict(text=text),status='returned')
            view=workflow.blinded_view(row);self.assertEqual(view['pre_answer_text'],'visible\n');self.assertNotIn('score',view)
        row['raw']['text']='unfinished prose';self.assertEqual(workflow.blinded_view(row)['pre_answer_text'],'unfinished prose')
    def test_roundtrip_boundaries_and_no_answer(self):
        b=Fake();raw=dict(text='x\n**ANSWER: A**',tokens=b.encode('x\n**ANSWER: A**')+[0])
        row=dict(raw=raw,boundaries=scoring.boundaries(b,raw));cuts=scoring.checkpoints(row)
        self.assertEqual(next(c for c in cuts if c['name']=='pre_answer')['char_end'],2)
        self.assertFalse(next(c for c in cuts if c['name']=='fixed/128')['eligible'])
        raw=dict(text='x'*300,tokens=b.encode('x'*300));row=dict(raw=raw,boundaries=scoring.boundaries(b,raw));cuts=scoring.checkpoints(row)
        self.assertFalse(next(c for c in cuts if c['name']=='pre_answer')['eligible']);self.assertTrue(next(c for c in cuts if c['name']=='fixed/256')['eligible'])
    def test_semantic_verification_and_table_form(self):
        row=dict(task=dict(expected='C'),raw=dict(text='| target | ? |'))
        event=dict(span=[11,12],text='?');cut=dict(eligible=True,k=13,char_end=14)
        draft=dict(replacements=dict(meaning_control='unknown',value_blind='Recorded in source',explicit_value='C'))
        texts,form=interventions.build_texts(row,event,cut,draft);self.assertEqual(form,'table_cell');self.assertEqual(texts['value_blind'],'| target | Recorded in source |')
        draft['replacements']['value_blind']='Class C is recorded'
        with self.assertRaises(ValueError):interventions.build_texts(row,event,cut,draft)
        draft['replacements']['value_blind']='recorded | new cell'
        with self.assertRaises(ValueError):interventions.build_texts(row,event,cut,draft)
    def test_world_weighting_unknown_bounds_and_independent_contrasts(self):
        cases=[dict(task_id='a',world='w1'),dict(task_id='b',world='w1'),dict(task_id='c',world='w2')]
        obs={'a':{'blind':{'correct':True},'meaning':{'correct':False}},'b':{'blind':{'correct':True},'meaning':{'correct':False}},'c':{'blind':{'correct':False},'meaning':{'correct':True}}}
        result=reporting.contrasts(cases,obs,'blind','meaning');self.assertEqual(result['effect']['estimate'],0);self.assertEqual(result['effect']['worlds'],2)
        obs['c']['meaning']['correct']=None;r=reporting.contrasts(cases,obs,'blind','meaning');self.assertEqual(r['effect']['worlds'],1);self.assertEqual(r['full_cohort_bounds'],[0,.5])

class PipelineTests(Offline):
    def test_entire_pipeline_families_measurements_lock_and_preservation(self):
        out,b=self.run_source();before={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
        ann=reviewed(out,self.root/'review');source=runner.Source(out);manifest=workflow.read_manifest(ann,source)
        ar=reporting.annotation_report(source,manifest);self.assertEqual(sum(ar['events']['erasure'].values()),48)
        self.assertGreater(ar['families']['O']['clean_worlds'],0);self.assertGreater(ar['both_family_cases'],0)
        ms=self.root/'measure';mp=readouts.prepare_measurements(out,ms,ann)
        self.assertLess(len(mp['computations']),48*28)
        n=len(b.calls);values=readouts.measure(ms,backend_override=b);self.assertEqual(n,len(b.calls));self.assertEqual(len(values['results']),len(mp['computations']))
        self.assertEqual(len(b.scores),3*len(mp['computations']))
        for key,c in mp['computations'].items():
            row=source.rows[c['task_id']];value=values['results'][key]['value']
            self.assertEqual(value['context_ids'],row['input_ids']+row['raw']['tokens'][:c['k']]+b.encode(c['cue_text']))
            self.assertEqual(value['preferred_class'],'A');self.assertAlmostEqual(sum(value['normalized'].values()),1)
            self.assertAlmostEqual(value['gold_pattern_log_odds'],value['scores'][row['task']['expected']]['logprob']-value['scores'][row['task']['pattern']]['logprob'])
        for family in ('M','O'):
            editout=self.root/family;em=edits(out,ann,editout,family,b);start=len(b.calls)
            result=interventions.intervene(editout,backend_override=b)
            self.assertEqual(len(b.calls)-start,4*len(em['cases']))
            for case in em['cases']:
                row=source.rows[case['task_id']]
                for arm in case['order']:
                    req=operations(editout)['v5/intervene/'+family+'/'+case['task_id']+'/'+arm+'/continuation']['request']
                    self.assertEqual(req['input_ids'],row['input_ids']+case['prefix_ids'][arm]);self.assertEqual(req['budget'],2048-case['original_k'])
                    a,e=case['event']['span'];new=case['texts'][arm];prefix=case['texts']['unchanged']
                    if arm!='unchanged':self.assertTrue(new.startswith(prefix[:a]));self.assertTrue(new.endswith(prefix[e:]))
            n=len(b.calls);interventions.intervene(editout,backend_override=b);self.assertEqual(n,len(b.calls))
        decisions=dump(self.root/'decisions.json',dict(reviewer='selection_reviewer',rationale='Synthetic lock only',criteria_unchanged=True,no_selection_on_2a_or_interventions=True,families={'M':True,'O':True}))
        lock=self.root/'lock.json';workflow.freeze_lock(out,ann,lock,decisions)
        p=core.prepare(self.root/'confirmation',phase='confirmation',selection_output=out,policy_lock=lock);self.assertEqual(len(p['tasks']),384)
        for name,data in before.items():self.assertEqual((out/name).read_bytes(),data,name)
    def test_adjudication_preserves_disagreements_and_invalid_statuses(self):
        out,b=self.run_source();r=self.root/'review';plan=workflow.prepare_review(out,r)
        cases={t:annotations_for(v) for t,v in plan['views'].items()};other=copy.deepcopy(cases);tid=next(iter(cases));other[tid]['miscopy']=dict(status='uncertain',span=None,text=None,anchor=None,subtype=None,rationale='Uncertain fixture.',certificates={})
        one=dump(r/'one.json',dict(review_plan_hash=plan['artifact_hash'],reviewer='one',cases=cases));two=dump(r/'two.json',dict(review_plan_hash=plan['artifact_hash'],reviewer='two',cases=other))
        with self.assertRaises(ValueError):workflow.freeze_annotations(r,one,two)
        adj=dump(r/'third.json',dict(review_plan_hash=plan['artifact_hash'],reviewer='three',cases={tid:cases[tid]}))
        result=workflow.freeze_annotations(r,one,two,adj);self.assertEqual(result['disagreements'],[tid]);self.assertFalse(result['cases'][tid]['initial_agreement'])
    def test_partial_arms_do_not_block_readouts_or_resample(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review');editout=self.root/'M';em=edits(out,ann,editout,'M',b)
        b.fail_generation=True;result=interventions.intervene(editout,backend_override=b)
        self.assertTrue(all(a['status']=='unavailable' and len(a['readouts'])==2 for r in result['rows'] for a in r['arms'].values()))
        n=len(b.calls);interventions.intervene(editout,backend_override=b);self.assertEqual(n,len(b.calls))
        summary=sealed_read(editout/'intervention-summary-v5.json');self.assertIsNone(summary['comparisons']['primary']['correct']['effect']['estimate'])
        self.assertIsNotNone(summary['comparisons']['primary']['preference']['effect']['estimate'])
    def test_readout_failure_never_generates_answers(self):
        out,b=self.run_source();mp=self.root/'measure';readouts.prepare_measurements(out,mp);b.fail_score=True;n=len(b.calls)
        result=readouts.measure(mp,backend_override=b);self.assertEqual(n,len(b.calls));self.assertTrue(all(x['status']=='unavailable' for x in result['results'].values()))
    def test_semantic_verifier_must_be_independent_and_bind_draft(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review');editout=self.root/'M';edits(out,ann,editout,'M',b)
        v=json.loads((editout/'verified.json').read_text());v['reviewer']='edit_author';dump(editout/'changed.json',v)
        with self.assertRaises(ValueError):interventions.freeze_edits(editout,editout/'draft.json',editout/'changed.json',backend_override=b)


class TokenizerTests(Offline):
    def test_pinned_v5_templates_candidates_and_no_block_reinsertion(self):
        from transformers import AutoTokenizer
        from exception_continuation.qwen3 import verify_local_snapshot,ASSISTANT_SUFFIX
        root=os.environ.get('QWEN3_TOKENIZER_DIR')
        if not root:self.skipTest('Explicit local pinned tokenizer path required; never downloads')
        verify_local_snapshot(root,tokenizer_only=True)
        tokenizer=AutoTokenizer.from_pretrained(root,local_files_only=True,trust_remote_code=False)
        backend=LocalBackend.__new__(LocalBackend);backend.tokenizer=tokenizer;backend.config=core.config()['model']
        for phase in ('selection','confirmation'):
            p=core.make_plan(phase,selection_lock={'fixture':True} if phase=='confirmation' else None)
            for t in p['tasks']:
                ids=backend.prompt(t['prompt']);rendered=tokenizer.decode(ids,skip_special_tokens=False)
                self.assertTrue(rendered.endswith(ASSISTANT_SUFFIX));self.assertEqual(rendered.count('<think>'),1)
                prefix=backend.encode('The target verified class is '+t['expected']+'.')
                joined=tokenizer.decode(ids+prefix,skip_special_tokens=False)
                self.assertEqual(joined,rendered+backend.decode(prefix));self.assertEqual(joined.count('<think>'),1)
        self.assertEqual({c:backend.encode(' '+c+'\n') for c in 'ABC'},{'A':[362,198],'B':[425,198],'C':[356,198]})

class ExtraSafetyTests(Offline):
    def test_cli_help_and_workload_are_offline(self):
        from exception_study2_v5.__main__ import main
        from contextlib import redirect_stdout
        import io
        with patch('sys.argv',['v5','workload']),redirect_stdout(io.StringIO()) as stream:main()
        self.assertEqual(json.loads(stream.getvalue())['selection']['originals'],96)
    def test_no_event_chosen_from_scores_and_no_probability_fields_in_view(self):
        raw=dict(text='Evidence prose\nANSWER: A');row=dict(task=dict(id='x',prompt='table'),raw=raw,status='returned',score={'correct':True},probability=1)
        first=workflow.blinded_view(row);row['score']={'correct':False};row['probability']=0
        self.assertEqual(first,workflow.blinded_view(row))
        self.assertEqual(set(first),{'task_id','source_prompt','pre_answer_text','original_available','rubric'})
    def test_unavailable_original_cannot_be_annotated_absent(self):
        view=dict(pre_answer_text='',original_available=False);ds={e:decision('',None,e) for e in EVENTS}
        with self.assertRaises(ValueError):workflow.validate_decisions(view,ds)
        for d in ds.values():d['status']='invalid'
        workflow.validate_decisions(view,ds)
    def test_partial_sequence_likelihood_rejected_without_sampling(self):
        b=Fake();p=core.make_plan();s=Session(self.root/'j',p,b)
        def bad(context,candidate):return dict(tokens=[1,2],token_logprobs=[-1.],logprob=-1.)
        b.score=bad
        with self.assertRaises(OperationUnavailable):readouts.score(s,'v5/bad-score',[1],[],dict(expected='A',pattern='B'),'\nANSWER:')
        self.assertEqual(b.calls,[])
    def test_special_tokens_roundtrip_and_edited_length_budget(self):
        b=Fake();text='The value is MISSING.';ids=b.encode(text)
        row=dict(task=dict(expected='C'),raw=dict(text=text,tokens=ids+[0]),input_ids=b.prompt('source'))
        event=dict(span=[0,len(text)],text=text);cut=dict(eligible=True,k=len(ids),char_end=len(text))
        d=dict(replacements=dict(meaning_control='The value is unavailable.',value_blind='The verified value exists in the original source table.',explicit_value='The value is C.'))
        texts,_=interventions.build_texts(row,event,cut,d)
        self.assertNotEqual(len(b.encode(texts['value_blind'])),cut['k'])
        self.assertEqual(2048-cut['k'],2027)
    def test_separate_fixed_and_event_names_deduplicate_exact_cuts(self):
        b=Fake();text='X\nANSWER: A';row=dict(raw=dict(text=text,tokens=b.encode(text)+[0]),boundaries=[])
        row['boundaries']=scoring.boundaries(b,row['raw'])
        ann={e:decision(text,None,e) for e in EVENTS};ann['acknowledgment']=decision(text,'X','acknowledgment')
        cuts=scoring.checkpoints(row,ann)
        self.assertEqual(next(c for c in cuts if c['name']=='acknowledgment/before')['k'],0)
        self.assertEqual(next(c for c in cuts if c['name']=='fixed/0')['k'],0)
        self.assertEqual(len({c['name'] for c in cuts}),14)
    def test_semantic_checks_cannot_be_autoaccepted(self):
        self.assertIn('blind_no_label_or_identifying_hint',EDIT_CHECKS)
        self.assertIn('grammar_and_structure_valid',EDIT_CHECKS)
        d=workflow.empty_decision()
        with self.assertRaises(ValueError):workflow.validate_decisions(dict(pre_answer_text='some text',original_available=True),{e:copy.deepcopy(d) for e in EVENTS})

class ReportStageTests(Offline):
    def test_confirmation_does_not_reuse_selection_calibration_thresholds(self):
        from types import SimpleNamespace
        source=SimpleNamespace(plan=core.make_plan('confirmation',selection_lock={'fixture':True}),rows={},
                               execution={'mode':'MOCK'},binding={})
        with patch.object(reporting,'Source',return_value=source):result=reporting.behavioral_report(self.root)
        self.assertEqual(result['calibration']['status'],'NOT_APPLICABLE_CONFIRMATION')
        self.assertIsNone(result['calibration']['passed']);self.assertIsNone(result['calibration']['thresholds'])
    def test_preflight_refuses_unpinned_numpy_before_tokenizer_loading(self):
        from exception_study2_v5 import preflight
        core.prepare(self.root/'source')
        with patch.dict(os.environ,{'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}),patch.object(preflight,'dependency_versions',return_value={}),patch.object(preflight.importlib.metadata,'version',return_value='0.0'):
            with self.assertRaisesRegex(ValueError,'numpy==2.2.4'):preflight.preflight(self.root/'source')


class DefaultMockTests(Offline):
    def test_public_cli_mock_validation_and_pilot_require_no_backend_override(self):
        from exception_study2_v5.__main__ import main
        from contextlib import redirect_stdout
        import io
        out=self.root/'source';core.prepare(out)
        for command in ('validate','collect'):
            with patch('sys.argv',['v5',command,'--output',str(out),'--mock']),redirect_stdout(io.StringIO()):main()
        source=runner.Source(out,complete=False)
        self.assertEqual(len(source.rows),32)
        self.assertTrue(all(r['status']=='returned' for r in source.rows.values()))
        self.assertEqual(source.execution['mode'],'MOCK')
        self.assertEqual(source.technical['real_model_status'],'PENDING')
        self.assertFalse((out/'behavioral-summary-v5.json').exists())
        self.assertFalse((out/'measurement-plan-v5.json').exists())

if __name__=='__main__':unittest.main()
