"""Read-only checks and byte snapshots; never normalize historical artifacts."""
import hashlib
import os
import subprocess
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.runner import Source
from exception_study2_v5.journal import operations
from exception_study2_v5 import PROTOCOL
from . import VERSION, ANALYSIS

ROOT=Path(__file__).resolve().parents[1]

def revision():
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def code_hash():
    return digest({p.name:p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def tree(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Regular artifact directory required')
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Artifact symlinks forbidden; never copy or follow model links')
        if p.is_file():
            if p.suffix in ('.safetensors','.bin','.pt','.pth'):raise ValueError('Model weights are not research artifacts')
            result[str(p.relative_to(root))]=sha(p)
    return result

def separate(out, roots):
    if any(out==p or out.is_relative_to(p) or p.is_relative_to(out) for p in roots):
        raise ValueError('Fresh replication output must be separate from all preserved inputs')

def operation_tree(root):
    """Reject orphan states in addition to the original strict journal checks."""
    root=Path(root);base=root/'operations-v5'
    for p in base.iterdir() if base.exists() else []:
        if not p.is_dir() or not (p/'request.json').is_file():raise ValueError('Orphan operation journal')
        if any(x.name not in ('request.json','started.json','returned.json','failed.json') for x in p.iterdir()):
            raise ValueError('Unexpected operation journal file')
    return operations(root)

def pilot(root):
    source=Source(root,scope='pilot');all_source=Source(root,complete=False,scope='all')
    plan=source.plan;ids=[t['id'] for t in plan['tasks'][:32]];saved=operation_tree(root)
    if (len(plan['worlds'])!=60 or len(plan['tasks'])!=480 or len(source.rows)!=32
        or list(all_source.rows)!=ids):raise ValueError('Exactly 32 preserved pilot originals and 448 unattempted originals required')
    if {k for k in saved if k.startswith('v5/original/')}!={'v5/original/'+t for t in ids}:
        raise ValueError('Unexpected/missing original attempt outside the complete pilot')
    if any(not (k.startswith('v5/technical/') or k.startswith('v5/original/')) for k in saved):
        raise ValueError('Source must contain only technical and original operations')
    if any(saved['v5/original/'+tid]['status'] not in ('returned','failed','started') for tid in ids):
        raise ValueError('Pilot contains an unattempted request')
    e=source.execution
    if any(e[k]!=plan[k] for k in ('protocol','plan_hash','source_hash')):
        raise ValueError('Pilot execution does not match the frozen scientific plan')
    if e['mode']=='LIVE_LOCAL':
        from exception_study2_v5.staging import require_design_confirmation
        require_design_confirmation(root)
    return source

def archive_ref(path,out):
    path=Path(path).resolve()
    return dict(path=os.path.relpath(path,out),files=tree(path))

def check_archives(amendment,out):
    for ref in amendment['archives']:
        if tree(Path(out)/ref['path'])!=ref['files']:raise ValueError('Preserved historical archive changed')

def expected_amendment(source,out,archives):
    return dict(version=VERSION,scientific_protocol=PROTOCOL,implementation_hash=code_hash(),analysis=ANALYSIS,
        pilot_examined_before_amendment=True,study_2b_prerequisite_removed=True,
        rationale='Complete the prespecified fixed sample and conditional answer-preference replication independently of unresolved semantic review and Study 2B. The four-world pilot was examined before this workflow decision.',
        original_source=source.binding_at(out),original_execution=source.execution,
        technical_hash=source.technical['artifact_hash'],scientific_plan_hash=source.plan['plan_hash'],
        scientific_source_hash=source.plan['source_hash'],archives=archives,
        copied_source_files=tree(source.root),pilot_rows={k:v['artifact_hash'] for k,v in source.rows.items()},
        remaining_worlds=source.plan['worlds'][4:],remaining_tasks=source.plan['tasks'][32:],
        remaining_visible_ids=[t['id'] for t in source.plan['tasks'][32:] if t['arm']=='visible'],
        original_count=32,remaining_count=448,remaining_visible_count=224,
        generation_budget=2048,readout_ceiling=2688,candidate_sequence_ceiling=8064,
        automatic_measurements=False,automatic_interventions=False,pilot_readouts_recomputed=0)

def read_amendment(output):
    out=Path(output).resolve();a=sealed_read(out/'amendment.json')
    if a['version']!=VERSION or a['implementation_hash']!=code_hash() or a['analysis']!=ANALYSIS:
        raise ValueError('Replication amendment implementation or analysis changed')
    roots=[(out/r['path']).resolve() for r in a['archives']];separate(out,roots)
    check_archives(a,out)
    src=pilot(out/a['original_source']['path'])
    expected=expected_amendment(src,out,a['archives'])
    if {k:v for k,v in a.items() if k!='artifact_hash'}!=expected:
        raise ValueError('Frozen amendment/source/design mismatch')
    copied=out/'originals'
    for name,h in a['copied_source_files'].items():
        if not (copied/name).is_file() or (copied/name).is_symlink() or sha(copied/name)!=h:
            raise ValueError('Copied pilot artifact changed: '+name)
    if Source(copied,scope='pilot').binding!=src.binding:raise ValueError('Copied pilot source binding changed')
    return a
