"""Source-bound reuse and one position per provider, with no majority voting."""
import copy
import re
from exception_study2_v5_review_v2 import candidates as canonical
from exception_study2_v5_review_v22.decisions import partial_vote

PROVIDERS = ('openai','anthropic')


def recorded_witness(packet, candidate):
    """Sufficient literal evidence for reusing an old positive A, never a new vote.

    Old semantic checks must ALSO pass. Ambiguous prose is not declared negative.
    Narrow whole-statement forms avoid accepting a matching prediction or a feature
    summary. These forms are audit-informed, not independent semantic validation.
    """
    f = candidate['mechanical']
    if (f['exact_span'] and f['target']=='yes' and f['field']=='verified'
        and f['role']=='recorded' and f['comparison']=='matches'):
        return 'Exact target recorded-cell/value witness'
    t = canonical.clean(candidate['text']).replace('"','')
    plate = re.escape(packet['target']['plate']); value = re.escape(packet['target']['verified_class'])
    forms = [
        rf'According to the table, (?:the value in the Verified class column|the Verified class) for (?:the )?(?:license plate )?{plate} is (?:explicitly listed as )?{value}\.',
        rf'The table directly provides the Verified class for (?:the )?(?:license plate )?{plate}, which is listed as {value}\.',
        rf'We are to determine the class of {plate}, which is already listed as {value} in the table\.',
        rf'Since the Verified class is (?:already given as |explicitly listed as |already ){value}, (?:we can confirm that the class of the vehicle with license plate {plate} is {value}|no prediction is necessary|the correct answer is {value})\.',
    ]
    if any(re.fullmatch(form,t) for form in forms):
        return 'Explicit whole-statement recorded-value witness; old independent semantic checks still required'
    return None


def prediction_only(candidate):
    t = canonical.clean(candidate['text'])
    return (candidate['mechanical']['role']=='prediction' or bool(re.fullmatch(
        r'(?i)Based on (?:the data and )?(?:the )?patterns(?: observed)?, (?:the vehicle with license plate )?[\w-]+ (?:belongs to class|is class|is classified as) [ABC][.!]?',t)))


def historical_evidence(packet, case, candidate, judges):
    result=[]
    for phase, data in case['phases'].items():
        for judge, vote in data['votes'].items():
            if candidate['id'] not in vote['decisions']:continue
            d=copy.deepcopy(vote['decisions'][candidate['id']]); original=copy.deepcopy(d)
            witness=recorded_witness(packet,candidate) if candidate['event']=='A' else None
            if d['status']=='present' and candidate['event']=='A' and not witness:
                d.update(status='uncertain',prior_ack_id=None,issue_kind='recorded_value_not_established',
                    validation_errors=d['validation_errors']+['Historical A lacks explicit source-bound recorded-value witness; matching prediction is insufficient'])
            result.append(dict(epoch='historical-v2.1',phase=phase,judge=judge,
                provider=judges[judge]['provider'],model=judges[judge]['model'],
                operation_key=vote['operation_key'],operation_hash=vote['operation_hash'],
                candidate_id=candidate['id'],source_row_hash=packet['source_row_hash'],span=candidate['span'],
                original_decision=original,decision=d,recorded_witness=witness))
    return result


def position(evidence, provider):
    history=[x for x in evidence if x['epoch']=='historical-v2.1' and x['provider']==provider]
    # The predesignated initial OpenAI judge has precedence, irrespective of outcome.
    # J3 is archived and is only a fallback where J1 has no valid position, never an
    # extra vote or a tie breaker. Both historical phases remain visible.
    names=('J1',) if provider=='openai' else ('J2',)
    selected=[x for x in history if x['judge'] in names and x['decision']['status'] in ('present','absent')]
    if not selected and provider=='openai':
        selected=[x for x in history if x['judge']=='J3' and x['decision']['status'] in ('present','absent')]
    selected += [x for x in evidence if x['epoch']=='residual-v1' and x['provider']==provider
                 and x['decision']['status'] in ('present','absent')]
    states={x['decision']['status'] for x in selected}
    return dict(status=next(iter(states)) if len(states)==1 else 'uncertain',
        conflict=len(states)>1, evidence=selected,
        reason='Contradictory valid judgments within provider' if len(states)>1 else
               'Valid provider evidence retained' if states else 'No conclusive revalidated provider evidence')


def resolve(evidence):
    ps={p:position(evidence,p) for p in PROVIDERS}
    states={p:x['status'] for p,x in ps.items()}
    conflict=any(p['conflict'] for p in ps.values()) or set(states.values())=={'present','absent'}
    accepted=not conflict and states['openai']==states['anthropic'] and states['openai'] in ('present','absent')
    missing=[] if accepted or conflict else [p for p in PROVIDERS if states[p]=='uncertain']
    return dict(status=states['openai'] if accepted else 'uncertain', providers=ps,
        genuine_disagreement=conflict, required_providers=missing,
        reason='Cross-provider agreement' if accepted else 'Genuine disagreement; no automatic adjudication' if conflict else 'Missing or invalid provider evidence',
        prior_ack_ids=sorted({x['decision']['prior_ack_id'] for p in ps.values() for x in p['evidence'] if x['decision']['prior_ack_id']}) if accepted else [])


def new_vote(parsed,packet,candidates):
    value=partial_vote(parsed.get('value'),packet,candidates,parsed['valid'],parsed.get('reason'))
    for c in candidates:
        d=value['decisions'][c['id']]
        if c['event']=='A' and d['status']=='present' and prediction_only(c):
            d.update(status='uncertain',prior_ack_id=None,issue_kind='recorded_value_not_established',
                validation_errors=d['validation_errors']+['Source is a prediction, not a recorded acknowledgment'])
    return value
