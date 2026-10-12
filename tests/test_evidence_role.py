"""Offline design, inference, journal and CLI checks; never issue model calls."""

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

from exception_pilot import provider
from exception_pilot.core import check_plan, digest
from exception_pilot.storage import load_attempts, run_lock, write_json
from exception_evidence_role.analysis import PRIMARY, effect, summarize, write_summary
from exception_evidence_role.core import (
    CLASS_CONDITIONS, COMMON_INSTRUCTION, CONDITIONS, COPY_CLASS, DEFAULT_CONFIG,
    ENTRY_INSTRUCTIONS, KEY_ORDERS, ORDERS, PLATE_PREFIX, VALUES, load_config, make_plan,
    messages_for, read_plan, request_for, request_hash, response_format_for,
    score_response, table_for, task_meta, validate_config,
)
from exception_evidence_role.rationales import code_text
from exception_evidence_role.runner import mock_complete, normalized_response, prepare, read_run, run
from exception_evidence_role.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evidence_role_gpt4o.json"


def config():
    return load_config(CONFIG_PATH)


def response(text, finish="stop", model="MOCK-NOT-A-MODEL", mode="mock"):
    return normalized_response({"id": "fixture", "model": model, "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}, config(), mode)


def answer_response(task, first, answer, reason="Fixture explanation."):
    fields = {"first_value": first, "reasoning": reason, "final_answer": answer}
    return response(json.dumps({k: fields[k] for k in KEY_ORDERS[task["order"]]}))


def fixture(plan, choose=None):
    records = []
    for task in plan["tasks"]:
        result = mock_complete(plan, task)
        if choose is not None:
            result = choose(task, result)
        records.append({"attempt": len(records) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                        "config_hash": digest(plan["config"]), "mode": "mock", "request": request_for(plan, task),
                        "meta": task_meta(plan, task), "response": result, **score_response(task, result)})
    return records


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch.object(provider, "complete", side_effect=AssertionError("Live provider forbidden")))


class DesignTests(OfflineTest):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_determinism_hash_unique_tasks_and_balanced_labels(self):
        plan = self.plan
        self.assertEqual(plan, make_plan(config()))
        check_plan(plan)
        body = {k: v for k, v in plan.items() if k != "plan_hash"}
        self.assertEqual(digest(body), plan["plan_hash"])
        self.assertEqual((len(plan["worlds"]), len(plan["tasks"])), (24, 480))
        self.assertEqual(len({t["id"] for t in plan["tasks"]}), 480)
        plates = [x["id"] for w in plan["worlds"] for x in w["items"]]
        self.assertEqual(len(set(plates)), 240)
        self.assertTrue(all(p.startswith(PLATE_PREFIX) for p in plates))
        roles = Counter((tuple(w["roles"].values()), w["items"][w["target_index"]]["climate"]) for w in plan["worlds"])
        self.assertEqual((len(roles), set(roles.values())), (12, {2}))
        expected = Counter(itertools.product(VALUES, CONDITIONS, ORDERS))
        schedules = set()
        for w in plan["worlds"]:
            tasks = [t for t in plan["tasks"] if t["world_id"] == w["id"]]
            actual = [(t["value"], t["condition"], t["order"]) for t in tasks]
            self.assertEqual(Counter(actual), expected)
            schedules.add(tuple(actual))
        self.assertGreater(len(schedules), 1)

    def test_namespace_unused_by_existing_modules_and_historical_plans(self):
        import re
        for p in ROOT.glob("exception_*/core.py"):
            if p.parent.name == "exception_evidence_role":
                continue
            text = p.read_text()
            prefixes = re.findall(r'(?:item\["id"\]|PLATE_PREFIX|plate)\s*=\s*"([A-Z])"', text)
            self.assertNotIn(PLATE_PREFIX, prefixes, str(p))
        # Compare actual archived identities as well as literal assignments.
        from zipfile import ZipFile
        plates = {x["id"] for w in self.plan["worlds"] for x in w["items"]}
        for name in ("explanation-001.zip", "revision-001.zip", "cue-001.zip"):
            with ZipFile(ROOT / name) as archive:
                path = next(n for n in archive.namelist() if n.endswith("/plan.json"))
                old = json.loads(archive.read(path))
            self.assertFalse(plates & {x["id"] for w in old["worlds"] for x in w["items"]})

    def test_row_ten_and_unchanged_other_row_order(self):
        for w in self.plan["worlds"]:
            target = w["target_index"]
            self.assertEqual(w["order"][-1], target)
            self.assertEqual(w["order"][:-1], [i for i in w["original_order"] if i != target])
            self.assertEqual(sorted(w["order"]), list(range(10)))
            for value in VALUES:
                labels = w["record_labels"][value]
                self.assertEqual(labels[target], w["roles"][value])
                peers = [i for i, item in enumerate(w["items"]) if i != target and item["climate"] == w["items"][target]["climate"]]
                self.assertEqual([labels[i] for i in peers], [w["roles"]["pattern"]] * 4)
            self.assertEqual([i for i in range(10) if w["record_labels"][VALUES[0]][i] != w["record_labels"][VALUES[1]][i]], [target])

    def test_first_two_conditions_differ_only_by_role_phrase(self):
        self.assertTrue(ENTRY_INSTRUCTIONS["copy_record"].startswith(COPY_CLASS))
        self.assertEqual(ENTRY_INSTRUCTIONS["copy_record"].replace("recorded class", "initial answer"), ENTRY_INSTRUCTIONS["copy_initial"])
        for w in self.plan["worlds"]:
            for value, order in itertools.product(VALUES, ORDERS):
                task = {"world_id": w["id"], "value": value, "condition": "copy_record", "order": order}
                a = messages_for(self.plan, task)[0]["content"]
                b = messages_for(self.plan, {**task, "condition": "copy_initial"})[0]["content"]
                self.assertEqual(a.replace("Treat this entry as the recorded class.", "Treat this entry as the initial answer."), b)

    def test_order_changes_only_serialized_schema_properties(self):
        for task in self.plan["tasks"][::2]:
            left = request_for(self.plan, {**task, "order": ORDERS[0]})
            right = request_for(self.plan, {**task, "order": ORDERS[1]})
            self.assertEqual(left, right)  # Dict equality ignores order.
            self.assertNotEqual(request_hash(left), request_hash(right))
            lp = left["response_format"]["json_schema"]["schema"]["properties"]
            rp = right["response_format"]["json_schema"]["schema"]["properties"]
            right["response_format"]["json_schema"]["schema"]["properties"] = {k: rp[k] for k in lp}
            self.assertEqual(request_hash(left), request_hash(right))
            self.assertIn("Your final answer may match or differ", left["messages"][0]["content"])
            self.assertEqual(left["max_completion_tokens"], 1000)
            self.assertEqual(lp["first_value"], {"type": ["string", "null"]})
            self.assertEqual(left["messages"], right["messages"])

    def test_identical_tables_profiles_and_common_instruction_in_all_cells(self):
        for w in self.plan["worlds"]:
            for value in VALUES:
                tasks = [t for t in self.plan["tasks"] if t["world_id"] == w["id"] and t["value"] == value]
                prefixes, tables = set(), set()
                for task in tasks:
                    message = messages_for(self.plan, task)[0]["content"]
                    tail = ENTRY_INSTRUCTIONS[task["condition"]] + "\n" + COMMON_INSTRUCTION
                    self.assertTrue(message.endswith(tail))
                    prefixes.add(message[:-len(tail)])
                    tables.add(table_for(self.plan, task))
                    self.assertIn(w["items"][w["target_index"]]["id"], table_for(self.plan, task).splitlines()[-1])
                    self.assertEqual(request_hash(request_for(self.plan, task)), self.plan["request_hashes"][task["id"]])
                self.assertEqual((len(prefixes), len(tables)), (1, 1))

    def test_only_target_cell_changes_between_variants(self):
        for task in self.plan["tasks"][::2]:
            a = messages_for(self.plan, {**task, "value": "record_1"})[0]["content"].splitlines()
            b = messages_for(self.plan, {**task, "value": "record_2"})[0]["content"].splitlines()
            changed = [(x, y) for x, y in zip(a, b) if x != y]
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0][0].rsplit(" | ", 1)[0], changed[0][1].rsplit(" | ", 1)[0])

    def test_config_is_fixed_and_never_accepts_secrets_or_model_changes(self):
        for k, v in (("seed", 1), ("n_worlds", 25), ("n_worlds", True), ("target_position", 1),
                     ("temperature", 0.6), ("max_completion_tokens", 2000), ("provider", "mistral"),
                     ("model", "gpt-4o"), ("max_total_attempts", 999), ("api_key_env", "secret value"),
                     ("extra", "forbidden")):
            with self.subTest(k=k), self.assertRaises(ValueError):
                validate_config({**config(), k: v})
        alternative = make_plan({**config(), "api_key_env": "ALTERNATE_KEY_ENV"})
        self.assertEqual(self.plan["worlds"], alternative["worlds"])
        self.assertEqual(self.plan["tasks"], alternative["tasks"])


