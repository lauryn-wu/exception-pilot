"""Bounded, resumable ordinary-chat collection for the query-role screen.

Every returned response is retained, including malformed, empty, or truncated
responses. Only unresolved transport attempts may be retried, with an explicit
flag and both per-task and global retry budgets. There are no accuracy gates.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

from exception_mistral_prefix_v2 import provider
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from .core import make_plan, read_plan, request_for, score_response, task_meta


def now():
    return datetime.now(timezone.utc).isoformat()


def _preview(plan):
    return [{"task_id": task["id"], "meta_not_sent": task_meta(plan, task),
             "request": request_for(plan, task)} for task in plan["tasks"]]


def _preview_markdown(plan, entries):
    lines = ["# Query-role screen — every exact prompt", "",
             "Preparing this file makes zero API calls. All 144 requests are frozen in advance. "
             "There are no outcome-dependent gates, interventions, or assistant prefixes.", "",
             "Each block below contains the complete user message. Metadata, including the expected answer, "
             "is shown for audit and is never supplied to the model. preview.json contains every complete API request in execution order.", "",
             "Plan hash: `" + plan["plan_hash"] + "`", "", "## Shared request settings", "", "```json",
             json.dumps({k: v for k, v in entries[0]["request"].items() if k != "messages"},
                        ensure_ascii=False, indent=2, allow_nan=False), "```", ""]
    for entry in entries:
        lines += ["## " + entry["task_id"], "", "### Metadata — not sent to the model", "", "```json",
                  json.dumps(entry["meta_not_sent"], ensure_ascii=False, indent=2, allow_nan=False), "```", "",
                  "### Exact user message", ""]
        for message in entry["request"]["messages"]:
            text = message["content"]
            fence = "`" * max(3, 1 + max((len(match.group()) for match in re.finditer(r"`+", text)), default=0))
            lines.append(fence + "text\n" + text + ("" if text.endswith("\n") else "\n") + fence)
            lines.append("")
    return "\n".join(lines) + "\n"


def _check_artifacts(output, plan):
    output = Path(output)
    checksum = hashlib.sha256((output / "plan.json").read_bytes()).hexdigest()
    if (output / "plan.sha256").read_text().strip() != checksum:
        raise ValueError("Plan file checksum changed; preserve this run")
    entries = _preview(plan)
    if json.loads((output / "preview.json").read_text()) != entries:
        raise ValueError("Exact request preview changed; preserve this run")
    if (output / "preview.md").read_text() != _preview_markdown(plan, entries):
        raise ValueError("Readable prompt preview changed; preserve this run")


def _prepare_locked(config, output):
    output = Path(output)
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from the frozen run")
        _check_artifacts(output, plan)
        return plan
    if any(p.name != "run.lock" for p in output.iterdir()):
        raise ValueError("Output is not empty; preserve it and use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    (output / "plan.sha256").write_text(hashlib.sha256((output / "plan.json").read_bytes()).hexdigest() + "\n")
    entries = _preview(plan)
    write_json(output / "preview.json", entries)
    (output / "preview.md").write_text(_preview_markdown(plan, entries))
    return plan


def prepare(config, output):
    """Freeze a fresh plan without contacting a provider; preserve existing runs."""
    from .analysis import write_summary
    with run_lock(output):
        plan = _prepare_locked(config, output)
        read_run(output)
        write_summary(output)
        return plan


def _hard_failure(plan, response, observed_model, seen_ids, mode):
    """Identity failures stop; ordinary response/format failures do not."""
    model = response.get("model")
    if isinstance(model, str) and model.strip():
        if mode == "live" and model != plan["config"]["model"]:
            return "unexpected_model" if observed_model is None else "response_model_changed"
        if observed_model is not None and model != observed_model:
            return "response_model_changed"
    response_id = response.get("response_id")
    if isinstance(response_id, str) and response_id.strip():
        if response_id in seen_ids:
            return "duplicate_response_id"
    elif response.get("complete") is True:
        # An otherwise valid response needs an identity. A malformed raw body
        # may lack every field, including id; that remains an unscorable return.
        return "missing_response_id"
    return None


def _score(plan, task, response, observed_model, seen_ids, mode):
    scored = score_response(task, response, task_meta(plan, task))
    failure = _hard_failure(plan, response, observed_model, seen_ids, mode)
    if failure:
        scored.update(status="invalid", answer=None, format_valid=False, correct=None,
                      pattern=None, decoded_value=None, score=None, invalid_reason=failure,
                      direct_instruction_adherent=None)
    return scored, failure


def _model_after(observed_model, response):
    candidate = response.get("model")
    return observed_model or (candidate if isinstance(candidate, str) and candidate.strip() else None)


def read_run(output, expected_mode=None):
    """Validate frozen requests, retry budgets, identities, and raw-response scores."""
    output = Path(output)
    plan = read_plan(output)
    _check_artifacts(output, plan)
    attempts = load_attempts(output, plan)
    path = output / "execution.json"
    execution = json.loads(path.read_text()) if path.exists() else None
    if execution is None:
        if attempts:
            raise ValueError("Execution metadata missing from a started run")
        return plan, None, attempts
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or (expected_mode is not None and mode != expected_mode)
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol") != plan["protocol_version"]):
        raise ValueError("Execution identity or live/mock mode changed")
    config = plan["config"]
    if len(attempts) > config["max_total_attempts"]:
        raise ValueError("Total attempt cap exceeded")
    task_counts = Counter(a["task_id"] for a in attempts)
    if (sum(count - 1 for count in task_counts.values()) > config["max_extra_attempts"]
            or any(count > 1 + config["max_retries_per_task"] for count in task_counts.values())):
        raise ValueError("Transport retry budget exceeded")
    tasks = {task["id"]: task for task in plan["tasks"]}
    records, seen_ids, observed_model, terminal, previous = {}, set(), None, False, {}
    last_started = None
    for attempt in attempts:
        if terminal:
            raise ValueError("A request followed a terminal identity failure")
        task = tasks[attempt["task_id"]]
        next_task = next((task for task in plan["tasks"] if task["id"] not in records), None)
        if task != next_task:
            raise ValueError("Task order changed or a returned answer was retried")
        prior = previous.get(task["id"])
        if (attempt.get("retry_of_attempt") != (prior["attempt"] if prior else None)
                or (prior is not None and attempt.get("retry_errors") is not True)):
            raise ValueError("Transport retry provenance changed or authorization is missing")
        if (type(attempt.get("retry_errors")) is not bool or attempt.get("mode") != mode
                or attempt["request"] != request_for(plan, task)
                or attempt["meta"] != task_meta(plan, task)):
            raise ValueError("Saved request or metadata differs from the frozen plan")
        try:
            started = datetime.fromisoformat(attempt["started_at"])
            if started.tzinfo is None or (last_started is not None and started < last_started):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise ValueError("Invalid attempt start time") from None
        last_started = started
        if attempt["status"] in ("complete", "invalid"):
            response = provider.normalize(attempt["response"]["raw_response"], observed_model)
            scored, failure = _score(plan, task, response, observed_model, seen_ids, mode)
            if (response != attempt["response"] or attempt.get("hard_failure") != failure
                    or any(attempt.get(key) != value for key, value in scored.items())):
                raise ValueError("Scoring or normalized response differs from the raw journal")
            observed_model = _model_after(observed_model, response)
            if isinstance(response.get("response_id"), str):
                seen_ids.add(response["response_id"])
            records[task["id"]] = attempt
            terminal = failure is not None
        elif "response" in attempt or attempt.get("hard_failure") is not None:
            raise ValueError("Returned content cannot be relabeled a transport error")
        previous[task["id"]] = attempt
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    """SIMULATED fixture: every condition is correct, with no fabricated effect."""
    text = "FINAL: " + task["expected"]
    if task["arm"] == "visible":
        text = "SIMULATED SOFTWARE FIXTURE ONLY.\n" + text
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
                               "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})


def _error_message(exc):
    """Keep bounded transport diagnostics without arbitrary headers or bodies."""
    if type(exc.status_code) is int:
        return "HTTP " + str(exc.status_code)
    value = str(exc)
    return value if re.fullmatch(r"[A-Za-z][A-Za-z0-9_ ]{0,79}", value) else "ProviderError"


def run(config, output, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    from .analysis import write_summary
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require --mock")
    mode = "mock" if mock else "live"
    with run_lock(output):
        output = Path(output)
        _prepare_locked(config, output)
        plan, execution, attempts = read_run(output, mode)
        if execution is not None and not resume:
            raise ValueError("Run has started; use --resume")
        records = accepted_records(attempts)
        if any(a.get("hard_failure") for a in attempts):
            raise ValueError("A terminal identity failure is retained; do not retry it")
        if execution is None:
            execution = {"mode": mode, "protocol": plan["protocol_version"],
                         "plan_hash": plan["plan_hash"], "created_at": now()}
            write_json(output / "execution.json", execution)
        observed_model = next((a["response"]["model"] for a in attempts
                               if "response" in a and isinstance(a["response"].get("model"), str)
                               and a["response"]["model"].strip()), None)
        seen_ids = {a["response"]["response_id"] for a in attempts
                    if "response" in a and isinstance(a["response"].get("response_id"), str)}
        task_counts = Counter(a["task_id"] for a in attempts)
        extra_attempts = sum(count - 1 for count in task_counts.values())
        calls, stop, error_message = 0, "complete", None
        last_start = datetime.fromisoformat(attempts[-1]["started_at"]).timestamp() if attempts else 0
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "total_attempt_limit"
                    break
                prior = next((a for a in reversed(attempts) if a["task_id"] == task["id"]), None)
                if prior is not None:
                    if not retry_errors:
                        stop = "retry_requires_flag"
                        break
                    if task_counts[task["id"]] >= 1 + config["max_retries_per_task"]:
                        stop = "task_retry_limit"
                        break
                    if extra_attempts >= config["max_extra_attempts"]:
                        stop = "extra_attempt_limit"
                        break
                if not mock:
                    provider.credential(config)
                    interval = config["min_request_interval_seconds"]
                    time.sleep(max(0, min(interval, last_start + interval - time.time())))
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(), "retry_errors": bool(retry_errors),
                          "retry_of_attempt": prior["attempt"] if prior else None,
                          "request": request_for(plan, task), "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                task_counts[task["id"]] += 1
                extra_attempts += int(prior is not None)
                calls += 1
                last_start = time.time()
                try:
                    response = (complete_fn(config, record["request"]) if complete_fn else
                                mock_complete(plan, task) if mock else provider.complete(config, record["request"]))
                except provider.ProviderError as exc:
                    error_message = _error_message(exc)
                    record.update(status="error", finished_at=now(), error=error_message,
                                  http_status=exc.status_code if type(exc.status_code) is int else None)
                    write_json(path, record)
                    stop = "provider_error"
                    break
                response = provider.normalize(response["raw_response"], observed_model)
                scored, failure = _score(plan, task, response, observed_model, seen_ids, mode)
                record.update(response=response, finished_at=now(), hard_failure=failure, **scored)
                write_json(path, record)
                records[task["id"]] = record
                observed_model = _model_after(observed_model, response)
                if isinstance(response.get("response_id"), str):
                    seen_ids.add(response["response_id"])
                print(f"{task['id']}: {record['status']}", flush=True)
                if failure is not None:
                    stop = "operational_failure"
                    break
            else:
                stop = "complete"
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        result = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": len(attempts),
                  "returned_answers": len(records), "valid_answers": sum(a["status"] == "complete" for a in records.values()),
                  "invalid_answers_retained": sum(a["status"] == "invalid" for a in records.values()),
                  "planned_calls": len(plan["tasks"]), "max_total_attempts": config["max_total_attempts"],
                  "extra_attempts_used": extra_attempts, "max_extra_attempts": config["max_extra_attempts"],
                  "max_retries_per_task": config["max_retries_per_task"], "is_simulated": mock,
                  "analysis_status": summary["analysis_status"]}
        for key in ("screen", "observed_model", "observed_model_counts", "observed_models"):
            if key in summary:
                result[key] = summary[key]
        if error_message:
            result["error"] = error_message
        return result
