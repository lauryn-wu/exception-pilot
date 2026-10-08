"""Matched counterfactual records with constant exception rate and target labels."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re

from exception_pilot.core import (DESCRIPTORS, check_plan, digest, opposite,
                                  payload_for, question, rng_for)

from . import PROTOCOL_VERSION, MINIMUM_EXTRA_CONFLICT_PENALTY, MINIMUM_LISTS

BACKGROUNDS = ("conflict", "support")
ARMS = ("direct", "cot")
INTRODUCTION = ("These are records of previously observed vehicles. Every record is accurate. "
                "An individual vehicle's class is fixed, and its license plate identifies it.")


def validate_config(config):
    required = {"protocol", "n_lists", "seed", "model", "api_key_env", "temperature",
                "max_completion_tokens", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("Config fields must match configs/counterfactual.json; never include credentials.")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; this command runs the independent counterfactual diagnostic.")
    if type(config["n_lists"]) is not int or not 1 <= config["n_lists"] <= 1000:
        raise ValueError("n_lists must be an integer between 1 and 1000")
    if type(config["seed"]) is not int:
        raise ValueError("seed must be an integer")
    if config["model"] != "gpt-4o-2024-08-06":
        raise ValueError("This protocol fixes gpt-4o-2024-08-06; do not replace the model mid-study.")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This protocol fixes temperature at 0")
    limits = config["max_completion_tokens"]
    if (not isinstance(limits, dict) or limits != {"direct": 10, "cot": 1000}
            or any(type(n) is not int for n in limits.values())):
        raise ValueError("This protocol fixes completion caps at direct=10 and cot=1000")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    # Include shared helpers without altering the frozen original package.
    files = [p for package in ("exception_counterfactual", "exception_pilot")
             for p in sorted((root / package).glob("*.py"))]
    return digest({str(p.relative_to(root)): p.read_text() for p in files})


def make_world(config, index, used_plates):
    rng = rng_for(PROTOCOL_VERSION, "data", config["seed"], index)
    cold_label = rng.choice(["A", "B"])
    majority = {"conflict": {"cold": cold_label, "warm": opposite(cold_label)},
                "support": {"cold": opposite(cold_label), "warm": cold_label}}
    items, targets, support_exceptions = [], [], []
    labels = {background: [] for background in BACKGROUNDS}
    for climate in ("cold", "warm"):
        descriptions = DESCRIPTORS[climate].copy()
        rng.shuffle(descriptions)
        target = rng.randrange(5)
        support_exception = rng.choice([j for j in range(5) if j != target])
        offset = len(items)
        targets.append(offset + target)
        support_exceptions.append(offset + support_exception)
        for j, descriptor in enumerate(descriptions):
            while True:
                plate = "V" + "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                if plate not in used_plates:
                    used_plates.add(plate)
                    break
            items.append({"id": plate, "descriptor": descriptor, "climate": climate,
                          "transmission": rng.choice(["Manual", "Automatic"]),
                          "seat_cover": rng.choice(["Cloth", "Vinyl"]),
                          "doors": rng.choice(["Two", "Four"])})
            for background, exception_index in (("conflict", target),
                                                 ("support", support_exception)):
                rule = majority[background][climate]
                labels[background].append(opposite(rule) if j == exception_index else rule)
    order = list(range(10))
    rng.shuffle(order)
    world = {"id": f"cf-list-{index:03d}", "items": items, "labels": labels,
             "majority_labels": majority, "target_indices": targets,
             "support_exception_indices": support_exceptions, "order": order}
    validate_world(world)
    return world


def validate_world(world):
    items, labels = world["items"], world["labels"]
    targets = world["target_indices"]
    if (len(items) != 10 or len({x["id"] for x in items}) != 10
            or sorted(world["order"]) != list(range(10))
            or len(targets) != 2 or {items[i]["climate"] for i in targets} != {"cold", "warm"}):
        raise ValueError("Counterfactual world has invalid records, order or targets")
    for background in BACKGROUNDS:
        values = labels[background]
        if len(values) != 10 or values.count("A") != 5 or values.count("B") != 5:
            raise ValueError("Both backgrounds must contain five A and five B labels")
        for climate in ("cold", "warm"):
            indices = [i for i, item in enumerate(items) if item["climate"] == climate]
            rule = world["majority_labels"][background][climate]
            if len(indices) != 5 or sum(values[i] == rule for i in indices) != 4:
                raise ValueError("Both backgrounds must have one exception per climate")
    changed = [i for i in range(10) if labels["conflict"][i] != labels["support"][i]]
    if len(changed) != 6 or set(changed) & set(targets):
        raise ValueError("Exactly six non-target labels must change")
    for i in targets:
        climate = items[i]["climate"]
        if (labels["conflict"][i] == world["majority_labels"]["conflict"][climate]
                or labels["support"][i] != world["majority_labels"]["support"][climate]):
            raise ValueError("Targets must oppose the conflict pattern and follow the support pattern")


def make_plan(config):
    validate_config(config)
    used_plates = set()
    worlds = [make_world(config, i, used_plates) for i in range(config["n_lists"])]
    tasks = []
    for world in worlds:
        cells = [{"id": f"{world['id']}/{i}/{background}/{arm}",
                  "world_id": world["id"], "item_index": i,
                  "background": background, "condition": arm}
                 for i in world["target_indices"] for background in BACKGROUNDS for arm in ARMS]
        rng_for(PROTOCOL_VERSION, "schedule", config["seed"], world["id"]).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": config, "worlds": worlds, "tasks": tasks,
            "decision_rule": {"minimum_extra_conflict_penalty": MINIMUM_EXTRA_CONFLICT_PENALTY,
                              "minimum_independent_lists": MINIMUM_LISTS,
                              "requires_positive_cot_conflict_penalty": True,
                              "requires_lower_cot_than_direct_conflict_accuracy": True}}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("This is not a counterfactual run. Use exception_pilot for the original stages.")
    validate_config(plan["config"])
    for world in plan["worlds"]:
        validate_world(world)
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    i, background = task["item_index"], task["background"]
    item = world["items"][i]
    label = world["labels"][background][i]
    rule = world["majority_labels"][background][item["climate"]]
    return {"world_id": world["id"], "item_id": item["id"],
            "condition": task["condition"], "background": background,
            "target_position": world["order"].index(i) + 1, "expected": label,
            "background_majority_label": rule, "is_exception_in_this_background": label != rule}


def messages_for(plan, task):
    world = world_for(plan, task)
    lines = [INTRODUCTION, "",
             "| License plate | Description | Transmission | Seat cover | Doors | Verified class |",
             "|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        values = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors")]
        values.append(world["labels"][task["background"]][i])
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", question(world["items"][task["item_index"]], task["condition"])])
    return [{"role": "user", "content": "\n".join(lines)}]


def request_for(plan, task):
    return payload_for(plan["config"], task, messages_for(plan, task))
