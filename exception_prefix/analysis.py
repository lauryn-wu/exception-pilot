"""Audited descriptive reporting for a bounded native-prefix feasibility bridge.

Practical integer gates determine whether the fixed collection can continue.
They are not significance tests or evidence of an internal mechanism.
"""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from .core import (LABELS, VALUES, capability_gate, phenomenon_gate, replay_gate, task_meta)


BASE_ARMS = ("direct", "visible")
INPUT_MISS_USD_PER_MILLION = 0.30
OUTPUT_USD_PER_MILLION = 1.20
UNCERTAINTY = (
    "Base contrasts use 10,000 whole-world bootstrap resamples, seed 981723, and descriptive "
    "unadjusted 95% intervals. There are 12 world-level units, not 73 independent observations. "
    "Degenerate intervals do not establish certainty or equivalence. Full-base unscorable bounds "
    "are point-estimate bounds, not confidence intervals. Replay agreement on the original "
    "pattern-error subset is a conditional diagnostic, not an estimate of error prevalence."
)
GATE_LIMIT = (
    "All thresholds are fixed practical feasibility rules, not significance thresholds or evidence "
    "of a mechanism. Passing permits design review only; no intervention or stage 2 starts automatically. "
    "A native-prefix replay is a new generation conditioned on saved text, not restoration of the "
    "original hidden state. The requested model alias is not an immutable model snapshot."
)


def average(values):
    return sum(values) / len(values) if values else None


def effect(values):
    interval = None
    if len(values) >= 2:
        if len(set(values)) == 1:
            interval = [values[0], values[0]]
        else:
            rng = random.Random(981723)
            draws = sorted(sum(rng.choices(values, k=len(values))) / len(values)
                           for _ in range(10000))
            interval = [draws[250], draws[9750]]
    return {"mean": average(values), "descriptive_cluster_bootstrap_95_ci": interval,
            "n_worlds": len(values), "positive_worlds": sum(x > 0 for x in values),
            "zero_worlds": sum(x == 0 for x in values), "negative_worlds": sum(x < 0 for x in values)}


def _score(label, row, metric):
    if metric == "accuracy":
        return int(label == row["expected"])
    return 1 if label == row["expected"] else 0 if label == row["pattern_label"] else -1


def _base_analysis(plan, rows, allowed):
    cells = {(row["world_id"], row["value"], row["arm"]): row for row in rows}
    world_ids = [world["id"] for world in plan["worlds"]]
    all_returned = all(row["status"] != "pending" for row in rows)
    metrics = {wid: {} for wid in world_ids}
    effects = {}
    for metric in ("accuracy", "record_sensitivity"):
        for name, arms in (("direct_minus_visible", (("direct", 1), ("visible", -1))),
                           ("direct", (("direct", 1),)), ("visible", (("visible", 1),))):
            key, values, bounds, excluded, missing_tasks = f"{metric}/{name}", [], [], [], []
            for wid in world_ids:
                scores, low, high = [], 0.0, 0.0
                for arm, sign in arms:
                    for value in VALUES:
                        row = cells[wid, value, arm]
                        possibilities = [0.5 * sign * _score(label, row, metric) for label in LABELS]
                        if row["status"] == "complete":
                            score = 0.5 * sign * _score(row["answer"], row, metric)
                            scores.append(score)
                            low += score
                            high += score
                        else:
                            low += min(possibilities)
                            high += max(possibilities)
                            missing_tasks.append(row["task_id"])
                value = sum(scores) if len(scores) == len(VALUES) * len(arms) else None
                metrics[wid][key] = value
                if value is None:
                    excluded.append(wid)
                else:
                    values.append(value)
                bounds.append((low, high))
            effects[key] = {
                **effect(values), "interpretation_allowed": allowed,
                "n_planned_worlds": len(world_ids), "excluded_worlds": len(excluded),
                "excluded_world_ids": excluded, "unscorable_or_pending_task_ids": missing_tasks,
                "weighting": "Equal weight per complete world after averaging its two target variants.",
                "full_plan_unscorable_bounds": [average([b[0] for b in bounds]), average([b[1] for b in bounds])]
                                                if all_returned else None,
            }
            if len(arms) == 2:
                pairs = []
                for wid in world_ids:
                    for value in VALUES:
                        lhs, rhs = cells[wid, value, "direct"], cells[wid, value, "visible"]
                        if lhs["status"] == rhs["status"] == "complete":
                            pairs.append(_score(lhs["answer"], lhs, metric) - _score(rhs["answer"], rhs, metric))
                effects[key].update({"case_weighted_mean": average(pairs), "n_paired_cases": len(pairs),
                    "paired_improved_cases": sum(x > 0 for x in pairs),
                    "paired_unchanged_cases": sum(x == 0 for x in pairs),
                    "paired_worsened_cases": sum(x < 0 for x in pairs)})
    return effects, [{"world_id": wid, "metrics": values} for wid, values in metrics.items()]


