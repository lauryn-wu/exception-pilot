"""Offline, uncued original-prefix reconstruction. Never import/load a tokenizer or model."""
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from . import PROTOCOL
from .scoring import checkpoints, marker_start

SCHEMA = 'v5-fresh-prefix-context-v1'

def validate_boundaries(row):
    raw=row['raw']; text=raw['text']; ids=raw['tokens']
    if not isinstance(ids,list) or any(type(t) is not int or t<0 for t in ids):
        raise ValueError('Corrupted original tokens')
    marker=marker_start(text); limit=len(text) if marker is None else marker
    previous=(-1,-1)
    for c in row['boundaries']:
        k,end=c.get('k'),c.get('char_end')
        if (type(k) is not int or type(end) is not int or not 0<=k<=len(ids) or not 0<=end<=limit
            or k<=previous[0] or end<previous[1] or c.get('roundtrip_exact') is not True
            or c.get('token_hash')!=digest(ids[:k]) or c.get('text_hash')!=digest(text[:end])):
            raise ValueError('Malformed or stale original boundary fingerprint')
        previous=(k,end)
    if not row['boundaries'] or row['boundaries'][0]['k']!=0 or row['boundaries'][0]['char_end']!=0:
        raise ValueError('Missing initial boundary')

def prepare_checkpoints(source_path, output, annotations=None, scope='pilot'):
    from .runner import Source
    from .review.workflow import read_manifest
    import os
    source=Source(source_path,scope=scope); target=Path(output)
    ann=read_manifest(annotations,source) if annotations else None
    rows={}
    for tid,row in source.rows.items():
        if row['task']['arm']!='visible':continue
        cuts=checkpoints(row,ann['cases'][tid]['events'] if ann else None) if row['status']=='returned' else [
            dict(name='original',eligible=False,k=None,reason=row['status'])]
        rows[tid]=dict(world=row['task']['world'],source_row_hash=row['artifact_hash'],
                      prompt_hash=row['input_hash'],output_hash=row['output_hash'],checkpoints=cuts)
    return freeze(target,dict(protocol=PROTOCOL,schema=SCHEMA,source=source.binding_at(target.parent),
        annotations=dict(path=os.path.relpath(Path(annotations).resolve(),target.parent.resolve()),
                         artifact_hash=ann['artifact_hash']) if ann else None,
        rows=rows,context_kind='fresh-prefix replay context',answer_cue_appended=False,
        original_hidden_state_equivalence=False,activations_collected=False))

def reconstruct(manifest_path, task_id, checkpoint, output=None):
    from .runner import bound_source
    from .review.workflow import read_manifest
    path=Path(manifest_path); manifest=sealed_read(path)
    if manifest.get('schema')!=SCHEMA or manifest.get('protocol')!=PROTOCOL:
        raise ValueError('Wrong checkpoint manifest type')
    source=bound_source(manifest['source'],path.parent)
    ann=None
    if manifest['annotations']:
        ref=manifest['annotations'];ann=read_manifest(path.parent/ref['path'],source)
        if ann['artifact_hash']!=ref['artifact_hash']:raise ValueError('Stale annotation manifest')
    expected_ids={tid for tid,r in source.rows.items() if r['task']['arm']=='visible'}
    if set(manifest['rows'])!=expected_ids:raise ValueError('Checkpoint population mismatch')
    if task_id not in expected_ids:raise ValueError('Only original visible tasks may supply reasoning prefixes')
    row=source.rows[task_id];saved=manifest['rows'][task_id]
    if (saved['world']!=row['task']['world'] or saved['source_row_hash']!=row['artifact_hash']
        or saved['prompt_hash']!=row['input_hash'] or saved['output_hash']!=row['output_hash']):
        raise ValueError('Checkpoint source identity changed')
    expected=checkpoints(row,ann['cases'][task_id]['events'] if ann else None) if row['status']=='returned' else [
        dict(name='original',eligible=False,k=None,reason=row['status'])]
    if expected!=saved['checkpoints']:raise ValueError('Checkpoint offsets/eligibility changed')
    cuts=[c for c in expected if c['name']==checkpoint]
    if len(cuts)!=1:raise ValueError('Unknown or duplicate checkpoint')
    cut=cuts[0]
    value=dict(schema=SCHEMA,protocol=PROTOCOL,task_id=task_id,world=row['task']['world'],
        task=row['task'],source_row_hash=row['artifact_hash'],operation_hash=row['operation_hash'],
        plan_hash=source.plan['plan_hash'],source_hash=source.plan['source_hash'],
        checkpoint_manifest_hash=manifest['artifact_hash'],checkpoint=cut,
        available=cut['eligible'],reason=cut['reason'],context_kind='fresh-prefix replay context',
        answer_cue_appended=False,original_hidden_state_equivalence=False,activations_collected=False,
        recorded_backend=source.execution['backend'],code_revision=source.execution['code_revision'],
        generation_parameters=dict(config=source.plan['config'],budget=2048,fresh_prefill=True),
        technical_report_hash=source.technical['artifact_hash'],
        replay_discrepancy_metadata=source.technical,
        original_finish=row['raw'].get('finish') if isinstance(row['raw'],dict) else None,
        original_score=row['score'])
    if cut['eligible']:
        k=cut['k']; prefix=row['raw']['tokens'][:k]; prompt=row['input_ids']
        value.update(prompt_ids=prompt,original_prefix_ids=prefix,context_ids=prompt+prefix,
                     prompt_token_hash=digest(prompt),prefix_token_hash=digest(prefix),context_hash=digest(prompt+prefix),
                     original_prefix_text=row['raw']['text'][:cut['char_end']],
                     input_length=len(prompt),prefix_length=k,context_length=len(prompt)+k)
    else:
        value.update(prompt_ids=None,original_prefix_ids=None,context_ids=None)
    return freeze(Path(output),value) if output else value
