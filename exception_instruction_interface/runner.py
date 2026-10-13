"""Evidence-role journal lifecycle, adapted for the isolated interface diagnostic.

Reuse shared atomic storage, locking and provider transport; never retry returned outputs.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot import provider
from exception_pilot.core import digest
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from .core import make_plan, read_plan, request_for, request_hash, task_meta
from .scoring import score_response


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    """No credentials or network; callers serialize access with run_lock."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from this frozen run; use a new directory")
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output is not empty and has no frozen plan; use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    preview = [{"task_id": t["id"], "answer_key_not_sent_separately": task_meta(plan, t),
                "request_sha256": plan["request_hashes"][t["id"]], "request": request_for(plan, t)}
               for t in plan["tasks"]]
    write_json(output / "preview.json", preview)
    lines = ["# Instruction × output-interface preview — offline, no model responses", "",
             "24 frozen worlds × 2 recorded-label variants × 4 conditions = 192 fresh responses.",
             "All 192 requests follow in collection order. Headings/answer keys are not sent.",
             "Every block contains the four conditions; every response is first_value → reasoning → final_answer.",
             "", f"Plan hash: `{plan['plan_hash']}`", ""]
    for entry in preview:
        lines += ["## " + entry["task_id"], "",
                  "Answer key (not sent separately): " + json.dumps(entry["answer_key_not_sent_separately"]),
                  "", "User message:", "", "```text", entry["request"]["messages"][0]["content"], "```", "",
                  "Exact request (schema properties retain their order):", "", "```json",
                  json.dumps(entry["request"], ensure_ascii=False, indent=2), "```", ""]
    (output / "preview.md").write_text("\n".join(lines), encoding="utf-8")
    return plan


def normalized_response(raw, config, mode):
    response = provider.normalize(raw)
    response["model_mismatch"] = mode == "live" and response["model"] != config["model"]
    if response["model_mismatch"]:
        response.update(complete=False, finish_reason="model_mismatch")
    return response


def read_run(output, expected_mode=None):
    output = Path(output)
    plan = read_plan(output)
    attempts = load_attempts(output, plan)
    execution_path = output / "execution.json"
    execution = json.loads(execution_path.read_text()) if execution_path.exists() else None
    if execution is None:
        if attempts:
            raise ValueError("Attempts exist without execution metadata")
        return plan, None, attempts
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or expected_mode is not None and expected_mode != mode
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("config_hash") != digest(plan["config"])
            or execution.get("protocol_version") != plan["protocol_version"]):
        raise ValueError("Execution identity or mock/live mode differs")
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Journal exceeds the cumulative attempt cap")
    returned, identity_stopped = set(), False
    for index, record in enumerate(attempts):
        task = next((t for t in plan["tasks"] if t["id"] not in returned), None)
        if identity_stopped or task is None or task["id"] != record["task_id"]:
            raise ValueError("Journal order differs, a returned answer was retried, or collection followed model mismatch")
        if (record.get("mode") != mode or record.get("meta") != task_meta(plan, task)
                or record.get("config_hash") != digest(plan["config"])
                or request_hash(record.get("request")) != plan["request_hashes"][task["id"]]):
            raise ValueError("Saved request (including schema order), metadata, mode or config differs")
        if record["status"] in ("complete", "invalid"):
            response = normalized_response(record["response"]["raw_response"], plan["config"], mode)
            scored = score_response(task, response)
            if response != record["response"] or any(record.get(k) != v for k, v in scored.items()):
                raise ValueError("Saved normalized response or score differs from raw response")
            returned.add(task["id"])
            identity_stopped = response["model_mismatch"]
        elif "response" in record:
            raise ValueError("Returned content cannot become a retryable transport error")
        elif record["status"] == "started" and index != len(attempts) - 1:
            raise ValueError("An unresolved attempt cannot be retried automatically")
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    meta = task_meta(plan, task)
    fields = {"first_value": meta["expected"],
              "reasoning": "SIMULATED software fixture; not research evidence.",
              "final_answer": meta["expected"]}
    text = (json.dumps(fields) if task["interface"] == "json" else
            "\n".join(f"{key}: {value}" for key, value in fields.items()))
    return normalized_response({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]},
        plan["config"], "mock")


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None, live=False):
    if mock == live:
        raise ValueError("Choose exactly one of explicit --live or offline --mock")
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer, counting transport attempts too")
    if retry_errors and not resume:
        raise ValueError("--retry-errors requires --resume")
    if complete_fn is not None and not mock:
        raise ValueError("Injected providers are allowed only in SIMULATED mock runs")
    mode = "mock" if mock else "live"
    from .analysis import write_summary
    with run_lock(output) as output:
        prepare(config, output)
        plan, execution, attempts = read_run(output, mode)
        if execution is not None and not resume:
            raise ValueError("Run already started; add --resume")
        records = accepted_records(attempts)
        if any(r["response"]["model_mismatch"] for r in records.values()):
            raise ValueError("Model mismatch is a hard stop; preserve this run and do not resample")
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
                previous = [r for r in attempts if r["task_id"] == task["id"]]
                if any(r["status"] == "started" for r in previous):
                    stopped = "unresolved_attempt_requires_review"
                    break
                if previous and not retry_errors:
                    stopped = "retry_requires_flag"
                    break
                if not mock:
                    provider.credential(config)
                if execution is None:
                    execution = {"mode": mode, "protocol_version": plan["protocol_version"],
                                 "plan_hash": plan["plan_hash"], "config_hash": digest(config), "created_at": now()}
                    write_json(output / "execution.json", execution)
                payload = request_for(plan, task)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "config_hash": digest(config), "mode": mode, "status": "started", "started_at": now(),
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
                    stopped, error_message = "provider_error", str(exc)
                    break
                response = normalized_response(response["raw_response"], config, mode)
                record.update(response=response, finished_at=now(), **score_response(task, response))
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}" + (" SIMULATED" if mock else ""), flush=True)
                if response["model_mismatch"]:
                    stopped = "model_mismatch"
                    break
        except KeyboardInterrupt:
            stopped = "interrupted"
        finally:
            summary = write_summary(output)
        result = {"stopped": stopped, "calls_this_invocation": calls, "attempts_total": summary["attempts"],
                  "returned_answers": summary["returned_answers"], "valid_answers": summary["valid_answers"],
                  "invalid_answers_retained": summary["invalid_answers"], "planned_calls": len(plan["tasks"]),
                  "max_total_attempts": config["max_total_attempts"], "is_simulated": mock,
                  "analysis_status": summary["analysis_status"]}
        if error_message:
            result["error"] = error_message
        return result
