"""Focused v2 acceptance tests; no network, pretrained inference or historical reruns."""
import copy
import gzip
import json
import os
import re
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read,sealed_write
from exception_review.artifacts import freeze
from exception_study2_source_report import planning as v1_planning,parser as v1_parser
from exception_study2_source_report.integrity import contract as v1_contract
from exception_study2_source_report.tokenizer import Tokenizer
from exception_study2_source_report.evidence import Evidence
from exception_study2_source_report_v2 import planning,execution,parser,prior,reporting,VERSION,INTERFACE,PARSER,SUFFIX,BUDGET,INVENTORY
from source_report_fixtures import Tokens,fixture,CountingBackend

V1_CONTRACT='ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d'


class PackedTokens(Tokens):
    """Simple reversible word/whitespace tokenizer for parser-only payload fixtures."""
    def __init__(self):self.words={};self.reverse={}
    def encode(self,text):
        out=[]
        for part in re.findall(r'\s+|\S+',text):
            if part not in self.words:
                index=2000+len(self.words);self.words[part]=index;self.reverse[index]=part
            out.append(self.words[part])
        return out
    def decode_all(self,ids):return ''.join('<eos>' if i==0 else '<assistant>' if i==1000000 else self.reverse[i] for i in ids)
    def decode(self,ids):return self.decode_all([i for i in ids if i not in self.special_ids])


class ParserTests(unittest.TestCase):
    def setUp(self):self.tok=PackedTokens()
    def raw(self,text,eos=True):
        ids=self.tok.encode(text)
        if eos:ids+=[0]
        else:
            padding=16-len(ids);ids+=self.tok.encode(' ')*padding;text+=' '*padding
        return dict(text=text,tokens=ids,finish='eos' if eos else 'length',stopped=eos,next_token_logits={})
    def test_exact_labels_whitespace_eos_and_length_stops(self):
        for label in ('A','B','C','MISSING'):
            for eos in (False,True):
                raw=self.raw(' \n'+label+' "',eos);r=parser.parse_reply(raw,label,self.tok)
                self.assertTrue(r['field_complete']);self.assertTrue(r['field_valid']);self.assertTrue(r['correct'])
                self.assertEqual(r['answer'],label);self.assertEqual(r['eos_observed'],eos)
                self.assertEqual(r['generation_length_stop'],not eos)
    def test_trailing_text_is_retained_not_rescored(self):
        raw=self.raw('A" extra explanation, B is later',False);r=parser.parse_reply(raw,'A',self.tok)
        self.assertTrue(r['correct']);self.assertEqual(r['trailing_text'],raw['text'].split('"',1)[1])
        self.assertEqual(r['field_value'],'A');self.assertTrue(r['generation_length_stop'])
    def test_no_quote_is_incomplete_even_label_and_eos(self):
        for text in ('A','MISSING','A”','', 'A” later B'):
            for eos in (False,True):
                r=parser.parse_reply(self.raw(text,eos),'A',self.tok)
                self.assertFalse(r['field_complete']);self.assertFalse(r['field_valid']);self.assertIsNone(r['answer'])
                self.assertEqual(r['category'],'incomplete_field')
    def test_first_field_prose_multiple_empty_and_later_answers_invalid(self):
        for text in ('The value is A"','A or B"','"A"','a"','A/B"','MISSING A"','wrong" A"','”A”"'):
            r=parser.parse_reply(self.raw(text),'A',self.tok)
            self.assertTrue(r['field_complete']);self.assertFalse(r['valid']);self.assertIsNone(r['answer'])
    def test_wrong_label_is_valid_but_incorrect(self):
        r=parser.parse_reply(self.raw('B"'),'A',self.tok)
        self.assertTrue(r['field_valid']);self.assertFalse(r['correct']);self.assertEqual(r['answer'],'B')
    def test_missing_never_defaulted(self):
        for raw in (None,{},self.raw(''),self.raw('MISSING')):
            r=parser.parse_reply(raw,'MISSING',self.tok);self.assertFalse(r['correct']);self.assertIsNone(r['answer'])
    def test_payload_metadata_errors_cannot_be_rescued_by_closed_field(self):
        cases=[]
        r=self.raw('A"');r['text']='B"';cases.append(r)
        r=self.raw('A"');r['stopped']=False;cases.append(r)
        r=self.raw('A"');r['finish']='length';cases.append(r)
        r=self.raw('A"');r['tokens'][0]=True;cases.append(r)
        r=self.raw('A"');r['tokens'][0]=-1;cases.append(r)
        r=self.raw('A"');r['tokens'].insert(0,1000000);cases.append(r)
        r=self.raw('A"');r['next_token_logits']={'x':[1.]};cases.append(r)
        r=self.raw('A"');r['next_logits']=[1.];cases.append(r)
        r=self.raw('A"',False);r['tokens']+=self.tok.encode(' ');r['text']+=' ';cases.append(r)
        r=self.raw('A"',False);r['tokens']=r['tokens'][:-1];r['text']=r['text'][:-1];cases.append(r)
        for raw in cases:
            r=parser.parse_reply(raw,'A',self.tok);self.assertTrue(r['metadata_errors']);self.assertFalse(r['valid']);self.assertFalse(r['correct'])
    def test_short_length_return_is_malformed_even_closed_correct_field(self):
        r=self.raw('A"');r['tokens'].pop();r.update(stopped=False,finish='length')
        parsed=parser.parse_reply(r,'A',self.tok)
        self.assertIn('length_stop_token_count_not_budget',parsed['metadata_errors']);self.assertFalse(parsed['field_valid'])
    def test_v1_does_not_reclassify_v2_or_failed_v1_returns(self):
        self.assertEqual(v1_contract(),V1_CONTRACT)
        raw=self.raw('A"',False)
        self.assertTrue(parser.parse_reply(raw,'A',self.tok)['correct'])
        self.assertFalse(v1_parser.parse_reply(raw,'A',self.tok)['correct'])
        original=self.raw('The value is A',False)
        self.assertFalse(v1_parser.parse_reply(original,'A',self.tok)['valid'])
        self.assertFalse(parser.parse_reply(original,'A',self.tok)['valid'])


