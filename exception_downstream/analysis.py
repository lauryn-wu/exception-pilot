"""Descriptive, paired world-level estimates for a selected source-response cohort."""
from __future__ import annotations

from collections import Counter
import csv
from itertools import combinations
import json
from pathlib import Path
import random

from exception_pilot.storage import accepted_records, write_json
from exception_study_support.runner import read_run
from . import core

COHORTS = ('contradiction', 'availability_control', 'genuine_missing_control', 'wrong_final_diagnostic')


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _percentile(values, q):
    index = (len(values) - 1) * q
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def bootstrap_ci(world_values, count=10000, seed=481602):
    if not world_values:
        return None
    rng = random.Random(seed)
    n = len(world_values)
    samples = sorted(sum(world_values[rng.randrange(n)] for _ in range(n)) / n for _ in range(count))
    return [_percentile(samples, .025), _percentile(samples, .975)]


def _metric(record, metric):
    if record is None or record['status'] != 'complete':
        return None
    return int(record['correct' if metric == 'accuracy' else 'false_missing'])


def _case_interval(tasks, records, metric):
    lower, upper = [], []
    for task in tasks:
        value = _metric(records.get(task['id']), metric)
        if value is None:
            lower.append(0)
            # A truly missing cell cannot produce a false claim of missingness.
            upper.append(0 if metric == 'false_missing' and task['expected'] == 'MISSING' else 1)
        else:
            lower.append(value)
            upper.append(value)
    return [_mean(lower), _mean(upper)]


def contrast(plan, records, cohort, left, right, metric):
    """A complete world requires all its cases and all repetitions in both arms."""
    cases = [c for c in plan['cases'] if c['cohort'] == cohort]
    tasks = {(c['id'], arm): [t for t in plan['tasks'] if t['case_id'] == c['id'] and t['arm'] == arm]
             for c in cases for arm in (left, right)}
    worlds = sorted({c['world_id'] for c in cases})
    complete = []
    all_lower, all_upper, rows = [], [], []
    for world in worlds:
        world_cases = [c for c in cases if c['world_id'] == world]
        deltas, lows, highs = [], [], []
        all_valid = True
        for case in world_cases:
            lt, rt = tasks[case['id'], left], tasks[case['id'], right]
            if len(lt) != plan['config']['repetitions'] or len(rt) != plan['config']['repetitions']:
                raise ValueError('Contrast is missing planned repetitions')
            lv = [_metric(records.get(t['id']), metric) for t in lt]
            rv = [_metric(records.get(t['id']), metric) for t in rt]
            valid = all(v is not None for v in lv + rv)
            all_valid &= valid
            if valid:
                deltas.append(_mean(lv) - _mean(rv))
            li, ri = _case_interval(lt, records, metric), _case_interval(rt, records, metric)
            lows.append(li[0] - ri[1]); highs.append(li[1] - ri[0])
        low, high = _mean(lows), _mean(highs)
        all_lower.append(low); all_upper.append(high)
        value = _mean(deltas) if all_valid else None
        if all_valid:
            complete.append(value)
        rows.append({'world_id': world, 'n_cases': len(world_cases), 'complete': all_valid,
                     'left_minus_right': value, 'full_plan_bounds': [low, high]})
    return {'cohort': cohort, 'metric': metric, 'left': left, 'right': right,
            'direction': 'left minus right', 'planned_worlds': len(worlds), 'complete_worlds': len(complete),
            'planned_cases': len(cases), 'estimate_complete_worlds': _mean(complete),
            'world_bootstrap_95_ci': bootstrap_ci(complete),
            'full_plan_bounds': [_mean(all_lower), _mean(all_upper)], 'worlds': rows}


