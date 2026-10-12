import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.core import digest
from exception_continuation import core, runner, edits, analysis
from exception_continuation.backend import MockBackend, readout, assert_plain_format
from exception_continuation.validation import compare_distributions, replay_check


class CalibratedFixture(MockBackend):
    identity = {'kind': 'SIMULATED_CALIBRATION_FIXTURE_NOT_EVIDENCE'}

    def __init__(self):
        plans = [core.make_plan('selection'), core.make_plan('confirmation', selection_lock={'fixture': True})]
        self.answers = {t['prompt']: t['expected'] if t['arm'] == 'direct' else t['pattern']
                        for p in plans for t in p['tasks']}

    def generate(self, ids, budget, capture_at=()):
        prompt = self.decode(ids[:ids.index(1000000)])
        self.script = MockBackend.script[:-1] + self.answers.get(prompt, 'A')
        return super().generate(ids, budget, capture_at)


def reviewed_file(out, collection, basis='predeclared_first_false_missingness'):
    path = edits.review_export(out)
    review = json.loads(path.read_text())
    review.update(selection_basis=basis, no_2a_selection_attested=True)
    byid = {r['task']['id']: r for r in collection['rows']}
    for i, a in enumerate(review['rows']):
        a.update(reviewed=True, false_missing=i == 0, reviewer='fixture', justification='SOFTWARE TEST ONLY',
                 semantic_certified=True, grammar_certified=True, first_false_missing_certified=True)
        if i == 0:
            old = 'Its verified class is missing.'
            a.update(statement_span=[0,len(old)], statement=old, span=[0,len(old)], old=old,
                replacements={'availability_repair':'Its verified class is recorded.',
                              'meaning_control':'Its verified class is absent.',
                              'value_repair':'Its verified class is ' + byid[a['task_id']]['task']['expected'] + '.'})
    path.write_text(json.dumps(review))
    return path


