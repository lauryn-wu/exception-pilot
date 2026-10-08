"""Frozen input interventions; no responses influence the schedule or prompts."""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
import re

from exception_counterfactual.core import INTRODUCTION, make_world
from exception_factorial.core import messages_for as anchor_messages
from exception_pilot.core import check_plan, describe, digest, parse_answer, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2", "missing")
ARMS = ("direct", "cot", "copy_class", "copy_marker", "priority")
LABELS = ("A", "B", "C")
COPY_ARMS = ("copy_class", "copy_marker")
INTRO = (INTRODUCTION + " The audit marker is an administrative code assigned independently "
         "of class. MISSING means the verified class has not been recorded. If that cell is "
         "MISSING, make your best prediction from the other records.")
QUESTION = "Which class, A, B, or C, does this vehicle belong to?"
FINAL = "Think step by step, then put ANSWER: followed by A, B, or C alone on the final line."
INSTRUCTIONS = {
    "direct": "Reply with only ANSWER: followed by A, B, or C.",
    "cot": FINAL,
    "copy_class": (
        "First copy the target vehicle's Verified class cell exactly, using COPIED: followed "
        "by the cell value alone on the first line. Do not explain before that line. " + FINAL),
    "copy_marker": (
        "First copy the target vehicle's Audit marker cell exactly, using COPIED: followed "
        "by the cell value alone on the first line. Do not explain before that line. " + FINAL),
    "priority": (
        "The target vehicle's verified class is definitive. Use that individual record even "
        "if the other vehicles suggest a different class. " + FINAL),
}
ANALYSIS_PLAN = {
    "primary": "record_sensitivity/direct_minus_cot",
    "key_secondary": "record_sensitivity/copy_class_minus_copy_marker",
    "unit": "independent world; variants and arms remain paired",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "missing_class": "no ground-truth accuracy; report answer distribution",
    "copy_errors": "score final answer regardless of copy correctness or copy formatting",
    "invalid_answers": "retain; never resample; per-contrast complete-world estimates and bounds",
    "decision": "no scientific pass gate; no outcome-dependent extension",
}


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "api_key_env", "temperature",
              "max_completion_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/explanation.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate output directory for this diagnostic")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 24:
        raise ValueError("This diagnostic fixes 24 independent worlds and 384 planned calls")
    if type(config["seed"]) is not int:
        raise ValueError("seed must be an integer")
    if config["model"] != "gpt-4o-2024-08-06":
        raise ValueError("This diagnostic fixes gpt-4o-2024-08-06")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This diagnostic fixes temperature at 0")
    limits = config["max_completion_tokens"]
    if (not isinstance(limits, dict)
            or limits != {"anchor_direct": 10, "direct": 16, "cot": 1000}
            or any(type(v) is not int for v in limits.values())):
        raise ValueError("Completion caps must be anchor_direct=10, direct=16, cot=1000")
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 400:
        raise ValueError("The cumulative cap is 400 attempts, including up to 16 transport retries")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation")
    return digest({str(p.relative_to(root)): p.read_text()
                   for package in packages for p in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Each of six label-role permutations occurs four times: twice per climate.
    assignments = [(p, climate) for p in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        world["id"] = f"ex-list-{index:03d}"
        for item in world["items"]:
            item["id"] = "E" + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip(("record_1", "record_2", "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", config["seed"], index)
        other_labels = [roles[0]] * 3 + [roles[1]] * 2
        # Balance the opposite-climate 3:2 split separately from semantic label roles.
        if index % 2:
            other_labels = [roles[0]] * 2 + [roles[1]] * 3
        rng.shuffle(other_labels)
        labels, markers = [], ["X", "Y", "Z"] * 3 + [rng.choice(["X", "Y", "Z"])]
        rng.shuffle(markers)
        for i, item in enumerate(world["items"]):
            item["audit_marker"] = markers[i]
            labels.append(roles[2] if item["climate"] == climate else other_labels.pop())
        world["record_labels"] = {}
        for value in VALUES:
            version = labels.copy()
            version[target] = "MISSING" if value == "missing" else world["roles"][value]
            world["record_labels"][value] = version
        worlds.append(world)
        cells = []
        for arm in ("direct", "cot"):
            cells.append({"id": f"{world['id']}/anchor/{arm}", "world_id": world["id"],
                          "family": "anchor", "value": "binary", "arm": arm})
        for value in VALUES:
            for arm in ARMS:
                if value == "missing" and arm == "priority":
                    continue
                cells.append({"id": f"{world['id']}/{value}/{arm}", "world_id": world["id"],
                              "family": "diagnostic", "value": value, "arm": arm})
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", config["seed"], index).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": config, "worlds": worlds, "tasks": tasks, "analysis_plan": ANALYSIS_PLAN}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    validate_config(plan["config"])
    # Rebuilding also checks schedule, label balance, every prompt dependency, and source identity.
    if plan != make_plan(plan["config"]):
        raise ValueError("Code or saved plan differs; preserve the run and use a new output directory")
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    i = world["target_index"]
    item = world["items"][i]
    anchor = task["family"] == "anchor"
    expected = (world["labels"]["conflict"][i] if anchor else
                None if task["value"] == "missing" else world["roles"][task["value"]])
    copied = (world["record_labels"][task["value"]][i] if task["arm"] == "copy_class" else
              item["audit_marker"] if task["arm"] == "copy_marker" else None)
    return {"world_id": world["id"], "family": task["family"], "value": task["value"],
            "arm": task["arm"], "item_id": item["id"], "expected": expected,
            "pattern_label": world["majority_labels"]["conflict"][item["climate"]] if anchor
                             else world["roles"]["pattern"],
            "copy_expected": copied, "target_position": world["order"].index(i) + 1}


def messages_for(plan, task):
    world = world_for(plan, task)
    if task["family"] == "anchor":
        return anchor_messages(plan, {"world_id": world["id"], "item_index": world["target_index"],
            "background": "conflict", "question_wording": "original", "uncertainty_clause": "absent",
            "condition": "direct" if task["arm"] == "direct" else "cot_neutral"})
    lines = [INTRO, "",
             "| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |",
             "|---|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        fields.append(world["record_labels"][task["value"]][i])
        lines.append("| " + " | ".join(fields) + " |")
    lines += ["", describe(world["items"][world["target_index"]]), QUESTION, INSTRUCTIONS[task["arm"]]]
    return [{"role": "user", "content": "\n".join(lines)}]


def request_for(plan, task):
    config = plan["config"]
    cap = "cot" if task["arm"] != "direct" else "anchor_direct" if task["family"] == "anchor" else "direct"
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"], "max_completion_tokens": config["max_completion_tokens"][cap],
            "n": 1, "store": False}


def score_response(task, response):
    """Read only prespecified boundary lines. Wrong copies remain behavioral data."""
    text = response["text"].strip() if response["complete"] else ""
    lines = text.splitlines()
    if task["family"] == "anchor":
        answer = parse_answer(text)
    else:
        final = re.fullmatch(r"ANSWER: ([ABC])", lines[-1].strip()) if lines else None
        answer = final.group(1) if final else None
    copied, copy_valid = None, None
    if task["arm"] in COPY_ARMS:
        pattern = r"COPIED: (A|B|C|MISSING)" if task["arm"] == "copy_class" else r"COPIED: ([XYZ])"
        first = re.fullmatch(pattern, lines[0].strip()) if len(lines) >= 2 else None
        copied, copy_valid = (first.group(1), True) if first else (None, False)
    return {"answer": answer, "copied": copied, "copy_valid": copy_valid,
            "status": "complete" if answer is not None else "invalid"}
