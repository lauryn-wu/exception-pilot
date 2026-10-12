import collections
import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_ordering import core, runner, analysis


class CharacterTokenizer:
    """Test offsets ONLY; never presented as real model tokenization."""
    def encode(self, text, add_special_tokens=False):
        class Encoded:
            ids = list(map(ord, text))
            offsets = [(i, i+1) for i in range(len(text))]
        return Encoded()


class OrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan()

    def test_design_inventory_distance_and_balance(self):
        self.assertEqual(len(self.plan['tasks']), 7680)
        roles = collections.Counter(tuple(w['roles']) for w in self.plan['worlds'])
        self.assertEqual(set(roles.values()), {4})
        for w in self.plan['worlds']:
            for p in core.SLOTS:
                counts = collections.defaultdict(collections.Counter)
                for k in range(20):
                    order = core.order_for(w, p, k)
                    self.assertEqual(sorted(order), list(range(10)))
                    self.assertEqual(order[4], w['target'])
                    self.assertEqual(sorted(abs(i-4) for i in core.SLOTS[p]), [1, 2, 3, 4])
                    for slot, i in enumerate(order): counts[i][slot] += 1
                for i in w['support']: self.assertEqual(set(counts[i].values()), {5})
                for i in w['other']: self.assertEqual(set(counts[i].values()), {4})
            for v in (0, 1):
                texts = [core.render(w, v, p, 7, 'direct')[0] for p in core.SLOTS]
                inventories = [sorted(line for line in t.splitlines() if line.startswith('| ')) for t in texts]
                self.assertTrue(all(i == inventories[0] for i in inventories))

    def test_row_equality_does_not_imply_token_equality(self):
        w = self.plan['worlds'][0]
        metrics = []
        for p in core.SLOTS:
            text, spans, _ = core.render(w, 0, p, 0, 'direct')
            a = core.token_audit(text, spans, CharacterTokenizer())
            self.assertEqual(text[slice(*spans['class'])], w['roles'][0])
            metrics.append(a['token_spans']['plate'][0])
        self.assertGreater(len(set(metrics)), 1)
        self.assertEqual(core.token_audit(text, spans)['status'], 'UNMEASURED')

    def test_complete_matched_prompt_invariants(self):
        groups = collections.defaultdict(list)
        for task in self.plan['tasks']:
            groups[task['world'], task['variant'], task['rotation']].append(task)
        self.assertEqual(len(groups), 960)
        for tasks in groups.values():
            inventories, targets, queries, counts = [], [], [], []
            for t in tasks:
                text = t['request']['messages'][0]['content']
                records = [line for line in text.splitlines() if line.startswith('| ')][1:]
                inventories.append(sorted(records))
                targets.append(text[slice(*t['position']['spans']['row'])])
                queries.append(text.split('\nLicense plate: ', 1)[1].rsplit('\n', 1)[0])
                counts.append(collections.Counter(row.split('|')[-2].strip() for row in records))
                self.assertEqual(len(records), 10)
                self.assertEqual(records[4], targets[-1])
                self.assertEqual(t['row'], 5)
                self.assertEqual(targets[-1].split('|')[-2].strip(), t['expected'])
            for values in (inventories, targets, queries, counts):
                self.assertTrue(all(value == values[0] for value in values))
            self.assertEqual({t['placement'] for t in tasks}, set(core.SLOTS))
            self.assertEqual({t['arm'] for t in tasks}, {'direct', 'visible'})

    def test_offset_report_retains_lengths_and_nonmatches(self):
        class WordFixture:
            # Synthetic test tokenizer, NOT the deployed model's tokenizer.
            def encode(self, text, add_special_tokens=False):
                offsets = [m.span() for m in re.finditer(r'\w+|[^\w\s]', text)]
                return type('Encoded', (), {'offsets': offsets, 'ids': list(range(len(offsets)))})()
        first = self.plan['tasks'][0]
        tasks = copy.deepcopy([t for t in self.plan['tasks'] if all(t[k] == first[k] for k in ('world', 'variant', 'rotation'))])
        for t in tasks:
            text = t['request']['messages'][0]['content']
            t['position'] = core.token_audit(text, t['position']['spans'], WordFixture())
            encoded = WordFixture().encode(text)
            self.assertEqual(t['position']['tokens'], len(encoded.ids))
            for name, (a, b) in t['position']['spans'].items():
                overlap = [i for i, (s, e) in enumerate(encoded.offsets) if s < b and e > a]
                self.assertEqual(t['position']['token_spans'][name], [overlap[0], overlap[-1]+1])
        report = runner.position_report(dict(tasks=tasks, tokenizer={'SOFTWARE_FIXTURE': True}))
        entry = report['comparisons'][0]
        self.assertEqual(report['measured'], 1)
        expected = len({tuple(t['position']['token_spans'][s][0] for s in ('plate', 'class')) for t in tasks if t['placement'] in ('before', 'after')}) == 1
        self.assertEqual(entry['before_after_match'], expected)
        self.assertGreater(len({p['tokens'] for p in entry['positions'].values()}), 1)
        # A class-token shift alone must defeat an exact match, even if plate starts match.
        for t in tasks:
            t['position']['token_spans']['plate'] = [100, 104]
            t['position']['token_spans']['class'] = [120, 121]
        next(t for t in tasks if t['placement'] == 'after')['position']['token_spans']['class'] = [121, 122]
        self.assertFalse(runner.position_report(dict(tasks=tasks, tokenizer={}))['comparisons'][0]['before_after_match'])

    def test_unmeasured_report_does_not_assert_token_control(self):
        report = runner.position_report(self.plan)
        self.assertEqual(report['measured'], 0)
        self.assertEqual(report['matched_before_after'], 0)
        self.assertTrue(all(e['before_after_match'] is None and e['quartet_match'] is None for e in report['comparisons']))
        self.assertTrue(all(t['position']['tokens'] is None for t in self.plan['tasks']))

    def test_scoring_retains_invalid_and_truncation(self):
        task = self.plan['tasks'][0]
        for text, complete in [('ANSWER: D', True), ('ANSWER: A', False), ('ANSWER: A\nANSWER: B', False)]:
            self.assertFalse(core.score(task, {'text': text, 'complete': complete})['valid'])
        self.assertFalse(core.score(dict(task, arm='direct'), {'text': 'Reason\nANSWER: A', 'complete': True})['adherence'])

    def test_primary_known_values_bounds_and_contrast_specific_coverage(self):
        records = {}
        for t in self.plan['tasks']:
            if t['placement'].startswith('both'): continue
            correct = not (t['placement'] == 'after' and t['arm'] == 'visible')
            records[t['id']] = {'score': {'correct': correct}}
        c = analysis.contrast(self.plan, records, analysis.COEFFICIENTS['primary_harm_after_minus_before'])
        self.assertAlmostEqual(c['estimate'], 1)
        self.assertEqual(c['complete_worlds'], 24)
        missing = analysis.contrast(self.plan, {}, analysis.COEFFICIENTS['primary_harm_after_minus_before'])
        self.assertAlmostEqual(missing['full_plan_bounds'][0], -2)
        self.assertAlmostEqual(missing['full_plan_bounds'][1], 2)

    def test_opt_in_mock_isolation_and_journal_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp)
            with self.assertRaises(ValueError): runner.run(tmp, max_calls=1)
            with self.assertRaises(ValueError): runner.run(tmp, live=True, max_calls=1)
            with patch('exception_ordering.runner.complete', side_effect=AssertionError('network')):
                runner.run(tmp, mock=True, max_calls=2)
                runner.run(tmp, mock=True, max_calls=2)
            entries = runner.journal(tmp, core.read_plan(tmp))
            self.assertEqual(len(entries), 4)
            f = next((Path(tmp)/'attempts').glob('*.json'))
            e = json.loads(f.read_text()); e['response']['text'] = 'tampered'; f.write_text(json.dumps(e))
            with self.assertRaises(ValueError): runner.journal(tmp, self.plan)

    def test_identity_drift_and_invalid_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp)
            # Test transport through live guard without credentials or actual HTTP.
            p = core.read_plan(tmp); p['tokenizer'] = {'test': True}
            with patch('exception_ordering.runner.read_plan', return_value=p):
                response = {'model': core.CONFIG['model'], 'complete': True, 'text': 'INVALID', 'raw_response': {'x': 1}}
                runner.run(tmp, live=True, accept_provenance=True, max_calls=1, transport=lambda *_: response)
                e = runner.journal(tmp, p)[0]
                self.assertEqual(e['status'], 'returned'); self.assertFalse(e['score']['valid'])
                response = {'model': 'wrong', 'complete': True, 'text': 'ANSWER: A'}
                with self.assertRaises(ValueError):
                    runner.run(tmp, live=True, accept_provenance=True, max_calls=1, transport=lambda *_: response)
                with self.assertRaises(ValueError): runner.run(tmp, live=True, accept_provenance=True, max_calls=1)


if __name__ == '__main__': unittest.main()
