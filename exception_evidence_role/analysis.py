"""World-paired estimates, contrasts, bounds, transitions and textual diagnostics."""

from collections import Counter
from functools import lru_cache
import math
from pathlib import Path
import random
from statistics import median

from exception_pilot.storage import accepted_records, write_json
from .core import (ANALYSIS_PLAN, CLASS_CONDITIONS, CONDITIONS, COPY_CONDITIONS,
                   ORDERS, PRIMARY, VALUES, task_meta)
from .rationales import code_text, write_csv, write_review

UNCERTAINTY = (
    "10,000 whole-world bootstrap resamples, seed 981723, descriptive unadjusted 95% percentile intervals. "
    "Each world first averages its two record variants. The exact two-sided sign test omits ties "
    "and tests sign balance, not mean magnitude. Only the declared primary is primary; all other "
    "contrasts are secondary/descriptive. Complete-world estimates exclude a world if any required "
    "answer is invalid or pending. Full-plan bounds range those answers over all three labels and "
    "are not confidence intervals. Degenerate intervals do not establish certainty or equivalence."
)
INTERPRETATION = (
    "All conditions use the same fixed row-10 tables, schema fields and permission to differ. "
    "Only entry instructions and schema property order vary. These are effects of instructions "
    "and output interfaces; they do not identify hidden beliefs, mediation by reasoning text, "
    "or effects across row positions. The whole schema is visible before the first entry, so "
    "order may affect that entry too. Wrong copies and first-entry format failures remain in "
    "final-answer estimates. Correct-to-wrong transitions are descriptive, never a selection rule. "
    "The no-entry control still writes null; it is not a format-identical replication of earlier "
    "plain-text direct/CoT arms. Audit-marker copying is an active instruction, not a proven "
    "neutral attention control. No outcome authorizes more calls automatically."
)


@lru_cache(maxsize=512)
def interval(values):
    if len(values) < 2:
        return None
    if len(set(values)) == 1:
        return [values[0], values[0]]
    rng = random.Random(981723)
    draws = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(10000))
    return [draws[250], draws[9750]]


def effect(values, sign_test=True):
    values = tuple(values)
    positive = sum(x > 0 for x in values)
    negative = sum(x < 0 for x in values)
    n = positive + negative
    p = (min(1.0, 2 * sum(math.comb(n, k) for k in range(min(positive, negative) + 1)) / 2**n)
         if n else 1.0)
    return {"mean": sum(values) / len(values) if values else None,
            "ci95": interval(values), "n_worlds": len(values),
            "positive_worlds": positive, "negative_worlds": negative,
            "ties": len(values) - n, "sign_p": p if sign_test and values else None}


def contrast_specs():
    """Terms are condition, order, coefficient. Primary uses all assigned cases."""
    specs = {}
    for condition in CONDITIONS:
        specs[f"{condition}_reasoning_harm"] = [(condition, "answer_then_reason", 1),
                                               (condition, "reason_then_answer", -1)]
    for name, other in (("initial_minus_record_reasoning_harm", "initial_answer"),
                        ("copied_initial_minus_record_reasoning_harm", "copy_initial"),
                        ("marker_minus_record_reasoning_harm", "copy_marker"),
                        ("no_entry_minus_record_reasoning_harm", "no_entry")):
        specs[name] = specs[f"{other}_reasoning_harm"] + [
            (c, order, -coefficient) for c, order, coefficient in specs["copy_record_reasoning_harm"]]
    for other in ("copy_initial", "initial_answer", "copy_marker", "no_entry"):
        specs[f"record_minus_{other}_before_final"] = [
            ("copy_record", "reason_then_answer", 1), (other, "reason_then_answer", -1)]
    return specs


def _score(label, meta, metric):
    if metric == "accuracy":
        return int(label == meta["expected"])
    return 1 if label == meta["expected"] else 0 if label == meta["pattern_label"] else -1


