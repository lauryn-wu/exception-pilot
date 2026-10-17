"""Bounded offline tests: synthetic counting backend and optional supplied archive."""
import copy
import json
import math
import os
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read,sealed_write
from exception_review.artifacts import freeze
from exception_study2_source_report import planning,execution,reporting,evidence,parser
from exception_study2_source_report import INVENTORY,CANDIDATES,BUDGET
from source_report_fixtures import Tokens,fixture,CountingBackend


class SourceReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixture();cls.plan=planning.make_plan(cls.fixture)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.out=self.root/'extension'
        def forbidden(*a,**kw):raise AssertionError('Network/model loading forbidden in offline tests')
        for target in ('socket.create_connection','socket.socket.connect','exception_continuation.backend.LocalBackend.__init__'):
            p=patch(target,side_effect=forbidden);p.start();self.addCleanup(p.stop)
        for target in ('exception_study2_v5.runner.collect','exception_study2_v5.runner.technical','exception_study2_v5.core.prepare','exception_study2_v5.readouts.prepare_measurements','exception_study2_v5.readouts.measure'):
            p=patch(target,side_effect=forbidden);p.start();self.addCleanup(p.stop)
        p=patch.object(planning,'Tokenizer',Tokens);p.start();self.addCleanup(p.stop)
        p=patch.object(planning,'Evidence',return_value=self.fixture);p.start();self.addCleanup(p.stop)
        for name in ('originals','readouts','tokens'):
            (self.root/name).mkdir();(self.root/name/'preserved.txt').write_text('Synthetic immutable historical fixture')
        self.plan=planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        self.backend=CountingBackend(self.plan,Tokens());self.loads=0
    def factory(self,*a):self.loads+=1;return self.backend
    def run_fake(self,**kw):return execution.run(self.out,_backend_factory=self.factory,**kw)
    def test_exact_main_inventory_and_exclusion_ledger(self):
        self.assertEqual(self.plan['inventory'],INVENTORY);self.assertEqual(len(self.plan['main']),332)
        self.assertEqual({q['checkpoint'] for q in self.plan['main']},{0,256,512})
        self.assertTrue(all(q['task_id'].endswith('/original/visible') and int(q['world'][-3:])>=4 for q in self.plan['main']))
        self.assertEqual(len(self.plan['exclusions']),4);self.assertTrue(all(q['checkpoint']==512 for q in self.plan['exclusions']))
    def test_exact_saved_prefix_and_independent_suffix_without_full_reencode(self):
        tok=Tokens()
        for q in self.plan['main']:
            row=self.fixture.remaining.rows[q['task_id']]
            self.assertEqual(q['input_ids'],row['input_ids']);self.assertEqual(q['prefix_ids'],row['raw']['tokens'][:q['checkpoint']])
            self.assertEqual(q['context_ids'],q['input_ids']+q['prefix_ids']+q['suffix_ids'])
            self.assertTrue(q['suffix'].startswith('\n\nWhat value'));self.assertFalse(q['suffix'].endswith('\n'))
            self.assertEqual(tok.decode_all(q['suffix_ids']),q['suffix'])
        # This tokenizer's separately rendered assistant boundary is intentionally
        # noncanonical when the entire decoded string is re-encoded.
        q=self.plan['main'][0];self.assertNotEqual(tok.encode(tok.decode_all(q['context_ids'])),q['context_ids'])
    def test_calibration_eight_present_four_deduplicated_missing_no_prefix(self):
        qs=self.plan['calibration'];self.assertEqual(len(qs),12)
        self.assertEqual({q['expected'] for q in qs},{'A','B','C','MISSING'})
        missing=[q for q in qs if q['kind']=='calibration_missing'];self.assertEqual(len(missing),4)
        for q in qs:self.assertEqual(q['prefix_ids'],[]);self.assertEqual(q['checkpoint'],0)
        for q in missing:
            self.assertEqual(len(q['parent_rows']),2);self.assertTrue(q['cell_edit']['variants_byte_identical'])
            for edit in q['cell_edit']['variant_edits']:
                old=self.fixture.pilot.rows[edit['source_task_id']]['task']['prompt'];a,b=edit['old_span']
                self.assertEqual(q['cell_edit']['prompt'],old[:a]+'MISSING'+old[b:])
    def test_default_run_inspect_analyze_zero_model_loads(self):
        with patch.object(execution,'load_backend',side_effect=AssertionError('No model')):
            for fn in (execution.inspect,execution.analyze,execution.run):
                r=fn(self.out);self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_generations'],0)
        self.assertEqual(r['executable_now'],12);self.assertEqual(r['main_conditional_on_calibration'],332)
    def test_full_fresh_and_second_cached_invocation_zero_loads(self):
        r=self.run_fake();self.assertEqual(self.loads,1);self.assertEqual(len(self.backend.calls),344)
        self.assertEqual(r['calibration_gate']['status'],'PASSED');self.assertEqual(r['counts']['main']['returned'],332)
        with patch.object(execution,'load_backend',side_effect=AssertionError('Cache must avoid loader')):
            r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('No construction')))
        self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_generations'],0)
        self.assertEqual(r['this_invocation']['reused_returns'],344)
        for name in ('originals','readouts','tokens'):
            self.assertEqual((self.root/name/'preserved.txt').read_text(),'Synthetic immutable historical fixture')
    def test_cached_calibration_and_request_only_entry_execute_main_once(self):
        self.run_fake(calibration_only=True);self.assertEqual(len(self.backend.calls),12)
        q=self.plan['main'][0];req=execution.request(q,self.plan);identity=execution.content_identity(self.plan,'MOCK')
        freeze(self.out/'operations-v5'/digest(q['id'])/'request.json',dict(identity,id=q['id'],request=req,request_hash=digest(req),stage='source_report_generation',status='planned'))
        self.backend.calls.clear();r=self.run_fake()
        self.assertEqual(len(self.backend.calls),332);self.assertEqual(len(set(self.backend.calls)),332)
        self.assertEqual(r['this_invocation']['new_generations'],332)
    def test_failed_calibration_blocks_main_and_next_load(self):
        self.backend.bad_id=self.plan['calibration'][0]['id'];r=self.run_fake()
        self.assertEqual(len(self.backend.calls),12);self.assertEqual(r['calibration_gate']['status'],'FAILED')
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Terminal calibration must stay offline')))
        self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['counts']['main']['never_started'],332)
    def test_failed_and_ambiguous_main_never_resend(self):
        q=self.plan['main'][2];self.backend.interrupt_id=q['id']
        with self.assertRaises(KeyboardInterrupt):self.run_fake()
        folder=self.out/'operations-v5'/digest(q['id']);self.assertTrue((folder/'failed.json').exists())
        (folder/'failed.json').unlink()  # Explicit synthetic ambiguous-state fixture.
        self.backend.calls.clear();self.backend.interrupt_id=None;r=self.run_fake()
        self.assertNotIn(q['id'],self.backend.calls);self.assertEqual(len(self.backend.calls),329)
        self.assertEqual(r['counts']['main']['ambiguous'],1)
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Only ambiguous work remains')))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_persistent_main_backend_failure_stops_once_and_resume_skips_it(self):
        generate=self.backend.generate
        def persistent_failure(ids,budget,capture_at=()):
            q=self.backend.queries[digest(ids)]
            if q['kind']=='main':
                self.backend.calls.append(q['id'])
                raise RuntimeError('Synthetic persistent backend failure')
            return generate(ids,budget,capture_at=capture_at)
        self.backend.generate=persistent_failure
        r=self.run_fake();failed_id=self.plan['main'][0]['id']
        self.assertEqual(r['calibration_gate']['status'],'PASSED')
        self.assertEqual(r['counts']['calibration']['returned'],12)
        main_ids=[q['id'] for q in self.plan['main']]
        self.assertEqual([i for i in self.backend.calls if i in main_ids],[failed_id])
        self.assertEqual(r['this_invocation']['new_generations'],13)
        self.assertEqual(r['counts']['main'],dict(planned=332,returned=0,never_started=331,failed=1,ambiguous=0))
        self.assertEqual(r['this_invocation']['stopped_after_exception'],dict(operation_id=failed_id,error_type='RuntimeError'))
        folder=self.out/'operations-v5'/digest(failed_id)
        failure=sealed_read(folder/'failed.json')
        self.assertEqual(failure['error_type'],'RuntimeError');self.assertFalse((folder/'returned.json').exists())
        self.assertTrue(all(not (self.out/'operations-v5'/digest(i)).exists() for i in main_ids[1:]))
        finished=list((self.out/'invocations').glob('*/finished.json'))
        self.assertEqual(len(finished),1);self.assertEqual(sealed_read(finished[0])['status'],'STOPPED')
        # Every already written operation/provenance record must survive resume byte-for-byte.
        before={p:p.read_bytes() for name in ('operations-v5','operation-execution') for p in (self.out/name).rglob('*.json')}
        self.backend.generate=generate;self.backend.calls.clear();r=self.run_fake()
        self.assertEqual(self.backend.calls,main_ids[1:]);self.assertEqual(r['this_invocation']['new_generations'],331)
        self.assertEqual(r['this_invocation']['reused_returns'],12)
        self.assertEqual(r['counts']['main'],dict(planned=332,returned=331,never_started=0,failed=1,ambiguous=0))
        self.assertNotIn('stopped_after_exception',r['this_invocation'])
        for path,value in before.items():self.assertEqual(path.read_bytes(),value)
        with patch.object(execution,'load_backend',side_effect=AssertionError('Only terminal work remains')):
            r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('No model construction')))
        self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_generations'],0)
    def test_new_calibration_backend_exception_leaves_later_work_unstarted(self):
        def persistent_failure(ids,budget,capture_at=()):
            self.backend.calls.append(self.backend.queries[digest(ids)]['id'])
            raise RuntimeError('Synthetic persistent calibration backend failure')
        self.backend.generate=persistent_failure;r=self.run_fake()
        self.assertEqual(len(self.backend.calls),1);self.assertEqual(r['this_invocation']['new_generations'],1)
        self.assertEqual(r['calibration_gate']['status'],'FAILED')
        self.assertEqual(r['counts']['calibration']['failed'],1);self.assertEqual(r['counts']['calibration']['never_started'],11)
        self.assertEqual(r['counts']['main']['never_started'],332)
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Failed calibration stays blocked')))
        self.assertEqual(r['this_invocation']['model_loads'],0)
    def test_failed_calibration_operation_stays_unavailable(self):
        self.backend.interrupt_id=self.plan['calibration'][0]['id']
        with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('No retry')))
        self.assertEqual(r['counts']['calibration']['failed'],1);self.assertEqual(r['calibration_gate']['status'],'FAILED')
    def test_crash_after_durable_raw_returns_before_report_recovers_offline(self):
        with patch.object(reporting,'save_report',side_effect=KeyboardInterrupt('Synthetic post-return report interruption')):
            with self.assertRaises(KeyboardInterrupt):self.run_fake()
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Raw returns must be reused')))
        self.assertEqual(r['counts']['all']['returned'],344);self.assertEqual(r['this_invocation']['new_generations'],0)
    def test_wrong_verbose_truncated_main_returns_stay_cached_without_stopping(self):
        qs=self.plan['main'][:3];generate=self.backend.generate
        wrong='B' if qs[0]['expected']=='A' else 'A'
        replies={qs[0]['id']:(wrong,True),qs[1]['id']:('class is A',True),qs[2]['id']:('r'*16,False)}
        def returned_but_incorrect(ids,budget,capture_at=()):
            raw=generate(ids,budget,capture_at=capture_at);op_id=self.backend.calls[-1]
            if op_id in replies:
                text,eos=replies[op_id]
                raw.update(text=text,tokens=self.backend.tok.encode(text)+([0] if eos else []),stopped=eos,finish='eos' if eos else 'length')
            return raw
        self.backend.generate=returned_but_incorrect;r=self.run_fake()
        self.assertEqual(len(self.backend.calls),344);self.assertEqual(r['counts']['main']['returned'],332)
        self.assertEqual(r['counts']['main']['failed'],0);self.assertNotIn('stopped_after_exception',r['this_invocation'])
        rows={q['operation_id']:q for q in r['main_contexts']}
        for q,category in zip(qs,(wrong,'verbose','truncated')):
            a=rows[q['id']]['source_report'];self.assertEqual(a['category'],category);self.assertFalse(a['correct'])
            s=r['main_checkpoint_summaries'][str(q['checkpoint'])]['0']
            self.assertEqual(s['returned'],s['eligible']);self.assertLess(s['source_accuracy']['estimate'],1)
        before={p:p.read_bytes() for p in (self.out/'operations-v5').rglob('*.json')}
        r=execution.run(self.out,_backend_factory=lambda *a:(_ for _ in ()).throw(AssertionError('Bad returns never retry')))
        self.assertEqual(r['this_invocation']['model_loads'],0);self.assertEqual(r['this_invocation']['new_generations'],0)
        for p,value in before.items():self.assertEqual(p.read_bytes(),value)
    def test_mismatched_backend_stops_before_generation(self):
        self.backend.identity['hardware']='wrong GPU'
        with self.assertRaisesRegex(ValueError,'backend differs'):self.run_fake()
        self.assertEqual(self.backend.calls,[])
    def test_source_context_query_model_and_contract_tampering_stop_offline(self):
        original=copy.deepcopy(self.plan)
        for field in ('context','source','query','model','contract'):
            p=copy.deepcopy(original)
            if field=='context':p['main'][0]['context_ids'][0]+=1
            elif field=='source':p['source']['historical_revision']='wrong'
            elif field=='query':p['suffix_template']='different interface'
            elif field=='model':p['backend']['hardware']='different'
            else:p['code_contract']='different'
            sealed_write(self.out/'source-report-plan.json',p)
            with self.assertRaises(ValueError):self.run_fake()
        sealed_write(self.out/'source-report-plan.json',original);self.assertEqual(self.loads,0)
    def test_same_output_lock_prevents_duplicate_calls(self):
        with run_lock(self.out):
            with self.assertRaisesRegex(ValueError,'Another process'):self.run_fake()
        self.assertEqual(self.loads,0)
    def test_content_compatible_revision_changes_reuse_cache_truthfully(self):
        self.run_fake(calibration_only=True)
        before={p.name:p.read_bytes() for p in (self.out/'operation-execution').glob('*.json')}
        with patch.object(execution,'revision',return_value='later-ordinary-repository-revision'):
            r=self.run_fake()
        self.assertEqual(r['this_invocation']['extension_revision'],'later-ordinary-repository-revision')
        self.assertTrue(all((self.out/'operation-execution'/name).read_bytes()==value for name,value in before.items()))
    def test_inventory_change_has_explicit_diagnostic(self):
        changed=copy.deepcopy(self.fixture);changed.remaining.tasks=changed.remaining.tasks[:-1]
        with self.assertRaisesRegex(ValueError,'inventory mismatch'):planning.make_plan(changed)
    def test_prepare_refuses_replacement_or_overlapping_source(self):
        with self.assertRaisesRegex(ValueError,'SAME output'):planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.out)
        with self.assertRaisesRegex(ValueError,'outside'):planning.prepare(self.root/'originals',self.root/'readouts',self.root/'tokens',self.root/'originals/new')
    def test_paired_denominators_preserve_108_case_cohort_and_unavailable(self):
        r=self.run_fake();self.assertEqual(r['paired_changes']['0->256']['eligible_trajectories'],112)
        self.assertEqual(r['paired_changes']['0->512']['eligible_trajectories'],108)
        self.assertEqual(r['paired_changes']['0->512']['returned_pairs'],108)
        self.assertEqual(r['paired_changes']['0->512']['source_accuracy_change']['estimate'],0)
        self.assertEqual(r['main_checkpoint_summaries']['0']['0']['source_accuracy']['planned_worlds'],56)

    def test_only_four_modified_prompts_are_rendered(self):
        tok=self.fixture.tokenizer
        with patch.object(tok,'prompt',wraps=tok.prompt) as render:
            plan=planning.make_plan(self.fixture)
        self.assertEqual(render.call_count,4)
        self.assertEqual([a.args[0] for a in render.call_args_list],
                         [q['cell_edit']['prompt'] for q in plan['calibration'] if q['kind']=='calibration_missing'])
    def test_source_and_journal_indexes_built_once_per_invocation(self):
        with patch.object(planning,'Evidence',return_value=self.fixture) as source, patch.object(execution,'operation_tree',wraps=execution.operation_tree) as index:
            r=self.run_fake()
        self.assertEqual(source.call_count,1);self.assertEqual(index.call_count,1)
        self.assertEqual(r['this_invocation']['new_generations'],344)
    def test_eos_terminated_wrong_calibration_label_blocks_main(self):
        generate=self.backend.generate;first=self.plan['calibration'][0]['id']
        def wrong(*a,**kw):
            result=generate(*a,**kw)
            if self.backend.calls[-1]==first:
                label='B' if self.plan['calibration'][0]['expected']=='A' else 'A'
                result.update(text=label,tokens=self.backend.tok.encode(label)+[0])
            return result
        self.backend.generate=wrong;r=self.run_fake()
        self.assertEqual(r['calibration_gate']['status'],'FAILED');self.assertEqual(len(self.backend.calls),12)
        self.assertTrue(r['calibration'][0]['source_report']['valid'])
        self.assertFalse(r['calibration'][0]['source_report']['correct'])
    def test_human_report_and_unfinished_load_accounting(self):
        # A synthetic killed invocation cannot support a claim of exact lifetime loads.
        freeze(self.out/'invocations/synthetic-unfinished/started.json',dict(model_load_intended=True))
        r=execution.analyze(self.out)
        self.assertFalse(r['cumulative_backend_loads_complete']);self.assertEqual(r['timing']['unfinished_invocations'],1)
        text=reporting.human(r)
        for label in ('Calibration (pilot worlds only)','Joint outcomes','Paired changes','Saved natural final answers','source-correct/wrong-preference','fixed/512','Source hashes','ABC mass','Unavailable measurements'):
            self.assertIn(label,text)
        self.assertEqual(r['natural_final_answers']['trajectories'],112)
        self.assertFalse(r['backend_requirements']['model_weight_bytes_checked'])


