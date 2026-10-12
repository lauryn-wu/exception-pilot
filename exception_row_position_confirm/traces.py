"""Offline, evidence-backed manual trace review; annotations never gate the run.

This module exports all returned visible responses, not a lexical or correctness
selected subset. Humans assign the codes; substring validation cannot establish
that two statements actually contradict one another.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, run_lock, write_json

from .core import task_meta
from .runner import read_run


CODING_RULE_VERSION = "row-position-confirm-manual-traces-v1"
CODES = ("false_missing", "self_contradiction", "gold_then_override")
GUIDANCE = {
    "scope": "Manual, descriptive coding of visible text; not hidden mechanisms or statistical gates. Review all returned visible responses, including invalid outputs and correct answers.",
    "false_missing": "True only when the response affirmatively describes the target's provided class as missing or unknown. Exclude conditional or negated mentions, actual MISSING input cells, and statements that only the query omits the class while acknowledging the table provides it. A bare question-mark placeholder or contradictory 'A (missing)' annotation requires an explanatory comment; do not silently conflate these with a clear MISSING claim.",
    "self_contradiction": "True when two unresolved assertions about the same target class conflict, including saying it is missing and elsewhere stating its recorded class. Supply at least two distinct exact quoted excerpts and explain the conflict. Mere discussion of alternative possibilities or an explicitly acknowledged correction is not coded as unresolved self-contradiction.",
    "gold_then_override": "True when the response explicitly states the target's correct recorded class and subsequently gives a different FINAL answer. Quote the gold statement and the later incompatible final answer in order; both excerpts must be exact substrings. A temporary wrong conclusion followed by a correct final answer does not qualify. Leave an ambiguous invalid final answer null and explain the uncertainty in comment.",
    "unknown": "Null means not yet reviewed or genuinely unresolved; never convert null to false. Codes are independent and may overlap. Record uncertainty in comment.",
    "evidence": "Every true code requires response-text evidence (at least one exact excerpt; at least two distinct excerpts for self_contradiction and gold_then_override). Evidence establishes the audit trail, not an automated semantic judgment.",
    "provenance": "Any non-null code requires a nonempty annotator and comment. Immutable fields and the entire attempt-journal digest are checked on import; export a new file after collection changes. Do not edit the run or original responses.",
}


def _blank_annotation():
    return {**{code: None for code in CODES},
            "evidence": {code: [] for code in CODES}, "annotator": "", "comment": ""}


def _target_row(record, meta):
    messages = record.get("request", {}).get("messages", [])
    candidates = []
    for message in messages:
        if message.get("role") != "user" or not isinstance(message.get("content"), str):
            continue
        for line in message["content"].splitlines():
            if line.startswith("|"):
                columns = [column.strip() for column in line.split("|")[1:-1]]
                if columns and columns[0] == meta["item_id"]:
                    candidates.append((line, columns[-1]))
    if len(candidates) != 1:
        raise ValueError("Expected exactly one retained input row for the target plate")
    return candidates[0]


def _snapshot(output):
    plan, config, execution, attempts = read_run(output)
    records = accepted_records(attempts)
    tasks = [task for task in plan["tasks"] if task["arm"] == "visible"]
    if len({task["id"] for task in tasks}) != len(tasks):
        raise ValueError("Duplicate visible task identifiers in frozen plan")
    items = []
    for task in tasks:
        record = records.get(task["id"])
        if record is None:
            continue
        meta = task_meta(plan, task)
        input_row, target_class = _target_row(record, meta)
        expected = meta.get("expected")
        if target_class != "MISSING" and target_class != expected:
            raise ValueError("Target input class disagrees with frozen expected label")
        response_text = record.get("response", {}).get("text", "")
        if not isinstance(response_text, str):
            raise ValueError("Returned response text must be a string")
        valid = record["status"] == "complete" and record.get("answer") in ("A", "B", "C")
        eligible = target_class in ("A", "B", "C") and expected in ("A", "B", "C")
        correct = record["answer"] == expected if valid and eligible else None
        items.append({
            "task_id": task["id"], "attempt": record["attempt"],
            "record_digest": digest(record), "status": record["status"],
            "world_id": meta["world_id"], "label_variant": meta["value"],
            "position": meta["position"] if "position" in meta else meta["target_position"],
            "item_id": meta["item_id"], "expected": expected,
            "answer": record.get("answer"), "correctness": correct,
            "coding_eligible": eligible,
            "target_input_row": input_row, "target_input_class": target_class,
            "raw_text": response_text,
            "raw_response_digest": digest(record.get("response", {}).get("raw_response")),
            "annotation": _blank_annotation(),
        })
    positions = sorted({task["position"] for task in tasks})
    coverage = {}
    for position in positions:
        planned = sum(task["position"] == position for task in tasks)
        returned = [item for item in items if item["position"] == position]
        coverage[str(position)] = {"planned_visible": planned,
                                   "returned_visible": len(returned),
                                   "unreturned_visible": planned - len(returned),
                                   "returned_invalid": sum(item["status"] == "invalid" for item in returned)}
    return {
        "coding_rule_version": CODING_RULE_VERSION,
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "config_hash": digest(config), "records_digest": digest(attempts),
        "execution_mode": execution["mode"] if execution else "not_started",
        "is_simulated": bool(execution and execution["mode"] == "mock"),
        "planned_visible": len(tasks), "returned_visible": len(items),
        "unreturned_visible": len(tasks) - len(items), "coverage_by_position": coverage,
        "guidance": GUIDANCE, "items": items,
    }


def _check_review_path(output, review_path):
    path = Path(review_path)
    if path.resolve() in {(Path(output) / name).resolve()
                          for name in ("trace_summary.json", "trace_summary.md")}:
        raise ValueError("The review file must differ from the generated trace summaries")
    return path


def _write_exclusive(path, value):
    """Atomically publish a new review without ever replacing an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise ValueError("Review file already exists; preserve annotations and choose a new path") from None
    finally:
        os.unlink(temporary)


