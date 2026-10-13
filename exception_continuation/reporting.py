"""Denominators for interventions; validity and replay are separate axes."""
from collections import Counter

from .runner import sealed_read

ARMS = ('unchanged', 'availability_repair', 'meaning_control', 'value_repair')
REPORT_VERSION = 'intervention-coverage-v2'


def intervention_coverage(out, edit_plan, data):
    rows = {r['task_id']: r for r in data['rows']}
    operations = {}
    for path in (out/'operations').glob('*.json'):
        op = sealed_read(path)
        if op['id'].startswith('edit/') and op['id'].endswith('/continuation'):
            operations[op['id']] = op
    planned = len(edit_plan['cases'])
    counts = {}
    for arm in ARMS:
        c = dict(planned=planned, attempted=0, returned=0, valid=0, invalid=0,
                 truncated=0, missing=0, unassessed=0)
        reasons = Counter()
        for case in edit_plan['cases']:
            tid = case['task_id']; row = rows.get(tid, {})
            saved = row.get('arms', {}).get(arm)
            op = operations.get(f'edit/{tid}/{arm}/continuation')
            attempted = saved is not None or op is not None
            returned = saved is not None or bool(op and op['status'] == 'returned')
            c['attempted'] += attempted; c['returned'] += returned
            if not returned:
                c['missing'] += 1
                reasons[row.get('reason') or ('operation_' + op['status'] if op else 'not_attempted')] += 1
                continue
            raw = saved['raw'] if saved else op['result']
            truncated = raw.get('finish') == 'length'
            c['truncated'] += truncated
            if saved is None:
                c['unassessed'] += 1
                reasons['returned_without_completed_arm_assessment'] += 1
            elif saved['score']['valid']:
                c['valid'] += 1
            else:
                c['invalid'] += 1
                reasons['truncated' if truncated else 'prefix_not_preserved' if not saved.get('prefix_text_preserved', True)
                        else 'not_stopped_at_eos' if not raw.get('stopped') else 'malformed_final_answer'] += 1
        counts[arm] = dict(c, reasons=dict(reasons))
    branch_failed = [r for r in data['rows'] if r.get('validation', {}).get('passed') is False]
    control_failed = [r for r in data['rows'] if r.get('control_validation', {}).get('passed') is False]
    replay_tids = {r['task_id'] for r in branch_failed + control_failed}
    excluded_reasons = Counter(e['reason'] for e in edit_plan['excluded'])
    token_failures = [r for r in data['rows'] if r.get('eligible') is False]
    return dict(report_version=REPORT_VERSION,
        definitions={
            'planned': 'One arm per case in the frozen edit plan; pre-freeze exclusions are separate.',
            'attempted': 'A continuation operation was journaled, including started/error operations.',
            'returned': 'The continuation returned, even if later validation failed.',
            'valid_invalid': 'Syntactic final-answer validity, independent of replay; invalid correctness remains unknown.',
            'truncated': 'finish=length; subtype of invalid for assessed returns; may overlap unassessed for partial runs.',
            'missing': 'planned-returned, including unattempted and unresolved operations.',
            'identities': 'valid+invalid+unassessed=returned; returned+missing=planned; returned<=attempted<=planned.',
            'replay': 'Case-level axis, not an extra arm outcome; failed replay makes all correctness unavailable.'},
        replay_failures=dict(cases=len(replay_tids), denominator=planned,
            branch_validation=len(branch_failed), unchanged_control=len(control_failed), task_ids=sorted(replay_tids)),
        eligibility=dict(reviewed=edit_plan['reviewed'], planned_cases=planned,
            excluded_before_freeze=len(edit_plan['excluded']), exclusion_reasons=dict(excluded_reasons),
            no_false_missing=excluded_reasons.get('reviewed_no_false_missing', 0),
            tokenization_or_boundary_exclusions=sum(n for reason, n in excluded_reasons.items() if reason != 'reviewed_no_false_missing'),
            tokenization_failures_after_freeze=len(token_failures),
            after_freeze_denominator=planned,
            after_freeze_reasons=dict(Counter(r.get('reason', 'unspecified') for r in token_failures))),
        per_arm=counts)
