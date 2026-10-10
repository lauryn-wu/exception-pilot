"""Frozen paired source records, semantic query roles, and terminal-answer scoring.

All calls are fresh conversations. Encoded and downstream queries use the exact
same bijection, while literal queries are a descriptive reference condition.
Nothing in generation or scheduling depends on model responses.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re

from . import PROTOCOL_VERSION

ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
FAMILIES = ("vehicle", "configuration")
VALUES = ("a", "b")
QUERIES = ("literal", "encoded", "downstream")
ARMS = ("direct", "visible")
CODES = ("K", "Z", "R")
SOURCE_VALUES = {"vehicle": ("A", "B", "C"),
                 "configuration": ("Quiet", "Balanced", "Fast")}
INSTRUCTIONS = {
    "direct": "Give only your final answer in this format:\nFINAL: <answer>",
    "visible": ("Explain your answer step by step, then give your final answer "
                "in this format:\nFINAL: <answer>"),
}
DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION,
    "n_worlds": 12,
    "worlds_per_family": 6,
    "seed": 2026101001,
    "model": "mistral-small-2603",
    "endpoint": ENDPOINT,
    "api_key_env": "MISTRAL_API_KEY",
    "temperature": 0.6,
    "top_p": 0.95,
    "reasoning_effort": "none",
    "max_tokens": 1600,
    "max_total_attempts": 153,
    "max_extra_attempts": 9,
    "max_retries_per_task": 2,
    "timeout_seconds": 120,
    "min_request_interval_seconds": 10,
    "bootstrap_samples": 10000,
    "bootstrap_seed": 2026101002,
}
ANALYSIS_PLAN = {
    "primary": "(downstream - encoded) responsiveness in visible minus direct",
    "responsiveness": "S = (score_b - score_a) / 2; decoded a=-1, b=+1, third=0",
    "unit": "independent world; retain the two source records and all query/response arms together",
    "families": "Report each family separately; the pooled descriptive estimate weights each of the 12 worlds equally.",
    "literal": "Descriptive reference only; it is not a substitute primary contrast.",
    "missingness": "Retain every returned invalid response; report complete-world estimates and full-plan point-estimate bounds, never treat an invalid answer as the third category.",
    "collection": "Fixed 144 requests; no answer-dependent selection, resampling, extension, or accuracy gate.",
    "interpretation": "Semantic subject of the question, not literal answer versus intermediate status: both encoded and downstream questions require the source property as an intermediate. A contrast identifies query-conditioned functional use, not an internal exclusion mechanism.",
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _rng(config, *parts):
    return random.Random(int(_digest((PROTOCOL_VERSION, config["seed"], parts)), 16))


def validate_config(config):
    """Freeze scientific settings; operational overrides create a different plan."""
    if not isinstance(config, dict) or set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Config fields must exactly match configs/query_role.json; never include credentials")
    variable = {"api_key_env", "timeout_seconds", "min_request_interval_seconds"}
    for key, expected in DEFAULT_CONFIG.items():
        if key not in variable and (type(config[key]) is not type(expected) or config[key] != expected):
            raise ValueError(f"{key} is fixed by this protocol; use configs/query_role.json")
    key_name = config["api_key_env"]
    if not isinstance(key_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key_name):
        raise ValueError("api_key_env must name an environment variable, never contain a key")
    for key in ("timeout_seconds", "min_request_interval_seconds"):
        value = config[key]
        if (type(value) not in (int, float) or not math.isfinite(value)
                or value < 0 or (key == "timeout_seconds" and value == 0)):
            raise ValueError(f"{key} must be finite and {'positive' if key == 'timeout_seconds' else 'nonnegative'}")
    return copy.deepcopy(config)


def load_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def source_digest():
    """Freeze this package and the local packages supporting reused transport/storage."""
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_query_role", "exception_pilot", "exception_mistral_prefix_v2",
                "exception_mistral_prefix", "exception_prefix", "exception_cue",
                "exception_counterfactual", "exception_explanation", "exception_factorial",
                "exception_wording")
    paths = [p for package in packages for p in sorted((root / package).glob("*.py"))]
    return _digest({str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in sorted(paths)})


def _identities(config, family, index, count):
    rng = _rng(config, family, index, "identities")
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    prefix = "QV" if family == "vehicle" else "QD"
    identities = []
    while len(identities) < count:
        candidate = prefix + str(index) + "".join(rng.choices(alphabet, k=5))
        if candidate not in identities:
            identities.append(candidate)
    rng.shuffle(identities)
    return identities


def _mapping_lines(world):
    family = world["family"]
    headers = ({"source": "Class", "encoded": "Class in coded notation", "downstream": "Dispatch gate"}
               if family == "vehicle" else
               {"source": "Mode", "encoded": "Mode in coded notation", "downstream": "Control signal"})
    columns = ["source"] + world["mapping_column_order"]
    lines = [" | ".join(headers[column] for column in columns)]
    for source in world["mapping_row_order"]:
        cells = {"source": source, "encoded": world["code_map"][source],
                 "downstream": world["code_map"][source]}
        lines.append(" | ".join(cells[column] for column in columns))
    return lines


def _vehicle_context(world, value):
    lines = ["Each vehicle has a fixed class: A, B, or C.",
             "The vehicle records below are accurate.", "", "Vehicle | Region | Class"]
    for row in world["records"]:
        source = world["roles"][value] if row["id"] == world["target_id"] else row["source"]
        lines.append(f"{row['id']} | {row['region']} | {source}")
    lines += ["", "Classes can also be written using the following coded notation.",
              "A vehicle's dispatch gate is determined by its class.", ""]
    return "\n".join(lines + _mapping_lines(world))


def _configuration_context(world, value):
    lines = ["A device-specific setting determines the active mode when present.",
             "Otherwise the site default applies, if one exists.", "", "Site | Default mode"]
    lines += [f"{row['site']} | {row['source']}" for row in world["defaults"]]
    lines += ["", "Device | Site"]
    lines += [f"{row['id']} | {row['site']}" for row in world["devices"]]
    lines += ["", "Device-specific settings:"]
    for row in world["overrides"]:
        source = world["roles"][value] if row["id"] == world["target_id"] else row["source"]
        lines.append(f"{row['id']}: {source}")
    lines += ["", "Modes can also be written using the following coded notation.",
              "A device's control signal is determined by its active mode.", ""]
    return "\n".join(lines + _mapping_lines(world))


def _question(world, query):
    target = world["target_id"]
    if world["family"] == "vehicle":
        opening = f"Which class does vehicle {target} belong to?"
        if query == "literal":
            return opening + "\nUse A, B, or C for your final answer."
        if query == "encoded":
            return opening + "\nUse the class's coded notation for your final answer: K, Z, or R."
        return f"Which dispatch gate is vehicle {target} assigned to?\nUse K, Z, or R for your final answer."
    opening = f"What is device {target}'s active mode?"
    if query == "literal":
        return opening + "\nUse Quiet, Balanced, or Fast for your final answer."
    if query == "encoded":
        return opening + "\nUse the mode's coded notation for your final answer: K, Z, or R."
    return f"Which control signal does device {target} use?\nUse K, Z, or R for your final answer."


def _world(config, family, index, roles, code_values):
    sources = SOURCE_VALUES[family]
    world = {"id": f"query-role-{family}-{index:03d}", "family": family,
             "roles": dict(zip(("a", "b", "pattern"), roles)),
             "source_a": roles[0], "source_b": roles[1], "pattern_source": roles[2],
             "code_map": dict(zip(sources, code_values)),
             "mapping_column_order": ["encoded", "downstream"],
             "mapping_row_order": list(sources)}
    _rng(config, family, index, "mapping-columns").shuffle(world["mapping_column_order"])
    _rng(config, family, index, "mapping-rows").shuffle(world["mapping_row_order"])
    if family == "vehicle":
        identities = _identities(config, family, index, 19)
        world["target_id"] = identities.pop()
        regions = ["Warm", "Cold", "Mild"]
        _rng(config, family, index, "regions").shuffle(regions)
        region_labels = dict(zip(regions, sources))
        target_region = next(region for region, source in region_labels.items() if source == roles[2])
        world["target_region"] = target_region
        world["region_labels"] = region_labels
        records = [{"id": identities.pop(), "region": region, "source": source}
                   for region, source in region_labels.items() for _ in range(6)]
        records.append({"id": world["target_id"], "region": target_region, "source": None})
        _rng(config, family, index, "record-order").shuffle(records)
        world["records"] = records
        world["target_position"] = next(i + 1 for i, row in enumerate(records) if row["id"] == world["target_id"])
        world["contexts"] = {value: _vehicle_context(world, value) for value in VALUES}
    else:
        identities = _identities(config, family, index, 3)
        sites = ["North", "East", "South"]
        _rng(config, family, index, "sites").shuffle(sites)
        defaults = [{"site": site, "source": source} for site, source in zip(sites, sources)]
        target_site = next(row["site"] for row in defaults if row["source"] == roles[2])
        devices = [{"id": identities.pop(), "site": row["site"]} for row in defaults]
        world["target_id"] = next(row["id"] for row in devices if row["site"] == target_site)
        world["target_site"] = target_site
        other_sources = list(sources)
        _rng(config, family, index, "other-overrides").shuffle(other_sources)
        overrides = [{"id": row["id"], "source": None if row["id"] == world["target_id"] else other_sources.pop()}
                     for row in devices]
        _rng(config, family, index, "defaults-order").shuffle(defaults)
        _rng(config, family, index, "device-order").shuffle(devices)
        _rng(config, family, index, "override-order").shuffle(overrides)
        world.update(defaults=defaults, devices=devices, overrides=overrides)
        world["target_position"] = next(i + 1 for i, row in enumerate(overrides) if row["id"] == world["target_id"])
        world["contexts"] = {value: _configuration_context(world, value) for value in VALUES}
    return world


def _worlds(config):
    worlds = []
    for family in FAMILIES:
        sources = SOURCE_VALUES[family]
        roles = list(itertools.permutations(sources))
        _rng(config, family, "value-assignments").shuffle(roles)
        # Uniform seeded selection among all eligible assignments of the six
        # distinct bijections to the six source-role permutations. In addition
        # to every source category occupying each role twice, every OUTPUT code
        # occupies each role twice. This is precollection counterbalancing, not
        # outcome-dependent rejection sampling or a change to the query arms.
        source_indices = {source: index for index, source in enumerate(sources)}
        eligible = [assignment for assignment in itertools.permutations(tuple(itertools.permutations(CODES)))
                    if all(sum(mapping[source_indices[role[position]]] == code
                               for role, mapping in zip(roles, assignment)) == 2
                           for position in range(3) for code in CODES)]
        if len(eligible) != 18:
            raise ValueError("Unexpected number of balanced mapping assignments")
        mappings = _rng(config, family, "code-assignments").choice(eligible)
        worlds.extend(_world(config, family, index, assignment, mappings[index])
                      for index, assignment in enumerate(roles))
    return worlds


def make_plan(config):
    config = validate_config(config)
    worlds = _worlds(config)
    tasks = []
    for world in worlds:
        for value, query, arm in itertools.product(VALUES, QUERIES, ARMS):
            decode = ({source: source for source in SOURCE_VALUES[world["family"]]}
                      if query == "literal" else
                      {code: source for source, code in world["code_map"].items()})
            encode = {source: answer for answer, source in decode.items()}
            question = _question(world, query)
            tasks.append({
                "id": f"{world['id']}/{value}/{query}/{arm}",
                "world_id": world["id"], "family": world["family"],
                "value": value, "query": query, "arm": arm,
                "expected": encode[world["roles"][value]],
                "pattern_label": encode[world["roles"]["pattern"]],
                "decode_map": decode, "source_a": world["source_a"], "source_b": world["source_b"],
                "question": question,
                "prompt": world["contexts"][value] + "\n\n" + question + "\n\n" + INSTRUCTIONS[arm],
            })
    _rng(config, "request-schedule").shuffle(tasks)
    if len(worlds) != 12 or len(tasks) != 144 or len({task["id"] for task in tasks}) != 144:
        raise ValueError("This protocol requires exactly 12 worlds and 144 distinct requests")
    plan = {"protocol_version": PROTOCOL_VERSION, "config": config,
            "source_digest": source_digest(), "worlds": worlds, "tasks": tasks,
            "analysis_plan": copy.deepcopy(ANALYSIS_PLAN)}
    plan["plan_hash"] = _digest(plan)
    return plan


def check_plan(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("config"), dict):
        raise ValueError("Malformed query-role plan")
    if plan.get("plan_hash") != _digest({key: value for key, value in plan.items() if key != "plan_hash"}):
        raise ValueError("Plan integrity check failed; do not edit a run's plan.json")
    if plan != make_plan(plan["config"]):
        raise ValueError("Code, config, or frozen plan changed; preserve this run and use a new output directory")


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text(encoding="utf-8"))
    check_plan(plan)
    return plan


def world_for(plan, task):
    return next(world for world in plan["worlds"] if world["id"] == task["world_id"])


def request_for(plan, task):
    config = plan["config"]
    return {"model": config["model"], "messages": [{"role": "user", "content": task["prompt"]}],
            "temperature": config["temperature"], "top_p": config["top_p"],
            "max_tokens": config["max_tokens"], "reasoning_effort": config["reasoning_effort"],
            "stream": False}


def task_meta(plan, task):
    world = world_for(plan, task)
    fields = ("world_id", "family", "value", "query", "arm", "expected", "pattern_label",
              "decode_map", "source_a", "source_b")
    result = {key: copy.deepcopy(task[key]) for key in fields}
    result.update(item_id=world["target_id"], target_position=world["target_position"],
                  pattern_source=world["pattern_source"])
    return result


def score_response(task, response, meta):
    """Score only the final nonempty line; preceding text never supplies a label.

    Direct responses containing an explanation remain scorable. Their format
    instruction adherence is recorded separately, without answer-based retries.
    """
    result = {"status": "invalid", "format_valid": False, "answer": None,
              "correct": None, "pattern": None, "decoded_value": None, "score": None,
              "invalid_reason": None, "direct_instruction_adherent": None}
    if response.get("complete") is not True or response.get("provider_invalid_reason"):
        result["invalid_reason"] = response.get("provider_invalid_reason") or "provider_incomplete"
        return result
    if response.get("finish_reason") != "stop":
        result["invalid_reason"] = "incomplete_finish_reason"
        return result
    text = response.get("text")
    if not isinstance(text, str):
        result["invalid_reason"] = "content_not_string"
        return result
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    match = re.fullmatch(r"FINAL\s*:\s*(\S(?:.*\S)?)\s*", lines[-1], re.IGNORECASE) if lines else None
    normalized = {answer.casefold(): answer for answer in task["decode_map"]}
    answer = normalized.get(match.group(1).strip().casefold()) if match else None
    if answer is None:
        result["invalid_reason"] = "final_answer_unparseable"
        return result
    decoded = task["decode_map"][answer]
    result.update(status="complete", format_valid=True, answer=answer,
                  correct=answer == task["expected"], pattern=answer == task["pattern_label"],
                  decoded_value=decoded,
                  score=-1 if decoded == task["source_a"] else 1 if decoded == task["source_b"] else 0,
                  direct_instruction_adherent=(len(lines) == 1) if task["arm"] == "direct" else None)
    return result
