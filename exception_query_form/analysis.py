"""Whole-world paired estimates, missing-data bounds and a spending decision."""
from collections import Counter
import csv
import math
from pathlib import Path
import random
import statistics

from code_rationales import summary_table, write_audit
from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, write_json
from .core import ARMS, DECISION_RULE, PREDICTIONS, QUERIES, VALUES, task_meta


def sign_test(values):
    positive = sum(v > 1e-12 for v in values)
    negative = sum(v < -1e-12 for v in values)
    n = positive + negative
    p = min(1., 2 * sum(math.comb(n, k) for k in range(min(positive, negative) + 1)) / 2 ** n) if n else 1.
    return {"p_two_sided": p, "positive": positive, "negative": negative, "ties": len(values) - n}


def percentile(ordered, q):
    position = (len(ordered) - 1) * q
    left = int(position)
    return ordered[left] + (ordered[min(left + 1, len(ordered) - 1)] - ordered[left]) * (position - left)


def estimate(values):
    if not values:
        return {"estimate": None, "ci95": None, "complete_worlds": 0, "sign_test": sign_test([])}
    n = len(values)
    if min(values) == max(values):
        ci = [values[0], values[0]]
    else:
        rng = random.Random(981723)
        draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
        ci = [percentile(draws, .025), percentile(draws, .975)]
    return {"estimate": statistics.mean(values), "ci95": ci, "complete_worlds": n, "sign_test": sign_test(values)}


def estimands():
    result = {f"{q}/{a}": {(q, a): 1} for q in QUERIES for a in ARMS}
    for q in QUERIES:
        for comparison in ("visible", "filler"):
            result[f"{q}_direct_minus_{comparison}"] = {(q, "direct"): 1, (q, comparison): -1}
    result["interaction"] = {("profile", "direct"): 1, ("profile", "visible"): -1,
                             ("key", "direct"): -1, ("key", "visible"): 1}
    return result


def record_score(answer, expected, pattern, metric):
    if metric == "accuracy":
        return int(answer == expected)
    return 1 if answer == expected else 0 if answer == pattern else -1


def paired_statistics(plan, records):
    tasks = {(t["world_id"], t["value"], t["query"], t["arm"]): t for t in plan["tasks"]}
    result = {}
    for metric in ("accuracy", "record_sensitivity"):
        result[metric] = {}
        for name, coefficients in estimands().items():
            complete_values, bounds, by_world = [], [], []
            for world in plan["worlds"]:
                observed, lower, upper, complete = 0., 0., 0., True
                for (query, arm), coefficient in coefficients.items():
                    for value in VALUES:
                        task = tasks[(world["id"], value, query, arm)]
                        record = records.get(task["id"], {})
                        answer = record.get("answer") if record.get("status") == "complete" else None
                        expected, pattern = world["roles"][value], world["roles"]["pattern"]
                        coefficient_half = coefficient / 2
                        if answer in ("A", "B", "C"):
                            score = coefficient_half * record_score(answer, expected, pattern, metric)
                            observed += score
                            lower += score
                            upper += score
                        else:
                            complete = False
                            possibilities = [coefficient_half * record_score(label, expected, pattern, metric) for label in "ABC"]
                            lower += min(possibilities)
                            upper += max(possibilities)
                bounds.append((lower, upper))
                by_world.append({"world_id": world["id"], "value": observed if complete else None, "bounds": [lower, upper]})
                if complete:
                    complete_values.append(observed)
            stat = estimate(complete_values)
            stat["full_plan_bounds"] = [statistics.mean(b[i] for b in bounds) for i in (0, 1)]
            stat["worlds"] = by_world
            result[metric][name] = stat
    return result


def local_decision(summary):
    if summary["is_simulated"]:
        return "simulated_only"
    if summary["returned_answers"] != summary["planned_calls"]:
        return "incomplete"
    if summary["model_identity_failures"]:
        return "model_identity_failure"
    controls = summary["controls"]
    if (any(controls[q + "/filler"]["filler_exact_fraction"] < .95 for q in QUERIES)
            or any(controls[q + "/visible"]["pretext_fraction"] < .95 for q in QUERIES)):
        return "output_manipulation_inconclusive"
    stats = summary["metrics"]["record_sensitivity"]
    if stats["interaction"]["complete_worlds"] < 22:
        return "insufficient_complete_worlds"
    def clear_harm(name):
        stat = stats[name]
        return stat["ci95"] is not None and stat["full_plan_bounds"][0] > .10 and stat["ci95"][0] > 0
    if any(clear_harm(q + "_direct_minus_filler") for q in QUERIES):
        return "stop_tokens_account_live"
    if all(clear_harm(q + "_direct_minus_visible") for q in QUERIES):
        return "stop_query_form"
    # Equal failure in both key arms must not count as retained record use.
    # Full-plan accuracy bounds count missing/invalid responses as incorrect.
    if any(summary["metrics"]["accuracy"][cell]["full_plan_bounds"][0]
           < DECISION_RULE["minimum_accuracy_lower_bound"]
           for cell in DECISION_RULE["competence_cells"]):
        return "insufficient_record_competence"
    interaction = stats["interaction"]
    eligible = (stats["profile_direct_minus_visible"]["full_plan_bounds"][0] >= .30
                and stats["key_direct_minus_visible"]["full_plan_bounds"][1] <= .10
                and interaction["full_plan_bounds"][0] >= .20
                and interaction["sign_test"]["p_two_sided"] < .05
                and all(stats[q + "_direct_minus_filler"]["full_plan_bounds"][1] <= .10 for q in QUERIES))
    return "eligible_for_dose_review" if eligible else "inconclusive"