def _counts(rows):
    returned = [row for row in rows if row["status"] != "pending"]
    valid = [row for row in rows if row["status"] == "complete"]
    scored = [row for row in valid if row["correct"] is not None]
    return {
        "n_planned": len(rows), "n_returned": len(returned), "n_valid": len(valid),
        "n_invalid": len(returned) - len(valid), "n_pending": len(rows) - len(returned),
        "n_correct": sum(row["correct"] for row in scored),
        "accuracy_valid_only": average([row["correct"] for row in scored]),
        "n_pattern_choices": sum(row["follows_pattern"] == 1 for row in valid),
        "n_format_valid": sum(row["format_valid"] is True for row in returned),
        "n_format_invalid": sum(row["format_valid"] is False for row in returned),
        "n_format_unknown": sum(row["format_valid"] is None for row in returned),
        "n_pre_answer_text": sum(row["pre_answer_text"] is True for row in returned),
        "n_pre_answer_text_false": sum(row["pre_answer_text"] is False for row in returned),
        "n_pre_answer_text_unknown": sum(row["pre_answer_text"] is None for row in returned),
        "answer_counts": {label: sum(row["answer"] == label for row in valid) for label in LABELS},
    }


def _model_observations(plan, attempts):
    observations = []
    for attempt in attempts:
        response = attempt.get("response") or {}
        raw = response.get("raw_response") or {}
        if not isinstance(raw, dict):
            raw = {}
        created = raw.get("created")
        try:
            created_utc = datetime.fromtimestamp(created, timezone.utc).isoformat() if isinstance(created, (int, float)) else None
        except (ValueError, OverflowError, OSError):
            created_utc = None
        observations.append({
            "attempt": attempt.get("attempt"), "task_id": attempt.get("task_id"), "status": attempt["status"],
            "response_id": response.get("response_id"), "returned_model": response.get("model", raw.get("model")),
            "system_fingerprint": response.get("system_fingerprint", raw.get("system_fingerprint")),
            "provider_created": created, "provider_created_utc": created_utc,
            "started_at": attempt.get("started_at"), "finished_at": attempt.get("finished_at"),
        })
    models = Counter(row["returned_model"] for row in observations if isinstance(row["returned_model"], str))
    fingerprints = Counter(row["system_fingerprint"] for row in observations if isinstance(row["system_fingerprint"], str))
    return {
        "requested_alias": plan["config"]["model"], "documentation": plan.get("model_documentation"),
        "immutable_snapshot": False, "observed_model_counts": dict(sorted(models.items())),
        "observed_fingerprint_counts": dict(sorted(fingerprints.items())),
        "n_missing_fingerprints": sum(row["system_fingerprint"] is None for row in observations),
        "n_nonstring_model_values": sum(row["returned_model"] is not None and not isinstance(row["returned_model"], str) for row in observations),
        "n_nonstring_fingerprint_values": sum(row["system_fingerprint"] is not None and not isinstance(row["system_fingerprint"], str) for row in observations),
        "observations": observations,
        "interpretation": "An observed returned model string or fingerprint does not guarantee an immutable implementation. Missing fingerprints are not inferred.",
    }


