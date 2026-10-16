"""Separate stages; preparation, inspection and default execution are offline."""
import argparse
import json
from . import workflow,readouts,analysis,timing


def main():
    p=argparse.ArgumentParser(description='Post-pilot Study 2A replication amendment. No inference by default.')
    cmds=p.add_subparsers(dest='command',required=True)
    q=cmds.add_parser('prepare');q.add_argument('--source',required=True);q.add_argument('--output',required=True)
    q.add_argument('--preserve',action='append',default=[])
    for name in ('inspect','approve','collect','prepare-readouts','measure','analyze'):
        q=cmds.add_parser(name);q.add_argument('--output',required=True)
        if name=='approve':
            for arg in ('amendment-hash','reviewer','rationale'):q.add_argument('--'+arg,required=True)
            q.add_argument('--acknowledge-pilot-examined',action='store_true');q.add_argument('--approve-remaining',action='store_true')
        if name in ('collect','measure'):
            modes=q.add_mutually_exclusive_group();modes.add_argument('--live-qwen',action='store_true');modes.add_argument('--mock',action='store_true')
        if name=='analyze':q.add_argument('--pilot-readouts')
    q=cmds.add_parser('estimate');q.add_argument('--source',required=True);q.add_argument('--pilot-readouts');q.add_argument('--hourly-rate',type=float)
    a=p.parse_args()
    if a.command=='prepare':value=workflow.prepare(a.source,a.output,a.preserve)
    elif a.command=='inspect':value=workflow.inspect(a.output)
    elif a.command=='approve':value=workflow.approve(a.output,a.amendment_hash,a.reviewer,a.rationale,a.acknowledge_pilot_examined,a.approve_remaining)
    elif a.command=='collect':value=workflow.collect(a.output,live_qwen=a.live_qwen,mock=a.mock)
    elif a.command=='prepare-readouts':value=readouts.prepare(a.output)
    elif a.command=='measure':value=readouts.measure(a.output,live_qwen=a.live_qwen,mock=a.mock)
    elif a.command=='analyze':value=analysis.analyze(a.output,a.pilot_readouts)
    else:value=timing.estimate(a.source,a.pilot_readouts,a.hourly_rate)
    print(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
