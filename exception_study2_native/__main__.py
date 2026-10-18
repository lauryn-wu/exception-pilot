"""Offline audit/design/prepare/inspect/analyze; explicit bounded live run and retry."""
import argparse
import json
from . import audit, planning, execution


def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    a=subs.add_parser('audit');a.add_argument('--v5-plan',required=True);a.add_argument('--output',required=True)
    a=subs.add_parser('design');a.add_argument('--kind',choices=('controlled-draft','historical-v5'),default='controlled-draft');a.add_argument('--v5-plan');a.add_argument('--output',required=True)
    a=subs.add_parser('audit-shortcuts');a.add_argument('--design-dir',required=True);a.add_argument('--output',required=True)
    a=subs.add_parser('prepare')
    for n in ('design-dir','tokenizer-dir','model-dir','output'):a.add_argument('--'+n,required=True)
    a=subs.add_parser('freeze-main')
    for n in ('pilot-output','output','truncation-review','repetition-review','reason'):a.add_argument('--'+n,required=True)
    a.add_argument('--budget',required=True,type=int)
    for n in ('inspect','analyze','run','retry','recover'):
        a=subs.add_parser(n);a.add_argument('--output',required=True)
        if n=='run':
            a.add_argument('--scope',choices=('pilot','main'),required=True);a.add_argument('--live-qwen',action='store_true');a.add_argument('--max-new',type=int,default=16)
        if n=='recover':a.add_argument('--reason',required=True)
        if n=='retry':a.add_argument('--cell-id',required=True);a.add_argument('--reason',required=True)
    a=p.parse_args()
    if a.command=='audit':
        r=audit.audit(a.v5_plan,a.output);value={k:r[k] for k in ('artifact_hash','facts','v5_summary','earlier_summary','model_calls')}
    elif a.command=='design':
        r=planning.design(a.kind,a.output,a.v5_plan);value={k:r[k] for k in ('artifact_hash','status','counts','constraints')}
    elif a.command=='audit-shortcuts':
        r=planning.shortcut_audit(a.design_dir,a.output);value={k:r[k] for k in ('artifact_hash','tables','worlds','perfect_shortcuts','histogram_only_upper_bound')}
    elif a.command=='prepare':
        r=planning.prepare(a.design_dir,a.tokenizer_dir,a.model_dir,a.output)
        value=dict(plan_hash=r['artifact_hash'],counts=r['design']['counts'],validated_contexts=len(r['requests']),model_loads=0,inference_calls=0)
    elif a.command=='freeze-main':
        r=planning.freeze_main(a.pilot_output,a.output,a.budget,a.truncation_review,a.repetition_review,a.reason)
        value=dict(plan_hash=r['artifact_hash'],cohort=r['cohort'],budget=r['budget'],requests=len(r['requests']),
                   pilot_measurement_mode=r['budget_review']['pilot']['measurement_mode'],model_loads=0,inference_calls=0)
    elif a.command=='recover':value=execution.recover(a.output,a.reason)
    elif a.command=='retry':value=execution.retry(a.output,a.cell_id,a.reason)
    else:
        r=execution.run(a.output,a.scope,a.live_qwen,a.max_new) if a.command=='run' else execution.analyze(a.output) if a.command=='analyze' else execution.inspect(a.output)
        value={k:r[k] for k in ('protocol','plan_hash','design','counts','this_invocation','cohort','budget','main_budget_status','length_repetition','journal_recovery','next_stage')}
    print(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False))

if __name__=='__main__':main()
