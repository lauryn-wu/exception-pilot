"""Focused offline risks; all generation tests use a fake backend."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
from contextlib import nullcontext
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read, sealed_write
from exception_review.artifacts import freeze
from exception_study2_native import design, planning, execution, analysis
from exception_study2_native import PILOT_BUDGET as BUDGET, BUDGET_POLICY, DECODING
from exception_study2_native.interface import NativeTokenizer, parse_result, OPEN, CLOSE, ON_SUFFIX
from exception_continuation.qwen3 import ASSISTANT_SUFFIX
from exception_study2_native.tables import audit_table, parse, render, association, DISTRACTORS


class Tokens:
    identity={'kind':'SYNTHETIC_TOKENIZER_ONLY'}
    eos_ids={151645,151643};special_ids={151643,151644,151645,OPEN,CLOSE}
    symbols={'<|im_start|>':151644,'<|im_end|>':151645,'<|endoftext|>':151643,'<think>':OPEN,'</think>':CLOSE}
    def __init__(self,*a):self.tokenizer=self
    def encode(self,text):
        ids=[]
        while text:
            found=next((s for s in self.symbols if text.startswith(s)),None)
            if found:ids.append(self.symbols[found]);text=text[len(found):]
            else:ids.append(ord(text[0]));text=text[1:]
        return ids
    def decode_all(self,ids):
        inverse={v:k for k,v in self.symbols.items()}
        return ''.join(inverse[i] if i in inverse else chr(i) for i in ids)
    def decode(self,ids):return self.decode_all([i for i in ids if i not in self.special_ids])
    def apply_chat_template(self,messages,tokenize=True,enable_thinking=True,**kwargs):
        text='<|im_start|>user\n'+messages[0]['content']+'<|im_end|>\n'+(ON_SUFFIX if enable_thinking else ASSISTANT_SUFFIX)
        return self.encode(text) if tokenize else text
    render=NativeTokenizer.render


def raw(tok,text,eos=True):
    ids=tok.encode(text)+([151645] if eos else [])
    return dict(tokens=ids,raw_text=tok.decode_all(ids),text=tok.decode(ids),stopped=eos,finish='eos' if eos else 'length',elapsed_seconds=0.1)


class FakeBackend:
    simulated=True
    def __init__(self,tok):self.tok=tok;self.identity={'fake':True,'tokenizer':tok.identity};self.calls=[];self.fail=False;self.answer='correct'
    def generate(self,r):
        assert r['budget'] in (BUDGET,6144) and r['decoding']==DECODING
        self.calls.append(copy.deepcopy(r))
        if self.fail:raise RuntimeError('mock failure')
        answer=r['expected'] if self.answer=='correct' else 'explanation '+r['expected']
        return raw(self.tok,('<think>scratchpad</think>\n' if r['thinking'] else '')+answer)


class DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.manifest=design.make_design()
    def test_exact_full_factorial_counts_and_determinism(self):
        m=self.manifest
        self.assertEqual(m,design.make_design());self.assertEqual(m['counts']['responses'],960)
        self.assertEqual(m['counts']['by_cohort'],{'pilot':64,'main':896})
        self.assertIsNone(m['counts']['maximum_output_tokens']);self.assertIsNone(m['counts']['main_budget'])
        self.assertEqual(m['counts']['pilot_maximum_output_tokens'],64*4096)
        self.assertEqual(len({c['id'] for c in m['cells']}),960)
        self.assertEqual(m['constraints']['counterbalance']['all']['doubled_marker'],{'X':20,'Y':20,'Z':20})
        for c in m['cells']:self.assertIn(c['table'],c['prompt'])
        for world in {c['world'] for c in m['cells']}:
            for wording in ('original','lookup'):
                self.assertEqual(len({c['seed'] for c in m['cells'] if c['world']==world and c['wording']==wording}),1)
    def test_budget_amendment_preserves_frozen_draft_cells_and_seeds(self):
        import gzip
        path=Path(__file__).resolve().parents[1]/'audits/study2-native-thinking-draft-v1/controlled-design.json.gz'
        previous=json.loads(gzip.decompress(path.read_bytes()))
        for key in ('cells','tables','constraints','seed'):
            self.assertEqual(self.manifest[key],previous[key])

    def test_every_final_table_marginal_and_full_joint_constraints(self):
        design.validate_controlled(self.manifest['tables'])
        for t in self.manifest['tables']:
            a=audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
            self.assertEqual(a['background_class_counts'],{'A':4,'B':4,'C':4})
            self.assertEqual(a['target_row_1based'],13)
            self.assertEqual(a['same_climate_peer_classes'],{t['pattern']:4})
            for f in DISTRACTORS:self.assertTrue(a['features'][f]['exact_class_independence'])
            self.assertTrue(all(x['exact_class_independence'] for x in a['joint_distractors'].values()))
            self.assertEqual(a['absolute_rate_margin_sum'],0)
    def test_transformation_rejects_distractor_or_target_changes(self):
        for change in ('label','transmission'):
            bad=copy.deepcopy(self.manifest['tables']);rows=parse(bad[0]['table'])
            rows[0][change]='A' if change=='label' and rows[0]['label']!='A' else 'B' if change=='label' else 'Extra'
            bad[0]['table']=render(rows)
            with self.assertRaises(ValueError):design.validate_controlled(bad)
    def test_joint_signal_can_survive_zero_marginal_signal(self):
        rows=[dict(label=c,x=str(x),y=str(y)) for c,x,y in [('A',0,0),('A',1,1),('B',0,1),('B',1,0)]]
        self.assertTrue(association(rows,('x',))['exact_class_independence'])
        self.assertTrue(association(rows,('y',))['exact_class_independence'])
        self.assertFalse(association(rows,('x','y'))['exact_class_independence'])


class InterfaceTests(unittest.TestCase):
    def setUp(self):self.tok=Tokens();self.request=dict(thinking=True,expected='A',budget=BUDGET)
    def test_template_switch_and_unchanged_plain_visible_guard(self):
        off=self.tok.render('hello',False);on=self.tok.render('hello',True)
        self.assertNotEqual(off,on);self.assertTrue(self.tok.decode_all(off).endswith(ASSISTANT_SUFFIX))
        self.assertTrue(self.tok.decode_all(on).endswith(ON_SUFFIX))
        from exception_continuation.core import validate_config
        from exception_study2_native.interface import loader_config
        cfg=loader_config('/existing/model');validate_config(cfg);cfg['chat_template_kwargs']['enable_thinking']=True
        with self.assertRaises(ValueError):validate_config(cfg)
        with patch.object(self.tok,'apply_chat_template',side_effect=lambda messages,tokenize=True,**kw: Tokens.apply_chat_template(self.tok,messages,tokenize=tokenize,enable_thinking=False)):
            with self.assertRaises(ValueError):self.tok.render('hello',True)
    def test_native_thinking_final_parser_and_truncation(self):
        cases=[('<think>reason</think>\nA',True,'valid',True),('<think>reason</think>\nB',True,'valid',False),
               ('\n <think>reason</think>\nA',True,'valid',True),
               ('<think>reason</think>\nANSWER: A',True,'invalid_final',False),
               ('A',True,'malformed_channel',False),('<think>reason',False,'truncated',False),
               ('<think>x</think><think>y</think>A',True,'malformed_channel',False)]
        for text,eos,status,correct in cases:
            score=parse_result(raw(self.tok,text,eos),self.request,self.tok)
            self.assertEqual(score['parsing_status'],status);self.assertEqual(score['correct'],correct)
        r=dict(self.request,thinking=False)
        self.assertTrue(parse_result(raw(self.tok,' A '),r,self.tok)['correct'])
        self.assertFalse(parse_result(raw(self.tok,'<think></think>A'),r,self.tok)['valid'])
        self.assertTrue(parse_result(raw(self.tok,'A',False),r,self.tok)['truncated'])
    def test_raw_metadata_and_token_count_fail_closed(self):
        x=raw(self.tok,'<think>x</think>A');x['raw_text']='A'
        self.assertTrue(parse_result(x,self.request,self.tok)['malformed'])
        self.assertTrue(parse_result(None,self.request,self.tok)['malformed'])
        x=raw(self.tok,'A');x['tokens']=[-1]
        self.assertTrue(parse_result(x,self.request,self.tok)['malformed'])

    def test_native_generate_boundary_explicit_sampler_and_request_seeds(self):
        from exception_study2_native.interface import NativeBackend
        # Exercise the actual wrapper with fake tensors/model; no weights/CUDA/transformers import.
        class Config:
            def __init__(self,**kw):self.values=kw
            def to_dict(self):return self.values
        gpu=SimpleNamespace(manual_seed_all=Mock(),synchronize=Mock())
        torch=SimpleNamespace(manual_seed=Mock(),cuda=gpu,inference_mode=lambda:nullcontext(),ones_like=lambda x:[1]*len(x))
        loaded=SimpleNamespace(identity={'loader_only':True},torch=torch,
            tokenizer=SimpleNamespace(pad_token_id=151643,bos_token_id=None),tensor=lambda ids:ids,
            model=SimpleNamespace(generate=Mock()),generate=Mock(side_effect=AssertionError('Historical greedy generate called')),
            prompt=Mock(side_effect=AssertionError('Historical prompt called')))
        with patch.dict('sys.modules',{'transformers':SimpleNamespace(GenerationConfig=Config)}), \
             patch('exception_continuation.backend.LocalBackend',return_value=loaded), \
             patch.object(self.tok,'verify_backend',create=True):
            backend=NativeBackend('/fake/weights',self.tok)
        self.assertEqual(DECODING['do_sample'],True)
        self.assertEqual({k:DECODING[k] for k in ('temperature','top_p','top_k','min_p')},
                         dict(temperature=.6,top_p=.95,top_k=20,min_p=0.0))
        for mode,seed in ((False,123),(True,123),(True,456)):
            ids=self.tok.render('test',mode);tokens=self.tok.encode('A')+[151645]
            loaded.model.generate.return_value=[SimpleNamespace(tolist=lambda:ids+tokens)]
            request=dict(input_ids=ids,budget=6144,budget_policy=BUDGET_POLICY,decoding=DECODING,seed=seed)
            backend.generate(request)
            kw=loaded.model.generate.call_args.kwargs
            for k,v in DECODING.items():self.assertEqual(kw[k],v);self.assertEqual(backend.generation.to_dict()[k],v)
            self.assertFalse(kw['use_model_defaults']);self.assertEqual(kw['max_new_tokens'],6144)
            torch.manual_seed.assert_called_with(seed);gpu.manual_seed_all.assert_called_with(seed)
        loaded.generate.assert_not_called();loaded.prompt.assert_not_called()
        before=loaded.model.generate.call_count
        with self.assertRaises(ValueError):backend.generate(dict(request,decoding=dict(DECODING,do_sample=False)))
        self.assertEqual(loaded.model.generate.call_count,before)

    def test_repetition_readout_repeated_unique_short_and_malformed(self):
        from exception_study2_native.diagnostics import repetition
        repeated=repetition(raw(self.tok,'abcdefghijklmnop'*4),self.tok)
        self.assertEqual(repeated['eligible_windows'],49);self.assertEqual(repeated['repeated_windows'],33)
        self.assertEqual(repeated['max_identical_window_occurrences'],4)
        self.assertEqual(repeated['repeated_window_fraction'],33/49)
        unique=repetition(raw(self.tok,'abcdefghijklmnopqrstuvwxyz'),self.tok)
        self.assertEqual(unique['repeated_windows'],0)
        self.assertIsNone(repetition(raw(self.tok,'A'),self.tok)['repeated_window_fraction'])
        self.assertEqual(repetition(raw(self.tok,'a'*32),self.tok)['longest_identical_token_run'],32)
        self.assertIsNone(repetition(None,self.tok))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.tok=Tokens();m=design.make_design();world=m['cells'][0]['world']
        m['cells']=[c for c in m['cells'] if c['world']==world];m['tables']=[t for t in m['tables'] if t['world']==world]
        self.manifest=dict(m,artifact_hash=digest(m));self.out=self.root/'run'
        for name in ('design','tokens','model'):(self.root/name).mkdir()
        for target,value in [('read_design',lambda *a:self.manifest),('NativeTokenizer',lambda *a:self.tok)]:
            p=patch.object(planning,target,value);p.start();self.addCleanup(p.stop)
        for target in ('socket.create_connection','socket.socket.connect','exception_continuation.backend.LocalBackend.__init__'):
            p=patch(target,side_effect=AssertionError('Forbidden network/weights'));p.start();self.addCleanup(p.stop)
        self.plan=planning.prepare(self.root/'design',self.root/'tokens',self.root/'model',self.out)
        self.backend=FakeBackend(self.tok);self.loads=0
    def factory(self,*a):self.loads+=1;return self.backend
    def run_fake(self,**kw):return execution.run(self.out,'pilot',_factory=self.factory,**kw)
    def test_one_load_matched_settings_and_completed_cache(self):
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(r['counts']['completed'],16)
        self.assertEqual(len(self.backend.calls),16)
        for pair in {x['cell']['pair_id'] for x in self.plan['requests']}:
            rs=[x['request'] for x in self.plan['requests'] if x['cell']['pair_id']==pair]
            self.assertEqual(rs[0]['seed'],rs[1]['seed']);self.assertEqual(rs[0]['decoding'],rs[1]['decoding'])
            self.assertNotEqual(rs[0]['input_ids'],rs[1]['input_ids'])
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(r['counts']['reused'],16)
        self.assertEqual(r['this_invocation']['new_calls'],0)
    def test_failure_then_resume_and_explicit_retry_preserves_attempt(self):
        self.backend.fail=True;r=self.run_fake();self.assertEqual(len(self.backend.calls),1)
        self.assertEqual(r['counts']['failed'],1);self.assertEqual(r['counts']['executable_pending'],15)
        first=self.plan['requests'][0];oid=execution.opid(first,1);failed=self.out/'operations-v5'/digest(oid)/'failed.json';before=failed.read_bytes()
        self.backend.fail=False;r=self.run_fake();self.assertEqual(len(self.backend.calls),16);self.assertEqual(r['counts']['completed'],15)
        r=self.run_fake();self.assertEqual(r['this_invocation']['model_loads'],0)
        execution.retry(self.out,first['cell']['id'],'Runtime repaired; explicitly retry prior failed attempt')
        r=self.run_fake();self.assertEqual(r['counts']['completed'],16);self.assertEqual(len(self.backend.calls),17)
        self.assertEqual(failed.read_bytes(),before)
        with self.assertRaises(ValueError):execution.retry(self.out,first['cell']['id'],'Cannot resample returned')
    def test_ambiguous_attempt_is_not_automatically_resent(self):
        c=planning.Context(self.out);freeze(self.out/'execution.json',dict(execution.binding(c,'MOCK'),backend=self.backend.identity,backend_hash=digest(self.backend.identity)))
        r=self.plan['requests'][0];identity=dict(execution.binding(c,'MOCK'),id=execution.opid(r,1),request=r['request'],request_hash=r['request_hash'],stage='native_generation')
        path=self.out/'operations-v5'/digest(identity['id'])
        freeze(path/'request.json',dict(identity,status='planned'));freeze(path/'started.json',dict(identity,status='started'))
        report=self.run_fake();self.assertEqual(len(self.backend.calls),15);self.assertEqual(report['counts']['interrupted'],1)
    def test_returned_malformed_answers_cached_and_reporting_interruption_safe(self):
        self.backend.answer='verbose'
        with patch.object(analysis,'report',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=self.run_fake();self.assertEqual(len(self.backend.calls),16);self.assertEqual(r['counts']['malformed'],16)
        self.assertEqual(r['this_invocation']['new_calls'],0)
    def test_exact_cache_identity_and_mock_live_separation(self):
        self.run_fake(max_new=1)
        with self.assertRaisesRegex(ValueError,'MOCK/LIVE'):execution.run(self.out,'pilot',True)
        original=self.plan['requests'][0]['request']
        changes=dict(seed=original['seed']+1,thinking=not original['thinking'],budget=BUDGET+1,
            decoding=dict(DECODING,temperature=0.7),model={'revision':'other'},tokenizer={'other':True},
            input_ids=original['input_ids']+[65],prompt=original['prompt']+'x')
        for name,value in changes.items():
            p=copy.deepcopy(self.plan);p['requests'][0]['request'][name]=value;sealed_write(self.out/'plan.json',p)
            with self.subTest(field=name),self.assertRaisesRegex(ValueError,'identity'):self.run_fake()
        sealed_write(self.out/'plan.json',self.plan)
        self.assertEqual(len(self.backend.calls),1)
    def test_offline_inspect_locks_and_output_separation(self):
        r=execution.inspect(self.out);self.assertEqual(r['counts']['planned'],16);self.assertEqual(self.loads,0)
        with run_lock(self.out):
            with self.assertRaises(ValueError):self.run_fake()
        with self.assertRaises(ValueError):planning.prepare(self.root/'design',self.root/'tokens',self.root/'model',self.root/'model'/'run')
        with self.assertRaises(ValueError):planning.prepare(self.root/'design',self.root/'tokens',self.root/'model',self.out)
    def test_paired_signs_and_complete_quartet_denominators(self):
        self.run_fake();c=planning.Context(self.out);_,current,_,_=execution.journal(c)
        # Synthetic condition-specific error: thinking-on conflict alone becomes wrong.
        for r in c.plan['requests']:
            if r['cell']['thinking'] and r['cell']['relation']=='conflict':
                op=copy.deepcopy(current[r['cell']['id']]['operation']);wrong=next(x for x in 'ABC' if x!=r['cell']['expected'])
                op['result']=raw(self.tok,'<think>x</think>'+wrong);current[r['cell']['id']]['operation']=op
        r=analysis.report(c,current,dict(model_loads=0,new_calls=0,reused=16))
        p=r['paired_thinking']['pilot/original/conflict'];self.assertEqual(p['estimate']['estimate'],-1)
        g=r['conflict_penalty_change']['pilot/original'];self.assertEqual(g['change']['estimate'],1);self.assertEqual(g['completed_quartets'],2)

    def test_main_scope_cannot_bypass_review_or_load_on_pilot_plan(self):
        with self.assertRaisesRegex(ValueError,'freeze-main'):
            execution.run(self.out,'main',live_qwen=True)
        self.assertEqual(self.loads,0)
        with self.assertRaisesRegex(ValueError,'complete returned pilot'):
            planning.freeze_main(self.out,self.root/'main',6144,'Reviewed truncation','Reviewed repetition','Pilot budget assessment')
        self.assertFalse((self.root/'main'/'plan.json').exists())

    def test_length_repetition_by_mode_and_failed_pilot_stays_blocked(self):
        self.backend.fail=True;self.run_fake(max_new=1)
        self.backend.fail=False;self.run_fake()
        with self.assertRaisesRegex(ValueError,'complete returned pilot'):
            planning.freeze_main(self.out,self.root/'main',6144,'Reviewed truncation','Reviewed repetition','Pilot assessment')
        r=execution.inspect(self.out)
        groups=r['length_repetition']['groups']
        self.assertEqual(sum(groups[f'pilot/thinking-{t}/all/all']['returned'] for t in (0,1)),15)
        self.assertEqual(sum(groups[f'pilot/thinking-{t}/all/all']['unavailable'] for t in (0,1)),1)
        self.assertEqual(r['main_budget_status'],'AWAITING_PILOT_REVIEW')

    def test_truncated_repetitive_pilot_retained_and_reported_not_retried(self):
        def generate(r):
            # Exactly the provisional cap; intentionally no EOS or closed thinking channel.
            ids=([OPEN] if r['thinking'] else [])+[65]*(r['budget']-int(r['thinking']))
            return dict(tokens=ids,raw_text=self.tok.decode_all(ids),text=self.tok.decode(ids),stopped=False,finish='length')
        with patch.object(self.backend,'generate',side_effect=generate) as call:
            r=self.run_fake();self.assertEqual(call.call_count,16)
            self.assertEqual(r['counts']['truncated'],16)
            for t in (0,1):
                g=r['length_repetition']['groups'][f'pilot/thinking-{t}/all/all']
                self.assertEqual(g['truncated'],8);self.assertEqual(g['responses_with_repeated_windows'],8)
                self.assertEqual(g['token_counts']['token_count']['maximum'],4096)
            self.run_fake();self.assertEqual(call.call_count,16)


class FullMockTests(unittest.TestCase):
    def test_full_manifest_pilot_review_separate_main_and_zero_completed_resume(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tok=Tokens();backend=FakeBackend(tok);loads=[]
            (root/'tokens').mkdir();(root/'model').mkdir()
            planning.design('controlled-draft',root/'design')
            def factory(*a):loads.append(1);return backend
            with patch.object(planning,'NativeTokenizer',return_value=tok),patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('exception_continuation.backend.LocalBackend.__init__',side_effect=AssertionError('No weights')):
                p=planning.prepare(root/'design',root/'tokens',root/'model',root/'run')
                self.assertEqual(len(p['requests']),64);self.assertEqual(p['cohort'],'pilot')
                self.assertTrue(all(r['request']['budget']==4096 for r in p['requests']))
                r=execution.run(root/'run','pilot',max_new=64,_factory=factory)
                self.assertEqual(r['this_invocation']['new_calls'],64);self.assertEqual(len(loads),1)
                before={str(x.relative_to(root/'run')):x.read_bytes() for x in (root/'run').rglob('*') if x.is_file()}
                for notes in (('','',''),('truncation','','budget'),('','repetition','budget')):
                    with self.assertRaises(ValueError):planning.freeze_main(root/'run',root/'main',6144,*notes)
                with self.assertRaises(ValueError):planning.freeze_main(root/'run',root/'main',40000,'truncation','repetition','budget')
                main=planning.freeze_main(root/'run',root/'main',6144,
                    'Synthetic pilot: no truncated outputs','Synthetic pilot: no repeated windows','Offline budget-gate regression only')
                self.assertEqual(len(main['requests']),896);self.assertEqual(main['budget'],6144)
                self.assertTrue(all(r['request']['budget']==6144 for r in main['requests']))
                self.assertEqual(main['budget_review']['pilot']['plan_hash'],p['artifact_hash'])
                self.assertEqual(main['budget_review']['pilot']['measurement_mode'],'MOCK')
                self.assertEqual(before,{str(x.relative_to(root/'run')):x.read_bytes() for x in (root/'run').rglob('*') if x.is_file()})
                with self.assertRaisesRegex(ValueError,'MOCK/LIVE pilot evidence'):execution.run(root/'main','main',live_qwen=True)
                self.assertEqual(len(loads),1)
                with self.assertRaises(ValueError):planning.freeze_main(root/'run',root/'main',6144,'truncation','repetition','another choice')
                with self.assertRaisesRegex(ValueError,'pilot plan'):planning.freeze_main(root/'main',root/'nested-main',6144,'truncation','repetition','incorrect parent')
                with self.assertRaises(ValueError):planning.freeze_main(root/'run',root/'model'/'main',6144,'truncation','repetition','overlapping assets')
                self.assertFalse((root/'model'/'main').exists())
                tampered=copy.deepcopy(main);tampered['budget_review']['pilot']['cases'][0]['token_count']+=1
                sealed_write(root/'main'/'plan.json',tampered)
                with self.assertRaisesRegex(ValueError,'pilot evidence'):execution.run(root/'main','main',_factory=factory)
                sealed_write(root/'main'/'plan.json',main)
                r=execution.run(root/'main','main',max_new=896,_factory=factory)
                self.assertEqual(r['this_invocation']['new_calls'],896);self.assertEqual(len(loads),2)
                self.assertEqual(r['counts']['completed'],896);self.assertEqual(len(backend.calls),960)
                self.assertEqual(r['main_budget_status'],'FROZEN_AFTER_PILOT_REVIEW')
                self.assertEqual(execution.inspect(root/'run')['counts']['completed'],64)
                r=execution.run(root/'main','main',max_new=896,_factory=factory)
                self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_calls'],0)


SAVED=Path(os.environ.get('STUDY2_V5_PLAN','/tmp/study2-source-report-input/study2-v5-replication-v1/originals/plan-v5.json'))
PILOT=Path('/tmp/study2-source-user-main-input/study2-source-user-pilot-v1/pilot-plan.json')

@unittest.skipUnless(SAVED.is_file(),'Actual v5 plan unavailable')
class SavedPlanTests(unittest.TestCase):
    def test_saved_v5_facts_earlier_generator_and_historical_option(self):
        from exception_study2_native.audit import audit
        before=SAVED.read_bytes()
        with tempfile.TemporaryDirectory() as d:r=audit(SAVED,Path(d)/'audit')
        self.assertEqual(r['facts']['worlds'],60);self.assertEqual(r['v5_summary']['tables'],120)
        self.assertTrue(r['facts']['one_target_cell_only']);self.assertTrue(r['facts']['background_4_pattern_3_role0_2_role1'])
        m=design.make_design('historical-v5',design.historical_plan(SAVED))
        self.assertEqual(m['counts']['responses'],480);self.assertEqual(m['counts']['by_cohort'],{'pilot':32,'main':448})
        self.assertEqual({c['relation'] for c in m['cells']},{'conflict'});self.assertEqual(SAVED.read_bytes(),before)

@unittest.skipUnless(PILOT.is_file() and importlib.util.find_spec('jinja2'),'Saved template/Jinja2 unavailable')
class SavedTemplateTests(unittest.TestCase):
    def test_actual_saved_pinned_template_mode_switch_without_tokenizer_or_weights(self):
        import jinja2
        p=sealed_read(PILOT);template=p['tokenizer']['chat_template']
        env=jinja2.Environment(extensions=['jinja2.ext.loopcontrols'])
        render_template=env.from_string(template)
        args=dict(messages=[{'role':'user','content':'Which class?'}],add_generation_prompt=True)
        on=render_template.render(**args,enable_thinking=True);off=render_template.render(**args,enable_thinking=False)
        self.assertNotEqual(on,off);self.assertTrue(on.endswith(ON_SUFFIX))
        self.assertEqual(off,on+'<think>\n\n</think>\n\n')
        self.assertEqual(p['tokenizer']['files']['tokenizer_config.json'],'d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101')

TOK=Path(os.environ.get('QWEN3_TOKENIZER_DIR','/tmp/study2-qwen3-tokenizer'))
@unittest.skipUnless((TOK/'tokenizer.json').is_file(),'Real pinned tokenizer absent; production prepare requires all contexts')
class RealTokenizerTests(unittest.TestCase):
    def test_real_native_templates_pilot_cells_offline_only(self):
        with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
            tok=NativeTokenizer(TOK);reqs=planning.requests(design.make_design(),tok,'pilot',4096)
        self.assertEqual(len(reqs),64)

if __name__=='__main__':unittest.main()
