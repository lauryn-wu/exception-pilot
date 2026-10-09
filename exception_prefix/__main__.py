"""Prefix capability and unedited replay feasibility. Only live run contacts the API."""

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
            child.add_argument("--max-calls", type=int, required=True, help="Attempt cap for this invocation")
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true", help="Retry only transport errors or unresolved requests")
            child.add_argument("--mock", action="store_true", help="Offline simulated software test, never research evidence")
    child = sub.add_parser("analyze")
    child.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            with run_lock(args.output):
                plan = prepare(load_config(args.config), args.output)
            result = {"protocol": plan["protocol_version"], "model_alias": plan["config"]["model"],
                      "independent_worlds": len(plan["worlds"]), "planned_calls": len(plan["tasks"]),
                      "max_total_attempts": plan["config"]["max_total_attempts"], "api_calls": 0}
        elif args.command == "analyze":
            with run_lock(args.output):
                result = write_summary(args.output)
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
