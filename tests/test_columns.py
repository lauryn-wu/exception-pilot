import copy
import itertools
from pathlib import Path
import unittest

from exception_explanation.core import INTRO as ORIGINAL_INTRO, INSTRUCTIONS as ORIGINAL_INSTRUCTIONS
from exception_columns import provider
from exception_columns.core import (ARMS, COLUMNS, SCHEMAS, VALUES, load_config, make_plan,
                                    prompt_parts, request_for, score_response, source_worlds, task_meta)

ROOT = Path(__file__).resolve().parents[1]


class ColumnDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(ROOT / "configs/columns_gpt4o.json")
        cls.plan = make_plan(cls.config)
        cls.tasks = {(t["world_id"], t["value"], t["schema"], t["arm"]): t for t in cls.plan["tasks"]}

    def test_all_worlds_and_balanced_roles_preserved(self):
        self.assertEqual(self.plan["worlds"], source_worlds()["worlds"])
        self.assertEqual(len(self.plan["worlds"]), 24)
        self.assertEqual(len(self.plan["tasks"]), 576)
        self.assertEqual(len({t["id"] for t in self.plan["tasks"]}), 576)
        roles = [tuple(w["roles"][v] for v in (*VALUES, "pattern")) for w in self.plan["worlds"]]
        for permutation in itertools.permutations("ABC"):
            self.assertEqual(roles.count(permutation), 4)

    def test_only_requested_columns_removed_all_576_requests(self):
        for world in self.plan["worlds"]:
            for value, arm in itertools.product(VALUES, ARMS):
                reference = self.tasks[world["id"], value, "full", arm]
                intro, full, query = prompt_parts(self.plan, reference)
                full_rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in full.splitlines()]
                for schema in SCHEMAS:
                    task = self.tasks[world["id"], value, schema, arm]
                    before, table, after = prompt_parts(self.plan, task)
                    self.assertEqual(before, intro)
                    self.assertEqual(after, query)
                    positions = [COLUMNS["full"].index(k) for k in COLUMNS[schema]]
                    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in table.splitlines()]
                    self.assertEqual(len(rows), 12)  # header + separator + ten unchanged rows
                    self.assertEqual(rows, [[row[i] for i in positions] for row in full_rows])
                    self.assertEqual(after.splitlines()[2], "License plate: " + task_meta(self.plan, task)["item_id"])
                    self.assertNotIn("Transmission:", after)
                    self.assertNotIn("Description:", after)
                    self.assertEqual(len(rows[0]), {"minimal": 2, "description": 3, "other_attributes": 6, "full": 7}[schema])

    def test_record_variants_change_exactly_one_cell(self):
        for world in self.plan["worlds"]:
            for schema, arm in itertools.product(SCHEMAS, ARMS):
                requests = [request_for(self.plan, self.tasks[world["id"], v, schema, arm]) for v in VALUES]
                lines = [r["messages"][0]["content"].splitlines() for r in requests]
                changed = [(a, b) for a, b in zip(*lines) if a != b]
                self.assertEqual(len(changed), 1)
                a, b = changed[0]
                self.assertEqual(a.rsplit("|", 2)[0], b.rsplit("|", 2)[0])
                self.assertIn(world["items"][world["target_index"]]["id"], a)
                self.assertEqual(a.rsplit("|", 2)[1].strip(), world["roles"]["record_1"])
                self.assertEqual(b.rsplit("|", 2)[1].strip(), world["roles"]["record_2"])
                self.assertEqual(set(requests[0]), {"model", "messages", "temperature", "max_completion_tokens", "n", "store"})

    def test_arm_changes_only_instruction_and_never_preseeds_answer(self):
        for world in self.plan["worlds"]:
            for schema, value in itertools.product(SCHEMAS, VALUES):
                requests = [request_for(self.plan, self.tasks[world["id"], value, schema, arm]) for arm in ARMS]
                prompts = [r["messages"][0]["content"] for r in requests]
                self.assertEqual(len({p.rsplit("\n", 1)[0] for p in prompts}), 1)
                self.assertTrue(all(len(r["messages"]) == 1 and r["messages"][0]["role"] == "user" for r in requests))
                self.assertTrue(all(r["max_completion_tokens"] == 1000 for r in requests))

    def test_instructions_match_original_and_plan_deterministic(self):
        from exception_columns.core import INTRO, INSTRUCTIONS
        self.assertEqual(INTRO, ORIGINAL_INTRO)
        for arm in ARMS:
            self.assertEqual(INSTRUCTIONS[arm], ORIGINAL_INSTRUCTIONS[arm])
        self.assertEqual(self.plan, make_plan(self.config))

    def test_config_cannot_silently_change_design(self):
        for key, value in (("model", "gpt-4o"), ("temperature", .6), ("max_total_attempts", 1000), ("max_completion_tokens", 2000)):
            with self.assertRaises(ValueError):
                make_plan({**self.config, key: value})

    def test_copy_and_answer_are_independent(self):
        task = {"arm": "copy_class"}
        normalized = {"complete": True, "text": "COPIED: A\nThe other records suggest B.\nANSWER: B"}
        result = score_response(task, normalized)
        self.assertEqual((result["copied"], result["answer"]), ("A", "B"))
        self.assertTrue(result["contract_met"])
        normalized["text"] = "COPIED: A\nThe other records suggest B.\nunclear"
        result = score_response(task, normalized)
        self.assertEqual((result["copied"], result["answer"], result["status"]), ("A", None, "invalid"))
        self.assertFalse(result["contract_met"])

    def test_parser_never_scores_rationale_and_retains_bad_copy(self):
        for text in ("ANSWER: A\nANSWER: B", "The class is A.", "ANSWER: D"):
            self.assertEqual(score_response({"arm": "cot"}, {"complete": True, "text": text})["status"], "invalid")
        result = score_response({"arm": "copy_class"}, {"complete": True, "text": "COPIED: Z\nExplanation.\n**ANSWER: B**"})
        self.assertEqual(result["answer"], "B")
        self.assertFalse(result["copy_valid"])
        self.assertFalse(result["strict_final_format"])
        self.assertFalse(result["contract_met"])

    def test_copy_only_is_not_reasoning(self):
        result = score_response({"arm": "copy_class"}, {"complete": True, "text": "COPIED: B\nANSWER: B"})
        self.assertEqual(result["answer"], "B")
        self.assertFalse(result["has_reasoning"])
        self.assertFalse(result["contract_met"])

    def test_model_identity_and_incomplete_provider_responses(self):
        raw = {"model": self.config["model"], "choices": [{"message": {"role": "assistant", "content": "ANSWER: A"}, "finish_reason": "length"}]}
        self.assertFalse(provider.normalize(raw, self.config, "live")["complete"])
        raw["choices"][0]["finish_reason"] = "stop"
        self.assertTrue(provider.normalize(raw, self.config, "live")["complete"])
        raw["model"] = "wrong-model"
        self.assertEqual(provider.normalize(raw, self.config, "live")["model_identity"], "mismatch")
        self.assertFalse(provider.normalize(raw, self.config, "live")["complete"])
        for invalid in (None, [], "not JSON", {"unparseable_http_body_utf8": "broken"}):
            self.assertFalse(provider.normalize(invalid, self.config, "live")["complete"])


if __name__ == "__main__":
    unittest.main()
