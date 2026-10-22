"""Allowlisted, checksummed evidence bundle. Never export a model folder or credentials."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from exception_pilot.storage import run_lock
from exception_review.artifacts import sha
from exception_study2_source_report.integrity import separate
from .planning import Context
from .execution import journal
from .analysis import report

ANNOTATIONS=('correct_record_mention','explicit_false_absence','record_uncertainty',
             'feature_based_justification','target_in_feature_class_association')
TOP={'plan.json','locations.json','execution.json','smoke-evidence.json','smoke-prefixes.json'}
DIRS={'operations-v5','dispatches','invocations','journal-recovery'}


def annotation_sheet(rows):
    stream=io.StringIO();fields=['cell_id','world','thinking','operation_status','request_hash','operation_hash','raw_text',
        'observability_note']
    for name in ANNOTATIONS:fields += [name,name+'_quote',name+'_start',name+'_end']
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
    for x in rows:
        d=dict(cell_id=x['cell']['id'],world=x['cell']['world'],thinking=x['cell']['thinking'],
            operation_status=x['operation_status'],request_hash=x['request_hash'],operation_hash=x['operation_hash'],
            raw_text=x['raw'].get('raw_text','') if isinstance(x['raw'],dict) else '',
            observability_note='Thinking-off label-only output offers less observable evidence.' if not x['cell']['thinking'] else '')
        for name in ANNOTATIONS:d[name]='not_reviewed'
        writer.writerow(d)
    return stream.getvalue()


def snapshot(c):
    current,_,_=journal(c);value=report(c,current,dict(new_generations=0,model_loads=0));files={}
    for p in sorted(c.out.rglob('*')):
        relative=p.relative_to(c.out)
        if relative.parts[0] not in DIRS and str(relative) not in TOP:continue
        if p.is_symlink():raise ValueError('Export rejects symlinks')
        if p.is_file():files[str(relative)]=p.read_bytes()
    if c.plan['kind']=='screen':
        from exception_study2_native.shortcuts import audit_shortcuts
        files['shortcut-audit.json']=(json.dumps(audit_shortcuts(c.plan['design']['tables']),indent=2,sort_keys=True)+'\n').encode()
    files['analysis.json']=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    files['manual-review.csv']=annotation_sheet(value['cases']).encode()
    traces=[]
    for x in value['cases']:
        traces += [x['cell']['id'],f"request={x['request_hash']} operation={x['operation_hash']} state={x['operation_status']}",
            json.dumps(x['score'],ensure_ascii=False),x['raw'].get('raw_text','') if isinstance(x['raw'],dict) else '[no returned text]','']
    files['traces.txt']='\n'.join(traces).encode()
    return files,value


def export(output,destination):
    c=Context(output);target=separate(destination,c.out,*[c.locations[k] for k in ('model','tokenizer')])
    if target.exists():raise ValueError('Fresh export path required')
    with run_lock(c.out):
        files,value=snapshot(c)
        if c.plan['smoke']:
            sc=Context(c.plan['smoke']['path'])
            if sc.plan['artifact_hash']!=c.plan['smoke']['plan_hash']:raise ValueError('Smoke plan changed')
            with run_lock(sc.out):
                smoke,_=snapshot(sc);files.update({'technical-smoke/'+k:v for k,v in smoke.items()})
        manifest=dict(protocol=c.plan['protocol'],plan_hash=c.plan['artifact_hash'],code_contract=c.plan['code_contract'],
            files={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in sorted(files.items())},
            annotation_states=['not_reviewed','absent','present'],
            annotation_offsets='Zero-based half-open Unicode character indices in raw_text; quotes must equal raw_text[start:end]. Indicators may coexist; no automatic semantic labeling.',
            note='Immutable operations authoritative. Derived views are regenerated. No weights, keys or environment variables collected.')
        files['bundle-manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as handle:
            with zipfile.ZipFile(handle,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name,data in sorted(files.items()):z.writestr(name,data)
    return dict(package=str(target),sha256=sha(target),files=len(files),measurement_mode=value['measurement_mode'],model_loads=0)
