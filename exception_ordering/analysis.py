"""World-clustered descriptive comparisons and missing-response bounds."""
from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import mean

from exception_pilot.core import rng_for
from exception_pilot.storage import write_json
from .core import read_plan
from .runner import journal, position_report

COEFFICIENTS = {
    'primary_harm_after_minus_before': {('after', 'direct'): 1, ('after', 'visible'): -1,
                                       ('before', 'direct'): -1, ('before', 'visible'): 1},
    'visible_after_minus_before': {('after', 'visible'): 1, ('before', 'visible'): -1},
    'direct_after_minus_before': {('after', 'direct'): 1, ('before', 'direct'): -1},
    'both_harm_minus_endpoints': {(p, a): c * s for p, c in
                                 [('both_left_near', .5), ('both_right_near', .5), ('before', -.5), ('after', -.5)]
                                 for a, s in [('direct', 1), ('visible', -1)]}}


def interval(values):
    if not values:
        return None
    rng = rng_for('ordering-bootstrap', 981723)
    draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(10000))
    return [draws[249], draws[9749]]


def contrast(plan, records, coefficients, allowed=None):
    groups = defaultdict(list)
    for t in plan['tasks']:
        key = (t['world'], t['variant'], t['rotation'])
        if (t['placement'], t['arm']) in coefficients and (allowed is None or key in allowed):
            groups[t['world']].append(t)
    values, bounds, detail = [], [], []
    for wid, tasks in groups.items():
        n = len({(t['variant'], t['rotation']) for t in tasks})
        lo = hi = value = 0.; complete = True
        for t in tasks:
            c = coefficients[t['placement'], t['arm']] / n
            score = records.get(t['id'], {}).get('score', {}).get('correct')
            if score is None:
                complete = False; lo += min(c, 0); hi += max(c, 0)
            else:
                value += c * score; lo += c * score; hi += c * score
        if complete:
            values.append(value)
        bounds.append((lo, hi))
        detail.append(dict(world=wid, paired_blocks=n, complete=complete,
                           estimate=value if complete else None, bounds=[lo, hi]))
    return dict(estimate=mean(values) if values else None, complete_worlds=len(values),
                eligible_worlds=len(groups), bootstrap_95=interval(values),
                full_plan_bounds=[mean(b[i] for b in bounds) for i in (0, 1)] if bounds else None,
                worlds=detail)


def analyze(output):
    out = Path(output); plan = read_plan(out); entries = journal(out, plan)
    records = {e['task_id']: e for e in entries if e['status'] == 'returned'}
    groups = defaultdict(list)
    for t in plan['tasks']:
        groups[t['placement'], t['arm']].append(t)
    cells = {}
    for (p, a), ts in groups.items():
        rs = [records[t['id']]['score'] for t in ts if t['id'] in records]
        valid = [s for s in rs if s['valid']]
        cells[p + '/' + a] = dict(planned=len(ts), returned=len(rs), valid=len(valid),
                                  invalid=len(rs)-len(valid), missing=len(ts)-len(rs),
                                  accuracy=mean(s['correct'] for s in valid) if valid else None,
                                  pattern_rate=mean(s['pattern'] for s in valid) if valid else None,
                                  adherent=sum(s['adherence'] for s in rs))
    audit = position_report(plan)
    allowed = {(e['world'], e['variant'], e['rotation']) for e in audit['comparisons'] if e['before_after_match']}
    contrasts = {name: contrast(plan, records, c) for name, c in COEFFICIENTS.items()}
    contrasts['token_matched_primary'] = contrast(plan, records, COEFFICIENTS['primary_harm_after_minus_before'], allowed)
    variability = []
    for w in plan['worlds']:
        for placement in ('before', 'after', 'both_left_near', 'both_right_near'):
            for arm in ('direct', 'visible'):
                vals = []
                for k in range(20):
                    ids = [f"{w['id']}/v{v}/r{k}/{placement}/{arm}" for v in range(2)]
                    scores = [records.get(i, {}).get('score', {}).get('correct') for i in ids]
                    vals.append(mean(scores) if all(s is not None for s in scores) else None)
                known = [v for v in vals if v is not None]
                variability.append(dict(world=w['id'], placement=placement, arm=arm,
                                        rotation_accuracies=vals, range=max(known)-min(known) if known else None))
    result = dict(mode=json.loads((out/'execution.json').read_text())['mode'] if (out/'execution.json').exists() else 'NOT_RUN',
                  cells=cells, contrasts=contrasts, rotation_variability=variability,
                  token_comparisons=len(audit['comparisons']), token_measured=audit['measured'],
                  token_matched=audit['matched_before_after'],
                  limitations='Conditional on this rearrangement; token audit is not verified provider serialization.')
    write_json(out / 'summary.json', result)
    with (out/'responses.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['id', 'world', 'arrangement', 'arm', 'answer', 'correct', 'raw_text', 'status'])
        for t in plan['tasks']:
            e = records.get(t['id'], {})
            writer.writerow([t['id'], t['world'], t['placement'], t['arm'], e.get('score', {}).get('answer'),
                             e.get('score', {}).get('correct'), e.get('response', {}).get('text'), e.get('status', 'missing')])
    (out/'summary.md').write_text('# ' + result['mode'] + '\n\n' +
        '\n'.join(f"- {name}: {c['estimate']}; complete worlds {c['complete_worlds']}/{c['eligible_worlds']}; bounds {c['full_plan_bounds']}"
                  for name, c in contrasts.items()) + '\n\nIntervals are descriptive. SIMULATED values are software tests, not evidence.\n')
    return result
