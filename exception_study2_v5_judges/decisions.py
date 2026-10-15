"""Mechanical alignment and explicit semantic assertions are distinct checks."""
from exception_review.decisions import positions
from exception_study2_v5.review.workflow import anchor, decision_key
from .policy import EVENTS, SCHEMAS, criteria, schema_check


def nonpresent(status, reason):
    return dict(status=status, span=None, text=None, anchor=None, subtype=None,
                rationale=reason, certificates={})


def validate_vote(family, value, view, request_valid=True, reason=None):
    result = dict(raw=value, request_valid=request_valid, schema_valid=False,
                  reason=reason, events={e: nonpresent('invalid', reason or 'Unusable judge response') for e in EVENTS[family]},
                  semantic_certification='NOT_PROVEN: explicit model assertions only')
    if not request_valid:
        return result
    try:
        schema_check(value, SCHEMAS[family])
    except (ValueError, TypeError, KeyError) as exc:
        result['reason'] = str(exc)
        return result
    result['schema_valid'] = True
    text = view['pre_answer_text']
    for event, d in value.items():
        status = d['status']
        if not view['original_available']:
            decision = nonpresent('invalid', 'Original unavailable; no event can be inferred')
        elif status != 'present':
            if any(d[k] is not None for k in ('claim_quote', 'anchor_quote', 'subtype')):
                decision = nonpresent('invalid', 'Non-present quotes/subtype must be null')
            elif status in ('absent', 'excluded') and d['checks']['reviewed_all_pre_answer_text']['status'] != 'pass':
                decision = nonpresent('uncertain', 'Complete-text review was not explicitly certified: ' + d['rationale'])
            else:
                decision = nonpresent(status, d['rationale'])
        else:
            claim, context = d['claim_quote'], d['anchor_quote']
            inside, outside = positions(context or '', claim), positions(text, context)
            if not claim or len(inside) != 1 or len(outside) != 1 or d['subtype'] is None:
                decision = nonpresent('invalid', 'Present claim/anchor/subtype is not uniquely aligned')
            elif any(d['checks'][c]['status'] != 'pass' for c in criteria(event)):
                decision = nonpresent('uncertain', 'At least one explicit semantic check did not pass: ' + d['rationale'])
            else:
                start = outside[0] + inside[0]; end = start + len(claim)
                local_anchor = anchor(text, start, end)
                if len(positions(text, local_anchor['before'] + claim + local_anchor['after'])) != 1:
                    decision = nonpresent('invalid', 'v5 context anchor does not uniquely identify this claim')
                else:
                    decision = dict(status='present', span=[start, end], text=claim, anchor=local_anchor,
                                    subtype=d['subtype'], rationale=d['rationale'],
                                    certificates={c: d['checks'][c]['status'] == 'pass' for c in criteria(event)})
        result['events'][event] = decision
    if family == 'O':
        enforce_acknowledgment(result['events'])
    return result


def enforce_acknowledgment(events):
    o, a = events['override'], events['acknowledgment']
    if o['status'] == 'present' and (a['status'] != 'present' or a['span'][1] > o['span'][0]):
        events['override'] = nonpresent('uncertain', 'Override lacks an accepted prior correct acknowledgment')


def pair(a, b):
    return a['status'] in ('present', 'absent', 'excluded') and decision_key(a) == decision_key(b)


def resolve(family, votes):
    result = dict(state='PENDING', needs_j3=False, events={}, pairs={}, initial_agreement={})
    if any(votes.get(j) is None for j in ('J1', 'J2')):
        return result
    for event in EVENTS[family]:
        initial = pair(votes['J1']['events'][event], votes['J2']['events'][event])
        result['initial_agreement'][event] = initial
        chosen = None
        for a, b in (('J1', 'J2'), ('J1', 'J3'), ('J2', 'J3')):
            if votes.get(a) and votes.get(b) and pair(votes[a]['events'][event], votes[b]['events'][event]):
                chosen = (a, b); break
        result['pairs'][event] = list(chosen) if chosen else None
        if chosen:
            result['events'][event] = dict(votes[chosen[0]]['events'][event])
        else:
            result['needs_j3'] = True
            invalid = all(v['events'][event]['status'] == 'invalid' for v in votes.values() if v)
            result['events'][event] = nonpresent('invalid' if invalid else 'uncertain', 'No conclusive exact independent pair; retained for optional manual review')
    result['state'] = 'TERMINAL' if not result['needs_j3'] or votes.get('J3') is not None else 'PENDING'
    if family == 'O':
        enforce_acknowledgment(result['events'])
    return result
