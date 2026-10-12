"""Offline synthetic checks of pairing, bounds and the frozen spending decision."""

import copy
import csv
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_row_position import analysis


CONFIG = {"model": "mistral-small-2603", "provider": "mistral", "max_total_attempts": 316}


def fixture(effect="positive"):
    """In-memory counterfactual data, never saved as live provider evidence."""
    worlds = [{"id": f"synthetic-{index:02d}",
               "roles": {"record_1": "A", "record_2": "B", "pattern": "C"}}
              for index in range(24)]
    tasks, attempts = [], []
    for index, world in enumerate(worlds):
        for value in ("record_1", "record_2"):
            for position in (1, 5, 10):
                for arm in ("direct", "visible"):
                    task = {"id": f"{world['id']}/{value}/{position}/{arm}",
                            "world_id": world["id"], "value": value,
                            "position": position, "arm": arm}
                    tasks.append(task)
                    expected = world["roles"][value]
                    harmed = arm == "visible" and (
                        effect == "positive" and index < 12 and position == 10
                        or effect == "negative" and index < 12 and position == 1
                        or effect == "constant_positive" and position == 10
                        or effect == "constant_negative" and position == 1
                        or effect == "small" and ((index < 2 and position == 10)
                                                  or (2 <= index < 4 and position == 1)))
                    answer = "C" if harmed else expected
                    attempts.append({
                        "attempt": len(attempts) + 1, "task_id": task["id"], "status": "complete",
                        "answer": answer, "meta": {**{key: task[key] for key in ("world_id", "value", "position", "arm")},
                                                  "expected": expected, "pattern_label": "C"},
                        "response": {"model": CONFIG["model"], "usage": {"completion_tokens": 20}},
                        "answer_only": arm == "direct", "pre_answer_text": arm == "visible",
                        "pre_answer_words": 5 if arm == "visible" else 0,
                        "strict_answer_match": True, "output_contract_met": True})
    plan = {"protocol_version": "SYNTHETIC-ANALYSIS-FIXTURE", "plan_hash": "SYNTHETIC",
            "worlds": worlds, "tasks": tasks}
    return plan, attempts


def synthetic_meta(plan, task):
    world = next(world for world in plan["worlds"] if world["id"] == task["world_id"])
    return {"world_id": world["id"], "value": task["value"], "position": task["position"],
            "arm": task["arm"], "expected": world["roles"][task["value"]],
            "pattern_label": world["roles"]["pattern"]}