def combine_decisions(first, second=None):
    if first["is_simulated"] or second is not None and second["is_simulated"]:
        return "simulated_only"
    if second is None:
        return "awaiting_replication" if first["local_decision"] == "eligible_for_dose_review" else first["local_decision"]
    if (first["plan_hash"] != second["plan_hash"] or
            {first["model"], second["model"]} != {"gpt-4o-2024-08-06", "mistral-small-2603"}):
        return "replication_identity_mismatch"
    decisions = {first["local_decision"], second["local_decision"]}
    if decisions == {"eligible_for_dose_review"}:
        return "proceed_to_dose"
    for decision in ("incomplete", "model_identity_failure", "output_manipulation_inconclusive",
                     "insufficient_complete_worlds", "stop_tokens_account_live", "stop_query_form",
                     "insufficient_record_competence"):
        if decision in decisions:
            return decision
    return "inconclusive"


def summarize(plan, config, execution, attempts):
    records = accepted_records(attempts)
    valid = [r for r in records.values() if r["status"] == "complete"]
    controls = {}
    for q in QUERIES:
        for arm in ARMS:
            tasks = [t for t in plan["tasks"] if t["query"] == q and t["arm"] == arm]
            returned = [records[t["id"]] for t in tasks if t["id"] in records]
            n = len(tasks)
            tokens = [r["response"]["usage"].get("completion_tokens") for r in returned]
            tokens = [t for t in tokens if type(t) is int]
            words = [r["pre_answer_words"] for r in returned if r.get("pre_answer_words") is not None]
            controls[q + "/" + arm] = {
                "planned": n, "returned": len(returned), "valid": sum(r["status"] == "complete" for r in returned),
                "invalid": sum(r["status"] == "invalid" for r in returned), "unreturned": n - len(returned),
                "pattern_choices": sum(r.get("answer") == r["meta"]["pattern_label"] for r in returned),
                "strict_answer_matches": sum(r.get("strict_answer_match") is True for r in returned),
                "answer_only_count": sum(r.get("answer_only") is True for r in returned),
                "contract_met_count": sum(r.get("output_contract_met") is True for r in returned),
                "pretext_fraction": sum(r.get("pre_answer_text") is True for r in returned) / n,
                "filler_exact_fraction": sum(r.get("filler_exact") is True for r in returned) / n if arm == "filler" else None,
                "median_pre_answer_words": statistics.median(words) if words else None,
                "median_completion_tokens": statistics.median(tokens) if tokens else None}
    result = {"protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"],
              "config_hash": digest(config), "model": config["model"], "provider": config["provider"],
              "mode": execution["mode"] if execution else "not_started", "is_simulated": bool(execution and execution["mode"] == "mock"),
              "evidence_label": "SIMULATED — software fixture, not model evidence" if execution and execution["mode"] == "mock" else "LIVE" if execution else "NOT STARTED",
              "attempts": len(attempts), "returned_answers": len(records), "valid_answers": len(valid),
              "invalid_answers": len(records) - len(valid), "planned_calls": len(plan["tasks"]),
              "transport_errors": sum(r["status"] == "error" for r in attempts),
              "unresolved_attempts": sum(r["status"] == "started" for r in attempts),
              "model_identity_failures": sum(r["response"]["model"] != config["model"] for r in records.values()) if execution and execution["mode"] == "live" else 0,
              "analysis_status": "complete" if len(records) == len(plan["tasks"]) else "incomplete",
              "controls": controls, "metrics": paired_statistics(plan, records),
              "predictions": PREDICTIONS, "decision_rule": DECISION_RULE}
    result["local_decision"] = local_decision(result)
    result["decision"] = combine_decisions(result)
    return result


