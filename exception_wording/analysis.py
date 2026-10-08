"""List-paired contrasts and fixed, ordered investment checks for wording robustness."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from exception_pilot.analysis import interval, mean, pct
from exception_pilot.core import parse_answer
from exception_pilot.storage import accepted_records, load_attempts, write_json
from .core import ARMS, BACKGROUNDS, QUESTIONS, read_plan, task_meta


def effect(values):
    return {"mean": mean(values),
            "paired_bootstrap_95_ci": (None if len(values) < 2 else
                [values[0], values[0]] if len(set(values)) == 1 else interval(values)),
            "positive_lists": sum(v > 0 for v in values),
            "zero_lists": sum(v == 0 for v in values),
            "negative_lists": sum(v < 0 for v in values)}


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
                     "status": record["status"] if record else "pending", "answer": answer,
                     "correct": int(answer == meta["expected"]) if valid else None})
    list_effects = []
    for world in plan["worlds"]:
        subset = [r for r in rows if r["world_id"] == world["id"]]
        if len(subset) != 24 or any(r["correct"] is None for r in subset):
            continue
        cells = {f"{question}/{arm}/{background}": mean([
            r["correct"] for r in subset if r["question_wording"] == question
            and r["condition"] == arm and r["background"] == background])
            for question in QUESTIONS for arm in ARMS for background in BACKGROUNDS}
        extras = {}
        for question in QUESTIONS:
            direct = cells[f"{question}/direct/support"] - cells[f"{question}/direct/conflict"]
            for arm in ARMS[1:]:
                extras[f"{question}/{arm}"] = (cells[f"{question}/{arm}/support"]
                    - cells[f"{question}/{arm}/conflict"] - direct)
        list_effects.append({"world_id": world["id"], "accuracy": cells,
                             "extra_conflict_penalty": extras})
    paired_accuracy = {f"{q}/{arm}/{bg}": mean([
        e["accuracy"][f"{q}/{arm}/{bg}"] for e in list_effects])
        for q in QUESTIONS for arm in ARMS for bg in BACKGROUNDS}
    threshold = plan["decision_rule"]["minimum_extra_conflict_penalty"]
    comparisons = {}
    for q in QUESTIONS:
        for arm in ARMS[1:]:
            key = f"{q}/{arm}"
            stats = effect([e["extra_conflict_penalty"][key] for e in list_effects])
            acc = {f"{a}_{bg}": paired_accuracy[f"{q}/{a}/{bg}"]
                   for a in ("direct", arm) for bg in BACKGROUNDS}
            direct = acc["direct_support"] - acc["direct_conflict"] if list_effects else None
            reasoning = acc[f"{arm}_support"] - acc[f"{arm}_conflict"] if list_effects else None
            numeric = stats["mean"] is not None and stats["mean"] >= threshold - 1e-12
            directions = bool(list_effects) and reasoning > 0 and acc[f"{arm}_conflict"] < acc["direct_conflict"]
            comparisons[key] = {"question_wording": q, "condition": arm,
                "paired_accuracy": acc, "direct_conflict_penalty": direct,
                "reasoning_conflict_penalty": reasoning, "extra_conflict_penalty": stats,
                "numeric_threshold_met": numeric, "directions_match_hypothesis": directions,
                "qualifies_descriptively": numeric and directions}
    wording_contrasts = {}
    for q in QUESTIONS:
        wording_contrasts[f"{q}/neutral_minus_classification"] = effect([
            e["extra_conflict_penalty"][f"{q}/cot_neutral"]
            - e["extra_conflict_penalty"][f"{q}/cot_classification"] for e in list_effects])
    wording_contrasts["neutral/original_minus_recorded"] = effect([
        e["extra_conflict_penalty"]["original/cot_neutral"]
        - e["extra_conflict_penalty"]["recorded/cot_neutral"] for e in list_effects])
    tables = []
    for q in QUESTIONS:
        for arm in ARMS:
            for bg in BACKGROUNDS:
                members = [r for r in rows if r["question_wording"] == q and r["condition"] == arm
                           and r["background"] == bg]
                valid = [r["correct"] for r in members if r["correct"] is not None]
                tables.append({"question_wording": q, "condition": arm, "background": bg,
                               "n_correct": sum(valid), "n_valid": len(valid),
                               "n_planned": len(members), "accuracy_valid_only": mean(valid)})
    valid_count = sum(r["correct"] is not None for r in rows)
    invalid = sum(r["status"] == "invalid" for r in rows)
    complete = valid_count == len(rows)
    checks = {key: comparisons[key]["qualifies_descriptively"]
              for key in plan["decision_rule"]["ordered_checks"]}
    failures = ("stop_replication_failed", "stop_neutral_wording_failed", "stop_explicit_record_boundary")
    if invalid:
        decision = "technical_failure"
    elif not complete:
        decision = "incomplete"
    elif len(list_effects) < plan["decision_rule"]["minimum_independent_lists"]:
        decision = "insufficient_lists"
    else:
        decision = next((failure for passed, failure in zip(checks.values(), failures) if not passed),
                        "review_for_second_model")
    if mode == "mock":
        decision = "simulated_not_evidence"
    return {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "planned_calls": len(rows), "attempts": len(attempts), "complete_answers": valid_count,
        "invalid_answers": invalid, "pending_tasks": sum(r["status"] == "pending" for r in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "complete": complete, "paired_lists": len(list_effects), "list_effects": list_effects,
        "accuracy_tables": tables, "paired_accuracy": paired_accuracy,
        "comparisons": comparisons, "wording_contrasts": wording_contrasts,
        "screen": {**plan["decision_rule"], "decision": decision,
                   "ordered_checks_pass": checks if complete and not invalid else None},
        "bootstrap_unit": "independent_list_pair", "bootstrap_replicates": 10000,
        "usage": {key: sum((a.get("response", {}).get("usage") or {}).get(key, 0) or 0
                            for a in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
        "interpretation": ("SIMULATED software test: no scientific evidence." if mode == "mock" else
            "Fresh-data wording follow-up specified after a positive exploratory pilot. "
            "All six wording cells share each list. The independent sample size is the number of "
            "complete lists, not calls. The ordered 15 pp checks are investment rules, not "
            "significance tests, mechanistic evidence or novelty claims. No follow-up runs automatically."),
    }, rows


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
    lines = ["# Fresh-data wording confirmation" + (" — SIMULATED" if result["is_simulated"] else ""),
             "", f"Model: `{result['model']}`; protocol: `{result['protocol_version']}`.", "",
             f"Valid: {result['complete_answers']}/{result['planned_calls']}; invalid: {result['invalid_answers']}; "
             f"provider errors: {result['provider_errors']}; attempts: {result['attempts']}.", "",
             f"Complete independent list pairs: {result['paired_lists']}.", "", result["interpretation"], "",
             f"Screen: **{result['screen']['decision']}**.", "",
             "The following paired table uses complete lists only. Both backgrounds retain two exceptions; "
             "the queried target records stay fixed. Each call is a fresh conversation.", "",
             "| Question | Response instruction | Support accuracy | Conflict accuracy |",
             "|---|---|---:|---:|"]
    for q in QUESTIONS:
        for arm in ARMS:
            lines.append(f"| {q} | {arm} | {pct(result['paired_accuracy'][f'{q}/{arm}/support'])} "
                         f"| {pct(result['paired_accuracy'][f'{q}/{arm}/conflict'])} |")
    lines += ["", "Extra conflict penalty = reasoning conflict penalty − matched direct conflict penalty.", "",
              "| Question / reasoning | Extra penalty | 95% list bootstrap | Positive / zero / negative lists |",
              "|---|---:|---|---|"]
    for key, comparison in result["comparisons"].items():
        stats = comparison["extra_conflict_penalty"]
        ci = stats["paired_bootstrap_95_ci"]
        interval_text = "—" if ci is None else f"[{pp(ci[0])}, {pp(ci[1])}]"
        lines.append(f"| {key} | {pp(stats['mean'])} | {interval_text} | "
                     f"{stats['positive_lists']} / {stats['zero_lists']} / {stats['negative_lists']} |")
    lines += ["", "Primary robustness contrast: recorded/cot_neutral. All three ordered checks must pass "
              "before review for another model; recorded/cot_classification is diagnostic only.", "",
              "| Wording contrast | Difference in extra penalties | 95% list bootstrap |",
              "|---|---:|---|"]
    for key, stats in result["wording_contrasts"].items():
        ci = stats["paired_bootstrap_95_ci"]
        interval_text = "—" if ci is None else f"[{pp(ci[0])}, {pp(ci[1])}]"
        lines.append(f"| {key} | {pp(stats['mean'])} | {interval_text} |")
    lines += ["", "Question wording changes include removal of the original uncertainty clause. "
              "These contrasts characterize the tested prompts, not hidden computation. "
              "A boundary stop preserves the previous finding within its original wording; it stops "
              "investment in the broader wording-robust claim. A stop is not proof of no smaller effect.", "",
              "## All returned answers (valid-only denominators)", "",
              "| Question | Response | Background | Correct / valid / planned | Accuracy |",
              "|---|---|---|---:|---:|"]
    for row in result["accuracy_tables"]:
        lines.append(f"| {row['question_wording']} | {row['condition']} | {row['background']} | "
                     f"{row['n_correct']} / {row['n_valid']} / {row['n_planned']} | "
                     f"{pct(row['accuracy_valid_only'])} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
