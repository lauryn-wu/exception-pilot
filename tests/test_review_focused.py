"""Focused audit regressions: no network, no pretrained models, no paid calls."""
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_automated_review import Base, FakeClock, Transport, config, verification, detection
from exception_continuation import runner
from exception_continuation.backend import MockBackend
from exception_pilot.core import digest
from exception_review import artifacts, integration, policy, reporting, semantic_eval, workflow
from exception_review.__main__ import main
from exception_review.coverage import intervention_coverage
from exception_review.fixtures import edit_fixtures
from exception_review.journal import Journal
from exception_review.qwen_timing import measure_fixed


class SemanticSchedulingTests(Base):
    def test_actual_cli_wall_boundary_and_cache_resume(self):
        cfg=self.root/'policy.json'; cfg.write_text(json.dumps(config()))
        clock=FakeClock(); transport=Transport(clock=clock); calls=[]
        def real_journal(*a,**kw):
            calls.append(kw['wall_seconds']); return Journal(*a,**dict(kw,transport=transport,clock=clock))
        args=['semantic-eval','--output',str(self.out),'--policy',str(cfg),'--wall-seconds','4']
        with patch('exception_review.semantic_eval.Journal',side_effect=real_journal),patch('sys.stdout',new_callable=io.StringIO):
            main(args)
            self.assertEqual(len(transport.calls),2)
            saved={str(p):p.read_bytes() for p in (self.out/'judge-operations').glob('*/returned.json')}
            main(args+['--max-calls','0'])
        self.assertEqual(calls,[4,4]); self.assertEqual(len(transport.calls),2)
        report=json.loads((self.out/'semantic-evaluation-report.json').read_text())
        self.assertEqual(report['returned'],2); self.assertEqual(report['status'],'INCOMPLETE')
        self.assertEqual(report['timing']['this_invocation']['cached'],2)
        for p,b in saved.items(): self.assertEqual(Path(p).read_bytes(),b)
        result=semantic_eval.evaluate(self.out,config(),transport=transport,clock=clock)
        self.assertEqual(result['returned'],48); self.assertEqual(len(transport.calls),48)
    def test_wall_request_and_spend_budgets_are_independent(self):
        for mode in ('wall','requests','spend'):
            clock=FakeClock(); tr=Transport(clock=clock); cfg=config()
            if mode=='spend': cfg['limits']['max_estimated_usd']=.0000001
            value=semantic_eval.evaluate(self.root/mode,cfg,transport=tr,clock=clock,
                                        wall_seconds=1 if mode=='wall' else 1000,max_calls=1 if mode=='requests' else 100)
            self.assertEqual(len(tr.calls),0 if mode=='spend' else 1)
            self.assertEqual(value['timing']['this_invocation']['stop_reason'],dict(wall='WALL_SCHEDULING_LIMIT',requests='REQUEST_BUDGET',spend='ESTIMATED_SPEND_BUDGET')[mode])
        # The first in-flight response may finish after the scheduling boundary.
        self.assertEqual(value['status'],'INCOMPLETE')
    def test_cli_rejects_invalid_wall_limits_before_requests(self):
        cfg=self.root/'policy.json'; cfg.write_text(json.dumps(config()))
        for limit in ('0','-1','nan','inf'):
            result=subprocess.run([sys.executable,'-m','exception_review','semantic-eval','--output',str(self.root/limit),'--policy',str(cfg),'--wall-seconds',limit],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertIn('Finite positive wall limit',result.stderr)
            self.assertFalse(list((self.root/limit).glob('judge-operations/*/started.json')))
    def test_semantic_interruption_report_and_no_resend(self):
        class Interrupted:
            kind='MOCK'
            def __call__(self,*args): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): semantic_eval.evaluate(self.out,config(),transport=Interrupted())
        report=json.loads((self.out/'semantic-evaluation-report.json').read_text())
        self.assertEqual(report['terminal'],1); self.assertEqual(report['returned'],0)
        tr=Transport(); result=semantic_eval.evaluate(self.out,config(),transport=tr,max_calls=0)
        self.assertEqual(len(tr.calls),0); self.assertEqual(result['terminal'],1)


