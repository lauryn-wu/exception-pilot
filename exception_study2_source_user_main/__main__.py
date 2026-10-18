"""Offline preparation/inspection/archive; explicit live flag for 332 main queries only."""
import argparse
import json
from . import planning,execution


def main():
    p=argparse.ArgumentParser(description=__doc__);cmd=p.add_subparsers(dest='command',required=True)
    sub=cmd.add_parser('prepare')
    for name in ('pilot','originals','readouts','tokenizer-dir','output'):sub.add_argument('--'+name,required=True)
    for name in ('inspect','run','archive'):
        sub=cmd.add_parser(name);sub.add_argument('--output',required=True)
        if name=='run':sub.add_argument('--live-qwen',action='store_true')
        if name=='archive':sub.add_argument('--archive',required=True)
    a=p.parse_args()
    if a.command=='prepare':
        plan=planning.prepare(a.pilot,a.originals,a.readouts,a.tokenizer_dir,a.output)
        r=dict(plan_hash=plan['artifact_hash'],inventory=plan['inventory'],real_tokenizer_contexts_validated=332,
            planned_input_token_occurrences=plan['planned_input_token_occurrences'],current_legacy_provenance=plan['source']['legacy'],
            model_loads=0,inference_calls=0,next_stage='STOP_REVIEW_FROZEN_MAIN_PLAN')
    elif a.command=='archive':r=execution.archive(a.output,a.archive)
    else:
        value=execution.run(a.output,a.live_qwen) if a.command=='run' else execution.inspect(a.output)
        r={k:value[k] for k in ('protocol','plan_hash','measurement_mode','prior_evidence','inventory','collection_status','counts',
            'executable_now','this_invocation','cumulative_dispatches','cumulative_dispatch_note','cumulative_finished_invocation_calls','cumulative_call_accounting_complete','cumulative_model_loads','cumulative_load_accounting_complete','next_stage')}
    print(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
