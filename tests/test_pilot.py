"""Offline checks of experimental invariants, scoring, HTTP shape and recovery."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot import provider
from exception_pilot.analysis import summarize
from exception_pilot.core import (load_config, make_plan, messages_for, items_for, parse_answer,
                                  payload_for, task_meta, world_for)
from exception_pilot.runner import run, mock_complete
from exception_pilot.storage import (read_plan, load_attempts, run_lock, write_json)

ROOT = Path(__file__).resolve().parents[1]


def config(stage=1, n=20):
    value = load_config(ROOT / "configs" / f"stage{stage}.json")
    value["n_lists"] = n
    return value


def completed_fixture(plan, rule_bias=True):
    entries = []
    for i, task in enumerate(plan["tasks"]):
        label = task_meta(plan, task)["expected"]
        response = mock_complete(plan, task, {})
        if not rule_bias:
            response["text"] = label
        answer = parse_answer(response["text"])
        entries.append({"attempt": i+1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                        "status": "complete", "answer": answer, "response": response})
    return entries


class DataTests(unittest.TestCase):
    def test_counts_and_reproducibility(self):
        for stage, calls in ((1, 1200), (2, 320)):
            p = make_plan(config(stage))
            self.assertEqual(p, make_plan(config(stage)))
            self.assertEqual(len(p["tasks"]), calls)
            self.assertEqual(len({t["id"] for t in p["tasks"]}), calls)

    def test_balance_and_exactly_two_stable_exceptions(self):
        p = make_plan(config())
        plates = []
        for w in p["worlds"]:
            self.assertEqual(sum(x["label"] == "A" for x in w["items"]), 5)
            self.assertEqual(sum(x["is_exception"] for x in w["items"]), 2)
            for climate in ("cold", "warm"):
                group = [x for x in w["items"] if x["climate"] == climate]
                self.assertEqual(len(group), 5)
                self.assertEqual(sum(x["label"] != x["rule_label"] for x in group), 1)
            for order in w["orders"]:
                self.assertEqual(sorted(order), list(range(10)))
            plates += [x["id"] for x in w["items"]]
        self.assertEqual(len(plates), len(set(plates)))

    def test_seeds_and_stages_separate_data(self):
        a = make_plan(config())
        b_config = config()
        b_config["seed"] += 1
        self.assertNotEqual(a["worlds"], make_plan(b_config)["worlds"])
        b = make_plan(config(2))
        ids = lambda p: {x["id"] for w in p["worlds"] for x in w["items"]}
        self.assertFalse(ids(a) & ids(b))

    def test_arms_share_stage1_order(self):
        p = make_plan(config(n=2))
        for w in p["worlds"]:
            seq = lambda c: [(t["round"], t["item_index"]) for t in p["tasks"]
                              if t["world_id"] == w["id"] and t["condition"] == c]
            self.assertEqual(seq("direct"), seq("cot"))

    def test_paired_world_changes_only_eight_background_labels(self):
        p = make_plan(config(2))
        for w in p["worlds"]:
            conflict, support = items_for(w), items_for(w, "support")
            changed = 0
            for a, b in zip(conflict, support):
                if a["is_exception"]:
                    self.assertEqual(a, b)
                else:
                    self.assertNotEqual(a["label"], b["label"])
                    self.assertEqual({k: v for k, v in a.items() if k != "label"},
                                     {k: v for k, v in b.items() if k != "label"})
                    changed += 1
            self.assertEqual(changed, 8)
            self.assertEqual(sum(x["label"] == "A" for x in support), 5)
            for climate in ("cold", "warm"):
                self.assertEqual(len({x["label"] for x in support if x["climate"] == climate}), 1)


class PromptTests(unittest.TestCase):
    def test_no_answer_key_leaks_in_stage1_first_prompt(self):
        p = make_plan(config(n=1))
        for t in p["tasks"][:2]:
            text = messages_for(p, t, {})[0]["content"]
            for forbidden in ("Verified class", "is_exception", "rule_label", "warm", "cold", "80%"):
                self.assertNotIn(forbidden, text)

    def test_history_has_only_own_answers_and_previous_feedback(self):
        p = make_plan(config(n=1))
        tasks = [t for t in p["tasks"] if t["condition"] == "cot"]
        first, second = tasks[:2]
        item = world_for(p, first)["items"][first["item_index"]]
        wrong = "A" if item["label"] == "B" else "B"
        history = {first["id"]: {"status": "complete", "answer": wrong,
                                 "response": {"text": "OWN FULL EXPLANATION\n" + wrong}}}
        messages = messages_for(p, second, history)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user"])
        self.assertEqual(messages[1]["content"], "OWN FULL EXPLANATION\n" + wrong)
        self.assertIn(f"Incorrect. Verified class for {item['id']}: {item['label']}.", messages[2]["content"])
        self.assertEqual(messages[2]["content"].count("Verified class"), 1)

    def test_missing_history_cannot_be_silently_skipped(self):
        p = make_plan(config(n=1))
        t = next(t for t in p["tasks"] if t["position"] == 2)
        with self.assertRaises(ValueError):
            messages_for(p, t, {})

    def test_diagnostic_queries_are_independent(self):
        p = make_plan(config(2, n=1))
        t = p["tasks"][0]
        self.assertEqual(messages_for(p, t, {}), messages_for(p, t, {"junk": "other answers"}))
        self.assertEqual(len(messages_for(p, t, {})), 1)

    def test_diagnostic_context_shared_and_record_arm_is_correct(self):
        p = make_plan(config(2, n=1))
        target = p["tasks"][0]["item_index"]
        by_arm = {t["condition"]: t for t in p["tasks"]
                  if t["background"] == "conflict" and t["item_index"] == target}
        texts = {k: messages_for(p, t, {})[0]["content"] for k, t in by_arm.items()}
        for a in ("direct", "cot", "recall", "cot_record"):
            self.assertEqual(texts[a].split("\n\n")[0], texts["direct"].split("\n\n")[0])
        self.assertEqual(texts["cot"].count("Verified class:"), 10)
        self.assertEqual(texts["cot_record"].count("Verified class:"), 11)
        item = p["worlds"][0]["items"][target]
        repeat = texts["cot_record"].split("Repeated record from the evidence above:")[1]
        self.assertIn(f"Verified class: {item['label']}", repeat)

    def test_parser_ignores_rationale_and_rejects_ambiguous_final_lines(self):
        for text, answer in [("B is the pattern.\nA", "A"), (" **B** ", "B"),
                             ("Final answer: 'A'.", "A"), ("A or B", None),
                             ("A\nI cannot decide.", None), ("", None), ("A\nB", "B")]:
            self.assertEqual(parse_answer(text), answer)


class ProviderTests(unittest.TestCase):
    def test_payload_uses_chat_api_and_never_contains_credentials(self):
        p = make_plan(config(n=1))
        for t in p["tasks"][:2]:
            payload = payload_for(p["config"], t, messages_for(p, t, {}))
            self.assertEqual(payload["max_completion_tokens"], 1000 if t["condition"] == "cot" else 10)
            self.assertEqual(payload["temperature"], 0)
            self.assertFalse(payload["store"])
            self.assertNotIn("response_format", payload)
            self.assertNotIn("reasoning_effort", payload)
            self.assertNotIn("api_key_env", payload)

    def test_incomplete_response_never_accepted_even_with_final_label(self):
        for finish in ("length", "content_filter", "tool_calls", None):
            result = provider.normalize({"choices": [{"finish_reason": finish,
                "message": {"role": "assistant", "content": "A"}}]})
            self.assertFalse(result["complete"])

    def test_refusal_and_multiple_choices_rejected(self):
        choice = {"finish_reason": "stop", "message": {"role": "assistant", "content": "B", "refusal": "no"}}
        self.assertFalse(provider.normalize({"choices": [choice]})["complete"])
        del choice["message"]["refusal"]
        self.assertFalse(provider.normalize({"choices": [choice, choice]})["complete"])
        self.assertTrue(provider.normalize({"choices": [choice]})["complete"])

    def test_credentials_checked_without_exposure(self):
        for key in ("", "key with spaces", "sk-secret\n", "sk-☃"):
            with patch.dict(os.environ, {"OPENAI_API_KEY": key}):
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.credential(config())
                if key:
                    self.assertNotIn(key, str(caught.exception))

    def test_http_request_and_model_snapshot_validation(self):
        cfg = config()
        raw = {"model": cfg["model"], "choices": [{"finish_reason": "stop",
                "message": {"role": "assistant", "content": "B"}}]}
        class Opener:
            def open(self, req, timeout):
                self.request = req
                self.timeout = timeout
                return io.BytesIO(json.dumps(raw).encode())
        opener = Opener()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "TEST_ONLY_NOT_REAL"}), \
                patch.object(provider.request, "build_opener", return_value=opener):
            result = provider.complete(cfg, {"model": cfg["model"], "messages": []})
            self.assertTrue(result["complete"])
            self.assertEqual(opener.request.full_url, provider.ENDPOINT)
            self.assertEqual(opener.request.get_method(), "POST")
            self.assertNotIn("TEST_ONLY_NOT_REAL", json.dumps(result))
            raw["model"] = "different-snapshot"
            self.assertFalse(provider.complete(cfg, {})["complete"])


class AnalysisTests(unittest.TestCase):
    def test_positive_fixture_has_correct_gap_and_cluster_count(self):
        p = make_plan(config())
        summary, rows = summarize(p, completed_fixture(p), "mock")
        self.assertEqual(summary["paired_lists"], 20)
        self.assertEqual(summary["exception"]["direct_accuracy"], 1)
        self.assertEqual(summary["exception"]["cot_accuracy"], 0)
        self.assertEqual(summary["exception"]["direct_minus_cot"], 1)
        self.assertEqual(summary["regular"]["direct_minus_cot"], 0)
        self.assertEqual(summary["screen"]["decision"], "eligible_for_diagnostics")
        self.assertEqual(len(rows), 1200)
        self.assertTrue(summary["is_simulated"])

    def test_null_fixture_stops(self):
        p = make_plan(config())
        summary, _ = summarize(p, completed_fixture(p, rule_bias=False))
        self.assertEqual(summary["screen"]["decision"], "stop_this_screen")
        self.assertEqual(summary["exception"]["paired_bootstrap_95_ci"], [0, 0])

    def test_invalid_does_not_become_a_wrong_answer_or_a_passing_screen(self):
        p = make_plan(config())
        records = completed_fixture(p)
        records[0].update(status="invalid", answer=None)
        summary, rows = summarize(p, records)
        self.assertEqual(summary["paired_lists"], 19)
        self.assertEqual(summary["invalid_answers"], 1)
        self.assertIsNone(rows[0]["correct"])
        self.assertEqual(summary["screen"]["decision"], "technical_failure")

    def test_diagnostic_interaction_and_record_rescue(self):
        p = make_plan(config(2))
        summary, _ = summarize(p, completed_fixture(p), "mock")
        self.assertEqual(summary["paired_lists"], 20)
        self.assertEqual(summary["diagnostics"]["reasoning_extra_conflict_penalty"]["mean"], 1)
        self.assertEqual(summary["diagnostics"]["record_rescue_in_conflict"]["mean"], 1)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def test_resume_identical_to_uninterrupted_run(self):
        cfg = config(n=1)
        a, b = self.root / "a", self.root / "b"
        first = run(cfg, a, 7, mock=True)
        self.assertEqual(first["calls_this_invocation"], 7)
        with self.assertRaises(ValueError):
            run(cfg, a, 60, mock=True)
        second = run(cfg, a, 60, mock=True, resume=True)
        self.assertEqual(second["calls_this_invocation"], 53)
        self.assertEqual(second["stopped"], "complete")
        run(cfg, b, 60, mock=True)
        aa, bb = load_attempts(a, read_plan(a)), load_attempts(b, read_plan(b))
        self.assertEqual([(x["request"], x["answer"]) for x in aa],
                         [(x["request"], x["answer"]) for x in bb])

    def test_transport_error_has_no_automatic_retry(self):
        cfg = config(n=1)
        dest = self.root / "run"
        def failing(*args):
            raise provider.ProviderError("HTTP 429", 429)
        result = run(cfg, dest, 50, mock=True, complete_fn=failing)
        self.assertEqual(result["calls_this_invocation"], 1)
        self.assertEqual(result["stopped"], "provider_error")
        result = run(cfg, dest, 50, mock=True, resume=True)
        self.assertEqual(result["calls_this_invocation"], 0)
        self.assertEqual(result["stopped"], "retry_requires_flag")
        result = run(cfg, dest, 1, mock=True, resume=True, retry_errors=True)
        self.assertEqual(result["attempts_total"], 2)
        self.assertEqual(result["valid_answers"], 1)

    def test_invalid_returned_answer_is_never_resampled(self):
        cfg = config(n=1)
        dest = self.root / "run"
        def invalid(*args):
            return {"text": "A\nB", "complete": False, "finish_reason": "length", "usage": {}}
        result = run(cfg, dest, 20, mock=True, complete_fn=invalid)
        self.assertEqual(result["stopped"], "invalid_response")
        self.assertEqual(result["valid_answers"], 0)
        with self.assertRaisesRegex(ValueError, "invalid"):
            run(cfg, dest, 20, mock=True, resume=True, retry_errors=True)

    def test_mock_live_mixing_and_config_change_rejected(self):
        cfg = config(n=1)
        dest = self.root / "run"
        run(cfg, dest, 1, mock=True)
        with self.assertRaisesRegex(ValueError, "mode"):
            run(cfg, dest, 1, mock=False, resume=True)
        cfg["seed"] += 1
        with self.assertRaisesRegex(ValueError, "Config"):
            run(cfg, dest, 1, mock=True, resume=True)

    def test_plan_tampering_rejected(self):
        dest = self.root / "run"
        run(config(n=1), dest, 1, mock=True)
        plan = read_plan(dest)
        plan["worlds"][0]["items"][0]["label"] = "bad"
        write_json(dest / "plan.json", plan)
        with self.assertRaisesRegex(ValueError, "integrity"):
            read_plan(dest)

    def test_second_writer_rejected(self):
        dest = self.root / "run"
        with run_lock(dest):
            with self.assertRaisesRegex(ValueError, "Another process"):
                with run_lock(dest):
                    pass

    def test_stage2_requires_real_eligible_parent_for_live_calls(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            run(config(2), self.root / "s2", 1, mock=True)
        parent = self.root / "s1"
        run(config(), parent, 1200, mock=True)
        with self.assertRaisesRegex(ValueError, "simulated"):
            run(config(2), self.root / "s2", 1, stage1_run=parent)
        result = run(config(2), self.root / "s2", 320, mock=True, stage1_run=parent)
        self.assertEqual(result["stopped"], "complete")
        self.assertEqual(result["valid_answers"], 320)

    def test_unresolved_crash_attempt_requires_explicit_retry(self):
        cfg = config(n=1)
        dest = self.root / "run"
        def interrupted(*args):
            raise KeyboardInterrupt()
        result = run(cfg, dest, 1, mock=True, complete_fn=interrupted)
        self.assertEqual(result["stopped"], "interrupted")
        self.assertEqual(result["attempts_total"], 1)
        result = run(cfg, dest, 1, mock=True, resume=True)
        self.assertEqual(result["stopped"], "retry_requires_flag")


if __name__ == "__main__":
    unittest.main()
