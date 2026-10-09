"""Fixed terminal presentation grammar; collect the entire unchanged screen."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest
from exception_pilot.storage import accepted_records
from exception_mistral_map import core as v1
from exception_mistral_map_v2 import core as v2
from exception_mistral_map_v2.analysis import summarize as summarize_v2
from exception_mistral_map_v2.runner import read_run as read_v2_run
from . import PROTOCOL_VERSION
from .parser import answer_boundary

# Reuse immutable checkpoint, request, and gate functions without monkeypatching.
case_point = v1.case_point
task_meta = v1.task_meta
request_for = v1.request_for
capability_gate = v1.capability_gate
def sampling_gate(plan, records):
    result = v1.sampling_gate(plan, records)
    tasks = [t for t in plan["tasks"] if t["family"] == "base"]
    invalid = [t["id"] for t in tasks if t["id"] in records and records[t["id"]]["status"] == "invalid"]
    result.update(n_invalid=len(invalid), n_pending=len(tasks) - result["n_returned"],
                  unscorable_task_ids=invalid)
    # Collect the entire fixed screen; never discard or replace invalid answers.
    if result["n_returned"] < len(tasks):
        result["status"] = "incomplete"
    result["decision_basis"] = ("collection_incomplete" if result["status"] == "incomplete" else
                                "unscorable_responses" if invalid else "original_behavioral_thresholds")
    return result

DEFAULT_CONFIG = {**copy.deepcopy(v1.DEFAULT_CONFIG), "protocol": PROTOCOL_VERSION}
SCORING_RULE = {
    "version": "terminal-answer-presentation-v1",
    "change": "Parse a bounded terminal block with an ASCII case-insensitive ANSWER marker, optional ASCII whitespace, balanced Markdown emphasis/inline code, optionally one period or a complete text fence. Labels stay uppercase A/B/C; no prose or alternatives are guessed.",
    "collection_change": "Collect all 48 base responses before evaluating format failures; retain every unscorable response without retry. Any unscorable response blocks mapping after collection.",
    "preserved": "All requests, prefix/capability/provider checks, reasoning and direct-format requirements, sampling settings, checkpoints, thresholds and attempt cap.",
    "retrospective": True,
    "reason": "After nine total responses, V2 rejected the unambiguous bold block **ANSWER: A**. V1 had rejected a newline after ANSWER: at response six.",
    "scope": "One grammar for every saved/future response, label and arm, regardless of correctness. Preserve V1/V2 scores and original journals.",
}


def validate_config(config):
    original = copy.deepcopy(config)
    if not isinstance(original, dict) or original.get("protocol") != PROTOCOL_VERSION:
        raise ValueError("Use configs/mistral_map_v3.json")
    original["protocol"] = v1.DEFAULT_CONFIG["protocol"]
    v1.validate_config(original)


def load_config(path):
    config = json.loads(Path(path).read_text())
    validate_config(config)
    return config


def source_digest():
    return digest({"frozen_v2": v2.source_digest(),
                   "v3": {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}})


def score_response(task, response, meta):
    previous = v2.score_response(task, response, meta)
    result = copy.deepcopy(previous)
    result.update(strict_v2_score=previous, answer_presentation_normalized=False)
    # Capability, provider completion, prefix identity, and raw text stay exact.
    if task["family"] == "capability" or previous["invalid_reason"] not in (
            None, "final_answer_unparseable", "direct_not_answer_only", "reasoning_text_missing"):
        return result
    label, start = answer_boundary(response["text"])
    pretext = bool(response["text"][:start].strip()) if label is not None else None
    reason = ("final_answer_unparseable" if label is None else
              "direct_not_answer_only" if task["arm"] == "direct" and pretext else
              "reasoning_text_missing" if task["arm"] in ("visible", "map") and not pretext else None)
    result.update(answer=label if reason is None else None,
                  status="complete" if reason is None else "invalid", format_valid=reason is None,
                  invalid_reason=reason, pre_answer_text=pretext,
                  answer_presentation_normalized=reason is None and not previous["format_valid"])
    return result


def snapshot_paths(path):
    """Copy V2 journals plus its entire frozen V1/parent provenance tree."""
    path = Path(path)
    top = [Path("plan.json"), Path("execution.json")] + [p.relative_to(path) for p in sorted((path / "attempts").glob("*.json"))]
    nested = [Path("source-map-v1") / p for p in v2.snapshot_paths(path / "source-map-v1")]
    return top + nested


def read_previous(path):
    path = Path(path)
    plan, execution, attempts = read_v2_run(path)
    if execution is None or not attempts:
        raise ValueError("Migration requires an existing V2 execution journal")
    tasks = {t["id"]: t for t in plan["tasks"]}
    if any(tasks[a["task_id"]]["family"] == "map" for a in attempts):
        raise ValueError("This amendment migrates the sampling check only; mapping already started")
    if any(a.get("hard_failure") for a in attempts):
        raise ValueError("A provider/prefix/capability failure cannot be repaired by this scoring amendment")
    changed, remaining = [], []
    for record in accepted_records(attempts).values():
        scored = score_response(tasks[record["task_id"]], record["response"], record["meta"])
        if scored["status"] == "invalid":
            remaining.append(record["task_id"])
        if scored["answer_presentation_normalized"]:
            changed.append(record["task_id"])
    if not any(r["status"] == "invalid" for r in accepted_records(attempts).values()):
        raise ValueError("No format failure to migrate; do not restart a failed accuracy check")
    summary = summarize_v2(plan, attempts, execution["mode"])
    hashes = {str(p): hashlib.sha256((path / p).read_bytes()).hexdigest() for p in snapshot_paths(path)}
    return {"plan": plan, "execution": execution, "attempts": attempts, "file_sha256": hashes,
            "original_analysis_status": summary["analysis_status"],
            "original_sampling_gate": summary["sampling_gate"], "normalized_task_ids": changed,
            "unscorable_task_ids": remaining}


def make_plan(config, previous):
    validate_config(config)
    old = previous["plan"]
    if {**config, "protocol": old["config"]["protocol"]} != old["config"]:
        raise ValueError("Only the scoring protocol may change; all request settings must match V2")
    plan = copy.deepcopy(old)
    plan.pop("plan_hash")
    plan.update(protocol_version=PROTOCOL_VERSION, config=copy.deepcopy(config), source_digest=source_digest(),
                previous_snapshot_digest=digest(previous), scoring_amendment=copy.deepcopy(SCORING_RULE),
                earlier_v1_run=copy.deepcopy(old["previous_run"]),
                previous_run={"plan_hash": old["plan_hash"], "attempts": len(previous["attempts"]),
                              "analysis_status": previous["original_analysis_status"],
                              "sampling_gate": previous["original_sampling_gate"],
                              "normalized_task_ids": previous["normalized_task_ids"],
                              "unscorable_task_ids": previous["unscorable_task_ids"]})
    plan["interpretation"] += " V3 presentation parsing and complete-screen collection were amended after nine responses. All past answers are retained; this is exploratory continuation, not independent confirmation."
    if any(request_for(plan, task) != v1.request_for(old, task) for task in plan["tasks"]):
        raise ValueError("The amendment changed a request")
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    output = Path(output)
    plan = json.loads((output / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"], read_previous(output / "source-map-v2")):
        raise ValueError("V3 source, code, config, or plan changed; preserve this run")
    return plan


def imported_attempts(plan, previous):
    """Derive all entries; originals remain byte-for-byte in source-map-v2."""
    result = []
    tasks = {t["id"]: t for t in plan["tasks"]}
    for old in previous["attempts"]:
        new = copy.deepcopy(old)
        new.update(plan_hash=plan["plan_hash"], imported_from_v2={
            "attempt": old["attempt"], "plan_hash": old["plan_hash"], "record_digest": digest(old)})
        if old["status"] in ("complete", "invalid"):
            new.update(score_response(tasks[old["task_id"]], old["response"], old["meta"]))
        result.append(new)
    return result
