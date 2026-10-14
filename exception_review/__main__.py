"""Default is offline: help/preparation and cache-only inspection never call APIs."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command')
    prep=sub.add_parser('prepare'); prep.add_argument('--source',required=True); prep.add_argument('--output',required=True); prep.add_argument('--policy',required=True); prep.add_argument('--scope',choices=['full','pilot'],default='full'); prep.add_argument('--policy-lock')
    judge=sub.add_parser('judge'); judge.add_argument('--output',required=True); judge.add_argument('--scope',choices=['full','pilot'],default='full'); judge.add_argument('--stage',choices=['initial','adjudicate','freeze-statements','draft','verify','all'],default='all')
    pilot=sub.add_parser('judge-pilot'); pilot.add_argument('--source',required=True); pilot.add_argument('--output',required=True); pilot.add_argument('--policy',required=True)
    ev=sub.add_parser('semantic-eval'); ev.add_argument('--output',required=True); ev.add_argument('--policy',required=True)
    for p in (judge,pilot,ev): p.add_argument('--live',action='store_true'); p.add_argument('--max-calls',type=int,default=None); p.add_argument('--wall-seconds',type=float)
    token=sub.add_parser('tokenize-edits'); token.add_argument('--output',required=True); token.add_argument('--scope',choices=['full','pilot'],default='full'); token.add_argument('--tokenizer-dir'); token.add_argument('--mock',action='store_true')
    for cmd in ('freeze-edits','report'):
        p=sub.add_parser(cmd); p.add_argument('--output',required=True); p.add_argument('--scope',choices=['full','pilot'],default='full')
    lock=sub.add_parser('freeze-policy-lock'); lock.add_argument('--output',required=True)
    events=sub.add_parser('freeze-events'); events.add_argument('--source',required=True); events.add_argument('--output',required=True); events.add_argument('--statements')
    for cmd in ('measure-events','intervene','qwen-collect'):
        p=sub.add_parser(cmd); p.add_argument('--output',required=True); p.add_argument('--live-qwen',action='store_true'); p.add_argument('--mock',action='store_true')
        if cmd=='intervene': p.add_argument('--scope',choices=['full','pilot'],default='full')
        if cmd=='qwen-collect': p.add_argument('--limit-originals',type=int,default=8); p.add_argument('--complete',action='store_true')
    timing=sub.add_parser('qwen-timing-report'); timing.add_argument('--output',required=True)
    model_timing=sub.add_parser('model-timing-report'); model_timing.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if not args.command: parser.print_help(); return
    if args.command in ('prepare','judge-pilot'):
        from .artifacts import prepare
        result=prepare(args.source,args.output,json.loads(Path(args.policy).read_text()),'pilot' if args.command=='judge-pilot' else args.scope,getattr(args,'policy_lock',None))
    if args.command in ('judge','judge-pilot'):
        from .workflow import run
        result=run(args.output,getattr(args,'stage','all'),getattr(args,'scope','pilot'),args.live,max_calls=(42 if args.command=='judge-pilot' and args.max_calls is None else args.max_calls),wall_seconds=args.wall_seconds)
    elif args.command=='semantic-eval':
        from .semantic_eval import evaluate
        result=evaluate(args.output,json.loads(Path(args.policy).read_text()),args.live,max_calls=args.max_calls)
    elif args.command=='tokenize-edits':
        from .integration import check_tokens
        result=check_tokens(args.output,args.scope,args.tokenizer_dir,args.mock)
    elif args.command=='freeze-edits':
        from .integration import freeze_edits
        result=freeze_edits(args.output,args.scope)
    elif args.command=='freeze-policy-lock':
        from .workflow import freeze_policy_lock
        result=freeze_policy_lock(args.output)
    elif args.command=='freeze-events':
        from .integration import freeze_events
        result=freeze_events(args.source,args.output,args.statements)
    elif args.command=='measure-events':
        from .integration import measure_events
        result=measure_events(args.output,args.live_qwen,args.mock)
    elif args.command=='intervene':
        from .integration import intervene
        result=intervene(args.output,args.scope,args.live_qwen,args.mock)
    elif args.command=='report':
        from .reporting import report
        result=report(args.output,args.scope)
    elif args.command=='qwen-collect':
        from .qwen_timing import collect_selection
        result=collect_selection(args.output,args.limit_originals,args.complete,args.live_qwen,args.mock)
    elif args.command=='model-timing-report':
        from .reporting import model_timing_report
        result=model_timing_report(args.output)
    elif args.command=='qwen-timing-report':
        from .reporting import qwen_timing_report
        result=qwen_timing_report(args.output)
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