class EditSemanticTests(Base):
    def test_complete_fixtures_and_independent_criterion_labels(self):
        fixtures=edit_fixtures(); self.assertEqual(len(fixtures),10)
        required={'original_prompt','queried_vehicle_id','target_row','target_value','accepted_statement','original_prefix','proposed_bundle','edit_span','proposed_prefixes'}
        for f in fixtures:
            view=f['input']; self.assertEqual(set(view),required)
            policy.schema_check(view['proposed_bundle'],policy.DRAFT_SCHEMA)
            self.assertEqual(set(view['proposed_prefixes']),set(policy.ARMS)|{'unchanged'})
            a,b=view['edit_span']; self.assertEqual(view['original_prefix'][a:b],view['proposed_bundle']['edit_quote'])
            if f['id']!='edit-outside_span_corruption':
                for arm in policy.ARMS:
                    self.assertEqual(view['proposed_prefixes'][arm],view['original_prefix'][:a]+view['proposed_bundle']['replacements'][arm]+view['original_prefix'][b:])
            self.assertNotIn('expected',json.dumps(view)); self.assertIn('before judge',f['label_origin'])
        self.assertEqual(sum(f['expected_approval'] for f in fixtures),2)
        for name,arm,criterion in [('wrong_explicit_value','value_repair','semantic_role'),('wrong_column','availability_repair','entity_column'),('grammar_corruption','availability_repair','grammar'),('reference_corruption','availability_repair','grammar')]:
            f=next(x for x in fixtures if x['id']=='edit-'+name)
            self.assertEqual(f['expected_criteria'][arm][criterion],'fail')
    def test_all_pass_judges_report_false_approvals_not_consensus_quality(self):
        tr=Transport(clock=FakeClock()); result=semantic_eval.evaluate(self.out,config(),transport=tr,clock=tr.clock,stage='edits')
        self.assertEqual(result['expected'],30); self.assertEqual(result['correct'],6)
        self.assertEqual(result['status'],'COMPLETE'); self.assertEqual(len(tr.calls),30)
        for call in tr.calls:
            self.assertEqual(call['kind'],'verify')
            schema=call['request'].get('text',{}).get('format',{}).get('schema') or call['request']['output_config']['format']['schema']
            self.assertEqual(schema,policy.VERIFY_SCHEMA)
            self.assertIn(policy.RUBRICS['verify'],call['request'].get('instructions',call['request'].get('system')))
        for model in result['per_model'].values():
            self.assertEqual(model['bundle_counts']['false_approvals'],8)
            self.assertEqual(model['criteria']['value_repair']['semantic_role']['false_approvals'],1)
            self.assertEqual(model['criteria']['availability_repair']['grammar']['false_approvals'],2)
            for arm in policy.ARMS:
                for c in policy.CRITERIA: self.assertEqual(model['criteria'][arm][c]['planned'],10)
        self.assertEqual(result['timing']['cumulative']['input_tokens'],3000)
        self.assertEqual(result['timing']['cumulative']['output_tokens'],750)
        self.assertEqual(result['timing']['this_invocation']['provider_seconds'],60)
        self.assertTrue(result['timing_separate_from_natural_trajectories'])
    def test_uncertain_malformed_refused_and_partial_coverage(self):
        def cb(call):
            model=call['request']['model']
            if model=='fixture-J1':
                v=verification(); v['replacements']['availability_repair']['grammar']['status']='uncertain'; return v
            if model=='fixture-J2': return {}
            return {'HTTP_RESPONSE':dict(status=200,body=json.dumps(dict(status='completed',model=model,output=[dict(type='message',content=[dict(type='refusal',refusal='fixture refusal')])])))}
        result=semantic_eval.evaluate(self.out,config(),stage='edits',transport=Transport(cb),max_calls=3)
        self.assertEqual(result['status'],'INCOMPLETE'); self.assertEqual(result['returned'],3)
        for judge,key in [('J1','uncertain'),('J2','malformed'),('J3','refused')]:
            self.assertEqual(result['per_model'][judge]['criteria']['availability_repair']['grammar'][key],1)
            self.assertEqual(result['per_model'][judge]['criteria']['availability_repair']['grammar']['pending'],9)
        self.assertEqual(result['per_model']['J1']['bundle_counts']['false_rejections'],0)
    def test_oracle_and_false_rejection_labels_are_independent(self):
        examples={digest(f['input']):f for f in edit_fixtures()}
        def cb(call):
            f=examples[digest(call['view'])]; value=verification()
            for a in policy.ARMS:
                for c in policy.CRITERIA: value['replacements'][a][c]['status']=f['expected_criteria'][a][c]
            return value
        result=semantic_eval.evaluate(self.out,config(),stage='edits',transport=Transport(cb))
        self.assertEqual(result['correct'],30)
        wrong=self.root/'wrong'; value=semantic_eval.evaluate(wrong,config(),stage='edits',transport=Transport(lambda c:verification(fail=True)),max_calls=3)
        for model in value['per_model'].values(): self.assertEqual(model['bundle_counts']['false_rejections'],1)
    def test_actual_edit_cli_opt_in_and_separate_frozen_stage(self):
        cfg=self.root/'policy.json'; cfg.write_text(json.dumps(config())); tr=Transport()
        def real_journal(*a,**kw): return Journal(*a,**dict(kw,transport=tr))
        with patch('exception_review.semantic_eval.Journal',side_effect=real_journal),patch('sys.stdout',new_callable=io.StringIO):
            main(['semantic-eval','--stage','edits','--output',str(self.out),'--policy',str(cfg),'--max-calls','1'])
        self.assertEqual(len(tr.calls),1); self.assertEqual(tr.calls[0]['kind'],'verify')
        with self.assertRaisesRegex(ValueError,'Immutable'): semantic_eval.evaluate(self.out,config())
        offline=semantic_eval.evaluate(self.root/'offline',config(),stage='edits')
        self.assertEqual(offline['returned'],0)


