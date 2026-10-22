"""All commands are offline unless --live-qwen is explicitly supplied to smoke/run."""
import argparse
import json
from . import planning, execution
from .export import export


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('design');d.add_argument('--output',required=True)
    for name in ('prepare-smoke','prepare'):
        a=sub.add_parser(name);a.add_argument('--output',required=True);a.add_argument('--tokenizer-dir',required=True);a.add_argument('--model-dir',required=True)
        if name=='prepare':a.add_argument('--design',required=True);a.add_argument('--smoke',required=True)
    for name in ('smoke','run','inspect','analyze','recover','export'):
        a=sub.add_parser(name);a.add_argument('--output',required=True)
        if name in ('smoke','run'):a.add_argument('--live-qwen',action='store_true');a.add_argument('--max-new',type=int,default=8)
        if name=='recover':a.add_argument('--reason',required=True)
        if name=='export':a.add_argument('--destination',required=True)
    a=p.parse_args(argv)
    if a.command=='design':value=planning.design(a.output)
    elif a.command in ('prepare','prepare-smoke'):
        value=planning.prepare(a.output,a.tokenizer_dir,a.model_dir,getattr(a,'design',None),getattr(a,'smoke',None),a.command=='prepare-smoke')
    elif a.command in ('smoke','run'):
        c=planning.Context(a.output)
        if c.plan['kind']!=('smoke' if a.command=='smoke' else 'screen'):p.error('Command does not match frozen plan kind')
        if a.command=='smoke' and not 1<=a.max_new<=8:p.error('Smoke --max-new must be 1..8; total immutable plan has at most eight requests')
        value=execution.run(a.output,a.live_qwen,a.max_new)
    elif a.command=='inspect':value=execution.inspect(a.output)
    elif a.command=='analyze':value=execution.analyze(a.output)
    elif a.command=='recover':value=execution.recover(a.output,a.reason)
    else:value=export(a.output,a.destination)
    if 'cases' in value:value={k:v for k,v in value.items() if k not in ('cases','factorial_cells')}
    print(json.dumps(value,indent=2,sort_keys=True))
    if a.command=='smoke' and a.live_qwen and not value['technical_passed']:return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
