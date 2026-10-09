"""Frozen prefix worlds with Mistral's full-completion response contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest
from exception_prefix import PROTOCOL_VERSION as ORIGINAL_PROTOCOL
from exception_prefix import core as original
from exception_prefix.core import (ARMS, BASE_ARMS, CAPABILITY_USER,
                                   INSTRUCTIONS, LABELS, VALUES, PrefixUnavailable,
                                   cut_parent_prefix, phenomenon_gate,
                                   replay_gate, task_meta, world_for)

from . import PROTOCOL_VERSION

ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
CAPABILITY_PREFIX = "Cobalt "
CAPABILITY_EXPECTED_FULL = "Cobalt Maple Lantern"
MODEL_DOCUMENTATION = {
    "requested_model": "mistral-small-2603", "identifier_kind": "versioned_model_id",
    "documented_family": "Mistral Small 4", "documentation_as_of": "2026-10-09",
    "immutable_backend_guaranteed": False,
    "returned_text_contract": "full_completion_including_supplied_prefix",
}
ANALYSIS_PLAN = copy.deepcopy(original.ANALYSIS_PLAN)
ANALYSIS_PLAN.update({
    "unit": "world; record variants and arms remain paired; world identities are reused from the prefix screen",
    "worlds": "The same frozen 12 worlds and schedule as the DeepSeek prefix screen, not new independent worlds.",
    "capability": "With the word-boundary prefix 'Cobalt ' (one trailing ASCII space), returned full text must equal 'Cobalt Maple Lantern' exactly, including whitespace.",
    "revision": "V2 replaces the V1 mid-word capability prefix only. Following transport errors, V1 attempt 7 returned 'Cobalt Mape Lantern'; V1 remains failed. This does not establish why the letter was omitted. No V1 research-case responses returned. All task worlds, base prompts, replay cuts, and scientific gates are unchanged.",
    "return_contract": ("Mistral returns full assistant completion including supplied prefix. Replay must "
                        "start with the exact supplied prefix. Remove exactly that prefix length once only "
                        "to compare suffixes; score the original full returned text without prepending it."),
})


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "endpoint", "api_key_env", "temperature",
              "reasoning_effort", "max_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/mistral_prefix_v2.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate Mistral prefix output directory")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 12:
        raise ValueError("This screen fixes 12 worlds, 48 base requests and up to 24 replays")
    if type(config["seed"]) is not int or config["seed"] != 2026100941:
        raise ValueError("This screen fixes seed 2026100941 and preserves the existing prefix worlds")
    if config["model"] != "mistral-small-2603" or config["endpoint"] != ENDPOINT:
        raise ValueError("This screen fixes mistral-small-2603 and the Mistral chat-completions endpoint")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This screen fixes temperature at zero")
    if config["reasoning_effort"] != "none":
        raise ValueError("This screen requires reasoning_effort=none")
    limits = config["max_tokens"]
    if (not isinstance(limits, dict)
            or limits != {"capability": 32, "direct": 1600, "visible": 1600, "replay": 1600}
            or any(type(value) is not int for value in limits.values())):
        raise ValueError("Token ceilings must be 32 for capability and 1600 for every base/replay arm")
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 89:
        raise ValueError("The cumulative cap is 89 attempts for up to 73 planned responses")
    if type(config["timeout_seconds"]) not in (int, float) or config["timeout_seconds"] != 120:
        raise ValueError("This screen fixes timeout_seconds at 120")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_cue",
                "exception_prefix", "exception_mistral_prefix", "exception_mistral_prefix_v2")
    return digest({str(path.relative_to(root)): path.read_text()
                   for package in packages for path in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Preserve the original generator's RNG namespace and fixed input config.
    # This changes provider routing, not the previously frozen world identities.
    original_config = {
        "protocol": ORIGINAL_PROTOCOL, "n_worlds": 12, "seed": 2026100941,
        "model": "deepseek-flash", "endpoint": original.ENDPOINT, "api_key_env": "DEEPSEEK_API_KEY",
        "temperature": 0.0, "thinking": {"type": "disabled"},
        "max_tokens": {"capability": 32, "direct": 1600, "visible": 1600, "replay": 1600},
        "max_total_attempts": 89, "timeout_seconds": 120,
    }
    original_plan = original.make_plan(original_config)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "model_documentation": copy.deepcopy(MODEL_DOCUMENTATION),
            "worlds": copy.deepcopy(original_plan["worlds"]), "tasks": copy.deepcopy(original_plan["tasks"]),
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


def messages_for(plan, task, records=None):
    if task["family"] == "capability":
        return [{"role": "user", "content": CAPABILITY_USER},
                {"role": "assistant", "content": CAPABILITY_PREFIX, "prefix": True}]
    return original.messages_for(plan, task, records)


def request_for(plan, task, records=None):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task, records),
            "temperature": config["temperature"], "max_tokens": config["max_tokens"][task["arm"]],
            "reasoning_effort": config["reasoning_effort"], "stream": False}


def score_response(task, response, meta=None):
    # Initialize the same descriptive fields as the preserved prefix screen.
    result = {"answer": None, "status": "invalid", "format_valid": False,
              "invalid_reason": None, "capability_exact": None, "pre_answer_text": None,
              "replay_answer_match": None, "replay_exact_suffix_match": None,
              "replay_pattern_error_match": None, "replay_prefix_exact": None, "replay_suffix": None}
    if response.get("complete") is not True:
        result["invalid_reason"] = response.get("provider_invalid_reason") or "provider_incomplete"
    elif not isinstance(response.get("text"), str):
        result["invalid_reason"] = "content_not_string"
    elif task["family"] == "capability":
        result["capability_exact"] = response["text"] == CAPABILITY_EXPECTED_FULL
        if result["capability_exact"]:
            result.update(status="complete", format_valid=True)
        else:
            result["invalid_reason"] = "capability_full_completion_mismatch"
    elif task["family"] == "replay":
        if not meta or meta.get("prefix_available") is not True:
            result["invalid_reason"] = "prefix_unavailable"
        else:
            prefix = meta["prefix_text"]
            result["replay_prefix_exact"] = response["text"].startswith(prefix)
            if not result["replay_prefix_exact"]:
                result["invalid_reason"] = "replay_prefix_mismatch"
            else:
                # The provider returns the supplied prefix as part of the full
                # completion. Do not prepend it, trim it, or search for it.
                suffix = response["text"][len(prefix):]
                scored = original.score_response({**task, "family": "base", "arm": "visible"}, response, meta)
                result.update(scored)
                result["replay_suffix"] = suffix
                if scored["status"] == "complete":
                    result.update(replay_answer_match=scored["answer"] == meta["parent_answer"],
                                  replay_exact_suffix_match=suffix == meta["parent_suffix"],
                                  replay_pattern_error_match=(scored["answer"] == meta["parent_answer"]
                                                              if meta["parent_pattern_error"] else None))
    else:
        result.update(original.score_response(task, response, meta))
    return result


def capability_gate(plan, records):
    result = original.capability_gate(plan, records)
    result.pop("required_raw_suffix", None)
    result["exact_full_completion_match"] = result.pop("exact_suffix_match")
    result["required_raw_completion"] = CAPABILITY_EXPECTED_FULL
    return result
