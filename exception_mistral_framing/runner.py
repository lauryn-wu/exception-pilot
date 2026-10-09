"""Fresh, bounded collection with a mandatory pause before framing interventions."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from exception_mistral_prefix_v2 import provider
from .core import (capability_gate, make_plan, read_plan, request_for,
                   score_response, task_meta)


def now():
    return datetime.now(timezone.utc).isoformat()


def _preview(plan):
    return [{"task_id": task["id"], "meta_not_sent": task_meta(plan, task),
             "request": request_for(plan, task)} for task in plan["tasks"]]


def _preview_markdown(plan, entries):
    def block(text):
        return "```text\n" + text + ("" if text.endswith("\n") else "\n") + "```"

    lines = ["# Record-status framing intervention — exact request preview", "",
             "This is a fresh run. Preparing this preview makes zero API calls.",
             "The baseline stage stops after the capability probe and every direct/visible baseline response. "
             "An explicit --stage intervene invocation is required afterward. Baseline accuracy never determines eligibility.", "",
             "All 48 target cases appear below. Each has one direct baseline request, one visible-reasoning baseline request, "
             "and four assistant prefixes supplied three times each. Repeats use the same prompt; they are separate requests. "
             "The schedule is frozen and randomized within case blocks. preview.json contains all 673 complete requests in execution order. "
             "Metadata is for analysis only and is not supplied to the model. "
             "An assistant message marked prefix=true is an unfinished explanation; all subsequent text is newly generated.", "",
             "Plan hash: `" + plan["plan_hash"] + "`", ""]
    capability = next(entry for entry in entries if entry["meta_not_sent"]["family"] == "capability")
    settings = {key: value for key, value in entries[1]["request"].items() if key != "messages"}
    lines += ["## Shared request settings", "", "These settings apply to every baseline and intervention request:", "",
              "```json", json.dumps(settings, ensure_ascii=False, indent=2), "```", "",
              "## Prefix capability probe", "", "The probe uses the same settings except max_tokens=32.", "",
              "User message:", "", block(capability["request"]["messages"][0]["content"]), "",
              "Assistant prefix (prefix=true; includes a trailing space after Cobalt):", "",
              block(capability["request"]["messages"][1]["content"]), ""]
    cases = {}
    for entry in entries:
        meta = entry["meta_not_sent"]
        if meta["family"] != "capability":
            cases.setdefault((meta["world_id"], meta["value"]), {}).setdefault(meta["arm"], []).append(entry)
    for (world_id, value), arms in cases.items():
        lines += ["## " + world_id + "/" + value, ""]
        for arm in ("direct", "visible"):
            entry = arms[arm][0]
            lines += ["### " + arm.title() + " baseline — exact user message", "",
                      "Task: `" + entry["task_id"] + "`", "",
                      block(entry["request"]["messages"][0]["content"]), ""]
        lines += ["### Intervention requests", "",
                  "Every arm below uses the exact visible-baseline user message above. "
                  "Append the indicated assistant prefix with prefix=true; regenerate everything afterward. "
                  "There is no additional user instruction and no saved explanation suffix.", ""]
        for arm in ("original", "paraphrase", "recorded", "bare"):
            arm_entries = arms[arm]
            title = arm + (" — observed wording" if arm == "original" else "")
            lines += ["#### " + title, "", "Tasks: " + ", ".join("`" + entry["task_id"] + "`" for entry in arm_entries), "",
                      "Exact assistant prefix (ends with two newline characters):", "",
                      block(arm_entries[0]["request"]["messages"][1]["content"]), ""]
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
        raise ValueError("Readable request preview changed; preserve this run")


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
    """Freeze a fresh plan; an identical existing preparation is read-only."""
    from .analysis import write_summary
    with run_lock(output):
        plan = _prepare_locked(config, output)
        # Also validate any journals when prepare is repeated on a started run.
        read_run(output)
        write_summary(output)
        return plan


def _baseline_complete(plan, records):
    return all(t["id"] in records for t in plan["tasks"] if t["family"] in ("capability", "base"))


def _hard_failure(plan, task, response, scored, seen_ids, mode):
    if not response["complete"]:
        return response["provider_invalid_reason"] or "provider_incomplete"
    if mode == "live" and response["model"] != plan["config"]["model"]:
        return "unexpected_model"
    if task["family"] == "capability" and scored["status"] != "complete":
        return "capability_failed"
    if task["family"] == "intervention" and scored.get("prefix_exact") is not True:
        return "prefix_mismatch"
    response_id = response.get("response_id")
    if not isinstance(response_id, str) or not response_id.strip():
        return "missing_response_id"
    if response_id in seen_ids:
        return "duplicate_response_id"
    return None


def read_run(output, expected_mode=None):
    """Recompute scoring from raw responses and validate the entire request journal."""
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
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Attempt cap exceeded")
    tasks = {t["id"]: t for t in plan["tasks"]}
    records, seen_ids, model, terminal, previous = {}, set(), None, False, {}
    last_started = None
    for attempt in attempts:
        if terminal:
            raise ValueError("A request followed a terminal operational failure")
        task = tasks[attempt["task_id"]]
        next_task = next((t for t in plan["tasks"] if t["id"] not in records), None)
        if task != next_task:
            raise ValueError("Task order changed or a returned answer was retried")
        stage = attempt.get("execution_stage")
        if stage not in ("baseline", "intervene"):
            raise ValueError("Missing or invalid execution stage")
        if task["family"] == "intervention":
            if stage != "intervene" or not _baseline_complete(plan, records):
                raise ValueError("Intervention before an explicit stage transition and complete baseline")
        elif stage != "baseline":
            raise ValueError("Baseline tasks cannot run in the intervention stage")
        if task["family"] != "capability" and capability_gate(plan, records)["status"] != "pass":
            raise ValueError("Request before capability pass")
        prior = previous.get(task["id"])
        if attempt.get("retry_of_attempt") != (prior["attempt"] if prior else None):
            raise ValueError("Retry provenance differs from the attempt journal")
        if prior and attempt.get("retry_errors") is not True:
            raise ValueError("A transport retry lacked explicit retry-errors authorization")
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
            response = provider.normalize(attempt["response"]["raw_response"], model)
            scored = score_response(task, response, attempt["meta"])
            failure = _hard_failure(plan, task, response, scored, seen_ids, mode)
            if failure:
                scored.update(status="invalid", format_valid=False, invalid_reason=failure, answer=None)
            if (response != attempt["response"] or attempt.get("hard_failure") != failure
                    or any(attempt.get(k) != v for k, v in scored.items())):
                raise ValueError("Scoring or normalized response differs from the raw journal")
            model = model or response["model"]
            if isinstance(response.get("response_id"), str):
                seen_ids.add(response["response_id"])
            records[task["id"]] = attempt
            terminal = bool(failure)
        elif "response" in attempt or attempt.get("hard_failure") is not None:
            raise ValueError("Returned content cannot be relabeled a transport error")
        previous[task["id"]] = attempt
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    """Software-only fixture: every arm is correct; no predicted effect is fabricated."""
    meta = task_meta(plan, task)
    if task["family"] == "capability":
        text = "Cobalt Maple Lantern"
    else:
        text = "ANSWER: " + meta["expected"]
        if task["arm"] != "direct":
            text = meta.get("prefix_text", "") + "SIMULATED software fixture only.\n" + text
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
                               "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})


def _error_message(exc):
    """Persist bounded transport diagnostics, never arbitrary response/header text."""
    if type(exc.status_code) is int:
        return "HTTP " + str(exc.status_code)
    value = str(exc)
    return value if re.fullmatch(r"[A-Za-z][A-Za-z0-9_ ]{0,79}", value) else "ProviderError"


def run(config, output, max_calls, stage="baseline", resume=False, retry_errors=False,
        mock=False, complete_fn=None):
    from .analysis import write_summary
    if type(max_calls) is not int or max_calls <= 0 or stage not in ("baseline", "intervene"):
        raise ValueError("Positive --max-calls and --stage baseline|intervene required")
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
            raise ValueError("A terminal operational failure is retained; do not retry it")
        if stage == "intervene" and (not _baseline_complete(plan, records)
                                      or capability_gate(plan, records)["status"] != "pass"):
            raise ValueError("Finish --stage baseline first; every baseline response must return")
        if execution is None:
            execution = {"mode": mode, "protocol": plan["protocol_version"],
                         "plan_hash": plan["plan_hash"], "created_at": now()}
            write_json(output / "execution.json", execution)
        model = next((a["response"]["model"] for a in attempts if "response" in a), None)
        seen_ids = {a["response"]["response_id"] for a in attempts
                    if "response" in a and isinstance(a["response"].get("response_id"), str)}
        calls, stop, error_message = 0, "complete", None
        last_start = datetime.fromisoformat(attempts[-1]["started_at"]).timestamp() if attempts else 0
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if task["family"] == "intervention" and stage == "baseline":
                    stop = "baseline_complete"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "total_attempt_limit"
                    break
                prior = next((a for a in reversed(attempts) if a["task_id"] == task["id"]), None)
                if prior is not None and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                if not mock:
                    provider.credential(config)
                    interval = config["min_request_interval_seconds"]
                    time.sleep(max(0, min(interval, last_start + interval - time.time())))
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "execution_stage": stage, "status": "started", "started_at": now(),
                          "retry_errors": bool(retry_errors), "retry_of_attempt": prior["attempt"] if prior else None,
                          "request": request_for(plan, task), "meta": task_meta(plan, task)}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                last_start = time.time()
                try:
                    response = (complete_fn(config, record["request"]) if complete_fn else
                                mock_complete(plan, task) if mock else provider.complete(config, record["request"]))
                except provider.ProviderError as exc:
                    error_message = _error_message(exc)
                    record.update(status="error", finished_at=now(), error=error_message, http_status=exc.status_code)
                    write_json(path, record)
                    stop = "provider_error"
                    break
                response = provider.normalize(response["raw_response"], model)
                scored = score_response(task, response, record["meta"])
                failure = _hard_failure(plan, task, response, scored, seen_ids, mode)
                if failure:
                    scored.update(status="invalid", format_valid=False, invalid_reason=failure, answer=None)
                record.update(response=response, finished_at=now(), hard_failure=failure, **scored)
                write_json(path, record)
                records[task["id"]] = record
                model = model or response["model"]
                if isinstance(response.get("response_id"), str):
                    seen_ids.add(response["response_id"])
                print(f"{task['id']}: {record['status']}", flush=True)
                if failure:
                    stop = "operational_failure"
                    break
            else:
                stop = "complete"
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        outcome = {"stopped": stop, "stage": stage, "calls_this_invocation": calls, "attempts_total": len(attempts),
                   "returned_answers": len(records), "valid_answers": sum(a["status"] == "complete" for a in records.values()),
                   "invalid_answers_retained": sum(a["status"] == "invalid" for a in records.values()),
                   "planned_calls": len(plan["tasks"]), "max_total_attempts": config["max_total_attempts"],
                   "is_simulated": mock, "analysis_status": summary["analysis_status"],
                   "capability_gate": summary["capability_gate"]}
        for key in ("collection_status", "baseline_completion", "intervention_completion"):
            if key in summary:
                outcome[key] = summary[key]
        if error_message:
            outcome["error"] = error_message
        return outcome
