"""Focused main-extension risks; no historical suite or unchanged-parser retests."""
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
from exception_review.artifacts import freeze
from exception_continuation.runner import sealed_read,sealed_write
from exception_study2_source_user_pilot import parent as old_parent,planning as pilot_planning,execution as pilot_execution
from exception_study2_source_user_pilot.integrity import artifact_files,contract as pilot_contract,v1_contract,v2_contract
from exception_study2_source_user_pilot import V1_CONTRACT,V2_CONTRACT
from exception_study2_source_user_pilot.rendering import bridge as pilot_bridge
from exception_study2_source_user_pilot.parser import parse_reply
from exception_study2_source_user_main import planning,evidence,execution,reporting
from exception_study2_source_user_main import PILOT_CONTRACT,PILOT_PLAN,INVENTORY,EXCLUDED
from source_report_fixtures import fixture
from test_study2_source_user_pilot import TemplateTokens,raw,fake_parent


def seal_pilot_returns(root,plan,tok):
    binding=pilot_execution.identity(plan,'LIVE_LOCAL');ex=freeze(root/'execution-content.json',binding)
    invocation='synthetic-live-pilot';revision='SYNTHETIC_ONLY'
    freeze(root/'invocations'/invocation/'started.json',dict(plan_hash=plan['artifact_hash'],measurement_mode='LIVE_LOCAL',
        executable_ids=[q['id'] for q in plan['queries']],extension_revision=revision))
    for q in plan['queries']:
        req=pilot_execution.request(q,plan);entry=dict(binding,id=q['id'],request=req,request_hash=digest(req),stage=pilot_execution.STAGE)
        folder=root/'operations-v5'/digest(q['id'])
        for status in ('planned','started','returned'):
            value=dict(entry,status=status)
            if status=='returned':value['result']=raw(tok,q['expected'])
            freeze(folder/('request.json' if status=='planned' else status+'.json'),value)
        freeze(root/'operation-execution'/(digest(q['id'])+'.json'),dict(operation_id=q['id'],request_hash=digest(req),
            execution_content_hash=ex['artifact_hash'],extension_revision=revision,historical_revision=plan['historical_revision'],invocation=invocation))
    freeze(root/'invocations'/invocation/'finished.json',dict(plan_hash=plan['artifact_hash'],measurement_mode='LIVE_LOCAL',
        model_loads=1,model_load_attempts=1,new_generations=12,reused_child_returns=0,extension_revision=revision,status='COMPLETE'))
    write_json(root/'report.json',dict(this_invocation={'model_loads':0,'new_generations':0}))


