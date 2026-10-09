"""Offline tests of the manipulation, collection safeguards, and estimand.

Synthetic completions exercise software only; no result here is model evidence.
"""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import itertools
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from exception_mistral_framing import analysis, core, runner


ROOT = Path(__file__).resolve().parents[1]


def raw(text, identifier="fixture", model="MOCK-NOT-A-MODEL", finish="stop"):
    return runner.provider.normalize({
        "id": identifier, "model": model, "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text},
                     "finish_reason": finish}],
    })


class FramingDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(ROOT / "configs/mistral_framing.json")
        cls.plan = core.make_plan(cls.config)

    def test_fixed_fresh_balanced_worlds_and_randomized_complete_blocks(self):
        plan = self.plan
        self.assertEqual(plan, core.make_plan(self.config))
        self.assertEqual(len(plan["tasks"]), 673)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 673)
        self.assertEqual(Counter(t["family"] for t in plan["tasks"]),
                         {"capability": 1, "base": 96, "intervention": 576})
        assignments = Counter()
        item_ids = []
        for world in plan["worlds"]:
            target = world["target_index"]
            roles = world["roles"]
            self.assertEqual(set(roles.values()), {"A", "B", "C"})
            assignments[(tuple(roles[k] for k in ("record_1", "record_2", "pattern")),
                         world["items"][target]["climate"])] += 1
            first, second = (world["record_labels"][v] for v in core.VALUES)
            self.assertEqual([i for i, pair in enumerate(zip(first, second)) if pair[0] != pair[1]], [target])
            self.assertEqual((first[target], second[target]), (roles["record_1"], roles["record_2"]))
            self.assertNotIn(roles["pattern"], (first[target], second[target]))
            self.assertNotIn("MISSING", first + second)
            item_ids.extend(item["id"] for item in world["items"])
        expected = {(roles, climate): 2 for roles in itertools.permutations("ABC")
                    for climate in ("cold", "warm")}
        self.assertEqual(assignments, expected)
        self.assertEqual(len(item_ids), len(set(item_ids)))
        self.assertTrue(all(identifier.startswith("F") for identifier in item_ids))
        orders = set()
        for offset in range(97, 673, 4):
            block = plan["tasks"][offset:offset + 4]
            self.assertEqual(len({(t["world_id"], t["value"], t["repeat"]) for t in block}), 1)
            self.assertEqual({t["arm"] for t in block}, set(core.ARMS))
            orders.add(tuple(t["arm"] for t in block))
        self.assertGreater(len(orders), 1)
        self.assertEqual(Counter(t["arm"] for t in plan["tasks"][97:]),
                         {arm: 144 for arm in core.ARMS})

    def test_only_the_specified_parenthetical_changes_within_each_case(self):
        for world in self.plan["worlds"]:
            for value in core.VALUES:
                tasks = [t for t in self.plan["tasks"] if t.get("world_id") == world["id"]
                         and t.get("value") == value and t["family"] == "intervention"]
                requests = {t["arm"]: core.request_for(self.plan, t) for t in tasks}
                bare = requests["bare"]
                expected = world["roles"][value]
                visible = next(t for t in self.plan["tasks"] if t.get("world_id") == world["id"]
                               and t.get("value") == value and t["arm"] == "visible")
                self.assertEqual(bare["messages"][0], core.request_for(self.plan, visible)["messages"][0])
                for arm, request in requests.items():
                    self.assertEqual(request["messages"][0], bare["messages"][0])
                    self.assertEqual(len(request["messages"]), 2)
                    prefix = request["messages"][1]
                    self.assertEqual((prefix["role"], prefix["prefix"]), ("assistant", True))
                    text = prefix["content"]
                    parenthetical = core.PARENTHETICALS[arm]
                    if parenthetical:
                        self.assertEqual(text.count(parenthetical), 1)
                        text = text.replace(" " + parenthetical, "")
                    self.assertEqual(text, bare["messages"][1]["content"])
                    self.assertTrue(text.endswith(f"- Verified class: {expected}\n\n"))
                    self.assertNotIn("ANSWER:", text)
                    self.assertEqual({k: v for k, v in request.items() if k != "messages"},
                                     {k: v for k, v in bare.items() if k != "messages"})
                for task in tasks:
                    self.assertEqual(core.request_for(self.plan, task), requests[task["arm"]])
        capability = core.request_for(self.plan, self.plan["tasks"][0])
        self.assertEqual(capability["messages"][-1]["content"], "Cobalt ")

    def test_scorer_keeps_immediate_answers_and_rejects_changed_prefixes(self):
        task = self.plan["tasks"][97]
        meta = core.task_meta(self.plan, task)
        prefix = meta["prefix_text"]
        result = core.score_response(task, raw(prefix + "ANSWER: " + meta["expected"]), meta)
        self.assertEqual((result["status"], result["answer"], result["prefix_exact"]),
                         ("complete", meta["expected"], True))
        self.assertEqual(result["generated_suffix"], "ANSWER: " + meta["expected"])
        self.assertFalse(result["suffix_pre_answer_text"])
        self.assertEqual(core.score_response(task, raw(prefix + "A or B"), meta)["status"], "invalid")
        bad = core.score_response(task, raw(prefix.replace("Verified class", "Predicted class") + "ANSWER: A"), meta)
        self.assertEqual(bad["invalid_reason"], "prefix_mismatch")
        self.assertIsNone(bad["answer"])
        self.assertEqual(core.score_response(task, raw(prefix + "ANSWER: A", finish="length"), meta)["status"], "invalid")
        visible = next(t for t in self.plan["tasks"] if t["arm"] == "visible")
        direct = next(t for t in self.plan["tasks"] if t["arm"] == "direct")
        self.assertEqual(core.score_response(visible, raw("ANSWER: A"), core.task_meta(self.plan, visible))["invalid_reason"],
                         "reasoning_text_missing")
        self.assertEqual(core.score_response(direct, raw("Explanation.\nANSWER: A"), core.task_meta(self.plan, direct))["invalid_reason"],
                         "direct_not_answer_only")

    def test_changed_design_or_attempt_budget_is_not_silently_resumed(self):
        for field, value in (("n_worlds", 12), ("repeats", 6), ("seed", 7),
                             ("max_total_attempts", 9999), ("temperature", 0.0)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.config)
                changed[field] = value
                with self.assertRaises(ValueError):
                    core.make_plan(changed)


class FramingCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(ROOT / "configs/mistral_framing.json")
        cls.temp = tempfile.TemporaryDirectory()
        cls.baseline = Path(cls.temp.name) / "baseline"
        with redirect_stdout(io.StringIO()), \
             patch.object(runner.provider, "complete", side_effect=AssertionError("network")), \
             patch.object(runner.provider, "credential", side_effect=AssertionError("credential")):
            cls.plan = runner.prepare(cls.config, cls.baseline)
            cls.baseline_result = runner.run(cls.config, cls.baseline, 705, mock=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def baseline_copy(self, root):
        output = Path(root) / "run"
        shutil.copytree(self.baseline, output)
        return output

    def test_one_full_mock_run_has_explicit_stage_pause_and_no_accuracy_gate(self):
        self.assertEqual((self.baseline_result["stopped"], self.baseline_result["calls_this_invocation"]),
                         ("baseline_complete", 97))
        self.assertEqual(self.baseline_result["valid_answers"], 97)
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()), \
             patch.object(runner.provider, "complete", side_effect=AssertionError("network")), \
             patch.object(runner.provider, "credential", side_effect=AssertionError("credential")):
            output = self.baseline_copy(root)
            repeat = runner.run(self.config, output, 705, resume=True, mock=True)
            self.assertEqual((repeat["stopped"], repeat["calls_this_invocation"]), ("baseline_complete", 0))
            result = runner.run(self.config, output, 705, stage="intervene", resume=True, mock=True)
            self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                             ("complete", 576, 673))
            plan, execution, attempts = runner.read_run(output)
            self.assertEqual(execution["mode"], "mock")
            self.assertEqual(len(attempts), len({a["task_id"] for a in attempts}))
            summary = json.loads((output / "summary.json").read_text())
            self.assertTrue(summary["is_simulated"])
            self.assertFalse(summary["interpretation_allowed"])
            self.assertEqual(summary["primary_contrast"]["n_worlds"], 24)
            self.assertEqual(summary["primary_contrast"]["mean"], 0)
            again = runner.run(self.config, output, 705, stage="intervene", resume=True, mock=True)
            self.assertEqual(again["calls_this_invocation"], 0)
            self.assertEqual(plan, runner.prepare(self.config, output))

    def test_unscorable_baseline_is_retained_without_selection_or_retries(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = Path(root) / "run"
            runner.run(self.config, output, 1, mock=True)
            result = runner.run(self.config, output, 1, resume=True, mock=True,
                                complete_fn=lambda cfg, payload: raw("Uncertain: A or B.", "invalid-baseline"))
            self.assertEqual(result["invalid_answers_retained"], 1)
            original = (output / "attempts/000002.json").read_bytes()
            result = runner.run(self.config, output, 705, resume=True, retry_errors=True, mock=True)
            self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                             ("baseline_complete", 95, 97))
            self.assertEqual((output / "attempts/000002.json").read_bytes(), original)
            result = runner.run(self.config, output, 1, stage="intervene", resume=True, mock=True)
            self.assertEqual(result["calls_this_invocation"], 1)
            self.assertEqual(runner.read_run(output)[2][-1]["task_id"], self.plan["tasks"][97]["id"])

    def test_returned_intervention_invalid_is_never_resampled(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = self.baseline_copy(root)
            def invalid(cfg, payload):
                return raw(payload["messages"][-1]["content"] + "No final answer.", "invalid-intervention")
            result = runner.run(self.config, output, 1, stage="intervene", resume=True, mock=True,
                                complete_fn=invalid)
            self.assertEqual(result["invalid_answers_retained"], 1)
            retained = (output / "attempts/000098.json").read_bytes()
            runner.run(self.config, output, 1, stage="intervene", resume=True, retry_errors=True, mock=True)
            self.assertEqual((output / "attempts/000098.json").read_bytes(), retained)
            _, _, attempts = runner.read_run(output)
            self.assertEqual(attempts[-1]["task_id"], self.plan["tasks"][98]["id"])
            self.assertNotEqual(attempts[-1]["task_id"], attempts[-2]["task_id"])

    def test_transport_retry_requires_flag_and_preserves_failed_attempt(self):
        def fail(cfg, payload):
            raise runner.provider.ProviderError("HTTP 429", status_code=429)
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = Path(root) / "run"
            result = runner.run(self.config, output, 1, mock=True, complete_fn=fail)
            self.assertEqual(result["stopped"], "provider_error")
            original = (output / "attempts/000001.json").read_bytes()
            result = runner.run(self.config, output, 1, resume=True, mock=True)
            self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("retry_requires_flag", 0))
            result = runner.run(self.config, output, 1, resume=True, retry_errors=True, mock=True)
            self.assertEqual((result["attempts_total"], result["valid_answers"]), (2, 1))
            self.assertEqual((output / "attempts/000001.json").read_bytes(), original)
            attempts = runner.read_run(output)[2]
            self.assertEqual(attempts[1]["task_id"], attempts[0]["task_id"])
            self.assertEqual(attempts[1]["retry_of_attempt"], 1)

    def test_prefix_failure_is_terminal_even_with_retry_flag(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = self.baseline_copy(root)
            result = runner.run(self.config, output, 1, stage="intervene", resume=True, mock=True,
                                complete_fn=lambda cfg, payload: raw("Replaced prefix.\nANSWER: A", "bad-prefix"))
            self.assertEqual(result["stopped"], "operational_failure")
            self.assertEqual(runner.read_run(output)[2][-1]["hard_failure"], "prefix_mismatch")
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, stage="intervene", resume=True, retry_errors=True, mock=True)

    def test_invalid_provider_identity_and_incomplete_answers_are_terminal(self):
        for problem in ("duplicate", "incomplete", "model_changed", "invalid_id"):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
                output = self.baseline_copy(root)
                duplicate = runner.read_run(output)[2][0]["response"]["response_id"]
                def bad(cfg, payload):
                    return raw(payload["messages"][-1]["content"] + "ANSWER: A",
                               duplicate if problem == "duplicate" else [] if problem == "invalid_id" else "bad-provider",
                               model="OTHER-MODEL" if problem == "model_changed" else "MOCK-NOT-A-MODEL",
                               finish="length" if problem == "incomplete" else "stop")
                result = runner.run(self.config, output, 1, stage="intervene", resume=True, mock=True, complete_fn=bad)
                self.assertEqual(result["stopped"], "operational_failure")
                expected = {"duplicate": "duplicate_response_id", "incomplete": "incomplete_finish_reason",
                            "model_changed": "response_model_changed", "invalid_id": "missing_response_id"}
                self.assertEqual(runner.read_run(output)[2][-1]["hard_failure"], expected[problem])

    def test_failed_capability_and_wrong_initial_live_model_cannot_proceed(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = Path(root) / "run"
            result = runner.run(self.config, output, 705, mock=True,
                                complete_fn=lambda cfg, payload: raw("Cobalt Mape Lantern", "failed-capability"))
            self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("operational_failure", 1))
            self.assertEqual(runner.read_run(output)[2][0]["hard_failure"], "capability_failed")
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, resume=True, retry_errors=True, mock=True)
        task = self.plan["tasks"][0]
        response = raw("Cobalt Maple Lantern", model="WRONG-LIVE-MODEL")
        score = core.score_response(task, response, core.task_meta(self.plan, task))
        self.assertEqual(runner._hard_failure(self.plan, task, response, score, set(), "live"), "unexpected_model")

    def test_total_attempt_limit_prevents_another_transport_retry(self):
        def fail(cfg, payload):
            raise runner.provider.ProviderError("HTTP 429", status_code=429)
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            output = Path(root) / "run"
            runner.run(self.config, output, 1, mock=True, complete_fn=fail)
            first = json.loads((output / "attempts/000001.json").read_text())
            # Offline construct an exhausted, otherwise valid mock retry chain.
            for number in range(2, self.config["max_total_attempts"] + 1):
                attempt = copy.deepcopy(first)
                attempt.update(attempt=number, retry_errors=True, retry_of_attempt=number - 1)
                (output / "attempts" / f"{number:06d}.json").write_text(json.dumps(attempt))
            with patch.object(runner, "mock_complete", side_effect=AssertionError("over-budget call")):
                result = runner.run(self.config, output, 1, resume=True, retry_errors=True, mock=True)
            self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                             ("total_attempt_limit", 0, 705))

    def test_incomplete_baseline_live_injection_and_mode_or_config_changes_rejected(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(runner.provider, "complete", side_effect=AssertionError("network")), \
             patch.object(runner.provider, "credential", side_effect=AssertionError("credential")):
            output = Path(root) / "fresh"
            runner.prepare(self.config, output)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, stage="intervene", mock=True)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, complete_fn=lambda cfg, payload: raw("anything"))
            output = self.baseline_copy(root)
            with self.assertRaises(ValueError):
                runner.run(self.config, output, 1, resume=True, mock=False)
            changed = copy.deepcopy(self.config)
            changed["api_key_env"] = "OTHER_TEST_KEY_ENV"
            with self.assertRaises(ValueError):
                runner.run(changed, output, 1, resume=True, mock=True)

    def test_saved_request_raw_response_and_preview_tampering_are_detected(self):
        with tempfile.TemporaryDirectory() as root:
            output = self.baseline_copy(root)
            path = output / "attempts/000002.json"
            original = path.read_bytes()
            for mutation in ("request", "response", "score", "retry"):
                data = json.loads(original)
                if mutation == "request":
                    data["request"]["temperature"] = 0.0
                elif mutation == "response":
                    data["response"]["raw_response"]["choices"][0]["message"]["content"] += " changed"
                elif mutation == "score":
                    data["answer"] = "Z"
                else:
                    data["retry_of_attempt"] = 1
                path.write_text(json.dumps(data))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    runner.read_run(output)
                path.write_bytes(original)
            preview = output / "preview.md"
            preview.write_text(preview.read_text() + "Changed preview\n")
            with self.assertRaises(ValueError):
                runner.read_run(output)


class FramingAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(ROOT / "configs/mistral_framing.json")
        cls.plan = core.make_plan(cls.config)

    def synthetic_attempts(self):
        """Analytic fixture: +1 world, -1 world, and 22 zero-difference worlds.

        Two original-arm outcomes in one case of the negative world are
        unscorable. This creates different complete-case/world denominators.
        """
        first, second = (world["id"] for world in self.plan["worlds"][:2])
        attempts = []
        for number, task in enumerate(self.plan["tasks"], 1):
            meta = core.task_meta(self.plan, task)
            answer = meta["expected"]
            invalid = (task.get("world_id") == second and task["arm"] == "original"
                       and task.get("value") == "record_1" and task.get("repeat") in (1, 2))
            wrong = (task.get("world_id") == first and task["arm"] == "original"
                     or task.get("world_id") == second and task["arm"] == "bare")
            if wrong:
                answer = meta["pattern_label"]
            if invalid:
                answer = None
            attempts.append({
                "attempt": number, "task_id": task["id"], "status": "invalid" if invalid else "complete",
                "answer": answer, "format_valid": not invalid, "hard_failure": None,
                "capability_exact": task["family"] == "capability",
            })
        return attempts

    def test_primary_contrast_uses_worlds_and_explicit_full_plan_missingness_bounds(self):
        summary = analysis.summarize(self.plan, self.synthetic_attempts(), "mock")
        contrast = summary["primary_contrast"]
        self.assertEqual(contrast["contrast"], "bare_minus_original")
        self.assertEqual((contrast["n_worlds"], contrast["planned_worlds"]), (23, 24))
        self.assertAlmostEqual(contrast["mean"], 1 / 23)
        self.assertEqual(contrast["n_paired_cases"], 47)
        self.assertAlmostEqual(contrast["case_weighted_mean"], 1 / 47)
        self.assertEqual(contrast["excluded_world_ids"], [self.plan["worlds"][1]["id"]])
        self.assertEqual(len(contrast["unscorable_or_pending_task_ids"]), 2)
        self.assertAlmostEqual(contrast["full_plan_unscorable_bounds"][0], 0)
        self.assertAlmostEqual(contrast["full_plan_unscorable_bounds"][1], 1 / 72)
        self.assertEqual(summary["arm_counts"]["original"]["invalid"], 2)
        self.assertEqual(summary["arm_counts"]["original"]["valid"], 142)
        self.assertEqual(summary["arm_counts"]["bare"]["valid"], 144)
        self.assertEqual(summary["arm_counts"]["original"]["pattern"], 6)
        self.assertEqual(summary["arm_counts"]["original"]["other"], 0)
        self.assertFalse(summary["interpretation_allowed"])
        self.assertFalse(contrast["interpretation_allowed"])
        self.assertTrue(summary["is_simulated"])
        self.assertIsNotNone(contrast["descriptive_cluster_bootstrap_95_ci"])

    def test_pending_responses_do_not_get_confidence_intervals_or_invalid_bounds(self):
        attempts = self.synthetic_attempts()
        remove = next(i for i, task in enumerate(self.plan["tasks"])
                      if task.get("world_id") == self.plan["worlds"][2]["id"] and task["arm"] == "bare")
        attempts.pop(remove)
        summary = analysis.summarize(self.plan, attempts, "mock")
        contrast = summary["primary_contrast"]
        self.assertEqual(contrast["n_worlds"], 22)
        self.assertIsNone(contrast["descriptive_cluster_bootstrap_95_ci"])
        self.assertIsNone(contrast["full_plan_unscorable_bounds"])
        self.assertFalse(contrast["all_returned"])
        self.assertEqual(summary["arm_counts"]["bare"]["pending"], 1)
        self.assertEqual(summary["arm_counts"]["bare"]["invalid"], 0)
        self.assertFalse(summary["interpretation_allowed"])

    def test_one_complete_world_cannot_produce_a_confidence_interval(self):
        attempts = self.synthetic_attempts()
        first = self.plan["worlds"][0]["id"]
        task_lookup = {task["id"]: task for task in self.plan["tasks"]}
        for attempt in attempts:
            task = task_lookup[attempt["task_id"]]
            if task["arm"] == "original" and task.get("world_id") != first:
                attempt.update(status="invalid", answer=None, format_valid=False)
        contrast = analysis.summarize(self.plan, attempts, "mock")["primary_contrast"]
        self.assertEqual(contrast["n_worlds"], 1)
        self.assertEqual(contrast["mean"], 1)
        self.assertTrue(contrast["all_returned"])
        self.assertIsNone(contrast["descriptive_cluster_bootstrap_95_ci"])


if __name__ == "__main__":
    unittest.main()
