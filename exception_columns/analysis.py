"""Paired world estimates, complete answer transitions, and raw-text exports."""

from __future__ import annotations

from collections import Counter
import csv
import itertools
import json
from pathlib import Path
import random
import statistics

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, SCHEMAS, VALUES, task_meta


def estimands():
    result = {f"cell/{schema}/{arm}": {(schema, arm): 1.0} for schema in SCHEMAS for arm in ARMS}
    for schema in SCHEMAS:
        result[f"reasoning_harm/{schema}"] = {(schema, "direct"): 1., (schema, "cot"): -1.}
        result[f"copy_gain/{schema}"] = {(schema, "copy_class"): 1., (schema, "cot"): -1.}
    weights = {
        "description_effect_on_reasoning_harm": {"minimal": -.5, "description": .5, "other_attributes": -.5, "full": .5},
        "other_attributes_effect_on_reasoning_harm": {"minimal": -.5, "description": -.5, "other_attributes": .5, "full": .5},
        "column_interaction_on_reasoning_harm": {"minimal": 1., "description": -1., "other_attributes": -1., "full": 1.},
    }
    for name, coefficients in weights.items():
        result[name] = {(schema, arm): weight * (1 if arm == "direct" else -1)
                        for schema, weight in coefficients.items() for arm in ("direct", "cot")}
    for schema in SCHEMAS[:-1]:
        for arm in ARMS:
            result[f"{schema}_minus_full/{arm}"] = {(schema, arm): 1., ("full", arm): -1.}
        result[f"copy_gain_{schema}_minus_full"] = {
            (schema, "copy_class"): 1., (schema, "cot"): -1., ("full", "copy_class"): -1., ("full", "cot"): 1.}
    return result


def score(answer, expected, pattern, metric):
    if metric == "accuracy":
        return int(answer == expected)
    return 1 if answer == expected else 0 if answer == pattern else -1


def estimate(values, resamples=10000):
    if not values:
        return {"estimate": None, "ci95": None, "complete_worlds": 0, "degenerate_interval": None,
                "positive_worlds": 0, "negative_worlds": 0, "tied_worlds": 0}
    n = len(values)
    if len(set(values)) == 1:
        interval = [values[0], values[0]]
    else:
        rng = random.Random(981723)
        means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
        def percentile(p):
            index = (len(means) - 1) * p
            lo = int(index)
            hi = min(lo + 1, len(means) - 1)
            return means[lo] + (means[hi] - means[lo]) * (index - lo)
        interval = [percentile(.025), percentile(.975)]
    return {"estimate": statistics.mean(values), "ci95": interval, "complete_worlds": n,
            "degenerate_interval": interval[0] == interval[1],
            "positive_worlds": sum(v > 0 for v in values), "negative_worlds": sum(v < 0 for v in values),
            "tied_worlds": sum(v == 0 for v in values)}


def paired_statistics(plan, records):
    tasks = {(t["world_id"], t["value"], t["schema"], t["arm"]): t for t in plan["tasks"]}
    result = {}
    for metric in ("accuracy", "record_sensitivity"):
        result[metric] = {}
        for name, coefficients in estimands().items():
            values, bounds, worlds = [], [], []
            for world in plan["worlds"]:
                total = lower = upper = 0.
                complete = True
                for (schema, arm), coefficient in coefficients.items():
                    for value in VALUES:
                        task = tasks[(world["id"], value, schema, arm)]
                        record = records.get(task["id"], {})
                        answer = record.get("answer") if record.get("status") == "complete" else None
                        expected, pattern = world["roles"][value], world["roles"]["pattern"]
                        weight = coefficient / 2
                        if answer in ("A", "B", "C"):
                            contribution = weight * score(answer, expected, pattern, metric)
                            total += contribution
                            lower += contribution
                            upper += contribution
                        else:
                            complete = False
                            possible = [weight * score(label, expected, pattern, metric) for label in "ABC"]
                            lower += min(possible)
                            upper += max(possible)
                worlds.append({"world_id": world["id"], "value": total if complete else None, "bounds": [lower, upper]})
                bounds.append((lower, upper))
                if complete:
                    values.append(total)
            result[metric][name] = {**estimate(values),
                                   "full_plan_bounds": [statistics.mean(b[i] for b in bounds) for i in (0, 1)],
                                   "worlds": worlds}
    return result