def export_trace_review(output, review_path):
    """Export a new manual-review snapshot offline. Acquires its own run lock."""
    path = _check_review_path(output, review_path)
    with run_lock(output):
        snapshot = _snapshot(output)
        _write_exclusive(path, snapshot)
    return {"review_file": str(path), "coding_rule_version": CODING_RULE_VERSION,
            **{key: snapshot[key] for key in ("plan_hash", "records_digest", "planned_visible",
                                              "returned_visible", "unreturned_visible", "is_simulated")},
            "api_calls": 0}


def _validate_annotation(item):
    annotation = item["annotation"]
    if not isinstance(annotation, dict) or set(annotation) != set(_blank_annotation()):
        raise ValueError("Annotation fields differ from the manual coding schema")
    if not isinstance(annotation["evidence"], dict) or set(annotation["evidence"]) != set(CODES):
        raise ValueError("Evidence must have one list per manual code")
    for field in ("annotator", "comment"):
        if not isinstance(annotation[field], str):
            raise ValueError("Annotator and comment must be strings")
    reviewed = any(annotation[code] is not None for code in CODES)
    if reviewed and (not annotation["annotator"].strip() or not annotation["comment"].strip()):
        raise ValueError("Every reviewed annotation needs a nonempty annotator and comment")
    if reviewed and not item["coding_eligible"]:
        raise ValueError("Actual MISSING or absent-gold inputs are excluded from trace coding")
    for code in CODES:
        value, quotes = annotation[code], annotation["evidence"][code]
        if value is not None and type(value) is not bool:
            raise ValueError("Manual codes must be true, false, or null; unknown is not false")
        if not isinstance(quotes, list) or any(not isinstance(q, str) or not q.strip() for q in quotes):
            raise ValueError("Evidence quotes must be nonempty strings")
        if value is not True and quotes:
            raise ValueError("Only positive codes may carry evidence excerpts")
        if value is True:
            minimum = 2 if code in ("self_contradiction", "gold_then_override") else 1
            if len(set(quotes)) < minimum:
                raise ValueError(f"{code} requires at least {minimum} distinct exact evidence excerpts")
            if any(quote not in item["raw_text"] for quote in quotes):
                raise ValueError("Evidence must quote the exact retained response text")
            if code == "gold_then_override":
                if item["answer"] == item["expected"]:
                    raise ValueError("Gold-then-override requires a final answer different from the recorded gold")
                # The two requested assertions must be in temporal text order.
                first = item["raw_text"].find(quotes[0])
                if item["raw_text"].find(quotes[1], first + len(quotes[0])) < 0:
                    raise ValueError("Gold-then-override evidence must quote gold before a later conflicting statement")


