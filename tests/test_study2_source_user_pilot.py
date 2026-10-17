"""Focused offline pilot tests; synthetic templates never certify real serialization."""
import copy
import json
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from exception_pilot.core import digest
from exception_pilot.storage import run_lock,write_json
from exception_continuation.runner import sealed_read,sealed_write
from exception_review.artifacts import freeze
from exception_study2_source_report_v2 import planning as v2_plan,execution as v2_exec,parser as v2_parser
from exception_study2_source_report.integrity import contract as v1_contract
from exception_study2_source_report_v2.integrity import contract as v2_contract
from exception_study2_source_user_pilot import planning,execution,reporting,parent,rendering,parser
from exception_study2_source_user_pilot import MESSAGE,NAMESPACE,INVENTORY,V1_CONTRACT,V2_CONTRACT,PARENT_PLAN,PARENT_ARTIFACTS_HASH
from exception_study2_source_user_pilot.integrity import artifact_files
from source_report_fixtures import Tokens,fixture


class TemplateTokens(Tokens):
    """Character-token fake with explicit role controls; not the pinned tokenizer."""
    def __init__(self,*args):
        self.tokenizer=self;self.chat_template='SYNTHETIC_QWEN_SHAPE'
        self.identity=dict(Tokens.identity,chat_template=self.chat_template)
    def encode(self,text):
        out=[]
        while text:
            if text.startswith('<|im_end|>'):out.append(0);text=text[10:]
            elif text.startswith('<|im_start|>'):out.append(1000000);text=text[12:]
            else:out.append(1000+ord(text[0]));text=text[1:]
        return out
    def decode_all(self,ids):
        return ''.join('<|im_end|>' if i==0 else '<|im_start|>' if i==1000000 else chr(i-1000) for i in ids)
    def convert_tokens_to_ids(self,token):return self.encode(token)[0]
    def prompt(self,text):return self.apply_chat_template([dict(role='user',content=text)],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    def apply_chat_template(self,messages,tokenize,add_generation_prompt,enable_thinking):
        assert add_generation_prompt and enable_thinking is False
        text=''.join('<|im_start|>'+m['role']+'\n'+m['content']+'<|im_end|>\n' for m in messages)+rendering.SCAFFOLD
        return self.encode(text) if tokenize else text


def raw(tok,text,eos=True):
    if eos:ids=tok.encode(text)+[0]
    else:text=text[:16].ljust(16);ids=tok.encode(text)
    return dict(text=text,tokens=ids,finish='eos' if eos else 'length',stopped=eos,next_token_logits={})


class FakeBackend:
    simulated=True
    def __init__(self,p,t):
        self.identity=copy.deepcopy(p['backend']);self.eos_ids=t.eos_ids;self.t=t
        self.queries={q['context_hash']:q for q in p['queries']};self.calls=[];self.failure=False;self.answer=None
    def generate(self,ids,budget,capture_at=()):
        assert budget==16 and capture_at==()
        q=self.queries[digest(ids)];self.calls.append(q['id'])
        if self.failure:raise RuntimeError('Persistent offline failure')
        return raw(self.t,self.answer if self.answer is not None else q['expected'])
    def score(self,*a,**k):raise AssertionError('No candidate scoring')


def fake_parent(root,tok):
    e=fixture();e.tokenizer=tok
    for source in (e.pilot,e.remaining):
        for row in source.rows.values():
            row['input_ids']=tok.prompt(row['task']['prompt'])
            row['artifact_hash']=digest({k:v for k,v in row.items() if k!='artifact_hash'})
    e.remaining.execution['backend']['config']={'model_dir':str(root/'model')}
    e.remaining.execution['backend_hash']=digest(e.remaining.execution['backend'])
    e.pilot.execution=e.remaining.execution
    e.binding.update(pilot=e.pilot.binding,historical_execution_hash=e.pilot.execution['artifact_hash'],technical_hash=e.pilot.technical['artifact_hash'])
    p=v2_plan.make_plan(e)
    p['prior_v1']=dict(available=True,v1_code_contract=V1_CONTRACT,original_parser_gate={'status':'FAILED'},valid_v1_calibration=0)
    folder=root/'parent';folder.mkdir()
    p=freeze(folder/'source-report-plan.json',p)
    freeze(folder/'locations.json',dict(originals=str(root/'originals'),tokenizer=str(root/'tokens')))
    binding=v2_exec.content_identity(p,'LIVE_LOCAL');ex=freeze(folder/'execution-content.json',binding)
    for q in p['calibration']:
        req=v2_exec.request(q,p);entry=dict(binding,id=q['id'],request=req,request_hash=digest(req),stage='source_report_generation')
        opdir=folder/'operations-v5'/digest(q['id'])
        freeze(opdir/'request.json',dict(entry,status='planned'));freeze(opdir/'started.json',dict(entry,status='started'))
        response=raw(tok,q['expected']+'"') if q['kind']=='calibration_present' else raw(tok,q['target_plate']+' | row features',False)
        freeze(opdir/'returned.json',dict(entry,status='returned',result=response))
        freeze(folder/'operation-execution'/(digest(q['id'])+'.json'),dict(operation_id=q['id'],request_hash=digest(req),
            execution_content_hash=ex['artifact_hash'],extension_revision='test',historical_revision=p['source']['historical_revision']))
    c=SimpleNamespace(out=folder,plan=p,queries={q['id']:q for q in p['calibration']+p['main']},tokenizer=tok)
    saved,mode=v2_exec.journal(c);scores=v2_exec.parsed(c,saved)
    write_json(folder/'report.json',dict(plan_hash=p['artifact_hash'],measurement_mode=mode,
        calibration_gate=v2_exec.gate(c,saved,scores),calibration=[dict(operation_id=q['id'],source_report=scores[q['id']]) for q in p['calibration']]))
    return e,p,folder


class ParserTests(unittest.TestCase):
    def setUp(self):self.t=TemplateTokens()
    def test_exact_labels_missing_and_wrong(self):
        for label in ('A','B','C','MISSING'):
            r=parser.parse_reply(raw(self.t,' \n'+label+'\n'),label,self.t)
            for k in ('raw_integrity','complete','format_valid','valid','correct'):self.assertTrue(r[k])
        r=parser.parse_reply(raw(self.t,'B'),'A',self.t)
        self.assertTrue(r['valid']);self.assertFalse(r['correct']);self.assertEqual(r['category'],'wrong')
    def test_quotes_prose_rows_punctuation_case_never_salvaged(self):
        for text in ('"A"','A.','a','The value is A','P | row | A','A B','MISSING,',''):
            r=parser.parse_reply(raw(self.t,text),'A',self.t)
            self.assertTrue(r['raw_integrity']);self.assertTrue(r['complete']);self.assertFalse(r['valid'])
    def test_length_label_incomplete_and_short_length_malformed(self):
        r=parser.parse_reply(raw(self.t,'A',False),'A',self.t)
        self.assertTrue(r['raw_integrity']);self.assertTrue(r['format_valid']);self.assertFalse(r['complete']);self.assertFalse(r['correct'])
        x=raw(self.t,'A');x['tokens'].pop();x.update(finish='length',stopped=False)
        r=parser.parse_reply(x,'A',self.t);self.assertIn('length_stop_token_count_not_budget',r['metadata_errors'])
    def test_metadata_integrity_and_malformed_payload(self):
        cases=[None,{},raw(self.t,'A '*9)]
        for key,value in (('text','B'),('tokens',[True]),('tokens',[-1]),('tokens',[99999999]),('stopped',False),('finish','length'),('next_logits',[0.]),('next_token_logits',{'0':[1]})):
            x=raw(self.t,'A');x[key]=value;cases.append(x)
        x=raw(self.t,'A');x['tokens'].insert(0,1000000);cases.append(x)
        x=raw(self.t,'A');x['tokens'].insert(0,0);cases.append(x)
        for x in cases:
            r=parser.parse_reply(x,'A',self.t);self.assertTrue(r['metadata_errors']);self.assertFalse(r['raw_integrity']);self.assertFalse(r['correct'])


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.out=self.root/'child';self.t=TemplateTokens()
        for name in ('originals','tokens','model'):(self.root/name).mkdir()
        self.e,self.pp,self.parent=fake_parent(self.root,self.t)
        def forbid(*a,**k):raise AssertionError('No network, weights, or parent execution')
        for target in ('socket.create_connection','socket.socket.connect','exception_continuation.backend.LocalBackend.__init__',
                       'exception_study2_source_report.execution.run','exception_study2_source_report_v2.execution.run',
                       'exception_study2_source_report_v2.execution.SourceSession'):
            p=patch(target,forbid);p.start();self.addCleanup(p.stop)
        for module,key,value in ((planning,'Tokenizer',lambda *a:self.t),(parent,'Source',lambda *a,**k:self.e.pilot),(parent,'PARENT_PLAN',self.pp['artifact_hash']),(parent,'PARENT_ARTIFACTS_HASH',digest(artifact_files(self.parent)))):
            p=patch.object(module,key,value);p.start();self.addCleanup(p.stop)
        self.before=artifact_files(self.parent)
        self.plan=planning.prepare(self.parent,self.out)
        self.backend=FakeBackend(self.plan,self.t);self.loads=0
    def factory(self,*a):self.loads+=1;return self.backend
    def run_fake(self):return execution.run(self.out,_backend_factory=self.factory)
    def test_exact_inventory_origin_hashes_and_prefixes(self):
        self.assertEqual(self.plan['inventory'],INVENTORY);self.assertEqual(self.plan['main_planned'],0);self.assertNotIn('main',self.plan)
        for q,p in zip(self.plan['queries'],self.pp['calibration']):
            self.assertEqual(q['origin_query'],p);self.assertEqual(q['origin_query_hash'],p['query_hash']);self.assertNotEqual(q['id'],p['id'])
            self.assertEqual(q['old_context_ids'],p['input_ids']);self.assertEqual(q['context_ids'],p['input_ids']+q['bridge_ids'])
            self.assertEqual(q['new_user_message'],MESSAGE.format(plate=p['target_plate']))
            self.assertNotIn(p['suffix'],self.t.decode_all(q['context_ids']))
            self.assertNotIn(rendering.SENTINEL,self.t.decode_all(q['context_ids']))
            self.assertEqual(len(q['role_boundaries']),4);self.assertTrue(q['empty_old_assistant_closed'])
            self.assertEqual(self.t.decode_all(q['context_ids']).count(rendering.SCAFFOLD),2)
        self.assertEqual(artifact_files(self.parent),self.before)
        self.assertEqual(v1_contract(),V1_CONTRACT);self.assertEqual(v2_contract(),V2_CONTRACT)
    def test_all_correct_one_load_twelve_calls_completed_resume_zero(self):
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(len(self.backend.calls),12)
        self.assertEqual(r['new_pilot_criterion']['status'],'PASSED');self.assertEqual(r['main_planned'],0)
        self.assertEqual(r['next_stage'],'STOP_AFTER_PILOT');self.assertEqual(r['source_present']['correct'],8);self.assertEqual(r['literal_missing']['correct'],4)
        r=execution.run(self.out,_backend_factory=lambda *a:self.fail('Completed must not load'))
        self.assertEqual(r['this_invocation']['new_generations'],0);self.assertEqual(r['this_invocation']['model_loads'],0)
        self.assertEqual(r['this_invocation']['reused_child_returns'],12);self.assertEqual(r['this_invocation']['prior_v2_returns'],12)
        self.assertEqual(artifact_files(self.parent),self.before)
    def test_all_wrong_or_verbose_collects_all_twelve(self):
        self.backend.answer='wrong';r=self.run_fake()
        self.assertEqual(len(self.backend.calls),12);self.assertEqual(r['counts']['returned_unsuccessful'],12)
        self.assertEqual(r['counts']['correct_per_returned'],dict(numerator=0,denominator=12))
        self.assertEqual(r['new_pilot_criterion']['status'],'FAILED');self.assertEqual(r['next_stage'],'STOP_AFTER_PILOT')
    def test_all_wrong_valid_labels_collect_all(self):
        original=self.backend.generate
        def wrong(ids,*a,**k):
            original(ids,*a,**k);q=self.backend.queries[digest(ids)]
            return raw(self.t,'B' if q['expected']!='B' else 'A')
        self.backend.generate=wrong;r=self.run_fake();self.assertEqual(len(self.backend.calls),12)
        self.assertTrue(all(x['score']['valid'] and not x['score']['correct'] for x in r['cases']))
    def test_first_exception_one_failed_eleven_never_started_resume_skips(self):
        self.backend.failure=True;r=self.run_fake();first=self.plan['queries'][0]['id']
        self.assertEqual(self.backend.calls,[first]);self.assertEqual(r['counts']['failed'],1);self.assertEqual(r['counts']['never_started'],11)
        self.assertEqual(r['counts']['correct_per_returned']['denominator'],0)
        for q in self.plan['queries'][1:]:self.assertFalse((self.out/'operations-v5'/digest(q['id'])).exists())
        before=artifact_files(self.out/'operations-v5');self.backend.failure=False;self.backend.calls.clear();r=self.run_fake()
        self.assertEqual(self.backend.calls,[q['id'] for q in self.plan['queries'][1:]])
        for name,h in before.items():self.assertEqual(artifact_files(self.out/'operations-v5')[name],h)
        self.assertEqual(r['new_pilot_criterion']['status'],'FAILED');self.assertFalse(r['main_eligible'])
        self.assertEqual(r['collection_status'],'INCOMPLETE');self.assertEqual(r['counts']['correct_per_returned'],dict(numerator=11,denominator=11))
        r=execution.run(self.out,_backend_factory=lambda *a:self.fail('Terminal failures cannot reload'))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_ambiguous_skipped_request_only_runs(self):
        binding=execution.identity(self.plan,'MOCK');freeze(self.out/'execution-content.json',binding)
        for q,started in zip(self.plan['queries'][:2],(True,False)):
            req=execution.request(q,self.plan);entry=dict(binding,id=q['id'],request=req,request_hash=digest(req),stage=execution.STAGE)
            path=self.out/'operations-v5'/digest(q['id']);freeze(path/'request.json',dict(entry,status='planned'))
            if started:freeze(path/'started.json',dict(entry,status='started'))
        r=self.run_fake();self.assertEqual(len(self.backend.calls),11);self.assertNotIn(self.plan['queries'][0]['id'],self.backend.calls)
        self.assertEqual(r['counts']['ambiguous'],1);self.assertEqual(r['counts']['returned'],11)
    def test_malformed_returns_terminal_not_exception(self):
        def bad(ids,*a,**k):self.backend.calls.append(digest(ids));return None
        self.backend.generate=bad;r=self.run_fake()
        self.assertEqual(len(self.backend.calls),12);self.assertEqual(r['counts']['returned_unsuccessful'],12);self.assertEqual(r['counts']['failed'],0)
        self.assertTrue(all(x['score']['metadata_errors'] for x in r['cases']))
    def test_durable_raw_recovery_after_report_interruption(self):
        with patch.object(reporting,'save_report',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=execution.run(self.out,_backend_factory=lambda *a:self.fail('Durable returns already exist'))
        self.assertEqual(r['counts']['returned'],12);self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_default_run_inspect_and_archive_do_not_load(self):
        with patch.object(execution,'load_backend',side_effect=AssertionError('No weights')):
            for f in (execution.inspect,execution.run):
                r=f(self.out);self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['counts']['never_started'],12)
            target=self.root/'child.tar.gz';execution.archive(self.out,target)
        with tarfile.open(target) as t:
            names=t.getnames();self.assertIn('child/parent-evidence/report.json',names);self.assertIn('child/contexts/00.txt',names)
        with self.assertRaises(FileExistsError):execution.archive(self.out,target)
        self.assertEqual(artifact_files(self.parent),self.before)
    def test_lock_separation_and_prepare_no_resampling(self):
        with run_lock(self.out):
            with self.assertRaisesRegex(ValueError,'Another process'):self.run_fake()
        with self.assertRaisesRegex(ValueError,'SAME output'):planning.prepare(self.parent,self.out)
        for out in (self.parent/'child',self.root/'tokens/child',self.root/'model/child',self.root/'originals/child'):
            with self.assertRaisesRegex(ValueError,'outside'):planning.prepare(self.parent,out)
    def test_cross_version_and_mock_live_cache_separation(self):
        self.run_fake()
        with self.assertRaisesRegex(ValueError,'MOCK/LIVE'):execution.run(self.out,True)
        opid='v5/source-report-v2/wrong';binding=execution.identity(self.plan,'MOCK');req={}
        freeze(self.out/'operations-v5'/digest(opid)/'request.json',dict(binding,id=opid,request=req,request_hash=digest(req),stage=execution.STAGE,status='planned'))
        with self.assertRaisesRegex(ValueError,'Cross-version'):self.run_fake()
    def test_plan_context_parent_and_backend_mismatch_block(self):
        value=copy.deepcopy(self.plan);value['queries'][0]['context_ids'][0]+=1;sealed_write(self.out/'pilot-plan.json',value)
        with self.assertRaises(ValueError):self.run_fake()
        sealed_write(self.out/'pilot-plan.json',self.plan)
        path=self.out/'parent-evidence/report.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'snapshot'):self.run_fake()
        path.write_bytes((self.parent/'report.json').read_bytes())
        self.backend.identity['hardware']='OTHER'
        with self.assertRaisesRegex(ValueError,'backend identity'):self.run_fake()
        self.assertEqual(self.backend.calls,[])
    def test_parent_missing_return_or_any_main_request_blocks(self):
        q=self.pp['main'][0];req=v2_exec.request(q,self.pp);binding=v2_exec.content_identity(self.pp,'LIVE_LOCAL')
        freeze(self.parent/'operations-v5'/digest(q['id'])/'request.json',dict(binding,id=q['id'],request=req,request_hash=digest(req),stage='source_report_generation',status='planned'))
        with self.assertRaisesRegex(ValueError,'no parent main records'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_parent_wrong_plan_or_original_verdict_blocks(self):
        with patch.object(parent,'PARENT_PLAN','wrong'):
            with self.assertRaisesRegex(ValueError,'Exact failed parent'):self.run_fake()
        report=json.loads((self.parent/'report.json').read_text());report['calibration_gate']['status']='PASSED';write_json(self.parent/'report.json',report)
        with self.assertRaisesRegex(ValueError,'verdict disagree'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_bridge_rejects_duplicate_sentinel_controls_or_changed_saved_prompt(self):
        q=self.plan['queries'][0];args=(self.t,q['original_user_prompt'],q['target_plate'],q['old_context_ids'])
        with self.assertRaisesRegex(ValueError,'unique'):rendering.bridge(self.t,q['original_user_prompt']+rendering.SENTINEL,q['target_plate'],q['old_context_ids'])
        with self.assertRaisesRegex(ValueError,'structural'):rendering.bridge(self.t,q['original_user_prompt'],'<|im_start|>',q['old_context_ids'])
        with self.assertRaisesRegex(ValueError,'reproduce'):rendering.bridge(*args[:-1],args[-1]+[1234])
        original=self.t.apply_chat_template
        def wrong(messages,**kw):
            value=original(messages,**kw)
            return value+'extra' if not kw['tokenize'] else value
        with patch.object(self.t,'apply_chat_template',wrong):
            with self.assertRaises(ValueError):rendering.bridge(*args)


REAL_TOK=os.environ.get('QWEN3_TOKENIZER_DIR','/tmp/study2-qwen3-tokenizer')
REAL_PARENT=os.environ.get('STUDY2_SOURCE_USER_PARENT','/tmp/study2-source-user-parent/study2-source-report-v2')
REAL_SOURCE=os.environ.get('STUDY2_SOURCE_REPORT_ORIGINALS','/tmp/study2-source-report-input/study2-v5-replication-v1/originals')
@unittest.skipUnless((Path(REAL_PARENT)/'source-report-plan.json').is_file() and (Path(REAL_SOURCE)/'plan-v5.json').is_file(),
    'Actual saved parent/source artifacts unavailable')
class SavedEvidenceTests(unittest.TestCase):
    def test_actual_parent_seals_inventory_source_binding_and_original_failed_report(self):
        from exception_study2_v5.runner import Source
        root=Path(REAL_PARENT);before=artifact_files(root);p=sealed_read(root/'source-report-plan.json')
        self.assertEqual(p['artifact_hash'],PARENT_PLAN);self.assertEqual(p['code_contract'],V2_CONTRACT)
        self.assertEqual(digest(before),PARENT_ARTIFACTS_HASH)
        c=SimpleNamespace(out=root,plan=p,queries={q['id']:q for q in p['calibration']+p['main']})
        saved,mode=v2_exec.journal(c)
        self.assertEqual(mode,'LIVE_LOCAL');self.assertEqual(set(saved),{q['id'] for q in p['calibration']})
        self.assertTrue(all(o['status']=='returned' for o in saved.values()))
        report=json.loads((root/'report.json').read_text());scores={r['operation_id']:r['source_report'] for r in report['calibration']}
        self.assertEqual(report['plan_hash'],PARENT_PLAN);self.assertEqual(report['calibration_gate'],v2_exec.gate(c,saved,scores))
        self.assertEqual(report['calibration_gate']['status'],'FAILED')
        source=Source(REAL_SOURCE,scope='pilot');self.assertEqual(source.binding,p['source']['pilot'])
        self.assertEqual([(q['world'],q['variant'],q['kind']) for q in p['calibration']],
            [(f'staged-v5-{i:03d}',v,k) for i in range(4) for v,k in ((0,'calibration_present'),(1,'calibration_present'),(0,'calibration_missing'))])
        for q in p['calibration']:
            self.assertEqual(digest({k:v for k,v in q.items() if k not in ('id','query_hash')}),q['query_hash'])
            self.assertEqual(q['prefix_ids'],[]);self.assertEqual(q['checkpoint'],0)
            row=source.rows[q['task_id']];self.assertEqual(q['source_row_hash'],row['artifact_hash'])
            if q['kind']=='calibration_present':
                self.assertEqual(q['input_ids'],row['input_ids']);self.assertTrue(scores[q['id']]['correct'])
            else:
                changed=[v2_plan.missing_prompt(source.rows[f"{q['world']}/v{v}/original/visible"]['task'])[0] for v in (0,1)]
                self.assertEqual(changed[0],changed[1]);self.assertEqual(changed[0],q['cell_edit']['prompt'])
                self.assertFalse(scores[q['id']]['correct']);self.assertEqual(len(saved[q['id']]['result']['tokens']),16)
        for name in before:
            if name.endswith('.json') and name!='report.json':sealed_read(root/name)
        self.assertEqual(artifact_files(root),before)
        # This check intentionally does NOT claim token decoding or new bridge validation.


@unittest.skipUnless((Path(REAL_TOK)/'tokenizer.json').is_file() and (Path(REAL_PARENT)/'source-report-plan.json').is_file(),
    'Pinned tokenizer assets unavailable; real parent/tokenizer integration REQUIRED at RunPod prepare, never replaced by fixtures')
class RealIntegrationTests(unittest.TestCase):
    def test_actual_parent_all_twelve_real_tokenized_bridges_and_preservation(self):
        from exception_study2_source_report.tokenizer import Tokenizer
        before=artifact_files(REAL_PARENT)
        def forbid(*a,**k):raise AssertionError('No network or weights')
        with patch('socket.create_connection',forbid),patch('socket.socket.connect',forbid),patch('exception_continuation.backend.LocalBackend.__init__',forbid):
            tok=Tokenizer(REAL_TOK);p=parent.Parent(REAL_PARENT,REAL_SOURCE,tok);plan=planning.make_plan(p,tok)
        self.assertEqual(p.plan['artifact_hash'],PARENT_PLAN);self.assertEqual(plan['inventory'],INVENTORY)
        for q in plan['queries']:
            self.assertEqual(q['context_ids'][:len(q['old_context_ids'])],q['old_context_ids'])
            self.assertEqual(q['bridge_text'],'<|im_end|>\n<|im_start|>user\n'+q['new_user_message']+'<|im_end|>\n'+rendering.SCAFFOLD)
            self.assertEqual(tok.tokenizer.apply_chat_template([dict(role='user',content=q['new_user_message'])],tokenize=True,add_generation_prompt=True,enable_thinking=False),q['bridge_ids'][len(tok.encode('<|im_end|>\n')):])
        self.assertEqual(artifact_files(REAL_PARENT),before)
        self.assertEqual(v1_contract(),V1_CONTRACT);self.assertEqual(v2_contract(),V2_CONTRACT)

if __name__=='__main__':unittest.main()