def _cost(plan, attempts):
    # Malformed provider metadata must not hide the retained operational failure.
    usages = [(attempt.get("response") or {}).get("usage") for attempt in attempts]
    usages = [value if isinstance(value, dict) else {} for value in usages]
    usage = {key: sum(value[key] for value in usages if type(value.get(key)) is int and value[key] >= 0)
             for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    known = sum(all(type(value.get(key)) is int and value[key] >= 0
                    for key in ("prompt_tokens", "completion_tokens")) for value in usages)
    return usage, {
        "currency": "USD", "input_cache_miss_per_million": INPUT_MISS_USD_PER_MILLION,
        "output_per_million": OUTPUT_USD_PER_MILLION,
        "observed_usage_estimate_usd": (usage["prompt_tokens"] * INPUT_MISS_USD_PER_MILLION
                                        + usage["completion_tokens"] * OUTPUT_USD_PER_MILLION) / 1_000_000,
        "n_attempts_with_known_usage": known, "n_attempts_with_unknown_usage": len(attempts) - known,
        "maximum_planned_calls": len(plan["tasks"]), "maximum_attempts": plan["config"]["max_total_attempts"],
        "assumptions": "Estimated from reported token usage at peak published rates, with all input charged at the cache-miss rate and no cache savings assumed. This is not a guaranteed bill or cost cap. Unreported usage, including timed-out requests, can be billable. Actual peak/off-peak prices and cache discounts can differ, and rates can change.",
    }


def summarize(plan, attempts, mode="live"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        meta = task_meta(plan, task, records)
        record = records.get(task["id"])
        valid = bool(record and record["status"] == "complete" and record.get("format_valid") is True)
        if task["family"] != "capability":
            valid = valid and record.get("answer") in LABELS
        answer = record.get("answer") if record else None
        row = {"task_id": task["id"], "family": task["family"], "arm": task["arm"],
               "status": ("complete" if valid else "invalid") if record else "pending", "answer": answer}
        for field in ("world_id", "value", "item_id", "expected", "pattern_label", "target_position",
                      "parent_task_id", "parent_answer", "parent_correct", "parent_pattern_error",
                      "parent_response_id", "parent_response_sha256", "parent_raw_sha256",
                      "prefix_available", "prefix_cut_chars", "prefix_cut_fraction", "prefix_chars",
                      "remaining_reasoning_chars", "remaining_reasoning_words", "prefix_unavailable_reason"):
            row[field] = meta.get(field, task.get(field))
        row.update({
            "correct": int(answer == meta["expected"]) if valid and meta.get("expected") in LABELS else None,
            "follows_pattern": int(answer == meta["pattern_label"]) if valid and meta.get("pattern_label") in LABELS else None,
        })
        for field in ("format_valid", "invalid_reason", "capability_exact", "pre_answer_text",
                      "replay_answer_match", "replay_exact_suffix_match", "replay_pattern_error_match"):
            row[field] = record.get(field) if record else None
        rows.append(row)
    cap_gate, base_gate, rep_gate = capability_gate(plan, records), phenomenon_gate(plan, records), replay_gate(plan, records)
    base_rows = [row for row in rows if row["family"] == "base"]
    replay_rows = [row for row in rows if row["family"] == "replay"]
    invalid = [row for row in rows if row["status"] == "invalid"]
    unavailable = [row for row in replay_rows if row["prefix_available"] is False]
    if cap_gate["status"] == "incomplete":
        underlying_status = "pending_capability"
    elif cap_gate["status"] == "fail":
        underlying_status = "capability_failed_stop"
    elif invalid:
        underlying_status = "operational_invalid_stop"
    elif base_gate["status"] == "incomplete":
        underlying_status = "pending_base"
    elif base_gate["status"] == "fail":
        underlying_status = "phenomenon_not_reproduced_stop"
    elif unavailable:
        underlying_status = "operational_invalid_stop"
    elif rep_gate["status"] == "incomplete":
        underlying_status = "pending_replay"
    elif rep_gate["status"] == "fail":
        underlying_status = "replay_failed_stop"
    else:
        underlying_status = "feasible_for_design_review"
    base_complete = all(row["status"] == "complete" for row in base_rows)
    terminal_descriptive = underlying_status in ("phenomenon_not_reproduced_stop", "replay_failed_stop",
                                                "feasible_for_design_review")
    base_allowed = mode == "live" and terminal_descriptive and cap_gate["status"] == "pass" and base_complete and not invalid
    replay_complete = all(row["status"] == "complete" for row in replay_rows)
    replay_allowed = base_allowed and base_gate["status"] == "pass" and replay_complete and not unavailable
    base_effects, world_metrics = _base_analysis(plan, base_rows, base_allowed)
    base_counts = [{"arm": arm, **_counts([row for row in base_rows if row["arm"] == arm]),
                    "accuracy_complete_world_weighted": base_effects[f"accuracy/{arm}"]["mean"],
                    "record_sensitivity_complete_world_weighted": base_effects[f"record_sensitivity/{arm}"]["mean"],
                    "n_complete_worlds": base_effects[f"accuracy/{arm}"]["n_worlds"]} for arm in BASE_ARMS]
    replay_valid = [row for row in replay_rows if row["status"] == "complete"]
    pattern_rows = [row for row in replay_rows if row["parent_pattern_error"] is True]
    pattern_valid = [row for row in pattern_rows if row["status"] == "complete"]
    replay_counts = {
        **_counts(replay_rows), "n_exact_parent_answer_matches": sum(row["replay_answer_match"] is True for row in replay_valid),
        "answer_agreement_valid_only": average([int(row["replay_answer_match"] is True) for row in replay_valid]),
        "n_exact_suffix_matches": sum(row["replay_exact_suffix_match"] is True for row in replay_valid),
        "exact_suffix_agreement_valid_only": average([int(row["replay_exact_suffix_match"] is True) for row in replay_valid]),
        "n_original_pattern_errors": len(pattern_rows), "n_valid_pattern_error_replays": len(pattern_valid),
        "n_pattern_error_answer_matches": sum(row["replay_pattern_error_match"] is True for row in pattern_valid),
        "pattern_error_agreement_valid_only": average([int(row["replay_pattern_error_match"] is True) for row in pattern_valid]),
        "n_correct_to_correct": sum(row["parent_correct"] == 1 and row["correct"] == 1 for row in replay_valid),
        "n_correct_to_wrong": sum(row["parent_correct"] == 1 and row["correct"] == 0 for row in replay_valid),
        "n_wrong_to_correct": sum(row["parent_correct"] == 0 and row["correct"] == 1 for row in replay_valid),
        "n_wrong_to_wrong": sum(row["parent_correct"] == 0 and row["correct"] == 0 for row in replay_valid),
        "n_parent_correct": sum(row["parent_correct"] == 1 for row in replay_rows),
        "interpretation_allowed": replay_allowed,
    }
    usage, cost = _cost(plan, attempts)
    report = {
        "protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"], "model": plan["config"]["model"],
        "mode": mode, "is_simulated": mode == "mock", "analysis_status": "SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE" if mode == "mock" else underlying_status,
        "underlying_status": underlying_status, "planned_calls": len(rows), "maximum_planned_calls": len(rows),
        "attempts": len(attempts), "max_total_attempts": plan["config"]["max_total_attempts"],
        "returned_answers": sum(row["status"] != "pending" for row in rows),
        "valid_answers": sum(row["status"] == "complete" for row in rows), "invalid_answers": len(invalid),
        "pending_tasks": sum(row["status"] == "pending" for row in rows),
        "provider_errors": sum(a["status"] == "error" for a in attempts), "n_planned_worlds": len(plan["worlds"]),
        "capability_gate": cap_gate, "phenomenon_gate": base_gate, "replay_gate": rep_gate,
        "replay_eligibility": ("not_eligible" if cap_gate["status"] == "fail" or base_gate["status"] == "fail"
                               else "eligible" if cap_gate["status"] == base_gate["status"] == "pass" else "pending"),
        "base_interpretation_allowed": base_allowed, "replay_interpretation_allowed": replay_allowed,
        "interpretation_allowed": replay_allowed, "automatic_stage_2": False,
        "base_effects": base_effects, "base_arm_counts": base_counts, "base_world_metrics": world_metrics,
        "replay_counts": replay_counts, "invalid_outputs": invalid, "unavailable_prefixes": unavailable,
        "answers": rows, "uncertainty": UNCERTAINTY, "gate_interpretation": GATE_LIMIT,
        "model_observations": _model_observations(plan, attempts), "usage": usage, "cost_estimate": cost,
    }
    return report, rows


def _number(value):
    return "—" if value is None else f"{value:.3f}"


def _interval(stats):
    ci = stats["descriptive_cluster_bootstrap_95_ci"]
    return "—" if ci is None else f"[{_number(ci[0])}, {_number(ci[1])}]"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    report, rows = summarize(plan, attempts, execution["mode"] if execution else "not_run")
    write_json(output / "summary.json", report)
    with (output / "answers.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    replay_gate_label = ("not eligible: earlier check failed" if report["replay_eligibility"] == "not_eligible"
                         else report["replay_gate"]["status"])
    lines = ["# Native-prefix feasibility bridge", "", f"Status: **{report['analysis_status']}**", "",
             f"{report['returned_answers']}/{report['maximum_planned_calls']} maximum planned calls returned; "
             f"{report['valid_answers']} valid; {report['invalid_answers']} invalid. "
             "The 24 replays are conditional on passing the capability and base feasibility checks.", "",
             report["gate_interpretation"], "", "## Fixed feasibility checks", "",
             "| Check | Status | Fixed practical requirement |", "|---|---|---|",
             f"| Native-prefix capability | {report['capability_gate']['status']} | Exact fixed synthetic continuation test |",
             f"| Base phenomenon | {report['phenomenon_gate']['status']} | All 48 valid; direct at least 20/24 correct; direct minus visible at least 4 correct answers; at least 4 visible pattern errors across at least 3 worlds |",
             f"| Unchanged prefix replay | {replay_gate_label} | All 24 valid; at least 22 exact parent-answer matches; at least ceiling(0.8 × original visible pattern errors) reproduced |", "",
             "## Base collection and format checks", "",
             "| Arm | Correct / valid / planned | Pattern choices | Format valid / returned | Pre-answer text / returned |",
             "|---|---:|---:|---:|---:|"]
    for row in report["base_arm_counts"]:
        lines.append(f"| {row['arm']} | {row['n_correct']}/{row['n_valid']}/{row['n_planned']} | {row['n_pattern_choices']} | "
                     f"{row['n_format_valid']}/{row['n_returned']} | {row['n_pre_answer_text']}/{row['n_returned']} |")
    if report["is_simulated"]:
        lines += ["", "**Simulated software test only; these are not experimental results.**", "",
                  f"The mock path's underlying collection status is `{report['underlying_status']}`."]
    elif report["underlying_status"] == "capability_failed_stop":
        lines += ["", "**The fixed native-prefix contract check failed.** The exact required suffix was not "
                  "confirmed, so collection stops. This does not show that the provider can never support continuation."]
    elif report["invalid_outputs"] or report["unavailable_prefixes"]:
        lines += ["", "**Operational failure: do not interpret compliant-subset differences as a successful test.** "
                  "Invalid outputs and unavailable prefix cuts are retained in the JSON and CSV; do not resample them."]
    elif not report["base_interpretation_allowed"]:
        lines += ["", "**Incomplete: comparative scientific interpretation is withheld.** Intermediate arithmetic "
                  "in summary.json is for audit only."]
    if report["base_interpretation_allowed"]:
        lines += ["", "## Descriptive base comparisons", "",
                  "Positive direct minus visible favors direct. Both target variants are averaged within each "
                  "world, then complete worlds receive equal weight.", "",
                  "| Metric | Mean | Descriptive 95% interval | Complete worlds | Paired improved / worsened |",
                  "|---|---:|---|---:|---:|"]
        for metric in ("accuracy", "record_sensitivity"):
            stats = report["base_effects"][f"{metric}/direct_minus_visible"]
            lines.append(f"| {metric}: direct minus visible | {_number(stats['mean'])} | {_interval(stats)} | "
                         f"{stats['n_worlds']}/{stats['n_planned_worlds']} | {stats['paired_improved_cases']} / {stats['paired_worsened_cases']} |")
        lines += ["", "Signed record sensitivity gives +0.5 per correctly followed target value, −0.5 for the other "
                  "target label, and 0 for the background pattern. Arm scores range from −1 to +1; contrasts range "
                  "from −2 to +2. Unchanged answers across target edits score 0. Sensitivity changes do not identify "
                  "record retrieval or an internal mechanism."]
        if report["underlying_status"] == "phenomenon_not_reproduced_stop":
            lines += ["", "The complete base collection did not meet the fixed practical behavior threshold. "
                      "Stop this route before replay. This does not refute the earlier GPT-4o results or establish "
                      "that the model never makes these errors."]
    replay = report["replay_counts"]
    lines += ["", "## Replay collection", "",
              f"{replay['n_returned']}/{replay['n_planned']} returned; {replay['n_valid']} valid. "
              "All visible cases were prespecified for replay, including originally correct answers."]
    if report["replay_interpretation_allowed"]:
        lines += ["", f"Exact parent-answer agreement: **{replay['n_exact_parent_answer_matches']}/{replay['n_valid']}**. "
                  f"Original pattern-error answers reproduced: **{replay['n_pattern_error_answer_matches']}/"
                  f"{replay['n_original_pattern_errors']}**. Exact suffix matches, a secondary descriptive measure: "
                  f"**{replay['n_exact_suffix_matches']}/{replay['n_valid']}**.", "",
                  "| Parent → replay correctness | Cases |", "|---|---:|",
                  f"| Correct → correct | {replay['n_correct_to_correct']} |",
                  f"| Correct → wrong | {replay['n_correct_to_wrong']} |",
                  f"| Wrong → correct | {replay['n_wrong_to_correct']} |",
                  f"| Wrong → wrong | {replay['n_wrong_to_wrong']} |", "",
                  "Pattern-error-subset agreement is conditional and descriptive; it does not estimate error "
                  "prevalence. Reproducing an answer does not establish the same internal computation or faithful reasoning."]
    elif report["replay_eligibility"] == "not_eligible":
        lines += ["", "The earlier fixed check failed, so replay is not eligible. The unrun conditional calls "
                  "are a protocol stop, not additional missing observations to collect."]
    else:
        lines += ["", "Replay comparison is withheld until every planned replay is valid and the earlier checks pass. "
                  "Per-case collection and prefix-cut details remain in answers.csv and summary.json."]
    model, cost = report["model_observations"], report["cost_estimate"]
    lines += ["", "## Model and estimated cost", "", f"Requested alias: `{model['requested_alias']}`. "
              "This is not an immutable snapshot guarantee.", "",
              f"Observed returned model strings: {model['observed_model_counts'] or 'none yet'}. "
              f"Observed fingerprints: {model['observed_fingerprint_counts'] or 'none reported'}. "
              "Per-attempt provider and local timestamps are saved in summary.json.", "",
              f"Reported-token estimate at peak rates: **${cost['observed_usage_estimate_usd']:.4f}**. "
              f"{cost['n_attempts_with_unknown_usage']} attempts have unknown reported usage.", "",
              "Rates used: $0.30 per million input tokens at the cache-miss rate and $1.20 per million output tokens. "
              + cost["assumptions"], "", report["uncertainty"], ""]
    if model["documentation"]:
        documentation = model["documentation"]
        lines.insert(lines.index("## Model and estimated cost") + 2,
                     f"Provider documentation recorded with this plan: **{documentation.get('documented_family', 'unspecified')}**, "
                     f"as of **{documentation.get('documentation_as_of', 'unspecified')}**. ")
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
