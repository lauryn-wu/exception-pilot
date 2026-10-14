"""Review provenance for actual v4 originals and their same-input technical gate."""
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze,sha,Review as LegacyReview
from ..source import Source
from .. import PROTOCOL
from .policy import freeze_policy

class Review(LegacyReview):
    def __init__(self,root):
        self.root=Path(root).resolve();self.meta=sealed_read(self.root/'review.json')
        if self.meta.get('source_schema')!=PROTOCOL:raise ValueError('An explicit v4 review is required')
        self.source=Source(self.meta['source_path']);self.policy=sealed_read(self.root/'policy.json')
        if freeze_policy(self.policy['config'])!={k:v for k,v in self.policy.items() if k!='artifact_hash'}:
            raise ValueError('v4 review policy/code changed; incompatible resume')
        if self.meta['source_hash']!=self.source.hash or self.meta['policy_hash']!=self.policy['policy_hash']:
            raise ValueError('v4 review source/policy identity changed')
        if self.source.plan['phase']=='confirmation':
            lock=self.meta.get('confirmation_policy_lock') or {};chosen=self.source.plan['selection_lock']
            if lock.get('artifact_hash')!=chosen['policy_lock_hash'] or self.policy['policy_hash']!=chosen['policy_hash']:
                raise ValueError('Confirmation review-policy lock changed')

    def binding(self):
        return dict(source_schema=PROTOCOL,source_hash=self.source.hash,policy_hash=self.policy['policy_hash'],code_hash=self.policy['code_hash'])

def prepare(source,output,config,scope='full',policy_lock=None):
    src=Source(source);out=Path(output).resolve();policy=freeze_policy(config)
    if out==src.root or src.root in out.parents or out in src.root.parents:raise ValueError('Review must live separately from source')
    if scope not in ('full','pilot'):raise ValueError('Unknown review scope')
    if scope=='pilot' and src.plan['phase']!='selection':raise ValueError('Judge pilot is selection only')
    locked=sealed_read(policy_lock) if policy_lock else None
    if src.plan['phase']=='confirmation':
        chosen=src.plan['selection_lock']
        if (not locked or locked['artifact_hash']!=chosen['policy_lock_hash'] or policy['policy_hash']!=chosen['policy_hash']
                or locked['selection_collection_hash']!=chosen['collection_hash'] or locked.get('no_2a_selection') is not True):
            raise ValueError('Confirmation needs the exact frozen selection policy')
    ids=list(src.rows)
    if scope=='pilot':
        worlds=[w['id'] for w in src.plan['worlds'][:3]]
        ids=[t['id'] for t in src.plan['tasks'] if t['arm']=='visible' and t['world'] in worlds]
    with run_lock(out/'locks'):
        freeze(out/'policy.json',policy)
        freeze(out/'review.json',dict(source_schema=PROTOCOL,source_path=str(src.root),source_hash=src.hash,source=src.binding,
            policy_hash=policy['policy_hash'],phase=src.plan['phase'],confirmation_policy_lock=locked))
        return freeze(out/'plans'/(scope+'.json'),dict(source_schema=PROTOCOL,source_hash=src.hash,policy_hash=policy['policy_hash'],
            code_hash=policy['code_hash'],scope=scope,case_ids=ids,source_case_count=len(src.rows),
            maximum_logical_calls=7*len(ids),concurrency=1,limitation=None,synthetic=src.execution['mode']=='MOCK'))
