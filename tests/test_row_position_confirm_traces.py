"""Offline audit controls for human-coded visible traces and their denominators."""

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.storage import write_json
from exception_row_position_confirm import core, runner, traces


ROOT = Path(__file__).resolve().parents[1]


class RowPositionConfirmTraceTests(unittest.TestCase):
    def setUp(self):
        network = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline review only"))
        network.start()
        self.addCleanup(network.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "run"
        self.review_path = Path(temporary.name) / "manual-review.json"
        self.config = core.load_config(ROOT / "configs/row_position_confirm_mistral.json")
        self.plan = core.make_plan(self.config)
        self.execution = {"mode": "mock"}
        # One whole world is retained; the remainder of the frozen plan is pending.
        self.attempts = self.make_records(self.plan["tasks"][:40])
        read_run = patch.object(traces, "read_run", side_effect=lambda output:
                                (self.plan, self.config, self.execution, self.attempts))
        read_run.start()
        self.addCleanup(read_run.stop)

    def make_records(self, tasks):
        records = []
        for number, task in enumerate(tasks, 1):
            meta = core.task_meta(self.plan, task)
            prefix = "The recorded target class is " + meta["expected"] + ".\n" if task["arm"] == "visible" else ""
            text = prefix + "ANSWER: " + meta["expected"]
            records.append({"attempt": number, "task_id": task["id"], "status": "complete",
                            "request": core.request_for(self.plan, task, self.config),
                            "response": {"text": text, "raw_response": {"synthetic": text}},
                            "meta": meta, "answer": meta["expected"]})
        return records

    def export(self):
        traces.export_trace_review(self.output, self.review_path)
        return json.loads(self.review_path.read_text())

    def summarize(self, review):
        write_json(self.review_path, review)
        return traces.summarize_trace_review(self.output, self.review_path)

    def positive(self, item, code, quotes):
        annotation = item["annotation"]
        annotation[code] = True
        annotation["evidence"][code] = quotes
        annotation["annotator"] = "test reviewer"
        annotation["comment"] = "Synthetic example used to check manual audit controls."

    def wrong_trace(self):
        record = next(record for record in self.attempts if record["meta"]["arm"] == "visible")
        gold = record["meta"]["expected"]
        answer = next(label for label in "ABC" if label != gold)
        record["answer"] = answer
        record["response"]["text"] = (f"The recorded target class is {gold}.\n"
                                           "The target's verified class is MISSING.\n"
                                           f"ANSWER: {answer}")
        return record

    def test_full_export_includes_all_480_visible_responses_and_invalids(self):
        self.attempts = self.make_records(self.plan["tasks"])
        invalid = next(record for record in self.attempts if record["meta"]["arm"] == "visible")
        invalid.update(status="invalid", answer=None)
        invalid["response"]["text"] = "Unparseable retained response."
        result = traces.export_trace_review(self.output, self.review_path)
        review = json.loads(self.review_path.read_text())
        self.assertEqual((result["planned_visible"], result["returned_visible"], result["unreturned_visible"]),
                         (480, 480, 0))
        self.assertNotIn("items", result)
        self.assertEqual(len({item["task_id"] for item in review["items"]}), 480)
        self.assertEqual(sum(item["status"] == "invalid" for item in review["items"]), 1)
        self.assertTrue(all(all(item["annotation"][code] is None for code in traces.CODES)
                            for item in review["items"]))
        for position, counts in review["coverage_by_position"].items():
            self.assertEqual(counts["returned_visible"], 48)
            for item in (item for item in review["items"] if item["position"] == int(position)):
                self.assertIn("| " + item["item_id"] + " |", item["target_input_row"])
                self.assertTrue(item["target_input_row"].endswith("| " + item["expected"] + " |"))

    def test_export_never_replaces_an_existing_review(self):
        review = self.export()
        review["items"][0]["annotation"]["comment"] = "Valuable in-progress notes."
        write_json(self.review_path, review)
        original = self.review_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            traces.export_trace_review(self.output, self.review_path)
        self.assertEqual(self.review_path.read_bytes(), original)

    def test_unknown_partial_and_missing_denominators_remain_distinct(self):
        wrong = self.wrong_trace()
        review = self.export()
        item = next(item for item in review["items"] if item["task_id"] == wrong["task_id"])
        self.positive(item, "false_missing", ["The target's verified class is MISSING."])
        item["annotation"]["self_contradiction"] = False
        summary = self.summarize(review)
        self.assertEqual((summary["returned_visible"], summary["unreturned_visible"]), (20, 460))
        self.assertNotIn("items", summary)
        self.assertEqual(summary["api_calls"], 0)
        missing = summary["total"]["codes"]["false_missing"]
        self.assertEqual((missing["positive"], missing["negative"], missing["reviewed"], missing["unreviewed"]),
                         (1, 0, 1, 19))
        self.assertEqual(missing["positive_fraction_among_reviewed"], 1)
        contradiction = summary["total"]["codes"]["self_contradiction"]
        self.assertEqual((contradiction["positive"], contradiction["negative"], contradiction["unreviewed"]),
                         (0, 1, 19))
        unknown = summary["total"]["codes"]["gold_then_override"]
        self.assertEqual((unknown["reviewed"], unknown["unreviewed"]), (0, 20))
        self.assertIsNone(unknown["positive_fraction_among_reviewed"])
        row = summary["by_position"][str(item["position"])]
        self.assertEqual((row["planned_visible"], row["returned_visible"], row["unreturned_visible"]), (48, 2, 46))
        self.assertEqual(row["by_correctness"]["wrong"]["codes"]["false_missing"]["positive"], 1)
        self.assertEqual(row["by_correctness"]["correct"]["codes"]["false_missing"]["reviewed"], 0)
        self.assertEqual(summary["total"]["fully_reviewed"], 0)
        self.assertIn("SIMULATED", (self.output / "trace_summary.md").read_text())
        self.assertEqual(json.loads((self.output / "trace_summary.json").read_text()), summary)

    def test_invalid_answer_remains_codable_without_becoming_wrong(self):
        invalid = self.wrong_trace()
        invalid.update(status="invalid", answer=None)
        review = self.export()
        item = next(item for item in review["items"] if item["task_id"] == invalid["task_id"])
        self.assertIsNone(item["correctness"])
        self.positive(item, "false_missing", ["The target's verified class is MISSING."])
        summary = self.summarize(review)
        row = summary["by_position"][str(item["position"])]
        self.assertEqual(row["returned_invalid"], 1)
        self.assertEqual(row["by_correctness"]["invalid_or_unscorable"]["codes"]["false_missing"]["positive"], 1)
        self.assertEqual(row["by_correctness"]["wrong"]["returned"], 0)

    def test_stale_attempt_journal_including_nonvisible_attempt_is_rejected(self):
        review = self.export()
        self.attempts.append({"attempt": 41, "task_id": self.plan["tasks"][40]["id"],
                              "status": "error", "error": "SyntheticTransportError"})
        with self.assertRaisesRegex(ValueError, "Stale or altered"):
            self.summarize(review)

    def test_changed_header_and_immutable_response_metadata_are_rejected(self):
        original = self.export()
        changes = [lambda review: review.update(plan_hash="different"),
                   lambda review: review.update(records_digest="different"),
                   lambda review: review.update(coding_rule_version=""),
                   lambda review: review["guidance"].update(false_missing="Different rule"),
                   lambda review: review["items"][0].update(raw_text="Different text"),
                   lambda review: review["items"][0].update(expected="Different gold"),
                   lambda review: review["items"][0].update(status="invalid"),
                   lambda review: review["items"][0].update(correctness=1),
                   lambda review: review["items"][0].update(record_digest="different")]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                review = copy.deepcopy(original)
                change(review)
                with self.assertRaises(ValueError):
                    self.summarize(review)

    def test_duplicate_unknown_and_omitted_items_are_rejected_but_reordering_is_allowed(self):
        original = self.export()
        changes = [lambda review: review["items"].append(copy.deepcopy(review["items"][0])),
                   lambda review: review["items"][0].update(task_id="unknown"),
                   lambda review: review["items"].pop()]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                review = copy.deepcopy(original)
                change(review)
                with self.assertRaises(ValueError):
                    self.summarize(review)
        original["items"].reverse()
        self.assertEqual(self.summarize(original)["returned_visible"], 20)

    def test_positive_codes_require_exact_evidence_and_human_provenance(self):
        self.wrong_trace()
        original = self.export()
        item_index = next(i for i, item in enumerate(original["items"]) if item["correctness"] is False)
        self.positive(original["items"][item_index], "false_missing", ["The target's verified class is MISSING."])
        changes = [lambda ann: ann.update(false_missing=1),
                   lambda ann: ann.update(annotator=" "),
                   lambda ann: ann.update(comment=""),
                   lambda ann: ann["evidence"].update(false_missing=[]),
                   lambda ann: ann["evidence"].update(false_missing=["missing paraphrase"]),
                   lambda ann: ann["evidence"].update(false_missing=[" "]),
                   lambda ann: ann.update(false_missing=False),
                   lambda ann: ann.update(false_missing=None),
                   lambda ann: ann.update(automatic_flag=True)]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                review = copy.deepcopy(original)
                change(review["items"][item_index]["annotation"])
                with self.assertRaises(ValueError):
                    self.summarize(review)
        self.assertEqual(self.summarize(original)["total"]["codes"]["false_missing"]["positive"], 1)

    def test_contradiction_and_override_require_two_distinct_quotes_and_final_disagreement(self):
        wrong = self.wrong_trace()
        original = self.export()
        item_index = next(i for i, item in enumerate(original["items"]) if item["task_id"] == wrong["task_id"])
        item = original["items"][item_index]
        gold = "The recorded target class is " + item["expected"] + "."
        missing = "The target's verified class is MISSING."
        final = "ANSWER: " + item["answer"]
        self.positive(item, "self_contradiction", [gold, missing])
        self.positive(item, "gold_then_override", [gold, final])
        summary = self.summarize(original)
        self.assertEqual(summary["total"]["codes"]["self_contradiction"]["positive"], 1)
        self.assertEqual(summary["total"]["codes"]["gold_then_override"]["positive"], 1)
        for code, quotes in (("self_contradiction", [gold]), ("self_contradiction", [gold, gold]),
                             ("gold_then_override", [final, gold]), ("gold_then_override", [gold])):
            with self.subTest(code=code, quotes=quotes):
                review = copy.deepcopy(original)
                review["items"][item_index]["annotation"]["evidence"][code] = quotes
                with self.assertRaises(ValueError):
                    self.summarize(review)
        correct = next(item for item in original["items"] if item["correctness"] is True)
        self.positive(correct, "gold_then_override",
                      ["The recorded target class is " + correct["expected"] + ".", "ANSWER: " + correct["answer"]])
        with self.assertRaisesRegex(ValueError, "final answer different"):
            self.summarize(original)

    def test_actual_missing_input_is_exported_but_excluded_from_coding(self):
        record = next(record for record in self.attempts if record["meta"]["arm"] == "visible")
        messages = record["request"]["messages"]
        target, _ = traces._target_row(record, record["meta"])
        changed = target.rsplit("|", 2)[0] + "| MISSING |"
        messages[0]["content"] = messages[0]["content"].replace(target, changed)
        review = self.export()
        item = next(item for item in review["items"] if item["task_id"] == record["task_id"])
        self.assertFalse(item["coding_eligible"])
        self.assertEqual(item["target_input_class"], "MISSING")
        summary = self.summarize(review)
        self.assertEqual((summary["total"]["eligible"], summary["total"]["excluded_no_recorded_gold"]), (19, 1))
        item["annotation"].update(false_missing=False, annotator="test", comment="Actual missing input.")
        with self.assertRaisesRegex(ValueError, "excluded"):
            self.summarize(review)

    def test_review_cannot_be_overwritten_by_generated_summary(self):
        for name in ("trace_summary.json", "trace_summary.md"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "must differ"):
                traces.export_trace_review(self.output, self.output / name)

    def test_real_mock_journal_roundtrip_uses_audited_reader(self):
        # Exercise actual source/config/request validation, not just synthetic fixtures.
        with redirect_stdout(io.StringIO()):
            runner.run(self.config, self.output, 40, mock=True)
        with patch.object(traces, "read_run", runner.read_run):
            review = self.export()
            summary = self.summarize(review)
        self.assertEqual(summary["returned_visible"], 20)
        self.assertTrue(summary["is_simulated"])
        self.assertEqual(summary["total"]["codes"]["false_missing"]["reviewed"], 0)
        self.assertEqual(summary["total"]["codes"]["false_missing"]["unreviewed"], 20)


if __name__ == "__main__":
    unittest.main()
