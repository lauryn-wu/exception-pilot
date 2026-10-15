"""All model responses are mocks. LIVE-shaped source fixtures are never model evidence."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_continuation.qwen3 import manifest as qwen_manifest
from exception_continuation.runner import sealed_read, sealed_write
from exception_pilot.core import digest
from exception_study2_v4 import core, runner
from exception_study2_v4.journal import Session
from scripts import study2_qwen_length_diagnostic as diagnostic


class MockQwen:
    """Synthetic character responses with realistic journal metadata, no torch/model."""
    eos_ids = {151645, 151643}
    special_ids = eos_ids | {151644}

    def __init__(self, config, fixture_source=False):
        # Only the temporary source fixture imitates LIVE_LOCAL journal shape.
        # Actual diagnostic calls below are explicitly labelled MOCK.
        self.simulated = not fixture_source
        self.config = copy.deepcopy(config)
        self.tasks = core.make_plan(configuration=dict(core.config(), model=config))['tasks']
        self.visible = [t for t in self.tasks[:8] if t['arm'] == 'visible']
        self.by_prompt = {tuple(self.prompt(t['prompt'])): t for t in self.tasks}
        self.calls = []
        self.identity = dict(kind='LOCAL_HF_TOKEN_IDS', config=copy.deepcopy(config),
            files={k: v['sha256'] for k, v in qwen_manifest()['files'].items()},
            dtype='torch.bfloat16', device='cuda:0', hardware='MOCK FIXTURE, NOT QWEN EVIDENCE',
            chat_template='MOCK template with original empty thinking block', special_ids=sorted(self.special_ids),
            generation=dict(do_sample=False, num_beams=1, use_cache=True, eos_token_id=[151645, 151643]),
            generation_overrides=dict(do_sample=False, num_beams=1, use_model_defaults=False))

    def prompt(self, text):
        return [151644] + [ord(c) for c in 'user\n' + text + '\nassistant\n<think>\n\n</think>\n\n']

    def decode(self, ids):
        return ''.join(chr(t) for t in ids if t not in self.special_ids)

    def encode(self, text):
        return [ord(c) for c in text]

    def generate(self, ids, budget, capture_at=()):
        self.calls.append(dict(input_ids=list(ids), budget=budget, capture_at=list(capture_at)))
        task = self.by_prompt.get(tuple(ids))
        if task is None:
            tokens = [151645]
        elif budget == 512:
            tokens = self.encode('R' * 512) if task['arm'] == 'visible' else self.encode('ANSWER: ' + task['expected']) + [151645]
        else:
            assert budget == 2048 and task['arm'] == 'visible'
            index = [t['id'] for t in self.visible].index(task['id'])
            prefix = 'R' * 512
            if index == 0:
                text = prefix + '\nANSWER: ' + task['expected']
            elif index == 1:
                text = prefix[:7] + 'D' + prefix[8:] + '\nANSWER: ' + task['pattern']
            elif index == 2:
                text = prefix + '\nNo final answer syntax.'
            else:
                text = (prefix + '\nANSWER: ' + task['expected'] + '\nStill checking. ' + 'Z' * 2048)[:2048]
            tokens = self.encode(text) + ([151645] if index != 3 else [])
        stopped = tokens[-1] in self.eos_ids
        vectors = {}
        if capture_at:
            values = [0.] * 151936
            values[151645] = 1.
            vectors = {'0': values}
        return dict(tokens=tokens, text=self.decode(tokens), stopped=stopped,
            finish='eos' if stopped else 'length', next_token_logits=vectors)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(root).rglob('*') if p.is_file()}


class PrefixTests(unittest.TestCase):
    def test_agreement_and_positions(self):
        old = [17] * 512
        self.assertTrue(diagnostic.prefix_comparison(old, old + [99])['first_512_tokens_exact_match'])
        for i in (0, 7, 511):
            new = old.copy(); new[i] = 18
            r = diagnostic.prefix_comparison(old, new + [99])
            self.assertFalse(r['first_512_tokens_exact_match'])
            self.assertEqual(r['first_differing_token_index_zero_based'], i)
            self.assertEqual(r['first_differing_token_position_one_based'], i + 1)
            self.assertEqual(r['divergence_kind'], 'TOKEN_MISMATCH')
        r = diagnostic.prefix_comparison(old, old[:9])
        self.assertEqual(r['first_differing_token_index_zero_based'], 9)
        self.assertEqual(r['divergence_kind'], 'NEW_SEQUENCE_ENDED')
        self.assertIsNone(r['new_token_at_difference'])


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='MOCK-length-source-')
        cls.fixture_root = Path(cls.fixture.name) / 'source'
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK FORBIDDEN')):
            plan = core.prepare(cls.fixture_root)
            backend = MockQwen(plan['config'], fixture_source=True)
            with contextlib.redirect_stdout(io.StringIO()):
                runner.run(cls.fixture_root, limit_originals=8, backend_override=backend)
        assert not (cls.fixture_root / 'collection-v4.json').exists()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / 'source'; self.out = self.root / 'diagnostic'
        shutil.copytree(self.fixture_root, self.source)
        self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK FORBIDDEN')))
        self.enterContext(patch('exception_continuation.backend.LocalBackend', side_effect=AssertionError('REAL MODEL FORBIDDEN')))
        self.enterContext(patch('exception_study2_v4.source.Source', side_effect=AssertionError('COMPLETE SOURCE FORBIDDEN')))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.backend = MockQwen(core.read_plan(self.source)['config'])

    def run_diag(self, live=True, backend=None):
        return diagnostic.run(self.source, self.out, live, backend_factory=lambda c: backend or self.backend)

    def original_path(self, task_id):
        return self.source / 'operations-v4' / digest('v4/original/' + task_id) / 'returned.json'

    def test_exact_four_prompts_budget_outputs_and_source_preservation(self):
        before = snapshot(self.source); hash_before = core.source_hash()
        result = self.run_diag()
        self.assertEqual(result['status'], 'COMPLETE')
        planned = core.read_plan(self.source)['tasks'][:8]
        expected = [t for t in planned if t['arm'] == 'visible']
        self.assertEqual([r['task_id'] for r in result['cases']], [t['id'] for t in expected])
        self.assertEqual(len(self.backend.calls), 4)
        for call, task, row in zip(self.backend.calls, expected, result['cases']):
            old = sealed_read(self.original_path(task['id']))
            self.assertEqual(call['input_ids'], old['request']['input_ids'])
            self.assertEqual(call['budget'], 2048); self.assertEqual(call['capture_at'], [])
            self.assertEqual(row['original_operation_hash'], old['artifact_hash'])
            self.assertEqual(row['prompt_ids_hash'], digest(call['input_ids']))
            self.assertEqual(row['prompt_hash'], digest(task['prompt']))
            self.assertEqual(row['measurement'], 'MOCK')
            self.assertEqual(row['raw']['text'], self.backend.decode(row['raw']['tokens']))
        self.assertEqual(snapshot(self.source), before); self.assertEqual(core.source_hash(), hash_before)
        rows = result['cases']
        self.assertEqual([r['outcome'] for r in rows], ['correct', 'wrong', 'invalid', 'invalid'])
        self.assertEqual([r['eos'] for r in rows], [True, True, True, False])
        self.assertEqual([r['truncated'] for r in rows], [False, False, False, True])
        self.assertEqual([r['answer_marker_present'] for r in rows], [True, True, False, True])
        self.assertEqual([r['first_512_tokens_exact_match'] for r in rows], [True, False, True, True])
        self.assertEqual(rows[1]['first_differing_token_position_one_based'], 8)
        self.assertIsNone(rows[3]['correctness']); self.assertIsNone(rows[3]['final_answer'])
        self.assertEqual(result['summary']['correctness_unknown'], 2)
        text = (self.out / 'diagnostic-traces.txt').read_text()
        for row in rows: self.assertIn(row['raw']['text'], text)
        self.assertIn('NOT an exact continuation', text)
        self.assertEqual(result['false_missingness_classification'], 'NOT_PERFORMED_MANUAL_REVIEW_REQUIRED')
        manifest = sealed_read(self.out / 'diagnostic-plan.json')
        self.assertEqual(manifest['generation_parameters']['frozen_model_config']['max_new_tokens'], 512)
        self.assertEqual(manifest['maximum_generated_tokens'], 8192)
        self.assertEqual(manifest['code']['v4_source_hash'], hash_before)

    def test_default_cli_and_cache_never_load_backend(self):
        diagnostic.main(['--source', str(self.source), '--output', str(self.out)])
        result = json.loads((self.out / 'diagnostic-results.json').read_text())
        self.assertEqual(result['status'], 'PREPARED_NO_INFERENCE')
        self.assertFalse(self.backend.calls)
        self.run_diag()
        entries_before = snapshot(self.out / 'operations')
        result = diagnostic.run(self.source, self.out, True,
            backend_factory=lambda _: self.fail('Completed cache must not load weights'))
        self.assertEqual(result['status'], 'COMPLETE_FROM_CACHE')
        self.assertEqual(snapshot(self.out / 'operations'), entries_before)

    def test_later_originals_and_direct_tasks_excluded(self):
        plan = core.read_plan(self.source); backend = MockQwen(plan['config'], fixture_source=True)
        session = Session(self.source, plan, backend)
        for task in plan['tasks'][8:12]:
            session.generate('v4/original/' + task['id'], backend.prompt(task['prompt']), 512, stage='original_generation')
        result = self.run_diag()
        self.assertEqual([r['task_id'] for r in result['cases']], [t['id'] for t in plan['tasks'][:8] if t['arm'] == 'visible'])
        self.assertEqual(len(self.backend.calls), 4)

    def test_backend_and_prompt_mismatch_before_any_generation(self):
        self.backend.identity['hardware'] = 'another GPU'
        with self.assertRaisesRegex(ValueError, 'backend identity'): self.run_diag()
        self.assertEqual(self.backend.calls, [])
        # A new output is used only inside this mock rejection test.
        self.out = self.root / 'prompt-mismatch'; self.backend = MockQwen(core.read_plan(self.source)['config'])
        old = self.backend.prompt
        self.backend.prompt = lambda text: old(text) + [9]
        with self.assertRaisesRegex(ValueError, 'prompt IDs'): self.run_diag()
        self.assertEqual(self.backend.calls, [])

    def test_source_and_code_change_refuse_resume(self):
        self.run_diag(live=False)
        task = self.backend.visible[0]; path = self.original_path(task['id']); op = sealed_read(path)
        op['result']['tokens'][0] = ord('S'); op['result']['text'] = 'S' + op['result']['text'][1:]
        sealed_write(path, op)
        with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'): self.run_diag()
        self.assertEqual(self.backend.calls, [])
        self.out = self.root / 'code-change'; self.run_diag(live=False)
        old = diagnostic.code_identity()
        with patch.object(diagnostic, 'code_identity', return_value=dict(old, git_revision='different')):
            with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'): self.run_diag()
        self.assertEqual(self.backend.calls, [])

    def test_missing_or_nontruncated_original_rejected(self):
        task = self.backend.visible[0]; path = self.original_path(task['id']); original = sealed_read(path)
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or unavailable'): self.run_diag()
        self.assertFalse(self.out.exists())
        op = copy.deepcopy(original); op['result'].update(tokens=[151645], text='', stopped=True, finish='eos')
        sealed_write(path, op)
        with self.assertRaisesRegex(ValueError, 'truncated at exactly 512'): self.run_diag()
        self.assertFalse(self.backend.calls)

    def test_source_model_and_technical_identity_mismatches(self):
        path = self.source / 'execution-v4.json'; old = sealed_read(path)
        changed = copy.deepcopy(old); changed['mode'] = 'MOCK'; sealed_write(path, changed)
        with self.assertRaisesRegex(ValueError, 'real-model'): self.run_diag()
        changed = copy.deepcopy(old); changed['backend']['config']['model_profile']['revision'] = 'wrong'
        changed['backend_hash'] = digest(changed['backend']); sealed_write(path, changed)
        with self.assertRaises(ValueError): self.run_diag()
        sealed_write(path, old)
        technical = self.source / 'technical-v4.json'; value = sealed_read(technical)
        value['records'][0]['repeats'][0]['distribution']['total_variation'] = .1
        sealed_write(technical, value)
        with self.assertRaisesRegex(ValueError, 'technical gate FAILED or changed'): self.run_diag()
        self.assertFalse(self.backend.calls)

    def test_source_plan_and_operation_request_mismatches(self):
        plan_path = self.source / 'plan-v4.json'; original = sealed_read(plan_path)
        changed = copy.deepcopy(original); changed['protocol'] = 'other'; sealed_write(plan_path, changed)
        with self.assertRaises(ValueError): self.run_diag()
        sealed_write(plan_path, original)
        task = self.backend.visible[0]; path = self.original_path(task['id']); op = sealed_read(path)
        op['request']['input_ids'] += [1]; sealed_write(path, op)
        with self.assertRaisesRegex(ValueError, 'identity'): self.run_diag()
        self.assertFalse(self.backend.calls)

    def test_returned_cache_and_unattempted_calls_resume(self):
        verify = diagnostic.unchanged_source; checks = [0]
        def fail_between_calls(src):
            verify(src); checks[0] += 1
            if checks[0] == 3: raise RuntimeError('mock interruption after first result saved')
        with patch.object(diagnostic, 'unchanged_source', side_effect=fail_between_calls):
            with self.assertRaises(RuntimeError): self.run_diag()
        self.assertEqual(len(self.backend.calls), 1)
        first = self.out / 'operations' / digest(self.backend.visible[0]['id']) / 'returned.json'
        before = first.read_bytes(); self.backend.calls.clear()
        result = self.run_diag()
        self.assertEqual(result['status'], 'COMPLETE'); self.assertEqual(len(self.backend.calls), 3)
        self.assertEqual(first.read_bytes(), before)
        self.assertNotEqual(self.backend.calls[0]['input_ids'], self.backend.prompt(self.backend.visible[0]['prompt']))

    def test_failed_and_ambiguous_calls_never_resent(self):
        generate = self.backend.generate; calls = [0]
        def interrupt(*a, **kw):
            calls[0] += 1
            if calls[0] == 2: raise KeyboardInterrupt()
            return generate(*a, **kw)
        self.backend.generate = interrupt
        with self.assertRaises(KeyboardInterrupt): self.run_diag()
        self.assertEqual(calls[0], 2)
        with self.assertRaisesRegex(ValueError, 'no automatic resend'):
            diagnostic.run(self.source, self.out, True, backend_factory=lambda _: self.fail('Must block before loading'))
        second = self.out / 'operations' / digest(self.backend.visible[1]['id'])
        (second / 'failed.json').unlink()  # Model SIGKILL: only started is durable.
        with self.assertRaisesRegex(ValueError, 'no automatic resend'):
            diagnostic.run(self.source, self.out, True, backend_factory=lambda _: self.fail('Ambiguous resend'))
        report = self.run_diag(live=False)
        self.assertEqual(report['status'], 'BLOCKED_NO_RESEND'); self.assertEqual(calls[0], 2)
        self.assertEqual(report['cases'][0]['status'], 'RETURNED')
        self.assertEqual(report['cases'][1]['status'], 'STARTED')

    def test_unusable_return_retained_and_never_resampled(self):
        generate = self.backend.generate
        def malformed(*a, **kw):
            raw = generate(*a, **kw)
            raw['text'] += ' inconsistent with token IDs'
            return raw
        self.backend.generate = malformed
        with self.assertRaisesRegex(ValueError, 'Unusable return preserved'): self.run_diag()
        report = json.loads((self.out / 'diagnostic-results.json').read_text())
        self.assertEqual(report['summary']['returned'], 1)
        self.assertEqual(report['summary']['usable_returned'], 0)
        self.assertEqual(report['cases'][0]['status'], 'UNUSABLE_RETURN')
        self.assertIsNone(report['cases'][0]['score']['correct'])
        self.assertIn('inconsistent with token IDs', report['cases'][0]['raw']['text'])
        self.backend.generate = generate
        self.backend.calls.clear()
        report = self.run_diag()
        self.assertEqual(len(self.backend.calls), 3)
        self.assertEqual(report['summary']['returned'], 4)
        self.assertEqual(report['status'], 'COMPLETE_WITH_UNUSABLE_RETURNS')
        self.assertEqual(report['cases'][0]['status'], 'UNUSABLE_RETURN')

    def test_output_cannot_overwrite_source_or_existing_experiments(self):
        before = snapshot(self.source)
        for out in (self.source, self.source / 'nested', self.root):
            with self.assertRaises(ValueError): diagnostic.run(self.source, out)
        alias = self.root / 'alias'; alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError): diagnostic.run(self.source, alias)
        other = self.root / 'existing'; other.mkdir(); (other / 'keep.txt').write_text('existing result')
        with self.assertRaises(ValueError): diagnostic.run(self.source, other)
        self.assertEqual((other / 'keep.txt').read_text(), 'existing result')
        self.assertEqual(snapshot(self.source), before)

    def test_diagnostic_request_corruption_refuses_resume(self):
        self.run_diag(live=False)
        task = self.backend.visible[0]['id']; path = self.out / 'operations' / digest(task) / 'request.json'
        value = sealed_read(path); value['request']['budget'] = 512; sealed_write(path, value)
        with self.assertRaises(ValueError): self.run_diag()
        self.assertFalse(self.backend.calls)


if __name__ == '__main__':
    unittest.main()