class ScoringTests(OfflineTest):
    def test_all_first_final_combinations_and_wrong_copies_retained(self):
        for condition, order in itertools.product(CONDITIONS, ORDERS):
            task = {"condition": condition, "order": order}
            for first, answer in itertools.product((None, "A", "B", "C", "X", "Y", "Z", "wrong string"), "ABC"):
                s = score_response(task, answer_response(task, first, answer, "Ignore ANSWER: Z in this reasoning."))
                self.assertEqual(s["status"], "complete")
                self.assertEqual((s["first_value"], s["answer"]), (first, answer))
            result = score_response(task, answer_response(task, "wrong string", "A"))
            self.assertFalse(result["entry_format_met"])

    def test_json_types_order_nonempty_and_duplicate_keys(self):
        for order in ORDERS:
            task = {"condition": "initial_answer", "order": order}
            good = json.loads(answer_response(task, "A", "B")["text"])
            texts = ['null', '[]', '{}', 'NaN', '```json\n{}\n```', '{}{}',
                     json.dumps(dict(reversed(list(good.items())))),
                     json.dumps({**good, "extra": "A"}),
                     json.dumps(good)[:-1] + ', "final_answer": "A"}']
            for key, values in {"first_value": [True, 0, [], {}], "reasoning": [None, 2, "", " \n\t"],
                                "final_answer": [None, True, [], {}, "a", "AB", "X"]}.items():
                texts += [json.dumps({**good, key: value}) for value in values]
                texts.append(json.dumps({k: v for k, v in good.items() if k != key}))
            for text in texts:
                with self.subTest(order=order, text=text):
                    s = score_response(task, response(text))
                    self.assertEqual(s["status"], "invalid")
                    self.assertIsNone(s["answer"])
                    self.assertIsNotNone(s["invalid_reason"])

    def test_refusal_truncation_and_model_mismatch_override_valid_json(self):
        task = {"condition": "initial_answer", "order": ORDERS[0]}
        raw = answer_response(task, "A", "A")["raw_response"]
        cases = [response(json.dumps({"first_value": "A", "reasoning": "x", "final_answer": "A"}), finish="length"),
                 normalized_response(raw, config(), "live")]
        refused = copy.deepcopy(raw)
        refused["choices"][0]["message"]["refusal"] = "declined"
        cases.append(normalized_response(refused, config(), "mock"))
        for result in cases:
            self.assertEqual(score_response(task, result)["status"], "invalid")
        self.assertTrue(cases[1]["model_mismatch"])


