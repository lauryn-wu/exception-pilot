import argparse
import json
import sys
from exception_study_support.runner import main
from . import core, analysis

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "code-review":
        parser = argparse.ArgumentParser(description="Validate provisional manual reasoning codes")
        parser.add_argument("command", choices=["code-review"])
        parser.add_argument("--output", required=True)
        parser.add_argument("--coding", required=True)
        args = parser.parse_args()
        print(json.dumps(analysis.code_review(args.output, args.coding), indent=2))
    else:
        raise SystemExit(main(core, analysis))
