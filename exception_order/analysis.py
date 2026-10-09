"""World-paired analysis of answer order under strict structured-output schemas.

Any returned invalid output invalidates the intended output manipulation. Raw
compliant-subset statistics remain auditable in JSON; they are not evidence for
the intended comparison when the output manipulation has failed.
"""

from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path
import random
from statistics import median

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, LABELS, VALUES, task_meta


PRIMARY = "accuracy/answer_first_minus_reasoning_first"
SECONDARY = (
    "accuracy/answer_only_minus_answer_first",
    "accuracy/answer_only_minus_reasoning_first",
)
CONTRASTS = {
    "answer_first_minus_reasoning_first": ("answer_first", "reasoning_first"),
    "answer_only_minus_answer_first": ("answer_only", "answer_first"),
    "answer_only_minus_reasoning_first": ("answer_only", "reasoning_first"),
}

UNCERTAINTY = (
    "10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. "
    "The sampling unit is the world, not an API call. There are 12 fresh worlds from the same task "
    "family and one model; this is not a cross-model replication. Degenerate intervals do not establish "
    "certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals."
)
INTERPRETATION = (
    "If all outputs comply, lower answer-first accuracy than answer-only can show harm before a written "
    "explanation is generated, but the requested task and output schema also differ. Lower reasoning-first "
    "accuracy than answer-first supports an effect of generation order, potentially including early answer commitment, in this interface, "
    "not a unique effect of text self-conditioning or an identified internal mechanism. Reasoning-field "
    "nonemptiness does not establish substantive or faithful reasoning. The first structured answer is final; "
    "no later answer inside reasoning is scored as a revision. An accurate result in all arms of this small study "
    "does not establish equivalence. The changed structured interface does not directly explain earlier "
    "unconstrained results. No scientific pass threshold or outcome-dependent sample extension is applied."
)


def average(values):
    return sum(values) / len(values) if values else None


def effect(values):
    """Unadjusted percentile intervals resample complete world-level scores."""
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


def _invalid_reason(record, arm):
    """Make malformed audit records fail visibly rather than count as compliant."""
    if record.get("invalid_reason"):
        return record["invalid_reason"]
    if record.get("response", {}).get("complete") is False:
        return "incomplete_response"
    if record.get("schema_valid") is not True:
        return "schema_validation_failed" if record.get("schema_valid") is False else "schema_validation_missing"
    if record.get("key_order_valid") is not True:
        return "key_order_validation_failed" if record.get("key_order_valid") is False else "key_order_validation_missing"
    if arm != "answer_only" and record.get("reasoning_nonempty") is not True:
        return "required_reasoning_empty" if record.get("reasoning_nonempty") is False else "reasoning_validation_missing"
    if record.get("answer") not in LABELS:
        return "answer_not_in_schema_enum"
    if record.get("status") != "complete":
        return "returned_invalid_status"
    return None