class ParserAndAnalysisTests(unittest.TestCase):
    def raw(self,text,eos=True):
        tok=Tokens();return dict(text=text,tokens=tok.encode(text)+([0] if eos else []),stopped=eos,finish='eos' if eos else 'length',next_token_logits={})
    def test_whole_response_parser_all_labels_and_whitespace(self):
        for label in ('A','B','C','MISSING'):
            r=parser.parse_reply(self.raw('\n '+label+' \n'),label,Tokens());self.assertTrue(r['correct']);self.assertEqual(r['answer'],label)
    def test_invalid_verbose_empty_ambiguous_and_truncated(self):
        for text,kind in [('The class is A.','verbose'),('','empty'),('A / B','ambiguous')]:
            r=parser.parse_reply(self.raw(text),'A',Tokens());self.assertFalse(r['valid']);self.assertEqual(r['category'],kind)
        r=parser.parse_reply(self.raw('A',False),'A',Tokens());self.assertEqual(r['diagnostic_label'],'A');self.assertFalse(r['correct']);self.assertEqual(r['category'],'truncated')
        r=parser.parse_reply(None,'A',Tokens());self.assertEqual(r['category'],'malformed')
    def test_eos_text_and_metadata_must_agree(self):
        raw=self.raw('A');raw['text']='B'
        self.assertFalse(parser.parse_reply(raw,'B',Tokens())['valid'])
        raw=self.raw('A');raw['stopped']=False
        self.assertFalse(parser.parse_reply(raw,'A',Tokens())['valid'])
    def test_exact_ties_not_wrong_preferences_and_abc_mass(self):
        p=evidence.preference({'A':-1.,'B':-1.,'C':-3.})
        self.assertIsNone(p['preferred_class']);self.assertEqual(p['tied_classes'],['A','B'])
        self.assertAlmostEqual(p['abc_mass'],2*math.exp(-1)+math.exp(-3))
    def test_world_bootstrap_uses_blocks_and_repeatable_common_draws(self):
        a=reporting.WorldBootstrap(['w1','w2']);b=reporting.WorldBootstrap(['w1','w2'])
        self.assertEqual(a.draws,b.draws)
        r=a.estimate([('w1',1),('w1',1),('w2',0),('w2',0)])
        self.assertEqual(r['estimate'],.5);self.assertEqual(r['unit'],'world')
    def test_missing_source_is_unavailable_but_literal_missing_is_answer(self):
        p=planning.make_plan(fixture());qs=p['main'][:2];answers={qs[0]['id']:parser.parse_reply(self.raw('MISSING'),qs[0]['expected'],Tokens())}
        s=reporting.summary(qs,answers,'0',reporting.WorldBootstrap(sorted({q['world'] for q in qs})))
        self.assertEqual(s['returned'],1);self.assertEqual(s['unavailable'],1);self.assertEqual(s['source_accuracy']['estimate'],0)
        self.assertEqual(s['source_return_categories']['MISSING'],1)
