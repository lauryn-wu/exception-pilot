"""Audit final rendered cells, never stale pre-remapping item labels."""
from collections import Counter
from itertools import combinations
import math
from exception_pilot.core import DESCRIPTORS, digest

FIELDS = ('plate', 'description', 'transmission', 'seat_cover', 'doors', 'audit_marker', 'label')
HEADER = '| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |'
DISTRACTORS = ('transmission', 'seat_cover', 'doors', 'audit_marker')
CLIMATES = {d:c for c,descriptions in DESCRIPTORS.items() for d in descriptions}


def render(rows):
    return '\n'.join([HEADER, '|---|---|---|---|---|---|---|'] +
                     ['| ' + ' | '.join(r[k] for k in FIELDS) + ' |' for r in rows])


def parse(table):
    lines = table.splitlines()
    if len(lines) < 3 or lines[:2] != [HEADER, '|---|---|---|---|---|---|---|']:
        raise ValueError('Unexpected table format')
    rows = []
    for line in lines[2:]:
        values = line.strip('| ').split(' | ')
        if len(values) != len(FIELDS):
            raise ValueError('Malformed rendered row')
        row = dict(zip(FIELDS, values))
        if row['label'] not in 'ABC' or len(row['label']) != 1 or row['description'] not in CLIMATES:
            raise ValueError('Unknown label/climate descriptor')
        row['climate'] = CLIMATES[row['description']]
        rows.append(row)
    if len({r['plate'] for r in rows}) != len(rows):
        raise ValueError('Duplicate target identifiers')
    return rows


def unique_max(values):
    if not values: return None
    top = max(values.values())
    winners = [c for c,v in values.items() if v == top]
    return winners[0] if len(winners) == 1 else None


def association(rows, fields):
    classes = sorted({r['label'] for r in rows})
    totals = Counter(r['label'] for r in rows)
    counts = {}
    for r in rows:
        key = ' / '.join(r[f] for f in fields)
        counts.setdefault(key, {c:0 for c in classes})[r['label']] += 1
    cells = {}
    mi = 0.0
    for key, ns in sorted(counts.items()):
        n = sum(ns.values())
        cells[key] = dict(counts=ns, p_class_given_value={c:ns[c]/n for c in classes},
                          p_value_given_class={c:ns[c]/totals[c] for c in classes})
        for c in classes:
            if ns[c]: mi += ns[c]/len(rows)*math.log2(ns[c]*len(rows)/(n*totals[c]))
    # Exact integer comparison avoids labeling approximately balanced data exact.
    independent = all(ns[c]*totals[d] == ns[d]*totals[c]
                      for ns in counts.values() for c in classes for d in classes)
    return dict(features=list(fields), class_counts=dict(totals), values=cells,
                exact_class_independence=independent, mutual_information_bits=mi)


def audit_table(table, plate, expected=None, pattern=None):
    rows = parse(table)
    targets = [r for r in rows if r['plate'] == plate]
    if len(targets) != 1: raise ValueError('Queried target must occur exactly once')
    target = targets[0]
    if expected is not None and expected != target['label']: raise ValueError('Source truth mismatch')
    background = [r for r in rows if r['plate'] != plate]
    features = {f:association(background, (f,)) for f in ('climate','description')+DISTRACTORS}
    joints = {'+'.join(fs):association(background, fs) for n in range(2,5) for fs in combinations(DISTRACTORS,n)}
    votes = {}
    for f in DISTRACTORS:
        assoc = features[f]; entry = assoc['values'].get(target[f])
        rates = entry['p_value_given_class'] if entry else {c:0.0 for c in assoc['class_counts']}
        counts = entry['counts'] if entry else {c:0 for c in assoc['class_counts']}
        margin = rates.get(pattern,0)-rates.get(target['label'],0) if pattern else None
        votes[f] = dict(target_value=target[f], matching_row_counts=counts,
                        count_vote=unique_max(counts), class_conditional_rates=rates,
                        equal_prior_rate_vote=unique_max(rates), pattern_minus_recorded_rate=margin)
    margins = [v['pattern_minus_recorded_rate'] for v in votes.values() if v['pattern_minus_recorded_rate'] is not None]
    full = joints['+'.join(DISTRACTORS)]
    key = ' / '.join(target[f] for f in DISTRACTORS)
    return dict(table_hash=digest(table), target_plate=plate, recorded_class=target['label'], pattern_class=pattern,
                background_class_counts=dict(Counter(r['label'] for r in background)),
                full_class_counts=dict(Counter(r['label'] for r in rows)),
                target_row_1based=rows.index(target)+1,
                same_climate_peer_positions_1based=[i+1 for i,r in enumerate(rows) if r is not target and r['climate']==target['climate']],
                same_climate_peer_classes=dict(Counter(r['label'] for r in background if r['climate']==target['climate'])),
                features=features, joint_distractors=joints, distractor_votes=votes,
                signed_rate_margin_sum=sum(margins), absolute_rate_margin_sum=sum(abs(v) for v in margins),
                nonzero_rate_margins=sum(v != 0 for v in margins),
                target_joint_profile=full['values'].get(key),
                note='Target excluded. Count votes use P(class|matching value); rate votes use P(value|class), equivalent to equal-prior likelihood ranking. Ties abstain. Signed margins can cancel; inspect absolute margins and joint tables. MI is descriptive, not an inferential test.')
