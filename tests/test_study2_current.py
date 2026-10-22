"""Design/scoring use real data and the actual pinned tokenizer. Only backend execution is mocked."""
import copy
import csv
import io
import json
import os
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_review.artifacts import freeze, sha
from exception_continuation.runner import sealed_read
from exception_study2_native.tables import parse, FIELDS
from exception_study2_native.shortcuts import audit_shortcuts
from exception_study2_current import BUDGET, MODEL, REVISION, SAMPLER, SAMPLING_OPTIONS
from exception_study2_current.design import make_design, validate
from exception_study2_current.adapter import Tokenizer, parse_result
from exception_study2_current.planning import design, prepare, Context, request, smoke_design
from exception_study2_current.execution import run, inspect, analyze, journal, opid, recover
from exception_study2_current.analysis import contrasts, summarize
from exception_study2_current.export import export, annotation_sheet, ANNOTATIONS

TOKENIZER=os.environ.get('CURRENT_QWEN_TOKENIZER_DIR')


class DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=make_design()
    def test_384_unique_cells_budget_and_determinism(self):
        m=self.m;self.assertEqual(m,make_design());self.assertEqual(len(m['cells']),384)
        self.assertEqual(len({x['id'] for x in m['cells']}),384)
        self.assertEqual(m['counts']['maximum_output_tokens'],1572864)
        self.assertEqual(sorted(Counter(x['world'] for x in m['cells']).values()),[16]*24)
    def test_exact_pairing(self):
        tables=self.m['tables'];validate(tables)
        for t in tables:
            other=next(x for x in tables if x['world']==t['world'] and x['cue_state']==t['cue_state'] and x['variant']!=t['variant'])
            a,b=parse(t['table']),parse(other['table'])
            self.assertEqual([(i,k) for i in range(16) for k in FIELDS if a[i][k]!=b[i][k]],[(15,'label')])
    def test_counterbalance_and_distinct_scaffolds(self):
        first=[x for x in self.m['tables'] if x['variant']==x['cue_state']==0]
        self.assertEqual(len({x['scaffold_hash'] for x in first}),24)
        self.assertEqual(Counter(x['climate'] for x in first),{'cold':12,'warm':12})
        self.assertEqual(Counter(x['target_profile'] for x in first),{0:6,1:6,2:6,3:6})
        for relation in ('support','conflict'):
            for variant in (0,1):
                xs=[x for x in self.m['tables'] if x['relation']==relation and x['variant']==variant]
                for key in ('expected','pattern'):self.assertEqual(Counter(x[key] for x in xs),dict(A=8,B=8,C=8))
    def test_no_absence_or_added_reasoning_instruction(self):
        for c in self.m['cells']:
            self.assertNotIn('MISSING',c['prompt'].upper());self.assertNotIn('step by step',c['prompt'].lower())
            other=next(x for x in self.m['cells'] if x['id']==c['id'][:-1]+str(1-int(c['thinking'])))
            self.assertEqual(c['prompt'],other['prompt']);self.assertEqual(c['seed'],other['seed'])
    def test_final_rendered_shortcut_audit(self):
        audit=audit_shortcuts(self.m['tables']);self.assertEqual(audit['perfect_shortcuts'],[])
        self.assertEqual(audit['histogram_only_upper_bound']['accuracy'],.625)
        self.assertEqual(len(audit['cases']),96);self.assertIn('pooled_associations',audit)
    def test_corrupt_target_rejected(self):
        bad=copy.deepcopy(self.m['tables']);bad[0]['expected']='Z'
        with self.assertRaises(ValueError):validate(bad)
    def test_analytic_contrast_and_unavailable_accounting(self):
        rows=[]
        for c in self.m['cells']:
            correct=not(c['thinking'] and c['relation']=='conflict')
            rows.append(dict(cell=c,score={'correct':correct}))
        x=contrasts(rows,'original');self.assertEqual(x['estimate'],1)
        self.assertEqual(x['block_bootstrap']['observed_clusters'],4);self.assertEqual(x['block_interval_95'],[1,1])
        next(x for x in rows if x['cell']['wording']=='original')['score']=None
        self.assertIsNone(contrasts(rows,'original')['estimate'])


