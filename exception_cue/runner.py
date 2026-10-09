"""One request per task; a returned answer is never retried or selected away."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot import provider
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from .analysis import write_summary
from .core import make_plan, read_plan, request_for, score_response, task_meta


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    output = Path(output)
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from the saved plan; do not change an ongoing study")
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output directory is not empty and has no plan; use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    tasks = plan["tasks"]
    preview = [{"task_id": t["id"], "answer_key_not_sent_separately": task_meta(plan, t),
                "request": request_for(plan, t)} for t in tasks]
    write_json(output / "preview.json", preview)
    lines = ["# Reasoning instruction and output diagnostic — no API calls", "",
             "24 worlds × 2 recorded-class variants × 3 conditions = 144 planned calls. "
             "The cumulative cap is 160 attempts, including explicitly requested transport retries.", "",
             "This document shows the six requests from the first world; preview.json contains "
             "all 144 exact requests. Each request starts an independent conversation. "
             "All targets have a recorded class. The shared MISSING definition is preserved from "
             "the previous task wording. Headings and answer keys below are for human inspection "
             "and are not added to API messages.", ""]
    for entry in preview[:6]:
        meta = entry["answer_key_not_sent_separately"]
        lines += [f"## {entry['task_id']}", "", f"Recorded class: {meta['expected']}; "
                  f"same-climate pattern: {meta['pattern_label']}.",
                  "", "```text", entry["request"]["messages"][0]["content"], "```", ""]
    (output / "preview.md").write_text("\n".join(lines))
    return plan


def normalized_response(raw, config, mode):
    result = provider.normalize(raw)
    if mode == "live" and result["model"] != config["model"]:
        result.update(complete=False, finish_reason="model_mismatch")
    return result


def read_run(output, expected_mode=None):
    output = Path(output)
    plan = read_plan(output)
    attempts = load_attempts(output, plan)
    path = output / "execution.json"
    execution = json.loads(path.read_text()) if path.exists() else None
    if execution is None:
        if attempts:
            raise ValueError("Attempt files exist without execution metadata")
        return plan, None, attempts
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or (expected_mode is not None and mode != expected_mode)
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol_version") != plan["protocol_version"]):
        raise ValueError("Run mode or execution identity differs")
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Journal exceeds the fixed cumulative attempt cap")
    tasks = {t["id"]: t for t in plan["tasks"]}
    returned = set()
    for record in attempts:
        task = tasks[record["task_id"]]
        next_task = next((t for t in plan["tasks"] if t["id"] not in returned), None)
        if task["id"] in returned:
            raise ValueError("A task was retried after a returned answer; refusing response selection")
        if next_task is None or task["id"] != next_task["id"]:
            raise ValueError("Attempt order differs from the fixed randomized schedule")
        if (record.get("mode") != mode or record.get("request") != request_for(plan, task)
                or record.get("meta") != task_meta(plan, task)):
            raise ValueError("Saved request, metadata, or mode differs from the frozen plan")
        if record["status"] in ("complete", "invalid"):
            response = record["response"]
            normalized = normalized_response(response["raw_response"], plan["config"], mode)
            scored = score_response(task, normalized)
            if response != normalized or any(record.get(k) != v for k, v in scored.items()):
                raise ValueError("Saved scoring or response differs from raw provider content")
            returned.add(task["id"])
        elif "response" in record:
            raise ValueError("A returned response cannot be relabeled as a retryable transport error")
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    """All-correct fixture, explicitly simulated; zero between-arm effects."""
    meta = task_meta(plan, task)
    text = "ANSWER: " + meta["expected"]
    if task["arm"] == "visible":
        text = "SIMULATED software fixture.\n" + text
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer; it counts attempts including errors")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require mock=True and cannot be labeled real evidence")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        prepare(config, output)
        plan, execution, attempts = read_run(output, mode)
        if execution is not None and not resume:
            raise ValueError("This run already started. Add --resume to continue it")
        records = accepted_records(attempts)
        if any(not r["response"]["complete"] for r in records.values()):
            raise ValueError("A returned response is truncated, refused, or technically invalid. "
                             "Preserve it and inspect the run; it cannot be resampled")
        if not mock and len(records) < len(plan["tasks"]) and len(attempts) < config["max_total_attempts"]:
            provider.credential(config)
        if execution is None:
            write_json(output / "execution.json", {"mode": mode, "protocol_version": plan["protocol_version"],
                       "plan_hash": plan["plan_hash"], "created_at": now()})
        calls, stop, error_message = 0, "complete", None
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "total_attempt_limit"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                if any(a["task_id"] == task["id"] for a in attempts) and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                payload = request_for(plan, task)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    response = (complete_fn(config, payload) if complete_fn is not None else
                                mock_complete(plan, task) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                record.update(response=response, finished_at=now(), **score_response(task, response))
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if not response["complete"]:
                    stop = "invalid_provider_response"
                    break
                # Format violations and unparseable final answers remain data; never resample.
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        outcome = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": summary["attempts"],
                   "returned_answers": summary["returned_answers"], "valid_answers": summary["valid_answers"],
                   "invalid_answers_retained": summary["invalid_answers"], "planned_calls": summary["planned_calls"],
                   "max_total_attempts": config["max_total_attempts"], "is_simulated": mock,
                   "analysis_status": summary["analysis_status"]}
        if error_message:
            outcome["error"] = error_message
        return outcome
