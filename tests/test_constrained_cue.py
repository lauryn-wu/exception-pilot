"""Offline checks of the constrained-cue manipulation, estimands, and journal."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_cue.core import load_config as load_cue_config, make_plan as make_cue_plan
from exception_cue.core import messages_for as cue_messages
from exception_pilot import provider
from exception_pilot.storage import run_lock, write_json
from exception_constrained_cue.analysis import summarize, write_summary
from exception_constrained_cue.core import (
    ARMS, VALUES, load_config, make_plan, messages_for, request_for,
    score_response, task_meta, validate_config,
)
from exception_constrained_cue.runner import (
    mock_complete, normalized_response, prepare, read_run, run,
)

ROOT = Path(__file__).resolve().parents[1]


def config():
    return load_config(ROOT / "configs/constrained_cue.json")


def response(text, finish="stop"):
    return provider.normalize({
        "id": "fixture", "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text},
                     "finish_reason": finish}],
    })


def answer_response(answer):
    return response(json.dumps({"answer": answer}))


def fixture(plan, choose=None):
    """Synthetic records for arithmetic tests; never saved as a live execution."""
    records = []
    for task in plan["tasks"]:
        result = mock_complete(plan, task)
        if choose is not None:
            result = choose(task, result)
        records.append({
            "attempt": len(records) + 1, "task_id": task["id"],
            "plan_hash": plan["plan_hash"], "mode": "mock",
            "request": request_for(plan, task), "meta": task_meta(plan, task),
            "response": result, **score_response(task, result),
        })
    return records


class ConstrainedCueDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_frozen_cue_worlds_and_balanced_96_call_design(self):
        plan = self.plan
        original = make_cue_plan(load_cue_config(ROOT / "configs/cue.json"))
        self.assertEqual(plan["worlds"], original["worlds"])
        self.assertEqual(plan, make_plan(config()))
        self.assertEqual(len(plan["worlds"]), 24)
        self.assertEqual(len(plan["tasks"]), 96)
        self.assertEqual(len({task["id"] for task in plan["tasks"]}), 96)
        plates = [item["id"] for world in plan["worlds"] for item in world["items"]]
        self.assertEqual(len(set(plates)), 240)
        roles = Counter(tuple(world["roles"].values()) for world in plan["worlds"])
        self.assertEqual(len(roles), 6)
        self.assertEqual(set(roles.values()), {4})
        assignments = Counter(
            (tuple(world["roles"].values()), world["items"][world["target_index"]]["climate"])
            for world in plan["worlds"]
        )
        self.assertEqual(set(assignments.values()), {2})
        schedules = []
        for world in plan["worlds"]:
            tasks = [task for task in plan["tasks"] if task["world_id"] == world["id"]]
            self.assertEqual(Counter((task["value"], task["arm"]) for task in tasks),
                             Counter((value, arm) for value in VALUES for arm in ARMS))
            schedules.append(tuple((task["value"], task["arm"]) for task in tasks))
        self.assertGreater(len(set(schedules)), 1)

    def test_paired_variants_change_only_the_target_class_cell(self):
        for world in self.plan["worlds"]:
            target_id = world["items"][world["target_index"]]["id"]
            for arm in ARMS:
                task = {"world_id": world["id"], "family": "diagnostic", "arm": arm,
                        "value": "record_1"}
                first = messages_for(self.plan, task)[0]["content"].splitlines()
                second = messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
                self.assertEqual(len(first), len(second))
                changes = [(a, b) for a, b in zip(first, second) if a != b]
                self.assertEqual(len(changes), 1)
                a, b = changes[0]
                self.assertIn(target_id, a)
                self.assertEqual(a.rsplit(" | ", 1)[0], b.rsplit(" | ", 1)[0])

    def test_exact_single_phrase_manipulation_and_identical_strict_schema(self):
        expected_format = {
            "type": "json_schema",
            "json_schema": {"name": "class_answer", "strict": True, "schema": {
                "type": "object", "properties": {"answer": {"type": "string", "enum": ["A", "B", "C"]}},
                "required": ["answer"], "additionalProperties": False,
            }},
        }
        ending = 'Output only a JSON object with one field, "answer", whose value is A, B, or C.'
        for task in self.plan["tasks"]:
            req = request_for(self.plan, task)
            direct = request_for(self.plan, {**task, "arm": "direct"})
            cue = request_for(self.plan, {**task, "arm": "cue"})
            body = direct["messages"][0]["content"].rsplit("\n", 1)[0]
            original_body = cue_messages(self.plan, task)[0]["content"].rsplit("\n", 1)[0]
            self.assertEqual(body, original_body)
            self.assertIn("MISSING means the verified class has not been recorded.", body)
            self.assertEqual(direct["messages"], [{"role": "user", "content": body + "\n" + ending}])
            self.assertEqual(cue["messages"], [{"role": "user", "content": body + "\nThink step by step before answering. " + ending}])
            direct.pop("messages")
            cue.pop("messages")
            self.assertEqual(direct, cue)
            self.assertEqual(req["response_format"], expected_format)
            self.assertEqual(req["max_completion_tokens"], 1000)
            self.assertEqual(req["model"], "gpt-4o-2024-08-06")
            self.assertEqual((req["temperature"], req["n"], req["store"]), (0, 1, False))
            self.assertNotIn("expected", req)
            self.assertNotIn("api_key_env", req)
            self.assertNotIn("cue-list", req["messages"][0]["content"])
        req["response_format"]["json_schema"]["schema"]["properties"]["answer"]["enum"].append("D")
        self.assertEqual(request_for(self.plan, self.plan["tasks"][0])["response_format"], expected_format)

    def test_config_prevents_changing_the_frozen_experiment(self):
        for key, value in (
            ("protocol", "verified-facts-cue-v1"), ("seed", 2026100893), ("n_worlds", 30),
            ("n_worlds", True), ("model", "gpt-4o"), ("temperature", True),
            ("max_completion_tokens", {"direct": 16, "cue": 1000}),
            ("max_completion_tokens", {"direct": 1000.0, "cue": 1000}),
            ("max_total_attempts", 113), ("timeout_seconds", float("nan")),
            ("api_key_env", "secret value"), ("extra", "not allowed"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_config({**config(), key: value})

    def test_schema_parser_accepts_only_one_json_answer_field(self):
        for arm in ARMS:
            for label in "ABC":
                self.assertEqual(score_response({"arm": arm}, response(' \n {"answer": "' + label + '"}\t')),
                                 {"answer": label, "status": "complete", "schema_valid": True, "invalid_reason": None})
            invalid = (
                '{"answer":"A","reasoning":"because"}', '{"answer":"A","answer":"B"}',
                '{"answer":"A","answer":"A"}', '{}', '{"Answer":"A"}',
                'Reasoning first. {"answer":"A"}', '```json\n{"answer":"A"}\n```',
                '{"answer":"A"} trailing', '{"answer":"A"}{"answer":"B"}',
                '{"answer":"a"}', '{"answer":"D"}', '{"answer":null}',
                '{"answer":true}', '{"answer":["A"]}', '{"answer":NaN}',
                '[{"answer":"A"}]', 'null', '"A"', '{"answer":"A",}',
            )
            for text in invalid:
                with self.subTest(arm=arm, text=text):
                    scored = score_response({"arm": arm}, response(text))
                    self.assertEqual((scored["answer"], scored["status"], scored["schema_valid"]),
                                     (None, "invalid", False))
                    self.assertTrue(scored["invalid_reason"])
        duplicate = score_response({}, response('{"answer":"A","answer":"B"}'))
        self.assertEqual(duplicate["invalid_reason"], "duplicate_json_key")

    def test_valid_looking_json_cannot_override_provider_failure(self):
        raw = answer_response("A")["raw_response"]
        cases = [normalized_response(raw, config(), "live"), response('{"answer":"A"}', "length")]
        raw = copy.deepcopy(raw)
        raw["model"] = config()["model"]
        raw["choices"][0]["message"]["refusal"] = "declined"
        cases.append(normalized_response(raw, config(), "live"))
        for result in cases:
            self.assertFalse(result["complete"])
            self.assertEqual(score_response({}, result), {
                "answer": None, "status": "invalid", "schema_valid": False,
                "invalid_reason": "provider_incomplete",
            })
        self.assertEqual(cases[0]["finish_reason"], "model_mismatch")


class ConstrainedCueAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_all_correct_mock_has_zero_contrast_and_is_not_evidence(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertTrue(report["is_simulated"])
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual((len(rows), report["schema_valid_answers"], report["invalid_answers"]), (96, 96, 0))
        for measure in ("accuracy", "record_sensitivity"):
            self.assertEqual(report["effects"][f"{measure}/direct_minus_cue"]["mean"], 0)
            self.assertEqual(report["effects"][f"{measure}/direct_minus_cue"]["n_worlds"], 24)
            for arm in ARMS:
                self.assertEqual(report["effects"][f"{measure}/{arm}"]["mean"], 1)

    def test_pattern_constant_and_reversed_choices_have_known_paired_estimands(self):
        worlds = {world["id"]: world for world in self.plan["worlds"]}
        for behavior, accuracy, sensitivity in (("pattern", 0, 0), ("constant", 0.5, 0), ("reverse", 0, -1)):
            def choose(task, result):
                if task["arm"] != "cue":
                    return result
                roles = worlds[task["world_id"]]["roles"]
                key = ("pattern" if behavior == "pattern" else "record_1" if behavior == "constant"
                       or task["value"] == "record_2" else "record_2")
                return answer_response(roles[key])
            with self.subTest(behavior=behavior):
                report, _ = summarize(self.plan, fixture(self.plan, choose))
                self.assertEqual(report["analysis_status"], "complete_ready_for_interpretation")
                self.assertTrue(report["interpretation_allowed"])
                self.assertEqual(report["effects"]["accuracy/cue"]["mean"], accuracy)
                self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["mean"], 1 - accuracy)
                self.assertEqual(report["effects"]["record_sensitivity/cue"]["mean"], sensitivity)
                self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cue"]["mean"], 1 - sensitivity)
                self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["n_worlds"], 24)

    def test_incomplete_results_exclude_unpaired_worlds_and_withhold_bounds(self):
        records = fixture(self.plan)
        target = "cue-list-000/record_1/cue"
        report, _ = summarize(self.plan, [record for record in records if record["task_id"] != target])
        self.assertEqual(report["analysis_status"], "incomplete")
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual(report["pending_tasks"], 1)
        for measure in ("accuracy", "record_sensitivity"):
            contrast = report["effects"][f"{measure}/direct_minus_cue"]
            self.assertEqual((contrast["n_worlds"], contrast["mean"]), (23, 0))
            self.assertEqual(contrast["excluded_world_ids"], ["cue-list-000"])
            self.assertIsNone(contrast["full_plan_unscorable_bounds"])
            self.assertEqual(report["effects"][f"{measure}/direct"]["n_worlds"], 24)

    def test_one_invalid_output_fails_manipulation_and_keeps_audit_bounds(self):
        target = "cue-list-000/record_1/cue"
        records = fixture(self.plan, lambda task, result: response('Here is {"answer":"A"}')
                          if task["id"] == target else result)
        report, rows = summarize(self.plan, records)
        self.assertEqual(report["analysis_status"], "technical_failure_output_manipulation")
        self.assertFalse(report["interpretation_allowed"])
        self.assertTrue(report["output_manipulation_failed"])
        self.assertEqual(report["invalid_reason_counts"], {"invalid_json": 1})
        self.assertEqual(report["valid_answers"], 95)
        self.assertIsNone(next(row for row in rows if row["task_id"] == target)["correct"])
        self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["full_plan_unscorable_bounds"], [0, 1 / 48])
        self.assertEqual(report["effects"]["record_sensitivity/direct_minus_cue"]["full_plan_unscorable_bounds"], [0, 1 / 24])
        self.assertEqual(report["effects"]["accuracy/direct_minus_cue"]["n_worlds"], 23)
        partial, _ = summarize(self.plan, [next(record for record in records if record["task_id"] == target)])
        self.assertEqual(partial["analysis_status"], "technical_failure_output_manipulation")
        self.assertIsNone(partial["effects"]["accuracy/direct_minus_cue"]["full_plan_unscorable_bounds"])
        with tempfile.TemporaryDirectory() as output:
            write_summary(output, self.plan, records)
            markdown = (Path(output) / "summary.md").read_text()
            self.assertIn("output manipulation failed", markdown)
            self.assertNotIn("## Primary paired accuracy contrast", markdown)


class ConstrainedCueRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"

    def invoke(self, calls, **kwargs):
        with redirect_stdout(io.StringIO()):
            return run(config(), self.output, calls, mock=True, **kwargs)

    def test_offline_preview_contains_all_exact_requests_and_protects_old_results(self):
        with run_lock(self.output), patch.object(provider, "complete", side_effect=AssertionError("no network")), \
             patch.object(provider, "credential", side_effect=AssertionError("no key access")):
            plan = prepare(config(), self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 96)
        self.assertEqual([row["request"] for row in preview], [request_for(plan, task) for task in plan["tasks"]])
        self.assertFalse((self.output / "execution.json").exists())
        old = Path(self.temp.name) / "old"
        with run_lock(old):
            (old / "summary.md").write_text("old results")
            with self.assertRaisesRegex(ValueError, "not empty"):
                prepare(config(), old)

    def test_mock_resume_never_calls_network_or_overwrites_returned_answers(self):
        with patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("key access forbidden")):
            first = self.invoke(6)
            self.assertEqual(first["calls_this_invocation"], 6)
            before = {path.name: path.read_bytes() for path in (self.output / "attempts").glob("*.json")}
            result = self.invoke(96, resume=True)
        self.assertEqual((result["calls_this_invocation"], result["stopped"], result["valid_answers"]), (90, "complete", 96))
        self.assertEqual(result["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        for name, content in before.items():
            self.assertEqual((self.output / "attempts" / name).read_bytes(), content)
        self.assertEqual(self.invoke(1, resume=True)["calls_this_invocation"], 0)

    def test_returned_invalid_output_is_retained_and_blocks_any_continuation(self):
        result = self.invoke(8, complete_fn=lambda c, p: response('{"answer":"A","reason":"extra"}'))
        self.assertEqual((result["stopped"], result["calls_this_invocation"], result["invalid_answers_retained"]),
                         ("invalid_response", 1, 1))
        path = self.output / "attempts/000001.json"
        before = path.read_bytes()
        for retry in (False, True):
            with self.assertRaisesRegex(ValueError, "do not resample"):
                self.invoke(1, resume=True, retry_errors=retry)
        self.assertEqual(path.read_bytes(), before)
        plan, _, attempts = read_run(self.output)
        successor = fixture(plan)[1]
        write_json(self.output / "attempts/000002.json", successor)
        with self.assertRaisesRegex(ValueError, "after a returned invalid"):
            read_run(self.output)
        self.assertEqual(attempts[0]["response"]["raw_response"]["choices"][0]["message"]["content"],
                         '{"answer":"A","reason":"extra"}')

    def test_transport_error_requires_explicit_retry_and_preserves_original_attempt(self):
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
        _, _, attempts = read_run(self.output)
        self.assertEqual(attempts[0]["task_id"], attempts[1]["task_id"])

    def test_interruption_journal_is_written_before_the_provider_call(self):
        def interrupt(c, p):
            record = json.loads((self.output / "attempts/000001.json").read_text())
            self.assertEqual(record["status"], "started")
            self.assertEqual(record["request"], p)
            raise KeyboardInterrupt
        result = self.invoke(8, complete_fn=interrupt)
        self.assertEqual(result["stopped"], "interrupted")
        self.assertEqual(self.invoke(1, resume=True)["stopped"], "retry_requires_flag")
        self.assertEqual(self.invoke(1, resume=True, retry_errors=True)["valid_answers"], 1)

    def test_cumulative_112_attempt_cap_survives_resume(self):
        def failure(c, p):
            raise provider.ProviderError("TimeoutError")
        self.invoke(1, complete_fn=failure)
        first = json.loads((self.output / "attempts/000001.json").read_text())
        for number in range(2, 112):
            write_json(self.output / "attempts" / f"{number:06d}.json", {**first, "attempt": number})
        result = self.invoke(100, resume=True, retry_errors=True)
        self.assertEqual((result["stopped"], result["calls_this_invocation"], result["attempts_total"]),
                         ("total_attempt_limit", 1, 112))
        self.assertEqual(self.invoke(100, resume=True, retry_errors=True)["calls_this_invocation"], 0)

    def test_run_identity_source_raw_content_and_schema_are_audited(self):
        self.invoke(1)
        with self.assertRaisesRegex(ValueError, "resume"):
            self.invoke(1)
        with self.assertRaisesRegex(ValueError, "identity"):
            run(config(), self.output, 1, resume=True, mock=False)
        with self.assertRaisesRegex(ValueError, "mock=True"):
            run(config(), self.output, 1, complete_fn=lambda c, p: answer_response("A"))
        with patch("exception_constrained_cue.core.source_digest", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                self.invoke(1, resume=True)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["response"]["text"] = '{"answer":"A","reason":"tampered"}'
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "raw provider"):
            read_run(self.output)
        changed = copy.deepcopy(original)
        changed["request"]["response_format"]["json_schema"]["strict"] = False
        write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "Saved request"):
            read_run(self.output)

    def test_duplicate_answers_and_reordered_schedule_are_rejected(self):
        self.invoke(2)
        first_path = self.output / "attempts/000001.json"
        second_path = self.output / "attempts/000002.json"
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
