"""Offline design, hand-calculated analysis, and interruption/resume checks."""

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.core import opposite
from exception_pilot.storage import load_attempts, run_lock, write_json
from exception_counterfactual.core import (
    load_config as prior_config, make_plan as prior_plan, messages_for as prior_messages,
)
from exception_wording.analysis import summarize, write_summary
from exception_wording.core import (
    ARMS, BACKGROUNDS, QUESTIONS, INSTRUCTIONS, QUESTION_TEXT, load_config, make_plan,
    messages_for, read_plan, request_for, task_meta, validate_config,
)
from exception_wording.runner import prepare, run

ROOT = Path(__file__).resolve().parents[1]


def config(n=20):
    cfg = load_config(ROOT / "configs/wording.json")
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


def all_reasoning_conflict(t):
    return t["condition"] != "direct" and t["background"] == "conflict"


class WordingDesignTests(unittest.TestCase):
    def test_full_factorial_fresh_lists_and_determinism(self):
        plan = make_plan(config())
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["tasks"]), 480)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 480)
        plates = {x["id"] for w in plan["worlds"] for x in w["items"]}
        self.assertEqual(len(plates), 200)
        self.assertTrue(all(p.startswith("W") for p in plates))
        previous = prior_plan(prior_config(ROOT / "configs/counterfactual.json"))
        self.assertFalse(plates & {x["id"] for w in previous["worlds"] for x in w["items"]})
        self.assertNotEqual([w["labels"] for w in plan["worlds"]],
                            [w["labels"] for w in previous["worlds"]])
        for w in plan["worlds"]:
            cells = [t for t in plan["tasks"] if t["world_id"] == w["id"]]
            self.assertEqual({(t["item_index"], t["background"], t["question_wording"], t["condition"])
                              for t in cells},
                {(i, bg, q, arm) for i in w["target_indices"] for bg in BACKGROUNDS
                 for q in QUESTIONS for arm in ARMS})

    def test_original_cells_reproduce_previous_templates_exactly(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            if task["question_wording"] == "original" and task["condition"] != "cot_neutral":
                old_task = {**task, "condition": "direct" if task["condition"] == "direct" else "cot"}
                self.assertEqual(messages_for(plan, task), prior_messages(plan, old_task))

    def test_only_intended_question_and_instruction_text_changes(self):
        plan = make_plan(config(n=2))
        for w in plan["worlds"]:
            for i in w["target_indices"]:
                for bg in BACKGROUNDS:
                    texts = {}
                    for task in plan["tasks"]:
                        if task["world_id"] == w["id"] and task["item_index"] == i and task["background"] == bg:
                            messages = messages_for(plan, task)
                            self.assertEqual(len(messages), 1)
                            self.assertEqual(messages[0]["role"], "user")
                            text = messages[0]["content"]
                            suffix = QUESTION_TEXT[task["question_wording"]] + "\n" + INSTRUCTIONS[task["condition"]]
                            self.assertTrue(text.endswith(suffix))
                            texts[task["question_wording"], task["condition"]] = text[:-len(suffix)]
                            for hidden in ("question_wording", "wd-list", "target_indices", "20%", "80%", "SIMULATED"):
                                self.assertNotIn(hidden, text)
                    self.assertEqual(len(texts), 6)
                    self.assertEqual(len(set(texts.values())), 1)

    def test_backgrounds_change_only_six_nontarget_label_lines(self):
        plan = make_plan(config(n=2))
        for w in plan["worlds"]:
            for q in QUESTIONS:
                for arm in ARMS:
                    for i in w["target_indices"]:
                        tasks = {t["background"]: t for t in plan["tasks"] if t["world_id"] == w["id"]
                                 and t["item_index"] == i and t["condition"] == arm and t["question_wording"] == q}
                        lines = {bg: messages_for(plan, t)[0]["content"].splitlines() for bg, t in tasks.items()}
                        self.assertEqual(len(lines["support"]), len(lines["conflict"]))
                        changed = [(a, b) for a, b in zip(lines["support"], lines["conflict"]) if a != b]
                        self.assertEqual(len(changed), 6)
                        for a, b in changed:
                            self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])
                            for target in w["target_indices"]:
                                self.assertNotIn(w["items"][target]["id"], a)
                        for bg in BACKGROUNDS:
                            self.assertEqual(w["labels"][bg].count("A"), 5)
                            for climate in ("warm", "cold"):
                                group = [j for j, item in enumerate(w["items"]) if item["climate"] == climate]
                                self.assertEqual(sum(w["labels"][bg][j] == w["majority_labels"][bg][climate]
                                                     for j in group), 4)

    def test_snapshot_caps_and_invalid_configs(self):
        plan = make_plan(config(n=1))
        for t in plan["tasks"]:
            req = request_for(plan, t)
            self.assertEqual(req["model"], "gpt-4o-2024-08-06")
            self.assertEqual(req["max_completion_tokens"], 10 if t["condition"] == "direct" else 1000)
            self.assertNotIn("api_key_env", req)
        for key, value in (("protocol", "verified-facts-counterfactual-v1"), ("model", "gpt-4o"),
                           ("n_lists", True), ("max_completion_tokens", {"direct": 10, "cot": 500}),
                           ("temperature", 0.5), ("unexpected", "not allowed")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})


