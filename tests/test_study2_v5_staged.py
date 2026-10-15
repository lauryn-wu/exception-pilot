"""Staged amendment: all synthetic, no network, model loading, tokenization or CUDA replay."""
import copy
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from tests.test_study2_v5 import Offline, Fake, reviewed, edits, dump
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read, sealed_write
from exception_study2_v5 import core, runner, readouts, interventions, staging, reconstruction, splits, reporting
from exception_study2_v5.journal import operations
from exception_study2_v5.review import workflow


def completed_checklist(test,out,b):
    ann=reviewed(out,test.root/'review')
    readouts.prepare_measurements(out,test.root/'measure',ann)
    readouts.measure(test.root/'measure',backend_override=b)
    for family in ('M','O'):
        edits(out,ann,test.root/family,family,b)
        interventions.intervene(test.root/family,backend_override=b)
    target=test.root/'checklist.json'
    staging.pilot_checklist(out,target,test.root/'measure/measurements-v5.json',ann,
                           test.root/'M/interventions-v5.json',test.root/'O/interventions-v5.json')
    decision=json.loads((test.root/'pilot-review-template.json').read_text())
    decision.update(reviewer='offline-test-reviewer',rationale='Synthetic technical acceptance, no outcome threshold.',approve_remaining=True)
    decision['checks']={k:dict(status='passed',evidence='Synthetic test artifacts independently inspected.') for k in staging.CHECKS}
    return target,dump(test.root/'review-decision.json',decision)


class StagedTests(Offline):
    def test_fixed_sixty_and_initial_four_complete_worlds(self):
        out,b=self.run_source();p=core.read_plan(out);src=runner.Source(out)
        self.assertEqual(len(p['worlds']),60);self.assertEqual(len(p['tasks']),480)
        self.assertEqual(list(src.rows),[t['id'] for t in p['tasks'][:32]])
        self.assertEqual({r['task']['world'] for r in src.rows.values()},{w['id'] for w in p['worlds'][:4]})
        self.assertEqual(sum(r['task']['arm']=='visible' for r in src.rows.values()),16)
        self.assertEqual(len(p['arm_orders']),480)
        self.assertTrue(all(sorted(a)==sorted(interventions.ARMS) for v in p['arm_orders'].values() for a in v.values()))
        self.assertEqual(len({r['plan_hash'] for r in src.rows.values()}),1)

    def test_remaining_requires_completed_pilot_review_and_no_implicit_stage(self):
        out,b=self.run_source();n=len(b.calls)
        with self.assertRaises(FileNotFoundError):runner.collect(out,batch='remaining',backend_override=b)
        self.assertEqual(len(b.calls),n)
        self.assertFalse((out/'measurement-plan-v5.json').exists())
        self.assertIsNone(reporting.behavioral_report(out)['calibration']['passed'])

    def test_approved_remaining_preserves_pilot_snapshot_and_only_unattempted_calls(self):
        out,b=self.run_source();before=runner.Source(out);plan_bytes=(out/'plan-v5.json').read_bytes()
        checklist,decision=completed_checklist(self,out,b)
        staging.approve_remaining(out,checklist,decision)
        b.fail_generation=True  # Retain all failures rather than selecting successes.
        n=len(b.calls);runner.collect(out,batch='remaining',backend_override=b)
        self.assertEqual(len(b.calls)-n,448)
        self.assertEqual(len(runner.Source(out,scope='all').rows),480)
        self.assertEqual(len(runner.Source(out,scope='remaining').rows),448)
        self.assertFalse(set(runner.Source(out,scope='remaining').rows)&set(before.rows))
        self.assertEqual(runner.Source(out).binding,before.binding)
        self.assertEqual((out/'plan-v5.json').read_bytes(),plan_bytes)
        self.assertTrue(all(r['plan_hash']==before.plan['plan_hash'] for r in runner.Source(out,scope='all').rows.values()))
        n=len(b.calls);runner.collect(out,batch='remaining',backend_override=b)
        self.assertEqual(len(b.calls),n)
        # All prior pilot artifacts still read after the remaining batch.
        workflow.read_manifest(self.root/'review/annotation-manifest-v5.json',runner.Source(out))
        readouts.measure(self.root/'measure',backend_override=b)
        self.assertEqual(len(b.calls),n)
        changed=json.loads(decision.read_text());changed['scientific_protocol_unchanged']=False
        with self.assertRaises(ValueError):staging.approve_remaining(out,checklist,dump(self.root/'changed.json',changed))
        changed=json.loads(decision.read_text());changed['checks'][staging.CHECKS[0]]['status']='failed'
        with self.assertRaises(ValueError):staging.approve_remaining(out,checklist,dump(self.root/'bad-check.json',changed))

    def test_live_requires_sample_confirmation_before_loading(self):
        out=self.root/'source';core.prepare(out)
        with patch.object(runner,'load_backend',side_effect=AssertionError('must not load')):
            with self.assertRaises(FileNotFoundError):runner.technical(out,live_qwen=True)
        with self.assertRaises(ValueError):staging.confirm_design(out,'reviewer','reason',48)
        staging.confirm_design(out,'reviewer','Sixty worlds confirmed',60)
        self.assertEqual(staging.require_design_confirmation(out)['worlds'],60)

    def test_historical_plan_rejected_without_mutation(self):
        out=self.root/'old';out.mkdir();p=core.make_plan();p.pop('design_version');p.pop('plan_hash');p['plan_hash']=digest(p)
        sealed_write(out/'plan-v5.json',p);before=(out/'plan-v5.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Historical v5 plan preserved'):core.read_plan(out)
        self.assertEqual(before,(out/'plan-v5.json').read_bytes())

    def test_corrupted_original_prevents_resume_before_any_new_call(self):
        out,b=self.run_source();source=runner.Source(out);tid=next(iter(source.rows));row=copy.deepcopy(source.rows[tid]);row.pop('artifact_hash')
        row['raw']['tokens'][0]+=1;sealed_write(out/'originals-v5'/(digest(tid)+'.json'),row)
        n=len(b.calls)
        with self.assertRaises(ValueError):runner.collect(out,backend_override=b)
        self.assertEqual(n,len(b.calls))

    def test_malformed_approval_cannot_authorize_remaining(self):
        out,b=self.run_source();sealed_write(out/'remaining-approval-v5.json',dict(schema='forged',source={}))
        with self.assertRaises(ValueError):runner.collect(out,batch='remaining',backend_override=b)


