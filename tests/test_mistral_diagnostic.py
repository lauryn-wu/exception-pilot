"""Offline tests: bounded error diagnostics must not alter the frozen experiment."""

from contextlib import redirect_stdout
from email.message import Message
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib import error, request

import mistral_diagnostic as diagnostic
from exception_mistral_prefix import core, provider, runner


ROOT = Path(__file__).resolve().parents[1]
KEY = "fixture-key-do-not-print-0123456789"


def config():
    return core.load_config(ROOT / "configs/mistral_prefix.json")


def raw_response(text="Cobalt Maple Lantern"):
    return {
        "id": "offline-diagnostic-fixture",
        "model": "mistral-small-2603-fixture",
        "usage": {"prompt_tokens": 18, "completion_tokens": 3, "total_tokens": 21},
        "choices": [{"message": {"role": "assistant", "content": text},
                     "finish_reason": "stop"}],
    }


class TrackingBody(io.BytesIO):
    def __init__(self, body, fail=False):
        super().__init__(body)
        self.read_sizes = []
        self.fail = fail

    def read(self, size=-1):
        self.read_sizes.append(size)
        if self.fail:
            raise OSError("untrusted-read-error-" + KEY)
        return super().read(size)


def http_error(body, fail=False):
    headers = Message()
    headers["Retry-After"] = "60"
    headers["X-Untrusted-Header"] = "do-not-copy-headers"
    stream = TrackingBody(body, fail)
    exc = error.HTTPError(core.ENDPOINT, 429, "Too Many Requests", headers, stream)
    return exc, stream


class Transport:
    """One prepared outcome per open; an unexpected retry fails the test."""
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.handlers = []

    def build_opener(self, *handlers):
        self.handlers.append(tuple(type(handler).__name__ for handler in handlers))
        return self

    def open(self, req, *, timeout):
        self.calls.append({"url": req.full_url, "method": req.get_method(),
                           "body": req.data, "headers": dict(req.header_items()),
                           "timeout": timeout})
        if not self.outcomes:
            raise AssertionError("Unexpected extra request / hidden retry")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return io.BytesIO(outcome)

    @property
    def request_api(self):
        return SimpleNamespace(Request=request.Request, build_opener=self.build_opener)


