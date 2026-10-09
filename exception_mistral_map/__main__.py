"""Prepare offline, check sampling, then explicitly start continuation mapping."""

import argparse
import json
from pathlib import Path
import sys

from exception_pilot.storage import run_lock
from .analysis import write_summary
from .core import load_config
from .runner import prepare, provider, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-calls", type=int, required=True)
    p.add_argument("--stage", choices=("check", "map"), default="check")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--retry-errors", action="store_true")
    p.add_argument("--mock", action="store_true")
    p = sub.add_parser("analyze")
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            with run_lock(args.output):
                plan = prepare(load_config(args.config), args.output, args.source)
            result = {"protocol": plan["protocol_version"], "api_calls": 0, "model": plan["config"]["model"],
                      "source_replay_gate_preserved": plan["source_replay_gate"]["status"],
                      "worlds": 12, "parent_cases": 24,
                      "checkpoints": sum(len(c["checkpoints"]) for c in plan["cases"]),
                      "draws_per_checkpoint": plan["config"]["repeats"], "check_calls": 49,
                      "planned_calls": len(plan["tasks"]), "max_total_attempts": plan["config"]["max_total_attempts"]}
        elif args.command == "analyze":
            with run_lock(args.output):
                summary = write_summary(args.output)
            result = {k: summary[k] for k in ("analysis_status", "is_simulated", "attempts_total", "planned_calls", "sampling_gate", "mapping")}
        else:
            result = run(load_config(args.config), args.output, args.max_calls,
                         args.stage, args.resume, args.retry_errors, args.mock)
        print(json.dumps(result, indent=2))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit", "sampling_check_passed"))
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
