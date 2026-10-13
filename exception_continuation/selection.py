"""Offline selection coverage and manual 2B eligibility; never launches another stage."""
from collections import Counter
import json
from pathlib import Path

from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from .core import read_plan, final_score
from .runner import sealed_read, sealed_write, validate_collection
from .validation import calibration_result


def _rows(out, plan, execution):
    tasks = {t['id']: t for t in plan['tasks']}
    if (out/'collection.json').exists():
        collection = sealed_read(out/'collection.json')
        validate_collection(plan, collection)
        technical = sealed_read(out/'validation.json')
        if (execution is None or collection['backend_hash'] != execution['backend_hash']
                or technical['backend_hash'] != execution['backend_hash']
                or collection['validation_hash'] != technical['artifact_hash'] or not technical['passed']):
            raise ValueError('Collection/technical/backend identity differs')
        return collection, collection['rows'], {}
    rows, unresolved = [], {}
    for path in sorted((out/'operations').glob('*.json')):
        operation = sealed_read(path)
        if (execution is None or operation['plan_hash'] != plan['plan_hash']
                or operation['backend_hash'] != execution['backend_hash']):
            raise ValueError('Partial operation identity differs')
        if not operation['id'].startswith('trajectory/'):
            continue
        tid = operation['id'][len('trajectory/'):]
        if tid not in tasks:
            raise ValueError('Unplanned trajectory')
        if operation['status'] != 'returned':
            unresolved[tid] = operation['status']
            continue
        t = tasks[tid]; raw = operation['result']
        rows.append(dict(task=t, raw=raw, score=final_score(raw['text'], raw['stopped'], t['expected'])))
    if len({r['task']['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate returned trajectory')
    return None, rows, unresolved


def _review_counts(out, plan, collection, review_file):
    visible = {t['id']: t for t in plan['tasks'] if t['arm'] == 'visible'}
    result = dict(status='PENDING_MANUAL_REVIEW', visible_planned=len(visible), reviewed=0,
                  reviewed_no_false_missing=0, reviewed_false_missing_cases=0,
                  reviewed_false_missing_worlds=0, eligible_cases_before_branch_validation=None,
                  eligible_worlds_before_branch_validation=None, boundary_exclusions=None,
                  per_case_replay_validation='PENDING', sufficiency='REQUIRES_SEPARATE_REVIEW',
                  explanation='The reasoning-error calibration gate does not establish a sufficient 2B cohort.')
    if collection is None:
        if review_file or (out/'edit-plan.json').exists():
            raise ValueError('Manual eligibility needs the complete original selection collection')
        return result
    frozen = sealed_read(out/'edit-plan.json') if (out/'edit-plan.json').exists() else None
    path = Path(review_file) if review_file else out/'review.json'
    review = json.loads(path.read_text()) if path.exists() else None
    if review_file and review is None:
        raise ValueError('Requested review file does not exist')
    if frozen:
        if frozen['plan_hash'] != plan['plan_hash'] or frozen['collection_hash'] != collection['artifact_hash']:
            raise ValueError('Frozen eligibility belongs to another collection')
        if review is not None and digest(review) != frozen['review_hash']:
            raise ValueError('Manual review differs from the frozen edit plan')
        annotations = frozen['review_rows']
    elif review is not None:
        if review['plan_hash'] != plan['plan_hash'] or review['collection_hash'] != collection['artifact_hash']:
            raise ValueError('Manual review belongs to another collection')
        annotations = review['rows']
    else:
        return result
    by_id = {a['task_id']: a for a in annotations}
    if len(by_id) != len(annotations) or set(by_id) != set(visible):
        raise ValueError('Review must retain every visible output, including negatives and invalids')
    originals = {r['task']['id']: r for r in collection['rows']}
    positives = []
    for tid, a in by_id.items():
        row = originals[tid]
        if (a['trajectory_hash'] != digest(row) or a['text'] != row['raw']['text']
                or a['prompt'] != row['task']['prompt'] or a['target_row'] != row['task']['target_row']):
            raise ValueError('Manual-review source changed')
        if a['reviewed'] is not True:
            continue
        if type(a['false_missing']) is not bool or not a['reviewer'] or not a['justification']:
            raise ValueError('Reviewed cases need an explicit manual label, reviewer and justification')
        result['reviewed'] += 1
        if a['false_missing']:
            positives.append(tid)
        else:
            result['reviewed_no_false_missing'] += 1
    result.update(reviewed_false_missing_cases=len(positives),
                  reviewed_false_missing_worlds=len({visible[tid]['world'] for tid in positives}),
                  status='REVIEWED_NOT_FROZEN' if result['reviewed'] == len(visible) else 'PARTIAL_MANUAL_REVIEW')
    if frozen:
        if result['reviewed'] != len(visible):
            raise ValueError('Frozen edit plan requires all manual reviews')
        cases = frozen['cases']
        result.update(status='CASES_AVAILABLE_REVIEW_REQUIRED' if cases else 'NO_ELIGIBLE_CASES',
                      eligible_cases_before_branch_validation=len(cases),
                      eligible_worlds_before_branch_validation=len({visible[c['task_id']]['world'] for c in cases}),
                      boundary_exclusions=dict(Counter(e['reason'] for e in frozen['excluded']
                                                       if e['reason'] != 'reviewed_no_false_missing')),
                      selection_basis=frozen['selection_basis'],
                      no_2a_selection_attested=frozen['no_2a_selection_attested'],
                      edit_plan_hash=frozen['artifact_hash'])
    return result


def selection_report(output, review_file=None):
    with run_lock(output) as out:
        plan = read_plan(out)
        if plan['phase'] != 'selection':
            raise ValueError('This report describes the existing 48-response selection only')
        execution = sealed_read(out/'execution.json') if (out/'execution.json').exists() else None
        if execution and execution['plan_hash'] != plan['plan_hash']:
            raise ValueError('Execution belongs to another plan')
        collection, rows, unresolved = _rows(out, plan, execution)
        for row in rows:
            raw = row['raw']
            if row['score'] != final_score(raw['text'], raw['stopped'], row['task']['expected']):
                raise ValueError('Saved score differs from the raw original response')
        arms = {}
        for arm in ('direct', 'visible'):
            group = [r for r in rows if r['task']['arm'] == arm]
            planned = sum(t['arm'] == arm for t in plan['tasks'])
            valid = sum(r['score']['valid'] for r in group)
            correct = sum(r['score']['correct'] is True for r in group)
            unknown = planned - valid
            arms[arm] = dict(planned=planned, returned=len(group), missing=planned-len(group),
                valid=valid, invalid=len(group)-valid, truncated=sum(r['raw']['finish'] == 'length' for r in group),
                correct=correct, wrong=valid-correct, accuracy_valid=correct/valid if valid else None,
                accuracy_full_plan_bounds=[correct/planned, (correct+unknown)/planned],
                correctness_unknown=unknown)
        paired = {}
        for r in rows:
            paired.setdefault((r['task']['world'], r['task']['variant']), {})[r['task']['arm']] = r
        wrong, pattern = [], []
        for key, pair in paired.items():
            if set(pair) != {'direct', 'visible'} or pair['direct']['score']['correct'] is not True:
                continue
            if pair['visible']['score']['correct'] is False:
                wrong.append(key)
                if pair['visible']['score']['answer'] == pair['visible']['task']['pattern']:
                    pattern.append(key)
        mode = execution['mode'] if execution else 'NOT_COLLECTED'
        technical = sealed_read(out/'validation.json') if (out/'validation.json').exists() else None
        if technical and (technical['plan_hash'] != plan['plan_hash'] or execution is None
                          or technical['backend_hash'] != execution['backend_hash']):
            raise ValueError('Technical validation identity differs')
        calibration = calibration_result(plan, collection) if collection else {'passed': None, 'status': 'PENDING_COMPLETE_COLLECTION'}
        real_validation = ('PENDING' if mode != 'LIVE_LOCAL' or technical is None else
                           'TECHNICAL_PASSED' if technical['passed'] else 'FAILED')
        result = dict(report_version='selection-readiness-v1', plan_hash=plan['plan_hash'],
            model_profile=plan['config'].get('model_profile'), mode=mode,
            original_response_source='This run only; no GPT-4o/Mistral historical trajectories',
            planned_responses=len(plan['tasks']), returned_responses=len(rows),
            collection_status='COMPLETE' if collection else 'INCOMPLETE',
            unresolved_operations=unresolved, real_model_compatibility=real_validation,
            behavioral_replication=('PENDING' if mode != 'LIVE_LOCAL' or collection is None else
                                    'PASSED_EXISTING_CRITERION' if calibration['passed'] else 'FAILED_EXISTING_CRITERION'),
            by_arm=arms, matched_reasoning_errors=dict(
                planned_pairs=24, returned_pairs=sum(set(p) == {'direct', 'visible'} for p in paired.values()),
                direct_correct_visible_wrong=len(wrong), any_error_worlds=len({w for w,v in wrong}),
                direct_correct_visible_pattern_errors=len(pattern), pattern_error_worlds=len({w for w,v in pattern})),
            existing_calibration=calibration, study_2b_manual_eligibility=_review_counts(out, plan, collection, review_file),
            checkpoint_measurements='NOT_LAUNCHED_BY_THIS_REPORT', confirmation='NOT_LAUNCHED_BY_THIS_REPORT',
            intervention_grid='NOT_LAUNCHED_BY_THIS_REPORT',
            definitions={'accuracy_valid': 'Correct/valid final answers, with coverage and full-plan bounds alongside.',
                         'invalid': 'Returned but invalid final answer; correctness remains unknown, not wrong.',
                         'truncated': 'finish=length; included within invalid, not an additional disjoint outcome.',
                         'missing': 'No returned original response; includes unstarted/error/unresolved operations.',
                         'eligible': 'Manual edit plan and exact original boundary rules passed; branch replay and edited-token checks still pending.'})
        sealed_write(out/'selection-summary.json', result)
        lines = ['# Study 2 selection readiness', '', f"Mode: {mode}. Collection: {result['collection_status']} ({len(rows)}/48).",
                 f"Real-model compatibility: {real_validation}. Behavioral replication: {result['behavioral_replication']}.", '',
                 '| Arm | Correct / planned | Accuracy on valid | Invalid | Truncated (subset) | Missing |',
                 '|---|---:|---:|---:|---:|---:|']
        for arm, counts in arms.items():
            lines.append(f"| {arm} | {counts['correct']}/{counts['planned']} | {counts['accuracy_valid']} | {counts['invalid']} | {counts['truncated']} | {counts['missing']} |")
        review = result['study_2b_manual_eligibility']
        lines += ['', f"Matched direct-correct / visible-wrong: {len(wrong)} pairs in {len({w for w,v in wrong})} worlds.",
                  f"Matched pattern errors (existing calibration criterion): {len(pattern)} pairs in {len({w for w,v in pattern})} worlds.",
                  f"Existing calibration passed: {calibration['passed']}.", '',
                  f"Manual review: {review['reviewed']}/24; false missingness: {review['reviewed_false_missing_cases']} cases in {review['reviewed_false_missing_worlds']} worlds.",
                  f"2B eligibility before branch validation: {review['eligible_cases_before_branch_validation']} cases in {review['eligible_worlds_before_branch_validation']} worlds. Status: {review['status']}.", '',
                  'Passing the reasoning-error criterion does not establish enough false-missingness cases for 2B.',
                  'All visible responses, including invalid/truncated and negative cases, require manual review.',
                  'Invalid correctness stays unknown; full-plan accuracy bounds and all denominators are in selection-summary.json.',
                  'This report launches no confirmation, checkpoint measurements or interventions.', '']
        (out/'selection-summary.md').write_text('\n'.join(lines))
        return result
