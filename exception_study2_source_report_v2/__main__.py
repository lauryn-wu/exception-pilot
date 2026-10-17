"""Use the same explicit run command for first execution and content-bound resume."""
import argparse
import json
from . import planning,execution


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare')
    for name in ('originals','readouts','tokenizer-dir','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--v1-output')
    p=commands.add_parser('archive');p.add_argument('--output',required=True);p.add_argument('--archive',required=True)
    for command in ('inspect','dry-run','analyze','run'):
        p=commands.add_parser(command);p.add_argument('--output',required=True)
        if command=='run':p.add_argument('--live-qwen',action='store_true');p.add_argument('--calibration-only',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare':
        v=planning.prepare(args.originals,args.readouts,args.tokenizer_dir,args.output,args.v1_output)
        result=dict(plan_hash=v['artifact_hash'],inventory=v['inventory'],prior_v1=v['prior_v1'],legacy=v['source']['legacy'],planned_input_token_occurrences=v['planned_input_token_occurrences'],model_loads=0,inference_calls=0,next_stage='STOP_EXPLICIT_LIVE_RUN')
    elif args.command=='archive':result=execution.archive(args.output,args.archive)
    else:
        if args.command in ('inspect','dry-run'):v=execution.inspect(args.output)
        elif args.command=='analyze':v=execution.analyze(args.output)
        else:v=execution.run(args.output,args.live_qwen,args.calibration_only)
        result={k:v[k] for k in ('plan_hash','prior_v1','measurement_mode','calibration_gate','counts','executable_now','main_conditional_on_calibration','this_invocation','backend_requirements','legacy_provenance_mode','next_stage')}
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
