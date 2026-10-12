"""Fixed schedules, retained raw returns, explicit transport retries, no resampling.

Adapters supply make_plan/read_plan/request_for/task_meta/score_response and
mock_complete(plan, task). Their read_plan must reject source/config drift.
The analysis adapter supplies write_summary(output), without taking another lock.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_columns import provider
from exception_pilot.core import check_plan
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def _check_structure(core, plan):
    check_plan(plan)
    tasks = plan.get("tasks")
    if (plan.get("protocol_version") != core.PROTOCOL_VERSION or not isinstance(tasks, list)
            or not tasks or any(not isinstance(t, dict) or not isinstance(t.get("id"), str)
                                or not t["id"] for t in tasks)):
        raise ValueError("Invalid protocol or task schedule")
    if len({t["id"] for t in tasks}) != len(tasks):
        raise ValueError("Task IDs must be unique")
    cap = plan["config"].get("max_total_attempts")
    if type(cap) is not int or cap < len(tasks):
        raise ValueError("Cumulative attempt cap must cover the fixed schedule")


def _preview(core, plan):
    return [{"task_id": task["id"], "answer_key_not_sent_separately": core.task_meta(plan, task),
             "request": core.request_for(plan, task)} for task in plan["tasks"]]


def _check_preview(core, output, plan):
    path = Path(output) / "preview.json"
    if not path.exists() or json.loads(path.read_text()) != _preview(core, plan):
        raise ValueError("Frozen request preview differs from the saved plan")


def prepare(core, config, output):
    """Freeze every request without credentials or network access. Caller owns lock."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        plan = core.read_plan(output)
        _check_structure(core, plan)
        if plan["config"] != config:
            raise ValueError("Config differs from the saved plan")
        _check_preview(core, output, plan)
        return plan
    if any(path.name != "run.lock" for path in output.iterdir()):
        raise ValueError("Output is not empty and has no plan; use a new directory")
    plan = core.make_plan(config)
    _check_structure(core, plan)
    preview = _preview(core, plan)
    write_json(output / "preview.json", preview)
    lines = ["# Frozen study preview — no API calls", "", f"Protocol: {plan['protocol_version']}.",
             f"All {len(preview)} exact requests are in preview.json. The first {min(12, len(preview))} are below.",
             "Metadata and headings are for inspection; only each request is sent to the provider.", ""]
    for entry in preview[:12]:
        lines += ["## " + entry["task_id"], "", "Inspection metadata:", "```json",
                  json.dumps(entry["answer_key_not_sent_separately"], indent=2, ensure_ascii=False), "```", ""]
        for message in entry["request"]["messages"]:
            lines += ["### " + message["role"], "", "```text", message["content"], "```", ""]
    (output / "preview.md").write_text("\n".join(lines), encoding="utf-8")
    # A plan is published only after all frozen previews have been written.
    write_json(output / "plan.json", plan)
    return plan


def _score(core, task, response):
    score = core.score_response(task, response)
    reserved = {"attempt", "task_id", "plan_hash", "mode", "started_at", "finished_at",
                "request", "meta", "response", "raw_response", "raw_returned_at", "error", "http_status"}
    if (not isinstance(score, dict) or score.get("status") not in ("complete", "invalid")
            or reserved & set(score)):
        raise ValueError("Study scorer returned an invalid journal record")
    if score["status"] == "complete" and not response["complete"]:
        raise ValueError("An incomplete provider response cannot be scored valid")
    return score


def read_run(core, output, expected_mode=None):
    """Reconstruct and verify a journal; never select among multiple returned answers."""
    output = Path(output)
    plan = core.read_plan(output)
    _check_structure(core, plan)
    _check_preview(core, output, plan)
    attempts = load_attempts(output, plan)
    path = output / "execution.json"
    execution = json.loads(path.read_text()) if path.exists() else None
    if execution is None:
        if attempts:
            raise ValueError("Attempts exist without execution identity")
        return plan, None, attempts
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or expected_mode is not None and mode != expected_mode
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol_version") != plan["protocol_version"]):
        raise ValueError("Execution mode or frozen identity differs")
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Journal exceeds the cumulative attempt cap")
    cursor, identity_failed = 0, False
    for index, record in enumerate(attempts):
        if identity_failed:
            raise ValueError("A model identity failure cannot be followed by more attempts")
        if cursor >= len(plan["tasks"]) or record["task_id"] != plan["tasks"][cursor]["id"]:
            raise ValueError("Attempt order differs or a returned response was retried")
        task = plan["tasks"][cursor]
        if (record.get("mode") != mode or record.get("request") != core.request_for(plan, task)
                or record.get("meta") != core.task_meta(plan, task)):
            raise ValueError("Saved request, metadata or mode differs from the plan")
        if record["status"] in ("complete", "invalid"):
            if "raw_response" not in record or "response" not in record:
                raise ValueError("Returned response is missing retained raw provider content")
            normalized = provider.normalize(record["raw_response"], plan["config"], mode)
            score = _score(core, task, normalized)
            if record["response"] != normalized or any(record.get(k) != v for k, v in score.items()):
                raise ValueError("Response or scoring differs from retained raw provider content")
            identity_failed = normalized["model_identity"] in ("missing", "mismatch")
            cursor += 1
        else:
            if "response" in record or record["status"] == "error" and "raw_response" in record:
                raise ValueError("A returned response cannot be relabeled as a retryable error")
            if record["status"] == "started" and index != len(attempts) - 1:
                raise ValueError("An unresolved request cannot be retried")
    accepted_records(attempts)
    return plan, execution, attempts


