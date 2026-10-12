import copy
from pathlib import Path
import unittest

from exception_columns.analysis import paired_statistics, record_pairs, score, summarize, transition_rows
from exception_columns.core import load_config, make_plan, task_meta

ROOT = Path(__file__).resolve().parents[1]


class ColumnAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(load_config(ROOT / "configs/columns_gpt4o.json"))

    def fixture(self):
        records = {}
        for task in self.plan["tasks"]:
            meta = task_meta(self.plan, task)
            answer = meta["pattern_label"] if task["arm"] == "cot" and task["schema"] in ("full", "description") else meta["expected"]
            records[task["id"]] = {"task_id": task["id"], "status": "complete", "answer": answer}
        return records

    def test_known_factorial_effects_and_world_denominator(self):
        stats = paired_statistics(self.plan, self.fixture())["accuracy"]
        self.assertEqual(stats["description_effect_on_reasoning_harm"]["estimate"], 1)
        self.assertEqual(stats["other_attributes_effect_on_reasoning_harm"]["estimate"], 0)
        self.assertEqual(stats["column_interaction_on_reasoning_harm"]["estimate"], 0)
        self.assertEqual(stats["copy_gain/full"]["estimate"], 1)
        self.assertEqual(stats["copy_gain/minimal"]["estimate"], 0)
        self.assertEqual(stats["cell/full/cot"]["complete_worlds"], 24)
        self.assertTrue(stats["description_effect_on_reasoning_harm"]["degenerate_interval"])

    def test_invalid_copy_does_not_remove_primary_world(self):
        records = self.fixture()
        key = next(t["id"] for t in self.plan["tasks"] if t["world_id"] == "ex-list-000" and t["schema"] == "minimal" and t["arm"] == "copy_class")
        records[key].update(status="invalid", answer=None)
        stats = paired_statistics(self.plan, records)["accuracy"]
        self.assertEqual(stats["description_effect_on_reasoning_harm"]["complete_worlds"], 24)
        self.assertEqual(stats["copy_gain/minimal"]["complete_worlds"], 23)
        self.assertEqual(stats["copy_gain/full"]["complete_worlds"], 24)

    def test_missing_bounds_respect_coefficient_signs(self):
        records = self.fixture()
        key = "ex-list-000/record_1/full/cot"
        del records[key]
        stats = paired_statistics(self.plan, records)
        primary = stats["accuracy"]["other_attributes_effect_on_reasoning_harm"]
        self.assertEqual(primary["complete_worlds"], 23)
        self.assertAlmostEqual(primary["full_plan_bounds"][0], -1 / 96)
        self.assertAlmostEqual(primary["full_plan_bounds"][1], 0)
        bounds = stats["record_sensitivity"]["other_attributes_effect_on_reasoning_harm"]["full_plan_bounds"]
        self.assertAlmostEqual(bounds[0], -1 / 96)
        self.assertAlmostEqual(bounds[1], 1 / 96)
        self.assertEqual(stats["accuracy"]["cell/minimal/direct"]["complete_worlds"], 24)

    def test_sensitivity_separates_fixed_answers_and_reversed_records(self):
        self.assertEqual((score("A", "A", "C", "record_sensitivity") + score("A", "B", "C", "record_sensitivity")) / 2, 0)
        self.assertEqual((score("B", "A", "C", "record_sensitivity") + score("A", "B", "C", "record_sensitivity")) / 2, -1)
        self.assertEqual((score("A", "A", "C", "record_sensitivity") + score("B", "B", "C", "record_sensitivity")) / 2, 1)

    def test_transition_export_keeps_every_case_and_direction(self):
        rows = transition_rows(self.plan, self.fixture())
        self.assertEqual(len(rows), 432)
        minimal_cot = [r for r in rows if r["arm"] == "cot" and r["reduced_schema"] == "minimal"]
        self.assertEqual(len(minimal_cot), 48)
        self.assertTrue(all(r["transition"] == "wrong_to_correct" and r["answer_changed"] for r in minimal_cot))
        records = self.fixture()
        records["ex-list-000/record_1/full/cot"].update(status="invalid", answer=None)
        rows = transition_rows(self.plan, records)
        self.assertEqual(sum(r["transition"] == "unresolved" for r in rows), 3)

    def test_record_pairs_require_both_answers(self):
        pairs = record_pairs(self.plan, self.fixture())
        self.assertEqual(len(pairs), 288)
        self.assertTrue(all(p["both_correct"] for p in pairs if p["arm"] == "copy_class"))
        self.assertTrue(all(not p["answers_differ"] for p in pairs if p["arm"] == "cot" and p["schema"] == "full"))

    def test_simulated_run_cannot_be_reported_as_live_success(self):
        summary, rows, _, _ = summarize(self.plan, {"mode": "mock"}, list(self.fixture().values()))
        self.assertEqual(summary["analysis_status"], "simulated_only")
        self.assertEqual(summary["returned_answers"], 576)
        self.assertEqual(summary["cells"]["full/cot"]["background_pattern_choices"], 48)
        self.assertEqual(summary["column_transitions"]["full_to_minimal/cot"]["wrong_to_correct"], 48)


if __name__ == "__main__":
    unittest.main()
