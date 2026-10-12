"""Frozen source worlds, one row relocation, and correctness-blind scoring."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest, rng_for
from exception_query_form import core as query_form
from exception_mistral_prefix_v2.core import ENDPOINT

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

POSITIONS = (1, 5, 10)
VALUES = ("record_1", "record_2")
ARMS = ("direct", "visible")
SEED = 2026101201
SOURCE_PLAN_HASH = "110bbe5e3f1dd1cc1b5967c3c2cdd8e52a35c6f266fec6d2215107de019cd74a"
SOURCE_WORLDS_DIGEST = "3eeaf3a09137f7faa60539f3b34c78916ea5f1cf068f2562df94720c644c74a4"
ROOT = Path(__file__).resolve().parents[1]
WORLD_FILE = ROOT / "configs" / "row_position_worlds.json"

DECISION_RULE = {
    "purpose": "Fixed development-study spending rule, not a mechanism, significance or equivalence claim.",
    "meaningful_effect": 0.20,
    "minimum_complete_worlds_primary": 22,
    "minimum_output_adherence": 0.95,
    "collection": "All 288 planned responses must return before a scientific spending recommendation; no outcome-selected extension.",
    "confirmation": "Absolute first/last interaction at least 0.20, 95% interval excluding zero, and full-plan bounds beyond the same 0.20 threshold in that direction. A constant large effect can merit confirmation review, but its degenerate bootstrap interval cannot establish precision.",
    "deprioritize": "The interval and full-plan bounds both lie strictly inside (-0.20,0.20), with a nondegenerate bootstrap interval; not an equivalence test.",
    "otherwise": "Inconclusive, including degenerate small/null effects; no automatic follow-up calls.",
    "adherence": "Each position/arm: at least 95% of planned responses have answer-only output for direct, nonempty pre-answer text for visible. Cosmetic terminal formatting is reported separately.",
}
ANALYSIS_PLAN = {
    "primary": "accuracy/interaction",
    "interaction": "(direct - visible) at row 10 minus (direct - visible) at row 1",
    "secondary": "Row 5 harm minus average endpoint harm; each position's reasoning harm; direct and visible first/last shifts; pattern-label choices; and record sensitivity.",
    "unit": "One source world; average its two record-label variants, then pair positions and arms within that world.",
    "primary_complete_world": "All eight first/last responses valid; middle-row availability does not change the primary complete-world set.",
    "bootstrap_resamples": 10000,
    "bootstrap_seed": 981723,
    "intervals": "Descriptive, unadjusted 95% percentile intervals from whole-world resampling; degenerate intervals do not prove equivalence.",
    "sign_test": "Exact two-sided sign test with ties reported; tests sign balance, not the mean interaction.",
    "bounds": "All 24 planned worlds; every missing/invalid accuracy ranges independently over 0..1, retaining each contrast coefficient's sign. Sensitivity ranges over -1..1.",
    "evidence": "Development follow-up on all 24 previously observed worlds, selected before this study without filtering their outcomes. No old model answers are imported.",
    "hypothesis": "Last-row placement increases direct-minus-visible accuracy harm. A substantial reverse interaction is reported and also eligible for confirmation review.",
    "decision_rule": DECISION_RULE,
}


def validate_config(config):
    fields = {"protocol", "provider", "model", "endpoint", "api_key_env", "seed", "n_worlds",
              "temperature", "reasoning_effort", "max_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config must exactly match the supplied row-position fields; never include credentials")
    fixed = {"protocol": PROTOCOL_VERSION, "provider": "mistral", "model": "mistral-small-2603",
             "endpoint": ENDPOINT, "seed": SEED, "n_worlds": 24, "temperature": 0,
             "reasoning_effort": "none", "max_total_attempts": 316, "timeout_seconds": 120}
    for key, value in fixed.items():
        if config[key] != value or isinstance(config[key], bool):
            raise ValueError(f"This study fixes {key}={value!r}")
    for key in ("seed", "n_worlds", "max_total_attempts", "timeout_seconds"):
        if type(config[key]) is not int:
            raise ValueError(f"{key} must be an integer")
    if (not isinstance(config["api_key_env"], str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"])):
        raise ValueError("api_key_env must name an environment variable")
    caps = config["max_tokens"]
    if not isinstance(caps, dict) or caps != {arm: 1600 for arm in ARMS} or any(type(v) is not int for v in caps.values()):
        raise ValueError("Both arms require the fixed equal 1600-token completion cap")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_worlds():
    fixture = json.loads(WORLD_FILE.read_text())
    if (set(fixture) != {"source_protocol", "source_plan_hash", "worlds_digest", "worlds"}
            or fixture["source_protocol"] != query_form.PROTOCOL_VERSION
            or fixture["source_plan_hash"] != SOURCE_PLAN_HASH
            or fixture["worlds_digest"] != SOURCE_WORLDS_DIGEST
            or digest(fixture["worlds"]) != SOURCE_WORLDS_DIGEST
            or len(fixture["worlds"]) != 24):
        raise ValueError("Bundled source worlds differ from the audited query-form plan")
    return fixture["worlds"]


def source_digest():
    # Bind the audited query-form scoring, prompt and transport dependency chain
    # as well as this study. No existing source module is modified.
    paths = sorted((ROOT / "exception_row_position").glob("*.py"))
    paths += [ROOT / "ROW_POSITION_PROTOCOL.md", WORLD_FILE]
    return digest({"query_form_dependencies": query_form.source_digest(),
                   "row_position_sources": {str(p.relative_to(ROOT)): p.read_text() for p in paths}})


def make_plan(config):
    validate_config(config)
    worlds = source_worlds()
    tasks = []
    for world in worlds:
        cells = [{"id": f"{world['id']}/{value}/row-{position:02d}/{arm}",
                  "world_id": world["id"], "family": "diagnostic", "value": value,
                  "query": "key", "position": position, "arm": arm}
                 for value in VALUES for position in POSITIONS for arm in ARMS]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", SEED, world["id"]).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "design": {"seed": SEED, "n_worlds": 24, "positions": list(POSITIONS),
                       "query": "key", "source_plan_hash": SOURCE_PLAN_HASH,
                       "source_worlds_digest": SOURCE_WORLDS_DIGEST,
                       "cohort": "existing_query_form_worlds_development"},
            "worlds": worlds, "tasks": tasks, "analysis_plan": copy.deepcopy(ANALYSIS_PLAN)}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    output = Path(output)
    plan = json.loads((output / "plan.json").read_text())
    check_plan(plan)
    frozen = json.loads((output / "run_config.json").read_text())
    config = validate_config(frozen["config"])
    if frozen != {"config": config, "config_hash": digest(config), "plan_hash": plan["plan_hash"]}:
        raise ValueError("Frozen run-config identity differs")
    if plan != make_plan(config):
        raise ValueError("Code or saved plan differs; preserve this run and use a new output directory")
    return plan, config


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def order_for(world, position):
    if type(position) is not int or position not in POSITIONS:
        raise ValueError("Target position must be 1, 5 or 10")
    order = [i for i in world["order"] if i != world["target_index"]]
    order.insert(position - 1, world["target_index"])
    return order


def task_meta(plan, task):
    world = world_for(plan, task)
    target = world["target_index"]
    return {k: task[k] for k in ("world_id", "family", "value", "query", "position", "arm")} | {
        "item_id": world["items"][target]["id"], "expected": world["roles"][task["value"]],
        "pattern_label": world["roles"]["pattern"], "target_position": task["position"],
        "original_target_position": world["order"].index(target) + 1}


def prompt_parts(plan, task):
    if task["query"] != "key" or task["arm"] not in ARMS or task["value"] not in VALUES:
        raise ValueError("Only the frozen key-query direct/visible conditions are permitted")
    world = world_for(plan, task)
    relocated = dict(world, order=order_for(world, task["position"]))
    return query_form.prompt_parts({"worlds": [relocated]}, task)


def messages_for(plan, task):
    return [{"role": "user", "content": "".join(prompt_parts(plan, task))}]


def request_for(plan, task, config):
    return {"model": config["model"], "messages": messages_for(plan, task),
            "temperature": config["temperature"], "max_tokens": config["max_tokens"][task["arm"]],
            "reasoning_effort": config["reasoning_effort"], "stream": False}


def score_response(task, response):
    # Parsing depends on output and instruction, never on the expected answer.
    return query_form.score_response(task, response)
