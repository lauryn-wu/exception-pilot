"""Complete-screen collection, no resampling, and preservation of V1/V2 results."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_mistral_map import core as v1_core
from exception_mistral_map_v2 import core as v2_core, runner as v2_runner
from exception_mistral_map_v3 import core, runner
from test_mistral_map import ROOT, make_parent, raw
import test_mistral_map_v2 as v2_tests


class CompleteScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.source = make_parent(Path(cls.temp.name) / 'source')
        cls.v1_config = v1_core.load_config(ROOT / 'configs/mistral_map.json')
        cls.v2_config = v2_core.load_config(ROOT / 'configs/mistral_map_v2.json')
        cls.config = core.load_config(ROOT / 'configs/mistral_map_v3.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def stopped_v2(self, root, ambiguous=False):
        source, _ = v2_tests.WhitespaceAmendmentTests.stopped_v1(self, root)
        output = Path(root) / 'v2'
        plan = v2_runner.migrate(self.v2_config, source, output)
        queue = iter(plan['tasks'][6:])
        def complete(config, payload):
            task = next(queue)
            meta = v2_core.task_meta(plan, task)
            if task['arm'] == 'direct':
                text = 'ANSWER: ' + meta['expected']
            else:
                text = 'The description seems to match a background pattern.\n'
                text += 'ANSWER: A or B' if ambiguous else '**ANSWER: ' + meta['pattern_label'] + '**'
            return raw(text, 'v2-new-' + task['id'])
        with redirect_stdout(io.StringIO()):
            result = v2_runner.run(self.v2_config, output, 49, resume=True, mock=True, complete_fn=complete)
        self.assertEqual((result['stopped'], result['attempts_total']), ('sampling_check_failed', 9))
        return output, plan

    def test_migration_all_nine_original_bytes_and_identical_requests_no_calls(self):
        with tempfile.TemporaryDirectory() as root:
            source, old_plan = self.stopped_v2(root)
            before = v2_tests.hashes(source)
            output = Path(root) / 'v3'
            with patch.object(runner.provider, 'complete', side_effect=AssertionError('network')), \
                 patch.object(runner.provider, 'credential', side_effect=AssertionError('credential')):
                plan = runner.migrate(self.config, source, output)
            self.assertEqual(v2_tests.hashes(source), before)
            _, _, old = v2_runner.read_run(source)
            _, _, new = runner.read_run(output)
            self.assertEqual(len(new), 9)
            for a, b in zip(old, new):
                self.assertEqual(a['response'], b['response'])
                self.assertEqual(a['request'], b['request'])
                self.assertEqual(a['started_at'], b['started_at'])
                self.assertEqual((source / 'attempts' / f"{a['attempt']:06d}.json").read_bytes(),
                                 (output / 'source-map-v2/attempts' / f"{a['attempt']:06d}.json").read_bytes())
            for task in plan['tasks']:
                self.assertEqual(core.request_for(plan, task), v2_core.request_for(old_plan, task))
            self.assertTrue((output / 'source-map-v2/source-map-v1/source-parent/plan.json').is_file())
            last = new[-1]
            self.assertEqual(last['status'], 'complete')
            self.assertEqual(last['answer'], last['meta']['pattern_label'])
            self.assertEqual(last['strict_v2_score']['status'], 'invalid')
            self.assertEqual(last['strict_v1_score']['status'], 'invalid')
            summary = json.loads((output / 'summary.json').read_text())
            self.assertEqual(summary['analysis_status'], 'pending_sampling_check')
            self.assertEqual(summary['previous_v1_result']['analysis_status'], 'sampling_check_failed_stop')
            self.assertEqual(summary['previous_v2_result']['analysis_status'], 'sampling_check_failed_stop')
            self.assertEqual(summary['sampling_gate']['n_valid'], 8)
            self.assertEqual(summary['strict_v2_sampling_gate_on_collected_answers']['n_valid'], 7)
            self.assertEqual(summary['strict_v1_sampling_gate_on_collected_answers']['n_valid'], 6)
            self.assertEqual(runner.migrate(self.config, source, output), plan)

    def test_resume_40_new_calls_no_replacements_or_automatic_mapping(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v2(root)
            output = Path(root) / 'v3'
            runner.migrate(self.config, source, output)
            result = runner.run(self.config, output, 1107, resume=True, mock=True)
            self.assertEqual((result['stopped'], result['calls_this_invocation'], result['attempts_total']),
                             ('sampling_check_passed', 40, 49))
            result = runner.run(self.config, output, 1107, resume=True, mock=True)
            self.assertEqual(result['calls_this_invocation'], 0)
            result = runner.run(self.config, output, 2, stage='map', resume=True, mock=True)
            self.assertEqual(result['calls_this_invocation'], 2)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, resume=True, mock=False)

    def test_new_unscorable_is_retained_collection_finishes_then_blocks_map(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v2(root)
            output = Path(root) / 'v3'
            runner.migrate(self.config, source, output)
            result = runner.run(self.config, output, 1, resume=True, mock=True,
                                complete_fn=lambda cfg, payload: raw('Uncertain: A or B.', 'new-unscorable'))
            self.assertEqual(result['stopped'], 'call_limit')
            self.assertEqual(result['analysis_status'], 'pending_sampling_check')
            self.assertEqual(result['sampling_gate']['n_invalid'], 1)
            self.assertEqual(result['sampling_gate']['decision_basis'], 'collection_incomplete')
            unscorable_bytes = (output / 'attempts/000010.json').read_bytes()
            result = runner.run(self.config, output, 1107, resume=True, retry_errors=True, mock=True)
            self.assertEqual((result['stopped'], result['calls_this_invocation'], result['attempts_total']),
                             ('sampling_check_unscorable', 39, 49))
            self.assertEqual(result['analysis_status'], 'sampling_check_unscorable_stop')
            self.assertEqual(result['sampling_gate']['n_returned'], 48)
            self.assertEqual(result['sampling_gate']['n_valid'], 47)
            self.assertEqual(result['sampling_gate']['decision_basis'], 'unscorable_responses')
            self.assertEqual((output / 'attempts/000010.json').read_bytes(), unscorable_bytes)
            self.assertEqual(runner.run(self.config, output, 1, resume=True, retry_errors=True, mock=True)['calls_this_invocation'], 0)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, stage='map', resume=True, mock=True)

    def test_imported_ambiguous_answer_is_not_guessed_or_retried(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v2(root, ambiguous=True)
            output = Path(root) / 'v3'
            plan = runner.migrate(self.config, source, output)
            self.assertEqual(len(plan['previous_run']['unscorable_task_ids']), 1)
            self.assertEqual(runner.read_run(output)[2][-1]['answer'], None)
            result = runner.run(self.config, output, 1107, resume=True, mock=True)
            self.assertEqual((result['stopped'], result['calls_this_invocation']), ('sampling_check_unscorable', 40))

    def test_behavioral_thresholds_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v2(root)
            output = Path(root) / 'v3'
            plan = runner.migrate(self.config, source, output)
            queue = iter(plan['tasks'][9:49])
            def correct(config, payload):
                task = next(queue)
                label = core.task_meta(plan, task)['expected']
                return raw(('Reasoning.\n' if task['arm'] == 'visible' else '') + '**ANSWER: ' + label + '**', task['id'])
            result = runner.run(self.config, output, 1107, resume=True, mock=True, complete_fn=correct)
            self.assertEqual(result['stopped'], 'sampling_check_failed')
            self.assertEqual(result['sampling_gate']['n_valid'], 48)
            self.assertEqual(result['sampling_gate']['visible_pattern_error_worlds'], 2)
            self.assertEqual(result['sampling_gate']['thresholds']['minimum_pattern_error_worlds'], 3)
            self.assertEqual(result['sampling_gate']['decision_basis'], 'original_behavioral_thresholds')

    def test_operational_failure_still_terminal_and_no_credential_lookup_for_mock(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            source, _ = self.stopped_v2(root)
            output = Path(root) / 'v3'
            runner.migrate(self.config, source, output)
            with patch.object(runner.provider, 'credential', side_effect=AssertionError('credential')):
                result = runner.run(self.config, output, 1, resume=True, mock=True,
                                    complete_fn=lambda cfg, payload: raw('Reasoning.\n**ANSWER: A**', 'truncated', finish='length'))
            self.assertEqual(result['stopped'], 'operational_failure')
            self.assertEqual(result['analysis_status'], 'operational_stop')
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, resume=True, retry_errors=True, mock=True)

    def test_imported_copy_and_snapshot_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source, _ = self.stopped_v2(root)
            output = Path(root) / 'v3'
            runner.migrate(self.config, source, output)
            path = output / 'attempts/000009.json'
            original = path.read_bytes()
            data = json.loads(original)
            data['response']['text'] += 'changed'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runner.read_run(output)
            path.write_bytes(original)
            frozen = output / 'source-map-v2/source-map-v1/attempts/000006.json'
            frozen.write_bytes(frozen.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                runner.read_run(output)

    def test_missing_reasoning_and_direct_explanations_stay_invalid(self):
        for text in ('**ANSWER: A**', '```text\nANSWER: A\n```', '**ANSWER:** **A**'):
            result = core.score_response({'family': 'base', 'arm': 'visible'}, raw(text), {})
            self.assertEqual(result['invalid_reason'], 'reasoning_text_missing')
            result = core.score_response({'family': 'base', 'arm': 'direct'}, raw('Reasoning.\n' + text), {})
            self.assertEqual(result['invalid_reason'], 'direct_not_answer_only')


if __name__ == '__main__':
    unittest.main()
