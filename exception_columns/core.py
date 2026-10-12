"""Frozen column deletions; no historical or new response selects a task."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest, rng_for
from exception_mistral_map_v3.parser import answer_boundary
from . import PROTOCOL_VERSION

ROOT = Path(__file__).resolve().parents[1]
WORLD_DIGEST = "a40ba696bfde0d863692f1f4ec53ca247aaf9378e76b16116a802256e69831c7"
SOURCE_PLAN_HASH = "81d29ff260b9b06999bd26f5cbea5611d3b5a9e507af31692b6ce0bff33c2a5a"
SEED = 2026101201
VALUES = ("record_1", "record_2")
ARMS = ("direct", "cot", "copy_class")
SCHEMAS = ("minimal", "description", "other_attributes", "full")
COLUMNS = {
    "minimal": ("id", "class"),
    "description": ("id", "descriptor", "class"),
    "other_attributes": ("id", "transmission", "seat_cover", "doors", "audit_marker", "class"),
    "full": ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker", "class"),
}
HEADERS = {"id": "License plate", "descriptor": "Description", "transmission": "Transmission",
           "seat_cover": "Seat cover", "doors": "Doors", "audit_marker": "Audit marker",
           "class": "Verified class"}
# Verbatim explanatory-study wording, fixed even when a column is absent.
INTRO = ("These are records of previously observed vehicles. Every record is accurate. "
         "An individual vehicle's class is fixed, and its license plate identifies it. "
         "The audit marker is an administrative code assigned independently of class. "
         "MISSING means the verified class has not been recorded. If that cell is "
         "MISSING, make your best prediction from the other records.")
QUESTION = "Which class, A, B, or C, does this vehicle belong to?"
FINAL = "Think step by step, then put ANSWER: followed by A, B, or C alone on the final line."
INSTRUCTIONS = {
    "direct": "Reply with only ANSWER: followed by A, B, or C.",
    "cot": FINAL,
    "copy_class": ("First copy the target vehicle's Verified class cell exactly, using COPIED: followed "
                   "by the cell value alone on the first line. Do not explain before that line. " + FINAL),
}
ANALYSIS_PLAN = {
    "primary": ["description_effect_on_reasoning_harm", "other_attributes_effect_on_reasoning_harm"],
    "primary_metric": "accuracy",
    "secondary_metric": "record_sensitivity: +1 target, -1 other record label, 0 background pattern",
    "unit": "world; all variants, schemas and arms stay paired",
    "bootstrap": "10000 whole-world resamples, seed 981723; descriptive unadjusted 95% intervals",
    "decision": "fixed exploratory development study; no success gate or automatic extension",
    "missing": "retain invalids; contrast-specific complete worlds plus full-plan bounds",
    "history": "reuse all 24 source worlds, never historical responses",
}


def validate_config(config):
    exact = {"protocol": PROTOCOL_VERSION, "model": "gpt-4o-2024-08-06", "temperature": 0,
             "max_completion_tokens": 1000, "max_total_attempts": 608}
    if not isinstance(config, dict) or set(config) != set(exact) | {"api_key_env", "timeout_seconds"}:
        raise ValueError("Config fields must match configs/columns_gpt4o.json; never include credentials")
    for key, value in exact.items():
        if config[key] != value or isinstance(config[key], bool):
            raise ValueError(f"This frozen study requires {key}={value!r}")
    if any(type(config[k]) is not int for k in ("max_completion_tokens", "max_total_attempts")):
        raise ValueError("Token and attempt caps must be integers")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must name an environment variable")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_worlds():
    snapshot = json.loads((ROOT / "configs/column_worlds.json").read_text())
    if digest(snapshot) != WORLD_DIGEST or snapshot["source_plan_hash"] != SOURCE_PLAN_HASH:
        raise ValueError("The bundled explanation-world snapshot has changed")
    return snapshot


def source_digest():
    files = list((ROOT / "exception_columns").glob("*.py"))
    files += [ROOT / "exception_pilot" / name for name in ("__init__.py", "core.py", "storage.py", "provider.py")]
    files += [ROOT / "exception_mistral_map_v3" / name for name in ("__init__.py", "parser.py")]
    return digest({str(p.relative_to(ROOT)): p.read_text() for p in sorted(files)})


def make_plan(config):
    validate_config(config)
    snapshot = source_worlds()
    tasks = []
    for world in snapshot["worlds"]:
        cells = [{"id": f"{world['id']}/{value}/{schema}/{arm}", "world_id": world["id"],
                  "value": value, "schema": schema, "arm": arm}
                 for value in VALUES for schema in SCHEMAS for arm in ARMS]
        rng_for(PROTOCOL_VERSION, SEED, world["id"]).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": config, "source_plan_hash": SOURCE_PLAN_HASH, "world_snapshot_hash": WORLD_DIGEST,
            "worlds": snapshot["worlds"], "tasks": tasks, "analysis_plan": ANALYSIS_PLAN,
            "seed": SEED}
    if len(plan["worlds"]) != 24 or len(tasks) != 576:
        raise ValueError("Expected all 24 worlds and exactly 576 tasks")
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"]):
        raise ValueError("Source, config or frozen plan differs; do not change an ongoing study")
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    target = world["target_index"]
    return {**task, "item_id": world["items"][target]["id"], "expected": world["roles"][task["value"]],
            "pattern_label": world["roles"]["pattern"], "target_position": world["order"].index(target) + 1,
            "columns": [HEADERS[k] for k in COLUMNS[task["schema"]]]}


def prompt_parts(plan, task):
    world = world_for(plan, task)
    columns = COLUMNS[task["schema"]]
    lines = ["| " + " | ".join(HEADERS[k] for k in columns) + " |", "|" + "---|" * len(columns)]
    for index in world["order"]:
        item = world["items"][index]
        values = [world["record_labels"][task["value"]][index] if k == "class" else item[k] for k in columns]
        lines.append("| " + " | ".join(values) + " |")
    target_id = world["items"][world["target_index"]]["id"]
    return INTRO + "\n\n", "\n".join(lines), "\n\nLicense plate: " + target_id + "\n" + QUESTION + "\n" + INSTRUCTIONS[task["arm"]]


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": [{"role": "user", "content": "".join(prompt_parts(plan, task))}],
            "temperature": config["temperature"], "max_completion_tokens": config["max_completion_tokens"],
            "n": 1, "store": False}


def score_response(task, response):
    text = response["text"].strip()
    answer, start = answer_boundary(text) if response["complete"] else (None, None)
    pretext = text[:start].strip() if start is not None else text
    copied, copy_valid = None, None
    reasoning = pretext
    if task["arm"] == "copy_class":
        first, _, rest = pretext.partition("\n")
        match = re.fullmatch(r"COPIED: ([ABC]|MISSING)", first.strip())
        copy_valid = bool(match)
        copied = match[1] if match else None
        reasoning = rest.strip() if match else pretext
    strict = answer is not None and text[start:].strip() == "ANSWER: " + answer
    answer_only = answer is not None and not pretext
    has_reasoning = bool(reasoning)
    adherence = (answer_only if task["arm"] == "direct" else
                 has_reasoning and (copy_valid if task["arm"] == "copy_class" else True))
    return {"status": "complete" if answer is not None else "invalid", "answer": answer,
            "copied": copied, "copy_valid": copy_valid, "strict_final_format": strict,
            "answer_only": answer_only, "has_reasoning": has_reasoning,
            "contract_met": bool(answer is not None and strict and adherence),
            "reasoning_words": len(reasoning.split())}
