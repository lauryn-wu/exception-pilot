"""Prepare and run the fresh record-status framing experiment in two explicit stages."""

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
    p = sub.add_parser("prepare", help="Freeze fresh worlds and write exact previews; zero API calls")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-calls", type=int, required=True)
    p.add_argument("--stage", choices=("baseline", "intervene"), default="baseline")
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
                      "planned_baseline_calls_including_capability": sum(t["family"] in ("capability", "base") for t in plan["tasks"]),
                      "planned_intervention_calls": sum(t["family"] == "intervention" for t in plan["tasks"]),
                      "plan_hash": plan["plan_hash"], "api_calls": 0,
                      "next": "Inspect preview.md, then run --stage baseline"}
        elif args.command == "analyze":
            with run_lock(args.output):
                summary = write_summary(args.output)
            result = {key: summary[key] for key in (
                "analysis_status", "collection_status", "is_simulated", "interpretation_allowed",
                "attempts_total", "returned_answers", "valid_answers", "invalid_answers_retained", "planned_calls",
                "capability_gate", "baseline_completion", "intervention_completion", "arm_counts", "primary_contrast")}
            result["full_summary"] = str((args.output / "summary.json").resolve())
            result["report"] = str((args.output / "report.md").resolve())
        else:
            result = run(load_config(args.config), args.output, args.max_calls,
                         args.stage, args.resume, args.retry_errors, args.mock)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit", "baseline_complete"))
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