class ReconstructionTests(Offline):
    def test_uncued_roundtrip_exact_ids_and_readout_linkage(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review');path=self.root/'checkpoints.json'
        mp=readouts.prepare_measurements(out,self.root/'measure',ann)
        reconstruction.prepare_checkpoints(out,path,ann)
        source=runner.Source(out);tid=next(t for t,r in source.rows.items() if r['task']['arm']=='visible')
        row=source.rows[tid];before={str(p):p.read_bytes() for p in out.rglob('*') if p.is_file()}
        with patch.object(Fake,'encode',side_effect=AssertionError('no retokenization')),patch.object(Fake,'generate',side_effect=AssertionError('no generation')),patch.object(runner,'load_backend',side_effect=AssertionError('no load')):
            result=reconstruction.reconstruct(path,tid,'fixed/128',self.root/'context.json')
        self.assertTrue(result['available']);self.assertEqual(result['context_ids'],row['input_ids']+row['raw']['tokens'][:128])
        self.assertEqual(result['prompt_ids'],row['input_ids']);self.assertEqual(result['original_prefix_ids'],row['raw']['tokens'][:128])
        self.assertFalse(result['answer_cue_appended']);self.assertFalse(result['activations_collected'])
        self.assertFalse(result['original_hidden_state_equivalence'])
        self.assertNotIn('ANSWER:',result['original_prefix_text'])
        self.assertEqual(sealed_read(self.root/'context.json')['context_ids'],result['context_ids'])
        cut=next(c for r in mp['rows'] if r['task_id']==tid for c in r['checkpoints'] if c['name']=='fixed/128')
        self.assertEqual({k:v for k,v in cut.items() if k!='computations'},result['checkpoint'])
        for name,data in before.items():self.assertEqual(Path(name).read_bytes(),data)

    def test_event_boundaries_and_unavailable_fixed_cut(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review');path=self.root/'checkpoints.json';reconstruction.prepare_checkpoints(out,path,ann)
        tid=next(t for t,r in runner.Source(out).rows.items() if r['task']['arm']=='visible')
        result=reconstruction.reconstruct(path,tid,'acknowledgment/after')
        self.assertTrue(result['available']);self.assertTrue(result['checkpoint']['roundtrip_exact'])
        self.assertEqual(result['original_prefix_text'],runner.Source(out).rows[tid]['raw']['text'][:result['checkpoint']['char_end']])
        absent=reconstruction.reconstruct(path,tid,'fixed/1024');self.assertFalse(absent['available']);self.assertIsNone(absent['context_ids'])
        self.assertIsNotNone(absent['reason'])

    def test_portable_reconstruction_without_original_path_or_gpu_match(self):
        out,b=self.run_source();path=self.root/'checkpoints.json';reconstruction.prepare_checkpoints(out,path)
        tid=next(t for t,r in runner.Source(out).rows.items() if r['task']['arm']=='visible')
        target=self.root.parent/(self.root.name+'-moved');shutil.copytree(self.root,target);self.addCleanup(shutil.rmtree,target)
        shutil.rmtree(out)  # Only temporary synthetic fixture; prove no old path dependency.
        with patch('torch.cuda.get_device_name',side_effect=AssertionError('no GPU query')),patch('torch.cuda.init',side_effect=AssertionError('no GPU initialization')):
            result=reconstruction.reconstruct(target/'checkpoints.json',tid,'fixed/128')
        self.assertTrue(result['available']);self.assertEqual(result['recorded_backend']['kind'],'SYNTHETIC_V5_TEST_ONLY')

    def test_stale_tokens_hashes_and_malformed_checkpoints_fail(self):
        out,b=self.run_source();path=self.root/'checkpoints.json';reconstruction.prepare_checkpoints(out,path)
        base=sealed_read(path);tid=next(iter(base['rows']))
        for change in ('offset','source','row','token'):
            value=copy.deepcopy(base);value.pop('artifact_hash')
            if change=='offset':value['rows'][tid]['checkpoints'][0]['k']=1
            if change=='source':value['source']['plan_hash']='stale'
            if change=='row':value['rows'][tid]['source_row_hash']='stale'
            if change=='token':value['rows'][tid]['output_hash']='stale'
            temp=self.root/(change+'.json');sealed_write(temp,value)
            with self.assertRaises(ValueError):reconstruction.reconstruct(temp,tid,'fixed/0')
        with self.assertRaises(FileNotFoundError):reconstruction.reconstruct(self.root/'missing.json',tid,'fixed/0')
        with self.assertRaises(ValueError):reconstruction.reconstruct(path,tid,'made-up/0')

    def test_original_only_never_uses_intervention_arm_ids(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review');editout=self.root/'M';manifest=edits(out,ann,editout,'M',b)
        path=self.root/'checkpoints.json';reconstruction.prepare_checkpoints(out,path,ann)
        case=manifest['cases'][0];result=reconstruction.reconstruct(path,case['task_id'],'erasure/after')
        self.assertEqual(result['original_prefix_ids'],case['prefix_ids']['unchanged'])
        self.assertNotEqual(result['original_prefix_ids'],case['prefix_ids']['value_blind'])
        self.assertEqual(result['source_row_hash'],case['source_row_hash'])
        with self.assertRaises(ValueError):reconstruction.reconstruct(editout/'intervention-manifest-v5.json',case['task_id'],'erasure/after')

    def test_boundary_fingerprints_reject_resealed_bad_offsets(self):
        out,b=self.run_source();row=copy.deepcopy(next(r for r in runner.Source(out).rows.values() if r['task']['arm']=='visible'))
        for field,value in [('k',True),('char_end',-1),('roundtrip_exact',False),('token_hash','bad'),('text_hash','bad')]:
            bad=copy.deepcopy(row);bad['boundaries'][1][field]=value
            with self.assertRaises(ValueError):reconstruction.validate_boundaries(bad)


class SplitTests(Offline):
    def test_deterministic_world_disjoint_and_all_descendants_follow_parent(self):
        out=self.root/'source';plan=core.prepare(out);a=self.root/'splits.json';m=splits.make_splits(out,a,pilot_informed_design=True)
        self.assertEqual(m,splits.make_splits(out,a,pilot_informed_design=True))
        self.assertEqual(sum(v=='evaluation' for v in m['worlds'].values()),12)
        self.assertTrue(all(m['worlds'][w['id']]=='train' for w in plan['worlds'][:4]))
        for task in plan['tasks']:
            self.assertEqual(m['tasks'][task['id']]['split'],m['worlds'][task['world']])
        # Representative original, every checkpoint and both families' four arms share this rule.
        t=plan['tasks'][0]
        for _ in m['checkpoint_names']+m['intervention_arms']:
            self.assertEqual(splits.descendant_split(a,t['id'],t['world'],out),'train')
        with self.assertRaises(ValueError):splits.descendant_split(a,t['id'],plan['worlds'][1]['id'],out)
        with self.assertRaises(ValueError):splits.make_splits(out,a,seed=1)
        self.assertFalse(m['outcome_stratification']);self.assertFalse(m['training_performed'])

    def test_recorded_pilot_method_design_cannot_be_declared_heldout(self):
        out=self.root/'source';plan=core.prepare(out)
        sealed_write(out/'remaining-approval-v5.json',dict(scientific_plan_hash=plan['plan_hash'],decisions={'pilot_informed_method_design':True}))
        with self.assertRaisesRegex(ValueError,'contradicts'):splits.make_splits(out,self.root/'splits.json',pilot_informed_design=False)

    def test_split_corruption_and_wrong_source_fail(self):
        out=self.root/'source';plan=core.prepare(out);path=self.root/'splits.json';m=splits.make_splits(out,path);tid=plan['tasks'][0]['id'];world=plan['tasks'][0]['world']
        m.pop('artifact_hash');m['tasks'][tid]['split']='evaluation';sealed_write(path,m)
        with self.assertRaises(ValueError):splits.descendant_split(path,tid,world,out)
        m['tasks'][tid]['split']='train';m['plan_hash']='wrong';sealed_write(path,m)
        with self.assertRaises(ValueError):splits.descendant_split(path,tid,world,out)

class NullPilotTests(Offline):
    def test_zero_events_and_no_accuracy_gap_can_be_approved_without_gpu(self):
        class NoEvents(Fake):
            def generate(self,ids,budget,capture_at=()):
                if '| License plate |' not in self.decode(ids):return super().generate(ids,budget,capture_at)
                self.calls.append((list(ids),budget,tuple(capture_at)))
                target=[line for line in self.decode(ids).splitlines() if line.startswith('| ')][-1]
                text='ANSWER: '+target.split('|')[-2].strip()
                return dict(tokens=self.encode(text)+[0],text=text,stopped=True,finish='eos',next_token_logits={})
        out=self.root/'source';core.prepare(out);b=NoEvents();runner.technical(out,backend_override=b);runner.collect(out,backend_override=b)
        checklist,decision=completed_checklist(self,out,b)
        value=sealed_read(checklist)
        self.assertEqual([v['cases'] for v in value['coverage']['families'].values()],[0,0])
        for family in ('M','O'):
            self.assertEqual(sealed_read(self.root/family/'interventions-v5.json')['gpu_calls'],0)
            with patch.object(runner,'load_backend',side_effect=AssertionError('zero-case stage must not load')):
                result=interventions.intervene(self.root/family,live_qwen=True)
            self.assertEqual(result['status'],'ZERO_ELIGIBLE_CASES')
        d=json.loads(decision.read_text())
        for key in ('source_spans_and_token_boundaries','four_arm_semantics_and_label_leak'):
            d['checks'][key]=dict(status='not_applicable_zero_cases',evidence='Both independently reviewed event families have zero cases.')
        dump(decision,d);staging.approve_remaining(out,checklist,decision)
        self.assertEqual(staging.require_approval(out)['remaining_worlds'],56)
        self.assertEqual(reporting.behavioral_report(out)['matched_errors'],0)

class EventStageTests(Offline):
    def test_separate_fixed_and_event_measurements_cover_combined_checkpoint_names(self):
        out,b=self.run_source();ann=reviewed(out,self.root/'review')
        fixed=readouts.prepare_measurements(out,self.root/'fixed')
        events=readouts.prepare_measurements(out,self.root/'events',ann,events_only=True)
        combined=readouts.prepare_measurements(out,self.root/'combined',ann)
        for f,e,c in zip(fixed['rows'],events['rows'],combined['rows']):
            self.assertEqual(f['task_id'],e['task_id'])
            self.assertEqual({v['name'] for v in f['checkpoints']}|{v['name'] for v in e['checkpoints']},{v['name'] for v in c['checkpoints']})
            self.assertFalse({v['name'] for v in f['checkpoints']}&{v['name'] for v in e['checkpoints']})
        self.assertEqual(events['layout'],'events_only')
        with self.assertRaises(ValueError):readouts.prepare_measurements(out,self.root/'no-ann',events_only=True)
        self.assertLessEqual(3*(len(fixed['computations'])+len(events['computations'])),1344)

class MalformedOriginalTests(Offline):
    def test_invalid_response_shapes_are_preserved_without_resampling(self):
        out=self.root/'source';core.prepare(out);b=Fake();runner.technical(out,backend_override=b)
        generated=[]
        def malformed(ids,budget,capture_at=()):
            generated.append(1)
            return {'text':'malformed missing IDs'} if len(generated)%2 else ['invalid shape']
        b.generate=malformed
        runner.collect(out,backend_override=b)
        src=runner.Source(out);self.assertEqual(len(src.rows),32)
        self.assertTrue(all(r['status']=='invalid_return' and r['raw'] is not None for r in src.rows.values()))
        self.assertTrue(all(r['lengths']['output'] is None for r in src.rows.values()))
        runner.collect(out,backend_override=b);self.assertEqual(len(generated),32)
        report=reporting.behavioral_report(out)
        self.assertEqual(sum(v['invalid_or_unavailable'] for g in report['by_condition'].values() for v in g.values()),32)