class Backend:
    simulated=True
    def __init__(self,plan,tok):
        self.identity=copy.deepcopy(plan['backend']);self.eos_ids=tok.eos_ids;self.tok=tok
        self.queries={q['context_hash']:q for q in plan['queries']};self.calls=[];self.fail=False;self.mode='correct'
    def generate(self,ids,budget,capture_at=()):
        assert budget==16 and capture_at==()
        q=self.queries[digest(ids)];self.calls.append(q['id'])
        if self.fail:raise RuntimeError('Persistent mock failure')
        if self.mode=='mixed':
            i=len(self.calls)%5
            if i==0:return None
            if i==1:return raw(self.tok,'MISSING')
            if i==2:return raw(self.tok,'verbose A')
            if i==3:return raw(self.tok,q['expected'],False)
            return raw(self.tok,'B' if q['expected']!='B' else 'A')
        return raw(self.tok,q['expected'])
    def score(self,*a,**k):raise AssertionError('No new cached-cue scoring')


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.out=self.root/'main';self.pilot=self.root/'pilot';self.tok=TemplateTokens()
        for name in ('originals','tokens','model','readouts'):(self.root/name).mkdir()
        e=fixture();e.binding['remaining']=e.remaining.binding
        with patch('test_study2_source_user_pilot.fixture',return_value=e):self.e,self.v2,self.v2root=fake_parent(self.root,self.tok)
        for module,key,value in ((old_parent,'Source',lambda *a,**k:self.e.pilot),(old_parent,'PARENT_PLAN',self.v2['artifact_hash']),
            (old_parent,'PARENT_ARTIFACTS_HASH',digest(artifact_files(self.v2root))),(pilot_planning,'Tokenizer',lambda *a:self.tok),
            (planning,'Tokenizer',lambda *a:self.tok),(evidence,'Source',lambda *a,**k:self.e.remaining),
            (evidence,'legacy',lambda *a:(self.e.legacy,self.e.binding['legacy']))):
            p=patch.object(module,key,value);p.start();self.addCleanup(p.stop)
        pp=pilot_planning.prepare(self.v2root,self.pilot);seal_pilot_returns(self.pilot,pp,self.tok)
        p=patch.object(evidence,'PILOT_PLAN',pp['artifact_hash']);p.start();self.addCleanup(p.stop)
        self.values={j['computation_id']:dict(original_value_hash=j['original_value_hash'],fixture='synthetic') for q in self.v2['main'] for j in q['legacy'].values()}
        p=patch.object(planning,'raw_join_evidence',return_value=self.values);p.start();self.addCleanup(p.stop)
        def forbidden(*a,**k):raise AssertionError('No network/weights/old execution')
        for target in ('socket.create_connection','socket.socket.connect','exception_continuation.backend.LocalBackend.__init__',
            'exception_study2_source_report.execution.run','exception_study2_source_report_v2.execution.run',
            'exception_study2_source_user_pilot.execution.run','exception_study2_source_user_pilot.execution.PilotSession',
            'exception_study2_v5.readouts.measure','exception_study2_v5.runner.collect'):
            p=patch(target,forbidden);p.start();self.addCleanup(p.stop)
        self.parent_before=artifact_files(self.pilot)
        self.plan=planning.prepare(self.pilot,self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        self.backend=Backend(self.plan,self.tok);self.loads=0
    def factory(self,*a):self.loads+=1;return self.backend
    def run_fake(self):return execution.run(self.out,_backend_factory=self.factory)
    def test_exact_332_origins_664_joins_exclusions_and_no_origin_operation(self):
        self.assertEqual(self.plan['inventory'],INVENTORY);self.assertEqual(len(self.plan['queries']),332)
        self.assertEqual(self.plan['exclusions'],self.v2['exclusions']);self.assertEqual([x['task_id'] for x in self.plan['exclusions']],list(EXCLUDED))
        self.assertNotIn('calibration',self.plan);self.assertEqual(self.plan['new_pilot_generations'],0)
        for q,old in zip(self.plan['queries'],self.v2['main']):
            self.assertEqual(q['origin_query'],old);self.assertEqual(q['legacy'],old['legacy'])
            self.assertNotEqual(q['id'],old['id']);self.assertEqual(q['origin_query_hash'],old['query_hash'])
            self.assertNotIn('origin_operation_hash',execution.request(q,self.plan))
        self.assertEqual(artifact_files(self.pilot),self.parent_before)
        self.assertEqual((v1_contract(),v2_contract(),pilot_contract()),(V1_CONTRACT,V2_CONTRACT,PILOT_CONTRACT))
    def test_k0_equivalence_nonempty_prefixes_offsets_and_no_metadata_in_input(self):
        for q in self.plan['queries']:
            old=q['origin_query'];b=pilot_bridge(self.tok,q['original_user_prompt'],q['target_plate'],old['input_ids'])
            k=q['checkpoint'];self.assertEqual(q['context_ids'],old['input_ids']+old['prefix_ids']+b['bridge_ids'])
            self.assertEqual(q['old_context_ids'],old['input_ids']+old['prefix_ids']);self.assertEqual(q['bridge_hash'],b['bridge_hash'])
            self.assertEqual(q['empty_old_assistant_closed'],k==0);self.assertTrue(q['assistant_explicitly_closed'])
            self.assertEqual(self.tok.decode_all(q['context_ids']),self.tok.decode_all(old['input_ids']+old['prefix_ids'])+b['bridge_text'])
            self.assertNotIn(old['suffix'],self.tok.decode_all(q['context_ids']))
            self.assertNotIn('AUDIT METADATA',self.tok.decode_all(q['context_ids']))
            for a,z in zip(q['role_boundaries'],b['role_boundaries']):
                self.assertEqual(a['bridge_token_offset'],z['bridge_token_offset']);self.assertEqual(a['context_token_offset'],z['context_token_offset']+k)
            if k==0:
                for key,value in b.items():self.assertEqual(q[key],value)
    def test_all_correct_332_calls_one_load_then_zero_resume(self):
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(len(self.backend.calls),332)
        self.assertEqual(r['counts']['returned'],332);self.assertEqual(r['next_stage'],'STOP_REVIEW_MAIN')
        self.assertEqual(r['prior_evidence']['new_pilot_generations'],0)
        for k,n in (('0',112),('256',112),('512',108)):
            s=r['checkpoints'][k];self.assertEqual(s['accuracy']['numerator'],n);self.assertEqual(s['accuracy']['denominator'],n)
            self.assertTrue(s['accuracy_bootstrap']['degenerate_interval']);self.assertIn('not certainty',s['accuracy_bootstrap']['caveat'])
        self.assertEqual({k:v['eligible_pairs'] for k,v in r['paired'].items()},{'0->256':112,'0->512':108,'256->512':108})
        self.assertEqual(r['natural_final_answers']['trajectories'],112)
        r=execution.run(self.out,_backend_factory=lambda *a:self.fail('Completed must not load'))
        self.assertEqual(r['this_invocation']['new_generations'],0);self.assertEqual(r['this_invocation']['model_loads'],0)
        self.assertEqual(r['this_invocation']['reused_child_returns'],332);self.assertEqual(artifact_files(self.pilot),self.parent_before)
    def test_wrong_missing_invalid_truncated_malformed_all_terminal_332(self):
        self.backend.mode='mixed';r=self.run_fake();self.assertEqual(len(self.backend.calls),332)
        self.assertEqual(r['counts']['failed'],0);self.assertEqual(r['collection_status'],'COMPLETE')
        for s in r['checkpoints'].values():
            self.assertEqual(s['accuracy']['numerator'],0);self.assertEqual(s['accuracy']['denominator'],s['eligible'])
            self.assertEqual(set(s['categories']),{'wrong_label','MISSING','incomplete','invalid_format','metadata_malformed'})
        self.assertTrue(any(x['score']['answer']=='MISSING' and x['outcome']=='MISSING' for x in r['cases']))
        self.assertEqual(execution.run(self.out,_backend_factory=lambda *a:self.fail('Never retry outcomes'))['this_invocation']['model_loads'],0)
    def test_first_exception_one_failed_331_untouched_resume_skips(self):
        self.backend.fail=True;r=self.run_fake();first=self.plan['queries'][0]['id']
        self.assertEqual(self.backend.calls,[first]);self.assertEqual(r['counts']['failed'],1);self.assertEqual(r['counts']['never_started'],331)
        for q in self.plan['queries'][1:]:self.assertFalse((self.out/'operations-v5'/digest(q['id'])).exists())
        before=artifact_files(self.out/'operations-v5');self.backend.fail=False;self.backend.calls.clear();r=self.run_fake()
        self.assertEqual(self.backend.calls,[q['id'] for q in self.plan['queries'][1:]])
        for name,h in before.items():self.assertEqual(artifact_files(self.out/'operations-v5')[name],h)
        self.assertEqual(r['counts']['returned'],331);self.assertEqual(r['counts']['unavailable'],1)
        self.assertEqual(r['checkpoints']['0']['accuracy']['denominator'],111)
        self.assertEqual(r['paired']['0->256']['returned_pairs'],111)
        self.assertEqual(execution.run(self.out,_backend_factory=lambda *a:self.fail('Blocked'))['this_invocation']['model_loads'],0)
    def test_ambiguous_skipped_request_only_runs(self):
        binding=execution.identity(self.plan,'MOCK');freeze(self.out/'execution-content.json',binding)
        for q,started in zip(self.plan['queries'][:2],(True,False)):
            req=execution.request(q,self.plan);entry=dict(binding,id=q['id'],request=req,request_hash=digest(req),stage=execution.STAGE)
            d=self.out/'operations-v5'/digest(q['id']);freeze(d/'request.json',dict(entry,status='planned'))
            if started:freeze(d/'started.json',dict(entry,status='started'))
        r=self.run_fake();self.assertEqual(len(self.backend.calls),331);self.assertNotIn(self.plan['queries'][0]['id'],self.backend.calls)
        self.assertEqual(r['counts']['ambiguous'],1)
        self.assertEqual(r['cumulative_finished_invocation_calls'],331);self.assertFalse(r['cumulative_call_accounting_complete'])
    def test_durable_returns_survive_reporting_interruption(self):
        with patch.object(reporting,'save_report',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=execution.run(self.out,_backend_factory=lambda *a:self.fail('Durable raw must not repeat'))
        self.assertEqual(r['counts']['returned'],332);self.assertEqual(r['this_invocation']['new_generations'],0)
    def test_offline_modes_archive_and_parent_counter_refresh(self):
        with patch.object(execution,'load_backend',side_effect=AssertionError('No weight loads')):
            r=execution.run(self.out);self.assertEqual(r['counts']['never_started'],332)
            write_json(self.pilot/'report.json',{'this_invocation':{'new_generations':0,'model_loads':0},'refreshed':'derived only'})
            r=execution.inspect(self.out);self.assertEqual(r['prior_evidence']['pilot_cumulative_calls'],12)
            target=self.root/'main.tar.gz';execution.archive(self.out,target)
            with self.assertRaises(FileExistsError):execution.archive(self.out,target)
        with tarfile.open(target) as t:
            names=t.getnames();self.assertIn('main/pilot-evidence/parent-evidence/source-report-plan.json',names)
            self.assertIn('main/legacy-values.json',names);self.assertIn('main/contexts/331.txt',names)
            self.assertEqual(sum(n.endswith('/parent-evidence/source-report-plan.json') for n in names),1)
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_source_join_boundary_or_plan_tamper_blocks_before_load(self):
        e=self.e;first=self.v2['main'][0];key=first['legacy']['0']['computation_id'];old=copy.deepcopy(e.legacy[key])
        del e.legacy[key]
        with self.assertRaisesRegex(ValueError,'join unavailable'):self.run_fake()
        e.legacy[key]=old;e.legacy[key]['class_token']['abc_mass']+=.1
        with self.assertRaisesRegex(ValueError,'origins/664'):self.run_fake()
        e.legacy[key]=old;old['class_token']['abc_mass']-=.1
        row=e.remaining.rows[first['task_id']];boundary=copy.deepcopy(row['boundaries']);row['boundaries']=[x for x in row['boundaries'] if x['k']!=256]
        with self.assertRaisesRegex(ValueError,'population cannot shrink'):self.run_fake()
        row['boundaries']=boundary
        changed=copy.deepcopy(self.plan);changed['queries'][0]['context_ids'][0]+=1;sealed_write(self.out/'main-plan.json',changed)
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_pilot_counters_raw_or_real_tokenizer_record_tamper(self):
        r=execution.inspect(self.out);self.assertEqual(r['prior_evidence']['successful_development_pilot'],12)
        q=sealed_read(self.pilot/'pilot-plan.json')['queries'][0];path=self.pilot/'operations-v5'/digest(q['id'])/'returned.json';op=sealed_read(path)
        old_raw=copy.deepcopy(op['result']);op['result']=raw(self.tok,'MISSING')
        sealed_write(path,op)
        with self.assertRaisesRegex(ValueError,'12/12'):self.run_fake()
        op['result']=old_raw;sealed_write(path,op)
        prep=sealed_read(self.pilot/'preparation.json');prep['real_tokenizer_serialization_validated']=False;sealed_write(self.pilot/'preparation.json',prep)
        with self.assertRaisesRegex(ValueError,'real-tokenizer preparation'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_locks_cache_version_mock_live_backend_and_separation(self):
        with run_lock(self.out):
            with self.assertRaisesRegex(ValueError,'Another process'):self.run_fake()
        with self.assertRaisesRegex(ValueError,'SAME output'):planning.prepare(self.pilot,self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        with self.assertRaisesRegex(ValueError,'outside'):planning.prepare(self.pilot,self.root/'originals',self.root/'readouts',self.root/'tokens',self.pilot/'child')
        self.backend.identity['hardware']='other'
        with self.assertRaisesRegex(ValueError,'backend identity'):self.run_fake()
        self.assertEqual(self.backend.calls,[])
        binding=execution.identity(self.plan,'MOCK');freeze(self.out/'execution-content.json',binding)
        with self.assertRaisesRegex(ValueError,'MOCK/LIVE'):execution.run(self.out,True)
        opid='v5/source-user-pilot-v1/unplanned';freeze(self.out/'operations-v5'/digest(opid)/'request.json',dict(binding,id=opid,request={},request_hash=digest({}),stage=execution.STAGE,status='planned'))
        with self.assertRaisesRegex(ValueError,'Cross-version'):self.run_fake()
    def test_comparison_denominators_ties_shared_response_and_paired_transitions(self):
        from exception_study2_source_report.evidence import preference
        from exception_study2_source_report_v2.reporting import WorldBootstrap
        qs=copy.deepcopy(self.plan['queries'][:3]);qs[0]['legacy']['0']['class_token']=preference({'A':-1,'B':-1,'C':-2})
        wrong=next(x for x in 'ABC' if x!=qs[1]['expected']);qs[1]['pattern']=wrong
        qs[1]['legacy']['0']['class_token']=preference({x:-1 if x==wrong else -3 for x in 'ABC'})
        qs[2]['legacy']['0']['class_token']=qs[1]['legacy']['0']['class_token'];qs[2]['pattern']=wrong;qs[2]['expected']=qs[1]['expected']
        answers={q['id']:parse_reply(raw(self.tok,q['expected']),q['expected'],self.tok) for q in qs[:2]}
        b=WorldBootstrap([qs[0]['world']]);r=reporting.comparison(qs,answers,'0','class_token',b)
        self.assertEqual(r['exact_ties'],1)
        w=r['uniquely_wrong'];self.assertEqual(w['joint_among_all_returned'],reporting.fraction(1,2))
        self.assertEqual(w['conditional_among_preference_returned'],reporting.fraction(1,1));self.assertEqual(w['unavailable_relevant_cases'],1)
        self.assertEqual(w['eligible_preference_cases'],2);self.assertEqual(r['pattern_preference']['unavailable_relevant_cases'],1)
        answers[qs[1]['id']]=parse_reply(raw(self.tok,wrong),qs[1]['expected'],self.tok)
        paired=reporting.paired(qs,answers,b)
        self.assertEqual(paired['0->256']['transitions']['correct->incorrect'],1)
        self.assertEqual(paired['0->256']['paired_accuracy_change']['estimate'],-1)
        self.assertEqual(paired['0->512']['returned_pairs'],0)


PILOT_DIR=os.environ.get('STUDY2_SOURCE_USER_PILOT','/tmp/study2-source-user-main-input/study2-source-user-pilot-v1')
ORIGINALS=os.environ.get('STUDY2_SOURCE_REPORT_ORIGINALS','/tmp/study2-source-report-input/study2-v5-replication-v1/originals')
READOUTS=os.environ.get('STUDY2_SOURCE_REPORT_READOUTS','/tmp/study2-source-report-input/study2-v5-replication-v1/readouts-remaining-v1')
TOK=os.environ.get('QWEN3_TOKENIZER_DIR','/tmp/study2-qwen3-tokenizer')
@unittest.skipUnless((Path(PILOT_DIR)/'pilot-plan.json').is_file() and (Path(READOUTS)/'measurements-v5.json').is_file(),'Actual saved evidence unavailable')
class SavedEvidenceTests(unittest.TestCase):
    def test_actual_pilot_execution_332_inventory_664_raw_joins_and_preservation(self):
        from exception_study2_v5.runner import Source
        from exception_study2_v5_replication.readouts import validate_value
        root=Path(PILOT_DIR);before=artifact_files(root);p=sealed_read(root/'pilot-plan.json')
        self.assertEqual(p['artifact_hash'],PILOT_PLAN);self.assertEqual(p['code_contract'],PILOT_CONTRACT)
        c=SimpleNamespace(out=root,plan=p,queries={q['id']:q for q in p['queries']});ops,mode=pilot_execution.journal(c)
        self.assertEqual(mode,'LIVE_LOCAL');self.assertEqual(len(ops),12);self.assertTrue(all(o['status']=='returned' for o in ops.values()))
        finished=[sealed_read(x) for x in (root/'invocations').glob('*/finished.json')]
        self.assertEqual(sum(f['new_generations'] for f in finished),12);self.assertEqual(sum(f['model_loads'] for f in finished),1)
        self.assertEqual(json.loads((root/'report.json').read_text())['this_invocation']['new_generations'],0)
        origin=sealed_read(root/'parent-evidence/source-report-plan.json');src=Source(ORIGINALS,scope='remaining')
        self.assertEqual(src.binding,origin['source']['remaining'])
        values=evidence.raw_join_evidence(SimpleNamespace(origin=origin,provenance={'legacy_provenance_mode':'exported_summary'}),READOUTS)
        self.assertEqual(len(values),664);self.assertEqual(len(origin['main']),332)
        self.assertEqual({str(k):sum(q['checkpoint']==k for q in origin['main']) for k in (0,256,512)},INVENTORY['checkpoints'])
        for q in origin['main']:
            row=src.rows[q['task_id']];self.assertEqual(q['source_row_hash'],row['artifact_hash']);self.assertEqual(q['prefix_ids'],row['raw']['tokens'][:q['checkpoint']])
            self.assertEqual(q['input_ids'],row['input_ids']);self.assertEqual(digest({k:v for k,v in q.items() if k not in ('id','query_hash')}),q['query_hash'])
            for join in q['legacy'].values():
                value=values[join['computation_id']]['value'];validate_value(value,row,dict(cue_text=join['cue_text'],k=q['checkpoint']))
        self.assertEqual(artifact_files(root),before)
        self.assertEqual((v1_contract(),v2_contract(),pilot_contract()),(V1_CONTRACT,V2_CONTRACT,PILOT_CONTRACT))
        # No real token decoding/bridge validation is claimed by this artifact test.


@unittest.skipUnless((Path(TOK)/'tokenizer.json').is_file() and (Path(PILOT_DIR)/'pilot-plan.json').is_file(),'Actual pinned tokenizer unavailable; all 332 constructions REQUIRED by production prepare')
class RealTokenizerTests(unittest.TestCase):
    def test_actual_pilot_reparse_and_all_332_real_tokenizer_contexts(self):
        from exception_study2_source_report.tokenizer import Tokenizer
        def forbidden(*a,**k):raise AssertionError('No inference/downloads')
        with patch('socket.create_connection',forbidden),patch('socket.socket.connect',forbidden),patch('exception_continuation.backend.LocalBackend.__init__',forbidden):
            tok=Tokenizer(TOK);e=evidence.Evidence(PILOT_DIR,ORIGINALS,READOUTS,tok)
            p=planning.make_plan(e,evidence.raw_join_evidence(e,READOUTS))
        self.assertEqual(p['inventory'],INVENTORY);self.assertEqual(e.pilot_binding['correct'],12)
        for q in p['queries']:
            self.assertEqual(q['context_ids'],q['original_input_ids']+q['prefix_ids']+q['bridge_ids'])
            self.assertEqual(q['empty_old_assistant_closed'],q['checkpoint']==0)

if __name__=='__main__':unittest.main()
