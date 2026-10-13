"""Offline profile, staging and real-tokenizer tests; never download or use 32B weights."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from exception_continuation import core, runner, edits
from exception_continuation.backend import LocalBackend, MockBackend, assert_plain_format, readout
from exception_continuation.qwen3 import PROFILE, ASSISTANT_SUFFIX, manifest, verify_local_snapshot, tokenizer_check
from exception_continuation.selection import selection_report
from tests.test_continuation_v2 import CalibratedFixture
from tests.test_continuation_v3 import annotate

ROOT = Path(__file__).resolve().parents[1]
TOKENIZER_DIR = os.environ.get('QWEN3_TOKENIZER_DIR')


def config():
    return json.loads((ROOT/'configs/continuation_v3_qwen3_32b.json').read_text())


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('socket.create_connection', side_effect=AssertionError('Network forbidden')))
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')))


class ProfileTests(OfflineTests):
    def test_exact_revision_bf16_no_thinking_and_unchanged_48_tasks(self):
        c = config(); core.validate_config(c)
        self.assertEqual(c['model_profile'], PROFILE)
        self.assertEqual(c['dtype'], 'bfloat16')
        self.assertEqual(c['chat_template_kwargs'], {'enable_thinking': False})
        self.assertEqual(core.make_plan('selection', c)['tasks'], core.make_plan('selection')['tasks'])
        tasks = core.make_plan('selection', c)['tasks']
        self.assertEqual(len(tasks), 48)
        self.assertEqual(sum(t['arm'] == 'direct' for t in tasks), 24)
        self.assertTrue(all('Write your reasoning' in t['prompt'] for t in tasks if t['arm'] == 'visible'))
        self.assertTrue(all(t['prompt'].endswith('Output only ANSWER: followed by A, B, or C.') for t in tasks if t['arm'] == 'direct'))
        self.assertEqual(c['validation_tolerances'], core.DEFAULT_CONFIG['validation_tolerances'])
        self.assertEqual(c['calibration'], core.DEFAULT_CONFIG['calibration'])

    def test_profile_refuses_fallbacks_and_threshold_relaxation(self):
        for name, value in [('dtype', 'float16'), ('device', 'cpu'), ('max_new_tokens', 1024),
                            ('chat_template_kwargs', {}), ('chat_template_kwargs', {'enable_thinking': True}),
                            ('calibration', dict(core.DEFAULT_CONFIG['calibration'], min_direct_correct=1)),
                            ('validation_tolerances', dict(core.DEFAULT_CONFIG['validation_tolerances'], logit_atol=1.0)),
                            ('model_profile', dict(PROFILE, revision='main')),
                            ('model_profile', dict(PROFILE, tokenizer_revision='main')),
                            ('model_profile', dict(PROFILE, repo_id='Qwen/Qwen3-32B-FP8')),
                            ('quantization_config', {'bits': 4})]:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                core.validate_config(dict(config(), **{name: value}))

    def test_existing_interface_accepts_closed_empty_block_without_modification(self):
        assert_plain_format(ASSISTANT_SUFFIX)
        with self.assertRaises(ValueError):
            assert_plain_format('<|im_start|>assistant\n<think>\n')
        with self.assertRaises(ValueError):
            assert_plain_format('<|channel|>analysis')

    def test_manifest_pins_full_bf16_weights_and_tokenizer(self):
        m = manifest()
        self.assertEqual({k: m[k] for k in PROFILE}, PROFILE)
        weights = [n for n in m['files'] if n.endswith('.safetensors')]
        self.assertEqual(len(weights), 17)
        self.assertEqual(m['weight_bytes'], 65524328560)
        self.assertEqual(m['parameter_count'], 32762123264)
        self.assertTrue(all(len(v['sha256']) == 64 for v in m['files'].values()))

    def test_snapshot_hashes_not_just_local_directory_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {'config.json': b'{}', 'model-00001-of-00001.safetensors': b'NOT-REAL-WEIGHTS'}
            fake = {'files': {n: {'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for n,b in files.items()}}
            for n,b in files.items(): (root/n).write_bytes(b)
            with patch('exception_continuation.qwen3.manifest', return_value=fake):
                self.assertEqual(set(verify_local_snapshot(root)), set(files))
                (root/'config.json').write_bytes(b'[]')
                with self.assertRaisesRegex(ValueError, 'hash differs'):
                    verify_local_snapshot(root)
                (root/'config.json').write_bytes(b'{}')
                (root/'model-00001-of-00001.safetensors').unlink()
                self.assertEqual(set(verify_local_snapshot(root, tokenizer_only=True)), {'config.json'})
                with self.assertRaisesRegex(ValueError, 'Missing'):
                    verify_local_snapshot(root)
                (root/'chat_template.jinja').write_text('replacement')
                with self.assertRaisesRegex(ValueError, 'override'):
                    verify_local_snapshot(root, tokenizer_only=True)

    def test_prepare_and_report_load_no_backend_and_advance_no_stage(self):
        with tempfile.TemporaryDirectory() as tmp, patch('exception_continuation.runner.LocalBackend', side_effect=AssertionError('No model load')):
            plan = runner.prepare(tmp, 'selection', config())
            report = selection_report(tmp)
            self.assertEqual(len(plan['tasks']), 48)
            self.assertEqual(report['returned_responses'], 0)
            self.assertEqual(report['real_model_compatibility'], 'PENDING')
            self.assertEqual(report['behavioral_replication'], 'PENDING')
            self.assertIsNone(report['study_2b_manual_eligibility']['eligible_cases_before_branch_validation'])
            self.assertFalse((Path(tmp)/'execution.json').exists())
            self.assertFalse((Path(tmp)/'measurements.json').exists())
            self.assertFalse((Path(tmp)/'interventions.json').exists())


class SelectionTests(OfflineTests):
    def test_reasoning_error_success_does_not_establish_2b_eligibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection', config())
            collection = runner.collect(tmp, backend_override=CalibratedFixture())
            report = selection_report(tmp)
            self.assertTrue(report['existing_calibration']['passed'])
            self.assertEqual(report['by_arm']['direct']['correct'], 24)
            self.assertEqual(report['matched_reasoning_errors']['direct_correct_visible_pattern_errors'], 24)
            self.assertEqual(report['study_2b_manual_eligibility']['reviewed'], 0)
            self.assertIsNone(report['study_2b_manual_eligibility']['eligible_cases_before_branch_validation'])
            annotate(Path(tmp), collection, positives=0)
            report = selection_report(tmp)
            self.assertTrue(report['existing_calibration']['passed'])
            review = report['study_2b_manual_eligibility']
            self.assertEqual((review['reviewed'], review['reviewed_false_missing_cases'], review['eligible_cases_before_branch_validation'], review['eligible_worlds_before_branch_validation']), (24,0,0,0))
            self.assertEqual(review['status'], 'NO_ELIGIBLE_CASES')
            self.assertEqual(report['behavioral_replication'], 'PENDING')  # simulated, never real evidence

    def test_manual_cases_and_distinct_worlds_separate_from_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection', config())
            collection = runner.collect(tmp, backend_override=CalibratedFixture())
            frozen = annotate(Path(tmp), collection, positives=3)
            report = selection_report(tmp)
            review = report['study_2b_manual_eligibility']
            tasks = {t['id']:t for t in core.read_plan(tmp)['tasks']}
            self.assertEqual(review['reviewed_false_missing_cases'], 3)
            self.assertEqual(review['eligible_cases_before_branch_validation'], 3)
            self.assertEqual(review['eligible_worlds_before_branch_validation'], len({tasks[c['task_id']]['world'] for c in frozen['cases']}))
            self.assertEqual(review['per_case_replay_validation'], 'PENDING')
            self.assertEqual(review['sufficiency'], 'REQUIRES_SEPARATE_REVIEW')
            self.assertFalse((Path(tmp)/'measurements.json').exists())
            self.assertFalse((Path(tmp)/'interventions.json').exists())

    def test_draft_review_does_not_count_as_frozen_eligibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection'); runner.collect(tmp, mock=True)
            path = edits.review_export(tmp); review = json.loads(path.read_text())
            review['rows'][0].update(reviewed=True, false_missing=True, reviewer='OFFLINE_FIXTURE', justification='Fixture only')
            path.write_text(json.dumps(review))
            result = selection_report(tmp)['study_2b_manual_eligibility']
            self.assertEqual(result['reviewed'], 1)
            self.assertEqual(result['reviewed_false_missing_cases'], 1)
            self.assertIsNone(result['eligible_cases_before_branch_validation'])
            review['rows'][0]['text'] += 'changed'; path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, 'source changed'):
                selection_report(tmp)

    def test_invalid_truncated_unknown_and_missing_axes_are_separate(self):
        for script, truncated in [(MockBackend.script[:-1]+'D', 0), (MockBackend.script*4, 24)]:
            class Invalid(MockBackend): pass
            b = Invalid(); b.script = script
            with self.subTest(truncated=truncated), tempfile.TemporaryDirectory() as tmp:
                runner.prepare(tmp, 'selection'); runner.collect(tmp, backend_override=b)
                report = selection_report(tmp)
                for arm in ('direct','visible'):
                    c = report['by_arm'][arm]
                    self.assertEqual((c['returned'],c['invalid'],c['truncated'],c['missing']), (24,24,truncated,0))
                    self.assertEqual(c['wrong'],0)
                    self.assertIsNone(c['accuracy_valid'])
                    self.assertEqual(c['accuracy_full_plan_bounds'],[0,1])
                self.assertEqual(report['matched_reasoning_errors']['direct_correct_visible_wrong'],0)

    def test_partial_failed_collection_retains_original_and_reports_missing(self):
        class FailSecond(MockBackend):
            count = 0
            def generate(self, ids, budget, capture_at=()):
                if 'Verified class' in self.decode(ids) and ids[-1] == 1000000:
                    self.count += 1
                    if self.count == 2: raise RuntimeError('OFFLINE fixture failure')
                return super().generate(ids,budget,capture_at)
        with tempfile.TemporaryDirectory() as tmp:
            runner.prepare(tmp, 'selection'); b = FailSecond()
            with self.assertRaises(RuntimeError): runner.collect(tmp, backend_override=b)
            before = {p.name:p.read_bytes() for p in (Path(tmp)/'operations').glob('*.json')}
            report = selection_report(tmp)
            self.assertEqual(report['returned_responses'],1)
            self.assertEqual(sum(a['missing'] for a in report['by_arm'].values()),47)
            self.assertEqual(len(report['unresolved_operations']),1)
            self.assertIsNone(report['existing_calibration']['passed'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in (Path(tmp)/'operations').glob('*.json')})


@unittest.skipUnless(TOKENIZER_DIR and importlib.util.find_spec('transformers'), 'Set QWEN3_TOKENIZER_DIR to pinned local tokenizer assets; no downloads in tests')
class ActualTokenizerTests(OfflineTests):
    def test_official_template_eos_candidates_and_all_selection_prompts(self):
        with patch('transformers.AutoModelForCausalLM.from_pretrained', side_effect=AssertionError('No model weights allowed')):
            report = tokenizer_check(TOKENIZER_DIR)
        self.assertEqual(report['status'], 'TOKENIZER_ONLY_PASSED')
        self.assertEqual(report['inference_calls'],0)
        self.assertEqual(report['real_model_compatibility'],'PENDING')
        self.assertEqual(report['empty_block_token_ids'],[151667,271,151668,271])
        self.assertEqual(report['candidates'],{'A':[362,198],'B':[425,198],'C':[356,198]})
        self.assertEqual(report['eos_token_ids'],[151645,151643])
        self.assertEqual(len(report['selection_prompts']),48)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'Requires locally installed torch; never installed by tests')
    def test_existing_loader_scoring_and_saved_prefix_on_tiny_random_qwen(self):
        import torch
        from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM, GenerationConfig
        torch.manual_seed(73)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = Qwen3Config(vocab_size=151936, hidden_size=8, intermediate_size=16,
                             num_hidden_layers=1, num_attention_heads=1, num_key_value_heads=1,
                             head_dim=8, max_position_embeddings=2048, bos_token_id=151643, eos_token_id=151645,
                             sliding_window=None)
            tiny = Qwen3ForCausalLM(cfg).to(torch.bfloat16)
            tiny.generation_config = GenerationConfig.from_pretrained(TOKENIZER_DIR, local_files_only=True)
            tiny.save_pretrained(root)
            for name in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt'):
                shutil.copyfile(Path(TOKENIZER_DIR)/name,root/name)
            del tiny
            # Synthetic CPU model tests adapter mechanics; this is not the pinned 32B model/profile.
            b = LocalBackend(dict(core.DEFAULT_CONFIG, model_dir=str(root), dtype='bfloat16',
                                  chat_template_kwargs={'enable_thinking':False}))
            self.assertEqual(b.model.dtype,torch.bfloat16)
            self.assertEqual(b.eos_ids,{151643,151645})
            self.assertFalse(b.generation.do_sample)
            self.assertEqual(b.generation_overrides, {'do_sample':False, 'num_beams':1, 'use_model_defaults':False})
            self.assertFalse(getattr(b.model,'is_quantized',False))
            ids = b.prompt('Describe a bookshelf.')
            rendered = b.tokenizer.decode(ids,skip_special_tokens=False)
            self.assertTrue(rendered.endswith(ASSISTANT_SUFFIX))
            base = b.generate(ids,6,capture_at=(0,1,2))
            self.assertEqual(len(base['next_token_logits']['0']),151936)
            for k, logits in base['next_token_logits'].items():
                self.assertEqual(base['tokens'][int(k)], max(range(len(logits)), key=logits.__getitem__))
            prefix = base['tokens'][:2]
            with patch.object(b.tokenizer,'apply_chat_template',side_effect=AssertionError('Never rebuild a continuation prompt')):
                replay = b.generate(ids+prefix,4,capture_at=(0,))
                self.assertEqual(replay['tokens'],base['tokens'][2:])
                context = ids+prefix+b.encode('\nANSWER:')
                for candidate in (' A\n',' B\n',' C\n'):
                    score = b.score(context,candidate); tokens = b.encode(candidate)
                    expected=[]
                    with torch.inference_mode():
                        for i,t in enumerate(tokens):
                            logits=b.model(input_ids=b.tensor(context+tokens[:i]),use_cache=False).logits[0,-1].float()
                            expected.append(torch.log_softmax(logits,dim=-1)[t].item())
                    self.assertEqual(score['tokens'],tokens)
                    self.assertEqual(len(score['token_logprobs']),2)
                    for actual,wanted in zip(score['token_logprobs'],expected):
                        self.assertAlmostEqual(actual,wanted,places=4)
                    self.assertAlmostEqual(score['logprob'],sum(expected),places=4)
                scored = readout(b,ids,prefix,'A','B')
                self.assertEqual(set(scored['scores']),set('ABC'))
                self.assertAlmostEqual(sum(scored['normalized'].values()),1)
            self.assertEqual(ids[-4:],[151667,271,151668,271])
            for eos in (151645,151643):
                with patch.object(b.model,'generate',return_value=b.tensor(ids+[eos])):
                    stopped=b.generate(ids,6)
                    self.assertTrue(stopped['stopped'])
                    self.assertEqual(stopped['finish'],'eos')
                    self.assertEqual(stopped['tokens'],[eos])


if __name__ == '__main__': unittest.main()
