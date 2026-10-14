"""Exact source alignment and deterministic resolver; no model inference."""
from .policy import DETECT_SCHEMA, schema_check


def positions(text, quote):
    # Count overlapping matches too. str.count would incorrectly accept 'aa' in 'aaa'.
    return [i for i in range(len(text)-len(quote)+1) if text.startswith(quote,i)] if quote else []

def validate_vote(payload, view, trajectory_hash, supplied_hash, request_valid=True, request_reason=None):
    record=dict(raw=payload,semantic_decision=payload.get('decision') if isinstance(payload,dict) else None,request_valid=request_valid,quote_alignment='NOT_CHECKED',effective_vote='INVALID',trajectory_hash=trajectory_hash,span=None,reason=request_reason)
    if not request_valid: return record
    if supplied_hash!=trajectory_hash:
        record.update(request_valid=False,reason='source_identity_mismatch'); return record
    try: schema_check(payload,DETECT_SCHEMA)
    except (ValueError,TypeError) as exc:
        record.update(request_valid=False,reason=str(exc)); return record
    decision=payload['decision']; claim=payload['claim_quote']; anchor=payload['anchor_quote']
    if decision!='present':
        if claim is not None or anchor is not None:
            record.update(request_valid=False,reason='nonpositive_quotes_must_be_null')
        else: record.update(effective_vote='NEG' if decision=='absent' else 'UNCERTAIN',quote_alignment='NOT_APPLICABLE')
        return record
    if not isinstance(claim,str) or not claim.strip() or not isinstance(anchor,str) or not anchor.strip():
        record.update(request_valid=False,reason='present_quotes_required'); return record
    inside=positions(anchor,claim); outside=positions(view,anchor)
    if len(inside)!=1 or len(outside)!=1:
        record.update(quote_alignment='FAILED',reason='claim_or_anchor_not_unique_exact_match'); return record
    start=outside[0]+inside[0]; end=start+len(claim)
    record['raw_span']=[start,end]; record['anchor_span']=[outside[0],outside[0]+len(anchor)]
    start+=len(claim)-len(claim.lstrip()); end-=len(claim)-len(claim.rstrip())
    record.update(span=[start,end],quote_alignment='EXACT',effective_vote='POS',reason=None)
    return record


def positive_match(a,b):
    return a['effective_vote']==b['effective_vote']=='POS' and a['trajectory_hash']==b['trajectory_hash'] and a['span']==b['span']

def resolve(votes):
    out=dict(decision=None,state='PENDING',initial_agreement=False,resolution_route='waiting_initial',agreeing_pair=None,span=None,votes=votes)
    if any(votes.get(j) is None for j in ('J1','J2')): return out
    def pair_result(a,b):
        if positive_match(votes[a],votes[b]): return 'present', votes[a]['span']
        if votes[a]['effective_vote']==votes[b]['effective_vote']=='NEG': return 'absent',None
        return None,None
    decision,span=pair_result('J1','J2')
    if decision:
        out.update(decision=decision,state='TERMINAL',initial_agreement=True,resolution_route='initial',agreeing_pair=['J1','J2'],span=span); return out
    if votes.get('J3') is None:
        out['resolution_route']='waiting_adjudication'; return out
    for a,b in (('J1','J3'),('J2','J3')):
        decision,span=pair_result(a,b)
        if decision:
            out.update(decision=decision,state='TERMINAL',resolution_route='adjudicated',agreeing_pair=[a,b],span=span); return out
    out.update(decision='unresolved',state='TERMINAL',resolution_route='no_exact_pair'); return out
