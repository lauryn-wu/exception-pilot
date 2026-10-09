"""Reuse every V1 request, allowing ASCII whitespace in the final answer block."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

from exception_pilot.core import check_plan, digest
from exception_pilot.storage import accepted_records
from exception_mistral_map import core as v1
from exception_mistral_map.analysis import summarize as summarize_v1
from exception_mistral_map.runner import read_run as read_v1_run
from . import PROTOCOL_VERSION

# Reuse immutable checkpoint, request, and gate functions without monkeypatching.
case_point = v1.case_point
task_meta = v1.task_meta
request_for = v1.request_for
capability_gate = v1.capability_gate
sampling_gate = v1.sampling_gate

DEFAULT_CONFIG = {**copy.deepcopy(v1.DEFAULT_CONFIG), "protocol": PROTOCOL_VERSION}
SCORING_RULE = {
    "version": "terminal-answer-ascii-whitespace-v1",
    "change": "Allow one or more ASCII whitespace characters between terminal ANSWER: and a single uppercase A/B/C; permit trailing ASCII whitespace.",
    "preserved": "Exact prefix and capability checks, complete provider responses, reasoning presence, direct answer-only requirement, prompts, sampling settings, task schedule, all thresholds and attempt cap.",
    "retrospective": True,
    "reason": "After six V1 calls, a visible response ended with ANSWER: followed by newline and A. The original strict parser rejected this unambiguous answer.",
    "scope": "Apply the same rule to every saved and future answer, for every arm and A/B/C, regardless of correctness. Preserve strict scores and every original journal.",
}
_FINAL = re.compile(r"^[ \t]*ANSWER:[ \t\r\n\f\v]+([ABC])[ \t\r\n\f\v]*\Z", re.M)


def validate_config(config):
    original = copy.deepcopy(config)
    if not isinstance(original, dict) or original.get("protocol") != PROTOCOL_VERSION:
        raise ValueError("Use configs/mistral_map_v2.json")
    original["protocol"] = v1.DEFAULT_CONFIG["protocol"]
    v1.validate_config(original)


def load_config(path):
    config = json.loads(Path(path).read_text())
    validate_config(config)
    return config


def source_digest():
    return digest({"frozen_v1": v1.source_digest(),
                   "v2": {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}})


def score_response(task, response, meta):
    strict = v1.score_response(task, response, meta)
    result = copy.deepcopy(strict)
    result.update(strict_v1_score=strict, answer_whitespace_normalized=False)
    # Never relax capability, prefix, provider completion, or reasoning checks.
    if strict["invalid_reason"] != "final_answer_unparseable":
        return result
    match = _FINAL.search(response["text"])
    if match is None:
        return result
    pretext = bool(response["text"][:match.start()].strip())
    reason = ("direct_not_answer_only" if task["arm"] == "direct" and pretext else
              "reasoning_text_missing" if task["arm"] in ("visible", "map") and not pretext else None)
    result.update(answer=match.group(1) if reason is None else None,
                  status="complete" if reason is None else "invalid", format_valid=reason is None,
                  invalid_reason=reason, pre_answer_text=pretext,
                  answer_whitespace_normalized=reason is None)
    return result


def snapshot_paths(path):
    """Only known run metadata and journals; no unrelated files or credentials."""
    path = Path(path)
    roots = [Path(), Path("source-parent")]
    return [relative for root in roots
            for relative in ([root / "plan.json", root / "execution.json"] +
                             [p.relative_to(path) for p in sorted((path / root / "attempts").glob("*.json"))])]


def read_previous(path):
    path = Path(path)
    plan, execution, attempts = read_v1_run(path)
    if execution is None or not attempts:
        raise ValueError("Migration requires an existing V1 execution journal")
    tasks = {t["id"]: t for t in plan["tasks"]}
    if any(tasks[a["task_id"]]["family"] == "map" for a in attempts):
        raise ValueError("This amendment migrates the sampling check only; mapping already started")
    if any(a.get("hard_failure") for a in attempts):
        raise ValueError("A provider/prefix/capability failure cannot be repaired by this scoring amendment")
    changed = []
    for record in accepted_records(attempts).values():
        scored = score_response(tasks[record["task_id"]], record["response"], record["meta"])
        if scored["status"] == "invalid":
            raise ValueError("An invalid response remains unscorable under the whitespace-only amendment")
        if scored["answer_whitespace_normalized"]:
            changed.append(record["task_id"])
    if not changed:
        raise ValueError("No whitespace-rejected response to migrate; do not restart a failed accuracy check")
    summary = summarize_v1(plan, attempts, execution["mode"])
    hashes = {str(p): hashlib.sha256((path / p).read_bytes()).hexdigest() for p in snapshot_paths(path)}
    return {"plan": plan, "execution": execution, "attempts": attempts, "file_sha256": hashes,
            "original_analysis_status": summary["analysis_status"],
            "original_sampling_gate": summary["sampling_gate"], "normalized_task_ids": changed}


def make_plan(config, previous):
    validate_config(config)
    old = previous["plan"]
    if {**config, "protocol": old["config"]["protocol"]} != old["config"]:
        raise ValueError("Only the scoring protocol may change; all request settings must match V1")
    plan = copy.deepcopy(old)
    plan.pop("plan_hash")
    plan.update(protocol_version=PROTOCOL_VERSION, config=copy.deepcopy(config), source_digest=source_digest(),
                previous_snapshot_digest=digest(previous), scoring_amendment=copy.deepcopy(SCORING_RULE),
                previous_run={"plan_hash": old["plan_hash"], "attempts": len(previous["attempts"]),
                              "analysis_status": previous["original_analysis_status"],
                              "sampling_gate": previous["original_sampling_gate"],
                              "normalized_task_ids": previous["normalized_task_ids"]})
    plan["interpretation"] += " Whitespace parsing was amended after six V1 calls; this is disclosed exploratory continuation, not a fresh or preregistered confirmation."
    if any(request_for(plan, task) != v1.request_for(old, task) for task in plan["tasks"]):
        raise ValueError("The amendment changed a request")
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    output = Path(output)
    plan = json.loads((output / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"], read_previous(output / "source-map-v1")):
        raise ValueError("V2 source, code, config, or plan changed; preserve this run")
    return plan


def imported_attempts(plan, previous):
    """Derive all entries; originals remain byte-for-byte in source-map-v1."""
    result = []
    tasks = {t["id"]: t for t in plan["tasks"]}
    for old in previous["attempts"]:
        new = copy.deepcopy(old)
        new.update(plan_hash=plan["plan_hash"], imported_from_v1={
            "attempt": old["attempt"], "plan_hash": old["plan_hash"], "record_digest": digest(old)})
        if old["status"] in ("complete", "invalid"):
            new.update(score_response(tasks[old["task_id"]], old["response"], old["meta"]))
        result.append(new)
    return result