def transition_rows(plan, records):
    """Every reduced/full pair, including unchanged, missing and invalid cases."""
    rows = []
    for world in plan["worlds"]:
        for value in VALUES:
            for arm in ARMS:
                for schema in SCHEMAS[:-1]:
                    full_id = f"{world['id']}/{value}/full/{arm}"
                    reduced_id = f"{world['id']}/{value}/{schema}/{arm}"
                    before, after = records.get(full_id, {}), records.get(reduced_id, {})
                    valid = before.get("status") == after.get("status") == "complete"
                    expected = world["roles"][value]
                    b = before.get("answer") if before.get("status") == "complete" else None
                    a = after.get("answer") if after.get("status") == "complete" else None
                    bc = b == expected if b is not None else None
                    ac = a == expected if a is not None else None
                    change = (f"{'correct' if bc else 'wrong'}_to_{'correct' if ac else 'wrong'}" if valid else "unresolved")
                    rows.append({"world_id": world["id"], "value": value, "arm": arm, "reduced_schema": schema,
                                 "expected": expected, "background_pattern_label": world["roles"]["pattern"],
                                 "full_task_id": full_id, "reduced_task_id": reduced_id,
                                 "full_status": before.get("status", "unreturned"), "reduced_status": after.get("status", "unreturned"),
                                 "full_answer": b, "reduced_answer": a, "full_correct": bc, "reduced_correct": ac,
                                 "paired_valid": valid, "answer_changed": b != a if valid else None, "transition": change})
    return rows


def record_pairs(plan, records):
    rows = []
    for world in plan["worlds"]:
        for schema in SCHEMAS:
            for arm in ARMS:
                pair = [records.get(f"{world['id']}/{v}/{schema}/{arm}", {}) for v in VALUES]
                valid = all(r.get("status") == "complete" for r in pair)
                answers = [r.get("answer") if r.get("status") == "complete" else None for r in pair]
                rows.append({"world_id": world["id"], "schema": schema, "arm": arm, "paired_valid": valid,
                             "record_1_class": world["roles"]["record_1"], "record_2_class": world["roles"]["record_2"],
                             "record_1_answer": answers[0], "record_2_answer": answers[1],
                             "answers_differ": answers[0] != answers[1] if valid else None,
                             "both_correct": all(a == world["roles"][v] for a, v in zip(answers, VALUES)) if valid else None})
    return rows


