"""Execution invariants use a tiny adapter; no provider calls or study outcomes."""

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from exception_columns import provider
from exception_pilot.core import check_plan, digest
from exception_pilot.storage import accepted_records, write_json
from exception_study_support.core import content_digest, source_digest
from exception_study_support.runner import main, prepare, read_run, run


class FixtureCore:
    PROTOCOL_VERSION = "offline-support-fixture-v1"

    def __init__(self):
        self.source = "frozen-fixture-source"

    def load_config(self, path):
        return json.loads(Path(path).read_text())

    def make_plan(self, config):
        plan = {"protocol_version": self.PROTOCOL_VERSION, "source_digest": self.source,
                "config": copy.deepcopy(config),
                "tasks": [{"id": f"task-{n}", "answer": answer} for n, answer in enumerate("ABCA")]}
        plan["plan_hash"] = content_digest(plan)
        return plan

    def read_plan(self, output):
        plan = json.loads((Path(output) / "plan.json").read_text())
        check_plan(plan)
        if plan != self.make_plan(plan["config"]):
            raise ValueError("Frozen source or schedule changed")
        return plan

    def request_for(self, plan, task):
        return {"model": plan["config"]["model"], "messages": [
            {"role": "user", "content": "fixture " + task["id"]},
            {"role": "assistant", "content": "saved fixture answer"},
            {"role": "user", "content": "follow-up fixture"}],
            "temperature": 0, "max_completion_tokens": 20, "n": 1, "store": False}

    def task_meta(self, plan, task):
        return {**task, "expected": task["answer"]}

    def score_response(self, task, response):
        text = response["text"]
        answer = text[-1:] if response["complete"] and text in ("ANSWER: A", "ANSWER: B", "ANSWER: C") else None
        return {"status": "complete" if answer else "invalid", "answer": answer}

    def mock_complete(self, plan, task):
        return raw_response("ANSWER: " + task["answer"])


