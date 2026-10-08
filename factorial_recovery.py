"""Finish an existing factorial plan while retaining unparseable returned answers.

Post-result amendment: see FACTORIAL_RECOVERY.md. The frozen packages and strict
parser are unchanged. Returned answers are never resampled or reclassified.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from exception_pilot import provider
from exception_pilot.core import digest, parse_answer
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from exception_factorial.analysis import factorial_contrasts, write_summary
from exception_factorial.core import (
    ARMS, BACKGROUNDS, QUESTIONS, UNCERTAINTY, make_plan, read_plan, request_for,
    source_digest, task_meta,
)
from exception_factorial.runner import mock_complete

AMENDMENT = "factorial-format-continuation-v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def recovery_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def is_unparseable_return(record):
    response = record.get("response", {})
    return (record["status"] == "invalid" and response.get("complete") is True
            and response.get("finish_reason") == "stop"
            and parse_answer(response.get("text")) is None)


def read_run(output, mode=None):
    output = Path(output)
    plan = read_plan(output)
    if plan["source_digest"] != source_digest() or plan != make_plan(plan["config"]):
        raise ValueError("Frozen code or plan differs; do not migrate or rewrite the existing run")
    execution = json.loads((output / "execution.json").read_text())
    if (execution.get("mode") not in ("live", "mock")
            or (mode is not None and execution["mode"] != mode)
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol_version") != plan["protocol_version"]):
        raise ValueError("Run mode or execution identity differs")
    attempts = load_attempts(output, plan)
    tasks = {t["id"]: t for t in plan["tasks"]}
    for record in attempts:
        if (record.get("mode") != execution["mode"]
                or record.get("request") != request_for(plan, tasks[record["task_id"]])):
            raise ValueError("Saved mode or request differs from the frozen plan")
        if record["status"] in ("complete", "invalid"):
            response = record["response"]
            normalized = provider.normalize(response["raw_response"])
            if normalized["model"] != plan["config"]["model"] and execution["mode"] == "live":
                normalized.update(complete=False, finish_reason="model_mismatch")
            answer = parse_answer(normalized["text"]) if normalized["complete"] else None
            if (response != normalized or record.get("answer") != answer
                    or record["status"] != ("complete" if answer else "invalid")):
                raise ValueError("Saved status or response differs from raw provider content")
    accepted_records(attempts)  # Reject duplicate returned answers before any new call.
    return plan, execution, attempts


def linear_estimates(plan, correctness):
    """Balanced full-plan means used only to bound the unscorable endpoints."""
    cells = {}
    for q in QUESTIONS:
        for u in UNCERTAINTY:
            for arm in ARMS:
                for bg in BACKGROUNDS:
                    values = [correctness[t["id"]] for t in plan["tasks"]
                              if (t["question_wording"], t["uncertainty_clause"],
                                  t["condition"], t["background"]) == (q, u, arm, bg)]
                    cells[q, u, arm, bg] = sum(values) / len(values)
    extras = {f"{q}/{u}": cells[q, u, "cot_neutral", "support"]
              - cells[q, u, "cot_neutral", "conflict"]
              - cells[q, u, "direct", "support"] + cells[q, u, "direct", "conflict"]
              for q in QUESTIONS for u in UNCERTAINTY}
    return {**{f"extra_penalty/{k}": v for k, v in extras.items()},
            **factorial_contrasts(extras)}


def sensitivity_bounds(plan, records):
    """Sharp bounds across all 0/1 assignments to invalid answers, never CIs."""
    if any(t["id"] not in records for t in plan["tasks"]):
        return None
    correctness = {t["id"]: (int(records[t["id"]]["answer"] == task_meta(plan, t)["expected"])
                            if records[t["id"]]["status"] == "complete" else 0)
                   for t in plan["tasks"]}
    unknown = [t["id"] for t in plan["tasks"] if records[t["id"]]["status"] == "invalid"]
    baseline = linear_estimates(plan, correctness)
    bounds = {k: [v, v] for k, v in baseline.items()}
    for task_id in unknown:
        flipped = linear_estimates(plan, {**correctness, task_id: 1})
        for key in bounds:
            coefficient = flipped[key] - baseline[key]
            bounds[key][0] += min(0, coefficient)
            bounds[key][1] += max(0, coefficient)
    return {"description": "Full-plan point-estimate bounds across every 0/1 assignment to invalid "
            "answers. These are sensitivity bounds, not scored answers or confidence intervals.",
            "invalid_answers_varied": len(unknown), "independent_lists": len(plan["worlds"]),
            "bounds": bounds}


def write_recovery_summary(output):
    output = Path(output)
    plan, execution, attempts = read_run(output)
    strict = write_summary(output)
    records = accepted_records(attempts)
    pending = [t["id"] for t in plan["tasks"] if t["id"] not in records]
    invalid = [{"task_id": t["id"], "attempt": records[t["id"]]["attempt"],
                "final_line": records[t["id"]]["response"]["text"].strip().splitlines()[-1]
                    if records[t["id"]]["response"]["text"].strip() else "",
                "complete_but_unparseable": is_unparseable_return(records[t["id"]])}
               for t in plan["tasks"] if t["id"] in records and records[t["id"]]["status"] == "invalid"]
    result = {"amendment": AMENDMENT, "plan_hash": plan["plan_hash"], "mode": execution["mode"],
              "is_simulated": execution["mode"] == "mock", "planned_calls": len(plan["tasks"]),
              "returned_answers": len(records), "valid_answers": strict["complete_answers"],
              "invalid_answers": len(invalid), "unattempted_or_unresolved_tasks": len(pending),
              "all_planned_tasks_returned": not pending, "strict_paired_lists": strict["paired_lists"],
              "strict_analysis_status": strict["analysis_status"], "retained_invalid": invalid,
              "sensitivity": sensitivity_bounds(plan, records),
              "automatic_followup": False,
              "interpretation": "The original strict analysis is unchanged. Returned invalid answers "
              "remain invalid and are never resampled. Continuation is a documented post-result "
              "amendment, not an unmodified completion of the original protocol."}
    write_json(output / "recovery-summary.json", result)
    lines = ["# Factorial continuation audit" + (" — SIMULATED" if result["is_simulated"] else ""), "",
             result["interpretation"], "",
             f"Returned: {len(records)}/{len(plan['tasks'])}; valid: {result['valid_answers']}; "
             f"invalid retained: {len(invalid)}; tasks without a returned answer: {len(pending)}.", "",
             f"Strict complete lists: {strict['paired_lists']}. Strict status: `{strict['analysis_status']}`.", "",
             "See summary.md for the unchanged strict paired estimates and all denominators. "
             "The frozen parser does not extract labels from sentences.", "", "## Retained invalid answers", ""]
    for row in invalid:
        lines += [f"- `{row['task_id']}` (attempt {row['attempt']}): " + json.dumps(row['final_line'])]
    if result["sensitivity"] is not None:
        lines += ["", "## Sensitivity bounds", "", result["sensitivity"]["description"], "",
                  "Each contrast has its own bounds; extreme assignments can differ across contrasts. "
                  "Sampling uncertainty is separate and is not represented by these bounds.", "",
                  "| Full-plan contrast | Lower | Upper |", "|---|---:|---:|"]
        for key, (lo, hi) in result["sensitivity"]["bounds"].items():
            lines.append(f"| {key} | {100 * lo:.2f} pp | {100 * hi:.2f} pp |")
    else:
        lines += ["", "Full-plan sensitivity bounds will be computed after every planned task returns."]
    (output / "recovery-summary.md").write_text("\n".join(lines) + "\n")
    return result


def run(output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    if not resume:
        raise ValueError("This command continues an existing run; --resume is required")
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer")
    if complete_fn is not None and not mock:
        raise ValueError("Injected test responses require mock=True")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        plan, execution, attempts = read_run(output, mode)
        records = accepted_records(attempts)
        if any(r["status"] == "invalid" and not is_unparseable_return(r) for r in records.values()):
            raise ValueError("A response is incomplete, refused, or otherwise invalid; inspect it separately")
        manifest_path = output / "recovery.json"
        identity = {"amendment": AMENDMENT, "mode": mode, "plan_hash": plan["plan_hash"],
                    "base_source_digest": plan["source_digest"], "recovery_source_digest": recovery_digest()}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            if ({k: manifest.get(k) for k in identity} != identity
                    or digest(attempts[:manifest["initial_attempt_count"]]) != manifest["initial_journal_digest"]):
                raise ValueError("Recovery code, identity, or pre-recovery journal changed")
        else:
            if not any(is_unparseable_return(r) for r in records.values()):
                raise ValueError("Use the original runner unless an unparseable returned answer blocks it")
            manifest = {**identity, "created_at": now(), "initial_attempt_count": len(attempts),
                        "initial_journal_digest": digest(attempts),
                        "initial_invalid_task_ids": [k for k, r in records.items() if r["status"] == "invalid"],
                        "policy": "Keep every returned answer unchanged; continue only tasks without a return."}
        if not mock:
            provider.credential(plan["config"])
        if not manifest_path.exists():
            write_json(manifest_path, manifest)
        calls, stop, error_message = 0, "all_planned_tasks_returned", None
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if any(a["task_id"] == task["id"] for a in attempts) and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                payload = request_for(plan, task)
                number = len(attempts) + 1
                record = {"attempt": number, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(), "request": payload,
                          "meta": task_meta(plan, task), "amendment": AMENDMENT}
                path = output / "attempts" / f"{number:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    response = (complete_fn(plan["config"], payload) if complete_fn is not None else
                                mock_complete(plan, task) if mock else provider.complete(plan["config"], payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                answer = parse_answer(response["text"]) if response["complete"] else None
                record.update(status="complete" if answer else "invalid", finished_at=now(),
                              response=response, answer=answer)
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if not response["complete"]:
                    stop = "invalid_provider_response"
                    break
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            report = write_recovery_summary(output)
        outcome = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": len(attempts),
                   "valid_answers": report["valid_answers"], "invalid_answers_retained": report["invalid_answers"],
                   "planned_calls": report["planned_calls"], "is_simulated": mock,
                   "tasks_without_return": report["unattempted_or_unresolved_tasks"],
                   "strict_analysis_status": report["strict_analysis_status"]}
        if error_message:
            outcome["error"] = error_message
        return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "analyze"):
        child = sub.add_parser(name)
        child.add_argument("--output", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True)
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true")
            child.add_argument("--mock", action="store_true", help="Only for an existing simulated run")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run(args.output, args.max_calls, args.resume, args.retry_errors, args.mock)
        else:
            with run_lock(args.output):
                result = write_recovery_summary(args.output)
        print(json.dumps(result, indent=2))
        return int(args.command == "run" and result["stopped"] not in ("all_planned_tasks_returned", "call_limit"))
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