def summarize(plan, execution, attempts):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"], {})
        meta = task_meta(plan, task)
        valid = record.get("status") == "complete"
        answer = record.get("answer") if valid else None
        copied = record.get("copied")
        response = record.get("response", {})
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        rows.append({**meta, "status": record.get("status", "unreturned"), "answer": answer,
                     "correct": answer == meta["expected"] if valid else None,
                     "pattern_choice": answer == meta["pattern_label"] if valid else None,
                     "copied": copied, "copy_valid": record.get("copy_valid"),
                     "copy_correct": copied == meta["expected"] if task["arm"] == "copy_class" and record else None,
                     "has_reasoning": record.get("has_reasoning"), "contract_met": record.get("contract_met", False),
                     "strict_final_format": record.get("strict_final_format"), "answer_only": record.get("answer_only"),
                     "reasoning_words": record.get("reasoning_words"), "completion_tokens": usage.get("completion_tokens"),
                     "model_identity": response.get("model_identity"), "text": response.get("text", "")})
    cells = {}
    pairs = record_pairs(plan, records)
    for schema, arm in itertools.product(SCHEMAS, ARMS):
        subset = [r for r in rows if r["schema"] == schema and r["arm"] == arm]
        pair_subset = [p for p in pairs if p["schema"] == schema and p["arm"] == arm]
        valid = sum(r["status"] == "complete" for r in subset)
        correct = sum(r["correct"] is True for r in subset)
        copies = sum(r["copy_correct"] is True for r in subset)
        cells[f"{schema}/{arm}"] = {
            "planned": len(subset), "returned": sum(r["status"] != "unreturned" for r in subset),
            "valid": valid, "invalid": sum(r["status"] == "invalid" for r in subset),
            "unreturned": sum(r["status"] == "unreturned" for r in subset), "correct": correct,
            "accuracy_valid_only": correct / valid if valid else None,
            "full_plan_accuracy_bounds": [correct / len(subset), (correct + len(subset) - valid) / len(subset)],
            "background_pattern_choices": sum(r["pattern_choice"] is True for r in subset),
            "answer_counts": dict(Counter(r["answer"] for r in subset if r["answer"] is not None)),
            "contract_met_count": sum(r["contract_met"] for r in subset),
            "contract_met_fraction_all_planned": sum(r["contract_met"] for r in subset) / len(subset),
            "correct_copies": copies if arm == "copy_class" else None,
            "valid_copy_format": sum(r["copy_valid"] is True for r in subset) if arm == "copy_class" else None,
            "correct_copy_wrong_final": sum(r["copy_correct"] is True and r["correct"] is False for r in subset) if arm == "copy_class" else None,
            "correct_copy_invalid_final": sum(r["copy_correct"] is True and r["status"] == "invalid" for r in subset) if arm == "copy_class" else None,
            "paired_record_worlds": sum(p["paired_valid"] for p in pair_subset),
            "both_record_variants_correct": sum(p["both_correct"] is True for p in pair_subset),
            "record_variant_answers_differ": sum(p["answers_differ"] is True for p in pair_subset),
        }
        for field in ("reasoning_words", "completion_tokens"):
            numeric = [r[field] for r in subset if type(r[field]) in (int, float)]
            cells[f"{schema}/{arm}"]["median_" + field] = statistics.median(numeric) if numeric else None
    transitions = transition_rows(plan, records)
    transition_summary = {}
    for schema, arm in itertools.product(SCHEMAS[:-1], ARMS):
        subset = [r for r in transitions if r["reduced_schema"] == schema and r["arm"] == arm]
        transition_summary[f"full_to_{schema}/{arm}"] = {
            "planned_pairs": len(subset), "paired_valid": sum(r["paired_valid"] for r in subset),
            "answers_changed": sum(r["answer_changed"] is True for r in subset),
            **{k: sum(r["transition"] == k for r in subset) for k in
               ("correct_to_correct", "correct_to_wrong", "wrong_to_correct", "wrong_to_wrong", "unresolved")}}
    identity_failures = sum(r["model_identity"] in ("missing", "mismatch") for r in rows)
    mode = execution["mode"] if execution else None
    returned = len(records)
    status = ("simulated_only" if mode == "mock" else "not_started" if mode is None else
              "model_identity_failure" if identity_failures else "incomplete" if returned < len(rows) else
              "exploratory_complete_with_invalids" if any(r["status"] == "invalid" for r in rows) else "exploratory_complete")
    summary = {"protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
               "source_plan_hash": plan["source_plan_hash"], "model": plan["config"]["model"],
               "evidence_label": "SIMULATED — NOT MODEL EVIDENCE" if mode == "mock" else "LIVE" if mode == "live" else "NOT STARTED",
               "is_simulated": mode == "mock", "analysis_status": status, "attempts": len(attempts),
               "attempt_status_counts": dict(Counter(a["status"] for a in attempts)), "planned_calls": len(rows),
               "returned_answers": returned, "valid_answers": sum(r["status"] == "complete" for r in rows),
               "invalid_answers": sum(r["status"] == "invalid" for r in rows), "unreturned_answers": len(rows) - returned,
               "model_identity_failures": identity_failures, "cells": cells,
               "metrics": paired_statistics(plan, records), "column_transitions": transition_summary}
    return summary, rows, transitions, pairs


