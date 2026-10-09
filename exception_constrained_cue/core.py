"""Reuse the frozen cue worlds; compare one instruction under a shared JSON schema."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from exception_cue import PROTOCOL_VERSION as CUE_PROTOCOL
from exception_cue.core import make_plan as cue_plan, messages_for as cue_messages
from exception_cue.core import task_meta, world_for
from exception_pilot.core import check_plan, digest, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
ARMS = ("direct", "cue")
LABELS = ("A", "B", "C")
CUE_PREFIX = "Think step by step before answering. "
FINAL_INSTRUCTION = ('Output only a JSON object with one field, "answer", '
                     'whose value is A, B, or C.')
INSTRUCTIONS = {"direct": FINAL_INSTRUCTION, "cue": CUE_PREFIX + FINAL_INSTRUCTION}
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "class_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string", "enum": list(LABELS)}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}
ANALYSIS_PLAN = {
    "primary": "accuracy/direct_minus_cue",
    "secondary": ["record_sensitivity/direct_minus_cue"],
    "unit": "world; both record variants and response arms remain paired",
    "worlds": "The same 24 frozen worlds as the cue study, not fresh independent confirmation data.",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "format": "An identical strict JSON schema in both arms; no prose or extra fields.",
    "invalid_answers": "Retain and stop on any returned schema or technical failure; no resampling or continuation.",
    "interpretation": ("This compares a reasoning instruction under constrained output. It does not establish "
                       "whether hidden reasoning occurred or identify an internal mechanism. Changes from "
                       "earlier free-output runs also change the response format."),
    "decision": "no scientific pass gate; no outcome-dependent extension",
}


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "api_key_env", "temperature",
              "max_completion_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/constrained_cue.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate constrained-cue output directory")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 24:
        raise ValueError("This diagnostic fixes 24 worlds and 96 planned calls")
    if type(config["seed"]) is not int or config["seed"] != 2026100892:
        raise ValueError("This diagnostic fixes seed 2026100892 and reuses the cue worlds")
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
        raise ValueError("Both arms must receive the same completion cap of 1000 tokens")
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 112:
        raise ValueError("The cumulative cap is 112 attempts, allowing 16 retries while completing 96 tasks")
    if type(config["timeout_seconds"]) not in (int, float) or config["timeout_seconds"] != 120:
        raise ValueError("This diagnostic fixes timeout_seconds at 120")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_cue",
                "exception_constrained_cue")
    return digest({str(path.relative_to(root)): path.read_text()
                   for package in packages for path in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Reuse the original generator with its original protocol/configuration. Changing
    # its RNG namespace would silently create new worlds rather than this fixed set.
    original_config = {**copy.deepcopy(config), "protocol": CUE_PROTOCOL,
                       "max_completion_tokens": {arm: 1000 for arm in ("direct", "cue", "visible")},
                       "max_total_attempts": 160}
    worlds = copy.deepcopy(cue_plan(original_config)["worlds"])
    tasks = []
    for index, world in enumerate(worlds):
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


def messages_for(plan, task):
    # Reuse every table and question byte, including the original MISSING definition.
    # Only the last instruction line changes to the common constrained-output form.
    messages = cue_messages(plan, task)
    prefix, _ = messages[0]["content"].rsplit("\n", 1)
    messages[0]["content"] = prefix + "\n" + INSTRUCTIONS[task["arm"]]
    return messages


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"][task["arm"]],
            "response_format": copy.deepcopy(RESPONSE_FORMAT), "n": 1, "store": False}


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
    """Require the whole returned content to satisfy the exact single-field schema."""
    reason, answer = None, None
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
            elif set(value) != {"answer"}:
                reason = "answer_field_only"
            elif not isinstance(value["answer"], str):
                reason = "answer_not_string"
            elif value["answer"] not in LABELS:
                reason = "answer_outside_enum"
            else:
                answer = value["answer"]
    valid = reason is None
    return {"answer": answer, "status": "complete" if valid else "invalid",
            "schema_valid": valid, "invalid_reason": reason}
