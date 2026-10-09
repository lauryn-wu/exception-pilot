"""World-paired analysis of cue instructions under a strict answer-only schema.

Any returned invalid output invalidates the intended output manipulation. Raw
compliant-subset statistics remain auditable in JSON; they are not evidence for
the intended comparison when the output manipulation has failed.
"""

from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, LABELS, VALUES, task_meta


PRIMARY = "accuracy/direct_minus_cue"
SECONDARY = "record_sensitivity/direct_minus_cue"
CONTRASTS = {"direct_minus_cue": ("direct", "cue")}

UNCERTAINTY = (
    "10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. "
    "The sampling unit is the world, not an API call. These reuse the earlier cue worlds, so this "
    "is an exploratory follow-up, not a fresh-data replication. Degenerate intervals do not establish "
    "certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals."
)
INTERPRETATION = (
    "If every output complies, a positive direct-minus-cue effect under this constrained interface "
    "would show that a generated written explanation is not necessary for the instruction effect "
    "in this interface. A null or uncertain effect does not show that written reasoning caused "
    "the earlier harm: the constrained format can change strategy. Neither result identifies "
    "hidden reasoning, task selection, or a neural mechanism. Correct answers do not by themselves "
    "establish record retrieval. No scientific pass threshold, automatic sample extension, or "
    "comparison to an unconstrained visible-explanation arm is applied."
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


def _invalid_reason(record):
    """Make malformed audit records fail visibly rather than count as compliant."""
    if record.get("invalid_reason"):
        return record["invalid_reason"]
    if record.get("response", {}).get("complete") is False:
        return "incomplete_response"
    if record.get("schema_valid") is not True:
        return "schema_validation_failed" if record.get("schema_valid") is False else "schema_validation_missing"
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
        reason = _invalid_reason(record) if record else None
        valid = record is not None and reason is None
        rows.append({
            "task_id": task["id"], **meta,
            "status": ("complete" if valid else "invalid") if record else "pending",
            "answer": answer,
            "schema_valid": record.get("schema_valid") if record else None,
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
        specifications[f"{metric}/direct_minus_cue"] = (metric, (("direct", 1), ("cue", -1)))
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
            "role": "primary" if name == PRIMARY else "secondary" if name == SECONDARY else "descriptive",
            "interpretation_allowed": interpretation_allowed,
            "weighting": "Equal weight per complete world; accuracy first averages its two target-record variants.",
            "n_planned_worlds": len(world_ids), "excluded_worlds": len(excluded),
            "excluded_world_ids": excluded, "n_required_answers": len(world_ids) * len(VALUES) * len(arms),
            "n_scorable_answers": n_scorable, "unscorable_or_pending_task_ids": unscorable_tasks,
            "full_plan_unscorable_bounds": [average([bound[0] for bound in bounds]),
                                             average([bound[1] for bound in bounds])]
                                            if all_returned else None,
        }
    paired = []
    for wid in world_ids:
        for value in VALUES:
            left, right = by_cell[wid, value, "direct"]["correct"], by_cell[wid, value, "cue"]["correct"]
            if left is not None and right is not None:
                paired.append(left - right)
    effects[PRIMARY].update({
        "case_weighted_mean": average(paired), "n_paired_cases": len(paired),
        "paired_improved_cases": sum(value > 0 for value in paired),
        "paired_unchanged_cases": sum(value == 0 for value in paired),
        "paired_worsened_cases": sum(value < 0 for value in paired),
        "case_weighting": "All compliant paired variants, including those in otherwise incomplete worlds.",
    })

    arm_counts, pair_counts = [], []
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
            "invalid_reason_counts": dict(sorted(Counter(row["invalid_reason"] for row in returned
                                                         if row["status"] == "invalid").items())),
            "n_correct": sum(row["correct"] for row in valid),
            "accuracy_valid_only_case_weighted": average([row["correct"] for row in valid]),
            "accuracy_complete_world_weighted": effects[f"accuracy/{arm}"]["mean"],
            "n_complete_worlds": effects[f"accuracy/{arm}"]["n_worlds"],
            "n_pattern_choices": sum(row["follows_pattern"] for row in valid),
            "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in LABELS},
        })
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
        "n_planned_worlds": len(world_ids), "primary_effect": PRIMARY, "secondary_effect": SECONDARY,
        "analysis_plan": plan.get("analysis_plan"),
        "effects": effects, "arm_counts": arm_counts, "record_pair_counts": pair_counts,
        "world_metrics": [{"world_id": wid, "metrics": metrics} for wid, metrics in world_metrics.items()],
        "answers": rows, "uncertainty": UNCERTAINTY, "interpretation": INTERPRETATION,
        "failure_policy": "Any returned invalid output is retained and never resampled. It causes a technical/output-manipulation failure even if other answers comply. Compliant-subset estimates and bounds in this JSON are audit diagnostics only when interpretation_allowed is false; do not use them to claim a successful manipulation or cue effect.",
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
    lines = ["# Reasoning cue under a constrained answer-only interface", "",
             f"Status: **{report['analysis_status']}**", "",
             f"{report['returned_answers']}/{report['planned_calls']} returned; "
             f"{report['valid_answers']} valid; {report['invalid_answers']} invalid; "
             f"{report['pending_tasks']} pending.", "",
             f"This exploratory follow-up reuses the {report['n_planned_worlds']} earlier cue worlds, "
             "with two target-record variants and two arms per world. It is not a fresh-data replication. "
             "Partial outcomes must not determine whether to extend collection.", "",
             "## Output compliance", "",
             "Both arms require one JSON object containing only an answer field with A, B, or C. "
             "Any returned invalid output causes a technical/output-manipulation stop; it is retained and never resampled.", "",
             "| Arm | Returned / planned | Valid | Schema valid / returned | Invalid | Pending |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in report["arm_counts"]:
        lines.append(f"| {row['arm']} | {row['n_returned']}/{row['n_planned']} | {row['n_valid']} | "
                     f"{row['n_schema_valid']}/{row['n_returned']} | {row['n_invalid']} | {row['n_pending']} |")
    if report["invalid_outputs"]:
        lines += ["", "**The output manipulation failed. Do not interpret this run as evidence for or against the "
                  "intended cue effect.** Compliant-subset arithmetic and full-plan bounds, when available, "
                  "remain in summary.json for audit only.", "", "| Task | Arm | Invalid reason |", "|---|---|---|"]
        for row in report["invalid_outputs"]:
            reason = str(row["invalid_reason"]).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {row['task_id']} | {row['arm']} | {reason} |")
    elif report["is_simulated"]:
        lines += ["", "**Simulated software test only. These outputs are not experimental evidence.**"]
    elif not report["interpretation_allowed"]:
        lines += ["", "**Incomplete: do not interpret the partial outcome.** Intermediate arithmetic is retained "
                  "in summary.json for audit, and full-plan bounds are withheld until all planned responses return."]
    else:
        stats = report["effects"][PRIMARY]
        lines += ["", "## Primary paired accuracy contrast", "",
                  "Positive direct minus cue favors direct. Each world first averages its two target-record "
                  "variants; complete worlds then receive equal weight.", "",
                  "| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |",
                  "|---|---:|---|---:|---:|",
                  f"| direct_minus_cue | {_number(stats['mean'])} | {_interval(stats)} | "
                  f"{stats['n_worlds']}/{stats['n_planned_worlds']} | "
                  f"{stats['paired_improved_cases']} / {stats['paired_worsened_cases']} |", "",
                  "## Answer counts", "",
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
                  "table-level label counts, and each cell has one sampled completion."]
    lines += ["", report["uncertainty"], "",
              "Each estimate excludes a world if any required answer is pending or invalid. The JSON records "
              "excluded worlds and task IDs, paired-case counts, and full-plan bounds once all planned responses "
              "return. An invalid answer cannot be assigned a class by extracting one from malformed text.", "",
              report["interpretation"], ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
