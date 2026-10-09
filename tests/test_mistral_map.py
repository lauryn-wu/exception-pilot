"""Offline integrity, prefix contract, sampling, and aggregation tests."""

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_mistral_prefix_v2 import core as old_core, runner as old_runner
from exception_mistral_map import core, runner, analysis
from exception_pilot.storage import accepted_records

ROOT = Path(__file__).resolve().parents[1]


def raw(text, identifier="fixture", model="MOCK-NOT-A-MODEL", finish="stop"):
    return runner.provider.normalize({"id": identifier, "model": model, "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]})


def make_parent(path):
    config = old_core.load_config(ROOT / "configs/mistral_prefix_v2.json")
    plan = old_core.make_plan(config)
    queue = iter(plan["tasks"])

    def complete(cfg, payload):
        task = next(queue)
        meta = old_core.task_meta(plan, task)
        if task["family"] == "capability":
            text = "Cobalt Maple Lantern"
        elif task["family"] == "replay":
            # The runner appends the real frozen prefix; return the original text.
            parent = next(t for t in plan["tasks"] if t["id"] == task["parent_task_id"])
            parent_meta = old_core.task_meta(plan, parent)
            text = reasoning(parent_meta)
        elif task["arm"] == "direct":
            text = "ANSWER: " + meta["expected"]
        else:
            text = reasoning(meta)
        return raw(text, "old-" + task["id"])

    def reasoning(meta):
        return ("Inspect the target carefully.\n\n1. Target attributes:\n"
                f"- License plate: {meta['item_id']}\n"
                "- Verified class: MISSING\n\n"
                "2. Compare other records:\n"
                "The repeated background relation might guide this choice.\n\n"
                "3. Conclusion:\nUse the pattern in this synthetic fixture.\n\nANSWER: " + meta["pattern_label"])

    with redirect_stdout(io.StringIO()):
        old_runner.run(config, path, 73, mock=True, complete_fn=complete)
    return path


class MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.source_path = make_parent(Path(cls.temp.name) / "source")
        cls.source = core.read_source(cls.source_path)
        cls.config = core.load_config(ROOT / "configs/mistral_map.json")
        cls.plan = core.make_plan(cls.config, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def prepare(self, root):
        out = Path(root) / "map"
        runner.prepare(self.config, out, self.source_path)
        return out

    def test_all_parents_included_and_prefixes_are_exact_with_new_suffixes(self):
        self.assertEqual(len(self.plan["cases"]), 24)
        self.assertEqual(len(self.plan["worlds"]), 12)
        self.assertEqual(self.plan, core.make_plan(self.config, self.source))
        for task in self.plan["tasks"]:
            req = core.request_for(self.plan, task)
            self.assertEqual((req["temperature"], req["top_p"], req["reasoning_effort"]), (0.6, 0.95, "none"))
            if task["family"] == "map":
                case, point = core.case_point(self.plan, task)
                prefix = case["parent_text"][:point["cut_chars"]]
                self.assertEqual(req["messages"][0], case["messages"][0])
                self.assertNotIn("ANSWER:", prefix)
                if prefix:
                    self.assertEqual(req["messages"][1], {"role": "assistant", "prefix": True, "content": prefix})
                else:
                    self.assertEqual(len(req["messages"]), 1)

    def test_cut_logic_excludes_other_records_and_conclusion(self):
        text = ("1. Compare:\n- OTHER: Verified class A\n- TARGET: class MISSING\n\n"
                "2. Conclusion:\nChoose B.\nANSWER: B")
        points, span = core.checkpoints(text, "TARGET", ["OTHER"])
        self.assertEqual(span["text"], "- TARGET: class MISSING\n\n")
        self.assertEqual(points[-1]["cut_chars"], text.index("2. Conclusion:"))
        no_record = "Step 1: Compare rows\n- OTHER: Verified class A\n\nStep 2: All remaining matching records point to class A\nANSWER: A"
        self.assertIsNone(core.checkpoints(no_record, "TARGET", ["OTHER"])[1])

    def test_prefix_mismatch_truncation_and_answer_only_are_not_valid(self):
        task = next(t for t in self.plan["tasks"] if t["family"] == "map" and core.task_meta(self.plan, t)["prefix_text"])
        meta = core.task_meta(self.plan, task)
        good = meta["prefix_text"] + "Fresh continuation.\nANSWER: A"
        self.assertEqual(core.score_response(task, raw(good), meta)["answer"], "A")
        self.assertFalse(core.score_response(task, raw("ANSWER: A"), meta)["format_valid"])
        self.assertFalse(core.score_response(task, raw(good, finish="length"), meta)["format_valid"])
        self.assertEqual(core.score_response(task, raw(good), meta)["generated_suffix"], "Fresh continuation.\nANSWER: A")

    def test_check_stops_at_49_even_with_large_budget_and_live_calls_forbidden(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()), \
             patch.object(runner.provider, "complete", side_effect=AssertionError("network")), \
             patch.object(runner.provider, "credential", side_effect=AssertionError("key")):
            out = self.prepare(root)
            with self.assertRaises(ValueError):
                runner.run(self.config, out, 10, stage="map", mock=True)
            result = runner.run(self.config, out, 1107, mock=True)
            self.assertEqual((result["stopped"], result["calls_this_invocation"]), ("sampling_check_passed", 49))
            self.assertTrue(result["is_simulated"])
            self.assertEqual(result["sampling_gate"]["status"], "pass")
            with self.assertRaises(ValueError):
                runner.run(self.config, out, 1, resume=True, mock=False)

    def test_full_mock_run_world_units_and_resume_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            runner.run(self.config, out, 49, mock=True)
            result = runner.run(self.config, out, 1107, stage="map", resume=True, mock=True)
            self.assertEqual(result["stopped"], "complete")
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["analysis_status"], "exploratory_map_complete")
            self.assertEqual(summary["base_direct_minus_visible_accuracy"]["n_worlds"], 12)
            self.assertEqual(summary["base_direct_minus_visible_accuracy"]["mean"], 1)
            self.assertEqual(summary["target_record_line_contrasts"][0]["n_worlds"], 12)
            self.assertEqual(summary["target_record_line_contrasts"][0]["mean"], 0)
            again = runner.run(self.config, out, 1107, stage="map", resume=True, mock=True)
            self.assertEqual(again["calls_this_invocation"], 0)

    def test_source_and_request_tampering_are_detected(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            runner.run(self.config, out, 1, mock=True)
            path = out / "attempts/000001.json"
            original = path.read_bytes()
            data = json.loads(original)
            data["request"]["temperature"] = 0
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runner.read_run(out)
            path.write_bytes(original)
            source = out / "source-parent/attempts/000002.json"
            data = json.loads(source.read_text())
            data["response"]["text"] += "modified"
            source.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runner.read_run(out)

    def test_transport_retry_requires_flag_and_retains_attempt(self):
        def fail(cfg, payload):
            raise runner.provider.ProviderError("HTTP 429", status_code=429)
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            result = runner.run(self.config, out, 1, mock=True, complete_fn=fail)
            self.assertEqual(result["stopped"], "provider_error")
            self.assertEqual(runner.run(self.config, out, 1, resume=True, mock=True)["stopped"], "retry_requires_flag")
            result = runner.run(self.config, out, 1, resume=True, retry_errors=True, mock=True)
            self.assertEqual(result["attempts_total"], 2)
            self.assertEqual(result["valid_answers"], 1)

    def test_failed_sampling_check_cannot_run_map(self):
        queue = iter(self.plan["tasks"])
        def all_correct(cfg, payload):
            task = next(queue)
            meta = core.task_meta(self.plan, task)
            if task["family"] == "capability":
                text = "Cobalt Maple Lantern"
            else:
                text = ("Fixture reasoning.\n" if task["arm"] == "visible" else "") + "ANSWER: " + meta["expected"]
            return raw(text, "correct-" + task["id"])
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            result = runner.run(self.config, out, 100, mock=True, complete_fn=all_correct)
            self.assertEqual(result["stopped"], "sampling_check_failed")
            self.assertEqual(result["attempts_total"], 49)
            with self.assertRaises(ValueError):
                runner.run(self.config, out, 100, stage="map", resume=True, mock=True)

    def test_returned_format_invalid_is_retained_without_retry(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            runner.run(self.config, out, 49, mock=True)
            def bad_format(cfg, payload):
                prefix = payload["messages"][-1]["content"] if len(payload["messages"]) == 2 else ""
                return raw(prefix + "No final answer in this fixture.", "invalid-format")
            runner.run(self.config, out, 1, stage="map", resume=True, mock=True, complete_fn=bad_format)
            plan, _, attempts = runner.read_run(out)
            self.assertEqual(attempts[-1]["status"], "invalid")
            first_task = attempts[-1]["task_id"]
            runner.run(self.config, out, 1, stage="map", resume=True, retry_errors=True, mock=True)
            _, _, attempts = runner.read_run(out)
            self.assertNotEqual(attempts[-1]["task_id"], first_task)

    def test_prefix_failure_is_terminal_even_with_retry_flag(self):
        with tempfile.TemporaryDirectory() as root, redirect_stdout(io.StringIO()):
            out = self.prepare(root)
            runner.run(self.config, out, 49, mock=True)
            # Stop at the first nonempty scheduled prefix.
            for task in self.plan["tasks"][49:]:
                if core.task_meta(self.plan, task)["prefix_text"]:
                    break
                runner.run(self.config, out, 1, stage="map", resume=True, mock=True)
            result = runner.run(self.config, out, 1, stage="map", resume=True, mock=True,
                                complete_fn=lambda cfg, payload: raw("Replacement text.\nANSWER: A", "bad-prefix"))
            self.assertEqual(result["stopped"], "operational_failure")
            with self.assertRaises(ValueError):
                runner.run(self.config, out, 1, stage="map", resume=True, retry_errors=True, mock=True)

    def test_counts_do_not_turn_unscorable_into_observed_errors(self):
        rows = [{"status": "complete", "correct": 1, "follows_pattern": 0, "answer": "A"},
                {"status": "invalid", "correct": None, "follows_pattern": None, "answer": None},
                {"status": "pending", "correct": None, "follows_pattern": None, "answer": None}]
        c = analysis.counts(rows)
        self.assertEqual(c["accuracy_valid_only"], 1)
        self.assertEqual(c["full_plan_accuracy_bounds"], [1 / 3, 1])
        self.assertEqual((c["other"], c["invalid"], c["pending"]), (0, 1, 1))


if __name__ == "__main__":
    unittest.main()
