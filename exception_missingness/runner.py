"""Two explicitly invoked phases, with a fixed gate before any edited replay."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from exception_pilot import provider
from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from exception_explanation.runner import normalized_response
from .analysis import replay_gate, write_summary
from .core import (ARMS, edited_prefix, load_sources, make_plan, read_plan, request_for,
                   score_response, task_meta)


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, parent, output):
    output = Path(output)
    if output.resolve() == Path(parent).resolve():
        raise ValueError("Use a new output directory; the parent run is read-only")
    if (output / "plan.json").exists():
        plan = read_plan(output)
        if plan["config"] != config:
            raise ValueError("Config differs from the saved plan")
    else:
        output.mkdir(parents=True, exist_ok=True)
        if any(p.name != "run.lock" for p in output.iterdir()):
            raise ValueError("Output directory is not empty and has no plan")
        plan = make_plan(config, load_sources(parent))
        write_json(output / "plan.json", plan)
    preview = [{"task_id": t["id"], "answer_key_not_sent_separately": task_meta(plan, t),
                "request": request_for(plan, t)} for t in plan["tasks"]]
    write_json(output / "preview.json", preview)
    lines = ["# False-missingness replay preview — no API calls", "",
             "10 selected traces, 9 worlds, 40 planned calls: first 10 unchanged replays, then "
             "30 edits only if all 10 replays are scorable and at least 8 match the original final label.", "",
             "Every request preserves the original user message. Only the assistant-history prefix "
             "changes; it ends at the first target-specific MISSING line. This is a new conversation "
             "turn, not an exact continuation of the original generation. Full requests are in preview.json.", ""]
    for case in plan["cases"]:
        lines += [f"## {case['id']} (parent attempt {case['source_attempt']})", "",
                  f"Recorded class: {case['expected']}; original final answer: {case['original_answer']}; "
                  f"pattern label: {case['pattern_label']}. Metadata headings are not sent to the model.", "",
                  "### Original user message (unchanged in every arm)", "", "```text",
                  case["original_messages"][0]["content"], "```", "",
                  "### Original assistant prefix", "", "```text", case["prefix"], "```", "",
                  "### Last prefix line in each arm", ""]
        for arm in ARMS:
            line = edited_prefix(case, arm).splitlines()[-1]
            lines += [f"**{arm}**", "", "```text", line, "```", ""]
    lines += ["## Identical continuation request", "", "```text",
              preview[0]["request"]["messages"][-1]["content"], "```", ""]
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
    returned, previous = set(), []
    for record in attempts:
        task = tasks[record["task_id"]]
        phase = "replay" if task["arm"] == "original" else "interventions"
        if (record.get("mode") != mode or record.get("phase") != phase
                or record.get("request") != request_for(plan, task)
                or record.get("meta") != task_meta(plan, task)):
            raise ValueError("Saved request, metadata, phase, or mode differs from the frozen plan")
        if phase == "interventions" and replay_gate(plan, previous)["status"] != "pass":
            raise ValueError("Intervention was attempted before the replay feasibility gate passed")
        if task["id"] in returned:
            raise ValueError("A task was retried after a returned answer; refusing response selection")
        if record["status"] in ("complete", "invalid"):
            response = record["response"]
            normalized = normalized_response(response["raw_response"], plan["config"], mode)
            scored = score_response(task, normalized)
            if response != normalized or any(record.get(k) != v for k, v in scored.items()):
                raise ValueError("Saved scoring or response differs from raw provider content")
            returned.add(task["id"])
        elif "response" in record:
            raise ValueError("A returned response cannot be relabeled as a retryable transport error")
        previous.append(record)
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    """A zero-effect fixture: all arms repeat the original answer, with explicit mock metadata."""
    answer = task_meta(plan, task)["original_answer"]
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
        "choices": [{"message": {"role": "assistant", "content":
                     "SIMULATED software fixture, not research evidence.\nANSWER: " + answer},
                     "finish_reason": "stop"}]})


def run(output, phase, max_calls, resume=False, retry_errors=False, mock=False, complete_fn=None):
    if phase not in ("replay", "interventions"):
        raise ValueError("Phase must be replay or interventions")
    if type(max_calls) is not int or max_calls <= 0:
        raise ValueError("--max-calls must be a positive integer and counts all attempted requests")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require mock=True and cannot be labeled real evidence")
    mode = "mock" if mock else "live"
    with run_lock(output) as output:
        plan, execution, attempts = read_run(output, mode)
        config = plan["config"]
        if execution is not None and not resume:
            raise ValueError("This run already started. Add --resume to continue it")
        records = accepted_records(attempts)
        if any(not r["response"]["complete"] for r in records.values()):
            raise ValueError("A returned response is truncated, refused, or technically invalid. "
                             "Preserve it; it cannot be resampled")
        gate = replay_gate(plan, attempts)
        if phase == "interventions" and gate["status"] != "pass":
            write_summary(output)
            return {"stopped": "replay_gate_not_passed", "calls_this_invocation": 0,
                    "replay_gate": gate, "is_simulated": mock}
        tasks = [t for t in plan["tasks"] if (t["arm"] == "original") == (phase == "replay")]
        pending = [t for t in tasks if t["id"] not in records]
        if not mock and pending and len(attempts) < config["max_total_attempts"]:
            provider.credential(config)
        if execution is None:
            write_json(output / "execution.json", {"mode": mode, "protocol_version": plan["protocol_version"],
                       "plan_hash": plan["plan_hash"], "created_at": now()})
        calls, stop, error_message = 0, "phase_complete", None
        try:
            for task in pending:
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
                          "mode": mode, "phase": phase, "status": "started", "started_at": now(),
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
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            summary = write_summary(output)
        if stop == "phase_complete":
            if phase == "replay" and summary["replay_gate"]["status"] == "stop":
                stop = "replay_gate_failed"
            elif phase == "interventions":
                stop = "complete"
        outcome = {"stopped": stop, "phase": phase, "calls_this_invocation": calls,
                   "attempts_total": summary["attempts"], "returned_answers": summary["returned_answers"],
                   "valid_answers": summary["valid_answers"], "invalid_answers_retained": summary["invalid_answers"],
                   "planned_calls": summary["planned_calls"], "max_total_attempts": config["max_total_attempts"],
                   "is_simulated": mock, "replay_gate": summary["replay_gate"],
                   "analysis_status": summary["analysis_status"]}
        if error_message:
            outcome["error"] = error_message
        return outcome
