from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import re
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.core import check_plan, digest
from exception_pilot.storage import write_json
from exception_query_form import core, provider, runner
from exception_query_form.__main__ import main
from exception_query_form.analysis import combine_decisions, paired_statistics, sign_test, summarize, write_summary

ROOT = Path(__file__).resolve().parents[1]


def config(name="gpt4o"):
    return core.load_config(ROOT / "configs" / f"query_form_{name}.json")


def raw_response(text, model="MOCK-NOT-A-MODEL", finish="stop"):
    return {"model": model, "usage": {}, "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


def fixture(plan, cfg, harm="interaction", live=False):
    records = []
    for index, task in enumerate(plan["tasks"], 1):
        meta = core.task_meta(plan, task)
        world_index = int(task["world_id"].split("-")[-1])
        # Harm half the worlds, producing mean interaction 0.5 and 12 nonzero
        # positive signs. These are synthetic fixtures, never provider evidence.
        affected = world_index < 12 and (
            task["arm"] == "visible" and (task["query"] == "profile" or harm == "both")
            or task["arm"] == "filler" and harm == "filler")
        answer = meta["pattern_label"] if affected else meta["expected"]
        pre = core.FILLER + "\n" if task["arm"] == "filler" else "SIMULATED fixture explanation.\n" if task["arm"] == "visible" else ""
        response = provider.normalize(raw_response(pre + "ANSWER: " + answer, cfg["model"] if live else "MOCK-NOT-A-MODEL"), cfg, "live" if live else "mock")
        records.append({"attempt": index, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                        "config_hash": digest(cfg), "mode": "live" if live else "mock", "meta": meta,
                        "request": core.request_for(plan, task, cfg), "response": response, **core.score_response(task, response)})
    return records


class QueryFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = config()
        cls.plan = core.make_plan(cls.cfg)

    def setUp(self):
        # Every new test fails immediately on attempted real networking.
        self.socket_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("No network in tests"))
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)

    def test_plan_determinism_hash_tasks_and_cross_config_identity(self):
        self.assertEqual(self.plan, core.make_plan(self.cfg))
        self.assertEqual(self.plan, core.make_plan(config("mistral")))
        check_plan(self.plan)
        self.assertEqual(set(Counter(t["world_id"] for t in self.plan["tasks"]).values()), {12})
        self.assertEqual(len({t["id"] for t in self.plan["tasks"]}), 288)
        self.assertNotIn("config", self.plan)
        for world in self.plan["worlds"]:
            diff = [i for i, (a, b) in enumerate(zip(world["record_labels"]["record_1"], world["record_labels"]["record_2"])) if a != b]
            self.assertEqual(diff, [world["target_index"]])

    def test_prefix_unused_and_plates_unique(self):
        used = set()
        for path in ROOT.glob("exception_*/core.py"):
            if path.parent.name == "exception_query_form":
                continue
            used.update(re.findall(r'item\["id"\] = "([A-Z])"', path.read_text()))
        self.assertNotIn(core.PLATE_PREFIX, used)
        plates = [item["id"] for w in self.plan["worlds"] for item in w["items"]]
        self.assertEqual(len(set(plates)), 240)
        self.assertTrue(all(p.startswith(core.PLATE_PREFIX) for p in plates))

    def test_prompt_byte_identity_and_key_has_no_attributes_outside_table(self):
        for task in self.plan["tasks"]:
            if task["query"] != "profile":
                continue
            key_task = dict(task, query="key")
            profile, key = core.prompt_parts(self.plan, task), core.prompt_parts(self.plan, key_task)
            self.assertEqual(profile[0].encode(), key[0].encode())
            self.assertEqual(profile[2].encode(), key[2].encode())
            self.assertEqual(len(profile[1].splitlines()), 5)
            target = core.task_meta(self.plan, task)["item_id"]
            self.assertEqual(key[1], "License plate: " + target)
            text = core.messages_for(self.plan, key_task)[0]["content"]
            outside = "\n".join(line for line in text.splitlines() if not line.startswith("|"))
            for phrase in ("Description:", "Transmission:", "Seat cover:", "Doors:"):
                self.assertNotIn(phrase, outside)
            world = core.world_for(self.plan, task)
            self.assertNotIn(world["items"][world["target_index"]]["descriptor"], outside)

    def test_filler_same_response_no_class_tokens(self):
        self.assertTrue(300 <= len(core.FILLER.split()) <= 340)
        self.assertIsNone(re.search(r"\b[ABC]\b", core.FILLER, re.I))
        self.assertIsNone(re.search(r"\b(vehicles?|classes?|tables?)\b", core.FILLER, re.I))
        for task in self.plan["tasks"]:
            messages = core.messages_for(self.plan, task)
            self.assertEqual([m["role"] for m in messages], ["user"])
            if task["arm"] == "filler":
                self.assertIn(core.FILLER, messages[0]["content"])

    def test_config_exact_fields_equal_caps_and_credentials(self):
        for key, value in (("unexpected", 1), ("seed", 42), ("model", "other"), ("max_completion_tokens", {"direct": 1000, "visible": 900, "filler": 1000})):
            changed = dict(self.cfg, **{key: value})
            with self.assertRaises(ValueError):
                core.validate_config(changed)
        mistral = config("mistral")
        self.assertEqual(core.request_for(self.plan, self.plan["tasks"][0], mistral)["reasoning_effort"], "none")

    def test_tolerant_strict_scoring_and_invalid(self):
        def score(text, arm="visible", finish="stop"):
            return core.score_response({"arm": arm}, provider.normalize(raw_response(text, finish=finish), self.cfg, "mock"))
        self.assertEqual(score("Some reasoning.\n**ANSWER: A**")["answer"], "A")
        self.assertFalse(score("Some reasoning.\n**ANSWER: A**")["strict_answer_match"])
        self.assertFalse(score("Some reasoning.\n**ANSWER: A**")["output_contract_met"])
        self.assertTrue(score("ANSWER: B", "direct")["answer_only"])
        self.assertFalse(score("ANSWER: B")["output_contract_met"])
        self.assertTrue(score(core.FILLER + "\nANSWER: C", "filler")["filler_exact"])
        self.assertFalse(score("Unrelated filler.\nANSWER: C", "filler")["output_contract_met"])
        self.assertEqual(score("ANSWER: B", finish="length")["status"], "invalid")
        self.assertEqual(score("ANSWER: A\nANSWER: B")["status"], "invalid")

    def test_returned_malformed_transport_body_and_refusal_retained(self):
        with patch.object(provider, "credential", return_value="SYNTHETIC_TEST_ONLY"), patch.object(provider.request, "build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = b"{bad json"
            result = provider.complete(self.cfg, core.request_for(self.plan, self.plan["tasks"][0], self.cfg))
        self.assertFalse(result["complete"])
        self.assertEqual(result["raw_response"], {"_invalid_json_body": "{bad json"})
        for raw in ([], {"choices": []}, raw_response("ANSWER: A", finish="length")):
            self.assertFalse(provider.normalize(raw, self.cfg, "mock")["complete"])
        raw = raw_response("ANSWER: A")
        raw["choices"][0]["message"]["refusal"] = "Synthetic refusal"
        self.assertFalse(provider.normalize(raw, self.cfg, "mock")["complete"])

    def test_planted_interaction_pairing_and_bounds(self):
        rows = fixture(self.plan, self.cfg)
        records = {r["task_id"]: r for r in rows}
        stats = paired_statistics(self.plan, records)
        primary = stats["record_sensitivity"]["interaction"]
        self.assertEqual(primary["estimate"], .5)
        self.assertEqual(primary["complete_worlds"], 24)
        self.assertEqual(primary["sign_test"]["positive"], 12)
        self.assertEqual(primary["sign_test"]["ties"], 12)
        self.assertLess(primary["sign_test"]["p_two_sided"], .05)
        self.assertLess(primary["ci95"][0], .5)
        self.assertGreater(primary["ci95"][1], .5)
        # One missing negative-coefficient response must expand in both directions.
        task = next(t for t in self.plan["tasks"] if t["query"] == "profile" and t["arm"] == "visible")
        del records[task["id"]]
        stats = paired_statistics(self.plan, records)
        self.assertEqual(stats["record_sensitivity"]["interaction"]["complete_worlds"], 23)
        low, high = stats["record_sensitivity"]["interaction"]["full_plan_bounds"]
        self.assertAlmostEqual(high - low, 1 / 24)
        low, high = stats["accuracy"]["interaction"]["full_plan_bounds"]
        self.assertAlmostEqual(high - low, .5 / 24)

    def test_sign_test_ties_and_record_scale(self):
        self.assertEqual(sign_test([0, 0])["p_two_sided"], 1.)
        self.assertEqual(sign_test([1, -1, 0])["ties"], 1)
        records = {r["task_id"]: r for r in fixture(self.plan, self.cfg)}
        for r in records.values():
            r["answer"] = r["meta"]["expected"]
        stat = paired_statistics(self.plan, records)["record_sensitivity"]["key/direct"]
        self.assertEqual(stat["estimate"], 1.)
        for r in records.values():
            r["answer"] = next(c for c in "ABC" if c not in (r["meta"]["expected"], r["meta"]["pattern_label"]))
        self.assertEqual(paired_statistics(self.plan, records)["record_sensitivity"]["key/direct"]["estimate"], -1.)

    def test_spending_decisions_require_two_live_models_and_controls(self):
        # In-memory counterfactual test data; never saved as live run artifacts.
        first = summarize(self.plan, self.cfg, {"mode": "live"}, fixture(self.plan, self.cfg, live=True))
        cfg2 = config("mistral")
        second = summarize(self.plan, cfg2, {"mode": "live"}, fixture(self.plan, cfg2, live=True))
        self.assertEqual(first["decision"], "awaiting_replication")
        self.assertEqual(combine_decisions(first, second), "proceed_to_dose")
        self.assertEqual(combine_decisions(first, first), "replication_identity_mismatch")
        for harm, decision in (("both", "stop_query_form"), ("filler", "stop_tokens_account_live")):
            result = summarize(self.plan, self.cfg, {"mode": "live"}, fixture(self.plan, self.cfg, harm, True))
            self.assertEqual(result["decision"], decision)
        simulated = summarize(self.plan, self.cfg, {"mode": "mock"}, fixture(self.plan, self.cfg))
        self.assertEqual(combine_decisions(first, simulated), "simulated_only")
        broken = fixture(self.plan, self.cfg, live=True)
        for r in broken:
            if r["meta"]["arm"] == "filler":
                r["filler_exact"] = False
        self.assertEqual(summarize(self.plan, self.cfg, {"mode": "live"}, broken)["decision"], "output_manipulation_inconclusive")

    def test_key_floor_cannot_pass_as_retained_record_use(self):
        rows = fixture(self.plan, self.cfg, live=True)
        for row in rows:
            if row["meta"]["query"] != "key":
                continue
            text = row["response"]["text"].rsplit("ANSWER: ", 1)[0] + "ANSWER: " + row["meta"]["pattern_label"]
            response = provider.normalize(raw_response(text, self.cfg["model"]), self.cfg, "live")
            row.update(response=response, **core.score_response(row["meta"], response))
        result = summarize(self.plan, self.cfg, {"mode": "live"}, rows)
        self.assertEqual(result["metrics"]["accuracy"]["key/visible"]["estimate"], 0)
        self.assertEqual(result["metrics"]["record_sensitivity"]["key_direct_minus_visible"]["estimate"], 0)
        self.assertEqual(result["decision"], "insufficient_record_competence")
        peer = dict(result, model="mistral-small-2603")
        self.assertEqual(combine_decisions(result, peer), "insufficient_record_competence")

    def test_competence_threshold_requires_44_of_48_correct(self):
        slots = [(world["id"], value) for world in self.plan["worlds"] for value in core.VALUES]
        for errors, decision in ((4, "eligible_for_dose_review"), (5, "insufficient_record_competence")):
            rows = fixture(self.plan, self.cfg, live=True)
            affected = set(slots[:errors])
            for row in rows:
                if (row["meta"]["world_id"], row["meta"]["value"]) not in affected:
                    continue
                text = row["response"]["text"].rsplit("ANSWER: ", 1)[0] + "ANSWER: " + row["meta"]["pattern_label"]
                response = provider.normalize(raw_response(text, self.cfg["model"]), self.cfg, "live")
                row.update(response=response, **core.score_response(row["meta"], response))
            result = summarize(self.plan, self.cfg, {"mode": "live"}, rows)
            self.assertEqual(result["local_decision"], decision)
            for cell in core.DECISION_RULE["competence_cells"]:
                self.assertAlmostEqual(result["metrics"]["accuracy"][cell]["full_plan_bounds"][0], (48 - errors) / 48)

    def test_prepare_zero_network_cross_config_bytes_and_change_block(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(provider, "credential", side_effect=AssertionError("prepare must not need key")):
            a, b = Path(directory) / "a", Path(directory) / "b"
            runner.prepare(self.cfg, a)
            runner.prepare(config("mistral"), b)
            self.assertEqual((a / "plan.json").read_bytes(), (b / "plan.json").read_bytes())
            self.assertEqual(len(json.loads((a / "preview.json").read_text())), 288)
            with self.assertRaisesRegex(ValueError, "Config differs"):
                runner.prepare(dict(self.cfg, api_key_env="OTHER_KEY"), a)
            with patch.object(core, "source_digest", return_value="changed"):
                with self.assertRaisesRegex(ValueError, "Code or saved plan"):
                    core.read_plan(a)

    def test_mock_end_to_end_resume_both_providers_and_read_only_coder(self):
        from code_rationales import audit_run
        for name in ("gpt4o", "mistral"):
            with self.subTest(provider=name), tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
                output = Path(directory) / "run"
                cfg = config(name)
                self.assertEqual(runner.run(cfg, output, 12, mock=True)["calls_this_invocation"], 12)
                with self.assertRaisesRegex(ValueError, "already started"):
                    runner.run(cfg, output, 1, mock=True)
                result = runner.run(cfg, output, 288, resume=True, mock=True)
                self.assertEqual(result["calls_this_invocation"], 276)
                self.assertEqual(result["returned_answers"], 288)
                self.assertEqual(result["decision"], "simulated_only")
                before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
                rows = audit_run(output, Path(directory) / "audit", sample=3)
                self.assertEqual(len(rows), 96)
                self.assertEqual(before, {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()})
                self.assertTrue((output / "answers.csv").exists())
                self.assertIn("SIMULATED", (output / "summary.md").read_text())
                self.assertEqual(runner.run(cfg, output, 288, resume=True, mock=True)["calls_this_invocation"], 0)
                with self.assertRaisesRegex(ValueError, "identity or run mode"):
                    runner.run(cfg, output, 1, resume=True)

    def test_invalid_retained_continues_and_not_resampled(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            def invalid(cfg, payload):
                return provider.normalize(raw_response("unclear"), cfg, "mock")
            self.assertEqual(runner.run(self.cfg, directory, 3, mock=True, complete_fn=invalid)["invalid_answers_retained"], 3)
            result = runner.run(self.cfg, directory, 288, resume=True, retry_errors=True, mock=True)
            self.assertEqual(result["calls_this_invocation"], 285)
            self.assertEqual(result["attempts_total"], 288)
            self.assertEqual(result["invalid_answers_retained"], 3)

    def test_transport_retry_only_and_mismatch_hard_stop(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            def fail(cfg, payload):
                raise provider.ProviderError("SyntheticTimeout")
            result = runner.run(self.cfg, directory, 1, mock=True, complete_fn=fail)
            self.assertEqual(result["stopped"], "provider_error")
            self.assertEqual(runner.run(self.cfg, directory, 1, resume=True, mock=True)["stopped"], "retry_requires_flag")
            result = runner.run(self.cfg, directory, 1, resume=True, retry_errors=True, mock=True)
            self.assertEqual(result["attempts_total"], 2)
            self.assertEqual(result["returned_answers"], 1)
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            def mismatch(cfg, payload):
                return provider.normalize(raw_response("ANSWER: A", "WRONG-MODEL"), cfg, "mock")
            self.assertEqual(runner.run(self.cfg, directory, 12, mock=True, complete_fn=mismatch)["stopped"], "model_mismatch")
            with self.assertRaisesRegex(ValueError, "hard stop"):
                runner.run(self.cfg, directory, 12, resume=True, retry_errors=True, mock=True)

    def test_raw_integrity_cap_and_unresolved_attempt(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            runner.run(self.cfg, directory, 1, mock=True)
            path = Path(directory) / "attempts" / "000001.json"
            record = json.loads(path.read_text())
            record["answer"] = next(c for c in "ABC" if c != record["answer"])
            write_json(path, record)
            with self.assertRaisesRegex(ValueError, "scoring differs"):
                runner.read_run(directory)
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            def interrupt(cfg, payload):
                raise KeyboardInterrupt
            runner.run(self.cfg, directory, 1, mock=True, complete_fn=interrupt)
            self.assertEqual(runner.run(self.cfg, directory, 1, mock=True, resume=True, retry_errors=True)["stopped"], "unresolved_attempt_requires_review")
            path = Path(directory) / "attempts" / "000001.json"
            record = json.loads(path.read_text())
            record.update(status="error", error="SyntheticTimeout")
            for i in range(1, 317):
                write_json(path.parent / f"{i:06d}.json", dict(record, attempt=i))
            self.assertEqual(runner.run(self.cfg, directory, 1, mock=True, resume=True, retry_errors=True)["stopped"], "total_attempt_limit")

    def test_cli_mock_and_analyze(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["prepare", "--config", str(ROOT / "configs/query_form_gpt4o.json"), "--output", directory]), 0)
            self.assertEqual(main(["run", "--config", str(ROOT / "configs/query_form_gpt4o.json"), "--output", directory, "--mock", "--max-calls", "1"]), 0)
            self.assertEqual(main(["analyze", "--output", directory]), 0)


if __name__ == "__main__":
    unittest.main()
