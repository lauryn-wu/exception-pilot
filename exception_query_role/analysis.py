"""Fixed-stage, world-level analysis of query-conditioned record responsiveness.

Synthetic runs exercise software only. Neither the practical spending screen nor
the descriptive bootstrap establishes novelty, significance, or a mechanism.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import json
import os
from pathlib import Path
import random
import tempfile


QUERIES = ("literal", "encoded", "downstream")
ARMS = ("direct", "visible")
VALUES = ("a", "b")
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 2026101002
FAMILIES = ("vehicle", "configuration")


def _mean(values):
    return sum(values) / len(values) if values else None


def _quantile(ordered, probability):
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


@lru_cache(maxsize=512)
def _bootstrap(groups, samples, seed):
    """Stratify whole eligible worlds, preserving their observed family counts."""
    if not groups or any(len(values) < 2 for _, values in groups):
        return None
    rng = random.Random(seed)
    total = sum(len(values) for _, values in groups)
    draws = []
    for _ in range(samples):
        draws.append(sum(sum(rng.choices(values, k=len(values)))
                         for _, values in groups) / total)
    draws.sort()
    return [_quantile(draws, 0.025), _quantile(draws, 0.975)]


def _accepted(attempts, task_ids):
    records = {}
    for attempt in attempts:
        task_id = attempt.get("task_id")
        if task_id not in task_ids:
            raise ValueError("Attempt refers to an unplanned task")
        if attempt.get("status") not in ("complete", "invalid"):
            continue
        if task_id in records:
            raise ValueError("A returned task was repeated; preserve the original journal")
        records[task_id] = attempt
    return records


def _rows(plan, attempts):
    tasks = plan["tasks"]
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate planned task id")
    records = _accepted(attempts, set(ids))
    rows, cells, world_family = [], {}, {}
    for task in tasks:
        world = task["world_id"]
        family = task["family"]
        if family not in FAMILIES:
            raise ValueError("Unknown task family")
        if world in world_family and world_family[world] != family:
            raise ValueError("A world belongs to two families")
        world_family[world] = family
        cell = (world, task["query"], task["arm"], task["value"])
        if (task["query"] not in QUERIES or task["arm"] not in ARMS
                or task["value"] not in VALUES or cell in cells):
            raise ValueError("Invalid or duplicated world/query/arm/value cell")
        record = records.get(task["id"])
        score = record.get("score") if record else None
        valid = bool(record and record.get("status") == "complete"
                     and record.get("format_valid") is True
                     and type(score) in (int, float) and score in (-1, 0, 1))
        answer = record.get("answer") if record else None
        row = {
            "task_id": task["id"], "world_id": world, "family": family,
            "query": task["query"], "arm": task["arm"], "value": task["value"],
            "status": ("complete" if valid else "invalid") if record else "pending",
            "answer": answer, "score": score if valid else None,
            "decoded_value": record.get("decoded_value") if valid else None,
            "expected": task["expected"], "pattern_label": task["pattern_label"],
            "correct": int(answer == task["expected"]) if valid else None,
            "pattern": int(answer == task["pattern_label"]) if valid else None,
            "invalid_reason": (record.get("invalid_reason") or "invalid_scored_response")
                              if record and not valid else None,
            "direct_instruction_adherent": record.get("direct_instruction_adherent") if record else None,
        }
        rows.append(row)
        cells[cell] = row
    for world in world_family:
        for query in QUERIES:
            for arm in ARMS:
                for value in VALUES:
                    if (world, query, arm, value) not in cells:
                        raise ValueError("Incomplete planned world: all twelve cells are required")
    return rows, cells, world_family


def _counts(rows):
    planned = len(rows)
    valid = [row for row in rows if row["status"] == "complete"]
    returned = sum(row["status"] != "pending" for row in rows)
    correct = sum(row["correct"] for row in valid)
    pattern = sum(row["pattern"] for row in valid)
    unknown = planned - len(valid)
    direct = [row for row in rows if row["arm"] == "direct"]
    adherence_known = [row for row in direct if type(row.get("direct_instruction_adherent")) is bool]
    adherence_yes = sum(row["direct_instruction_adherent"] for row in adherence_known)
    return {
        "planned": planned, "returned": returned, "valid": len(valid),
        "invalid": returned - len(valid), "pending": planned - returned,
        "correct": correct, "pattern": pattern,
        "other": sum(not row["correct"] and not row["pattern"] for row in valid),
        "accuracy_valid_only": correct / len(valid) if valid else None,
        "accuracy_invalid_as_incorrect": correct / planned if planned else None,
        "pattern_rate_valid_only": pattern / len(valid) if valid else None,
        "answer_counts": dict(sorted(Counter(str(row["answer"]) for row in valid).items())),
        "full_plan_accuracy_bounds": [correct / planned, (correct + unknown) / planned]
                                     if planned else None,
        "all_returned": bool(planned and returned == planned),
        "all_valid": bool(planned and len(valid) == planned),
        "direct_instruction_adherence": {
            "planned_direct": len(direct), "known": len(adherence_known), "adherent": adherence_yes,
            "nonadherent": len(adherence_known) - adherence_yes,
            "unknown": len(direct) - len(adherence_known),
            "rate_known_only": adherence_yes / len(adherence_known) if adherence_known else None,
        },
    }


def _coefficients(terms):
    """Expand and combine terms before bounding: shared outcomes are one variable."""
    coefficients = defaultdict(float)
    for query, arm, multiplier in terms:
        coefficients[query, arm, "b"] += multiplier / 2
        coefficients[query, arm, "a"] -= multiplier / 2
    return {key: value for key, value in coefficients.items() if value != 0}


def _metric_specs():
    specs = {f"{query}_{arm}_R": ((query, arm, 1),)
             for query in QUERIES for arm in ARMS}
    for query in QUERIES:
        specs[f"{query}_harm"] = ((query, "direct", 1), (query, "visible", -1))
    specs["primary_D"] = (("downstream", "visible", 1), ("encoded", "visible", -1),
                          ("downstream", "direct", -1), ("encoded", "direct", 1))
    specs["visible_role_gap"] = (("downstream", "visible", 1), ("encoded", "visible", -1))
    specs["direct_role_gap"] = (("downstream", "direct", 1), ("encoded", "direct", -1))
    return specs


def _linear_world(cells, world, coefficients):
    known, radius, missing = 0.0, 0.0, []
    for (query, arm, value), coefficient in coefficients.items():
        row = cells[world, query, arm, value]
        if row["status"] == "complete":
            known += coefficient * row["score"]
        else:
            radius += abs(coefficient)
            missing.append(row["task_id"])
    return {"value": known if not missing else None,
            "bounds": [known - radius, known + radius], "unscorable_or_pending": missing}


def _metric(cells, world_family, terms, all_returned, samples, seed):
    coefficients = _coefficients(terms)
    worlds = {world: _linear_world(cells, world, coefficients) for world in sorted(world_family)}
    complete = {world: result["value"] for world, result in worlds.items() if result["value"] is not None}
    planned_counts = Counter(world_family.values())
    eligible_counts = Counter(world_family[world] for world in complete)
    groups = tuple((family, tuple(complete[world] for world in complete if world_family[world] == family))
                   for family in sorted(planned_counts))
    interval = _bootstrap(groups, samples, seed) if all_returned else None
    return {
        "mean": _mean(list(complete.values())), "n_complete_worlds": len(complete),
        "n_planned_worlds": len(worlds), "world_values": complete,
        "excluded_world_ids": [world for world in worlds if world not in complete],
        "planned_family_counts": dict(planned_counts), "eligible_family_counts": dict(eligible_counts),
        "full_plan_bounds": [_mean([result["bounds"][0] for result in worlds.values()]),
                             _mean([result["bounds"][1] for result in worlds.values()])],
        "world_bounds": {world: result["bounds"] for world, result in worlds.items()},
        "unscorable_or_pending_task_ids": sorted({task for result in worlds.values()
                                                   for task in result["unscorable_or_pending"]}),
        "descriptive_bootstrap_95_interval": interval,
        "interval_status": ("available" if interval is not None else
                            "withheld_incomplete_collection" if not all_returned else
                            "withheld_fewer_than_two_eligible_worlds_in_a_planned_family"),
    }


def _criterion(name, observed, threshold, complete, strict=False):
    passed = None if not complete else bool(observed is not None and
                                            (observed > threshold if strict else observed >= threshold - 1e-12))
    return {"criterion": name, "observed": observed, "operator": ">" if strict else ">=",
            "threshold": threshold, "passed": passed}


def analyze(plan, attempts, execution=None):
    """Describe the frozen 144-call screen; never authorize or execute stage two."""
    attempts = list(attempts)
    rows, cells, world_family = _rows(plan, attempts)
    count = _counts(rows)
    all_returned = count["all_returned"]
    config = plan.get("config", {})
    samples = config.get("bootstrap_samples", BOOTSTRAP_SAMPLES)
    seed = config.get("bootstrap_seed", BOOTSTRAP_SEED)
    if type(samples) is not int or samples < 1 or type(seed) is not int:
        raise ValueError("Invalid bootstrap configuration")
    specs = _metric_specs()
    metrics = {name: _metric(cells, world_family, terms, all_returned, samples, seed)
               for name, terms in specs.items()}
    family_results = {}
    for family in sorted(set(world_family.values())):
        subset = {world: value for world, value in world_family.items() if value == family}
        family_results[family] = {
            "counts": _counts([row for row in rows if row["family"] == family]),
            "metrics": {name: _metric(cells, subset, specs[name], all_returned, samples, seed)
                        for name in ("encoded_harm", "primary_D", "downstream_visible_R")},
        }
    conditions = {query: {arm: _counts([row for row in rows if row["query"] == query and row["arm"] == arm])
                          for arm in ARMS} for query in QUERIES}
    expected_shape = len(rows) == 144 and Counter(world_family.values()) == Counter(vehicle=6, configuration=6)
    criteria = [_criterion("fixed_144_call_12_world_plan", int(expected_shape), 1, all_returned),
                _criterion("scorable_answers", count["valid"], 137, all_returned)]
    for query in QUERIES:
        criteria.append(_criterion(f"{query}_direct_correct_invalid_as_incorrect",
                                    conditions[query]["direct"]["correct"], 22, all_returned))
    for metric, threshold in (("encoded_harm", .15), ("downstream_visible_R", .75), ("primary_D", .15)):
        criteria.append(_criterion(f"{metric}_worst_case_lower_bound", metrics[metric]["full_plan_bounds"][0],
                                    threshold, all_returned))
    for family in FAMILIES:
        for metric in ("encoded_harm", "primary_D"):
            lower = (family_results[family]["metrics"][metric]["full_plan_bounds"][0]
                     if family in family_results else None)
            criteria.append(_criterion(f"{family}_{metric}_worst_case_lower_bound", lower, 0,
                                        all_returned, strict=True))
    mode = (execution or {}).get("mode", "unstarted" if not attempts else "unknown")
    is_simulated = mode in ("mock", "simulated") or any(attempt.get("mode") in ("mock", "simulated")
                                                     for attempt in attempts)
    operational_failures = [{"attempt": attempt.get("attempt"), "task_id": attempt.get("task_id"),
                             "reason": attempt["hard_failure"]}
                            for attempt in attempts if attempt.get("hard_failure")]
    practical_pass = all(criterion["passed"] for criterion in criteria) if all_returned else None
    eligible = bool(practical_pass and not is_simulated and mode == "live" and not operational_failures)
    if operational_failures:
        decision = "operational_stop"
    elif not all_returned:
        decision = "incomplete"
    elif is_simulated or mode != "live":
        decision = "simulated_no_scientific_decision" if is_simulated else "mode_unverified_no_scientific_decision"
    elif practical_pass:
        decision = "eligible_for_separate_heldout_review"
    else:
        decision = "stop_this_screen"
    analysis_status = ("operational_failure_stop" if operational_failures else
                       "incomplete" if not all_returned else
                       "screen_complete_with_unscorable" if count["invalid"] else "screen_complete")
    usage, observed_models = Counter(), Counter()
    for attempt in attempts:
        response = attempt.get("response") or {}
        if isinstance(response.get("model"), str):
            observed_models[response["model"]] += 1
        for key, value in (response.get("usage") or {}).items():
            if key in ("prompt_tokens", "completion_tokens", "total_tokens") and type(value) is int and value >= 0:
                usage[key] += value
    return {
        "protocol": plan.get("protocol", plan.get("protocol_version", "query-conditioned-fact-use-v1")),
        "plan_hash": plan.get("plan_hash"), "analysis_status": analysis_status,
        "collection_status": "complete" if all_returned else "incomplete",
        "interpretation_allowed": bool(all_returned and mode == "live" and not is_simulated and not operational_failures),
        "mode": mode, "is_simulated": is_simulated, "attempts_total": len(attempts),
        "planned_calls": len(rows), "returned_answers": count["returned"],
        "valid_answers": count["valid"], "invalid_answers_retained": count["invalid"],
        "pending_answers": count["pending"], "independent_worlds": len(world_family),
        "counts": count, "conditions": conditions, "metrics": metrics, "families": family_results,
        "screen": {"decision": decision, "practical_criteria_pass": practical_pass,
                   "eligible_for_separate_heldout_review": eligible, "criteria": criteria,
                   "failed_criteria": [criterion["criterion"] for criterion in criteria if criterion["passed"] is False],
                   "statistical_significance_test": False, "automatic_followup_authorized": False},
        "bootstrap": {"samples": samples, "seed": seed,
                      "method": "Unadjusted percentile bootstrap of whole eligible worlds, stratified by family; each family's eligible-world count is preserved.",
                      "weighting": "Equal weight per complete world for each reported metric. Missingness can change eligible-family proportions; counts are reported. Fixed-plan bounds instead weight every planned world equally.",
                      "interpretation": "Descriptive intervals, not gate criteria or confidence intervals for missingness bounds. No interval before collection completes; at least two eligible worlds in every planned family are required. Degenerate intervals do not establish certainty or equivalence."},
        "operational_failures": operational_failures, "observed_models": dict(observed_models),
        "observed_model_counts": dict(observed_models),
        "observed_model": next(iter(observed_models)) if len(observed_models) == 1 else None,
        "usage_all_attempts": dict(usage), "rows": rows,
        "limitations": [
            "The outcome is record-consistent counterfactual responsiveness, not a pure measure of retrieval or internal evidence use. Mapping mistakes remain a competing explanation.",
            "The primary D is the downstream-minus-encoded responsiveness gap under visible reasoning minus that gap under direct answering. Encoded harm and downstream retention are separate required spending criteria.",
            "A returned invalid answer is retained, not replaced. Pending and invalid scores range from -1 to 1 in full-plan bounds. Coefficients are combined before bounding shared outcomes.",
            "Each world is an independent unit; its record variants, queries, and reasoning instructions are paired observations. Component R estimates use complete two-response pairs; contrasts require every response with a nonzero coefficient.",
            "All gate decisions wait for all 144 responses. Thresholds are practical spending rules, not significance tests. A failed screen is insufficient support for the fixed extension, not proof that no effect exists.",
            "The two task families remain close analogues of record lookup. Positive findings cannot establish broad task generality, a novel mechanism, or an internal causal explanation.",
            "Stage two is not implemented or automatically authorized. A passing live screen only supports a separate review of a frozen held-out design.",
        ],
    }


def _number(value):
    return "—" if value is None else f"{value:.3f}"


def _interval(values):
    return "—" if values is None else "[" + ", ".join(_number(value) for value in values) + "]"


def _report(summary):
    counts = summary["counts"]
    lines = ["# Query-conditioned fact use: fixed first-stage screen", "",
             f"Status: **{summary['analysis_status']}**. Screen: **{summary['screen']['decision']}**.", "",
             f"{counts['returned']}/{counts['planned']} returned; {counts['valid']} scorable; "
             f"{counts['invalid']} retained invalid; {counts['pending']} pending. "
             f"{summary['independent_worlds']} independent worlds; {summary['attempts_total']} attempts.", ""]
    if summary["is_simulated"]:
        lines += ["**SIMULATED SOFTWARE CHECK. These answers are not model evidence and cannot authorize scientific continuation.**", ""]
    if not counts["all_returned"]:
        lines += ["Collection is incomplete. Partial estimates describe only the eligible worlds so far; no spending decision is evaluated.", ""]
    lines += ["## Prespecified outcome", "",
              "For counterfactual records a and b, score the decoded answer -1 for source a, +1 for source b, and 0 for the third value. "
              "R = (score_b - score_a) / 2. The primary interaction D = "
              "(R_downstream,visible - R_encoded,visible) - (R_downstream,direct - R_encoded,direct). "
              "Encoded harm = R_encoded,direct - R_encoded,visible. Positive D alone does not establish encoded deterioration.", "",
              "## Response counts", "",
              "| Query | Instruction | Returned / planned | Valid | Correct | Pattern | Other | Accuracy among valid | Direct format adherent / assessed |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for query in QUERIES:
        for arm in ARMS:
            count = summary["conditions"][query][arm]
            adherence = count["direct_instruction_adherence"]
            adherence_text = f"{adherence['adherent']}/{adherence['known']}" if arm == "direct" else "—"
            lines.append(f"| {query} | {arm} | {count['returned']}/{count['planned']} | {count['valid']} | "
                         f"{count['correct']} | {count['pattern']} | {count['other']} | {_number(count['accuracy_valid_only'])} | {adherence_text} |")
    lines += ["", "Direct-instruction adherence is a separate descriptive format check, not a spending criterion; unassessed responses are excluded from its denominator.",
              "", "## World-level outcomes", "",
              "| Metric | Complete worlds / planned | Mean | Descriptive 95% interval | Fixed-plan bounds | Eligible vehicle / configuration |",
              "|---|---:|---:|---|---|---:|"]
    for name, metric in summary["metrics"].items():
        families = metric["eligible_family_counts"]
        lines.append(f"| {name} | {metric['n_complete_worlds']}/{metric['n_planned_worlds']} | {_number(metric['mean'])} | "
                     f"{_interval(metric['descriptive_bootstrap_95_interval'])} | {_interval(metric['full_plan_bounds'])} | "
                     f"{families.get('vehicle', 0)} / {families.get('configuration', 0)} |")
    lines += ["", summary["bootstrap"]["method"], "", summary["bootstrap"]["weighting"], "",
              summary["bootstrap"]["interpretation"], "",
              "Bounds include pending and invalid answers and are extrema of the fixed-plan point estimate, not confidence intervals.", "",
              "## Practical spending criteria", "",
              "The criteria are evaluated only after all planned answers return. Invalid answers count as incorrect in direct-mode accuracy. "
              "Effect criteria use the worst-case lower bound, including within-family criteria. No second-stage calls are run automatically.", "",
              "| Criterion | Observed | Required | Passed |", "|---|---:|---:|---|"]
    for criterion in summary["screen"]["criteria"]:
        passed = "pending" if criterion["passed"] is None else "yes" if criterion["passed"] else "no"
        lines.append(f"| {criterion['criterion']} | {_number(criterion['observed'])} | "
                     f"{criterion['operator']} {_number(criterion['threshold'])} | {passed} |")
    lines += ["", "## Interpretation limits", ""]
    lines += ["- " + value for value in summary["limitations"]]
    if summary["operational_failures"]:
        lines += ["", "Operational failures are recorded in summary.json; they prevent advancement independently of outcome estimates."]
    return "\n".join(lines) + "\n"


def _atomic_text(path, text):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_summary(output):
    """Read/revalidate the journal lazily, then atomically replace both reports."""
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    summary = analyze(plan, attempts, execution)
    _atomic_text(output / "summary.json", json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    _atomic_text(output / "report.md", _report(summary))
    return summary
