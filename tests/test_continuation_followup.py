import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.core import digest
from exception_continuation import core, runner, edits, analysis
from exception_continuation.backend import MockBackend, readout


def annotate(path, collection, positive_count=1):
    review = json.loads(path.read_text())
    gold = {r['task']['id']: r['task']['expected'] for r in collection['rows']}
    for i, a in enumerate(review['rows']):
        a.update(reviewed=True, false_missing=i < positive_count, reviewer='offline-test',
                 justification='SOFTWARE FIXTURE: compare exact target row',
                 first_false_missing_certified=True, semantic_certified=True, grammar_certified=True)
        if i < positive_count:
            old = 'Its verified class is missing.'
            a.update(statement_span=[0, len(old)], statement=old, span=[0, len(old)], old=old, replacements={
                'availability_repair': 'Its verified class is recorded.',
                'meaning_control': 'Its verified class is absent.',
                'value_repair': 'Its verified class is recorded as ' + gold[a['task_id']] + '.'})
    path.write_text(json.dumps(review))
    return review


class BadReplay(MockBackend):
    def generate(self, ids, budget, capture_at=()):
        result = super().generate(ids, budget, capture_at)
        if ids[-1] != 1000000:
            result['tokens'] = [ord('!')] + result['tokens']; result['text'] = self.decode(result['tokens'])
        return result


class ScientificBadReplay(MockBackend):
    def generate(self, ids, budget, capture_at=()):
        result = super().generate(ids, budget, capture_at)
        if 'Verified class' in self.decode(ids) and ids[-1] != 1000000:
            result['tokens'] = [ord('!')] + result['tokens']
        return result


