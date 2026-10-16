"""Source-bound reuse and one position per provider, with no majority voting."""
import copy
import re
from exception_study2_v5_review_v2 import candidates as canonical
from exception_study2_v5_review_v22.decisions import partial_vote
from . import VERSION

PROVIDERS = ('openai','anthropic')


def recorded_witness(packet, candidate):
    """Necessary source witness for historical AND new positive A, never a vote.

    Independent semantic checks must ALSO pass. Ambiguous prose is not declared negative.
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
        return 'Explicit whole-statement recorded-value witness; independent semantic checks still required'
    return None


def acknowledgment_decision(packet, candidate, decision):
    """Apply the same source requirement after independent semantic validation.

    A judge's self-reported value_basis/asserted_class cannot substitute for an
    explicit witness in the frozen source. Failure preserves uncertainty, not absence.
    The returned copy leaves the original normalized vote and paid artifact intact.
    """
    d = copy.deepcopy(decision)
    witness = recorded_witness(packet, candidate) if candidate['event'] == 'A' else None
    if candidate['event'] == 'A' and d['status'] == 'present' and not witness:
        d.update(status='uncertain', prior_ack_id=None, issue_kind='recorded_value_not_established',
            validation_errors=d['validation_errors'] + [
                'A lacks explicit source-bound recognition of the target actual recorded Verified class; matching classification or feature summary is insufficient'])
    return d, witness


def historical_evidence(packet, case, candidate, judges):
    result=[]
    for phase, data in case['phases'].items():
        for judge, vote in data['votes'].items():
            if candidate['id'] not in vote['decisions']:continue
            original=copy.deepcopy(vote['decisions'][candidate['id']])
            d,witness=acknowledgment_decision(packet,candidate,original)
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
    selected += [x for x in evidence if x['epoch']==VERSION and x['provider']==provider
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


def source_resolution(packet, candidate, evidence):
    """Separate missing votes from dispatch eligibility without inventing negatives.

    An unresolved A with no frozen witness cannot become an accepted positive under
    this policy, regardless of paid votes. Keep it in the candidate population and
    downstream uncertainty checks, but defer its verification to separate review.
    Already supported negatives remain valid; coverage obligations are unchanged.
    """
    result = resolve(evidence)
    witness = recorded_witness(packet, candidate) if candidate['event'] == 'A' else None
    deferred = candidate['event'] == 'A' and result['status'] == 'uncertain' and not witness
    return dict(result, recorded_witness=witness, deferred_source_witness=deferred,
        dispatch_providers=[] if deferred else result['required_providers'],
        deferral_reason='Frozen A source lacks the required recorded-value witness; paid verification cannot repair source text. Retained uncertain for separate review.' if deferred else None)


def new_vote(parsed,packet,candidates):
    value=partial_vote(parsed.get('value'),packet,candidates,parsed['valid'],parsed.get('reason'))
    value['audit']['source_witness_checks']={}
    for c in candidates:
        key=c['id'];original=value['decisions'][key]
        d,witness=acknowledgment_decision(packet,c,original)
        value['decisions'][key]=d
        if c['event']=='A':
            value['audit']['source_witness_checks'][key]=dict(
                witness=witness,original_decision=original,accepted_status=d['status'])
        if d!=original:
            # partial_vote's audit precedes the additional source gate. Keep its
            # schema-valid record, but never leave a rejected positive conclusive.
            value['audit']['conclusive_ids'].remove(key)
            value['audit']['invalid_decisions'][key]=d['validation_errors']
    return value
