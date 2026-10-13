"""Paired world-level interaction with explicit missingness and manual-review traces."""

from collections import Counter
import csv
import json
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from .core import ANALYSIS_PLAN, CONDITIONS, VALUES, task_meta
from .scoring import CATEGORIES


def quantile(sorted_values, p):
    index = (len(sorted_values) - 1) * p
    low = int(index)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (index - low) * (sorted_values[high] - sorted_values[low])


def world_interactions(plan, records):
    """Each contrast is formed from all eight cells of one world, before sampling."""
    by_cell = {(t["world_id"], t["value"], t["instruction"], t["interface"]): records[t["id"]]
               for t in plan["tasks"] if t["id"] in records}
    results = []
    for world in plan["worlds"]:
        means = {}
        for instruction, interface in CONDITIONS:
            cells = [by_cell.get((world["id"], value, instruction, interface)) for value in VALUES]
            if any(cell is None for cell in cells):
                break
            means[f"{instruction}/{interface}"] = sum(c["first_correct"] for c in cells) / 2
        if len(means) == 4:
            contrast = ((means["initial_answer/json"] - means["copy_record/json"])
                        - (means["initial_answer/text"] - means["copy_record/text"]))
            results.append({"world_id": world["id"], "condition_means": means, "interaction": contrast})
    return results


def bootstrap_worlds(worlds, seed, n_resamples):
    """Resample world contrasts, algebraically identical to retaining their paired 8 cells."""
    if not worlds:
        raise ValueError("No complete worlds")
    values = [w["interaction"] for w in worlds]
    rng = random.Random(seed)
    draws = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n_resamples))
    return {"estimate": sum(values) / len(values),
            "ci95": [quantile(draws, 0.025), quantile(draws, 0.975)],
            "resampling_unit": "whole_world", "n_worlds": len(values),
            "resamples": n_resamples, "seed": seed,
            "percentile_method": "linear interpolation at (n-1)*p"}


