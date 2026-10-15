import argparse
import json
from pathlib import Path
from . import core, runner, readouts, interventions, reporting, workloads, staging, reconstruction, splits
from .review import workflow

def main():
    p=argparse.ArgumentParser(description='Explicit staged v5; every command stops after its own stage')
    sub=p.add_subparsers(dest='command',required=True)
    def output(c):c.add_argument('--output',required=True)
    def scope(c):c.add_argument('--scope',choices=['pilot','remaining','all'],default='pilot')
    def source(c):c.add_argument('--source',required=True);output(c)
    c=sub.add_parser('configure');c.add_argument('--model-dir',required=True);c.add_argument('--config',required=True)
    c=sub.add_parser('prepare');c.add_argument('--config',required=True);output(c)
    c=sub.add_parser('confirm-design');output(c);c.add_argument('--reviewer',required=True);c.add_argument('--rationale',required=True);c.add_argument('--worlds',type=int,required=True)
    for name in ('preflight','summary','timing'):
        c=sub.add_parser(name);output(c)
        if name=='summary':scope(c)
    for name in ('validate','collect','measure','intervene'):
        c=sub.add_parser(name);output(c)
        g=c.add_mutually_exclusive_group(required=True);g.add_argument('--live-qwen',action='store_true');g.add_argument('--mock',action='store_true')
        if name=='collect':c.add_argument('--batch',choices=['pilot','remaining'],default='pilot')
    for name in ('prepare-review','prepare-measurements','prepare-edits','prepare-checkpoints'):
        c=sub.add_parser(name);source(c);scope(c)
        if name!='prepare-review':c.add_argument('--annotations',required=name=='prepare-edits')
        if name=='prepare-measurements':c.add_argument('--events-only',action='store_true')
        if name=='prepare-edits':c.add_argument('--family',choices=['M','O'],required=True)
    c=sub.add_parser('freeze-annotations');output(c);c.add_argument('--first',required=True);c.add_argument('--second',required=True);c.add_argument('--adjudication')
    c=sub.add_parser('annotation-summary');c.add_argument('--source',required=True);c.add_argument('--annotations',required=True);scope(c)
    c=sub.add_parser('freeze-edits');output(c);c.add_argument('--drafts',required=True);c.add_argument('--verification',required=True);c.add_argument('--tokenizer-dir',required=True)
    c=sub.add_parser('pilot-checklist');source(c)
    for key in ('measurements','annotations','family-m','family-o'):c.add_argument('--'+key,required=True)
    c.add_argument('--event-measurements')
    c=sub.add_parser('approve-remaining');output(c);c.add_argument('--checklist',required=True);c.add_argument('--decisions',required=True)
    c=sub.add_parser('reconstruct');c.add_argument('--manifest',required=True);c.add_argument('--task',required=True);c.add_argument('--checkpoint',required=True);output(c)
    c=sub.add_parser('split-worlds');source(c);c.add_argument('--seed',type=int,default=20261015054);c.add_argument('--test-worlds',type=int,default=12);c.add_argument('--pilot-informed-design',choices=['yes','no'],required=True)
    sub.add_parser('workload')
    a=p.parse_args();d=vars(a);command=d.pop('command')
    if command=='configure':result=core.configure(a.model_dir,a.config)
    elif command=='prepare':
        d['configuration']=json.loads(Path(d.pop('config')).read_text());result=core.prepare(**d)
    elif command=='confirm-design':result=staging.confirm_design(**d)
    elif command=='preflight':
        from .preflight import preflight
        result=preflight(a.output)
    elif command=='validate':result=runner.technical(**d)
    elif command=='collect':result=runner.collect(**d)
    elif command=='summary':result=reporting.behavioral_report(**d)
    elif command=='timing':result=reporting.timing_report(a.output)
    elif command=='prepare-review':result=workflow.prepare_review(a.source,a.output,a.scope)
    elif command=='freeze-annotations':result=workflow.freeze_annotations(**d)
    elif command=='annotation-summary':
        src=runner.Source(a.source,scope=a.scope);result=reporting.annotation_report(src,workflow.read_manifest(a.annotations,src))
    elif command=='prepare-measurements':result=readouts.prepare_measurements(a.source,a.output,a.annotations,a.scope,a.events_only)
    elif command=='measure':result=readouts.measure(**d)
    elif command=='prepare-edits':result=interventions.prepare_edits(a.source,a.annotations,a.output,a.family,a.scope)
    elif command=='freeze-edits':result=interventions.freeze_edits(**d)
    elif command=='intervene':result=interventions.intervene(**d)
    elif command=='prepare-checkpoints':result=reconstruction.prepare_checkpoints(a.source,a.output,a.annotations,a.scope)
    elif command=='reconstruct':result=reconstruction.reconstruct(a.manifest,a.task,a.checkpoint,a.output)
    elif command=='split-worlds':result=splits.make_splits(a.source,a.output,a.seed,a.test_worlds,a.pilot_informed_design=='yes')
    elif command=='pilot-checklist':
        d['source_path']=d.pop('source');result=staging.pilot_checklist(**d)
    elif command=='approve-remaining':result=staging.approve_remaining(**d)
    else:result=workloads.report()
    if isinstance(result,dict) and 'artifact_hash' in result:
        result={k:result[k] for k in ('protocol','artifact_hash','family','technical_same_input_passed','measurement','real_model_status','maximum_operations') if k in result}
        result['next_stage']='STOP'
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