class AnalysisTests(OfflineTest):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(config())

    def test_all_correct_simulation_has_zero_harm_and_is_not_evidence(self):
        report, rows = summarize(self.plan, fixture(self.plan), "mock")
        self.assertEqual((len(rows), report["valid_answers"]), (480, 480))
        self.assertEqual(report["analysis_status"], "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE")
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual(report["decision"], "no_automatic_followup")
        self.assertTrue(all(e["mean"] == 0 for e in report["effects"].values()))
        self.assertEqual(report["effects"][PRIMARY]["n_worlds"], 24)
        self.assertNotIn("copy_marker/reason_then_answer", report["transitions"])
        self.assertEqual(report["cells"]["copy_marker/reason_then_answer"]["copy_correct"], 48)

    def test_planted_primary_and_bridge_interactions(self):
        def choose(task, result):
            meta = task_meta(self.plan, task)
            index = int(task["world_id"].rsplit("-", 1)[1])
            harmed = task["order"] == "reason_then_answer" and (
                task["condition"] == "initial_answer" and index < 12 or
                task["condition"] == "copy_initial" and index < 6)
            if harmed:
                return answer_response(task, meta["expected"], meta["pattern_label"])
            return result
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        e = report["effects"][PRIMARY]
        self.assertEqual(e["mean"], 0.5)
        self.assertEqual((e["positive_worlds"], e["negative_worlds"], e["ties"]), (12, 0, 12))
        self.assertAlmostEqual(e["sign_p"], 2 / 2**12)
        self.assertGreater(e["ci95"][0], 0)
        self.assertEqual(e["full_plan_bounds"], [0.5, 0.5])
        self.assertEqual(report["effects"]["accuracy/copied_initial_minus_record_reasoning_harm"]["mean"], 0.25)
        self.assertEqual(report["transitions"]["initial_answer/reason_then_answer"]["correct_to_wrong"], 24)

    def test_other_label_sensitivity_and_constant_answer_pairs(self):
        def choose(task, result):
            if task["condition"] == "copy_marker":
                meta = task_meta(self.plan, task)
                return answer_response(task, meta["target_marker"], "A")
            return result
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        cell = report["cells"]["copy_marker/reason_then_answer"]
        self.assertEqual(cell["record_sensitivity"]["mean"], 0)
        self.assertEqual(cell["final_answer_unchanged"], 24)
        self.assertEqual(cell["accuracy"]["mean"], 1/3)
        self.assertEqual(cell["copy_correct"], 48)

    def test_wrong_copies_and_non_label_first_entries_do_not_select_cases(self):
        def choose(task, result):
            if task["condition"] in CLASS_CONDITIONS:
                return answer_response(task, None, task_meta(self.plan, task)["expected"])
            return result
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        self.assertEqual(report["valid_answers"], 480)
        self.assertEqual(report["effects"][PRIMARY]["mean"], 0)
        c = report["cells"]["copy_record/reason_then_answer"]
        self.assertEqual((c["copy_correct"], c["correct"], c["entry_format_met"]), (0, 48, 0))
        self.assertEqual(report["transitions"]["initial_answer/reason_then_answer"]["non_label_to_correct"], 48)

    def test_invalid_and_pending_bounds_and_contrast_specific_world_counts(self):
        records = fixture(self.plan)
        idx = next(i for i, r in enumerate(records) if r["meta"]["condition"] == "initial_answer" and r["meta"]["order"] == ORDERS[0])
        r = records[idx]
        r.update(response=response("broken"), **score_response(r["meta"], response("broken")))
        report, _ = summarize(self.plan, records)
        self.assertEqual(report["invalid_answers"], 1)
        self.assertFalse(report["interpretation_allowed"])
        self.assertEqual(report["analysis_status"], "output_manipulation_inconclusive")
        e = report["effects"][PRIMARY]
        self.assertEqual(e["n_worlds"], 23)
        self.assertEqual(e["full_plan_bounds"], [0, 1/48])
        self.assertEqual(report["effects"]["accuracy/copied_initial_minus_record_reasoning_harm"]["n_worlds"], 24)
        records.pop(idx)
        report, _ = summarize(self.plan, records)
        self.assertEqual((report["pending_answers"], report["invalid_answers"]), (1, 0))
        self.assertEqual(report["effects"][PRIMARY]["full_plan_bounds"], [0, 1/48])

    def test_sign_test_ties_empty_and_degenerate_intervals(self):
        self.assertEqual(effect([1, 1, 0, -1])["sign_p"], 1)
        self.assertEqual(effect([0] * 24)["sign_p"], 1)
        self.assertEqual(effect([0] * 24)["ci95"], [0, 0])
        self.assertIsNone(effect([])["mean"])
        self.assertIsNone(effect([1])["ci95"])

    def test_rationale_flags_are_separate_from_answer_accuracy(self):
        for text, answer, expected_code in (
            ("Feature comparisons only.", "A", "never_stated"),
            ("J12345: MISSING", "A", "relabeled_missing"),
            ("J12345 class A is recorded.", "B", "stated_then_overridden"),
            ("J12345 class A is recorded.", "A", "stated_and_followed"),
            ("J12345 is not missing; class A.", "A", "stated_and_followed"),
            ("If J12345 were MISSING, prediction would apply.", "A", "never_stated"),
            ("J12345 class A.\nJ12345: MISSING", "A", "relabeled_missing")):
            with self.subTest(text=text):
                self.assertEqual(code_text(text, "J12345", "A", answer)["rationale_code"], expected_code)
        def choose(task, result):
            obj = json.loads(result["text"])
            return answer_response(task, obj["first_value"], obj["final_answer"], f"{task_meta(self.plan, task)['item_id']}: MISSING")
        report, _ = summarize(self.plan, fixture(self.plan, choose))
        c = report["rationale_counts"]["copy_record/reason_then_answer"]
        self.assertEqual((c["missing_candidates"], c["missing_and_correct"]), (48, 48))


