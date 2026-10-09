"""Frozen fresh worlds and four paired, early assistant-prefix interventions.

Every intervention preserves a correctly copied target record. No observed
answer, natural trace, or mapping outcome selects a world or changes its prefix.
"""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_mistral_map_v3.parser import answer_boundary
from exception_pilot.core import check_plan, describe, digest, rng_for

from . import PROTOCOL_VERSION

ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
CAPABILITY_USER = "Output exactly this text, without quotation marks or commentary:\nCobalt Maple Lantern"
CAPABILITY_PREFIX = "Cobalt "
CAPABILITY_EXPECTED_FULL = "Cobalt Maple Lantern"
LABELS = ("A", "B", "C")
VALUES = ("record_1", "record_2")
BASE_ARMS = ("direct", "visible")
ARMS = ("original", "paraphrase", "recorded", "bare")
PARENTHETICALS = {
    "original": "(This is the value we are trying to confirm or predict.)",
    "paraphrase": "(This is the value we are trying to verify or infer.)",
    "recorded": "(This is the value already recorded for this vehicle.)",
    "bare": "",
}
INSTRUCTIONS = {
    "direct": "Output only ANSWER: followed by A, B, or C.",
    "visible": ("Think step by step before answering. Write your reasoning, then put "
                "ANSWER: followed by A, B, or C alone on the final line."),
}
DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION, "n_worlds": 24, "seed": 2026100944,
    "model": "mistral-small-2603", "endpoint": ENDPOINT, "api_key_env": "MISTRAL_API_KEY",
    "temperature": 0.6, "top_p": 0.95, "reasoning_effort": "none", "repeats": 3,
    "max_tokens": {"capability": 32, "direct": 1600, "visible": 1600, "intervention": 1600},
    "max_total_attempts": 705, "timeout_seconds": 120, "min_request_interval_seconds": 10,
}
ANALYSIS_PLAN = {
    "primary": "bare_minus_original",
    "secondary": ["bare_minus_paraphrase", "recorded_minus_original", "recorded_minus_paraphrase",
                  "recorded_minus_bare", "original_minus_paraphrase", "direct_minus_visible"],
    "outcome": "accuracy of the terminal answer; pattern-error choices are descriptive secondary outcomes",
    "unit": "independent world; average three repeats within each case and two record variants within each world; equal world weights",
    "bootstrap": "10000 whole-world resamples, seed 981723; descriptive unadjusted 95% percentile intervals, computed only after all planned responses for that contrast have returned",
    "missingness": "Retain every returned invalid answer without resampling; require all cells for a complete-world contrast and report full-plan point-estimate bounds after all responses return.",
    "allocation": "Capability, then all 96 baseline tasks, then all 576 intervention tasks; no scientific gate and no filtering by baseline results.",
    "hypothesis": "Adding the original prediction parenthetical to an accurate copied class can reduce accuracy relative to the bare factual statement; paraphrase checks semantic robustness and recorded wording checks repair.",
    "interpretation": "A randomized supplied-prefix text intervention establishes effects of these particular prefix variants on downstream answers. It does not establish mediation of spontaneous errors or an internal mechanism. All intervention prefixes are standardized fresh templates, not resumed natural explanations. Bare deletion changes length; recorded wording may be a helpful cue.",
    "decision": "Fixed 24 fresh worlds; no outcome-dependent extension, arm pooling, or selection.",
}


def validate_config(config):
    expected = copy.deepcopy(DEFAULT_CONFIG)
    key = config.get("api_key_env") if isinstance(config, dict) else None
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key):
        raise ValueError("api_key_env must name an environment variable, never contain a key")
    expected["api_key_env"] = key
    if (config != expected or any(type(config[k]) is not type(v) for k, v in expected.items())
            or any(type(v) is not int for v in config["max_tokens"].values())):
        raise ValueError("Use the fixed configs/mistral_framing.json; changes require a new protocol")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_mistral_framing")
    paths = [p for package in packages for p in sorted((root / package).glob("*.py"))]
    # The fixed presentation parser and provider are reused without editing them.
    paths.extend(root / name for name in (
        "exception_mistral_map_v3/__init__.py", "exception_mistral_map_v3/parser.py",
        "exception_mistral_prefix/__init__.py", "exception_mistral_prefix/provider.py",
        "exception_mistral_prefix_v2/__init__.py", "exception_mistral_prefix_v2/provider.py",
        "exception_mistral_prefix/core.py", "exception_prefix/__init__.py", "exception_prefix/core.py",
        "exception_cue/__init__.py", "exception_cue/core.py"))
    return digest({str(p.relative_to(root)): p.read_text() for p in sorted(set(paths))})


