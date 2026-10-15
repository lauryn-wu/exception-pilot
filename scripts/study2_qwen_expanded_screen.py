#!/usr/bin/env python3
"""Bounded exploratory Qwen screen: next four worlds, 8 visible + 8 direct, 2048 tokens.

Never writes to the frozen v4 selection source. No GPU inference without --live-qwen.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_continuation.core import final_score
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from scripts import study2_qwen_length_diagnostic as first_four

PROTOCOL = "qwen3-expanded-conditional-length-screen-v1"
NEW_TOKEN_BUDGET = 2048
FIRST_TASK_INDEX = 8
LAST_TASK_INDEX = 24
INTERPRETATION = (
    "Exploratory screen, NOT frozen v4 collection or confirmation. The next four "
    "pre-existing v4 selection worlds are screened in full with 2048 new tokens "
    "per arm. Strict final-answer compliance and Markdown-tolerant final answers "
    "are reported separately. No edits, answer cues, false-missingness classifiers, "
    "or future tokens are injected. Do not pool with 512-token results."
)


def code_identity():
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    return dict(
        git_revision=revision,
        script_sha256=first_four.sha(__file__),
        v4_source_hash=first_four.v4_source_hash(),
    )


def choose_tasks(plan):
    """Predeclare worlds 2, 3, 4, 5; never choose by observed outcomes."""
    tasks = plan["tasks"][FIRST_TASK_INDEX:LAST_TASK_INDEX]
    if len(tasks) != 16:
        raise ValueError("Expected precisely 16 additional tasks")
    world_order = list(dict.fromkeys(t["world"] for t in tasks))
    if len(world_order) != 4 or world_order != [w["id"] for w in plan["worlds"][2:6]]:
        raise ValueError("Expected the four consecutive selection worlds 2-5")
    for world in world_order:
        cells = [t for t in tasks if t["world"] == world]
        if len(cells) != 4 or {(t["variant"], t["arm"]) for t in cells} != {
            (0, "direct"), (0, "visible"), (1, "direct"), (1, "visible")
        }:
            raise ValueError("Incomplete direct/visible matched world: " + world)
    return tasks


def setup_plan(source):
    pilot = first_four.inspect_pilot(source)
    tasks = choose_tasks(pilot["plan"])
    return dict(
        protocol=PROTOCOL,
        interpretation=INTERPRETATION,
        code=code_identity(),
        source=pilot["binding"],
        source_hash=pilot["source_hash"],
        backend_hash=pilot["execution"]["backend_hash"],
        backend_identity=pilot["execution"]["backend"],
        frozen_config=pilot["plan"]["config"],
        original_v4_plan_hash=pilot["plan"]["plan_hash"],
        selection="world_indices_2_through_5_inclusive",
        generation_budget=NEW_TOKEN_BUDGET,
        tasks=tasks,
        planned_calls=16,
        planned_visible=8,
        planned_direct=8,
        maximum_new_tokens=16 * NEW_TOKEN_BUDGET,
    ), pilot


def other_directory(source, output):
    src, out = Path(source).resolve(), Path(output).resolve()
    if src == out or src in out.parents or out in src.parents:
        raise ValueError("Screen output must be separate from the original v4 source")
    if out.exists() and (out / "plan-v4.json").exists():
        raise ValueError("Cannot overwrite a v4 run")
    if out.exists() and any(out.iterdir()) and not (out / "screen-plan.json").exists():
        raise ValueError("Use an empty screen output directory")
    return out


def tolerant_final(text, stopped):
    """Secondary literal-markdown adjustment only; never overwrite strict score."""
    if not stopped or not isinstance(text, str):
        return None
    last = text.strip().splitlines()[-1].strip() if text.strip() else ""
    match = re.fullmatch(r"(?:\*\*)?ANSWER:\s*([ABC])(?:\*\*)?", last)
    return match.group(1) if match else None


def validate_raw(raw, backend):
    try:
        first_four.check_raw(raw, NEW_TOKEN_BUDGET, backend.eos_ids)
        if backend.decode(raw["tokens"]) != raw["text"]:
            return "Generated text and token IDs disagree"
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return type(exc).__name__ + ": " + str(exc)
    return None


def request(task, prompt_ids, plan):
    return dict(
        protocol=PROTOCOL,
        screen_plan_hash=plan["artifact_hash"],
        source_hash=plan["source_hash"],
        backend_hash=plan["backend_hash"],
        task_id=task["id"],
        world=task["world"],
        variant=task["variant"],
        arm=task["arm"],
        prompt_hash=digest(task["prompt"]),
        prompt_ids=prompt_ids,
        prompt_ids_hash=digest(prompt_ids),
        generation_budget=NEW_TOKEN_BUDGET,
        fresh_uninterrupted_generation=True,
    )


def journal_state(path, req):
    states = {}
    for state in ("request", "started", "returned", "failed"):
        p = path / (state + ".json")
        if p.exists():
            entry = sealed_read(p)
            if entry.get("status") != state or entry.get("request") != req:
                raise ValueError("Incompatible journal request/state: " + str(p))
            states[state] = entry
    if any(s in states for s in ("started", "returned", "failed")) and "request" not in states:
        raise ValueError("Incomplete journal state chain")
    if "returned" in states and "failed" in states:
        raise ValueError("Conflicting terminal journal outcomes")
    if "returned" in states and "started" not in states:
        raise ValueError("Returned record lacks started record")
    return states


def reports(output, plan):
    root = Path(output)
    rows = []
    readable = [PROTOCOL, INTERPRETATION, "Original: " + plan["source"]["source_path"]]
    for task in plan["tasks"]:
        dir_ = root / "operations" / digest(task["id"])
        saved = {}
        for state in ("request", "started", "returned", "failed"):
            p = dir_ / (state + ".json")
            if p.exists():
                saved[state] = sealed_read(p)
        state = next((s for s in ("returned", "failed", "started", "request") if s in saved), None)
        row = dict(
            task_id=task["id"], world=task["world"],
            variant=task["variant"], arm=task["arm"],
            expected=task["expected"], misleading_pattern=task["pattern"],
            status=state or "unattempted",
        )
        if state == "returned":
            raw = saved["returned"]["raw"]
            row.update(
                raw=raw, validation_error=saved["returned"].get("validation_error"),
                elapsed_seconds=saved["returned"]["elapsed_seconds"],
                generation_tokens=len(raw.get("tokens", [])),
                finish=raw.get("finish"),
                stopped=raw.get("stopped"),
            )
            if not row["validation_error"]:
                strict = final_score(raw["text"], raw["stopped"], task["expected"])
                tolerant = tolerant_final(raw["text"], raw["stopped"])
                row.update(
                    strict_score=strict,
                    tolerant_answer=tolerant,
                    tolerant_valid=tolerant is not None,
                    tolerant_correct=None if tolerant is None else tolerant == task["expected"],
                    pattern_answer=None if tolerant is None else tolerant == task["pattern"],
                    truncated=raw["finish"] == "length",
                )
        elif state == "failed":
            row["error_type"] = saved["failed"].get("error_type")
        rows.append(row)
        meta = {k: v for k, v in row.items() if k != "raw"}
        readable.extend(["", "=" * 72, json.dumps(meta, indent=2),
                         "--- NEW COMPLETE RESPONSE ---",
                         row.get("raw", {}).get("text", "[not returned]"),
                         "--- END RESPONSE ---"])
    usable = [r for r in rows if r["status"] == "returned" and not r.get("validation_error")]
    by_arm = {}
    for arm in ("direct", "visible"):
        r = [x for x in usable if x["arm"] == arm]
        by_arm[arm] = dict(
            planned=8,
            returned_usable=len(r),
            strict_valid=sum(x["strict_score"]["valid"] for x in r),
            strict_correct=sum(x["strict_score"]["correct"] is True for x in r),
            tolerant_valid=sum(x["tolerant_valid"] for x in r),
            tolerant_correct=sum(x["tolerant_correct"] is True for x in r),
            tolerant_wrong=sum(x["tolerant_correct"] is False for x in r),
            matched_pattern_errors=sum(x["pattern_answer"] is True and x["tolerant_correct"] is False for x in r),
            truncated=sum(x["truncated"] for x in r),
        )
    status = "COMPLETE" if len(usable) == len(plan["tasks"]) else "PARTIAL_OR_UNAVAILABLE"
    report = dict(
        protocol=PROTOCOL, interpretation=INTERPRETATION,
        status=status, selection=plan["selection"],
        screen_plan_hash=plan["artifact_hash"],
        source_hash=plan["source_hash"], by_arm=by_arm,
        returned_usable=len(usable), planned=16, cases=rows,
        false_missingness_audit="NOT_PERFORMED; manually review complete traces",
    )
    write_json(root / "screen-results.json", report)
    p = root / "screen-traces.txt"
    temp = p.with_suffix(".tmp")
    temp.write_text("\n".join(readable) + "\n")
    temp.replace(p)
    return report


def run(source, output, live_qwen=False):
    output = other_directory(source, output)
    source_plan, pilot = setup_plan(source)
    with run_lock(output):
        plan = freeze(output / "screen-plan.json", source_plan)
        if not live_qwen:
            result = reports(output, plan)
            print("Prepared; no inference. To run, add --live-qwen.", flush=True)
            return result
        # Abort before loading weights if any previous call was interrupted/failed.
        for task in plan["tasks"]:
            p = output / "operations" / digest(task["id"])
            for name in ("started", "failed"):
                if (p / (name + ".json")).exists() and not (p / "returned.json").exists():
                    raise ValueError("Ambiguous/failed operation; will not resend: " + task["id"])
        from exception_continuation.backend import LocalBackend
        print("Loading pinned Qwen3-32B backend...", flush=True)
        backend = LocalBackend(copy.deepcopy(plan["frozen_config"]))
        if digest(backend.identity) != plan["backend_hash"]:
            raise ValueError("Qwen backend identity differs from the frozen v4 pilot; stop")
        for task in plan["tasks"]:
            first_four.unchanged_source(pilot)
            ids = backend.prompt(task["prompt"])
            req = request(task, ids, plan)
            path = output / "operations" / digest(task["id"])
            freeze(path / "request.json", dict(status="request", request=req))
            states = journal_state(path, req)
            if "returned" in states:
                print("CACHED: " + task["id"], flush=True)
                continue
            if "started" in states or "failed" in states:
                raise ValueError("Refusing to resend ambiguous/failed operation: " + task["id"])
            print("RUN: " + task["id"], flush=True)
            freeze(path / "started.json", dict(status="started", request=req))
            begin = time.monotonic()
            try:
                raw = backend.generate(ids, NEW_TOKEN_BUDGET)
                if hasattr(backend, "torch"):
                    backend.torch.cuda.synchronize(backend.model.device)
            except BaseException as exc:
                freeze(path / "failed.json", dict(
                    status="failed", request=req,
                    error_type=type(exc).__name__,
                    elapsed_seconds=time.monotonic() - begin,
                ))
                reports(output, plan)
                raise
            invalid = validate_raw(raw, backend)
            freeze(path / "returned.json", dict(
                status="returned", request=req, raw=raw,
                elapsed_seconds=time.monotonic() - begin,
                validation_error=invalid,
            ))
            report = reports(output, plan)
            if invalid:
                raise ValueError("Unusable return retained; no resend: " + invalid)
        first_four.unchanged_source(pilot)
        return reports(output, plan)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Existing 8-response live v4 pilot directory")
    parser.add_argument("--output", required=True, help="Separate screen output directory")
    parser.add_argument("--live-qwen", action="store_true", help="Authorize 16 new 2048-token generations")
    args = parser.parse_args(argv)
    value = run(args.source, args.output, args.live_qwen)
    print(json.dumps(dict(status=value["status"], by_arm=value["by_arm"],
                          planned=value["planned"], returned_usable=value["returned_usable"]), indent=2))


if __name__ == "__main__":
    main()
