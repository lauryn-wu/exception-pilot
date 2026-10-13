import copy
import json
from pathlib import Path
import tempfile
import unittest

from exception_pilot.core import digest
from exception_continuation import core, runner, edits, analysis, events
from exception_continuation.backend import MockBackend


def annotate(out, col, positives=1):
    path = edits.review_export(out); review = json.loads(path.read_text())
    gold = {r['task']['id']: r['task']['expected'] for r in col['rows']}
    review['no_2a_selection_attested'] = True
    for i, a in enumerate(review['rows']):
        a.update(reviewed=True, false_missing=i < positives, reviewer='fixture',
                 justification='SOFTWARE FIXTURE ONLY', first_false_missing_certified=True,
                 semantic_certified=True, grammar_certified=True)
        if i < positives:
            old = 'Its verified class is missing.'; start = a['text'].index(old)
            a.update(statement_span=[start, start+len(old)], statement=old,
                     span=[start, start+len(old)], old=old, replacements={
                         'availability_repair': 'Its verified class is recorded.',
                         'meaning_control': 'Its verified class is absent.',
                         'value_repair': 'Its verified class is ' + gold[a['task_id']] + '.'})
    path.write_text(json.dumps(review))
    return edits.freeze_edits(out, path)


class FailedCut(MockBackend):
    def __init__(self, k, prompt=None): self.k, self.only_prompt = k, prompt

    def generate(self, ids, budget, capture_at=()):
        raw = super().generate(ids, budget, capture_at)
        prompt = self.decode(ids[:ids.index(1000000)])
        k = len(ids)-ids.index(1000000)-1
        if ('Verified class' in prompt and tuple(capture_at) == (0,) and k == self.k
                and (self.only_prompt is None or prompt == self.only_prompt)):
            raw['next_token_logits']['0'] = [9., -1., -2.]
        return raw