def raw_response(text="ANSWER: A", model="MOCK-NOT-A-MODEL", finish="stop"):
    return {"model": model, "usage": {}, "choices": [
        {"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


class FixtureAnalysis:
    def __init__(self, core):
        self.core = core

    def write_summary(self, output):
        plan, execution, attempts = read_run(self.core, output)
        returned = list(accepted_records(attempts).values())
        valid = sum(record["status"] == "complete" for record in returned)
        result = {"returned_answers": len(returned), "valid_answers": valid,
                  "invalid_answers": len(returned) - valid,
                  "analysis_status": "simulated" if execution and execution["mode"] == "mock" else "fixture",
                  "planned_calls": len(plan["tasks"])}
        write_json(Path(output) / "summary.json", result)
        return result


class StudySupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "run"
        self.core = FixtureCore()
        self.analysis = FixtureAnalysis(self.core)
        self.config = {"model": "gpt-4o-2024-08-06", "max_total_attempts": 6,
                       "timeout_seconds": 120, "api_key_env": "SUPPORT_TEST_API_KEY"}
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def run_fixture(self, max_calls=4, **kwargs):
        return run(self.core, self.analysis, self.config, self.output, max_calls, **kwargs)

    def attempt(self, n=1):
        path = self.output / "attempts" / f"{n:06d}.json"
        return path, json.loads(path.read_text())

    def test_prepare_is_offline_and_previews_all_messages(self):
        with patch.object(provider, "credential", side_effect=AssertionError("credential forbidden")), \
                patch.object(provider, "complete", side_effect=AssertionError("network forbidden")):
            plan = prepare(self.core, self.config, self.output)
            self.analysis.write_summary(self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 4)
        self.assertEqual(preview[0]["request"], self.core.request_for(plan, plan["tasks"][0]))
        self.assertIn("saved fixture answer", (self.output / "preview.md").read_text())
        self.assertIn("follow-up fixture", (self.output / "preview.md").read_text())
        self.assertFalse((self.output / "execution.json").exists())

    def test_dynamic_schedule_and_resume_do_not_replace_answers(self):
        first = self.run_fixture(1, mock=True)
        self.assertEqual((first["stopped"], first["planned_calls"]), ("call_limit", 4))
        with self.assertRaisesRegex(ValueError, "resume"):
            self.run_fixture(1, mock=True)
        final = self.run_fixture(10, mock=True, resume=True)
        self.assertEqual((final["calls_this_invocation"], final["returned_answers"]), (3, 4))
        self.assertEqual(final["stopped"], "complete")
        self.assertEqual(self.run_fixture(1, mock=True, resume=True)["calls_this_invocation"], 0)

    def test_config_and_source_drift_are_rejected(self):
        prepare(self.core, self.config, self.output)
        with self.assertRaisesRegex(ValueError, "Config differs"):
            prepare(self.core, {**self.config, "timeout_seconds": 1}, self.output)
        self.core.source = "modified-source"
        with self.assertRaisesRegex(ValueError, "Frozen source"):
            read_run(self.core, self.output)

    def test_plan_and_preview_tampering_are_rejected(self):
        prepare(self.core, self.config, self.output)
        path = self.output / "plan.json"
        original = json.loads(path.read_text())
        path.write_text(json.dumps({**original, "source_digest": "tampered"}))
        with self.assertRaisesRegex(ValueError, "integrity"):
            read_run(self.core, self.output)
        path.write_text(json.dumps(original))
        preview = json.loads((self.output / "preview.json").read_text())
        preview[0]["request"]["messages"][0]["content"] = "tampered"
        (self.output / "preview.json").write_text(json.dumps(preview))
        with self.assertRaisesRegex(ValueError, "preview"):
            read_run(self.core, self.output)

    def test_invalid_return_stays_terminal_even_with_retry_flag(self):
        first = self.run_fixture(1, mock=True, complete_fn=lambda *_: raw_response("No answer"))
        self.assertEqual(first["invalid_answers_retained"], 1)
        self.run_fixture(1, mock=True, resume=True, retry_errors=True)
        attempts = read_run(self.core, self.output)[2]
        self.assertEqual([a["task_id"] for a in attempts], ["task-0", "task-1"])
        self.assertEqual(attempts[0]["raw_response"], raw_response("No answer"))

    def test_truncation_and_refusal_are_terminal_invalids(self):
        truncated = raw_response("ANSWER: A", finish="length")
        first = self.run_fixture(1, mock=True, complete_fn=lambda *_: truncated)
        self.assertEqual(first["invalid_answers_retained"], 1)
        refused = raw_response("ANSWER: B")
        refused["choices"][0]["message"]["refusal"] = "fixture refusal"
        second = self.run_fixture(1, mock=True, resume=True, complete_fn=lambda *_: refused)
        self.assertEqual(second["invalid_answers_retained"], 2)

    def test_transport_errors_require_flag_and_count_against_cap(self):
        def fail(*_):
            raise provider.ProviderError("HTTP 503", status_code=503)
        first = self.run_fixture(4, mock=True, complete_fn=fail)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        blocked = self.run_fixture(4, mock=True, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        for _ in range(5):
            self.run_fixture(4, mock=True, resume=True, retry_errors=True, complete_fn=fail)
        capped = self.run_fixture(4, mock=True, resume=True, retry_errors=True)
        self.assertEqual((capped["stopped"], capped["calls_this_invocation"], capped["attempts_total"]),
                         ("total_attempt_limit", 0, 6))

    def test_successful_retry_advances_only_after_return(self):
        def fail(*_):
            raise provider.ProviderError("HTTP 503", status_code=503)
        self.run_fixture(1, mock=True, complete_fn=fail)
        result = self.run_fixture(1, mock=True, resume=True, retry_errors=True)
        self.assertEqual((result["attempts_total"], result["returned_answers"]), (2, 1))
        self.assertEqual([a["task_id"] for a in read_run(self.core, self.output)[2]], ["task-0", "task-0"])

    def test_unresolved_request_never_retried(self):
        def interrupt(*_):
            raise KeyboardInterrupt
        result = self.run_fixture(1, mock=True, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.run_fixture(1, mock=True, resume=True, retry_errors=True)

    def test_raw_return_survives_a_local_scoring_failure(self):
        with patch.object(self.core, "score_response", side_effect=ValueError("local scorer bug")):
            with self.assertRaisesRegex(ValueError, "local scorer bug"):
                self.run_fixture(1, mock=True)
        _, record = self.attempt()
        self.assertEqual(record["status"], "started")
        self.assertEqual(record["raw_response"], raw_response())
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.run_fixture(1, mock=True, resume=True, retry_errors=True)

    def test_mock_and_live_cannot_mix(self):
        self.run_fixture(1, mock=True)
        with self.assertRaisesRegex(ValueError, "mode"):
            self.run_fixture(1, resume=True)
        with self.assertRaisesRegex(ValueError, "mock"):
            self.run_fixture(1, complete_fn=lambda *_: raw_response())

    def test_identity_failure_is_retained_and_permanently_stops(self):
        raw = raw_response(model="unexpected-model")
        with patch.object(provider, "credential", return_value="offline-placeholder"), \
                patch.object(provider, "complete", return_value=raw) as call:
            result = self.run_fixture(4)
        self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("model_identity_failure", 1))
        self.assertEqual(result["invalid_answers_retained"], 1)
        self.assertEqual(call.call_count, 1)
        with self.assertRaisesRegex(ValueError, "identity failure"):
            self.run_fixture(1, resume=True, retry_errors=True)

    def test_missing_identity_is_permanent_too(self):
        with patch.object(provider, "credential", return_value="offline-placeholder"), \
                patch.object(provider, "complete", return_value={"unparseable_http_body_utf8": "not json"}):
            result = self.run_fixture(4)
        self.assertEqual(result["stopped"], "model_identity_failure")
        self.assertEqual(self.attempt()[1]["raw_response"], {"unparseable_http_body_utf8": "not json"})

    def test_fully_completed_live_run_needs_no_credentials_to_resume(self):
        with patch.object(provider, "credential", return_value="offline-placeholder"), \
                patch.object(provider, "complete", return_value=raw_response(model=self.config["model"])):
            self.run_fixture(4)
        with patch.object(provider, "credential", side_effect=AssertionError("credential forbidden")):
            result = self.run_fixture(4, resume=True)
        self.assertEqual(result["calls_this_invocation"], 0)

    def test_saved_request_raw_and_scoring_tampering_rejected(self):
        self.run_fixture(1, mock=True)
        path, original = self.attempt()
        for mutation, expected in (("answer", "scoring"), ("request", "request"), ("raw_response", "scoring")):
            changed = copy.deepcopy(original)
            if mutation == "answer":
                changed["answer"] = "B"
            elif mutation == "request":
                changed["request"]["messages"][-1]["content"] += " modified"
            else:
                changed["raw_response"] = raw_response("ANSWER: B")
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, expected):
                read_run(self.core, self.output)
        path.write_text(json.dumps(original))

    def test_a_returned_response_cannot_be_retried_or_relabelled_error(self):
        self.run_fixture(1, mock=True)
        path, original = self.attempt()
        path.write_text(json.dumps({**original, "status": "error"}))
        with self.assertRaisesRegex(ValueError, "relabeled"):
            read_run(self.core, self.output)
        path.write_text(json.dumps(original))
        second = self.output / "attempts/000002.json"
        second.write_text(json.dumps({**original, "attempt": 2}))
        with self.assertRaisesRegex(ValueError, "retried"):
            read_run(self.core, self.output)

    def test_attempts_without_execution_identity_rejected(self):
        self.run_fixture(1, mock=True)
        (self.output / "execution.json").unlink()
        with self.assertRaisesRegex(ValueError, "without execution"):
            read_run(self.core, self.output)

    def test_nonempty_directory_and_invalid_call_caps_rejected(self):
        self.output.mkdir()
        (self.output / "unrelated.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "not empty"):
            prepare(self.core, self.config, self.output)
        for bad in (True, 0, -1, 1.5):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                self.run_fixture(bad, mock=True)

    def test_cli_prepare_run_analyze_and_errors(self):
        config_path = Path(self.temp.name) / "config.json"
        config_path.write_text(json.dumps(self.config))
        base = ["--config", str(config_path), "--output", str(self.output)]
        self.assertEqual(main(self.core, self.analysis, ["prepare", *base]), 0)
        self.assertEqual(main(self.core, self.analysis, ["run", *base, "--max-calls", "4", "--mock"]), 0)
        self.assertEqual(main(self.core, self.analysis, ["analyze", "--output", str(self.output)]), 0)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(self.core, self.analysis, ["run", *base, "--max-calls", "4", "--mock"]), 2)

    def test_malformed_successful_http_body_retained_no_retry(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"invalid json body"
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(provider, "credential", return_value="offline-placeholder"), \
                patch.object(provider.request, "build_opener", return_value=opener):
            raw = provider.complete(self.config, {"model": self.config["model"], "messages": []})
        self.assertEqual(raw, {"unparseable_http_body_utf8": "invalid json body"})
        self.assertEqual(opener.open.call_count, 1)


class SourceIdentityTests(unittest.TestCase):
    def test_canonical_digest_matches_existing_repository(self):
        value = {"z": [1, "☃"], "a": {"B": False}}
        self.assertEqual(content_digest(value), digest(value))

    def test_source_digest_includes_data_protocol_config_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = ["study/core.py", "study/data/corpus.json", "study/analysis.py",
                     "exception_study_support/runner.py", "exception_columns/__init__.py",
                     "exception_columns/provider.py", "exception_pilot/__init__.py", "exception_pilot/core.py",
                     "exception_pilot/storage.py", "exception_pilot/provider.py",
                     "exception_mistral_map_v3/__init__.py", "exception_mistral_map_v3/parser.py",
                     "configs/study.json", "PROTOCOL.md"]
            for path in paths:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("initial " + path)
            get = lambda: source_digest(root, "study", ("configs/study.json", "PROTOCOL.md"))
            initial = get()
            for path in paths:
                target = root / path
                old = target.read_text()
                target.write_text(old + " changed")
                self.assertNotEqual(initial, get(), path)
                target.write_text(old)
            ignored = root / "study/__pycache__/core.pyc"
            ignored.parent.mkdir()
            ignored.write_bytes(b"cached bytecode")
            self.assertEqual(initial, get())
            (root / "PROTOCOL.md").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                get()


if __name__ == "__main__":
    unittest.main()
