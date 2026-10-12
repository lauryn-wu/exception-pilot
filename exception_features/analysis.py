"""World-paired estimates and an explicitly manual, blinded prose audit."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import itertools
import json
from pathlib import Path
import random
import statistics
from exception_pilot.storage import accepted_records, write_json
from . import core


def estimate(values):
    n = len(values)
    if not n:
        return {"estimate": None, "ci95": None, "complete_worlds": 0}
    if len(set(values)) == 1:
        interval = [values[0], values[0]]
    else:
        rng = random.Random(981723)
        means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
        def percentile(p):
            at = (len(means) - 1) * p
            lo = int(at)
            return means[lo] + (means[min(lo + 1, len(means) - 1)] - means[lo]) * (at - lo)
        interval = [percentile(.025), percentile(.975)]
    return {"estimate": statistics.mean(values), "ci95": interval, "complete_worlds": n,
            "positive_worlds": sum(v > 0 for v in values), "negative_worlds": sum(v < 0 for v in values),
            "tied_worlds": sum(v == 0 for v in values), "degenerate_interval": interval[0] == interval[1]}


def estimands():
    # Terms are (record, cue, arm, outcome, weight), retaining dependencies exactly.
    out = {}
    for arm in core.ARMS:
        cue = [(record, setting, arm, "signed", direction / 4)
               for record in core.RECORDS for setting, direction in (("favor_1", 1), ("favor_2", -1))]
        out[f"cue_sensitivity/{arm}"] = cue
        out[f"record_sensitivity/{arm}"] = [(record, setting, arm, "signed", direction / 6)
               for setting in core.CUES for record, direction in (("record_1", 1), ("record_2", -1))]
        for setting in core.CUES:
            out[f"accuracy/{setting}/{arm}"] = [(record, setting, arm, "accuracy", .5) for record in core.RECORDS]
            out[f"record_sensitivity/{setting}/{arm}"] = [(record, setting, arm, "signed", direction / 2)
               for record, direction in (("record_1", 1), ("record_2", -1))]
        for alignment in ("aligned", "opposed"):
            pairs = (("record_1", "favor_1"), ("record_2", "favor_2")) if alignment == "aligned" else (("record_1", "favor_2"), ("record_2", "favor_1"))
            out[f"accuracy/{alignment}/{arm}"] = [(record, cue, arm, "accuracy", .5) for record, cue in pairs]
        out[f"alignment_advantage/{arm}"] = out[f"accuracy/aligned/{arm}"] + [(r,c,a,m,-w) for r,c,a,m,w in out[f"accuracy/opposed/{arm}"]]
    out["cot_minus_direct_cue_sensitivity"] = out["cue_sensitivity/cot"] + [(r,c,a,m,-w) for r,c,a,m,w in out["cue_sensitivity/direct"]]
    out["copy_minus_cot_cue_sensitivity"] = out["cue_sensitivity/copy_class"] + [(r,c,a,m,-w) for r,c,a,m,w in out["cue_sensitivity/cot"]]
    out["copy_minus_cot_record_sensitivity"] = out["record_sensitivity/copy_class"] + [(r,c,a,m,-w) for r,c,a,m,w in out["record_sensitivity/cot"]]
    return out


def outcome(answer, world, record, metric):
    if metric == "accuracy":
        return int(answer == world["roles"][record])
    return 1 if answer == world["roles"]["record_1"] else -1 if answer == world["roles"]["record_2"] else 0


def paired_statistics(plan, records):
    result = {}
    for name, terms in estimands().items():
        world_values, bounds, details = [], [], []
        for world in plan["worlds"]:
            # Combine duplicate task terms before bounding; one answer cannot vary twice.
            per_task = {}
            for record, cue, arm, metric, weight in terms:
                task_id = f"{world['id']}/{record}/{cue}/{arm}"
                per_task.setdefault(task_id, []).append((record, metric, weight))
            total = low = high = 0.
            complete = True
            for task_id, subterms in per_task.items():
                rec = records.get(task_id, {})
                answer = rec.get("answer") if rec.get("status") == "complete" else None
                def value(label):
                    return sum(weight * outcome(label, world, record, metric) for record, metric, weight in subterms)
                if answer in ("A", "B", "C"):
                    contribution = value(answer)
                    total += contribution; low += contribution; high += contribution
                else:
                    complete = False
                    possible = [value(label) for label in "ABC"]
                    low += min(possible); high += max(possible)
            if complete: world_values.append(total)
            bounds.append((low, high))
            details.append({"world_id": world["id"], "estimate": total if complete else None, "bounds": [low, high]})
        result[name] = {**estimate(world_values), "full_plan_bounds": [statistics.mean(x[i] for x in bounds) for i in (0,1)], "worlds": details}
    return result


def response_rows(plan, records):
    rows = []
    for task in plan["tasks"]:
        record = records.get(task["id"], {})
        meta = core.task_meta(plan, task)
        valid = record.get("status") == "complete"
        answer = record.get("answer") if valid else None
        response = record.get("response", {})
        rows.append({**meta, "status": record.get("status", "unreturned"), "answer": answer,
            "correct": answer == meta["expected"] if valid else None,
            "pattern_choice": answer == meta["pattern_label"] if valid else None,
            "favored_choice": answer == meta["favored_label"] if valid and meta["favored_label"] else None,
            "copied": record.get("copied"), "copy_valid": record.get("copy_valid"),
            "copy_correct": record.get("copied") == meta["expected"] if task["arm"] == "copy_class" and record else None,
            "contract_met": record.get("contract_met", False), "model_identity": response.get("model_identity"),
            "text": response.get("text", "")})
    return rows


def transition_rows(plan, records):
    rows = []
    for world in plan["worlds"]:
        for arm in core.ARMS:
            comparisons = [("cue", record, "favor_1", "favor_2", f"{world['id']}/{record}/favor_1/{arm}", f"{world['id']}/{record}/favor_2/{arm}") for record in core.RECORDS]
            comparisons += [("record", cue, "record_1", "record_2", f"{world['id']}/record_1/{cue}/{arm}", f"{world['id']}/record_2/{cue}/{arm}") for cue in core.CUES]
            for kind, held, first, second, first_id, second_id in comparisons:
                recs = [records.get(x, {}) for x in (first_id, second_id)]
                valid = all(r.get("status") == "complete" for r in recs)
                answers = [r.get("answer") if r.get("status") == "complete" else None for r in recs]
                rows.append({"world_id": world["id"], "arm": arm, "comparison": kind, "held_fixed": held,
                    "first_condition": first, "second_condition": second, "first_task_id": first_id, "second_task_id": second_id,
                    "first_status": recs[0].get("status", "unreturned"), "second_status": recs[1].get("status", "unreturned"),
                    "first_answer": answers[0], "second_answer": answers[1], "paired_valid": valid,
                    "answer_changed": answers[0] != answers[1] if valid else None})
    return rows


def summarize(plan, execution, attempts):
    records = accepted_records(attempts)
    rows = response_rows(plan, records)
    cells = {}
    for cue, arm in itertools.product(core.CUES, core.ARMS):
        subset = [r for r in rows if (r["cue"], r["arm"]) == (cue, arm)]
        valid = sum(r["status"] == "complete" for r in subset)
        correct = sum(r["correct"] is True for r in subset)
        cells[f"{cue}/{arm}"] = {"planned": len(subset), "returned": sum(r["status"] != "unreturned" for r in subset),
            "valid": valid, "invalid": sum(r["status"] == "invalid" for r in subset), "correct": correct,
            "accuracy_valid_only": correct / valid if valid else None,
            "full_plan_accuracy_bounds": [correct / len(subset), (correct + len(subset) - valid) / len(subset)],
            "pattern_choices": sum(r["pattern_choice"] is True for r in subset), "favored_choices": sum(r["favored_choice"] is True for r in subset),
            "answer_counts": dict(Counter(r["answer"] for r in subset if r["answer"])),
            "correct_copies": sum(r["copy_correct"] is True for r in subset) if arm == "copy_class" else None,
            "correct_copy_wrong_final": sum(r["copy_correct"] is True and r["correct"] is False for r in subset) if arm == "copy_class" else None,
            "correct_copy_invalid_final": sum(r["copy_correct"] is True and r["status"] == "invalid" for r in subset) if arm == "copy_class" else None,
            "contracts_met": sum(r["contract_met"] for r in subset)}
    mode = execution["mode"] if execution else None
    invalid = sum(r["status"] == "invalid" for r in rows)
    identity_failures = sum(r["model_identity"] in ("missing", "mismatch") for r in rows)
    status = ("simulated_only" if mode == "mock" else "not_started" if not mode else "model_identity_failure" if identity_failures else
              "incomplete" if len(records) < len(rows) else "exploratory_complete_with_invalids" if invalid else "exploratory_complete")
    summary = {"protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"], "model": plan["config"]["model"],
        "analysis_status": status, "is_simulated": mode == "mock", "evidence_label": "SIMULATED — NOT MODEL EVIDENCE" if mode == "mock" else "LIVE" if mode else "NOT STARTED",
        "planned_calls": len(rows), "returned_answers": len(records), "valid_answers": sum(r["status"] == "complete" for r in rows),
        "invalid_answers": invalid, "attempts": len(attempts), "cells": cells, "metrics": paired_statistics(plan, records),
        "semantic_coding_status": "unreviewed; no automatic semantic findings", "primary_metric": "cot_minus_direct_cue_sensitivity"}
    return summary, rows, transition_rows(plan, records)


CODING_FIELDS = ("false_missing", "false_cell", "false_match", "claimed_support")


def review_packet(plan, records):
    packet, key = [], []
    for task in plan["tasks"]:
        rec = records.get(task["id"])
        if not rec: continue
        text = rec.get("response", {}).get("text", "")
        reasoning = core.reasoning_text(text)
        if not reasoning: continue
        review_id = hashlib.sha256(("feature-prose-review|" + task["id"]).encode()).hexdigest()[:16]
        packet.append({"review_id": review_id, "target_id": core.world_for(plan, task)["target_id"],
            "reasoning": reasoning, "ground_truth_table": core.table_text(plan, task),
            "coding": {field: None for field in CODING_FIELDS}, "reviewer": None, "notes": None})
        key.append({"review_id": review_id, **core.task_meta(plan, task), "response_status": rec["status"],
                    "copied": rec.get("copied"), "answer": rec.get("answer")})
    random.Random(873125).shuffle(packet)
    return packet, key


def validate_coding(packet, coding):
    expected = {row["review_id"]: row for row in packet}
    if not isinstance(coding, list) or len({row.get("review_id") for row in coding}) != len(coding):
        raise ValueError("Coding must be a list with unique review IDs")
    counts = {field: {"reviewed": 0, "present": 0, "absent": 0, "unreviewed": len(packet)} for field in CODING_FIELDS}
    for entry in coding:
        if entry.get("review_id") not in expected:
            raise ValueError("Unknown review ID")
        original = expected[entry["review_id"]]
        for frozen in ("reasoning", "target_id", "ground_truth_table"):
            if entry.get(frozen) != original[frozen]: raise ValueError("Blinded source content changed")
        codes = entry.get("coding", {})
        if set(codes) != set(CODING_FIELDS): raise ValueError("Coding fields differ")
        any_reviewed = any(value is not None for value in codes.values())
        if any_reviewed and (not isinstance(entry.get("reviewer"), str) or not entry["reviewer"].strip()):
            raise ValueError("Reviewed entries require reviewer identity")
        for field, value in codes.items():
            if value is None: continue
            if not isinstance(value, dict) or set(value) != {"present", "quotes", "notes"} or type(value["present"]) is not bool:
                raise ValueError("Each reviewed code needs present(bool), quotes(list), notes(string)")
            quotes = value["quotes"]
            if not isinstance(quotes, list) or not quotes or any(not isinstance(q, str) or not q.strip() or q not in original["reasoning"] for q in quotes):
                raise ValueError("Reviewed coding requires nonempty exact evidence quotes")
            if not isinstance(value["notes"], str) or not value["notes"].strip():
                raise ValueError("Reviewed coding requires explanatory notes")
            counts[field]["reviewed"] += 1
            counts[field]["unreviewed"] -= 1
            counts[field]["present" if value["present"] else "absent"] += 1
    return {"status": "manual_provisional", "total_reasoning_responses": len(packet), "fields": counts,
            "limitation": "Quoted manual judgments are provisional factual/claimed-support codes, not validated measurements of latent reasoning."}


def write_csv(path, rows):
    if not rows: return
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def code_review(output, coding_path):
    from exception_study_support.runner import read_run
    plan, execution, attempts = read_run(core, output)
    packet, _ = review_packet(plan, accepted_records(attempts))
    coding = json.loads(Path(coding_path).read_text())
    result = validate_coding(packet, coding)
    write_json(Path(output) / "reasoning-coding-summary.json", result)
    return result


def write_summary(output):
    from exception_study_support.runner import read_run
    plan, execution, attempts = read_run(core, output)
    output = Path(output)
    summary, rows, transitions = summarize(plan, execution, attempts)
    write_json(output / "summary.json", summary)
    with (output / "responses.jsonl").open("w") as stream:
        for row in rows: stream.write(json.dumps(row) + "\n")
    write_csv(output / "responses.csv", [{k:v for k,v in row.items() if k != "text"} for row in rows])
    write_csv(output / "paired-transitions.csv", transitions)
    packet, key = review_packet(plan, accepted_records(attempts))
    write_json(output / "reasoning-review-template.json", packet)
    write_json(output / "reasoning-review-key.json", key)
    lines = ["# Feature support and recorded classes", "", f"**{summary['evidence_label']}** — {summary['model']}", "",
        f"Returned {summary['returned_answers']}/648, valid {summary['valid_answers']}, retained invalid {summary['invalid_answers']}. Status: {summary['analysis_status']}.", "",
        "Thirty-six fresh worlds; all 18 cells/world are paired. This tests deliberately structured competing cues. It does not by itself explain the earlier random-column benefit.", "",
        "Primary: cot-minus-direct cue sensitivity. Positive means the secondary bundle allocation changes reasoning answers more than direct answers.", "",
        "| Condition | Correct / valid | Pattern choices | Correct copy → wrong final |", "|---|---:|---:|---:|"]
    for name, cell in summary["cells"].items():
        lines.append(f"| {name} | {cell['correct']}/{cell['valid']} | {cell['pattern_choices']} | {cell['correct_copy_wrong_final']} |")
    lines += ["", "Intervals use 10,000 whole-world bootstrap resamples. All intervals are descriptive and unadjusted; complete-world denominators are contrast-specific. Full-plan bounds vary invalid/unreturned answers over A/B/C and are not confidence intervals. Degenerate intervals do not establish equivalence.", "",
        "| Contrast | Estimate | 95% interval | Complete worlds | Full-plan bounds |", "|---|---:|---|---:|---|"]
    for name, stat in summary["metrics"].items():
        lines.append(f"| {name} | {stat['estimate']} | {stat['ci95']} | {stat['complete_worlds']} | {stat['full_plan_bounds']} |")
    lines += ["", "Favor-1 versus favor-2 holds every pattern-class row fixed. The balanced record-cue reference also changes those rows: it is a balanced-support reference, not a pure removal of one cue.", "",
        "Semantic judgments are not automatically generated. Copy reasoning-review-template.json to a separate coding file and annotate using FEATURES_PROTOCOL.md. The template removes the initial COPIED line and terminal answer and omits assigned condition/arm; prose and the truth table may still reveal them. This is partial blinding. Keep reasoning-review-key.json separate until coding is finished.", ""]
    (output / "summary.md").write_text("\n".join(lines))
    return summary
