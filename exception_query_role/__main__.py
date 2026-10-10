"""Prepare, run, and analyze the fixed 144-call query-role screen."""

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
    p = sub.add_parser("prepare", help="Freeze fresh cases and exact prompts; zero API calls")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-calls", type=int, required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--retry-errors", action="store_true")
    p.add_argument("--mock", action="store_true", help="SIMULATED software check; never scientific data")
    p = sub.add_parser("analyze")
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            plan = prepare(load_config(args.config), args.output)
            result = {"protocol": plan["protocol_version"], "model_id": plan["config"]["model"],
                      "planned_calls": len(plan["tasks"]), "max_total_attempts": plan["config"]["max_total_attempts"],
                      "max_retries_per_task": plan["config"]["max_retries_per_task"],
                      "max_extra_attempts": plan["config"]["max_extra_attempts"],
                      "plan_hash": plan["plan_hash"], "api_calls": 0,
                      "next": "Inspect preview.md, then run with an explicit --max-calls budget"}
        elif args.command == "analyze":
            with run_lock(args.output):
                summary = write_summary(args.output)
            result = {key: summary[key] for key in (
                "analysis_status", "is_simulated", "attempts_total", "returned_answers", "valid_answers",
                "invalid_answers_retained", "planned_calls", "screen", "observed_model", "observed_model_counts", "observed_models") if key in summary}
            result["full_summary"] = str((args.output / "summary.json").resolve())
            result["report"] = str((args.output / "report.md").resolve())
        else:
            result = run(load_config(args.config), args.output, args.max_calls,
                         args.resume, args.retry_errors, args.mock)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit"))
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
