"""Independent 480-call fresh-data wording confirmation. Only live `run` contacts OpenAI."""

import argparse
import json
from pathlib import Path
import sys

from exception_pilot.provider import ProviderError
from exception_pilot.storage import run_lock

from .analysis import write_summary
from .core import load_config
from .runner import prepare, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if name == "run":
            child.add_argument("--max-calls", type=int, required=True,
                               help="Cap on new attempts in this invocation, including errors")
            child.add_argument("--resume", action="store_true")
            child.add_argument("--retry-errors", action="store_true",
                               help="Retry only transport errors or unresolved requests")
            child.add_argument("--mock", action="store_true", help="Simulated software test; no API calls")
    child = sub.add_parser("analyze")
    child.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            with run_lock(args.output):
                plan = prepare(load_config(args.config), args.output)
            result = {"protocol": plan["protocol_version"], "model": plan["config"]["model"],
                      "independent_list_pairs": len(plan["worlds"]), "planned_calls": len(plan["tasks"]),
                      "output": str(args.output), "api_calls": 0}
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
