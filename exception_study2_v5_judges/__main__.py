"""CPU-only judge CLI. Network requires both --live-judges and verified live policy."""
import argparse
import json
from pathlib import Path
from .workflow import prepare, run, export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('prepare')
    p.add_argument('--source', required=True); p.add_argument('--output', required=True)
    p.add_argument('--config', default='configs/study2_v5_judges_offline.json')
    p.add_argument('--scope', choices=('pilot', 'remaining', 'all'), default='pilot')
    p = subs.add_parser('run')
    p.add_argument('--output', required=True); p.add_argument('--live-judges', action='store_true')
    p.add_argument('--max-calls', type=int); p.add_argument('--wall-seconds', type=float)
    p.add_argument('--stage', choices=('initial', 'all'), default='all')
    p = subs.add_parser('export'); p.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        value = prepare(args.source, args.output, json.loads(Path(args.config).read_text()), args.scope)
        value = {k:value[k] for k in ('artifact_hash','scope','initial_request_ceiling','total_request_ceiling')}
    elif args.command == 'run':
        value = run(args.output, live=args.live_judges, max_calls=args.max_calls, wall_seconds=args.wall_seconds, stage=args.stage)
    else:
        value = export(args.output)
        value = dict(annotation_hash=value['artifact_hash'], cases=len(value['cases']), disagreements=len(value['disagreements']))
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
