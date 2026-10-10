"""World-level descriptive contrasts for the fixed record-status intervention.

Repeated continuations and the two target variants are nested within worlds.
This module never selects an arm, a checkpoint, or a scientific pass threshold.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import random
import re

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, BASE_ARMS, VALUES, capability_gate, task_meta


BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 981723
CONTRASTS = (
    ("bare_minus_original", "bare", "original"),
    ("bare_minus_paraphrase", "bare", "paraphrase"),
    ("recorded_minus_original", "recorded", "original"),
    ("recorded_minus_paraphrase", "recorded", "paraphrase"),
    ("recorded_minus_bare", "recorded", "bare"),
    ("original_minus_paraphrase", "original", "paraphrase"),
    ("direct_minus_visible", "direct", "visible"),
)


def _mean(values):
    return sum(values) / len(values) if values else None


def _quantile(ordered, probability):
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


@lru_cache(maxsize=128)
def _bootstrap_interval(values):
    """Deterministic percentile interval from whole-world resampling only."""
    if len(values) < 2:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    draws = sorted(_mean(rng.choices(values, k=len(values)))
                   for _ in range(BOOTSTRAP_RESAMPLES))
    return (_quantile(draws, 0.025), _quantile(draws, 0.975))


def _counts(rows):
    valid = [row for row in rows if row["status"] == "complete"]
    returned = [row for row in rows if row["status"] != "pending"]
    correct = sum(row["correct"] == 1 for row in valid)
    pattern = sum(row["follows_pattern"] == 1 for row in valid)
    all_returned = bool(rows) and len(returned) == len(rows)
    return {
        "planned": len(rows), "returned": len(returned), "valid": len(valid),
        "invalid": len(returned) - len(valid), "pending": len(rows) - len(returned),
        "correct": correct, "pattern": pattern,
        "other": sum(row["correct"] == 0 and row["follows_pattern"] == 0 for row in valid),
        "accuracy_valid_only": correct / len(valid) if valid else None,
        "pattern_rate_valid_only": pattern / len(valid) if valid else None,
        "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in "ABC"},
        "all_returned": all_returned, "all_valid": bool(rows) and len(valid) == len(rows),
        "full_plan_accuracy_bounds": [correct / len(rows),
                                       (correct + len(rows) - len(valid)) / len(rows)]
                                     if all_returned else None,
    }


def _row(plan, task, record):
    meta = task_meta(plan, task)
    valid = bool(record and record["status"] == "complete"
                 and record.get("format_valid") is True
                 and record.get("answer") in ("A", "B", "C")
                 and not record.get("hard_failure"))
    answer = record.get("answer") if record else None
    response = (record.get("response") or {}) if record else {}
    result = {
        "task_id": task["id"], "family": task["family"], "arm": task["arm"],
        "status": ("complete" if valid else "invalid") if record else "pending",
        "answer": answer,
    }
    for field in ("world_id", "value", "case_id", "item_id", "expected", "pattern_label",
                  "target_position", "repeat", "prefix_text", "target_id"):
        result[field] = meta.get(field, task.get(field))
    if result["case_id"] is None:
        result["case_id"] = f"{result['world_id']}/{result['value']}"
    result.update(
        correct=int(answer == result["expected"]) if valid else None,
        follows_pattern=int(answer == result["pattern_label"]) if valid else None,
        format_valid=record.get("format_valid") if record else None,
        invalid_reason=record.get("invalid_reason") if record else None,
        hard_failure=record.get("hard_failure") if record else None,
        prefix_exact=record.get("prefix_exact") if record else None,
        generated_suffix=record.get("generated_suffix") if record else None,
        raw_text=response.get("text"),
        response_id=response.get("response_id"),
        observed_model=response.get("model"),
    )
    return result


def _contrast(rows, name, first, second, metric, allowed):
    selected = [row for row in rows if row["arm"] in (first, second)]
    cells = defaultdict(list)
    for row in selected:
        cells[row["world_id"], row["value"], row["arm"]].append(row)
    worlds = sorted({row["world_id"] for row in selected})
    all_returned = bool(selected) and all(row["status"] != "pending" for row in selected)
    world_deltas, case_deltas, excluded_worlds, excluded_cases = {}, {}, [], []
    world_bounds, case_details = [], []
    missing_tasks = [row["task_id"] for row in selected if row["status"] != "complete"]
    for world in worlds:
        deltas, bounds = [], []
        for value in VALUES:
            left, right = cells[world, value, first], cells[world, value, second]
            case_id = next((row["case_id"] for row in left + right), f"{world}/{value}")
            complete = bool(left and right) and all(row["status"] == "complete" for row in left + right)
            left_mean = _mean([row[metric] for row in left]) if complete else None
            right_mean = _mean([row[metric] for row in right]) if complete else None
            delta = left_mean - right_mean if complete else None
            if complete:
                deltas.append(delta)
                case_deltas[case_id] = delta
            else:
                excluded_cases.append(case_id)
            # Missing/invalid responses can each score zero or one. These are
            # fixed-plan extrema, never confidence intervals or imputations.
            arm_bounds = []
            for group in (left, right):
                if not group:
                    raise ValueError("Contrast is missing a planned world/variant/arm cell")
                known = sum(row[metric] for row in group if row["status"] == "complete")
                unknown = sum(row["status"] != "complete" for row in group)
                arm_bounds.append((known / len(group), (known + unknown) / len(group)))
            bound = (arm_bounds[0][0] - arm_bounds[1][1],
                     arm_bounds[0][1] - arm_bounds[1][0])
            bounds.append(bound)
            case_details.append({
                "world_id": world, "value": value, "case_id": case_id,
                "complete": complete, "first_mean": left_mean, "second_mean": right_mean,
                "difference": delta, "first_planned": len(left), "second_planned": len(right),
                "full_plan_unscorable_bounds": list(bound) if all_returned else None,
            })
        if len(deltas) == len(VALUES):
            world_deltas[world] = _mean(deltas)
        else:
            excluded_worlds.append(world)
        world_bounds.append((_mean([bound[0] for bound in bounds]),
                             _mean([bound[1] for bound in bounds])))
    values = tuple(world_deltas.values())
    interval = _bootstrap_interval(values) if all_returned else None
    return {
        "contrast": name, "first_arm": first, "second_arm": second, "metric": metric,
        "role": "primary" if name == "bare_minus_original" and metric == "correct" else "secondary_descriptive",
        "mean": _mean(values), "n_worlds": len(values), "planned_worlds": len(worlds),
        "world_deltas": world_deltas,
        "descriptive_cluster_bootstrap_95_ci": list(interval) if interval is not None else None,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
        "interval_method": "Unadjusted percentile bootstrap, resampling whole complete worlds with replacement; withheld until all responses in this contrast have returned and at least two complete worlds remain.",
        "all_returned": all_returned, "interpretation_allowed": bool(allowed and all_returned),
        "excluded_world_ids": excluded_worlds, "excluded_case_ids": excluded_cases,
        "unscorable_or_pending_task_ids": missing_tasks,
        "case_weighted_mean": _mean(list(case_deltas.values())), "n_paired_cases": len(case_deltas),
        "paired_improved_cases": sum(delta > 0 for delta in case_deltas.values()),
        "paired_worsened_cases": sum(delta < 0 for delta in case_deltas.values()),
        "paired_unchanged_cases": sum(delta == 0 for delta in case_deltas.values()),
        "full_plan_unscorable_bounds": [_mean([bound[0] for bound in world_bounds]),
                                        _mean([bound[1] for bound in world_bounds])]
                                      if all_returned else None,
        "case_details": case_details,
        "weighting": "Mean across repeats within each variant and arm, paired arm difference within variant, mean of the two variants within world, equal weight per complete world. A world is excluded if any required response is unscorable or pending.",
        "sign": ("Positive values favor the first arm's accuracy." if metric == "correct" else
                 "Positive values mean more background-pattern choices in the first arm."),
    }


def summarize(plan, attempts, mode="live"):
    records = accepted_records(attempts)
    rows = [_row(plan, task, records.get(task["id"]))
            for task in plan["tasks"] if task["family"] != "capability"]
    cap = capability_gate(plan, records)
    baseline = [row for row in rows if row["arm"] in BASE_ARMS]
    intervention = [row for row in rows if row["arm"] in ARMS]
    baseline_count, intervention_count = _counts(baseline), _counts(intervention)
    hard_failures = [{"attempt": attempt.get("attempt"), "task_id": attempt["task_id"],
                      "reason": attempt["hard_failure"]}
                     for attempt in attempts if attempt.get("hard_failure")]
    operational_failure = bool(hard_failures) or cap["status"] == "fail"
    if operational_failure:
        status = "operational_failure_stop"
    elif cap["status"] != "pass":
        status = "pending_capability"
    elif not baseline_count["all_returned"]:
        status = "baseline_incomplete"
    elif not intervention_count["returned"]:
        status = "ready_for_intervention"
    elif not intervention_count["all_returned"]:
        status = "intervention_incomplete"
    else:
        status = "exploratory_intervention_complete"
        if any(row["status"] == "invalid" for row in rows):
            status += "_with_unscorable"
    all_returned = len(records) == len(plan["tasks"])
    allowed = mode == "live" and not operational_failure and all_returned
    baseline_allowed = mode == "live" and not operational_failure and baseline_count["all_returned"]
    accuracy, pattern = {}, {}
    for name, first, second in CONTRASTS:
        contrast_allowed = baseline_allowed if name == "direct_minus_visible" else allowed
        accuracy[name] = _contrast(rows, name, first, second, "correct", contrast_allowed)
        pattern[name] = _contrast(rows, name, first, second, "follows_pattern", contrast_allowed)
    usage = Counter()
    observed_models = Counter()
    for attempt in attempts:
        response = attempt.get("response") or {}
        if isinstance(response.get("model"), str):
            observed_models[response["model"]] += 1
        raw_usage = response.get("usage") or {}
        if isinstance(raw_usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if type(raw_usage.get(key)) is int and raw_usage[key] >= 0:
                    usage[key] += raw_usage[key]
    limits = [
        "The primary estimand is bare minus original accuracy. Prediction-wording arms are not pooled. All other contrasts and pattern-choice outcomes are descriptive secondary analyses.",
        "Fresh worlds use supplied early explanation prefixes. This tests the effect of the supplied wording, not whether the wording mediates the model's spontaneous failures or identifies an internal mechanism.",
        "The recorded-fact wording adds semantic guidance and the bare statement changes length. Paraphrase comparisons check wording sensitivity but cannot eliminate all lexical or length differences.",
        "Worlds are the independent units; repeated continuations and two target variants are nested observations. Intervals are unadjusted descriptive whole-world bootstrap intervals, not a significance or pass/fail gate.",
        "Incomplete estimates cannot support the intervention conclusion. Intervals are withheld until every planned response for that contrast has returned. A complete fresh baseline may be described separately while interventions remain incomplete.",
        "Returned invalid answers are retained without replacement. Complete-world comparisons exclude an entire world when a required answer is unscorable. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.",
        "Intervals require at least two complete worlds. Degenerate intervals do not establish certainty or equivalence; no threshold was set for proceeding based on baseline accuracy or intervention effect.",
        "Spontaneous visible explanations are exported without automatic interpretation or selection. Their prose is not a faithful readout of internal model state; subsequent annotations and natural-prefix interventions require a separate fixed protocol.",
    ]
    if operational_failure:
        limits.insert(0, "Operational failure: numerical exports are for audit only and must not be interpreted as a valid intervention experiment.")
    if mode == "mock":
        limits.insert(0, "SIMULATED SOFTWARE FIXTURE: no empirical or model-behavior conclusions are permitted.")
    return {
        "protocol": plan.get("protocol_version", plan.get("protocol")),
        "plan_hash": plan.get("plan_hash"), "mode": mode,
        "is_simulated": mode == "mock",
        "analysis_status": "simulated_" + status if mode == "mock" else status,
        "collection_status": status, "interpretation_allowed": allowed,
        "attempts_total": len(attempts), "planned_calls": len(plan["tasks"]),
        "max_total_attempts": plan["config"]["max_total_attempts"],
        "returned_answers": len(records),
        "valid_answers": sum(record["status"] == "complete" for record in records.values()),
        "invalid_answers_retained": sum(record["status"] == "invalid" for record in records.values()),
        "transport_or_interrupted_attempts": sum(attempt["status"] not in ("complete", "invalid") for attempt in attempts),
        "independent_worlds": len({row["world_id"] for row in rows}),
        "capability_gate": cap, "baseline_completion": baseline_count,
        "intervention_completion": intervention_count, "hard_failures": hard_failures,
        "baseline_interpretation_allowed": baseline_allowed,
        "arm_counts": {arm: _counts([row for row in rows if row["arm"] == arm]) for arm in (*BASE_ARMS, *ARMS)},
        "primary_contrast": accuracy["bare_minus_original"],
        "accuracy_contrasts": accuracy, "pattern_choice_contrasts": pattern,
        "observed_model_counts": dict(observed_models), "reported_usage": dict(usage),
        "usage_note": "Reported usage only; missing usage and timed-out requests may still be billable. No dollar cost is inferred.",
        "answers": rows, "limits": limits,
    }


def _rate(value):
    return "—" if value is None else f"{value:.3f}"


def _interval(value):
    return "—" if value is None else f"[{value[0]:.3f}, {value[1]:.3f}]"


def _fenced(text):
    text = "" if text is None else text
    fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", text)), default=3))
    return [fence + "text", text, fence]


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    result = summarize(plan, attempts, execution["mode"] if execution else "unstarted")
    write_json(output / "summary.json", result)
    write_json(output / "rows.json", result["answers"])
    lines = [
        "# Record-status framing intervention — exploratory", "",
        f"Status: **{result['analysis_status']}**. SIMULATED: **{result['is_simulated']}**.", "",
        f"{result['returned_answers']}/{result['planned_calls']} returned; "
        f"{result['valid_answers']} valid; {result['invalid_answers_retained']} unscorable. "
        f"{result['independent_worlds']} independent worlds, with two target variants per world.", "",
        "The intervention keeps the correct copied class fixed and changes only the parenthetical. "
        "The primary comparison is bare minus original accuracy. Positive values indicate lower accuracy with the original prediction wording.", "",
        "## Collection and interpretation", "",
        f"Capability: {result['capability_gate']['status']}. "
        f"Baseline returned: {result['baseline_completion']['returned']}/{result['baseline_completion']['planned']}. "
        f"Intervention returned: {result['intervention_completion']['returned']}/{result['intervention_completion']['planned']}.", "",
        "Collection of the full baseline permits the intervention regardless of baseline accuracy; there is no behavioral pass gate.", "",
        f"Intervention interpretation permitted: **{result['interpretation_allowed']}**. "
        f"Complete-baseline descriptive interpretation permitted: **{result['baseline_interpretation_allowed']}**.", "",
        "## Arm counts", "",
        "| Arm | Returned / planned | Valid | Correct | Pattern | Other | Invalid | Pending | Accuracy among valid |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, count in result["arm_counts"].items():
        lines.append(f"| {arm} | {count['returned']}/{count['planned']} | {count['valid']} | {count['correct']} | {count['pattern']} | {count['other']} | {count['invalid']} | {count['pending']} | {_rate(count['accuracy_valid_only'])} |")
    for title, key in (("Accuracy contrasts", "accuracy_contrasts"),
                       ("Pattern-choice contrasts (secondary)", "pattern_choice_contrasts")):
        lines += ["", "## " + title, "", "Positive values mean a higher rate in the first arm. "
                  "Average repeats within each variant, then the two variants within each world, then give each complete world equal weight.", "",
                  "| Contrast | World-weighted difference | Descriptive 95% interval | Complete / planned worlds | Full-plan unscorable bounds |",
                  "|---|---:|---|---:|---|"]
        for name, contrast in result[key].items():
            label = name + (" (primary)" if contrast["role"] == "primary" else "")
            lines.append(f"| {label} | {_rate(contrast['mean'])} | {_interval(contrast['descriptive_cluster_bootstrap_95_ci'])} | {contrast['n_worlds']}/{contrast['planned_worlds']} | {_interval(contrast['full_plan_unscorable_bounds'])} |")
    lines += ["", "Intervals use 10,000 whole-world bootstrap resamples, seed 981723; unadjusted and descriptive. "
              "They are withheld until all planned responses in a contrast have returned and at least two complete worlds remain. "
              "Unscorable bounds are point-estimate bounds, not confidence intervals. "
              "Every excluded world, case and task is listed in summary.json.", "",
              "## Interpretation limits", ""]
    lines += ["- " + limit for limit in result["limits"]]
    lines += ["", "rows.json contains all planned task rows, including pending/invalid answers and exact generated text. "
              "spontaneous-visible-traces.md exports every baseline visible explanation without outcome selection. "
              "These files are regenerated; save human annotations under a different filename."]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    trace_lines = ["# Spontaneous visible explanations — audit export", "",
                   f"Status: {result['analysis_status']}. SIMULATED: {result['is_simulated']}.", "",
                   "All baseline visible tasks are included, regardless of correctness. "
                   "These are fresh unprefilled explanations; no automatic semantic labels or eligible-case selection are applied. "
                   "Exact original requests are in preview.json. This regenerated file must not hold manual annotations.", ""]
    for row in result["answers"]:
        if row["arm"] != "visible":
            continue
        trace_lines += ["## " + row["task_id"], "",
                        f"Status: {row['status']}; recorded class: {row['expected']}; pattern class: {row['pattern_label']}; answer: {row['answer']}.", ""]
        trace_lines += _fenced(row["raw_text"]) + [""]
    (output / "spontaneous-visible-traces.md").write_text("\n".join(trace_lines) + "\n")
    return result
