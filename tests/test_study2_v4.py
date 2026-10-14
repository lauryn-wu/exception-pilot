"""v4 scientific-contract regressions. All model/provider operations are mocks."""
import copy
import hashlib
import json
import os
from types import SimpleNamespace
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation import core as old_core,runner as old_runner
from exception_continuation.backend import MockBackend,LocalBackend as LocalBackendClass
from exception_continuation.runner import sealed_read,sealed_write
from exception_review.artifacts import Source as OldSource
from exception_review import workflow as old_workflow
from exception_study2_v4 import core,runner,validation,readouts,reporting,workloads
from exception_study2_v4.source import Source
from exception_study2_v4.journal import Session,OperationUnavailable,operations
from exception_study2_v4.demo import SyntheticBackend,policy_config,demo
from exception_study2_v4.review import artifacts,integration,workflow,policy
from exception_study2_v4.review import reporting as reviews
from tests.test_automated_review import Transport,detection,verification,FakeClock,CLAIM

class PureTests(unittest.TestCase):
    def test_scientific_design_and_prompts_unchanged(self):
        for phase in ('selection','confirmation'):
            lock=None if phase=='selection' else {'fixture':True}
            p=core.make_plan(phase,selection_lock=lock);q=old_core.make_plan(phase,p['config'],lock)
            for key in ('tasks','worlds','seed','checkpoints','config','selection_lock'):
                self.assertEqual(p[key],q[key],key)
            self.assertEqual(len(p['tasks']),48 if phase=='selection' else 96)
            self.assertEqual(p['config']['validation_tolerances'],old_core.DEFAULT_CONFIG['validation_tolerances'])
            self.assertEqual(p['config']['calibration'],old_core.DEFAULT_CONFIG['calibration'])
        self.assertEqual(set(core.ARMS),{'unchanged','meaning_control','availability_repair','value_repair'})

    def sample(self):
        return dict(tokens=[1,2],stopped=True,finish='eos',next_token_logits={'0':[0.,-1.,-2.]})
    def compare(self,a,b):return validation.compare(a,b,old_core.DEFAULT_CONFIG['validation_tolerances'])
    def test_same_input_logit_shift_reported_not_gated(self):
        a=self.sample();b=copy.deepcopy(a);b['next_token_logits']['0']=[x+10 for x in b['next_token_logits']['0']]
        result=self.compare(a,b)
        self.assertTrue(result['technical_same_input_passed']);self.assertFalse(result['distribution']['raw_logit_check_passed'])
        self.assertAlmostEqual(result['distribution']['max_abs_logit_error'],10)
    def test_each_same_input_failure_dimension(self):
        for name in ('tokens','stopped','finish','probability','argmax','TV','missing','empty','nonfinite','length','missing_tokens','missing_finish'):
            with self.subTest(name=name):
                a=self.sample();b=copy.deepcopy(a)
                if name=='tokens':b['tokens']=[1,3]
                elif name=='stopped':b['stopped']=False
                elif name=='finish':b['finish']='length'
                elif name=='probability':b['next_token_logits']['0']=[0.,-1.1,-2.]
                elif name=='argmax':b['next_token_logits']['0']=[-1.,0.,-2.]
                elif name=='TV':
                    a['next_token_logits']['0']=[0.]*1000;b['next_token_logits']['0']=[.001]*500+[-.001]*500
                elif name=='missing':b['next_token_logits']={}
                elif name=='empty':b['next_token_logits']['0']=[]
                elif name=='nonfinite':b['next_token_logits']['0']=['nan',-1.,-2.]
                elif name=='length':b['next_token_logits']['0']=[0.,-1.]
                elif name=='missing_tokens':del a['tokens'];del b['tokens']
                else:del a['finish'];del b['finish']
                result=self.compare(a,b);self.assertFalse(result['technical_same_input_passed'])
                if name=='TV':
                    self.assertTrue(result['distribution']['probabilities_allclose'])
                    self.assertGreater(result['distribution']['total_variation'],1e-4)

    def test_full_vocabulary_size_required_for_real_profile(self):
        a=self.sample()
        r=validation.compare(a,a,old_core.DEFAULT_CONFIG['validation_tolerances'],151936)
        self.assertFalse(r['full_vocabulary']);self.assertFalse(r['technical_same_input_passed'])
        a['next_token_logits']['0']=[0.]*151936
        self.assertTrue(validation.compare(a,a,old_core.DEFAULT_CONFIG['validation_tolerances'],151936)['technical_same_input_passed'])

    def test_v3_judge_logic_reused_without_monkeypatch(self):
        self.assertEqual(Path(workflow.__file__),Path(old_workflow.__file__))
        self.assertIsNot(workflow.run,old_workflow.run)
        self.assertIs(workflow.Review,artifacts.Review)
        self.assertIsNot(old_workflow.Review,artifacts.Review)
        from exception_review import policy as old
        self.assertEqual(policy.RUBRICS,old.RUBRICS);self.assertEqual(policy.SCHEMAS,old.SCHEMAS)
        self.assertEqual(policy.RULES,old.RULES)
        self.assertNotEqual(policy.freeze_policy(policy_config())['policy_hash'],old.freeze_policy(policy_config())['policy_hash'])

    def test_world_weighting_independent_arms_unknown_bounds(self):
        cases=[dict(task_id='a',world='w1',initial_agreement=True),dict(task_id='b',world='w1',initial_agreement=False),dict(task_id='c',world='w2',initial_agreement=True)]
        def obs(v):return dict(arm_input_valid=True,prefix_text_preserved=True,score=dict(valid=v is not None,correct=v))
        rows=[dict(task_id='a',arms=dict(availability_repair=obs(True),meaning_control=obs(False))),
              dict(task_id='b',arms=dict(availability_repair=obs(False),meaning_control=obs(False))),
              dict(task_id='c',arms=dict(availability_repair=obs(True),meaning_control=obs(False)))]
        p=reviews.comparisons(cases,rows)['primary_availability_minus_meaning']
        self.assertEqual(p['estimate'],.75);self.assertEqual(p['planned_cases'],3)
        self.assertEqual(reviews.comparisons(cases,rows,True)['primary_availability_minus_meaning']['estimate'],1.)
        rows[2]['arms']['availability_repair']=obs(None)
        p=reviews.comparisons(cases,rows)['primary_availability_minus_meaning']
        self.assertEqual(p['estimate'],.5);self.assertEqual(p['unknown_bounds'],[.25,.75]);self.assertEqual(p['planned_worlds'],2)
        self.assertEqual(reviews.comparisons([],[])['primary_availability_minus_meaning']['status'],'NO_ELIGIBLE_CASES')

