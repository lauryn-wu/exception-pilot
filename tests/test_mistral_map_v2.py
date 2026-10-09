"""Whitespace amendment: retained failures, zero-call migration, exact resume."""

from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_mistral_map import core as v1_core, runner as v1_runner
from exception_mistral_map_v2 import core, runner, analysis
from test_mistral_map import ROOT, make_parent, raw


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(path).rglob('*') if p.is_file()}


class WhitespaceAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.source = make_parent(Path(cls.temp.name) / 'source')
        cls.v1_config = v1_core.load_config(ROOT / 'configs/mistral_map.json')
        cls.config = core.load_config(ROOT / 'configs/mistral_map_v2.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def stopped_v1(self, root):
        out = Path(root) / 'v1'
        plan = v1_runner.prepare(self.v1_config, out, self.source)
        queue = iter(plan['tasks'])
        calls = 0

        def complete(config, payload):
            nonlocal calls
            calls += 1
            task = next(queue)
            meta = v1_core.task_meta(plan, task)
            if task['family'] == 'capability':
                text = 'Cobalt Maple Lantern'
            else:
                answer = meta['expected'] if task['arm'] == 'direct' else meta['pattern_label']
                text = ('Verified class: MISSING (to be predicted).\n' if task['arm'] == 'visible' else '')
                text += 'ANSWER:' + ('\n' if calls == 6 else ' ') + answer
            return raw(text, 'original-' + str(calls))

        with redirect_stdout(io.StringIO()):
            result = v1_runner.run(self.v1_config, out, 49, mock=True, complete_fn=complete)
        self.assertEqual((result['stopped'], result['attempts_total']), ('sampling_check_failed', 6))
        return out, plan

    def test_whitespace_rule_accepts_each_label_without_using_gold_or_pattern(self):
        for arm in ('direct', 'visible', 'map'):
            for label in 'ABC':
                for separator in (' ', '\n', '\r\n', '\t', '  ', '\n\n'):
                    for expected in 'ABC':
                        task = {'family': 'map' if arm == 'map' else 'base', 'arm': arm}
                        prefix = 'Retained reasoning.\n' if arm == 'map' else ''
                        lead = prefix or ('Fresh reasoning.\n' if arm == 'visible' else '')
                        text = lead + 'ANSWER:' + separator + label + '\n'
                        meta = {'expected': expected, 'pattern_label': 'A', 'prefix_text': prefix}
                        result = core.score_response(task, raw(text), meta)
                        self.assertEqual(result['answer'], label)
                        self.assertEqual(result['status'], 'complete')
                        self.assertEqual(result['strict_v1_score'], v1_core.score_response(task, raw(text), meta))

    def test_ambiguous_or_decorated_endings_and_missing_reasoning_stay_invalid(self):
        endings = ['ANSWER:\nA or B', 'ANSWER:\nA\nB', 'ANSWER:\nA because it matches',
                   '**ANSWER: A**', 'ANSWER:\na', 'ANSWER:\nD', 'A', 'ANSWER:',
                   'ANSWER:\nA\nMore commentary', 'ANSWER:A']
        for ending in endings:
            result = core.score_response({'family': 'base', 'arm': 'visible'}, raw('Reasoning.\n' + ending), {})
            self.assertEqual(result['status'], 'invalid', ending)
        for text in ['ANSWER: A', 'ANSWER:\nA']:
            result = core.score_response({'family': 'base', 'arm': 'visible'}, raw(text), {})
            self.assertEqual(result['invalid_reason'], 'reasoning_text_missing')
        result = core.score_response({'family': 'base', 'arm': 'direct'}, raw('Reasoning.\nANSWER:\nA'), {})
        self.assertEqual(result['invalid_reason'], 'direct_not_answer_only')

    def test_prefix_capability_and_provider_guards_not_relaxed(self):
        task, meta = {'family': 'map', 'arm': 'map'}, {'prefix_text': 'Exact prefix.\n'}
        bad = core.score_response(task, raw('Changed prefix.\nANSWER:\nA'), meta)
        self.assertEqual(bad['invalid_reason'], 'prefix_mismatch')
        bad = core.score_response(task, raw('Exact prefix.\nANSWER:\nA', finish='length'), meta)
        self.assertEqual(bad['invalid_reason'], 'incomplete_finish_reason')
        bad = core.score_response({'family': 'capability', 'arm': 'capability'}, raw('Cobalt\nMaple Lantern'), {})
        self.assertEqual(bad['status'], 'invalid')

    def test_migration_preserves_bytes_all_requests_and_all_six_responses_offline(self):
        with tempfile.TemporaryDirectory() as root:
            source, old_plan = self.stopped_v1(root)
            before = hashes(source)
            output = Path(root) / 'v2'
            with patch.object(runner.provider, 'credential', side_effect=AssertionError('credential')), \
                 patch.object(runner.provider, 'complete', side_effect=AssertionError('network')):
                plan = runner.migrate(self.config, source, output)
            self.assertEqual(hashes(source), before)
            _, _, old = v1_runner.read_run(source)
            _, _, new = runner.read_run(output)
            self.assertEqual(len(new), 6)
            for a, b in zip(old, new):
                self.assertEqual(a['response'], b['response'])
                self.assertEqual(a['request'], b['request'])
                self.assertEqual(a['started_at'], b['started_at'])
                self.assertEqual((source / 'attempts' / f"{a['attempt']:06d}.json").read_bytes(),
                                 (output / 'source-map-v1/attempts' / f"{a['attempt']:06d}.json").read_bytes())
            for task in plan['tasks']:
                self.assertEqual(core.request_for(plan, task), v1_core.request_for(old_plan, task))
            self.assertEqual(new[-1]['status'], 'complete')
            self.assertEqual(new[-1]['strict_v1_score']['invalid_reason'], 'final_answer_unparseable')
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(report['previous_v1_result']['analysis_status'], 'sampling_check_failed_stop')
            self.assertEqual(report['analysis_status'], 'pending_sampling_check')
            self.assertEqual(report['whitespace_normalized_responses'], 1)
            self.assertEqual(report['new_attempts'], 0)
            self.assertEqual(runner.migrate(self.config, source, output), plan)
            self.assertEqual(len(runner.read_run(output)[2]), 6)

    def test_resume_makes_only_43_new_check_calls_and_does_not_start_mapping(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v1(root)
            output = Path(root) / 'v2'
            runner.migrate(self.config, source, output)
            result = runner.run(self.config, output, 1107, resume=True, mock=True)
            self.assertEqual((result['stopped'], result['calls_this_invocation'], result['attempts_total']),
                             ('sampling_check_passed', 43, 49))
            again = runner.run(self.config, output, 1107, resume=True, mock=True)
            self.assertEqual(again['calls_this_invocation'], 0)
            result = runner.run(self.config, output, 2, stage='map', resume=True, mock=True)
            self.assertEqual(result['calls_this_invocation'], 2)
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(report['analysis_status'], 'mapping_incomplete')
            self.assertEqual(report['imported_attempts'], 6)
            self.assertEqual(report['new_attempts'], 45)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, resume=True, mock=False)

    def test_imported_journal_and_original_snapshot_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source, _ = self.stopped_v1(root)
            output = Path(root) / 'v2'
            runner.migrate(self.config, source, output)
            path = output / 'attempts/000006.json'
            original = path.read_bytes()
            data = json.loads(original)
            data['answer'] = 'B' if data['answer'] != 'B' else 'C'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runner.read_run(output)
            path.write_bytes(original)
            snapshot = output / 'source-map-v1/attempts/000006.json'
            snapshot.write_bytes(snapshot.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                runner.read_run(output)

    def test_later_invalid_answer_is_retained_and_not_retried(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v1(root)
            output = Path(root) / 'v2'
            runner.migrate(self.config, source, output)
            result = runner.run(self.config, output, 10, resume=True, mock=True,
                                complete_fn=lambda cfg, payload: raw('No answer.', 'new-invalid'))
            self.assertEqual(result['stopped'], 'sampling_check_failed')
            again = runner.run(self.config, output, 10, resume=True, retry_errors=True, mock=True)
            self.assertEqual(again['calls_this_invocation'], 0)
            self.assertEqual(again['attempts_total'], 7)

    def test_accuracy_gate_still_fails_when_direct_visible_gap_is_too_small(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v1(root)
            output = Path(root) / 'v2'
            plan = runner.migrate(self.config, source, output)
            queue = iter(plan['tasks'][6:49])
            def correct(cfg, payload):
                task = next(queue)
                answer = core.task_meta(plan, task)['expected']
                return raw(('Reasoning.\n' if task['arm'] == 'visible' else '') + 'ANSWER:\n' + answer, task['id'])
            result = runner.run(self.config, output, 1107, resume=True, mock=True, complete_fn=correct)
            self.assertEqual(result['stopped'], 'sampling_check_failed')
            self.assertEqual(result['sampling_gate']['n_valid'], 48)
            self.assertEqual(result['sampling_gate']['gap'], 3)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, stage='map', resume=True, mock=True)

    def test_no_restart_without_whitespace_failure_and_no_in_place_migration(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v1(root)
            with self.assertRaises(ValueError):
                runner.migrate(self.config, source, source)
            with self.assertRaises(ValueError):
                runner.migrate(self.config, source, source / 'v2')
            clean = Path(root) / 'clean-v1'
            v1_runner.prepare(self.v1_config, clean, self.source)
            v1_runner.run(self.v1_config, clean, 49, mock=True)
            with self.assertRaises(ValueError):
                runner.migrate(self.config, clean, Path(root) / 'clean-v2')


if __name__ == '__main__':
    unittest.main()