def run(core, analysis, config, output, max_calls, resume=False, retry_errors=False,
        mock=False, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer and counts all new attempts")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require --mock; they cannot be labeled live evidence")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        prepare(core, config, output)
        plan, execution, attempts = read_run(core, output, mode)
        if execution is not None and not resume:
            raise ValueError("Run already started; add --resume")
        if any(attempt["status"] == "started" for attempt in attempts):
            raise ValueError("An unresolved request remains; it cannot be automatically retried, even with --retry-errors")
        records = accepted_records(attempts)
        if any(record["response"]["model_identity"] in ("missing", "mismatch") for record in records.values()):
            raise ValueError("Model identity failure is retained; preserve this run for review")
        pending = next((task for task in plan["tasks"] if task["id"] not in records), None)
        can_call = (pending is not None and len(attempts) < config["max_total_attempts"]
                    and (retry_errors or not any(a["task_id"] == pending["id"] for a in attempts)))
        if not mock and can_call:
            provider.credential(config)
        if execution is None:
            write_json(output / "execution.json", {"mode": mode, "protocol_version": plan["protocol_version"],
                       "plan_hash": plan["plan_hash"], "created_at": now()})
        calls, stopped, error_message = 0, "complete", None
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if len(attempts) >= config["max_total_attempts"]:
                    stopped = "total_attempt_limit"
                    break
                if calls >= max_calls:
                    stopped = "call_limit"
                    break
                if any(a["task_id"] == task["id"] for a in attempts) and not retry_errors:
                    stopped = "retry_requires_flag"
                    break
                payload = core.request_for(plan, task)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": core.task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    raw = (complete_fn(config, payload) if complete_fn is not None else
                           core.mock_complete(plan, task) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", error=str(exc), http_status=exc.status_code, finished_at=now())
                    write_json(path, record)
                    stopped, error_message = "provider_error", str(exc)
                    break
                # Retain the HTTP return before parsing/scoring. If local scoring
                # fails, the started record stays unresolved and is never retried.
                record.update(raw_response=raw, raw_returned_at=now())
                write_json(path, record)
                response = provider.normalize(raw, config, mode)
                score = _score(core, task, response)
                record.update(response=response, finished_at=now(), **score)
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if response["model_identity"] in ("missing", "mismatch"):
                    stopped = "model_identity_failure"
                    break
                # Refusal, truncation, and unparseable answer text are terminal data.
        except KeyboardInterrupt:
            stopped = "interrupted"
        finally:
            summary = analysis.write_summary(output)
        result = {"stopped": stopped, "calls_this_invocation": calls, "attempts_total": len(attempts),
                  "returned_answers": summary["returned_answers"], "valid_answers": summary["valid_answers"],
                  "invalid_answers_retained": summary["invalid_answers"], "planned_calls": len(plan["tasks"]),
                  "max_total_attempts": config["max_total_attempts"], "is_simulated": mock,
                  "analysis_status": summary["analysis_status"]}
        if error_message:
            result["error"] = error_message
        return result


def main(core, analysis, argv=None):
    """Shared CLI, normally invoked by a study's __main__.py."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=f"Frozen study {core.PROTOCOL_VERSION}; only live run makes API calls.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True, help="All new attempts in this invocation")
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true", help="Retry recorded transport errors only")
            child.add_argument("--mock", action="store_true", help="Offline simulated fixture; never model evidence")
    sub.add_parser("analyze").add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            with run_lock(args.output):
                plan = prepare(core, core.load_config(args.config), args.output)
            result = {"protocol": plan["protocol_version"], "model": plan["config"]["model"],
                      "planned_calls": len(plan["tasks"]), "max_total_attempts": plan["config"]["max_total_attempts"],
                      "api_calls": 0, "plan_hash": plan["plan_hash"]}
            if "worlds" in plan:
                result["worlds"] = len(plan["worlds"])
        elif args.command == "analyze":
            with run_lock(args.output):
                result = analysis.write_summary(args.output)
        else:
            result = run(core, analysis, core.load_config(args.config), args.output, args.max_calls,
                         args.resume, args.retry_errors, args.mock)
        print(json.dumps(result, indent=2, allow_nan=False))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit"))
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
