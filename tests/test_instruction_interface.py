"""Offline contract tests; sockets and live transport are forbidden throughout."""

from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.core import digest
from exception_pilot.storage import write_json
from exception_instruction_interface.analysis import bootstrap_worlds, summarize, world_interactions, write_summary
from exception_instruction_interface.core import (
    CONDITIONS, DATA, DEFAULT_CONFIG, FIELD_ORDER, TEXT_INSTRUCTION, VALUES,
    load_source, make_plan, read_plan, request_for, request_hash, task_meta, validate_config,
)
from exception_instruction_interface.runner import mock_complete, normalized_response, prepare, read_run, run
from exception_instruction_interface.scoring import score_response
from exception_instruction_interface.__main__ import main


def response(text, finish="stop", model="MOCK-NOT-A-MODEL", mode="mock"):
    return normalized_response({"id": "fixture", "model": model, "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]},
        DEFAULT_CONFIG, mode)


def task(interface="json", expected="A"):
    return {"interface": interface, "expected": expected}


def fixture(plan, choose=None):
    records = []
    for t in plan["tasks"]:
        result = mock_complete(plan, t) if choose is None else choose(t)
        records.append({"attempt": len(records) + 1, "task_id": t["id"], "response": result,
                        **score_response(t, result)})
    return records


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch.object(provider, "complete", side_effect=AssertionError("Paid calls forbidden")))
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))