def _validate_review(review, snapshot):
    if not isinstance(review, dict) or set(review) != set(snapshot):
        raise ValueError("Review schema differs from the exported snapshot")
    if digest({key: review[key] for key in review if key != "items"}) != digest(
            {key: snapshot[key] for key in snapshot if key != "items"}):
        raise ValueError("Stale or altered review identity, coding rules, or attempt-journal digest")
    if not isinstance(review["items"], list):
        raise ValueError("Review items must be a list")
    expected = {item["task_id"]: item for item in snapshot["items"]}
    seen = set()
    for item in review["items"]:
        if not isinstance(item, dict) or item.get("task_id") not in expected:
            raise ValueError("Review contains an unknown response identifier")
        task_id = item["task_id"]
        if task_id in seen:
            raise ValueError("Duplicate response identifier in manual review")
        seen.add(task_id)
        original = expected[task_id]
        if set(item) != set(original) or digest({key: item[key] for key in item if key != "annotation"}) != digest(
                {key: original[key] for key in original if key != "annotation"}):
            raise ValueError("Immutable response text, metadata, or identity was altered")
        _validate_annotation(item)
    if seen != set(expected):
        raise ValueError("Review omits returned visible responses; leave unreviewed codes null instead")


def _counts(items):
    eligible = [item for item in items if item["coding_eligible"]]
    result = {"returned": len(items), "eligible": len(eligible),
              "excluded_no_recorded_gold": len(items) - len(eligible),
              "fully_reviewed": sum(all(item["annotation"][code] is not None for code in CODES)
                                    for item in eligible), "codes": {}}
    for code in CODES:
        values = [item["annotation"][code] for item in eligible]
        positive, negative = sum(value is True for value in values), sum(value is False for value in values)
        reviewed = positive + negative
        result["codes"][code] = {"positive": positive, "negative": negative,
                                 "reviewed": reviewed, "unreviewed": len(values) - reviewed,
                                 "positive_fraction_among_reviewed": positive / reviewed if reviewed else None}
    return result


def summarize_trace_review(output, review_path):
    """Validate a partial/complete manual snapshot, then write descriptive counts."""
    output, path = Path(output), _check_review_path(output, review_path)
    with run_lock(output):
        snapshot = _snapshot(output)
        review = json.loads(path.read_text())
        _validate_review(review, snapshot)
        items = review["items"]
        by_position = {}
        for position, coverage in snapshot["coverage_by_position"].items():
            selected = [item for item in items if item["position"] == int(position)]
            by_position[position] = {**coverage, **_counts(selected), "by_correctness": {
                label: _counts([item for item in selected if item["correctness"] is value])
                for label, value in (("correct", True), ("wrong", False), ("invalid_or_unscorable", None))}}
        result = {"coding_rule_version": CODING_RULE_VERSION,
                  **{key: snapshot[key] for key in ("protocol_version", "plan_hash", "config_hash",
                                                   "records_digest", "execution_mode", "is_simulated",
                                                   "planned_visible", "returned_visible", "unreturned_visible")},
                  "review_file": str(path), "review_digest": digest(review), "api_calls": 0,
                  "method": "Manual descriptive annotations. Positive counts are human judgments with exact quoted evidence, not automated semantic classifications. Codes overlap and do not enter any statistical gate.",
                  "total": _counts(items), "by_position": by_position}
        lines = ["# Manual visible-trace review", "",
                 "**SIMULATED — software fixture, not model evidence**" if snapshot["is_simulated"]
                 else "Offline manual review of retained responses.", "",
                 result["method"], "",
                 f"Returned visible responses: {snapshot['returned_visible']} / {snapshot['planned_visible']}; "
                 f"unreturned: {snapshot['unreturned_visible']}. Unreturned responses have no trace to review.",
                 "Unknown codes remain unreviewed; positive rates use only reviewed, eligible responses. "
                 "Invalid answers remain available for trace coding and appear separately by correctness. "
                 "Actual MISSING or absent-gold inputs are excluded. Review is not blinded to outcomes, "
                 "and correctness does not validate a rationale.", "",
                 f"Coding rules: `{CODING_RULE_VERSION}`. Annotators: "
                 + (", ".join(sorted({item['annotation']['annotator'].strip() for item in items
                                      if any(item['annotation'][code] is not None for code in CODES)})) or "none")
                 + ".", "",
                 "| Row | Outcome group | Returned / eligible | Code | Positive / reviewed | Negative | Unreviewed |",
                 "|---|---|---:|---|---:|---:|---:|"]
        for position, aggregate in by_position.items():
            for label, group in [("all", aggregate), *aggregate["by_correctness"].items()]:
                for code, count in group["codes"].items():
                    lines.append(f"| {position} | {label} | {group['returned']} / {group['eligible']} | {code} | "
                                 f"{count['positive']} / {count['reviewed']} | {count['negative']} | {count['unreviewed']} |")
        write_json(output / "trace_summary.json", result)
        (output / "trace_summary.md").write_text("\n".join(lines) + "\n")
    return result
