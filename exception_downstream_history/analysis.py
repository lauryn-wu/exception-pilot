"""Descriptive, paired world-level analysis of the frozen history control."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

from exception_downstream.analysis import bootstrap_ci
from exception_pilot.storage import accepted_records, write_json
from exception_study_support.runner import read_run
from . import core

COHORTS = ('contradiction', 'availability_control', 'genuine_missing_control',
           'wrong_final_diagnostic')
METRICS = ('false_missing', 'accuracy')


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _metric(task, record, metric):
    if metric not in METRICS:
        raise ValueError('Unknown analysis metric')
    if record is None or record['status'] != 'complete':
        return None
    # Even a literal MISSING response cannot be false missingness when the
    # source table actually contains MISSING. Invalid responses remain unknown.
    if metric == 'false_missing' and task['expected'] == 'MISSING':
        return 0
    return int(record['correct' if metric == 'accuracy' else 'false_missing'])


def _case_interval(tasks, records, metric):
    lower, upper = [], []
    for task in tasks:
        value = _metric(task, records.get(task['id']), metric)
        lower.append(0 if value is None else value)
        upper.append((0 if metric == 'false_missing' and task['expected'] == 'MISSING' else 1)
                     if value is None else value)
    return [_mean(lower), _mean(upper)]


def contrast(plan, records, cohort, left, right, metric):
    """Average repetitions, then cases within world, then equally across worlds.

    Both arm rates use exactly the same complete-world membership as the delta.
    All planned cases/repetitions in BOTH arms must be valid for membership.
    Invalid and absent responses remain in the full-plan worst-case bounds.
    """
    if metric not in METRICS or left == right:
        raise ValueError('Invalid contrast')
    cases = [case for case in plan['cases'] if case['cohort'] == cohort]
    tasks = {(case['id'], arm): [task for task in plan['tasks']
                               if task['case_id'] == case['id'] and task['arm'] == arm]
             for case in cases for arm in (left, right)}
    expected_repetitions = set(range(1, plan['config']['repetitions'] + 1))
    for block in tasks.values():
        if (len(block) != len(expected_repetitions)
                or {task['repetition'] for task in block} != expected_repetitions):
            raise ValueError('Contrast is missing or duplicating planned repetitions')
    rows = []
    for world_id in sorted({case['world_id'] for case in cases}):
        world_cases = [case for case in cases if case['world_id'] == world_id]
        left_values, right_values = [], []
        left_intervals, right_intervals = [], []
        all_valid = True
        for case in world_cases:
            lt, rt = tasks[case['id'], left], tasks[case['id'], right]
            lv = [_metric(task, records.get(task['id']), metric) for task in lt]
            rv = [_metric(task, records.get(task['id']), metric) for task in rt]
            valid = all(value is not None for value in lv + rv)
            all_valid &= valid
            if valid:
                left_values.append(_mean(lv))
                right_values.append(_mean(rv))
            left_intervals.append(_case_interval(lt, records, metric))
            right_intervals.append(_case_interval(rt, records, metric))
        li = [_mean(interval[i] for interval in left_intervals) for i in (0, 1)]
        ri = [_mean(interval[i] for interval in right_intervals) for i in (0, 1)]
        left_rate = _mean(left_values) if all_valid else None
        right_rate = _mean(right_values) if all_valid else None
        rows.append({'world_id': world_id, 'n_cases': len(world_cases), 'complete': all_valid,
                     'left_rate': left_rate, 'right_rate': right_rate,
                     'left_minus_right': left_rate - right_rate if all_valid else None,
                     'left_full_plan_bounds': li, 'right_full_plan_bounds': ri,
                     'full_plan_bounds': [li[0] - ri[1], li[1] - ri[0]]})
    complete = [row for row in rows if row['complete']]
    deltas = [row['left_minus_right'] for row in complete]
    bootstrap = plan.get('analysis_plan', {})
    count = bootstrap.get('bootstrap_replicates', 10000)
    seed = bootstrap.get('bootstrap_seed', 481602)
    return {'cohort': cohort, 'metric': metric, 'left': left, 'right': right,
            'direction': 'left minus right', 'unit': 'world',
            'weighting': 'repetition mean, then case mean within world, then equal world mean',
            'planned_worlds': len(rows), 'complete_worlds': len(complete),
            'planned_cases': len(cases),
            'left_rate_complete_worlds': _mean(row['left_rate'] for row in complete),
            'right_rate_complete_worlds': _mean(row['right_rate'] for row in complete),
            'estimate_complete_worlds': _mean(deltas),
            'world_bootstrap_95_ci': bootstrap_ci(deltas, count=count, seed=seed),
            'left_full_plan_bounds': [_mean(row['left_full_plan_bounds'][i] for row in rows)
                                      for i in (0, 1)],
            'right_full_plan_bounds': [_mean(row['right_full_plan_bounds'][i] for row in rows)
                                       for i in (0, 1)],
            'full_plan_bounds': [_mean(row['full_plan_bounds'][i] for row in rows)
                                for i in (0, 1)], 'worlds': rows}


def _analysis_status(plan, attempts, records, execution):
    simulated = execution is not None and execution.get('mode') == 'mock'
    identity_failed = any(record.get('response', {}).get('model_identity') in ('missing', 'mismatch')
                          for record in records.values())
    if identity_failed:
        status = 'model_identity_failure'
    elif not attempts:
        status = 'not_started'
    elif len(records) < len(plan['tasks']):
        status = 'incomplete'
    elif any(record['status'] != 'complete' for record in records.values()):
        status = 'exploratory_complete_with_invalid'
    else:
        status = 'exploratory_complete'
    return ('SIMULATED_' if simulated else '') + status, simulated, identity_failed


def summarize(plan, attempts, execution):
    records = accepted_records(attempts)
    task_ids = {task['id'] for task in plan['tasks']}
    if len(task_ids) != len(plan['tasks']) or any(record_id not in task_ids for record_id in records):
        raise ValueError('Duplicate planned task or unplanned response')
    comparisons = [contrast(plan, records, cohort, 'history_present', 'history_absent', metric)
                   for cohort in COHORTS for metric in METRICS]
    indexed = {(comparison['cohort'], comparison['metric']): comparison
               for comparison in comparisons}
    cells = []
    for cohort in COHORTS:
        for arm in core.ARMS:
            tasks = [task for task in plan['tasks'] if task['cohort'] == cohort and task['arm'] == arm]
            returns = [records[task['id']] for task in tasks if task['id'] in records]
            valid = [record for record in returns if record['status'] == 'complete']
            false_missing = sum(_metric(task, records.get(task['id']), 'false_missing') or 0 for task in tasks)
            accuracy = indexed[cohort, 'accuracy']
            missing = indexed[cohort, 'false_missing']
            side = 'left' if arm == 'history_present' else 'right'
            counts = Counter(record['answer'] for record in valid)
            cells.append({'cohort': cohort, 'arm': arm, 'planned': len(tasks),
                          'returned': len(returns), 'valid': len(valid),
                          'invalid_retained': len(returns) - len(valid),
                          'pending': len(tasks) - len(returns),
                          'correct': sum(record['correct'] for record in valid),
                          'false_missing': false_missing,
                          'wrong_class': sum(record['wrong_class'] for record in valid),
                          'answer_counts': {label: counts[label] for label in core.LABELS},
                          'accuracy_valid_calls_only_descriptive': _mean(int(record['correct']) for record in valid),
                          'false_missing_rate_valid_calls_only_descriptive': false_missing / len(valid) if valid else None,
                          'paired_complete_worlds': accuracy['complete_worlds'],
                          'planned_worlds': accuracy['planned_worlds'],
                          'accuracy_world_weighted_paired_complete_worlds': accuracy[side + '_rate_complete_worlds'],
                          'false_missing_world_weighted_paired_complete_worlds': missing[side + '_rate_complete_worlds'],
                          'accuracy_full_plan_bounds': accuracy[side + '_full_plan_bounds'],
                          'false_missing_full_plan_bounds': missing[side + '_full_plan_bounds']})
    status, simulated, identity_failed = _analysis_status(plan, attempts, records, execution)
    valid_count = sum(record['status'] == 'complete' for record in records.values())
    return {'protocol_version': plan['protocol_version'], 'plan_hash': plan['plan_hash'],
            'analysis_status': status, 'is_simulated': simulated,
            'model_identity_failure': identity_failed,
            'planned_calls': len(plan['tasks']), 'attempts_total': len(attempts),
            'returned_answers': len(records), 'valid_answers': valid_count,
            'invalid_answers': len(records) - valid_count,
            'pending': len(plan['tasks']) - len(records),
            'transport_error_attempts': sum(attempt['status'] == 'error' for attempt in attempts),
            'unresolved_attempts': sum(attempt['status'] == 'started' for attempt in attempts),
            'max_total_attempts': plan['config']['max_total_attempts'],
            'cells': cells, 'primary': indexed['contradiction', 'false_missing'],
            'comparisons': comparisons,
            'notes': [
                'Primary: false-MISSING rate with history minus without history in the frozen contradiction cohort.',
                'All other cohort and accuracy comparisons are secondary and unadjusted; cohorts are never pooled.',
                'Weights: mean repetitions within case, mean cases within world, then equal world weight. Calls and cases are not independent worlds.',
                'Arm rates and deltas use the same paired complete-world membership: every planned case and repetition in both arms must be valid.',
                'Invalid and absent responses are unknown, retained in full-plan worst-case bounds, and never silently scored incorrect.',
                'A truly MISSING cell has false-missingness bounded at zero even when its response is invalid; its accuracy remains unknown.',
                'The 95% bootstrap intervals resample worlds and are descriptive for these selected historical cases; they do not estimate semantic missingness prevalence or population effects.',
                'Three temperature-zero repetitions can expose endpoint variation but do not create independent cases or worlds.',
                'Both arms contain fresh follow-up calls. Historical follow-up answers are not imported into this comparison; source classification responses are frozen.',
                'History removal removes the classification question, its output instructions and assistant response, and changes conversation length and turn structure. The contrast concerns that entire history package, not the explanation alone.',
                'Similar observed arm rates or an interval containing zero do not establish equivalence or absence of a history effect; no equivalence margin is specified.',
                'A degenerate bootstrap interval, especially for a single-world diagnostic, does not show an exactly known population effect.',
                'Availability controls have reviewed absence of a false target-missingness claim, not certified factual reasoning throughout.',
                'Genuine-missing controls use a different historical feature-profile query and provide separate calibration, not a matched missingness counterfactual.',
                'No significance threshold, success gate, or outcome-dependent expansion is applied.',
            ]}


def _csv(path, rows, fields):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def write_summary(output):
    output = Path(output)
    plan, execution, attempts = read_run(core, output)
    summary = summarize(plan, attempts, execution)
    records = accepted_records(attempts)
    latest = {attempt['task_id']: attempt for attempt in attempts}
    response_rows = []
    for task in plan['tasks']:
        record = records.get(task['id'])
        attempt = latest.get(task['id'])
        response = record.get('response', {}) if record else {}
        response_rows.append(core.task_meta(plan, task) | {
            'status': attempt['status'] if attempt else 'not_started',
            'answer': record['answer'] if record else None,
            'correct': record['correct'] if record else None,
            'false_missing': record['false_missing'] if record else None,
            'wrong_class': record['wrong_class'] if record else None,
            'model_identity': response.get('model_identity'),
            'finish_reason': response.get('finish_reason'),
            'text': response.get('text'),
        })
    (output / 'responses.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in response_rows),
        encoding='utf-8')
    _csv(output / 'responses.csv', response_rows,
         ['id', 'case_id', 'world_id', 'cohort', 'arm', 'repetition', 'expected', 'status',
          'answer', 'correct', 'false_missing', 'wrong_class', 'model_identity', 'finish_reason', 'text'])
    by_pair = {(task['case_id'], task['arm'], task['repetition']): task for task in plan['tasks']}
    transitions = []
    for case in plan['cases']:
        for repetition in range(1, plan['config']['repetitions'] + 1):
            row = {'case_id': case['id'], 'world_id': case['world_id'], 'cohort': case['cohort'],
                   'repetition': repetition, 'expected': case['expected'],
                   'left': 'history_present', 'right': 'history_absent'}
            for side, arm in (('left', 'history_present'), ('right', 'history_absent')):
                task = by_pair[case['id'], arm, repetition]
                record = records.get(task['id'])
                attempt = latest.get(task['id'])
                row[side + '_status'] = attempt['status'] if attempt else 'not_started'
                row[side + '_answer'] = record['answer'] if record else None
            row['both_valid'] = row['left_status'] == row['right_status'] == 'complete'
            transitions.append(row)
    _csv(output / 'paired-transitions.csv', transitions,
         ['case_id', 'world_id', 'cohort', 'repetition', 'expected', 'left', 'right',
          'left_status', 'right_status', 'left_answer', 'right_answer', 'both_valid'])
    world_rows = [{key: comparison[key] for key in ('cohort', 'metric', 'left', 'right')} | world
                  for comparison in summary['comparisons'] for world in comparison['worlds']]
    _csv(output / 'world-contrasts.csv', world_rows,
         ['cohort', 'metric', 'left', 'right', 'world_id', 'n_cases', 'complete',
          'left_rate', 'right_rate', 'left_minus_right', 'left_full_plan_bounds',
          'right_full_plan_bounds', 'full_plan_bounds'])
    write_json(output / 'summary.json', summary)
    lines = ['# Downstream history control', '', 'Status: ' + summary['analysis_status'] + '.',
             f"Returned {summary['returned_answers']}/{summary['planned_calls']}; valid {summary['valid_answers']}; invalid retained {summary['invalid_answers']}; pending {summary['pending']}.", '',
             'Counts below describe calls; the paired estimates weight worlds equally.', '',
             '| Cohort | Arm | Correct / valid | False MISSING / valid | Invalid | Pending |',
             '|---|---|---:|---:|---:|---:|']
    for cell in summary['cells']:
        lines.append(f"| {cell['cohort']} | {cell['arm']} | {cell['correct']}/{cell['valid']} | {cell['false_missing']}/{cell['valid']} | {cell['invalid_retained']} | {cell['pending']} |")
    primary = summary['primary']
    lines += ['', 'Primary: history-present minus history-absent false-MISSING rate in the contradiction cohort.',
              f"Paired complete worlds: {primary['complete_worlds']}/{primary['planned_worlds']}.",
              f"World-weighted rates on those same worlds: history-present {primary['left_rate_complete_worlds']}; history-absent {primary['right_rate_complete_worlds']}.",
              f"Difference: {primary['estimate_complete_worlds']}; descriptive 95% world-bootstrap interval: {primary['world_bootstrap_95_ci']}; full-plan difference bounds: {primary['full_plan_bounds']}.", '',
              'All secondary contrasts, arm rates, complete-world denominators and full-plan bounds are in summary.json and world-contrasts.csv. Responses are in responses.jsonl and responses.csv; paired responses are in paired-transitions.csv.', '']
    lines += ['- ' + note for note in summary['notes']]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary
