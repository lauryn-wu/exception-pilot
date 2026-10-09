"""Descriptive maps and world-level contrasts, never a mechanism verdict."""

from __future__ import annotations

import csv
from pathlib import Path

from exception_pilot.storage import accepted_records, write_json
from exception_mistral_map.analysis import summarize as summarize_v1
from .core import sampling_gate


def summarize(plan, attempts, mode):
    result = summarize_v1(plan, attempts, mode)
    strict = []
    for attempt in attempts:
        record = dict(attempt)
        if "strict_v1_score" in record:
            record.update(record["strict_v1_score"])
        if record.get("hard_failure"):
            record.update(status="invalid", format_valid=False, answer=None, invalid_reason=record["hard_failure"])
        strict.append(record)
    strict_records = accepted_records(strict)
    records = accepted_records(attempts)
    result.update(scoring_amendment=plan["scoring_amendment"], previous_v1_result=plan["previous_run"],
                  imported_attempts=plan["previous_run"]["attempts"],
                  new_attempts=len(attempts) - plan["previous_run"]["attempts"],
                  whitespace_normalized_responses=sum(bool(a.get("answer_whitespace_normalized")) for a in attempts),
                  strict_v1_sampling_gate_on_collected_answers=sampling_gate(plan, strict_records))
    for row in result["answers"]:
        record = records.get(row["task_id"], {})
        original = strict_records.get(row["task_id"], {})
        row.update(strict_v1_status=original.get("status", "pending"),
                   strict_v1_answer=original.get("answer"), strict_v1_invalid_reason=original.get("invalid_reason"),
                   answer_whitespace_normalized=bool(record.get("answer_whitespace_normalized")))
    result["strict_v1_format_counts"] = {
        group: {"returned": sum(r["status"] != "pending" for r in result["answers"] if r["arm"] == group),
                "strict_valid": sum(r["strict_v1_status"] == "complete" for r in result["answers"] if r["arm"] == group),
                "whitespace_normalized": sum(r["answer_whitespace_normalized"] for r in result["answers"] if r["arm"] == group)}
        for group in ("direct", "visible", "map")}
    result["limits"].append("Whitespace scoring was amended after observing a V1 formatting failure. The original failed check is preserved; strict scoring of all later responses is a sensitivity view, not an executed V1 run. Imported calls are not fresh samples.")
    return result


def _rate(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    result = summarize(plan, attempts, execution["mode"] if execution else "unstarted")
    write_json(output / "summary.json", result)
    rows = result["answers"]
    with (output / "answers.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Regenerated export. Human coding must be saved under a different filename.
    with (output / "continuations-to-code.csv").open("w", newline="") as f:
        fields = ["task_id", "case_id", "checkpoint_id", "generated_suffix", "target_missing_claim", "uses_record", "uses_pattern", "notes"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({**{k: r.get(k) for k in fields[:4]}, **{k: "" for k in fields[4:]}}
                        for r in rows if r["family"] == "map" and r["generated_suffix"] is not None)
    lines = ["# Mistral continuation map V2 — exploratory", "", f"Status: **{result['analysis_status']}**",
             f"SIMULATED: {result['is_simulated']}. {result['attempts_total']}/{result['planned_calls']} attempts/planned responses.",
             "12 reused parent worlds; 24 parent traces. No corrected text is supplied. No independent confirmation or internal mechanism claim.", "",
             "## Scoring amendment", "", result["scoring_amendment"]["change"],
             f"Original V1 status: **{result['previous_v1_result']['analysis_status']}**. Imported attempts: {result['imported_attempts']}; new attempts: {result['new_attempts']}.",
             f"Whitespace-normalized responses: {result['whitespace_normalized_responses']}. Raw responses are unchanged. Strict scores are retained in answers.csv and summary.json.",
             "This amendment was made after seeing the first six V1 calls. These are reused responses, not an independent rerun.", "",
             "## Sampling check", "", f"Decision: {result['sampling_gate']['status']}. Direct correct: {result['sampling_gate']['direct_correct']}/24; visible correct: {result['sampling_gate']['visible_correct']}/24.",
             "The original source replay status is preserved; this study compares fresh continuation distributions.", "",
             "## Target-record-line contrast", "", "Positive values favor retaining the line. Whole-world descriptive intervals only.", "",
             "| Subset (lexical) | After minus before | 95% interval | Complete / eligible worlds | Eligible cases |",
             "|---|---:|---|---:|---:|"]
    for c in result["target_record_line_contrasts"]:
        lines.append(f"| {c['subset']} | {_rate(c['mean'])} | {c['descriptive_cluster_bootstrap_95_ci']} | {c['n_worlds']}/{c['eligible_worlds']} | {c['eligible_cases']} |")
    lines += ["", "## All trajectories", "", "Each checkpoint has six planned draws. Adjacent changes are exploratory and may be sampling noise. Exact retained blocks are in preview.md and summary.json.", ""]
    for trace in result["trajectories"]:
        lines += [f"### {trace['case_id']}", "", f"Recorded: {trace['expected']}; pattern: {trace['pattern_label']}; saved parent answer: {trace['parent_answer']}.", "",
                  "| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |",
                  "|---|---:|---|---:|---:|---:|---:|---:|"]
        for p in trace["checkpoints"]:
            lines.append(f"| {p['id']} | {p['cut_chars']} | {', '.join(p['labels'])} | {p['valid']}/6 | {p['correct']} | {p['pattern']} | {_rate(p['accuracy_valid_only'])} | {_rate(p['accuracy_change_from_previous'])} |")
        lines.append("")
    lines += ["## Interpretation limits", ""] + ["- " + s for s in result["limits"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
