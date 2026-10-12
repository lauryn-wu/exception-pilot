"""Provisional text flags, plus an answer/condition-masked manual-review export.

These narrow lexical flags are not judgments of hidden computation or complete
factuality. Only the reasoning field is coded, never the first or final field.
"""

import csv
import json
from pathlib import Path
import random
import re

from .core import table_for, world_for


def code_text(text, plate, expected, answer):
    plate_pattern = re.escape(plate)
    states = bool(re.search(plate_pattern + r"[^\n]{0,160}\b[Cc]lass\s*(?:is|of|:|as)?\s*\**"
                            + re.escape(expected) + r"\b", text))
    evidence = []
    for line in text.splitlines():
        if not re.search(r"\b" + plate_pattern + r"\b", line):
            continue
        clean = re.sub(r"\*|`", "", line)
        # Avoid treating the explicit negation seen in historical traces as a claim.
        clean = re.sub(r"\b(?:not|never)\s+(?:actually\s+)?(?:missing|unknown)\b", "", clean, flags=re.I)
        if re.search(r"\b(?:if|unless|whether)\b", clean, re.I):
            continue
        if re.search(r"\b(?:missing|unknown|not recorded|not listed|to be predicted)\b|\?", clean, re.I):
            evidence.append(line)
    missing = bool(evidence)
    code = ("relabeled_missing" if missing else "never_stated" if not states else
            "stated_and_followed" if answer == expected else "stated_then_overridden")
    return {"states_recorded_class": states, "missing_claim_candidate": missing,
            "missing_evidence": "\n".join(evidence), "rationale_code": code,
            "audit_marker_mentioned": bool(re.search(r"\baudit marker\b", text, re.I))}


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_review(output, plan, rows):
    """No judge API. All available valid reasoning fields, without outcome selection."""
    output = Path(output)
    review_rows = [r for r in rows if r["reasoning"] is not None]
    random.Random(981724).shuffle(review_rows)
    tasks = {t["id"]: t for t in plan["tasks"]}
    lines = ["# Rationale review", "",
             "SIMULATED outputs are software fixtures, never research evidence. "
             "Condition, output order, first entry, scored answer and correctness are omitted here. "
             "The reasoning itself can reveal them, so this is only partial blinding. "
             "The original table is supplied to check factual claims. Do not inspect rationale_key.csv "
             "before coding. Suggested codes: explicit target missingness; correct record stated; "
             "record overridden; false feature/marker claims; uncertain. Flags in the analysis are "
             "provisional and do not replace this review.", ""]
    keys = []
    for index, row in enumerate(review_rows, 1):
        review_id = f"review-{index:03d}"
        task = tasks[row["task_id"]]
        world = world_for(plan, task)
        target = world["items"][world["target_index"]]["id"]
        lines += [f"## {review_id}", "", f"Target plate: {target}", "", table_for(plan, task), "",
                  "Reasoning field:", "", "````text", row["reasoning"], "````", "",
                  "Manual coding: ____________________", ""]
        keys.append({"review_id": review_id, "task_id": task["id"], "condition": row["condition"],
                     "order": row["order"], "expected": row["expected"], "answer": row["answer"],
                     "first_value_json": json.dumps(row["first_value"]), "correct": row["correct"]})
    (output / "rationale_review.md").write_text("\n".join(lines), encoding="utf-8")
    write_csv(output / "rationale_key.csv", keys,
              ["review_id", "task_id", "condition", "order", "expected", "answer", "first_value_json", "correct"])