@unittest.skipUnless(TOKENIZER,'Set CURRENT_QWEN_TOKENIZER_DIR to the pinned real tokenizer assets; no download in tests')
class RealTokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok=Tokenizer(TOKENIZER)
    def req(self,on=True):return request(smoke_design()['cells'][int(on)],self.tok,256)['request']
    def raw(self,ids,finish=None):
        eos=bool(ids and ids[-1] in self.tok.eos_ids)
        return dict(tokens=ids,raw_text=self.tok.decode_all(ids),text=self.tok.decode(ids),stopped=eos,
                    finish=finish or ('eos' if eos else 'length'),input_ids_verified=True)
    def completed(self,text):return self.raw(self.tok.encode(text)+[min(self.tok.eos_ids)])
    def test_actual_template_and_new_model_markers(self):
        tok=self.tok;on=tok.decode_all(tok.render('Return A.',True));off=tok.decode_all(tok.render('Return A.',False))
        self.assertEqual((tok.open_id,tok.close_id),(248068,248069));self.assertNotEqual(tok.close_id,151668)
        self.assertTrue(on.endswith('<think>\n'));self.assertTrue(off.endswith('<think>\n\n</think>\n\n'))
        self.assertEqual(tok.identity['revision'],REVISION)
    def test_effort_is_applied_and_unsupported_rejected(self):
        msg=[{'role':'user','content':'Return A.'}]
        self.assertNotEqual(self.tok._template(msg,True,'medium'),self.tok._template(msg,True,'xhigh'))
        self.assertNotEqual(self.tok._template(msg,True,'medium'),self.tok._template(msg,True,'low'))
        with self.assertRaises(Exception):self.tok._template(msg,True,'unsupported')
    def test_conflicting_thinking_does_not_supply_answer(self):
        r=self.req();s=parse_result(self.completed('A is a tempting guess. C is wrong.</think>\nB'),r,self.tok)
        self.assertTrue(s['correct']);self.assertEqual(s['answer'],'B');self.assertIn('A',s['thinking_text'])
    def test_off_mode_and_strict_final_format(self):
        for text,valid in [('B',True),(' B\n',True),('ANSWER: B',False),('B.',False),('B because record says so',False),('AB',False)]:
            with self.subTest(text=text):self.assertEqual(parse_result(self.completed(text),self.req(False),self.tok)['valid'],valid)
    def test_no_rescue_of_unclosed_thinking_or_duplicate_open(self):
        for text in ('The answer is B.','<think>B</think>B','B</think>B</think>B'):
            self.assertFalse(parse_result(self.completed(text),self.req(),self.tok)['valid'])
    def test_truncation_wrong_and_missing_final_separate(self):
        r=self.req();ids=self.tok.encode('A')*256;s=parse_result(self.raw(ids),r,self.tok)
        self.assertTrue(s['truncated']);self.assertTrue(s['missing_final']);self.assertIsNone(s['answer'])
        wrong=parse_result(self.completed('Reason.</think>C'),r,self.tok)
        self.assertTrue(wrong['valid']);self.assertFalse(wrong['correct']);self.assertFalse(wrong['truncated'])
        invalid=parse_result(self.completed('Reason.</think>'),r,self.tok)
        self.assertTrue(invalid['missing_final']);self.assertFalse(invalid['valid'])
    def test_bad_metadata_and_structural_tokens(self):
        raw=self.completed('B');raw['raw_text']='A'
        self.assertFalse(parse_result(raw,self.req(False),self.tok)['valid'])
        raw=self.completed('B');raw['stopped']=False
        self.assertFalse(parse_result(raw,self.req(False),self.tok)['valid'])
        self.assertFalse(parse_result(self.completed('<|im_start|>B'),self.req(False),self.tok)['valid'])
    def test_all_exact_scientific_tokens_and_identity_changes(self):
        for c in make_design()['cells']:
            r=request(c,self.tok,BUDGET);q=r['request']
            self.assertEqual(q['input_ids'],self.tok.encode(q['rendered_input']))
            self.assertLessEqual(len(q['input_ids'])+4096,8192);self.assertEqual(q['budget'],4096)
            self.assertNotIn('MISSING',q['rendered_input'].upper())
        base=self.req()
        for key,value in [('budget',512),('seed',17),('model_revision','old'),('thinking',False),('effort','low'),('protocol','old')]:
            other=dict(base);other[key]=value;self.assertNotEqual(digest(other),digest(base))
        for key in ('sampler','input_ids','tokenizer'):
            other=copy.deepcopy(base)
            if key=='sampler':other[key]['temperature']=.6
            elif key=='input_ids':other[key]=other[key]+[self.tok.one('A')]
            else:other[key]['revision']='old'
            self.assertNotEqual(digest(other),digest(base))
    def test_supplied_prefix_has_no_duplicate_template(self):
        r=self.req();prefix=self.tok.encode('Consider A then ');new=self.completed('B.</think>B')
        r=dict(r,prefix_token_ids=prefix,input_ids=r['input_ids']+prefix,budget=256-len(prefix))
        s=parse_result(new,r,self.tok);self.assertTrue(s['correct']);self.assertEqual(s['thinking_text'],'Consider A then B.')
    def test_annotation_states_and_offsets_are_unfilled(self):
        rows=[dict(cell=dict(id='x',world='w',thinking=False),operation_status='never_started',request_hash='h',operation_hash=None,raw=None)]
        row=next(csv.DictReader(io.StringIO(annotation_sheet(rows))))
        for name in ANNOTATIONS:self.assertEqual(row[name],'not_reviewed');self.assertEqual(row[name+'_start'],'')


