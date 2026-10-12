"""Offline integration checks for the retained-response row-position journal."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.storage import write_json
from exception_row_position import core, provider, runner
from exception_row_position.__main__ import main


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "row_position_mistral.json"


def raw_response(text, model="MOCK-NOT-A-MODEL", finish="stop"):
    return {"model": model, "usage": {}, "choices": [{
        "message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


class RowPositionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.cfg = core.load_config(CONFIG_PATH)
        self.socket_patch = patch.object(socket.socket, "connect",
                                        side_effect=AssertionError("No network in tests"))
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def run_quiet(self, max_calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return runner.run(self.cfg, self.output, max_calls, **kwargs)

    def test_prepare_offline_preview_and_source_identity(self):
        with patch.object(provider, "credential", side_effect=AssertionError("Prepare must not need key")):
            plan = runner.prepare(self.cfg, self.output)
        self.assertEqual(len(plan["tasks"]), 288)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 288)
        self.assertEqual((self.output / "preview.md").read_text().count("\n## "), 12)
        self.assertEqual(runner.prepare(self.cfg, self.output), plan)
        with self.assertRaisesRegex(ValueError, "Config differs"):
            runner.prepare(dict(self.cfg, api_key_env="OTHER_TEST_KEY"), self.output)
        with patch.object(core, "source_digest", return_value="changed"):
            with self.assertRaises(ValueError):
                runner.read_run(self.output)

    def test_mock_full_schedule_resume_and_live_mode_separation(self):
        first = self.run_quiet(12, mock=True)
        self.assertEqual(first["calls_this_invocation"], 12)
        self.assertEqual(first["stopped"], "call_limit")
        with self.assertRaisesRegex(ValueError, "already started"):
            self.run_quiet(1, mock=True)
        resumed = self.run_quiet(288, resume=True, mock=True)
        self.assertEqual(resumed["calls_this_invocation"], 276)
        self.assertEqual(resumed["returned_answers"], 288)
        self.assertEqual(resumed["attempts_total"], 288)
        self.assertEqual(resumed["decision"], "simulated_only")
        self.assertTrue(resumed["is_simulated"])
        self.assertIn("SIMULATED", (self.output / "summary.md").read_text())
        self.assertEqual(self.run_quiet(288, resume=True, mock=True)["calls_this_invocation"], 0)
        with self.assertRaisesRegex(ValueError, "identity or run mode"):
            self.run_quiet(1, resume=True)

    def test_invalid_response_is_terminal_and_not_resampled(self):
        def invalid(cfg, payload):
            return provider.normalize(raw_response("Unparseable returned response"), cfg, "mock")

        result = self.run_quiet(3, mock=True, complete_fn=invalid)
        self.assertEqual(result["invalid_answers_retained"], 3)
        before = [(self.output / "attempts" / f"{i:06d}.json").read_bytes() for i in range(1, 4)]
        result = self.run_quiet(288, resume=True, retry_errors=True, mock=True)
        self.assertEqual(result["calls_this_invocation"], 285)
        self.assertEqual(result["invalid_answers_retained"], 3)
        self.assertEqual(before, [(self.output / "attempts" / f"{i:06d}.json").read_bytes()
                                  for i in range(1, 4)])

    def test_transport_error_requires_explicit_retry(self):
        def fail(cfg, payload):
            raise provider.ProviderError("SyntheticTimeout")

        result = self.run_quiet(12, mock=True, complete_fn=fail)
        self.assertEqual(result["stopped"], "provider_error")
        self.assertEqual(result["calls_this_invocation"], 1)
        self.assertEqual(self.run_quiet(1, resume=True, mock=True)["stopped"], "retry_requires_flag")
        result = self.run_quiet(1, resume=True, retry_errors=True, mock=True)
        self.assertEqual(result["attempts_total"], 2)
        self.assertEqual(result["returned_answers"], 1)

    def test_model_mismatch_stops_and_cannot_be_retried(self):
        def wrong_model(cfg, payload):
            return provider.normalize(raw_response("ANSWER: A", "WRONG-MODEL"), cfg, "mock")

        result = self.run_quiet(12, mock=True, complete_fn=wrong_model)
        self.assertEqual(result["stopped"], "model_mismatch")
        self.assertEqual(result["calls_this_invocation"], 1)
        self.assertEqual(result["invalid_answers_retained"], 1)
        with self.assertRaisesRegex(ValueError, "hard stop"):
            self.run_quiet(12, resume=True, retry_errors=True, mock=True)

    def test_missing_model_identity_blocks_live_decision(self):
        from exception_row_position.analysis import summarize

        # In-memory synthetic data exercises live identity rules; no live files
        # or provider calls are made, and nothing becomes scientific evidence.
        plan = core.make_plan(self.cfg)
        attempts = []
        for number, task in enumerate(plan["tasks"], 1):
            meta = core.task_meta(plan, task)
            pretext = "Synthetic fixture reasoning.\n" if task["arm"] == "visible" else ""
            raw = raw_response(pretext + "ANSWER: " + meta["expected"], self.cfg["model"])
            if number == 1:
                del raw["model"]
            response = provider.normalize(raw, self.cfg, "live")
            attempts.append({"attempt": number, "task_id": task["id"], "meta": meta,
                             "response": response, **core.score_response(task, response)})
        summary = summarize(plan, self.cfg, {"mode": "live"}, attempts)
        self.assertEqual(summary["returned_answers"], 288)
        self.assertEqual(summary["invalid_answers"], 1)
        self.assertEqual(summary["model_identity_failures"], 1)
        self.assertEqual(summary["decision"], "model_identity_failure")

    def test_interrupted_request_remains_unresolved(self):
        def interrupt(cfg, payload):
            raise KeyboardInterrupt

        result = self.run_quiet(1, mock=True, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        self.assertEqual(self.run_quiet(1, resume=True, retry_errors=True, mock=True)["stopped"],
                         "unresolved_attempt_requires_review")
        record = json.loads((self.output / "attempts" / "000001.json").read_text())
        self.assertEqual(record["status"], "started")
        self.assertNotIn("response", record)

    def test_unresolved_started_attempt_cannot_precede_later_attempt(self):
        def interrupt(cfg, payload):
            raise KeyboardInterrupt

        self.run_quiet(1, mock=True, complete_fn=interrupt)
        plan, config, _, attempts = runner.read_run(self.output)
        started = attempts[0]
        task = next(task for task in plan["tasks"] if task["id"] == started["task_id"])
        response = runner.mock_complete(plan, task, config)
        completed = dict(started, attempt=2, response=response,
                         **core.score_response(task, response))
        error = dict(started, attempt=2, status="error", error="SyntheticTimeout")
        for later in (completed, error):
            with self.subTest(later_status=later["status"]):
                write_json(self.output / "attempts" / "000002.json", later)
                with self.assertRaisesRegex(ValueError, "unresolved started attempt"):
                    runner.read_run(self.output)

    def test_raw_scoring_and_request_integrity(self):
        self.run_quiet(1, mock=True)
        path = self.output / "attempts" / "000001.json"
        original = json.loads(path.read_text())
        changed = dict(original, answer=next(x for x in "ABC" if x != original["answer"]))
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "scoring differs"):
            runner.read_run(self.output)
        changed = json.loads(json.dumps(original))
        changed["request"]["messages"][0]["content"] += " Changed request."
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            runner.read_run(self.output)

    def test_cumulative_transport_attempt_cap(self):
        def fail(cfg, payload):
            raise provider.ProviderError("SyntheticTimeout")

        self.run_quiet(1, mock=True, complete_fn=fail)
        path = self.output / "attempts" / "000001.json"
        record = json.loads(path.read_text())
        for i in range(2, self.cfg["max_total_attempts"] + 1):
            write_json(path.parent / f"{i:06d}.json", dict(record, attempt=i))
        result = self.run_quiet(1, resume=True, retry_errors=True, mock=True)
        self.assertEqual(result["stopped"], "total_attempt_limit")
        self.assertEqual(result["calls_this_invocation"], 0)
        self.assertEqual(result["attempts_total"], 316)

    def test_cli_prepare_mock_analyze(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["prepare", "--config", str(CONFIG_PATH),
                                   "--output", str(self.output)]), 0)
            self.assertEqual(main(["run", "--config", str(CONFIG_PATH), "--output", str(self.output),
                                   "--mock", "--max-calls", "1"]), 0)
            self.assertEqual(main(["analyze", "--output", str(self.output)]), 0)


if __name__ == "__main__":
    unittest.main()
