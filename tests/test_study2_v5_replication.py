"""Replication amendment acceptance: synthetic backends, blocked loaders/network."""
import copy
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read,sealed_write
from exception_study2_v5 import core,runner,readouts as old_readouts,scoring
from exception_study2_v5.journal import operations
from exception_study2_v5_replication import workflow,readouts,analysis,integrity
from test_study2_v5 import Offline,Fake
from test_study2_v5_review_v2 import snapshot


class ShortFake(Fake):
    def generate(self,ids,budget,capture_at=()):
        self.calls.append((list(ids),budget,tuple(capture_at)))
        if self.fail_generation:raise RuntimeError('Synthetic failed attempt')
        prompt=self.decode(ids);target=[s for s in prompt.splitlines() if s.startswith('| ')][-1]
        gold=target.split('|')[-2].strip()
        text=('Recorded evidence noted.\n' if 'reasoning' in prompt.lower() else '')+'ANSWER: '+gold+'\n'
        tokens=self.encode(text)+[0]
        return dict(tokens=tokens,text=self.decode(tokens),stopped=True,finish='eos',next_logits={})


class ReplicationTests(Offline):
    @classmethod
    def setUpClass(cls):
        cls.cache=tempfile.TemporaryDirectory();cls.base=Path(cls.cache.name)
        def forbidden(*a,**k):raise AssertionError('Offline fixtures only')
        with patch.object(socket.socket,'connect',forbidden):
            core.prepare(cls.base/'pilot');b=Fake()
            # Simulate an earlier checkout honestly in a wholly synthetic fixture.
            import subprocess
            original_check_output=subprocess.check_output
            def earlier(args,**kwargs):
                return 'synthetic-earlier-revision\n' if args==['git','rev-parse','HEAD'] else original_check_output(args,**kwargs)
            with patch('exception_study2_v5.journal.subprocess.check_output',side_effect=earlier):
                runner.technical(cls.base/'pilot',backend_override=b);runner.collect(cls.base/'pilot',backend_override=b)
            old_readouts.prepare_measurements(cls.base/'pilot',cls.base/'fixed')
            old_readouts.measure(cls.base/'fixed',backend_override=b)
        (cls.base/'judges').mkdir();(cls.base/'judges/immutable.txt').write_text('Synthetic archived judge evidence; never changed')
    @classmethod
    def tearDownClass(cls):cls.cache.cleanup()
    def setup_rep(self):
        for name in ('pilot','fixed','judges'):shutil.copytree(self.base/name,self.root/name)
        out=self.root/'replication';a=workflow.prepare(self.root/'pilot',out,[self.root/'fixed',self.root/'judges'])
        return out,a
    def approve(self,out,a):return workflow.approve(out,a['artifact_hash'],'offline-reviewer','Synthetic post-pilot amendment acceptance.',True,True)
    def test_exact_design_copy_and_preview_32_448_224(self):
        out,a=self.setup_rep();before=snapshot(self.root/'pilot');v=workflow.inspect(out)
        self.assertEqual(len(v['remaining_tasks']),448);self.assertEqual(len(v['remaining_worlds']),56)
        self.assertEqual(len(v['remaining_visible_ids']),224);self.assertEqual(a['remaining_tasks'],core.read_plan(self.root/'pilot')['tasks'][32:])
        self.assertEqual(snapshot(out/'originals'),before);self.assertEqual(v['recorded_remaining'],0)
        self.assertNotEqual((out/'originals/plan-v5.json').stat().st_ino,(self.root/'pilot/plan-v5.json').stat().st_ino)
        self.assertEqual(v['edited_continuations'],0);self.assertEqual(v['readout_ceiling'],2688)
    def test_preparation_and_default_collection_do_not_load_or_generate(self):
        with patch.object(Fake,'generate',side_effect=AssertionError('No generation')):
            out,a=self.setup_rep();self.assertEqual(workflow.collect(out)['inference_calls'],0)
            self.assertEqual(workflow.prepare(self.root/'pilot',out,[self.root/'fixed',self.root/'judges']),a)
        self.assertFalse((out/'replication-execution.json').exists())
    def test_approval_requires_exact_hash_and_pilot_acknowledgment(self):
        out,a=self.setup_rep()
        for h,ack,approved in [('wrong',True,True),(a['artifact_hash'],False,True),(a['artifact_hash'],True,False)]:
            with self.assertRaises(ValueError):workflow.approve(out,h,'reviewer','reason',ack,approved)
        b=ShortFake()
        with self.assertRaises(FileNotFoundError):workflow.collect(out,backend_override=b)
        self.assertEqual(b.calls,[])
        self.assertTrue(self.approve(out,a)['study_2b_not_a_prerequisite'])
        self.assertFalse((out/'originals/remaining-approval-v5.json').exists())
    def test_no_pilot_or_judge_mutations_and_no_old_approval_calls(self):
        out,a=self.setup_rep();self.approve(out,a);before={n:snapshot(self.root/n) for n in ('pilot','fixed','judges')}
        b=ShortFake();b.fail_generation=True
        with patch('exception_study2_v5.staging.require_approval',side_effect=AssertionError('No legacy approval bypass')):
            r=workflow.collect(out,backend_override=b)
        self.assertEqual(len(b.calls),448);self.assertEqual(r['next_stage'],'STOP')
        self.assertEqual(before,{n:snapshot(self.root/n) for n in before})
        self.assertFalse((out/'readouts-remaining-v1').exists());self.assertEqual(runner.Source(out/'originals',scope='pilot').binding,runner.Source(self.root/'pilot').binding)
        n=len(b.calls);workflow.collect(out,backend_override=b);self.assertEqual(n,len(b.calls))
        self.assertEqual(len(runner.Source(out/'originals',scope='remaining').rows),448)
    def test_new_revision_recorded_without_rewriting_pilot_execution(self):
        out,a=self.setup_rep();self.approve(out,a);old=(out/'originals/execution-v5.json').read_bytes()
        b=ShortFake()
        def stop(*args,**kwargs):raise KeyboardInterrupt('Synthetic interruption')
        b.generate=stop
        with self.assertRaises(KeyboardInterrupt):workflow.collect(out,backend_override=b)
        runtime=sealed_read(out/'replication-execution.json');self.assertEqual(runtime['code_revision'],integrity.revision())
        self.assertEqual(runtime['original_code_revision'],'synthetic-earlier-revision');self.assertEqual((out/'originals/execution-v5.json').read_bytes(),old)
        op=operations(out/'originals')['v5/original/'+a['remaining_tasks'][0]['id']]
        self.assertEqual(op['replication_execution_hash'],runtime['artifact_hash'])
        with patch.object(workflow,'revision',return_value='different-revision'):
            with self.assertRaisesRegex(ValueError,'runtime/revision'):workflow.collect(out,backend_override=ShortFake())
    def test_ambiguous_interruption_consumed_without_retry_and_only_448_total(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake()
        def interrupt(*args,**kwargs):b.calls.append(args);raise KeyboardInterrupt('Synthetic uncertain completion')
        b.generate=interrupt
        with self.assertRaises(KeyboardInterrupt):workflow.collect(out,backend_override=b)
        first='v5/original/'+a['remaining_tasks'][0]['id'];folder=out/'originals/operations-v5'/digest(first)
        (folder/'failed.json').unlink()  # Synthetic journal left at ambiguous started state.
        resume=ShortFake();resume.fail_generation=True;workflow.collect(out,backend_override=resume)
        self.assertEqual(len(resume.calls),447)
        self.assertEqual(runner.Source(out/'originals',scope='remaining').rows[a['remaining_tasks'][0]['id']]['status'],'unavailable')
        workflow.collect(out,backend_override=resume);self.assertEqual(len(resume.calls),447)
    def test_returned_operation_without_row_is_reused_without_resampling(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();original_freeze=workflow.freeze
        target=out/'originals/originals-v5'/(digest(a['remaining_tasks'][0]['id'])+'.json')
        def interrupted(path,value):
            if Path(path).resolve()==target.resolve():raise KeyboardInterrupt('Synthetic interruption after durable model return')
            return original_freeze(path,value)
        with patch.object(workflow,'freeze',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):workflow.collect(out,backend_override=b)
        self.assertEqual(len(b.calls),1);self.assertFalse(target.exists())
        resumed=ShortFake();resumed.fail_generation=True;workflow.collect(out,backend_override=resumed)
        self.assertEqual(len(resumed.calls),447);self.assertEqual(sealed_read(target)['status'],'returned')

    def test_backend_model_mismatch_stops_before_generation(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();b.identity=dict(b.identity,model='different')
        with self.assertRaisesRegex(ValueError,'backend identity'):workflow.collect(out,backend_override=b)
        self.assertEqual(b.calls,[]);self.assertFalse((out/'replication-execution.json').exists())
    def test_prompt_token_mismatch_stops_before_generation(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();b.prompt=lambda text:[999]
        with self.assertRaisesRegex(ValueError,'prompt token'):workflow.collect(out,backend_override=b)
        self.assertEqual(b.calls,[])
    def test_original_source_or_judge_archive_mutation_stops(self):
        out,a=self.setup_rep();self.approve(out,a);p=self.root/'judges/immutable.txt';p.write_text('Changed')
        with self.assertRaisesRegex(ValueError,'archive changed'):workflow.collect(out,backend_override=ShortFake())
    def test_copied_pilot_or_technical_tamper_stops(self):
        out,a=self.setup_rep();p=out/'originals/technical-v5.json';v=sealed_read(p);v['technical_same_input_passed']=False;sealed_write(p,v)
        with self.assertRaisesRegex(ValueError,'pilot artifact'):workflow.inspect(out)
    def test_no_additional_source_attempts_and_orphan_states_accepted(self):
        src=self.root/'pilot';shutil.copytree(self.base/'pilot',src)
        folder=src/'operations-v5/orphan';folder.mkdir();(folder/'started.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Orphan'):workflow.prepare(src,self.root/'out')
    def test_nested_or_nonfresh_outputs_and_weight_links_rejected(self):
        src=self.root/'pilot';shutil.copytree(self.base/'pilot',src)
        with self.assertRaises(ValueError):workflow.prepare(src,src/'nested')
        (self.root/'out').mkdir()
        with self.assertRaisesRegex(ValueError,'Fresh'):workflow.prepare(src,self.root/'out')
        (src/'weights').symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlinks'):workflow.prepare(src,self.root/'fresh')
    def test_measurements_require_all_remaining_attempts(self):
        out,a=self.setup_rep();self.approve(out,a)
        with self.assertRaisesRegex(ValueError,'Complete attempted'):readouts.prepare(out)
        self.assertFalse((out/'readouts-remaining-v1').exists())
    def test_full_remaining_readouts_no_pilot_replay_both_cues_original_formats(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();workflow.collect(out,backend_override=b)
        before={n:snapshot(self.root/n) for n in ('pilot','fixed','judges')};n=len(b.calls)
        plan=readouts.prepare(out);self.assertEqual(len(plan['rows']),224)
        self.assertEqual(plan['layout'],'fixed_only');self.assertIsNone(plan['annotations_hash'])
        self.assertEqual({c['task_id'] for c in plan['computations'].values()},set(a['remaining_visible_ids']))
        self.assertFalse({c['task_id'] for c in plan['computations'].values()} & set(a['pilot_rows']))
        self.assertEqual({c['cue_text'] for c in plan['computations'].values()},{'\nANSWER:','\nFinal answer:'})
        source=runner.Source(out/'originals',scope='remaining')
        for item in plan['rows']:
            expected=scoring.checkpoints(source.rows[item['task_id']])
            self.assertEqual([{k:v for k,v in c.items() if k!='computations'} for c in item['checkpoints']],expected)
        self.assertEqual(readouts.measure(out)['inference_calls'],0)
        with patch.object(b,'generate',side_effect=AssertionError('Measurements must not generate')):
            data=readouts.measure(out,backend_override=b)
        self.assertEqual(len(b.calls),n);self.assertEqual(len(data['results']),len(plan['computations']))
        self.assertTrue(all(set(r['value']['scores'])==set('ABC') for r in data['results'].values()))
        p,read=readouts.read_data(source,out/'readouts-remaining-v1');self.assertEqual(data['results'],read['results'])
        report=analysis.analyze(out,self.root/'fixed');self.assertEqual(report['remaining_56']['behavioral']['worlds'],56)
        self.assertEqual(report['examined_pilot_4']['behavioral']['worlds'],4);self.assertIsNone(report['pooled_60'])
        self.assertEqual(before,{n:snapshot(self.root/n) for n in before})
        scores=len(b.scores);readouts.measure(out,backend_override=b);self.assertEqual(scores,len(b.scores))
        # Frozen readout requests cannot be redirected to a pilot trajectory.
        bad=copy.deepcopy(plan);bad['computations'][next(iter(bad['computations']))]['task_id']=next(iter(a['pilot_rows']))
        sealed_write(out/'readouts-remaining-v1/measurement-plan-v5.json',bad)
        with self.assertRaises(ValueError):readouts.measure(out,backend_override=b)
        self.assertEqual(len(b.scores),scores)
    def test_failed_originals_retained_in_all_224_readout_rows(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();b.fail_generation=True;workflow.collect(out,backend_override=b)
        plan=readouts.prepare(out);self.assertEqual(len(plan['rows']),224);self.assertEqual(plan['computations'],{})
        self.assertTrue(all(r['checkpoints'][0]['reason']=='unavailable' for r in plan['rows']))
    def test_analysis_missing_readouts_never_zero_filled(self):
        out,a=self.setup_rep();self.approve(out,a);b=ShortFake();workflow.collect(out,backend_override=b);readouts.prepare(out)
        report=analysis.analyze(out)
        primary=report['remaining_56']['cues']['0']['framing']['original']['primary_pre_answer_minus_initial']
        self.assertEqual(primary['complete_worlds'],0);self.assertIsNone(primary['estimate']['estimate']);self.assertEqual(primary['planned_pairs'],112)
        self.assertEqual(report['examined_pilot_4']['readouts'],'NOT_PROVIDED')
    def test_amendment_and_remaining_task_tamper_rejected(self):
        out,a=self.setup_rep();v=copy.deepcopy(a);v['remaining_tasks']=v['remaining_tasks'][:8];sealed_write(out/'amendment.json',v)
        with self.assertRaisesRegex(ValueError,'amendment/source/design'):workflow.inspect(out)


class AnalysisTests(unittest.TestCase):
    def task(self,world='w',variant=0):return dict(world=world,variant=variant,expected='C',pattern='A')
    def test_world_weighting_is_not_checkpoint_or_trajectory_weighting(self):
        tasks=[self.task('w1',0),self.task('w1',1),self.task('w2',0)]
        r=analysis.grouped(list(zip(tasks,[0,0,9])),tasks)
        self.assertEqual(r['estimate'],4.5);self.assertEqual(r['worlds'],2);self.assertEqual(r['observed_trajectories'],3)
    def test_reversal_and_recovery_in_actual_order(self):
        r=analysis.preference_events([{'preferred_class':x} for x in 'CBAC'],self.task())
        self.assertTrue(r['reversal']);self.assertTrue(r['recovery']);self.assertEqual(r['adjacent_verified_to_pattern'],0)
    def test_missing_checkpoint_does_not_invent_reversal_or_recovery(self):
        r=analysis.preference_events([{'preferred_class':'C'},None,{'preferred_class':'A'},{'preferred_class':'C'}],self.task())
        self.assertIsNone(r['reversal']);self.assertIsNone(r['recovery'])
    def test_observed_reversal_with_missing_later_readout_has_unknown_recovery(self):
        r=analysis.preference_events([{'preferred_class':'C'},{'preferred_class':'A'},None],self.task())
        self.assertTrue(r['reversal']);self.assertIsNone(r['recovery'])
    def test_complete_series_negative_is_distinct_from_unknown(self):
        r=analysis.preference_events([{'preferred_class':'C'},{'preferred_class':'B'}],self.task())
        self.assertIs(r['reversal'],False);self.assertIs(r['recovery'],False)
    def test_complete_world_primary_and_paired_population_denominators(self):
        tasks=[];rows={};planned=[];results={}
        for world in ('w1','w2'):
            for variant in (0,1):
                tid=f'{world}/v{variant}/original/visible'
                task=dict(self.task(world,variant),id=tid,framing='original',arm='visible');tasks.append(task)
                rows[tid]=dict(task=task,status='returned',raw={},score=dict(outcome='correct',valid=True,correct=True,answer='C',strict_format=True,strict_correct=True))
                cuts=[]
                for i,name in enumerate(analysis.CUTS):
                    keys=[]
                    for ci in (0,1):
                        key=f'{tid}/{i}/{ci}';keys.append(key)
                        initial=0 if world=='w1' else 10 if variant==0 else 30
                        val=initial if i==0 else (1 if variant==0 else 3) if world=='w1' else 19
                        if world=='w2' and variant==1 and name=='pre_answer' and ci==0:results[key]=dict(status='unavailable')
                        else:results[key]=dict(status='returned',value=dict(gold_pattern_log_odds=val,preferred_class='C' if ci==0 else 'A'))
                    cuts.append(dict(name=name,eligible=True,k=i,computations=keys))
                planned.append(dict(task_id=tid,checkpoints=cuts))
        source=SimpleNamespace(tasks=tasks,rows=rows,worlds=[dict(id=w) for w in ('w1','w2')],plan=dict(config=dict(readout_cues=['\nANSWER:','\nFinal answer:'])))
        plan=dict(rows=planned,computations={k:{} for k in results});r=analysis.summarize(source,plan,dict(results=results))
        original=r['cues']['0']['framing']['original'];p=original['primary_pre_answer_minus_initial']
        self.assertEqual(p['estimate']['estimate'],2);self.assertEqual(p['complete_worlds'],1);self.assertEqual(p['complete_pairs'],3)
        self.assertEqual(original['checkpoint_levels']['pre_answer']['observed_trajectories'],3)
        self.assertEqual(original['paired_changes_from_initial']['pre_answer']['estimate'],5.5)
        self.assertEqual(len(original['complete_checkpoint_cohort']['task_ids']),3)
        self.assertEqual(r['cue_agreement']['original']['pre_answer']['disagreements'],3)
        self.assertEqual(r['legacy_v5']['primary_original_pre_answer_minus_initial']['estimate']['estimate'],2)

    def test_exact_checkpoint_rules_and_aliases_unchanged(self):
        raw=dict(text='x'*1100+'\nANSWER: C',tokens=list(range(1110)),stopped=True)
        row=dict(raw=raw,boundaries=[dict(k=k,char_end=k,text_hash=digest(raw['text'][:k]),token_hash=digest(raw['tokens'][:k]),roundtrip_exact=True) for k in [0,128,256,512,1024,1101]])
        cuts=scoring.checkpoints(row);self.assertEqual([c['name'] for c in cuts],analysis.CUTS)
        self.assertTrue(all(c['eligible'] for c in cuts));self.assertEqual(cuts[-1]['k'],1101)
        row['boundaries']=[c for c in row['boundaries'] if c['k']!=512]
        self.assertFalse(scoring.checkpoints(row)[3]['eligible'])

if __name__=='__main__':unittest.main()