def _estimate(plan, by_cell, metric, terms, sign_test=True):
    values, excluded, bounds = [], [], []
    for world in plan["worlds"]:
        total, low, high, complete = 0.0, 0.0, 0.0, True
        for condition, order, coefficient in terms:
            for value in VALUES:
                row = by_cell[world["id"], value, condition, order]
                if row["status"] == "complete":
                    candidates = [coefficient * _score(row["answer"], row, metric) / 2]
                    total += candidates[0]
                else:
                    complete = False
                    candidates = [coefficient * _score(label, row, metric) / 2 for label in "ABC"]
                low += min(candidates)
                high += max(candidates)
        bounds.append((low, high))
        if complete:
            values.append(total)
        else:
            excluded.append(world["id"])
    result = effect(values, sign_test)
    result.update(excluded_worlds=excluded, full_plan_bounds=[sum(b[i] for b in bounds) / len(bounds) for i in (0, 1)])
    return result


def summarize(plan, attempts, mode="live"):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        meta = task_meta(plan, task)
        record = records.get(task["id"])
        valid = record is not None and record["status"] == "complete"
        answer = record["answer"] if valid else None
        first = record["first_value"] if valid else None
        reason = record["reasoning"] if valid else None
        row = {"task_id": task["id"], **meta, "status": record["status"] if record else "pending",
               "answer": answer, "first_value": first, "reasoning": reason,
               "correct": int(answer == meta["expected"]) if valid else None,
               "record_sensitivity": _score(answer, meta, "record_sensitivity") if valid else None,
               "copy_correct": int(first == meta["copy_expected"]) if valid and task["condition"] in COPY_CONDITIONS else None,
               "first_class_correct": int(first == meta["expected"]) if valid and task["condition"] in CLASS_CONDITIONS else None,
               "entry_format_met": record.get("entry_format_met", False) if record else False,
               "output_contract_met": record.get("output_contract_met", False) if record else False,
               "reasoning_words": len(reason.split()) if reason is not None else None,
               "invalid_reason": record.get("invalid_reason") if record else None,
               "attempt_file": f"attempts/{record['attempt']:06d}.json" if record else None}
        codes = code_text(reason or "", meta["item_id"], meta["expected"], answer)
        row.update(codes if reason is not None else {key: None for key in codes})
        rows.append(row)
    by_cell = {(r["world_id"], r["value"], r["condition"], r["order"]): r for r in rows}
    cells, effects, transitions, rationale_counts = {}, {}, {}, {}
    for condition in CONDITIONS:
        for order in ORDERS:
            name = f"{condition}/{order}"
            group = [r for r in rows if r["condition"] == condition and r["order"] == order]
            valid = [r for r in group if r["status"] == "complete"]
            counts = {"planned": len(group), "returned": sum(r["status"] != "pending" for r in group),
                      "valid": len(valid), "correct": sum(r["correct"] for r in valid),
                      "pattern_choices": sum(r["answer"] == r["pattern_label"] for r in valid),
                      "other_wrong": sum(r["answer"] == r["other_record_label"] for r in valid),
                      "invalid": sum(r["status"] == "invalid" for r in group),
                      "pending": sum(r["status"] == "pending" for r in group),
                      "entry_format_met": sum(r["entry_format_met"] for r in valid),
                      "copy_correct": sum(r["copy_correct"] for r in valid) if condition in COPY_CONDITIONS else None,
                      "first_class_correct": sum(r["first_class_correct"] for r in valid) if condition in CLASS_CONDITIONS else None,
                      "reasoning_median_words": median(r["reasoning_words"] for r in valid) if valid else None}
            for metric in ("accuracy", "record_sensitivity"):
                counts[metric] = _estimate(plan, by_cell, metric, [(condition, order, 1)], False)
            pairs = [[by_cell[w["id"], value, condition, order] for value in VALUES] for w in plan["worlds"]]
            pairs = [pair for pair in pairs if all(r["status"] == "complete" for r in pair)]
            counts.update(complete_worlds=len(pairs), both_records_correct=sum(all(r["correct"] for r in pair) for pair in pairs),
                          final_answer_unchanged=sum(pair[0]["answer"] == pair[1]["answer"] for pair in pairs))
            counts["copy_final_joint_counts"] = (dict(Counter(
                f"copy_{'correct' if r['copy_correct'] else 'wrong'}__final_{'correct' if r['correct'] else 'wrong'}"
                for r in valid)) if condition in COPY_CONDITIONS else None)
            cells[name] = counts
            coding = Counter(r["rationale_code"] for r in valid)
            rationale_counts[name] = {"valid_reasoning_fields": len(valid), "class_counts": dict(coding),
                                     "class_shares": {k: v / len(valid) for k, v in coding.items()},
                                     "missing_candidates": sum(r["missing_claim_candidate"] for r in valid),
                                     "missing_and_correct": sum(r["missing_claim_candidate"] and r["correct"] for r in valid),
                                     "marker_mentions": sum(r["audit_marker_mentioned"] for r in valid),
                                     "wrong_response_classes": dict(Counter(r["rationale_code"] for r in valid if not r["correct"]))}
            if condition in CLASS_CONDITIONS:
                matrix = Counter()
                # Non-label first entries receive a separate category, never a made-up initial class.
                for r in valid:
                    initial = ("correct" if r["first_value"] == r["expected"] else
                               "wrong" if r["first_value"] in ("A", "B", "C") else "non_label")
                    matrix[f"{initial}_to_{'correct' if r['correct'] else 'wrong'}"] += 1
                transitions[name] = {"valid_final_cases": len(valid), **dict(matrix)}
    for metric in ("accuracy", "record_sensitivity"):
        for name, terms in contrast_specs().items():
            effects[f"{metric}/{name}"] = _estimate(plan, by_cell, metric, terms)
    returned = sum(r["status"] != "pending" for r in rows)
    invalid = sum(r["status"] == "invalid" for r in rows)
    complete = returned == len(rows)
    mismatch = any(r.get("response", {}).get("model_mismatch") for r in records.values())
    status = ("SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE" if mode == "mock" else
              "prepared_not_run" if mode == "prepared" else "model_mismatch_stop" if mismatch else
              "output_manipulation_inconclusive" if invalid else "complete_ready_for_interpretation" if complete else "incomplete")
    summary = {"protocol_version": plan["protocol_version"], "plan_hash": plan["plan_hash"], "mode": mode,
               "analysis_status": status, "is_simulated": mode == "mock",
               "interpretation_allowed": mode == "live" and complete and invalid == 0 and not mismatch,
               "planned_calls": len(rows), "attempts": len(attempts), "returned_answers": returned,
               "valid_answers": returned - invalid, "invalid_answers": invalid,
               "pending_answers": len(rows) - returned, "primary_effect": PRIMARY,
               "analysis_plan": ANALYSIS_PLAN, "cells": cells, "effects": effects,
               "transitions": transitions, "rationale_counts": rationale_counts,
               "uncertainty": UNCERTAINTY, "interpretation": INTERPRETATION,
               "decision": "no_automatic_followup", "target_position": 10}
    return summary, rows