def summarize(plan, attempts, mode="live"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"])
        meta = task_meta(plan, task)
        answer = record.get("answer") if record else None
        reason = _invalid_reason(record, meta["arm"]) if record else None
        valid = record is not None and reason is None
        rows.append({
            "task_id": task["id"], **meta,
            "status": ("complete" if valid else "invalid") if record else "pending",
            "answer": answer,
            "schema_valid": record.get("schema_valid") if record else None,
            "key_order_valid": record.get("key_order_valid") if record else None,
            "reasoning_nonempty": record.get("reasoning_nonempty") if record else None,
            "reasoning_chars": record.get("reasoning_chars") if record else None,
            "reasoning_words": record.get("reasoning_words") if record else None,
            "invalid_reason": reason,
            "correct": int(answer == meta["expected"]) if valid else None,
            "follows_pattern": int(answer == meta["pattern_label"]) if valid else None,
        })
    by_cell = {(row["world_id"], row["value"], row["arm"]): row for row in rows}
    world_ids = [world["id"] for world in plan["worlds"]]
    n_returned = sum(row["status"] != "pending" for row in rows)
    n_invalid = sum(row["status"] == "invalid" for row in rows)
    all_returned = n_returned == len(rows)
    manipulation_failed = n_invalid > 0
    interpretation_allowed = all_returned and not manipulation_failed and mode == "live"
    status = "complete_ready_for_interpretation" if all_returned else "incomplete"
    if manipulation_failed:
        status = "technical_failure_output_manipulation"
    if mode == "mock":
        status = "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE"

    specifications = {}
    for metric in ("accuracy", "record_sensitivity"):
        for name, (left, right) in CONTRASTS.items():
            specifications[f"{metric}/{name}"] = (metric, ((left, 1), (right, -1)))
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
            "role": ("primary" if name == PRIMARY else "secondary" if len(arms) == 2 else "descriptive"),
            "interpretation_allowed": interpretation_allowed,
            "weighting": "Equal weight per complete world; accuracy first averages its two target-record variants.",
            "n_planned_worlds": len(world_ids), "excluded_worlds": len(excluded),
            "excluded_world_ids": excluded, "n_required_answers": len(world_ids) * len(VALUES) * len(arms),
            "n_scorable_answers": n_scorable, "unscorable_or_pending_task_ids": unscorable_tasks,
            "full_plan_unscorable_bounds": [average([bound[0] for bound in bounds]),
                                             average([bound[1] for bound in bounds])]
                                            if all_returned else None,
        }
    for metric in ("accuracy", "record_sensitivity"):
        for name, (left, right) in CONTRASTS.items():
            paired = []
            for wid in world_ids:
                for value in VALUES:
                    lhs, rhs = by_cell[wid, value, left], by_cell[wid, value, right]
                    if lhs["status"] == "complete" and rhs["status"] == "complete":
                        def case_score(row):
                            if metric == "accuracy":
                                return row["correct"]
                            return 1 if row["correct"] else 0 if row["follows_pattern"] else -1
                        paired.append(case_score(lhs) - case_score(rhs))
            effects[f"{metric}/{name}"].update({
                "case_weighted_mean": average(paired), "n_paired_cases": len(paired),
                "paired_improved_cases": sum(value > 0 for value in paired),
                "paired_unchanged_cases": sum(value == 0 for value in paired),
                "paired_worsened_cases": sum(value < 0 for value in paired),
                "paired_count_interpretation": ("Improvement means higher correctness." if metric == "accuracy" else
                                                "Improvement means higher signed sensitivity contribution: correct +1, pattern 0, other record label -1."),
                "case_weighting": "All compliant paired variants, including those in otherwise incomplete worlds.",
            })

    arm_counts, pair_counts, reasoning_lengths = [], [], []
    for arm in ARMS:
        members = [row for row in rows if row["arm"] == arm]
        returned = [row for row in members if row["status"] != "pending"]
        valid = [row for row in members if row["status"] == "complete"]
        arm_counts.append({
            "arm": arm, "n_planned": len(members), "n_returned": len(returned), "n_valid": len(valid),
            "n_invalid": len(returned) - len(valid), "n_pending": len(members) - len(returned),
            "n_schema_valid": sum(row["schema_valid"] is True for row in returned),
            "n_schema_invalid": sum(row["schema_valid"] is False for row in returned),
            "n_schema_unknown": sum(row["schema_valid"] is None for row in returned),
            "n_key_order_valid": sum(row["key_order_valid"] is True for row in returned),
            "n_key_order_invalid": sum(row["key_order_valid"] is False for row in returned),
            "n_key_order_unknown": sum(row["key_order_valid"] is None for row in returned),
            "n_reasoning_required_returned": len(returned) if arm != "answer_only" else 0,
            "n_reasoning_nonempty": sum(row["reasoning_nonempty"] is True for row in returned),
            "n_reasoning_empty": sum(row["reasoning_nonempty"] is False for row in returned),
            "n_reasoning_unknown": sum(row["reasoning_nonempty"] is None for row in returned) if arm != "answer_only" else 0,
            "n_reasoning_not_required": len(returned) if arm == "answer_only" else 0,
            "invalid_reason_counts": dict(sorted(Counter(row["invalid_reason"] for row in returned
                                                         if row["status"] == "invalid").items())),
            "n_correct": sum(row["correct"] for row in valid),
            "accuracy_valid_only_case_weighted": average([row["correct"] for row in valid]),
            "accuracy_complete_world_weighted": effects[f"accuracy/{arm}"]["mean"],
            "n_complete_worlds": effects[f"accuracy/{arm}"]["n_worlds"],
            "n_pattern_choices": sum(row["follows_pattern"] for row in valid),
            "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in LABELS},
        })
        lengths = {"arm": arm, "reasoning_required": arm != "answer_only",
                   "interpretation": "Descriptive observed string lengths; not reasoning quality, faithfulness, or an adjusted causal mediator."}
        for field in ("reasoning_chars", "reasoning_words"):
            measured = [row[field] for row in returned if row[field] is not None]
            valid_measured = [row[field] for row in valid if row[field] is not None]
            lengths[field] = {
                "n_measured_returned": len(measured), "mean": average(measured),
                "median": median(measured) if measured else None,
                "min": min(measured) if measured else None, "max": max(measured) if measured else None,
                "n_measured_valid": len(valid_measured), "mean_valid_only": average(valid_measured),
            }
        reasoning_lengths.append(lengths)
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
    invalid_outputs = [{"task_id": row["task_id"], "arm": row["arm"], "invalid_reason": row["invalid_reason"]}
                       for row in rows if row["status"] == "invalid"]
    report = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
        "model": plan["config"]["model"], "mode": mode, "is_simulated": mode == "mock",
        "analysis_status": status, "interpretation_allowed": interpretation_allowed,
        "output_manipulation_failed": manipulation_failed,
        "output_manipulation_status": ("failed" if manipulation_failed else
                                       "complete_compliant" if all_returned else "pending"),
        "planned_calls": len(rows), "attempts": len(attempts),
        "max_total_attempts": plan["config"]["max_total_attempts"],
        "returned_answers": n_returned, "valid_answers": n_returned - n_invalid,
        "invalid_answers": n_invalid, "pending_tasks": len(rows) - n_returned,
        "schema_valid_answers": sum(row["schema_valid"] is True for row in rows),
        "invalid_reason_counts": dict(sorted(Counter(row["invalid_reason"] for row in invalid_outputs).items())),
        "invalid_outputs": invalid_outputs,
        "provider_errors": sum(attempt["status"] == "error" for attempt in attempts),
        "n_planned_worlds": len(world_ids), "primary_effect": PRIMARY, "secondary_effects": list(SECONDARY),
        "analysis_plan": plan.get("analysis_plan"),
        "effects": effects, "arm_counts": arm_counts, "record_pair_counts": pair_counts,
        "reasoning_lengths": reasoning_lengths,
        "world_metrics": [{"world_id": wid, "metrics": metrics} for wid, metrics in world_metrics.items()],
        "answers": rows, "uncertainty": UNCERTAINTY, "interpretation": INTERPRETATION,
        "failure_policy": "Any returned invalid output is retained and never resampled. Wrong schema, wrong key order, empty required reasoning, or any other returned invalidity causes a technical/output-manipulation failure even if other answers comply. Compliant-subset estimates and bounds in this JSON are audit diagnostics only when interpretation_allowed is false; do not use them to claim a successful manipulation or an answer-order effect.",
        "usage": {key: sum((attempt.get("response", {}).get("usage") or {}).get(key, 0) or 0
                           for attempt in attempts)
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
    }
    return report, rows


