"""Explicitly offline by default; separate plan-bound paid authorization per stage."""
import argparse
import json
from pathlib import Path
from . import workflow


def main():
    p=argparse.ArgumentParser(description='Study 2 residual review. No paid requests by default.')
    cmds=p.add_subparsers(dest='command',required=True)
    q=cmds.add_parser('prepare')
    for name in ('review','salvage','output','config'):q.add_argument('--'+name,required=True)
    for name in ('inspect','smoke','run','export'):
        q=cmds.add_parser(name);q.add_argument('--output',required=True)
        if name in ('smoke','run'):
            q.add_argument('--live',action='store_true');q.add_argument('--authorize-paid-'+('smoke' if name=='smoke' else 'review'),dest='authorization',metavar='PLAN_HASH')
            q.add_argument('--max-calls',type=int);q.add_argument('--wall-seconds',type=float)
    a=p.parse_args()
    if a.command=='prepare':result=workflow.prepare(a.review,a.salvage,a.output,json.loads(Path(a.config).read_text()))
    elif a.command in ('smoke','run'):result=workflow.run(a.output,stage='smoke' if a.command=='smoke' else 'review',live=a.live,
        authorization=a.authorization,max_calls=a.max_calls,wall_seconds=a.wall_seconds)
    else:result=getattr(workflow,a.command)(a.output)
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