class CountingBackend(MockBackend):
    def __init__(self): self.calls=[]
    def generate(self,ids,budget,capture_at=()):
        self.calls.append(('generate',ids,budget,list(capture_at)))
        return super().generate(ids,budget,capture_at)
    def score(self,context,candidate):
        self.calls.append(('score',context,candidate))
        return super().score(context,candidate)


class FixedTimingTests(Base):
    def test_equal_legacy_artifacts_counts_and_calls_cache_reuse(self):
        legacy=self.root/'legacy'; timed=self.root/'timed'
        shutil.copytree(self.source,legacy); shutil.copytree(self.source,timed)
        a=CountingBackend(); b=CountingBackend()
        runner.measure(legacy,backend_override=a); measure_fixed(timed,backend_override=b,clock=FakeClock())
        self.assertEqual(a.calls,b.calls)
        for name in ('collection.json','calibration.json','validation.json','execution.json','measurements.json'):
            self.assertEqual((legacy/name).read_bytes(),(timed/name).read_bytes())
        for file in (legacy/'operations').glob('*.json'):
            self.assertEqual(file.read_bytes(),(timed/'operations'/file.name).read_bytes())
        report=reporting.fixed_timing_report(timed)
        self.assertEqual(report['actual_timed_calls']['unchanged_replay']['returned'],96)
        self.assertEqual(report['actual_timed_calls']['candidate_sequence_scoring']['returned'],432)
        n=len(b.calls); measure_fixed(timed,backend_override=b)
        self.assertEqual(len(b.calls),n)
        report=reporting.qwen_timing_report(timed)
        self.assertEqual(report['fixed_2a']['cache_hits'],240)
        self.assertEqual(report['remaining_work']['candidate_sequence_scoring_fixed_2a']['remaining_count_scenario'],[0,0])
        self.assertEqual(report['remaining_work']['unchanged_replay']['remaining_count_scenario'],[0,0])
        self.assertIsNone(report['remaining_work']['unchanged_replay']['seconds_scenario'])
        self.assertTrue(report['fixed_2a']['this_invocation']['source_hash'])
        self.assertEqual(report['fixed_2a']['hardware_software_precision'][0],MockBackend.identity)
    def test_completed_untimed_legacy_is_not_wholly_remaining(self):
        out=self.root/'legacy'; shutil.copytree(self.source,out); runner.measure(out,backend_override=MockBackend())
        report=reporting.qwen_timing_report(out)
        self.assertEqual(report['remaining_work']['candidate_sequence_scoring_fixed_2a']['remaining_count_scenario'],[0,0])
        self.assertEqual(report['fixed_2a']['observations'],{})
        b=CountingBackend(); measure_fixed(out,backend_override=b)
        self.assertEqual(b.calls,[]); self.assertEqual(reporting.fixed_timing_report(out)['cache_hits'],240)
    def test_scoring_failure_partial_actuals_and_no_resend(self):
        out=self.root/'fail'; shutil.copytree(self.source,out)
        class Fail(CountingBackend):
            scores=0
            def score(self,*a):
                self.scores+=1
                if self.scores==2: raise RuntimeError('fixture score failure')
                return super().score(*a)
        b=Fail()
        with self.assertRaisesRegex(RuntimeError,'fixture score'): measure_fixed(out,backend_override=b)
        report=reporting.fixed_timing_report(out)
        self.assertEqual(report['actual_timed_calls']['candidate_sequence_scoring'],dict(attempted=2,returned=1,failed=1))
        self.assertEqual(report['workload']['logical_operations']['terminal_unavailable'],1)
        self.assertEqual(report['status'],'INCOMPLETE')
        n=len(b.calls)
        with self.assertRaisesRegex(ValueError,'Unresolved'): measure_fixed(out,backend_override=b)
        self.assertEqual(len(b.calls),n)
    def test_keyboard_interruption_report_and_explicit_cli(self):
        out=self.root/'interrupt'; shutil.copytree(self.source,out)
        class Interrupt(MockBackend):
            def generate(self,*a,**kw): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): measure_fixed(out,backend_override=Interrupt())
        report=reporting.fixed_timing_report(out)
        self.assertEqual(report['failures'],1); self.assertEqual(report['workload']['logical_operations']['terminal_unavailable'],1)
        with patch('exception_review.qwen_timing.load_backend',side_effect=AssertionError('NO LOAD')):
            with self.assertRaisesRegex(ValueError,'explicit'): main(['measure-fixed','--output',str(out)])
        fresh=self.root/'cli'; shutil.copytree(self.source,fresh)
        with patch('sys.stdout',new_callable=io.StringIO): main(['measure-fixed','--output',str(fresh),'--mock'])
        self.assertTrue((fresh/'measurements.json').exists())


