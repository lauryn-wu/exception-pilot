"""Fresh confirmation worlds, all target rows, and correctness-blind scoring."""

from __future__ import annotations

import copy
import json
import itertools
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest, rng_for
from exception_counterfactual.core import make_world
from exception_query_form import core as query_form
from exception_mistral_prefix_v2.core import ENDPOINT

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

POSITIONS = tuple(range(1, 11))
VALUES = ("record_1", "record_2")
ARMS = ("direct", "visible")
SEED = 2026101202
DEVELOPMENT_PLAN_HASH = "110bbe5e3f1dd1cc1b5967c3c2cdd8e52a35c6f266fec6d2215107de019cd74a"
DEVELOPMENT_WORLDS_DIGEST = "3eeaf3a09137f7faa60539f3b34c78916ea5f1cf068f2562df94720c644c74a4"
ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_WORLD_FILE = ROOT / "configs" / "row_position_worlds.json"

DECISION_RULE = {
    "purpose": "Fresh-world confirmation within the same generator family; not a mechanism or broad generality claim.",
    "meaningful_effect": 0.20,
    "minimum_complete_worlds_primary": 22,
    "minimum_output_adherence": 0.95,
    "collection": "All 960 planned responses must return; no outcome-selected extension or stopping.",
    "confirmation": "Positive first/last interaction >= 0.20, 95% interval lower endpoint > 0, and full-plan lower bound >= 0.20. Label confirm_positive_interaction.",
    "reverse": "Interaction <= -0.20, interval upper endpoint < 0, and full-plan upper bound <= -0.20. Label reverse_effect; this does not confirm the directional prediction.",
    "deprioritize": "Nondegenerate interval and full-plan bounds strictly inside (-0.20,0.20): smaller_than_target, not equivalence or proof of no position effect.",
    "otherwise": "Inconclusive; degenerate bootstrap intervals cannot calibrate precision, including when a large observed effect meets the directional rule.",
    "adherence": "Every position/arm: at least 95% of all 48 planned responses must have answer-only output for direct or pre-answer text for visible. Cosmetic terminal formatting is separate.",
}
ANALYSIS_PLAN = {
    "primary": "accuracy/interaction",
    "interaction": "(direct - visible) at row 10 minus (direct - visible) at row 1",
    "secondary": "All ten row accuracies and harms; H2-H1; H10-H9; (H5+H6)/2-(H1+H10)/2; direct/visible endpoint shifts; pattern choices and record sensitivity. Curve intervals are pointwise and unadjusted, not a search for the best contrast.",
    "unit": "One fresh world, averaging both recorded-label variants before pairing positions and arms.",
    "primary_complete_world": "Only the eight endpoint responses must be valid; missing nonendpoint responses do not discard a primary world.",
    "bootstrap_resamples": 10000,
    "bootstrap_seed": 981723,
    "intervals": "95% percentile intervals from whole-world resampling. Pointwise secondary intervals are unadjusted. Degenerate intervals cannot establish precision.",
    "sign_test": "Exact two-sided sign balance test on nonzero world contrasts, with ties reported; not a test of the mean magnitude or a decision gate.",
    "bounds": "All 24 planned worlds; missing/invalid accuracy ranges 0..1 and sensitivity -1..1, retaining all coefficient signs. Bounds are not confidence intervals.",
    "evidence": "24 fresh deterministic draws from the same generator family. No previous responses or outcome selection; original development worlds are excluded. This tests new-world generalization, not new task families or models.",
    "hypothesis": "Moving the target from row 1 to row 10 increases direct-minus-visible accuracy harm by at least 0.20.",
    "trace_review": "Offline manual review of every returned visible response, including invalid responses, with exact quoted evidence. False missingness, within-trace contradictions, and gold-then-override are separate nullable codes; never decision gates.",
    "decision_rule": DECISION_RULE,
}

