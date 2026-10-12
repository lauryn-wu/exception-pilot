"""Read-only, offline lexical audit of archived visible reasoning.

Codes describe written evidence, not hidden computation. The original brief's
regex is retained as legacy_states_recorded_class; improved codes require an
assertion about the target record and allow multiline attribute lists.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import importlib
import json
from pathlib import Path
import random
import re

from exception_pilot.core import check_plan, digest
from exception_pilot.storage import accepted_records, load_attempts, write_json
from exception_mistral_map_v3.parser import answer_boundary

CODER_VERSION = "record-evidence-lexical-v2"
PROTOCOLS = {
    "verified-facts-reasoning-cue-v1": ("exception_cue", ("visible",)),
    "verified-facts-explanation-v1": ("exception_explanation", ("cot",)),
    "verified-facts-answer-order-v1": ("exception_order", ("reasoning_first",)),
    "verified-facts-answer-revision-v1": ("exception_revision", ("reasoning_first", "revision")),
    "verified-facts-mistral-prefix-feasibility-v2": ("exception_mistral_prefix_v2", ("visible",)),
    "verified-facts-query-form-v1": ("exception_query_form", ("visible",)),
}
CLASSES = ("never_stated", "relabeled_missing", "stated_then_overridden", "stated_and_followed")
MISSING = r"(?:\bMISSING\b|\?|\bunknown\b|\bnot recorded\b|\bnot listed\b|\bto be predicted\b)"


def reasoning_text(text):
    """Remove JSON answer fields / the terminal answer without editing reasoning."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        value = None
    if isinstance(value, dict) and isinstance(value.get("reasoning"), str):
        # Some historical JSON traces contain literal backslash-n inside the string.
        return value["reasoning"].replace("\\n", "\n")
    _, start = answer_boundary(text)
    return text[:start].rstrip() if start is not None else text


def code_text(text, plate, expected, answer, other_plates=()):
    if expected not in ("A", "B", "C") or answer not in ("A", "B", "C"):
        raise ValueError("Coding requires a scorable answer and recorded gold label")
    text = reasoning_text(text)
    legacy = bool(re.search(re.escape(plate) + r"[^\n]{0,160}\b[Cc]lass\s*(?:is|of|:|as)?\s*\**" + expected + r"\b", text))
    legacy_missing = any(plate in line and re.search(MISSING, line, re.I) for line in text.splitlines())
    clean = re.sub(r"[*`_]", "", text)
    lines = clean.splitlines()
    evidence, missing_evidence = [], []
    for i, line in enumerate(lines):
        if not re.search(r"\b" + re.escape(plate) + r"\b", line):
            continue
        # A target-led record block, bounded by a new paragraph, another plate,
        # or eight lines. Attribute bullets may put the class far beyond 160 chars.
        block = [line]
        for following in lines[i + 1:i + 9]:
            if not following.strip() or any(p in following for p in other_plates):
                break
            block.append(following)
        excerpt = "\n".join(block)
        for part in block:
            inferential = re.search(r"\b(align\w*|suggest\w*|likely|predict\w*|infer\w*|would|should|could|may|might|shares?|common|similar|therefore|conclud\w*)\b", part, re.I)
            explicitly_recorded = re.search(
                r"\b(?:verified|recorded)\s+(?:class|label)\s*(?:is|of|:|as)?\s*" + expected + r"\b"
                r"|\b(?:listed|recorded|verified|labeled|labelled|marked)\s+(?:(?:as|under|in)\s+)?(?:class\s*)?" + expected + r"\b"
                r"|\bclass\s*(?:is|of|:|as)?\s*" + expected + r"\s*\(?\s*(?:(?:is|as|already|currently)\s+)?(?:given|listed|recorded|verified|marked)\b", part, re.I)
            # Enumerated class membership and copied row summaries assert the
            # plate's record; merely sharing a feature with a class does not.
            membership = (re.search(r"\bclass\s+" + expected + r"\s*:[^\n]*\b" + re.escape(plate) + r"\b", part, re.I)
                          or re.search(r"\bclass\s+" + expected + r"\s*\([^)]*\b" + re.escape(plate) + r"\b[^)]*\)", part, re.I))
            row_summary = (re.match(r"[\s\-\d.)]*" + re.escape(plate) + r"\s*[:|—-]", part)
                           and re.search(r"\bclass\s*(?:is|of|:|as)?\s*" + expected + r"\b", part, re.I))
            row_summary = row_summary or re.match(r"[\s\-\d.)]*" + re.escape(plate) + r"\s*\(\s*class\s+" + expected + r"\s*\)\s*:", part, re.I)
            # Copying a seven-column row is direct textual evidence too.
            table_copy = plate in part and len(part.split("|")) >= 8 and part.strip().rstrip("|").strip().endswith(expected)
            if explicitly_recorded or table_copy or ((membership or row_summary) and not inferential):
                evidence.append(excerpt)
            negative = re.search(r"\b(?:not|isn't|is not)\s+(?:missing|unknown)\b|\bno\s+(?:missing|unknown)\b", part, re.I)
            if re.search(MISSING, part, re.I) and not negative:
                # A bare question mark in a rhetorical question is not a missing cell.
                marker = re.search(r"\bMISSING\b|\bunknown\b|\bnot recorded\b|\bnot listed\b|\bto be predicted\b", part, re.I)
                cell_question = re.search(r"(?:class\s*:\s*|\|\s*)\?\s*(?:\||$)", part, re.I)
                cell_question = cell_question or re.search(re.escape(plate) + r"\s*:\s*\?\s*$", part)
                if marker or cell_question:
                    missing_evidence.append(excerpt)
    states, missing = bool(evidence), bool(missing_evidence)
    # Missing has priority so contradictory traces remain visible in both flags.
    category = ("relabeled_missing" if missing else
                "stated_and_followed" if states and answer == expected else
                "stated_then_overridden" if states else "never_stated")
    return {"states_recorded_class": states, "relabels_missing": missing,
            "class": category, "legacy_states_recorded_class": legacy,
            "legacy_relabels_missing": legacy_missing,
            "record_evidence": "\n---\n".join(dict.fromkeys(evidence)),
            "missing_evidence": "\n---\n".join(dict.fromkeys(missing_evidence))}


def rows_from_records(plan, records, run_name):
    package, arms = PROTOCOLS[plan["protocol_version"]]
    core = importlib.import_module(package + ".core")
    rows = []
    for task in plan["tasks"]:
        if task.get("arm") not in arms or task.get("value") not in ("record_1", "record_2") or task.get("family") not in ("diagnostic", "base"):
            continue
        record = records.get(task["id"])
        if not record or record["status"] != "complete" or record.get("answer") not in ("A", "B", "C"):
            continue
        meta = core.task_meta(plan, task)
        if record.get("meta") != meta:
            raise ValueError("Task metadata differs from the frozen plan: " + task["id"])
        scored = (core.score_response(task, record["response"], meta) if package == "exception_mistral_prefix_v2"
                  else core.score_response(task, record["response"]))
        if scored.get("status") != "complete" or scored.get("answer") != record["answer"]:
            raise ValueError("Saved answer differs from its protocol's scorer: " + task["id"])
        world = next(w for w in plan["worlds"] if w["id"] == task["world_id"])
        others = [item["id"] for item in world["items"] if item["id"] != meta["item_id"]]
        text = record["response"]["text"]
        coded = code_text(text, meta["item_id"], meta["expected"], record["answer"], others)
        rows.append({"run": run_name, "protocol_version": plan["protocol_version"],
                     "plan_hash": plan["plan_hash"], "coder_version": CODER_VERSION,
                     "task_id": task["id"], "attempt": record["attempt"], "mode": record["mode"],
                     **meta, "answer": record["answer"], "correct": record["answer"] == meta["expected"],
                     **coded, "reasoning": reasoning_text(text)})
    return rows


def summary_table(rows, by_cell=False):
    counts = Counter((r["run"], r.get("query", "") + "/" + r["arm"] if by_cell else "all selected arms",
                      "correct" if r["correct"] else "wrong", r["class"]) for r in rows)
    lines = ["| Run | Cell | Outcome | Code | Count | Share within cell/outcome |", "|---|---|---|---|---:|---:|"]
    for run, cell, outcome in sorted({k[:3] for k in counts}):
        total = sum(counts[(run, cell, outcome, c)] for c in CLASSES)
        for category in CLASSES:
            count = counts[(run, cell, outcome, category)]
            lines.append(f"| {run} | {cell} | {outcome} | {category} | {count} | {count / total:.1%} |")
    return "\n".join(lines)


