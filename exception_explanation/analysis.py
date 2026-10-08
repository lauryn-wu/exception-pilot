"""Paired whole-world estimates; missing class is never assigned a gold answer."""

from __future__ import annotations

import csv
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, COPY_ARMS, LABELS, VALUES, task_meta


def average(values):
    return sum(values) / len(values) if values else None


def effect(values):
    interval = None
    if len(values) >= 2:
        if len(set(values)) == 1:
            interval = [values[0], values[0]]
        else:
            rng = random.Random(981723)
            draws = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(10000))
            interval = [draws[250], draws[9750]]
    return {"mean": average(values), "paired_bootstrap_95_ci": interval,
            "n_worlds": len(values), "positive_worlds": sum(v > 0 for v in values),
            "zero_worlds": sum(v == 0 for v in values), "negative_worlds": sum(v < 0 for v in values)}


def metric_terms(world):
    """Linear scores of categorical answers make unscorable-answer bounds explicit."""
    roles, wid = world["roles"], world["id"]

    def sensitivity(arm, sign=1):
        return [(f"{wid}/{value}/{arm}", {
            label: sign * (0.5 if label == roles[value] else -0.5 if label != roles["pattern"] else 0)
            for label in LABELS}) for value in VALUES[:2]]

    def accuracy(arm, sign=1):
        return [(f"{wid}/{value}/{arm}", {label: sign * 0.5 * int(label == roles[value])
                                         for label in LABELS}) for value in VALUES[:2]]

    def pattern(arm, value, weight):
        return (f"{wid}/{value}/{arm}", {label: weight * int(label == roles["pattern"])
                                        for label in LABELS})

    gold = world["labels"]["conflict"][world["target_index"]]
    terms = {
        "record_sensitivity/direct_minus_cot": sensitivity("direct") + sensitivity("cot", -1),
        "record_sensitivity/copy_class_minus_copy_marker": sensitivity("copy_class") + sensitivity("copy_marker", -1),
        "visible_accuracy/copy_class_minus_copy_marker": accuracy("copy_class") + accuracy("copy_marker", -1),
        "visible_accuracy/priority_minus_cot": accuracy("priority") + accuracy("cot", -1),
        "visible_pattern/cot_minus_direct": [pattern("cot", v, 0.5) for v in VALUES[:2]]
                                             + [pattern("direct", v, -0.5) for v in VALUES[:2]],
        "pattern/cot_missing_minus_visible": [pattern("cot", "missing", 1)]
                                             + [pattern("cot", v, -0.5) for v in VALUES[:2]],
        "anchor_accuracy/direct_minus_cot": [
            (f"{wid}/anchor/{arm}", {label: sign * int(label == gold) for label in ("A", "B")})
            for arm, sign in (("direct", 1), ("cot", -1))],
    }
    for arm in ARMS:
        terms[f"record_sensitivity/{arm}"] = sensitivity(arm)
    return terms


