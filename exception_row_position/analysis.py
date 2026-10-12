"""World-paired position contrasts and a fixed, conservative spending rule.

The two recorded-label variants are averaged before any across-world analysis.
Missing answers stay unknown; bounds never turn them into model mistakes.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
import random
import statistics

from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, write_json

from .core import ANALYSIS_PLAN, ARMS, DECISION_RULE, POSITIONS, VALUES, task_meta


BOOTSTRAP_RESAMPLES = ANALYSIS_PLAN["bootstrap_resamples"]
BOOTSTRAP_SEED = ANALYSIS_PLAN["bootstrap_seed"]
PRIMARY = "interaction"


def sign_test(values):
    """Exact two-sided sign balance test; this is not a test of mean magnitude."""
    positive = sum(value > 1e-12 for value in values)
    negative = sum(value < -1e-12 for value in values)
    n = positive + negative
    probability = (min(1., 2 * sum(math.comb(n, k)
                                 for k in range(min(positive, negative) + 1)) / 2 ** n)
                   if n else 1.)
    return {"p_two_sided": probability, "positive": positive,
            "negative": negative, "ties": len(values) - n}


def percentile(ordered, quantile):
    position = (len(ordered) - 1) * quantile
    left = int(position)
    return (ordered[left] + (ordered[min(left + 1, len(ordered) - 1)] - ordered[left])
            * (position - left))


def estimate(values):
    if not values:
        return {"estimate": None, "ci95": None, "complete_worlds": 0,
                "bootstrap_degenerate": None, "sign_test": sign_test([])}
    n = len(values)
    if min(values) == max(values):
        interval = [values[0], values[0]]
    else:
        rng = random.Random(BOOTSTRAP_SEED)
        draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n
                       for _ in range(BOOTSTRAP_RESAMPLES))
        interval = [percentile(draws, .025), percentile(draws, .975)]
    return {"estimate": statistics.mean(values), "ci95": interval,
            "complete_worlds": n, "bootstrap_degenerate": interval[0] == interval[1],
            "sign_test": sign_test(values)}


def estimands():
    result = {f"{position}/{arm}": {(position, arm): 1}
              for position in POSITIONS for arm in ARMS}
    for position in POSITIONS:
        result[f"{position}_direct_minus_visible"] = {
            (position, "direct"): 1, (position, "visible"): -1}
    for arm in ARMS:
        result[f"{arm}_last_minus_first"] = {(10, arm): 1, (1, arm): -1}
    result["middle_harm_minus_endpoint_average"] = {
        (5, "direct"): 1, (5, "visible"): -1,
        (1, "direct"): -.5, (1, "visible"): .5,
        (10, "direct"): -.5, (10, "visible"): .5}
    result[PRIMARY] = {(10, "direct"): 1, (10, "visible"): -1,
                       (1, "direct"): -1, (1, "visible"): 1}
    return result


def record_score(answer, expected, pattern, metric):
    if metric == "accuracy":
        return int(answer == expected)
    if metric == "record_sensitivity":
        return 1 if answer == expected else 0 if answer == pattern else -1
    raise ValueError("Unknown metric")


def scorable(record):
    return record.get("status") == "complete" and record.get("answer") in ("A", "B", "C")


def paired_statistics(plan, records):
    tasks = {(task["world_id"], task["value"], task["position"], task["arm"]): task
             for task in plan["tasks"]}
    result = {}
    for metric in ("accuracy", "record_sensitivity"):
        result[metric] = {}
        for name, coefficients in estimands().items():
            complete_values, world_bounds, by_world = [], [], []
            for world in plan["worlds"]:
                observed, lower, upper, complete = 0., 0., 0., True
                for (position, arm), coefficient in coefficients.items():
                    for value in VALUES:
                        task = tasks[(world["id"], value, position, arm)]
                        record = records.get(task["id"], {})
                        expected, pattern = world["roles"][value], world["roles"]["pattern"]
                        weight = coefficient / len(VALUES)
                        if scorable(record):
                            score = weight * record_score(record["answer"], expected, pattern, metric)
                            observed += score
                            lower += score
                            upper += score
                        else:
                            complete = False
                            possibilities = [weight * record_score(label, expected, pattern, metric)
                                             for label in ("A", "B", "C")]
                            lower += min(possibilities)
                            upper += max(possibilities)
                world_bounds.append((lower, upper))
                by_world.append({"world_id": world["id"], "complete": complete,
                                 "value": observed if complete else None,
                                 "bounds": [lower, upper]})
                if complete:
                    complete_values.append(observed)
            stat = estimate(complete_values)
            stat["full_plan_bounds"] = [statistics.mean(bound[i] for bound in world_bounds)
                                        for i in (0, 1)]
            stat["worlds"] = by_world
            result[metric][name] = stat
    return result


def local_decision(summary):
    """Return a spending recommendation, never an automatic further run."""
    if summary["is_simulated"]:
        return "simulated_only"
    if summary["mode"] == "not_started":
        return "not_started"
    if summary["returned_answers"] != summary["planned_calls"]:
        return "incomplete"
    if summary["model_identity_failures"]:
        return "model_identity_failure"
    adherence = DECISION_RULE["minimum_output_adherence"]
    if any(control["manipulation_adherence_fraction"] < adherence
           for control in summary["controls"].values()):
        return "output_manipulation_inconclusive"
    primary = summary["metrics"]["accuracy"][PRIMARY]
    if primary["complete_worlds"] < DECISION_RULE["minimum_complete_worlds_primary"]:
        return "insufficient_complete_worlds"
    interval, bounds = primary["ci95"], primary["full_plan_bounds"]
    if interval is None:
        return "inconclusive"
    threshold = DECISION_RULE["meaningful_effect"]
    point = primary["estimate"]
    positive = point >= threshold and bounds[0] >= threshold and interval[0] > 0
    negative = point <= -threshold and bounds[1] <= -threshold and interval[1] < 0
    if positive or negative:
        return "review_fresh_world_confirmation"
    # A large constant development effect can justify checking fresh worlds;
    # its degenerate bootstrap does not calibrate precision. Constant small
    # samples cannot establish enough precision to deprioritize an effect.
    if primary["bootstrap_degenerate"]:
        return "inconclusive"
    if min(interval[0], bounds[0]) > -threshold and max(interval[1], bounds[1]) < threshold:
        return "deprioritize_first_last"
    return "inconclusive"


def summarize(plan, config, execution, attempts):
    records = accepted_records(attempts)
    planned_ids = {task["id"] for task in plan["tasks"]}
    if set(records) - planned_ids:
        raise ValueError("Returned response does not belong to the frozen plan")
    controls = {}
    for position in POSITIONS:
        for arm in ARMS:
            tasks = [task for task in plan["tasks"]
                     if task["position"] == position and task["arm"] == arm]
            returned = [records[task["id"]] for task in tasks if task["id"] in records]
            valid = [record for record in returned if scorable(record)]
            n = len(tasks)
            correct = sum(record["answer"] == record["meta"]["expected"] for record in valid)
            pattern = sum(record["answer"] == record["meta"]["pattern_label"] for record in valid)
            direct = sum(record.get("answer_only") is True for record in valid)
            visible = sum(record.get("pre_answer_text") is True for record in valid)
            words = [record["pre_answer_words"] for record in returned
                     if record.get("pre_answer_words") is not None]
            tokens = [record.get("response", {}).get("usage", {}).get("completion_tokens")
                      for record in returned]
            tokens = [value for value in tokens if type(value) is int]
            controls[f"{position}/{arm}"] = {
                "position": position, "arm": arm, "planned": n, "returned": len(returned),
                "valid": len(valid), "correct": correct, "wrong": len(valid) - correct,
                "pattern_choices": pattern, "other_wrong": len(valid) - correct - pattern,
                "invalid": len(returned) - len(valid), "unreturned": n - len(returned),
                "accuracy_valid_only": correct / len(valid) if valid else None,
                "strict_answer_matches": sum(record.get("strict_answer_match") is True for record in valid),
                "contract_met_count": sum(record.get("output_contract_met") is True for record in valid),
                "answer_only_count": direct, "pre_answer_text_count": visible,
                "answer_only_fraction": direct / n, "pretext_fraction": visible / n,
                "manipulation_adherence_fraction": (direct if arm == "direct" else visible) / n,
                "median_pre_answer_words": statistics.median(words) if words else None,
                "median_completion_tokens": statistics.median(tokens) if tokens else None}
    mode = execution["mode"] if execution else "not_started"
    valid_count = sum(scorable(record) for record in records.values())
    result = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "config_hash": digest(config), "model": config["model"], "provider": config["provider"],
        "mode": mode, "is_simulated": mode == "mock",
        "evidence_label": ("SIMULATED — software fixture, not model evidence" if mode == "mock"
                           else "LIVE" if mode == "live" else "NOT STARTED"),
        "attempts": len(attempts), "planned_calls": len(plan["tasks"]),
        "returned_answers": len(records), "valid_answers": valid_count,
        "invalid_answers": len(records) - valid_count,
        "transport_errors": sum(record["status"] == "error" for record in attempts),
        "unresolved_attempts": sum(record["status"] == "started" for record in attempts),
        "model_identity_failures": (sum(record.get("response", {}).get("model") != config["model"]
                                        for record in records.values()) if mode == "live" else 0),
        "analysis_status": "complete" if len(records) == len(plan["tasks"]) else "incomplete",
        "controls": controls, "metrics": paired_statistics(plan, records),
        "analysis_plan": ANALYSIS_PLAN, "decision_rule": DECISION_RULE}
    result["decision"] = local_decision(result)
    primary = result["metrics"]["accuracy"][PRIMARY]
    point = primary["estimate"]
    result["primary_direction"] = (None if point is None else "last_more_harm" if point > 0
                                   else "first_more_harm" if point < 0 else "zero_observed_difference")
    result["primary_uncertainty_envelope"] = (
        [min(primary["ci95"][0], primary["full_plan_bounds"][0]),
         max(primary["ci95"][1], primary["full_plan_bounds"][1])] if primary["ci95"] else None)
    result["primary_bootstrap_warning"] = (
        "The primary bootstrap interval is degenerate and cannot calibrate precision. "
        "A large uniform development effect may justify fresh-world review; "
        "a zero or small degenerate result cannot justify deprioritization."
        if primary["bootstrap_degenerate"] else None)
    return result


def fmt(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, config, execution, attempts = read_run(output)
    result = summarize(plan, config, execution, attempts)
    records = accepted_records(attempts)
    answer_rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"], {})
        meta = task_meta(plan, task)
        answer_rows.append({"task_id": task["id"], **meta,
                            "position": task["position"], "arm": task["arm"],
                            "status": record.get("status", "unreturned"),
                            "answer": record.get("answer"),
                            "correct": record["answer"] == meta["expected"] if scorable(record) else None,
                            **{key: record.get(key) for key in (
                                "strict_answer_match", "pre_answer_text", "answer_only",
                                "output_contract_met", "pre_answer_words")}})
    with (output / "answers.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(answer_rows[0]))
        writer.writeheader()
        writer.writerows(answer_rows)
    with (output / "world_contrasts.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("metric", "estimand", "world_id", "complete",
                                                   "value", "lower_bound", "upper_bound"))
        writer.writeheader()
        for metric, stats in result["metrics"].items():
            for name, stat in stats.items():
                for world in stat["worlds"]:
                    writer.writerow({"metric": metric, "estimand": name,
                                     "world_id": world["world_id"], "complete": world["complete"],
                                     "value": world["value"], "lower_bound": world["bounds"][0],
                                     "upper_bound": world["bounds"][1]})
    write_json(output / "summary.json", result)
    lines = ["# Target row position", "", f"**{result['evidence_label']}** — {config['model']}", "",
             f"Returned {result['returned_answers']}/{result['planned_calls']}; valid {result['valid_answers']}; "
             f"retained invalid {result['invalid_answers']}; attempts {result['attempts']}/{config['max_total_attempts']}.",
             f"Decision: `{result['decision']}`. Observed direction: `{result['primary_direction']}`.", "",
             "Primary: accuracy interaction (direct − visible at row 10) − (direct − visible at row 1). "
             "Positive values mean more reasoning harm at the last row. Each world averages both recorded-label variants; "
             "the endpoint interaction requires its eight endpoint responses, not the row-5 responses.", "",
             "This reuses all 24 development worlds and tests a record-order intervention. It does not establish "
             "a retrieval mechanism, generality to fresh worlds, or equivalence. No decision automatically runs further calls. "
             "Deprioritizing is a spending decision, not proof of no position effect.", "",
             "Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples (seed 981723). "
             "Sign tests describe sign balance among nonzero world contrasts, not mean magnitude, and never gate spending. "
             "Full-plan bounds hold valid answers fixed and range missing/invalid answers over all three labels; "
             "they are not confidence intervals. A degenerate bootstrap interval cannot calibrate precision: "
             "a large uniform development effect can prompt fresh-world review, but a zero or small degenerate effect "
             "cannot trigger deprioritization.", "",
             "## Per-cell results", "",
             "| Row / arm | Correct / valid / planned | Wrong: pattern / other | Invalid / unreturned | Manipulation adherence / planned | Median words / tokens |",
             "|---|---:|---:|---:|---:|---:|"]
    for cell, control in result["controls"].items():
        adherence_count = (control["answer_only_count"] if control["arm"] == "direct"
                           else control["pre_answer_text_count"])
        lines.append(f"| {cell} | {control['correct']} / {control['valid']} / {control['planned']} | "
                     f"{control['pattern_choices']} / {control['other_wrong']} | "
                     f"{control['invalid']} / {control['unreturned']} | {adherence_count} / {control['planned']} | "
                     f"{fmt(control['median_pre_answer_words'])} / {fmt(control['median_completion_tokens'])} |")
    for metric, stats in result["metrics"].items():
        lines += ["", "## " + metric, "",
                  "| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |",
                  "|---|---:|---|---:|---:|---|---|"]
        for name, stat in stats.items():
            interval = "—" if stat["ci95"] is None else ", ".join(fmt(value) for value in stat["ci95"])
            signs = stat["sign_test"]
            lines.append(f"| {name} | {fmt(stat['estimate'])} | {interval} | {stat['complete_worlds']} | "
                         f"{fmt(signs['p_two_sided'])} | {signs['positive']} / {signs['negative']} / {signs['ties']} | "
                         + ", ".join(fmt(value) for value in stat["full_plan_bounds"]) + " |")
    lines += ["", "Secondary record sensitivity averages +1 (correct target label), −1 (other target label), "
              "0 (pattern label), over both variants. Its range is [−1, 1]; it does not enter the spending decision.", "",
              "Controls count every planned response in their denominators: direct requires answer-only output; "
              "visible requires pre-answer text. Noncompliance is retained in all scorable-answer estimates. "
              "Written text need not reflect hidden computation. Missing answers remain unknown in paired estimates."]
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
