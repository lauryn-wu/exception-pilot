"""Offline design invariants for the within-world relocation intervention."""
from collections import Counter
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from exception_pilot.core import check_plan, digest
from exception_query_form import core as parent
from exception_row_position_confirm import core

ROOT = Path(__file__).resolve().parents[1]


class RowPositionConfirmDesignTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline tests only"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.config = core.load_config(ROOT / "configs/row_position_confirm_mistral.json")
        self.plan = core.make_plan(self.config)

    def test_fresh_cohort_excludes_development_and_balances_every_row(self):
        previous = parent.make_plan(parent.load_config(ROOT / "configs/query_form_mistral.json"))
        old_plates = {x["id"] for w in previous["worlds"] for x in w["items"]}
        fresh_plates = [x["id"] for w in self.plan["worlds"] for x in w["items"]]
        self.assertEqual(len(set(fresh_plates)), 240)
        self.assertFalse(set(fresh_plates) & old_plates)
        self.assertFalse({w["id"] for w in previous["worlds"]} & {w["id"] for w in self.plan["worlds"]})
        def features(world):
            return tuple(tuple(sorted((k, v) for k, v in item.items() if k != "id"))
                         for item in world["items"])
        self.assertFalse({features(w) for w in previous["worlds"]} & {features(w) for w in self.plan["worlds"]})
        self.assertEqual(digest(self.plan["worlds"]), self.plan["design"]["fresh_worlds_digest"])
        self.assertEqual(self.plan["design"]["development_plan_hash"], core.DEVELOPMENT_PLAN_HASH)
        balance = Counter((tuple(w["roles"][k] for k in (*core.VALUES, "pattern")),
                           w["items"][w["target_index"]]["climate"]) for w in self.plan["worlds"])
        self.assertEqual(len(balance), 12)
        self.assertEqual(set(balance.values()), {2})
        for position in core.POSITIONS:
            tasks = [t for t in self.plan["tasks"] if t["position"] == position]
            self.assertEqual(len(tasks), 96)
            self.assertEqual({t["world_id"] for t in tasks}, {w["id"] for w in self.plan["worlds"]})

    def test_only_target_row_moves_other_rows_and_query_are_identical(self):
        snapshot = copy.deepcopy(self.plan)
        for world in self.plan["worlds"]:
            for value in core.VALUES:
                for arm in core.ARMS:
                    non_target_tables, outer_texts, target_lines = [], [], []
                    for position in core.POSITIONS:
                        task = next(t for t in self.plan["tasks"] if
                                    (t["world_id"], t["value"], t["arm"], t["position"]) == (world["id"],value,arm,position))
                        parts = core.prompt_parts(self.plan, task)
                        text = "".join(parts)
                        rows = [line for line in parts[0].splitlines() if line.startswith("| ")][1:]
                        self.assertEqual(len(rows), 10)
                        target = world["items"][world["target_index"]]["id"]
                        self.assertEqual(rows[position-1].split("|")[1].strip(), target)
                        target_lines.append(rows[position-1])
                        non_target_tables.append(rows[:position-1]+rows[position:])
                        outer_texts.append([line for line in text.splitlines() if not line.startswith("|")])
                        self.assertEqual(parts[1], "License plate: " + target)
                        self.assertEqual(core.task_meta(self.plan, task)["target_position"], position)
                        self.assertEqual(core.order_for(world, position)[position-1], world["target_index"])
                    for i in range(1, 10):
                        self.assertEqual(non_target_tables[0], non_target_tables[i])
                        self.assertEqual(target_lines[0], target_lines[i])
                        self.assertEqual(outer_texts[0], outer_texts[i])
        self.assertEqual(snapshot, self.plan)

    def test_record_variants_change_only_target_class(self):
        for world in self.plan["worlds"]:
            for position in core.POSITIONS:
                task = next(t for t in self.plan["tasks"] if t["world_id"] == world["id"] and t["position"] == position)
                one = core.messages_for(self.plan, dict(task, value="record_1"))[0]["content"].splitlines()
                two = core.messages_for(self.plan, dict(task, value="record_2"))[0]["content"].splitlines()
                differences = [(a,b) for a,b in zip(one,two) if a != b]
                self.assertEqual(len(differences), 1)
                a,b=differences[0]
                self.assertEqual(a.rsplit("|",2)[0], b.rsplit("|",2)[0])
                self.assertEqual(a.split("|")[-2].strip(), world["roles"]["record_1"])
                self.assertEqual(b.split("|")[-2].strip(), world["roles"]["record_2"])

    def test_unchanged_parent_prompt_at_matching_position(self):
        for task in self.plan["tasks"]:
            world = core.world_for(self.plan, task)
            if world["order"].index(world["target_index"])+1 == task["position"]:
                self.assertEqual(core.messages_for(self.plan, task), parent.messages_for(self.plan, task))
            payload = core.request_for(self.plan, task, self.config)
            self.assertEqual([m["role"] for m in payload["messages"]], ["user"])
            self.assertEqual(payload["max_tokens"], 1600)
            self.assertEqual(payload["temperature"], 0)
            self.assertEqual(payload["reasoning_effort"], "none")
            self.assertEqual(set(payload), {"model","messages","temperature","max_tokens","reasoning_effort","stream"})

    def test_schedule_hash_and_primary_cells(self):
        check_plan(self.plan)
        self.assertEqual(self.plan, core.make_plan(self.config))
        tasks=self.plan["tasks"]
        self.assertEqual(len(tasks), 960)
        self.assertEqual(len({t["id"] for t in tasks}), 960)
        self.assertEqual(set(Counter(t["world_id"] for t in tasks).values()), {40})
        for w in self.plan["worlds"]:
            cells=[t for t in tasks if t["world_id"]==w["id"]]
            self.assertEqual(len([t for t in cells if t["position"] in (1,10)]), 8)
            self.assertEqual(len({(t["position"],t["value"],t["arm"]) for t in cells}),40)
        self.assertEqual(self.plan["analysis_plan"]["primary"], "accuracy/interaction")
        scheduled = [tasks[i]["world_id"] for i in range(0, 960, 40)]
        self.assertEqual(scheduled, self.plan["design"]["world_schedule"])
        self.assertNotEqual(scheduled, [w["id"] for w in self.plan["worlds"]])
        self.assertEqual(set(Counter((t["position"], t["arm"]) for t in tasks).values()), {48})

    def test_config_and_source_tamper_are_rejected(self):
        for key,value in [("provider","openai"),("model","mistral-small-latest"),("seed",7),
                          ("n_worlds",12),("max_tokens",{"direct":10,"visible":1600}),
                          ("api_key_env","not an env name"),("max_total_attempts",400)]:
            with self.assertRaises(ValueError):
                core.validate_config(dict(self.config,**{key:value}))
        fixture=json.loads(core.DEVELOPMENT_WORLD_FILE.read_text())
        fixture["worlds"][0]["order"].reverse()
        fixture["worlds_digest"]=digest(fixture["worlds"])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"changed.json";path.write_text(json.dumps(fixture))
            with patch.object(core,"DEVELOPMENT_WORLD_FILE",path), self.assertRaises(ValueError):
                core.source_worlds()
        for position in (0,11,True,1.0):
            with self.assertRaises(ValueError):
                core.order_for(self.plan["worlds"][0],position)


if __name__ == "__main__":
    unittest.main()