class RowPositionAnalysisTests(unittest.TestCase):
    def setUp(self):
        networking = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline test"))
        networking.start()
        self.addCleanup(networking.stop)

    def test_world_pairing_and_primary_uses_only_endpoints(self):
        plan, attempts = fixture()
        records = {record["task_id"]: record for record in attempts}
        stats = analysis.paired_statistics(plan, records)
        primary = stats["accuracy"]["interaction"]
        self.assertEqual(primary["estimate"], .5)
        self.assertEqual(primary["complete_worlds"], 24)
        self.assertEqual(primary["sign_test"]["positive"], 12)
        self.assertEqual(primary["sign_test"]["ties"], 12)
        self.assertLess(primary["ci95"][0], .5)
        self.assertGreater(primary["ci95"][1], .5)
        shape = stats["accuracy"]["middle_harm_minus_endpoint_average"]
        self.assertEqual(shape["estimate"], -.25)
        self.assertEqual(shape["worlds"][0]["value"], -.5)
        self.assertEqual(shape["complete_worlds"], 24)
        middle = next(record for record in attempts if record["meta"]["position"] == 5)
        del records[middle["task_id"]]
        stats = analysis.paired_statistics(plan, records)
        self.assertEqual(stats["accuracy"]["interaction"]["complete_worlds"], 24)
        self.assertEqual(stats["accuracy"]["interaction"]["estimate"], .5)
        self.assertEqual(stats["accuracy"]["5_direct_minus_visible"]["complete_worlds"], 23)
        self.assertEqual(stats["accuracy"]["5/direct"]["complete_worlds"], 23)
        self.assertEqual(stats["accuracy"]["5/visible"]["complete_worlds"], 24)
        self.assertEqual(stats["accuracy"]["middle_harm_minus_endpoint_average"]["complete_worlds"], 23)

    def test_variants_are_averaged_not_counted_as_independent_worlds(self):
        plan, attempts = fixture()
        for record in attempts:
            if record["meta"]["value"] == "record_2":
                record["answer"] = record["meta"]["expected"]
        stats = analysis.paired_statistics(plan, {record["task_id"]: record for record in attempts})
        self.assertEqual(stats["accuracy"]["interaction"]["estimate"], .25)
        self.assertEqual(stats["accuracy"]["interaction"]["complete_worlds"], 24)
        self.assertEqual(stats["accuracy"]["interaction"]["worlds"][0]["value"], .5)

    def test_invalid_endpoint_is_unknown_and_bounds_preserve_sign(self):
        plan, attempts = fixture()
        records = {record["task_id"]: record for record in attempts}
        task = next(task for task in plan["tasks"] if task["position"] == 10 and task["arm"] == "visible")
        records[task["id"]].update(status="invalid", answer=None)
        stats = analysis.paired_statistics(plan, records)
        primary = stats["accuracy"]["interaction"]
        self.assertEqual(primary["complete_worlds"], 23)
        self.assertAlmostEqual(primary["full_plan_bounds"][0], .5 - 1 / 48)
        self.assertEqual(primary["full_plan_bounds"][1], .5)
        self.assertIsNone(primary["worlds"][0]["value"])
        self.assertFalse(primary["worlds"][0]["complete"])
        sensitivity = stats["record_sensitivity"]["interaction"]["full_plan_bounds"]
        self.assertAlmostEqual(sensitivity[1] - sensitivity[0], 1 / 24)
        # Removing a positive-coefficient correct response has the same accuracy
        # endpoints here, not a spurious negative score or reversed interval.
        plan, attempts = fixture()
        records = {record["task_id"]: record for record in attempts}
        task = next(task for task in plan["tasks"] if task["position"] == 1 and task["arm"] == "visible")
        del records[task["id"]]
        primary = analysis.paired_statistics(plan, records)["accuracy"]["interaction"]
        self.assertAlmostEqual(primary["full_plan_bounds"][0], .5 - 1 / 48)
        self.assertEqual(primary["full_plan_bounds"][1], .5)

    def test_empty_data_bounds_and_no_invented_correctness(self):
        plan, _ = fixture()
        result = analysis.summarize(plan, CONFIG, None, [])
        self.assertEqual(result["decision"], "not_started")
        self.assertEqual(result["valid_answers"], 0)
        self.assertIsNone(result["controls"]["1/direct"]["accuracy_valid_only"])
        primary = result["metrics"]["accuracy"]["interaction"]
        self.assertIsNone(primary["estimate"])
        self.assertEqual(primary["full_plan_bounds"], [-2, 2])
        self.assertEqual(result["metrics"]["record_sensitivity"]["interaction"]["full_plan_bounds"], [-4, 4])

    def test_positive_and_negative_interactions_can_recommend_review(self):
        for effect, direction in (("positive", "last_more_harm"), ("negative", "first_more_harm")):
            plan, attempts = fixture(effect)
            result = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
            self.assertEqual(result["decision"], "review_fresh_world_confirmation")
            self.assertEqual(result["primary_direction"], direction)
            self.assertEqual(result["returned_answers"], 288)

    def test_small_nonconstant_effect_deprioritizes_without_equivalence_claim(self):
        plan, attempts = fixture("small")
        result = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
        self.assertEqual(result["decision"], "deprioritize_first_last")
        self.assertGreater(result["primary_uncertainty_envelope"][0], -.2)
        self.assertLess(result["primary_uncertainty_envelope"][1], .2)

    def test_degenerate_large_effect_prompts_review_but_zero_cannot_deprioritize(self):
        for effect, decision in (("zero", "inconclusive"),
                                 ("constant_positive", "review_fresh_world_confirmation"),
                                 ("constant_negative", "review_fresh_world_confirmation")):
            plan, attempts = fixture(effect)
            result = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
            self.assertTrue(result["metrics"]["accuracy"]["interaction"]["bootstrap_degenerate"])
            self.assertEqual(result["decision"], decision)
            self.assertIn("cannot calibrate precision", result["primary_bootstrap_warning"])

    def test_completion_identity_and_output_controls_gate_before_effect(self):
        plan, attempts = fixture()
        baseline = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
        changed = copy.deepcopy(baseline)
        changed["is_simulated"] = True
        self.assertEqual(analysis.local_decision(changed), "simulated_only")
        changed = copy.deepcopy(baseline)
        changed["returned_answers"] = 287
        self.assertEqual(analysis.local_decision(changed), "incomplete")
        changed = copy.deepcopy(baseline)
        changed["model_identity_failures"] = 1
        self.assertEqual(analysis.local_decision(changed), "model_identity_failure")
        attempts[0]["response"]["model"] = None
        missing_identity = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
        self.assertEqual(missing_identity["model_identity_failures"], 1)
        self.assertEqual(missing_identity["decision"], "model_identity_failure")
        changed = copy.deepcopy(baseline)
        changed["controls"]["5/direct"]["manipulation_adherence_fraction"] = 45 / 48
        self.assertEqual(analysis.local_decision(changed), "output_manipulation_inconclusive")
        changed = copy.deepcopy(baseline)
        changed["metrics"]["accuracy"]["interaction"]["complete_worlds"] = 21
        self.assertEqual(analysis.local_decision(changed), "insufficient_complete_worlds")

    def test_decision_uses_bounds_and_uncertainty_not_just_point_or_sign_p(self):
        plan, attempts = fixture()
        baseline = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
        changed = copy.deepcopy(baseline)
        changed["metrics"]["accuracy"]["interaction"]["full_plan_bounds"] = [.19, .6]
        self.assertEqual(analysis.local_decision(changed), "inconclusive")
        changed = copy.deepcopy(baseline)
        changed["metrics"]["accuracy"]["interaction"]["ci95"] = [-.01, .8]
        self.assertEqual(analysis.local_decision(changed), "inconclusive")
        changed = copy.deepcopy(baseline)
        changed["metrics"]["accuracy"]["interaction"]["sign_test"]["p_two_sided"] = 1.
        self.assertEqual(analysis.local_decision(changed), "review_fresh_world_confirmation")
        changed = copy.deepcopy(baseline)
        primary = changed["metrics"]["accuracy"]["interaction"]
        primary.update(estimate=0, ci95=[-.2, .1], full_plan_bounds=[0, 0])
        self.assertEqual(analysis.local_decision(changed), "inconclusive")

    def test_controls_keep_all_planned_in_denominator_and_error_taxonomy(self):
        plan, attempts = fixture("zero")
        selected = [record for record in attempts if record["meta"]["position"] == 5 and record["meta"]["arm"] == "direct"]
        selected[0]["answer"] = "C"
        selected[1]["answer"] = "A"  # Other target label; expected B.
        selected[2].update(status="invalid", answer=None, answer_only=None)
        attempts.remove(selected[3])
        result = analysis.summarize(plan, CONFIG, {"mode": "live"}, attempts)
        cell = result["controls"]["5/direct"]
        self.assertEqual((cell["correct"], cell["wrong"], cell["pattern_choices"], cell["other_wrong"]), (44, 2, 1, 1))
        self.assertEqual((cell["valid"], cell["invalid"], cell["unreturned"]), (46, 1, 1))
        self.assertEqual(cell["answer_only_fraction"], 46 / 48)
        self.assertEqual(result["decision"], "incomplete")

    def test_sign_test_reports_ties_and_sensitivity_full_scale(self):
        self.assertEqual(analysis.sign_test([0, 0]), {"p_two_sided": 1., "positive": 0, "negative": 0, "ties": 2})
        self.assertEqual(analysis.sign_test([1, -1, 0])["p_two_sided"], 1.)
        self.assertEqual(analysis.sign_test([1] * 6 + [0] * 18)["p_two_sided"], .03125)
        self.assertEqual(analysis.record_score("A", "A", "C", "record_sensitivity"), 1)
        self.assertEqual(analysis.record_score("B", "A", "C", "record_sensitivity"), -1)
        self.assertEqual(analysis.record_score("C", "A", "C", "record_sensitivity"), 0)

    def test_report_exports_worlds_and_retains_unknown_cells(self):
        plan, attempts = fixture()
        attempts[0].update(status="invalid", answer=None, answer_only=None)
        with tempfile.TemporaryDirectory() as directory:
            with patch("exception_row_position.runner.read_run", return_value=(plan, CONFIG, {"mode": "mock"}, attempts)), patch.object(analysis, "task_meta", side_effect=synthetic_meta):
                result = analysis.write_summary(directory)
            self.assertEqual(result["decision"], "simulated_only")
            path = Path(directory)
            saved = json.loads((path / "summary.json").read_text())
            self.assertEqual(saved["invalid_answers"], 1)
            with (path / "answers.csv").open() as stream:
                answers = list(csv.DictReader(stream))
            self.assertEqual(answers[0]["correct"], "")
            self.assertEqual(answers[0]["status"], "invalid")
            with (path / "world_contrasts.csv").open() as stream:
                world_rows = list(csv.DictReader(stream))
            self.assertEqual(len(world_rows), 2 * len(analysis.estimands()) * 24)
            self.assertIn("SIMULATED", (path / "summary.md").read_text())


if __name__ == "__main__":
    unittest.main()
