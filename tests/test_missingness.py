"""Offline integrity checks for the selected-case missingness intervention.

These fixtures are synthetic; private parent responses are never committed.
"""

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
from exception_pilot.storage import write_json
from exception_missingness import core
from exception_missingness.analysis import replay_gate, summarize


def response(text, finish="stop"):
    return provider.normalize({"id": "synthetic-missingness-fixture",
        "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text},
                     "finish_reason": finish}]})


def sources():
    records = []
    worlds = (0, 1, 5, 6, 8, 10, 10, 14, 18, 20)
    numbers = (2, 22, 82, 105, 129, 167, 170, 240, 297, 329)
    for index, (number, world) in enumerate(zip(numbers, worlds)):
        target = f"ETEST{index:02d}"
        value = "record_2" if number == 167 else "record_1"
        world_id = f"ex-list-{world:03d}"
        original_answer = "A" if number in (2, 170) else "B"
        original_prompt = (f"Accurate records.\n| {target} | A |\n"
                           f"| EOTHER | B |\nClass for {target}? Think step by step.")
        # A non-target missingness mention must not be edited or chosen as the cut.
        text = ("Prior notes: EOTHER: MISSING\n"
                f"- {target}: Manual - MISSING\n"
                f"Later notes: {target}: MISSING\nThe pattern suggests B.\n"
                f"ANSWER: {original_answer}")
        records.append({"attempt": number, "task_id": f"{world_id}/{value}/cot",
            "status": "complete", "answer": original_answer,
            "request": {"messages": [{"role": "user", "content": original_prompt}]},
            "response": {"text": text},
            "meta": {"world_id": world_id, "family": "diagnostic", "arm": "cot",
                     "value": value, "item_id": target, "expected": "A", "pattern_label": "B"}})
    return records


class SyntheticPlan(unittest.TestCase):
    def setUp(self):
        self.sources = sources()
        self.source_patch = patch.object(core, "SOURCE_HASHES",
            {source["attempt"]: digest(source) for source in self.sources})
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)
        self.plan = core.make_plan(copy.deepcopy(core.DEFAULT_CONFIG), self.sources)

    def records(self, choose=None):
        records = []
        for task in self.plan["tasks"]:
            case = core.case_for(self.plan, task)
            answer = case["original_answer"] if task["arm"] == "original" else case["expected"]
            if choose is not None:
                answer = choose(task, case, answer)
            result = response("unparseable" if answer is None else f"ANSWER: {answer}")
            records.append({"attempt": len(records) + 1, "task_id": task["id"],
                "plan_hash": self.plan["plan_hash"], "mode": "mock",
                "request": core.request_for(self.plan, task), "meta": core.task_meta(self.plan, task),
                "response": result, **core.score_response(task, result)})
        return records