class QuotedBackend(CountingBackend):
    def __init__(self,*args):super().__init__(*args);self.fail_main=False;self.invalid_id=None
    def generate(self,ids,budget,capture_at=()):
        assert budget==16 and capture_at==()
        q=self.queries[digest(ids)];self.calls.append(q['id'])
        if self.fail_main and q['kind']=='main':raise RuntimeError('Persistent synthetic backend failure')
        text=q['expected'] if q['id']==self.invalid_id else q['expected']+'"'
        text=text.ljust(16)
        return dict(text=text,tokens=self.tok.encode(text),stopped=False,finish='length',next_token_logits={})


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.evidence=fixture()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.out=self.root/'v2'
        def forbidden(*a,**k):raise AssertionError('No network, weights, or historical execution')
        for target in ('socket.create_connection','socket.socket.connect','exception_continuation.backend.LocalBackend.__init__',
            'exception_study2_source_report.planning.prepare','exception_study2_source_report.execution.run',
            'exception_study2_v5.runner.collect','exception_study2_v5.runner.technical','exception_study2_v5.readouts.measure'):
            p=patch(target,forbidden);p.start();self.addCleanup(p.stop)
        for target,value in (('Tokenizer',Tokens),('Evidence',lambda *a:self.evidence)):
            p=patch.object(planning,target,value);p.start();self.addCleanup(p.stop)
        for n in ('originals','readouts','tokens'):
            (self.root/n).mkdir();(self.root/n/'untouched.txt').write_text('Immutable synthetic source')
        self.plan=planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        self.backend=QuotedBackend(self.plan,Tokens());self.loads=0
    def factory(self,*a):self.loads+=1;return self.backend
    def run_fake(self,**kw):return execution.run(self.out,_backend_factory=self.factory,**kw)
    def test_inventory_legacy_joins_prefixes_and_controls_unchanged(self):
        old=v1_planning.make_plan(self.evidence);self.assertEqual(self.plan['inventory'],INVENTORY)
        for name in ('source','backend','generation_settings','exclusions'):self.assertEqual(self.plan[name],old[name])
        for a,b in zip(self.plan['main']+self.plan['calibration'],old['main']+old['calibration']):
            for key in ('task_id','world','variant','checkpoint','expected','pattern','input_ids','prefix_ids','source_row_hash','parent_rows','cell_edit'):
                self.assertEqual(a[key],b[key],key)
            self.assertEqual(a.get('legacy'),b.get('legacy'))
            self.assertEqual(a['context_ids'],a['input_ids']+a['prefix_ids']+a['suffix_ids'])
            self.assertEqual(a['suffix'],SUFFIX.format(plate=a['target_plate']))
            self.assertNotEqual(a['context_hash'],b['context_hash']);self.assertNotEqual(a['id'],b['id'])
            self.assertTrue(a['id'].startswith('v5/source-report-v2/'))
        self.assertEqual(self.plan['interface_version'],INTERFACE);self.assertEqual(self.plan['parser_version'],PARSER)
    def test_default_inspect_run_analyze_zero_loads(self):
        with patch.object(execution,'load_backend',side_effect=AssertionError('No load')):
            for f in (execution.inspect,execution.run,execution.analyze):
                r=f(self.out);self.assertEqual(r['this_invocation']['model_loads'],0)
                self.assertEqual(r['this_invocation']['new_generations'],0)
        self.assertEqual(r['executable_now'],12);self.assertEqual(r['main_conditional_on_calibration'],332)
    def test_single_load_full_run_and_cached_zero_load(self):
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(len(self.backend.calls),344)
        self.assertEqual(r['calibration_gate']['status'],'PASSED');self.assertEqual(r['counts']['main']['returned'],332)
        d=r['calibration_field_diagnostics'];self.assertEqual(d['valid_field_with_length_stop'],12);self.assertEqual(d['eos'],0)
        s=r['main_checkpoint_summaries']['512']['0'];self.assertEqual(s['source_accuracy']['estimate'],1)
        self.assertEqual(s['field_diagnostics']['generation_length_stop'],108)
        self.assertEqual(r['paired_changes']['0->512']['returned_pairs'],108)
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Must stay unloaded')))
        self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_generations'],0)
        for n in ('originals','readouts','tokens'):self.assertEqual((self.root/n/'untouched.txt').read_text(),'Immutable synthetic source')
    def test_invalid_calibration_blocks_main_and_cached_load(self):
        self.backend.invalid_id=self.plan['calibration'][0]['id'];r=self.run_fake()
        self.assertEqual(len(self.backend.calls),12);self.assertEqual(r['calibration_gate']['status'],'FAILED')
        self.assertEqual(r['counts']['main']['never_started'],332)
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Failed gate')))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_wrong_valid_calibration_also_blocks_main(self):
        generate=self.backend.generate
        def wrong(*a,**k):
            r=generate(*a,**k)
            if self.backend.calls[-1]==self.plan['calibration'][0]['id']:
                label='B' if self.plan['calibration'][0]['expected']=='A' else 'A'
                r['text']=(label+'"').ljust(16);r['tokens']=self.backend.tok.encode(r['text'])
            return r
        self.backend.generate=wrong;r=self.run_fake()
        self.assertEqual(r['calibration_gate']['status'],'FAILED');self.assertTrue(r['calibration'][0]['source_report']['valid'])
        self.assertEqual(len(self.backend.calls),12)
    def test_first_main_exception_stops_once_then_only_331_resume(self):
        self.backend.fail_main=True;r=self.run_fake();first=self.plan['main'][0]['id']
        self.assertEqual(self.loads,1);self.assertEqual(r['calibration_gate']['status'],'PASSED')
        self.assertEqual(self.backend.calls,[q['id'] for q in self.plan['calibration']]+[first])
        self.assertEqual(r['counts']['main'],dict(planned=332,returned=0,never_started=331,failed=1,ambiguous=0))
        self.assertTrue(all(not (self.out/'operations-v5'/digest(q['id'])).exists() for q in self.plan['main'][1:]))
        before={p:p.read_bytes() for p in (self.out/'operations-v5').rglob('*.json')}
        self.backend.fail_main=False;self.backend.calls.clear();r=self.run_fake()
        self.assertEqual(self.backend.calls,[q['id'] for q in self.plan['main'][1:]])
        self.assertEqual(r['this_invocation']['new_generations'],331);self.assertEqual(r['counts']['main']['failed'],1)
        for p,data in before.items():self.assertEqual(p.read_bytes(),data)
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Only terminal work remains')))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_request_only_executes_and_ambiguous_never_resends(self):
        self.run_fake(calibration_only=True);identity=execution.content_identity(self.plan,'MOCK')
        for q,started in zip(self.plan['main'][:2],(True,False)):
            req=execution.request(q,self.plan);entry=dict(identity,id=q['id'],request=req,request_hash=digest(req),stage='source_report_generation',status='planned')
            folder=self.out/'operations-v5'/digest(q['id']);freeze(folder/'request.json',entry)
            if started:freeze(folder/'started.json',dict(entry,status='started'))
        self.backend.calls.clear();r=self.run_fake()
        self.assertNotIn(self.plan['main'][0]['id'],self.backend.calls);self.assertIn(self.plan['main'][1]['id'],self.backend.calls)
        self.assertEqual(len(self.backend.calls),331);self.assertEqual(r['counts']['main']['ambiguous'],1)
    def test_returned_invalid_main_not_exception_or_retry(self):
        self.backend.invalid_id=self.plan['main'][0]['id'];r=self.run_fake()
        self.assertEqual(len(self.backend.calls),344);self.assertEqual(r['counts']['main']['failed'],0)
        self.assertNotIn('stopped_after_exception',r['this_invocation'])
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Never retry invalid return')))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_durable_raw_recovery_after_report_interruption(self):
        with patch.object(reporting,'save_report',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Raw cache exists')))
        self.assertEqual(r['counts']['all']['returned'],344);self.assertEqual(r['this_invocation']['new_generations'],0)
    def test_lock_and_source_v1_output_separation(self):
        with run_lock(self.out):
            with self.assertRaisesRegex(ValueError,'Another process'):self.run_fake()
        with self.assertRaisesRegex(ValueError,'outside'):
            planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.root/'v1/new',self.root/'v1')
        with self.assertRaisesRegex(ValueError,'outside'):
            planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.root/'originals/new')
        with self.assertRaisesRegex(ValueError,'SAME output'):
            planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        self.assertEqual(self.loads,0)
    def test_v1_plan_or_operations_cannot_be_v2_cache(self):
        v1=self.root/'v1';v1.mkdir();old=v1_planning.make_plan(self.evidence)
        sealed_write(v1/'source-report-plan.json',old);before=(v1/'source-report-plan.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'identity mismatch'):execution.run(v1,_backend_factory=self.factory)
        self.assertEqual((v1/'source-report-plan.json').read_bytes(),before)
        q=self.plan['main'][0];op_id='v5/source-report/'+q['query_hash'];req=execution.request(q,self.plan)
        identity=execution.content_identity(self.plan,'MOCK');freeze(self.out/'execution-content.json',identity)
        freeze(self.out/'operations-v5'/digest(op_id)/'request.json',dict(identity,id=op_id,request=req,request_hash=digest(req),stage='source_report_generation',status='planned'))
        with self.assertRaisesRegex(ValueError,'Cross-version'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_model_source_plan_tamper_fails_offline(self):
        for field in ('context','code_contract','backend_hash'):
            p=copy.deepcopy(self.plan)
            if field=='context':p['main'][0]['context_ids'][0]+=1
            else:p[field]='bad'
            sealed_write(self.out/'source-report-plan.json',p)
            with self.assertRaises(ValueError):self.run_fake()
        sealed_write(self.out/'source-report-plan.json',self.plan);self.assertEqual(self.loads,0)
        self.backend.identity['hardware']='wrong hardware'
        with self.assertRaisesRegex(ValueError,'backend differs'):self.run_fake()
        self.assertEqual(self.backend.calls,[])
    def test_truthful_ordinary_revision_change_keeps_cache(self):
        self.run_fake(calibration_only=True)
        with patch.object(execution,'revision',return_value='new-content-compatible-head'):
            r=self.run_fake()
        self.assertEqual(r['this_invocation']['extension_revision'],'new-content-compatible-head')
        self.assertEqual(r['this_invocation']['new_generations'],332)
    def test_archive_snapshots_without_overwrite_or_source_changes(self):
        execution.run(self.out);target=self.root/'archive.tar.gz'
        before={p:p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
        r=execution.archive(self.out,target);self.assertEqual(r['model_loads'],0)
        with tarfile.open(target) as t:
            names=t.getnames();self.assertIn('v2/source-report-plan.json',names);self.assertIn('v2/report.json',names)
            self.assertNotIn('v2/run.lock',names)
        with self.assertRaises(FileExistsError):execution.archive(self.out,target)
        for p,data in before.items():self.assertEqual(p.read_bytes(),data)
        with self.assertRaisesRegex(ValueError,'outside'):execution.archive(self.out,self.out/'bad.tar.gz')
    def test_prior_unavailable_never_invents_hashes(self):
        p=prior.prior_evidence(self.root/'absent',Tokens())
        self.assertFalse(p['available']);self.assertEqual(p['actual_artifact_hashes'],{})
        self.assertEqual(p['reported_v1_status'],'FAILED');self.assertEqual(p['reference_plan_hash'],prior.V1_PLAN_HASH)
        self.assertEqual(v1_contract(),V1_CONTRACT)


@unittest.skipUnless(all(os.environ.get(k) for k in ('QWEN3_TOKENIZER_DIR','STUDY2_SOURCE_REPORT_ORIGINALS','STUDY2_SOURCE_REPORT_READOUTS','STUDY2_SOURCE_REPORT_V1_OUTPUT')),'Explicit local tokenizer/original/readout/v1 paths required; never downloads')
class SavedDataTests(unittest.TestCase):
    def test_real_saved_inputs_v1_failed_provenance_and_pinned_v2_suffix(self):
        def forbidden(*a,**kw):raise AssertionError('No network or weights')
        from exception_continuation import backend
        real=backend.file_hash;hashed=[]
        def checked(p):
            self.assertNotEqual(Path(p).suffix,'.safetensors');hashed.append(str(p));return real(p)
        original_contract=v1_contract();root=Path(os.environ['STUDY2_SOURCE_REPORT_V1_OUTPUT'])
        before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with patch('socket.create_connection',forbidden),patch('socket.socket.connect',forbidden),patch.object(backend.LocalBackend,'__init__',forbidden),patch.object(backend,'file_hash',checked):
            tok=Tokenizer(os.environ['QWEN3_TOKENIZER_DIR']);e=Evidence(os.environ['STUDY2_SOURCE_REPORT_ORIGINALS'],os.environ['STUDY2_SOURCE_REPORT_READOUTS'],tok)
            prior_result=prior.prior_evidence(root,tok);p=planning.make_plan(e,prior_result)
        self.assertEqual(len(hashed),7);self.assertEqual(p['inventory'],INVENTORY)
        self.assertEqual(prior_result['original_parser_gate']['status'],'FAILED')
        self.assertEqual(prior_result['valid_v1_calibration'],0);self.assertEqual(prior_result['v1_length_stops'],12)
        self.assertEqual(prior_result['main_never_started'],332);self.assertTrue(prior_result['actual_artifact_hashes'])
        for q in p['calibration']+p['main']:
            self.assertEqual(tok.decode_all(q['suffix_ids']),SUFFIX.format(plate=q['target_plate']))
            self.assertEqual(q['context_ids'],q['input_ids']+q['prefix_ids']+q['suffix_ids'])
        self.assertEqual(p['inventory']['legacy_entries'],664)
        for f,data in before.items():self.assertEqual(f.read_bytes(),data)
        self.assertEqual(v1_contract(),original_contract);self.assertEqual(original_contract,V1_CONTRACT)
