"""Frozen 5 × 2 design; neither the first entry nor any result selects cases."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import check_plan, describe, digest, rng_for
from . import CALLS_PER_WORLD, PROTOCOL_VERSION

SEED = 2026101201
PLATE_PREFIX = "J"
VALUES = ("record_1", "record_2")
LABELS = ("A", "B", "C")
CONDITIONS = ("copy_record", "copy_initial", "initial_answer", "copy_marker", "no_entry")
ORDERS = ("reason_then_answer", "answer_then_reason")
CLASS_CONDITIONS = ("copy_record", "copy_initial", "initial_answer")
COPY_CONDITIONS = ("copy_record", "copy_initial", "copy_marker")
KEY_ORDERS = {
    "reason_then_answer": ("first_value", "reasoning", "final_answer"),
    "answer_then_reason": ("first_value", "final_answer", "reasoning"),
}
COPY_CLASS = "Copy the target vehicle's Verified class cell exactly into first_value. "
ENTRY_INSTRUCTIONS = {
    "copy_record": COPY_CLASS + "Treat this entry as the recorded class.",
    "copy_initial": COPY_CLASS + "Treat this entry as the initial answer.",
    "initial_answer": "Give your initial answer to the class question in first_value.",
    "copy_marker": "Copy the target vehicle's Audit marker cell exactly into first_value.",
    "no_entry": "Set first_value to null.",
}
COMMON_INSTRUCTION = (
    'Output only a JSON object with the fields "first_value", "reasoning", and "final_answer". '
    'Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. '
    "Your final answer may match or differ from the preliminary entry."
)
DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION, "provider": "openai", "model": "gpt-4o-2024-08-06",
    "api_key_env": "OPENAI_API_KEY", "n_worlds": 24, "seed": SEED, "target_position": 10,
    "temperature": 0, "max_completion_tokens": 1000, "max_total_attempts": 528,
    "timeout_seconds": 120,
}
PRIMARY = "accuracy/initial_minus_record_reasoning_harm"
ANALYSIS_PLAN = {
    "primary": PRIMARY,
    "harm": "accuracy(answer_then_reason) minus accuracy(reason_then_answer)",
    "primary_definition": "harm(initial_answer) minus harm(copy_record)",
    "bridge": "harm(copy_initial) minus harm(copy_record); secondary",
    "metrics": ["accuracy", "record_sensitivity", "first_entry_correctness", "transitions",
                "pattern_choices", "rationale_text_flags", "output_compliance"],
    "record_sensitivity": "+1 correct target class, -1 other target-record class, 0 pattern class",
    "unit": "whole world, averaging its two record variants before any contrast",
    "bootstrap": "10000 whole-world resamples, seed 981723; descriptive 95% percentile intervals",
    "sign_test": "exact two-sided sign test on nonzero world-level contrasts; tests sign balance, not mean magnitude",
    "selection": "all assigned cases; never condition primary effects on first-entry correctness",
    "missing": "retain invalid responses without resampling; complete-world estimates and full-plan bounds",
    "decision": "fixed 480 planned calls; no scientific pass gate, extension, or automatic next study",
    "scope": "fresh GPT-4o worlds with the target at row 10; no position-general or mechanistic claim",
}


def validate_config(config):
    if not isinstance(config, dict) or set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Use exactly configs/evidence_role_gpt4o.json fields; credentials belong only in the environment")
    for key, expected in DEFAULT_CONFIG.items():
        if key == "api_key_env":
            if not isinstance(config[key], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", config[key]):
                raise ValueError("api_key_env must be an environment variable name")
        elif type(config[key]) is not type(expected) or config[key] != expected:
            raise ValueError(f"This fixed protocol requires {key}={expected!r}; use a new protocol for changes")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_evidence_role", "exception_pilot", "exception_counterfactual",
                "exception_explanation", "exception_factorial", "exception_wording")
    paths = [p for package in packages for p in sorted((root / package).glob("*.py"))]
    paths.append(root / "EVIDENCE_ROLE_PROTOCOL.md")
    return digest({str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in paths})


def request_hash(request):
    """Unlike dict equality, preserve the schema's serialized property order."""
    encoded = json.dumps(request, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def make_plan(config):
    validate_config(config)
    assignments = [(roles, climate) for roles in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", SEED).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world({"seed": SEED}, index, used)
        for field in ("labels", "majority_labels", "support_exception_indices"):
            world.pop(field)
        world["id"] = f"er-list-{index:03d}"
        for item in world["items"]:
            item["id"] = PLATE_PREFIX + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip((*VALUES, "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", SEED, index)
        other_labels = [roles[0]] * (2 if index % 2 else 3) + [roles[1]] * (3 if index % 2 else 2)
        rng.shuffle(other_labels)
        markers = ["X", "Y", "Z"] * 3 + [rng.choice(["X", "Y", "Z"])]
        rng.shuffle(markers)
        labels = []
        for i, item in enumerate(world["items"]):
            item["audit_marker"] = markers[i]
            labels.append(roles[2] if item["climate"] == climate else other_labels.pop())
        world["record_labels"] = {}
        for value in VALUES:
            version = labels.copy()
            version[target] = world["roles"][value]
            world["record_labels"][value] = version
        world["original_order"] = world["order"].copy()
        world["order"] = [i for i in world["order"] if i != target] + [target]
        worlds.append(world)
        cells = [{"id": f"{world['id']}/{value}/{condition}/{order}", "world_id": world["id"],
                  "value": value, "condition": condition, "order": order}
                 for value, condition, order in itertools.product(VALUES, CONDITIONS, ORDERS)]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", SEED, index).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "worlds": worlds, "tasks": tasks,
            "analysis_plan": copy.deepcopy(ANALYSIS_PLAN), "entry_instructions": ENTRY_INSTRUCTIONS.copy(),
            "common_instruction": COMMON_INSTRUCTION}
    plan["request_hashes"] = {t["id"]: request_hash(request_for(plan, t)) for t in tasks}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text(encoding="utf-8"))
    check_plan(plan)
    if plan != make_plan(plan["config"]):
        raise ValueError("Code, protocol, config or frozen plan differs; preserve this run and use a new directory")
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    target = world["items"][world["target_index"]]
    expected = world["roles"][task["value"]]
    copy_expected = (target["audit_marker"] if task["condition"] == "copy_marker" else
                     expected if task["condition"] in ("copy_record", "copy_initial") else None)
    return {"world_id": world["id"], "value": task["value"], "condition": task["condition"],
            "order": task["order"], "item_id": target["id"], "expected": expected,
            "other_record_label": world["roles"][next(v for v in VALUES if v != task["value"])],
            "pattern_label": world["roles"]["pattern"], "copy_expected": copy_expected,
            "target_marker": target["audit_marker"], "target_position": 10}


def table_for(plan, task):
    world = world_for(plan, task)
    lines = ["| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |",
             "|---|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        lines.append("| " + " | ".join(fields + [world["record_labels"][task["value"]][i]]) + " |")
    return "\n".join(lines)


def messages_for(plan, task):
    world = world_for(plan, task)
    content = "\n".join([INTRO, "", table_for(plan, task), "",
                          describe(world["items"][world["target_index"]]), QUESTION,
                          ENTRY_INSTRUCTIONS[task["condition"]], COMMON_INSTRUCTION])
    return [{"role": "user", "content": content}]


def response_format_for(order):
    fields = {"first_value": {"type": ["string", "null"]}, "reasoning": {"type": "string"},
              "final_answer": {"type": "string", "enum": list(LABELS)}}
    return {"type": "json_schema", "json_schema": {"name": "class_response", "strict": True,
            "schema": {"type": "object", "properties": {k: fields[k] for k in KEY_ORDERS[order]},
                       "required": ["first_value", "reasoning", "final_answer"], "additionalProperties": False}}}


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task), "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"], "response_format": response_format_for(task["order"]),
            "n": 1, "store": False}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def score_response(task, response):
    scored = {"status": "invalid", "answer": None, "first_value": None, "reasoning": None,
              "schema_valid": False, "key_order_valid": False, "reasoning_nonempty": False,
              "entry_format_met": False, "output_contract_met": False, "invalid_reason": None}
    if not response.get("complete"):
        scored["invalid_reason"] = "provider_incomplete"
        return scored
    try:
        obj = json.loads(response["text"], object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, TypeError):
        scored["invalid_reason"] = "invalid_json"
        return scored
    if (not isinstance(obj, dict) or set(obj) != {"first_value", "reasoning", "final_answer"}
            or not (obj["first_value"] is None or isinstance(obj["first_value"], str))
            or not isinstance(obj["reasoning"], str) or obj["final_answer"] not in LABELS):
        scored["invalid_reason"] = "schema_invalid"
        return scored
    scored["schema_valid"] = True
    scored["key_order_valid"] = tuple(obj) == KEY_ORDERS[task["order"]]
    scored["reasoning_nonempty"] = bool(obj["reasoning"].strip())
    if not scored["key_order_valid"] or not scored["reasoning_nonempty"]:
        scored["invalid_reason"] = "wrong_key_order" if not scored["key_order_valid"] else "empty_reasoning"
        return scored
    first = obj["first_value"]
    entry_format = (first is None if task["condition"] == "no_entry" else
                    first in ("X", "Y", "Z") if task["condition"] == "copy_marker" else first in LABELS)
    # Wrong copies and wrong/absent first entries remain final-answer data.
    scored.update(status="complete", answer=obj["final_answer"], first_value=first,
                  reasoning=obj["reasoning"], entry_format_met=entry_format, output_contract_met=entry_format)
    return scored
