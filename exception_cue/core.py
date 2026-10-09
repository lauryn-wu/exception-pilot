"""Frozen fresh worlds and prompts; no responses influence the design."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import check_plan, describe, digest, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
ARMS = ("direct", "cue", "visible")
LABELS = ("A", "B", "C")
INSTRUCTIONS = {
    "direct": "Output only ANSWER: followed by A, B, or C.",
    "cue": ("Think step by step before answering. "
            "Output only ANSWER: followed by A, B, or C."),
    "visible": ("Think step by step before answering. Write your reasoning, then put "
                "ANSWER: followed by A, B, or C alone on the final line."),
}
ANALYSIS_PLAN = {
    "co_primary": ["accuracy/direct_minus_cue", "accuracy/cue_minus_visible"],
    "secondary": ["accuracy/direct_minus_visible", "record_sensitivity"],
    "unit": "independent world; both record variants and all three arms remain paired",
    "bootstrap": "10000 whole-world resamples; descriptive unadjusted 95% percentile intervals",
    "format": "score parseable final answers regardless of output-format compliance; no resampling",
    "invalid_answers": "retain; per-contrast complete-world estimates and full-plan bounds",
    "interpretation": ("Cue-only requests no visible reasoning; this does not establish that hidden "
                       "reasoning occurred. Pre-answer text presence does not establish reasoning "
                       "quality or faithfulness. The visible-output contrast also changes the "
                       "output requirement and cannot identify self-conditioning alone."),
    "decision": "no scientific pass gate; no outcome-dependent extension",
}


def validate_config(config):
    fields = {"protocol", "n_worlds", "seed", "model", "api_key_env", "temperature",
              "max_completion_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config fields must match configs/cue.json; never include credentials")
    if config["protocol"] != PROTOCOL_VERSION:
        raise ValueError("Wrong protocol; use a separate output directory for this diagnostic")
    if type(config["n_worlds"]) is not int or config["n_worlds"] != 24:
        raise ValueError("This diagnostic fixes 24 independent worlds and 144 planned calls")
    if type(config["seed"]) is not int or config["seed"] != 2026100892:
        raise ValueError("This diagnostic fixes seed 2026100892; do not select new worlds by outcome")
    if config["model"] != "gpt-4o-2024-08-06":
        raise ValueError("This diagnostic fixes gpt-4o-2024-08-06")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("This diagnostic fixes temperature at 0")
    limits = config["max_completion_tokens"]
    if (not isinstance(limits, dict)
            or limits != {arm: 1000 for arm in ARMS}
            or any(type(v) is not int for v in limits.values())):
        raise ValueError("All three arms must receive the same completion cap of 1000 tokens")
    if type(config["max_total_attempts"]) is not int or config["max_total_attempts"] != 160:
        raise ValueError("The cumulative cap is 160 attempts, allowing 16 retries while completing 144 tasks")
    if type(config["timeout_seconds"]) not in (int, float) or config["timeout_seconds"] != 120:
        raise ValueError("This diagnostic fixes timeout_seconds at 120")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_cue")
    return digest({str(p.relative_to(root)): p.read_text()
                   for package in packages for p in sorted((root / package).glob("*.py"))})


def make_plan(config):
    validate_config(config)
    # Each of the six semantic role permutations occurs twice per target climate.
    assignments = [(p, climate) for p in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", config["seed"]).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world(config, index, used)
        world["id"] = f"cue-list-{index:03d}"
        for item in world["items"]:
            item["id"] = "Q" + item["id"][1:]
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
            "config": config, "worlds": worlds, "tasks": tasks, "analysis_plan": ANALYSIS_PLAN}
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
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


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
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        fields.append(world["record_labels"][task["value"]][i])
        lines.append("| " + " | ".join(fields) + " |")
    lines += ["", describe(world["items"][world["target_index"]]), QUESTION, INSTRUCTIONS[task["arm"]]]
    return [{"role": "user", "content": "\n".join(lines)}]


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"][task["arm"]],
            "n": 1, "store": False}


def score_response(task, response):
    """Score a strict final line independently of observable output formatting.

    Pre-answer text means only nonempty text before a parseable final line. It is
    not an annotation of reasoning, correctness, or faithfulness. For unparseable
    answers it is unknown (None), since no valid final-answer boundary was found.
    """
    text = response["text"].strip() if response["complete"] else ""
    lines = text.splitlines()
    final = re.fullmatch(r"ANSWER: ([ABC])", lines[-1].strip()) if lines else None
    answer = final.group(1) if final else None
    answer_only = bool(answer is not None and re.fullmatch(r"ANSWER: ([ABC])", text))
    pre_answer_text = bool("\n".join(lines[:-1]).strip()) if answer is not None else None
    contract = (pre_answer_text if task["arm"] == "visible" else answer_only)
    return {"answer": answer, "status": "complete" if answer is not None else "invalid",
            "answer_only": answer_only, "pre_answer_text": pre_answer_text,
            "output_contract_met": bool(answer is not None and contract)}
