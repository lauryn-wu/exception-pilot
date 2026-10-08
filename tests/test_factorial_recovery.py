"""Offline continuation tests: preserve returns, budgets, and strict scoring."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import factorial_recovery as recovery
from exception_pilot import provider
from exception_pilot.core import opposite
from exception_pilot.storage import load_attempts
from exception_factorial.core import load_config, make_plan, read_plan, task_meta
from exception_factorial.runner import run as original_run

ROOT = Path(__file__).resolve().parents[1]


def config(n=1):
    cfg = load_config(ROOT / "configs/factorial.json")
    cfg["n_lists"] = n
    return cfg


def response(text="This vehicle belongs to class B.", finish="stop"):
    return provider.normalize({"id": "offline-fixture", "model": "MOCK", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]})


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def blocked(self, name="blocked", n=1):
        output = self.root / name
        stopped = original_run(config(n), output, 1, mock=True, complete_fn=lambda *args: response())
        self.assertEqual(stopped["stopped"], "invalid_response")
        return output

    def test_finish_only_pending_tasks_preserves_every_prior_file_and_strict_parser(self):
        output = self.blocked()
        preserved = {path: path.read_bytes() for path in
                     [output / "plan.json", output / "execution.json", output / "attempts/000001.json"]}
        done = recovery.run(output, 44, resume=True, mock=True)
        self.assertEqual(done["calls_this_invocation"], 31)
        self.assertEqual(done["valid_answers"], 31)
        self.assertEqual(done["invalid_answers_retained"], 1)
        self.assertEqual(done["tasks_without_return"], 0)
        self.assertEqual(done["stopped"], "all_planned_tasks_returned")
        for path, before in preserved.items():
            self.assertEqual(path.read_bytes(), before)
        attempts = load_attempts(output, read_plan(output))
        self.assertEqual(len({a['task_id'] for a in attempts}), 32)
        self.assertIsNone(attempts[0]["answer"])
        self.assertEqual(attempts[0]["status"], "invalid")
        self.assertTrue(all(a["amendment"] == recovery.AMENDMENT for a in attempts[1:]))
        manifest = json.loads((output / "recovery.json").read_text())
        self.assertEqual(manifest["initial_attempt_count"], 1)
        self.assertEqual(recovery.run(output, 44, resume=True, mock=True)["calls_this_invocation"], 0)
        self.assertIn("SIMULATED", (output / "recovery-summary.md").read_text())
        with self.assertRaisesRegex(ValueError, "invalid"):
            original_run(config(), output, 1, resume=True, retry_errors=True, mock=True)

    def test_bounded_resume_equals_uninterrupted_and_counts_new_invalids_without_retry(self):
        a = self.blocked("a", n=2)
        b = self.blocked("b", n=2)
        first = recovery.run(a, 5, resume=True, mock=True)
        self.assertEqual(first["calls_this_invocation"], 5)
        self.assertEqual(first["stopped"], "call_limit")
        final = recovery.run(a, 64, resume=True, mock=True)
        self.assertEqual(final["calls_this_invocation"], 58)
        recovery.run(b, 64, resume=True, mock=True)
        aa = load_attempts(a, read_plan(a)); bb = load_attempts(b, read_plan(b))
        self.assertEqual([(r["task_id"], r["request"], r["answer"]) for r in aa],
                         [(r["task_id"], r["request"], r["answer"]) for r in bb])
        c = self.blocked("more_invalid")
        result = recovery.run(c, 3, resume=True, mock=True, complete_fn=lambda *args: response("A or B"))
        self.assertEqual(result["calls_this_invocation"], 3)
        self.assertEqual(result["invalid_answers_retained"], 4)
        self.assertEqual(result["tasks_without_return"], 28)

    def test_timeouts_and_interruption_require_flag_and_retry_same_request_only(self):
        for name, error in (("timeout", provider.ProviderError("TimeoutError")), ("interrupt", KeyboardInterrupt())):
            output = self.blocked(name)
            def fail(*args):
                raise error
            failed = recovery.run(output, 31, resume=True, mock=True, complete_fn=fail)
            self.assertEqual(failed["calls_this_invocation"], 1)
            held = recovery.run(output, 31, resume=True, mock=True)
            self.assertEqual(held["stopped"], "retry_requires_flag")
            self.assertEqual(held["calls_this_invocation"], 0)
            done = recovery.run(output, 31, resume=True, retry_errors=True, mock=True)
            self.assertEqual(done["calls_this_invocation"], 31)
            attempts = load_attempts(output, read_plan(output))
            self.assertEqual(attempts[1]["request"], attempts[2]["request"])
            self.assertNotEqual(attempts[0]["task_id"], attempts[1]["task_id"])
            self.assertEqual(len(attempts), 33)

    def test_truncated_response_stops_and_cannot_be_skipped_as_formatting(self):
        output = self.blocked()
        stopped = recovery.run(output, 5, resume=True, mock=True,
                               complete_fn=lambda *args: response("B", finish="length"))
        self.assertEqual(stopped["stopped"], "invalid_provider_response")
        self.assertEqual(stopped["calls_this_invocation"], 1)
        with self.assertRaisesRegex(ValueError, "incomplete, refused"):
            recovery.run(output, 5, resume=True, mock=True)

    def test_identity_mode_source_and_initial_journal_guards(self):
        output = self.blocked()
        with self.assertRaisesRegex(ValueError, "resume"):
            recovery.run(output, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "mode or execution"):
            recovery.run(output, 1, resume=True)
        with self.assertRaisesRegex(ValueError, "require mock"):
            recovery.run(output, 1, resume=True, complete_fn=lambda *args: response())
        with patch.object(recovery, "source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Frozen code"):
                recovery.run(output, 1, resume=True, mock=True)
        recovery.run(output, 1, resume=True, mock=True)
        with patch.object(recovery, "recovery_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Recovery code"):
                recovery.run(output, 1, resume=True, mock=True)
        path = output / "attempts/000001.json"
        record = json.loads(path.read_text())
        record["finished_at"] += "changed"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "pre-recovery journal changed"):
            recovery.run(output, 1, resume=True, mock=True)

    def test_refuses_new_runs_and_changed_raw_answers(self):
        normal = self.root / "normal"
        original_run(config(), normal, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "original runner"):
            recovery.run(normal, 1, resume=True, mock=True)
        output = self.blocked()
        path = output / "attempts/000001.json"
        record = json.loads(path.read_text())
        record.update(status="complete", answer="B")
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "raw provider content"):
            recovery.run(output, 1, resume=True, mock=True)

    def test_analyze_calls_no_provider_and_reports_incompleteness(self):
        output = self.blocked()
        with patch.object(provider, "complete", side_effect=AssertionError("No network")), \
                patch.object(provider, "credential", side_effect=AssertionError("No key needed")):
            result = recovery.write_recovery_summary(output)
        self.assertFalse(result["all_planned_tasks_returned"])
        self.assertEqual(result["unattempted_or_unresolved_tasks"], 31)
        self.assertIsNone(result["sensitivity"])
        self.assertEqual(result["strict_analysis_status"], "simulated_not_evidence")
        self.assertFalse(result["automatic_followup"])


class SensitivityTests(unittest.TestCase):
    def test_one_unknown_endpoint_has_expected_two_and_half_point_bounds(self):
        plan = make_plan(config(n=20))
        records = {t["id"]: {"status": "complete", "answer": task_meta(plan, t)["expected"]}
                   for t in plan["tasks"]}
        bad = next(t for t in plan["tasks"] if (t["question_wording"],t["uncertainty_clause"],
                    t["condition"],t["background"]) == ("original","present","cot_neutral","conflict"))
        records[bad["id"]] = {"status": "invalid", "answer": None}
        result = recovery.sensitivity_bounds(plan, records)
        self.assertEqual(result["invalid_answers_varied"], 1)
        for key in ("extra_penalty/original/present", "question_by_uncertainty_interaction",
                    "uncertainty_effect/original", "question_effect/present"):
            self.assertAlmostEqual(result["bounds"][key][0], 0)
            self.assertAlmostEqual(result["bounds"][key][1], .025)
        self.assertAlmostEqual(result["bounds"]["average_question_effect"][1], .0125)
        self.assertEqual(result["bounds"]["question_effect/absent"], [0, 0])
        self.assertEqual(records[bad["id"]], {"status":"invalid", "answer":None})

    def test_multiple_unknowns_use_coefficient_signs_and_missing_tasks_block_bounds(self):
        plan = make_plan(config(n=20))
        records = {t["id"]: {"status": "complete", "answer": task_meta(plan, t)["expected"]}
                   for t in plan["tasks"]}
        for uncertainty in ("present", "absent"):
            task = next(t for t in plan["tasks"] if (t["question_wording"],t["uncertainty_clause"],
                        t["condition"],t["background"]) == ("original",uncertainty,"cot_neutral","conflict"))
            records[task["id"]] = {"status":"invalid", "answer":None}
        result = recovery.sensitivity_bounds(plan, records)
        lo, hi = result["bounds"]["question_by_uncertainty_interaction"]
        self.assertAlmostEqual(lo, -.025)
        self.assertAlmostEqual(hi, .025)
        del records[plan["tasks"][0]["id"]]
        self.assertIsNone(recovery.sensitivity_bounds(plan, records))


if __name__ == "__main__":
    unittest.main()
