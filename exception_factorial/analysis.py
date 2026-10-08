"""Whole-list paired factorial contrasts, with no outcome-dependent pass gate."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from exception_pilot.analysis import mean, pct
from exception_pilot.core import parse_answer
from exception_pilot.storage import accepted_records, load_attempts, write_json
from exception_wording.analysis import effect, pp
from . import CALLS_PER_LIST, PRIMARY_CONTRAST
from .core import ARMS, BACKGROUNDS, QUESTIONS, UNCERTAINTY, read_plan, task_meta

CONTRAST_DESCRIPTIONS = {
    PRIMARY_CONTRAST: "Sentence effect under original minus sentence effect under recorded (primary)",
    "uncertainty_effect/original": "Original: sentence present minus absent",
    "uncertainty_effect/recorded": "Recorded: sentence present minus absent",
    "question_effect/absent": "Sentence absent: original minus recorded",
    "question_effect/present": "Sentence present: original minus recorded",
    "average_uncertainty_effect": "Average present-minus-absent effect across questions",
    "average_question_effect": "Average original-minus-recorded effect across sentence levels",
}


def factorial_contrasts(extras):
    original_sentence = extras["original/present"] - extras["original/absent"]
    recorded_sentence = extras["recorded/present"] - extras["recorded/absent"]
    question_absent = extras["original/absent"] - extras["recorded/absent"]
    question_present = extras["original/present"] - extras["recorded/present"]
    return {
        PRIMARY_CONTRAST: original_sentence - recorded_sentence,
        "uncertainty_effect/original": original_sentence,
        "uncertainty_effect/recorded": recorded_sentence,
        "question_effect/absent": question_absent,
        "question_effect/present": question_present,
        "average_uncertainty_effect": (original_sentence + recorded_sentence) / 2,
        "average_question_effect": (question_absent + question_present) / 2,
    }


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
        if len(subset) != CALLS_PER_LIST or any(r["correct"] is None for r in subset):
            continue
        cells = {f"{q}/{u}/{arm}/{bg}": mean([
            r["correct"] for r in subset if r["question_wording"] == q
            and r["uncertainty_clause"] == u and r["condition"] == arm and r["background"] == bg])
            for q in QUESTIONS for u in UNCERTAINTY for arm in ARMS for bg in BACKGROUNDS}
        extras = {}
        for q in QUESTIONS:
            for u in UNCERTAINTY:
                prefix = f"{q}/{u}"
                direct = cells[f"{prefix}/direct/support"] - cells[f"{prefix}/direct/conflict"]
                reasoning = cells[f"{prefix}/cot_neutral/support"] - cells[f"{prefix}/cot_neutral/conflict"]
                extras[prefix] = reasoning - direct
        list_effects.append({"world_id": world["id"], "accuracy": cells,
                            "extra_conflict_penalty": extras,
                            "factorial_contrasts": factorial_contrasts(extras)})
    paired_accuracy = {f"{q}/{u}/{arm}/{bg}": mean([
        e["accuracy"][f"{q}/{u}/{arm}/{bg}"] for e in list_effects])
        for q in QUESTIONS for u in UNCERTAINTY for arm in ARMS for bg in BACKGROUNDS}
    comparisons = {}
    for q in QUESTIONS:
        for u in UNCERTAINTY:
            key = f"{q}/{u}"
            acc = {f"{arm}_{bg}": paired_accuracy[f"{key}/{arm}/{bg}"]
                   for arm in ARMS for bg in BACKGROUNDS}
            direct = acc["direct_support"] - acc["direct_conflict"] if list_effects else None
            reasoning = acc["cot_neutral_support"] - acc["cot_neutral_conflict"] if list_effects else None
            harm = acc["direct_conflict"] - acc["cot_neutral_conflict"] if list_effects else None
            comparisons[key] = {
                "question_wording": q, "uncertainty_clause": u, "paired_accuracy": acc,
                "direct_conflict_penalty": direct, "reasoning_conflict_penalty": reasoning,
                "direct_minus_reasoning_conflict_accuracy": harm,
                "extra_conflict_penalty": effect([e["extra_conflict_penalty"][key] for e in list_effects]),
            }
    contrasts = {key: {"description": description, **effect([
        e["factorial_contrasts"][key] for e in list_effects])}
        for key, description in CONTRAST_DESCRIPTIONS.items()}
    tables = []
    for q in QUESTIONS:
        for u in UNCERTAINTY:
            for arm in ARMS:
                for bg in BACKGROUNDS:
                    members = [r for r in rows if r["question_wording"] == q and r["uncertainty_clause"] == u
                               and r["condition"] == arm and r["background"] == bg]
                    valid = [r["correct"] for r in members if r["correct"] is not None]
                    tables.append({"question_wording": q, "uncertainty_clause": u,
                                   "condition": arm, "background": bg,
                                   "n_correct": sum(valid), "n_valid": len(valid),
                                   "n_planned": len(members), "accuracy_valid_only": mean(valid)})
    valid_count = sum(r["correct"] is not None for r in rows)
    invalid = sum(r["status"] == "invalid" for r in rows)
    complete = valid_count == len(rows)
    if invalid:
        status = "technical_failure"
    elif not complete:
        status = "incomplete"
    elif len(list_effects) < plan["analysis_plan"]["minimum_independent_lists"]:
        status = "insufficient_lists"
    else:
        status = "complete_ready_for_interpretation"
    if mode == "mock":
        status = "simulated_not_evidence"
    return {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "planned_calls": len(rows), "attempts": len(attempts), "complete_answers": valid_count,
        "invalid_answers": invalid, "pending_tasks": sum(r["status"] == "pending" for r in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "complete": complete, "paired_lists": len(list_effects), "list_effects": list_effects,
        "accuracy_tables": tables, "paired_accuracy": paired_accuracy,
        "comparisons": comparisons, "factorial_contrasts": contrasts,
        "analysis_plan": plan["analysis_plan"], "analysis_status": status,
        "bootstrap_unit": "independent_list_pair", "bootstrap_replicates": 10000,
        "bootstrap_seed": 981723,
        "usage": {key: sum((a.get("response", {}).get("usage") or {}).get(key, 0) or 0
                            for a in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
        "interpretation": ("SIMULATED software test: no scientific evidence." if mode == "mock" else
            "Explanatory study specified after observing the previous wording boundary. "
            "Question text and the uncertainty sentence vary independently. All cells share each "
            "list; the independent sample size is complete lists, not calls. Completion is not "
            "a pass, mechanism claim, novelty claim, or authorization for another study. "
            "The earlier stop_explicit_record_boundary decision is preserved."),
    }, rows


def interval_text(stats):
    ci = stats["paired_bootstrap_95_ci"]
    return "—" if ci is None else f"[{pp(ci[0])}, {pp(ci[1])}]"


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
    lines = ["# Question × uncertainty diagnostic" + (" — SIMULATED" if result["is_simulated"] else ""),
             "", f"Model: `{result['model']}`; protocol: `{result['protocol_version']}`.", "",
             f"Valid: {result['complete_answers']}/{result['planned_calls']}; invalid: {result['invalid_answers']}; "
             f"provider errors: {result['provider_errors']}; attempts: {result['attempts']}.", "",
             f"Complete independent list pairs: {result['paired_lists']}.", "", result["interpretation"], "",
             f"Analysis status: **{result['analysis_status']}**. No numerical pass threshold.", "",
             "## Paired cell accuracies", "",
             "These tables use only lists with all 32 valid answers. The target facts remain fixed "
             "across backgrounds; six non-target labels change. Every call is stateless.", "",
             "| Question | Uncertainty sentence | Response | Support accuracy | Conflict accuracy |",
             "|---|---|---|---:|---:|"]
    for q in QUESTIONS:
        for u in UNCERTAINTY:
            for arm in ARMS:
                key = f"{q}/{u}/{arm}"
                lines.append(f"| {q} | {u} | {arm} | {pct(result['paired_accuracy'][key + '/support'])} "
                             f"| {pct(result['paired_accuracy'][key + '/conflict'])} |")
    lines += ["", "## Reasoning-specific extra conflict penalties", "",
              "E = (reasoning support − reasoning conflict) − (direct support − direct conflict). "
              "Positive E means conflict hurts reasoning more. Inspect the components too.", "",
              "| Question / sentence | E | 95% list bootstrap | Positive / zero / negative lists |",
              "|---|---:|---|---|"]
    for key, comparison in result["comparisons"].items():
        stats = comparison["extra_conflict_penalty"]
        lines.append(f"| {key} | {pp(stats['mean'])} | {interval_text(stats)} | "
                     f"{stats['positive_lists']} / {stats['zero_lists']} / {stats['negative_lists']} |")
    lines += ["", "| Question / sentence | Direct conflict penalty | Reasoning conflict penalty | Direct − reasoning in conflict |",
              "|---|---:|---:|---:|"]
    for key, comparison in result["comparisons"].items():
        lines.append(f"| {key} | {pp(comparison['direct_conflict_penalty'])} | "
                     f"{pp(comparison['reasoning_conflict_penalty'])} | "
                     f"{pp(comparison['direct_minus_reasoning_conflict_accuracy'])} |")
    lines += ["", "## Factorial contrasts in E", "",
              "Primary interaction = (original present − original absent) − "
              "(recorded present − recorded absent). Positive means the sentence increases E more "
              "under the original question. Zero interaction can coexist with additive wording effects.", "",
              "| Contrast | Difference | 95% list bootstrap | Positive / zero / negative lists |",
              "|---|---:|---|---|"]
    for stats in result["factorial_contrasts"].values():
        lines.append(f"| {stats['description']} | {pp(stats['mean'])} | {interval_text(stats)} | "
                     f"{stats['positive_lists']} / {stats['zero_lists']} / {stats['negative_lists']} |")
    lines += ["", "Intervals use 10,000 whole-list resamples, seed 981723. They are descriptive, "
              "not simultaneous confidence statements. Degenerate intervals reflect a constant "
              "observed vector, not population certainty. Small or uncertain effects do not prove "
              "absence. The primary contrast and all components must be interpreted together.", "",
              "These are effects of exact prompt interventions on final answers, not observations "
              "of an internal mechanism. Only one snapshot and task family are tested. See "
              "FACTORIAL_PROTOCOL.md for scope, limitations, and the fixed interpretation plan.", "",
              "## All returned answers (valid-only denominators)", "",
              "| Question | Sentence | Response | Background | Correct / valid / planned | Accuracy |",
              "|---|---|---|---|---:|---:|"]
    for row in result["accuracy_tables"]:
        lines.append(f"| {row['question_wording']} | {row['uncertainty_clause']} | {row['condition']} | "
                     f"{row['background']} | {row['n_correct']} / {row['n_valid']} / {row['n_planned']} | "
                     f"{pct(row['accuracy_valid_only'])} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
