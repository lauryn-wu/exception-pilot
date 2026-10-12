"""Resumable fixed schedule with raw responses, no response replacement."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from . import provider
from .core import make_plan, read_plan, request_for, score_response, task_meta


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from the saved plan")
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output is not empty and has no plan; use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    preview = [{"task_id": t["id"], "answer_key_not_sent_separately": task_meta(plan, t),
                "request": request_for(plan, t)} for t in plan["tasks"]]
    write_json(output / "preview.json", preview)
    lines = ["# Column study preview — no API calls", "",
             "24 previously inspected worlds × 2 record variants × 4 column sets × 3 arms = 576 calls.",
             "All 576 exact requests are in preview.json. Below are all 24 requests from the first world.",
             "Headings and answer keys are for inspection and are never added to provider messages.", ""]
    for entry in preview[:24]:
        meta = entry["answer_key_not_sent_separately"]
        lines += ["## " + entry["task_id"], "", f"Recorded: {meta['expected']}; background-pattern label: {meta['pattern_label']}; row: {meta['target_position']}.",
                  "", "```text", entry["request"]["messages"][0]["content"], "```", ""]
    (output / "preview.md").write_text("\n".join(lines))
    return plan


def read_run(output, expected_mode=None):
    output = Path(output)
    plan = read_plan(output)
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
    cursor = 0
    for index, record in enumerate(attempts):
        if cursor >= len(plan["tasks"]) or record["task_id"] != plan["tasks"][cursor]["id"]:
            raise ValueError("Attempt order differs or a returned response was retried")
        task = plan["tasks"][cursor]
        if (record.get("mode") != mode or record.get("request") != request_for(plan, task)
                or record.get("meta") != task_meta(plan, task)):
            raise ValueError("Saved request, metadata or mode differs from the plan")
        if record["status"] in ("complete", "invalid"):
            normalized = provider.normalize(record["response"]["raw_response"], plan["config"], mode)
            if record["response"] != normalized or any(record.get(k) != v for k, v in score_response(task, normalized).items()):
                raise ValueError("Response or scoring differs from retained raw provider content")
            cursor += 1
        else:
            if "response" in record:
                raise ValueError("A returned response cannot be relabeled as a retryable error")
            if record["status"] == "started" and index != len(attempts) - 1:
                raise ValueError("An unresolved request cannot be retried")
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    answer = task_meta(plan, task)["expected"]
    text = "ANSWER: " + answer
    if task["arm"] != "direct":
        text = "SIMULATED software fixture; not model evidence.\n" + text
    if task["arm"] == "copy_class":
        text = "COPIED: " + answer + "\n" + text
    return {"id": "SIMULATED-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
            "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    from .analysis import write_summary
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer and counts all new attempts")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require --mock; they cannot be labeled live evidence")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        prepare(config, output)
        plan, execution, attempts = read_run(output, mode)
        if execution is not None and not resume:
            raise ValueError("Run already started; add --resume")
        if any(a["status"] == "started" for a in attempts):
            raise ValueError("An unresolved request remains; it cannot be automatically retried, even with --retry-errors")
        records = accepted_records(attempts)
        if any(r["response"]["model_identity"] in ("missing", "mismatch") for r in records.values()):
            raise ValueError("Model identity failure is retained; preserve this run for review")
        if not mock and len(records) < 576 and len(attempts) < config["max_total_attempts"]:
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
                payload = request_for(plan, task)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    raw = (complete_fn(config, payload) if complete_fn is not None else
                           mock_complete(plan, task) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", error=str(exc), http_status=exc.status_code, finished_at=now())
                    write_json(path, record)
                    stopped, error_message = "provider_error", str(exc)
                    break
                response = provider.normalize(raw, config, mode)
                record.update(response=response, finished_at=now(), **score_response(task, response))
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if response["model_identity"] in ("missing", "mismatch"):
                    stopped = "model_identity_failure"
                    break
                # Refusals, truncation and invalid answer formats remain terminal data.
        except KeyboardInterrupt:
            stopped = "interrupted"
        finally:
            summary = write_summary(output)
        result = {"stopped": stopped, "calls_this_invocation": calls, "attempts_total": len(attempts),
                  "returned_answers": summary["returned_answers"], "valid_answers": summary["valid_answers"],
                  "invalid_answers_retained": summary["invalid_answers"], "planned_calls": 576,
                  "max_total_attempts": config["max_total_attempts"], "is_simulated": mock,
                  "analysis_status": summary["analysis_status"]}
        if error_message:
            result["error"] = error_message
        return result