class MissingnessDesignTests(SyntheticPlan):
    def test_first_target_missingness_cut_and_only_local_replacement(self):
        for case, source in zip(self.plan["cases"], self.sources):
            self.assertEqual(case["cut_line_1based"], 2)
            self.assertEqual(case["prefix"], "\n".join(source["response"]["text"].splitlines()[:2]))
            self.assertNotIn("Later notes", case["prefix"])
            self.assertNotIn("ANSWER:", case["prefix"])
            for arm, replacement in (("original", "MISSING"),
                    ("available", "RECORDED IN THE TABLE"),
                    ("unavailable", "NOT RECORDED IN THE TABLE"), ("gold", "A")):
                prefix = core.edited_prefix(case, arm)
                self.assertEqual(prefix, case["before_edit_line"] + case["edit_line"].replace("MISSING", replacement))
                self.assertTrue(prefix.startswith("Prior notes: EOTHER: MISSING\n"))
            self.assertEqual(core.edited_prefix(case, "unavailable").replace("NOT RECORDED", "RECORDED"),
                             core.edited_prefix(case, "available"))

    def test_original_prompt_and_continuation_held_fixed_no_source_mutation(self):
        before = copy.deepcopy(self.sources)
        for task in self.plan["tasks"]:
            case = core.case_for(self.plan, task)
            request = core.request_for(self.plan, task)
            self.assertEqual(request["messages"][:-2], case["original_messages"])
            self.assertEqual(request["messages"][-2]["role"], "assistant")
            self.assertEqual(request["messages"][-1], {"role": "user", "content": core.CONTINUATION})
            self.assertEqual(request["max_completion_tokens"], 1000)
            self.assertEqual(request["model"], "gpt-4o-2024-08-06")
            self.assertEqual(request["n"], 1)
            self.assertFalse(request["store"])
            request["messages"][0]["content"] = "mutated local copy"
            self.assertNotEqual(case["original_messages"][0]["content"], "mutated local copy")
        self.assertEqual(self.sources, before)
        self.assertEqual(len(self.plan["tasks"]), 40)
        self.assertEqual([task["arm"] for task in self.plan["tasks"][:10]], ["original"] * 10)
        self.assertNotIn("original", [task["arm"] for task in self.plan["tasks"][10:]])

    def test_source_tampering_rejected_even_before_plan_generation(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["response"]["text"] += " injected"
        with self.assertRaisesRegex(ValueError, "audited source"):
            core.make_plan(core.DEFAULT_CONFIG, changed)
        with self.assertRaisesRegex(ValueError, "selection or order"):
            core.make_plan(core.DEFAULT_CONFIG, list(reversed(self.sources)))

    def test_rehashed_plan_or_changed_code_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            changed = copy.deepcopy(self.plan)
            changed["cases"][0]["prefix"] += " ANSWER: A"
            changed["plan_hash"] = digest({k: v for k, v in changed.items() if k != "plan_hash"})
            write_json(output / "plan.json", changed)
            with self.assertRaises(ValueError):
                core.read_plan(output)
            write_json(output / "plan.json", self.plan)
            with patch.object(core, "source_digest", return_value="different source"):
                with self.assertRaisesRegex(ValueError, "Saved plan or code"):
                    core.read_plan(output)


class MissingnessAnalysisTests(SyntheticPlan):
    def test_replay_gate_needs_all_ten_scorable_and_eight_exact_matches(self):
        complete = self.records()[:10]
        self.assertEqual(replay_gate(self.plan, complete[:9])["status"], "incomplete")
        self.assertEqual(replay_gate(self.plan, complete)["status"], "pass")
        # Exactly eight matches passes; two originally correct cases remain in the gate.
        for index in (0, 1):
            complete[index]["answer"] = "C"
        self.assertEqual(replay_gate(self.plan, complete)["exact_matches"], 8)
        self.assertEqual(replay_gate(self.plan, complete)["status"], "pass")
        complete[2]["answer"] = "C"
        self.assertEqual(replay_gate(self.plan, complete)["status"], "stop")
        invalid = self.records()[:10]
        invalid[0].update(status="invalid", answer=None)
        self.assertEqual(replay_gate(self.plan, invalid)["status"], "stop")

    def test_two_cases_in_one_world_share_that_worlds_weight(self):
        def choose(task, case, answer):
            if task["arm"] in ("available", "unavailable"):
                return "A" if task["arm"] == "available" and case["source_attempt"] == 167 else "B"
            return answer
        report, _ = summarize(self.plan, self.records(choose))
        primary = report["effects"]["available_minus_unavailable"]
        self.assertEqual(primary["n_worlds"], 9)
        self.assertAlmostEqual(primary["mean"], 1 / 18)
        self.assertAlmostEqual(primary["case_weighted_mean"], 1 / 10)
        world = next(w for w in report["world_metrics"] if w["world_id"] == "ex-list-010")
        self.assertEqual(world["metrics"]["available_minus_unavailable"], .5)

    def test_invalid_one_case_excludes_its_world_and_bounds_retain_plan(self):
        def choose(task, case, answer):
            if task["arm"] in ("available", "unavailable"):
                return None if task["arm"] == "available" and case["source_attempt"] == 167 else "B"
            return answer
        report, _ = summarize(self.plan, self.records(choose))
        primary = report["effects"]["available_minus_unavailable"]
        self.assertEqual(primary["n_worlds"], 8)
        self.assertEqual(primary["n_paired_cases"], 9)
        self.assertEqual(primary["mean"], 0)
        self.assertEqual(primary["full_plan_unscorable_bounds"], [0, 1 / 18])


class MissingnessRunnerTests(SyntheticPlan):
    def setUp(self):
        super().setUp()
        from exception_missingness import runner
        self.runner = runner
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"
        write_json(self.output / "plan.json", self.plan)

    def invoke(self, phase, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return self.runner.run(self.output, phase, calls, mock=True, **kwargs)

    def test_phase_isolation_mock_never_accesses_keys_or_network_and_resume_bytes(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            first = self.invoke("replay", 48)
            self.assertEqual(first["calls_this_invocation"], 10)
            old = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
            self.assertEqual(len(old), 10)
            self.assertEqual(self.invoke("replay", 48, resume=True)["calls_this_invocation"], 0)
            result = self.invoke("interventions", 48, resume=True)
            self.assertEqual(result["calls_this_invocation"], 30)
            self.assertEqual(result["attempts_total"], 40)
            self.assertEqual(self.invoke("interventions", 48, resume=True)["calls_this_invocation"], 0)
        for name, data in old.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), data)

    def test_failed_or_incomplete_replay_blocks_intervention_calls(self):
        calls = []
        def wrong(config, payload):
            calls.append(payload)
            return response("ANSWER: C")
        # No replay yet: even live mode must stop before credential access.
        with patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            result = self.runner.run(self.output, "interventions", 48)
        self.assertEqual(result["calls_this_invocation"], 0)
        self.invoke("replay", 1, complete_fn=wrong)
        result = self.invoke("interventions", 48, resume=True, complete_fn=wrong)
        self.assertEqual(result["calls_this_invocation"], 0)
        self.assertEqual(len(calls), 1)
        self.invoke("replay", 9, resume=True, complete_fn=wrong)
        self.assertEqual(len(calls), 10)
        result = self.invoke("interventions", 48, resume=True, complete_fn=wrong)
        self.assertEqual(result["calls_this_invocation"], 0)
        self.assertEqual(len(calls), 10)

    def test_invalid_return_is_retained_not_retried(self):
        first = self.invoke("replay", 1, complete_fn=lambda c, p: response("No final label"))
        self.assertEqual(first["calls_this_invocation"], 1)
        path = self.output / "attempts/000001.json"
        old = path.read_bytes()
        self.assertEqual(json.loads(old)["status"], "invalid")
        result = self.invoke("replay", 48, resume=True, retry_errors=True)
        self.assertEqual(result["calls_this_invocation"], 9)
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(self.invoke("interventions", 48, resume=True)["calls_this_invocation"], 0)

    def test_transport_retry_requires_explicit_flag_and_cumulative_cap_is_48(self):
        def failure(config, payload):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke("replay", 48, complete_fn=failure)
        self.assertEqual(first["calls_this_invocation"], 1)
        self.assertEqual(first["stopped"], "provider_error")
        blocked = self.invoke("replay", 48, resume=True)
        self.assertEqual(blocked["calls_this_invocation"], 0)
        self.assertEqual(blocked["stopped"], "retry_requires_flag")
        failed = json.loads((self.output / "attempts/000001.json").read_text())
        for number in range(2, 48):
            write_json(self.output / "attempts" / f"{number:06d}.json", {**failed, "attempt": number})
        result = self.invoke("replay", 48, resume=True, retry_errors=True)
        self.assertEqual(result["calls_this_invocation"], 1)
        self.assertEqual(result["attempts_total"], 48)
        self.assertEqual(result["stopped"], "total_attempt_limit")
        self.assertEqual(self.invoke("replay", 48, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_truncated_return_blocks_resampling(self):
        first = self.invoke("replay", 10, complete_fn=lambda c, p: response("ANSWER: A", "length"))
        self.assertEqual(first["stopped"], "invalid_provider_response")
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.invoke("replay", 10, resume=True, retry_errors=True)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(list((self.output / "attempts").glob("*.json"))), 1)

    def test_journal_cannot_introduce_intervention_before_gate(self):
        self.invoke("replay", 1)
        task = self.plan["tasks"][10]
        result = response("ANSWER: A")
        record = {"attempt": 2, "task_id": task["id"], "plan_hash": self.plan["plan_hash"],
            "mode": "mock", "phase": "interventions", "request": core.request_for(self.plan, task),
            "meta": core.task_meta(self.plan, task), "response": result, **core.score_response(task, result)}
        write_json(self.output / "attempts/000002.json", record)
        with self.assertRaisesRegex(ValueError, "before the replay"):
            self.runner.read_run(self.output)

    def test_execution_identity_saved_request_and_raw_response_tampering(self):
        self.invoke("replay", 1)
        with self.assertRaises(ValueError):
            self.invoke("replay", 1)
        with self.assertRaises(ValueError):
            self.runner.run(self.output, "replay", 1, resume=True, mock=False)
        with self.assertRaises(ValueError):
            self.runner.read_run(self.output, expected_mode="live")
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["request"]["messages"][-2]["content"] += " injected"
        write_json(path, changed)
        with self.assertRaises(ValueError):
            self.runner.read_run(self.output)
        write_json(path, original)
        changed = copy.deepcopy(original)
        changed["response"]["text"] = "ANSWER: C"
        write_json(path, changed)
        with self.assertRaises(ValueError):
            self.runner.read_run(self.output)


if __name__ == "__main__":
    unittest.main()
