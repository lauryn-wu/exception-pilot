"""Offline invariants and collection-integrity checks for the fixed role screen.

All returned answers below are software fixtures, never empirical observations.
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

from exception_query_role import core, runner


ROOT = Path(__file__).resolve().parents[1]


def response(text, identifier="fixture", model="MOCK-NOT-A-MODEL", finish="stop", reasoning=None):
    message = {"role": "assistant", "content": text}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return runner.provider.normalize({
        "id": identifier, "model": model, "usage": {},
        "choices": [{"message": message, "finish_reason": finish}],
    })


def fail_transport(config, payload):
    raise runner.provider.ProviderError("HTTP 429", status_code=429)


class QueryRoleDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(ROOT / "configs/query_role.json")
        cls.plan = core.make_plan(cls.config)

    def test_frozen_balanced_complete_factorial(self):
        plan = self.plan
        self.assertEqual(plan, core.make_plan(copy.deepcopy(self.config)))
        self.assertEqual(len(plan["worlds"]), 12)
        self.assertEqual(len(plan["tasks"]), 144)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 144)
        self.assertEqual(Counter(t["arm"] for t in plan["tasks"]), {"direct": 72, "visible": 72})
        self.assertEqual(Counter(t["query"] for t in plan["tasks"]),
                         {"literal": 48, "encoded": 48, "downstream": 48})
        self.assertEqual(Counter(t["value"] for t in plan["tasks"]), {"a": 72, "b": 72})
        families = Counter(w["family"] for w in plan["worlds"])
        self.assertEqual(sorted(families.values()), [6, 6])
        for world in plan["worlds"]:
            tasks = [t for t in plan["tasks"] if t["world_id"] == world["id"]]
            self.assertEqual(len(tasks), 12)
            self.assertEqual(len({(t["value"], t["query"], t["arm"]) for t in tasks}), 12)
            self.assertTrue(all(t["family"] == world["family"] for t in tasks))
        self.assertEqual(self.config["max_total_attempts"], 153)
        self.assertEqual(self.config["max_extra_attempts"], 9)
        self.assertEqual(self.config["max_retries_per_task"], 2)
        self.assertEqual(self.config["bootstrap_samples"], 10000)

    def test_counterfactual_changes_only_target_and_background_is_balanced(self):
        for world in self.plan["worlds"]:
            first = world["contexts"]["a"].splitlines()
            second = world["contexts"]["b"].splitlines()
            self.assertEqual(len(first), len(second))
            changed = [(a, b) for a, b in zip(first, second) if a != b]
            self.assertEqual(len(changed), 1)
            self.assertTrue(all(world["target_id"] in line for line in changed[0]))
            self.assertIn(world["source_a"], changed[0][0])
            self.assertIn(world["source_b"], changed[0][1])
            if world["family"] == "vehicle":
                peers = [r for r in world["records"] if r["id"] != world["target_id"]]
                self.assertEqual(len(peers), 18)
                self.assertEqual(Counter(r["source"] for r in peers), {"A": 6, "B": 6, "C": 6})
                self.assertEqual(sorted(Counter(r["region"] for r in peers).values()), [6, 6, 6])
                target_peers = [r for r in peers if r["region"] == world["target_region"]]
                self.assertTrue(all(r["source"] == world["pattern_source"] for r in target_peers))
            else:
                self.assertEqual((len(world["defaults"]), len(world["devices"]), len(world["overrides"])), (3, 3, 3))
                target_default = next(r for r in world["defaults"] if r["site"] == world["target_site"])
                self.assertEqual(target_default["source"], world["pattern_source"])
        for family, values in core.SOURCE_VALUES.items():
            worlds = [w for w in self.plan["worlds"] if w["family"] == family]
            self.assertEqual({tuple(w["code_map"][v] for v in values) for w in worlds},
                             set(itertools.permutations(core.CODES)))
            self.assertEqual({tuple(w["roles"][k] for k in ("a", "b", "pattern")) for w in worlds},
                             set(itertools.permutations(values)))
            for role in ("a", "b", "pattern"):
                self.assertEqual(Counter(w["code_map"][w["roles"][role]] for w in worlds),
                                 {code: 2 for code in core.CODES})

    def test_encoding_is_bijective_and_primary_questions_have_same_gold(self):
        for world in self.plan["worlds"]:
            tasks = [t for t in self.plan["tasks"] if t["world_id"] == world["id"]]
            encoded = [t for t in tasks if t["query"] in ("encoded", "downstream")]
            mappings = [t["decode_map"] for t in encoded]
            self.assertTrue(all(m == mappings[0] for m in mappings))
            self.assertEqual(len(mappings[0]), len(set(mappings[0].values())))
            for value in ("a", "b"):
                paired = [t for t in encoded if t["value"] == value]
                self.assertEqual(len({t["expected"] for t in paired}), 1)
                self.assertEqual(len({t["pattern_label"] for t in paired}), 1)
                self.assertNotEqual(paired[0]["expected"], paired[0]["pattern_label"])
            for query in ("literal", "encoded", "downstream"):
                for arm in ("direct", "visible"):
                    pair = [t for t in tasks if t["query"] == query and t["arm"] == arm]
                    self.assertNotEqual(pair[0]["expected"], pair[1]["expected"])
                    self.assertEqual(pair[0]["pattern_label"], pair[1]["pattern_label"])

    def test_requests_are_ordinary_chat_with_matching_settings(self):
        settings = []
        for task in self.plan["tasks"]:
            request = core.request_for(self.plan, task)
            self.assertEqual(len(request["messages"]), 1)
            self.assertEqual(request["messages"][0]["role"], "user")
            self.assertNotIn("prefix", request["messages"][0])
            self.assertEqual(request["messages"][0]["content"], task["prompt"])
            self.assertEqual(request["model"], "mistral-small-2603")
            self.assertEqual(request["reasoning_effort"], "none")
            self.assertFalse(request["stream"])
            settings.append({k: v for k, v in request.items() if k != "messages"})
        self.assertTrue(all(s == settings[0] for s in settings))

    def test_final_scoring_is_label_blind_and_retains_wrong_answers(self):
        direct = next(t for t in self.plan["tasks"] if t["arm"] == "direct")
        visible = next(t for t in self.plan["tasks"] if t["arm"] == "visible")
        for task in (direct, visible):
            lead = "A software fixture explanation.\n" if task["arm"] == "visible" else ""
            for label in (task["expected"], task["pattern_label"]):
                scored = core.score_response(task, response(lead + "FINAL: " + label), core.task_meta(self.plan, task))
                self.assertEqual(scored["status"], "complete")
                self.assertEqual(scored["answer"], label)
                self.assertEqual(scored["correct"], label == task["expected"])
            for text in (lead + "FINAL: A or B", lead + "FINAL: UNDECLARED", lead + "FINAL: " + task["expected"] + "\nTrailing prose.",
                         lead + "FINAL: " + task["expected"] + "."):
                self.assertEqual(core.score_response(task, response(text), core.task_meta(self.plan, task))["status"], "invalid")

    def test_direct_adherence_is_separate_from_accuracy_and_case_is_normalized(self):
        for task in self.plan["tasks"]:
            meta = core.task_meta(self.plan, task)
            text = " final :  " + task["expected"].lower() + " \n\n"
            scored = core.score_response(task, response(text), meta)
            self.assertEqual((scored["status"], scored["answer"], scored["correct"]),
                             ("complete", task["expected"], True))
            if task["arm"] == "direct":
                self.assertTrue(scored["direct_instruction_adherent"])
                extra = core.score_response(task, response("Extra explanatory text.\n" + text), meta)
                self.assertEqual((extra["status"], extra["correct"]), ("complete", True))
                self.assertFalse(extra["direct_instruction_adherent"])

    def test_truncation_and_hidden_reasoning_cannot_be_scored_as_valid(self):
        task = self.plan["tasks"][0]
        text = "A software fixture explanation.\nFINAL: " + task["expected"]
        for raw in (response(text, finish="length"), response(text, reasoning="hidden reasoning"),
                    response(""), runner.provider.normalize({"bad": "body"})):
            scored = core.score_response(task, raw, core.task_meta(self.plan, task))
            self.assertEqual(scored["status"], "invalid")
            self.assertIsNone(scored["answer"])

    def test_design_changes_require_new_protocol(self):
        for key, replacement in (("seed", 1), ("model", "other-model"), ("max_total_attempts", 154),
                                 ("max_extra_attempts", 10), ("max_retries_per_task", 3)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                core.make_plan(cfg)


class QueryRoleCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(ROOT / "configs/query_role.json")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)
        for name in ("complete", "credential"):
            guard = patch.object(runner.provider, name, side_effect=AssertionError("No network or credentials in offline tests"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_prepare_makes_no_calls_and_preserves_existing_files(self):
        plan = runner.prepare(self.config, self.output)
        self.assertFalse((self.output / "execution.json").exists())
        self.assertEqual(runner.read_run(self.output)[2], [])
        before = {name: (self.output / name).read_bytes()
                  for name in ("plan.json", "plan.sha256", "preview.json", "preview.md")}
        self.assertEqual(plan, runner.prepare(self.config, self.output))
        self.assertEqual(before, {name: (self.output / name).read_bytes() for name in before})
        nonempty = Path(self.temp.name) / "nonempty"
        nonempty.mkdir()
        sentinel = nonempty / "keep.txt"
        sentinel.write_text("Preserve input")
        with self.assertRaises(ValueError):
            runner.prepare(self.config, nonempty)
        self.assertEqual(sentinel.read_text(), "Preserve input")

    def test_mock_resume_completes_once_without_duplicate_tasks(self):
        one = runner.run(self.config, self.output, 1, mock=True)
        self.assertEqual((one["calls_this_invocation"], one["attempts_total"]), (1, 1))
        with self.assertRaises(ValueError):
            runner.run(self.config, self.output, 1, mock=True)
        two = runner.run(self.config, self.output, 2, resume=True, mock=True)
        self.assertEqual((two["calls_this_invocation"], two["attempts_total"]), (2, 3))
        complete = runner.run(self.config, self.output, 153, resume=True, mock=True)
        self.assertEqual((complete["stopped"], complete["calls_this_invocation"], complete["valid_answers"]),
                         ("complete", 141, 144))
        plan, execution, attempts = runner.read_run(self.output, "mock")
        self.assertEqual(execution["mode"], "mock")
        self.assertEqual([a["task_id"] for a in attempts], [t["id"] for t in plan["tasks"]])
        self.assertTrue(all(a["correct"] for a in attempts))
        again = runner.run(self.config, self.output, 153, resume=True, retry_errors=True, mock=True)
        self.assertEqual(again["calls_this_invocation"], 0)

    def test_live_mock_mixing_and_live_injection_are_forbidden(self):
        with self.assertRaises(ValueError):
            runner.run(self.config, self.output, 1, complete_fn=lambda *_: response("FINAL: A"))
        runner.run(self.config, self.output, 1, mock=True)
        with self.assertRaises(ValueError):
            runner.run(self.config, self.output, 1, resume=True)
        with self.assertRaises(ValueError):
            runner.read_run(self.output, "live")

    def test_all_returned_invalid_forms_are_retained_and_collection_continues(self):
        fixtures = [response("No terminal answer", "ambiguous"), response("FINAL: A", "truncated", finish="length"),
                    response("", "empty"), runner.provider.normalize({"bad": "body"}),
                    response("FINAL: A", "hidden", reasoning="hidden thought")]
        result = runner.run(self.config, self.output, len(fixtures), mock=True,
                            complete_fn=lambda cfg, payload: fixtures.pop(0))
        self.assertEqual((result["calls_this_invocation"], result["invalid_answers_retained"]), (5, 5))
        saved = {p.name: p.read_bytes() for p in (self.output / "attempts").glob("*.json")}
        result = runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((result["attempts_total"], result["valid_answers"]), (6, 1))
        self.assertEqual(saved, {name: (self.output / "attempts" / name).read_bytes() for name in saved})
        _, _, attempts = runner.read_run(self.output)
        self.assertEqual(len({a["task_id"] for a in attempts}), 6)

    def test_transport_retry_requires_flag_and_has_three_attempt_task_cap(self):
        result = runner.run(self.config, self.output, 1, mock=True, complete_fn=fail_transport)
        self.assertEqual(result["stopped"], "provider_error")
        original = (self.output / "attempts/000001.json").read_bytes()
        blocked = runner.run(self.config, self.output, 1, resume=True, mock=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("retry_requires_flag", 0))
        for expected in (2, 3):
            result = runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True,
                                complete_fn=fail_transport)
            self.assertEqual(result["attempts_total"], expected)
        result = runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("task_retry_limit", 0))
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), original)
        attempts = runner.read_run(self.output)[2]
        self.assertEqual([a["retry_of_attempt"] for a in attempts], [None, 1, 2])

    def test_global_extra_budget_and_total_attempt_cap_prevent_provider_calls(self):
        # Nine tasks each consume exactly one authorized transport retry.
        for index in range(9):
            runner.run(self.config, self.output, 1, resume=index > 0, mock=True, complete_fn=fail_transport)
            result = runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((result["attempts_total"], result["extra_attempts_used"]), (18, 9))
        cap_output = Path(self.temp.name) / "total-cap"
        shutil.copytree(self.output, cap_output)
        runner.run(self.config, self.output, 1, resume=True, mock=True, complete_fn=fail_transport)
        blocked = runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("extra_attempt_limit", 0))
        runner.run(self.config, cap_output, 134, resume=True, mock=True)
        last = runner.run(self.config, cap_output, 1, resume=True, mock=True, complete_fn=fail_transport)
        self.assertEqual(last["attempts_total"], 153)
        blocked = runner.run(self.config, cap_output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((blocked["stopped"], blocked["calls_this_invocation"]), ("total_attempt_limit", 0))

    def test_model_change_and_duplicate_response_identity_are_terminal(self):
        runner.run(self.config, self.output, 1, mock=True)
        first = runner.read_run(self.output)[2][0]
        duplicate_output = Path(self.temp.name) / "duplicate"
        shutil.copytree(self.output, duplicate_output)
        result = runner.run(self.config, self.output, 1, resume=True, mock=True,
                            complete_fn=lambda *_: response("FINAL: A", "changed-model", model="OTHER-MODEL"))
        self.assertEqual(result["stopped"], "operational_failure")
        self.assertEqual(runner.read_run(self.output)[2][-1]["hard_failure"], "response_model_changed")
        with self.assertRaises(ValueError):
            runner.run(self.config, self.output, 1, resume=True, retry_errors=True, mock=True)
        result = runner.run(self.config, duplicate_output, 1, resume=True, mock=True,
                            complete_fn=lambda *_: response("FINAL: A", first["response"]["response_id"]))
        self.assertEqual(result["stopped"], "operational_failure")
        self.assertEqual(runner.read_run(duplicate_output)[2][-1]["hard_failure"], "duplicate_response_id")

    def test_plan_config_preview_and_attempt_tampering_are_detected(self):
        runner.run(self.config, self.output, 2, mock=True)
        changed = copy.deepcopy(self.config)
        changed["api_key_env"] = "OTHER_TEST_KEY"
        with self.assertRaises(ValueError):
            runner.run(changed, self.output, 1, resume=True, mock=True)
        with patch.object(core, "source_digest", return_value="modified-source-code"), self.assertRaises(ValueError):
            runner.read_run(self.output)
        for relative in ("plan.json", "preview.json", "preview.md"):
            path = self.output / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\nChanged artifact\n")
            with self.subTest(path=relative), self.assertRaises(ValueError):
                runner.read_run(self.output)
            path.write_bytes(original)
        path = self.output / "attempts/000001.json"
        original = path.read_bytes()
        for mutation in ("request", "raw", "score", "retry"):
            record = json.loads(original)
            if mutation == "request":
                record["request"]["temperature"] = 0.99
            elif mutation == "raw":
                record["response"]["raw_response"]["choices"][0]["message"]["content"] += " altered"
            elif mutation == "score":
                record["answer"] = "UNDECLARED"
            else:
                record["retry_of_attempt"] = 123
            path.write_text(json.dumps(record))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                runner.read_run(self.output)
            path.write_bytes(original)
        self.assertEqual(len(runner.read_run(self.output)[2]), 2)


if __name__ == "__main__":
    unittest.main()
