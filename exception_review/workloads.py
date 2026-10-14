"""Read-only workload accounting from frozen plans and operation journals."""
from pathlib import Path
from exception_continuation.core import read_plan
from exception_continuation.runner import sealed_read, validate_collection
from .artifacts import Source


def records_at(out):
    return [sealed_read(p) for p in (Path(out)/'timing-sidecar/events').glob('*.json')]


def event_workload(output, source_hash):
    out=Path(output).resolve(); plan=sealed_read(out/'event-plan.json')
    if plan['source_hash']!=source_hash: raise ValueError('Event timing source changed')
    expected={}
    for row in plan['rows']:
        tid=row['task_id']; ks={c['k'] for c in row['cuts'] if c['eligible']}
        if ks: expected[f'event/{tid}/reference']='event_reference'
        for k in ks:
            expected[f'event/{tid}/replay/{k}']='event_validation'
            expected[f'event/{tid}/readout/{k}']='candidate_sequence_scoring_events'
    ops={}
    for p in (out/'model-operations').glob('*.json'):
        op=sealed_read(p)
        if op['source_hash']!=source_hash or op['manifest_hash']!=plan['artifact_hash']:
            raise ValueError('Event operation binding changed')
        if op['id'] not in expected: raise ValueError('Unexpected event operation')
        ops[op['id']]=op
    finished=(out/'event-measurements.json').exists()
    if finished:
        result=sealed_read(out/'event-measurements.json')
        if result['event_plan_hash']!=plan['artifact_hash'] or result['source_hash']!=source_hash: raise ValueError('Event result binding changed')
    counts={}
    for stage in ('event_reference','event_validation','candidate_sequence_scoring_events'):
        weight=3 if stage.startswith('candidate_') else 1
        ids=[k for k,v in expected.items() if v==stage]
        attempted=sum(k in ops for k in ids); returned=sum(k in ops and ops[k]['status']=='returned' for k in ids)
        counts[stage]=dict(planned_maximum=weight*len(ids),attempted=weight*attempted,returned=weight*returned,
                           terminal_unavailable=weight*(attempted-returned),
                           remaining_count_scenario=[0,0 if finished else weight*(len(ids)-attempted)],
                           gate_excluded=weight*(len(ids)-attempted) if finished else None)
    return dict(output=str(out),kind=plan['kind'],plan_hash=plan['artifact_hash'],counts=counts,
                cache_hits=sum(e.get('status')=='cache_hit' for e in records_at(out)),
                completed=finished,
                candidate_count_note='Three sequences per readout; partial failed readouts have per-sequence actuals in telemetry.')


def aggregate_events(output, event_outputs=None):
    plan=read_plan(output); visible=sum(t['arm']=='visible' for t in plan['tasks'])
    enabled=plan['config']['event_checkpoints']; answer=int('before_answer' in enabled)
    statement=sum(n in enabled for n in ('before_statement','after_statement'))
    if event_outputs is None:
        return dict(basis='CONDITIONAL_SCENARIOS_NO_EVENT_DIRECTORIES_SUPPLIED',plans=[],
                    conditional_scenarios=dict(before_answer_only=dict(event_reference=[0,answer*visible]),
                                               statement_only=dict(event_reference=[0,int(bool(statement))*visible]),
                                               both_separate_directories=dict(event_reference=[0,(answer+bool(statement))*visible])),
                    counts=dict(event_reference=dict(remaining_count_scenario=[0,(answer+bool(statement))*visible]),
                                event_validation=dict(remaining_count_scenario=[0,(answer+statement)*visible]),
                                candidate_sequence_scoring_events=dict(remaining_count_scenario=[0,3*(answer+statement)*visible])),
                    note='Each event directory has its own reference; identical cuts are deduplicated only within that plan. This changes reference work, not the entire runtime.')
    source=Source(output)
    # The same path repeated in a CLI argument is one requested plan; separate
    # directories intentionally count separately, even when their cuts overlap.
    paths=list(dict.fromkeys(str(Path(p).resolve()) for p in event_outputs))
    plans=[event_workload(p,source.hash) for p in paths]; combined={}
    for stage in ('event_reference','event_validation','candidate_sequence_scoring_events'):
        combined[stage]={key:sum(p['counts'][stage][key] for p in plans) for key in ('planned_maximum','attempted','returned','terminal_unavailable')}
        combined[stage]['remaining_count_scenario']=[0,sum(p['counts'][stage]['remaining_count_scenario'][1] for p in plans)]
    return dict(basis='EXPLICIT_REQUESTED_FROZEN_EVENT_DIRECTORIES',plans=plans,counts=combined,
                note='Only supplied directories are included; no other event plan is implicitly requested.')


