"""Orthogonal question and uncertainty manipulations on fresh matched records."""

from __future__ import annotations

import json
from pathlib import Path

from exception_pilot.core import check_plan, describe, digest, rng_for
from exception_counterfactual.core import (
    INTRODUCTION, make_world as base_world, task_meta as base_meta,
    validate_config as base_config, validate_world,
)
from exception_counterfactual import PROTOCOL_VERSION as BASE_PROTOCOL
from . import CALLS_PER_LIST, MINIMUM_LISTS, PRIMARY_CONTRAST, PROTOCOL_VERSION

QUESTIONS = ("original", "recorded")
UNCERTAINTY = ("absent", "present")
ARMS = ("direct", "cot_neutral")
BACKGROUNDS = ("conflict", "support")
QUESTION_TEXT = {
    "original": "Which class, A or B, does this vehicle belong to?",
    "recorded": "Which class, A or B, is recorded for this vehicle in the table above?",
}
UNCERTAINTY_TEXT = "Choose the more likely class even if uncertain."
INSTRUCTIONS = {
    "direct": "Reply with only A or B.",
    "cot_neutral": "Think step by step, then put A or B alone on the final line.",
}


def validate_config(config):
    if not isinstance(config, dict) or config.get("protocol") != PROTOCOL_VERSION:
        raise ValueError("Use configs/factorial.json and a new factorial-study output directory")
    base_config({**config, "protocol": BASE_PROTOCOL})
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_factorial", "exception_wording", "exception_counterfactual", "exception_pilot")
    files = [p for package in packages for p in sorted((root / package).glob("*.py"))]
    return digest({str(p.relative_to(root)): p.read_text() for p in files})


def make_plan(config):
    validate_config(config)
    used = set()
    worlds, tasks = [], []
    for index in range(config["n_lists"]):
        world = base_world(config, index, used)
        world["id"] = f"fx-list-{index:03d}"
        # A new seed changes the lists; a bijective prefix change prevents plate reuse.
        for item in world["items"]:
            item["id"] = "F" + item["id"][1:]
        worlds.append(world)
        cells = [
            {"id": f"{world['id']}/{i}/{bg}/{q}/{u}/{arm}",
             "world_id": world["id"], "item_index": i, "background": bg,
             "question_wording": q, "uncertainty_clause": u, "condition": arm}
            for i in world["target_indices"] for bg in BACKGROUNDS
            for q in QUESTIONS for u in UNCERTAINTY for arm in ARMS
        ]
        rng_for(PROTOCOL_VERSION, "schedule", config["seed"], index).shuffle(cells)
        tasks.extend(cells)
    plan = {
        "protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
        "config": config, "worlds": worlds, "tasks": tasks,
        "analysis_plan": {
            "purpose": "explanatory_followup_after_wording_boundary",
            "primary_contrast": PRIMARY_CONTRAST,
            "minimum_independent_lists": MINIMUM_LISTS,
            "calls_per_list": CALLS_PER_LIST,
            "numerical_pass_threshold": None,
            "automatic_followup": False,
            "previous_stop_decision_preserved": "stop_explicit_record_boundary",
        },
    }
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("This is not a factorial-study run; preserve the earlier run directory")
    validate_config(plan["config"])
    for world in plan["worlds"]:
        validate_world(world)
    return plan


def task_meta(plan, task):
    return {**base_meta(plan, task), "question_wording": task["question_wording"],
            "uncertainty_clause": task["uncertainty_clause"]}


def messages_for(plan, task):
    world = next(w for w in plan["worlds"] if w["id"] == task["world_id"])
    lines = [INTRODUCTION, "",
             "| License plate | Description | Transmission | Seat cover | Doors | Verified class |",
             "|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors")]
        fields.append(world["labels"][task["background"]][i])
        lines.append("| " + " | ".join(fields) + " |")
    lines += ["", describe(world["items"][task["item_index"]]),
              QUESTION_TEXT[task["question_wording"]]]
    if task["uncertainty_clause"] == "present":
        lines.append(UNCERTAINTY_TEXT)
    lines.append(INSTRUCTIONS[task["condition"]])
    return [{"role": "user", "content": "\n".join(lines)}]


def request_for(plan, task):
    config = plan["config"]
    limit_key = "direct" if task["condition"] == "direct" else "cot"
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"][limit_key],
            "store": False, "n": 1}