class ContinuationTests(unittest.TestCase):
    def test_design_and_phase_separation(self):
        selection = core.make_plan('selection')
        confirm = core.make_plan('confirmation', selection_lock={'mock_for_design_test': True})
        self.assertEqual(len(selection['tasks']), 48)
        self.assertEqual(len(confirm['tasks']), 96)
        a = {x['id'] for w in selection['worlds'] for x in w['items']}
        b = {x['id'] for w in confirm['worlds'] for x in w['items']}
        self.assertFalse(a & b)
        self.assertEqual({t['target_row'].split('|')[1].strip() == t['target_plate'] for t in confirm['tasks']}, {True})
        with self.assertRaises(ValueError): core.make_plan('confirmation')

    def test_requires_explicit_opt_in_before_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection')
            with patch('exception_continuation.runner.LocalBackend', side_effect=AssertionError('loaded')):
                with self.assertRaises(ValueError): runner.collect(tmp)
                with self.assertRaises(ValueError): runner.collect(tmp, live=True, mock=True)

    def test_technical_replay_failure_blocks_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection')
            with self.assertRaises(ValueError): runner.collect(tmp, mock=True, backend_override=BadReplay())
            self.assertFalse((Path(tmp)/'collection.json').exists())
            self.assertFalse(runner.sealed_read(Path(tmp)/'validation.json')['passed'])

    def test_scientific_replay_failure_blocks_only_affected_readouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection')
            backend = ScientificBadReplay()
            runner.collect(tmp, mock=True, backend_override=backend)
            r = runner.measure(tmp, mock=True, backend_override=backend)
            self.assertTrue(all(not row['replay_passed'] for row in r['rows']))
            self.assertTrue(all('readout' in row['cuts'][0] for row in r['rows']))
            self.assertFalse(any('readout' in c for row in r['rows'] for c in row['cuts'][1:]))

    def test_predefined_cuts_before_answer_and_no_new_turn(self):
        b = MockBackend()
        cuts = core.eligible_cuts(b, b.encode('ANSWER: A') + [0])
        self.assertTrue(cuts[0]['eligible'])
        self.assertFalse(any(c['eligible'] for c in cuts[1:]))
        ids = b.prompt('user')
        raw = b.generate(ids, 512)
        for c in core.eligible_cuts(b, raw['tokens']):
            if not c['eligible']: continue
            combined = ids + raw['tokens'][:c['k']]
            self.assertEqual(combined.count(1000000), 1)
            replay = b.generate(combined, 512-c['k'])
            self.assertEqual(replay['tokens'], raw['tokens'][c['k']:])

    def test_multi_token_readout_is_normalized_candidate_score(self):
        b = MockBackend(); ids = b.prompt('question'); prefix = b.encode('reason')
        frozen = ids.copy(), prefix.copy()
        r = readout(b, ids, prefix, 'B', 'A')
        self.assertAlmostEqual(sum(r['normalized'].values()), 1)
        self.assertEqual(len(r['scores']['A']['tokens']), 3)
        self.assertEqual(r['scores']['B']['logprob'], sum(r['scores']['B']['token_logprobs']))
        self.assertEqual((ids, prefix), frozen)
        self.assertEqual(r['context_hash'], digest(ids + prefix + b.encode('\nANSWER:')))

    def test_repair_no_extra_letter_and_span_controls(self):
        text = MockBackend.script[:32]; old = 'Its verified class is missing.'
        a = dict(span=[0, len(old)], old=old, reviewer='test', justification='table', semantic_certified=True,
                 replacements={'availability_repair': 'Its class is recorded.', 'meaning_control': 'Its verified class is absent.',
                               'value_repair': 'Its class is B.'})
        changed = core.edit_prefix(text, a, 'B')
        self.assertEqual(changed['unchanged'], text)
        self.assertEqual(core.letters(changed['availability_repair']), core.letters(text))
        a['replacements']['availability_repair'] = 'Its class is B.'
        with self.assertRaises(ValueError): core.edit_prefix(text, a, 'B')
        a['replacements']['availability_repair'] = 'Recorded.'; a['old'] = 'not the exact old text'
        with self.assertRaises(ValueError): core.edit_prefix(text, a, 'B')

    def test_full_mock_pipeline_edits_freeze_and_confirmation_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'selection'; confirm = Path(tmp)/'confirm'
            runner.prepare(out, 'selection', core.DEFAULT_CONFIG)
            collection = runner.collect(out, mock=True)
            runner.measure(out, mock=True)
            review = edits.review_export(out)
            with self.assertRaises(ValueError): edits.freeze_edits(out, review)
            annotate(review, collection)
            plan = edits.freeze_edits(out, review)
            self.assertEqual(len(plan['cases']), 1)
            self.assertEqual(plan['cases'][0]['k'], len('Its verified class is missing.'))
            original_bytes = (out/'collection.json').read_bytes()
            response = edits.intervene(out, mock=True)
            case = response['rows'][0]
            self.assertTrue(case['unchanged_replay_passed'])
            self.assertEqual(set(case['arms']), {'unchanged', 'availability_repair', 'meaning_control', 'value_repair'})
            self.assertEqual(original_bytes, (out/'collection.json').read_bytes())
            result = analysis.analyze(out)
            self.assertEqual(result['mode'], 'SIMULATED')
            self.assertEqual(result['interventions']['planned_cases'], 1)
            self.assertEqual(result['real_model_validation'], 'PENDING')
            self.assertFalse(result['study_2b']['validated_same_response_interventions'])
            self.assertEqual(result['longitudinal_primary_64_minus_0']['worlds'], 12)
            with self.assertRaises(ValueError): edits.freeze_edits(out, review)
            with self.assertRaisesRegex(ValueError, 'behavioral calibration'):
                runner.prepare(confirm, 'confirmation', core.DEFAULT_CONFIG, out, 'SOFTWARE TEST ONLY')

    def test_raw_invalid_truncation_and_corruption_retained(self):
        self.assertIsNone(core.final_score('ANSWER: A', False, 'A')['answer'])
        self.assertIsNone(core.final_score('ANSWER: D', True, 'A')['answer'])
        with tempfile.TemporaryDirectory() as tmp:
            p = runner.prepare(tmp, 'selection'); session = runner.Session(tmp, p, MockBackend())
            def broken(): raise RuntimeError('test failure')
            with self.assertRaises(RuntimeError): session.operation('fails', {'tokens': [3]}, broken)
            path = next((Path(tmp)/'operations').glob('*.json'))
            self.assertEqual(runner.sealed_read(path)['status'], 'error')
            with self.assertRaises(ValueError): runner.Session(tmp, p, MockBackend())
            value = json.loads(path.read_text()); value['status'] = 'returned'; path.write_text(json.dumps(value))
            with self.assertRaises(ValueError): runner.sealed_read(path)

    def test_roundtrip_difference_is_not_silently_retokenized(self):
        class DifferentEncoding(MockBackend):
            def encode(self, text):
                if text.startswith('Its verified class') and len(text) == 32: return [777]
                return super().encode(text)
        # Token slicing remains exact even if re-encoding decoded body would differ.
        b = DifferentEncoding(); raw = MockBackend().generate(MockBackend().prompt('user'), 512)
        cuts = core.eligible_cuts(b, raw['tokens'])
        cut = next(c for c in cuts if c['k'] == 32)
        self.assertNotEqual(b.encode(cut['prefix']), raw['tokens'][:32])
        self.assertEqual(cut['prefix'], MockBackend.script[:32])


if __name__ == '__main__': unittest.main()