class V2Tests(unittest.TestCase):
    def test_numeric_tolerances_missing_and_nonfinite(self):
        t = core.DEFAULT_CONFIG['validation_tolerances']
        self.assertTrue(compare_distributions([0., -1.], [0., -1. + 1e-6], t)['passed'])
        self.assertFalse(compare_distributions([0., -1.], [0., -1. + .01], t)['passed'])
        for x in (None, [], ['nan'], [float('nan')], [float('inf')]):
            self.assertFalse(compare_distributions([0.], x, t)['passed'])
        original = {'tokens':[1,2], 'stopped':True, 'finish':'eos', 'next_token_logits':{'1':[0.,-1.]}}
        replay = {'tokens':[2], 'stopped':True, 'finish':'eos', 'next_token_logits':{'0':[0.,-2.]}}
        check = replay_check(original, replay, 1, t)
        self.assertTrue(check['exact_suffix_match']); self.assertFalse(check['passed'])

    def test_distribution_failure_blocks_collection_even_with_identical_tokens(self):
        class ChangedLogits(MockBackend):
            def generate(self, ids, budget, capture_at=()):
                r = super().generate(ids,budget,capture_at)
                if ids[-1] != 1000000: r['next_token_logits']['0'] = [0., -8., -9.]
                return r
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp,'selection')
            with self.assertRaisesRegex(ValueError,'validation FAILED'):
                runner.collect(tmp, backend_override=ChangedLogits())
            report = runner.sealed_read(Path(tmp)/'validation.json')
            check = report['records'][0]['replays'][0]
            self.assertTrue(check['exact_suffix_match']); self.assertFalse(check['distribution']['passed'])
            self.assertEqual(runner.sealed_read(Path(tmp)/'validation-status.json')['real_model_status'], 'PENDING')

    def test_exact_probe_inputs_cues_and_original_immutability(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp); runner.prepare(out,'selection')
            collection = runner.collect(out,mock=True)
            original = (out/'collection.json').read_bytes()
            result = runner.measure(out,mock=True)
            byid = {r['task']['id']:r for r in collection['rows']}
            operations = [runner.sealed_read(p) for p in (out/'operations').glob('*.json')]
            # Exactly one uninterrupted scientific generation per original task.
            self.assertEqual(sum(o['id'].startswith('trajectory/') for o in operations),48)
            for o in operations:
                if not o['id'].startswith('readout/'): continue
                tid, k, ci = o['id'][len('readout/'):].rsplit('/',2)
                r = byid[tid]; req = o['request']; k = int(k)
                self.assertEqual(req['input_ids'],r['input_ids'])
                self.assertEqual(req['prefix_ids'],r['raw']['tokens'][:k])
                self.assertEqual(req['cue_text'],core.DEFAULT_CONFIG['readout_cues'][int(ci[3:])])
                self.assertNotIn('ANSWER:',MockBackend().decode(req['prefix_ids']))
                expected = req['input_ids']+req['prefix_ids']+MockBackend().encode(req['cue_text'])
                self.assertEqual(o['result']['context_hash'],digest(expected))
            for row in result['rows']:
                self.assertEqual([c['k'] for c in row['cuts']],[0,32,64,128])
                for cut in row['cuts']:
                    self.assertEqual(len(cut['readouts']),2 if cut['k'] in (0,64) else 1)
            self.assertEqual(original,(out/'collection.json').read_bytes())
            report = analysis.analyze(out)
            self.assertIn('wrong/k64',report['study_2a']['by_final_outcome_descriptive'])
            self.assertIn('correct/k64',report['study_2a']['by_final_outcome_descriptive'])
            self.assertEqual(set(report['study_2a']['cue_sensitivity']),{'cue1/k0','cue1/k64'})

    def test_candidate_whitespace_and_bad_tokenization(self):
        b=MockBackend(); p=b.prompt('table'); r=readout(b,p,[], 'A','B')
        for label in 'ABC':
            self.assertEqual(r['candidate_texts'][label],' '+label+'\n')
            self.assertEqual(b.decode(r['scores'][label]['tokens']),' '+label+'\n')
        class DropsSpace(MockBackend):
            def encode(self,text): return super().encode(text.lstrip(' '))
        with self.assertRaisesRegex(ValueError,'Candidate tokens'):
            readout(DropsSpace(),p,[],'A','B')

    def test_statement_cut_independent_of_fixed_checkpoints_and_preserves_preceding_text(self):
        b=MockBackend(); preceding='INITIAL: A\n'+'Original earlier reasoning. '*6
        statement='Its verified class is missing.'
        text=preceding+statement+' More reasoning.\nANSWER: B'
        tokens=b.encode(text)+[0]
        row={'raw':{'text':text,'tokens':tokens},'boundaries':core.response_boundaries(b,tokens)}
        start=len(preceding); a={'statement_span':[start,start+len(statement)],'statement':statement,
            'span':[start+len('Its verified class is '),start+len(statement)-1], 'old':'missing',
            'reviewer':'fixture','justification':'table','semantic_certified':True,
            'replacements':{'availability_repair':'recorded','meaning_control':'absent','value_repair':'B'}}
        cut,reason=core.statement_cut(row,a)
        self.assertIsNone(reason); self.assertGreater(cut['k'],128)
        self.assertEqual(cut['prefix'],preceding+statement)
        arms=core.edit_prefix(cut['prefix'],a,'B')
        for arm in arms.values(): self.assertTrue(arm.startswith(preceding))
        self.assertEqual(arms['availability_repair'],preceding+'Its verified class is recorded.')
        self.assertEqual(core.letters(arms['availability_repair']),core.letters(cut['prefix']))
        merged=copy.deepcopy(row)
        merged['boundaries']=[{'k':cut['k']+5,'char_end':len(cut['prefix'])+5,'roundtrip_exact':True}]
        self.assertEqual(core.statement_cut(merged,a)[1],'no_token_boundary_immediately_after_statement')
        a.update(statement_span=[0,10],statement=text[:10],span=[0,7])
        with self.assertRaisesRegex(ValueError,'preliminary entry'): core.statement_cut(row,a)

    def test_2b_without_2a_fresh_natural_suffixes_and_pending_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); runner.prepare(out,'selection'); col=runner.collect(out,mock=True)
            original=(out/'collection.json').read_bytes()
            manifest=edits.freeze_edits(out,reviewed_file(out,col))
            self.assertFalse((out/'measurements.json').exists())
            result=edits.intervene(out,mock=True); case=result['rows'][0]; k=manifest['cases'][0]['k']
            row=next(r for r in col['rows'] if r['task']['id']==case['task_id'])
            self.assertEqual(k,len('Its verified class is missing.'))
            self.assertEqual(result['real_model_status'],'PENDING')
            self.assertFalse(case['same_response_validated'])
            ops=[runner.sealed_read(p) for p in (out/'operations').glob('*.json')]
            generated=[o for o in ops if o['id'].startswith('edit/') and o['id'].endswith('/continuation')]
            self.assertEqual(len(generated),4)
            for op in generated:
                arm=op['id'].rsplit('/',2)[1]; saved=case['arms'][arm]
                self.assertEqual(op['request']['input_ids'],row['input_ids']+saved['prefix_ids'])
                self.assertEqual(op['request']['budget'],512-k)
                self.assertNotIn('ANSWER:',saved['prefix_text'])
                self.assertEqual(saved['full_tokens'],saved['prefix_ids']+saved['raw']['tokens'])
                self.assertIn('delta',saved['changed_tokens'])
                if arm!='unchanged':
                    self.assertEqual(saved['raw']['text'],'\nANSWER: A')
                    self.assertNotEqual(saved['raw']['tokens'],row['raw']['tokens'][k:])
            self.assertEqual(original,(out/'collection.json').read_bytes())
            summary=analysis.analyze(out)
            self.assertEqual(summary['study_2a']['status'],'PENDING')
            self.assertFalse(summary['study_2b']['validated_same_response_interventions'])

    def test_calibration_confirmation_and_discovery_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'selection'; conf=Path(tmp)/'confirmation'; b=CalibratedFixture()
            runner.prepare(out,'selection'); runner.collect(out,backend_override=b)
            p=runner.prepare(conf,'confirmation',core.DEFAULT_CONFIG,out,'SOFTWARE FIXTURE ONLY')
            self.assertTrue(p['selection_lock']['calibration']['passed'])
            self.assertEqual(p['selection_lock']['mode'],'SIMULATED')
            col=runner.collect(conf,backend_override=b)
            review=reviewed_file(conf,col,'2A_informed_discovery')
            with self.assertRaisesRegex(ValueError,'discovery only'): edits.freeze_edits(conf,review)
            data=json.loads(review.read_text()); data['selection_basis']='predeclared_first_false_missingness'
            data['no_2a_selection_attested']=False; review.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'attestation'): edits.freeze_edits(conf,review)
            data['no_2a_selection_attested']=True; review.write_text(json.dumps(data))
            self.assertEqual(len(edits.freeze_edits(conf,review)['cases']),1)
            fake_live=CalibratedFixture(); fake_live.simulated=False
            with self.assertRaises(ValueError): runner.Session(conf,p,fake_live)

    def test_invalid_final_trajectories_still_measured(self):
        class InvalidFinal(MockBackend): script=MockBackend.script[:-1]+'D'
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp,'selection'); runner.collect(tmp,backend_override=InvalidFinal())
            measurements=runner.measure(tmp,backend_override=InvalidFinal())
            self.assertEqual(len(measurements['rows']),24)
            summary=analysis.analyze(tmp)
            self.assertEqual(summary['baseline']['visible']['valid'],0)
            self.assertIn('invalid/k64',summary['study_2a']['by_final_outcome_descriptive'])

    def test_validation_command_optin_and_pending_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp,'selection')
            with patch('exception_continuation.runner.LocalBackend',side_effect=AssertionError('loaded')):
                with self.assertRaises(ValueError): runner.validate_run(tmp)
            self.assertEqual(analysis.analyze(tmp)['real_model_validation'],'PENDING')
            self.assertTrue(runner.validate_run(tmp,mock=True)['passed'])
            self.assertEqual(runner.sealed_read(Path(tmp)/'validation-status.json')['real_model_status'],'PENDING')

    def test_legacy_version_and_unsupported_thinking(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=runner.prepare(tmp,'selection'); p['protocol']='within-reasoning-continuation-v1'
            p.pop('plan_hash'); p['plan_hash']=digest(p)
            path=Path(tmp)/'plan.json'; path.write_text(json.dumps(p)); before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'Legacy protocol'): core.read_plan(tmp)
            self.assertEqual(path.read_bytes(),before)
        c=copy.deepcopy(core.DEFAULT_CONFIG); c['chat_template_kwargs']={'enable_thinking':True}
        with self.assertRaisesRegex(ValueError,'visible assistant'): core.validate_config(c)
        for s in ('<think>unfinished','[THINK]thinking','<|channel|>analysis'):
            with self.assertRaisesRegex(ValueError,'unsupported'): assert_plain_format(s)


if __name__=='__main__': unittest.main()
