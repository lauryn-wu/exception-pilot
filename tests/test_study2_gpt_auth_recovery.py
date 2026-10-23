"""Offline recovery tests; no credentials, GPU, or real API requests."""
import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from test_study2_gpt_explanation import ARCHIVE, MockTransport, response
from exception_pilot.core import digest
from exception_review.artifacts import freeze, sha
from exception_study2_gpt_explanation.planning import Context, prepare, contract
from exception_study2_gpt_explanation import execution as legacy
import exception_study2_gpt_auth_recovery as recovery


def rejected(status=401, code='invalid_api_key', **extra):
    body = {'error': {'code': code, 'type': 'invalid_request_error',
                      'message': 'Deterministic offline authentication fixture.'}, **extra}
    return {'status': status, 'body': json.dumps(body), 'request_id': 'req_auth_fixture'}


class AuthenticationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.base_temp.name) / 'base'
        prepare(ARCHIVE, cls.base)
        cls.requests = Context(cls.base).requests
        cls.answers = {r['cell']['prompt']: r['cell']['expected'] for r in cls.requests}

    @classmethod
    def tearDownClass(cls):
        cls.base_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / 'run'
        shutil.copytree(self.base, self.out)

    def tearDown(self):
        self.temp.cleanup()

    def answer(self, payload):
        prompt = payload['input'][0]['content']
        label = self.answers[prompt]
        text = 'The supplied record gives this class.\n' + label if 'Write your reasoning' in prompt else label
        return response(text)['response']

    def original(self, *, fail_at=5, failure=None, live=False):
        failure = rejected() if failure is None else failure
        def callback(n, payload):
            if n == fail_at:
                if isinstance(failure, BaseException):
                    raise failure
                return failure
            return self.answer(payload)
        transport = MockTransport(callback)
        with contextlib.redirect_stdout(io.StringIO()):
            if live:
                with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-fixture-key'}), \
                     patch.object(legacy, 'HTTPTransport', return_value=transport):
                    value = legacy.run(self.out, live=True, max_new=192)
            else:
                value = legacy.run(self.out, max_new=192, _transport=transport)
        return value, transport

    def recovered(self, transport=None, max_new=192):
        transport = transport or MockTransport(lambda n, p: self.answer(p))
        with contextlib.redirect_stdout(io.StringIO()):
            value = recovery.run(self.out, max_new=max_new, _transport=transport)
        return value, transport

    def protected_hashes(self):
        names = {'plan.json', 'source-validation.json', 'execution.json'}
        roots = {'source-evidence', 'operations-v5', 'dispatches', 'responses', 'invocations'}
        return {str(p.relative_to(self.out)): sha(p) for p in self.out.rglob('*')
                if p.is_file() and (p.name in names or p.relative_to(self.out).parts[0] in roots)}

    def assert_originals_preserved(self, before):
        for name, value in before.items():
            self.assertTrue((self.out / name).exists(), name)
            self.assertEqual(sha(self.out / name), value, name)

    def test_four_saved_one_rejected_then_192_combined_without_repeating_answers(self):
        initial, old = self.original()
        self.assertEqual(initial['totals']['completed'], 4)
        self.assertEqual(initial['totals']['failed'], 1)
        self.assertEqual(initial['totals']['pending'], 187)
        original_contract = contract()
        protected = self.protected_hashes()

        final, new = self.recovered()
        self.assertTrue(final['complete'])
        self.assertEqual(final['totals']['completed'], 192)
        self.assertEqual(final['totals']['scientific_dispatches'], 193)
        self.assertEqual(final['totals']['pending'], 0)
        self.assertEqual(final['totals']['failed'], 0)
        self.assertEqual(final['totals']['ambiguous'], 0)
        self.assertEqual(len(new.calls), 188)
        self.assertEqual(new.calls[0], old.calls[4])
        for payload in old.calls[:4]:
            self.assertNotIn(payload, new.calls)
        self.assertEqual(len({digest(p) for p in old.calls[:4] + new.calls}), 192)
        self.assertEqual(final['primary']['estimate'], 0)
        retried = [r for r in final['cases'] if r.get('selected_attempt') == 'authentication_retry']
        self.assertEqual(len(retried), 1)
        self.assertEqual(retried[0]['cell']['id'], self.requests[4]['cell']['id'])
        self.assertTrue(retried[0]['original_operation_hash'])
        self.assert_originals_preserved(protected)
        self.assertEqual(contract(), original_contract)
        # The legacy interpretation remains intact and sees its original held failure.
        legacy_value = legacy.inspect(self.out)
        self.assertEqual(legacy_value['totals']['completed'], 191)
        self.assertEqual(legacy_value['totals']['failed'], 1)

    def test_retry_counts_toward_invocation_cap_and_is_never_repeated(self):
        initial, old = self.original()
        partial, first = self.recovered(max_new=1)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(first.calls[0], old.calls[4])
        self.assertEqual(partial['totals']['completed'], 5)
        self.assertEqual(partial['totals']['pending'], 187)
        final, rest = self.recovered()
        self.assertTrue(final['complete'])
        self.assertEqual(len(rest.calls), 187)
        self.assertNotIn(first.calls[0], rest.calls)
        completed, no_calls = self.recovered()
        self.assertTrue(completed['complete'])
        self.assertEqual(no_calls.calls, [])
        self.assertEqual(completed['this_invocation']['new_dispatches'], 0)

    def test_completed_live_resume_needs_no_key_or_transport(self):
        self.original(live=True)
        transport = MockTransport(lambda n, p: self.answer(p))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-fixture-key'}), \
             patch.object(recovery, 'HTTPTransport', return_value=transport), \
             patch.object(legacy, 'HTTPTransport', return_value=transport), \
             contextlib.redirect_stdout(io.StringIO()):
            result = recovery.run(self.out, live=True)
        self.assertTrue(result['complete'])
        self.assertEqual(len(transport.calls), 188)
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(recovery, 'HTTPTransport', side_effect=AssertionError('network')), \
             patch.object(legacy, 'HTTPTransport', side_effect=AssertionError('network')):
            again = recovery.run(self.out, live=True)
        self.assertTrue(again['complete'])
        self.assertEqual(again['this_invocation']['new_dispatches'], 0)

    def test_offline_commands_do_not_authorize_or_dispatch(self):
        self.original()
        with patch.object(recovery, 'HTTPTransport', side_effect=AssertionError('network')), \
             patch.object(legacy, 'HTTPTransport', side_effect=AssertionError('network')):
            result = recovery.run(self.out)
            value = recovery.inspect(self.out)
        self.assertEqual(result['this_invocation']['new_dispatches'], 0)
        self.assertEqual(value['totals']['completed'], 4)
        self.assertFalse((self.out / 'auth-recovery-v1' / 'amendment.json').exists())

    def test_other_errors_and_generation_evidence_are_never_retried(self):
        fixtures = [rejected(status=429), rejected(code='organization_deactivated'),
                    rejected(status=500), rejected(output=[{'type': 'message'}]),
                    rejected(id='resp_unexpected'), TimeoutError('offline timeout')]
        for index, failure in enumerate(fixtures):
            with self.subTest(index=index):
                if index:
                    shutil.rmtree(self.out)
                    shutil.copytree(self.base, self.out)
                initial, old = self.original(fail_at=1, failure=failure)
                self.assertEqual(initial['totals']['failed'], 1)
                transport = MockTransport(lambda n, p: self.answer(p))
                try:
                    self.recovered(transport, max_new=1)
                except ValueError:
                    pass  # Ineligible failures may block the wrapper before any dispatch.
                self.assertNotIn(old.calls[0], transport.calls)
                self.assertEqual(transport.calls, [])
                self.assertEqual(legacy.inspect(self.out)['totals']['failed'], 1)

    def test_ambiguous_original_is_held_without_retry(self):
        c = Context(self.out)
        r = c.requests[0]
        binding = legacy.binding(c, 'MOCK')
        freeze(self.out / 'execution.json', binding)
        identity = dict(binding, id=legacy.opid(r), request=r['request'],
                        request_hash=r['request_hash'], stage=legacy.STAGE)
        folder = self.out / 'operations-v5' / digest(legacy.opid(r))
        freeze(folder / 'request.json', dict(identity, status='planned'))
        freeze(folder / 'started.json', dict(identity, status='started'))
        transport = MockTransport(lambda n, p: self.answer(p))
        try:
            self.recovered(transport, max_new=1)
        except ValueError:
            pass
        self.assertEqual(transport.calls, [])
        self.assertEqual(legacy.inspect(self.out)['totals']['ambiguous'], 1)

    def test_returned_invalid_retry_is_preserved_and_not_resampled(self):
        self.original()
        invalid = MockTransport(lambda n, p: response('Not an allowed final label')['response'])
        partial, first = self.recovered(invalid, max_new=1)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(partial['totals']['completed'], 5)
        selected = next(r for r in partial['cases'] if r.get('selected_attempt') == 'authentication_retry')
        self.assertFalse(selected['score']['valid'])
        final, rest = self.recovered()
        self.assertTrue(final['complete'])
        self.assertNotIn(first.calls[0], rest.calls)
        selected = next(r for r in final['cases'] if r.get('selected_attempt') == 'authentication_retry')
        self.assertEqual(selected['score']['category'], 'invalid_format')

    def test_returned_invalid_original_is_preserved_and_not_resampled(self):
        def callback(n, payload):
            if n == 1:
                return response('Not an allowed final label')['response']
            if n == 5:
                return rejected()
            return self.answer(payload)
        original = MockTransport(callback)
        with contextlib.redirect_stdout(io.StringIO()):
            legacy.run(self.out, max_new=192, _transport=original)
        protected = self.protected_hashes()
        final, new = self.recovered()
        self.assertTrue(final['complete'])
        self.assertNotIn(original.calls[0], new.calls)
        saved = next(r for r in final['cases'] if r['cell']['id'] == self.requests[0]['cell']['id'])
        self.assertEqual(saved['selected_attempt'], 'original')
        self.assertEqual(saved['score']['category'], 'invalid_format')
        self.assert_originals_preserved(protected)

    def test_receipt_before_terminal_crash_is_held_without_resampling(self):
        from exception_study2_v5 import journal
        self.original()
        protected = self.protected_hashes()
        real_freeze = journal.freeze
        def interrupt_terminal(path, value):
            path = Path(path)
            if path.name == 'returned.json' and 'auth-recovery-v1' in path.parts:
                raise KeyboardInterrupt('Simulated crash after receipt and before terminal seal')
            return real_freeze(path, value)
        first = MockTransport(lambda n, p: self.answer(p))
        with patch.object(journal, 'freeze', side_effect=interrupt_terminal):
            with self.assertRaises(KeyboardInterrupt):
                self.recovered(first, max_new=1)
        self.assertEqual(len(first.calls), 1)
        receipts = list((self.out / 'auth-recovery-v1' / 'responses').glob('*.json'))
        self.assertEqual(len(receipts), 1)
        value = recovery.inspect(self.out)
        self.assertEqual(value['totals']['completed'], 4)
        self.assertEqual(value['totals']['ambiguous'], 1)
        self.assertEqual(value['totals']['scientific_dispatches'], 6)
        again = MockTransport(lambda n, p: self.answer(p))
        try:
            self.recovered(again)
        except ValueError:
            pass
        self.assertEqual(again.calls, [])
        self.assert_originals_preserved(protected)

    def test_failed_retry_is_held_and_stops_before_other_requests(self):
        self.original()
        protected = self.protected_hashes()
        failed = MockTransport(lambda n, p: rejected())
        result, transport = self.recovered(failed)
        self.assertEqual(len(transport.calls), 1)
        self.assertFalse(result['complete'])
        self.assertEqual(result['totals']['completed'], 4)
        self.assertEqual(result['totals']['pending'], 187)
        self.assertEqual(result['totals']['scientific_dispatches'], 6)
        again = MockTransport(lambda n, p: self.answer(p))
        try:
            self.recovered(again)
        except ValueError:
            pass
        self.assertEqual(again.calls, [])
        self.assert_originals_preserved(protected)

    def test_export_is_portable_and_contains_both_attempts(self):
        self.original()
        self.recovered()
        destination = self.root / 'combined.zip'
        result = recovery.export(self.out, destination)
        self.assertTrue(result['complete'])
        with zipfile.ZipFile(destination) as archive:
            names = set(archive.namelist())
            self.assertTrue(any(n.startswith('auth-recovery-v1/') for n in names))
            manifest = json.loads(archive.read('bundle-manifest.json'))
            self.assertEqual(names, set(manifest['files']) | {'bundle-manifest.json'})
            for name, info in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), info['sha256'])
            analysis = json.loads(archive.read('analysis.json'))
            self.assertTrue(analysis['complete'])
            self.assertEqual(analysis['totals']['completed'], 192)
            self.assertEqual(analysis['totals']['scientific_dispatches'], 193)
            rows = list(csv.DictReader(io.StringIO(archive.read('manual-review.csv').decode())))
            self.assertEqual(len(rows), 192)
            self.assertTrue(all(r['correct_record_mention'] == 'not_reviewed' for r in rows))
            relocated = self.root / 'relocated'
            archive.extractall(relocated)
        moved = recovery.inspect(relocated)
        self.assertTrue(moved['complete'])
        self.assertEqual(moved['totals']['completed'], 192)
        self.assertEqual(moved['primary'], analysis['primary'])


if __name__ == '__main__':
    unittest.main()
