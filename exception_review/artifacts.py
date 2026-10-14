"""Separate immutable review artifacts; never amend frozen source evidence."""
import hashlib
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.core import read_plan
from exception_continuation.runner import sealed_read, sealed_write, validate_collection
from .policy import freeze_policy


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def freeze(path, value):
    value = {k:v for k,v in value.items() if k!='artifact_hash'}
    path=Path(path)
    if path.exists():
        old=sealed_read(path)
        if {k:v for k,v in old.items() if k!='artifact_hash'} != value: raise ValueError('Immutable artifact differs: '+str(path))
        return old
    return sealed_write(path,value)

class Source:
    def __init__(self, root):
        self.root=Path(root).resolve(); self.plan=read_plan(self.root)
        self.collection=sealed_read(self.root/'collection.json'); validate_collection(self.plan,self.collection)
        self.execution=sealed_read(self.root/'execution.json'); self.technical=sealed_read(self.root/'validation.json')
        if (self.collection['backend_hash']!=self.execution['backend_hash'] or self.technical['backend_hash']!=self.execution['backend_hash'] or self.collection['validation_hash']!=self.technical['artifact_hash'] or not self.technical['passed']): raise ValueError('Source technical/backend identity mismatch')
        self.rows={r['task']['id']:r for r in self.collection['rows'] if r['task']['arm']=='visible'}
        self.binding=dict(plan_hash=self.plan['plan_hash'], collection_hash=self.collection['artifact_hash'], backend_hash=self.execution['backend_hash'], validation_hash=self.technical['artifact_hash'], legacy_source_hash=self.plan['source_hash'], files={n:sha(self.root/n) for n in ('plan.json','collection.json','execution.json','validation.json')}, trajectories={k:digest(r) for k,r in self.rows.items()})
        self.hash=digest(self.binding)
    def detector(self, tid):
        row=self.rows[tid]; raw=row['raw']['text']; marker=raw.find('ANSWER:')
        return dict(original_prompt=row['task']['prompt'], queried_vehicle_id=row['task']['target_plate'], target_row=row['task']['target_row'], detection_view=raw[:marker] if marker>=0 else raw)
    def case_binding(self,tid):
        return dict(source_hash=self.hash, task_id=tid, trajectory_hash=digest(self.rows[tid]), view_hash=digest(self.detector(tid)))

class Review:
    def __init__(self, root):
        self.root=Path(root).resolve(); self.meta=sealed_read(self.root/'review.json')
        self.source=Source(self.meta['source_path']); self.policy=sealed_read(self.root/'policy.json')
        current=freeze_policy(self.policy['config'])
        if current!={k:v for k,v in self.policy.items() if k!='artifact_hash'}: raise ValueError('Review code/prompt/schema/settings changed; use a new policy/output')
        if self.meta['source_hash']!=self.source.hash or self.meta['policy_hash']!=self.policy['policy_hash']: raise ValueError('Review source/policy identity changed')
    def binding(self): return dict(source_hash=self.source.hash,policy_hash=self.policy['policy_hash'],code_hash=self.policy['code_hash'])
    def case_path(self,tid,name): return self.root/'cases'/digest(tid)/(name+'.json')
    def read_case(self,tid,name):
        value=sealed_read(self.case_path(tid,name))
        expected=dict(self.binding(),**self.source.case_binding(tid))
        if any(value.get(k)!=v for k,v in expected.items()): raise ValueError('Wrong-source or stale case artifact: '+name)
        return value

    def plan(self,name='full'):
        if name not in ('full','pilot'): raise ValueError('Unknown review scope')
        p=sealed_read(self.root/'plans'/(name+'.json'))
        if any(p[k]!=v for k,v in self.binding().items()): raise ValueError('Stale review scope')
        return p


def prepare(source, output, config, scope='full', policy_lock=None):
    src=Source(source); out=Path(output).resolve(); policy=freeze_policy(config)
    if out==src.root or src.root in out.parents or out in src.root.parents: raise ValueError('Review must live separately from source')
    if scope not in ('full','pilot'): raise ValueError('Unknown scope')
    if scope=='pilot' and src.plan['phase']!='selection': raise ValueError('Timing pilot requires completed selection/development, never confirmation')
    if src.plan['phase']=='confirmation':
        if not policy_lock: raise ValueError('Confirmation needs frozen selection policy lock')
        lock=sealed_read(policy_lock)
        selected=src.plan['selection_lock']
        if (lock.get('policy_hash')!=policy['policy_hash'] or lock.get('selection_collection_hash')!=selected['collection_hash'] or lock.get('no_2a_selection') is not True): raise ValueError('Confirmation policy was not frozen during selected discovery')
    ids=list(src.rows); limitation=None
    if scope=='pilot':
        worlds=[]
        for w in src.plan['worlds']:
            rows=[t for t in src.plan['tasks'] if t['world']==w['id'] and t['arm']=='visible']
            if {t['variant'] for t in rows}!={0,1} or len(rows)!=2: break
            worlds.append(w['id'])
            if len(worlds)==3: break
        ids=[t['id'] for t in src.plan['tasks'] if t['arm']=='visible' and t['world'] in worlds]
        if len(worlds)<3: limitation=f'Only {len(worlds)} complete worlds available; no outcome-based replacement'
    with run_lock(out/'locks'):
        freeze(out/'policy.json',policy)
        freeze(out/'review.json',dict(source_path=str(src.root),source_hash=src.hash,source=src.binding,policy_hash=policy['policy_hash'],phase=src.plan['phase'],confirmation_policy_lock=None if policy_lock is None else sealed_read(policy_lock)))
        value=dict(source_hash=src.hash,policy_hash=policy['policy_hash'],code_hash=policy['code_hash'],scope=scope,case_ids=ids,source_case_count=len(src.rows),maximum_logical_calls=7*len(ids),concurrency=1,limitation=limitation,synthetic=src.execution['mode']=='SIMULATED')
        return freeze(out/'plans'/(scope+'.json'),value)
