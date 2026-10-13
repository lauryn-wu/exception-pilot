"""Software fixtures only: no Mistral client, credentials, network or inference."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mistral_study2_capability as check


TEXT = 'Organize the shelves carefully. ' * 4 + 'Finish by checking the labels.'


def rows(text):
    # Fake character-token IDs, explicitly not a tokenizer for the actual model.
    return [dict(token=c, token_id=ord(c), bytes=list(c.encode()), logprob=-0.25) for c in text]


def response(text, output=None, prompt=None, finish='stop', model=check.MODEL):
    choice = dict(message=dict(role='assistant', content=text), finish_reason=finish)
    if output is not None:
        choice['logprobs'] = dict(content=output)
    if prompt is not None:
        choice['prompt_logprobs'] = dict(content=prompt)
    return dict(model=model, id='OFFLINE_FIXTURE', choices=[choice], usage=dict(completion_tokens=1))


class FakeTransport:
    def __init__(self, echo=False, reject=None, status=422):
        self.calls, self.echo, self.reject, self.status = [], echo, reject, status

    def __call__(self, body, key):
        self.calls.append(copy.deepcopy(body))
        if self.reject and self.reject(body):
            return self.status, {}, b'{"error":"OFFLINE_FIXTURE: unsupported"}'
        prefix = body['messages'][-1]['content'] if len(body['messages']) > 1 else ''
        text = TEXT[len(prefix):] if TEXT.startswith(prefix) else 'x'
        if body['max_tokens'] == 1:
            text = 'x'
        output = rows(text) if body.get('logprobs') else None
        prompt = rows('FAKE_SERIALIZED_USER:' + check.PROMPT + ':ASSISTANT:' + prefix) if body.get('prompt_logprobs') else None
        if body.get('top_logprobs') and output:
            for row in output:
                row['top_logprobs'] = [dict(row)]
        if body.get('top_prompt_logprobs') and prompt:
            for row in prompt:
                row['top_logprobs'] = [dict(row)]
        raw = response(prefix + text if self.echo else text, output, prompt)
        return 200, {'x-request-id': 'fixture', 'Authorization': 'NEVER_SAVE'}, json.dumps(raw).encode()


class CapabilityTests(unittest.TestCase):
    def test_default_and_help_never_touch_key_network_or_output(self):
        environ_get = check.os.environ.get
        def guard_key(name, *args):
            if name == 'MISTRAL_API_KEY':
                raise AssertionError('key read')
            return environ_get(name, *args)
        with tempfile.TemporaryDirectory() as tmp, patch.object(check, 'post', side_effect=AssertionError('network')), \
                patch.object(check.urllib.request, 'build_opener', side_effect=AssertionError('network')), \
                patch.object(check.os.environ, 'get', side_effect=guard_key):
            out = Path(tmp) / 'must_not_exist'
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(check.main(['--output', str(out)]), 0)
            report = json.loads(captured.getvalue())
            self.assertEqual(report['mode'], 'offline')
            self.assertFalse(report['live_tested'])
            self.assertFalse(out.exists())
            self.assertEqual(report['max_requests'], 12)
            self.assertEqual(len(report['slots']), 12)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
                check.main(['--help'])
            self.assertEqual(error.exception.code, 0)

    def test_live_requires_explicit_output_and_key(self):
        with patch.object(check, 'run_live', side_effect=AssertionError('live')), \
                patch.dict(check.os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            for args in (['--live'], ['--live', '--output', 'unused']):
                with self.assertRaises(SystemExit):
                    check.main(args)

    def test_complete_fixed_budget_preserves_prompt_settings_and_raw_records(self):
        for echo in (False, True):
            with self.subTest(echo=echo), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'new'
                fake = FakeTransport(echo=echo)
                report = check.run_live(out, 'SECRET_FIXTURE', fake)
                self.assertEqual(report['requests_attempted'], 12)
                self.assertEqual(sum(b['max_tokens'] for b in fake.calls), 1062)
                self.assertEqual(len(list(out.glob('*.response.bin'))), 12)
                for body in fake.calls:
                    self.assertEqual(body['messages'][0], dict(role='user', content=check.PROMPT))
                    self.assertEqual(sum(m['role'] == 'user' for m in body['messages']), 1)
                    self.assertEqual({k: body[k] for k in check.SETTINGS}, check.SETTINGS)
                    self.assertNotIn('prompt_mode', body)
                    self.assertNotIn('logit_bias', body)
                    if len(body['messages']) > 1:
                        self.assertTrue(body['messages'][1]['prefix'])
                        self.assertEqual(body['messages'][1]['role'], 'assistant')
                self.assertTrue(all(r['behavioral_replay'] for r in report['replays']))
                self.assertTrue(all(r['suffix_token_ids_equal'] for r in report['replays'] if r['unit'] == 'observed_tokens'))
                self.assertTrue(all(r['server_prefix_tail_ids_equal'] for r in report['replays'] if r['unit'] == 'observed_tokens'))
                self.assertTrue(report['study_2a']['complete_candidate_scores_observed'])
                for study in ('study_2a', 'study_2b'):
                    self.assertFalse(report[study]['protocol_compatible'])
                for candidate in report['candidates'].values():
                    self.assertEqual(candidate['logprob'], -0.75)  # Includes space AND newline.
                ctx = fake.calls[7]['messages'][-1]['content']
                self.assertEqual(fake.calls[6]['messages'][-1]['content'], ctx)
                self.assertEqual(fake.calls[8]['messages'][-1]['content'], ctx)
                for body, candidate in zip(fake.calls[9:], check.CANDIDATES.values()):
                    self.assertEqual(body['messages'][-1]['content'], ctx + candidate)
                for file in out.iterdir():
                    self.assertNotIn(b'SECRET_FIXTURE', file.read_bytes())
                    self.assertNotIn(b'NEVER_SAVE', file.read_bytes())
                with self.assertRaises(FileExistsError):
                    check.run_live(out, 'unused', fake)
                self.assertEqual(len(fake.calls), 12)

    def test_unsupported_probability_fields_do_not_prevent_plain_replay(self):
        fake = FakeTransport(reject=lambda b: b.get('logprobs') or b.get('prompt_logprobs'))
        with tempfile.TemporaryDirectory() as tmp:
            report = check.run_live(Path(tmp) / 'new', 'fixture', fake)
        self.assertEqual(report['requests_attempted'], 10)  # Two dependent token cuts skipped.
        self.assertTrue(all(r['behavioral_replay'] for r in report['replays']))
        self.assertFalse(report['study_2a']['complete_candidate_scores_observed'])
        self.assertTrue(all(v['logprob'] is None for v in report['candidates'].values()))

    def test_top_k_rejection_does_not_block_base_probability_fields(self):
        fake = FakeTransport(reject=lambda b: b.get('top_logprobs') or b.get('top_prompt_logprobs'))
        with tempfile.TemporaryDirectory() as tmp:
            report = check.run_live(Path(tmp) / 'new', 'fixture', fake)
        self.assertEqual(report['requests_attempted'], 12)
        self.assertTrue(report['study_2a']['complete_candidate_scores_observed'])
        self.assertEqual(sum(r['status'] == 'rejected_or_unusable' for r in report['records']), 2)

    def test_silently_ignored_probability_fields_remain_unavailable(self):
        class Ignored(FakeTransport):
            def __call__(self, body, key):
                status, headers, raw = super().__call__(body, key)
                data = json.loads(raw)
                data['choices'][0].pop('logprobs', None)
                data['choices'][0].pop('prompt_logprobs', None)
                return status, headers, json.dumps(data).encode()
        with tempfile.TemporaryDirectory() as tmp:
            report = check.run_live(Path(tmp) / 'new', 'fixture', Ignored())
        self.assertEqual(report['requests_attempted'], 10)
        self.assertFalse(report['study_2a']['complete_candidate_scores_observed'])
        self.assertEqual(report['records'][3]['probability_fields']['logprobs']['status'], 'not_returned')
        self.assertTrue(all(v['logprob'] is None for v in report['candidates'].values()))

    def test_auth_rate_server_redirect_and_transport_errors_never_retry(self):
        for status in (401, 403, 429, 500, 302):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                fake = FakeTransport(reject=lambda b: True, status=status)
                report = check.run_live(Path(tmp) / 'new', 'fixture', fake)
                self.assertEqual(len(fake.calls), 1)
                self.assertEqual(report['requests_attempted'], 1)
                self.assertEqual(len(report['records']), 12)
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def timeout(body, key):
                calls.append(body)
                raise TimeoutError('fixture')
            report = check.run_live(Path(tmp) / 'new', 'fixture', timeout)
            self.assertEqual(len(calls), 1)
            self.assertEqual(report['records'][0]['status'], 'transport_error')

    def test_budget_counts_attempts_and_raw_invalid_json_is_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            probe = check.Probe(out, 'fixture', lambda b, k: (200, {}, b'not json'))
            for i in range(12):
                self.assertIsNone(probe.call(str(i), check.payload()))
            with self.assertRaises(RuntimeError):
                probe.call('thirteenth', check.payload())
            self.assertEqual((out / '0.response.bin').read_bytes(), b'not json')
        self.assertIsNone(check.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))

    def test_token_identity_is_separate_from_text_and_probability(self):
        original = check.response_view(response(TEXT, rows(TEXT)))
        prefix, suffix = TEXT[:32], TEXT[32:]
        output, prompt = rows(suffix), rows('HEADER' + prefix)
        replay = check.response_view(response(suffix, output, prompt))
        output[0]['token_id'] += 1
        prompt[-1]['token_id'] += 1
        result = check.replay_report(original, replay, prefix, 32)
        self.assertTrue(result['behavioral_replay'])
        self.assertFalse(result['suffix_token_ids_equal'])
        self.assertFalse(result['server_prefix_tail_ids_equal'])
        self.assertFalse(result['full_distribution_equivalence'])

    def test_truncation_divergence_and_missing_telemetry_never_pass_full_replay(self):
        for finish in ('length', 'model_length', 'error'):
            a = check.response_view(response(TEXT, finish=finish))
            b = check.response_view(response(TEXT[32:], finish=finish))
            self.assertFalse(check.replay_report(a, b, TEXT[:32])['behavioral_replay'])
        a = check.response_view(response(TEXT))
        b = check.response_view(response('different'))
        self.assertFalse(check.replay_report(a, b, TEXT[:32])['behavioral_replay'])
        b = check.response_view(response(TEXT[32:]))
        result = check.replay_report(a, b, TEXT[:32], 32)
        self.assertTrue(result['behavioral_replay'])
        self.assertIsNone(result['suffix_token_ids_equal'])

    def test_unexpected_thinking_or_model_identity_is_not_accepted(self):
        for content in ('<think>hidden</think>text', [{'type': 'thinking', 'thinking': []}], None):
            self.assertIsNone(check.response_view(response(content)))
        self.assertIsNone(check.response_view(response('text', model='another-model')))
        self.assertIsNone(check.response_view(response('text', model='mistral-small-latest')))
        self.assertIsNotNone(check.response_view(response([{'type': 'text', 'text': 'hello'}])))

    def test_candidate_missing_top_k_is_unknown_not_zero_and_multitoken_is_summed(self):
        context = 'Saved prefix\nANSWER:'
        base = rows('HEADER' + context)
        base_view = check.response_view(response('x', prompt=base))
        for label, candidate in check.CANDIDATES.items():
            tail = rows(candidate)
            for row in tail:
                row['top_logprobs'] = [dict(token='unrelated', token_id=999, bytes=[120], logprob=-0.1)]
            view = check.response_view(response('x', prompt=base + tail))
            score = check.candidate_score(base_view, view, context, candidate)
            self.assertEqual(score['logprob'], -0.75)
            no_prompt = check.response_view(response(label, output=tail))
            self.assertIsNone(check.candidate_score(base_view, no_prompt, context, candidate)['logprob'])

    def test_candidate_alignment_and_probability_failures_are_closed(self):
        context, candidate = 'Saved prefix\nANSWER:', ' A\n'
        base = rows('HEADER' + context)
        base_view = check.response_view(response('x', prompt=base))
        bad = []
        changed = copy.deepcopy(base + rows(candidate)); changed[0]['token_id'] += 1; bad.append(changed)
        bad.append(base + rows(' A'))  # Missing newline.
        bad.append(base + rows(candidate + 'EOS'))
        bad.append(base[:-1] + [dict(token=': A\n', token_id=9999, bytes=list(b': A\n'), logprob=-0.3)])
        for value in (None, float('nan'), float('inf'), 0.1, True):
            changed = copy.deepcopy(base + rows(candidate)); changed[-1]['logprob'] = value; bad.append(changed)
        changed = copy.deepcopy(base + rows(candidate)); del changed[-1]['token_id']; bad.append(changed)
        for token_list in bad:
            view = check.response_view(response('x', prompt=token_list))
            self.assertIsNone(check.candidate_score(base_view, view, context, candidate)['logprob'])

    def test_bytes_are_authoritative_not_token_display_strings(self):
        context, candidate = 'Saved prefix\nANSWER:', ' A\n'
        base, tail = rows('HEADER' + context), rows(candidate)
        for row in base + tail:
            row['token'] = 'DISPLAY_ONLY'
        result = check.candidate_score(check.response_view(response('x', prompt=base)),
            check.response_view(response('x', prompt=base + tail)), context, candidate)
        self.assertEqual(result['logprob'], -0.75)
        tail[-1]['bytes'] = [256]
        self.assertIsNone(check.candidate_score(check.response_view(response('x', prompt=base)),
            check.response_view(response('x', prompt=base + tail)), context, candidate)['logprob'])

    def test_no_exact_generated_token_bytes_skips_token_cuts(self):
        class BadBytes(FakeTransport):
            def __call__(self, body, key):
                status, headers, raw = super().__call__(body, key)
                data = json.loads(raw)
                if body.get('logprobs'):
                    data['choices'][0]['logprobs']['content'][0]['bytes'] = [120]
                return status, headers, json.dumps(data).encode()
        with tempfile.TemporaryDirectory() as tmp:
            report = check.run_live(Path(tmp) / 'new', 'fixture', BadBytes())
            context = json.loads((Path(tmp) / 'new' / 'scoring-context.json').read_text())
        self.assertEqual(report['requests_attempted'], 10)
        self.assertEqual(context['unit'], 'characters_not_protocol_tokens')
        self.assertTrue(all(r['unit'] == 'characters' for r in report['replays']))


if __name__ == '__main__':
    unittest.main()
