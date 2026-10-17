"""All twelve denominators; prior results stay separate from child measurements."""
import json
from collections import Counter
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from . import LIMITATION
from .execution import state
from .parser import parse_reply


def summary(rows):
    counts=Counter(r['operation_status'] for r in rows)
    returned=[r for r in rows if r['score'] is not None];correct=sum(r['score']['correct'] for r in returned)
    return dict(planned=len(rows),**{s:counts[s] for s in ('returned','never_started','failed','ambiguous')},
        correct=correct,correct_per_returned=dict(numerator=correct,denominator=len(returned)),
        successful_per_planned=dict(numerator=correct,denominator=len(rows)),
        returned_unsuccessful=len(returned)-correct,unavailable=len(rows)-len(returned))


def report(c,saved,mode,stats):
    rows=[];prior={x['query']['id']:x for x in c.parent.cases}
    for q in c.plan['queries']:
        op=saved.get(q['id']);raw=op.get('result') if state(op)=='returned' else None
        score=parse_reply(raw,q['expected'],c.tokenizer) if state(op)=='returned' else None
        p=prior[q['origin_query_id']]
        rows.append(dict(operation_id=q['id'],**{k:q[k] for k in ('origin_query_id','origin_query_hash','task_id','world','variant','target_plate','kind','expected','context_hash')},
            operation_status=state(op),raw=raw,score=score,
            prior_v2=dict(interface=c.parent.plan['interface_version'],parser=c.parent.plan['parser_version'],
                operation_hash=p['operation']['artifact_hash'],raw=p['operation']['result'],frozen_score=p['score'],
                note='Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control.')))
    counts=summary(rows);done=counts['returned']==12;pending=counts['never_started'];bad=counts['returned_unsuccessful']+counts['failed']+counts['ambiguous']
    criterion='PASSED' if done and counts['correct']==12 else 'FAILED' if bad else 'PENDING'
    finished=[sealed_read(p) for p in sorted((c.out/'invocations').glob('*/finished.json'))]
    unfinished=len(list((c.out/'invocations').glob('*/started.json')))-len(finished)
    events=[sealed_read(p) for p in sorted((c.out/'timing-pilot/events').glob('*.json'))]
    generations=[e for e in events if e.get('stage')=='source_user_pilot_generation']
    return dict(protocol=c.plan['version'],plan_hash=c.plan['artifact_hash'],code_contract=c.plan['code_contract'],
        measurement_mode=mode,live_pilot_results_obtained=mode=='LIVE_LOCAL' and counts['returned']>0,
        parent_v2_calibration_gate='FAILED',prior_v1_gate='FAILED',prior_v2=dict(returned=12,present_correct=8,missing_correct=0,main_started=0),
        new_pilot_criterion=dict(status=criterion,rule=c.plan['criterion'],correct=counts['correct'],required=12),
        inventory=c.plan['inventory'],main_planned=0,main_eligible=False,
        collection_status='COMPLETE' if done else 'INCOMPLETE',counts=counts,
        source_present=summary([r for r in rows if r['kind']=='calibration_present']),
        literal_missing=summary([r for r in rows if r['kind']=='calibration_missing']),
        present_label_variant_pairs={w:[r for r in rows if r['world']==w and r['kind']=='calibration_present'] for w in sorted({r['world'] for r in rows})},
        cases=rows,unresolved_operations=[r['operation_id'] for r in rows if r['operation_status']!='returned'],
        executable_now=pending,this_invocation=stats,
        cumulative_new_dispatches=sum(state(o) in ('returned','failed','ambiguous') for o in saved.values()),
        cumulative_backend_loads=sum(f['model_loads'] for f in finished),cumulative_load_accounting_complete=unfinished==0,
        timing=dict(finished_invocations=len(finished),unfinished_invocations=unfinished,
            generation_events=len(generations),generation_seconds=sum(e.get('elapsed_seconds',0) for e in generations),
            note='Finished-invocation load totals are lower bounds if an invocation was interrupted.'),
        backend_hash=c.plan['backend_hash'],backend_requirements=c.plan['backend'],generation_settings=c.plan['generation_settings'],
        interpretation=LIMITATION,next_stage='STOP_AFTER_PILOT' if done else 'INCOMPLETE_NO_MAIN')


def human(value):
    lines=['# New-user-turn source-transcription pilot','',
        f"Mode: {value['measurement_mode']}; collection: {value['collection_status']}; criterion: {value['new_pilot_criterion']['status']}.",
        'Parent v2: FAILED (8/8 present correct; 0/4 MISSING correct). V1 remains FAILED.',
        'Main planned: 0. Main eligible: false.',
        'Counts: '+json.dumps(value['counts']),
        'Source-present: '+json.dumps(value['source_present']),
        'Literal-MISSING: '+json.dumps(value['literal_missing']),
        'This invocation: '+json.dumps(value['this_invocation']),
        'Timing: '+json.dumps(value['timing']),'',value['interpretation'],'']
    for r in value['cases']:
        lines += [f"## {r['world']} v{r['variant']} {r['kind']}",
            f"Source: {r['task_id']}; plate: {r['target_plate']}; expected: {r['expected']}.",
            f"Parent query: {r['origin_query_id']}; child: {r['operation_id']}.",
            f"Status: {r['operation_status']}",'Child raw payload (complete):',json.dumps(r['raw'],ensure_ascii=False),
            'Child score:',json.dumps(r['score'],ensure_ascii=False),'Prior v2 raw + frozen score (different interface/parser):',
            json.dumps(r['prior_v2'],ensure_ascii=False),'']
    lines += [value['next_stage'], 'Review all twelve replies before any separately specified larger experiment.','']
    return '\n'.join(lines)


def save_report(c,value):
    import os
    from tempfile import NamedTemporaryFile
    write_json(c.out/'report.json',value)
    with NamedTemporaryFile('w',dir=c.out,delete=False,suffix='.tmp') as stream:
        stream.write(human(value));stream.flush();os.fsync(stream.fileno());name=stream.name
    os.replace(name,c.out/'report.md')
    return value
