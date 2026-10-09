"""Fresh paired worlds with answer-order anchors and a matched revision comparison."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import check_plan, describe, digest, rng_for
from exception_order.core import EXPLANATION_INSTRUCTION, response_format_for as anchor_response_format

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
ARMS = ("reasoning_first", "answer_first", "revision", "repeat_control")
ANCHOR_ARMS = ("reasoning_first", "answer_first")
REVISION_ARMS = ("revision", "repeat_control")
LABELS = ("A", "B", "C")
REVISION_INSTRUCTION = ('Output only a JSON object with three fields, "initial_answer", "reasoning", '
                        'and "final_answer". Set both answer fields to A, B, or C and write your '
                        'reasoning in "reasoning". Your final answer may match or differ from your initial answer.')
INSTRUCTIONS = {"reasoning_first": EXPLANATION_INSTRUCTION,
                "answer_first": EXPLANATION_INSTRUCTION,
                "revision": REVISION_INSTRUCTION,
                "repeat_control": REVISION_INSTRUCTION}
KEY_ORDERS = {"reasoning_first": ("reasoning", "answer"),
              "answer_first": ("answer", "reasoning"),
              "revision": ("initial_answer", "reasoning", "final_answer"),
              "repeat_control": ("initial_answer", "final_answer", "reasoning")}
ANALYSIS_PLAN = {
    "primary": "accuracy/repeat_control_minus_revision",
    "secondary": ["accuracy/answer_first_minus_reasoning_first", "record_sensitivity",
                  "initial_to_final_transitions", "pattern_following_revisions"],
    "unit": "fresh world; both record variants and all four arms remain paired",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "format": ("The revision and repeat-control arms have identical user messages and schemas differing "
               "only in property order. The two anchor arms retain the original two-field instructions "
               "and schemas. Validate actual serialized order and nonempty reasoning in every arm."),
    "invalid_answers": ("Retain and stop on any returned schema, order, empty-reasoning, or technical "
                        "failure; no resampling or continuation."),
    "interpretation": ("Compare final accuracy across all paired cases, not a subset conditioned on initial "
                       "correctness. Initial and final answers may differ; retain every valid contradiction. "
                       "The order effect includes placement, delay, and prospective schema information, "
                       "and does not identify a unique internal mechanism. Reasoning text is not evidence "
                       "of faithful internal computation."),
    "decision": "no scientific pass gate; no outcome-dependent extension",
}


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "api_key_env", "temperature",
              "max_completion_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/revision.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate answer-revision output directory")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 24:
        raise ValueError("This diagnostic fixes 24 fresh worlds and 192 planned calls")
    if type(config["seed"]) is not int or config["seed"] != 2026100894:
        raise ValueError("This diagnostic fixes seed 2026100894; do not select new worlds by outcome")
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
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 224:
        raise ValueError("The cumulative cap is 224 attempts, allowing 32 retries while completing 192 tasks")
    if type(config["timeout_seconds"]) not in (int, float) or config["timeout_seconds"] != 120:
        raise ValueError("This diagnostic fixes timeout_seconds at 120")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_order", "exception_revision")
    return digest({str(path.relative_to(root)): path.read_text()
                   for package in packages for path in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Each of six label-role permutations occurs exactly twice per target climate.
    assignments = [(roles, climate) for roles in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    revision_plates = set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        world["id"] = f"revision-list-{index:03d}"
        for item in world["items"]:
            plate = "V" + item["id"][1:]
            if plate in revision_plates:
                raise ValueError("Plate collision after revision namespace replacement")
            revision_plates.add(plate)
            item["id"] = plate
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
    if arm in ANCHOR_ARMS:
        return anchor_response_format(arm)
    fields = {"initial_answer": {"type": "string", "enum": list(LABELS)},
              "reasoning": {"type": "string"},
              "final_answer": {"type": "string", "enum": list(LABELS)}}
    # The new pair differs only in properties' serialized order. Required's order
    # and the instruction text stay identical in both conditions.
    return {"type": "json_schema", "json_schema": {
        "name": "class_response", "strict": True,
        "schema": {"type": "object", "properties": {key: fields[key] for key in KEY_ORDERS[arm]},
                   "required": ["initial_answer", "reasoning", "final_answer"],
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
    """Validate full output and field order; retain disagreements between valid answers.

    Visible reasoning metrics are descriptive. Every answer field is unscorable
    after any schema, order, empty-reasoning, or provider failure.
    """
    reason, initial_answer, final_answer = None, None, None
    schema_valid, order_valid = False, None
    nonempty, chars, words = None, None, None
    answer_fields = (("answer",) if task["arm"] in ANCHOR_ARMS else
                     ("initial_answer", "final_answer"))
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
            else:
                for field in answer_fields:
                    if not isinstance(value[field], str):
                        reason = field + "_not_string"
                        break
                    if value[field] not in LABELS:
                        reason = field + "_outside_enum"
                        break
                if reason is None and not isinstance(value["reasoning"], str):
                    reason = "reasoning_not_string"
                if reason is None:
                    schema_valid = True
                    order_valid = tuple(value) == KEY_ORDERS[task["arm"]]
                    reasoning = value["reasoning"].strip()
                    nonempty, chars, words = bool(reasoning), len(reasoning), len(reasoning.split())
                    if not order_valid:
                        reason = "key_order_mismatch"
                    elif not nonempty:
                        reason = "reasoning_empty"
                    elif task["arm"] in ANCHOR_ARMS:
                        final_answer = value["answer"]
                    else:
                        initial_answer = value["initial_answer"]
                        final_answer = value["final_answer"]
    return {"answer": final_answer, "initial_answer": initial_answer, "final_answer": final_answer,
            "status": "complete" if reason is None else "invalid",
            "schema_valid": schema_valid, "key_order_valid": order_valid,
            "reasoning_nonempty": nonempty, "reasoning_chars": chars, "reasoning_words": words,
            "invalid_reason": reason}