class RunnerTests(OfflineTest):
    def setUp(self):
        super().setUp()
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.output = Path(self.tmp) / "run"
        self.silent = self.enterContext(redirect_stdout(io.StringIO()))

    def test_prepare_and_analyze_need_no_credentials_network_or_attempts(self):
        with patch.object(provider, "credential", side_effect=AssertionError("No credential lookup")):
            self.assertEqual(main(["prepare", "--config", str(CONFIG_PATH), "--output", str(self.output)]), 0)
            self.assertEqual(main(["analyze", "--output", str(self.output)]), 0)
        self.assertFalse((self.output / "attempts").exists())
        plan = read_plan(self.output)
        preview = json.loads((self.output / "preview.json").read_text())
        self.assertEqual(len(preview), 480)
        self.assertEqual((self.output / "preview.md").read_text().count("## er-list-000/"), 20)
        self.assertEqual([x["request_sha256"] for x in preview], [plan["request_hashes"][t["id"]] for t in plan["tasks"]])
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertEqual(summary["analysis_status"], "prepared_not_run")

    def test_full_mock_resume_and_rationale_exports(self):
        first = run(config(), self.output, 20, mock=True)
        self.assertEqual((first["calls_this_invocation"], first["stopped"]), (20, "call_limit"))
        with self.assertRaises(ValueError):
            run(config(), self.output, 20, mock=True)
        original = (self.output / "attempts/000001.json").read_bytes()
        rest = run(config(), self.output, 480, resume=True, mock=True)
        self.assertEqual((rest["calls_this_invocation"], rest["attempts_total"], rest["stopped"]), (460, 480, "complete"))
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), original)
        self.assertEqual(run(config(), self.output, 10, resume=True, mock=True)["calls_this_invocation"], 0)
        summary = write_summary(self.output)
        self.assertFalse(summary["interpretation_allowed"])
        self.assertEqual(summary["effects"][PRIMARY]["mean"], 0)
        text = (self.output / "rationale_review.md").read_text()
        self.assertEqual(text.count("## review-"), 480)
        self.assertNotIn("er-list-", text)
        self.assertTrue(all((self.output / name).exists() for name in ("summary.json", "summary.md", "answers.csv", "rationales.csv", "rationale_key.csv")))
        self.assertFalse(list(self.output.rglob("*.tmp")))

    def test_invalid_return_is_retained_collection_continues_and_never_retried(self):
        calls = []
        def invalid(config_, payload):
            calls.append(payload)
            return response("not JSON")
        run(config(), self.output, 2, mock=True, complete_fn=invalid)
        first = (self.output / "attempts/000001.json").read_bytes()
        result = run(config(), self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual(result["attempts_total"], 3)
        self.assertEqual(result["invalid_answers_retained"], 2)
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), first)
        _, _, attempts = read_run(self.output)
        self.assertEqual(len({a["task_id"] for a in attempts}), 3)

    def test_transport_error_requires_explicit_retry_and_keeps_error_attempt(self):
        def broken(config_, payload):
            raise provider.ProviderError("HTTP 503", 503)
        first = run(config(), self.output, 10, mock=True, complete_fn=broken)
        self.assertEqual(first["stopped"], "provider_error")
        self.assertEqual(run(config(), self.output, 10, resume=True, mock=True)["stopped"], "retry_requires_flag")
        before = (self.output / "attempts/000001.json").read_bytes()
        resumed = run(config(), self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual(resumed["attempts_total"], 2)
        _, _, attempts = read_run(self.output)
        self.assertEqual(attempts[0]["task_id"], attempts[1]["task_id"])
        self.assertEqual((self.output / "attempts/000001.json").read_bytes(), before)

    def test_unresolved_attempt_cannot_be_retried(self):
        def interrupted(config_, payload):
            raise KeyboardInterrupt
        self.assertEqual(run(config(), self.output, 1, mock=True, complete_fn=interrupted)["stopped"], "interrupted")
        result = run(config(), self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((result["stopped"], result["attempts_total"]), ("unresolved_attempt_requires_review", 1))

    def test_live_model_mismatch_is_permanent_stop_without_real_network(self):
        with patch.object(provider, "credential", return_value="fake"), patch.object(provider, "complete", return_value=response("{}")):
            result = run(config(), self.output, 20)
        self.assertEqual((result["stopped"], result["attempts_total"]), ("model_mismatch", 1))
        with self.assertRaises(ValueError):
            run(config(), self.output, 1, resume=True, retry_errors=True)

    def test_config_source_mode_and_hash_changes_block_resume(self):
        run(config(), self.output, 1, mock=True)
        with self.assertRaises(ValueError):
            run({**config(), "api_key_env": "ANOTHER_ENV"}, self.output, 1, resume=True, mock=True)
        with self.assertRaises(ValueError):
            run(config(), self.output, 1, resume=True)
        with patch("exception_evidence_role.core.source_digest", return_value="changed"), self.assertRaises(ValueError):
            read_run(self.output)
        plan = json.loads((self.output / "plan.json").read_text())
        plan["worlds"][0]["order"].reverse()
        write_json(self.output / "plan.json", plan)
        with self.assertRaises(ValueError):
            read_plan(self.output)

    def test_tampered_schema_order_score_or_returned_error_is_rejected(self):
        run(config(), self.output, 1, mock=True)
        path = self.output / "attempts/000001.json"
        original = json.loads(path.read_text())
        bad = copy.deepcopy(original)
        schema = bad["request"]["response_format"]["json_schema"]["schema"]
        schema["properties"] = dict(reversed(list(schema["properties"].items())))
        variants = [bad, {**original, "answer": "Z"}, {**original, "status": "error"}]
        for bad in variants:
            write_json(path, bad)
            with self.assertRaises(ValueError):
                read_run(self.output)
        write_json(path, original)
        read_run(self.output)

    def test_attempt_cap_counts_failed_attempts_and_blocks_network(self):
        with run_lock(self.output):
            plan = prepare(config(), self.output)
            write_json(self.output / "execution.json", {"mode": "mock", "plan_hash": plan["plan_hash"],
                "protocol_version": plan["protocol_version"], "config_hash": digest(config())})
            task = plan["tasks"][0]
            for i in range(528):
                write_json(self.output / "attempts" / f"{i+1:06d}.json", {
                    "attempt": i+1, "task_id": task["id"], "plan_hash": plan["plan_hash"], "config_hash": digest(config()),
                    "mode": "mock", "status": "error", "error": "HTTP 503", "http_status": 503,
                    "request": request_for(plan, task), "meta": task_meta(plan, task)})
        result = run(config(), self.output, 1, resume=True, retry_errors=True, mock=True)
        self.assertEqual((result["calls_this_invocation"], result["stopped"]), (0, "total_attempt_limit"))

    def test_lock_nonempty_directory_and_injected_live_provider_rejected(self):
        with run_lock(self.output), self.assertRaises(ValueError):
            run(config(), self.output, 1, mock=True)
        with self.assertRaises(ValueError):
            run(config(), self.output, 1, complete_fn=lambda c, p: None)
        with self.assertRaises(ValueError):
            run(config(), self.output, 1, retry_errors=True, mock=True)
        (self.output / "unrelated.txt").write_text("retain")
        with self.assertRaises(ValueError):
            prepare(config(), self.output)
        self.assertEqual((self.output / "unrelated.txt").read_text(), "retain")


if __name__ == "__main__":
    unittest.main()
