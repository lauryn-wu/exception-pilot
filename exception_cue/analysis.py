"""Paired world-level analysis of reasoning cues and written-output requirements.

Final-answer parseability and output-contract compliance are separate outcomes.
All parseable final answers contribute, including noncompliant outputs.
"""

from __future__ import annotations

import csv
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, LABELS, VALUES, task_meta


CONTRASTS = {
    "direct_minus_cue": ("direct", "cue"),
    "cue_minus_visible": ("cue", "visible"),
    "direct_minus_visible": ("direct", "visible"),
}
CO_PRIMARY = ("accuracy/direct_minus_cue", "accuracy/cue_minus_visible")


def average(values):
    return sum(values) / len(values) if values else None


def effect(values):
    """Unadjusted percentile intervals resample entire independent worlds."""
    interval = None
    if len(values) >= 2:
        if len(set(values)) == 1:
            interval = [values[0], values[0]]
        else:
            rng = random.Random(981723)
            draws = sorted(sum(rng.choices(values, k=len(values))) / len(values)
                           for _ in range(10000))
            interval = [draws[250], draws[9750]]
    return {
        "mean": average(values), "descriptive_cluster_bootstrap_95_ci": interval,
        "n_worlds": len(values), "positive_worlds": sum(value > 0 for value in values),
        "zero_worlds": sum(value == 0 for value in values),
        "negative_worlds": sum(value < 0 for value in values),
    }


def _terms(by_cell, world_id, metric, arms):
    terms = []
    for arm, sign in arms:
        for value in VALUES:
            row = by_cell[world_id, value, arm]
            possibilities = {}
            for label in LABELS:
                if metric == "accuracy":
                    score = 0.5 * int(label == row["expected"])
                else:
                    score = (0.5 if label == row["expected"] else
                             0.0 if label == row["pattern_label"] else -0.5)
                possibilities[label] = sign * score
            terms.append((row, possibilities))
    return terms


