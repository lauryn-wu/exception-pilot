"""Descriptive paired analysis of a post-hoc, ten-case continuation diagnostic.

The selected cases come from nine parent worlds. They are not a fresh random
sample, so cluster bootstrap intervals describe this subset rather than supply
confirmatory inference about a broader population.
"""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json


ARMS = ("original", "unavailable", "available", "gold")
LABELS = ("A", "B", "C")
CONTRASTS = {
    "available_minus_unavailable": ("available", "unavailable"),
    "available_minus_original": ("available", "original"),
    "gold_minus_available": ("gold", "available"),
    "unavailable_minus_original": ("unavailable", "original"),
}


def average(values):
    return sum(values) / len(values) if values else None


def _scorable(record):
    return bool(record is not None and record["status"] == "complete"
                and record.get("answer") in LABELS)


def replay_gate(plan, attempts):
    """Fixed feasibility check; not a significance test or scientific pass gate."""
    records = accepted_records(attempts)
    cases = {case["id"]: case for case in plan["cases"]}
    originals = [task for task in plan["tasks"] if task["arm"] == "original"]
    n_returned = sum(task["id"] in records for task in originals)
    valid = [(cases[task["case_id"]], records[task["id"]]) for task in originals
             if _scorable(records.get(task["id"]))]
    exact = sum(record["answer"] == case["original_answer"] for case, record in valid)
    n_original = len(originals)
    if n_returned < n_original:
        status = "incomplete"
    elif n_original == 10 and len(valid) == 10 and exact >= 8:
        status = "pass"
    else:
        status = "stop"
    return {
        "status": status,
        "n_planned": n_original,
        "n_returned": n_returned,
        "n_valid": len(valid),
        "n_invalid": n_returned - len(valid),
        "n_missing": n_original - n_returned,
        "exact_matches": exact,
        "original_error_retained": sum(
            not case["original_correct"] and record["answer"] != case["expected"]
            for case, record in valid),
        "original_error_exact_matches": sum(
            not case["original_correct"] and record["answer"] == case["original_answer"]
            for case, record in valid),
        "original_correct_retained": sum(
            bool(case["original_correct"]) and record["answer"] == case["expected"]
            for case, record in valid),
        "n_original_errors": sum(not cases[task["case_id"]]["original_correct"]
                                 for task in originals),
        "n_original_correct": sum(bool(cases[task["case_id"]]["original_correct"])
                                  for task in originals),
        "rule": "All 10 original continuations must be scorable; at least 8 must exactly match their saved parent answers.",
        "interpretation": "Fixed practical feasibility threshold, not statistical significance or evidence of a mechanism.",
    }


def _descriptive_interval(values):
    if len(values) < 2:
        return None
    if len(set(values)) == 1:
        return [values[0], values[0]]
    rng = random.Random(981723)
    draws = sorted(sum(rng.choices(values, k=len(values))) / len(values)
                   for _ in range(10000))
    return [draws[250], draws[9750]]