def _number(value):
    return "—" if value is None else f"{value:.3f}"


def _interval(stats):
    interval = stats["descriptive_cluster_bootstrap_95_ci"]
    return "—" if interval is None else f"[{_number(interval[0])}, {_number(interval[1])}]"


def write_summary(output, plan=None, attempts=None, mode="live"):
    """Write an audited saved run, or an already-validated plan and journal."""
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
    lines = ["# Structured answer order: fresh-world diagnostic", "",
             f"Status: **{report['analysis_status']}**", "",
             f"{report['returned_answers']}/{report['planned_calls']} returned; "
             f"{report['valid_answers']} valid; {report['invalid_answers']} invalid; "
             f"{report['pending_tasks']} pending.", "",
             f"The fixed sample contains {report['n_planned_worlds']} fresh worlds, two target-record variants, "
             "and three arms per world. These worlds come from the same task family and model. "
             "Partial outcomes must not determine whether to extend collection.", "",
             "## Output compliance", "",
             "Answer-only requires one answer field. The other arms require answer and reasoning fields in "
             "the assigned order, with a nonempty reasoning string. Wrong schema, wrong key order, empty "
             "required reasoning, or another returned invalidity causes a technical/output-manipulation stop. "
             "The returned output is retained and never resampled. Only the first structured answer is scored; "
             "an answer mentioned later in reasoning cannot revise it.", "",
             "| Arm | Returned / planned | Valid | Schema valid / returned | Key order valid / returned | Nonempty reasoning / required returned | Invalid |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["arm_counts"]:
        reasoning = (f"{row['n_reasoning_nonempty']}/{row['n_reasoning_required_returned']}"
                     if row["arm"] != "answer_only" else "not required")
        lines.append(f"| {row['arm']} | {row['n_returned']}/{row['n_planned']} | {row['n_valid']} | "
                     f"{row['n_schema_valid']}/{row['n_returned']} | "
                     f"{row['n_key_order_valid']}/{row['n_returned']} | {reasoning} | {row['n_invalid']} |")
    lines += ["", "Schema validity is structural and can be true even when the required key order or "
              "reasoning presence fails. Nonempty reasoning is an output check; it does not establish "
              "substantive reasoning or a faithful description of internal computation. Unknown checks "
              "are counted separately in the JSON.", "",
              "## Descriptive reasoning lengths", "",
              "| Arm | Measured returned outputs | Mean characters | Median characters | Mean whitespace-separated words |",
              "|---|---:|---:|---:|---:|"]
    for row in report["reasoning_lengths"]:
        chars, words = row["reasoning_chars"], row["reasoning_words"]
        lines.append(f"| {row['arm']} | {chars['n_measured_returned']} | {_number(chars['mean'])} | "
                     f"{_number(chars['median'])} | {_number(words['mean'])} |")
    lines += ["", "Lengths describe validated reasoning strings, including any present in outputs with another "
              "compliance failure. Answer-only has no reasoning field. Lengths are not evidence of reasoning "
              "quality, a causal mediator, or a reason to exclude or resample outputs."]
    if report["is_simulated"]:
        lines += ["", "**Simulated software test only. These outputs are not experimental evidence.**"]
    if report["invalid_outputs"]:
        lines += ["", "**The output manipulation failed. Do not interpret this run as evidence for or against the "
                  "intended answer-order effect.** Compliant-subset arithmetic and full-plan bounds, when available, "
                  "remain in summary.json for audit only.", "", "| Task | Arm | Invalid reason |", "|---|---|---|"]
        for row in report["invalid_outputs"]:
            reason = str(row["invalid_reason"]).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {row['task_id']} | {row['arm']} | {reason} |")
    elif not report["is_simulated"] and not report["interpretation_allowed"]:
        lines += ["", "**Incomplete: do not interpret the partial outcome.** Intermediate arithmetic is retained "
                  "in summary.json for audit, and full-plan bounds are withheld until all planned responses return."]
    if report["interpretation_allowed"]:
        lines += ["", "## Paired accuracy contrasts", "",
                  "Answer-first minus reasoning-first is primary. The answer-only comparisons are secondary. "
                  "Positive values favor the first arm. Each world first averages its two target-record "
                  "variants; complete worlds then receive equal weight.", "",
                  "| Contrast | Role | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |",
                  "|---|---|---:|---|---:|---:|"]
        for name in CONTRASTS:
            stats = report["effects"][f"accuracy/{name}"]
            lines.append(f"| {name} | {stats['role']} | {_number(stats['mean'])} | {_interval(stats)} | "
                         f"{stats['n_worlds']}/{stats['n_planned_worlds']} | "
                         f"{stats['paired_improved_cases']} / {stats['paired_worsened_cases']} |")
        lines += ["", "## Answer counts", "",
                  "| Arm | Correct / valid | Accuracy | Pattern choices |", "|---|---:|---:|---:|"]
        for row in report["arm_counts"]:
            lines.append(f"| {row['arm']} | {row['n_correct']}/{row['n_valid']} | "
                         f"{_number(row['accuracy_valid_only_case_weighted'])} | {row['n_pattern_choices']} |")
        lines += ["", "## Secondary signed record sensitivity", "",
                  "| Effect | Mean | Descriptive 95% interval | Complete worlds |", "|---|---:|---|---:|"]
        for name, stats in report["effects"].items():
            if name.startswith("record_sensitivity/"):
                lines.append(f"| {name.removeprefix('record_sensitivity/')} | {_number(stats['mean'])} | "
                             f"{_interval(stats)} | {stats['n_worlds']}/{stats['n_planned_worlds']} |")
        lines += ["", "Each followed target label contributes +0.5, the other target label −0.5, and the "
                  "background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. "
                  "An unchanged answer across target-record variants scores 0. This score is not accuracy.", "",
                  "## Target-record pairs", "",
                  "| Arm | Complete worlds | Both correct | Both wrong | Answer changed | Answer unchanged | Pattern both |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for row in report["record_pair_counts"]:
            lines.append(f"| {row['arm']} | {row['n_complete_worlds']} | {row['n_both_correct']} | "
                         f"{row['n_both_wrong']} | {row['n_answer_changed']} | {row['n_answer_unchanged']} | "
                         f"{row['n_pattern_both']} |")
        lines += ["", "Changed answers alone do not establish record retrieval: editing the target also changes "
                  "table-level label counts, and each cell has one sampled completion.", "", report["interpretation"]]
    lines += ["", report["uncertainty"], "",
              "Each estimate excludes a world if any required answer is pending or invalid. The JSON records "
              "excluded worlds and task IDs, paired-case counts for every contrast, and full-plan bounds once all "
              "planned responses return. An invalid answer cannot be assigned a class by extracting one from "
              "malformed or noncompliant text. Estimates are audit diagnostics only whenever interpretation_allowed "
              "is false. No automatic scientific pass gate or sample extension is applied.", ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