def summarize(plan, attempts, mode="live"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"])
        meta = task_meta(plan, task)
        answer = record.get("answer") if record else None
        valid = bool(record is not None and record["status"] == "complete" and answer in LABELS)
        rows.append({
            "task_id": task["id"], **meta,
            "status": ("complete" if valid else "invalid") if record else "pending",
            "answer": answer,
            "correct": int(answer == meta["expected"]) if valid else None,
            "follows_pattern": int(answer == meta["pattern_label"]) if valid else None,
            "answer_only": record.get("answer_only") if record else None,
            "pre_answer_text": record.get("pre_answer_text") if record else None,
            "output_contract_met": record.get("output_contract_met") if record else None,
        })
    by_cell = {(row["world_id"], row["value"], row["arm"]): row for row in rows}
    world_ids = [world["id"] for world in plan["worlds"]]
    n_returned = sum(row["status"] != "pending" for row in rows)
    all_returned = n_returned == len(rows)
    specifications = {}
    for metric in ("accuracy", "record_sensitivity"):
        for contrast, (left, right) in CONTRASTS.items():
            specifications[f"{metric}/{contrast}"] = (metric, ((left, 1), (right, -1)))
        for arm in ARMS:
            specifications[f"{metric}/{arm}"] = (metric, ((arm, 1),))
    effects = {}
    world_metrics = {wid: {} for wid in world_ids}
    for name, (metric, arms) in specifications.items():
        values, bounds, excluded, unscorable_tasks = [], [], [], []
        n_scorable = 0
        for wid in world_ids:
            terms = _terms(by_cell, wid, metric, arms)
            scores, low, high = [], 0.0, 0.0
            for row, possibilities in terms:
                if row["status"] == "complete":
                    score = possibilities[row["answer"]]
                    scores.append(score)
                    low += score
                    high += score
                    n_scorable += 1
                else:
                    low += min(possibilities.values())
                    high += max(possibilities.values())
                    unscorable_tasks.append(row["task_id"])
            value = sum(scores) if len(scores) == len(terms) else None
            world_metrics[wid][name] = value
            if value is None:
                excluded.append(wid)
            else:
                values.append(value)
            bounds.append((low, high))
        effects[name] = {
            **effect(values),
            "role": ("co_primary" if name in CO_PRIMARY else
                     "baseline_replication" if name == "accuracy/direct_minus_visible" else
                     "secondary" if metric == "record_sensitivity" else "descriptive"),
            "weighting": "Equal weight per complete world; accuracy averages its two recorded-class variants.",
            "n_planned_worlds": len(world_ids), "excluded_worlds": len(excluded),
            "excluded_world_ids": excluded, "n_required_answers": len(world_ids) * len(VALUES) * len(arms),
            "n_scorable_answers": n_scorable, "unscorable_or_pending_task_ids": unscorable_tasks,
            "full_plan_unscorable_bounds": [average([bound[0] for bound in bounds]),
                                             average([bound[1] for bound in bounds])]
                                            if all_returned else None,
        }
    for name, (left, right) in CONTRASTS.items():
        paired = []
        for wid in world_ids:
            for value in VALUES:
                lhs, rhs = by_cell[wid, value, left]["correct"], by_cell[wid, value, right]["correct"]
                if lhs is not None and rhs is not None:
                    paired.append(lhs - rhs)
        effects[f"accuracy/{name}"].update({
            "case_weighted_mean": average(paired), "n_paired_cases": len(paired),
            "paired_improved_cases": sum(value > 0 for value in paired),
            "paired_unchanged_cases": sum(value == 0 for value in paired),
            "paired_worsened_cases": sum(value < 0 for value in paired),
            "case_weighting": "All scorable paired variants, including those in otherwise incomplete worlds.",
        })
    arm_counts, pair_counts = [], []
    for arm in ARMS:
        members = [row for row in rows if row["arm"] == arm]
        returned = [row for row in members if row["status"] != "pending"]
        valid = [row for row in members if row["status"] == "complete"]
        counts = {
            "arm": arm, "n_planned": len(members), "n_returned": len(returned), "n_valid": len(valid),
            "n_invalid": len(returned) - len(valid), "n_pending": len(members) - len(returned),
            "n_correct": sum(row["correct"] for row in valid),
            "accuracy_valid_only_case_weighted": average([row["correct"] for row in valid]),
            "accuracy_complete_world_weighted": effects[f"accuracy/{arm}"]["mean"],
            "n_complete_worlds": effects[f"accuracy/{arm}"]["n_worlds"],
            "n_pattern_choices": sum(row["follows_pattern"] for row in valid),
            "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in LABELS},
        }
        for field in ("answer_only", "pre_answer_text", "output_contract_met"):
            counts[f"n_{field}"] = sum(row[field] is True for row in returned)
            counts[f"n_{field}_false"] = sum(row[field] is False for row in returned)
            counts[f"n_{field}_unknown"] = sum(row[field] is None for row in returned)
        counts["n_valid_noncompliant"] = sum(row["output_contract_met"] is False for row in valid)
        counts["n_valid_with_pre_answer_text"] = sum(row["pre_answer_text"] is True for row in valid)
        arm_counts.append(counts)
        pairs = [[by_cell[wid, value, arm] for value in VALUES] for wid in world_ids]
        complete_pairs = [pair for pair in pairs if all(row["status"] == "complete" for row in pair)]
        pair_counts.append({
            "arm": arm, "n_complete_worlds": len(complete_pairs),
            "n_both_correct": sum(all(row["correct"] for row in pair) for pair in complete_pairs),
            "n_exactly_one_correct": sum(sum(row["correct"] for row in pair) == 1 for pair in complete_pairs),
            "n_both_wrong": sum(not any(row["correct"] for row in pair) for pair in complete_pairs),
            "n_answer_changed": sum(pair[0]["answer"] != pair[1]["answer"] for pair in complete_pairs),
            "n_answer_unchanged": sum(pair[0]["answer"] == pair[1]["answer"] for pair in complete_pairs),
            "n_pattern_both": sum(all(row["follows_pattern"] for row in pair) for pair in complete_pairs),
        })
    n_invalid = sum(row["status"] == "invalid" for row in rows)
    status = "complete_ready_for_interpretation" if all_returned else "incomplete"
    if all_returned and n_invalid:
        status = "complete_with_unscorable_answers"
    if any(record.get("response", {}).get("complete") is False for record in records.values()):
        status = "technical_failure"
    if mode == "mock":
        status = "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE"
    report = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "analysis_status": status, "planned_calls": len(rows), "attempts": len(attempts),
        "max_total_attempts": plan["config"]["max_total_attempts"],
        "returned_answers": n_returned, "valid_answers": n_returned - n_invalid,
        "invalid_answers": n_invalid, "pending_tasks": len(rows) - n_returned,
        "provider_errors": sum(attempt["status"] == "error" for attempt in attempts),
        "n_planned_worlds": len(world_ids), "co_primary_effects": list(CO_PRIMARY),
        "baseline_effect": "accuracy/direct_minus_visible", "analysis_plan": plan.get("analysis_plan"),
        "effects": effects, "arm_counts": arm_counts, "record_pair_counts": pair_counts,
        "world_metrics": [{"world_id": wid, "metrics": metrics} for wid, metrics in world_metrics.items()],
        "answers": rows,
        "uncertainty": "10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. The independent unit is the world, not an API call. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.",
        "interpretation": "This fixed diagnostic compares prompt instructions and output requirements. The cue arm does not establish that hidden reasoning occurred; pre-answer text is not evidence of faithful internal reasoning. A cue-versus-visible difference does not uniquely identify self-conditioning. If contemporaneous direct-versus-visible harm is not reproduced, this run cannot locate the source of the earlier harm. No automatic scientific pass gate or sample extension is applied.",
        "usage": {key: sum((attempt.get("response", {}).get("usage") or {}).get(key, 0) or 0
                           for attempt in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
    }
    return report, rows


def _number(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output, plan=None, attempts=None, mode="live"):
    """Write an audited saved run, or already-validated plan and attempts."""
    output = Path(output)
    if plan is None:
        from .runner import read_run
        plan, execution, attempts = read_run(output)
        mode = execution["mode"] if execution else "not_run"
    elif attempts is None:
        raise ValueError("Attempts are required when a plan is supplied")
    report, rows = summarize(plan, attempts, mode)
    write_json(output / "summary.json", report)
    with (output / "answers.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Reasoning cue and written-output diagnostic", "",
             f"Status: **{report['analysis_status']}**", "",
             f"{report['returned_answers']}/{report['planned_calls']} returned; "
             f"{report['valid_answers']} parseable final answers; {report['invalid_answers']} unscorable.", "",
             f"The fixed sample contains {report['n_planned_worlds']} fresh worlds. Partial results must not determine "
             "whether to extend collection. Parseable final answers remain in the analysis regardless of output compliance.", "",
             "## Paired accuracy contrasts", "",
             "The co-primary contrasts are direct minus cue and cue minus visible. Direct minus visible is the "
             "contemporaneous baseline replication. Positive values favor the first arm. Each world first averages "
             "its two target-cell variants, then each complete world receives equal weight.", "",
             "| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |",
             "|---|---:|---|---:|---:|"]
    for name in CONTRASTS:
        stats = report["effects"][f"accuracy/{name}"]
        interval = stats["descriptive_cluster_bootstrap_95_ci"]
        text = "—" if interval is None else f"[{_number(interval[0])}, {_number(interval[1])}]"
        lines.append(f"| {name} | {_number(stats['mean'])} | {text} | {stats['n_worlds']}/{stats['n_planned_worlds']} | "
                     f"{stats['paired_improved_cases']} / {stats['paired_worsened_cases']} |")
    lines += ["", report["uncertainty"], "",
              "Each contrast excludes a world if any required answer is unscorable or pending. The JSON records exact "
              "excluded worlds and task IDs, all scorable paired-case counts, and full-plan bounds once every planned "
              "response has returned. Paired-case counts can include a scorable case from an otherwise incomplete world.", "",
              "## Answer and output-compliance counts", "",
              "| Arm | Parseable / planned | Correct | Accuracy among parseable | Pre-answer text / returned | Answer only / returned | Contract met / returned |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["arm_counts"]:
        lines.append(f"| {row['arm']} | {row['n_valid']}/{row['n_planned']} | {row['n_correct']} | "
                     f"{_number(row['accuracy_valid_only_case_weighted'])} | {row['n_pre_answer_text']}/{row['n_returned']} | "
                     f"{row['n_answer_only']}/{row['n_returned']} | {row['n_output_contract_met']}/{row['n_returned']} |")
    lines += ["", "Pre-answer text records the presence of text, not whether that text is a meaningful or faithful "
              "explanation. Missing/unknown compliance flags are counted separately in the JSON. If cue outputs contain "
              "pre-answer text, their errors cannot demonstrate harm in the absence of generated explanation. If visible "
              "outputs omit text, the intended output manipulation was not fully followed. No format-based exclusion or retry is applied.", "",
              "## Secondary record sensitivity", "",
              "| Effect | Mean | Descriptive 95% interval | Complete worlds |", "|---|---:|---|---:|"]
    for name, stats in report["effects"].items():
        if not name.startswith("record_sensitivity/"):
            continue
        interval = stats["descriptive_cluster_bootstrap_95_ci"]
        text = "—" if interval is None else f"[{_number(interval[0])}, {_number(interval[1])}]"
        lines.append(f"| {name.removeprefix('record_sensitivity/')} | {_number(stats['mean'])} | {text} | "
                     f"{stats['n_worlds']}/{stats['n_planned_worlds']} |")
    lines += ["", "For each world, each correctly followed target label contributes +0.5, the other target label −0.5, "
              "and the background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. "
              "An unchanged answer across the two target-cell values scores 0. Changed answers alone do not establish "
              "record retrieval: the edit also changes table-level label counts, and each cell has one sampled completion.", "",
              report["interpretation"], ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