class EventCountingTests(Base):
    def setUp(self):
        super().setUp(); source=self.root/'source'; shutil.copytree(self.source,source); self.source=source
    def plans(self,eligible=True):
        answer=self.root/'answer'; first=integration.freeze_events(self.source,answer)
        source=artifacts.Source(self.source); rows=[]
        for item in first['rows']:
            cut={k:v for k,v in item['cuts'][0].items() if k!='event'}
            bounds={name:dict(cut,eligible=eligible,k=cut['k'] if eligible else None) for name in ('before_statement','after_statement')}
            rows.append(dict(task_id=item['task_id'],trajectory_hash=item['trajectory_hash'],decision='present' if eligible else 'absent',boundaries=bounds))
        annotation=self.root/'statements.json'; artifacts.freeze(annotation,dict(source_hash=source.hash,code_hash=policy.code_hash(),rows=rows))
        statement=self.root/'statement'; integration.freeze_events(self.source,statement,annotation)
        return answer,statement
    def test_one_both_and_conditional_reference_counts(self):
        answer,statement=self.plans()
        default=reporting.qwen_timing_report(self.source)
        self.assertEqual(default['remaining_work']['event_reference']['remaining_count_scenario'],[0,48])
        one=reporting.qwen_timing_report(self.source,event_outputs=[answer])
        both=reporting.qwen_timing_report(self.source,event_outputs=[answer,statement,answer])
        self.assertEqual(one['remaining_work']['event_reference']['planned_maximum'],24)
        self.assertEqual(both['remaining_work']['event_reference']['planned_maximum'],48)
        self.assertEqual(len(both['event_workloads']['plans']),2)
        # Two identical statement cuts still need only one replay per trajectory in that directory.
        self.assertEqual(both['remaining_work']['event_validation']['planned_maximum'],48)
        self.assertEqual(both['remaining_work']['candidate_sequence_scoring_events']['planned_maximum'],144)
        self.assertIsNone(both['remaining_work']['event_reference']['seconds_scenario'])
        self.assertIsNone(both['full_study_total'])
    def test_no_eligible_statement_cuts_and_empty_request(self):
        answer,statement=self.plans(False)
        report=reporting.qwen_timing_report(self.source,event_outputs=[answer,statement])
        self.assertEqual(report['remaining_work']['event_reference']['planned_maximum'],24)
        self.assertEqual(report['event_workloads']['plans'][1]['counts']['event_reference']['planned_maximum'],0)
        empty=reporting.qwen_timing_report(self.source,event_outputs=[])
        self.assertEqual(empty['remaining_work']['event_reference']['remaining_count_scenario'],[0,0])
    def test_completed_events_cache_reuse_actual_journals_and_cli(self):
        answer,statement=self.plans(); b=CountingBackend()
        integration.measure_events(answer,backend_override=b); n=len(b.calls)
        integration.measure_events(answer,backend_override=b); self.assertEqual(len(b.calls),n)
        one=reporting.qwen_timing_report(self.source,event_outputs=[answer,statement])
        self.assertEqual(one['remaining_work']['event_reference']['remaining_count_scenario'],[0,24])
        self.assertEqual(one['event_workloads']['plans'][0]['cache_hits'],72)
        integration.measure_events(statement,backend_override=b)
        with patch('sys.stdout',new_callable=io.StringIO) as output:
            main(['qwen-timing-report','--output',str(self.source),'--event-output',str(answer),'--event-output',str(statement)])
        both=json.loads(output.getvalue())
        self.assertEqual(both['remaining_work']['event_reference']['remaining_count_scenario'],[0,0])
        self.assertEqual(both['remaining_work']['event_reference']['returned'],48)
        self.assertEqual(both['event_observations']['event_reference/MOCK']['observations'],48)
    def test_event_report_rejects_different_source(self):
        answer,statement=self.plans(); frozen=runner.sealed_read(answer/'event-plan.json'); frozen['source_hash']='other'
        runner.sealed_write(answer/'event-plan.json',frozen)
        with self.assertRaisesRegex(ValueError,'source changed'): reporting.qwen_timing_report(self.source,event_outputs=[answer])


