"""Paired list analysis of the independent counterfactual diagnostic."""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

from exception_pilot.analysis import interval, mean, pct
from exception_pilot.core import parse_answer
from exception_pilot.storage import accepted_records, load_attempts, write_json

from .core import ARMS, BACKGROUNDS, read_plan, task_meta


def summarize(plan, attempts, mode="not_run"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"])
        meta = task_meta(plan, task)
        valid = record is not None and record["status"] == "complete"
        answer = record.get("answer") if record else None
        if valid and (not record["response"]["complete"] or answer not in ("A", "B")
                      or answer != parse_answer(record["response"]["text"])):
            raise ValueError("Stored answer disagrees with returned content; inspect the attempt journal")
        rows.append({"task_id": task["id"], **meta,
                     "status": record["status"] if record else "pending",
                     "answer": answer, "correct": int(answer == meta["expected"]) if valid else None})
    list_effects = []
    transitions = {arm: Counter() for arm in ARMS}
    for world in plan["worlds"]:
        subset = [r for r in rows if r["world_id"] == world["id"]]
        if any(r["correct"] is None for r in subset):
            continue
        entry = {"world_id": world["id"]}
        for arm in ARMS:
            for background in BACKGROUNDS:
                entry[f"{arm}_{background}"] = mean([r["correct"] for r in subset
                    if r["condition"] == arm and r["background"] == background])
            entry[f"{arm}_conflict_penalty"] = entry[f"{arm}_support"] - entry[f"{arm}_conflict"]
            for index in world["target_indices"]:
                pair = {r["background"]: r["correct"] for r in subset
                        if r["condition"] == arm and r["item_id"] == world["items"][index]["id"]}
                transitions[arm][f"{pair['support']}_to_{pair['conflict']}"] += 1
        entry["extra_conflict_penalty"] = entry["cot_conflict_penalty"] - entry["direct_conflict_penalty"]
        list_effects.append(entry)
    effects = {}
    for key in ("direct_conflict_penalty", "cot_conflict_penalty", "extra_conflict_penalty"):
        values = [entry[key] for entry in list_effects]
        effects[key] = {"mean": mean(values), "paired_bootstrap_95_ci": interval(values),
                        "positive_lists": sum(v > 0 for v in values),
                        "zero_lists": sum(v == 0 for v in values),
                        "negative_lists": sum(v < 0 for v in values)}
    paired_accuracy = {f"{arm}_{background}": mean([e[f"{arm}_{background}"] for e in list_effects])
                       for arm in ARMS for background in BACKGROUNDS}
    accuracy_tables = []
    for arm in ARMS:
        for background in BACKGROUNDS:
            members = [r for r in rows if r["condition"] == arm and r["background"] == background]
            scored = [r["correct"] for r in members if r["correct"] is not None]
            accuracy_tables.append({"condition": arm, "background": background,
                                    "n_valid": len(scored), "n_planned": len(members),
                                    "n_correct": sum(scored), "accuracy_valid_only": mean(scored)})
    valid_count = sum(r["correct"] is not None for r in rows)
    invalid = sum(r["status"] == "invalid" for r in rows)
    complete = valid_count == len(rows)
    threshold = plan["decision_rule"]["minimum_extra_conflict_penalty"]
    extra = effects["extra_conflict_penalty"]["mean"]
    numeric_pass = extra is not None and extra >= threshold - 1e-12
    directions_match = bool(list_effects) and (
        effects["cot_conflict_penalty"]["mean"] > 0
        and paired_accuracy["cot_conflict"] < paired_accuracy["direct_conflict"])
    if invalid:
        decision = "technical_failure"
    elif not complete:
        decision = "incomplete"
    elif len(list_effects) < plan["decision_rule"]["minimum_independent_lists"]:
        decision = "insufficient_lists"
    elif not numeric_pass:
        decision = "stop_this_extension"
    elif not directions_match:
        decision = "stop_direction_mismatch"
    else:
        decision = "review_for_confirmation"
    result = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "planned_calls": len(rows), "attempts": len(attempts), "complete_answers": valid_count,
        "invalid_answers": invalid, "pending_tasks": sum(r["status"] == "pending" for r in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "complete": complete, "paired_lists": len(list_effects), "list_effects": list_effects,
        "accuracy_tables": accuracy_tables, "paired_accuracy": paired_accuracy, "effects": effects,
        "support_to_conflict_transitions": {
            arm: {"correct_to_wrong": values["1_to_0"], "wrong_to_correct": values["0_to_1"],
                  "correct_in_both": values["1_to_1"], "wrong_in_both": values["0_to_0"]}
            for arm, values in transitions.items()},
        "screen": {**plan["decision_rule"],
                   "decision": "simulated_not_evidence" if mode == "mock" else decision,
                   "numeric_threshold_met": numeric_pass if complete and not invalid else None,
                   "directions_match_hypothesis": directions_match if complete and not invalid else None},
        "bootstrap_unit": "independent_list_pair", "bootstrap_replicates": 10000,
        "interpretation": ("SIMULATED software test: no scientific evidence." if mode == "mock" else
            "Separate exploratory study designed after the original stage-1 stop decision. "
            "The 15 pp rule is an investment screen, not a significance test. "
            "A positive interaction alone does not establish an internal mechanism or novelty. "
            "A stop decision does not establish the absence of smaller effects."),
    }
    result["usage"] = {key: sum((a.get("response", {}).get("usage") or {}).get(key, 0) or 0
                                for a in attempts)
                       for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return result, rows


def pp(value):
    return "—" if value is None else f"{100 * value:.1f} pp"


def write_summary(output):
    output = Path(output)
    plan = read_plan(output)
    execution_path = output / "execution.json"
    execution = json.loads(execution_path.read_text()) if execution_path.exists() else {}
    attempts = load_attempts(output, plan)
    if attempts and (execution.get("mode") not in ("live", "mock")
                     or execution.get("plan_hash") != plan["plan_hash"]
                     or execution.get("protocol_version") != plan["protocol_version"]
                     or any(a.get("mode") != execution["mode"] for a in attempts)):
        raise ValueError("Attempt journal has missing or inconsistent execution identity")
    result, rows = summarize(plan, attempts, execution.get("mode", "not_run"))
    write_json(output / "summary.json", result)
    with (output / "scores.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Verified-facts counterfactual diagnostic" + (" — SIMULATED" if result["is_simulated"] else ""),
             "", f"Model: `{result['model']}`; protocol: `{result['protocol_version']}`.", "",
             f"Valid: {result['complete_answers']}/{result['planned_calls']}; invalid: {result['invalid_answers']}; "
             f"provider errors: {result['provider_errors']}; attempts: {result['attempts']}.", "",
             f"Complete independent list pairs: {result['paired_lists']} (not {result['complete_answers']} independent samples).",
             "", result["interpretation"], "", f"Screen: **{result['screen']['decision']}**.", "",
             "All queried target labels are identical across the two backgrounds. Both backgrounds have 20% exceptions.",
             "", "| Response | Supporting pattern | Conflicting pattern | Conflict penalty |",
             "|---|---:|---:|---:|"]
    for arm in ARMS:
        lines.append(f"| {arm} | {pct(result['paired_accuracy'][f'{arm}_support'])} "
                     f"| {pct(result['paired_accuracy'][f'{arm}_conflict'])} "
                     f"| {pp(result['effects'][f'{arm}_conflict_penalty']['mean'])} |")
    primary = result["effects"]["extra_conflict_penalty"]
    ci = primary["paired_bootstrap_95_ci"]
    ci_text = "—" if ci is None else f"[{pp(ci[0])}, {pp(ci[1])}]"
    lines += ["", f"**Extra conflict penalty under CoT: {pp(primary['mean'])}; 95% list bootstrap: {ci_text}.**", "",
              "The table and primary contrast use complete matched lists only.", "",
              f"List-level interaction: {primary['positive_lists']} positive, {primary['zero_lists']} zero, "
              f"{primary['negative_lists']} negative.", "",
              "Review for confirmation requires all planned answers valid, at least 20 lists, an extra penalty of at least "
              "15 pp, an actual CoT accuracy drop under conflict, and lower CoT than direct accuracy under conflict. "
              "Inspect the interval and individual lists before any new experiment. No further calls start automatically.",
              "", "| Response | Correct → wrong | Wrong → correct | Correct in both | Wrong in both |",
              "|---|---:|---:|---:|---:|"]
    for arm, transition in result["support_to_conflict_transitions"].items():
        lines.append(f"| {arm} | {transition['correct_to_wrong']} | {transition['wrong_to_correct']} "
                     f"| {transition['correct_in_both']} | {transition['wrong_in_both']} |")
    lines += ["", "Transitions run from the supporting to the conflicting background; these are independent calls, "
              "not chronological revisions in a conversation.", "",
              "| Response | Background | Correct / valid / planned | Accuracy among valid |",
              "|---|---|---:|---:|"]
    for row in result["accuracy_tables"]:
        lines.append(f"| {row['condition']} | {row['background']} | {row['n_correct']} / {row['n_valid']} / "
                     f"{row['n_planned']} | {pct(row['accuracy_valid_only'])} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
