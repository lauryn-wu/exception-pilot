"""Offline checks of the cue diagnostic's controls, estimands, and data retention."""

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
from exception_explanation.core import INTRO as ORIGINAL_INTRO
from exception_cue.analysis import summarize
from exception_cue.core import (ARMS, VALUES, load_config, make_plan,
    messages_for, request_for, score_response, task_meta, validate_config)
from exception_cue.runner import (mock_complete, normalized_response, prepare,
                                 read_run, run)

ROOT = Path(__file__).resolve().parents[1]


def config():
    return load_config(ROOT / "configs/cue.json")


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
    return response("\n".join(result["text"].splitlines()[:-1] + ["ANSWER: " + answer]))


class CueDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_fresh_balanced_fixed_design(self):
        plan = self.plan
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["tasks"]), 144)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 144)
        plates = [x["id"] for w in plan["worlds"] for x in w["items"]]
        self.assertEqual(len(set(plates)), 240)
        self.assertTrue(all(p.startswith("Q") for p in plates))
        roles = Counter(tuple(w["roles"].values()) for w in plan["worlds"])
        self.assertEqual(len(roles), 6)
        self.assertEqual(set(roles.values()), {4})
        assignments = Counter((tuple(w["roles"].values()), w["items"][w["target_index"]]["climate"])
                              for w in plan["worlds"])
        self.assertEqual(set(assignments.values()), {2})
        schedules = []
        for world in plan["worlds"]:
            tasks = [t for t in plan["tasks"] if t["world_id"] == world["id"]]
            self.assertEqual(Counter((t["value"], t["arm"]) for t in tasks),
                             Counter((value, arm) for value in VALUES for arm in ARMS))
            schedules.append(tuple((t["value"], t["arm"]) for t in tasks))
            target = world["target_index"]
            peers = [j for j, item in enumerate(world["items"]) if j != target
                     and item["climate"] == world["items"][target]["climate"]]
            for value in VALUES:
                self.assertEqual(world["record_labels"][value][target], world["roles"][value])
                self.assertEqual([world["record_labels"][value][j] for j in peers],
                                 [world["roles"]["pattern"]] * 4)
        self.assertGreater(len(set(schedules)), 1)

    def test_only_target_class_cell_changes_between_paired_questions(self):
        for world in self.plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in ARMS:
                task = {"world_id": world["id"], "family": "diagnostic", "arm": arm, "value": "record_1"}
                first = messages_for(self.plan, task)[0]["content"].splitlines()
                second = messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
                self.assertEqual(len(first), len(second))
                changes = [(a, b) for a, b in zip(first, second) if a != b]
                self.assertEqual(len(changes), 1)
                a, b = changes[0]
                self.assertIn(target_id, a)
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_exact_prompt_controls_keep_existing_task_wording(self):
        endings = {
            "direct": "Output only ANSWER: followed by A, B, or C.",
            "cue": "Think step by step before answering. Output only ANSWER: followed by A, B, or C.",
            "visible": "Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.",
        }
        bodies = {}
        for task in self.plan["tasks"]:
            messages = messages_for(self.plan, task)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["role"], "user")
            body, ending = messages[0]["content"].rsplit("\n", 1)
            self.assertEqual(ending, endings[task["arm"]])
            self.assertTrue(body.startswith(ORIGINAL_INTRO + "\n"))
            self.assertIn("MISSING means the verified class has not been recorded.", body)
            key = (task["world_id"], task["value"])
            if key in bodies:
                self.assertEqual(body, bodies[key])
            bodies[key] = body

    def test_identical_token_caps_and_no_answer_key_in_request(self):
        for task in self.plan["tasks"]:
            req = request_for(self.plan, task)
            self.assertEqual(req["max_completion_tokens"], 1000)
            self.assertEqual(req["model"], "gpt-4o-2024-08-06")
            self.assertEqual(req["temperature"], 0)
            self.assertFalse(req["store"])
            self.assertEqual(req["n"], 1)
            self.assertNotIn("api_key_env", req)
            self.assertNotIn("expected", req)
            self.assertNotIn("cue-list", req["messages"][0]["content"])
        for key, value in (("seed", 2026100893), ("n_worlds", 30), ("n_worlds", True),
                           ("max_total_attempts", 161), ("model", "gpt-4o"), ("temperature", 1),
                           ("max_completion_tokens", {"direct": 16, "cue": 1000, "visible": 1000}),
                           ("timeout_seconds", float("nan")), ("api_key_env", "secret value"),
                           ("extra", "not allowed")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})

    def test_output_contract_is_separate_from_final_answer_parseability(self):
        for arm in ARMS:
            direct = score_response({"arm": arm}, response("ANSWER: B"))
            prose = score_response({"arm": arm}, response("The table has a recorded class.\nANSWER: B"))
            for scored in (direct, prose):
                self.assertEqual((scored["answer"], scored["status"]), ("B", "complete"))
            self.assertTrue(direct["answer_only"])
            self.assertFalse(direct["pre_answer_text"])
            self.assertEqual(direct["output_contract_met"], arm != "visible")
            self.assertFalse(prose["answer_only"])
            self.assertTrue(prose["pre_answer_text"])
            self.assertEqual(prose["output_contract_met"], arm == "visible")
            for text in ("The answer is B.", "ANSWER: B\nActually A", "ANSWER: b", "**ANSWER: B**"):
                scored = score_response({"arm": arm}, response(text))
                self.assertEqual(scored["status"], "invalid")
                self.assertIsNone(scored["answer"])
                self.assertIsNone(scored["pre_answer_text"])
                self.assertFalse(scored["output_contract_met"])
            self.assertIsNone(score_response({"arm": arm}, response("ANSWER: B", "length"))["answer"])


class CueAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_all_correct_mock_is_zero_contrast_not_scientific_evidence(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertTrue(report["is_simulated"])
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertEqual(len(rows), 144)
        for measure in ("accuracy", "record_sensitivity"):
            for contrast in ("direct_minus_cue", "cue_minus_visible", "direct_minus_visible"):
                effect = report["effects"][f"{measure}/{contrast}"]
                self.assertEqual(effect["mean"], 0)
                self.assertEqual(effect["n_worlds"], 24)
        for arm in ARMS:
            self.assertEqual(report["effects"][f"record_sensitivity/{arm}"]["mean"], 1)

    def test_pattern_answers_lose_accuracy_and_record_sensitivity(self):
        def choose(task, result):
            return (replace_final(result, task_meta(self.plan, task)["pattern_label"])
                    if task["arm"] == "visible" else result)
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        for measure in ("accuracy", "record_sensitivity"):
            self.assertEqual(report["effects"][f"{measure}/direct_minus_cue"]["mean"], 0)
            self.assertEqual(report["effects"][f"{measure}/cue_minus_visible"]["mean"], 1)
            self.assertEqual(report["effects"][f"{measure}/direct_minus_visible"]["mean"], 1)
        self.assertEqual(report["effects"]["record_sensitivity/visible"]["mean"], 0)

    def test_constant_or_reversed_answers_are_not_record_tracking(self):
        worlds = {w["id"]: w for w in self.plan["worlds"]}
        for behavior, expected in (("constant", 0), ("reverse", -1)):
            def choose(task, result):
                if task["arm"] == "cue":
                    roles = worlds[task["world_id"]]["roles"]
                    value = "record_1" if behavior == "constant" or task["value"] == "record_2" else "record_2"
                    return replace_final(result, roles[value])
                return result
            report, _ = summarize(self.plan, fixture(self.plan, choose))
            self.assertEqual(report["effects"]["record_sensitivity/cue"]["mean"], expected)
            self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cue"]["mean"], 1 - expected)

    def test_invalid_answers_exclude_whole_world_per_contrast_and_give_bounds(self):
        target = "cue-list-000/record_1/cue"
        records = fixture(self.plan, lambda t, r: response("unparseable") if t["id"] == target else r)
        report, _ = summarize(self.plan, records)
        for measure in ("accuracy", "record_sensitivity"):
            affected = report["effects"][f"{measure}/direct_minus_cue"]
            self.assertEqual(affected["n_worlds"], 23)
            self.assertEqual(affected["mean"], 0)
            self.assertIsNotNone(affected["full_plan_unscorable_bounds"])
            self.assertEqual(report["effects"][f"{measure}/direct_minus_visible"]["n_worlds"], 24)
        self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["full_plan_unscorable_bounds"], [0, 1 / 48])
        self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cue"]["full_plan_unscorable_bounds"], [0, 1 / 24])
        self.assertEqual(report["analysis_status"], "complete_with_unscorable_answers")

    def test_format_noncompliance_does_not_select_accuracy_sample(self):
        def choose(task, result):
            final = result["text"].splitlines()[-1]
            return response(final if task["arm"] == "visible" else "Unrequested prose.\n" + final)
        report, rows = summarize(self.plan, fixture(self.plan, choose))
        self.assertEqual(report["valid_answers"], 144)
        self.assertTrue(all(r["output_contract_met"] is False for r in rows))
        self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["n_worlds"], 24)
        self.assertEqual(report["effects"]["accuracy/cue_minus_visible"]["mean"], 0)


class CueRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return run(config(), self.output, calls, mock=True, **kwargs)

    def test_mock_and_resume_do_not_read_key_call_network_or_overwrite_records(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("key access forbidden")):
            first = self.invoke(6)
            self.assertEqual(first["calls_this_invocation"], 6)
            before = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
            result = self.invoke(144, resume=True)
        self.assertEqual(result["calls_this_invocation"], 138)
        self.assertEqual(result["stopped"], "complete")
        self.assertEqual(result["valid_answers"], 144)
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(self.invoke(1, resume=True)["calls_this_invocation"], 0)

    def test_parseable_contract_violations_are_retained_without_resampling(self):
        result = self.invoke(6, complete_fn=lambda c, p: response("ANSWER: A"))
        self.assertEqual(result["valid_answers"], 6)
        before = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
        plan, _, attempts = read_run(self.output)
        visible = [a for a in attempts if a["meta"]["arm"] == "visible"]
        self.assertEqual(len(visible), 2)
        self.assertTrue(all(a["status"] == "complete" and not a["output_contract_met"] for a in visible))
        self.invoke(1, resume=True, retry_errors=True)
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(json.loads((self.output / "attempts/000007.json").read_text())["task_id"], plan["tasks"][6]["id"])

    def test_unparseable_answers_are_retained_without_resampling(self):
        first = self.invoke(2, complete_fn=lambda c, p: response("No valid final answer"))
        self.assertEqual(first["invalid_answers_retained"], 2)
        before = [(self.output / "attempts" / f"{i:06d}.json").read_bytes() for i in (1, 2)]
        after = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual(after["attempts_total"], 3)
        for i, content in enumerate(before, 1):
            self.assertEqual((self.output / "attempts" / f"{i:06d}.json").read_bytes(), content)

    def test_transport_failure_requires_explicit_retry_and_counts_against_cap(self):
        def failure(c, p):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke(8, complete_fn=failure)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        blocked = self.invoke(8, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        success = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((success["attempts_total"], success["valid_answers"]), (2, 1))

    def test_truncation_is_retained_and_blocks_resampling(self):
        result = self.invoke(8, complete_fn=lambda c, p: response("ANSWER: A", "length"))
        self.assertEqual(result["stopped"], "invalid_provider_response")
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual(len(list((self.output / "attempts").glob("*.json"))), 1)

    def test_interruption_journal_precedes_provider_call(self):
        def interrupt(c, p):
            raise KeyboardInterrupt
        result = self.invoke(8, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        self.assertEqual(json.loads((self.output / "attempts/000001.json").read_text())["status"], "started")
        self.assertEqual(self.invoke(1, resume=True)["stopped"], "retry_requires_flag")
        self.assertEqual(self.invoke(1, resume=True, retry_errors=True)["valid_answers"], 1)

    def test_cumulative_attempt_cap_survives_resume(self):
        def failure(c, p):
            raise provider.ProviderError("TimeoutError")
        self.invoke(1, complete_fn=failure)
        first = json.loads((self.output / "attempts/000001.json").read_text())
        for n in range(2, 160):
            write_json(self.output / "attempts" / f"{n:06d}.json", {**first, "attempt": n})
        result = self.invoke(100, resume=True, retry_errors=True)
        self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                         ("total_attempt_limit", 1, 160))
        self.assertEqual(self.invoke(100, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_saved_identity_source_raw_text_and_request_are_audited(self):
        self.invoke(1)
        with self.assertRaisesRegex(ValueError, "resume"):
            self.invoke(1)
        with self.assertRaisesRegex(ValueError, "identity"):
            run(config(), self.output, 1, resume=True, mock=False)
        with patch("exception_cue.core.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                self.invoke(1, resume=True)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["response"]["text"] = "tampered"
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "raw provider"):
            read_run(self.output)
        write_json(path, original)
        changed = copy.deepcopy(original)
        changed["request"]["max_completion_tokens"] = 16
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            read_run(self.output)

    def test_rehashed_plan_change_duplicate_return_and_wrong_schedule_rejected(self):
        self.invoke(2)
        original_plan = json.loads((self.output / "plan.json").read_text())
        changed = copy.deepcopy(original_plan)
        changed["worlds"][0]["roles"]["pattern"] = "Z"
        changed["plan_hash"] = digest({k: v for k, v in changed.items() if k != "plan_hash"})
        write_json(self.output / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "Code or saved plan"):
            read_run(self.output)
        write_json(self.output / "plan.json", original_plan)
        first = json.loads((self.output / "attempts/000001.json").read_text())
        second = json.loads((self.output / "attempts/000002.json").read_text())
        write_json(self.output / "attempts/000002.json", {**first, "attempt": 2})
        with self.assertRaises(ValueError):
            read_run(self.output)
        write_json(self.output / "attempts/000001.json", {**second, "attempt": 1})
        write_json(self.output / "attempts/000002.json", {**first, "attempt": 2})
        with self.assertRaisesRegex(ValueError, "schedule"):
            read_run(self.output)

    def test_model_refusal_and_live_injected_provider_guards(self):
        raw = response("ANSWER: A")["raw_response"]
        self.assertFalse(normalized_response(raw, config(), "live")["complete"])
        raw["model"] = config()["model"]
        raw["choices"][0]["message"]["refusal"] = "declined"
        self.assertFalse(normalized_response(raw, config(), "live")["complete"])
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(), self.output, 1, complete_fn=lambda c, p: response("ANSWER: A"))

    def test_full_preview_is_offline_and_old_result_directory_is_protected(self):
        with run_lock(self.output), patch.object(provider, "complete", side_effect=AssertionError("no network")), \
             patch.object(provider, "credential", side_effect=AssertionError("no key access")):
            plan = prepare(config(), self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 144)
        self.assertEqual(len(plan["tasks"]), 144)
        self.assertFalse((self.output / "execution.json").exists())
        old = Path(self.temp.name) / "old"
        with run_lock(old):
            (old / "summary.md").write_text("old results")
            with self.assertRaisesRegex(ValueError, "not empty"):
                prepare(config(), old)


if __name__ == "__main__":
    unittest.main()
