"""Paired world-level analysis of the frozen history by prediction-rule control."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

from exception_downstream.analysis import bootstrap_ci
from exception_downstream_history.analysis import (
    _analysis_status, _case_interval, _mean, _metric, contrast as _history_contrast,
)
from exception_pilot.storage import accepted_records, write_json
from exception_study_support.runner import read_run
from . import core

COHORTS = ('contradiction', 'availability_control', 'genuine_missing_control',
           'wrong_final_diagnostic')
METRICS = ('false_missing', 'accuracy')
PAIR_CONTRASTS = {
    'rule_effect_without_history': ('history_absent_rule_absent', 'history_absent_rule_present'),
    'rule_effect_with_history': ('history_present_rule_absent', 'history_present_rule_present'),
    'history_effect_rule_present': ('history_present_rule_present', 'history_absent_rule_present'),
    'history_effect_rule_absent': ('history_present_rule_absent', 'history_absent_rule_absent'),
}
INTERACTION_ID = 'history_by_rule_interaction'
INTERACTION_WEIGHTS = {
    'history_present_rule_present': 1,
    'history_absent_rule_present': -1,
    'history_present_rule_absent': -1,
    'history_absent_rule_absent': 1,
}


def contrast(plan, records, cohort, left, right, metric):
    """Reuse the validated pairwise estimator with this study's bootstrap seed."""
    analysis_plan = {'bootstrap_replicates': 10000, 'bootstrap_seed': 481603,
                     **plan.get('analysis_plan', {})}
    return _history_contrast({**plan, 'analysis_plan': analysis_plan}, records,
                             cohort, left, right, metric)


def interaction(plan, records, cohort, metric):
    """Compute the difference in history effects on the same four-arm worlds.

    The bootstrap resamples actual four-arm world differences. Its input is
    never a subtraction of pairwise estimates with different world membership.
    Unknown outcomes remain in sign-aware full-plan bounds.
    """
    if metric not in METRICS:
        raise ValueError('Unknown analysis metric')
    cases = [case for case in plan['cases'] if case['cohort'] == cohort]
    tasks = {(case['id'], arm): [task for task in plan['tasks']
                               if task['case_id'] == case['id'] and task['arm'] == arm]
             for case in cases for arm in core.ARMS}
    expected_repetitions = set(range(1, plan['config']['repetitions'] + 1))
    for block in tasks.values():
        if (len(block) != len(expected_repetitions)
                or {task['repetition'] for task in block} != expected_repetitions):
            raise ValueError('Interaction is missing or duplicating planned repetitions')
    rows = []
    for world_id in sorted({case['world_id'] for case in cases}):
        world_cases = [case for case in cases if case['world_id'] == world_id]
        case_means = {arm: [] for arm in core.ARMS}
        case_bounds = {arm: [] for arm in core.ARMS}
        all_valid = True
        for case in world_cases:
            for arm in core.ARMS:
                block = tasks[case['id'], arm]
                values = [_metric(task, records.get(task['id']), metric) for task in block]
                valid = all(value is not None for value in values)
                all_valid &= valid
                case_means[arm].append(_mean(values) if valid else None)
                case_bounds[arm].append(_case_interval(block, records, metric))
        arm_rates = {arm: _mean(case_means[arm]) if all_valid else None for arm in core.ARMS}
        arm_bounds = {arm: [_mean(bounds[i] for bounds in case_bounds[arm]) for i in (0, 1)]
                      for arm in core.ARMS}
        estimate = (sum(INTERACTION_WEIGHTS[arm] * arm_rates[arm] for arm in core.ARMS)
                    if all_valid else None)
        lower = sum(weight * arm_bounds[arm][0 if weight > 0 else 1]
                    for arm, weight in INTERACTION_WEIGHTS.items())
        upper = sum(weight * arm_bounds[arm][1 if weight > 0 else 0]
                    for arm, weight in INTERACTION_WEIGHTS.items())
        rows.append({'world_id': world_id, 'n_cases': len(world_cases), 'complete': all_valid,
                     'arm_rates': arm_rates, 'estimate': estimate,
                     'arm_full_plan_bounds': arm_bounds, 'full_plan_bounds': [lower, upper]})
    complete = [row for row in rows if row['complete']]
    deltas = [row['estimate'] for row in complete]
    bootstrap = plan.get('analysis_plan', {})
    return {
        'contrast_id': INTERACTION_ID, 'contrast_type': 'interaction',
        'cohort': cohort, 'metric': metric,
        'weights': dict(INTERACTION_WEIGHTS),
        'direction': '(history_present_rule_present - history_absent_rule_present) - '
                     '(history_present_rule_absent - history_absent_rule_absent)',
        'positive_means': 'Prediction-rule presence increases the history effect on this metric.',
        'unit': 'world',
        'weighting': 'repetition mean, then case mean within world, then equal world mean',
        'planned_worlds': len(rows), 'complete_worlds': len(complete),
        'planned_cases': len(cases),
        'arm_rates_complete_worlds': {arm: _mean(row['arm_rates'][arm] for row in complete)
                                     for arm in core.ARMS},
        'estimate_complete_worlds': _mean(deltas),
        'world_bootstrap_95_ci': bootstrap_ci(
            deltas, count=bootstrap.get('bootstrap_replicates', 10000),
            seed=bootstrap.get('bootstrap_seed', 481603)),
        'arm_full_plan_bounds': {
            arm: [_mean(row['arm_full_plan_bounds'][arm][i] for row in rows) for i in (0, 1)]
            for arm in core.ARMS},
        'full_plan_bounds': [_mean(row['full_plan_bounds'][i] for row in rows) for i in (0, 1)],
        'worlds': rows,
    }


