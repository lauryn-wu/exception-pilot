"""Offline tests of experimental controls, estimands, and irreversible response retention."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_factorial.core import messages_for as old_messages
from exception_explanation.analysis import summarize
from exception_explanation.core import (ARMS, COPY_ARMS, VALUES, load_config, make_plan,
    messages_for, request_for, score_response, task_meta, validate_config)
from exception_explanation.runner import (mock_complete, normalized_response, prepare,
                                         read_run, run)

ROOT = Path(__file__).resolve().parents[1]


def config():
    return load_config(ROOT / "configs/explanation.json")


def response(text, finish="stop"):
    return provider.normalize({"id": "fixture", "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]})


def fixture(plan, choose=None):
    records = []
    for task in plan["tasks"]:
        result = mock_complete(plan, task)
        if choose is not None:
            result = choose(task, result)
        records.append({"attempt": len(records) + 1, "task_id": task["id"],
            "plan_hash": plan["plan_hash"], "mode": "mock", "request": request_for(plan, task),
            "meta": task_meta(plan, task), "response": result, **score_response(task, result)})
    return records


def replace_final(result, answer):
    lines = result["text"].splitlines()
    lines[-1] = "ANSWER: " + answer
    return response("\n".join(lines))


class ExplanationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_balanced_fresh_deterministic_design(self):
        plan = self.plan
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["tasks"]), 384)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 384)
        plates = [x["id"] for w in plan["worlds"] for x in w["items"]]
        self.assertEqual(len(set(plates)), 240)
        self.assertTrue(all(p.startswith("E") for p in plates))
        roles = Counter(tuple(w["roles"].values()) for w in plan["worlds"])
        self.assertEqual(set(roles.values()), {4})
        self.assertEqual(len(roles), 6)
        assignments = Counter((tuple(w["roles"].values()), w["items"][w["target_index"]]["climate"])
                              for w in plan["worlds"])
        self.assertEqual(set(assignments.values()), {2})
        for w in plan["worlds"]:
            self.assertEqual(len([t for t in plan["tasks"] if t["world_id"] == w["id"]]), 16)
            i = w["target_index"]
            peers = [j for j, x in enumerate(w["items"]) if j != i
                     and x["climate"] == w["items"][i]["climate"]]
            for value in VALUES:
                self.assertEqual([w["record_labels"][value][j] for j in peers], [w["roles"]["pattern"]] * 4)
                self.assertEqual(w["record_labels"][value][i], "MISSING" if value == "missing" else w["roles"][value])

    def test_only_target_class_cell_changes(self):
        plan = self.plan
        for world in plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in ARMS:
                base = {"world_id": world["id"], "family": "diagnostic", "arm": arm, "value": "record_1"}
                first = messages_for(plan, base)[0]["content"].splitlines()
                for value in ("record_2", "missing"):
                    if value == "missing" and arm == "priority":
                        continue
                    other = messages_for(plan, {**base, "value": value})[0]["content"].splitlines()
                    changes = [(a, b) for a, b in zip(first, other) if a != b]
                    self.assertEqual(len(first), len(other))
                    self.assertEqual(len(changes), 1)
                    a, b = changes[0]
                    self.assertIn(target_id, a)
                    self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_anchor_matches_frozen_original_absent_prompt(self):
        for task in self.plan["tasks"]:
            if task["family"] != "anchor":
                continue
            world = next(w for w in self.plan["worlds"] if w["id"] == task["world_id"])
            old_task = {"world_id": world["id"], "item_index": world["target_index"],
                "background": "conflict", "question_wording": "original", "uncertainty_clause": "absent",
                "condition": "direct" if task["arm"] == "direct" else "cot_neutral"}
            self.assertEqual(messages_for(self.plan, task), old_messages(self.plan, old_task))
            text = messages_for(self.plan, task)[0]["content"]
            self.assertNotIn("MISSING", text)
            self.assertNotIn("Audit marker", text)

    def test_copy_control_changes_only_field_name_in_instruction(self):
        world = self.plan["worlds"][0]
        for value in VALUES:
            task = {"world_id": world["id"], "family": "diagnostic", "value": value, "arm": "copy_class"}
            a = messages_for(self.plan, task)[0]["content"]
            b = messages_for(self.plan, {**task, "arm": "copy_marker"})[0]["content"]
            self.assertEqual(a.replace("vehicle's Verified class cell", "vehicle's Audit marker cell"), b)

    def test_caps_stateless_messages_and_no_answer_key_leak(self):
        caps = []
        for task in self.plan["tasks"]:
            req = request_for(self.plan, task)
            caps.append(req["max_completion_tokens"])
            self.assertEqual(len(req["messages"]), 1)
            self.assertEqual(req["messages"][0]["role"], "user")
            self.assertEqual(req["model"], "gpt-4o-2024-08-06")
            self.assertEqual(req["temperature"], 0)
            self.assertFalse(req["store"])
            self.assertEqual(req["n"], 1)
            self.assertNotIn("api_key_env", req)
            self.assertNotIn("ex-list", req["messages"][0]["content"])
        self.assertEqual(Counter(caps), {10: 24, 16: 72, 1000: 288})
        self.assertEqual(sum(caps), 289392)

    def test_invalid_configs_and_copy_parser(self):
        for key, value in (("n_worlds", 30), ("n_worlds", True), ("max_total_attempts", 401),
                           ("model", "gpt-4o"), ("temperature", 1), ("timeout_seconds", float("nan")),
                           ("api_key_env", "secret value"), ("extra", "not allowed")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})
        task = {"family": "diagnostic", "arm": "copy_class"}
        good = score_response(task, response("COPIED: B\nExplanation\nANSWER: C"))
        self.assertEqual((good["copied"], good["answer"], good["copy_valid"], good["status"]), ("B", "C", True, "complete"))
        # A valid final answer is retained even with a malformed or wrong-vocabulary copy.
        for text in ("COPIED: X\nANSWER: A", "Reasoning first\nCOPIED: B\nANSWER: A"):
            result = score_response(task, response(text))
            self.assertFalse(result["copy_valid"])
            self.assertEqual(result["answer"], "A")
        for text in ("The answer is A.", "ANSWER: A\nActually B", "ANSWER: a", "**ANSWER: A**"):
            self.assertIsNone(score_response(task, response(text))["answer"])
        self.assertIsNone(score_response(task, response("COPIED: B\nANSWER: B", "length"))["answer"])


class ExplanationAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_all_correct_is_not_a_positive_result_and_missing_has_no_gold(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertTrue(report["is_simulated"])
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        for name in ("record_sensitivity/direct_minus_cot", "record_sensitivity/copy_class_minus_copy_marker"):
            self.assertEqual(report["effects"][name]["mean"], 0)
            self.assertEqual(report["effects"][name]["n_worlds"], 24)
        missing = [r for r in rows if r["value"] == "missing"]
        self.assertEqual(len(missing), 96)
        self.assertTrue(all(r["correct"] is None and r["expected"] is None for r in missing))
        for row in report["answer_tables"]:
            if row["value"] == "missing":
                self.assertIsNone(row["accuracy_valid_only"])
                self.assertEqual(row["pattern_choice_valid_only"], 1)

    def test_selective_rescue_and_correct_copy_wrong_final_are_distinct(self):
        for rescue_class in (True, False):
            def choose(task, result):
                arms = ("cot", "copy_marker") if rescue_class else ("cot", "copy_marker", "copy_class")
                if task["family"] == "diagnostic" and task["value"] != "missing" and task["arm"] in arms:
                    return replace_final(result, task_meta(self.plan, task)["pattern_label"])
                return result
            report, _ = summarize(self.plan, fixture(self.plan, choose))
            self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cot"]["mean"], 1)
            self.assertEqual(report["effects"]["record_sensitivity/copy_class_minus_copy_marker"]["mean"], int(rescue_class))
            self.assertEqual(report["effects"]["visible_accuracy/priority_minus_cot"]["mean"], 1)
            copy_row = next(r for r in report["copy_tables"] if r["arm"] == "copy_class" and r["value_group"] == "visible")
            self.assertEqual(copy_row["joint_visible_counts"]["copy_1/answer_0"], 0 if rescue_class else 48)

    def test_constant_answer_differs_from_tracking_or_reversing_record(self):
        worlds = {w["id"]: w for w in self.plan["worlds"]}
        for behavior, expected_s in (("constant", 0), ("reverse", -1)):
            def choose(task, result):
                if task["family"] == "diagnostic" and task["value"] != "missing" and task["arm"] == "cot":
                    roles = worlds[task["world_id"]]["roles"]
                    value = "record_1" if behavior == "constant" or task["value"] == "record_2" else "record_2"
                    return replace_final(result, roles[value])
                return result
            report, _ = summarize(self.plan, fixture(self.plan, choose))
            self.assertEqual(report["effects"]["record_sensitivity/cot"]["mean"], expected_s)
            self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cot"]["mean"], 1 - expected_s)

    def test_invalid_final_exclusion_and_full_plan_bounds(self):
        target = "ex-list-000/record_1/cot"
        records = fixture(self.plan, lambda t, r: response("unparseable") if t["id"] == target else r)
        report, _ = summarize(self.plan, records)
        primary = report["effects"]["record_sensitivity/direct_minus_cot"]
        self.assertEqual(primary["n_worlds"], 23)
        self.assertEqual(primary["mean"], 0)
        self.assertEqual(primary["full_plan_unscorable_bounds"], [0, 1 / 24])
        self.assertEqual(report["effects"]["record_sensitivity/copy_class_minus_copy_marker"]["n_worlds"], 24)
        self.assertEqual(report["analysis_status"], "complete_with_unscorable_answers")

    def test_copy_format_errors_do_not_select_final_answer_sample(self):
        def choose(task, result):
            if task["arm"] in COPY_ARMS:
                return response("Malformed first line\n" + result["text"].splitlines()[-1])
            return result
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        self.assertEqual(report["valid_answers"], 384)
        self.assertEqual(report["copy_format_issues"], 144)
        self.assertEqual(report["effects"]["record_sensitivity/copy_class_minus_copy_marker"]["n_worlds"], 24)


class ExplanationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return run(config(), self.output, calls, mock=True, **kwargs)

    def test_mock_never_reads_key_or_network_and_resume_preserves_prior_bytes(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("key access forbidden")):
            first = self.invoke(16)
            self.assertEqual(first["calls_this_invocation"], 16)
            before = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
            result = self.invoke(384, resume=True)
        self.assertEqual(result["calls_this_invocation"], 368)
        self.assertEqual(result["stopped"], "complete")
        self.assertEqual(result["valid_answers"], 384)
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(self.invoke(1, resume=True)["calls_this_invocation"], 0)

    def test_unparseable_returns_continue_and_never_resample(self):
        result = self.invoke(2, complete_fn=lambda c, p: response("No valid final answer"))
        self.assertEqual(result["invalid_answers_retained"], 2)
        first_two = [(self.output / "attempts" / f"{i:06d}.json").read_bytes() for i in (1, 2)]
        after = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual(after["attempts_total"], 3)
        for i, content in enumerate(first_two, 1):
            self.assertEqual((self.output / "attempts" / f"{i:06d}.json").read_bytes(), content)

    def test_transport_error_requires_flag_and_counts_against_budget(self):
        def failure(c, p):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke(8, complete_fn=failure)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        blocked = self.invoke(8, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        success = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((success["attempts_total"], success["valid_answers"]), (2, 1))

    def test_incomplete_return_is_retained_and_blocks_resampling(self):
        result = self.invoke(8, complete_fn=lambda c, p: response("ANSWER: A", "length"))
        self.assertEqual(result["stopped"], "invalid_provider_response")
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual(len(list((self.output / "attempts").glob("*.json"))), 1)

    def test_interruption_is_journaled_before_call(self):
        def interrupt(c, p):
            raise KeyboardInterrupt
        result = self.invoke(8, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        self.assertEqual(json.loads((self.output / "attempts/000001.json").read_text())["status"], "started")
        self.assertEqual(self.invoke(1, resume=True)["stopped"], "retry_requires_flag")
        self.assertEqual(self.invoke(1, resume=True, retry_errors=True)["valid_answers"], 1)

    def test_hard_cumulative_cap_survives_new_invocation(self):
        self.invoke(1, complete_fn=lambda c, p: (_ for _ in ()).throw(provider.ProviderError("TimeoutError")))
        first = json.loads((self.output / "attempts/000001.json").read_text())
        for n in range(2, 400):
            write_json(self.output / "attempts" / f"{n:06d}.json", {**first, "attempt": n})
        result = self.invoke(100, resume=True, retry_errors=True)
        self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                         ("total_attempt_limit", 1, 400))
        self.assertEqual(self.invoke(100, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_identity_plan_source_and_raw_response_guards(self):
        self.invoke(1)
        with self.assertRaisesRegex(ValueError, "resume"):
            self.invoke(1)
        with self.assertRaisesRegex(ValueError, "identity"):
            run(config(), self.output, 1, resume=True, mock=False)
        with patch("exception_explanation.core.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                self.invoke(1, resume=True)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["response"]["text"] = "ANSWER: A"
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "raw provider"):
            read_run(self.output)
        write_json(path, original)
        changed = copy.deepcopy(original)
        changed["request"]["temperature"] = 1
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            read_run(self.output)

    def test_rehashed_plan_mutation_and_duplicate_returns_rejected(self):
        self.invoke(1)
        original_plan = json.loads((self.output / "plan.json").read_text())
        changed = copy.deepcopy(original_plan)
        changed["worlds"][0]["roles"]["pattern"] = "Z"
        changed["plan_hash"] = digest({k: v for k, v in changed.items() if k != "plan_hash"})
        write_json(self.output / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "Code or saved plan"):
            read_run(self.output)
        write_json(self.output / "plan.json", original_plan)
        first = json.loads((self.output / "attempts/000001.json").read_text())
        write_json(self.output / "attempts/000002.json", {**first, "attempt": 2})
        with self.assertRaisesRegex(ValueError, "retried after a returned"):
            read_run(self.output)

    def test_model_mismatch_refusal_and_injected_live_calls_rejected(self):
        raw = response("ANSWER: A")["raw_response"]
        self.assertFalse(normalized_response(raw, config(), "live")["complete"])
        raw["model"] = config()["model"]
        raw["choices"][0]["message"]["refusal"] = "declined"
        self.assertFalse(normalized_response(raw, config(), "live")["complete"])
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(), self.output, 1, complete_fn=lambda c, p: response("ANSWER: A"))

    def test_prepare_is_offline_and_rejects_old_study_directories(self):
        with run_lock(self.output), patch.object(provider, "complete", side_effect=AssertionError("no network")):
            plan = prepare(config(), self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 16)
        self.assertEqual(len(plan["tasks"]), 384)
        self.assertFalse((self.output / "execution.json").exists())
        old = Path(self.temp.name) / "old"
        with run_lock(old):
            (old / "summary.md").write_text("old results")
            with self.assertRaisesRegex(ValueError, "not empty"):
                prepare(config(), old)


if __name__ == "__main__":
    unittest.main()
