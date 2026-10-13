"""Plan and inspect offline; opt in explicitly to a bounded live run."""

import argparse
import json
from pathlib import Path
import sys

from exception_pilot.provider import ProviderError
from exception_pilot.storage import run_lock
from .analysis import write_summary
from .core import load_config, read_plan
from .runner import prepare, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preview", "run", "analyze"):
        child = sub.add_parser(name)
        child.add_argument("--output", type=Path, required=True)
        if name in ("plan", "run"):
            child.add_argument("--config", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True, help="Bound all attempts, including transport errors")
            mode = child.add_mutually_exclusive_group(required=True)
            mode.add_argument("--live", action="store_true", help="Explicitly authorize paid API requests")
            mode.add_argument("--mock", action="store_true", help="Offline simulated software test")
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true", help="Retry transport errors only; requires --resume")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            with run_lock(args.output):
                plan = prepare(load_config(args.config), args.output)
                write_summary(args.output)
            result = {"experiment_id": plan["experiment_id"], "planned_responses": len(plan["tasks"]),
                      "plan_hash": plan["plan_hash"], "api_calls": 0}
        elif args.command == "preview":
            with run_lock(args.output):
                read_plan(args.output)
                print((args.output / "preview.md").read_text(encoding="utf-8"))
            return 0
        elif args.command == "analyze":
            with run_lock(args.output):
                result = write_summary(args.output)
        else:
            result = run(load_config(args.config), args.output, args.max_calls,
                         resume=args.resume, retry_errors=args.retry_errors,
                         mock=args.mock, live=args.live)
        print(json.dumps(result, indent=2))
        return int(args.command == "run" and result["stopped"] not in ("complete", "call_limit"))
    except (ValueError, OSError, ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