def validate_config(config):
    fields = {"protocol", "provider", "model", "endpoint", "api_key_env", "seed", "n_worlds",
              "temperature", "reasoning_effort", "max_tokens", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Config must exactly match the supplied row-position fields; never include credentials")
    fixed = {"protocol": PROTOCOL_VERSION, "provider": "mistral", "model": "mistral-small-2603",
             "endpoint": ENDPOINT, "seed": SEED, "n_worlds": 24, "temperature": 0,
             "reasoning_effort": "none", "max_total_attempts": 1056, "timeout_seconds": 120}
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


def development_worlds():
    fixture = json.loads(DEVELOPMENT_WORLD_FILE.read_text())
    if (fixture.get("source_plan_hash") != DEVELOPMENT_PLAN_HASH
            or fixture.get("worlds_digest") != DEVELOPMENT_WORLDS_DIGEST
            or digest(fixture.get("worlds")) != DEVELOPMENT_WORLDS_DIGEST
            or len(fixture["worlds"]) != 24):
        raise ValueError("Development exclusion fixture differs from the frozen query-form worlds")
    return fixture["worlds"]


def source_worlds():
    """Fresh seeded draws using the original generator family, never responses."""
    old_worlds = development_worlds()
    old_plates = {item["id"] for world in old_worlds for item in world["items"]}
    # make_world generates V-prefixed IDs; preserve the prior U-format while
    # excluding suffix collisions with the development cohort before sampling.
    used = {"V" + plate[1:] for plate in old_plates}
    assignments = [(roles, climate) for roles in itertools.permutations(("A", "B", "C"))
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", SEED).shuffle(assignments)
    worlds = []
    for index, (roles, climate) in enumerate(assignments):
        world = make_world({"seed": SEED}, index, used)
        world["id"] = f"rpc-list-{index:03d}"
        for item in world["items"]:
            item["id"] = query_form.PLATE_PREFIX + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip((*VALUES, "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", SEED, index)
        other_labels = ([roles[0]] * 2 + [roles[1]] * 3 if index % 2
                        else [roles[0]] * 3 + [roles[1]] * 2)
        rng.shuffle(other_labels)
        markers = ["X", "Y", "Z"] * 3 + [rng.choice(["X", "Y", "Z"])]
        rng.shuffle(markers)
        labels = []
        for i, item in enumerate(world["items"]):
            item["audit_marker"] = markers[i]
            labels.append(roles[2] if item["climate"] == climate else other_labels.pop())
        world["record_labels"] = {}
        for value in VALUES:
            variant = labels.copy()
            variant[target] = world["roles"][value]
            world["record_labels"][value] = variant
        worlds.append(world)
    new_plates = [item["id"] for world in worlds for item in world["items"]]
    if len(set(new_plates)) != 240 or set(new_plates) & old_plates:
        raise ValueError("Fresh-world plate identities overlap or are duplicated")
    return worlds


def source_digest():
    paths = sorted((ROOT / "exception_row_position_confirm").glob("*.py"))
    paths += [ROOT / "ROW_POSITION_CONFIRM_PROTOCOL.md", DEVELOPMENT_WORLD_FILE]
    return digest({"query_form_dependencies": query_form.source_digest(),
                   "confirmation_sources": {str(p.relative_to(ROOT)): p.read_text() for p in paths}})


def make_plan(config):
    validate_config(config)
    worlds = source_worlds()
    schedule_worlds = worlds.copy()
    rng_for(PROTOCOL_VERSION, "world_schedule", SEED).shuffle(schedule_worlds)
    tasks = []
    for world in schedule_worlds:
        cells = [{"id": f"{world['id']}/{value}/row-{position:02d}/{arm}",
                  "world_id": world["id"], "family": "diagnostic", "value": value,
                  "query": "key", "position": position, "arm": arm}
                 for value in VALUES for position in POSITIONS for arm in ARMS]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", SEED, world["id"]).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "design": {"seed": SEED, "n_worlds": 24, "positions": list(POSITIONS),
                       "query": "key", "development_plan_hash": DEVELOPMENT_PLAN_HASH,
                       "excluded_worlds_digest": DEVELOPMENT_WORLDS_DIGEST,
                       "fresh_worlds_digest": digest(worlds),
                       "world_schedule": [w["id"] for w in schedule_worlds],
                       "cohort": "fresh_world_confirmation_same_generator"},
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
        raise ValueError("Target position must be an integer from 1 through 10")
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
