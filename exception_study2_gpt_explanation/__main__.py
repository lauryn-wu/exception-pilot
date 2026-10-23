"""Offline by default. Only run --live-openai can dispatch paid requests."""
import argparse
import json
from . import planning, execution
from .export import export


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('prepare'); p.add_argument('--source',required=True); p.add_argument('--output',required=True)
    for command in ('inspect','run','analyze','export','recover'):
        p = sub.add_parser(command); p.add_argument('--output',required=True)
        if command == 'run':
            p.add_argument('--live-openai',action='store_true'); p.add_argument('--max-new',type=int,default=192)
        if command == 'export': p.add_argument('--destination',required=True)
        if command == 'recover': p.add_argument('--reason',required=True)
    a = parser.parse_args(argv)
    if a.command == 'prepare': value = planning.prepare(a.source,a.output)
    elif a.command == 'run': value = execution.run(a.output,a.live_openai,a.max_new)
    elif a.command == 'inspect': value = execution.inspect(a.output)
    elif a.command == 'analyze': value = execution.analyze(a.output)
    elif a.command == 'recover': value = execution.recover(a.output,a.reason)
    else: value = export(a.output,a.destination)
    print(json.dumps({k:v for k,v in value.items() if k not in ('cases','sensitivities')},indent=2,sort_keys=True))
    if a.command == 'run' and a.live_openai and (value['totals']['failed'] or value['totals']['ambiguous']): return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