class V3Tests(unittest.TestCase):
    def test_failure_128_keeps_0_64_primary_and_failed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp); runner.prepare(out, 'selection'); b = FailedCut(128)
            runner.collect(out, backend_override=b)
            result = runner.measure(out, backend_override=b)
            for row in result['rows']:
                self.assertTrue(row['any_checkpoint_failed'])
                cuts = {c['k']: c for c in row['cuts']}
                self.assertTrue(cuts[0]['passed']); self.assertTrue(cuts[64]['passed'])
                self.assertFalse(cuts[128]['passed']); self.assertTrue(cuts[128]['exact_suffix_match'])
                self.assertNotIn('readout', cuts[128])
            report = analysis.analyze(out)['study_2a']
            self.assertEqual(report['primary']['worlds'], 12)
            self.assertEqual(report['checkpoint_replay_failures'][128], 24)
            self.assertEqual(report['coverage'][128]['measured'], 0)
            self.assertEqual(report['coverage'][64]['measured'], 24)
            # A persisted stray readout cannot override a failed validation flag.
            for row in result['rows']:
                row['cuts'][-1]['readout'] = row['cuts'][0]['readout']
            runner.sealed_write(out/'measurements.json', result)
            self.assertEqual(analysis.analyze(out)['study_2a']['coverage'][128]['measured'], 0)

    def test_failure_at_either_primary_cut_excludes_comparison(self):
        for k in (0, 64):
            with self.subTest(k=k), tempfile.TemporaryDirectory() as tmp:
                runner.prepare(tmp, 'selection'); b = FailedCut(k)
                runner.collect(tmp, backend_override=b); runner.measure(tmp, backend_override=b)
                report = analysis.analyze(tmp)['study_2a']
                self.assertEqual(report['primary']['worlds'], 0)
                self.assertEqual(report['coverage'][128]['measured'], 24)

    def test_one_missing_variant_excludes_whole_world_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection'); b = FailedCut(64)
            col = runner.collect(tmp, backend_override=b)
            b.only_prompt = next(r['task']['prompt'] for r in col['rows'] if r['task']['arm'] == 'visible')
            runner.measure(tmp, backend_override=b)
            self.assertEqual(analysis.analyze(tmp)['study_2a']['primary']['worlds'], 11)

    def test_invalid_and_truncated_arms_with_successful_replay(self):
        for truncated in (False, True):
            class InvalidRepair(MockBackend):
                def generate(self, ids, budget, capture_at=()):
                    raw = super().generate(ids, budget, capture_at)
                    if self.decode(ids).endswith('Its verified class is recorded.'):
                        tokens = self.encode(' malformed answer') if not truncated else [ord('x')]*budget
                        raw.update(tokens=tokens if truncated else tokens+[0], text=self.decode(tokens),
                                   stopped=not truncated, finish='length' if truncated else 'eos')
                    return raw
            with self.subTest(truncated=truncated), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp); runner.prepare(out, 'selection'); b = InvalidRepair()
                col = runner.collect(out, backend_override=b); annotate(out, col)
                data = edits.intervene(out, backend_override=b); row = data['rows'][0]
                self.assertTrue(row['unchanged_replay_passed'])
                self.assertIsNone(row['arms']['availability_repair']['score']['correct'])
                summary = analysis.analyze(out)['study_2b']; report = summary['coverage']
                self.assertEqual(report['replay_failures']['cases'], 0)
                c = report['per_arm']['availability_repair']
                self.assertEqual([c[x] for x in ('planned','attempted','returned','valid','invalid','truncated','missing')],
                                 [1,1,1,0,1,int(truncated),0])
                primary = summary['comparisons']['primary_availability_minus_meaning']
                bscore = int(row['arms']['meaning_control']['score']['correct'])
                self.assertEqual(primary['accuracy']['worlds'], 0)
                self.assertEqual(primary['full_plan_accuracy_bounds'], [-bscore, 1-bscore])
                self.assertEqual(summary['comparisons']['meaning_minus_unchanged']['accuracy']['worlds'], 1)
                self.assertNotIn('invalid_or_replay_failed', summary)

    def test_partial_failure_reports_attempts_missing_and_unknown_bounds(self):
        class BrokenRepair(MockBackend):
            def generate(self, ids, budget, capture_at=()):
                if self.decode(ids).endswith('Its verified class is recorded.'): raise RuntimeError('fixture')
                return super().generate(ids, budget, capture_at)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); runner.prepare(out,'selection'); b=BrokenRepair()
            col=runner.collect(out,backend_override=b); annotate(out,col)
            with self.assertRaises(RuntimeError): edits.intervene(out,backend_override=b)
            summary=analysis.analyze(out)['study_2b']
            c=summary['coverage']['per_arm']['availability_repair']
            self.assertEqual((c['attempted'],c['returned'],c['missing']), (1,0,1))
            self.assertEqual(c['reasons'], {'operation_error':1})
            self.assertEqual(summary['comparisons']['primary_availability_minus_meaning']['full_plan_accuracy_bounds'],[-1,1])

    def test_replay_and_tokenization_failures_have_separate_denominators(self):
        class BadEditEncoding(MockBackend):
            def encode(self, text):
                return [999] if text == 'Its verified class is recorded.' else super().encode(text)
        for b, replay_count, token_count in [(FailedCut(30),1,0),(BadEditEncoding(),0,1)]:
            with self.subTest(backend=type(b).__name__), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp); runner.prepare(out,'selection')
                col=runner.collect(out,backend_override=b); annotate(out,col)
                edits.intervene(out,backend_override=b)
                report=analysis.analyze(out)['study_2b']['coverage']
                self.assertEqual(report['replay_failures']['cases'],replay_count)
                self.assertEqual(report['replay_failures']['denominator'],1)
                self.assertEqual(report['eligibility']['tokenization_failures_after_freeze'],token_count)
                self.assertEqual(report['eligibility']['no_false_missing'],23)
                for c in report['per_arm'].values():
                    self.assertEqual((c['planned'],c['attempted'],c['returned'],c['missing']),(1,0,0,1))

    def test_changed_uninterrupted_event_reference_blocks_all_readouts(self):
        class ChangedReference(MockBackend):
            def generate(self, ids, budget, capture_at=()):
                raw=super().generate(ids,budget,capture_at)
                if 'Verified class' in self.decode(ids) and ids[-1] == 1000000 and len(capture_at) == 3:
                    raw['tokens']=[ord('!')]+raw['tokens'][1:]
                return raw
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); runner.prepare(out,'selection'); b=ChangedReference()
            col=runner.collect(out,backend_override=b); annotate(out,col,24); events.freeze_events(out)
            data=events.measure_events(out,backend_override=b)
            for row in data['rows']:
                for c in row['cuts']:
                    self.assertFalse(c['uninterrupted_matches_saved'])
                    self.assertFalse(c['passed']); self.assertNotIn('readout',c)

    def test_events_frozen_all_cases_late_boundaries_and_no_future_leakage(self):
        class LateStatement(MockBackend):
            script = 'Earlier reasoning. '*10 + MockBackend.script
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); runner.prepare(out,'selection'); b=LateStatement()
            col=runner.collect(out,backend_override=b); original=(out/'collection.json').read_bytes()
            manifest=annotate(out,col,24)
            with self.assertRaises(FileNotFoundError): events.measure_events(out,backend_override=b)
            frozen=events.freeze_events(out)
            self.assertEqual(len(frozen['rows']),24)
            self.assertTrue(all(c['k'] > 128 for r in frozen['rows'] for c in r['cuts']))
            data=events.measure_events(out,backend_override=b)
            self.assertFalse((out/'measurements.json').exists())
            self.assertFalse((out/'interventions.json').exists())
            self.assertTrue(all(c['passed'] for r in data['rows'] for c in r['cuts']))
            summary=analysis.analyze(out)['study_2a_events_secondary']
            self.assertTrue(summary['secondary']); self.assertEqual(summary['real_model_status'],'PENDING')
            self.assertEqual(summary['after_minus_before_statement']['worlds'],12)
            saved={r['task']['id']:r for r in col['rows']}
            ops=[runner.sealed_read(p) for p in (out/'operations').glob('*.json')]
            refs=[o for o in ops if o['id'].startswith('event/') and o['id'].endswith('/reference')]
            self.assertEqual(len(refs),24)
            for op in refs:
                tid=op['id'][6:-10]
                self.assertEqual(op['request']['input_ids'],saved[tid]['input_ids'])
            for op in ops:
                if not op['id'].startswith('event/') or '/readout/' not in op['id']: continue
                tid,k=op['id'][6:].rsplit('/readout/',1); req=op['request']
                self.assertEqual(req['prefix_ids'],saved[tid]['raw']['tokens'][:int(k)])
                self.assertEqual(op['result']['context_hash'],digest(req['input_ids']+req['prefix_ids']+b.encode('\nANSWER:')))
            self.assertEqual(original,(out/'collection.json').read_bytes())
            operation_count=len(ops); events.measure_events(out,backend_override=b)
            self.assertEqual(len(list((out/'operations').glob('*.json'))),operation_count)

    def test_event_unavailable_and_boundary_rules(self):
        b=MockBackend(); text='Earlier. Its verified class is missing.\nANSWER: D'
        tokens=b.encode(text)+[0]
        row=dict(raw=dict(text=text,tokens=tokens),boundaries=core.response_boundaries(b,tokens))
        start=text.index('Its'); end=text.index('\n')
        a=dict(false_missing=True,statement_span=[start,end],statement=text[start:end],span=[start,end])
        cuts=events.event_cuts(row,a,list(core.EVENTS))
        self.assertEqual([c['k'] for c in cuts],[start,end,end+1])
        # No stable boundary before the statement: retain explicit unavailable.
        row['boundaries']=[c for c in row['boundaries'] if c['char_end'] < start-1 or c['char_end'] > start]
        cut=events.event_cuts(row,a,['before_statement'])[0]
        self.assertFalse(cut['eligible']); self.assertIn('boundary',cut['reason'])
        neg=dict(a,false_missing=False)
        self.assertEqual(events.event_cuts(row,neg,['after_statement'])[0]['reason'],'reviewed_no_false_missing')
        row['raw']['text']=text.split('ANSWER:')[0]
        self.assertEqual(events.event_cuts(row,neg,['before_answer'])[0]['reason'],'no_answer_marker')

    def test_event_failure_retained_never_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); runner.prepare(out,'selection'); b=FailedCut(len('Its verified class is missing.'))
            col=runner.collect(out,backend_override=b); annotate(out,col,24); events.freeze_events(out)
            data=events.measure_events(out,backend_override=b)
            for row in data['rows']:
                cuts={c['event']:c for c in row['cuts']}
                self.assertFalse(cuts['after_statement']['passed'])
                self.assertNotIn('readout',cuts['after_statement'])
                self.assertIn('readout',cuts['before_statement'])
            summary=analysis.analyze(out)['study_2a_events_secondary']
            self.assertEqual(summary['after_minus_before_statement']['worlds'],0)
            self.assertEqual(summary['coverage']['after_statement']['measured'],0)

    def test_new_version_config_and_old_plan_not_reinterpreted(self):
        c=copy.deepcopy(core.DEFAULT_CONFIG); c['event_checkpoints']=[]
        self.assertEqual(core.make_plan('selection',c)['event_version'],'event-checkpoints-v1')
        c['event_checkpoints']=['before_answer','before_answer']
        with self.assertRaises(ValueError): core.validate_config(c)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); p=runner.prepare(out,'selection')
            p['protocol']='within-reasoning-continuation-v2'; p.pop('plan_hash'); p['plan_hash']=digest(p)
            (out/'plan.json').write_text(json.dumps(p)); before=(out/'plan.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'4baf414'): core.read_plan(out)
            self.assertEqual(before,(out/'plan.json').read_bytes())


if __name__ == '__main__': unittest.main()
