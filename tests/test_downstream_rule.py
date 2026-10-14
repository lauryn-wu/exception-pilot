"""Independent checks of the prediction-rule factorial; no live provider calls."""

from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from exception_columns import provider
from exception_downstream import core as original
from exception_downstream_history import analysis as history_analysis
from exception_downstream_history import core as history
from exception_downstream_rule import analysis, core
from exception_study_support.core import content_digest
from exception_study_support.runner import prepare, read_run, run


CONFIG = "configs/downstream_rule_gpt4o.json"
HP_RP = "history_present_rule_present"
HA_RP = "history_absent_rule_present"
HP_RA = "history_present_rule_absent"
HA_RA = "history_absent_rule_absent"
ARMS = (HP_RP, HA_RP, HP_RA, HA_RA)
RULE = " If that cell is MISSING, make your best prediction from the other records."
FACTORS = {
    HP_RP: {"history_present": True, "prediction_rule_present": True},
    HA_RP: {"history_present": False, "prediction_rule_present": True},
    HP_RA: {"history_present": True, "prediction_rule_present": False},
    HA_RA: {"history_present": False, "prediction_rule_present": False},
}


def source_parts(case):
    parts = case["source_request"]["messages"][0]["content"].split("\n\n")
    assert len(parts) == 3
    return parts