def write_csv(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    summary, rows, transitions, pairs = summarize(plan, execution, attempts)
    write_json(output / "summary.json", summary)
    write_csv(output / "responses.csv", [{k: v for k, v in r.items() if k not in ("columns", "text")} for r in rows])
    write_csv(output / "column-transitions.csv", transitions)
    write_csv(output / "record-pairs.csv", pairs)
    with (output / "responses.jsonl").open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    lines = ["# Column availability and reasoning", "", f"**{summary['evidence_label']}** — {summary['model']}", "",
             f"Status: `{summary['analysis_status']}`. Returned {summary['returned_answers']}/576; valid {summary['valid_answers']}; retained invalid {summary['invalid_answers']}; attempts {summary['attempts']}/608.", "",
             "This study reuses all 24 explanation worlds. It is exploratory development, not a fresh-world confirmation. No automated success threshold or extension.", "",
             "Minimal = plate + class. Description adds Description. Other attributes adds Transmission, Seat cover, Doors, Audit marker. Full retains all seven columns.", "",
             "| Table / arm | Correct / valid | Pattern choices | Invalid / unreturned | Contract / 48 | Correct copy → wrong final |", "|---|---:|---:|---:|---:|---:|"]
    for name, cell in summary["cells"].items():
        cp = "—" if cell["correct_copy_wrong_final"] is None else str(cell["correct_copy_wrong_final"])
        lines.append(f"| {name} | {cell['correct']}/{cell['valid']} | {cell['background_pattern_choices']} | {cell['invalid']}/{cell['unreturned']} | {cell['contract_met_count']} | {cp} |")
    lines += ["", "## Paired estimates", "",
              "H = direct accuracy − reasoning accuracy. The two primary contrasts average the change in H from adding each column group across absence/presence of the other group. Positive = more reasoning harm with that group.", "",
              "Record sensitivity averages +1 for the target class, −1 for the other record variant's class, and 0 for the background-pattern label; range [−1, 1]. A fixed answer across variants scores 0.", "",
              "Intervals use 10,000 whole-world bootstrap resamples and are descriptive and unadjusted. Complete-world denominators are contrast-specific. Full-plan bounds vary invalid/unreturned answers over A/B/C; they are not confidence intervals. Degenerate intervals do not establish precision or equivalence.", ""]
    for metric, stats in summary["metrics"].items():
        lines += ["### " + metric, "", "| Contrast | Estimate | 95% interval | Complete worlds | Full-plan bounds |", "|---|---:|---|---:|---|"]
        for name, stat in stats.items():
            ci = "—" if stat["ci95"] is None else ", ".join(fmt(v) for v in stat["ci95"])
            lines.append(f"| {name} | {fmt(stat['estimate'])} | {ci} | {stat['complete_worlds']} | " + ", ".join(fmt(v) for v in stat["full_plan_bounds"]) + " |")
    lines += ["", "## Full table → reduced table", "", "| Comparison | Valid pairs | Wrong → correct | Correct → wrong | Both wrong | Both correct | Changed label |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, t in summary["column_transitions"].items():
        lines.append(f"| {name} | {t['paired_valid']} | {t['wrong_to_correct']} | {t['correct_to_wrong']} | {t['wrong_to_wrong']} | {t['correct_to_correct']} | {t['answers_changed']} |")
    lines += ["", "Every case, including unchanged and unresolved pairs, is in column-transitions.csv. record-pairs.csv compares both target-class variants. responses.jsonl retains all model text for reviewing missingness claims, invented similarities, and changes in justification. These are not automatically coded as hidden beliefs or causal mechanisms.", "",
              "Column deletion changes width, token count, and class-cell position as well as available information. The license-plate-only query and shared instructions are fixed. The background-pattern label remains a label identity when Description is absent; a choice of it does not prove climate inference. Chance feature correlations and background class frequencies remain. Historical responses are never pooled into these estimates.", ""]
    (output / "summary.md").write_text("\n".join(lines))
    return summary