def _worlds(config):
    assignments = [(roles, climate) for roles in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, used = [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        # Only the ternary record_labels below are sent or scored. Remove the
        # binary generator's unused label maps so the saved plan is unambiguous.
        for legacy_field in ("labels", "majority_labels", "support_exception_indices"):
            world.pop(legacy_field)
        world["id"] = f"framing-list-{index:03d}"
        for item in world["items"]:
            item["id"] = "F" + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip(("record_1", "record_2", "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", config["seed"], index)
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
        worlds.append(world)
    return worlds


def make_plan(config):
    validate_config(config)
    worlds = _worlds(config)
    cases = [(w["id"], value) for w in worlds for value in VALUES]
    tasks = [{"id": "prefix-capability", "family": "capability", "arm": "capability"}]
    baseline_cases = cases.copy()
    rng_for(PROTOCOL_VERSION, "baseline-blocks", config["seed"]).shuffle(baseline_cases)
    for world_id, value in baseline_cases:
        block = [{"id": f"{world_id}/{value}/{arm}", "family": "base", "arm": arm,
                  "world_id": world_id, "value": value} for arm in BASE_ARMS]
        rng_for(PROTOCOL_VERSION, "baseline-arms", config["seed"], world_id, value).shuffle(block)
        tasks.extend(block)
    for repeat in range(1, config["repeats"] + 1):
        repeat_cases = cases.copy()
        rng_for(PROTOCOL_VERSION, "intervention-blocks", config["seed"], repeat).shuffle(repeat_cases)
        for world_id, value in repeat_cases:
            block = [{"id": f"{world_id}/{value}/{arm}/r{repeat}", "family": "intervention", "arm": arm,
                      "world_id": world_id, "value": value, "repeat": repeat} for arm in ARMS]
            rng_for(PROTOCOL_VERSION, "intervention-arms", config["seed"], repeat, world_id, value).shuffle(block)
            tasks.extend(block)
    if len(worlds) != 24 or len(tasks) != 673 or len({t["id"] for t in tasks}) != 673:
        raise ValueError("The fixed design requires 24 worlds and 673 unique tasks")
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "worlds": worlds, "tasks": tasks,
            "analysis_plan": copy.deepcopy(ANALYSIS_PLAN), "parentheticals": copy.deepcopy(PARENTHETICALS),
            "template_provenance": {
                "source_case": "prefix-list-008/record_1/visible",
                "source_run": "mistral-map-v3-001",
                "adaptation": "Opening wording and data-list presentation adapted from the inspected source explanation before checkpoint c03. All target attributes and classes are filled from fresh worlds; only the final parenthetical varies across arms. The template is fixed before new responses and does not depend on any new baseline or intervention answer.",
                "natural_trace_replay": False,
            },
            "interpretation": ANALYSIS_PLAN["interpretation"]}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"]):
        raise ValueError("Code, config, or saved plan differs; preserve the run and use a new output directory")
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def prefix_for(plan, task):
    world = world_for(plan, task)
    item = world["items"][world["target_index"]]
    lines = [f"Let's analyze the given records step by step to determine the class of the vehicle with the license plate {item['id']}.",
             "", f"1. **Given Data for {item['id']}:**",
             f"   - License plate: {item['id']}", f"   - Description: {item['descriptor']}",
             f"   - Transmission: {item['transmission']}", f"   - Seat cover: {item['seat_cover']}",
             f"   - Doors: {item['doors']}", f"   - Audit marker: {item['audit_marker']}"]
    line = f"   - Verified class: {world['roles'][task['value']]}"
    parenthetical = PARENTHETICALS[task["arm"]]
    if parenthetical:
        line += " " + parenthetical
    return "\n".join(lines + [line]) + "\n\n"


def task_meta(plan, task):
    if task["family"] == "capability":
        return {"family": "capability", "arm": "capability", "world_id": None, "value": None,
                "repeat": None, "item_id": None, "expected": None, "pattern_label": None,
                "target_position": None, "prefix_text": CAPABILITY_PREFIX}
    world = world_for(plan, task)
    target = world["target_index"]
    return {"family": task["family"], "arm": task["arm"], "world_id": world["id"],
            "value": task["value"], "repeat": task.get("repeat"), "item_id": world["items"][target]["id"],
            "expected": world["roles"][task["value"]], "pattern_label": world["roles"]["pattern"],
            "target_position": world["order"].index(target) + 1,
            "prefix_text": prefix_for(plan, task) if task["family"] == "intervention" else ""}


def messages_for(plan, task):
    if task["family"] == "capability":
        return [{"role": "user", "content": CAPABILITY_USER},
                {"role": "assistant", "content": CAPABILITY_PREFIX, "prefix": True}]
    world = world_for(plan, task)
    lines = [INTRO, "",
             "| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |",
             "|---|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        fields.append(world["record_labels"][task["value"]][i])
        lines.append("| " + " | ".join(fields) + " |")
    instruction = INSTRUCTIONS[task["arm"] if task["family"] == "base" else "visible"]
    lines += ["", describe(world["items"][world["target_index"]]), QUESTION, instruction]
    messages = [{"role": "user", "content": "\n".join(lines)}]
    if task["family"] == "intervention":
        messages.append({"role": "assistant", "content": prefix_for(plan, task), "prefix": True})
    return messages


def request_for(plan, task):
    config = plan["config"]
    ceiling = "intervention" if task["family"] == "intervention" else task["arm"]
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"], "top_p": config["top_p"],
            "max_tokens": config["max_tokens"][ceiling], "reasoning_effort": config["reasoning_effort"],
            "stream": False}


def score_response(task, response, meta):
    result = {"answer": None, "status": "invalid", "format_valid": False, "invalid_reason": None,
              "capability_exact": None, "pre_answer_text": None, "prefix_exact": None,
              "generated_suffix": None, "suffix_pre_answer_text": None}
    if response.get("complete") is not True:
        result["invalid_reason"] = response.get("provider_invalid_reason") or "provider_incomplete"
        return result
    text = response.get("text")
    if not isinstance(text, str):
        result["invalid_reason"] = "content_not_string"
        return result
    if task["family"] == "capability":
        exact = text == CAPABILITY_EXPECTED_FULL
        result.update(capability_exact=exact, prefix_exact=text.startswith(CAPABILITY_PREFIX),
                      generated_suffix=text[len(CAPABILITY_PREFIX):] if text.startswith(CAPABILITY_PREFIX) else None,
                      status="complete" if exact else "invalid", format_valid=exact,
                      invalid_reason=None if exact else "capability_full_completion_mismatch")
        return result
    if task["family"] == "intervention":
        prefix = meta.get("prefix_text")
        if not isinstance(prefix, str) or not prefix:
            result["invalid_reason"] = "prefix_unavailable"
            return result
        exact = text.startswith(prefix)
        result["prefix_exact"] = exact
        if not exact:
            result["invalid_reason"] = "prefix_mismatch"
            return result
        result["generated_suffix"] = text[len(prefix):]
    label, start = answer_boundary(text)
    pretext = bool(text[:start].strip()) if label is not None else None
    reason = ("final_answer_unparseable" if label is None else
              "direct_not_answer_only" if task["arm"] == "direct" and pretext else
              "reasoning_text_missing" if task["arm"] == "visible" and not pretext else None)
    if task["family"] == "intervention" and label is not None:
        # The answer boundary is after the known prefix; an immediate terminal
        # answer is valid and is measured rather than retried or selected away.
        result["suffix_pre_answer_text"] = bool(text[len(meta["prefix_text"]):start].strip())
    result.update(answer=label if reason is None else None, pre_answer_text=pretext,
                  status="complete" if reason is None else "invalid", format_valid=reason is None,
                  invalid_reason=reason)
    return result


def capability_gate(plan, records):
    record = records.get("prefix-capability")
    returned = int(record is not None)
    valid = int(record is not None and record["status"] == "complete")
    passed = bool(valid and record.get("capability_exact") is True)
    return {"status": "pass" if passed else "fail" if returned else "incomplete",
            "n_planned": 1, "n_returned": returned, "n_valid": valid,
            "exact_full_completion_match": passed, "required_raw_completion": CAPABILITY_EXPECTED_FULL}
