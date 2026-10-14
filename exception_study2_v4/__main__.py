"""Explicit v4 stages. Default/help/preparation/reporting never execute inference."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command')
    p=sub.add_parser('configure');p.add_argument('--model-dir',required=True);p.add_argument('--config',required=True)
    p=sub.add_parser('prepare');p.add_argument('--output',required=True);p.add_argument('--config',required=True)
    p.add_argument('--phase',choices=['selection','confirmation'],default='selection');p.add_argument('--selection-output');p.add_argument('--policy-lock')
    for name in ('validate','collect','measure-fixed'):
        p=sub.add_parser(name);p.add_argument('--output',required=True)
        g=p.add_mutually_exclusive_group(required=True);g.add_argument('--mock',action='store_true');g.add_argument('--live-qwen',action='store_true')
        if name=='collect':p.add_argument('--limit-originals',type=int,default=8);p.add_argument('--complete',action='store_true')
    for name in ('selection-report','timing-report'):
        p=sub.add_parser(name);p.add_argument('--output',required=True)
        if name=='timing-report':p.add_argument('--event-output',action='append')
    args=parser.parse_args(argv)
    if args.command is None:parser.print_help();return
    if args.command=='configure':
        from .core import configure
        r=configure(args.model_dir,args.config)
    elif args.command=='prepare':
        from .core import prepare
        r=prepare(args.output,args.phase,json.loads(Path(args.config).read_text()),args.selection_output,args.policy_lock)
    elif args.command in ('validate','collect'):
        from .runner import run
        r=run(args.output,technical_only=args.command=='validate',limit_originals=getattr(args,'limit_originals',8),complete=getattr(args,'complete',False),live_qwen=args.live_qwen,mock=args.mock)
    elif args.command=='measure-fixed':
        from .readouts import measure_fixed
        r=measure_fixed(args.output,args.live_qwen,args.mock)
    elif args.command=='selection-report':
        from .reporting import selection_report
        r=selection_report(args.output)
    else:
        from .reporting import timing_report
        r=timing_report(args.output,args.event_output)
    print(json.dumps(r,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
