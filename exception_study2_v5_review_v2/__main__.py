"""Explicit offline preparation/evaluation and bounded opt-in live execution."""
import argparse
import json
from pathlib import Path
from .workflow import prepare, run, inspect, export
from .controlled import evaluate

def main():
    p=argparse.ArgumentParser(description='Study 2 v5 Review v2; CPU only, no network by default.')
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--source',required=True);q.add_argument('--output',required=True)
    q.add_argument('--config',required=True);q.add_argument('--scope',choices=['pilot','remaining','all'],default='pilot')
    for name in ('run','smoke','inspect','export'):
        q=sub.add_parser(name);q.add_argument('--output',required=True)
        if name in ('run','smoke'):
            q.add_argument('--live',action='store_true');q.add_argument('--max-calls',type=int);q.add_argument('--wall-seconds',type=float)
        if name=='smoke':q.add_argument('--case-id',help='Exact visible task ID; selection is frozen for this output directory')
    q=sub.add_parser('evaluate');q.add_argument('--output',required=True)
    q.add_argument('--suite',choices=['historical','balanced-audit1'],default='historical')
    a=p.parse_args()
    if a.command=='prepare':result=prepare(a.source,a.output,json.loads(Path(a.config).read_text()),a.scope)
    elif a.command in ('run','smoke'):result=run(a.output,live=a.live,max_calls=a.max_calls,wall_seconds=a.wall_seconds,stage='smoke' if a.command=='smoke' else 'all',case_id=getattr(a,'case_id',None))
    elif a.command=='inspect':result=inspect(a.output)
    elif a.command=='export':result=export(a.output)
    else:
        if a.suite=='balanced-audit1':
            from .controlled_balanced import evaluate as evaluate_balanced
            result=evaluate_balanced()
        else:result=evaluate()
        # Never overwrite an earlier suite's evidence with changed labels/results.
        from exception_review.artifacts import freeze
        result=freeze(Path(a.output),result)
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