def summarize(plan, attempts, execution):
    records = accepted_records(attempts)
    task_ids = {task['id'] for task in plan['tasks']}
    if len(task_ids) != len(plan['tasks']) or any(record_id not in task_ids for record_id in records):
        raise ValueError('Duplicate planned task or unplanned response')
    comparisons = []
    for cohort in COHORTS:
        for metric in METRICS:
            for contrast_id, (left, right) in PAIR_CONTRASTS.items():
                comparison = contrast(plan, records, cohort, left, right, metric)
                comparison.update({'contrast_id': contrast_id, 'contrast_type': 'pair'})
                comparisons.append(comparison)
            comparisons.append(interaction(plan, records, cohort, metric))
    indexed = {(comparison['cohort'], comparison['metric'], comparison['contrast_id']): comparison
               for comparison in comparisons}
    cells = []
    for cohort in COHORTS:
        accuracy = indexed[cohort, 'accuracy', INTERACTION_ID]
        missing = indexed[cohort, 'false_missing', INTERACTION_ID]
        for arm in core.ARMS:
            tasks = [task for task in plan['tasks'] if task['cohort'] == cohort and task['arm'] == arm]
            returns = [records[task['id']] for task in tasks if task['id'] in records]
            valid = [record for record in returns if record['status'] == 'complete']
            false_missing = sum(_metric(task, records.get(task['id']), 'false_missing') or 0
                                for task in tasks)
            counts = Counter(record['answer'] for record in valid)
            cells.append({
                'cohort': cohort, 'arm': arm, **core.ARM_FACTORS[arm],
                'planned': len(tasks), 'returned': len(returns), 'valid': len(valid),
                'invalid_retained': len(returns) - len(valid), 'pending': len(tasks) - len(returns),
                'correct': sum(record['correct'] for record in valid), 'false_missing': false_missing,
                'wrong_class': sum(record['wrong_class'] for record in valid),
                'answer_counts': {label: counts[label] for label in core.LABELS},
                'accuracy_valid_calls_only_descriptive': _mean(int(record['correct']) for record in valid),
                'false_missing_rate_valid_calls_only_descriptive': false_missing / len(valid) if valid else None,
                'four_arm_complete_worlds': accuracy['complete_worlds'],
                'planned_worlds': accuracy['planned_worlds'],
                'accuracy_world_weighted_four_arm_complete_worlds': accuracy['arm_rates_complete_worlds'][arm],
                'false_missing_world_weighted_four_arm_complete_worlds': missing['arm_rates_complete_worlds'][arm],
                'accuracy_full_plan_bounds': accuracy['arm_full_plan_bounds'][arm],
                'false_missing_full_plan_bounds': missing['arm_full_plan_bounds'][arm],
            })
    status, simulated, identity_failed = _analysis_status(plan, attempts, records, execution)
    valid_count = sum(record['status'] == 'complete' for record in records.values())
    return {
        'protocol_version': plan['protocol_version'], 'plan_hash': plan['plan_hash'],
        'analysis_status': status, 'is_simulated': simulated,
        'model_identity_failure': identity_failed,
        'planned_calls': len(plan['tasks']), 'attempts_total': len(attempts),
        'returned_answers': len(records), 'valid_answers': valid_count,
        'invalid_answers': len(records) - valid_count,
        'pending': len(plan['tasks']) - len(records),
        'transport_error_attempts': sum(attempt['status'] == 'error' for attempt in attempts),
        'unresolved_attempts': sum(attempt['status'] == 'started' for attempt in attempts),
        'max_total_attempts': plan['config']['max_total_attempts'],
        'cells': cells,
        'primary': indexed['genuine_missing_control', 'accuracy', 'rule_effect_without_history'],
        'comparisons': comparisons,
        'notes': [
            'Primary: accuracy after prediction-rule removal minus accuracy with the rule retained, without history, in the frozen genuine-missing cohort.',
            'The primary outcome uses the literal table cell as the answer key: a genuinely MISSING cell is correct only when the factual answer is MISSING.',
            'All other cohort, metric and interaction comparisons are secondary and unadjusted; cohorts are never pooled.',
            'This control was designed after observing the earlier history-control results. It is a prospective follow-up on the same selected historical cases, not independent case replication.',
            'Weights: mean repetitions within case, mean cases within world, then equal world weight. Calls and cases are not independent worlds.',
            'Each pairwise estimate uses every planned case and repetition in both arms on its own complete-world set. Both reported arm rates use that exact same set.',
            'The interaction requires all four arms, cases and repetitions to be valid within a world. It bootstraps the actual four-arm world differences; it does not subtract pairwise confidence intervals or unmatched world estimates.',
            'Cell-level world-weighted rates use the common four-arm complete-world set. Raw cell counts use valid calls in that cell and may have different denominators.',
            'Invalid and absent responses are unknown, retained in sign-aware full-plan worst-case bounds, and never silently scored incorrect.',
            'A truly MISSING cell has false-missingness bounded at zero even when its response is invalid; its accuracy remains unknown.',
            'The 95% bootstrap intervals resample worlds and are descriptive for these selected historical cases. They do not estimate semantic missingness prevalence or population effects.',
            'Three temperature-zero repetitions can expose endpoint variation but do not create independent cases or worlds.',
            'All four arms contain fresh follow-up calls. Earlier follow-up outcomes are not imported; the saved original classification response is fixed and replayed unchanged wherever history is present.',
            'Rule removal deletes only the specified prediction sentence from the original user introduction. It does not regenerate or edit the saved assistant response, even if that response contains prediction language.',
            'The rule contrast therefore measures the effect of editing that user instruction conditional on the fixed historical response. It does not measure how the rule would change a newly generated classification response.',
            'History removal removes the classification question, output instructions and assistant response, and changes conversation length and turn structure. Its effect concerns the entire history package, not the explanation alone.',
            'The rule-absent introduction still defines MISSING, and the follow-up still offers MISSING as an answer. No condition is claimed to be a neutral retrieval baseline or a measure of latent belief.',
            'Similar observed rates or an interval containing zero do not establish equivalence or absence of an effect; no equivalence margin is specified.',
            'A degenerate bootstrap interval, especially for a single-world diagnostic, does not show an exactly known population effect.',
            'Availability controls have reviewed absence of a false target-missingness claim, not certified factual reasoning throughout.',
            'Genuine-missing controls use a different historical feature-profile query and provide separate calibration, not a matched missingness counterfactual.',
            'No significance threshold, scientific success gate, or outcome-dependent expansion is applied.',
        ],
    }


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
        response_rows.append(core.task_meta(plan, task) | core.ARM_FACTORS[task['arm']] | {
            'status': attempt['status'] if attempt else 'not_started',
            'answer': record['answer'] if record else None,
            'correct': record['correct'] if record else None,
            'false_missing': record['false_missing'] if record else None,
            'wrong_class': record['wrong_class'] if record else None,
            'model_identity': response.get('model_identity'),
            'finish_reason': response.get('finish_reason'), 'text': response.get('text'),
        })
    (output / 'responses.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in response_rows),
        encoding='utf-8')
    _csv(output / 'responses.csv', response_rows,
         ['id', 'case_id', 'world_id', 'cohort', 'arm', 'history_present', 'prediction_rule_present',
          'repetition', 'expected', 'status', 'answer', 'correct', 'false_missing', 'wrong_class',
          'model_identity', 'finish_reason', 'text'])
    by_pair = {(task['case_id'], task['arm'], task['repetition']): task for task in plan['tasks']}
    transitions = []
    for case in plan['cases']:
        for repetition in range(1, plan['config']['repetitions'] + 1):
            for contrast_id, (left, right) in PAIR_CONTRASTS.items():
                row = {'contrast_id': contrast_id, 'case_id': case['id'], 'world_id': case['world_id'],
                       'cohort': case['cohort'], 'repetition': repetition, 'expected': case['expected'],
                       'left': left, 'right': right}
                for side, arm in (('left', left), ('right', right)):
                    task = by_pair[case['id'], arm, repetition]
                    record = records.get(task['id'])
                    attempt = latest.get(task['id'])
                    row[side + '_status'] = attempt['status'] if attempt else 'not_started'
                    row[side + '_answer'] = record['answer'] if record else None
                row['both_valid'] = row['left_status'] == row['right_status'] == 'complete'
                transitions.append(row)
    _csv(output / 'paired-transitions.csv', transitions,
         ['contrast_id', 'case_id', 'world_id', 'cohort', 'repetition', 'expected', 'left', 'right',
          'left_status', 'right_status', 'left_answer', 'right_answer', 'both_valid'])
    world_rows = []
    for comparison in summary['comparisons']:
        for world in comparison['worlds']:
            row = {key: comparison[key] for key in ('contrast_id', 'contrast_type', 'cohort', 'metric')}
            row.update(world)
            if comparison['contrast_type'] == 'pair':
                row.update({'left': comparison['left'], 'right': comparison['right'],
                            'estimate': world['left_minus_right']})
            else:
                # One numerical column per arm keeps the interaction inspectable
                # without parsing Python dictionary representations from CSV.
                for arm in core.ARMS:
                    row[arm + '_rate'] = world['arm_rates'][arm]
                    row[arm + '_lower'] = world['arm_full_plan_bounds'][arm][0]
                    row[arm + '_upper'] = world['arm_full_plan_bounds'][arm][1]
            row['full_plan_lower'], row['full_plan_upper'] = world['full_plan_bounds']
            world_rows.append(row)
    _csv(output / 'world-contrasts.csv', world_rows,
         ['contrast_id', 'contrast_type', 'cohort', 'metric', 'left', 'right', 'world_id', 'n_cases',
          'complete', 'left_rate', 'right_rate', 'left_minus_right', 'estimate',
          'left_full_plan_bounds', 'right_full_plan_bounds', 'full_plan_lower', 'full_plan_upper']
         + [arm + suffix for arm in core.ARMS for suffix in ('_rate', '_lower', '_upper')])
    write_json(output / 'summary.json', summary)
    lines = [
        '# Downstream history by prediction-rule control', '',
        'Status: ' + summary['analysis_status'] + '.',
        f"Returned {summary['returned_answers']}/{summary['planned_calls']}; valid {summary['valid_answers']}; invalid retained {summary['invalid_answers']}; pending {summary['pending']}.",
        '', 'Counts below describe calls; the paired estimates weight worlds equally.', '',
        '| Cohort | Arm | Correct / valid | False MISSING / valid | Invalid | Pending |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for cell in summary['cells']:
        lines.append(f"| {cell['cohort']} | {cell['arm']} | {cell['correct']}/{cell['valid']} | {cell['false_missing']}/{cell['valid']} | {cell['invalid_retained']} | {cell['pending']} |")
    primary = summary['primary']
    lines += [
        '', 'Primary: rule-absent minus rule-present accuracy without history in the genuine-missing cohort.',
        f"Paired complete worlds: {primary['complete_worlds']}/{primary['planned_worlds']}.",
        f"World-weighted rates on those same worlds: rule absent {primary['left_rate_complete_worlds']}; rule present {primary['right_rate_complete_worlds']}.",
        f"Difference: {primary['estimate_complete_worlds']}; descriptive 95% world-bootstrap interval: {primary['world_bootstrap_95_ci']}; full-plan difference bounds: {primary['full_plan_bounds']}.",
        '', 'All pairwise comparisons and four-arm interactions follow. Each row uses its own complete-world set.', '',
        '| Cohort | Metric | Contrast | Complete / planned worlds | Difference | Descriptive 95% interval | Full-plan bounds |',
        '|---|---|---|---:|---:|---|---|',
    ]
    for comparison in summary['comparisons']:
        lines.append(f"| {comparison['cohort']} | {comparison['metric']} | {comparison['contrast_id']} | {comparison['complete_worlds']}/{comparison['planned_worlds']} | {comparison['estimate_complete_worlds']} | {comparison['world_bootstrap_95_ci']} | {comparison['full_plan_bounds']} |")
    lines += [
        '', 'Rule effects are rule absent minus rule present. History effects are history present minus history absent. The interaction is the history effect with the rule minus the history effect without it.',
        '', 'All arm rates, world memberships and bounds are in summary.json and world-contrasts.csv. Raw responses and factors are in responses.jsonl and responses.csv; the four paired response comparisons are in paired-transitions.csv.', '',
    ]
    lines += ['- ' + note for note in summary['notes']]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary
