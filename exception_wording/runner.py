"""Bounded execution of the fresh-data wording study; previous studies stay frozen."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot import provider
from exception_pilot.core import opposite, parse_answer
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json

from .analysis import write_summary
from .core import make_plan, read_plan, request_for, source_digest, task_meta


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
    tasks = [t for t in plan["tasks"] if t["world_id"] == plan["worlds"][0]["id"]]
    write_json(output / "preview.json", [
        {"task_id": t["id"], "answer_key_not_sent_separately_to_model": task_meta(plan, t),
         "request": request_for(plan, t)} for t in tasks])
    from .core import QUESTIONS, ARMS, QUESTION_TEXT, INSTRUCTIONS
    lines = ["# Wording preview — no model calls", "",
             "20 fresh lists × 2 targets × 2 backgrounds × 2 questions × 3 instructions = 480 calls "
             "in the default config. This preview includes every first-list request.", "",
             "All conditions share the verified record table and target attributes. Both backgrounds "
             "have 20% exceptions; only six non-target labels change.", "",
             "## Exact question and response wording", ""]
    for q in QUESTIONS:
        lines += [f"### Question: {q}", "", QUESTION_TEXT[q], ""]
    for arm in ARMS:
        lines += [f"### Response: {arm}", "", INSTRUCTIONS[arm], ""]
    lines += ["## All 24 first-list requests", "",
              "Condition headings and answer keys below are for human inspection, never extra API content.", ""]
    for task in tasks:
        meta = task_meta(plan, task)
        lines += [f"### {task['id']}", "", f"Answer key: {meta['expected']} (already in the record table).", "",
                  "```text", request_for(plan, task)["messages"][0]["content"], "```", ""]
    (output / "preview.md").write_text("\n".join(lines) + "\n")
    return plan


def mock_complete(plan, task):
    """Engineered positive fixture, never a forecast or scientific observation."""
    label = task_meta(plan, task)["expected"]
    if task["condition"] != "direct" and task["background"] == "conflict":
        label = opposite(label)
    text = "SIMULATED software fixture.\n" + label if task["condition"] != "direct" else label
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer; it caps attempts in this invocation")
    if complete_fn is not None and not mock:
        raise ValueError("Injected test responses require mock=True; they cannot be labeled real evidence")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        plan = prepare(config, output)
        attempts = load_attempts(output, plan)
        execution_path = output / "execution.json"
        identity = {"mode": mode, "protocol_version": plan["protocol_version"],
                    "plan_hash": plan["plan_hash"]}
        if execution_path.exists():
            execution = json.loads(execution_path.read_text())
            if {k: execution.get(k) for k in identity} != identity:
                raise ValueError("Run mode or identity differs; use a new output directory")
            if not resume:
                raise ValueError("This run already started. Add --resume to continue it.")
        elif attempts:
            raise ValueError("Attempt files exist without execution metadata")
        records = accepted_records(attempts)
        if any(r["status"] == "invalid" for r in records.values()):
            raise ValueError("A returned answer was invalid. Inspect it; never resample it. "
                             "Preserve this run if a protocol fix is needed.")
        if not mock:
            provider.credential(config)
        if not execution_path.exists():
            write_json(execution_path, {**identity, "created_at": now()})
        calls, stop, error_message = 0, "complete", None
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
                          "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{number:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    result = (complete_fn(config, payload) if complete_fn is not None else
                              mock_complete(plan, task) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
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
