"""Bounded, resumable collection with an explicit stop between check and map."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

from exception_pilot.storage import accepted_records, load_attempts, run_lock, write_json
from exception_mistral_prefix_v2 import provider
from .analysis import write_summary
from .core import (capability_gate, make_plan, read_plan, request_for,
                   sampling_gate, score_response, task_meta, read_previous, imported_attempts)


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(config, output):
    plan = read_plan(output)
    if plan["config"] != config:
        raise ValueError("Config changed")
    return plan


def migrate(config, source_path, output):
    from exception_pilot.core import digest
    source_path, output = Path(source_path).resolve(), Path(output).resolve()
    if source_path == output or source_path in output.parents or output in source_path.parents:
        raise ValueError("Source and output must be separate, non-nested directories")
    if not (source_path / "plan.json").is_file():
        raise ValueError("Source must be the existing mistral-map-001 run")
    with run_lock(source_path), run_lock(output):
        previous = read_previous(source_path)
        plan = make_plan(config, previous)
        if (output / "plan.json").exists():
            existing, _, _ = read_run(output)
            if existing != plan:
                raise ValueError("Output belongs to a different source or amendment")
            return existing
        if any(p.name != "run.lock" for p in output.iterdir()):
            raise ValueError("Output is not empty; preserve it and use a new directory")
        snapshot = output / "source-map-v1"
        for name in previous["file_sha256"]:
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path / name, destination)
        if digest(read_previous(snapshot)) != digest(previous):
            raise ValueError("Source changed while copying; preserve output for inspection")
        for entry in imported_attempts(plan, previous):
            write_json(output / "attempts" / f"{entry['attempt']:06d}.json", entry)
        write_json(output / "execution.json", {"mode": previous["execution"]["mode"],
                    "protocol": plan["protocol_version"], "plan_hash": plan["plan_hash"], "created_at": now(),
                    "migration": {"previous_plan_hash": previous["plan"]["plan_hash"],
                                  "imported_attempts": len(previous["attempts"]),
                                  "previous_snapshot_digest": plan["previous_snapshot_digest"]}})
        write_json(output / "plan.json", plan)
        write_json(output / "preview.json", [{"task_id": task["id"], "meta_not_sent": task_meta(plan, task),
                                              "request": request_for(plan, task)} for task in plan["tasks"]])
        lines = ["# Continuation mapping V2 — whitespace scoring amendment", "",
                 plan["interpretation"], "", "Migration made zero API calls. All requests, checkpoints, thresholds and sampling settings equal V1.",
                 "Every original journal is retained in source-map-v1. Both strict and amended scores are reported.",
                 "preview.json contains every exact request. Each assistant prefix is cumulative through the indicated cut.", ""]
        for case in plan["cases"]:
            lines += [f"## {case['id']}", "", "### Original user prompt", "", "```text", case["messages"][0]["content"], "```", ""]
            for point in case["checkpoints"]:
                lines += [f"### {point['id']} — cut {point['cut_chars']}: {', '.join(point['labels'])}", "",
                          "Exact added block:", "```text", point["retained_block_since_previous"], "```", "",
                          "Next original line (not supplied): `" + point["parent_next_line"].replace("`", "'") + "`", ""]
        (output / "preview.md").write_text("\n".join(lines) + "\n")
        write_summary(output)
        return plan


def _hard_failure(task, response, scored, seen_ids, mode):
    if task["family"] == "capability" and scored["status"] == "invalid":
        return "capability_failed"
    if not response["complete"]:
        return response["provider_invalid_reason"] or "provider_incomplete"
    if mode == "live" and response["model"] != "mistral-small-2603":
        return "unexpected_model"
    if task["family"] == "map" and scored["prefix_exact"] is not True:
        return "prefix_mismatch"
    response_id = response.get("response_id")
    if not isinstance(response_id, str) or not response_id.strip():
        return "missing_response_id"
    if response_id in seen_ids:
        return "duplicate_response_id"
    return None


def read_run(output, expected_mode=None):
    output = Path(output)
    plan = read_plan(output)
    attempts = load_attempts(output, plan)
    path = output / "execution.json"
    execution = json.loads(path.read_text()) if path.exists() else None
    if execution is None:
        raise ValueError("V2 migration execution metadata is missing")
    mode = execution.get("mode")
    if (mode not in ("live", "mock") or (expected_mode and mode != expected_mode)
            or execution.get("plan_hash") != plan["plan_hash"]
            or execution.get("protocol") != plan["protocol_version"]
            or (mode == "live" and plan["source_mode"] != "live")):
        raise ValueError("Execution identity or live/mock source differs")
    previous = read_previous(output / "source-map-v1")
    imported = imported_attempts(plan, previous)
    expected_migration = {"previous_plan_hash": previous["plan"]["plan_hash"],
                          "imported_attempts": len(imported),
                          "previous_snapshot_digest": plan["previous_snapshot_digest"]}
    if execution.get("migration") != expected_migration or attempts[:len(imported)] != imported:
        raise ValueError("Imported responses or their migration provenance changed")
    if any("imported_from_v1" in a for a in attempts[len(imported):]):
        raise ValueError("New attempts cannot be marked as imported")
    if len(attempts) > plan["config"]["max_total_attempts"]:
        raise ValueError("Attempt cap exceeded")
    tasks = {t["id"]: t for t in plan["tasks"]}
    records, seen_ids, model, terminal = {}, set(), None, False
    for attempt in attempts:
        if terminal:
            raise ValueError("A request followed a terminal failure")
        task = tasks[attempt["task_id"]]
        next_task = next((t for t in plan["tasks"] if t["id"] not in records), None)
        if task != next_task:
            raise ValueError("Attempt order changed or a returned answer was retried")
        if task["family"] != "capability" and capability_gate(plan, records)["status"] != "pass":
            raise ValueError("Request before capability pass")
        if task["family"] == "map" and sampling_gate(plan, records)["status"] != "pass":
            raise ValueError("Mapping before sampling check passed")
        if (attempt.get("mode") != mode or attempt["request"] != request_for(plan, task)
                or attempt["meta"] != task_meta(plan, task)):
            raise ValueError("Saved request or metadata differs from frozen plan")
        if attempt["status"] in ("complete", "invalid"):
            response = provider.normalize(attempt["response"]["raw_response"], model)
            scored = score_response(task, response, attempt["meta"])
            failure = _hard_failure(task, response, scored, seen_ids, mode)
            if failure:
                scored.update(status="invalid", format_valid=False, invalid_reason=failure, answer=None)
            if response != attempt["response"] or attempt.get("hard_failure") != failure or any(attempt.get(k) != v for k, v in scored.items()):
                raise ValueError("Scoring or response differs from raw journal")
            model = model or response["model"]
            seen_ids.add(response.get("response_id"))
            records[task["id"]] = attempt
            terminal = bool(failure) or (task["family"] == "base" and sampling_gate(plan, records)["status"] == "fail")
        elif "response" in attempt:
            raise ValueError("Returned content cannot be relabeled a transport error")
    accepted_records(attempts)
    return plan, execution, attempts


def mock_complete(plan, task):
    """Deliberate synthetic fixture: base reasoning always chooses the pattern."""
    meta = task_meta(plan, task)
    if task["family"] == "capability":
        text = "Cobalt Maple Lantern"
    else:
        answer = meta["expected"] if task["arm"] == "direct" else meta["pattern_label"]
        text = "ANSWER: " + answer
        if task["arm"] != "direct":
            text = meta.get("prefix_text", "") + "SIMULATED software fixture only.\n" + text
    return provider.normalize({"id": "mock-" + task["id"], "model": "MOCK-NOT-A-MODEL", "usage": {},
                               "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})


def run(config, output, max_calls, stage="check", resume=False, retry_errors=False, mock=False, complete_fn=None):
    if type(max_calls) is not int or max_calls <= 0 or stage not in ("check", "map"):
        raise ValueError("Positive --max-calls and --stage check|map required")
    if complete_fn is not None and not mock:
        raise ValueError("Injected responses require --mock")
    mode = "mock" if mock else "live"
    with run_lock(output):
        output = Path(output)
        prepare(config, output)
        plan, execution, attempts = read_run(output, mode)
        if mode == "live" and plan["source_mode"] != "live":
            raise ValueError("A simulated source cannot be live research")
        if execution is not None and not resume:
            raise ValueError("Run has started; use --resume")
        records = accepted_records(attempts)
        if any(a.get("hard_failure") for a in attempts):
            raise ValueError("A terminal operational failure is retained; do not retry it")
        if stage == "map" and sampling_gate(plan, records)["status"] != "pass":
            raise ValueError("Complete --stage check first; mapping is not yet enabled")
        model = next((a["response"]["model"] for a in attempts if "response" in a), None)
        seen_ids = {a["response"].get("response_id") for a in attempts if "response" in a}
        calls, stop, error_message = 0, "complete", None
        # Pacing also applies across invocations by reading the last start time.
        last_start = datetime.fromisoformat(attempts[-1]["started_at"]).timestamp() if attempts else 0
        try:
            for task in plan["tasks"]:
                if task["id"] in records:
                    continue
                if sampling_gate(plan, records)["status"] == "fail":
                    stop = "sampling_check_failed"
                    break
                if task["family"] == "map" and stage == "check":
                    stop = "sampling_check_passed"
                    break
                if calls >= max_calls:
                    stop = "call_limit"
                    break
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "total_attempt_limit"
                    break
                if any(a["task_id"] == task["id"] for a in attempts) and not retry_errors:
                    stop = "retry_requires_flag"
                    break
                if not mock:
                    provider.credential(config)
                    time.sleep(max(0, min(config["min_request_interval_seconds"], last_start + config["min_request_interval_seconds"] - time.time())))
                record = {"attempt": len(attempts) + 1, "task_id": task["id"], "plan_hash": plan["plan_hash"],
                          "mode": mode, "status": "started", "started_at": now(),
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
                    record.update(status="error", finished_at=now(), error=str(exc), http_status=exc.status_code)
                    write_json(path, record)
                    stop, error_message = "provider_error", str(exc)
                    break
                response = provider.normalize(response["raw_response"], model)
                scored = score_response(task, response, record["meta"])
                failure = _hard_failure(task, response, scored, seen_ids, mode)
                if failure:
                    scored.update(status="invalid", format_valid=False, invalid_reason=failure, answer=None)
                record.update(response=response, finished_at=now(), hard_failure=failure, **scored)
                write_json(path, record)
                records[task["id"]] = record
                model = model or response["model"]
                seen_ids.add(response.get("response_id"))
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
        outcome = {"stopped": stop, "calls_this_invocation": calls, "attempts_total": len(attempts),
                   "returned_answers": len(records), "valid_answers": sum(a["status"] == "complete" for a in records.values()),
                   "planned_calls": len(plan["tasks"]), "max_total_attempts": config["max_total_attempts"],
                   "is_simulated": mock, "analysis_status": summary["analysis_status"],
                   "sampling_gate": summary["sampling_gate"], "capability_gate": summary["capability_gate"]}
        if error_message:
            outcome["error"] = error_message
        return outcome
