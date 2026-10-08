"""Offline scientific-invariant and recovery tests; no paid model requests."""

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.core import make_plan as original_plan, load_config as original_config, opposite
from exception_pilot.storage import load_attempts, run_lock, write_json
from exception_counterfactual.analysis import summarize, write_summary
from exception_counterfactual.core import (load_config, make_plan, messages_for, read_plan,
                                          request_for, task_meta, validate_config)
from exception_counterfactual.runner import run

ROOT = Path(__file__).resolve().parents[1]


def config(n=20):
    cfg = load_config(ROOT / "configs/counterfactual.json")
    cfg["n_lists"] = n
    return cfg


def fixture(plan, wrong=lambda task: False):
    records = []
    for i, task in enumerate(plan["tasks"]):
        label = task_meta(plan, task)["expected"]
        if wrong(task):
            label = opposite(label)
        records.append({"attempt": i + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                        "status": "complete", "answer": label,
                        "response": {"text": "Fixture only.\n" + label, "complete": True}})
    return records


class CounterfactualDesignTests(unittest.TestCase):
    def test_exact_count_reproducibility_and_disjoint_original_ids(self):
        plan = make_plan(config())
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["tasks"]), 160)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 160)
        ids = {x["id"] for w in plan["worlds"] for x in w["items"]}
        self.assertEqual(len(ids), 200)
        for stage in (1, 2):
            old = original_plan(original_config(ROOT / f"configs/stage{stage}.json"))
            self.assertFalse(ids & {x["id"] for w in old["worlds"] for x in w["items"]})
        changed = config()
        changed["seed"] += 1
        self.assertNotEqual(plan["worlds"], make_plan(changed)["worlds"])

    def test_constant_80_percent_rule_and_balanced_classes_over_multiple_seeds(self):
        for seed in (11, 123, config()["seed"]):
            cfg = config()
            cfg["seed"] = seed
            for world in make_plan(cfg)["worlds"]:
                for background in ("conflict", "support"):
                    labels = world["labels"][background]
                    self.assertEqual(labels.count("A"), 5)
                    disagreements = []
                    for climate in ("cold", "warm"):
                        ix = [i for i, x in enumerate(world["items"]) if x["climate"] == climate]
                        frequencies = {label: sum(labels[i] == label for i in ix) for label in ("A", "B")}
                        self.assertEqual(sorted(frequencies.values()), [1, 4])
                        majority = max(frequencies, key=frequencies.get)
                        disagreements += [i for i in ix if labels[i] != majority]
                    self.assertEqual(len(disagreements), 2)
                    self.assertEqual(set(disagreements), set(world["target_indices"] if background == "conflict"
                                                           else world["support_exception_indices"]))

    def test_only_six_nontarget_labels_change_in_actual_prompts(self):
        plan = make_plan(config())
        for world in plan["worlds"]:
            for index in world["target_indices"]:
                tasks = {t["background"]: t for t in plan["tasks"] if t["world_id"] == world["id"]
                         and t["item_index"] == index and t["condition"] == "direct"}
                texts = {bg: messages_for(plan, task)[0]["content"] for bg, task in tasks.items()}
                self.assertEqual(len(texts["conflict"]), len(texts["support"]))
                differences = [(a, b) for a, b in zip(texts["conflict"].splitlines(), texts["support"].splitlines()) if a != b]
                self.assertEqual(len(differences), 6)
                for a, b in differences:
                    self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])
                    self.assertNotIn(world["items"][index]["id"], a)
                self.assertEqual(task_meta(plan, tasks["conflict"])["expected"],
                                 task_meta(plan, tasks["support"])["expected"])
                self.assertTrue(task_meta(plan, tasks["conflict"])["is_exception_in_this_background"])
                self.assertFalse(task_meta(plan, tasks["support"])["is_exception_in_this_background"])

    def test_evidence_and_positions_identical_across_response_arms(self):
        plan = make_plan(config(n=2))
        for task in plan["tasks"]:
            other = next(t for t in plan["tasks"] if t["world_id"] == task["world_id"]
                         and t["item_index"] == task["item_index"] and t["background"] == task["background"]
                         and t["condition"] != task["condition"])
            one, two = messages_for(plan, task), messages_for(plan, other)
            self.assertEqual(len(one), 1)
            self.assertEqual(one[0]["role"], "user")
            self.assertEqual(one[0]["content"].rsplit("\n", 1)[0], two[0]["content"].rsplit("\n", 1)[0])
            self.assertEqual(task_meta(plan, task)["target_position"], task_meta(plan, other)["target_position"])
            for forbidden in ("conflict", "support", "80%", "20%", "exception", "target_indices", "SIMULATED"):
                self.assertNotIn(forbidden, one[0]["content"])

    def test_same_snapshot_caps_and_no_credentials_in_request(self):
        plan = make_plan(config(n=1))
        for task in plan["tasks"]:
            request = request_for(plan, task)
            self.assertEqual(request["model"], "gpt-4o-2024-08-06")
            self.assertEqual(request["max_completion_tokens"], 10 if task["condition"] == "direct" else 1000)
            self.assertNotIn("api_key_env", request)
            self.assertFalse(request["store"])

    def test_wrong_protocol_or_changed_model_and_caps_rejected(self):
        for key, value in (("protocol", "exception-pilot-v1"), ("model", "gpt-4o"),
                           ("temperature", 0.5), ("max_completion_tokens", {"direct": 10, "cot": 20}),
                           ("timeout_seconds", float("nan")), ("n_lists", True)):
            cfg = config()
            cfg[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config(cfg)


class CounterfactualAnalysisTests(unittest.TestCase):
    def test_hand_calculated_threshold_interaction_and_transitions(self):
        plan = make_plan(config())
        # Exactly six errors / 40 targets = 15 pp; only three independent lists affected.
        wrong = lambda t: t["world_id"] in {"cf-list-000", "cf-list-001", "cf-list-002"} and t["condition"] == "cot" and t["background"] == "conflict"
        result, _ = summarize(plan, fixture(plan, wrong))
        self.assertAlmostEqual(result["effects"]["extra_conflict_penalty"]["mean"], 0.15)
        self.assertEqual(result["paired_lists"], 20)
        self.assertEqual(result["effects"]["extra_conflict_penalty"]["positive_lists"], 3)
        self.assertEqual(result["screen"]["decision"], "review_for_confirmation")
        self.assertEqual(result["support_to_conflict_transitions"]["cot"]["correct_to_wrong"], 6)
        self.assertEqual(result["support_to_conflict_transitions"]["direct"]["correct_in_both"], 40)
        self.assertEqual(result["effects"]["extra_conflict_penalty"]["paired_bootstrap_95_ci"][0], 0)

    def test_five_errors_below_threshold_stops(self):
        plan = make_plan(config())
        bad = {t["id"] for t in [t for t in plan["tasks"] if t["condition"] == "cot" and t["background"] == "conflict"][:5]}
        result, _ = summarize(plan, fixture(plan, lambda t: t["id"] in bad))
        self.assertAlmostEqual(result["effects"]["extra_conflict_penalty"]["mean"], 0.125)
        self.assertEqual(result["screen"]["decision"], "stop_this_extension")

    def test_null_and_common_conflict_harm_do_not_qualify(self):
        plan = make_plan(config())
        for wrong in (lambda t: False, lambda t: t["background"] == "conflict"):
            result, _ = summarize(plan, fixture(plan, wrong))
            self.assertEqual(result["effects"]["extra_conflict_penalty"]["mean"], 0)
            self.assertEqual(result["screen"]["decision"], "stop_this_extension")

    def test_positive_interaction_without_actual_cot_harm_is_flagged(self):
        plan = make_plan(config())
        cases = [lambda t: t["condition"] == "direct" and t["background"] == "support",
                 lambda t: t["condition"] == "direct" or (t["background"] == "conflict" and int(t["world_id"][-3:]) < 10)]
        for wrong in cases:
            result, _ = summarize(plan, fixture(plan, wrong))
            self.assertGreater(result["effects"]["extra_conflict_penalty"]["mean"], 0.15)
            self.assertEqual(result["screen"]["decision"], "stop_direction_mismatch")

    def test_missing_invalid_and_small_runs_do_not_pass(self):
        plan = make_plan(config())
        records = fixture(plan)
        partial, _ = summarize(plan, records[:-1])
        self.assertEqual(partial["paired_lists"], 19)
        self.assertEqual(partial["screen"]["decision"], "incomplete")
        records[-1].update(status="invalid", answer=None)
        invalid, rows = summarize(plan, records)
        self.assertEqual(invalid["screen"]["decision"], "technical_failure")
        self.assertIsNone(rows[-1]["correct"])
        small = make_plan(config(n=1))
        self.assertEqual(summarize(small, fixture(small))[0]["screen"]["decision"], "insufficient_lists")

    def test_simulation_never_labeled_scientific_evidence(self):
        plan = make_plan(config())
        records = fixture(plan, lambda t: t["condition"] == "cot" and t["background"] == "conflict")
        result, _ = summarize(plan, records, "mock")
        self.assertEqual(result["screen"]["decision"], "simulated_not_evidence")
        self.assertTrue(result["screen"]["numeric_threshold_met"])

    def test_stored_answer_cannot_disagree_with_actual_content(self):
        plan = make_plan(config(n=1))
        records = fixture(plan)
        records[0]["answer"] = opposite(records[0]["answer"])
        with self.assertRaisesRegex(ValueError, "disagrees"):
            summarize(plan, records)


class CounterfactualRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def test_resume_matches_uninterrupted_and_finished_resume_makes_no_calls(self):
        cfg = config(n=2)
        a, b = self.root / "a", self.root / "b"
        self.assertEqual(run(cfg, a, 3, mock=True)["calls_this_invocation"], 3)
        with self.assertRaisesRegex(ValueError, "resume"):
            run(cfg, a, 16, mock=True)
        self.assertEqual(run(cfg, a, 16, mock=True, resume=True)["calls_this_invocation"], 13)
        run(cfg, b, 16, mock=True)
        aa, bb = load_attempts(a, read_plan(a)), load_attempts(b, read_plan(b))
        self.assertEqual([(r["request"], r["answer"]) for r in aa], [(r["request"], r["answer"]) for r in bb])
        self.assertEqual(run(cfg, a, 16, mock=True, resume=True)["calls_this_invocation"], 0)
        self.assertEqual(len(json.loads((a / "preview.json").read_text())), 8)
        self.assertIn("Both worlds", (a / "preview.md").read_text())

    def test_timeout_and_interruption_require_explicit_retry(self):
        for name, exception in (("timeout", provider.ProviderError("TimeoutError")), ("interrupt", KeyboardInterrupt())):
            dest = self.root / name
            def fail(*args):
                raise exception
            run(config(n=1), dest, 8, mock=True, complete_fn=fail)
            result = run(config(n=1), dest, 8, mock=True, resume=True)
            self.assertEqual(result["stopped"], "retry_requires_flag")
            result = run(config(n=1), dest, 8, mock=True, resume=True, retry_errors=True)
            self.assertEqual(result["valid_answers"], 8)
            attempts = load_attempts(dest, read_plan(dest))
            self.assertEqual(attempts[0]["request"], attempts[1]["request"])

    def test_invalid_answer_never_resampled(self):
        dest = self.root / "bad"
        result = run(config(n=1), dest, 8, mock=True, complete_fn=lambda *args:
                     {"text": "A", "complete": False, "finish_reason": "length"})
        self.assertEqual(result["stopped"], "invalid_response")
        self.assertEqual(result["valid_answers"], 0)
        with self.assertRaisesRegex(ValueError, "invalid"):
            run(config(n=1), dest, 8, mock=True, resume=True, retry_errors=True)

    def test_original_run_and_config_are_rejected_without_overwriting(self):
        dest = self.root / "original"
        dest.mkdir()
        old = original_plan(original_config(ROOT / "configs/stage1.json"))
        write_json(dest / "plan.json", old)
        before = (dest / "plan.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "not a counterfactual"):
            run(config(), dest, 8, mock=True)
        with self.assertRaisesRegex(ValueError, "not a counterfactual"):
            write_summary(dest)
        self.assertEqual((dest / "plan.json").read_bytes(), before)
        self.assertFalse((dest / "summary.json").exists())

    def test_config_code_plan_and_mode_changes_block_resume(self):
        dest = self.root / "run"
        cfg = config(n=1)
        run(cfg, dest, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "mode"):
            run(cfg, dest, 8, resume=True)
        changed = copy.deepcopy(cfg)
        changed["seed"] += 1
        with self.assertRaisesRegex(ValueError, "Config"):
            run(changed, dest, 8, mock=True, resume=True)
        with patch("exception_counterfactual.runner.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code"):
                run(cfg, dest, 8, mock=True, resume=True)
        plan = read_plan(dest)
        plan["worlds"][0]["labels"]["conflict"][0] = "bad"
        write_json(dest / "plan.json", plan)
        with self.assertRaisesRegex(ValueError, "integrity"):
            read_plan(dest)

    def test_injected_response_cannot_be_labeled_live(self):
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(n=1), self.root / "run", 1, complete_fn=lambda *args: {})

    def test_missing_execution_identity_cannot_turn_mock_into_real_results(self):
        dest = self.root / "run"
        run(config(n=1), dest, 8, mock=True)
        before = (dest / "summary.json").read_bytes()
        (dest / "execution.json").unlink()
        with self.assertRaisesRegex(ValueError, "execution identity"):
            write_summary(dest)
        self.assertEqual((dest / "summary.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
