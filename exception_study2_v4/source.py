"""Explicit v4 source contract. No legacy validation files or status aliases."""
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.core import final_score
from exception_continuation.runner import sealed_read
from exception_review.artifacts import Source as LegacySource, sha
from . import PROTOCOL
from .core import read_plan
from .validation import require_technical
from .journal import operations

class Source(LegacySource):
    # Only detector/case_binding's pure text views are inherited, never v3's loader.
    def __init__(self, root):
        self.root=Path(root).resolve(); self.plan=read_plan(self.root)
        self.execution=sealed_read(self.root/'execution-v4.json')
        self.collection=sealed_read(self.root/'collection-v4.json')
        if self.execution['backend_hash']!=digest(self.execution['backend']):raise ValueError('Backend fingerprint changed')
        self.technical=require_technical(self.root,self.plan,self.execution)
        if (self.collection['protocol']!=PROTOCOL or self.collection['plan_hash']!=self.plan['plan_hash']
                or self.collection['backend_hash']!=self.execution['backend_hash']
                or self.collection['technical_same_input_hash']!=self.technical['artifact_hash']
                or self.execution['plan_hash']!=self.plan['plan_hash']
                or self.execution['source_hash']!=self.plan['source_hash']):raise ValueError('v4 source identities differ')
        if [r['task'] for r in self.collection['rows']]!=self.plan['tasks']:
            raise ValueError('Complete ordered v4 original collection required')
        saved=operations(root)
        for row in self.collection['rows']:
            tid=row['task']['id']; op=saved['v4/original/'+tid]; ids=row['input_ids'];raw=row['raw']
            if (op['status']!='returned' or op['result']!=raw or op['plan_hash']!=self.plan['plan_hash']
                    or op['protocol']!=PROTOCOL or op['source_hash']!=self.plan['source_hash']
                    or op['backend_hash']!=self.execution['backend_hash']
                    or op['request']!=dict(input_ids=ids,context_hash=digest(ids),budget=512,capture_at=[],fresh_prefill=True)
                    or row['input_hash']!=digest(ids) or row['full_token_ids']!=ids+raw['tokens']
                    or row['score']!=final_score(raw['text'],raw['stopped'],row['task']['expected'])):
                raise ValueError('Original trajectory/journal differs')
        self.rows={r['task']['id']:r for r in self.collection['rows'] if r['task']['arm']=='visible'}
        names=('plan-v4.json','collection-v4.json','execution-v4.json','technical-v4.json')
        self.binding=dict(source_schema=PROTOCOL,plan_hash=self.plan['plan_hash'],collection_hash=self.collection['artifact_hash'],
            backend_hash=self.execution['backend_hash'],technical_same_input_hash=self.technical['artifact_hash'],
            v4_source_hash=self.plan['source_hash'],files={n:sha(self.root/n) for n in names},
            trajectories={k:digest(r) for k,r in self.rows.items()})
        self.hash=digest(self.binding)
