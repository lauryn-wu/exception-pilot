"""Command-line interface. Only `run` without --mock can contact OpenAI."""

import argparse
import json
from pathlib import Path
import sys

from .analysis import write_summary
from .core import load_config
from .provider import ProviderError
from .runner import prepare, run
from .storage import run_lock


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True,
                               help="Maximum new request attempts in this invocation (including errors)")
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true",
                               help="Retry failed/uncertain transport attempts, never returned invalid answers")
            child.add_argument("--mock", action="store_true", help="Simulated software fixture; no API calls")
            child.add_argument("--stage1-run", type=Path)
    child = sub.add_parser("analyze")
    child.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            with run_lock(args.output):
                plan = prepare(load_config(args.config), args.output)
                result = {"stage": plan["config"]["stage"], "model": plan["config"]["model"],
                          "independent_lists_or_pairs": len(plan["worlds"]),
                          "planned_calls": len(plan["tasks"]), "plan_hash": plan["plan_hash"],
                          "output": str(args.output), "api_calls": 0}
        elif args.command == "analyze":
            with run_lock(args.output):
                result = write_summary(args.output)
        else:
            result = run(load_config(args.config), args.output, args.max_calls, args.resume,
                         args.retry_errors, args.mock, args.stage1_run)
        print(json.dumps(result, indent=2))
        if args.command == "run" and result["stopped"] not in ("complete", "call_limit"):
            return 1
        return 0
    except (ValueError, OSError, ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