class WordingAnalysisTests(unittest.TestCase):
    def test_hand_calculated_15pp_boundary_uses_twenty_lists(self):
        plan = make_plan(config())
        records = fixture(plan, lambda t: all_reasoning_conflict(t) and int(t["world_id"][-3:]) < 3)
        result, _ = summarize(plan, records)
        self.assertEqual(result["screen"]["decision"], "review_for_second_model")
        self.assertEqual(result["paired_lists"], 20)
        for comparison in result["comparisons"].values():
            stats = comparison["extra_conflict_penalty"]
            self.assertAlmostEqual(stats["mean"], 0.15)
            self.assertEqual(stats["positive_lists"], 3)
            self.assertEqual(stats["paired_bootstrap_95_ci"][0], 0)
        self.assertEqual(len(result["accuracy_tables"]), 12)
        self.assertTrue(all(r["n_valid"] == 40 for r in result["accuracy_tables"]))

    def test_five_recorded_neutral_errors_below_threshold_stops(self):
        plan = make_plan(config())
        primary = [t for t in plan["tasks"] if t["question_wording"] == "recorded"
                   and t["condition"] == "cot_neutral" and t["background"] == "conflict"]
        bad = {t["id"] for t in primary[:5]}
        records = fixture(plan, lambda t: all_reasoning_conflict(t) and
                          (t["question_wording"] == "original" or t["condition"] == "cot_classification"
                           or t["id"] in bad))
        result, _ = summarize(plan, records)
        self.assertEqual(result["comparisons"]["recorded/cot_neutral"]["extra_conflict_penalty"]["mean"], 0.125)
        self.assertEqual(result["screen"]["decision"], "stop_explicit_record_boundary")

    def test_ordered_checks_cannot_be_rescued_by_diagnostic_cells(self):
        plan = make_plan(config())
        failures = [("original", "cot_classification", "stop_replication_failed"),
                    ("original", "cot_neutral", "stop_neutral_wording_failed"),
                    ("recorded", "cot_neutral", "stop_explicit_record_boundary")]
        for q, arm, expected in failures:
            records = fixture(plan, lambda t: all_reasoning_conflict(t)
                              and (t["question_wording"], t["condition"]) != (q, arm))
            result, _ = summarize(plan, records)
            self.assertEqual(result["screen"]["decision"], expected)
            self.assertTrue(result["comparisons"]["recorded/cot_classification"]["qualifies_descriptively"])

    def test_common_conflict_harm_and_direct_improvement_do_not_pass(self):
        plan = make_plan(config())
        for wrong in (lambda t: t["background"] == "conflict",
                      lambda t: t["condition"] == "direct" and t["background"] == "support"):
            result, _ = summarize(plan, fixture(plan, wrong))
            self.assertEqual(result["screen"]["decision"], "stop_replication_failed")
            self.assertFalse(result["comparisons"]["recorded/cot_neutral"]["directions_match_hypothesis"])

    def test_paired_wording_differences_have_expected_signs(self):
        plan = make_plan(config())
        records = fixture(plan, lambda t: all_reasoning_conflict(t) and
                          (t["condition"] == "cot_classification" or
                           (t["question_wording"] == "original" and int(t["world_id"][-3:]) < 10)))
        result, _ = summarize(plan, records)
        contrasts = result["wording_contrasts"]
        self.assertEqual(contrasts["original/neutral_minus_classification"]["mean"], -0.5)
        self.assertEqual(contrasts["recorded/neutral_minus_classification"]["mean"], -1)
        self.assertEqual(contrasts["neutral/original_minus_recorded"]["mean"], 0.5)

    def test_partial_invalid_empty_and_small_runs_do_not_pass(self):
        plan = make_plan(config())
        records = fixture(plan, all_reasoning_conflict)
        partial, rows = summarize(plan, records[:-1])
        self.assertEqual(partial["screen"]["decision"], "incomplete")
        self.assertEqual(partial["paired_lists"], 19)
        self.assertEqual(sum(r["correct"] is None for r in rows), 1)
        records[-1].update(status="invalid", answer=None)
        invalid, _ = summarize(plan, records)
        self.assertEqual(invalid["screen"]["decision"], "technical_failure")
        empty, _ = summarize(plan, [])
        self.assertEqual(empty["paired_lists"], 0)
        self.assertIsNone(empty["comparisons"]["recorded/cot_neutral"]["extra_conflict_penalty"]["mean"])
        small = make_plan(config(n=1))
        self.assertEqual(summarize(small, fixture(small, all_reasoning_conflict))[0]["screen"]["decision"],
                         "insufficient_lists")

    def test_mock_label_and_stored_answer_integrity(self):
        plan = make_plan(config(n=2))
        records = fixture(plan, all_reasoning_conflict)
        simulated, _ = summarize(plan, records, "mock")
        self.assertEqual(simulated["screen"]["decision"], "simulated_not_evidence")
        records[0]["answer"] = opposite(records[0]["answer"])
        with self.assertRaisesRegex(ValueError, "disagrees"):
            summarize(plan, records)


class WordingRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def test_prepare_preview_all_24_and_no_provider_call(self):
        with patch("exception_wording.runner.provider.complete", side_effect=AssertionError("No live calls")):
            with run_lock(self.root / "preview") as output:
                plan = prepare(config(n=1), output)
            previews = json.loads((output / "preview.json").read_text())
            self.assertEqual(len(previews), 24)
            for preview, task in zip(previews, plan["tasks"]):
                self.assertEqual(preview["request"], request_for(plan, task))
            self.assertIn("recorded", (output / "preview.md").read_text())
            self.assertFalse((output / "execution.json").exists())

    def test_resume_equals_uninterrupted_and_finished_resume_makes_no_calls(self):
        a, b = self.root / "a", self.root / "b"
        cfg = config(n=2)
        self.assertEqual(run(cfg, a, 24, mock=True)["calls_this_invocation"], 24)
        with self.assertRaisesRegex(ValueError, "resume"):
            run(cfg, a, 48, mock=True)
        self.assertEqual(run(cfg, a, 48, mock=True, resume=True)["calls_this_invocation"], 24)
        run(cfg, b, 48, mock=True)
        aa, bb = load_attempts(a, read_plan(a)), load_attempts(b, read_plan(b))
        self.assertEqual([(r["request"], r["answer"]) for r in aa], [(r["request"], r["answer"]) for r in bb])
        self.assertEqual(run(cfg, a, 48, mock=True, resume=True)["calls_this_invocation"], 0)
        result = write_summary(a)
        self.assertEqual(result["screen"]["decision"], "simulated_not_evidence")
        self.assertIn("SIMULATED", (a / "summary.md").read_text())

    def test_timeout_and_interruption_retry_exact_request_with_flag(self):
        for name, error in (("timeout", provider.ProviderError("TimeoutError")), ("interrupt", KeyboardInterrupt())):
            output = self.root / name
            def fail(*args):
                raise error
            failed = run(config(n=1), output, 24, mock=True, complete_fn=fail)
            self.assertEqual(failed["calls_this_invocation"], 1)
            self.assertEqual(run(config(n=1), output, 24, mock=True, resume=True)["stopped"], "retry_requires_flag")
            done = run(config(n=1), output, 24, mock=True, resume=True, retry_errors=True)
            self.assertEqual(done["valid_answers"], 24)
            self.assertEqual(done["attempts_total"], 25)
            attempts = load_attempts(output, read_plan(output))
            self.assertEqual(attempts[0]["request"], attempts[1]["request"])

    def test_invalid_return_cannot_be_resampled(self):
        output = self.root / "invalid"
        def invalid(*args):
            return provider.normalize({"model": "MOCK", "choices": [{"message": {
                "role": "assistant", "content": "A or B"}, "finish_reason": "stop"}]})
        result = run(config(n=1), output, 24, mock=True, complete_fn=invalid)
        self.assertEqual(result["stopped"], "invalid_response")
        with self.assertRaisesRegex(ValueError, "invalid"):
            run(config(n=1), output, 24, mock=True, resume=True, retry_errors=True)
        self.assertEqual(len(list((output / "attempts").glob("*.json"))), 1)

    def test_previous_run_is_rejected_without_modification(self):
        output = self.root / "old"
        output.mkdir()
        old = prior_plan(prior_config(ROOT / "configs/counterfactual.json"))
        write_json(output / "plan.json", old)
        before = (output / "plan.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "not a wording-study"):
            run(config(), output, 1, mock=True, resume=True)
        self.assertEqual((output / "plan.json").read_bytes(), before)
        self.assertFalse((output / "execution.json").exists())

    def test_config_source_mode_and_injected_live_responses_are_guarded(self):
        output = self.root / "frozen"
        cfg = config(n=1)
        run(cfg, output, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "Config differs"):
            run({**cfg, "seed": cfg["seed"] + 1}, output, 1, mock=True, resume=True)
        with patch("exception_wording.runner.source_digest", return_value="changed"):
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
