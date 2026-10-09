"""Descriptive maps and world-level contrasts, never a mechanism verdict."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from pathlib import Path

from exception_pilot.storage import accepted_records, write_json
from exception_mistral_prefix_v2.analysis import effect
from .core import capability_gate, sampling_gate, task_meta


def counts(rows):
    valid = [r for r in rows if r["status"] == "complete"]
    returned = [r for r in rows if r["status"] != "pending"]
    correct = sum(r["correct"] == 1 for r in valid)
    pattern = sum(r["follows_pattern"] == 1 for r in valid)
    unknown = len(rows) - len(valid)
    n = len(rows)
    return {"planned": n, "returned": len(returned), "valid": len(valid),
            "invalid": len(returned) - len(valid), "pending": n - len(returned),
            "correct": correct, "pattern": pattern, "other": len(valid) - correct - pattern,
            "answer_counts": dict(Counter(r["answer"] for r in valid)),
            "accuracy_valid_only": correct / len(valid) if valid else None,
            "pattern_rate_valid_only": pattern / len(valid) if valid else None,
            "full_plan_accuracy_bounds": [correct / n, (correct + unknown) / n] if n else None,
            "all_valid": bool(n and len(valid) == n)}


def _line_contrast(plan, points, subset):
    eligible = defaultdict(list)
    for case in plan["cases"]:
        span = case["target_record_line"]
        if span is None or (subset != "all" and span["contains_missing_word"] != (subset == "missing_word")):
            continue
        eligible[case["meta"]["world_id"]].append(case)
    world_deltas, missing_worlds = {}, []
    for world, cases in eligible.items():
        deltas = []
        for case in cases:
            before = next(p for p in case["checkpoints"] if "before_target_record_line" in p["labels"])
            after = next(p for p in case["checkpoints"] if "after_target_record_line" in p["labels"])
            a = points[(case["id"], after["id"])]
            b = points[(case["id"], before["id"])]
            if a["all_valid"] and b["all_valid"]:
                deltas.append(a["accuracy_valid_only"] - b["accuracy_valid_only"])
        if len(deltas) == len(cases):
            world_deltas[world] = sum(deltas) / len(deltas)
        else:
            missing_worlds.append(world)
    return {"subset": subset, "contrast": "after_minus_before_target_record_line_accuracy",
            "eligible_cases": sum(map(len, eligible.values())), "eligible_worlds": len(eligible),
            "incomplete_worlds": missing_worlds, "world_deltas": world_deltas,
            **effect(list(world_deltas.values()))}


def summarize(plan, attempts, mode):
    records = accepted_records(attempts)
    rows = []
    for task in plan["tasks"]:
        if task["family"] == "capability":
            continue
        meta = task_meta(plan, task)
        record = records.get(task["id"])
        valid = record is not None and record["status"] == "complete"
        answer = record.get("answer") if record else None
        rows.append({"task_id": task["id"], "family": task["family"], "arm": task["arm"],
                     "world_id": meta["world_id"], "value": meta["value"],
                     "case_id": meta.get("case_id"), "checkpoint_id": meta.get("checkpoint_id"),
                     "repeat": meta.get("repeat"), "cut_chars": meta.get("cut_chars"),
                     "expected": meta["expected"], "pattern_label": meta["pattern_label"],
                     "status": record["status"] if record else "pending", "answer": answer,
                     "correct": int(answer == meta["expected"]) if valid else None,
                     "follows_pattern": int(answer == meta["pattern_label"]) if valid else None,
                     "prefix_exact": record.get("prefix_exact") if record else None,
                     "invalid_reason": record.get("invalid_reason") if record else None,
                     "suffix_contains_missing_word": record.get("suffix_contains_missing_word") if record else None,
                     "generated_suffix": record.get("generated_suffix") if record else None})
    point_rows = defaultdict(list)
    for row in rows:
        if row["family"] == "map":
            point_rows[(row["case_id"], row["checkpoint_id"])].append(row)
    point_counts = {key: counts(group) for key, group in point_rows.items()}
    trajectories = []
    for case in plan["cases"]:
        points, previous = [], None
        for point in case["checkpoints"]:
            count = point_counts[(case["id"], point["id"])]
            delta = None
            if previous is not None and previous["all_valid"] and count["all_valid"]:
                delta = count["accuracy_valid_only"] - previous["accuracy_valid_only"]
            points.append({**point, **count, "accuracy_change_from_previous": delta})
            previous = count
        trajectories.append({"case_id": case["id"], "world_id": case["meta"]["world_id"],
                             "expected": case["meta"]["expected"], "pattern_label": case["meta"]["pattern_label"],
                             "parent_answer": case["parent_answer"], "parent_correct": case["parent_correct"],
                             "target_record_line": case["target_record_line"], "checkpoints": points})
    cap, gate = capability_gate(plan, records), sampling_gate(plan, records)
    mapping_rows = [r for r in rows if r["family"] == "map"]
    mapping = counts(mapping_rows)
    hard_failure = next((a for a in attempts if a.get("hard_failure")), None)
    if hard_failure or cap["status"] == "fail":
        status = "operational_stop"
    elif cap["status"] != "pass":
        status = "pending_capability"
    elif gate["status"] == "fail":
        status = "sampling_check_failed_stop"
    elif gate["status"] != "pass":
        status = "pending_sampling_check"
    elif mapping["returned"] == mapping["planned"]:
        status = "exploratory_map_complete" if mapping["all_valid"] else "exploratory_map_complete_with_unscorable"
    elif mapping["returned"]:
        status = "mapping_incomplete"
    else:
        status = "ready_for_mapping"
    base_worlds = defaultdict(dict)
    for row in rows:
        if row["family"] == "base":
            base_worlds[row["world_id"]][(row["value"], row["arm"])] = row
    base_deltas = []
    for cells in base_worlds.values():
        if len(cells) == 4 and all(r["status"] == "complete" for r in cells.values()):
            base_deltas.append(sum(cells[(v, "direct")]["correct"] - cells[(v, "visible")]["correct"]
                                   for v in ("record_1", "record_2")) / 2)
    usages = [a.get("response", {}).get("usage", {}) for a in attempts]
    return {"protocol": plan["protocol_version"], "plan_hash": plan["plan_hash"],
            "analysis_status": status, "is_simulated": mode == "mock", "source_mode": plan["source_mode"],
            "source_replay_gate_preserved": plan["source_replay_gate"], "worlds": 12,
            "parent_cases": len(plan["cases"]), "attempts_total": len(attempts),
            "planned_calls": len(plan["tasks"]), "mapping": mapping,
            "capability_gate": cap, "sampling_gate": gate,
            "base_counts": {arm: counts([r for r in rows if r["family"] == "base" and r["arm"] == arm])
                            for arm in ("direct", "visible")},
            "base_direct_minus_visible_accuracy": effect(base_deltas),
            "target_record_line_contrasts": [_line_contrast(plan, point_counts, subset)
                                             for subset in ("all", "missing_word", "no_missing_word")],
            "trajectories": trajectories, "answers": rows,
            "reported_usage": {key: sum(u.get(key, 0) or 0 for u in usages)
                               for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "response_models": sorted({a["response"]["model"] for a in attempts
                                       if a.get("response", {}).get("model")}),
            "limits": [plan["interpretation"],
                       "Before/after includes the entire retained text block. It does not isolate semantic content from length or wording.",
                       "MISSING is a lexical flag only; it does not establish a target-specific false availability claim.",
                       "All returned invalid answers are retained. Only transport errors/unresolved requests can be retried.",
                       "World contrasts average eligible cases within each world, then weight complete worlds equally. No individual rollouts are independent worlds.",
                       "10,000 whole-world bootstrap draws, seed 981723: descriptive unadjusted intervals, no multiplicity correction. Six draws per checkpoint provide coarse probabilities only. Degenerate intervals are not certainty or equivalence.",
                       "Bounds assign all unscorable or pending slots incorrect/correct; they are not confidence intervals. No novelty or mechanism pass/fail test."]}


def _rate(value):
    return "—" if value is None else f"{value:.3f}"


def write_summary(output):
    from .runner import read_run
    output = Path(output)
    plan, execution, attempts = read_run(output)
    result = summarize(plan, attempts, execution["mode"] if execution else "unstarted")
    write_json(output / "summary.json", result)
    rows = result["answers"]
    with (output / "answers.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Regenerated export. Human coding must be saved under a different filename.
    with (output / "continuations-to-code.csv").open("w", newline="") as f:
        fields = ["task_id", "case_id", "checkpoint_id", "generated_suffix", "target_missing_claim", "uses_record", "uses_pattern", "notes"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({**{k: r.get(k) for k in fields[:4]}, **{k: "" for k in fields[4:]}}
                        for r in rows if r["family"] == "map" and r["generated_suffix"] is not None)
    lines = ["# Mistral continuation map — exploratory", "", f"Status: **{result['analysis_status']}**",
             f"SIMULATED: {result['is_simulated']}. {result['attempts_total']}/{result['planned_calls']} attempts/planned responses.",
             "12 reused parent worlds; 24 parent traces. No corrected text is supplied. No independent confirmation or internal mechanism claim.", "",
             "## Sampling check", "", f"Decision: {result['sampling_gate']['status']}. Direct correct: {result['sampling_gate']['direct_correct']}/24; visible correct: {result['sampling_gate']['visible_correct']}/24.",
             "The original source replay status is preserved; this study compares fresh continuation distributions.", "",
             "## Target-record-line contrast", "", "Positive values favor retaining the line. Whole-world descriptive intervals only.", "",
             "| Subset (lexical) | After minus before | 95% interval | Complete / eligible worlds | Eligible cases |",
             "|---|---:|---|---:|---:|"]
    for c in result["target_record_line_contrasts"]:
        lines.append(f"| {c['subset']} | {_rate(c['mean'])} | {c['descriptive_cluster_bootstrap_95_ci']} | {c['n_worlds']}/{c['eligible_worlds']} | {c['eligible_cases']} |")
    lines += ["", "## All trajectories", "", "Each checkpoint has six planned draws. Adjacent changes are exploratory and may be sampling noise. Exact retained blocks are in preview.md and summary.json.", ""]
    for trace in result["trajectories"]:
        lines += [f"### {trace['case_id']}", "", f"Recorded: {trace['expected']}; pattern: {trace['pattern_label']}; saved parent answer: {trace['parent_answer']}.", "",
                  "| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |",
                  "|---|---:|---|---:|---:|---:|---:|---:|"]
        for p in trace["checkpoints"]:
            lines.append(f"| {p['id']} | {p['cut_chars']} | {', '.join(p['labels'])} | {p['valid']}/6 | {p['correct']} | {p['pattern']} | {_rate(p['accuracy_valid_only'])} | {_rate(p['accuracy_change_from_previous'])} |")
        lines.append("")
    lines += ["## Interpretation limits", ""] + ["- " + s for s in result["limits"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return result