def summarize(plan, attempts, execution):
    records = accepted_records(attempts)
    cells = []
    for cohort in COHORTS:
        arms = core.ARMS if cohort in ('contradiction', 'wrong_final_diagnostic') else ('original', 'endpoints_only')
        for arm in arms:
            tasks = [t for t in plan['tasks'] if t['cohort'] == cohort and t['arm'] == arm]
            returns = [records[t['id']] for t in tasks if t['id'] in records]
            valid = [r for r in returns if r['status'] == 'complete']
            cells.append({'cohort': cohort, 'arm': arm, 'planned': len(tasks), 'returned': len(returns),
                'valid': len(valid), 'invalid_retained': len(returns)-len(valid), 'pending': len(tasks)-len(returns),
                'correct': sum(r['correct'] for r in valid), 'false_missing': sum(r['false_missing'] for r in valid),
                'wrong_class': sum(r['wrong_class'] for r in valid),
                'answer_counts': dict(Counter(r['answer'] for r in valid)),
                'accuracy_valid_calls_only_descriptive': _mean(int(r['correct']) for r in valid)})
    comparisons = []
    for cohort in COHORTS:
        arms = core.ARMS if cohort in ('contradiction', 'wrong_final_diagnostic') else ('original', 'endpoints_only')
        for left, right in combinations(arms, 2):
            for metric in ('false_missing', 'accuracy'):
                comparisons.append(contrast(plan, records, cohort, left, right, metric))
    primary = next(c for c in comparisons if c['cohort']=='contradiction' and c['metric']=='false_missing'
                   and c['left']=='original' and c['right']=='availability_repair')
    valid_count = sum(r['status']=='complete' for r in records.values())
    complete = len(records) == len(plan['tasks'])
    simulated = execution is not None and execution['mode'] == 'mock'
    status = ('SIMULATED_' if simulated else '') + ('exploratory_complete' if complete else 'incomplete')
    return {'protocol_version': plan['protocol_version'], 'plan_hash': plan['plan_hash'],
            'analysis_status': status, 'is_simulated': simulated, 'planned_calls': len(plan['tasks']),
            'attempts_total': len(attempts), 'returned_answers': len(records), 'valid_answers': valid_count,
            'invalid_answers': len(records)-valid_count, 'pending': len(plan['tasks'])-len(records),
            'max_total_attempts': plan['config']['max_total_attempts'], 'cells': cells,
            'primary': primary, 'comparisons': comparisons,
            'notes': ['All comparisons except the named primary are secondary and unadjusted.',
                'Primary weights: average three repetitions within each case, then cases within each world, then equal weight each of nine worlds.',
                'Complete-world estimates require every planned case and repetition in both arms valid; other worlds remain in full-plan bounds.',
                'Bootstrap intervals describe selected observed worlds; nine worlds and outcome-selected historical traces do not establish population prevalence.',
                'A degenerate all-zero bootstrap interval is not evidence that the population effect is exactly zero.',
                'Availability controls have no reviewed false target-missingness claim; their other reasoning is not certified factual.',
                'Genuine-missing controls originate in a different feature-profile query and calibrate literal retrieval; do not pool cohorts.',
                'Temperature-zero repetitions measure possible endpoint variation and are not independent worlds.',
                'No significance threshold, success gate, or outcome-dependent expansion is applied.']}


def _csv(path, rows, fields):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)


def write_summary(output):
    output = Path(output)
    plan, execution, attempts = read_run(core, output)
    summary = summarize(plan, attempts, execution)
    records = accepted_records(attempts)
    response_rows = []
    for task in plan['tasks']:
        record = records.get(task['id'])
        row = core.task_meta(plan, task) | {'status': record['status'] if record else 'pending',
             'answer': record['answer'] if record else None, 'correct': record['correct'] if record else None,
             'false_missing': record['false_missing'] if record else None,
             'wrong_class': record['wrong_class'] if record else None,
             'text': record['response']['text'] if record else None}
        response_rows.append(row)
    (output/'responses.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False)+'\n' for r in response_rows))
    _csv(output/'responses.csv', response_rows, ['id','case_id','world_id','cohort','arm','repetition','expected','status','answer','correct','false_missing','wrong_class','text'])
    transitions = []
    for case in plan['cases']:
        arms = core.ARMS if case['spans'] else ('original','endpoints_only')
        for left, right in combinations(arms, 2):
            for repeat in range(1, plan['config']['repetitions']+1):
                lt = next(t for t in plan['tasks'] if t['case_id']==case['id'] and t['arm']==left and t['repetition']==repeat)
                rt = next(t for t in plan['tasks'] if t['case_id']==case['id'] and t['arm']==right and t['repetition']==repeat)
                lr, rr = records.get(lt['id']), records.get(rt['id'])
                transitions.append({'case_id':case['id'],'world_id':case['world_id'],'cohort':case['cohort'],
                    'repetition':repeat,'left':left,'right':right,'left_answer':lr['answer'] if lr else None,
                    'right_answer':rr['answer'] if rr else None,'left_status':lr['status'] if lr else 'pending',
                    'right_status':rr['status'] if rr else 'pending'})
    _csv(output/'paired-transitions.csv',transitions,['case_id','world_id','cohort','repetition','left','right','left_status','right_status','left_answer','right_answer'])
    world_rows = [{k:c[k] for k in ('cohort','metric','left','right')} | world
                  for c in summary['comparisons'] for world in c['worlds']]
    _csv(output/'world-contrasts.csv', world_rows, ['cohort','metric','left','right','world_id','n_cases','complete','left_minus_right','full_plan_bounds'])
    write_json(output/'summary.json', summary)
    lines = ['# Downstream factual follow-up', '', 'Status: '+summary['analysis_status']+'.',
             f"Returned {summary['returned_answers']}/{summary['planned_calls']}; valid {summary['valid_answers']}; invalid retained {summary['invalid_answers']}.", '',
             '| Cohort | Arm | Correct / valid | False MISSING | Invalid | Pending |',
             '|---|---|---:|---:|---:|---:|']
    for cell in summary['cells']:
        lines.append(f"| {cell['cohort']} | {cell['arm']} | {cell['correct']}/{cell['valid']} | {cell['false_missing']} | {cell['invalid_retained']} | {cell['pending']} |")
    p = summary['primary']
    lines += ['', 'Primary: original minus availability-repair false-MISSING rate.',
              f"Complete worlds: {p['complete_worlds']}/{p['planned_worlds']}; estimate: {p['estimate_complete_worlds']}; descriptive 95% world-bootstrap interval: {p['world_bootstrap_95_ci']}; full-plan bounds: {p['full_plan_bounds']}.", '',
              'All paired comparisons, their own complete-world denominators and bounds are in summary.json. Raw answers are in responses.jsonl; transitions are in paired-transitions.csv.', '']
    lines += ['- '+note for note in summary['notes']]
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    return summary