class DesignTests(OfflineTest):
    def test_exact_factorial_and_deterministic_block_schedule(self):
        plan = make_plan(DEFAULT_CONFIG)
        self.assertEqual(plan, make_plan(DEFAULT_CONFIG))
        self.assertEqual(len(plan["tasks"]), 192)
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 192)
        self.assertEqual(Counter((t["instruction"], t["interface"]) for t in plan["tasks"]),
                         Counter({c: 48 for c in CONDITIONS}))
        blocks = []
        for i in range(0, 192, 4):
            cells = plan["tasks"][i:i + 4]
            self.assertEqual({(t["instruction"], t["interface"]) for t in cells}, set(CONDITIONS))
            self.assertEqual(len({(t["world_id"], t["value"]) for t in cells}), 1)
            self.assertEqual({t["block_index"] for t in cells}, {i // 4})
            blocks.append((cells[0]["world_id"], cells[0]["value"]))
        self.assertEqual(set(blocks), set(itertools.product([w["id"] for w in plan["worlds"]], VALUES)))
        self.assertNotEqual(blocks, sorted(blocks))
        self.assertGreater(len({tuple((t["instruction"], t["interface"]) for t in plan["tasks"][i:i + 4])
                                for i in range(0, 192, 4)}), 1)

    def test_no_replacement_world_generation_and_original_provenance(self):
        with patch("exception_evidence_role.core.make_world", side_effect=AssertionError("Regeneration forbidden")):
            plan = make_plan(DEFAULT_CONFIG)
        source, original = load_source()
        self.assertEqual(plan["worlds"], original["worlds"])
        self.assertEqual(source["provenance"]["source_run"], "evidence-role-gpt4o-001")
        self.assertEqual(hashlib.sha256((DATA / "evidence_role_source_plan.json").read_bytes()).hexdigest(),
                         source["provenance"]["plan_file_sha256"])
        self.assertEqual(len(source["stimuli"]), 48)

    def test_all_matched_stimuli_and_original_json_requests_are_verbatim(self):
        from exception_evidence_role.core import request_for as old_request
        source, original = load_source()
        plan = make_plan(DEFAULT_CONFIG)
        for s in source["stimuli"]:
            matched = [t for t in plan["tasks"] if (t["world_id"], t["value"]) == (s["world_id"], s["value"])]
            for t in matched:
                req = request_for(plan, t)
                old_task = {"world_id": t["world_id"], "value": t["value"],
                            "condition": t["instruction"], "order": "reason_then_answer"}
                old = old_request(original, old_task)
                instruction = source["entry_instructions"][t["instruction"]]
                output = source["json_instruction"] if t["interface"] == "json" else TEXT_INSTRUCTION
                self.assertEqual(req["messages"][0]["content"], s["prompt_stem"] + instruction + "\n" + output)
                self.assertIn("MISSING means the verified class has not been recorded.", s["prompt_stem"])
                self.assertEqual(task_meta(plan, t)["target_position"], 10)
                self.assertEqual(req["messages"], [{"role": "user", "content": req["messages"][0]["content"]}])
                if t["interface"] == "json":
                    self.assertEqual(req, old)
                    self.assertEqual(request_hash(req), s["source_request_hashes"][f"{t['world_id']}/{t['value']}/{t['instruction']}/reason_then_answer"])
                else:
                    self.assertNotIn("response_format", req)
                    for k in ("model", "temperature", "max_completion_tokens", "n", "store"):
                        self.assertEqual(req[k], old[k])
            world = next(w for w in plan["worlds"] if w["id"] == s["world_id"])
            self.assertEqual(world["order"][-1], world["target_index"])

    def test_exact_instructions_unrestricted_schema_and_order_sensitive_hash(self):
        source, _ = load_source()
        self.assertEqual(source["entry_instructions"], {
            "copy_record": "Copy the target vehicle's Verified class cell exactly into first_value. Treat this entry as the recorded class.",
            "initial_answer": "Give your initial answer to the class question in first_value."})
        self.assertEqual(TEXT_INSTRUCTION, 'Output only plain text with the fields "first_value", "reasoning", and "final_answer", in that order. Begin each field on a new line using "field_name: value". Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. Your final answer may match or differ from the preliminary entry.')
        schema = source["json_response_format"]["json_schema"]
        self.assertTrue(schema["strict"])
        props = schema["schema"]["properties"]
        self.assertEqual(tuple(props), FIELD_ORDER)
        self.assertEqual(props["first_value"], {"type": ["string", "null"]})
        self.assertEqual(props["final_answer"], {"type": "string", "enum": ["A", "B", "C"]})
        reverse = copy.deepcopy(schema)
        reverse["schema"]["properties"] = dict(reversed(list(props.items())))
        self.assertEqual(schema, reverse)
        self.assertNotEqual(request_hash(schema), request_hash(reverse))

    def test_config_fixed_and_secrets_never_accepted(self):
        for k, v in (("model", "gpt-4o"), ("temperature", 0.1), ("block_seed", 7),
                     ("bootstrap_seed", 7), ("n_worlds", True), ("max_total_attempts", 999),
                     ("extra", "x"), ("api_key_env", "secret value")):
            with self.subTest(key=k), self.assertRaises(ValueError):
                validate_config({**DEFAULT_CONFIG, k: v})


class ScoringTests(OfflineTest):
    def test_all_first_categories_raw_preserved_and_failures_retained(self):
        cases = [(" A \n", "correct_class"), ("B", "wrong_abc_class"), ("MISSING", "MISSING"),
                 (None, "null"), ("null", "other_emitted_value"), ("a", "other_emitted_value"),
                 ("\u00a0A", "other_emitted_value"), ("", "other_emitted_value"),
                 (3, "other_emitted_value"), (False, "other_emitted_value"),
                 (["A"], "other_emitted_value"), ({"answer": "A"}, "other_emitted_value")]
        for value, expected in cases:
            with self.subTest(value=value):
                s = score_response(task(), response(json.dumps({"first_value": value, "reasoning": "r", "final_answer": "B"})))
                self.assertEqual(s["first_category"], expected)
                self.assertEqual(s["first_value_raw"], value)
                self.assertEqual(s["first_correct"], expected == "correct_class")
                self.assertEqual(s["output_contract_met"], isinstance(value, str) or value is None)

    def test_json_first_survives_invalid_or_truncated_suffix(self):
        for text in ('{"first_value":"A", "reasoning":', '{"first_value":"A"',
                     '{"first_value":"A" THIS IS INVALID',
                     '{"first_value":"A", "first_value":"B"}',
                     '{"first_value":"A", "reasoning":"unterminated'):
            for finish in ("stop", "length"):
                with self.subTest(text=text, finish=finish):
                    s = score_response(task(), response(text, finish))
                    self.assertTrue(s["first_correct"])
                    self.assertFalse(s["output_contract_met"])
                    self.assertIsNone(s["answer"])

    def test_never_recover_first_from_other_fields_or_prefaces(self):
        for interface, texts in {
            "json": ['{"reasoning":"A", "first_value":"A", "final_answer":"A"}',
                     '```json\n{"first_value":"A"}', '{"first_value":"A',
                     '{"first_value":nul', '{"first_value":nullx}', '{"first_value":1e}',
                     '{"first_value":NaN}', '{"first_value":1e999}', 'null'],
            "text": ['reasoning: A\nfirst_value: A\nfinal_answer: A',
                     'Here is the result:\nfirst_value: A', 'FIRST_VALUE: A', 'A\nfinal_answer: A',
                     '```text\nfirst_value: A\nreasoning: r\nfinal_answer: A']}.items():
            for text in texts:
                with self.subTest(interface=interface, text=text):
                    s = score_response(task(interface), response(text))
                    self.assertFalse(s["first_emitted"])
                    self.assertEqual(s["first_category"], "absent_or_unparseable")

    def test_bare_json_scalar_completion_boundary(self):
        for value in ("null", "true", "false", "17"):
            self.assertEqual(score_response(task(), response('{"first_value":' + value, "length"))["first_emitted"], value != "17")
            self.assertTrue(score_response(task(), response('{"first_value":' + value + ',', "length"))["first_emitted"])
            self.assertTrue(score_response(task(), response('{"first_value":' + value))["first_emitted"])

    def test_text_first_survives_truncation_only_when_complete_line(self):
        for suffix in ("\nreasoning: truncated", "\r\nbroken output", "\n", "\nfinal_answer: B"):
            s = score_response(task("text"), response("first_value: A" + suffix, "length"))
            self.assertTrue(s["first_correct"])
            self.assertFalse(s["output_contract_met"])
        self.assertFalse(score_response(task("text"), response("first_value: A", "length"))["first_emitted"])
        self.assertTrue(score_response(task("text"), response("first_value: A"))["first_correct"])

    def test_text_categories_contract_and_no_quote_or_case_repair(self):
        for value, cat in (("A", "correct_class"), ("B", "wrong_abc_class"), ("MISSING", "MISSING"),
                           ("null", "null"), ('"A"', "other_emitted_value"), ("a", "other_emitted_value"),
                           ("A reasoning: r", "other_emitted_value"), ("", "other_emitted_value")):
            s = score_response(task("text"), response(f" \nfirst_value: {value}\r\nreasoning: line one\nline two\nfinal_answer: B\n"))
            self.assertEqual(s["first_category"], cat)
            self.assertTrue(s["output_contract_met"])
            self.assertEqual(s["correct_first_wrong_final"], value == "A")

    def test_text_duplicate_keys_misordering_extra_suffix_and_reasoning_mentions(self):
        for suffix in ("reasoning: r\nfinal_answer: A\nextra", "final_answer: A\nreasoning: r",
                       "reasoning: r\nfirst_value: B\nfinal_answer: A", "reasoning: r\nfinal_answer: A\nfinal_answer: B"):
            s = score_response(task("text"), response("first_value: A\n" + suffix))
            self.assertTrue(s["first_correct"])
            self.assertFalse(s["output_contract_met"])
        s = score_response(task("text"), response('first_value: A\nreasoning: quote "final_answer: B" here\nfinal_answer: C'))
        self.assertEqual(s["answer"], "C")
        self.assertTrue(s["output_contract_met"])

    def test_truncated_final_and_model_identity_do_not_pass_contract(self):
        s = score_response(task("text"), response("first_value: A\nreasoning: r\nfinal_answer: B", "length"))
        self.assertTrue(s["first_correct"])
        self.assertIsNone(s["answer"])
        s = score_response(task("text"), response("first_value: A\nreasoning: r\nfinal_answer: B\n", "length"))
        self.assertEqual(s["answer"], "B")
        self.assertFalse(s["output_contract_met"])
        r = response('{"first_value":"A","reasoning":"r","final_answer":"A"}', model="other", mode="live")
        self.assertTrue(r["model_mismatch"])
        self.assertFalse(score_response(task(), r)["output_contract_met"])


class AnalysisTests(OfflineTest):
    def test_paired_world_interaction_and_bootstrap_match_explicit_resampling(self):
        plan = make_plan(DEFAULT_CONFIG)
        def choose(t):
            i = int(t["world_id"].rsplit("-", 1)[1])
            good = ((i + (t["value"] == "record_2") + (t["instruction"] == "initial_answer")
                     + 2 * (t["interface"] == "json")) % 4) != 0
            value = t["expected"] if good else next(c for c in "ABC" if c != t["expected"])
            text = json.dumps({"first_value": value, "reasoning": "r", "final_answer": value}) if t["interface"] == "json" else f"first_value: {value}\nreasoning: r\nfinal_answer: {value}"
            return response(text)
        records = fixture(plan, choose)
        report, _ = summarize(plan, records, "mock")
        by_id = {r["task_id"]: r for r in records}
        worlds = world_interactions(plan, by_id)
        explicit = []
        for w in plan["worlds"]:
            contrast = 0
            for value, instruction, interface in itertools.product(VALUES, ("copy_record", "initial_answer"), ("text", "json")):
                r = by_id[f"{w['id']}/{value}/{instruction}/{interface}"]
                sign = (1 if instruction == "initial_answer" else -1) * (1 if interface == "json" else -1)
                contrast += sign * r["first_correct"] / 2
            explicit.append(contrast)
        self.assertEqual([w["interaction"] for w in worlds], explicit)
        rng = random.Random(DEFAULT_CONFIG["bootstrap_seed"])
        draws = sorted(sum(explicit[i] for i in rng.choices(range(24), k=24)) / 24 for _ in range(10000))
        expected_ci = []
        for p in (.025, .975):
            x = 9999 * p; low = int(x)
            expected_ci.append(draws[low] + (x - low) * (draws[low + 1] - draws[low]))
        self.assertEqual(report["primary"]["estimate"], sum(explicit) / 24)
        self.assertEqual(report["primary"]["ci95"], expected_ci)
        self.assertEqual(report["primary"]["resampling_unit"], "whole_world")
        self.assertEqual(bootstrap_worlds(worlds, DEFAULT_CONFIG["bootstrap_seed"], 10000)["ci95"], expected_ci)

    def test_interaction_sign_and_both_variants_average_within_world(self):
        plan = make_plan(DEFAULT_CONFIG)
        def choose(t):
            good = not (t["interface"] == "json" and t["instruction"] == "copy_record" and t["value"] == "record_2")
            first = t["expected"] if good else "MISSING"
            return response(json.dumps({"first_value": first, "reasoning": "r", "final_answer": t["expected"]})
                            if t["interface"] == "json" else f"first_value: {first}\nreasoning: r\nfinal_answer: {t['expected']}")
        report, _ = summarize(plan, fixture(plan, choose), "mock")
        self.assertEqual(report["primary"]["estimate"], .5)
        self.assertEqual(report["primary"]["ci95"], [.5, .5])
        self.assertFalse(report["interpretation_allowed"])

    def test_invalid_suffix_retained_and_transport_missing_not_incorrect(self):
        plan = make_plan(DEFAULT_CONFIG)
        records = fixture(plan)
        t = plan["tasks"][0]
        r = response('{"first_value":' + json.dumps(t["expected"]) + ', bad' if t["interface"] == "json"
                     else f"first_value: {t['expected']}\nbad", "length")
        records[0].update(response=r, **score_response(t, r))
        report, _ = summarize(plan, records, "mock")
        self.assertEqual(report["primary"]["estimate"], 0)
        self.assertEqual(report["invalid_answers"], 1)
        self.assertEqual(sum(c["first_correct"] for c in report["conditions"].values()), 192)
        partial = records[:191] + [{"task_id": records[-1]["task_id"], "status": "error"}]
        report, _ = summarize(plan, partial, "live")
        self.assertEqual(report["returned_answers"], 191)
        self.assertEqual(report["missing_responses"], 1)
        self.assertEqual(report["transport_errors"], 1)
        self.assertEqual(report["primary"]["status"], "INCOMPLETE")
        self.assertIsNone(report["primary"]["estimate"])
        self.assertIsNone(report["primary"]["ci95"])
        self.assertEqual(sum(c["first_correct"] for c in report["conditions"].values()), 191)


class JournalTests(OfflineTest):
    def test_plan_preview_analyze_offline_and_live_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "run"
            cfg = Path(folder) / "config.json"; write_json(cfg, DEFAULT_CONFIG)
            self.assertEqual(main(["plan", "--config", str(cfg), "--output", str(out)]), 0)
            plan = read_plan(out)
            preview = json.loads((out / "preview.json").read_text())
            self.assertEqual(len(preview), 192)
            self.assertEqual([p["request"] for p in preview], [request_for(plan, t) for t in plan["tasks"]])
            self.assertEqual((out / "preview.md").read_text().count("## er-list-"), 192)
            self.assertEqual(main(["preview", "--output", str(out)]), 0)
            self.assertEqual(main(["analyze", "--output", str(out)]), 0)
            self.assertFalse((out / "execution.json").exists())
            self.assertEqual(json.loads((out / "summary.json").read_text())["primary"]["status"], "INCOMPLETE")
            with self.assertRaises(SystemExit):
                main(["run", "--config", str(cfg), "--output", str(out), "--max-calls", "1"])
            with self.assertRaises(ValueError):
                run(DEFAULT_CONFIG, out, 1)
            self.assertFalse((out / "execution.json").exists())

    def test_resume_preserves_all_returned_including_invalid_first_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            def invalid(_, req):
                return response("No parseable entry here")
            run(DEFAULT_CONFIG, folder, 1, mock=True, complete_fn=invalid)
            first = (Path(folder) / "attempts/000001.json").read_bytes()
            result = run(DEFAULT_CONFIG, folder, 191, mock=True, resume=True)
            self.assertEqual(result["returned_answers"], 192)
            self.assertEqual(result["invalid_answers_retained"], 1)
            self.assertEqual((Path(folder) / "attempts/000001.json").read_bytes(), first)
            again = run(DEFAULT_CONFIG, folder, 192, mock=True, resume=True)
            self.assertEqual(again["calls_this_invocation"], 0)
            traces = [json.loads(line) for line in (Path(folder) / "traces.jsonl").read_text().splitlines()]
            self.assertEqual(len(traces), 192)
            self.assertTrue(all(t["manual_contradiction_recognition"] is None for t in traces))
            self.assertEqual(traces[0]["attempts"][0]["response"]["raw_response"]["choices"][0]["message"]["content"], "No parseable entry here")

    def test_error_retries_explicit_and_missing_until_returned(self):
        with tempfile.TemporaryDirectory() as folder:
            def fail(_, req):
                raise provider.ProviderError("fixture transport failure", 503)
            first = run(DEFAULT_CONFIG, folder, 2, mock=True, complete_fn=fail)
            self.assertEqual(first["returned_answers"], 0)
            self.assertEqual(first["calls_this_invocation"], 1)
            saved = (Path(folder) / "attempts/000001.json").read_bytes()
            retry = run(DEFAULT_CONFIG, folder, 1, mock=True, resume=True)
            self.assertEqual(retry["stopped"], "retry_requires_flag")
            self.assertEqual(retry["calls_this_invocation"], 0)
            retry = run(DEFAULT_CONFIG, folder, 1, mock=True, resume=True, retry_errors=True)
            self.assertEqual(retry["returned_answers"], 1)
            self.assertEqual((Path(folder) / "attempts/000001.json").read_bytes(), saved)
            self.assertEqual(write_summary(folder)["transport_errors"], 1)

    def test_unresolved_attempt_cannot_be_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            def interrupt(_, req):
                raise KeyboardInterrupt()
            result = run(DEFAULT_CONFIG, folder, 1, mock=True, complete_fn=interrupt)
            self.assertEqual(result["stopped"], "interrupted")
            result = run(DEFAULT_CONFIG, folder, 1, mock=True, resume=True, retry_errors=True)
            self.assertEqual(result["stopped"], "unresolved_attempt_requires_review")
            self.assertEqual(result["calls_this_invocation"], 0)

    def test_order_tamper_and_raw_score_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run(DEFAULT_CONFIG, folder, 1, mock=True)
            p = Path(folder) / "plan.json"; plan = json.loads(p.read_text())
            t = next(t for t in plan["tasks"] if t["interface"] == "json")
            schema = plan["requests"][t["id"]]["response_format"]["json_schema"]["schema"]
            schema["properties"] = dict(reversed(list(schema["properties"].items())))
            # The old sorted digest cannot see this change; ordered validation must.
            self.assertEqual(digest({k: v for k, v in plan.items() if k != "plan_hash"}), plan["plan_hash"])
            write_json(p, plan)
            with self.assertRaises(ValueError):
                read_run(folder)
        with tempfile.TemporaryDirectory() as folder:
            run(DEFAULT_CONFIG, folder, 1, mock=True)
            p = Path(folder) / "attempts/000001.json"; record = json.loads(p.read_text())
            record["first_correct"] = False; write_json(p, record)
            with self.assertRaises(ValueError):
                read_run(folder)

    def test_mock_live_mix_and_restart_without_resume_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run(DEFAULT_CONFIG, folder, 1, mock=True)
            with self.assertRaises(ValueError):
                run(DEFAULT_CONFIG, folder, 1, mock=True)
            with self.assertRaises(ValueError):
                run(DEFAULT_CONFIG, folder, 1, live=True, resume=True)
            with self.assertRaises(ValueError):
                run(DEFAULT_CONFIG, folder, 1, mock=True, live=True)

    def test_cumulative_attempt_cap_cannot_be_extended_on_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = prepare(DEFAULT_CONFIG, folder)
            write_json(Path(folder) / "execution.json", {
                "mode": "mock", "protocol_version": plan["protocol_version"],
                "plan_hash": plan["plan_hash"], "config_hash": digest(DEFAULT_CONFIG)})
            t = plan["tasks"][0]
            for i in range(212):
                write_json(Path(folder) / "attempts" / f"{i+1:06d}.json", {
                    "attempt": i + 1, "task_id": t["id"], "plan_hash": plan["plan_hash"],
                    "mode": "mock", "status": "error", "error": "offline transport fixture",
                    "config_hash": digest(DEFAULT_CONFIG), "request": request_for(plan, t),
                    "meta": task_meta(plan, t)})
            result = run(DEFAULT_CONFIG, folder, 999, mock=True, resume=True, retry_errors=True)
            self.assertEqual(result["calls_this_invocation"], 0)
            self.assertEqual(result["stopped"], "total_attempt_limit")
            self.assertEqual(result["returned_answers"], 0)

    def test_model_mismatch_stops_and_cannot_resume_or_count_as_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            wrong = response('{"first_value":"A","reasoning":"r","final_answer":"A"}',
                             model="unexpected-model", mode="live")
            with patch.object(provider, "credential", return_value="OFFLINE-TEST-ONLY"), \
                    patch.object(provider, "complete", return_value=wrong) as mocked_transport:
                result = run(DEFAULT_CONFIG, folder, 192, live=True)
            self.assertEqual(mocked_transport.call_count, 1)
            self.assertEqual(result["stopped"], "model_mismatch")
            report = write_summary(folder)
            self.assertFalse(report["model_identity_ok"])
            self.assertFalse(report["interpretation_allowed"])
            self.assertEqual(report["primary"]["status"], "INCOMPLETE")
            with self.assertRaises(ValueError):
                run(DEFAULT_CONFIG, folder, 192, live=True, resume=True)


if __name__ == "__main__":
    unittest.main()
