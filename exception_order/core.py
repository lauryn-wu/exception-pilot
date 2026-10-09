"""Fresh paired worlds, identical explanation instructions, and ordered schemas."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import check_plan, describe, digest, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
ARMS = ("answer_only", "reasoning_first", "answer_first")
LABELS = ("A", "B", "C")
ANSWER_ONLY_INSTRUCTION = ('Output only a JSON object with one field, "answer", '
                           'whose value is A, B, or C.')
EXPLANATION_INSTRUCTION = ('Output only a JSON object with two fields, "answer" and "reasoning". '
                           'Set "answer" to A, B, or C and write your reasoning in "reasoning".')
INSTRUCTIONS = {"answer_only": ANSWER_ONLY_INSTRUCTION,
                "reasoning_first": EXPLANATION_INSTRUCTION,
                "answer_first": EXPLANATION_INSTRUCTION}
KEY_ORDERS = {"answer_only": ("answer",),
              "reasoning_first": ("reasoning", "answer"),
              "answer_first": ("answer", "reasoning")}
ANALYSIS_PLAN = {
    "primary": "accuracy/answer_first_minus_reasoning_first",
    "secondary": ["accuracy/answer_only_minus_reasoning_first",
                  "accuracy/answer_only_minus_answer_first", "record_sensitivity"],
    "unit": "fresh world; both record variants and all three arms remain paired",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "format": ("Explanation arms have identical user messages and schemas differing only in property "
               "key order. Validate actual serialized output order and nonempty reasoning text."),
    "invalid_answers": ("Retain and stop on any returned schema, order, empty-reasoning, or technical "
                        "failure; no resampling or continuation."),
    "interpretation": ("This compares constrained output order, not a unique internal mechanism. "
                       "Text after an answer cannot revise the scored first answer, but the model "
                       "knows the full schema and can anticipate later text. Reasoning text is not "
                       "evidence of faithful internal computation."),
    "decision": "no scientific pass gate; no outcome-dependent extension",
}


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "api_key_env", "temperature",
              "max_completion_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/order.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate answer-order output directory")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 12:
        raise ValueError("This diagnostic fixes 12 fresh worlds and 72 planned calls")
    if type(config["seed"]) is not int or config["seed"] != 2026100893:
        raise ValueError("This diagnostic fixes seed 2026100893; do not select new worlds by outcome")
    if config["model"] != "gpt-4o-2024-08-06":
        raise ValueError("This diagnostic fixes gpt-4o-2024-08-06")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This diagnostic fixes temperature at 0")
    limits = config["max_completion_tokens"]
    if (not isinstance(limits, dict) or limits != {arm: 1000 for arm in ARMS}
            or any(type(value) is not int for value in limits.values())):
        raise ValueError("All arms must receive the same completion cap of 1000 tokens")
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 88:
        raise ValueError("The cumulative cap is 88 attempts, allowing 16 retries while completing 72 tasks")
    if type(config["timeout_seconds"]) not in (int, float) or config["timeout_seconds"] != 120:
        raise ValueError("This diagnostic fixes timeout_seconds at 120")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_order")
    return digest({str(path.relative_to(root)): path.read_text()
                   for package in packages for path in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Each of six label-role permutations occurs exactly once per target climate.
    assignments = [(roles, climate) for roles in itertools.permutations(LABELS)
                   for climate in ("cold", "warm")]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        world["id"] = f"order-list-{index:03d}"
        for item in world["items"]:
            item["id"] = "R" + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip(("record_1", "record_2", "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", config["seed"], index)
        other_labels = [roles[0]] * 3 + [roles[1]] * 2
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
            version[target] = world["roles"][value]
            world["record_labels"][value] = version
        worlds.append(world)
        cells = [{"id": f"{world['id']}/{value}/{arm}", "world_id": world["id"],
                  "family": "diagnostic", "value": value, "arm": arm}
                 for value in VALUES for arm in ARMS]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", config["seed"], index).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "worlds": worlds, "tasks": tasks,
            "analysis_plan": copy.deepcopy(ANALYSIS_PLAN)}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    validate_config(plan["config"])
    if plan != make_plan(plan["config"]):
        raise ValueError("Code or saved plan differs; preserve the run and use a new output directory")
    return plan


def world_for(plan, task):
    return next(world for world in plan["worlds"] if world["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    i = world["target_index"]
    item = world["items"][i]
    return {"world_id": world["id"], "family": task["family"], "value": task["value"],
            "arm": task["arm"], "item_id": item["id"], "expected": world["roles"][task["value"]],
            "pattern_label": world["roles"]["pattern"], "target_position": world["order"].index(i) + 1}


def messages_for(plan, task):
    world = world_for(plan, task)
    lines = [INTRO, "",
             "| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |",
             "|---|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[key] for key in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        fields.append(world["record_labels"][task["value"]][i])
        lines.append("| " + " | ".join(fields) + " |")
    lines += ["", describe(world["items"][world["target_index"]]), QUESTION, INSTRUCTIONS[task["arm"]]]
    return [{"role": "user", "content": "\n".join(lines)}]


def response_format_for(arm):
    fields = {"answer": {"type": "string", "enum": list(LABELS)}, "reasoning": {"type": "string"}}
    # The two explanation schemas differ only in properties' serialized key order.
    # Keep required's order identical: it is not an independent manipulation.
    return {"type": "json_schema", "json_schema": {
        "name": "class_response", "strict": True,
        "schema": {"type": "object", "properties": {key: fields[key] for key in KEY_ORDERS[arm]},
                   "required": ["answer"] if arm == "answer_only" else ["answer", "reasoning"],
                   "additionalProperties": False}}}


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"][task["arm"]],
            "response_format": response_format_for(task["arm"]), "n": 1, "store": False}


def ordered_request_equal(left, right):
    """Compare serialized key order as well as values; normal dict equality loses it."""
    return json.dumps(left, ensure_ascii=False, allow_nan=False, separators=(",", ":")) == json.dumps(
        right, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


class DuplicateJSONKey(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKey("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def score_response(task, response):
    """Validate the entire JSON response, including actual output order.

    Reasoning metrics describe stripped visible text, not its truth, quality,
    faithfulness, or internal computation. Any manipulation failure is retained
    as invalid; the first answer field is scored only when every check passes.
    """
    reason, answer = None, None
    schema_valid, order_valid = False, None
    nonempty, chars, words = None, None, None
    if response.get("complete") is not True:
        reason = "provider_incomplete"
    elif not isinstance(response.get("text"), str):
        reason = "content_not_string"
    else:
        try:
            value = json.loads(response["text"], object_pairs_hook=_unique_object,
                               parse_constant=_reject_constant)
        except DuplicateJSONKey:
            reason = "duplicate_json_key"
        except (ValueError, TypeError, RecursionError):
            reason = "invalid_json"
        else:
            if not isinstance(value, dict):
                reason = "object_required"
            elif set(value) != set(KEY_ORDERS[task["arm"]]):
                reason = "unexpected_fields"
            elif not isinstance(value["answer"], str):
                reason = "answer_not_string"
            elif value["answer"] not in LABELS:
                reason = "answer_outside_enum"
            elif task["arm"] != "answer_only" and not isinstance(value["reasoning"], str):
                reason = "reasoning_not_string"
            else:
                schema_valid = True
                order_valid = tuple(value) == KEY_ORDERS[task["arm"]]
                if task["arm"] != "answer_only":
                    reasoning = value["reasoning"].strip()
                    nonempty, chars, words = bool(reasoning), len(reasoning), len(reasoning.split())
                if not order_valid:
                    reason = "key_order_mismatch"
                elif nonempty is False:
                    reason = "reasoning_empty"
                else:
                    answer = value["answer"]
    return {"answer": answer, "status": "complete" if reason is None else "invalid",
            "schema_valid": schema_valid, "key_order_valid": order_valid,
            "reasoning_nonempty": nonempty, "reasoning_chars": chars, "reasoning_words": words,
            "invalid_reason": reason}
