"""Offline tests only: recorded source input and deterministic mocked API responses."""
import contextlib
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_study2_native import FINAL_INSTRUCTION
from exception_study2_current.planning import contract as screen_contract
from exception_study2_explanation.planning import contract as qwen_contract
from exception_study2_gpt_explanation import VERSION, SETTINGS, INSTRUCTION, SOURCE_ZIP, SOURCE_SHA256, SOURCE_CONTRACT
from exception_study2_gpt_explanation.source import Source
from exception_study2_gpt_explanation.planning import Context, prepare, plan_fields
from exception_study2_gpt_explanation.execution import run, inspect, analyze, opid, binding, journal, recover
from exception_study2_gpt_explanation.parsing import parse_result, account
from exception_study2_gpt_explanation.analysis import outcomes
from exception_study2_gpt_explanation.export import export, review_sheet

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'results/current-qwen-screen-v1'/SOURCE_ZIP
QWEN_CONTRACT = 'afa22d341708255bf3836d30c5db88176eb979981bf47741446b241041eeed48'


def response(text='A', *, status='completed', phase=None, usage=None, output=None):
    body = dict(id='resp_mock', model='gpt-6-sol-resolved-test-id', created_at=1792700000, completed_at=1792700001,
                status=status, error=None, incomplete_details={'reason':'max_output_tokens'} if status=='incomplete' else None,
                output=output if output is not None else [dict(type='message',role='assistant',id='msg_mock',status=status,
                    phase=phase,content=[dict(type='output_text',text=text,annotations=[])])],
                usage=usage if usage is not None else dict(input_tokens=100,output_tokens=10,
                    input_tokens_details=dict(cached_tokens=20,cache_write_tokens=0),output_tokens_details=dict(reasoning_tokens=3)),
                service_tier='default')
    return dict(response=dict(status=200,body=json.dumps(body),request_id='req_mock'),requested_model=SETTINGS['model'],
                started_utc='2026-10-22T00:00:00+00:00',finished_utc='2026-10-22T00:00:01+00:00',elapsed_seconds=1.,redacted=False)


class MockTransport:
    kind = 'MOCK'
    def __init__(self, callback=None): self.calls=[]; self.callback=callback
    def __call__(self, provider, payload, timeout):
        assert provider == 'openai' and timeout == 180
        self.calls.append(deepcopy(payload))
        if self.callback: return self.callback(len(self.calls),payload)
        return response('The record gives A.\nA' if payload['input'][0]['content'].endswith(INSTRUCTION) else 'A')['response']


class SourceAndPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Source(ARCHIVE); cls.plan = plan_fields(cls.source)

    def test_96_pairs_192_fresh_requests(self):
        requests = self.plan['requests']
        self.assertEqual(len(requests),192)
        pairs={r['cell']['pair_id'] for r in requests}; self.assertEqual(len(pairs),96)
        for arm in ('direct','explanation'):
            for rel in ('support','conflict'):
                self.assertEqual(sum(r['cell']['arm']==arm and r['cell']['relation']==rel for r in requests),48)
        self.assertEqual(self.plan['reused_model_outputs'],0)
        self.assertEqual(self.plan['source']['verified_returns'],384)
        self.assertEqual(self.plan['source']['verified_smoke_returns'],8)

    def test_byte_exact_originals_and_suffix_only_changes(self):
        originals={r['cell']['id']:r['request']['prompt'] for r in self.source.cases}
        for r in self.plan['requests']:
            q=r['request']; old=originals[q['source_reference']['cell_id']]; actual=q['payload']['input'][0]['content']
            expected=old if q['arm']=='direct' else old[:-len(FINAL_INSTRUCTION)]+INSTRUCTION
            self.assertEqual(actual.encode(),expected.encode())
            self.assertEqual(r['cell']['prompt'],actual)
            self.assertEqual(q['request_hash'] if 'request_hash' in q else digest(q),r['request_hash'])

    def test_payload_allowlist_no_judge_or_answer_key_metadata(self):
        for r in self.plan['requests']:
            p=r['request']['payload']
            self.assertEqual(set(p),set(SETTINGS)|{'input'})
            self.assertEqual({k:p[k] for k in SETTINGS},SETTINGS)
            self.assertEqual(p['input'],[{'role':'user','content':r['cell']['prompt']}])
            for key in ('expected','pattern','instructions','text','tools','seed','top_k','min_p','input_ids','template_args'):
                self.assertNotIn(key,p)
            self.assertNotIn('BEGIN_UNTRUSTED_SOURCE_JSON',p['input'][0]['content'])
            self.assertNotIn('<|im_start|>',p['input'][0]['content'])

    def test_counterbalanced_adjacent_pairs_in_each_block_and_relation(self):
        rs=self.plan['requests']; first=[]
        for a,b in zip(rs[::2],rs[1::2]):
            self.assertEqual(a['cell']['pair_id'],b['cell']['pair_id'])
            self.assertEqual({a['cell']['arm'],b['cell']['arm']},{'direct','explanation'})
            first.append(a)
        for block in range(4):
            for rel in ('support','conflict'):
                arms=[r['cell']['arm'] for r in first if r['cell']['block']==block and r['cell']['relation']==rel]
                self.assertEqual(arms.count('direct'),6); self.assertEqual(arms.count('explanation'),6)
        self.assertEqual(plan_fields(self.source),self.plan)
        self.assertNotIn('seed',SETTINGS)

    def test_request_identity_binds_arm_prompt_model_and_settings(self):
        q=self.plan['requests'][0]['request']; baseline=digest(q)
        for key,value in [('model','different'),('temperature',.5),('max_output_tokens',2048)]:
            changed=deepcopy(q); changed['payload'][key]=value; self.assertNotEqual(digest(changed),baseline)
        changed=deepcopy(q); changed['arm']='other'; self.assertNotEqual(digest(changed),baseline)
        changed=deepcopy(q); changed['payload']['input'][0]['content']+=' '; self.assertNotEqual(digest(changed),baseline)

    def test_source_and_frozen_qwen_contracts_unchanged(self):
        self.assertEqual(sha(ARCHIVE),SOURCE_SHA256)
        self.assertEqual(screen_contract(),SOURCE_CONTRACT)
        self.assertEqual(qwen_contract(),QWEN_CONTRACT)

    def test_changed_source_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'changed.zip'; p.write_bytes(self.source.data+b'x')
            with self.assertRaisesRegex(ValueError,'SHA256'): Source(p)

    def test_no_historical_answers_become_gpt_scores(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'run'; prepare(ARCHIVE,out); value=inspect(out)
            self.assertEqual(value['totals']['completed'],0)
            self.assertEqual(value['totals']['qwen_outputs_reused'],0)
            self.assertTrue(all(r['score'] is None and r['raw'] is None for r in value['cases']))
            self.assertIsNone(value['primary']['estimate'])


class ParsingTests(unittest.TestCase):
    def score(self,raw,arm='explanation',expected='A'):
        return parse_result(raw,dict(arm=arm,expected=expected))

    def test_correct_wrong_and_label_only_compliance(self):
        a=self.score(response('The recorded class is A.\nA'))
        self.assertTrue(a['correct']); self.assertTrue(a['explanation_format_compliant'])
        b=self.score(response('The recorded class is B.\nB'))
        self.assertEqual(b['category'],'wrong_label'); self.assertTrue(b['explanation_format_compliant'])
        a=self.score(response('A')); self.assertTrue(a['correct']); self.assertFalse(a['explanation_format_compliant'])

    def test_direct_requires_entire_visible_answer(self):
        self.assertTrue(self.score(response(' \nA\n '),'direct')['correct'])
        for text in ('Answer: A','The record says A.\nA','**A**','A\nB',''):
            self.assertFalse(self.score(response(text),'direct')['valid'])

    def test_final_line_exact_no_format_rescue(self):
        for text in ('Reason\n A','Reason\nA ','Reason\n**A**','Reason\nANSWER: A','A\nI conclude.'):
            self.assertEqual(self.score(response(text))['category'],'invalid_format')
        self.assertTrue(self.score(response('A is a possibility.\nB\n\n'),expected='B')['correct'])
        self.assertTrue(self.score(response('Recorded A.\r\nA\r\n'))['correct'])

    def test_truncated_valid_looking_answer_is_unsuccessful(self):
        s=self.score(response('Reason\nA',status='incomplete'))
        self.assertEqual(s['category'],'truncated'); self.assertTrue(s['truncated']); self.assertFalse(s['valid'])
        self.assertEqual(s['final_answer_text'],'Reason\nA')

    def test_refusal_preserved_and_separate(self):
        raw=response(output=[dict(type='message',role='assistant',content=[dict(type='refusal',refusal='Cannot comply.')])])
        s=self.score(raw); self.assertEqual(s['category'],'refusal'); self.assertFalse(s['valid'])
        self.assertEqual(s['messages'][0]['refusals'],['Cannot comply.'])

    def test_non_token_incomplete_is_separate(self):
        raw=response('A',status='incomplete'); body=json.loads(raw['response']['body']); body['incomplete_details']['reason']='content_filter'
        raw['response']['body']=json.dumps(body)
        s=self.score(raw); self.assertEqual(s['category'],'incomplete'); self.assertFalse(s['truncated'])

    def test_reasoning_summary_is_not_explanation(self):
        raw=response(output=[dict(type='reasoning',summary=[dict(type='summary_text',text='A long hidden-reasoning summary.')]),
                            dict(type='message',role='assistant',content=[dict(type='output_text',text='A')])])
        s=self.score(raw); self.assertTrue(s['correct']); self.assertFalse(s['explanation_format_compliant'])
        self.assertEqual(len(s['output_items']),2); self.assertEqual(s['complete_visible_text'],'A')

    def test_phases_order_and_content_boundaries(self):
        items=[dict(type='message',role='assistant',phase='commentary',content=[dict(type='output_text',text='Looking at the record.')]),
               dict(type='message',role='assistant',phase='final_answer',content=[dict(type='output_text',text='Recorded '),dict(type='output_text',text='A.\nA')])]
        s=self.score(response(output=items)); self.assertTrue(s['correct'])
        self.assertEqual(s['final_message_index'],1)
        self.assertEqual(s['messages'][1]['content'],items[1]['content'])
        self.assertEqual(s['complete_visible_text'],'Looking at the record.\nRecorded A.\nA')
        self.assertFalse(self.score(response(output=items),'direct')['valid'])

    def test_visible_commentary_counts_but_reasoning_summary_does_not(self):
        items=[dict(type='message',role='assistant',phase='commentary',content=[dict(type='output_text',text='The target record says A.')]),
               dict(type='message',role='assistant',phase='final_answer',content=[dict(type='output_text',text='A')])]
        s=self.score(response(output=items)); self.assertTrue(s['correct']); self.assertTrue(s['explanation_format_compliant'])
        self.assertEqual(s['explanation_parts'][0]['phase'],'commentary')
        self.assertEqual(s['explanation_parts'][0]['text'],'The target record says A.')

    def test_ambiguous_or_reordered_final_messages_rejected(self):
        a=dict(type='message',role='assistant',content=[dict(type='output_text',text='A')])
        self.assertTrue(self.score(response(output=[a,a]))['malformed'])
        self.assertTrue(self.score(response(output=[dict(a,phase='final_answer'),dict(a,phase='commentary')]))['malformed'])
        self.assertTrue(self.score(response(output=[dict(a,phase='final_answer'),dict(a,phase='final_answer')]))['malformed'])

    def test_alias_and_metadata_preserved(self):
        raw=response('A'); s=self.score(raw)
        self.assertTrue(s['correct']); self.assertNotEqual(s['requested_model'],s['returned_model'])
        self.assertEqual(s['request_id'],'req_mock'); self.assertEqual(s['response_id'],'resp_mock')
        self.assertEqual(s['usage']['output_tokens_details']['reasoning_tokens'],3)
        self.assertEqual(s['created_at'],1792700000)

    def test_malformed_json_and_unexpected_output_retained(self):
        raw=response(); raw['response']['body']='{oops'
        self.assertEqual(self.score(raw)['category'],'malformed_response')
        self.assertEqual(self.score(response(output=[dict(type='function_call',name='not_requested')]))['category'],'malformed_response')

    def test_usage_cache_writes_and_reasoning_not_double_counted(self):
        usage=dict(input_tokens=1000,output_tokens=100,input_tokens_details=dict(cached_tokens=200,cache_write_tokens=300,
                   cache_write_tokens_details=dict(ttl_30m_tokens=200,ttl_12h_tokens=100)),output_tokens_details=dict(reasoning_tokens=70))
        a=account(response(usage=usage))
        self.assertAlmostEqual(a['estimated_usd'],(500*2+200*.2+200*2.5+100*5+100*10)/1e6)
        self.assertEqual(a['reasoning_tokens'],70); self.assertEqual(a['ordinary_input_tokens'],500)

    def test_long_context_pricing_and_inconsistent_usage(self):
        usage=dict(input_tokens=300000,output_tokens=100,input_tokens_details=dict(cached_tokens=0,cache_write_tokens=0),
                   output_tokens_details=dict(reasoning_tokens=20))
        self.assertAlmostEqual(account(response(usage=usage))['estimated_usd'],(300000*4+100*15)/1e6)
        usage['input_tokens_details']['cached_tokens']=300001
        self.assertIsNone(account(response(usage=usage))['estimated_usd'])

    def test_unknown_usage_and_unpriced_tier_never_imputed(self):
        raw=response(usage={}); self.assertIsNone(account(raw)['estimated_usd'])
        raw=response(); body=json.loads(raw['response']['body']); del body['usage']['input_tokens_details']['cache_write_tokens']
        raw['response']['body']=json.dumps(body); self.assertIsNone(account(raw)['estimated_usd'])
        body=json.loads(response()['response']['body']); body['service_tier']='priority'; raw['response']['body']=json.dumps(body)
        self.assertIsNone(account(raw)['estimated_usd'])


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.base=Path(cls.tmp.name)/'base'
        prepare(ARCHIVE,cls.base)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def setUp(self):
        self.tmpcase=tempfile.TemporaryDirectory(); self.root=Path(self.tmpcase.name); self.out=self.root/'run'
        shutil.copytree(self.base,self.out)
    def tearDown(self): self.tmpcase.cleanup()
    def run_mock(self,transport=None,max_new=192):
        with contextlib.redirect_stdout(io.StringIO()):
            return run(self.out,max_new=max_new,_transport=transport or MockTransport())

    def test_prepare_uses_no_tokenizer_backend_or_network(self):
        fresh=self.root/'fresh'
        with patch('exception_study2_current.adapter.Tokenizer',side_effect=AssertionError('tokenizer')), patch('exception_study2_current.adapter.Backend',side_effect=AssertionError('GPU')), patch('socket.socket',side_effect=AssertionError('network')):
            result=prepare(ARCHIVE,fresh)
        self.assertEqual(result['requests'],192)

    def test_cli_offline_sequence_standard_library_only(self):
        env={k:v for k,v in os.environ.items() if k not in ('OPENAI_API_KEY','ANTHROPIC_API_KEY')}
        for command in ('inspect','run','analyze','export'):
            args=[sys.executable,'-S','-m','exception_study2_gpt_explanation',command,'--output',str(self.out)]
            if command=='export': args += ['--destination',str(self.root/'cli.zip')]
            result=subprocess.run(args,cwd=ROOT,env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            value=json.loads(result.stdout)
            if command != 'export': self.assertEqual(value['totals']['pending'],192)
        self.assertFalse((self.out/'execution.json').exists())

    def test_offline_default_never_constructs_transport(self):
        with patch('exception_study2_gpt_explanation.execution.HTTPTransport',side_effect=AssertionError('network')):
            r=run(self.out)
        self.assertEqual(r['this_invocation']['new_dispatches'],0); self.assertEqual(r['totals']['pending'],192)
        self.assertFalse((self.out/'execution.json').exists())

    def test_bounded_run_resume_complete_then_zero_calls(self):
        t=MockTransport(); a=self.run_mock(t,4)
        self.assertEqual(len(t.calls),4); self.assertEqual(a['totals']['completed'],4); self.assertEqual(a['totals']['pending'],188)
        b=self.run_mock(t)
        self.assertEqual(len(t.calls),192); self.assertTrue(b['complete']); self.assertEqual(b['this_invocation']['cached'],4)
        finals={str(p.relative_to(self.out)):sha(p) for p in (self.out/'operations-v5').rglob('*.json')}
        c=self.run_mock(t); self.assertEqual(len(t.calls),192); self.assertEqual(c['totals']['cached'],192)
        self.assertEqual(finals,{str(p.relative_to(self.out)):sha(p) for p in (self.out/'operations-v5').rglob('*.json')})
        self.assertEqual(c['resource_summary']['priced_responses'],192)

    def test_completed_live_mode_resume_needs_no_key_or_transport(self):
        transport=MockTransport()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'offline-test-key'}), patch('exception_study2_gpt_explanation.execution.HTTPTransport',return_value=transport), contextlib.redirect_stdout(io.StringIO()):
            first=run(self.out,live=True)
        self.assertTrue(first['complete']); self.assertEqual(len(transport.calls),192)
        with patch.dict(os.environ,{},clear=True), patch('exception_study2_gpt_explanation.execution.HTTPTransport',side_effect=AssertionError('network')):
            final=run(self.out,live=True)
        self.assertEqual(final['this_invocation']['new_dispatches'],0)
        self.assertEqual(final['measurement_mode'],'LIVE_API')

    def test_keyboard_interrupt_does_not_resend_attempt(self):
        def interrupted(n,p):
            if n==2: raise KeyboardInterrupt()
            return response('A')['response']
        t=MockTransport(interrupted)
        with self.assertRaises(KeyboardInterrupt): self.run_mock(t)
        a=inspect(self.out); self.assertEqual(a['totals']['completed'],1); self.assertEqual(a['totals']['failed'],1)
        self.assertEqual(a['totals']['pending'],190)
        next_t=MockTransport(); b=self.run_mock(next_t)
        self.assertEqual(len(next_t.calls),190); self.assertEqual(b['totals']['completed'],191); self.assertFalse(b['complete'])
        self.assertNotIn(t.calls[1],next_t.calls)

    def test_persistent_transport_failure_one_dispatch_resume_remaining_only(self):
        def fail(n,p): raise TimeoutError('mock timeout')
        t=MockTransport(fail); a=self.run_mock(t)
        self.assertEqual(len(t.calls),1); self.assertEqual(a['totals']['failed'],1); self.assertEqual(a['totals']['pending'],191)
        failed=list((self.out/'operations-v5').glob('*/failed.json'))[0]; old=failed.read_bytes()
        next_t=MockTransport(); b=self.run_mock(next_t)
        self.assertEqual(len(next_t.calls),191); self.assertEqual(b['totals']['failed'],1); self.assertEqual(b['totals']['completed'],191)
        self.assertFalse(b['complete']); self.assertIsNone(b['primary']['estimate']); self.assertEqual(old,failed.read_bytes())
        self.assertNotIn(t.calls[0],next_t.calls)
        c=self.run_mock(next_t); self.assertEqual(c['this_invocation']['new_dispatches'],0)

    def test_http_error_preserves_raw_body_and_stops(self):
        t=MockTransport(lambda n,p:dict(status=429,body='{"error":{"message":"quota"}}',request_id='req_error'))
        a=self.run_mock(t); self.assertEqual(len(t.calls),1); self.assertEqual(a['totals']['failed'],1)
        saved=sealed_read(next((self.out/'responses').glob('*.json')))
        self.assertEqual(saved['raw']['response']['body'],'{"error":{"message":"quota"}}')
        self.assertEqual(saved['raw']['response']['request_id'],'req_error')

    def test_malformed_identity_and_usage_do_not_crash_analysis_or_resume(self):
        def malformed(n,p):
            raw=response(); body=json.loads(raw['response']['body']); body['model']=['bad']; body['usage']['output_tokens_details']='bad'
            return dict(raw['response'],body=json.dumps(body))
        t=MockTransport(malformed); a=self.run_mock(t,2)
        self.assertEqual(a['totals']['completed'],2); self.assertEqual(a['totals']['failed'],0)
        self.assertEqual(a['returned_models'],{})
        for row in a['cases']:
            if row['score']:
                self.assertEqual(row['score']['category'],'malformed_response')
                self.assertIsNone(row['usage_accounting']['reasoning_tokens'])
        self.assertEqual(inspect(self.out)['totals']['completed'],2)

    def test_server_failure_and_setting_change_stop(self):
        def failure(n,p):
            raw=response(); b=json.loads(raw['response']['body']); b['status']='failed'; b['error']={'code':'server_error'}
            return dict(raw['response'],body=json.dumps(b))
        a=self.run_mock(MockTransport(failure)); self.assertEqual(a['totals']['failed'],1)
        def mismatch(n,p):
            raw=response(); b=json.loads(raw['response']['body']); b['temperature']=.5
            return dict(raw['response'],body=json.dumps(b))
        b=self.run_mock(MockTransport(mismatch)); self.assertEqual(b['totals']['failed'],2); self.assertEqual(b['totals']['pending'],190)

    def test_echoed_output_usage_over_cap_stops(self):
        def too_long(n,p):
            raw=response(); body=json.loads(raw['response']['body']); body['usage']['output_tokens']=4097
            return dict(raw['response'],body=json.dumps(body))
        transport=MockTransport(too_long); value=self.run_mock(transport)
        self.assertEqual(len(transport.calls),1); self.assertEqual(value['totals']['failed'],1)
        self.assertEqual(value['totals']['pending'],191)

    def test_invalid_refused_truncated_malformed_returns_do_not_stop(self):
        returns=[response('verbose answer'),response('A',status='incomplete'),
                 response(output=[dict(type='message',role='assistant',content=[dict(type='refusal',refusal='No')])])]
        malformed=response(); malformed['response']['body']='not json'; returns.append(malformed)
        t=MockTransport(lambda n,p:returns[(n-1)%4]['response']); a=self.run_mock(t,8)
        self.assertEqual(len(t.calls),8); self.assertEqual(a['totals']['completed'],8); self.assertEqual(a['totals']['failed'],0)
        cats={r['score']['category'] for r in a['cases'] if r['score']}; self.assertEqual(cats,{'invalid_format','truncated','refusal','malformed_response'})
        self.run_mock(MockTransport(),1); self.assertEqual(len(t.calls),8)

    def test_ambiguous_started_request_is_held(self):
        c=Context(self.out); r=c.requests[0]; b=binding(c,'MOCK'); freeze(self.out/'execution.json',b)
        identity=dict(b,id=opid(r),request=r['request'],request_hash=r['request_hash'],stage='gpt_matched_explanation')
        folder=self.out/'operations-v5'/digest(opid(r))
        freeze(folder/'request.json',dict(identity,status='planned')); freeze(folder/'started.json',dict(identity,status='started'))
        t=MockTransport(); value=self.run_mock(t)
        self.assertEqual(len(t.calls),191); self.assertEqual(value['totals']['ambiguous'],1); self.assertFalse(value['complete'])
        self.assertNotIn(r['request']['payload'],t.calls)

    def test_atomic_start_debris_quarantine_never_resends_held_case(self):
        c=Context(self.out); r=c.requests[0]; b=binding(c,'MOCK'); freeze(self.out/'execution.json',b)
        identity=dict(b,id=opid(r),request=r['request'],request_hash=r['request_hash'],stage='gpt_matched_explanation')
        folder=self.out/'operations-v5'/digest(opid(r)); freeze(folder/'request.json',dict(identity,status='planned'))
        debris=folder/'started.json.abcdefgh.tmp'; debris.write_text('partial')
        a=inspect(self.out); self.assertEqual(a['totals']['ambiguous'],1)
        recover(self.out,'Offline test of interrupted atomic write')
        t=MockTransport(); a=self.run_mock(t,1); self.assertEqual(len(t.calls),1)
        self.assertNotEqual(t.calls[0],r['request']['payload']); self.assertEqual(a['totals']['ambiguous'],1)

    def test_payload_tampering_and_mode_mix_fail_closed(self):
        plan=sealed_read(self.out/'plan.json'); plan['requests'][0]['request']['payload']['max_output_tokens']=8192
        plan.pop('artifact_hash'); plan['artifact_hash']=digest(plan)
        (self.out/'plan.json').write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError,'Frozen GPT plan'): self.run_mock()

    def test_mock_live_modes_and_call_limit(self):
        self.run_mock(max_new=1)
        with self.assertRaisesRegex(ValueError,'caches cannot mix'): run(self.out,live=True)
        for cap in (0,193,-1,True):
            with self.assertRaises(ValueError): run(self.out,max_new=cap)

    def test_real_optin_missing_key_fails_without_dispatch(self):
        with patch.dict(os.environ,{},clear=True),patch('exception_study2_gpt_explanation.execution.HTTPTransport',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(ValueError,'OPENAI_API_KEY'): run(self.out,live=True)
        self.assertFalse((self.out/'execution.json').exists())

    def test_export_relocation_hashes_and_blank_annotations(self):
        self.run_mock(max_new=2); bundle=self.root/'bundle.zip'; result=export(self.out,bundle)
        self.assertFalse(result['complete'])
        relocated=self.root/'relocated'
        with zipfile.ZipFile(bundle) as z:
            manifest=json.loads(z.read('bundle-manifest.json'))
            self.assertEqual(set(z.namelist()),set(manifest['files'])|{'bundle-manifest.json'})
            for name,info in manifest['files'].items():
                import hashlib
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),info['sha256'])
            sheet=list(csv.DictReader(io.StringIO(z.read('manual-review.csv').decode())))
            self.assertEqual(len(sheet),192); self.assertTrue(all(r['correct_record_mention']=='not_reviewed' for r in sheet))
            self.assertNotIn('native_on',sheet[0]); z.extractall(relocated)
        r=inspect(relocated); self.assertEqual(r['totals']['completed'],2)
        self.assertEqual(sha(ARCHIVE),SOURCE_SHA256)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.requests=plan_fields(Source(ARCHIVE))['requests']
    def rows(self,callback):
        result=[]
        for r in self.requests:
            cell=r['cell']; answer=callback(cell)
            score=None if answer is None else parse_result(response(('Record.\n' if cell['arm']=='explanation' else '')+answer),cell)
            result.append(dict(cell=cell,score=score))
        return result

    def test_known_extra_conflict_penalty_and_paired_changes(self):
        rows=self.rows(lambda c:c['pattern'] if c['arm']=='explanation' and c['relation']=='conflict' else c['expected'])
        a=outcomes(rows); self.assertEqual(a['primary']['estimate'],1.0); self.assertEqual(a['primary']['block_interval_95'],[1.,1.])
        self.assertEqual(a['paired_changes']['conflict']['control_only_correct'],48)
        self.assertEqual(a['paired_changes']['support']['both_correct'],48)
        self.assertEqual(a['arms']['explanation']['conflict']['conflict_pattern_errors'],48)
        self.assertEqual(a['primary']['block_bootstrap']['observed_clusters'],4)

    def test_all_perfect_and_correct_sensitivity_pairing(self):
        a=outcomes(self.rows(lambda c:c['expected']))
        self.assertEqual(a['primary']['estimate'],0.)
        for arm in ('direct','explanation'):
            self.assertEqual(a['sensitivities'][arm]['record']['label_changes'],48)
            self.assertEqual(a['sensitivities'][arm]['cue']['label_changes'],0)
            self.assertEqual(a['sensitivities'][arm]['record']['planned_pairs'],48)

    def test_unavailable_direct_prevents_primary_and_completion(self):
        rows=self.rows(lambda c:c['expected']); next(r for r in rows if r['cell']['arm']=='direct')['score']=None
        a=outcomes(rows); self.assertIsNone(a['primary']['estimate']); self.assertEqual(a['primary']['unavailable'],1)
        self.assertEqual(sum(x['unavailable'] for x in a['paired_changes'].values()),1)

    def test_invalid_fixed_budget_and_unscorable_pairs(self):
        rows=self.rows(lambda c:c['expected']); rows[0]['score']=parse_result(response('Not a label'),rows[0]['cell'])
        a=outcomes(rows); cell=rows[0]['cell']; g=a['arms'][cell['arm']][cell['relation']]
        self.assertEqual(g['planned'],48); self.assertEqual(g['correct'],47); self.assertEqual(g['accuracy'],47/48)
        self.assertEqual(a['sensitivities'][cell['arm']]['record']['unscorable_pairs'],1)
        self.assertEqual(a['sensitivities'][cell['arm']]['cue']['unscorable_pairs'],1)


if __name__ == '__main__': unittest.main()
