"""Fresh-world all-row confirmation: only live run contacts a model API."""

import argparse
import json
from pathlib import Path
import sys

from exception_pilot.storage import run_lock
from .analysis import write_summary
from .core import load_config
from .provider import ProviderError
from .runner import prepare, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True)
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true",
                               help="With resume, retry known transport errors only")
            child.add_argument("--mock", action="store_true", help="Offline SIMULATED fixture")
    child = sub.add_parser("analyze")
    child.add_argument("--output", type=Path, required=True)
    for name in ("trace-export", "trace-summarize"):
        child = sub.add_parser(name, help="Offline manual evidence review; no model calls")
        child.add_argument("--output", type=Path, required=True)
        child.add_argument("--review-file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            config = load_config(args.config)
            with run_lock(args.output):
                plan = prepare(config, args.output)
            result = {"protocol": plan["protocol_version"], "plan_hash": plan["plan_hash"],
                      "model": config["model"], "independent_worlds": len(plan["worlds"]),
                      "planned_calls": len(plan["tasks"]),
                      "max_total_attempts": config["max_total_attempts"], "api_calls": 0}
        elif args.command == "analyze":
            with run_lock(args.output):
                summary = write_summary(args.output)
            result = {key: summary[key] for key in
                      ("evidence_label", "returned_answers", "valid_answers", "invalid_answers", "decision")}
            result["summary"] = str(args.output / "summary.md")
        elif args.command in ("trace-export", "trace-summarize"):
            from .traces import export_trace_review, summarize_trace_review
            function = export_trace_review if args.command == "trace-export" else summarize_trace_review
            result = function(args.output, args.review_file)
        else:
            result = run(load_config(args.config), args.output, args.max_calls,
                         args.resume, args.retry_errors, args.mock)
        print(json.dumps(result, indent=2))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit"))
    except (ValueError, OSError, ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
