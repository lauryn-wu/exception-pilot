"""Frozen source snapshots, natural boundaries, and exact continuation requests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import random
import re

from exception_pilot.core import check_plan, digest
from exception_pilot.storage import accepted_records
from exception_mistral_prefix_v2 import core as parent_core
from exception_mistral_prefix_v2.runner import read_run as read_parent_run
from . import PROTOCOL_VERSION

DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION, "model": "mistral-small-2603",
    "endpoint": parent_core.ENDPOINT, "api_key_env": "MISTRAL_API_KEY",
    "temperature": 0.6, "top_p": 0.95, "reasoning_effort": "none",
    "repeats": 6, "seed": 2026100943,
    "max_tokens": {"capability": 32, "direct": 1600, "visible": 1600, "map": 1600},
    "max_total_attempts": 1107, "timeout_seconds": 120,
    "min_request_interval_seconds": 10,
}


def load_config(path):
    config = json.loads(Path(path).read_text())
    validate_config(config)
    return config


def validate_config(config):
    expected = copy.deepcopy(DEFAULT_CONFIG)
    key = config.get("api_key_env") if isinstance(config, dict) else None
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key):
        raise ValueError("api_key_env must name an environment variable, never contain a key")
    expected["api_key_env"] = key
    if config != expected or any(type(config[k]) is not type(v) for k, v in expected.items()):
        raise ValueError("Use the fixed configs/mistral_map.json; changes require a new protocol")


def source_digest():
    root = Path(__file__).resolve().parents[1]
    return digest({"parent_source": parent_core.source_digest(),
                   "map_source": {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}})


def read_source(path):
    plan, execution, attempts = read_parent_run(path)
    if execution is None:
        raise ValueError("The source has no execution journal")
    records = accepted_records(attempts)
    if execution["mode"] == "live" and any(r["response"]["model"] != "mistral-small-2603" for r in records.values()):
        raise ValueError("Live source returned a different model identifier")
    if (parent_core.capability_gate(plan, records)["status"] != "pass"
            or parent_core.phenomenon_gate(plan, records)["status"] != "pass"):
        raise ValueError("Source must be an audited V2 run with all 48 base responses and a passing base gate")
    # The old replay result is retained, never changed or used to filter parents.
    return {"plan": plan, "execution": execution, "attempts": attempts}


def checkpoints(text, target_id, other_ids):
    """Coarse numbered-step map plus an isolated first target-class line.

    This is a syntactic rule, not an LLM or semantic annotation of causality.
    Exact offsets and intervening blocks are exported for human inspection.
    """
    numbered = re.compile(r"^(?:\d+\.\s|Step\s+\d+:\s)", re.I)
    conclusion = re.compile(r"\b(?:conclusion|summary)\b|\btherefore\b|all remaining matching records point", re.I)
    final_intro = re.compile(r"^(?:Therefore\b|Thus\b|Hence\b|Given that\b|Given the verified class\b)", re.I)
    lines, offset = [], 0
    for raw in text.splitlines(keepends=True):
        lines.append((offset, offset + len(raw), raw))
        offset += len(raw)
    stop = None
    stop_reason = None
    for start, end, raw in lines:
        plain = raw.replace("*", "").strip()
        if (numbered.match(plain) and conclusion.search(plain)) or final_intro.match(plain):
            stop, stop_reason = start, "before_conclusion_or_summary"
            break
        if re.fullmatch(r"ANSWER:\s*[ABC]", plain):
            stop, stop_reason = start, "before_final_answer_line"
            break
    if stop is None or not text[stop:].strip():
        raise ValueError("Source lacks a supported pre-answer boundary")
    points = {0: ["start_without_assistant_prefix"]}

    def add(position, label):
        if position < 0 or position > stop or (position and not text[position - 1].isspace()):
            raise ValueError("A checkpoint must be a complete whitespace/line boundary")
        points.setdefault(position, []).append(label)

    for start, end, raw in lines:
        if start < stop and numbered.match(raw.replace("*", "").strip()):
            add(start, "before_numbered_step")
    add(stop, stop_reason)
    record_span = None
    # A bare field in the opening target-attribute block, or an explicitly
    # target-linked class statement. Other vehicles' class lines are excluded.
    value = r"(?:[ABC]\b|MISSING\b|\?)"
    field = re.compile(r"verified\s+class\s*(?::|is|of)?\s*" + value, re.I)
    target_field = re.compile(re.escape(target_id) + r"[^\n]*?\bclass\s*(?::|is|of)?\s*" + value, re.I)
    seen_other = False
    for start, end, raw in lines:
        if start >= stop:
            break
        plain = raw.replace("*", "")
        foreign = any(other in plain for other in other_ids)
        explicit = target_field.search(plain)
        opening_field = field.search(plain) and not seen_other and not foreign
        if explicit or opening_field:
            # Include following blank whitespace, but no subsequent reasoning.
            while end < stop and text[end].isspace():
                end += 1
            if end <= stop:
                add(start, "before_target_record_line")
                add(end, "after_target_record_line")
                record_span = {"start": start, "end": end, "text": text[start:end],
                               "contains_missing_word": bool(re.search(r"\bmissing\b", plain, re.I))}
            break
        seen_other = seen_other or foreign
    ordered = []
    for index, position in enumerate(sorted(points)):
        ordered.append({"id": f"c{index:02d}", "cut_chars": position,
                        "labels": sorted(set(points[position])),
                        "retained_block_since_previous": text[ordered[-1]["cut_chars"]:position] if ordered else "",
                        "parent_next_line": text[position:].splitlines()[0] if text[position:] else ""})
    if len(ordered) > 14:
        raise ValueError("More than 14 checkpoints in a trace; stop for design review, do not silently prune")
    return ordered, record_span


def make_plan(config, source):
    validate_config(config)
    parent = source["plan"]
    records = accepted_records(source["attempts"])
    cases = []
    for task in parent["tasks"]:
        if task["family"] != "base" or task["arm"] != "visible":
            continue
        record = records[task["id"]]
        if record["status"] != "complete":
            raise ValueError("All visible parents must be valid; no answer-based case selection")
        meta = record["meta"]
        world = parent_core.world_for(parent, task)
        text = record["response"]["text"]
        points, span = checkpoints(text, meta["item_id"],
                                  [item["id"] for item in world["items"] if item["id"] != meta["item_id"]])
        cases.append({"id": task["id"], "meta": copy.deepcopy(meta),
                      "messages": copy.deepcopy(record["request"]["messages"]),
                      "parent_text": text, "parent_answer": record["answer"],
                      "parent_correct": record["answer"] == meta["expected"],
                      "parent_response_id": record["response"]["response_id"],
                      "parent_raw_digest": digest(record["response"]["raw_response"]),
                      "checkpoints": points, "target_record_line": span})
    if len(cases) != 24 or len({c["meta"]["world_id"] for c in cases}) != 12:
        raise ValueError("This pilot requires all 24 visible parents from 12 V2 worlds")
    tasks = [copy.deepcopy(t) for t in parent["tasks"] if t["family"] in ("capability", "base")]
    mapping = []
    rng = random.Random(config["seed"])
    for repeat in range(1, config["repeats"] + 1):
        block = [{"id": f"{case['id']}/map/{point['id']}/r{repeat}", "family": "map", "arm": "map",
                  "case_id": case["id"], "checkpoint_id": point["id"], "repeat": repeat,
                  "world_id": case["meta"]["world_id"], "value": case["meta"]["value"]}
                 for case in cases for point in case["checkpoints"]]
        rng.shuffle(block)
        mapping.extend(block)
    tasks.extend(mapping)
    if len(tasks) + 24 > config["max_total_attempts"]:
        raise ValueError("Plan leaves fewer than 24 transport-retry attempts; stop for design review")
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "config": copy.deepcopy(config), "source_snapshot_digest": digest(source),
            "source_plan_hash": parent["plan_hash"], "source_mode": source["execution"]["mode"],
            "source_replay_gate": parent_core.replay_gate(parent, records),
            "worlds": copy.deepcopy(parent["worlds"]), "cases": cases, "tasks": tasks,
            "interpretation": "Exploratory mapping of previously inspected traces on reused worlds. Six stochastic continuations per checkpoint are coarse estimates. No corrections or independent confirmation; no internal-state restoration or replay-agreement gate."}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    output = Path(output)
    plan = json.loads((output / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"], read_source(output / "source-parent")):
        raise ValueError("Source, code, config, or saved plan changed; preserve this run")
    return plan


def case_point(plan, task):
    case = next(c for c in plan["cases"] if c["id"] == task["case_id"])
    point = next(p for p in case["checkpoints"] if p["id"] == task["checkpoint_id"])
    return case, point


def task_meta(plan, task):
    if task["family"] != "map":
        return parent_core.task_meta(plan, task)
    case, point = case_point(plan, task)
    return {**case["meta"], "family": "map", "arm": "map", "case_id": case["id"],
            "checkpoint_id": point["id"], "repeat": task["repeat"], "cut_chars": point["cut_chars"],
            "checkpoint_labels": point["labels"], "parent_answer": case["parent_answer"],
            "parent_correct": case["parent_correct"], "parent_raw_digest": case["parent_raw_digest"],
            "prefix_text": case["parent_text"][:point["cut_chars"]]}


def request_for(plan, task):
    if task["family"] == "map":
        case, point = case_point(plan, task)
        messages = copy.deepcopy(case["messages"])
        prefix = case["parent_text"][:point["cut_chars"]]
        if prefix:
            messages.append({"role": "assistant", "content": prefix, "prefix": True})
    else:
        messages = parent_core.messages_for(plan, task)
    config = plan["config"]
    return {"model": config["model"], "messages": messages, "temperature": config["temperature"],
            "top_p": config["top_p"], "max_tokens": config["max_tokens"][task["arm"]],
            "reasoning_effort": config["reasoning_effort"], "stream": False}


def score_response(task, response, meta):
    prefix = meta.get("prefix_text", "")
    exact = response["text"].startswith(prefix) if task["family"] == "map" else None
    normalized = copy.deepcopy(response)
    if task["family"] == "map" and not exact:
        normalized.update(complete=False, provider_invalid_reason="prefix_mismatch")
    scoring_task = {**task, "family": "base", "arm": "visible"} if task["family"] == "map" else task
    result = parent_core.score_response(scoring_task, normalized, meta)
    suffix = response["text"][len(prefix):] if exact else None
    result.update(prefix_exact=exact, generated_suffix=suffix,
                  suffix_contains_missing_word=bool(re.search(r"\bmissing\b", suffix, re.I)) if suffix is not None else None)
    return result


def capability_gate(plan, records):
    return parent_core.capability_gate(plan, records)


def sampling_gate(plan, records):
    return parent_core.phenomenon_gate(plan, records)
