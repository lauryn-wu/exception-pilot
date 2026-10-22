"""Deterministic final-channel accounting; unavailable cells never become wrong votes."""
from collections import Counter, defaultdict
from statistics import mean
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_study2_native.recovery import state, summary as recovery_summary
from exception_study2_native.diagnostics import repetition, distribution, DEFINITION
from exception_study2_source_report.reporting import WorldBootstrap
from . import VERSION, STOP
from .adapter import parse_result


def cases(c,current):
    result=[]
    for r in c.requests:
        op=current.get(r['cell']['id']);status=state(op);raw=op['result'] if status=='returned' else None
        score=parse_result(raw,r['request'],c.tok) if status=='returned' else None
        result.append(dict(cell=r['cell'],request_hash=r['request_hash'],operation_status=status,
            operation_hash=op['artifact_hash'] if op else None,score=score,raw=raw,
            repetition=repetition(raw,c.tok) if status=='returned' else None))
    return result


def summarize(rows):
    returned=[x for x in rows if x['score'] is not None];n=len(rows)
    correct=sum(x['score']['correct'] for x in returned)
    wrong=[x for x in returned if x['score']['valid'] and not x['score']['correct']]
    pattern=sum(x['cell']['relation']=='conflict' and x['score']['answer']==x['cell']['pattern'] for x in wrong)
    return dict(planned=n,returned=len(returned),unavailable=n-len(returned),correct=correct,
        accuracy_all_planned=correct/n if n and len(returned)==n else None,
        accuracy_bounds=[correct/n,(correct+n-len(returned))/n] if n else None,
        valid_wrong_labels=len(wrong),conflict_pattern_choices=pattern,other_wrong_labels=len(wrong)-pattern,
        invalid_final=sum(not x['score']['valid'] and not x['score']['truncated'] for x in returned),
        malformed=sum(x['score']['malformed'] for x in returned),
        truncated=sum(x['score']['truncated'] for x in returned),missing_final=sum(x['score']['missing_final'] for x in returned),
        tokens={k:distribution([x['score'][k] for x in returned]) for k in ('token_count','thinking_tokens','final_tokens')},
        generation_seconds=distribution([x['raw'].get('elapsed_seconds') for x in returned if isinstance(x['raw'],dict)]),
        repeated_window_fraction=distribution([x['repetition']['repeated_window_fraction'] for x in returned if x['repetition']]))


def contrasts(rows,wording):
    selected=[x for x in rows if x['cell']['wording']==wording];worlds=defaultdict(list)
    for x in selected:worlds[x['cell']['world']].append(x)
    missing=sum(x['score'] is None for x in selected)
    result=dict(wording=wording,role='primary' if wording=='original' else 'secondary',planned=192,
        unavailable=missing,estimable=bool(selected) and missing==0,
        definition='(on support - on conflict) - (off support - off conflict); positive means increased conflict penalty',
        construction_clusters=4,worlds=24,interpretation='Exploratory. Four shared construction families, not 24 independent construction families.')
    if not result['estimable']:return dict(result,estimate=None,block_interval_95=None,world_sensitivity=None)
    values=[];world_values=[];per_world={}
    for world,xs in sorted(worlds.items()):
        means={}
        for on in (False,True):
            for relation in ('support','conflict'):
                pair=[x for x in xs if x['cell']['thinking']==on and x['cell']['relation']==relation]
                if len(pair)!=2 or {x['cell']['variant'] for x in pair}!={0,1}:raise ValueError('Incomplete paired world')
                means[on,relation]=mean(int(x['score']['correct']) for x in pair)
        value=means[True,'support']-means[True,'conflict']-means[False,'support']+means[False,'conflict']
        values.append((xs[0]['cell']['block'],value));world_values.append((world,value));per_world[world]=value
    block=WorldBootstrap(range(4)).estimate(values);world=WorldBootstrap(sorted(worlds)).estimate(world_values)
    block.update(unit='construction_block',observed_clusters=block.pop('observed_worlds'),planned_clusters=block.pop('planned_worlds'),
        method='Resample four shared construction blocks, retaining six worlds and both target variants in each; mean of paired world contrasts.')
    return dict(result,estimate=block['estimate'],block_interval_95=block['interval_95'],block_bootstrap=block,
        world_sensitivity=dict(world,label='Descriptive 24-world sensitivity; ignores shared count-family dependence'),world_contrasts=per_world)


def technical(rows,c):
    checks=[]
    for x in rows:
        r=c.by_cell[x['cell']['id']]['request'];s=x['score'];raw=x['raw'];prefix=r.get('prefix_token_ids',[])
        prefix_check=None
        if prefix:
            source_id=x['cell']['id'].removesuffix('/saved-prefix')
            source=next(z for z in rows if z['cell']['id']==source_id)
            base=c.by_cell[source_id]['request']
            prefix_check=(r['input_ids']==base['input_ids']+source['raw']['tokens'][:len(prefix)] and
                prefix==source['raw']['tokens'][:len(prefix)] and r['prefix_source']['operation_hash']==source['operation_hash'])
        passed=bool(s and s['valid'] and raw.get('input_ids_verified') is True and (prefix_check is not False))
        checks.append(dict(cell=x['cell']['id'],passed=passed,exact_supplied_prefix=prefix_check,
            channel_status=s['parsing_status'] if s else 'unavailable'))
    return dict(passed=len(rows)==8 and all(x['passed'] for x in checks),checks=checks,
        interpretation='Checks input-prefix preservation, channels, EOS and token/text identity. Sampled continuations need not match an uninterrupted suffix; no distribution-equivalence or scientific accuracy claim.')


