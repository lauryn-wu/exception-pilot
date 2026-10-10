"""Offline estimand checks; synthetic responses are never scientific evidence."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_query_role import analysis


def fixture(policy=None):
    """Twelve independent worlds, each with all twelve paired conditions."""
    tasks, attempts = [], []
    for index in range(12):
        family = "vehicle" if index < 6 else "configuration"
        world = f"{family}-{index:02d}"
        for query in analysis.QUERIES:
            encode = {"A": "A", "B": "B", "C": "C"} if query == "literal" else {"A": "4", "B": "2", "C": "7"}
            for arm in analysis.ARMS:
                for value in analysis.VALUES:
                    expected_source = "A" if value == "a" else "C"
                    task = {"id": f"{world}/{query}/{arm}/{value}", "world_id": world,
                            "family": family, "query": query, "arm": arm, "value": value,
                            "source_a": "A", "source_b": "C", "expected": encode[expected_source],
                            "pattern_label": encode["B"], "decode_map": {v: k for k, v in encode.items()},
                            "prompt": "Synthetic offline fixture."}
                    source = policy(index, query, arm, value, expected_source) if policy else expected_source
                    tasks.append(task)
                    attempts.append({"attempt": len(attempts) + 1, "task_id": task["id"],
                                     "mode": "live", "status": "complete", "format_valid": True,
                                     "answer": encode[source], "decoded_value": source,
                                     "score": {"A": -1, "B": 0, "C": 1}[source],
                                     "correct": source == expected_source, "pattern": source == "B"})
    return {"protocol": "query-conditioned-fact-use-v1", "tasks": tasks,
            "config": {"bootstrap_samples": 10000, "bootstrap_seed": 2026101002}}, attempts


def true_interaction(index, query, arm, value, expected):
    return "B" if query == "encoded" and arm == "visible" else expected


def invalidate(attempt):
    attempt.update(status="invalid", format_valid=False, answer=None, score=None,
                   decoded_value=None, invalid_reason="fixture_invalid")


class QueryRoleAnalysisTests(unittest.TestCase):
    def test_true_interaction_satisfies_practical_screen(self):
        plan, attempts = fixture(true_interaction)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertEqual(summary["metrics"]["primary_D"]["mean"], 1)
        self.assertEqual(summary["metrics"]["encoded_harm"]["mean"], 1)
        self.assertEqual(summary["metrics"]["downstream_visible_R"]["mean"], 1)
        self.assertEqual(summary["screen"]["decision"], "eligible_for_separate_heldout_review")
        self.assertTrue(summary["screen"]["practical_criteria_pass"])
        self.assertFalse(summary["screen"]["automatic_followup_authorized"])
        self.assertFalse(summary["screen"]["statistical_significance_test"])
        self.assertEqual(summary["conditions"]["encoded"]["visible"]["pattern"], 24)

    def test_all_correct_is_a_null_pattern_and_cannot_pass(self):
        plan, attempts = fixture()
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertEqual(summary["counts"]["correct"], 144)
        self.assertEqual(summary["metrics"]["primary_D"]["mean"], 0)
        self.assertEqual(summary["metrics"]["encoded_harm"]["mean"], 0)
        self.assertEqual(summary["screen"]["decision"], "stop_this_screen")
        self.assertIn("encoded_harm_worst_case_lower_bound", summary["screen"]["failed_criteria"])

    def test_downstream_improvement_alone_does_not_pass_positive_interaction(self):
        def policy(index, query, arm, value, expected):
            if index in (0, 6) and query == "downstream" and arm == "direct" and value == "b":
                return "A"
            return expected
        plan, attempts = fixture(policy)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertAlmostEqual(summary["metrics"]["primary_D"]["mean"], 1 / 6)
        self.assertEqual(summary["conditions"]["downstream"]["direct"]["correct"], 22)
        self.assertEqual(summary["metrics"]["encoded_harm"]["mean"], 0)
        self.assertEqual(summary["screen"]["decision"], "stop_this_screen")

    def test_invalid_bounds_can_block_an_apparently_qualifying_effect(self):
        def policy(index, query, arm, value, expected):
            if index in (0, 6) and query == "encoded" and arm == "visible" and value == "b":
                return "A"
            return expected
        plan, attempts = fixture(policy)
        baseline = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertTrue(baseline["screen"]["practical_criteria_pass"])
        damaged = next(row for row in attempts if row["task_id"] == "vehicle-00/encoded/visible/b")
        invalidate(damaged)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        bounds = summary["metrics"]["primary_D"]["full_plan_bounds"]
        self.assertAlmostEqual(bounds[0], 1 / 12)
        self.assertAlmostEqual(bounds[1], 1 / 6)
        self.assertEqual(summary["metrics"]["primary_D"]["n_complete_worlds"], 11)
        self.assertEqual(summary["metrics"]["literal_direct_R"]["n_complete_worlds"], 12)
        self.assertEqual(summary["screen"]["decision"], "stop_this_screen")
        self.assertEqual(summary["analysis_status"], "screen_complete_with_unscorable")
        self.assertEqual(summary["invalid_answers_retained"], 1)

    def test_missing_scores_are_bounded_and_never_advance_partial_collection(self):
        plan, attempts = fixture(true_interaction)
        summary = analysis.analyze(plan, attempts[:-1], {"mode": "live"})
        self.assertEqual(summary["analysis_status"], "incomplete")
        self.assertEqual(summary["pending_answers"], 1)
        self.assertIsNone(summary["screen"]["practical_criteria_pass"])
        self.assertTrue(all(row["passed"] is None for row in summary["screen"]["criteria"]))
        self.assertIsNone(summary["metrics"]["primary_D"]["descriptive_bootstrap_95_interval"])
        self.assertEqual(summary["metrics"]["primary_D"]["n_complete_worlds"], 11)
        self.assertEqual(summary["metrics"]["literal_direct_R"]["n_complete_worlds"], 12)
        self.assertEqual(summary["conditions"]["downstream"]["visible"]["planned"], 24)
        self.assertEqual(summary["conditions"]["downstream"]["visible"]["returned"], 23)

    def test_reverse_tracking_has_negative_responsiveness(self):
        def policy(index, query, arm, value, expected):
            return ("C" if value == "a" else "A") if query == "literal" and arm == "visible" else expected
        plan, attempts = fixture(policy)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertEqual(summary["metrics"]["literal_visible_R"]["mean"], -1)
        self.assertEqual(summary["metrics"]["literal_harm"]["mean"], 2)

    def test_bootstrap_clusters_worlds_and_preserves_family_counts(self):
        def policy(index, query, arm, value, expected):
            return "B" if index % 6 < 3 and query == "encoded" and arm == "visible" else expected
        plan, attempts = fixture(policy)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        primary = summary["metrics"]["primary_D"]
        self.assertEqual(primary["n_complete_worlds"], 12)
        self.assertEqual(primary["eligible_family_counts"], {"vehicle": 6, "configuration": 6})
        self.assertEqual(primary["mean"], .5)
        lower, upper = primary["descriptive_bootstrap_95_interval"]
        self.assertLessEqual(lower, .25)
        self.assertGreaterEqual(upper, .75)
        self.assertEqual(primary["descriptive_bootstrap_95_interval"],
                         analysis.analyze(plan, attempts, {"mode": "live"})["metrics"]["primary_D"]["descriptive_bootstrap_95_interval"])

    def test_shared_coefficients_cancel_before_missing_value_bounds(self):
        plan, _ = fixture()
        _, cells, _ = analysis._rows(plan, [])
        coefficients = analysis._coefficients((("encoded", "direct", 1), ("encoded", "direct", -1)))
        self.assertEqual(coefficients, {})
        self.assertEqual(analysis._linear_world(cells, "vehicle-00", coefficients),
                         {"value": 0.0, "bounds": [0.0, 0.0], "unscorable_or_pending": []})

    def test_mock_positive_is_never_scientific_advance(self):
        plan, attempts = fixture(true_interaction)
        for attempt in attempts:
            attempt["mode"] = "mock"
        summary = analysis.analyze(plan, attempts, {"mode": "mock"})
        self.assertTrue(summary["screen"]["practical_criteria_pass"])
        self.assertTrue(summary["is_simulated"])
        self.assertFalse(summary["screen"]["eligible_for_separate_heldout_review"])
        self.assertFalse(summary["interpretation_allowed"])
        self.assertEqual(summary["screen"]["decision"], "simulated_no_scientific_decision")

    def test_last_answer_operational_failure_blocks_numerically_positive_screen(self):
        plan, attempts = fixture(true_interaction)
        attempts[-1]["hard_failure"] = "unexpected_model"
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertTrue(summary["screen"]["practical_criteria_pass"])
        self.assertEqual(summary["collection_status"], "complete")
        self.assertEqual(summary["analysis_status"], "operational_failure_stop")
        self.assertEqual(summary["screen"]["decision"], "operational_stop")
        self.assertFalse(summary["interpretation_allowed"])
        self.assertFalse(summary["screen"]["eligible_for_separate_heldout_review"])

    def test_transport_attempt_does_not_count_as_returned_or_replace_original(self):
        plan, attempts = fixture()
        error = {"attempt": 1, "task_id": attempts[0]["task_id"], "status": "provider_error", "mode": "live"}
        summary = analysis.analyze(plan, [error] + attempts, {"mode": "live"})
        self.assertEqual(summary["attempts_total"], 145)
        self.assertEqual(summary["returned_answers"], 144)
        with self.assertRaisesRegex(ValueError, "returned task was repeated"):
            analysis.analyze(plan, attempts + [copy.deepcopy(attempts[0])], {"mode": "live"})

    def test_family_direction_gate_blocks_a_one_family_only_pattern(self):
        def policy(index, query, arm, value, expected):
            return "B" if index < 6 and query == "encoded" and arm == "visible" else expected
        plan, attempts = fixture(policy)
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertEqual(summary["metrics"]["primary_D"]["mean"], .5)
        self.assertIn("configuration_encoded_harm_worst_case_lower_bound", summary["screen"]["failed_criteria"])
        self.assertFalse(summary["screen"]["practical_criteria_pass"])

    def test_model_and_direct_adherence_are_reported_without_changing_gates(self):
        plan, attempts = fixture()
        direct_ids = {task["id"] for task in plan["tasks"] if task["arm"] == "direct"}
        for attempt in attempts:
            attempt["response"] = {"model": "fixture-model", "usage": {"prompt_tokens": 10}}
            if attempt["task_id"] in direct_ids:
                attempt["direct_instruction_adherent"] = True
        attempts[0]["direct_instruction_adherent"] = False
        summary = analysis.analyze(plan, attempts, {"mode": "live"})
        self.assertEqual(summary["observed_model"], "fixture-model")
        self.assertEqual(summary["observed_model_counts"], {"fixture-model": 144})
        self.assertEqual(summary["counts"]["direct_instruction_adherence"]["known"], 72)
        self.assertEqual(summary["counts"]["direct_instruction_adherence"]["adherent"], 71)
        self.assertEqual(summary["conditions"]["literal"]["direct"]["direct_instruction_adherence"]["nonadherent"], 1)
        self.assertEqual(summary["usage_all_attempts"]["prompt_tokens"], 1440)
        self.assertEqual(summary["screen"]["decision"], "stop_this_screen")

    def test_write_summary_lazily_reads_validated_run_and_writes_complete_artifacts(self):
        plan, attempts = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("exception_query_role.runner.read_run", return_value=(plan, {"mode": "mock"}, attempts)) as reader:
                result = analysis.write_summary(temporary)
            reader.assert_called_once_with(Path(temporary))
            saved = json.loads((Path(temporary) / "summary.json").read_text())
            self.assertEqual(saved, result)
            report = (Path(temporary) / "report.md").read_text()
            self.assertIn("SIMULATED SOFTWARE CHECK", report)
            self.assertIn("primary_D", report)
            self.assertEqual(sorted(path.name for path in Path(temporary).iterdir()), ["report.md", "summary.json"])


if __name__ == "__main__":
    unittest.main()