def write_audit(plan, records, run_name, output, sample=0, seed=981723):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = rows_from_records(plan, records, run_name)
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["run", "class"]
    with (output / "rationales.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    disagreements = sum(r["states_recorded_class"] != r["legacy_states_recorded_class"] for r in rows)
    lines = ["# Offline rationale audit", "", f"Coder: `{CODER_VERSION}`. {len(rows)} scorable visible responses.", "",
             "Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. "
             "They do not establish retrieval, task recognition, or faithful internal reasoning. "
             "The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. "
             "Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.", "",
             f"The brief's single-line regex disagrees with the revised record-evidence flag on {disagreements}/{len(rows)} responses. "
             "Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. "
             "Revision and reasoning-first traces are also shown separately below.", "", summary_table(rows), "", summary_table(rows, True), ""]
    (output / "summary.md").write_text("\n".join(lines))
    if sample:
        chosen = random.Random(seed).sample(rows, min(sample, len(rows)))
        lines = ["# Blind rationale sample", "", f"Seed {seed}; {len(chosen)} sampled without replacement. "
                 "Final answer fields, gold, correctness, model and condition IDs are withheld. "
                 "Code the label explicitly asserted as the target's recorded class (if any), missing-label assertions, and evidence spans. "
                 "Outcome-dependent categories can only be assigned after unblinding. The prose can itself reveal a proposed answer. "
                 "The target gold cell is masked; source identifiers are replaced consistently within each item. Do not inspect sample_key.json while coding.", ""]
        key = []
        for index, row in enumerate(chosen, 1):
            world = next(w for w in plan["worlds"] if w["id"] == row["world_id"])
            names = {item["id"]: ("TARGET" if item["id"] == row["item_id"] else f"PEER{j:02d}") for j, item in enumerate(world["items"], 1)}
            rationale = row["reasoning"]
            for plate, name in names.items():
                rationale = rationale.replace(plate, name)
            lines += [f"## Sample {index:02d}", "", "| Identifier | Description | Transmission | Seat cover | Doors | Marker | Verified class |", "|---|---|---|---|---|---|---|"]
            for j in world["order"]:
                item = world["items"][j]
                label = "[HIDDEN]" if item["id"] == row["item_id"] else world["record_labels"][row["value"]][j]
                lines.append("| " + " | ".join([names[item["id"]]] + [item[k] for k in ("descriptor", "transmission", "seat_cover", "doors", "audit_marker")] + [label]) + " |")
            lines += ["", "```text", rationale, "```", "", "Manual recorded-label assertion: ___; missing assertion: ___; evidence: ___", ""]
            key.append({"sample": index, "task_id": row["task_id"], "answer": row["answer"], "expected": row["expected"], "automatic_class": row["class"]})
        (output / "rationale_sample.md").write_text("\n".join(lines))
        write_json(output / "sample_key.json", key)
    write_json(output / "audit.json", {"coder_version": CODER_VERSION, "coder_source_digest": digest(Path(__file__).read_text()), "plan_hash": plan["plan_hash"],
               "records_digest": digest(records), "scorable_visible_responses": len(rows),
               "legacy_record_flag_disagreements": disagreements, "sample_seed": seed, "sample_requested": sample})
    return rows


def audit_run(run, output, sample=0, seed=981723):
    run, output = Path(run).resolve(), Path(output).resolve()
    if output == run or run in output.parents:
        raise ValueError("Offline audit output must be outside the source run directory")
    plan = json.loads((run / "plan.json").read_text())
    check_plan(plan)
    if plan["protocol_version"] not in PROTOCOLS:
        raise ValueError("Unsupported protocol version")
    records = accepted_records(load_attempts(run, plan))
    return write_audit(plan, records, run.name, output, sample, seed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--seed", type=int, default=981723)
    args = parser.parse_args(argv)
    if args.sample < 0:
        parser.error("--sample must be nonnegative")
    rows = audit_run(args.run, args.out, args.sample, args.seed)
    print(json.dumps({"run": str(args.run), "coded": len(rows), "api_calls": 0, "output": str(args.out)}))


if __name__ == "__main__":
    main()
