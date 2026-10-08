"""Paired, list-level analysis with technical failures reported separately."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import statistics

from .core import task_meta
from .storage import read_plan, load_attempts, accepted_records, write_json


def mean(values):
    return statistics.mean(values) if values else None


def interval(values, draws=10000):
    """Percentile bootstrap over independent lists (never over individual calls)."""
    if len(values) < 2:
        return None
    rng = random.Random(981723)
    estimates = sorted(mean(rng.choices(values, k=len(values))) for _ in range(draws))
    return [estimates[int(0.025 * draws)], estimates[int(0.975 * draws)]]


def summarize(plan, attempts, mode="not_run"):
    returned = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = returned.get(task["id"])
        meta = task_meta(plan, task)
        valid = record is not None and record["status"] == "complete"
        rows.append({"task_id": task["id"], **meta,
                     "status": record["status"] if record else "pending",
                     "answer": record.get("answer") if record else None,
                     "correct": int(record["answer"] == meta["expected"]) if valid else None})
    valid_rows = [r for r in rows if r["correct"] is not None]
    invalid = sum(r["status"] == "invalid" for r in rows)
    result = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "stage": plan["config"]["stage"],
        "mode": mode, "is_simulated": mode == "mock",
        "planned_calls": len(rows), "attempts": len(attempts),
        "complete_answers": len(valid_rows), "invalid_answers": invalid,
        "pending_tasks": sum(r["status"] == "pending" for r in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "complete": len(valid_rows) == len(rows), "accuracy_tables": [],
        "screen": {"decision": "incomplete", "minimum_exception_gap": 0.15,
                   "maximum_regular_gap": 0.05},
    }
    result["usage"] = {key: sum((a.get("response", {}).get("usage") or {}).get(key, 0) or 0
                                for a in attempts)
                       for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    groups = {}
    for row in rows:
        key = (row["condition"], row["round"], row["background"], row["is_exception"])
        groups.setdefault(key, []).append(row)
    for (condition, round_number, background, exception), members in groups.items():
        scored = [r["correct"] for r in members if r["correct"] is not None]
        result["accuracy_tables"].append({
            "condition": condition, "round": round_number, "background": background,
            "is_exception": exception, "n_valid": len(scored), "n_planned": len(members),
            "accuracy_valid_only": mean(scored),
        })
    list_effects = []
    diagnostic_effects = []
    for world in plan["worlds"]:
        subset = [r for r in rows if r["world_id"] == world["id"]]
        if any(r["correct"] is None for r in subset):
            continue
        if plan["config"]["stage"] == 1:
            entry = {"world_id": world["id"]}
            for category, is_exception in (("exception", True), ("regular", False)):
                for arm in ("direct", "cot"):
                    scores = [r["correct"] for r in subset if r["condition"] == arm
                              and r["round"] in (2, 3) and r["is_exception"] == is_exception]
                    entry[f"{category}_{arm}"] = mean(scores)
                entry[f"{category}_gap"] = entry[f"{category}_direct"] - entry[f"{category}_cot"]
            list_effects.append(entry)
        else:
            entry = {"world_id": world["id"]}
            for arm in ("direct", "cot", "recall", "cot_record"):
                for background in ("conflict", "support"):
                    entry[f"{arm}_{background}"] = mean([r["correct"] for r in subset
                        if r["condition"] == arm and r["background"] == background])
                entry[f"{arm}_conflict_penalty"] = entry[f"{arm}_support"] - entry[f"{arm}_conflict"]
            entry["reasoning_extra_conflict_penalty"] = (entry["cot_conflict_penalty"]
                                                         - entry["direct_conflict_penalty"])
            entry["record_rescue_in_conflict"] = entry["cot_record_conflict"] - entry["cot_conflict"]
            diagnostic_effects.append(entry)
    result["paired_lists"] = len(list_effects or diagnostic_effects)
    result["list_effects"] = list_effects or diagnostic_effects
    if plan["config"]["stage"] == 1:
        for category in ("exception", "regular"):
            differences = [r[f"{category}_gap"] for r in list_effects]
            result[category] = {
                "direct_accuracy": mean([r[f"{category}_direct"] for r in list_effects]),
                "cot_accuracy": mean([r[f"{category}_cot"] for r in list_effects]),
                "direct_minus_cot": mean(differences), "paired_bootstrap_95_ci": interval(differences)}
        if invalid:
            result["screen"]["decision"] = "technical_failure"
        elif result["complete"]:
            if len(list_effects) < 20:
                decision = "insufficient_lists"
            elif (result["exception"]["direct_minus_cot"] >= 0.15 - 1e-12
                  and result["regular"]["direct_minus_cot"] <= 0.05 + 1e-12):
                decision = "eligible_for_diagnostics"
            else:
                decision = "stop_this_screen"
            result["screen"]["decision"] = decision
    else:
        result["screen"] = None
        result["diagnostics"] = {}
        for key in ("reasoning_extra_conflict_penalty", "record_rescue_in_conflict"):
            values = [r[key] for r in diagnostic_effects]
            result["diagnostics"][key] = {"mean": mean(values), "paired_bootstrap_95_ci": interval(values)}
    result["interpretation"] = (
        "SIMULATED software test: no scientific evidence." if mode == "mock" else
        "Exploratory screen only. The 15 pp / 5 pp gate is a budget decision, not a significance test. "
        "Bootstrap intervals are descriptive and the small pilot can miss modest effects. "
        "A stop decision does not establish absence of the phenomenon.")
    return result, rows


def pct(value):
    return "—" if value is None else f"{100 * value:.1f}%"


def write_summary(output):
    output = Path(output)
    plan = read_plan(output)
    execution_path = output / "execution.json"
    execution = json.loads(execution_path.read_text()) if execution_path.exists() else {}
    summary, rows = summarize(plan, load_attempts(output, plan), execution.get("mode", "not_run"))
    write_json(output / "summary.json", summary)
    with (output / "scores.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Exception pilot results" + (" — SIMULATED" if summary["is_simulated"] else ""), "",
             f"Stage: {summary['stage']}; model: `{summary['model']}`; mode: {summary['mode']}.", "",
             f"Valid answers: {summary['complete_answers']}/{summary['planned_calls']}; "
             f"invalid: {summary['invalid_answers']}; provider errors: {summary['provider_errors']}; "
             f"attempts: {summary['attempts']}.", "",
             f"Complete independent lists/pairs: {summary['paired_lists']}.", "",
             summary["interpretation"], ""]
    if summary["stage"] == 1:
        lines += [f"Screen decision: **{summary['screen']['decision']}**.", "",
                  "| Passes 2–3 | Direct | Reasoned | Direct − reasoned | 95% list bootstrap |",
                  "|---|---:|---:|---:|---|"]
        for category in ("exception", "regular"):
            stat = summary[category]
            ci = stat["paired_bootstrap_95_ci"]
            ci_text = "—" if ci is None else f"[{pct(ci[0])}, {pct(ci[1])}]"
            lines.append(f"| {category} | {pct(stat['direct_accuracy'])} | {pct(stat['cot_accuracy'])} "
                         f"| {pct(stat['direct_minus_cot'])} | {ci_text} |")
    else:
        lines += ["| Diagnostic | Mean | 95% pair bootstrap |", "|---|---:|---|"]
        for name, stat in summary["diagnostics"].items():
            ci = stat["paired_bootstrap_95_ci"]
            ci_text = "—" if ci is None else f"[{pct(ci[0])}, {pct(ci[1])}]"
            lines.append(f"| {name} | {pct(stat['mean'])} | {ci_text} |")
        lines += ["", "Recall and classification use separate prompts. A recall/classification gap alone "
                  "does not demonstrate active rejection of an internally represented fact. "
                  "The repeated-record arm adds salience and text; it is not a uniquely identified mechanism."]
    lines += ["", "Per-pass/background accuracy (valid answers only; check denominators):", "",
              "| Condition | Pass | Background | Target kind | Valid/planned | Accuracy |",
              "|---|---:|---|---|---:|---:|"]
    for row in summary["accuracy_tables"]:
        lines.append(f"| {row['condition']} | {row['round'] or '—'} | {row['background'] or '—'} "
                     f"| {'exception target' if row['is_exception'] else 'ordinary'} "
                     f"| {row['n_valid']}/{row['n_planned']} | {pct(row['accuracy_valid_only'])} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return summary
