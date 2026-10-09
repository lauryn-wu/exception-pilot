"""Offline checks for the separately versioned word-boundary capability probe."""

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_mistral_prefix import core as v1_core, runner as v1_runner
from exception_mistral_prefix_v2 import core, provider, runner
from exception_pilot.storage import accepted_records


ROOT = Path(__file__).resolve().parents[1]
V1_PLAN_HASH = "6f3084db3fc7f8d0c68770db32915bf85d7d542c0928a3738e14ec07142b597b"


def config():
    return core.load_config(ROOT / "configs/mistral_prefix_v2.json")


def response(text):
    return provider.normalize({"id": "synthetic-v2-capability", "model": "mistral-small-2603",
        "usage": {}, "choices": [{"message": {"role": "assistant", "content": text},
                                  "finish_reason": "stop"}]})


def synthetic_v1_records(plan):
    """All visible parents deliberately err; replay returns their exact full text."""
    records = {}
    for task in plan["tasks"]:
        meta = v1_core.task_meta(plan, task, records)
        if task["family"] == "capability":
            text = "Cobalt Maple Lantern"
        elif task["family"] == "replay":
            text = records[task["parent_task_id"]]["response"]["text"]
        elif task["arm"] == "visible":
            text = ("Inspect the recorded target and compare its details with the surrounding rows. "
                    "The repeated background pattern guides this synthetic choice.\nANSWER: "
                    + meta["pattern_label"])
        else:
            text = "ANSWER: " + meta["expected"]
        result = response(text)
        records[task["id"]] = {"attempt": len(records) + 1, "task_id": task["id"],
            "plan_hash": plan["plan_hash"], "mode": "mock",
            "request": v1_core.request_for(plan, task, records), "meta": meta,
            "response": result, **v1_core.score_response(task, result, meta)}
    return records


class MistralPrefixV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_config = v1_core.load_config(ROOT / "configs/mistral_prefix.json")
        cls.old_plan = v1_core.make_plan(cls.old_config)
        cls.plan = core.make_plan(config())

    def test_v1_is_preserved_and_v2_has_the_same_worlds_and_schedule(self):
        self.assertEqual(self.old_plan["plan_hash"], V1_PLAN_HASH)
        self.assertNotEqual(self.plan["plan_hash"], V1_PLAN_HASH)
        self.assertEqual(self.plan, core.make_plan(config()))
        self.assertEqual(self.plan["worlds"], self.old_plan["worlds"])
        self.assertEqual(self.plan["tasks"], self.old_plan["tasks"])
        self.assertEqual(len(self.plan["tasks"]), 73)
        cfg = copy.deepcopy(config())
        self.assertEqual(cfg["protocol"], "verified-facts-mistral-prefix-feasibility-v2")
        cfg["protocol"] = self.old_config["protocol"]
        self.assertEqual(cfg, self.old_config)

    def test_only_capability_assistant_prefix_changes_in_all_requests(self):
        records = synthetic_v1_records(self.old_plan)
        for task in self.plan["tasks"]:
            with self.subTest(task=task["id"]):
                old = v1_core.request_for(self.old_plan, task, records)
                new = core.request_for(self.plan, task, records)
                if task["family"] == "capability":
                    self.assertEqual(old["messages"][-1]["content"], "Cobalt Ma")
                    self.assertEqual(new["messages"][-1],
                                     {"role": "assistant", "content": "Cobalt ", "prefix": True})
                    expected = copy.deepcopy(old)
                    expected["messages"][-1]["content"] = "Cobalt "
                    self.assertEqual(new, expected)
                else:
                    self.assertEqual(new, old)
                    self.assertEqual(core.task_meta(self.plan, task, records),
                                     v1_core.task_meta(self.old_plan, task, records))

    def test_scoring_and_scientific_gates_are_unchanged(self):
        records = synthetic_v1_records(self.old_plan)
        for task in self.plan["tasks"]:
            record = records[task["id"]]
            self.assertEqual(core.score_response(task, record["response"], record["meta"]),
                             v1_core.score_response(task, record["response"], record["meta"]))
        for gate_name in ("capability_gate", "phenomenon_gate", "replay_gate"):
            old = getattr(v1_core, gate_name)(self.old_plan, records)
            new = getattr(core, gate_name)(self.plan, records)
            self.assertEqual(new, old)
            self.assertEqual(new["status"], "pass")

    def test_exact_capability_still_rejects_typo_suffix_and_whitespace_changes(self):
        task = self.plan["tasks"][0]
        meta = core.task_meta(self.plan, task)
        good = core.score_response(task, response("Cobalt Maple Lantern"), meta)
        self.assertEqual((good["status"], good["capability_exact"]), ("complete", True))
        for text in ("Cobalt Mape Lantern", "Maple Lantern", "ple Lantern",
                     "Cobalt Maple Lantern\n", " Cobalt Maple Lantern", "Cobalt  Maple Lantern"):
            with self.subTest(text=text):
                bad = core.score_response(task, response(text), meta)
                self.assertEqual((bad["status"], bad["invalid_reason"]),
                                 ("invalid", "capability_full_completion_mismatch"))

    def test_old_config_and_run_are_rejected_without_modifying_the_old_run(self):
        with self.assertRaises(ValueError):
            core.validate_config(self.old_config)
        with self.assertRaises(ValueError):
            v1_core.validate_config(config())
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            output = Path(temporary) / "v1"
            v1_runner.run(self.old_config, output, 1, mock=True)
            before = {path.relative_to(output): path.read_bytes()
                      for path in output.rglob("*") if path.is_file()}
            with self.assertRaises(ValueError):
                runner.read_run(output)
            with self.assertRaises(ValueError):
                runner.run(config(), output, 1, resume=True, mock=True)
            self.assertEqual(before, {path.relative_to(output): path.read_bytes()
                                     for path in output.rglob("*") if path.is_file()})

    def test_one_call_mock_records_the_new_exact_request_and_success(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()), \
             patch.object(provider, "complete", side_effect=AssertionError("network forbidden")), \
             patch.object(provider, "credential", side_effect=AssertionError("credentials forbidden")):
            output = Path(temporary) / "v2"
            result = runner.run(config(), output, 1, mock=True)
            self.assertEqual((result["calls_this_invocation"], result["valid_answers"]), (1, 1))
            self.assertTrue(result["is_simulated"])
            self.assertEqual(result["capability_gate"]["status"], "pass")
            plan, execution, attempts = runner.read_run(output)
            self.assertEqual(execution["protocol_version"], config()["protocol"])
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["request"]["messages"][-1]["content"], "Cobalt ")
            self.assertEqual(attempts[0]["response"]["text"], "Cobalt Maple Lantern")
            self.assertEqual(core.capability_gate(plan, accepted_records(attempts))["status"], "pass")
            preview = json.loads((output / "preview.json").read_text())
            self.assertEqual(preview[0]["request"], attempts[0]["request"])

    def test_returned_capability_failure_remains_terminal_with_no_base_requests(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            output = Path(temporary) / "v2"
            result = runner.run(config(), output, 73, mock=True,
                                complete_fn=lambda cfg, payload: response("Cobalt Mape Lantern"))
            self.assertEqual((result["stopped"], result["calls_this_invocation"]),
                             ("capability_gate_failed", 1))
            before = (output / "attempts/000001.json").read_bytes()
            for retry in (False, True):
                with self.assertRaises(ValueError):
                    runner.run(config(), output, 73, resume=True, retry_errors=retry, mock=True)
            self.assertEqual((output / "attempts/000001.json").read_bytes(), before)
            self.assertEqual(len(list((output / "attempts").glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
