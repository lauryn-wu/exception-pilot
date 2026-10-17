"""Explicit pilot-only commands; default run is offline."""
import argparse
import json
from . import planning,execution


def main():
    parser=argparse.ArgumentParser(description=__doc__);cmd=parser.add_subparsers(dest='command',required=True)
    p=cmd.add_parser('prepare');p.add_argument('--parent',required=True);p.add_argument('--output',required=True)
    p.add_argument('--originals');p.add_argument('--tokenizer-dir')
    for command in ('inspect','run','archive'):
        p=cmd.add_parser(command);p.add_argument('--output',required=True)
        if command=='run':p.add_argument('--live-qwen',action='store_true')
        if command=='archive':p.add_argument('--archive',required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        p=planning.prepare(args.parent,args.output,args.originals,args.tokenizer_dir)
        result=dict(plan_hash=p['artifact_hash'],inventory=p['inventory'],planned_input_token_occurrences=p['planned_input_token_occurrences'],
            parent_v2_calibration_gate='FAILED',real_tokenizer_serialization_validated=True,model_loads=0,inference_calls=0,next_stage='STOP_REVIEW_FROZEN_PILOT')
    elif args.command=='archive':result=execution.archive(args.output,args.archive)
    else:
        r=execution.run(args.output,args.live_qwen) if args.command=='run' else execution.inspect(args.output)
        result={k:r[k] for k in ('protocol','plan_hash','measurement_mode','parent_v2_calibration_gate','new_pilot_criterion','collection_status',
            'counts','source_present','literal_missing','main_planned','main_eligible','executable_now','this_invocation','unresolved_operations','next_stage')}
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
