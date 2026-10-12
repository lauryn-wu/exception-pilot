"""Frozen schedule and atomic journal; returned responses are never resampled."""

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from . import provider
from .core import make_plan, read_plan, request_for, score_response, task_meta


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    """Prepare offline; callers using this function directly must hold run_lock."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        plan, frozen_config = read_plan(output)
        if frozen_config != config:
            raise ValueError("Config differs from the saved run; use a new output directory")
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output is not empty and has no complete frozen plan; use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    write_json(output / "run_config.json", {
        "config": config, "config_hash": digest(config), "plan_hash": plan["plan_hash"]})
    preview = [{"task_id": task["id"], "answer_key_not_sent_separately": task_meta(plan, task),
                "request": request_for(plan, task, config)} for task in plan["tasks"]]
    write_json(output / "preview.json", preview)
    lines = ["# All-row fresh-world confirmation preview — no API calls", "",
             "24 fresh worlds × 2 record variants × 10 target rows × 2 response arms = "
             "960 separate requests across 24 paired worlds. The first scheduled world's 40 exact requests appear below; "
             "preview.json contains all 960. Answer keys and headings are for inspection only.", ""]
    first_world = plan["tasks"][0]["world_id"]
    for item, task in zip(preview, plan["tasks"]):
        if task["world_id"] != first_world:
            continue
        meta = item["answer_key_not_sent_separately"]
        lines += ["## " + item["task_id"], "",
                  f"Expected {meta['expected']}; pattern {meta['pattern_label']}; "
                  f"target row {task['position']}.", "", "```text",
                  item["request"]["messages"][0]["content"], "```", ""]
    (output / "preview.md").write_text("\n".join(lines))
    return plan


def read_run(output, expected_mode=None):
    """Revalidate every journal entry against its frozen request and raw response."""
    output = Path(output)
    plan, config = read_plan(output)
    attempts = load_attempts(output, plan)
    path = output / "execution.json"
    execution = json.loads(path.read_text()) if path.exists() else None
    if execution is None:
        if attempts:
            raise ValueError("Attempts exist without execution metadata")
        return plan, config, None, attempts
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or expected_mode is not None and mode != expected_mode
            or execution.get("config_hash") != digest(config)
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol_version") != plan["protocol_version"]):
        raise ValueError("Execution identity or run mode differs")
    if len(attempts) > config["max_total_attempts"]:
        raise ValueError("Fixed cumulative attempt cap exceeded")
    tasks = {task["id"]: task for task in plan["tasks"]}
    returned, identity_stopped = set(), False
    for index, record in enumerate(attempts):
        if record["status"] == "started" and index != len(attempts) - 1:
            raise ValueError("An unresolved started attempt cannot be followed by another attempt")
        task = tasks[record["task_id"]]
        next_task = next((task for task in plan["tasks"] if task["id"] not in returned), None)
        if identity_stopped or next_task is None or task["id"] != next_task["id"]:
            raise ValueError("Attempt order differs, a returned answer was retried, or collection continued after model mismatch")
        if (record.get("mode") != mode or record.get("config_hash") != digest(config)
                or record.get("request") != request_for(plan, task, config)
                or record.get("meta") != task_meta(plan, task)):
            raise ValueError("Saved request, metadata, mode or config differs")
        if record["status"] in ("complete", "invalid"):
            response = provider.normalize(record["response"]["raw_response"], config, mode)
            scored = score_response(task, response)
            if response != record["response"] or any(record.get(key) != value for key, value in scored.items()):
                raise ValueError("Saved response/scoring differs from raw returned data")
            returned.add(task["id"])
            identity_stopped = response["model_mismatch"]
        elif "response" in record:
            raise ValueError("A returned response cannot become a retryable transport error")
    accepted_records(attempts)
    return plan, config, execution, attempts


def mock_complete(plan, task, config):
    meta = task_meta(plan, task)
    pretext = (f"SIMULATED fixture: {meta['item_id']} has recorded class {meta['expected']}.\n"
               if task["arm"] == "visible" else "")
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": pretext + "ANSWER: " + meta["expected"]},
                     "finish_reason": "stop"}]}, config, "mock")


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer including transport attempts")
    if retry_errors and not resume:
        raise ValueError("--retry-errors requires --resume")
    if complete_fn is not None and not mock:
        raise ValueError("Injected providers are allowed only in SIMULATED mock runs")
    mode = "mock" if mock else "live"
    from .analysis import write_summary
    with run_lock(output) as output:
        prepare(config, output)
        plan, _, execution, attempts = read_run(output, mode)
        if execution is not None and not resume:
            raise ValueError("Run already started; add --resume")
        records = accepted_records(attempts)
        if any(record["response"]["model_mismatch"] for record in records.values()):
            raise ValueError("Model mismatch is a hard stop; preserve this run and do not resample")
        if not mock and len(records) < len(plan["tasks"]) and len(attempts) < config["max_total_attempts"]:
            provider.credential(config)
        if execution is None:
            write_json(output / "execution.json", {"mode": mode, "protocol_version": plan["protocol_version"],
                       "plan_hash": plan["plan_hash"], "config_hash": digest(config), "created_at": now()})
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
                previous = [record for record in attempts if record["task_id"] == task["id"]]
                if any(record["status"] == "started" for record in previous):
                    stop = "unresolved_attempt_requires_review"
                    break
                if previous and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                payload = request_for(plan, task, config)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "config_hash": digest(config), "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    response = (complete_fn(config, payload) if complete_fn is not None else
                                mock_complete(plan, task, config) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                response = provider.normalize(response["raw_response"], config, mode)
                record.update(response=response, finished_at=now(), **score_response(task, response))
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}" + (" SIMULATED" if mock else ""), flush=True)
                if response["model_mismatch"]:
                    stop = "model_mismatch"
                    break
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        result = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": summary["attempts"],
                  "returned_answers": summary["returned_answers"], "invalid_answers_retained": summary["invalid_answers"],
                  "planned_calls": len(plan["tasks"]), "is_simulated": mock, "decision": summary["decision"]}
        if error_message:
            result["error"] = error_message
        return result