def summarize(plan, attempts, mode):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"])
        row = {"task_id": task["id"], **task_meta(plan, task), "returned": record is not None}
        if record is not None:
            row.update({k: record[k] for k in (
                "first_emitted", "first_value_raw", "first_value_lexeme", "first_value", "first_category",
                "first_correct", "output_contract_met", "answer", "reasoning", "final_correct",
                "correct_first_wrong_final")})
        rows.append(row)
    cells = {}
    for instruction, interface in CONDITIONS:
        group = [r for r in rows if (r["instruction"], r["interface"]) == (instruction, interface)]
        returned = [r for r in group if r["returned"]]
        n = len(returned)
        categories = Counter(r["first_category"] for r in returned)
        final_known = sum(r["answer"] is not None for r in returned)
        final_correct = sum(r["final_correct"] is True for r in returned)
        first_correct = sum(r["first_correct"] for r in returned)
        transition_eligible = sum(r["first_correct"] and r["answer"] is not None for r in returned)
        transition_count = sum(r["correct_first_wrong_final"] for r in returned)
        cells[f"{instruction}/{interface}"] = {
            "planned": len(group), "returned": n, "missing": len(group) - n,
            "first_categories": {c: categories[c] for c in CATEGORIES},
            "first_correct": first_correct,
            "first_accuracy_returned": first_correct / n if n else None,
            "output_contract_met": sum(r["output_contract_met"] for r in returned),
            "final_correct": final_correct, "final_scored": final_known,
            "final_absent_or_unparseable": n - final_known,
            "final_accuracy_returned": final_correct / n if n else None,
            "final_accuracy_scored": final_correct / final_known if final_known else None,
            "correct_first_wrong_final": transition_count,
            "correct_first_with_scored_final": transition_eligible,
            "correct_first_without_scored_final": first_correct - transition_eligible,
            "transition_rate_scored": transition_count / transition_eligible if transition_eligible else None,
        }
    full_coverage = len(records) == len(plan["tasks"])
    identity_ok = not any(r["response"]["model_mismatch"] for r in records.values())
    complete_worlds = world_interactions(plan, records)
    primary_status = ("INCOMPLETE" if not full_coverage else
                      "BLOCKED_MODEL_IDENTITY" if not identity_ok else "COMPLETE")
    primary = {"status": primary_status, "formula": ANALYSIS_PLAN["primary"],
               "estimate": None, "ci95": None, "complete_worlds": len(complete_worlds),
               "planned_worlds": 24, "positive_means": ANALYSIS_PLAN["positive"],
               "seed": plan["config"]["bootstrap_seed"],
               "resamples": plan["config"]["bootstrap_resamples"]}
    if primary_status == "COMPLETE":
        primary.update(bootstrap_worlds(complete_worlds, primary["seed"], primary["resamples"]))
    analysis_status = ("SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE" if mode == "mock" else primary_status)
    report = {"experiment_id": plan["experiment_id"], "protocol_version": plan["protocol_version"],
              "plan_hash": plan["plan_hash"], "mode": mode or "unstarted", "analysis_status": analysis_status,
              "interpretation_allowed": mode == "live" and primary_status == "COMPLETE",
              "planned_calls": len(plan["tasks"]), "attempts": len(attempts),
              "returned_answers": len(records), "missing_responses": len(plan["tasks"]) - len(records),
              "transport_errors": sum(a["status"] == "error" for a in attempts),
              "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
              "model_identity_ok": identity_ok,
              "valid_answers": sum(r["output_contract_met"] for r in records.values()),
              "invalid_answers": sum(not r["output_contract_met"] for r in records.values()),
              "primary": primary, "conditions": cells, "world_interactions": complete_worlds,
              "source_provenance": plan["source_provenance"], "analysis_plan": plan["analysis_plan"],
              "limits": ["Diagnostic using previously examined worlds; not independent confirmation.",
                         "Interface package includes formatting instructions and schema constraints.",
                         "Equal completion-token caps do not guarantee equal reasoning lengths.",
                         "Percentile intervals can be degenerate; they do not establish equivalence.",
                         "Condition accuracies use returned-response denominators; transport failures are missing.",
                         "Final accuracy over returned responses counts missing final fields as unsuccessful; scored-final accuracy is also shown.",
                         "No automatic contradiction-recognition labels or follow-up calls."]}
    return report, rows


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    mode = execution["mode"] if execution else None
    report, rows = summarize(plan, attempts, mode)
    write_json(output / "summary.json", report)
    write_json(output / "scored_trials.json", rows)
    lines = ["# Instruction × output-interface diagnostic", "", f"Status: **{report['analysis_status']}**",
             f"Primary report: **{report['primary']['status']}**", "",
             f"Coverage: {report['returned_answers']}/192 returned responses; "
             f"{report['missing_responses']} missing; {report['transport_errors']} transport errors.", "",
             "Primary: `(initial − copy)JSON − (initial − copy)text`.",
             "Positive values mean JSON increases copying's disadvantage.", "",
             f"Estimate: {report['primary']['estimate']}; 95% whole-world percentile CI: {report['primary']['ci95']}",
             "", "| Condition | Returned/48 | Correct first | Final correct/scored | Contract met | Correct first → wrong final |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, cell in report["conditions"].items():
        lines.append(f"| {name} | {cell['returned']}/48 | {cell['first_correct']} | "
                     f"{cell['final_correct']}/{cell['final_scored']} | {cell['output_contract_met']} | "
                     f"{cell['correct_first_wrong_final']} |")
    lines += ["", "All first-entry categories and denominators appear in summary.json.", "",
              "Manual review: traces.jsonl contains complete requests, raw responses and all attempts for every planned trial. "
              "manual_review_template.csv is a blank coding sheet; save edits under another name (analysis regenerates the template).", ""]
    lines += ["- " + limit for limit in report["limits"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    by_task = {t["id"]: [] for t in plan["tasks"]}
    for attempt in attempts:
        by_task[attempt["task_id"]].append(attempt)
    with (output / "traces.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            trace = {**row, "request": plan["requests"][row["task_id"]],
                     "attempts": by_task[row["task_id"]],
                     "manual_contradiction_recognition": None, "manual_review_notes": ""}
            stream.write(json.dumps(trace, ensure_ascii=False, allow_nan=False) + "\n")
    with (output / "manual_review_template.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["task_id", "returned", "contradiction_recognition", "supporting_excerpt", "notes"])
        for row in rows:
            writer.writerow([row["task_id"], row["returned"], "", "", ""])
    return report
