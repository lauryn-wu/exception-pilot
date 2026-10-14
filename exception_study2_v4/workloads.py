"""Conditional v4 workload counts from versioned plans and immutable journals."""
from pathlib import Path
from exception_continuation.runner import sealed_read
from .core import read_plan
from .journal import operations
from .readouts import saved_cut


def count(expected,output,finished=False,binding=None):
    saved=operations(output);result={}
    if binding and any(any(op.get(k)!=v for k,v in binding.items()) for op in saved.values()):
        raise ValueError('Workload journal provenance changed')
    for stage in set(expected.values()):
        ids=[k for k,v in expected.items() if v==stage]
        attempted=sum(k in saved and saved[k]['status']!='planned' for k in ids)
        returned=sum(k in saved and saved[k]['status']=='returned' for k in ids)
        factor=3 if stage=='candidate_sequences' else 1
        result[stage]=dict(logical_planned=len(ids),logical_attempted=attempted,logical_returned=returned,
            sequence_ceiling_per_operation=factor,terminal_unavailable=attempted-returned,
            remaining_count_scenario=[0,0 if finished else factor*(len(ids)-attempted)],
            partial_failure_note='Candidate counts are ceilings; individual completed/failed sequence calls are in telemetry' if factor==3 else None)
    return result


def fixed_expected(plan,rows):
    expected={}
    for row in rows:
        t=row['task']
        if t['arm']!='visible':continue
        for k in plan['checkpoints']:
            if saved_cut(row,k) is None:continue
            cues=plan['config']['readout_cues'] if k in plan['config']['cue_check_checkpoints'] else plan['config']['readout_cues'][:1]
            for ci in range(len(cues)):expected[f"v4/fixed/{t['id']}/{k}/cue{ci}"]='candidate_sequences'
    return expected


def event_counts(output,source_hash=None):
    out=Path(output);p=sealed_read(out/'event-plan-v4.json')
    from .source import Source
    from . import PROTOCOL
    from .core import source_hash as code_hash
    source=Source(p['source_path'])
    if (p['protocol']!=PROTOCOL or p['source_hash']!=source.hash or p['code_hash']!=code_hash()
            or source_hash is not None and p['source_hash']!=source_hash):raise ValueError('Event source changed')
    expected={f"v4/event/{r['task_id']}/{k}/cue0":'candidate_sequences' for r in p['rows'] for k in {c['k'] for c in r['cuts'] if c['eligible']}}
    return dict(output=str(out.resolve()),basis='FROZEN_V4_EVENT_PLAN',counts=count(expected,out,(out/'event-measurements-v4.json').exists(),dict(source_binding=source.hash,manifest_hash=p['artifact_hash'])),generation_operations=0)


def workload(output,event_outputs=None):
    out=Path(output)
    if (out/'plan-v4.json').exists():
        plan=read_plan(out);saved=operations(out)
        expected={'v4/original/'+t['id']:'original_generation' for t in plan['tasks']}
        originals=count(expected,out,(out/'collection-v4.json').exists(),dict(plan_hash=plan['plan_hash'],source_hash=plan['source_hash']))
        technical=[v for k,v in saved.items() if k.startswith('v4/technical/')]
        technical_done=(out/'technical-v4.json').exists()
        technical_max=sealed_read(out/'technical-v4.json')['operation_count'] if technical_done else 33
        technical_attempts=sum(x['status']!='planned' for x in technical)
        result=dict(basis='V4_PLAN_AND_JOURNAL',originals=originals,technical=dict(planned_maximum=technical_max,
            attempted=technical_attempts,remaining_count_scenario=[0,0 if technical_done else technical_max-technical_attempts]),
            downstream_automatically_launched=False)
        if (out/'collection-v4.json').exists():
            from .source import Source
            source=Source(out)
            result['fixed_2a']=dict(basis='SAVED_ORIGINAL_BOUNDARIES',counts=count(fixed_expected(plan,source.collection['rows']),out/'fixed-v4',(out/'fixed-v4/measurements-v4.json').exists(),dict(source_binding=source.hash)),generation_operations=0)
        else:
            n=sum(t['arm']=='visible' for t in plan['tasks']);cues=sum(len(plan['config']['readout_cues']) if k in plan['config']['cue_check_checkpoints'] else 1 for k in plan['checkpoints'])
            result['fixed_2a']=dict(basis='CONDITIONAL_BEFORE_COLLECTION',candidate_sequences=[0,3*n*cues],generation_operations=0)
        if event_outputs is not None:
            from .source import Source
            source=Source(out);paths=list(dict.fromkeys(str(Path(p).resolve()) for p in event_outputs))
            result['events']=[event_counts(p,source.hash) for p in paths]
        else:
            n=sum(t['arm']=='visible' for t in plan['tasks'])
            result['events']=dict(basis='CONDITIONAL_NO_FROZEN_EVENT_PLANS_SUPPLIED',candidate_sequences=[0,3*n*len(plan['config']['event_checkpoints'])],generation_operations=0)
        result['interventions']=dict(basis='CONDITIONAL_ON_FROZEN_REVIEW_COHORT',continuations_per_case=4,candidate_sequences_per_case=12,case_count=None)
        return result
    if (out/'event-plan-v4.json').exists():return event_counts(out)
    if out.name=='fixed-v4' and (out.parent/'plan-v4.json').exists():
        from .source import Source
        s=Source(out.parent)
        return dict(basis='SAVED_ORIGINAL_BOUNDARIES',counts=count(fixed_expected(s.plan,s.collection['rows']),out,(out/'measurements-v4.json').exists(),dict(source_binding=s.hash)),generation_operations=0)
    if (out/'edit-plan-reference-v4.json').exists():
        from .source import Source
        from . import PROTOCOL
        from .core import source_hash as code_hash
        p=sealed_read(out/'edit-plan-reference-v4.json');expected={};source=Source(p['source_path'])
        if (p['protocol']!=PROTOCOL or p['source_hash']!=source.hash or p['manifest']['source_hash']!=source.hash
                or p['manifest']['code_hash']!=code_hash()):raise ValueError('Intervention workload source changed')
        for c in p['manifest']['cases']:
            for arm in c['arm_order']:
                expected[f"v4/edit/{c['task_id']}/{arm}/continuation"]='edited_continuation'
                expected[f"v4/edit/{c['task_id']}/{arm}/readout"]='candidate_sequences'
        return dict(basis='FROZEN_V4_INTERVENTION_COHORT',counts=count(expected,out,(out/'interventions-v4.json').exists(),dict(source_binding=source.hash,manifest_hash=p['manifest']['artifact_hash'])))
    return dict(basis='NO_FROZEN_WORK_PLAN',remaining=None)