def _fmt(value):
    return "—" if value is None else f"{value:.3f}"


def _ci(values):
    return "—" if values is None else f"[{values[0]:.3f}, {values[1]:.3f}]"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    summary, rows = summarize(plan, attempts, execution["mode"] if execution else "prepared")
    write_json(output / "summary.json", summary)
    write_csv(output / "answers.csv", rows, [k for k in rows[0] if k != "reasoning"])
    write_csv(output / "rationales.csv", rows, list(rows[0]))
    write_review(output, plan, rows)
    primary = summary["effects"][PRIMARY]
    lines = ["# Evidence role and reasoning placement", "",
             f"**{summary['analysis_status']}** — {summary['mode']}", "",
             f"{summary['returned_answers']}/480 returned; {summary['valid_answers']} valid; "
             f"{summary['invalid_answers']} invalid retained. Target fixed at row 10. "
             f"{summary['attempts']}/528 cumulative attempts.", "",
             "Primary: reasoning harm for initial_answer minus reasoning harm for copy_record. "
             "Harm = accuracy when reasoning follows the final answer minus accuracy when reasoning precedes it.", "",
             f"Primary estimate: **{_fmt(primary['mean'])}**, descriptive 95% CI {_ci(primary['ci95'])}; "
             f"{primary['n_worlds']}/24 complete worlds; exact sign p={_fmt(primary['sign_p'])}.", "",
             "Working prediction: the primary contrast is positive. The secondary copied-initial versus "
             "copied-record contrast tests the role wording while requiring identical extraction. "
             "A null does not establish equivalence. No estimate triggers more calls.", "",
             "## Cells", "",
             "| Condition / order | Correct / valid / planned | First class correct | Copy correct | Entry format met | Pattern / other wrong | Invalid / pending | Accuracy CI | Sensitivity CI |",
             "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for name, c in summary["cells"].items():
        lines.append(f"| {name} | {c['correct']}/{c['valid']}/{c['planned']} | "
                     f"{c['first_class_correct'] if c['first_class_correct'] is not None else '—'} | "
                     f"{c['copy_correct'] if c['copy_correct'] is not None else '—'} | {c['entry_format_met']} | "
                     f"{c['pattern_choices']} / {c['other_wrong']} | {c['invalid']} / {c['pending']} | "
                     f"{_ci(c['accuracy']['ci95'])} | {_ci(c['record_sensitivity']['ci95'])} |")
    lines += ["", "First-entry counts use the valid-final denominator; every planned case remains in the primary design. "
              "A wrong copy does not invalidate its final answer. Full cell estimates, bounds, record-variant pairs "
              "and reasoning lengths are in summary.json.", "", "## Paired contrasts", "",
              "| Effect | Mean | Descriptive 95% CI | Complete worlds | Sign p | Full-plan bounds |",
              "|---|---:|---|---:|---:|---|"]
    for name, e in summary["effects"].items():
        lines.append(f"| {name} | {_fmt(e['mean'])} | {_ci(e['ci95'])} | {e['n_worlds']}/24 | "
                     f"{_fmt(e['sign_p'])} | {_ci(e['full_plan_bounds'])} |")
    lines += ["", "## First-to-final transitions", "",
              "Only the three class-entry conditions have initial-class transitions. A marker is not an initial class.", "",
              "| Condition / order | Correct → correct | Correct → wrong | Wrong → correct | Wrong → wrong | Non-label first entry |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, counts in summary["transitions"].items():
        lines.append(f"| {name} | {counts.get('correct_to_correct', 0)} | {counts.get('correct_to_wrong', 0)} | "
                     f"{counts.get('wrong_to_correct', 0)} | {counts.get('wrong_to_wrong', 0)} | "
                     f"{counts.get('non_label_to_correct', 0) + counts.get('non_label_to_wrong', 0)} |")
    lines += ["", "## Provisional rationale flags", "",
              "Flags inspect the reasoning field only. 'Never stated' means the narrow class-statement regex "
              "did not match, not that the record was never used. Missingness matches are candidates for "
              "manual verification, not a complete factuality measure. Negated and conditional missingness "
              "lines are excluded. Longer explanations have more opportunities to trigger a flag. "
              "rationale_review.md masks assignment and scored answer; rationale_key.csv contains the key. "
              "The prose itself can reveal the condition, so blinding is partial.", "",
              "| Condition / order | Reasoning fields | Never stated | Missing candidate | Stated then overridden | Stated and followed | Missing + correct |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for name, c in summary["rationale_counts"].items():
        counts = c["class_counts"]
        lines.append(f"| {name} | {c['valid_reasoning_fields']} | {counts.get('never_stated', 0)} | "
                     f"{counts.get('relabeled_missing', 0)} | {counts.get('stated_then_overridden', 0)} | "
                     f"{counts.get('stated_and_followed', 0)} | {c['missing_and_correct']} |")
    lines += ["", UNCERTAINTY, "", INTERPRETATION, "",
              "Invalid outputs remain in the journal and are never resampled. With a structural/order failure, "
              "the report is output_manipulation_inconclusive: surviving-case estimates are diagnostics, "
              "not confirmation of the intended manipulation. Entry-format failures are reported separately "
              "without deleting their valid final answers. SIMULATED outputs cannot be evidence.", ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
