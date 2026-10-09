"""Frozen capability, fresh baseline worlds, and deterministic unedited prefixes."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_cue.core import INSTRUCTIONS as CUE_INSTRUCTIONS
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import check_plan, describe, digest, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
ARMS = BASE_ARMS = ("direct", "visible")
LABELS = ("A", "B", "C")
INSTRUCTIONS = {arm: CUE_INSTRUCTIONS[arm] for arm in BASE_ARMS}
ENDPOINT = "https://api.deepseek.com/beta/chat/completions"
CAPABILITY_USER = "Output exactly this text, without quotation marks or commentary:\nCobalt Maple Lantern"
CAPABILITY_PREFIX = "Cobalt Ma"
CAPABILITY_EXPECTED_SUFFIX = "ple Lantern"
MODEL_DOCUMENTATION = {"requested_alias": "deepseek-flash", "documented_family": "DeepSeek V4.1 Flash",
                       "documentation_as_of": "2026-10-09", "is_pinned_snapshot": False}
ANALYSIS_PLAN = {
    "scope": "Capability and unedited replay feasibility only; no edited-prefix arms or stage two.",
    "unit": "fresh world; record variants and arms remain paired",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "capability": "Raw suffix must equal 'ple Lantern' exactly, including whitespace.",
    "phenomenon_gate": {"minimum_direct_correct": 20, "minimum_direct_minus_visible_count": 4,
                        "minimum_visible_pattern_errors": 4, "minimum_pattern_error_worlds": 3},
    "replay_gate": {"required_valid": 24, "minimum_answer_matches": 22,
                    "minimum_pattern_error_match_fraction": 0.8},
    "cuts": "Nearest eligible whitespace boundary at or before midpoint; otherwise first eligible boundary after it.",
    "invalid_answers": "Retain and stop on every returned invalid response; never resample or continue past it.",
    "interpretation": ("Fixed practical investment gates are not significance tests or evidence of a mechanism. "
                       "Provider continuation is not a saved internal state. Prefixes may contain an early "
                       "answer cue; no edited-prefix causal experiment is run in this screen."),
}


class PrefixUnavailable(ValueError):
    """The prespecified parent prefix cannot be constructed; never choose another cut."""


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "endpoint", "api_key_env", "temperature",
              "thinking", "max_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/prefix.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate prefix-feasibility output directory")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 12:
        raise ValueError("This screen fixes 12 fresh worlds, 48 base requests and up to 24 replays")
    if type(config["seed"]) is not int or config["seed"] != 2026100941:
        raise ValueError("This screen fixes seed 2026100941; do not select worlds by outcome")
    if config["model"] != "deepseek-flash" or config["endpoint"] != ENDPOINT:
        raise ValueError("This screen fixes the deepseek-flash alias and DeepSeek beta endpoint")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This screen fixes temperature at zero")
    if config["thinking"] != {"type": "disabled"}:
        raise ValueError("This screen requires thinking disabled")
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
                "exception_factorial", "exception_explanation", "exception_cue", "exception_prefix")
    return digest({str(path.relative_to(root)): path.read_text()
                   for package in packages for path in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    assignments = [(roles, climate) for roles in itertools.permutations(LABELS)
                   for climate in ("cold", "warm")]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, base, replay, used = [], [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        world["id"] = f"prefix-list-{index:03d}"
        for item in world["items"]:
            item["id"] = "N" + item["id"][1:]
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
                  "family": "base", "value": value, "arm": arm}
                 for value in VALUES for arm in BASE_ARMS]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", config["seed"], index).shuffle(cells)
        base.extend(cells)
        replay.extend({"id": f"{world['id']}/{value}/replay", "world_id": world["id"],
                       "family": "replay", "value": value, "arm": "replay",
                       "parent_task_id": f"{world['id']}/{value}/visible"} for value in VALUES)
    tasks = [{"id": "prefix-capability", "family": "capability", "arm": "capability"}] + base + replay
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "model_documentation": copy.deepcopy(MODEL_DOCUMENTATION),
            "worlds": worlds, "tasks": tasks, "analysis_plan": copy.deepcopy(ANALYSIS_PLAN)}
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


def _answer_boundary(text):
    lines = text.splitlines(keepends=True)
    last = next((index for index in range(len(lines) - 1, -1, -1) if lines[index].strip()), None)
    if last is None:
        return None, None
    match = re.fullmatch(r"ANSWER: ([ABC])", lines[last].strip())
    return (match.group(1), sum(map(len, lines[:last]))) if match else (None, None)


def cut_parent_prefix(text):
    """Cut original bytes-as-text at a deterministic whitespace boundary before the final answer."""
    if not isinstance(text, str):
        raise PrefixUnavailable("parent_text_not_string")
    answer, final_start = _answer_boundary(text)
    if answer is None:
        raise PrefixUnavailable("parent_final_answer_unparseable")
    pre_answer = text[:final_start]
    # A boundary follows an entire whitespace run. Both remaining pieces must
    # contain non-whitespace reasoning text; never cut within a word or answer line.
    candidates = [match.end() for match in re.finditer(r"\s+", pre_answer)
                  if pre_answer[:match.end()].strip() and pre_answer[match.end():].strip()]
    if not candidates:
        raise PrefixUnavailable("no_eligible_whitespace_boundary")
    midpoint = len(pre_answer) / 2
    before = [position for position in candidates if position <= midpoint]
    cut = max(before) if before else min(candidates)
    remaining = pre_answer[cut:]
    return {"prefix_text": text[:cut], "parent_suffix": text[cut:],
            "prefix_cut_chars": cut, "prefix_cut_fraction": cut / len(pre_answer),
            "prefix_chars": len(text[:cut]), "remaining_reasoning_chars": len(remaining),
            "remaining_reasoning_words": len(remaining.split()), "pre_answer_chars": len(pre_answer)}


def task_meta(plan, task, records=None):
    if task["family"] == "capability":
        return {"family": "capability", "arm": "capability", "world_id": None, "value": None,
                "item_id": None, "expected": None, "pattern_label": None, "target_position": None}
    world = world_for(plan, task)
    i = world["target_index"]
    item = world["items"][i]
    meta = {"world_id": world["id"], "family": task["family"], "value": task["value"],
            "arm": task["arm"], "item_id": item["id"], "expected": world["roles"][task["value"]],
            "pattern_label": world["roles"]["pattern"], "target_position": world["order"].index(i) + 1}
    if task["family"] != "replay":
        return meta
    meta.update({"parent_task_id": task["parent_task_id"], "prefix_available": None,
                 "prefix_unavailable_reason": "parent_pending"})
    parent = (records or {}).get(task["parent_task_id"])
    if parent is None:
        return meta
    if parent["status"] != "complete":
        meta.update(prefix_available=False, prefix_unavailable_reason="parent_invalid")
        return meta
    response = parent["response"]
    meta.update({"parent_answer": parent["answer"], "parent_correct": parent["answer"] == meta["expected"],
                 "parent_pattern_error": parent["answer"] == meta["pattern_label"],
                 "parent_response_id": response.get("response_id"),
                 "parent_response_sha256": hashlib.sha256(response["text"].encode("utf-8")).hexdigest(),
                 "parent_raw_sha256": digest(response["raw_response"])})
    try:
        meta.update(cut_parent_prefix(response["text"]))
    except PrefixUnavailable as exc:
        meta.update(prefix_available=False, prefix_unavailable_reason=str(exc))
    else:
        meta.update(prefix_available=True, prefix_unavailable_reason=None)
    return meta


def messages_for(plan, task, records=None):
    if task["family"] == "capability":
        return [{"role": "user", "content": CAPABILITY_USER},
                {"role": "assistant", "content": CAPABILITY_PREFIX, "prefix": True}]
    if task["family"] == "replay":
        meta = task_meta(plan, task, records)
        if meta["prefix_available"] is not True:
            raise PrefixUnavailable(meta["prefix_unavailable_reason"])
        parent_task = next(value for value in plan["tasks"] if value["id"] == task["parent_task_id"])
        return messages_for(plan, parent_task) + [{"role": "assistant", "content": meta["prefix_text"], "prefix": True}]
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


def request_for(plan, task, records=None):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task, records),
            "temperature": config["temperature"], "max_tokens": config["max_tokens"][task["arm"]],
            "thinking": copy.deepcopy(config["thinking"]), "stream": False}


def score_response(task, response, meta=None):
    answer, reason, capability, pretext = None, None, None, None
    replay_match, exact_suffix, pattern_match = None, None, None
    if response.get("complete") is not True:
        reason = response.get("provider_invalid_reason") or "provider_incomplete"
    elif not isinstance(response.get("text"), str):
        reason = "content_not_string"
    elif task["family"] == "capability":
        capability = response["text"] == CAPABILITY_EXPECTED_SUFFIX
        if not capability:
            reason = "capability_suffix_mismatch"
    else:
        text = response["text"]
        if task["family"] == "replay":
            if not meta or meta.get("prefix_available") is not True:
                reason = "prefix_unavailable"
            else:
                # Raw response content is a suffix. Never strip a repeated prefix heuristically.
                text = meta["prefix_text"] + text
        if reason is None:
            parsed, boundary = _answer_boundary(text)
            pretext = bool(text[:boundary].strip()) if parsed is not None else None
            if parsed is None:
                reason = "final_answer_unparseable"
            elif task["arm"] == "direct" and text.strip() != f"ANSWER: {parsed}":
                reason = "direct_not_answer_only"
            elif task["arm"] in ("visible", "replay") and pretext is not True:
                reason = "reasoning_text_missing"
            else:
                answer = parsed
                if task["family"] == "replay":
                    replay_match = answer == meta["parent_answer"]
                    exact_suffix = response["text"] == meta["parent_suffix"]
                    pattern_match = answer == meta["parent_answer"] if meta["parent_pattern_error"] else None
    valid = reason is None
    return {"answer": answer, "status": "complete" if valid else "invalid", "format_valid": valid,
            "invalid_reason": reason, "capability_exact": capability, "pre_answer_text": pretext,
            "replay_answer_match": replay_match, "replay_exact_suffix_match": exact_suffix,
            "replay_pattern_error_match": pattern_match}


def capability_gate(plan, records):
    record = records.get("prefix-capability")
    returned = int(record is not None)
    valid = int(record is not None and record["status"] == "complete")
    passed = bool(valid and record.get("capability_exact") is True)
    return {"status": "pass" if passed else "fail" if returned else "incomplete",
            "n_planned": 1, "n_returned": returned, "n_valid": valid, "exact_suffix_match": passed,
            "required_raw_suffix": CAPABILITY_EXPECTED_SUFFIX}


def phenomenon_gate(plan, records):
    tasks = [task for task in plan["tasks"] if task["family"] == "base"]
    present = [records[task["id"]] for task in tasks if task["id"] in records]
    valid = [record for record in present if record["status"] == "complete"]
    direct = sum(record["answer"] == record["meta"]["expected"] for record in valid if record["meta"]["arm"] == "direct")
    visible = sum(record["answer"] == record["meta"]["expected"] for record in valid if record["meta"]["arm"] == "visible")
    errors = [record for record in valid if record["meta"]["arm"] == "visible"
              and record["answer"] == record["meta"]["pattern_label"]]
    worlds = len({record["meta"]["world_id"] for record in errors})
    thresholds = ANALYSIS_PLAN["phenomenon_gate"]
    passed = (len(valid) == len(tasks) and direct >= 20 and direct - visible >= 4
              and len(errors) >= 4 and worlds >= 3)
    status = "pass" if passed else "fail" if len(present) != len(valid) or len(present) == len(tasks) else "incomplete"
    return {"status": status, "n_planned": len(tasks), "n_returned": len(present), "n_valid": len(valid),
            "direct_correct": direct, "visible_correct": visible, "gap": direct - visible,
            "visible_pattern_errors": len(errors), "visible_pattern_error_worlds": worlds,
            "thresholds": copy.deepcopy(thresholds)}


def replay_gate(plan, records):
    tasks = [task for task in plan["tasks"] if task["family"] == "replay"]
    present = [records[task["id"]] for task in tasks if task["id"] in records]
    valid = [record for record in present if record["status"] == "complete"]
    parent_errors = [records[task["parent_task_id"]] for task in tasks if task["parent_task_id"] in records
                     and records[task["parent_task_id"]]["status"] == "complete"
                     and records[task["parent_task_id"]]["answer"] == records[task["parent_task_id"]]["meta"]["pattern_label"]]
    original_errors = len(parent_errors)
    answer_matches = sum(record.get("replay_answer_match") is True for record in valid)
    pattern_matches = sum(record.get("replay_pattern_error_match") is True for record in valid)
    required_pattern = (4 * original_errors + 4) // 5
    passed = len(valid) == len(tasks) and answer_matches >= 22 and pattern_matches >= required_pattern
    status = "pass" if passed else "fail" if len(present) != len(valid) or len(present) == len(tasks) else "incomplete"
    return {"status": status, "n_planned": len(tasks), "n_returned": len(present), "n_valid": len(valid),
            "answer_matches": answer_matches, "required_answer_matches": 22,
            "original_pattern_errors": original_errors, "pattern_error_matches": pattern_matches,
            "required_pattern_error_matches": required_pattern,
            "exact_suffix_matches": sum(record.get("replay_exact_suffix_match") is True for record in valid)}
