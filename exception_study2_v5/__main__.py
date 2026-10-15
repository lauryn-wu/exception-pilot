import argparse
import json
from pathlib import Path
from . import core, runner, readouts, interventions, reporting, workloads
from .review import workflow

def main():
    p=argparse.ArgumentParser(description='Explicit isolated v5 stages; no automatic downstream execution')
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('configure');c.add_argument('--model-dir',required=True);c.add_argument('--config',required=True)
    c=sub.add_parser('prepare');c.add_argument('--config',required=True);c.add_argument('--output',required=True);c.add_argument('--phase',choices=['selection','confirmation'],default='selection');c.add_argument('--selection-output');c.add_argument('--policy-lock')
    for name in ('preflight','summary','timing'):
        c=sub.add_parser(name);c.add_argument('--output',required=True)
    for name in ('validate','collect','measure','intervene'):
        c=sub.add_parser(name);c.add_argument('--output',required=True)
        g=c.add_mutually_exclusive_group(required=True);g.add_argument('--live-qwen',action='store_true');g.add_argument('--mock',action='store_true')
        if name=='collect':c.add_argument('--complete',action='store_true')
    for name in ('prepare-review','prepare-measurements','prepare-edits'):
        c=sub.add_parser(name);c.add_argument('--source',required=True);c.add_argument('--output',required=True)
        if name!='prepare-review':c.add_argument('--annotations',required=name=='prepare-edits')
        if name=='prepare-edits':c.add_argument('--family',choices=['M','O'],required=True)
    c=sub.add_parser('freeze-annotations');c.add_argument('--output',required=True);c.add_argument('--first',required=True);c.add_argument('--second',required=True);c.add_argument('--adjudication')
    c=sub.add_parser('annotation-summary');c.add_argument('--source',required=True);c.add_argument('--annotations',required=True)
    c=sub.add_parser('freeze-edits');c.add_argument('--output',required=True);c.add_argument('--drafts',required=True);c.add_argument('--verification',required=True);c.add_argument('--tokenizer-dir',required=True)
    c=sub.add_parser('freeze-lock');c.add_argument('--source',required=True);c.add_argument('--annotations',required=True);c.add_argument('--output',required=True);c.add_argument('--decisions',required=True)
    sub.add_parser('workload')
    a=p.parse_args();d=vars(a);command=d.pop('command')
    if command=='configure':result=core.configure(a.model_dir,a.config)
    elif command=='prepare':
        d['configuration']=json.loads(Path(d.pop('config')).read_text());result=core.prepare(**d)
    elif command=='preflight':
        from .preflight import preflight
        result=preflight(a.output)
    elif command=='validate':result=runner.technical(**d)
    elif command=='collect':result=runner.collect(**d)
    elif command=='summary':result=reporting.behavioral_report(a.output)
    elif command=='timing':result=reporting.timing_report(a.output)
    elif command=='prepare-review':result=workflow.prepare_review(a.source,a.output)
    elif command=='freeze-annotations':result=workflow.freeze_annotations(**d)
    elif command=='annotation-summary':
        source=runner.Source(a.source);result=reporting.annotation_report(source,workflow.read_manifest(a.annotations,source))
    elif command=='prepare-measurements':result=readouts.prepare_measurements(a.source,a.output,a.annotations)
    elif command=='measure':result=readouts.measure(**d)
    elif command=='prepare-edits':result=interventions.prepare_edits(a.source,a.annotations,a.output,a.family)
    elif command=='freeze-edits':result=interventions.freeze_edits(**d)
    elif command=='intervene':result=interventions.intervene(**d)
    elif command=='freeze-lock':result=workflow.freeze_lock(a.source,a.annotations,a.output,a.decisions)
    else:result=workloads.report()
    # Large plans remain on disk. The printed seal binds the complete artifact.
    if isinstance(result,dict) and 'artifact_hash' in result:
        result={k:result[k] for k in ('protocol','artifact_hash','family','technical_same_input_passed','measurement','real_model_status','maximum_operations') if k in result}
        result['next_stage']='STOP'
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