class MockBackend:
    simulated=True
    def __init__(self,model,tok,callback=None):self.tok=tok;self.callback=callback;self.identity=dict(tokenizer=tok.identity,model=MODEL,revision=REVISION,backend='TEST_ONLY')
    def generate(self,r):
        if self.callback:return self.callback(r)
        text=('Consider the supplied record. The recorded answer is B.</think>\n' if r['thinking'] else '')+r['expected']
        ids=self.tok.encode(text)+[min(self.tok.eos_ids)]
        if r['prefix_token_ids']:ids=ids[len(r['prefix_token_ids']):]
        return dict(tokens=ids,raw_text=self.tok.decode_all(ids),text=self.tok.decode(ids),stopped=True,finish='eos',
            input_ids_verified=True,elapsed_seconds=.01,peak_process_allocated_bytes=0,gpu_memory_used_bytes=0)


@unittest.skipUnless(TOKENIZER,'Requires pinned real tokenizer; only model dispatch is mocked')
class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.smoke=self.root/'smoke';self.screen=self.root/'screen';self.design=self.root/'design'
        prepare(self.smoke,TOKENIZER,self.root/'weights',technical=True)
    def tearDown(self):self.temp.cleanup()
    def screen_plan(self):
        design(self.design);prepare(self.screen,TOKENIZER,self.root/'weights',self.design,self.smoke)
    def passed(self):
        x=run(self.smoke,max_new=8,_factory=MockBackend);self.assertTrue(x['technical_passed']);return x
    def test_eight_call_smoke_prefixes_cached_with_zero_loads(self):
        x=self.passed();self.assertEqual(x['this_invocation']['new_generations'],8);self.assertEqual(x['this_invocation']['model_loads'],1)
        c=Context(self.smoke);self.assertEqual(len(c.requests),8)
        for r in c.requests[4:]:self.assertTrue(r['request']['prefix_token_ids']);self.assertLess(r['request']['budget'],256)
        with patch('exception_study2_current.execution.Backend',side_effect=AssertionError('must not load')):
            self.assertEqual(inspect(self.smoke)['this_invocation']['model_loads'],0)
            self.assertEqual(analyze(self.smoke)['this_invocation']['model_loads'],0)
            self.assertEqual(run(self.smoke,_factory=lambda *a: self.fail('cached'))['this_invocation']['model_loads'],0)
        self.assertEqual(len(list((self.smoke/'operations-v5').glob('*/returned.json'))),8)
    def test_smoke_gate_before_backend_load_and_mock_not_live(self):
        self.screen_plan()
        with self.assertRaisesRegex(ValueError,'Technical smoke'):run(self.screen,_factory=lambda *a:self.fail('must not load'))
        self.passed()
        with self.assertRaisesRegex(ValueError,'Technical smoke'):run(self.screen,live=True)
    def test_persistent_failure_one_dispatch_then_resume_only_unstarted(self):
        self.passed();self.screen_plan();calls=[]
        def failure(r):calls.append(r);raise RuntimeError('persistent')
        x=run(self.screen,max_new=384,_factory=lambda m,t:MockBackend(m,t,failure))
        self.assertEqual(len(calls),1);self.assertEqual(x['totals']['failed'],1);self.assertEqual(x['totals']['never_started'],383)
        old=next((self.screen/'operations-v5').glob('*/failed.json'));h=sha(old)
        y=run(self.screen,max_new=2,_factory=MockBackend)
        self.assertEqual(y['totals']['failed'],1);self.assertEqual(y['totals']['returned'],2);self.assertEqual(y['totals']['never_started'],381);self.assertEqual(h,sha(old))
    def test_invalid_and_truncated_are_retained_not_resent(self):
        self.passed();self.screen_plan();calls=[]
        def wrong(r):
            calls.append(r);tok=Tokenizer(TOKENIZER)
            ids=tok.encode('B')*r['budget'] if len(calls)==1 else tok.encode('ANSWER: A')+[min(tok.eos_ids)]
            return dict(tokens=ids,raw_text=tok.decode_all(ids),text=tok.decode(ids),stopped=len(calls)>1,finish='length' if len(calls)==1 else 'eos')
        x=run(self.screen,max_new=2,_factory=lambda m,t:MockBackend(m,t,wrong))
        self.assertEqual(x['summary']['truncated'],1);self.assertEqual(x['summary']['invalid_final'],1)
        paths=list((self.screen/'operations-v5').glob('*/returned.json'));before={str(p):sha(p) for p in paths}
        y=run(self.screen,max_new=1,_factory=MockBackend);self.assertEqual(y['totals']['returned'],3)
        self.assertEqual(before,{str(p):sha(p) for p in paths});self.assertIsNone(y['primary']['estimate'])
    def test_ambiguous_dispatch_held_and_no_automatic_retry(self):
        self.passed();self.screen_plan();run(self.screen,max_new=1,_factory=MockBackend)
        c=Context(self.screen);r=c.requests[1];ex=sealed_read(self.screen/'execution.json')
        # Simulate process death after request/start, before return, using the real Session identity.
        from exception_study2_current.execution import binding
        identity=dict(binding(c,'MOCK'),id=opid(r),request=r['request'],request_hash=r['request_hash'],stage='current_native_generation')
        folder=self.screen/'operations-v5'/digest(opid(r))
        freeze(folder/'request.json',dict(identity,status='planned'));freeze(folder/'started.json',dict(identity,status='started'))
        y=run(self.screen,max_new=1,_factory=MockBackend)
        self.assertEqual(y['totals']['ambiguous'],1);self.assertEqual(y['totals']['returned'],2)
        self.assertFalse((folder/'returned.json').exists())
    def test_atomic_debris_quarantine_never_promotes_or_retries(self):
        self.passed();c=Context(self.smoke);r=c.requests[0];folder=self.smoke/'operations-v5'/digest(opid(r))
        debris=folder/'returned.json.abcdefgh.tmp';debris.write_text('partial');returned=sha(folder/'returned.json')
        self.assertEqual(len(inspect(self.smoke)['recovery']['pending_entries']),1)
        recover(self.smoke,'Offline interrupted-write fixture')
        self.assertFalse(debris.exists());self.assertEqual(returned,sha(folder/'returned.json'))
        self.assertEqual(run(self.smoke,_factory=lambda *a:self.fail('cached'))['this_invocation']['model_loads'],0)
    def test_mutated_frozen_plan_fails_before_loading(self):
        self.screen_plan();p=self.screen/'plan.json';v=sealed_read(p);v['requests'][0]['request']['budget']=512
        v.pop('artifact_hash');p.unlink();freeze(p,v)
        with self.assertRaisesRegex(ValueError,'identity mismatch'):run(self.screen,_factory=lambda *a:self.fail('load'))
    def test_export_allowlist_complete_and_historical_bytes_unchanged(self):
        self.passed();self.screen_plan();before={str(p):sha(p) for p in self.smoke.rglob('*.json')}
        (self.screen/'.env').write_text('SECRET=not_exported');(self.screen/'model.safetensors').write_text('not_a_weight')
        out=self.root/'bundle.zip';x=export(self.screen,out);self.assertEqual(x['model_loads'],0)
        with zipfile.ZipFile(out) as z:
            self.assertNotIn('.env',z.namelist());self.assertNotIn('model.safetensors',z.namelist())
            self.assertIn('technical-smoke/plan.json',z.namelist());self.assertIn('manual-review.csv',z.namelist())
            manifest=json.loads(z.read('bundle-manifest.json'))
            import hashlib
            for name,item in manifest['files'].items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),item['sha256'])
        self.assertEqual(before,{str(p):sha(p) for p in self.smoke.rglob('*.json')})
        with self.assertRaisesRegex(ValueError,'Fresh export'):export(self.screen,out)
    def test_exclusive_run_lock(self):
        from exception_pilot.storage import run_lock
        with run_lock(self.smoke):
            with self.assertRaises(Exception):run(self.smoke,_factory=lambda *a:self.fail('locked'))


    def test_full_scientific_cache_no_model_and_complete_analysis(self):
        self.passed();self.screen_plan();c=Context(self.screen)
        from exception_study2_current.execution import ScreenSession, binding, smoke_evidence
        b=MockBackend(None,c.tok);identity=binding(c,'MOCK')
        freeze(c.out/'execution.json',dict(identity,backend=b.identity,backend_hash=digest(b.identity)))
        evidence=smoke_evidence(c,'MOCK');freeze(c.out/'smoke-evidence.json',evidence)
        freeze(c.out/'invocations'/'test-complete'/'started.json',dict(identity,max_new=384))
        session=ScreenSession(c,'MOCK')
        for r in c.requests:
            def dispatch(r=r):
                freeze(c.out/'dispatches'/(digest(opid(r))+'.json'),dict(invocation='test-complete',request_hash=r['request_hash'],backend_hash=digest(b.identity)))
                return b.generate(r['request'])
            session.operation(opid(r),r['request'],dispatch,'current_native_generation')
        x=run(self.screen,_factory=lambda *a:self.fail('fully cached scientific run loaded model'))
        self.assertEqual(x['totals']['returned'],384);self.assertEqual(x['totals']['remaining'],0)
        self.assertEqual(x['this_invocation']['model_loads'],0);self.assertEqual(x['primary']['estimate'],0)
        self.assertEqual(x['primary']['block_bootstrap']['observed_clusters'],4)
        self.assertEqual(x['totals']['unresolved_invocations'],1)  # deliberately unfinished control fixture

if __name__=='__main__':unittest.main()
