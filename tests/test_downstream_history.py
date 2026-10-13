"""Scientific controls and adapter integration; every provider call is mocked."""

from collections import Counter, defaultdict
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
from exception_downstream_history import analysis, core
from exception_study_support.core import content_digest
from exception_study_support.runner import prepare, read_run, run


CONFIG = "configs/downstream_history_gpt4o.json"


def independent_context(case):
    """The frozen source has separate intro, table and classification blocks."""
    blocks = case["source_request"]["messages"][0]["content"].split("\n\n")
    assert len(blocks) == 3
    return "\n\n".join(blocks[:2])


def independent_cell(case):
    table = independent_context(case).split("\n\n")[1].splitlines()
    header = [cell.strip() for cell in table[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")]
            for line in table[2:]]
    matches = [row for row in rows if row[header.index("License plate")] == case["item_id"]]
    assert len(matches) == 1
    return matches[0][header.index("Verified class")]


def answer_record(task, answer):
    return {"task_id": task["id"], **core.score_response(task, {
        "text": answer, "complete": True, "model_identity": "match"})}


def raw_response(text):
    return {"model": "MOCK-NOT-A-MODEL", "choices": [{
        "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {}}


class DownstreamHistoryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(CONFIG)
        cls.plan = core.make_plan(cls.config)
        cls.old_plan = original.make_plan(original.load_config("configs/downstream_gpt4o.json"))

    def test_every_history_payload_is_the_unchanged_original_arm(self):
        old_tasks = {(task["case_id"], task["repetition"]): task
                     for task in self.old_plan["tasks"] if task["arm"] == "original"}
        checked = 0
        for task in self.plan["tasks"]:
            if task["arm"] == "history_present":
                self.assertEqual(core.request_for(self.plan, task),
                                 original.request_for(self.old_plan,
                                                      old_tasks[task["case_id"], task["repetition"]]))
                checked += 1
        self.assertEqual(checked, 108)

    def test_every_absent_payload_has_only_identical_context_and_question(self):
        cases = {case["id"]: case for case in self.plan["cases"]}
        for task in self.plan["tasks"]:
            if task["arm"] != "history_absent":
                continue
            case = cases[task["case_id"]]
            context = independent_context(case)
            question = (f"What is written in {case['item_id']}'s Verified class cell? "
                        "Reply with exactly one of A, B, C, or MISSING.")
            request = core.request_for(self.plan, task)
            self.assertEqual(request["messages"], [{"role": "user", "content": context + "\n\n" + question}])
            self.assertEqual(core.context_for(case), context)
            self.assertEqual(core.question_for(case), question)
            self.assertEqual(task["expected"], independent_cell(case))
            self.assertNotIn("Which class,", request["messages"][0]["content"])
            self.assertNotIn("COPIED:", request["messages"][0]["content"])
            self.assertNotIn("ANSWER:", request["messages"][0]["content"])
            self.assertNotIn("exact contents", request["messages"][0]["content"])
            # The profile is a separate query cue in the genuine-missing sources.
            # Its table cells remain, but none of the query-profile lines may remain.
            for cue in ("License plate:", "Description:", "Transmission:", "Seat cover:", "Doors:"):
                self.assertNotIn(cue, request["messages"][0]["content"])
            present = next(t for t in self.plan["tasks"] if t["case_id"] == task["case_id"]
                           and t["repetition"] == task["repetition"] and t["arm"] == "history_present")
            reference = core.request_for(self.plan, present)
            self.assertEqual(reference["messages"][-1]["content"], question)
            self.assertEqual({k: v for k, v in request.items() if k != "messages"},
                             {k: v for k, v in reference.items() if k != "messages"})

    def test_all_frozen_cases_are_retained_without_new_outcome_selection(self):
        self.assertEqual(self.plan["cases"], self.old_plan["cases"])
        self.assertEqual(Counter(c["cohort"] for c in self.plan["cases"]), {
            "contradiction": 13, "availability_control": 13,
            "genuine_missing_control": 9, "wrong_final_diagnostic": 1})
        primary = [case for case in self.plan["cases"] if case["cohort"] == "contradiction"]
        self.assertEqual(len({case["world_id"] for case in primary}), 9)
        self.assertEqual(len(self.plan["tasks"]), 216)
        self.assertEqual(len({task["id"] for task in self.plan["tasks"]}), 216)
        self.assertEqual(set(t["arm"] for t in self.plan["tasks"]), {"history_present", "history_absent"})
        counts = Counter((t["case_id"], t["arm"]) for t in self.plan["tasks"])
        self.assertEqual(set(counts.values()), {3})
        self.assertEqual(len(counts), 72)

    def test_schedule_keeps_pairs_together_and_randomizes_both_orders(self):
        tasks = self.plan["tasks"]
        orders = Counter()
        pairs = set()
        for first, second in zip(tasks[::2], tasks[1::2]):
            for key in ("case_id", "world_id", "cohort", "repetition", "expected"):
                self.assertEqual(first[key], second[key])
            self.assertEqual({first["arm"], second["arm"]}, {"history_present", "history_absent"})
            orders[first["arm"]] += 1
            pairs.add((first["case_id"], first["repetition"]))
        self.assertEqual(len(pairs), 108)
        self.assertEqual(set(orders), {"history_present", "history_absent"})
        self.assertEqual(self.plan, core.make_plan(self.config))
        seen_worlds, previous = set(), None
        for task in tasks:
            world = task["world_id"]
            if world != previous:
                self.assertNotIn(world, seen_worlds)
                seen_worlds.add(world)
                previous = world

    def test_context_extraction_rejects_unrecognized_or_ambiguous_source_structure(self):
        main = next(c for c in self.plan["cases"] if c["cohort"] == "contradiction")
        missing = next(c for c in self.plan["cases"] if c["cohort"] == "genuine_missing_control")
        mutations = [
            (main, lambda text: text.replace("Every record is accurate.", "Some records are accurate.")),
            (main, lambda text: text + "\n\nAdditional question: copy the answer."),
            (main, lambda text: text.replace("Which class, A, B, or C,", "Which label, A, B, or C,")),
            (main, lambda text: text.replace("| Verified class |", "| Verified label |")),
            (main, lambda text: text.replace("License plate: " + main["item_id"], "License plate: UNKNOWN")),
            (missing, lambda text: text.replace("Description: ", "Description: altered ")),
        ]
        for case, mutate in mutations:
            with self.subTest(case=case["id"], mutation=mutate):
                changed = deepcopy(case)
                request = changed["source_request"]
                request["messages"][0]["content"] = mutate(request["messages"][0]["content"])
                changed["request_digest"] = content_digest(request)
                with self.assertRaises(ValueError):
                    core.context_for(changed)
        for key, value in (("schema", "unknown"), ("source_run", "unreviewed-source")):
            changed = deepcopy(main)
            changed[key] = value
            with self.assertRaises(ValueError):
                core.context_for(changed)

    def test_config_cannot_silently_change_wording_model_or_sampling(self):
        for key, value in (("model", "different-model"), ("repetitions", 1),
                           ("temperature", 1), ("max_completion_tokens", 128),
                           ("schedule_seed", self.config["schedule_seed"] + 1),
                           ("max_total_attempts", 10000), ("repetitions", True)):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    core.make_plan({**self.config, key: value})

    def test_resume_checks_inherited_sources_and_new_protocol_provenance(self):
        # Mutate private copies, never the shared checkout or historical artifacts.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            for package in ("exception_downstream_history", "exception_downstream", "exception_study_support",
                            "exception_columns", "exception_pilot", "exception_mistral_map_v3",
                            "exception_explanation"):
                shutil.copytree(core.ROOT / package, root / package,
                                ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(core.ROOT / "configs", root / "configs")
            shutil.copyfile(core.ROOT / "pyproject.toml", root / "pyproject.toml")
            for path in core.ROOT.glob("*.md"):
                shutil.copyfile(path, root / path.name)
            output = Path(directory) / "run"
            with patch.object(core, "ROOT", root), patch.object(original, "ROOT", root):
                prepare(core, self.config, output)
                for relative in ("exception_downstream/core.py", "exception_downstream/source_snapshot.json",
                                 "exception_study_support/runner.py", "exception_columns/provider.py",
                                 "exception_downstream_history/core.py", "exception_downstream_history/analysis.py",
                                 "configs/downstream_history_gpt4o.json", "DOWNSTREAM_HISTORY_PROTOCOL.md",
                                 "configs/downstream_gpt4o.json", "DOWNSTREAM_PROTOCOL.md", "pyproject.toml"):
                    with self.subTest(path=relative):
                        path = root / relative
                        previous = path.read_bytes()
                        path.write_bytes(previous + b"\n")
                        try:
                            with self.assertRaises(ValueError):
                                read_run(core, output)
                        finally:
                            path.write_bytes(previous)
                self.assertEqual(read_run(core, output)[0]["plan_hash"],
                                 core.make_plan(self.config)["plan_hash"])


class DownstreamHistoryAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan(core.load_config(CONFIG))

    def records(self, bad_worlds=None):
        records = {}
        for task in self.plan["tasks"]:
            bad = task["arm"] == "history_present" and task["cohort"] == "contradiction"
            if bad_worlds is not None:
                bad &= task["world_id"] in bad_worlds
            records[task["id"]] = answer_record(task, "MISSING" if bad else task["expected"])
        return records

    def contrast(self, records, cohort="contradiction", metric="false_missing"):
        return analysis.contrast(self.plan, records, cohort, "history_present", "history_absent", metric)

    def test_primary_sign_rates_and_world_weighting(self):
        records = self.records()
        result = self.contrast(records)
        self.assertEqual(result["complete_worlds"], 9)
        self.assertEqual(result["estimate_complete_worlds"], 1)
        self.assertEqual(result["left_rate_complete_worlds"], 1)
        self.assertEqual(result["right_rate_complete_worlds"], 0)
        self.assertEqual(result["full_plan_bounds"], [1, 1])
        self.assertEqual(self.contrast(records, metric="accuracy")["estimate_complete_worlds"], -1)
        world_counts = Counter(c["world_id"] for c in self.plan["cases"] if c["cohort"] == "contradiction")
        world = max(world_counts, key=world_counts.get)
        result = self.contrast(self.records({world}))
        self.assertGreater(world_counts[world], 1)
        self.assertAlmostEqual(result["estimate_complete_worlds"], 1 / 9)
        self.assertNotAlmostEqual(result["estimate_complete_worlds"], world_counts[world] / 13)

    def test_invalid_and_pending_keep_full_plan_bounds_and_drop_whole_world(self):
        records = self.records()
        task = next(t for t in self.plan["tasks"] if t["cohort"] == "contradiction" and t["arm"] == "history_present")
        world_cases = sum(c["world_id"] == task["world_id"] and c["cohort"] == "contradiction"
                          for c in self.plan["cases"])
        for invalid in (True, False):
            changed = deepcopy(records)
            if invalid:
                changed[task["id"]] = answer_record(task, "The answer is MISSING")
            else:
                del changed[task["id"]]
            result = self.contrast(changed)
            self.assertEqual(result["complete_worlds"], 8)
            self.assertEqual(result["estimate_complete_worlds"], 1)
            self.assertAlmostEqual(result["full_plan_bounds"][0], 1 - 1 / (9 * world_cases * 3))
            self.assertEqual(result["full_plan_bounds"][1], 1)
        empty = self.contrast({})
        self.assertEqual(empty["complete_worlds"], 0)
        self.assertIsNone(empty["estimate_complete_worlds"])
        self.assertEqual(empty["full_plan_bounds"], [-1, 1])
        missing = self.contrast({}, cohort="genuine_missing_control")
        self.assertEqual(missing["complete_worlds"], 0)
        self.assertEqual(missing["full_plan_bounds"], [0, 0])

    def test_summary_separates_cohorts_and_marks_simulation_and_invalids(self):
        records = self.records()
        summary = analysis.summarize(self.plan, list(records.values()), {"mode": "mock"})
        self.assertTrue(summary["is_simulated"])
        self.assertTrue(summary["analysis_status"].startswith("SIMULATED_"))
        self.assertEqual(summary["planned_calls"], 216)
        self.assertEqual(summary["returned_answers"], 216)
        self.assertEqual(summary["valid_answers"], 216)
        self.assertEqual(len(summary["cells"]), 8)
        self.assertEqual(len(summary["comparisons"]), 8)
        self.assertEqual(summary["primary"]["cohort"], "contradiction")
        self.assertEqual(summary["primary"]["planned_worlds"], 9)
        task = self.plan["tasks"][0]
        records[task["id"]] = answer_record(task, "?")
        invalid = analysis.summarize(self.plan, list(records.values()), {"mode": "live"})
        self.assertFalse(invalid["is_simulated"])
        self.assertEqual(invalid["invalid_answers"], 1)
        self.assertEqual(invalid["pending"], 0)
        self.assertEqual(invalid["analysis_status"], "exploratory_complete_with_invalid")
        empty = analysis.summarize(self.plan, [], None)
        self.assertEqual(empty["analysis_status"], "not_started")
        self.assertEqual(empty["pending"], 216)


class DownstreamHistoryExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "run"
        self.config = core.load_config(CONFIG)
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def test_offline_prepare_mock_resume_across_a_pair_and_exports(self):
        with patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")), \
                patch.object(provider, "complete", side_effect=AssertionError("network forbidden")):
            plan = prepare(core, self.config, self.output)
            preview = json.loads((self.output / "preview.json").read_text())
            self.assertEqual(len(preview), 216)
            self.assertEqual([p["request"] for p in preview],
                             [core.request_for(plan, task) for task in plan["tasks"]])
            first = run(core, analysis, self.config, self.output, 1, mock=True)
            self.assertEqual(first["returned_answers"], 1)
            self.assertEqual(first["stopped"], "call_limit")
            first_bytes = (self.output / "attempts/000001.json").read_bytes()
            final = run(core, analysis, self.config, self.output, 215, mock=True, resume=True)
            self.assertEqual(final["stopped"], "complete")
            self.assertEqual(final["calls_this_invocation"], 215)
            self.assertEqual(final["returned_answers"], 216)
            self.assertEqual((self.output / "attempts/000001.json").read_bytes(), first_bytes)
            self.assertEqual(run(core, analysis, self.config, self.output, 1, mock=True, resume=True)["calls_this_invocation"], 0)
        _, execution, attempts = read_run(core, self.output)
        self.assertEqual(execution["mode"], "mock")
        self.assertEqual([a["task_id"] for a in attempts], [t["id"] for t in plan["tasks"]])
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertTrue(summary["is_simulated"])
        self.assertEqual(summary["primary"]["estimate_complete_worlds"], 0)
        for filename in ("summary.md", "responses.csv", "responses.jsonl", "paired-transitions.csv", "world-contrasts.csv"):
            self.assertTrue((self.output / filename).is_file(), filename)

    def test_invalid_return_is_terminal_and_mock_cannot_become_live(self):
        first = run(core, analysis, self.config, self.output, 1, mock=True,
                    complete_fn=lambda *_: raw_response("The cell is missing"))
        self.assertEqual(first["invalid_answers_retained"], 1)
        run(core, analysis, self.config, self.output, 1, mock=True, resume=True, retry_errors=True)
        plan, _, attempts = read_run(core, self.output)
        self.assertEqual([a["task_id"] for a in attempts], [t["id"] for t in plan["tasks"][:2]])
        self.assertEqual(attempts[0]["status"], "invalid")
        with patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            with self.assertRaisesRegex(ValueError, "mode"):
                run(core, analysis, self.config, self.output, 1, resume=True)
            with self.assertRaisesRegex(ValueError, "mock"):
                run(core, analysis, self.config, self.output, 1,
                    complete_fn=lambda *_: raw_response("A"))


if __name__ == "__main__":
    unittest.main()