class MistralDiagnosticDetailsTests(unittest.TestCase):
    def test_allowlisted_root_and_nested_fields_redact_credentials_and_preserve_retry_after(self):
        body = {"message": "quota exhausted for " + KEY, "type": "rate_limit",
                "code": "monthly_limit", "param": None,
                "detail": {"not_scalar": "do-not-copy-dict"},
                "unknown": "do-not-copy-unknown",
                "error": {"message": "Bearer " + KEY, "type": "quota",
                          "code": 429, "detail": "Organization quota exceeded",
                          "unknown": "do-not-copy-nested-unknown"},
                "request_headers": {"Authorization": "Bearer " + KEY}}
        exc, stream = http_error(json.dumps(body).encode())
        details = diagnostic.safe_http_details(exc, KEY)
        encoded = json.dumps(details)
        self.assertIsInstance(details, dict)
        self.assertIn("quota", encoded)
        self.assertIn("Organization quota exceeded", encoded)
        self.assertIn("60", encoded)
        self.assertNotIn(KEY, encoded)
        for forbidden in ("do-not-copy", "request_headers", "Authorization"):
            self.assertNotIn(forbidden, encoded)
        self.assertTrue(stream.read_sizes)
        self.assertTrue(all(0 < size <= 16385 for size in stream.read_sizes))
        root_only = dict(body)
        del root_only["error"]
        root_exc, _ = http_error(json.dumps(root_only).encode())
        root_encoded = json.dumps(diagnostic.safe_http_details(root_exc, KEY))
        self.assertIn("monthly_limit", root_encoded)
        self.assertIn("quota exhausted for", root_encoded)
        self.assertNotIn(KEY, root_encoded)
        self.assertNotIn("do-not-copy", root_encoded)

    def test_bad_json_html_and_read_failure_do_not_echo_body_or_exception(self):
        for body, fail in ((b"<html>do-not-copy-HTML-" + KEY.encode() + b"</html>", False),
                           (b'{"message":', False),
                           (b"", True)):
            with self.subTest(body=body, fail=fail):
                exc, stream = http_error(body, fail)
                details = diagnostic.safe_http_details(exc, KEY)
                encoded = json.dumps(details)
                self.assertNotIn(KEY, encoded)
                self.assertNotIn("do-not-copy-HTML", encoded)
                self.assertNotIn("untrusted-read-error", encoded)
                self.assertIn("60", encoded)
                self.assertTrue(all(0 < size <= 16385 for size in stream.read_sizes))

    def test_large_error_body_is_read_with_a_fixed_bound(self):
        exc, stream = http_error(b"x" * 100000)
        diagnostic.safe_http_details(exc, KEY)
        self.assertEqual(len(stream.read_sizes), 1)
        # One sentinel byte beyond the 16KiB accepted-body bound detects truncation.
        self.assertLessEqual(stream.read_sizes[0], 16385)
        self.assertGreater(stream.read_sizes[0], 0)

    def test_credentials_are_redacted_before_message_length_truncation(self):
        long_key = "begin-sensitive-key-" + "x" * 1500 + "-end-sensitive-key"
        body = {"message": "Rate limit: " + long_key + " Please try later."}
        exc, _ = http_error(json.dumps(body).encode())
        encoded = json.dumps(diagnostic.safe_http_details(exc, long_key))
        self.assertNotIn("begin-sensitive-key", encoded)
        self.assertNotIn("end-sensitive-key", encoded)
        self.assertIn("Rate limit:", encoded)


class MistralDiagnosticTransportTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.plan = core.make_plan(self.cfg)
        self.payload = core.request_for(self.plan, self.plan["tasks"][0])

    def test_error_keeps_http_status_and_adds_only_safe_diagnostics_without_retry(self):
        exc, stream = http_error(json.dumps({"message": "Monthly quota reached " + KEY,
                                            "code": "monthly_quota"}).encode())
        transport = Transport([exc])
        request_api = transport.request_api
        with patch.object(provider, "credential", return_value=KEY), \
             patch.object(provider, "request", request_api):
            with self.assertRaises(provider.ProviderError) as caught:
                diagnostic.complete_with_diagnostics(self.cfg, self.payload)
            self.assertIs(provider.request, request_api)
        self.assertEqual(caught.exception.status_code, 429)
        self.assertIn("HTTP 429", str(caught.exception))
        self.assertIn("Monthly quota reached", str(caught.exception))
        self.assertIn("monthly_quota", str(caught.exception))
        self.assertIn("60", str(caught.exception))
        self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(stream.closed)

    def test_success_normalization_and_every_transport_argument_match_original(self):
        raw = raw_response()
        raw["choices"][0]["message"]["content"] = [
            {"type": "text", "text": "Cobalt Ma"},
            {"type": "text", "text": "ple Lantern"},
        ]
        raw["extra_telemetry"] = {"retained": "exactly"}
        body = json.dumps(raw, ensure_ascii=False).encode()
        original = Transport([body])
        wrapped = Transport([body])
        with patch.object(provider, "credential", return_value=KEY), \
             patch.object(provider, "request", original.request_api):
            expected = provider.complete(self.cfg, self.payload)
        request_api = wrapped.request_api
        with patch.object(provider, "credential", return_value=KEY), \
             patch.object(provider, "request", request_api):
            actual = diagnostic.complete_with_diagnostics(self.cfg, self.payload)
            self.assertIs(provider.request, request_api)
        self.assertEqual(json.dumps(actual), json.dumps(expected))
        self.assertEqual(actual, provider.normalize(raw))
        self.assertEqual(wrapped.calls, original.calls)
        self.assertEqual(wrapped.handlers, original.handlers)
        self.assertEqual(len(wrapped.calls), 1)


class MistralDiagnosticJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"
        self.cfg = config()

    def start_failed_run(self):
        with patch.object(provider, "credential", return_value=KEY), \
             patch.object(provider, "complete", side_effect=provider.ProviderError("HTTP 429", status_code=429)), \
             redirect_stdout(io.StringIO()):
            result = runner.run(self.cfg, self.output, max_calls=1)
        self.assertEqual(result["attempts_total"], 1)
        return {path.relative_to(self.output): path.read_bytes() for path in self.output.rglob("*")
                if path.is_file() and (path.parent.name == "attempts" or path.name in ("plan.json", "execution.json"))}

    def invoke(self, transport):
        original_complete = provider.complete
        request_api = transport.request_api
        with patch.object(provider, "credential", return_value=KEY), \
             patch.object(provider, "request", request_api), redirect_stdout(io.StringIO()):
            result = diagnostic.run_once(self.cfg, self.output)
            self.assertIs(provider.complete, original_complete)
            self.assertIs(provider.request, request_api)
        return result

    def test_one_failed_diagnostic_then_one_success_keeps_plan_and_attempts_immutable(self):
        before = self.start_failed_run()
        exc, _ = http_error(json.dumps({"message": "quota " + KEY, "code": "quota_exceeded"}).encode())
        failing = Transport([exc])
        error_result = self.invoke(failing)
        self.assertEqual((error_result["stopped"], error_result["calls_this_invocation"],
                          error_result["attempts_total"]), ("provider_error", 1, 2))
        self.assertEqual(len(failing.calls), 1)
        failed_path = self.output / "attempts/000002.json"
        failed_bytes = failed_path.read_bytes()
        failed_record = json.loads(failed_bytes)
        self.assertEqual((failed_record["status"], failed_record["http_status"]), ("error", 429))
        self.assertNotIn("response", failed_record)
        self.assertIn("quota_exceeded", failed_record["error"])
        self.assertNotIn(KEY, failed_bytes.decode())
        successful = Transport([json.dumps(raw_response()).encode()])
        result = self.invoke(successful)
        self.assertEqual((result["calls_this_invocation"], result["attempts_total"],
                          result["returned_answers"], result["valid_answers"]), (1, 3, 1, 1))
        self.assertEqual(result["capability_gate"]["status"], "pass")
        self.assertEqual(len(successful.calls), 1)
        for relative, previous in before.items():
            self.assertEqual((self.output / relative).read_bytes(), previous)
        self.assertEqual(failed_path.read_bytes(), failed_bytes)
        plan, _, attempts = runner.read_run(self.output, "live")
        self.assertEqual(len(attempts), 3)
        self.assertTrue(all(attempt["plan_hash"] == plan["plan_hash"] for attempt in attempts))

    def test_returned_invalid_response_is_retained_and_terminal(self):
        self.start_failed_run()
        transport = Transport([json.dumps(raw_response("ple Lantern")).encode()])
        result = self.invoke(transport)
        self.assertEqual((result["returned_answers"], result["invalid_answers_retained"]), (1, 1))
        path = self.output / "attempts/000002.json"
        previous = path.read_bytes()
        self.assertEqual(json.loads(previous)["status"], "invalid")
        forbidden = Transport([])
        with self.assertRaises(ValueError):
            self.invoke(forbidden)
        self.assertEqual(forbidden.calls, [])
        self.assertEqual(path.read_bytes(), previous)
        self.assertEqual(len(list((self.output / "attempts").glob("*.json"))), 2)

    def test_missing_existing_run_is_rejected_without_creating_files_or_calling_provider(self):
        transport = Transport([])
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.invoke(transport)
        self.assertEqual(transport.calls, [])
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