def fixed_workload(output):
    out=Path(output); plan=read_plan(out); expected={}; collection_path=out/'collection.json'
    if collection_path.exists():
        collection=sealed_read(collection_path); validate_collection(plan,collection)
        for row in collection['rows']:
            task=row['task']
            if task['arm']!='visible': continue
            # This saved catalog was produced by the original backend. Its
            # eligibility matches eligible_cuts; zero is the empty prefix.
            ks={c['k'] for c in row['boundaries']}
            if row['raw']['tokens']: ks.add(0)
            for k in plan['checkpoints']:
                if k not in ks: continue
                expected[f"replay/{task['id']}/{k}"]='unchanged_replay'
                cues=plan['config']['readout_cues'] if k in plan['config']['cue_check_checkpoints'] else plan['config']['readout_cues'][:1]
                for ci in range(len(cues)): expected[f"readout/{task['id']}/{k}/cue{ci}"]='candidate_sequence_scoring_fixed_2a'
    else:
        visible=sum(t['arm']=='visible' for t in plan['tasks'])
        cues=sum(len(plan['config']['readout_cues']) if k in plan['config']['cue_check_checkpoints'] else 1 for k in plan['checkpoints'])
        return dict(basis='CONDITIONAL_BEFORE_COLLECTION',counts={stage:dict(planned_maximum=n,remaining_count_scenario=[0,n]) for stage,n in [('unchanged_replay',visible*len(plan['checkpoints'])),('candidate_sequence_scoring_fixed_2a',3*visible*cues)]})
    ops={}
    for path in (out/'operations').glob('*.json'):
        op=sealed_read(path)
        if op['id'].startswith(('replay/','readout/')):
            if op['id'] not in expected or op['plan_hash']!=plan['plan_hash'] or op['backend_hash']!=collection['backend_hash']: raise ValueError('Fixed-2A operation binding changed')
            ops[op['id']]=op
    finished=(out/'measurements.json').exists()
    if finished:
        measured=sealed_read(out/'measurements.json')
        if measured['plan_hash']!=plan['plan_hash'] or measured['collection_hash']!=collection['artifact_hash'] or measured['backend_hash']!=collection['backend_hash']: raise ValueError('Fixed-2A measurements changed')
    counts={}
    for stage in ('unchanged_replay','candidate_sequence_scoring_fixed_2a'):
        weight=3 if stage.startswith('candidate_') else 1; ids=[k for k,v in expected.items() if v==stage]
        attempted=sum(k in ops for k in ids); returned=sum(k in ops and ops[k]['status']=='returned' for k in ids)
        counts[stage]=dict(planned_maximum=weight*len(ids),attempted=weight*attempted,returned=weight*returned,
                          terminal_unavailable=weight*(attempted-returned),
                          remaining_count_scenario=[0,0 if finished else weight*(len(ids)-attempted)],
                          gate_excluded=weight*(len(ids)-attempted) if finished else None)
    return dict(basis='SAVED_ORIGINAL_BOUNDARIES_AND_LEGACY_JOURNAL',completed=finished,counts=counts,
                logical_operations=dict(planned=len(expected),attempted=len(ops),returned=sum(o['status']=='returned' for o in ops.values()),terminal_unavailable=sum(o['status']!='returned' for o in ops.values())),
                note='Candidate journal counts are sequence ceilings per readout. Actual partial sequence calls are in fixed-2A telemetry. Failed/started legacy operations block automatic resume; completed legacy work may have no timing.')