def report(c,current,invocation):
    rows=cases(c,current);planned=c.plan['planned_responses'];counts=Counter(x['operation_status'] for x in rows)
    blocked=planned-len(rows);counts['dependency_blocked']=blocked
    totals={k:counts[k] for k in ('returned','failed','ambiguous','never_started','dependency_blocked')}
    totals.update(planned=planned,remaining=planned-counts['returned'],executable_never_started=counts['never_started'])
    finished=[sealed_read(p) for p in sorted((c.out/'invocations').glob('*/finished.json'))]
    starts=list((c.out/'invocations').glob('*/started.json'))
    totals.update(model_loads=sum(x.get('model_loads',0) for x in finished),
        model_load_attempts=sum(x.get('model_load_attempts',0) for x in finished),
        completed_invocation_seconds=sum(x.get('elapsed_seconds',0) for x in finished),
        unresolved_invocations=len(starts)-len(finished),
        dispatched=len(list((c.out/'dispatches').glob('*.json'))),
        returned_input_tokens=sum(len(c.by_cell[x['cell']['id']]['request']['input_ids']) for x in rows if x['score']),
        returned_output_tokens=sum(x['score']['token_count'] or 0 for x in rows if x['score']))
    ex=c.out/'execution.json';mode=sealed_read(ex)['measurement_mode'] if ex.exists() else 'UNEXECUTED'
    recovery=recovery_summary(c);recovery['action']='inspect is read-only; recover only quarantines recognized debris. Failed/ambiguous calls remain held. No automatic resend or replacement. Preserve the run for explicit forensic review.'
    groups={}
    if c.plan['kind']=='screen':
        for word in ('original','lookup'):
            for variant in (0,1):
                for on in (False,True):
                    for relation in ('support','conflict'):
                        subset=[x for x in rows if x['cell']['wording']==word and x['cell']['variant']==variant and x['cell']['thinking']==on and x['cell']['relation']==relation]
                        groups[f'{word}/v{variant}/thinking-{int(on)}/{relation}']=summarize(subset)
    smoke=technical(rows,c) if c.plan['kind']=='smoke' else None
    return dict(protocol=VERSION,kind=c.plan['kind'],plan_hash=c.plan['artifact_hash'],measurement_mode=mode,
        totals=totals,this_invocation=invocation,summary=summarize(rows),factorial_cells=groups,
        primary=contrasts(rows,'original') if groups else None,lookup=contrasts(rows,'lookup') if groups else None,
        technical_passed=smoke['passed'] if smoke else None,technical=smoke,
        memory=dict(peak_process_allocated_bytes=max((x['raw'].get('peak_process_allocated_bytes',0) for x in rows if isinstance(x['raw'],dict)),default=0),
            maximum_observed_device_used_bytes=max((x['raw'].get('gpu_memory_used_bytes',0) for x in rows if isinstance(x['raw'],dict)),default=0),
            note='Process allocator statistics may omit vLLM worker allocations; device-used snapshots include other processes and are not a continuous peak.'),
        repetition_definition=DEFINITION,recovery=recovery,cases=rows,stop=STOP,
        accounting='Invalid and truncated returns count as unsuccessful in the fixed-budget outcome. Unavailable cells are not incorrect: accuracy and contrasts remain undefined until complete, with bounds shown. Valid wrong labels are separate from truncation. In support cells recorded and pattern labels coincide; the route cannot be inferred.')


def save_report(c,current,invocation):
    value=report(c,current,invocation);write_json(c.out/'analysis.json',value)
    lines=['# Current Qwen native-thinking screen', '',f"Measurement: {value['measurement_mode']}. {value['totals']['returned']}/{value['totals']['planned']} returned.",
        '',value['accounting'],'',f"Technical smoke passed: {value['technical_passed']}",
        '', '| Cell | Returned / planned | Correct | Pattern errors | Other wrong | Invalid | Truncated |', '|---|---:|---:|---:|---:|---:|---:|']
    for name,s in value['factorial_cells'].items():
        lines.append(f"| {name} | {s['returned']}/{s['planned']} | {s['correct']} | {s['conflict_pattern_choices']} | {s['other_wrong_labels']} | {s['invalid_final']} | {s['truncated']} |")
    for name in ('primary','lookup'):
        x=value[name]
        if x:lines+=['',f"{name}: estimate={x['estimate']}; 95% construction-block interval={x['block_interval_95']}. {x['interpretation']}"]
    lines+=['',value['recovery']['action'],'',STOP,'']
    # Derived reports can be regenerated; immutable journals remain authoritative.
    from tempfile import NamedTemporaryFile
    import os
    with NamedTemporaryFile('w',dir=c.out,delete=False) as f:
        f.write('\n'.join(lines));f.flush();os.fsync(f.fileno());name=f.name
    os.replace(name,c.out/'analysis.md')
    return value