class ArmCoverageTests(Base):
    def test_count_identities_partial_syntax_replay_and_missing(self):
        cases=[dict(task_id=str(i)) for i in range(8)]; rows=[]; out=self.root/'interventions'
        for i in range(8):
            arms={}; row=dict(task_id=str(i),validation=dict(passed=i!=6),unchanged_replay_passed=i not in (4,6),arms=arms)
            if i==7: row.pop('unchanged_replay_passed')
            for arm in (*policy.ARMS,'unchanged'):
                if i in (3,6): continue
                status='failed' if i==5 else 'returned'
                op=dict(id=f'edit/{i}/{arm}/continuation',source_hash='source',manifest_hash='manifest',status=status,result=dict(tokens=[1],stopped=i!=1))
                runner.sealed_write(out/'model-operations'/(digest(op['id'])+'.json'),op)
                if i not in (2,5): arms[arm]=dict(score=dict(valid=i!=1,correct=None if i==1 else True))
            rows.append(row)
        result=intervention_coverage(cases,rows,out,'source','manifest')
        for counts in result['per_arm'].values():
            self.assertEqual({k:counts[k] for k in ('planned','attempted','returned','valid','invalid','truncated','missing','unassessed','replay_excluded')},dict(planned=8,attempted=6,returned=5,valid=3,invalid=1,truncated=1,missing=3,unassessed=1,replay_excluded=2))
            self.assertEqual(counts['analysis_valid'],1); self.assertEqual(counts['valid_replay_unassessed'],1)
    def test_secondary_arm_failure_preserves_primary_and_zero_case_null(self):
        self.all(); integration.check_tokens(self.out,'pilot',mock=True); integration.freeze_edits(self.out,'pilot')
        class Failure(MockBackend):
            def generate(self,ids,budget,capture_at=()):
                text=self.decode(ids[ids.index(1000000)+1:])
                if any('Its verified class is '+c+'.' in text for c in 'ABC'): raise RuntimeError('secondary fixture')
                return super().generate(ids,budget,capture_at)
        integration.intervene(self.out,'pilot',backend_override=Failure())
        result=reporting.report(self.out,'pilot'); coverage=result['intervention_coverage']['per_arm']
        self.assertEqual(coverage['value_repair']['attempted'],6); self.assertEqual(coverage['value_repair']['missing'],6)
        self.assertEqual(coverage['availability_repair']['analysis_valid'],6)
        self.assertEqual(result['primary_and_secondary']['primary_availability_minus_meaning']['complete_worlds'],3)
        self.out=self.root/'zero'; self.all(Transport(lambda c:detection('absent')))
        integration.freeze_edits(self.out,'pilot'); zero=reporting.report(self.out,'pilot')
        self.assertTrue(all(c['planned']==0 for c in zero['intervention_coverage']['per_arm'].values()))
        self.assertIsNone(zero['primary_and_secondary']['primary_availability_minus_meaning']['estimate'])
    def test_interrupted_scoring_retains_returned_but_unassessed(self):
        self.all(); integration.check_tokens(self.out,'pilot',mock=True); integration.freeze_edits(self.out,'pilot')
        class Interrupted(MockBackend):
            def score(self,*args): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): integration.intervene(self.out,'pilot',backend_override=Interrupted())
        result=reporting.report(self.out,'pilot'); counts=result['intervention_coverage']['per_arm']
        self.assertEqual(sum(c['returned'] for c in counts.values()),1)
        self.assertEqual(sum(c['unassessed'] for c in counts.values()),1)
        self.assertEqual(sum(c['valid']+c['invalid'] for c in counts.values()),0)
        self.assertEqual(sum(c['candidate_scoring_failed'] for c in counts.values()),1)
        self.assertIsNone(result['primary_and_secondary']['primary_availability_minus_meaning']['estimate'])

if __name__=='__main__': unittest.main()
