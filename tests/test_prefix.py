"""Offline safeguards for native-prefix feasibility; synthetic data are not evidence."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, run_lock, write_json
from exception_cue.core import INSTRUCTIONS as CUE_INSTRUCTIONS
from exception_explanation.core import INTRO
from exception_prefix import core, provider, runner
from exception_prefix.analysis import summarize

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODEL = "deepseek-flash-fixture"


def config():
    return core.load_config(ROOT / "configs/prefix.json")


def response(text, model=FIXTURE_MODEL, finish="stop", reasoning_content=None):
    message = {"role": "assistant", "content": text}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return provider.normalize({"id": "synthetic-prefix-fixture", "model": model, "usage": {},
        "choices": [{"message": message, "finish_reason": finish}]})


def base_text(plan, task, wrong=False):
    meta = core.task_meta(plan, task)
    answer = meta["pattern_label"] if wrong else meta["expected"]
    if task["arm"] == "direct":
        return "ANSWER: " + answer
    return (f"Inspect the vehicle {meta['item_id']} among the recorded examples. "
            "Compare the target row with the repeated descriptions before choosing a class. "
            "The listed information provides the basis for this selection.\nANSWER: " + answer)


def fixture(plan, wrong_ids=None, changed_replays=None):
    """Build complete synthetic records, including dynamic requests from saved parents."""
    wrong_ids = set(wrong_ids or [])
    changed_replays = changed_replays or {}
    records, by_id = [], {}
    for task in plan["tasks"]:
        request = core.request_for(plan, task, by_id)
        meta = core.task_meta(plan, task, by_id)
        if task["family"] == "capability":
            text = core.CAPABILITY_EXPECTED_SUFFIX
        elif task["family"] == "base":
            text = base_text(plan, task, task["id"] in wrong_ids)
        else:
            parent = by_id[task["parent_task_id"]]
            prefix = meta["prefix_text"]
            text = parent["response"]["text"][len(prefix):]
            if task["id"] in changed_replays:
                text = text.rsplit("ANSWER: ", 1)[0] + "ANSWER: " + changed_replays[task["id"]]
        result = response(text)
        record = {"attempt": len(records) + 1, "task_id": task["id"],
            "plan_hash": plan["plan_hash"], "mode": "mock", "request": request, "meta": meta,
            "response": result, **core.score_response(task, result, meta)}
        records.append(record)
        by_id[task["id"]] = record
    return records


class PassingProvider:
    """Deterministic observed harm plus exact native suffix replay for runner tests."""
    def __init__(self, plan):
        self.plan = plan
        self.by_request = {json.dumps(core.request_for(plan, task)): task for task in plan["tasks"]
                           if task["family"] != "replay"}
        self.parents = {}

    def __call__(self, cfg, payload):
        task = self.by_request.get(json.dumps(payload))
        if task is not None:
            if task["family"] == "capability":
                return response(core.CAPABILITY_EXPECTED_SUFFIX)
            text = base_text(self.plan, task, wrong=task["arm"] == "visible")
            if task["arm"] == "visible":
                self.parents[json.dumps(payload["messages"])] = text
            return response(text)
        prefix = payload["messages"][-1]
        parent = self.parents[json.dumps(payload["messages"][:-1])]
        assert prefix["role"] == "assistant" and prefix["prefix"] is True
        assert parent.startswith(prefix["content"])
        return response(parent[len(prefix["content"]):])


class PrefixDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan(config())

    def test_fixed_balanced_design_and_capability_first_replay_last(self):
        plan = self.plan
        self.assertEqual(plan, core.make_plan(config()))
        self.assertEqual(len(plan["worlds"]), 12)
        self.assertEqual(len(plan["tasks"]), 73)
        self.assertEqual(len({task["id"] for task in plan["tasks"]}), 73)
        self.assertEqual(plan["tasks"][0]["id"], "prefix-capability")
        self.assertEqual([task["family"] for task in plan["tasks"]],
                         ["capability"] + ["base"] * 48 + ["replay"] * 24)
        plates = [item["id"] for world in plan["worlds"] for item in world["items"]]
        self.assertEqual(len(set(plates)), 120)
        self.assertTrue(all(plate.startswith("N") for plate in plates))
        roles = Counter(tuple(world["roles"].values()) for world in plan["worlds"])
        self.assertEqual((len(roles), set(roles.values())), (6, {2}))
        climates = Counter((tuple(world["roles"].values()),
                            world["items"][world["target_index"]]["climate"])
                           for world in plan["worlds"])
        self.assertEqual((len(climates), set(climates.values())), (12, {1}))
        for world in plan["worlds"]:
            base = [task for task in plan["tasks"] if task.get("world_id") == world["id"] and task["family"] == "base"]
            self.assertEqual(Counter((t["value"], t["arm"]) for t in base),
                             Counter((value, arm) for value in core.VALUES for arm in core.ARMS))
        base_ids = {task["id"] for task in plan["tasks"] if task["family"] == "base" and task["arm"] == "visible"}
        self.assertEqual({task["parent_task_id"] for task in plan["tasks"] if task["family"] == "replay"}, base_ids)

    def test_baseline_record_variants_change_exactly_one_target_cell(self):
        for world in self.plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in core.ARMS:
                task = next(t for t in self.plan["tasks"] if t.get("world_id") == world["id"]
                            and t["family"] == "base" and t["arm"] == arm and t["value"] == "record_1")
                first = core.messages_for(self.plan, task)[0]["content"].splitlines()
                second = core.messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
                self.assertEqual(len(first), len(second))
                differences = [(a, b) for a, b in zip(first, second) if a != b]
                self.assertEqual(len(differences), 1)
                a, b = differences[0]
                self.assertIn(target_id, a)
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_native_request_shapes_capability_and_exact_context_reuse(self):
        records = fixture(self.plan)
        by_id = accepted_records(records)
        for task in self.plan["tasks"]:
            request = core.request_for(self.plan, task, by_id)
            self.assertEqual(request["model"], "deepseek-flash")
            self.assertEqual(request["thinking"], {"type": "disabled"})
            self.assertEqual(request["temperature"], 0)
            self.assertEqual(request["max_tokens"], 32 if task["family"] == "capability" else 1600)
            self.assertEqual(set(request), {"model", "thinking", "temperature", "max_tokens", "messages", "stream"})
            self.assertFalse(request["stream"])
            self.assertNotIn("expected", request)
            if task["family"] == "base":
                self.assertEqual(len(request["messages"]), 1)
                self.assertEqual(request["messages"][0]["role"], "user")
                self.assertNotIn(task["id"], request["messages"][0]["content"])
                self.assertTrue(request["messages"][0]["content"].startswith(INTRO + "\n"))
                self.assertEqual(request["messages"][0]["content"].splitlines()[-1], CUE_INSTRUCTIONS[task["arm"]])
            elif task["family"] == "replay":
                parent = by_id[task["parent_task_id"]]
                self.assertEqual(request["messages"][:-1], parent["request"]["messages"])
                self.assertEqual(request["messages"][-1], {"role": "assistant",
                    "content": by_id[task["id"]]["meta"]["prefix_text"], "prefix": True})
                self.assertEqual(request["messages"][-2]["role"], "user")
                self.assertEqual(len(request["messages"]), 2)
                self.assertNotIn("ANSWER:", request["messages"][-1]["content"])
                request["messages"][0]["content"] += " tampered local copy"
                self.assertNotEqual(request["messages"][0]["content"], parent["request"]["messages"][0]["content"])
        smoke = core.request_for(self.plan, self.plan["tasks"][0])
        self.assertEqual(smoke["messages"], [{"role": "user", "content": core.CAPABILITY_USER},
                         {"role": "assistant", "content": "Cobalt Ma", "prefix": True}])
        self.assertEqual(core.CAPABILITY_EXPECTED_SUFFIX, "ple Lantern")

    def test_capability_requires_exact_suffix_not_echo_or_whitespace_cleanup(self):
        task = self.plan["tasks"][0]
        meta = core.task_meta(self.plan, task)
        good = core.score_response(task, response("ple Lantern"), meta)
        self.assertEqual(good["status"], "complete")
        for text in ("Cobalt Maple Lantern", "ple Lantern\n", " ple Lantern", "ple Lantern.", "ANSWER: A"):
            with self.subTest(text=text):
                self.assertEqual(core.score_response(task, response(text), meta)["status"], "invalid")

    def test_prefix_cut_is_deterministic_lossless_and_independent_of_final_label(self):
        text = "The target row is present. Compare recorded facts before choosing the class.\nANSWER: A"
        cut = core.cut_parent_prefix(text)
        self.assertEqual(cut, core.cut_parent_prefix(text))
        self.assertTrue(cut["prefix_text"].strip())
        self.assertNotIn("ANSWER:", cut["prefix_text"])
        self.assertEqual(cut["prefix_text"] + cut["parent_suffix"], text)
        other = core.cut_parent_prefix(text[:-1] + "C")
        self.assertEqual(cut["prefix_text"], other["prefix_text"])
        self.assertTrue(cut["parent_suffix"].rsplit("ANSWER:", 1)[0].strip())
        for invalid in ("ANSWER: A", "\nANSWER: B", "oneword\nANSWER: C", "not a final answer"):
            with self.subTest(text=invalid), self.assertRaises(core.PrefixUnavailable):
                core.cut_parent_prefix(invalid)
        short = core.cut_parent_prefix("a b\nANSWER: C")
        self.assertEqual(short["prefix_text"] + short["parent_suffix"], "a b\nANSWER: C")
        self.assertTrue(short["prefix_text"].strip())
        self.assertTrue(short["parent_suffix"].rsplit("ANSWER:", 1)[0].strip())
        fallback = core.cut_parent_prefix("longword x\nANSWER: A")
        self.assertEqual(fallback["prefix_text"], "longword ")
        self.assertGreater(fallback["prefix_cut_fraction"], 0.5)

    def test_dynamic_replay_requires_parent_and_scores_literal_prefix_plus_suffix(self):
        replay = next(task for task in self.plan["tasks"] if task["family"] == "replay")
        with self.assertRaises(core.PrefixUnavailable):
            core.request_for(self.plan, replay, {})
        records = fixture(self.plan)
        saved = next(record for record in records if record["task_id"] == replay["id"])
        scored = core.score_response(replay, saved["response"], saved["meta"])
        self.assertEqual(scored["answer"], saved["answer"])
        suffix = saved["response"]["text"]
        full = saved["meta"]["prefix_text"] + suffix
        self.assertEqual(full, next(record for record in records if record["task_id"] == replay["parent_task_id"])["response"]["text"])
        echoed = core.score_response(replay, response(full), saved["meta"])
        self.assertFalse(echoed["replay_exact_suffix_match"])

    def test_baseline_format_failures_are_distinct_from_wrong_but_valid_answers(self):
        direct = next(task for task in self.plan["tasks"] if task["family"] == "base" and task["arm"] == "direct")
        visible = next(task for task in self.plan["tasks"] if task["family"] == "base" and task["arm"] == "visible")
        for task in (direct, visible):
            scored = core.score_response(task, response(base_text(self.plan, task, wrong=True)), core.task_meta(self.plan, task))
            self.assertEqual(scored["status"], "complete")
            self.assertEqual(scored["answer"], core.task_meta(self.plan, task)["pattern_label"])
        for task, text in ((direct, "Extra prose.\nANSWER: A"), (visible, "ANSWER: A"),
                           (visible, "Reasoning.\nANSWER: a"), (visible, "Reasoning.\nANSWER: A\nDone")):
            scored = core.score_response(task, response(text), core.task_meta(self.plan, task))
            self.assertEqual((scored["status"], scored["answer"]), ("invalid", None))

    def test_model_latching_and_no_thinking_channel_are_provider_invariants(self):
        raw = response("ANSWER: A")["raw_response"]
        self.assertTrue(provider.normalize(raw, observed_model=FIXTURE_MODEL)["complete"])
        self.assertFalse(provider.normalize(raw, observed_model="different-model")["complete"])
        for leaked in ("reasoning", " ", "\n"):
            self.assertFalse(response("ANSWER: A", reasoning_content=leaked)["complete"])
        self.assertTrue(response("ANSWER: A", reasoning_content="")["complete"])
        self.assertFalse(response("ANSWER: A", model="")["complete"])
        self.assertFalse(response("ANSWER: A", finish="length")["complete"])

    def test_config_cannot_silently_change_model_endpoint_thinking_or_budget(self):
        for key, value in (("protocol", "other"), ("seed", 2026100942), ("n_worlds", 24),
                           ("n_worlds", True), ("model", "deepseek-chat"), ("temperature", True),
                           ("endpoint", "https://api.deepseek.com/chat/completions"),
                           ("thinking", {"type": "enabled"}), ("max_total_attempts", 90),
                           ("timeout_seconds", float("nan")), ("api_key_env", "secret value"),
                           ("max_tokens", {"capability": 32, "direct": 16, "visible": 1600, "replay": 1600}),
                           ("extra", "not allowed")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                core.validate_config({**config(), key: value})


class PrefixGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan(config())
        cls.visible = [task for task in cls.plan["tasks"] if task["family"] == "base" and task["arm"] == "visible"]

    def test_capability_must_be_returned_valid_and_exact(self):
        self.assertEqual(core.capability_gate(self.plan, {})["status"], "incomplete")
        records = accepted_records(fixture(self.plan))
        self.assertEqual(core.capability_gate(self.plan, records)["status"], "pass")
        records["prefix-capability"]["capability_exact"] = False
        self.assertEqual(core.capability_gate(self.plan, records)["status"], "fail")

    def test_baseline_needs_four_pattern_errors_in_at_least_three_worlds(self):
        selected = [task["id"] for task in self.visible[:3]] + [self.visible[4]["id"]]
        records = accepted_records(fixture(self.plan, wrong_ids=selected))
        gate = core.phenomenon_gate(self.plan, records)
        self.assertEqual((gate["status"], gate["direct_correct"], gate["visible_correct"], gate["gap"]),
                         ("pass", 24, 20, 4))
        self.assertEqual((gate["visible_pattern_errors"], gate["visible_pattern_error_worlds"]), (4, 3))
        concentrated = accepted_records(fixture(self.plan, wrong_ids=[task["id"] for task in self.visible[:4]]))
        self.assertEqual(core.phenomenon_gate(self.plan, concentrated)["status"], "fail")
        three = accepted_records(fixture(self.plan, wrong_ids=selected[:3]))
        self.assertEqual(core.phenomenon_gate(self.plan, three)["status"], "fail")
        del records[self.visible[-1]["id"]]
        self.assertEqual(core.phenomenon_gate(self.plan, records)["status"], "incomplete")

    def test_direct_accuracy_floor_and_invalid_baseline_prevent_progress(self):
        all_pattern = [task["id"] for task in self.visible]
        base = [task for task in self.plan["tasks"] if task["family"] == "base" and task["arm"] == "direct"]
        pass_ids = all_pattern + [task["id"] for task in base[:4]]
        passing = accepted_records(fixture(self.plan, wrong_ids=pass_ids))
        self.assertEqual(core.phenomenon_gate(self.plan, passing)["status"], "pass")
        fail_ids = pass_ids + [base[4]["id"]]
        failing = accepted_records(fixture(self.plan, wrong_ids=fail_ids))
        gate = core.phenomenon_gate(self.plan, failing)
        self.assertEqual((gate["status"], gate["direct_correct"]), ("fail", 19))
        passing[base[-1]["id"]].update(status="invalid", answer=None)
        self.assertEqual(core.phenomenon_gate(self.plan, passing)["status"], "fail")

    def test_replay_requires_overall_fidelity_and_pattern_error_specific_fidelity(self):
        # Five pattern errors need ceil(.8 * 5) = four matching replays.
        wrong_ids = {task["id"] for task in self.visible[:5]}
        replays = [task for task in self.plan["tasks"] if task["family"] == "replay"]
        pattern_replays = [task for task in replays if task["parent_task_id"] in wrong_ids]
        other_replays = [task for task in replays if task["parent_task_id"] not in wrong_ids]
        changed = {pattern_replays[0]["id"]: core.task_meta(self.plan, pattern_replays[0])["expected"],
                   other_replays[0]["id"]: core.task_meta(self.plan, other_replays[0])["pattern_label"]}
        records = accepted_records(fixture(self.plan, wrong_ids=wrong_ids, changed_replays=changed))
        gate = core.replay_gate(self.plan, records)
        self.assertEqual((gate["status"], gate["answer_matches"], gate["pattern_error_matches"],
                          gate["required_pattern_error_matches"]), ("pass", 22, 4, 4))
        pattern_changed = {task["id"]: core.task_meta(self.plan, task)["expected"] for task in pattern_replays[:2]}
        records = accepted_records(fixture(self.plan, wrong_ids=wrong_ids, changed_replays=pattern_changed))
        gate = core.replay_gate(self.plan, records)
        self.assertEqual((gate["status"], gate["answer_matches"], gate["pattern_error_matches"]), ("fail", 22, 3))
        many_changed = {task["id"]: core.task_meta(self.plan, task)["pattern_label"] for task in other_replays[:3]}
        records = accepted_records(fixture(self.plan, wrong_ids=wrong_ids, changed_replays=many_changed))
        self.assertEqual(core.replay_gate(self.plan, records)["status"], "fail")
        del records[replays[-1]["id"]]
        self.assertEqual(core.replay_gate(self.plan, records)["status"], "incomplete")


class PrefixAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = core.make_plan(config())
        cls.wrong = [task["id"] for task in cls.plan["tasks"]
                     if task["family"] == "base" and task["arm"] == "visible"]

    def test_passing_feasibility_remains_a_diagnostic_and_mock_is_not_evidence(self):
        attempts = fixture(self.plan, wrong_ids=self.wrong)
        report, rows = summarize(self.plan, attempts)
        self.assertEqual(report["analysis_status"], "feasible_for_design_review")
        self.assertFalse(report["automatic_stage_2"])
        self.assertEqual((len(rows), report["replay_counts"]["n_exact_parent_answer_matches"]), (73, 24))
        self.assertEqual(report["replay_counts"]["n_wrong_to_wrong"], 24)
        self.assertEqual(report["replay_counts"]["n_wrong_to_correct"], 0)
        for measure in ("accuracy", "record_sensitivity"):
            effect = report["base_effects"][f"{measure}/direct_minus_visible"]
            self.assertEqual((effect["mean"], effect["n_worlds"]), (1, 12))
            self.assertEqual(effect["n_paired_cases"], 24)
        simulated, _ = summarize(self.plan, attempts, "mock")
        self.assertEqual(simulated["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertFalse(simulated["interpretation_allowed"])
        self.assertFalse(simulated["base_interpretation_allowed"])

    def test_all_correct_stopped_baseline_is_not_replay_failure(self):
        report, _ = summarize(self.plan, fixture(self.plan)[:49])
        self.assertEqual(report["analysis_status"], "phenomenon_not_reproduced_stop")
        self.assertEqual(report["replay_gate"]["status"], "incomplete")
        self.assertEqual(report["replay_counts"]["n_returned"], 0)
        self.assertEqual(report["base_effects"]["accuracy/direct_minus_visible"]["mean"], 0)

    def test_incomplete_or_invalid_answers_exclude_only_affected_worlds_and_withhold_science(self):
        attempts = fixture(self.plan)[:49]
        target = next(record for record in attempts if record["meta"]["arm"] == "visible")
        partial, _ = summarize(self.plan, [record for record in attempts if record is not target])
        effect = partial["base_effects"]["accuracy/direct_minus_visible"]
        self.assertEqual((effect["n_worlds"], effect["mean"]), (11, 0))
        self.assertIsNone(effect["full_plan_unscorable_bounds"])
        self.assertFalse(partial["interpretation_allowed"])
        task = next(task for task in self.plan["tasks"] if task["id"] == target["task_id"])
        result = response("unparseable")
        target.update(response=result, **core.score_response(task, result, target["meta"]))
        invalid, _ = summarize(self.plan, attempts)
        self.assertEqual(invalid["analysis_status"], "operational_invalid_stop")
        self.assertFalse(invalid["base_interpretation_allowed"])
        self.assertEqual(invalid["base_effects"]["accuracy/direct_minus_visible"]["full_plan_unscorable_bounds"], [0, 1 / 24])
        self.assertEqual(invalid["base_effects"]["record_sensitivity/direct_minus_visible"]["full_plan_unscorable_bounds"], [0, 1 / 12])


class PrefixRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return runner.run(config(), self.output, calls, mock=True, **kwargs)

    def test_all_correct_mock_stops_after49_and_is_never_evidence(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            result = self.invoke(100)
        self.assertEqual((result["calls_this_invocation"], result["attempts_total"]), (49, 49))
        self.assertTrue(result["is_simulated"])
        self.assertEqual(result["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertEqual(self.invoke(100, resume=True)["calls_this_invocation"], 0)
        plan, _, attempts = runner.read_run(self.output)
        self.assertEqual(core.phenomenon_gate(plan, accepted_records(attempts))["status"], "fail")
        self.assertTrue(all(record["meta"]["family"] != "replay" for record in attempts))

    def test_passing_synthetic_harm_resumes_from5_to_exactly73_immutable_calls(self):
        backend = PassingProvider(core.make_plan(config()))
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            first = self.invoke(5, complete_fn=backend)
            self.assertEqual(first["calls_this_invocation"], 5)
            before = {path.name: path.read_bytes() for path in (self.output / "attempts").glob("*.json")}
            final = self.invoke(100, resume=True, complete_fn=backend)
        self.assertEqual((final["calls_this_invocation"], final["attempts_total"]), (68, 73))
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        plan, _, attempts = runner.read_run(self.output)
        records = accepted_records(attempts)
        self.assertEqual(core.phenomenon_gate(plan, records)["status"], "pass")
        self.assertEqual(core.replay_gate(plan, records)["status"], "pass")
        self.assertEqual(core.replay_gate(plan, records)["answer_matches"], 24)
        self.assertEqual(self.invoke(100, resume=True, complete_fn=backend)["calls_this_invocation"], 0)

    def test_smoke_echo_is_retained_and_terminal_without_calling_baseline(self):
        result = self.invoke(100, complete_fn=lambda c, p: response("Cobalt Maple Lantern"))
        self.assertEqual(result["calls_this_invocation"], 1)
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        self.assertEqual(json.loads(before)["status"], "invalid")
        for retry in (False, True):
            with self.assertRaises(ValueError):
                self.invoke(100, resume=True, retry_errors=retry)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(list((self.output / "attempts").glob("*.json"))), 1)

    def test_model_change_or_reasoning_channel_leak_after_smoke_stops_and_is_not_retried(self):
        for bad_kind in ("model", "reasoning"):
            self.output = Path(self.temp.name) / bad_kind
            backend = PassingProvider(core.make_plan(config()))
            calls = []
            def changed(c, payload):
                result = backend(c, payload)
                calls.append(payload)
                if len(calls) == 1:
                    return result
                raw = copy.deepcopy(result["raw_response"])
                if bad_kind == "model":
                    raw["model"] = "changed-after-first-return"
                else:
                    raw["choices"][0]["message"]["reasoning_content"] = "unexpected hidden channel"
                return provider.normalize(raw)
            result = self.invoke(100, complete_fn=changed)
            self.assertEqual(result["calls_this_invocation"], 2)
            path = self.output / "attempts/000002.json"
            before = path.read_bytes()
            self.assertEqual(json.loads(before)["status"], "invalid")
            with self.assertRaises(ValueError):
                self.invoke(100, resume=True, retry_errors=True, complete_fn=changed)
            self.assertEqual(path.read_bytes(), before)

    def test_replay_cannot_be_inserted_before_baseline_gate(self):
        backend = PassingProvider(core.make_plan(config()))
        self.invoke(5, complete_fn=backend)
        plan, _, _ = runner.read_run(self.output)
        generated = fixture(plan, wrong_ids=[task["id"] for task in plan["tasks"]
                                            if task["family"] == "base" and task["arm"] == "visible"])
        replay = next(record for record in generated if record["meta"]["family"] == "replay")
        write_json(self.output / "attempts/000006.json", {**replay, "attempt": 6})
        with self.assertRaises(ValueError):
            runner.read_run(self.output)

    def test_transport_errors_are_retried_only_explicitly_and_cap_is89(self):
        def fail(c, p):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke(8, complete_fn=fail)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        blocked = self.invoke(8, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        record = json.loads(before)
        for number in range(2, 89):
            write_json(self.output / "attempts" / f"{number:06d}.json", {**record, "attempt": number})
        final = self.invoke(100, resume=True, retry_errors=True)
        self.assertEqual((final["stopped"], final["calls_this_invocation"], final["attempts_total"]),
                         ("total_attempt_limit", 1, 89))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.invoke(100, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_mode_source_plan_and_raw_response_integrity(self):
        self.invoke(5)
        with self.assertRaises(ValueError):
            self.invoke(1)
        with self.assertRaises(ValueError):
            runner.run(config(), self.output, 1, resume=True, mock=False)
        with self.assertRaises(ValueError):
            runner.run(config(), self.output, 1, complete_fn=lambda c, p: response("ple Lantern"))
        with patch.object(core, "source_digest", return_value="changed"):
            with self.assertRaises(ValueError):
                runner.read_run(self.output)
        plan_path = self.output / "plan.json"
        original_plan = json.loads(plan_path.read_text())
        changed_plan = copy.deepcopy(original_plan)
        changed_plan["worlds"][0]["roles"]["pattern"] = "Z"
        changed_plan["plan_hash"] = digest({key: value for key, value in changed_plan.items() if key != "plan_hash"})
        write_json(plan_path, changed_plan)
        with self.assertRaises(ValueError):
            runner.read_run(self.output)
        write_json(plan_path, original_plan)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["response"]["text"] = "Cobalt Maple Lantern"
        write_json(path, changed)
        with self.assertRaises(ValueError):
            runner.read_run(self.output)

    def test_replay_request_and_parent_mutation_are_detected_from_raw_journal(self):
        backend = PassingProvider(core.make_plan(config()))
        self.invoke(100, complete_fn=backend)
        paths = sorted((self.output / "attempts").glob("*.json"))
        replay_path = next(path for path in paths if json.loads(path.read_text())["meta"]["family"] == "replay")
        original_replay = json.loads(replay_path.read_text())
        changed = copy.deepcopy(original_replay)
        changed["request"]["messages"][-1]["content"] += " injected"
        write_json(replay_path, changed)
        with self.assertRaises(ValueError):
            runner.read_run(self.output)
        write_json(replay_path, original_replay)
        changed = copy.deepcopy(original_replay)
        changed["meta"]["prefix_text"] += " injected"
        write_json(replay_path, changed)
        with self.assertRaises(ValueError):
            runner.read_run(self.output)
        write_json(replay_path, original_replay)
        parent_path = next(path for path in paths if json.loads(path.read_text())["task_id"] == original_replay["meta"]["parent_task_id"])
        parent = json.loads(parent_path.read_text())
        # Consistently alter normalized and raw parent text; saved replay must still fail rebuilding.
        parent["response"]["text"] = "Extra early notes. " + parent["response"]["text"]
        parent["response"]["raw_response"]["choices"][0]["message"]["content"] = parent["response"]["text"]
        write_json(parent_path, parent)
        with self.assertRaises(ValueError):
            runner.read_run(self.output)


if __name__ == "__main__":
    unittest.main()