def summarize(plan, attempts, mode="not_run"):
    records = accepted_records(attempts)
    cases = {case["id"]: case for case in plan["cases"]}
    rows = []
    for task in plan["tasks"]:
        case = cases[task["case_id"]]
        record = records.get(task["id"])
        valid = _scorable(record)
        answer = record.get("answer") if record else None
        rows.append({
            "task_id": task["id"], "case_id": case["id"], "world_id": case["world_id"],
            "arm": task["arm"], "item_id": case.get("item_id"),
            "source_attempt": case.get("source_attempt"), "expected": case["expected"],
            "pattern_label": case["pattern_label"], "original_answer": case["original_answer"],
            "original_correct": int(bool(case["original_correct"])),
            "status": ("complete" if valid else "invalid") if record else "pending",
            "answer": answer, "correct": int(answer == case["expected"]) if valid else None,
            "follows_pattern": int(answer == case["pattern_label"]) if valid else None,
            "matches_original_answer": int(answer == case["original_answer"]) if valid else None,
        })
    by_case_arm = {(row["case_id"], row["arm"]): row for row in rows}
    world_cases = defaultdict(list)
    for case in plan["cases"]:
        world_cases[case["world_id"]].append(case["id"])
    n_returned = sum(row["status"] != "pending" for row in rows)
    all_returned = n_returned == len(rows)
    effects, world_metrics = {}, {wid: {} for wid in world_cases}
    for name, (lhs, rhs) in CONTRASTS.items():
        world_values, world_bounds, all_pairs = [], [], []
        for wid, ids in world_cases.items():
            differences, low, high = [], 0.0, 0.0
            for case_id in ids:
                left = by_case_arm[case_id, lhs]["correct"]
                right = by_case_arm[case_id, rhs]["correct"]
                if left is not None and right is not None:
                    diff = left - right
                    differences.append(diff)
                    all_pairs.append(diff)
                low += (0 if left is None else left) - (1 if right is None else right)
                high += (1 if left is None else left) - (0 if right is None else right)
            value = average(differences) if len(differences) == len(ids) else None
            world_metrics[wid][name] = value
            if value is not None:
                world_values.append(value)
            world_bounds.append((low / len(ids), high / len(ids)))
        effects[name] = {
            "mean": average(world_values),
            "weighting": "Equal weight per complete world after averaging its selected cases.",
            "n_worlds": len(world_values), "n_planned_worlds": len(world_cases),
            "excluded_worlds": len(world_cases) - len(world_values),
            "descriptive_cluster_bootstrap_95_ci": _descriptive_interval(world_values),
            "interval_interpretation": "Descriptive only: selected post-hoc cases; not confirmatory population inference.",
            "positive_worlds": sum(v > 0 for v in world_values),
            "zero_worlds": sum(v == 0 for v in world_values),
            "negative_worlds": sum(v < 0 for v in world_values),
            "case_weighted_mean": average(all_pairs),
            "case_weighting": "Equal weight per scorable paired case, including cases in otherwise incomplete worlds.",
            "n_paired_cases": len(all_pairs),
            "paired_improved_cases": sum(v > 0 for v in all_pairs),
            "paired_unchanged_cases": sum(v == 0 for v in all_pairs),
            "paired_worsened_cases": sum(v < 0 for v in all_pairs),
            "full_plan_unscorable_bounds": [average([b[0] for b in world_bounds]),
                                             average([b[1] for b in world_bounds])]
                                            if all_returned else None,
        }
    arm_counts = []
    for arm in ARMS:
        members = [row for row in rows if row["arm"] == arm]
        valid = [row for row in members if row["correct"] is not None]
        world_accuracy = []
        for ids in world_cases.values():
            values = [by_case_arm[case_id, arm]["correct"] for case_id in ids]
            if all(value is not None for value in values):
                world_accuracy.append(average(values))
        arm_counts.append({
            "arm": arm, "n_planned": len(members), "n_returned": sum(r["status"] != "pending" for r in members),
            "n_valid": len(valid), "n_invalid": sum(r["status"] == "invalid" for r in members),
            "n_missing": sum(r["status"] == "pending" for r in members),
            "n_correct": sum(row["correct"] for row in valid),
            "accuracy_valid_only_case_weighted": average([row["correct"] for row in valid]),
            "accuracy_complete_world_weighted": average(world_accuracy),
            "n_complete_worlds": len(world_accuracy),
            "n_pattern_choices": sum(row["follows_pattern"] for row in valid),
            "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in LABELS},
        })
    gate = replay_gate(plan, attempts)
    n_invalid = sum(row["status"] == "invalid" for row in rows)
    status = "complete_ready_for_interpretation" if all_returned else "incomplete"
    if all_returned and n_invalid:
        status = "complete_with_unscorable_answers"
    if gate["status"] == "stop":
        status = "replay_gate_failed_stop"
    if any(record.get("response", {}).get("complete") is False for record in records.values()):
        status = "technical_failure"
    if mode == "mock":
        status = "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE"
    comparisons = []
    for case in plan["cases"]:
        row = by_case_arm[case["id"], "original"]
        comparisons.append({
            "case_id": case["id"], "world_id": case["world_id"],
            "expected": case["expected"], "original_answer": case["original_answer"],
            "original_correct": bool(case["original_correct"]),
            "replay_answer": row["answer"], "replay_status": row["status"],
            "replay_correct": row["correct"], "exact_match": row["matches_original_answer"],
        })
    summary = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "analysis_status": status, "planned_calls": len(rows), "attempts": len(attempts),
        "max_total_attempts": plan["config"]["max_total_attempts"],
        "returned_answers": n_returned, "valid_answers": n_returned - n_invalid,
        "invalid_answers": n_invalid, "pending_tasks": len(rows) - n_returned,
        "provider_errors": sum(attempt["status"] == "error" for attempt in attempts),
        "n_selected_cases": len(cases), "n_selected_worlds": len(world_cases),
        "selection": "Post-hoc diagnostic: 10 cases selected from 9 parent worlds. This is not an independent confirmation set.",
        "primary_effect": "available_minus_unavailable", "replay_gate": gate,
        "effects": effects, "arm_counts": arm_counts, "original_vs_replay": comparisons,
        "world_metrics": [{"world_id": wid, "n_cases": len(world_cases[wid]), "metrics": metrics}
                          for wid, metrics in world_metrics.items()],
        "answers": rows,
        "uncertainty": "10,000 whole-world bootstrap resamples, seed 981723, descriptive unadjusted 95% intervals only. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.",
        "usage": {key: sum((attempt.get("response", {}).get("usage") or {}).get(key, 0) or 0
                           for attempt in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
    }
    return summary, rows


def _number(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    # Keep this import local because the runner calls the analysis functions.
    from .runner import read_run

    output = Path(output)
    plan, execution, attempts = read_run(output)
    report, rows = summarize(plan, attempts, execution["mode"] if execution else "not_run")
    write_json(output / "summary.json", report)
    with (output / "answers.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    gate = report["replay_gate"]
    lines = ["# Target-record availability: selected-case diagnostic", "",
             f"Status: **{report['analysis_status']}**", "",
             f"{report['returned_answers']}/{report['planned_calls']} returned; "
             f"{report['valid_answers']} valid; {report['invalid_answers']} unscorable.", "",
             report["selection"], "",
             "Results describe this selected subset. They cannot establish prevalence, an internal mechanism, "
             "or novelty. Do not treat the 40 calls as 40 independent observations.", "",
             "## Replay feasibility check", "",
             f"Decision: **{gate['status']}**. Exact parent-answer matches: "
             f"{gate['exact_matches']}/{gate['n_planned']}; scorable: {gate['n_valid']}; "
             f"invalid: {gate['n_invalid']}; missing: {gate['n_missing']}.", "",
             gate["rule"], gate["interpretation"], "",
             "## Paired contrasts", "",
             "Positive values favor the first arm. The primary contrast is available minus unavailable. "
             "Cases are averaged within each parent world before giving each complete world equal weight.", "",
             "| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Case-weighted mean |",
             "|---|---:|---|---:|---:|"]
    for name, result in report["effects"].items():
        ci = result["descriptive_cluster_bootstrap_95_ci"]
        interval = "—" if ci is None else f"[{_number(ci[0])}, {_number(ci[1])}]"
        lines.append(f"| {name} | {_number(result['mean'])} | {interval} | "
                     f"{result['n_worlds']}/{result['n_planned_worlds']} | "
                     f"{_number(result['case_weighted_mean'])} |")
    lines += ["", report["uncertainty"], "",
              "Each contrast excludes a world if any selected case lacks a scorable answer in either required arm. "
              "Case-weighted estimates use all scorable pairs. The JSON also records exclusions, paired improvement/worsening counts, "
              "and full-plan bounds after all planned responses have returned.", "",
              "## Arm counts", "", "| Arm | Valid / planned | Correct | Case-weighted accuracy | Pattern choices |",
              "|---|---:|---:|---:|---:|"]
    for row in report["arm_counts"]:
        lines.append(f"| {row['arm']} | {row['n_valid']}/{row['n_planned']} | {row['n_correct']} | "
                     f"{_number(row['accuracy_valid_only_case_weighted'])} | {row['n_pattern_choices']} |")
    by_case_arm = {(row["case_id"], row["arm"]): row for row in rows}
    lines += ["", "## All selected cases", "",
              "| Case | Gold | Parent answer | Replay | Unavailable | Available | Gold continuation |",
              "|---|---|---|---|---|---|---|"]
    for case in plan["cases"]:
        cells = []
        for arm in ARMS:
            row = by_case_arm[case["id"], arm]
            cells.append(str(row["answer"]) if row["status"] == "complete" else row["status"])
        lines.append(f"| {case['id']} | {case['expected']} | {case['original_answer']} | "
                     + " | ".join(cells) + " |")
    lines += ["", "The saved parent answer is descriptive; causal arm comparisons use the new original replay. "
              "A replay feasibility pass only permits the fixed diagnostic to continue. It is not a scientific finding.", ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