def table_gold(case):
    table = source_parts(case)[1].splitlines()
    header = [cell.strip() for cell in table[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in table[2:]]
    target = [row for row in rows if row[header.index("License plate")] == case["item_id"]]
    assert len(target) == 1
    return target[0][header.index("Verified class")]


def answer_record(task, answer):
    return {"task_id": task["id"], **core.score_response(task, {
        "text": answer, "complete": True, "model_identity": "match"})}


class DownstreamRuleControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(CONFIG)
        cls.plan = core.make_plan(cls.config)
        cls.history_plan = history.make_plan(history.load_config("configs/downstream_history_gpt4o.json"))

    def test_all_432_payloads_are_independently_reconstructed_from_frozen_sources(self):
        cases = {case["id"]: case for case in self.plan["cases"]}
        old_tasks = {(t["case_id"], t["arm"], t["repetition"]): t for t in self.history_plan["tasks"]}
        for task in self.plan["tasks"]:
            case = cases[task["case_id"]]
            intro, table, tail = source_parts(case)
            factors = FACTORS[task["arm"]]
            self.assertEqual(intro.count(RULE), 1)
            self.assertTrue(intro.endswith(RULE))
            if not factors["prediction_rule_present"]:
                intro = intro[:-len(RULE)]
            question = (f"What is written in {case['item_id']}'s Verified class cell? "
                        "Reply with exactly one of A, B, C, or MISSING.")
            if factors["history_present"]:
                messages = [
                    {"role": "user", "content": "\n\n".join((intro, table, tail))},
                    {"role": "assistant", "content": case["source_response"]["text"]},
                    {"role": "user", "content": question},
                ]
            else:
                messages = [{"role": "user", "content": "\n\n".join((intro, table, question))}]
            expected = {"model": "gpt-4o-2024-08-06", "temperature": 0,
                        "max_completion_tokens": 64, "n": 1, "store": False,
                        "messages": messages}
            self.assertEqual(core.request_for(self.plan, task), expected, task["id"])
            self.assertEqual(task["expected"], table_gold(case))
            self.assertIn("MISSING means the verified class has not been recorded.", messages[0]["content"])
            if factors["prediction_rule_present"]:
                old_arm = "history_present" if factors["history_present"] else "history_absent"
                old = old_tasks[task["case_id"], old_arm, task["repetition"]]
                self.assertEqual(core.request_for(self.plan, task),
                                 history.request_for(self.history_plan, old))

    def test_frozen_cases_factors_and_adjacent_randomized_quadruplets(self):
        self.assertEqual(self.plan["cases"], self.history_plan["cases"])
        self.assertEqual(Counter(c["cohort"] for c in self.plan["cases"]), {
            "contradiction": 13, "availability_control": 13,
            "genuine_missing_control": 9, "wrong_final_diagnostic": 1})
        self.assertEqual({c["schema"] for c in self.plan["cases"]}, {"full", "other_attributes"})
        self.assertEqual(tuple(core.ARMS), ARMS)
        self.assertEqual(core.ARM_FACTORS, FACTORS)
        tasks = self.plan["tasks"]
        self.assertEqual(len(tasks), 432)
        self.assertEqual(len({t["id"] for t in tasks}), 432)
        self.assertEqual(Counter(t["arm"] for t in tasks), dict.fromkeys(ARMS, 108))
        orders, pairs = Counter(), set()
        for start in range(0, len(tasks), 4):
            block = tasks[start:start + 4]
            self.assertEqual({t["arm"] for t in block}, set(ARMS))
            for key in ("case_id", "world_id", "cohort", "repetition", "expected"):
                self.assertEqual(len({t[key] for t in block}), 1)
            pairs.add((block[0]["case_id"], block[0]["repetition"]))
            orders[tuple(t["arm"] for t in block)] += 1
        self.assertEqual(len(pairs), 108)
        self.assertGreater(len(orders), 1)
        seen, previous = set(), None
        for task in tasks:
            if task["world_id"] != previous:
                self.assertNotIn(task["world_id"], seen)
                seen.add(task["world_id"])
                previous = task["world_id"]
        self.assertEqual(self.plan, core.make_plan(self.config))

    def test_rule_removal_fails_closed_if_the_source_boundary_or_rule_changes(self):
        task = next(t for t in self.plan["tasks"] if t["arm"] == HP_RA)
        for change in (
                lambda text: text.replace(RULE, ""),
                lambda text: text.replace(RULE, RULE + RULE),
                lambda text: text.replace("best prediction", "best guess"),
                lambda text: text.replace("Every record is accurate.", "Some records are accurate."),
                lambda text: text + "\n\nAnother task: predict a class."):
            plan = deepcopy(self.plan)
            case = next(c for c in plan["cases"] if c["id"] == task["case_id"])
            request = case["source_request"]
            request["messages"][0]["content"] = change(request["messages"][0]["content"])
            case["request_digest"] = content_digest(request)
            with self.assertRaises(ValueError):
                core.request_for(plan, task)

    def test_config_does_not_allow_unplanned_sampling_or_budget_changes(self):
        self.assertEqual(self.config["max_total_attempts"], 480)
        for key, value in (("model", "different-model"), ("repetitions", 1),
                           ("temperature", 1), ("max_completion_tokens", 128),
                           ("max_total_attempts", 10000), ("repetitions", True),
                           ("schedule_seed", self.config["schedule_seed"] + 1)):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    core.make_plan({**self.config, key: value})

    def test_new_and_inherited_source_changes_invalidate_a_saved_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            for package in ("exception_downstream_rule", "exception_downstream_history",
                            "exception_downstream", "exception_study_support", "exception_columns",
                            "exception_pilot", "exception_mistral_map_v3", "exception_explanation"):
                shutil.copytree(core.ROOT / package, root / package,
                                ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(core.ROOT / "configs", root / "configs")
            shutil.copyfile(core.ROOT / "pyproject.toml", root / "pyproject.toml")
            for path in core.ROOT.glob("*.md"):
                shutil.copyfile(path, root / path.name)
            with patch.object(core, "ROOT", root), patch.object(history, "ROOT", root), \
                    patch.object(original, "ROOT", root), redirect_stdout(io.StringIO()):
                output = Path(directory) / "run"
                prepare(core, self.config, output)
                for relative in ("exception_downstream_rule/core.py", "exception_downstream_rule/analysis.py",
                                 "exception_downstream_history/core.py", "exception_downstream_history/analysis.py",
                                 "exception_downstream/source_snapshot.json", "exception_study_support/runner.py",
                                 "configs/downstream_rule_gpt4o.json", "DOWNSTREAM_RULE_PROTOCOL.md"):
                    with self.subTest(path=relative):
                        path = root / relative
                        before = path.read_bytes()
                        path.write_bytes(before + b"\n")
                        try:
                            with self.assertRaises(ValueError):
                                read_run(core, output)
                        finally:
                            path.write_bytes(before)
                self.assertEqual(read_run(core, output)[0]["plan_hash"],
                                 core.make_plan(self.config)["plan_hash"])


class DownstreamRuleAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan(core.load_config(CONFIG))
        # Small resampling count is enough for deterministic arithmetic checks.
        cls.plan["analysis_plan"]["bootstrap_replicates"] = 100

    def records(self, answers=None):
        return {t["id"]: answer_record(t, answers(t) if answers else t["expected"])
                for t in self.plan["tasks"]}

    def test_primary_direction_and_equal_world_weighting_not_pooled_calls(self):
        records = self.records(lambda t: "A" if t["cohort"] == "genuine_missing_control"
                               and t["arm"] == HA_RP else t["expected"])
        summary = analysis.summarize(self.plan, list(records.values()), {"mode": "live"})
        primary = summary["primary"]
        self.assertEqual(primary["cohort"], "genuine_missing_control")
        self.assertEqual(primary["metric"], "accuracy")
        self.assertEqual(primary["contrast_id"], "rule_effect_without_history")
        self.assertEqual((primary["left"], primary["right"]), (HA_RA, HA_RP))
        self.assertEqual(primary["estimate_complete_worlds"], 1)
        self.assertEqual(primary["full_plan_bounds"], [1, 1])
        world_counts = Counter(c["world_id"] for c in self.plan["cases"] if c["cohort"] == "contradiction")
        world = max(world_counts, key=world_counts.get)
        self.assertGreater(world_counts[world], 1)
        task = next(t for t in self.plan["tasks"] if t["cohort"] == "contradiction"
                    and t["world_id"] == world and t["arm"] == HP_RP)
        records = self.records()
        records[task["id"]] = answer_record(task, "MISSING")
        result = analysis.contrast(self.plan, records, "contradiction", HP_RP, HA_RP, "false_missing")
        weight = 1 / (9 * world_counts[world] * 3)
        self.assertAlmostEqual(result["estimate_complete_worlds"], weight)
        self.assertNotAlmostEqual(result["estimate_complete_worlds"], 1 / 39)
        interaction = analysis.interaction(self.plan, records, "contradiction", "false_missing")
        self.assertAlmostEqual(interaction["estimate_complete_worlds"], weight)

    def test_interaction_uses_all_four_arms_with_declared_signs(self):
        records = self.records(lambda t: "MISSING" if t["cohort"] == "contradiction"
                               and t["arm"] in (HP_RP, HA_RA) else t["expected"])
        result = analysis.interaction(self.plan, records, "contradiction", "false_missing")
        self.assertEqual(result["complete_worlds"], 9)
        self.assertEqual(result["estimate_complete_worlds"], 2)
        self.assertEqual(result["full_plan_bounds"], [2, 2])
        self.assertEqual(result["arm_rates_complete_worlds"], {HP_RP: 1, HA_RP: 0, HP_RA: 0, HA_RA: 1})
        accuracy = analysis.interaction(self.plan, records, "contradiction", "accuracy")
        self.assertEqual(accuracy["estimate_complete_worlds"], -2)
        summary = analysis.summarize(self.plan, list(records.values()), {"mode": "mock"})
        self.assertTrue(summary["is_simulated"])
        self.assertTrue(summary["analysis_status"].startswith("SIMULATED_"))
        self.assertEqual(summary["planned_calls"], 432)
        self.assertEqual(len(summary["cells"]), 16)
        self.assertEqual(len(summary["comparisons"]), 40)
        self.assertEqual(Counter(c["contrast_type"] for c in summary["comparisons"]),
                         {"pair": 32, "interaction": 8})
        self.assertEqual(len({(c["cohort"], c["metric"], c["contrast_id"])
                             for c in summary["comparisons"]}), 40)

    def test_invalid_or_pending_arm_excludes_whole_world_only_from_affected_comparisons(self):
        world_counts = Counter(c["world_id"] for c in self.plan["cases"] if c["cohort"] == "contradiction")
        world = max(world_counts, key=world_counts.get)
        records = self.records(lambda t: "MISSING" if t["cohort"] == "contradiction"
                               and t["world_id"] == world and t["arm"] == HP_RP else t["expected"])
        task = next(t for t in self.plan["tasks"] if t["cohort"] == "contradiction"
                    and t["world_id"] == world and t["arm"] == HA_RA)
        for invalid in (True, False):
            changed = deepcopy(records)
            if invalid:
                changed[task["id"]] = answer_record(task, "The class is " + task["expected"])
            else:
                del changed[task["id"]]
            result = analysis.interaction(self.plan, changed, "contradiction", "false_missing")
            self.assertEqual(result["complete_worlds"], 8)
            self.assertEqual(result["estimate_complete_worlds"], 0)
            self.assertEqual(result["arm_rates_complete_worlds"], dict.fromkeys(ARMS, 0))
            self.assertAlmostEqual(result["full_plan_bounds"][0], 1 / 9)
            self.assertAlmostEqual(result["full_plan_bounds"][1], 1 / 9 + 1 / (9 * world_counts[world] * 3))
            unaffected = analysis.contrast(self.plan, changed, "contradiction", HP_RP, HA_RP, "false_missing")
            self.assertEqual(unaffected["complete_worlds"], 9)
            self.assertAlmostEqual(unaffected["estimate_complete_worlds"], 1 / 9)
            affected = analysis.contrast(self.plan, changed, "contradiction", HP_RA, HA_RA, "false_missing")
            self.assertEqual(affected["complete_worlds"], 8)
            self.assertEqual(affected["left_rate_complete_worlds"], 0)
            self.assertEqual(affected["right_rate_complete_worlds"], 0)
            summary = analysis.summarize(self.plan, list(changed.values()), {"mode": "live"})
            self.assertEqual(summary["analysis_status"], "exploratory_complete_with_invalid" if invalid else "incomplete")
            self.assertEqual(summary["invalid_answers"], int(invalid))
            self.assertEqual(summary["pending"], int(not invalid))

    def test_empty_bounds_treat_genuine_missingness_as_zero_and_accuracy_as_unknown(self):
        for cohort in ("contradiction", "genuine_missing_control"):
            for metric in ("false_missing", "accuracy"):
                forced_zero = cohort == "genuine_missing_control" and metric == "false_missing"
                pair = analysis.contrast(self.plan, {}, cohort, HP_RP, HA_RP, metric)
                interaction = analysis.interaction(self.plan, {}, cohort, metric)
                self.assertEqual(pair["full_plan_bounds"], [0, 0] if forced_zero else [-1, 1])
                self.assertEqual(interaction["full_plan_bounds"], [0, 0] if forced_zero else [-2, 2])
                self.assertEqual(interaction["complete_worlds"], 0)
                self.assertIsNone(interaction["estimate_complete_worlds"])
        summary = analysis.summarize(self.plan, [], None)
        self.assertEqual(summary["analysis_status"], "not_started")
        self.assertEqual(summary["pending"], 432)


class DownstreamRuleExecution(unittest.TestCase):
    def test_mock_pause_resume_across_quadruplet_preserves_existing_run_and_exports(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()), \
                patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")), \
                patch.object(provider, "complete", side_effect=AssertionError("network forbidden")):
            root = Path(directory)
            old_output = root / "history-existing"
            old_config = history.load_config("configs/downstream_history_gpt4o.json")
            run(history, history_analysis, old_config, old_output, 1, mock=True)
            old_bytes = {p.relative_to(old_output): p.read_bytes() for p in old_output.rglob("*") if p.is_file()}
            output = root / "rule-new"
            config = core.load_config(CONFIG)
            plan = prepare(core, config, output)
            preview = json.loads((output / "preview.json").read_text())
            self.assertEqual(len(preview), 432)
            self.assertEqual([p["request"] for p in preview],
                             [core.request_for(plan, t) for t in plan["tasks"]])
            first = run(core, analysis, config, output, 2, mock=True)
            self.assertEqual(first["returned_answers"], 2)
            self.assertEqual(first["stopped"], "call_limit")
            saved = {p.name: p.read_bytes() for p in (output / "attempts").glob("*.json")}
            final = run(core, analysis, config, output, 430, mock=True, resume=True)
            self.assertEqual(final["stopped"], "complete")
            self.assertEqual(final["calls_this_invocation"], 430)
            self.assertEqual(final["returned_answers"], 432)
            for name, data in saved.items():
                self.assertEqual((output / "attempts" / name).read_bytes(), data)
            self.assertEqual(run(core, analysis, config, output, 1, mock=True, resume=True)["calls_this_invocation"], 0)
            self.assertEqual(old_bytes, {p.relative_to(old_output): p.read_bytes()
                                       for p in old_output.rglob("*") if p.is_file()})
            _, execution, attempts = read_run(core, output)
            self.assertEqual(execution["mode"], "mock")
            self.assertEqual([a["task_id"] for a in attempts], [t["id"] for t in plan["tasks"]])
            summary = json.loads((output / "summary.json").read_text())
            self.assertTrue(summary["is_simulated"])
            self.assertEqual(summary["primary"]["estimate_complete_worlds"], 0)
            for filename in ("summary.md", "responses.csv", "responses.jsonl", "paired-transitions.csv", "world-contrasts.csv"):
                self.assertTrue((output / filename).is_file(), filename)


if __name__ == "__main__":
    unittest.main()