def fmt(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output, replication=None):
    from .runner import read_run
    output = Path(output)
    plan, config, execution, attempts = read_run(output)
    result = summarize(plan, config, execution, attempts)
    if replication is not None:
        other_plan, other_config, other_execution, other_attempts = read_run(replication)
        other = summarize(other_plan, other_config, other_execution, other_attempts)
        result["decision"] = combine_decisions(result, other)
        result["replication"] = {"output": str(Path(replication).resolve()), **{k: other[k] for k in (
            "plan_hash", "config_hash", "model", "mode", "returned_answers", "local_decision")}}
    records = accepted_records(attempts)
    coded = write_audit(plan, records, output.name, output / "rationales")
    wrong = [r for r in coded if not r["correct"]]
    result["rationale_codes"] = {"scorable_visible": len(coded), "wrong_visible": len(wrong),
        "wrong_never_or_missing_share": sum(r["class"] in ("never_stated", "relabeled_missing") for r in wrong) / len(wrong) if wrong else None,
        "by_cell_outcome": [{"query": q, "correct": correct, "counts": dict(Counter(r["class"] for r in coded if r["query"] == q and r["correct"] == correct))}
                            for q in QUERIES for correct in (True, False)],
        "provisional_automated_only": True}
    answer_rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"], {})
        meta = task_meta(plan, task)
        answer_rows.append({"task_id": task["id"], **meta, "status": record.get("status", "unreturned"),
                           "answer": record.get("answer"), "correct": record.get("answer") == meta["expected"] if record.get("answer") else None,
                           **{k: record.get(k) for k in ("strict_answer_match", "pre_answer_text", "answer_only", "output_contract_met", "filler_exact", "pre_answer_words")}})
    with (output / "answers.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(answer_rows[0]))
        writer.writeheader()
        writer.writerows(answer_rows)
    write_json(output / "summary.json", result)
    lines = ["# Query form × response", "", f"**{result['evidence_label']}** — {config['model']}", "",
             f"Returned {result['returned_answers']}/288; valid {result['valid_answers']}; retained invalid {result['invalid_answers']}; attempts {len(attempts)}/316.",
             f"Decision: `{result['decision']}`. Local decision: `{result['local_decision']}`. "
             "This is a predeclared spending rule, not a mechanism or equivalence claim. No extension or outcome-selected worlds.", "",
             "Record sensitivity averages +1 (target label), −1 (other target label), 0 (pattern) across variants, range [−1,1]. "
             "Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples, seed 981723. "
             "Sign tests test sign balance among nontied complete worlds. Unadjusted secondary tests are descriptive. "
             "Full-plan bounds vary every missing/invalid answer over A/B/C; they are not confidence intervals. "
             "Constant samples have degenerate bootstrap intervals and do not prove equivalence.", ""]
    for metric, stats in result["metrics"].items():
        lines += ["## " + metric, "", "| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |", "|---|---:|---|---:|---:|---|---|"]
        for name, stat in stats.items():
            ci = "—" if stat["ci95"] is None else ", ".join(fmt(v) for v in stat["ci95"])
            signs = stat["sign_test"]
            lines.append(f"| {name} | {fmt(stat['estimate'])} | {ci} | {stat['complete_worlds']} | {fmt(signs['p_two_sided'])} | {signs['positive']} / {signs['negative']} / {signs['ties']} | " + ", ".join(fmt(v) for v in stat["full_plan_bounds"]) + " |")
    lines += ["", "## Predictions alongside estimates", "", "| Prediction | Predeclared statement | Estimate |", "|---|---|---|"]
    stats = result["metrics"]["record_sensitivity"]
    observed = {"P1": fmt(stats["profile_direct_minus_visible"]["estimate"]),
                "P2": fmt(stats["key_direct_minus_visible"]["estimate"]),
                "P3": fmt(stats["interaction"]["estimate"]) + "; p=" + fmt(stats["interaction"]["sign_test"]["p_two_sided"]),
                "P4": "; ".join(q + "=" + fmt(stats[q + "_direct_minus_filler"]["estimate"]) for q in QUERIES),
                "P5": fmt(result["rationale_codes"]["wrong_never_or_missing_share"]) + " (automated; not a gate)",
                "P6": fmt(stats["interaction"]["estimate"]) + " for this model; compare both live summaries"}
    lines += [f"| {key} | {text} | {observed[key]} |" for key, text in PREDICTIONS.items()]
    lines += ["", "## Output controls", "", "| Cell | Pattern | Invalid | Unreturned | Contract met / 48 | Exact filler fraction | Median pre-answer words | Median completion tokens |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cell, control in result["controls"].items():
        lines.append(f"| {cell} | {control['pattern_choices']} | {control['invalid']} | {control['unreturned']} | {control['contract_met_count']} | {fmt(control['filler_exact_fraction'])} | {fmt(control['median_pre_answer_words'])} | {fmt(control['median_completion_tokens'])} |")
    lines += ["", "The filler is same-response neutral copying, not a pure token/computation control. "
              "Input length, instructions and generated content differ. Noncompliance remains data. "
              "Visible pretext need not be faithful reasoning; length is observed, not conditioned on.", "", "## Provisional rationale coding", "",
              summary_table(coded, True), "", "See rationales/rationales.csv for legacy flags and evidence excerpts. "
              "Coding is a text audit and has not been validated by independent blinded human annotators.", ""]
    (output / "summary.md").write_text("\n".join(lines))
    return result
