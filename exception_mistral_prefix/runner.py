"""Immutable journals and fixed gates for capability, baseline, and unedited replay."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json

from . import provider
from .analysis import write_summary
from .core import (CAPABILITY_EXPECTED_FULL, PrefixUnavailable, capability_gate, make_plan,
                   phenomenon_gate, read_plan, replay_gate, request_for, score_response, task_meta)


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    output = Path(output)
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from the saved plan; do not change an ongoing screen")
        return plan
    if any(path.name != "run.lock" for path in output.iterdir()):
        raise ValueError("Output directory is not empty and has no plan; use a new directory")
    plan = make_plan(config)
    write_json(output / "plan.json", plan)
    preview = []
    for task in plan["tasks"]:
        entry = {"task_id": task["id"], "family": task["family"],
                 "answer_key_not_sent_separately": task_meta(plan, task)}
        if task["family"] == "replay":
            entry.update(request=None, deferred_request={
                "parent_task_id": task["parent_task_id"],
                "rule": "Original visible user message followed by its exact deterministic assistant prefix, prefix=true.",
                "cut_rule": plan["analysis_plan"]["cuts"],
                "model": config["model"], "max_tokens": config["max_tokens"]["replay"],
                "temperature": config["temperature"], "reasoning_effort": config["reasoning_effort"], "stream": False})
        else:
            entry["request"] = request_for(plan, task)
        preview.append(entry)
    write_json(output / "preview.json", preview)
    lines = ["# Mistral prefix feasibility preview — no API calls", "",
             "1 capability check + 48 base requests + 24 conditional unedited replays = at most 73 planned calls. "
             "The cumulative cap is 89 attempts. No edited-prefix arms or stage two are implemented.", "",
             "The requested mistral-small-2603 identifier is versioned; this is not a guarantee of an immutable backend. The first nonempty returned model identity "
             "is latched from the journal; any later model-name change terminates the screen. reasoning_effort is none. "
             "Raw reasoning_content and system_fingerprint are retained, and nonempty reasoning_content is invalid.", "",
             "Capability succeeds only if returned full text is exactly `Cobalt Maple Lantern`, without a leading or "
             "trailing character, including whitespace. The assistant prefix is `Cobalt Ma`. Mistral includes the supplied prefix in its returned completion. Replay requires an exact leading-prefix match; suffix comparisons remove exactly that prefix length once, while scoring uses the full returned text.", "",
             "preview.json contains exact capability and base requests and all 24 frozen replay recipes. Replay "
             "payloads cannot be known until their saved visible parents exist; each exact request and parent "
             "hash/cut metadata is journaled before sending. No gold answer is supplied separately.", "",
             "## Capability request", "", "```json", json.dumps(preview[0]["request"], indent=2), "```", "",
             "## First world's four base requests", ""]
    for entry in preview[1:5]:
        meta = entry["answer_key_not_sent_separately"]
        lines += [f"### {entry['task_id']}", "", f"Recorded class: {meta['expected']}; pattern: {meta['pattern_label']}.",
                  "", "```json", json.dumps(entry["request"], indent=2), "```", ""]
    lines += ["## Practical gates", "", "```json", json.dumps(plan["analysis_plan"], indent=2), "```", ""]
    (output / "preview.md").write_text("\n".join(lines), encoding="utf-8")
    return plan


def observed_model_from(records):
    for record in records.values():
        model = record["response"].get("model")
        if isinstance(model, str) and model.strip():
            return model
    return None


def unavailable_prefixes(plan, records):
    return [task["id"] for task in plan["tasks"] if task["family"] == "replay"
            and task_meta(plan, task, records).get("prefix_available") is not True]


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
            or execution.get("protocol_version") != plan["protocol_version"]
            or execution.get("requested_model_id") != plan["config"]["model"]
            or execution.get("endpoint") != plan["config"]["endpoint"]):
        raise ValueError("Run mode or execution identity differs")
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Journal exceeds the fixed cumulative attempt cap")
    tasks = {task["id"]: task for task in plan["tasks"]}
    records, terminal_failure, observed_model = {}, False, None
    for record in attempts:
        if terminal_failure:
            raise ValueError("A task was attempted after a returned invalid response; collection must stop")
        task = tasks[record["task_id"]]
        next_task = next((value for value in plan["tasks"] if value["id"] not in records), None)
        if task["id"] in records:
            raise ValueError("A task was retried after a returned response; refusing response selection")
        if next_task is None or task["id"] != next_task["id"]:
            raise ValueError("Attempt order differs from the fixed schedule")
        if task["family"] != "capability" and capability_gate(plan, records)["status"] != "pass":
            raise ValueError("Base or replay request attempted before the exact capability check passed")
        if task["family"] == "replay":
            if phenomenon_gate(plan, records)["status"] != "pass":
                raise ValueError("Replay attempted before the fixed phenomenon gate passed")
            if unavailable_prefixes(plan, records):
                raise ValueError("Replay attempted despite an unavailable prespecified parent prefix")
        if (record.get("mode") != mode or record.get("request") != request_for(plan, task, records)
                or record.get("meta") != task_meta(plan, task, records)):
            raise ValueError("Saved request, deterministic prefix metadata, or mode differs from the plan")
        if record["status"] in ("complete", "invalid"):
            response = record["response"]
            normalized = provider.normalize(response["raw_response"], observed_model)
            scored = score_response(task, normalized, record["meta"])
            if response != normalized or any(record.get(key) != value for key, value in scored.items()):
                raise ValueError("Saved scoring, identity, or response differs from raw provider content")
            if observed_model is None and isinstance(normalized["model"], str) and normalized["model"].strip():
                observed_model = normalized["model"]
            records[task["id"]] = record
            terminal_failure = scored["status"] == "invalid"
        elif "response" in record:
            raise ValueError("A returned response cannot be relabeled as a retryable transport error")
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task, records=None):
    """Capability succeeds, base answers are all correct, so the phenomenon gate stops."""
    if task["family"] == "capability":
        text = CAPABILITY_EXPECTED_FULL
    else:
        meta = task_meta(plan, task, records)
        if task["family"] == "replay":
            text = meta["prefix_text"] + meta["parent_suffix"]
        else:
            text = "ANSWER: " + meta["expected"]
            if task["arm"] == "visible":
                text = "SIMULATED software fixture. The saved answer is copied for this test only.\n" + text
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content": text, "reasoning_content": None},
                     "finish_reason": "stop"}]})


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
        if any(record["status"] == "invalid" for record in records.values()):
            raise ValueError("A returned invalid response stops this screen. Preserve it; do not resample or continue")
        observed_model = observed_model_from(records)
        if execution is None:
            write_json(output / "execution.json", {"mode": mode, "protocol_version": plan["protocol_version"],
                       "plan_hash": plan["plan_hash"], "created_at": now(),
                       "requested_model_id": config["model"], "endpoint": config["endpoint"]})
        calls, stop, error_message = 0, "complete", None
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if task["family"] != "capability" and capability_gate(plan, records)["status"] != "pass":
                    stop = "capability_gate_failed"
                    break
                if task["family"] == "replay":
                    if phenomenon_gate(plan, records)["status"] != "pass":
                        stop = "phenomenon_gate_failed"
                        break
                    # All saved parents are already available: avoid spending any
                    # replay calls if the fixed set contains an ineligible prefix.
                    if unavailable_prefixes(plan, records):
                        stop = "prefix_unavailable"
                        break
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "total_attempt_limit"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                if any(attempt["task_id"] == task["id"] for attempt in attempts) and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                payload, meta = request_for(plan, task, records), task_meta(plan, task, records)
                # Validate credentials before journaling a call, and only when a
                # new live request has passed every practical and budget gate.
                if not mock:
                    provider.credential(config)
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(),
                          "request": payload, "meta": meta}
                path = output / "attempts" / f"{record['attempt']:06d}.json"
                write_json(path, record)
                attempts.append(record)
                calls += 1
                try:
                    response = (complete_fn(config, payload) if complete_fn is not None else
                                mock_complete(plan, task, records) if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                response = provider.normalize(response["raw_response"], observed_model)
                if observed_model is None and isinstance(response["model"], str) and response["model"].strip():
                    observed_model = response["model"]
                record.update(response=response, finished_at=now(), **score_response(task, response, meta))
                write_json(path, record)
                records[task["id"]] = record
                print(f"{task['id']}: {record['status']}", flush=True)
                if record["status"] == "invalid":
                    stop = "capability_gate_failed" if task["family"] == "capability" else "invalid_response"
                    break
            else:
                if replay_gate(plan, records)["status"] != "pass":
                    stop = "replay_gate_failed"
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        outcome = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": len(attempts),
                   "returned_answers": len(records),
                   "valid_answers": sum(record["status"] == "complete" for record in records.values()),
                   "invalid_answers_retained": sum(record["status"] == "invalid" for record in records.values()),
                   "planned_calls": len(plan["tasks"]), "max_total_attempts": config["max_total_attempts"],
                   "is_simulated": mock, "analysis_status": summary["analysis_status"],
                   "observed_model": observed_model, "capability_gate": capability_gate(plan, records),
                   "phenomenon_gate": phenomenon_gate(plan, records), "replay_gate": replay_gate(plan, records)}
        if error_message:
            outcome["error"] = error_message
        return outcome