def summarize(plan, attempts, mode="not_run"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"])
        meta = task_meta(plan, task)
        answer = record.get("answer") if record else None
        valid = record is not None and record["status"] == "complete"
        copy_valid = record.get("copy_valid") if record else None
        copied = record.get("copied") if record else None
        rows.append({"task_id": task["id"], **meta, "status": record["status"] if record else "pending",
                     "answer": answer, "copied": copied, "copy_valid": copy_valid,
                     "copy_correct": int(copied == meta["copy_expected"]) if copy_valid else None,
                     "correct": int(answer == meta["expected"]) if valid and meta["expected"] is not None else None,
                     "follows_pattern": int(answer == meta["pattern_label"]) if valid else None})
    by_id = {r["task_id"]: r for r in rows}
    all_returned = len(records) == len(rows)
    world_values, all_bounds, estimates = [], {}, {}
    for world in plan["worlds"]:
        values = {}
        for metric, terms in metric_terms(world).items():
            scores, low, high = [], 0, 0
            for task_id, possibilities in terms:
                answer = by_id[task_id]["answer"]
                valid = by_id[task_id]["status"] == "complete"
                if valid:
                    score = possibilities[answer]
                    scores.append(score)
                    low += score
                    high += score
                else:
                    low += min(possibilities.values())
                    high += max(possibilities.values())
            values[metric] = sum(scores) if len(scores) == len(terms) else None
            all_bounds.setdefault(metric, []).append((low, high))
        world_values.append({"world_id": world["id"], "metrics": values})
    for metric in all_bounds:
        values = [w["metrics"][metric] for w in world_values if w["metrics"][metric] is not None]
        estimates[metric] = {**effect(values), "excluded_worlds": len(plan["worlds"]) - len(values),
            "full_plan_unscorable_bounds": ([average([b[0] for b in all_bounds[metric]]),
                                             average([b[1] for b in all_bounds[metric]])]
                                            if all_returned else None)}
    tables = []
    groups = [("anchor", "binary", arm) for arm in ("direct", "cot")]
    groups += [("diagnostic", value, arm) for value in VALUES for arm in ARMS
               if not (value == "missing" and arm == "priority")]
    for family, value, arm in groups:
        members = [r for r in rows if (r["family"], r["value"], r["arm"]) == (family, value, arm)]
        valid = [r for r in members if r["status"] == "complete"]
        scored = [r["correct"] for r in valid if r["correct"] is not None]
        tables.append({"family": family, "value": value, "arm": arm, "n_planned": len(members),
            "n_valid": len(valid), "n_invalid": sum(r["status"] == "invalid" for r in members),
            "n_correct": sum(scored) if scored else None, "accuracy_valid_only": average(scored),
            "pattern_choice_valid_only": average([r["follows_pattern"] for r in valid]),
            "answer_counts": {label: sum(r["answer"] == label for r in valid) for label in LABELS}})
    copies = []
    for arm in COPY_ARMS:
        for value_group in ("visible", "missing"):
            subset = [r for r in rows if r["arm"] == arm
                      and ((r["value"] == "missing") == (value_group == "missing"))]
            copies.append({"arm": arm, "value_group": value_group, "n_planned": len(subset),
                "n_returned": sum(r["status"] != "pending" for r in subset),
                "n_copy_correct": sum(r["copy_correct"] == 1 for r in subset),
                "n_copy_wrong": sum(r["copy_correct"] == 0 for r in subset),
                "n_copy_unparseable": sum(r["copy_valid"] is False for r in subset),
                "n_final_unparseable": sum(r["status"] == "invalid" for r in subset),
                "joint_visible_counts": None if value_group == "missing" else {
                    f"copy_{c}/answer_{a}": sum(r["copy_correct"] == c and r["correct"] == a for r in subset)
                    for c in (0, 1) for a in (0, 1)}})
    n_invalid = sum(r["status"] == "invalid" for r in rows)
    status = "complete_ready_for_interpretation" if all_returned else "incomplete"
    if all_returned and n_invalid:
        status = "complete_with_unscorable_answers"
    if any(not r["response"]["complete"] for r in records.values()):
        status = "technical_failure"
    if mode == "mock":
        status = "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE"
    result = {"protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "analysis_status": status, "planned_calls": len(rows), "attempts": len(attempts),
        "max_total_attempts": plan["config"]["max_total_attempts"], "returned_answers": len(records),
        "valid_answers": sum(r["status"] == "complete" for r in rows), "invalid_answers": n_invalid,
        "pending_tasks": len(rows) - len(records),
        "copy_format_issues": sum(r["copy_valid"] is False for r in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts),
        "analysis_plan": plan["analysis_plan"], "effects": estimates, "answer_tables": tables,
        "copy_tables": copies, "world_metrics": world_values,
        "usage": {key: sum((a.get("response", {}).get("usage") or {}).get(key, 0) or 0 for a in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")}}
    return result, rows


def number(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    # Local import avoids a runner/analysis import cycle.
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    report, rows = summarize(plan, attempts, execution["mode"] if execution else "not_run")
    write_json(output / "summary.json", report)
    with (output / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Record sensitivity and evidence use", "", f"Status: **{report['analysis_status']}**", "",
        f"{report['returned_answers']}/{report['planned_calls']} returned; {report['invalid_answers']} "
        f"unscorable final answers; {report['copy_format_issues']} copy-format issues.", "",
        "Do not interpret partial results to decide whether to extend collection. The planned unit is "
        "24 independent worlds, not 384 independent observations.", "",
        "## Prespecified effects", "", "| Effect | Estimate | 95% interval | Complete worlds |",
        "|---|---:|---|---:|"]
    for key, stats in report["effects"].items():
        ci = stats["paired_bootstrap_95_ci"]
        interval = "—" if ci is None else f"[{number(ci[0])}, {number(ci[1])}]"
        lines.append(f"| {key} | {number(stats['mean'])} | {interval} | {stats['n_worlds']}/24 |")
    lines += ["", "Record sensitivity ranges from −1 (both labels reversed) to +1 (both followed). "
              "An unchanged answer across target-cell edits scores 0. The primary effect is direct "
              "minus CoT sensitivity; the key secondary is class-copy minus marker-copy sensitivity.", "",
              "Intervals are exploratory and unadjusted; a constant observed score can have a "
              "degenerate bootstrap interval without establishing certainty or equivalence. "
              "Per-effect full-plan bounds for unscorable answers are in summary.json; they are not CIs.", "",
              "## Answers", "", "| Family | Target cell | Arm | Valid | Accuracy | Pattern choice |",
              "|---|---|---|---:|---:|---:|"]
    for row in report["answer_tables"]:
        lines.append(f"| {row['family']} | {row['value']} | {row['arm']} | {row['n_valid']}/24 | "
                     f"{number(row['accuracy_valid_only'])} | {number(row['pattern_choice_valid_only'])} |")
    lines += ["", "MISSING has no individual ground-truth label. Pattern choice on missing cases "
              "is a descriptive outcome, not accuracy. Final answers in copy arms are scored "
              "regardless of copy success; correct-copy subgroups are descriptive only.", "",
              "## Copy and final-answer joint counts", "", "```json"]
    import json
    lines += [json.dumps(report["copy_tables"], indent=2), "```", "",
              "The original-format binary anchor diagnoses loss of the original effect. If the "
              "anchor shows harm but the ternary baseline does not, this is a task-format boundary. "
              "This study cannot identify an internal mechanism from narrated reasoning or prove novelty.", ""]
    (output / "summary.md").write_text("\n".join(lines))
    return report
