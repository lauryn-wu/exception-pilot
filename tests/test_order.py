"""Offline checks of answer-order manipulation, world pairing, and immutable returns."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_cue.core import load_config as old_config, make_plan as old_plan
from exception_explanation.core import INTRO as ORIGINAL_INTRO
from exception_pilot import provider
from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_order.analysis import summarize, write_summary
from exception_order.core import (
    ARMS, VALUES, load_config, make_plan, messages_for, request_for,
    score_response, task_meta, validate_config,
)
from exception_order.runner import mock_complete, normalized_response, prepare, read_run, run

ROOT = Path(__file__).resolve().parents[1]
CONTRASTS = ("answer_first_minus_reasoning_first", "answer_only_minus_answer_first",
             "answer_only_minus_reasoning_first")


def config():
    return load_config(ROOT / "configs/order.json")


def response(text, finish="stop"):
    return provider.normalize({
        "id": "fixture", "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
    })


def answer_response(arm, answer, reasoning="The recorded class is used."):
    fields = ({"answer": answer} if arm == "answer_only" else
              {"reasoning": reasoning, "answer": answer} if arm == "reasoning_first" else
              {"answer": answer, "reasoning": reasoning})
    return response(json.dumps(fields))


def fixture(plan, choose=None):
    records = []
    for task in plan["tasks"]:
        result = mock_complete(plan, task)
        if choose is not None:
            result = choose(task, result)
        records.append({
            "attempt": len(records) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
            "mode": "mock", "request": request_for(plan, task), "meta": task_meta(plan, task),
            "response": result, **score_response(task, result),
        })
    return records


class OrderDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_fixed_fresh_balanced_worlds_and_full_within_world_pairing(self):
        plan = self.plan
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual((len(plan["worlds"]), len(plan["tasks"])), (12, 72))
        self.assertEqual(len({task["id"] for task in plan["tasks"]}), 72)
        plates = {item["id"] for world in plan["worlds"] for item in world["items"]}
        self.assertEqual(len(plates), 120)
        self.assertTrue(all(plate.startswith("R") for plate in plates))
        previous = old_plan(old_config(ROOT / "configs/cue.json"))
        old_plates = {item["id"] for world in previous["worlds"] for item in world["items"]}
        self.assertFalse(plates & old_plates)
        self.assertFalse({w["id"] for w in plan["worlds"]} & {w["id"] for w in previous["worlds"]})
        roles = Counter(tuple(world["roles"].values()) for world in plan["worlds"])
        self.assertEqual((len(roles), set(roles.values())), (6, {2}))
        climate_roles = Counter((tuple(world["roles"].values()),
                                world["items"][world["target_index"]]["climate"])
                               for world in plan["worlds"])
        self.assertEqual((len(climate_roles), set(climate_roles.values())), (12, {1}))
        schedules = []
        for world in plan["worlds"]:
            tasks = [task for task in plan["tasks"] if task["world_id"] == world["id"]]
            self.assertEqual(Counter((t["value"], t["arm"]) for t in tasks),
                             Counter((value, arm) for value in VALUES for arm in ARMS))
            schedules.append(tuple((task["value"], task["arm"]) for task in tasks))
            target = world["target_index"]
            peers = [i for i, item in enumerate(world["items"]) if i != target
                     and item["climate"] == world["items"][target]["climate"]]
            for value in VALUES:
                self.assertEqual(world["record_labels"][value][target], world["roles"][value])
                self.assertEqual([world["record_labels"][value][i] for i in peers],
                                 [world["roles"]["pattern"]] * 4)
        self.assertGreater(len(set(schedules)), 1)

    def test_paired_variants_change_only_target_verified_class(self):
        for world in self.plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in ARMS:
                task = {"world_id": world["id"], "family": "diagnostic", "arm": arm, "value": "record_1"}
                first = messages_for(self.plan, task)[0]["content"].splitlines()
                second = messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
                self.assertEqual(len(first), len(second))
                differences = [(a, b) for a, b in zip(first, second) if a != b]
                self.assertEqual(len(differences), 1)
                a, b = differences[0]
                self.assertIn(target_id, a)
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_explanation_requests_differ_only_in_schema_property_order(self):
        for task in self.plan["tasks"]:
            first = request_for(self.plan, {**task, "arm": "reasoning_first"})
            last = request_for(self.plan, {**task, "arm": "answer_first"})
            # Dict equality alone would miss this experimental manipulation.
            self.assertEqual(first, last)
            self.assertEqual(first["messages"], last["messages"])
            self.assertNotEqual(json.dumps(first), json.dumps(last))
            one_schema = first["response_format"]["json_schema"]["schema"]
            two_schema = last["response_format"]["json_schema"]["schema"]
            self.assertEqual(list(one_schema["properties"]), ["reasoning", "answer"])
            self.assertEqual(list(two_schema["properties"]), ["answer", "reasoning"])
            self.assertEqual(one_schema["required"], ["answer", "reasoning"])
            self.assertEqual(one_schema["required"], two_schema["required"])
            two_schema["properties"] = dict(reversed(list(two_schema["properties"].items())))
            self.assertEqual(json.dumps(first), json.dumps(last))
            for arm in ARMS:
                request = request_for(self.plan, {**task, "arm": arm})
                self.assertEqual(len(request["messages"]), 1)
                self.assertEqual(request["messages"][0]["role"], "user")
                self.assertTrue(request["messages"][0]["content"].startswith(ORIGINAL_INTRO + "\n"))
                self.assertIn("MISSING means the verified class has not been recorded.", request["messages"][0]["content"])
                self.assertEqual((request["model"], request["temperature"], request["n"], request["store"]),
                                 ("gpt-4o-2024-08-06", 0, 1, False))
                self.assertEqual(request["max_completion_tokens"], 1000)
                self.assertTrue(request["response_format"]["json_schema"]["strict"])
                self.assertFalse(request["response_format"]["json_schema"]["schema"]["additionalProperties"])
                self.assertNotIn("expected", request)
                self.assertNotIn("api_key_env", request)
                self.assertNotIn(task["world_id"], request["messages"][0]["content"])
        mutated = request_for(self.plan, self.plan["tasks"][0])
        mutated["response_format"]["json_schema"]["schema"]["properties"]["answer"]["enum"].append("D")
        fresh = request_for(self.plan, self.plan["tasks"][0])
        self.assertEqual(fresh["response_format"]["json_schema"]["schema"]["properties"]["answer"]["enum"], ["A", "B", "C"])

    def test_fixed_config_rejects_scientific_or_budget_changes(self):
        for key, value in (("protocol", "other"), ("seed", 2026100894), ("n_worlds", 24),
                           ("n_worlds", True), ("model", "gpt-4o"), ("temperature", True),
                           ("max_total_attempts", 89), ("timeout_seconds", float("nan")),
                           ("api_key_env", "secret value"), ("extra", "not allowed"),
                           ("max_completion_tokens", {arm: 16 if arm == "answer_only" else 1000 for arm in ARMS}),
                           ("max_completion_tokens", {arm: 1000.0 for arm in ARMS})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})

    def test_parser_preserves_single_answer_and_measures_required_reasoning(self):
        for arm in ARMS:
            for answer in "ABC":
                scored = score_response({"arm": arm}, answer_response(arm, answer, "  Two useful words.  "))
                self.assertEqual((scored["answer"], scored["status"], scored["schema_valid"], scored["key_order_valid"]),
                                 (answer, "complete", True, True))
                self.assertIsNone(scored["invalid_reason"])
                if arm == "answer_only":
                    self.assertIsNone(scored["reasoning_nonempty"])
                    self.assertIsNone(scored["reasoning_chars"])
                    self.assertIsNone(scored["reasoning_words"])
                else:
                    self.assertTrue(scored["reasoning_nonempty"])
                    self.assertEqual(scored["reasoning_chars"], len("Two useful words."))
                    self.assertEqual(scored["reasoning_words"], 3)
        # A contradictory string is data; only the unique answer field is scored.
        scored = score_response({"arm": "answer_first"},
                                answer_response("answer_first", "A", "Actually I would choose C."))
        self.assertEqual((scored["answer"], scored["status"]), ("A", "complete"))

    def test_parser_rejects_wrong_order_empty_reasoning_and_schema_violations(self):
        for arm, other in (("reasoning_first", "answer_first"), ("answer_first", "reasoning_first")):
            wrong_order = score_response({"arm": arm}, answer_response(other, "A"))
            self.assertEqual((wrong_order["answer"], wrong_order["status"], wrong_order["schema_valid"],
                              wrong_order["key_order_valid"]), (None, "invalid", True, False))
            self.assertTrue(wrong_order["invalid_reason"])
            for reasoning in ("", " \n\t "):
                empty = score_response({"arm": arm}, answer_response(arm, "A", reasoning))
                self.assertEqual((empty["answer"], empty["status"], empty["schema_valid"], empty["key_order_valid"],
                                  empty["reasoning_nonempty"], empty["reasoning_chars"], empty["reasoning_words"]),
                                 (None, "invalid", True, True, False, 0, 0))
        common_bad = ('{}', 'null', '[]', '"A"', '{"answer":"a"}', '{"answer":"D"}',
                      '{"answer":null}', '{"answer":true}', '{"answer":NaN}',
                      '{"answer":"A","answer":"B"}', '{"answer":"A","answer":"A"}',
                      '{"answer":"A","extra":"field"}', 'before {"answer":"A"}',
                      '```json\n{"answer":"A"}\n```', '{"answer":"A"} trailing',
                      '{"answer":"A"}{"answer":"B"}', '{"answer":"A",}')
        for arm in ARMS:
            for text in common_bad:
                with self.subTest(arm=arm, text=text):
                    scored = score_response({"arm": arm}, response(text))
                    self.assertEqual((scored["answer"], scored["status"], scored["schema_valid"]), (None, "invalid", False))
                    self.assertIsNone(scored["key_order_valid"])
                    self.assertTrue(scored["invalid_reason"])
        for arm in ("reasoning_first", "answer_first"):
            for text in ('{"answer":"A","reasoning":null}', '{"answer":"A","reasoning":42}',
                         '{"answer":"A","reasoning":"x","reasoning":"y"}'):
                scored = score_response({"arm": arm}, response(text))
                self.assertEqual((scored["status"], scored["schema_valid"]), ("invalid", False))
                self.assertIsNone(scored["reasoning_nonempty"])

    def test_valid_json_does_not_override_provider_failure(self):
        for arm in ARMS:
            raw = answer_response(arm, "A")["raw_response"]
            cases = [normalized_response(raw, config(), "live"), response(json.dumps({"answer": "A"}), "length")]
            refused = copy.deepcopy(raw)
            refused["model"] = config()["model"]
            refused["choices"][0]["message"]["refusal"] = "declined"
            cases.append(normalized_response(refused, config(), "live"))
            for result in cases:
                scored = score_response({"arm": arm}, result)
                self.assertEqual((scored["answer"], scored["status"], scored["schema_valid"]), (None, "invalid", False))
                self.assertEqual(scored["invalid_reason"], "provider_incomplete")


class OrderAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_all_correct_mock_has_zero_effects_and_is_not_evidence(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertTrue(report["is_simulated"])
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual((len(rows), report["valid_answers"], report["invalid_answers"]), (72, 72, 0))
        for measure in ("accuracy", "record_sensitivity"):
            for contrast in CONTRASTS:
                effect = report["effects"][f"{measure}/{contrast}"]
                self.assertEqual((effect["mean"], effect["n_worlds"]), (0, 12))
                self.assertEqual(effect["descriptive_cluster_bootstrap_95_ci"], [0, 0])
            for arm in ARMS:
                self.assertEqual(report["effects"][f"{measure}/{arm}"]["mean"], 1)

    def test_primary_accuracy_and_sensitivity_contrast_signs(self):
        for bad_arm, expected in (("reasoning_first", 1), ("answer_first", -1)):
            def choose(task, result):
                return (answer_response(task["arm"], task_meta(self.plan, task)["pattern_label"])
                        if task["arm"] == bad_arm else result)
            report, rows = summarize(self.plan, fixture(self.plan, choose))
            self.assertEqual(report["analysis_status"], "complete_ready_for_interpretation")
            self.assertTrue(report["interpretation_allowed"])
            self.assertEqual(sum(row["correct"] == 0 for row in rows), 24)
            for measure in ("accuracy", "record_sensitivity"):
                primary = report["effects"][f"{measure}/answer_first_minus_reasoning_first"]
                self.assertEqual(primary["mean"], expected)
                self.assertEqual(primary["paired_improved_cases"], 24 if expected > 0 else 0)
                self.assertEqual(primary["paired_worsened_cases"], 24 if expected < 0 else 0)
                self.assertEqual(primary["positive_worlds"], 12 if expected > 0 else 0)
                self.assertEqual(primary["negative_worlds"], 12 if expected < 0 else 0)
                self.assertEqual(report["effects"][f"{measure}/answer_only_minus_{bad_arm}"]["mean"], 1)
            pairs = next(item for item in report["record_pair_counts"] if item["arm"] == bad_arm)
            self.assertEqual((pairs["n_both_wrong"], pairs["n_pattern_both"], pairs["n_answer_unchanged"]), (12, 12, 12))

    def test_uncertainty_resamples_worlds_with_both_record_variants_together(self):
        bad_world = self.plan["worlds"][0]["id"]
        def choose(task, result):
            return (answer_response(task["arm"], task_meta(self.plan, task)["pattern_label"])
                    if task["world_id"] == bad_world and task["arm"] == "reasoning_first" else result)
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        primary = report["effects"]["accuracy/answer_first_minus_reasoning_first"]
        self.assertEqual(primary["mean"], 1 / 12)
        self.assertEqual(primary["descriptive_cluster_bootstrap_95_ci"], [0, 0.25])
        self.assertEqual((primary["positive_worlds"], primary["zero_worlds"], primary["negative_worlds"]), (1, 11, 0))
        self.assertEqual((primary["paired_improved_cases"], primary["paired_unchanged_cases"]), (2, 22))

    def test_constant_and_reversed_answers_are_not_record_tracking(self):
        worlds = {world["id"]: world for world in self.plan["worlds"]}
        for behavior, accuracy, sensitivity in (("constant", 0.5, 0), ("reverse", 0, -1)):
            def choose(task, result):
                if task["arm"] != "reasoning_first":
                    return result
                key = "record_1" if behavior == "constant" or task["value"] == "record_2" else "record_2"
                return answer_response(task["arm"], worlds[task["world_id"]]["roles"][key])
            report, _ = summarize(self.plan, fixture(self.plan, choose))
            self.assertEqual(report["effects"]["accuracy/reasoning_first"]["mean"], accuracy)
            self.assertEqual(report["effects"]["record_sensitivity/reasoning_first"]["mean"], sensitivity)
            self.assertEqual(report["effects"]["record_sensitivity/answer_first_minus_reasoning_first"]["mean"], 1 - sensitivity)
            pairs = next(item for item in report["record_pair_counts"] if item["arm"] == "reasoning_first")
            self.assertEqual(pairs["n_answer_changed"], 0 if behavior == "constant" else 12)
            self.assertEqual(pairs["n_exactly_one_correct"], 12 if behavior == "constant" else 0)

    def test_incomplete_worlds_are_excluded_only_where_required(self):
        records = fixture(self.plan)
        missing = next(record for record in records if record["meta"]["arm"] == "reasoning_first")
        report, _ = summarize(self.plan, [r for r in records if r is not missing])
        self.assertEqual((report["analysis_status"], report["pending_tasks"]), ("incomplete", 1))
        self.assertFalse(report["interpretation_allowed"])
        effect = report["effects"]["accuracy/answer_first_minus_reasoning_first"]
        self.assertEqual((effect["n_worlds"], effect["mean"]), (11, 0))
        self.assertEqual(effect["excluded_world_ids"], [missing["meta"]["world_id"]])
        self.assertIsNone(effect["full_plan_unscorable_bounds"])
        self.assertEqual(report["effects"]["accuracy/answer_only_minus_answer_first"]["n_worlds"], 12)

    def test_wrong_order_fails_manipulation_and_retains_full_plan_bounds(self):
        target = next(task for task in self.plan["tasks"] if task["arm"] == "reasoning_first")
        def choose(task, result):
            return (answer_response("answer_first", task_meta(self.plan, task)["expected"])
                    if task["id"] == target["id"] else result)
        records = fixture(self.plan, choose)
        report, rows = summarize(self.plan, records)
        self.assertEqual(report["analysis_status"], "technical_failure_output_manipulation")
        self.assertTrue(report["output_manipulation_failed"])
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual(report["valid_answers"], 71)
        self.assertIsNone(next(row for row in rows if row["task_id"] == target["id"])["correct"])
        for measure, bound in (("accuracy", 1 / 24), ("record_sensitivity", 1 / 12)):
            effect = report["effects"][f"{measure}/answer_first_minus_reasoning_first"]
            self.assertEqual(effect["n_worlds"], 11)
            self.assertEqual(effect["full_plan_unscorable_bounds"], [0, bound])
        partial, _ = summarize(self.plan, [r for r in records if r["task_id"] == target["id"]])
        self.assertEqual(partial["analysis_status"], "technical_failure_output_manipulation")
        self.assertIsNone(partial["effects"]["accuracy/answer_first_minus_reasoning_first"]["full_plan_unscorable_bounds"])
        with tempfile.TemporaryDirectory() as output:
            write_summary(output, self.plan, records)
            text = (Path(output) / "summary.md").read_text()
            self.assertIn("output manipulation failed", text)
            self.assertNotIn("## Primary paired accuracy contrast", text)


class OrderRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return run(config(), self.output, calls, mock=True, **kwargs)

    def test_preview_is_offline_and_preserves_schema_key_order(self):
        with run_lock(self.output), patch.object(provider, "complete", side_effect=AssertionError("no network")), \
             patch.object(provider, "credential", side_effect=AssertionError("no key access")):
            plan = prepare(config(), self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 72)
        for row, task in zip(preview, plan["tasks"]):
            self.assertEqual(json.dumps(row["request"]), json.dumps(request_for(plan, task)))
        self.assertFalse((self.output / "execution.json").exists())
        old = Path(self.temp.name) / "old"
        with run_lock(old):
            (old / "summary.md").write_text("old results")
            with self.assertRaisesRegex(ValueError, "not empty"):
                prepare(config(), old)

    def test_mock_six_then_resume_finishes_exactly_72_without_network_or_overwrites(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("key access forbidden")):
            first = self.invoke(6)
            self.assertEqual((first["calls_this_invocation"], first["valid_answers"]), (6, 6))
            before = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
            result = self.invoke(72, resume=True)
        self.assertEqual((result["calls_this_invocation"], result["valid_answers"], result["stopped"]), (66, 72, "complete"))
        self.assertEqual(result["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(self.invoke(1, resume=True)["calls_this_invocation"], 0)

    def test_returned_invalid_answer_stops_and_cannot_be_resampled_or_skipped(self):
        result = self.invoke(8, complete_fn=lambda c, p: response('{"answer":"A","unexpected":"x"}'))
        self.assertEqual((result["stopped"], result["calls_this_invocation"], result["invalid_answers_retained"]),
                         ("invalid_response", 1, 1))
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        for retry in (False, True):
            with self.assertRaisesRegex(ValueError, "do not resample"):
                self.invoke(1, resume=True, retry_errors=retry)
        self.assertEqual(path.read_bytes(), before)
        plan, _, attempts = read_run(self.output)
        self.assertEqual(attempts[0]["response"]["raw_response"]["choices"][0]["message"]["content"],
                         '{"answer":"A","unexpected":"x"}')
        write_json(self.output / "attempts/000002.json", fixture(plan)[1])
        with self.assertRaisesRegex(ValueError, "after a returned invalid"):
            read_run(self.output)

    def test_wrong_valid_answer_is_data_and_never_triggers_revision(self):
        plan = make_plan(config())
        by_request = {json.dumps(request_for(plan, task)): task for task in plan["tasks"]}
        def wrong(c, payload):
            task = by_request[json.dumps(payload)]
            return answer_response(task["arm"], task_meta(plan, task)["pattern_label"], "The pattern favors this answer.")
        result = self.invoke(6, complete_fn=wrong)
        self.assertEqual((result["calls_this_invocation"], result["valid_answers"]), (6, 6))
        _, _, attempts = read_run(self.output)
        self.assertEqual(len(attempts), 6)
        self.assertTrue(all(a["answer"] == a["meta"]["pattern_label"] for a in attempts))
        self.assertEqual(len({a["task_id"] for a in attempts}), 6)
        before = (self.output / "attempts/000001.json").read_bytes()
        self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), before)

    def test_transport_error_requires_explicit_retry_and_preserves_error(self):
        def failure(c, p):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke(8, complete_fn=failure)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        blocked = self.invoke(8, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        success = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((success["attempts_total"], success["valid_answers"]), (2, 1))
        self.assertEqual(path.read_bytes(), before)

    def test_interruption_is_journaled_before_call_and_attempt_cap_is_cumulative(self):
        def interrupt(c, p):
            saved = json.loads((self.output / "attempts/000001.json").read_text())
            self.assertEqual(saved["status"], "started")
            self.assertEqual(json.dumps(saved["request"]), json.dumps(p))
            raise KeyboardInterrupt
        self.assertEqual(self.invoke(8, complete_fn=interrupt)["stopped"], "interrupted")
        self.assertEqual(self.invoke(1, resume=True)["stopped"], "retry_requires_flag")
        first = json.loads((self.output / "attempts/000001.json").read_text())
        for number in range(2, 88):
            write_json(self.output / "attempts" / f"{number:06d}.json", {**first, "attempt": number})
        final = self.invoke(100, resume=True, retry_errors=True)
        self.assertEqual((final["stopped"], final["calls_this_invocation"], final["attempts_total"]),
                         ("total_attempt_limit", 1, 88))
        self.assertEqual(self.invoke(100, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_request_audit_detects_property_order_change_despite_dict_equality(self):
        self.invoke(6)
        path = next(path for path in sorted((self.output / "attempts").glob("*.json"))
                    if json.loads(path.read_text())["meta"]["arm"] == "reasoning_first")
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        schema = changed["request"]["response_format"]["json_schema"]["schema"]
        schema["properties"] = dict(reversed(list(schema["properties"].items())))
        self.assertEqual(changed["request"], original["request"])
        self.assertNotEqual(json.dumps(changed["request"]), json.dumps(original["request"]))
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            read_run(self.output)

    def test_mode_source_plan_raw_scoring_and_schema_are_audited(self):
        self.invoke(1)
        with self.assertRaisesRegex(ValueError, "resume"):
            self.invoke(1)
        with self.assertRaisesRegex(ValueError, "identity"):
            run(config(), self.output, 1, resume=True, mock=False)
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(), self.output, 1, complete_fn=lambda c, p: answer_response("answer_only", "A"))
        with patch("exception_order.core.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                self.invoke(1, resume=True)
        plan_path = self.output / "plan.json"
        original_plan = json.loads(plan_path.read_text())
        changed_plan = copy.deepcopy(original_plan)
        changed_plan["worlds"][0]["roles"]["pattern"] = "Z"
        changed_plan["plan_hash"] = digest({k: v for k, v in changed_plan.items() if k != "plan_hash"})
        write_json(plan_path, changed_plan)
        with self.assertRaisesRegex(ValueError, "Code or saved plan"):
            read_run(self.output)
        write_json(plan_path, original_plan)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        for field in ("response", "scoring", "schema"):
            changed = copy.deepcopy(original)
            if field == "response":
                changed["response"]["text"] = "tampered"
            elif field == "scoring":
                changed["key_order_valid"] = False
            else:
                changed["request"]["response_format"]["json_schema"]["strict"] = False
            write_json(path, changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                read_run(self.output)

    def test_duplicate_returns_and_reordered_schedule_are_rejected(self):
        self.invoke(2)
        first_path, second_path = (self.output / f"attempts/{i:06d}.json" for i in (1, 2))
        first, second = json.loads(first_path.read_text()), json.loads(second_path.read_text())
        write_json(second_path, {**first, "attempt": 2})
        with self.assertRaises(ValueError):
            read_run(self.output)
        write_json(first_path, {**second, "attempt": 1})
        write_json(second_path, {**first, "attempt": 2})
        with self.assertRaisesRegex(ValueError, "schedule"):
            read_run(self.output)


if __name__ == "__main__":
    unittest.main()
