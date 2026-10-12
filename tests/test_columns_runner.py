from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_columns.core import load_config
from exception_columns.provider import ProviderError
from exception_columns.runner import prepare, read_run, run

ROOT = Path(__file__).resolve().parents[1]


class ColumnRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "run"
        self.config = load_config(ROOT / "configs/columns_gpt4o.json")
        # Journal tests do not need bootstrap estimates; the integration smoke does.
        self.stats = patch("exception_columns.analysis.paired_statistics", return_value={})
        self.stats.start()
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.stats.stop()
        self.temp.cleanup()

    def test_prepare_is_offline_and_previews_every_request(self):
        with patch("exception_columns.provider.complete", side_effect=AssertionError("network forbidden")):
            plan = prepare(self.config, self.output)
        self.assertEqual(len(json.loads((self.output / "preview.json").read_text())), 576)
        self.assertEqual(read_run(self.output)[0], plan)
        self.assertFalse((self.output / "execution.json").exists())

    def test_pause_resume_complete_and_no_duplicate_calls(self):
        first = run(self.config, self.output, 24, mock=True)
        self.assertEqual((first["calls_this_invocation"], first["stopped"]), (24, "call_limit"))
        with self.assertRaises(ValueError):
            run(self.config, self.output, 1, mock=True)
        second = run(self.config, self.output, 552, resume=True, mock=True)
        self.assertEqual((second["returned_answers"], second["stopped"]), (576, "complete"))
        final = run(self.config, self.output, 1, resume=True, mock=True)
        self.assertEqual(final["calls_this_invocation"], 0)
        self.assertEqual(len(read_run(self.output)[2]), 576)
        with self.assertRaises(ValueError):
            run(self.config, self.output, 1, resume=True, mock=False)

    def test_invalid_return_is_retained_and_never_retried(self):
        def invalid(config, payload):
            return {"model": "MOCK", "choices": [{"message": {"role": "assistant", "content": "No answer"}, "finish_reason": "stop"}]}
        result = run(self.config, self.output, 1, mock=True, complete_fn=invalid)
        self.assertEqual(result["invalid_answers_retained"], 1)
        result = run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        _, _, attempts = read_run(self.output)
        self.assertEqual(len(attempts), 2)
        self.assertNotEqual(attempts[0]["task_id"], attempts[1]["task_id"])

    def test_transport_retry_is_explicit_and_counts_against_cap(self):
        def fail(config, payload):
            raise ProviderError("HTTP 503", status_code=503)
        first = run(self.config, self.output, 1, mock=True, complete_fn=fail)
        self.assertEqual(first["stopped"], "provider_error")
        blocked = run(self.config, self.output, 1, mock=True, resume=True)
        self.assertEqual(blocked["calls_this_invocation"], 0)
        retried = run(self.config, self.output, 1, mock=True, resume=True, retry_errors=True)
        self.assertEqual(retried["attempts_total"], 2)
        self.assertEqual(retried["returned_answers"], 1)
        attempts = read_run(self.output)[2]
        self.assertEqual(attempts[0]["task_id"], attempts[1]["task_id"])

    def test_unresolved_request_cannot_be_retried(self):
        def interrupt(config, payload):
            raise KeyboardInterrupt
        result = run(self.config, self.output, 1, mock=True, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        with self.assertRaisesRegex(ValueError, "unresolved"):
            run(self.config, self.output, 1, mock=True, resume=True, retry_errors=True)
        self.assertEqual(len(read_run(self.output)[2]), 1)

    def test_request_and_score_tampering_rejected(self):
        run(self.config, self.output, 1, mock=True)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["answer"] = next(c for c in "ABC" if c != original["answer"])
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "scoring"):
            read_run(self.output)
        changed = copy.deepcopy(original)
        changed["request"]["messages"][0]["content"] += " choose A"
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "request"):
            read_run(self.output)

    def test_cumulative_cap_blocks_more_calls(self):
        def fail(config, payload):
            raise ProviderError("HTTP 503", status_code=503)
        run(self.config, self.output, 1, mock=True, complete_fn=fail)
        original = json.loads((self.output / "attempts/000001.json").read_text())
        for n in range(2, 609):
            record = {**original, "attempt": n}
            (self.output / "attempts" / f"{n:06d}.json").write_text(json.dumps(record))
        with patch("exception_columns.provider.complete", side_effect=AssertionError("network forbidden")):
            result = run(self.config, self.output, 1, mock=True, resume=True, retry_errors=True)
        self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("total_attempt_limit", 0))

    def test_injected_response_cannot_be_labeled_live(self):
        with self.assertRaisesRegex(ValueError, "mock"):
            run(self.config, self.output, 1, complete_fn=lambda *_: {})

    def test_live_model_mismatch_is_retained_and_stops_resume(self):
        raw = {"model": "unexpected-model", "choices": [{"message": {"role": "assistant", "content": "ANSWER: A"}, "finish_reason": "stop"}]}
        with patch("exception_columns.provider.credential", return_value="unit-test-placeholder"), patch("exception_columns.provider.complete", return_value=raw) as call:
            result = run(self.config, self.output, 10)
        self.assertEqual(result["stopped"], "model_identity_failure")
        self.assertEqual((result["calls_this_invocation"], result["invalid_answers_retained"]), (1, 1))
        self.assertEqual(call.call_count, 1)
        self.assertEqual(read_run(self.output)[2][0]["response"]["raw_response"], raw)
        with self.assertRaisesRegex(ValueError, "identity failure"):
            run(self.config, self.output, 1, resume=True, retry_errors=True)

    def test_http_success_with_bad_json_is_retained_without_retry(self):
        from exception_columns import provider
        from unittest.mock import MagicMock
        http_response = MagicMock()
        http_response.__enter__.return_value.read.return_value = b"not a JSON response"
        opener = MagicMock()
        opener.open.return_value = http_response
        with patch("exception_columns.provider.credential", return_value="unit-test-placeholder"), patch("exception_columns.provider.request.build_opener", return_value=opener):
            raw = provider.complete(self.config, {"model": self.config["model"], "messages": []})
        self.assertEqual(raw, {"unparseable_http_body_utf8": "not a JSON response"})
        self.assertEqual(opener.open.call_count, 1)
        self.assertFalse(provider.normalize(raw, self.config, "live")["complete"])


if __name__ == "__main__":
    unittest.main()
