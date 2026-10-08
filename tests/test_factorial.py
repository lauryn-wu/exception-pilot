"""Offline prompt isolation, hand-calculated factorial effects, and recovery."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.core import opposite
from exception_pilot.storage import load_attempts, run_lock, write_json
from exception_counterfactual.core import load_config as prior_config, make_plan as prior_plan
from exception_wording.core import (
    load_config as wording_config, make_plan as wording_plan, messages_for as wording_messages,
)
from exception_factorial import PRIMARY_CONTRAST
from exception_factorial.analysis import summarize, write_summary
from exception_factorial.core import (
    ARMS, BACKGROUNDS, QUESTIONS, UNCERTAINTY, INSTRUCTIONS, QUESTION_TEXT, UNCERTAINTY_TEXT,
    load_config, make_plan, messages_for, read_plan, request_for, task_meta, validate_config,
)
from exception_factorial.runner import prepare, run

ROOT = Path(__file__).resolve().parents[1]


def config(n=20):
    cfg = load_config(ROOT / "configs/factorial.json")
    cfg["n_lists"] = n
    return cfg


def fixture(plan, wrong=lambda t: False):
    records = []
    for i, task in enumerate(plan["tasks"]):
        label = task_meta(plan, task)["expected"]
        if wrong(task):
            label = opposite(label)
        records.append({"attempt": i + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                        "status": "complete", "answer": label,
                        "response": {"text": "OFFLINE FIXTURE\n" + label, "complete": True}})
    return records


def reasoning_conflict(task):
    return task["condition"] == "cot_neutral" and task["background"] == "conflict"


class FactorialDesignTests(unittest.TestCase):
    def test_full_factorial_fresh_lists_and_determinism(self):
        plan = make_plan(config())
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["tasks"]), 640)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 640)
        plates = {x["id"] for w in plan["worlds"] for x in w["items"]}
        self.assertEqual(len(plates), 200)
        self.assertTrue(all(p.startswith("F") for p in plates))
        for previous in (prior_plan(prior_config(ROOT / "configs/counterfactual.json")),
                         wording_plan(wording_config(ROOT / "configs/wording.json"))):
            self.assertFalse(plates & {x["id"] for w in previous["worlds"] for x in w["items"]})
            self.assertNotEqual([w["labels"] for w in plan["worlds"]],
                                [w["labels"] for w in previous["worlds"]])
        for w in plan["worlds"]:
            cells = [t for t in plan["tasks"] if t["world_id"] == w["id"]]
            self.assertEqual(len(cells), 32)
            self.assertEqual({(t["item_index"], t["background"], t["question_wording"],
                               t["uncertainty_clause"], t["condition"]) for t in cells},
                {(i, bg, q, u, arm) for i in w["target_indices"] for bg in BACKGROUNDS
                 for q in QUESTIONS for u in UNCERTAINTY for arm in ARMS})

    def test_existing_two_combinations_reproduce_prior_templates_exactly(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            if (task["question_wording"], task["uncertainty_clause"]) in (
                    ("original", "present"), ("recorded", "absent")):
                self.assertEqual(messages_for(plan, task), wording_messages(plan, task))

    def test_toggle_only_the_uncertainty_line_for_both_questions(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            if task["uncertainty_clause"] != "absent":
                continue
            absent = messages_for(plan, task)[0]["content"]
            present = messages_for(plan, {**task, "uncertainty_clause": "present"})[0]["content"]
            self.assertNotIn(UNCERTAINTY_TEXT, absent)
            self.assertEqual(present.count(UNCERTAINTY_TEXT), 1)
            self.assertEqual(present.replace(UNCERTAINTY_TEXT + "\n", ""), absent)
            self.assertIn(QUESTION_TEXT[task["question_wording"]] + "\n" + UNCERTAINTY_TEXT
                          + "\n" + INSTRUCTIONS[task["condition"]], present)

    def test_toggle_only_question_or_response_without_changing_evidence(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            messages = messages_for(plan, task)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["role"], "user")
            text = messages[0]["content"]
            other_q = "recorded" if task["question_wording"] == "original" else "original"
            changed_q = messages_for(plan, {**task, "question_wording": other_q})[0]["content"]
            self.assertEqual(text.replace(QUESTION_TEXT[task["question_wording"]], QUESTION_TEXT[other_q]),
                             changed_q)
            other_arm = "direct" if task["condition"] == "cot_neutral" else "cot_neutral"
            changed_arm = messages_for(plan, {**task, "condition": other_arm})[0]["content"]
            self.assertEqual(text.replace(INSTRUCTIONS[task["condition"]], INSTRUCTIONS[other_arm]),
                             changed_arm)
            for hidden in ("uncertainty_clause", "question_wording", "fx-list", "target_indices", "80%", "SIMULATED"):
                self.assertNotIn(hidden, text)

    def test_backgrounds_change_only_six_nontarget_label_lines(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            if task["background"] != "support":
                continue
            world = next(w for w in plan["worlds"] if w["id"] == task["world_id"])
            support = messages_for(plan, task)[0]["content"].splitlines()
            conflict = messages_for(plan, {**task, "background": "conflict"})[0]["content"].splitlines()
            self.assertEqual(len(support), len(conflict))
            changed = [(a, b) for a, b in zip(support, conflict) if a != b]
            self.assertEqual(len(changed), 6)
            for a, b in changed:
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])
                for target in world["target_indices"]:
                    self.assertNotIn(world["items"][target]["id"], a)
            for bg in BACKGROUNDS:
                self.assertEqual(world["labels"][bg].count("A"), 5)
                for climate in ("warm", "cold"):
                    group = [j for j, item in enumerate(world["items"]) if item["climate"] == climate]
                    self.assertEqual(sum(world["labels"][bg][j] == world["majority_labels"][bg][climate]
                                         for j in group), 4)

    def test_snapshot_caps_and_invalid_configs(self):
        plan = make_plan(config(n=1))
        for task in plan["tasks"]:
            req = request_for(plan, task)
            self.assertEqual(req["model"], "gpt-4o-2024-08-06")
            self.assertEqual(req["temperature"], 0)
            self.assertEqual(req["max_completion_tokens"], 10 if task["condition"] == "direct" else 1000)
            self.assertFalse(req["store"])
            self.assertEqual(req["n"], 1)
            self.assertNotIn("api_key_env", req)
        for key, value in (("protocol", "verified-facts-wording-v1"), ("model", "gpt-4o"),
                           ("n_lists", True), ("max_completion_tokens", {"direct": 10, "cot": 500}),
                           ("temperature", 0.5), ("unexpected", "not allowed")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})


class FactorialAnalysisTests(unittest.TestCase):
    def test_hand_calculated_paired_interaction_and_simple_effects(self):
        plan = make_plan(config())
        # 15, 5, 5, and 0 whole lists with CoT conflict errors in OP, OA, RP, RA.
        counts = {("original", "present"): 15, ("original", "absent"): 5,
                  ("recorded", "present"): 5, ("recorded", "absent"): 0}
        records = fixture(plan, lambda t: reasoning_conflict(t)
                          and int(t["world_id"][-3:]) < counts[t["question_wording"], t["uncertainty_clause"]])
        result, _ = summarize(plan, records)
        expected = {PRIMARY_CONTRAST: .25, "uncertainty_effect/original": .5,
                    "uncertainty_effect/recorded": .25, "question_effect/absent": .25,
                    "question_effect/present": .5, "average_uncertainty_effect": .375,
                    "average_question_effect": .375}
        for key, value in expected.items():
            self.assertEqual(result["factorial_contrasts"][key]["mean"], value)
        primary = result["factorial_contrasts"][PRIMARY_CONTRAST]
        self.assertEqual((primary["positive_lists"], primary["zero_lists"], primary["negative_lists"]), (10, 5, 5))
        self.assertLess(primary["paired_bootstrap_95_ci"][0], 0)
        self.assertGreater(primary["paired_bootstrap_95_ci"][1], .25)
        self.assertEqual(result["paired_lists"], 20)
        self.assertEqual(sum(row["n_correct"] for row in result["accuracy_tables"]), 590)
        self.assertEqual(len(result["accuracy_tables"]), 16)
        self.assertTrue(all(r["n_valid"] == r["n_planned"] == 40 for r in result["accuracy_tables"]))
        for (q, u), count in counts.items():
            self.assertEqual(result["comparisons"][f"{q}/{u}"]["extra_conflict_penalty"]["mean"], count / 20)

    def test_additive_effects_do_not_require_a_nonzero_interaction(self):
        plan = make_plan(config(n=2))
        def wrong(t):
            if not reasoning_conflict(t):
                return False
            if (t["question_wording"], t["uncertainty_clause"]) == ("original", "present"):
                return True
            if (t["question_wording"], t["uncertainty_clause"]) == ("recorded", "absent"):
                return False
            return t["item_index"] < 5  # Exactly one of two preselected targets.
        result, _ = summarize(plan, fixture(plan, wrong))
        self.assertEqual(result["factorial_contrasts"][PRIMARY_CONTRAST]["mean"], 0)
        self.assertEqual(result["factorial_contrasts"]["average_uncertainty_effect"]["mean"], .5)
        self.assertEqual(result["factorial_contrasts"]["average_question_effect"]["mean"], .5)

    def test_strong_or_zero_effects_never_authorize_another_study(self):
        plan = make_plan(config())
        for wrong in (lambda t: False, lambda t: reasoning_conflict(t)
                      and t["question_wording"] == "original" and t["uncertainty_clause"] == "present"):
            result, _ = summarize(plan, fixture(plan, wrong))
            self.assertEqual(result["analysis_status"], "complete_ready_for_interpretation")
            self.assertIsNone(result["analysis_plan"]["numerical_pass_threshold"])
            self.assertFalse(result["analysis_plan"]["automatic_followup"])
            self.assertEqual(result["analysis_plan"]["previous_stop_decision_preserved"],
                             "stop_explicit_record_boundary")
            self.assertNotIn("screen", result)

    def test_components_expose_common_harm_and_direct_only_changes(self):
        plan = make_plan(config(n=2))
        common, _ = summarize(plan, fixture(plan, lambda t: t["background"] == "conflict"))
        for comparison in common["comparisons"].values():
            self.assertEqual(comparison["extra_conflict_penalty"]["mean"], 0)
            self.assertEqual(comparison["reasoning_conflict_penalty"], 1)
            self.assertEqual(comparison["direct_conflict_penalty"], 1)
        direct_only, _ = summarize(plan, fixture(plan, lambda t: t["condition"] == "direct"
                                               and t["background"] == "support"))
        for comparison in direct_only["comparisons"].values():
            self.assertEqual(comparison["extra_conflict_penalty"]["mean"], 1)
            self.assertEqual(comparison["reasoning_conflict_penalty"], 0)
            self.assertEqual(comparison["direct_minus_reasoning_conflict_accuracy"], 0)

    def test_partial_invalid_empty_and_small_runs_are_distinct(self):
        plan = make_plan(config())
        records = fixture(plan)
        partial, rows = summarize(plan, records[:-1])
        self.assertEqual(partial["analysis_status"], "incomplete")
        self.assertEqual(partial["paired_lists"], 19)
        self.assertEqual(sum(r["correct"] is None for r in rows), 1)
        self.assertEqual(sum(r["n_valid"] for r in partial["accuracy_tables"]), 639)
        records[-1].update(status="invalid", answer=None)
        invalid, rows = summarize(plan, records)
        self.assertEqual(invalid["analysis_status"], "technical_failure")
        self.assertEqual(sum(r["correct"] is None for r in rows), 1)
        empty, _ = summarize(plan, [])
        self.assertEqual(empty["paired_lists"], 0)
        self.assertIsNone(empty["factorial_contrasts"][PRIMARY_CONTRAST]["mean"])
        self.assertIsNone(empty["factorial_contrasts"][PRIMARY_CONTRAST]["paired_bootstrap_95_ci"])
        small = make_plan(config(n=1))
        result, _ = summarize(small, fixture(small))
        self.assertEqual(result["analysis_status"], "insufficient_lists")
        self.assertIsNone(result["factorial_contrasts"][PRIMARY_CONTRAST]["paired_bootstrap_95_ci"])

    def test_mock_label_stored_answer_integrity_and_duplicate_returns(self):
        plan = make_plan(config(n=2))
        records = fixture(plan)
        simulated, _ = summarize(plan, records, "mock")
        self.assertEqual(simulated["analysis_status"], "simulated_not_evidence")
        self.assertEqual(simulated["factorial_contrasts"][PRIMARY_CONTRAST]["paired_bootstrap_95_ci"], [0, 0])
        with self.assertRaisesRegex(ValueError, "Multiple returned"):
            summarize(plan, records + [records[0]])
        records[0]["answer"] = opposite(records[0]["answer"])
        with self.assertRaisesRegex(ValueError, "disagrees"):
            summarize(plan, records)


class FactorialRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def test_prepare_preview_all_32_and_no_provider_call(self):
        with patch("exception_factorial.runner.provider.complete", side_effect=AssertionError("No live calls")):
            with run_lock(self.root / "preview") as output:
                plan = prepare(config(n=1), output)
            previews = json.loads((output / "preview.json").read_text())
            self.assertEqual(len(previews), 32)
            for preview, task in zip(previews, plan["tasks"]):
                self.assertEqual(preview["request"], request_for(plan, task))
            self.assertIn("recorded", (output / "preview.md").read_text())
            self.assertFalse((output / "execution.json").exists())

    def test_resume_equals_uninterrupted_and_finished_resume_makes_no_calls(self):
        a, b = self.root / "a", self.root / "b"
        cfg = config(n=2)
        self.assertEqual(run(cfg, a, 32, mock=True)["calls_this_invocation"], 32)
        with self.assertRaisesRegex(ValueError, "resume"):
            run(cfg, a, 64, mock=True)
        self.assertEqual(run(cfg, a, 64, mock=True, resume=True)["calls_this_invocation"], 32)
        run(cfg, b, 64, mock=True)
        aa, bb = load_attempts(a, read_plan(a)), load_attempts(b, read_plan(b))
        self.assertEqual([(r["request"], r["answer"]) for r in aa], [(r["request"], r["answer"]) for r in bb])
        self.assertEqual(run(cfg, a, 64, mock=True, resume=True)["calls_this_invocation"], 0)
        result = write_summary(a)
        self.assertEqual(result["analysis_status"], "simulated_not_evidence")
        self.assertIn("SIMULATED", (a / "summary.md").read_text())

    def test_timeout_and_interruption_retry_exact_request_with_flag(self):
        for name, error in (("timeout", provider.ProviderError("TimeoutError")), ("interrupt", KeyboardInterrupt())):
            output = self.root / name
            def fail(*args):
                raise error
            failed = run(config(n=1), output, 32, mock=True, complete_fn=fail)
            self.assertEqual(failed["calls_this_invocation"], 1)
            self.assertEqual(run(config(n=1), output, 32, mock=True, resume=True)["stopped"], "retry_requires_flag")
            done = run(config(n=1), output, 32, mock=True, resume=True, retry_errors=True)
            self.assertEqual(done["valid_answers"], 32)
            self.assertEqual(done["attempts_total"], 33)
            attempts = load_attempts(output, read_plan(output))
            self.assertEqual(attempts[0]["request"], attempts[1]["request"])

    def test_invalid_return_cannot_be_resampled(self):
        output = self.root / "invalid"
        def invalid(*args):
            return provider.normalize({"model": "MOCK", "choices": [{"message": {
                "role": "assistant", "content": "A or B"}, "finish_reason": "stop"}]})
        result = run(config(n=1), output, 32, mock=True, complete_fn=invalid)
        self.assertEqual(result["stopped"], "invalid_response")
        with self.assertRaisesRegex(ValueError, "invalid"):
            run(config(n=1), output, 32, mock=True, resume=True, retry_errors=True)
        self.assertEqual(len(list((output / "attempts").glob("*.json"))), 1)

    def test_previous_run_is_rejected_without_modification(self):
        output = self.root / "old"
        output.mkdir()
        old = prior_plan(prior_config(ROOT / "configs/counterfactual.json"))
        write_json(output / "plan.json", old)
        before = (output / "plan.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "not a factorial-study"):
            run(config(), output, 1, mock=True, resume=True)
        self.assertEqual((output / "plan.json").read_bytes(), before)
        self.assertFalse((output / "execution.json").exists())

    def test_config_source_mode_and_injected_live_responses_are_guarded(self):
        output = self.root / "frozen"
        cfg = config(n=1)
        run(cfg, output, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "Config differs"):
            run({**cfg, "seed": cfg["seed"] + 1}, output, 1, mock=True, resume=True)
        with patch("exception_factorial.runner.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code differs"):
                run(cfg, output, 1, mock=True, resume=True)
        with self.assertRaisesRegex(ValueError, "mode or identity"):
            run(cfg, output, 1, mock=False, resume=True)
        with self.assertRaisesRegex(ValueError, "require mock"):
            run(cfg, self.root / "injected", 1, complete_fn=lambda *args: {})

    def test_missing_execution_metadata_and_modified_plan_are_rejected(self):
        output = self.root / "identity"
        run(config(n=1), output, 1, mock=True)
        (output / "execution.json").unlink()
        with self.assertRaisesRegex(ValueError, "without execution"):
            run(config(n=1), output, 1, mock=True, resume=True)
        with self.assertRaisesRegex(ValueError, "execution identity"):
            write_summary(output)
        plan = json.loads((output / "plan.json").read_text())
        plan["config"]["seed"] += 1
        write_json(output / "plan.json", plan)
        with self.assertRaises(ValueError):
            read_plan(output)


if __name__ == "__main__":
    unittest.main()
