"""Bounded, explicitly resumed execution with full per-attempt audit files."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from . import provider
from .analysis import write_summary
from .core import (make_plan, source_digest, messages_for, payload_for, parse_answer,
                   task_meta, world_for, opposite)
from .storage import (write_json, run_lock, read_plan, load_attempts, accepted_records)


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    output = Path(output)
    plan_path = output / "plan.json"
    if plan_path.exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from saved plan. Use a new output directory.")
        if plan["source_digest"] != source_digest():
            raise ValueError("Code differs from saved plan. Use a new output directory.")
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output directory is not empty and has no plan; use a new directory")
    plan = make_plan(config)
    write_json(plan_path, plan)
    # Preview real first calls and a canonical diagnostic. No simulated model
    # output is ever silently inserted into a live preview or training history.
    examples = []
    seen = set()
    for task in plan["tasks"]:
        key = (task["condition"], task.get("background"))
        if key in seen:
            continue
        if config["stage"] == 1 and not (task["round"] == 1 and task["position"] == 1):
            continue
        seen.add(key)
        examples.append({"task_id": task["id"], "answer_key_not_sent_to_model": task_meta(plan, task),
                         "request": payload_for(config, task, messages_for(plan, task, {}))})
    write_json(output / "preview.json", examples)
    return plan


def mock_complete(plan, task, payload):
    """Intentionally engineered positive fixture, not a prediction of a real LLM."""
    item = world_for(plan, task)["items"][task["item_index"]]
    label = item["label"]
    if task["condition"] == "cot" and item["is_exception"] and task.get("background", "conflict") == "conflict":
        label = opposite(label)
    text = ("SIMULATED fixture for software testing.\n" + label
            if task["condition"].startswith("cot") else label)
    raw = {"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
           "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
    return provider.normalize(raw)


def parent_reference(config, parent, mode):
    if config["stage"] == 1:
        if parent:
            raise ValueError("--stage1-run applies only to stage 2")
        return None
    if not parent:
        raise ValueError("Stage 2 requires --stage1-run pointing to a completed eligible stage-1 run")
    with run_lock(parent):
        parent_plan = read_plan(parent)
        summary = write_summary(parent)
        parent_execution = json.loads((Path(parent) / "execution.json").read_text())
    if parent_plan["config"]["stage"] != 1 or not summary["complete"]:
        raise ValueError("Stage-1 parent is not a complete stage-1 run")
    if summary["screen"]["decision"] != "eligible_for_diagnostics":
        raise ValueError("Stage-1 screen did not meet the predeclared diagnostic gate")
    if parent_execution["mode"] != mode:
        raise ValueError("A simulated run cannot authorize live stage 2")
    for key in ("model", "temperature", "max_completion_tokens"):
        if parent_plan["config"][key] != config[key]:
            raise ValueError(f"Stage-2 {key} must match its stage-1 parent")
    return {"path": str(Path(parent).resolve()), "plan_hash": parent_plan["plan_hash"]}


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False,
        stage1_run=None, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer; it caps attempts in this invocation")
    mode = "mock" if mock else "live"
    parent = parent_reference(config, stage1_run, mode)
    with run_lock(output) as output:
        plan = prepare(config, output)
        attempts = load_attempts(output, plan)
        execution_path = output / "execution.json"
        identity = {"mode": mode, "parent": parent, "plan_hash": plan["plan_hash"]}
        if execution_path.exists():
            execution = json.loads(execution_path.read_text())
            if {k: execution[k] for k in identity} != identity:
                raise ValueError("Run mode or parent differs; use a new output directory")
            if not resume:
                raise ValueError("This run already started. Add --resume to continue it.")
        elif attempts:
            raise ValueError("Attempt files exist without execution metadata")
        records = accepted_records(attempts)
        if any(r["status"] == "invalid" for r in records.values()):
            raise ValueError("A returned answer was invalid. Inspect its raw response; do not resample it. "
                             "If the protocol needs a fix, preserve this run and start a new one.")
        if not mock and complete_fn is None:
            provider.credential(config)  # Fail before recording a paid attempt.
        if not execution_path.exists():
            write_json(execution_path, {**identity, "created_at": now()})
        calls = 0
        stop = "complete"
        error_message = None
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                prior_attempts = [a for a in attempts if a["task_id"] == task["id"]]
                if prior_attempts and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                messages = messages_for(plan, task, records)
                payload = payload_for(config, task, messages)
                number = len(attempts) + 1
                record = {"attempt": number, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(), "request": payload,
                          "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{number:06d}.json"
                write_json(path, record)  # Crash after this point: request may have been billed.
                attempts.append(record)
                calls += 1
                try:
                    result = (complete_fn(config, payload) if complete_fn is not None else
                              mock_complete(plan, task, payload) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc),
                                  http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                answer = parse_answer(result["text"]) if result["complete"] else None
                record.update(status="complete" if answer else "invalid", finished_at=now(),
                              response=result, answer=answer)
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if not answer:
                    stop = "invalid_response"
                    break
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        outcome = {"stopped": stop, "calls_this_invocation": calls,
                   "attempts_total": summary["attempts"], "valid_answers": summary["complete_answers"],
                   "planned_calls": summary["planned_calls"], "is_simulated": mock,
                   "screen": summary["screen"]}
        if error_message:
            outcome["error"] = error_message
        return outcome