class Offline(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN')))
        self.enterContext(patch('exception_continuation.backend.LocalBackend',side_effect=AssertionError('REAL MODEL FORBIDDEN')))
    def source(self,name='source',complete=True):
        out=self.root/name;core.prepare(out);b=SyntheticBackend();runner.run(out,complete=complete,backend_override=b);return out,b

    def test_technical_same_input_passes_despite_original_divergence(self):
        out=self.root/'technical';core.prepare(out);b=SyntheticBackend()
        result=runner.run(out,technical_only=True,backend_override=b)
        t=sealed_read(out/'technical-v4.json');self.assertTrue(result['technical_same_input_passed'])
        self.assertEqual(t['measurement'],'MOCK');self.assertEqual(t['real_model_status'],'PENDING')
        self.assertEqual(len(b.calls),33);self.assertFalse((out/'collection-v4.json').exists())
        self.assertEqual(sum(x['original_vs_fresh']['exact_suffix_match'] is False for r in t['records'] for x in r['repeats']),12)
        saved=operations(out)
        for r in t['records']:
            self.assertEqual([x['k'] for x in r['repeats']],[0,1,8,16,32])
        for i in range(3):
            base=saved[f'v4/technical/{i}/original']
            for k in core.CUTS:
                a=saved[f'v4/technical/{i}/fresh/{k}/a'];bb=saved[f'v4/technical/{i}/fresh/{k}/b']
                self.assertEqual(a['request'],bb['request'])
                self.assertEqual(a['request']['input_ids'],base['request']['input_ids']+base['result']['tokens'][:k])
                self.assertEqual(a['request']['budget'],128-k)
        before=len(b.calls);runner.run(out,technical_only=True,backend_override=b);self.assertEqual(len(b.calls),before)

    def test_real_same_input_failure_blocks_and_preserves(self):
        class Bad(SyntheticBackend):
            def __init__(self):super().__init__();self.counter=0
            def generate(self,ids,budget,capture_at=()):
                r=super().generate(ids,budget,capture_at)
                if capture_at:
                    self.counter+=1
                    if self.counter%2==0:r['next_token_logits']['0']=[0.,-3.,-2.]
                return r
        out=self.root/'failed';core.prepare(out);b=Bad()
        with self.assertRaisesRegex(ValueError,'FAILED'):runner.run(out,backend_override=b)
        snapshot=(out/'technical-v4.json').read_bytes();n=len(b.calls)
        with self.assertRaisesRegex(ValueError,'FAILED'):runner.run(out,complete=True,backend_override=b)
        self.assertEqual((out/'technical-v4.json').read_bytes(),snapshot);self.assertEqual(len(b.calls),n)
        self.assertFalse(any(k.startswith('v4/original/') for k in operations(out)))
        self.assertEqual(reporting.selection_report(out)['returned_originals'],0)

    def test_pilot_order_cache_complete_and_timed_parity(self):
        a,b=self.source(complete=False);self.assertEqual(len(b.calls),41)
        ops=operations(a);originals=[ops['v4/original/'+t['id']]['result'] for t in core.read_plan(a)['tasks'][:8]]
        runner.run(a,backend_override=b);self.assertEqual(len(b.calls),41)
        runner.run(a,complete=True,backend_override=b);self.assertEqual(len(b.calls),81)
        self.assertEqual([r['raw'] for r in Source(a).collection['rows'][:8]],originals)
        c=self.root/'untimed';core.prepare(c);other=SyntheticBackend();runner.run(c,complete=True,backend_override=other,timed=False)
        self.assertEqual(Source(a).collection,Source(c).collection)
        self.assertEqual(operations(a),operations(c))
        report=reporting.timing_report(a);self.assertGreater(report['cache_hits'],0)
        self.assertIsNone(report['full_study_live_total_seconds']);self.assertFalse(any(k.endswith('/LIVE') for k in report['observations']))
        self.assertNotIn('backend_initialization_total/MOCK',report['observations'])
        self.assertTrue(reporting.selection_report(a)['calibration']['passed'])
        self.assertEqual(reporting.selection_report(a)['study_2b_eligibility']['status'],'PENDING_INDEPENDENT_REVIEW')

    def test_model_config_source_segregation_and_no_legacy_spoof(self):
        out,b=self.source();self.assertFalse((out/'validation.json').exists());self.assertFalse((out/'collection.json').exists())
        with self.assertRaises((ValueError,FileNotFoundError)):OldSource(out)
        legacy=self.root/'old';old_runner.prepare(legacy,'selection')
        with self.assertRaisesRegex(ValueError,'v4 plan'):Source(legacy)
        with self.assertRaisesRegex(ValueError,'legacy'):core.prepare(legacy)
        before=len(b.calls);b.identity={'kind':'changed-model'}
        with self.assertRaises(ValueError):runner.run(out,backend_override=b)
        self.assertEqual(len(b.calls),before)
        p=sealed_read(out/'plan-v4.json');p['config']['model_dir']='changed'
        sealed_write(out/'plan-v4.json',p)
        with self.assertRaises(ValueError):Source(out)

    def test_ambiguous_and_failed_operations_never_resend(self):
        out=self.root/'journal';p=core.prepare(out);b=SyntheticBackend();s=Session(out,p,b)
        def interrupt():raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):s.operation('v4/probe',{},interrupt,'test')
        with self.assertRaises(OperationUnavailable):s.operation('v4/probe',{},lambda:self.fail('resend'),'test')
        with self.assertRaises(ValueError):s.operation('v4/probe',{'different':True},lambda:None,'test')
        failed=out/'operations-v4'/digest('v4/probe')/'failed.json';failed.unlink()
        with self.assertRaises(OperationUnavailable):s.operation('v4/probe',{},lambda:self.fail('ambiguous resend'),'test')

    def test_fixed_readouts_no_generation_future_tokens_and_later_failure(self):
        out,b=self.source();original=Source(out).collection;start=len(b.calls)
        # A separate target uses the same backend identity but fails one k=128 readout.
        first=next(r for r in original['rows'] if r['task']['arm']=='visible');context=first['input_ids']+first['raw']['tokens'][:128]+b.encode('\nANSWER:')
        score=b.score
        def failed(c,s):
            if c==context:raise RuntimeError('one late readout unavailable')
            return score(c,s)
        b.score=failed
        data=readouts.measure_fixed(out,backend_override=b)
        self.assertEqual(len(b.calls),start)
        row=next(r for r in data['rows'] if r['task_id']==first['task']['id']);cuts={c['k']:c for c in row['cuts']}
        self.assertTrue(cuts[0]['conditional_readout_valid']);self.assertTrue(cuts[64]['conditional_readout_valid']);self.assertFalse(cuts[128]['conditional_readout_valid'])
        summary=sealed_read(out/'fixed-v4/summary-v4.json');self.assertEqual(summary['primary_64_minus_0']['worlds'],12)
        world_values={}
        for item in data['rows']:
            cs={c['k']:c for c in item['cuts']};task=next(r['task'] for r in original['rows'] if r['task']['id']==item['task_id'])
            world_values.setdefault(task['world'],[]).append(cs[64]['readout']['gold_pattern_log_odds']-cs[0]['readout']['gold_pattern_log_odds'])
        self.assertAlmostEqual(summary['primary_64_minus_0']['estimate'],sum(sum(v)/2 for v in world_values.values())/12)
        attempts=len(b.scores);again=readouts.measure_fixed(out,backend_override=b)
        self.assertEqual(data,again);self.assertEqual(len(b.scores),attempts)
        byid={r['task']['id']:r for r in original['rows']}
        for op in operations(out/'fixed-v4').values():
            tid,k,ci=op['id'][len('v4/fixed/'):].rsplit('/',2);r=byid[tid];req=op['request']
            self.assertEqual(req['prefix_ids'],r['raw']['tokens'][:int(k)])
            self.assertEqual(req['input_ids'],r['input_ids']);self.assertNotIn('ANSWER:',b.decode(req['prefix_ids']))
            if op['status']=='returned':self.assertEqual(op['result']['context_hash'],digest(req['input_ids']+req['prefix_ids']+b.encode(req['cue_text'])))
        self.assertEqual(workloads.workload(out)['fixed_2a']['generation_operations'],0)
        for c in row['cuts']:
            if c['conditional_readout_valid']:
                vals=c['readout']['scores'];gold=first['task']['expected'];pattern=first['task']['pattern']
                self.assertAlmostEqual(c['readout']['gold_pattern_log_odds'],sum(vals[gold]['token_logprobs'])-sum(vals[pattern]['token_logprobs']))

    def prepare_review(self,scope='pilot',callback=None):
        source,b=self.source();out=self.root/'review';artifacts.prepare(source,out,policy_config(),scope)
        tr=Transport(callback);workflow.run(out,scope=scope,transport=tr)
        return source,out,b,tr

    def test_v4_judges_edits_events_interventions_and_independent_arm_failure(self):
        seen={'verified':0}
        def callback(call):
            if call['kind']=='detect' and call['request']['model']=='synthetic-J2':return detection('uncertain')
            if call['kind']=='verify':
                seen['verified']+=1
                if seen['verified']==1:return verification(fail=True)
        source,out,b,tr=self.prepare_review(callback=callback)
        r=artifacts.Review(out);self.assertTrue(any(r.read_case(t,'resolution')['agreeing_pair']==['J1','J3'] for t in r.plan('pilot')['case_ids']))
        self.assertTrue(any(r.case_path(t,'draft-1').exists() for t in r.plan('pilot')['case_ids']))
        n=len(tr.calls);workflow.run(out,scope='pilot',transport=tr);self.assertEqual(len(tr.calls),n)
        integration.check_tokens(out,'pilot',backend_override=b);manifest=integration.freeze_edits(out,'pilot')
        event=self.root/'events';integration.freeze_events(source,event,out/'manifests/pilot-statements.json')
        generations=len(b.calls);integration.measure_events(event,backend_override=b);self.assertEqual(len(b.calls),generations)
        case=manifest['cases'][0];row=r.source.rows[case['task_id']];bad=row['input_ids']+case['tokenized']['unchanged'];generate=b.generate
        def fail_one(ids,budget,capture_at=()):
            if ids==bad:raise RuntimeError('one unchanged arm unavailable')
            return generate(ids,budget,capture_at)
        b.generate=fail_one
        results=integration.intervene(out,'pilot',backend_override=b)
        result=next(x for x in results['rows'] if x['task_id']==case['task_id'])
        self.assertNotIn('raw',result['arms']['unchanged'])
        self.assertTrue(result['arms']['availability_repair']['arm_input_valid'])
        self.assertTrue(result['arms']['meaning_control']['arm_input_valid'])
        primary=reviews.comparisons(manifest['cases'],results['rows'])['primary_availability_minus_meaning']
        self.assertEqual(primary['complete_accuracy_cases'],len(manifest['cases']))
        for item in results['rows']:
            c=next(c for c in manifest['cases'] if c['task_id']==item['task_id']);original=r.source.rows[item['task_id']]
            self.assertEqual(set(item['arms']),set(core.ARMS));self.assertNotIn('unchanged_replay_passed',item)
            for arm,obs in item['arms'].items():
                self.assertEqual(obs['context_ids'],original['input_ids']+c['tokenized'][arm]);self.assertEqual(obs['suffix_budget'],512-c['k'])
                self.assertEqual(obs['token_length_delta'],len(c['tokenized'][arm])-c['k'])
            if item['task_id']!=case['task_id']:self.assertFalse(item['original_vs_unchanged']['exact_suffix_match'])
        report=reviews.report(out,'pilot');self.assertEqual(report['intervention_coverage']['per_arm']['unchanged']['missing'],1)
        self.assertEqual(report['intervention_coverage']['per_arm']['availability_repair']['analysis_valid'],len(manifest['cases']))
        self.assertEqual(report['real_model_status'],'PENDING')
        attempts=(len(b.calls),len(b.scores));again=integration.intervene(out,'pilot',backend_override=b)
        self.assertEqual(again,results);self.assertEqual((len(b.calls),len(b.scores)),attempts)

    def test_negative_statements_keep_before_answer_and_no_cases(self):
        source,out,b,tr=self.prepare_review(callback=lambda c:detection('absent') if c['kind']=='detect' else None)
        manifest=integration.freeze_edits(out,'pilot');self.assertEqual(manifest['cases'],[])
        before=len(b.calls);result=integration.intervene(out,'pilot',backend_override=b)
        self.assertEqual(result['status'],'NO_ELIGIBLE_CASES');self.assertEqual(len(b.calls),before)
        target=self.root/'negative-events';integration.freeze_events(source,target,out/'manifests/pilot-statements.json')
        result=integration.measure_events(target,backend_override=b)
        self.assertEqual(sum(c['conditional_readout_valid'] for r in result['rows'] for c in r['cuts'] if c['event']=='before_answer'),24)
        self.assertFalse(any(c['conditional_readout_valid'] for r in result['rows'] for c in r['cuts'] if c['event']=='after_statement'))
        other=self.root/'answer-only';integration.freeze_events(source,other)
        work=workloads.workload(source,[target,other,target]);self.assertEqual(len(work['events']),2)
        self.assertTrue(all(e['generation_operations']==0 for e in work['events']))

    def test_review_budget_pause_policy_change_confirmation_lock(self):
        source,b=self.source();out=self.root/'full-review';cfg=policy_config();artifacts.prepare(source,out,cfg,'full')
        tr=Transport(lambda c:detection('absent') if c['kind']=='detect' else None)
        first=workflow.run(out,transport=tr,max_calls=3);self.assertEqual(first['attempted'],3)
        self.assertEqual(first['stop_reason'],'REQUEST_BUDGET')
        workflow.run(out,transport=tr);self.assertEqual(len(tr.calls),48)
        lock=workflow.freeze_policy_lock(out)
        confirm=self.root/'confirmation';core.prepare(confirm,'confirmation',selection_output=source,policy_lock=out/'policy-lock.json')
        p=core.read_plan(confirm);self.assertEqual(len(p['tasks']),96);self.assertEqual(p['selection_lock']['policy_lock_hash'],lock['artifact_hash'])
        runner.run(confirm,complete=True,backend_override=b)
        artifacts.prepare(confirm,self.root/'confirm-review',cfg,policy_lock=out/'policy-lock.json')
        changed=copy.deepcopy(cfg);changed['judges']['J1']['model']='another'
        with self.assertRaises(ValueError):artifacts.prepare(confirm,self.root/'bad-review',changed,policy_lock=out/'policy-lock.json')
        with self.assertRaises(ValueError):artifacts.prepare(source,out,changed)
        with self.assertRaises(ValueError):core.prepare(self.root/'no-lock','confirmation',selection_output=source)
        different=core.config();different['model']['model_dir']+='-different'
        with self.assertRaises(ValueError):core.prepare(self.root/'other-config','confirmation',different,source,out/'policy-lock.json')

    def test_source_rejects_false_gate_flag_even_with_new_seal(self):
        out,b=self.source();t=sealed_read(out/'technical-v4.json');t['records'][0]['repeats'][0]['distribution']['total_variation']=.1
        sealed_write(out/'technical-v4.json',t)
        with self.assertRaises(ValueError):Source(out)

    def test_v4_semantic_evaluation_budget_cache_and_separation(self):
        from exception_study2_v4.review import semantic_eval
        out=self.root/'semantic-edits';transport=Transport();cfg=policy_config()
        first=semantic_eval.evaluate(out,cfg,transport=transport,max_calls=3,stage='edits')
        self.assertEqual(first['terminal'],3);self.assertEqual(first['status'],'INCOMPLETE')
        self.assertTrue(first['timing_separate_from_natural_trajectories']);self.assertEqual(first['measurement'],'MOCK')
        second=semantic_eval.evaluate(out,cfg,transport=transport,max_calls=3,stage='edits')
        self.assertEqual(second['terminal'],6);self.assertEqual(len(transport.calls),6)
        self.assertGreater(second['timing']['cumulative']['cache_hits'],0)
        frozen=sealed_read(out/'semantic-evaluation-plan.json')
        self.assertEqual(frozen['policy']['source_contract'],core.PROTOCOL)
        self.assertFalse((out/'collection-v4.json').exists())

    def test_actual_tokenizer_empty_block_and_saved_prefix(self):
        path=os.environ.get('QWEN3_TOKENIZER_DIR')
        if not path or not Path(path).is_dir():self.skipTest('Set QWEN3_TOKENIZER_DIR to existing pinned tokenizer assets; never downloaded')
        from transformers import AutoTokenizer
        from exception_continuation.backend import LocalBackend,readout
        from exception_continuation.qwen3 import ASSISTANT_SUFFIX,verify_local_snapshot
        verify_local_snapshot(path,tokenizer_only=True)
        # __new__ attaches only an existing tokenizer; no pretrained model constructor.
        with patch('transformers.AutoModelForCausalLM.from_pretrained',side_effect=AssertionError('NO WEIGHTS')):
            tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        backend=SimpleNamespace(tokenizer=tokenizer,config=core.config()['model'])
        backend.encode=lambda text:tokenizer.encode(text,add_special_tokens=False)
        backend.decode=lambda ids:tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        backend.special_ids=set(tokenizer.all_special_ids)|{151645,151643}
        for task in core.make_plan()['tasks']:
            ids=LocalBackendClass.prompt(backend,task['prompt'])
            rendered=tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
            self.assertTrue(rendered.endswith(ASSISTANT_SUFFIX));self.assertEqual(rendered.count('<think>'),1)
            prefix='The record is visible.';tokens=backend.encode(prefix)
            context=ids+tokens
            self.assertEqual(tokenizer.decode(context,skip_special_tokens=False,clean_up_tokenization_spaces=False),rendered+prefix)
            for cue in core.config()['model']['readout_cues']:
                for label in 'ABC':
                    full=context+backend.encode(cue)+backend.encode(' '+label+'\n')
                    self.assertEqual(backend.decode(full),backend.decode(context)+cue+' '+label+'\n')

    def test_gpu_sync_timing_does_not_change_operations(self):
        from exception_review.telemetry import Telemetry
        events=[];b=SyntheticBackend();b.model=SimpleNamespace(device='cuda:0')
        b.torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda device:events.append(('sync',device))))
        call=b.generate
        def gen(*args,**kwargs):events.append(('generate',None));return call(*args,**kwargs)
        b.generate=gen
        out=self.root/'timed';p=core.prepare(out);tel=Telemetry(out/'timing-v4',dict(protocol=core.PROTOCOL),FakeClock())
        session=Session(out,p,b,tel);ids=b.prompt('technical');session.generate('v4/test-sync',ids,128)
        self.assertEqual([x[0] for x in events],['sync','generate','sync'])
        session.generate('v4/test-sync',ids,128);self.assertEqual(len(events),3)
        self.assertEqual(tel.events[-1]['status'],'cache_hit')

    def test_fresh_machine_config_refuses_overwrite_and_preserves_science(self):
        target=self.root/'local.json';result=core.configure(self.root,target)
        cfg=json.loads(target.read_text());expected=core.config();expected['model']['model_dir']=str(self.root.resolve())
        self.assertEqual(cfg,expected);self.assertFalse(result['model_content_verified'])
        with self.assertRaises(FileExistsError):core.configure(self.root,target)
        with self.assertRaises(ValueError):core.configure(self.root/'missing',self.root/'missing.json')

    def test_journal_terminal_identity_and_workload_manifest_rejected(self):
        out,b=self.source();tid=core.read_plan(out)['tasks'][0]['id']
        p=out/'operations-v4'/digest('v4/original/'+tid)/'returned.json'
        value=sealed_read(p);value['request']['input_ids']=[9];sealed_write(p,value)
        with self.assertRaisesRegex(ValueError,'identity'):operations(out)
        with self.assertRaises(ValueError):Source(out)

    def test_full_mock_smoke(self):
        r=demo(self.root/'demo');self.assertEqual(r['measurement'],'MOCK');self.assertEqual(r['live_model_status'],'PENDING')
        self.assertEqual(r['generation_calls_at_eight_pause'],41);self.assertTrue(r['originals_not_resampled'])
        self.assertEqual(r['collection']['returned_originals'],48);self.assertEqual(r['fixed_readout_rows'],24)
        self.assertGreater(r['divergent_fresh_controls'],0);self.assertEqual(r['frozen_cases'],5)
        root=self.root/'demo';manifest=sealed_read(root/'review/manifests/pilot-edits.json')
        excluded=next(e for e in manifest['excluded'] if e['reason']=='edit_failure')
        event=sealed_read(root/'events/event-measurements-v4.json')
        event_row=next(e for e in event['rows'] if e['task_id']==excluded['task_id'])
        self.assertTrue(all(c['conditional_readout_valid'] for c in event_row['cuts']))
        timing=reporting.timing_report(root/'source/fixed-v4')
        self.assertEqual(timing['completed_generated_output_tokens'],0)
        self.assertGreater(timing['completed_candidate_scored_tokens'],0)
        self.assertEqual(timing['completed_candidate_forward_tokens'],timing['completed_candidate_scored_tokens']+timing['completed_candidate_context_tokens'])

if __name__=='__main__':unittest.main()
