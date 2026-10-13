"""Immutable source stimuli, ordered requests and a blocked factorial schedule."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import re

from exception_pilot.core import check_plan, digest
import exception_pilot
from . import PROTOCOL_VERSION
from .scoring import PARSING_RULES

DATA = Path(__file__).with_name("data")
STIMULI_SHA256 = "2633c6520fabbb8706cd7cffede03c82bb50ad47d5a805efdadf6530dfe69bc0"
VALUES = ("record_1", "record_2")
INSTRUCTIONS = ("copy_record", "initial_answer")
INTERFACES = ("text", "json")
CONDITIONS = tuple(itertools.product(INSTRUCTIONS, INTERFACES))
FIELD_ORDER = ("first_value", "reasoning", "final_answer")
TEXT_INSTRUCTION = (
    'Output only plain text with the fields "first_value", "reasoning", and "final_answer", '
    'in that order. Begin each field on a new line using "field_name: value". '
    'Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. '
    'Your final answer may match or differ from the preliminary entry.'
)
DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION, "experiment_id": "instruction-interface-gpt4o-001",
    "provider": "openai", "model": "gpt-4o-2024-08-06", "api_key_env": "OPENAI_API_KEY",
    "n_worlds": 24, "target_position": 10, "temperature": 0,
    "max_completion_tokens": 1000, "timeout_seconds": 120,
    "block_seed": 2026101202, "within_block_seed": 2026101203,
    "bootstrap_seed": 2026101204, "bootstrap_resamples": 10000,
    "max_total_attempts": 212,
}
ANALYSIS_PLAN = {
    "primary": "(initial_answer-copy_record)json - (initial_answer-copy_record)text",
    "outcome": "Generated first entry equals target recorded class; all returned responses retained",
    "unit": "Average both variants within each world, then average the 24 paired world contrasts",
    "interval": "95% percentile; 10000 draws of 24 whole worlds with replacement; linear quantiles",
    "missing": "Transport errors/pending trials are missing, never incorrect; primary withheld until 192 returned",
    "positive": "JSON increases copying's disadvantage",
    "recognition": "Manual review only; no keyword-based recognition labels",
    "scope": "Previously examined worlds; output-interface package, not constrained decoding alone",
}


def request_hash(value):
    """Same order-sensitive serialization as the evidence-role harness."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_config(config):
    if not isinstance(config, dict) or set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Configuration fields differ from the frozen diagnostic")
    for key, expected in DEFAULT_CONFIG.items():
        actual = config[key]
        if key == "api_key_env":
            if not isinstance(actual, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", actual):
                raise ValueError("api_key_env must name an environment variable, never contain a secret")
        elif type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"Frozen configuration differs: {key}")


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_config(config)
    return config


def load_source():
    data = (DATA / "frozen_stimuli.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != STIMULI_SHA256:
        raise ValueError("Frozen source stimuli changed")
    source = json.loads(data)
    plan_bytes = (DATA / "evidence_role_source_plan.json").read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != source["provenance"]["plan_file_sha256"]:
        raise ValueError("Original source plan changed")
    original = json.loads(plan_bytes)
    check_plan(original)
    if original["plan_hash"] != source["provenance"]["plan_hash"]:
        raise ValueError("Original plan identity differs")
    return source, original


def source_digest():
    # Hash the new implementation and the reused provider/journal dependencies.
    paths = [*Path(__file__).parent.glob("*.py"),
             *Path(exception_pilot.__file__).parent.glob("*.py")]
    return digest({f"{p.parent.name}/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(paths)})


def make_plan(config):
    validate_config(config)
    source, original = load_source()  # Deliberately never calls make_world / the old make_plan.
    blocks = copy.deepcopy(source["stimuli"])
    random.Random(config["block_seed"]).shuffle(blocks)
    condition_rng = random.Random(config["within_block_seed"])
    tasks, requests = [], {}
    for block_index, stimulus in enumerate(blocks):
        conditions = list(CONDITIONS)
        condition_rng.shuffle(conditions)
        for instruction, interface in conditions:
            task_id = f"{stimulus['world_id']}/{stimulus['value']}/{instruction}/{interface}"
            task = {"id": task_id, "world_id": stimulus["world_id"], "value": stimulus["value"],
                    "instruction": instruction, "interface": interface, "block_index": block_index,
                    "expected": stimulus["meta"]["expected"]}
            output_instruction = source["json_instruction"] if interface == "json" else TEXT_INSTRUCTION
            prompt = (stimulus["prompt_stem"] + source["entry_instructions"][instruction]
                      + "\n" + output_instruction)
            request = {"model": config["model"], "messages": [{"role": "user", "content": prompt}],
                       "temperature": config["temperature"], "max_completion_tokens": config["max_completion_tokens"]}
            if interface == "json":
                request["response_format"] = copy.deepcopy(source["json_response_format"])
            request.update(n=source["settings"]["n"], store=source["settings"]["store"])
            tasks.append(task)
            requests[task_id] = request
    plan = {"protocol_version": PROTOCOL_VERSION, "experiment_id": config["experiment_id"],
            "source_digest": source_digest(), "config": copy.deepcopy(config),
            "source_provenance": {**source["provenance"], "frozen_stimuli_sha256": STIMULI_SHA256},
            "worlds": original["worlds"], "stimuli": source["stimuli"], "tasks": tasks,
            "requests": requests, "request_hashes": {k: request_hash(v) for k, v in requests.items()},
            "entry_instructions": source["entry_instructions"],
            "output_instructions": {"json": source["json_instruction"], "text": TEXT_INSTRUCTION},
            "analysis_plan": ANALYSIS_PLAN.copy(), "parsing_rules": PARSING_RULES.copy()}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text(encoding="utf-8"))
    check_plan(plan)
    if request_hash(plan) != request_hash(make_plan(plan["config"])):
        raise ValueError("Code, source, plan or schema order changed; preserve this run")
    return plan


def request_for(plan, task):
    return copy.deepcopy(plan["requests"][task["id"]])


def task_meta(plan, task):
    source = next(s for s in plan["stimuli"] if (s["world_id"], s["value"]) ==
                  (task["world_id"], task["value"]))
    return {**{k: v for k, v in source["meta"].items() if k not in ("condition", "copy_expected")},
            "instruction": task["instruction"], "interface": task["interface"],
            "block_index": task["block_index"]}
