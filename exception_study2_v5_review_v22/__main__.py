"""CPU-only offline salvage and opt-in bounded prospective review."""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description='Study 2 review v2.2. No paid requests by default.')
    commands=p.add_subparsers(dest='command',required=True)
    q=commands.add_parser('salvage');q.add_argument('--review',required=True);q.add_argument('--output',required=True)
    q=commands.add_parser('prepare');q.add_argument('--source',required=True);q.add_argument('--output',required=True);q.add_argument('--config',required=True);q.add_argument('--scope',choices=['pilot','remaining','all'],default='pilot')
    for name in ('run','inspect','export'):
        q=commands.add_parser(name);q.add_argument('--output',required=True)
        if name=='run':q.add_argument('--live',action='store_true');q.add_argument('--max-calls',type=int);q.add_argument('--wall-seconds',type=float)
    a=p.parse_args()
    if a.command=='salvage':
        from .salvage import analyze
        result=analyze(a.review,a.output)
    else:
        from . import workflow
        if a.command=='prepare':result=workflow.prepare(a.source,a.output,json.loads(Path(a.config).read_text()),a.scope)
        elif a.command=='run':result=workflow.run(a.output,live=a.live,max_calls=a.max_calls,wall_seconds=a.wall_seconds)
        else:result=getattr(workflow,a.command)(a.output)
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
