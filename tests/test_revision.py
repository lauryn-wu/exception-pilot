"""Offline checks of the matched revision comparison and retained initial answers."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_cue.core import load_config as cue_config, make_plan as cue_plan
from exception_order.core import (
    load_config as order_config, make_plan as order_plan, request_for as order_request,
)
from exception_pilot import provider
from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_revision.analysis import summarize, write_summary
from exception_revision.core import (
    ARMS, VALUES, KEY_ORDERS, load_config, make_plan, messages_for, request_for,
    score_response, task_meta, validate_config,
)
from exception_revision.runner import mock_complete, normalized_response, prepare, read_run, run


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = "accuracy/repeat_control_minus_revision"
ANCHOR = "accuracy/answer_first_minus_reasoning_first"
NEW_ARMS = ("revision", "repeat_control")


def config():
    return load_config(ROOT / "configs/revision.json")


def response(text, finish="stop"):
    return provider.normalize({
        "id": "fixture", "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
    })


def answer_response(arm, final, initial=None, reasoning="The recorded class is used."):
    values = {"answer": final, "initial_answer": initial if initial is not None else final,
              "final_answer": final, "reasoning": reasoning}
    return response(json.dumps({key: values[key] for key in KEY_ORDERS[arm]}))


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


class RevisionDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_fixed_balanced_fresh_worlds_and_eight_paired_tasks_each(self):
        plan = self.plan
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual((len(plan["worlds"]), len(plan["tasks"])), (24, 192))
        self.assertEqual(len({task["id"] for task in plan["tasks"]}), 192)
        plates = {item["id"] for world in plan["worlds"] for item in world["items"]}
        self.assertEqual(len(plates), 240)
        for previous in (cue_plan(cue_config(ROOT / "configs/cue.json")),
                         order_plan(order_config(ROOT / "configs/order.json"))):
            self.assertFalse(plates & {item["id"] for w in previous["worlds"] for item in w["items"]})
            self.assertFalse({w["id"] for w in plan["worlds"]} & {w["id"] for w in previous["worlds"]})
        roles = Counter(tuple(w["roles"].values()) for w in plan["worlds"])
        self.assertEqual((len(roles), set(roles.values())), (6, {4}))
        climate_roles = Counter((tuple(w["roles"].values()), w["items"][w["target_index"]]["climate"])
                               for w in plan["worlds"])
        self.assertEqual((len(climate_roles), set(climate_roles.values())), (12, {2}))
        schedules = []
        for world in plan["worlds"]:
            tasks = [t for t in plan["tasks"] if t["world_id"] == world["id"]]
            self.assertEqual(Counter((t["value"], t["arm"]) for t in tasks),
                             Counter(itertools.product(VALUES, ARMS)))
            schedules.append(tuple((t["value"], t["arm"]) for t in tasks))
            target = world["target_index"]
            peers = [i for i, item in enumerate(world["items"]) if i != target
                     and item["climate"] == world["items"][target]["climate"]]
            for value in VALUES:
                self.assertEqual(world["record_labels"][value][target], world["roles"][value])
                self.assertEqual([world["record_labels"][value][i] for i in peers],
                                 [world["roles"]["pattern"]] * 4)
        self.assertGreater(len(set(schedules)), 1)

    def test_record_variants_change_only_the_target_class_cell(self):
        for world in self.plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in ARMS:
                task = {"world_id": world["id"], "family": "diagnostic", "arm": arm, "value": "record_1"}
                first = messages_for(self.plan, task)[0]["content"].splitlines()
                second = messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
                self.assertEqual(len(first), len(second))
                different = [(a, b) for a, b in zip(first, second) if a != b]
                self.assertEqual(len(different), 1)
                a, b = different[0]
                self.assertIn(target_id, a)
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_anchors_exactly_preserve_old_order_requests_on_new_worlds(self):
        for task in self.plan["tasks"]:
            for arm in ("reasoning_first", "answer_first"):
                anchor = {**task, "arm": arm}
                self.assertEqual(json.dumps(request_for(self.plan, anchor)),
                                 json.dumps(order_request(self.plan, anchor)))

    def test_new_pair_differs_only_in_schema_property_order_and_budgets_match(self):
        for task in self.plan["tasks"]:
            revision = request_for(self.plan, {**task, "arm": "revision"})
            repeat = request_for(self.plan, {**task, "arm": "repeat_control"})
            self.assertEqual(revision, repeat)
            self.assertEqual(revision["messages"], repeat["messages"])
            self.assertNotEqual(json.dumps(revision), json.dumps(repeat))
            schemas = [r["response_format"]["json_schema"]["schema"] for r in (revision, repeat)]
            self.assertEqual(list(schemas[0]["properties"]), ["initial_answer", "reasoning", "final_answer"])
            self.assertEqual(list(schemas[1]["properties"]), ["initial_answer", "final_answer", "reasoning"])
            self.assertEqual(schemas[0]["required"], schemas[1]["required"])
            self.assertEqual(set(schemas[0]["required"]), {"initial_answer", "reasoning", "final_answer"})
            schemas[1]["properties"] = {key: schemas[1]["properties"][key] for key in schemas[0]["properties"]}
            self.assertEqual(json.dumps(revision), json.dumps(repeat))
            for arm in ARMS:
                request = request_for(self.plan, {**task, "arm": arm})
                self.assertEqual(len(request["messages"]), 1)
                self.assertEqual(request["messages"][0]["role"], "user")
                self.assertEqual((request["model"], request["temperature"], request["n"], request["store"]),
                                 ("gpt-4o-2024-08-06", 0, 1, False))
                self.assertEqual(request["max_completion_tokens"], 1000)
                self.assertTrue(request["response_format"]["json_schema"]["strict"])
                self.assertFalse(request["response_format"]["json_schema"]["schema"]["additionalProperties"])
                self.assertNotIn(task["world_id"], request["messages"][0]["content"])
                self.assertNotIn("expected", request)
                self.assertNotIn("api_key_env", request)

    def test_frozen_config_rejects_outcome_dependent_or_unequal_budgets(self):
        changes = (("protocol", "other"), ("seed", 2026100893), ("n_worlds", 12),
                   ("n_worlds", True), ("model", "gpt-4o"), ("temperature", True),
                   ("max_total_attempts", 225), ("timeout_seconds", float("nan")),
                   ("api_key_env", "secret value"), ("extra", "not allowed"),
                   ("max_completion_tokens", {arm: 16 if arm == "revision" else 1000 for arm in ARMS}),
                   ("max_completion_tokens", {arm: 1000.0 for arm in ARMS}))
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({**config(), key: value})

    def test_every_initial_final_combination_is_valid_and_only_final_is_scored(self):
        for arm in NEW_ARMS:
            for initial, final in itertools.product("ABC", repeat=2):
                scored = score_response({"arm": arm}, answer_response(
                    arm, final, initial, "Actually choose something else: ANSWER: B.  "))
                self.assertEqual((scored["initial_answer"], scored["final_answer"], scored["answer"]),
                                 (initial, final, final))
                self.assertEqual((scored["status"], scored["schema_valid"], scored["key_order_valid"]),
                                 ("complete", True, True))
                self.assertTrue(scored["reasoning_nonempty"])
                self.assertEqual(scored["reasoning_words"], 6)
                self.assertEqual(scored["reasoning_chars"], len("Actually choose something else: ANSWER: B."))
                self.assertIsNone(scored["invalid_reason"])
        for arm in ("reasoning_first", "answer_first"):
            for final in "ABC":
                scored = score_response({"arm": arm}, answer_response(arm, final))
                self.assertEqual((scored["initial_answer"], scored["final_answer"], scored["answer"]),
                                 (None, final, final))
                self.assertEqual(scored["status"], "complete")

    def test_malformed_answers_empty_reasoning_duplicates_and_wrong_order_are_invalid(self):
        for arm in ARMS:
            texts = ['null', '[]', '{}', '"A"', 'NaN', '```json\n{}\n```', '{} trailing', '{}{}']
            valid = json.loads(answer_response(arm, "A", "B")["text"])
            for key in ("initial_answer", "final_answer") if arm in NEW_ARMS else ("answer",):
                for value in (None, True, 2, "a", "D", "AB"):
                    texts.append(json.dumps({**valid, key: value}))
                texts.append(json.dumps({key_: value for key_, value in valid.items() if key_ != key}))
                text = json.dumps(valid)
                texts.append(text[:-1] + ', "' + key + '": "A"}')
            for value in (None, 3, [], {}, True, "", " \n\t "):
                texts.append(json.dumps({**valid, "reasoning": value}))
            texts.append(json.dumps({**valid, "extra": "A"}))
            texts.append(json.dumps(dict(reversed(list(valid.items())))))
            for text in texts:
                with self.subTest(arm=arm, text=text):
                    scored = score_response({"arm": arm}, response(text))
                    self.assertEqual(scored["status"], "invalid")
                    self.assertTrue(scored["invalid_reason"])
                    self.assertEqual((scored["initial_answer"], scored["final_answer"], scored["answer"]),
                                     (None, None, None))
        for arm, other in (("revision", "repeat_control"), ("repeat_control", "revision")):
            scored = score_response({"arm": arm}, answer_response(other, "A", "B"))
            self.assertEqual((scored["schema_valid"], scored["key_order_valid"], scored["status"]),
                             (True, False, "invalid"))

    def test_valid_json_never_overrides_refusal_truncation_or_model_mismatch(self):
        for arm in ARMS:
            raw = answer_response(arm, "A", "B")["raw_response"]
            cases = [normalized_response(raw, config(), "live"), response(answer_response(arm, "A")["text"], "length")]
            refused = copy.deepcopy(raw)
            refused["model"] = config()["model"]
            refused["choices"][0]["message"]["refusal"] = "declined"
            cases.append(normalized_response(refused, config(), "live"))
            for result in cases:
                scored = score_response({"arm": arm}, result)
                self.assertEqual((scored["initial_answer"], scored["final_answer"], scored["answer"]),
                                 (None, None, None))
                self.assertEqual((scored["status"], scored["invalid_reason"]), ("invalid", "provider_incomplete"))


class RevisionAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_mock_is_not_evidence_and_all_correct_effects_are_zero(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertTrue(report["is_simulated"])
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual((len(rows), report["valid_answers"], report["invalid_answers"]), (192, 192, 0))
        for contrast in (PRIMARY, ANCHOR):
            effect = report["effects"][contrast]
            self.assertEqual((effect["mean"], effect["n_worlds"]), (0, 24))
            self.assertEqual(effect["descriptive_cluster_bootstrap_95_ci"], [0, 0])
        for arm in ARMS:
            self.assertEqual(report["effects"][f"accuracy/{arm}"]["mean"], 1)
        for counts in report["revision_counts"]:
            self.assertEqual((counts["n_valid"], counts["n_correct_to_correct"], counts["n_answer_unchanged"]),
                             (48, 48, 48))

    def test_known_transitions_use_final_answers_and_all_paired_worlds(self):
        indexes = {w["id"]: i for i, w in enumerate(self.plan["worlds"])}
        def choose(task, result):
            if task["arm"] not in NEW_ARMS:
                return result
            meta = task_meta(self.plan, task)
            gold, pattern = meta["expected"], meta["pattern_label"]
            other = next(label for label in "ABC" if label not in (gold, pattern))
            group = indexes[task["world_id"]] % 4
            initial = (gold, gold, pattern, other)[group]
            finals = ((gold, pattern, gold, pattern) if task["arm"] == "revision"
                      else (gold, gold, pattern, gold))
            return answer_response(task["arm"], finals[group], initial)
        report, rows = summarize(self.plan, fixture(self.plan, choose))
        self.assertEqual(report["analysis_status"], "complete_ready_for_interpretation")
        self.assertTrue(report["interpretation_allowed"])
        self.assertEqual(report["primary_effect"], PRIMARY)
        effect = report["effects"][PRIMARY]
        self.assertEqual((effect["mean"], effect["n_worlds"], effect["n_paired_cases"]), (0.25, 24, 48))
        # Filtering to initially correct answers would instead produce 0.5.
        self.assertNotEqual(effect["mean"], 0.5)
        self.assertEqual((effect["paired_improved_cases"], effect["paired_worsened_cases"],
                          effect["paired_unchanged_cases"]), (24, 12, 12))
        counts = {row["arm"]: row for row in report["revision_counts"]}
        revision = counts["revision"]
        self.assertEqual((revision["n_valid"], revision["n_initial_correct"], revision["n_final_correct"]), (48, 24, 24))
        self.assertEqual([revision[key] for key in ("n_correct_to_correct", "n_correct_to_wrong", "n_wrong_to_correct", "n_wrong_to_wrong")], [12] * 4)
        self.assertEqual((revision["n_answer_changed"], revision["n_answer_unchanged"], revision["n_correct_to_pattern"]), (36, 12, 12))
        self.assertEqual(revision["transition_matrix"], {
            "gold": {"gold": 12, "pattern": 12, "other": 0},
            "pattern": {"gold": 12, "pattern": 0, "other": 0},
            "other": {"gold": 0, "pattern": 12, "other": 0},
        })
        self.assertEqual((counts["repeat_control"]["n_initial_correct"], counts["repeat_control"]["n_final_correct"]), (24, 36))
        for row in rows:
            self.assertEqual(row["answer"], row["final_answer"])
            self.assertEqual(row["correct"], row["final_correct"])
            if row["arm"] not in NEW_ARMS:
                self.assertIsNone(row["initial_answer"])
                self.assertIsNone(row["initial_correct"])

    def test_anchor_effect_remains_separate_from_primary(self):
        def choose(task, result):
            return (answer_response(task["arm"], task_meta(self.plan, task)["pattern_label"])
                    if task["arm"] == "reasoning_first" else result)
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        self.assertEqual(report["effects"][PRIMARY]["mean"], 0)
        self.assertEqual(report["effects"][ANCHOR]["mean"], 1)
        self.assertEqual(report["effects"][ANCHOR]["role"], "secondary")

    def test_incomplete_primary_world_is_excluded_without_dropping_anchor_world(self):
        records = fixture(self.plan)
        missing = next(record for record in records if record["meta"]["arm"] == "revision")
        report, _ = summarize(self.plan, [record for record in records if record is not missing])
        self.assertEqual((report["analysis_status"], report["pending_tasks"]), ("incomplete", 1))
        self.assertFalse(report["interpretation_allowed"])
        effect = report["effects"][PRIMARY]
        self.assertEqual((effect["n_worlds"], effect["mean"]), (23, 0))
        self.assertEqual(effect["excluded_world_ids"], [missing["meta"]["world_id"]])
        self.assertIsNone(effect["full_plan_unscorable_bounds"])
        self.assertEqual(report["effects"][ANCHOR]["n_worlds"], 24)
        counts = next(row for row in report["revision_counts"] if row["arm"] == "revision")
        self.assertEqual((counts["n_valid"], counts["n_pending"]), (47, 1))

    def test_invalid_order_withholds_interpretation_and_keeps_transition_denominators(self):
        target = next(task for task in self.plan["tasks"] if task["arm"] == "revision")
        def choose(task, result):
            return (answer_response("repeat_control", task_meta(self.plan, task)["expected"])
                    if task["id"] == target["id"] else result)
        records = fixture(self.plan, choose)
        report, rows = summarize(self.plan, records)
        self.assertEqual(report["analysis_status"], "technical_failure_output_manipulation")
        self.assertTrue(report["output_manipulation_failed"])
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual(report["valid_answers"], 191)
        invalid = next(row for row in rows if row["task_id"] == target["id"])
        for key in ("answer", "initial_answer", "final_answer", "correct", "initial_correct", "final_correct"):
            self.assertIsNone(invalid[key])
        self.assertEqual(report["effects"][PRIMARY]["n_worlds"], 23)
        self.assertEqual(report["effects"][PRIMARY]["full_plan_unscorable_bounds"], [0, 1 / 48])
        counts = next(row for row in report["revision_counts"] if row["arm"] == "revision")
        self.assertEqual((counts["n_planned"], counts["n_returned"], counts["n_valid"], counts["n_invalid"]), (48, 48, 47, 1))
        self.assertEqual(sum(sum(values.values()) for values in counts["transition_matrix"].values()), 47)
        with tempfile.TemporaryDirectory() as output:
            write_summary(output, self.plan, records)
            text = (Path(output) / "summary.md").read_text()
            self.assertIn("output manipulation failed", text)


class RevisionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return run(config(), self.output, calls, mock=True, **kwargs)

    def test_prepare_is_offline_and_preserves_serialized_order(self):
        with run_lock(self.output), patch.object(provider, "complete", side_effect=AssertionError("no network")), \
             patch.object(provider, "credential", side_effect=AssertionError("no key access")):
            plan = prepare(config(), self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 192)
        for row, task in zip(preview, plan["tasks"]):
            self.assertEqual(json.dumps(row["request"]), json.dumps(request_for(plan, task)))
        self.assertFalse((self.output / "execution.json").exists())

    def test_mock_resume_finishes_192_without_network_or_overwriting_returns(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("key access forbidden")):
            first = self.invoke(8)
            self.assertEqual((first["calls_this_invocation"], first["valid_answers"]), (8, 8))
            before = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
            final = self.invoke(192, resume=True)
        self.assertEqual((final["calls_this_invocation"], final["valid_answers"], final["stopped"]), (184, 192, "complete"))
        self.assertEqual(final["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(self.invoke(1, resume=True)["calls_this_invocation"], 0)

    def test_returned_invalidity_is_retained_and_never_resampled(self):
        result = self.invoke(8, complete_fn=lambda c, p: response('{"initial_answer":"A","final_answer":"D"}'))
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
                         '{"initial_answer":"A","final_answer":"D"}')
        write_json(self.output / "attempts/000002.json", fixture(plan)[1])
        with self.assertRaisesRegex(ValueError, "after a returned invalid"):
            read_run(self.output)

    def test_valid_initial_final_disagreement_and_wrong_answers_are_retained(self):
        plan = make_plan(config())
        by_request = {json.dumps(request_for(plan, task)): task for task in plan["tasks"]}
        def wrong(c, payload):
            task = by_request[json.dumps(payload)]
            meta = task_meta(plan, task)
            return answer_response(task["arm"], meta["pattern_label"], meta["expected"])
        result = self.invoke(8, complete_fn=wrong)
        self.assertEqual((result["calls_this_invocation"], result["valid_answers"]), (8, 8))
        _, _, attempts = read_run(self.output)
        self.assertEqual(len({row["task_id"] for row in attempts}), 8)
        for attempt in attempts:
            self.assertEqual(attempt["answer"], attempt["meta"]["pattern_label"])
            if attempt["meta"]["arm"] in NEW_ARMS:
                self.assertEqual(attempt["initial_answer"], attempt["meta"]["expected"])
                self.assertNotEqual(attempt["initial_answer"], attempt["final_answer"])
        before = (self.output / "attempts/000001.json").read_bytes()
        self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), before)

    def test_transport_retry_requires_flag_and_preserves_failed_attempt(self):
        def failure(c, payload):
            raise provider.ProviderError("TimeoutError")
        first = self.invoke(8, complete_fn=failure)
        self.assertEqual((first["stopped"], first["calls_this_invocation"]), ("provider_error", 1))
        before = (self.output / "attempts/000001.json").read_bytes()
        blocked = self.invoke(8, resume=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        success = self.invoke(1, resume=True, retry_errors=True)
        self.assertEqual((success["attempts_total"], success["valid_answers"]), (2, 1))
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), before)

    def test_interruption_is_journaled_and_224_attempt_cap_includes_retries(self):
        def interrupt(c, payload):
            saved = json.loads((self.output / "attempts/000001.json").read_text())
            self.assertEqual(saved["status"], "started")
            self.assertEqual(json.dumps(saved["request"]), json.dumps(payload))
            raise KeyboardInterrupt
        self.assertEqual(self.invoke(8, complete_fn=interrupt)["stopped"], "interrupted")
        self.assertEqual(self.invoke(1, resume=True)["stopped"], "retry_requires_flag")
        first = json.loads((self.output / "attempts/000001.json").read_text())
        for number in range(2, 224):
            write_json(self.output / "attempts" / f"{number:06d}.json", {**first, "attempt": number})
        last = self.invoke(192, resume=True, retry_errors=True)
        self.assertEqual((last["stopped"], last["calls_this_invocation"], last["attempts_total"]),
                         ("total_attempt_limit", 1, 224))
        self.assertEqual(self.invoke(192, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_request_audit_detects_schema_order_change_despite_dictionary_equality(self):
        self.invoke(8)
        path = next(p for p in sorted((self.output / "attempts").glob("*.json"))
                    if json.loads(p.read_text())["meta"]["arm"] == "revision")
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        schema = changed["request"]["response_format"]["json_schema"]["schema"]
        schema["properties"] = {key: schema["properties"][key]
                                for key in ("initial_answer", "final_answer", "reasoning")}
        self.assertEqual(changed["request"], original["request"])
        self.assertNotEqual(json.dumps(changed["request"]), json.dumps(original["request"]))
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            read_run(self.output)

    def test_raw_answer_order_and_initial_final_scoring_tampering_are_detected(self):
        self.invoke(8)
        path = next(p for p in sorted((self.output / "attempts").glob("*.json"))
                    if json.loads(p.read_text())["meta"]["arm"] == "revision")
        original = json.loads(path.read_text())
        for field in ("text", "raw_order", "initial_answer", "final_answer", "answer", "key_order_valid"):
            changed = copy.deepcopy(original)
            if field == "text":
                changed["response"]["text"] = "tampered"
            elif field == "raw_order":
                value = json.loads(changed["response"]["text"])
                reordered = json.dumps({key: value[key] for key in ("initial_answer", "final_answer", "reasoning")})
                changed["response"]["text"] = reordered
                changed["response"]["raw_response"]["choices"][0]["message"]["content"] = reordered
            elif field == "key_order_valid":
                changed[field] = False
            else:
                changed[field] = next(letter for letter in "ABC" if letter != changed[field])
            write_json(path, changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                read_run(self.output)
        write_json(path, original)
        read_run(self.output)

    def test_plan_source_identity_duplicate_returns_and_schedule_are_audited(self):
        self.invoke(2)
        with self.assertRaisesRegex(ValueError, "resume"):
            self.invoke(1)
        with self.assertRaisesRegex(ValueError, "identity"):
            run(config(), self.output, 1, resume=True, mock=False)
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(), self.output, 1, complete_fn=lambda c, p: answer_response("revision", "A"))
        with patch("exception_revision.core.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                self.invoke(1, resume=True)
        plan_path = self.output / "plan.json"
        original_plan = json.loads(plan_path.read_text())
        changed_plan = copy.deepcopy(original_plan)
        changed_plan["worlds"][0]["roles"]["pattern"] = "Z"
        changed_plan["plan_hash"] = digest({key: value for key, value in changed_plan.items() if key != "plan_hash"})
        write_json(plan_path, changed_plan)
        with self.assertRaisesRegex(ValueError, "Code or saved plan"):
            read_run(self.output)
        write_json(plan_path, original_plan)
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
