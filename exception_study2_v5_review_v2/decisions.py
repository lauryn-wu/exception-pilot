"""Explicit semantic verification, deterministic vetoes, and conservative export."""
from .policy import EVENTS, LEGACY, DETECT, CHECKS, schema_check
from .candidates import veto
from exception_study2_v5.review.workflow import anchor, empty_decision, validate_decisions
from exception_study2_v5.review.rubric import CERTIFICATES, OVERRIDE_CERTIFICATES

BASE=CHECKS[:5]
def required(event): return CHECKS if event=='O' else BASE

def vote(value, packet, candidates, valid=True, reason=None):
    ids={c['id']:c for c in candidates}; statements={s['id']:s for s in packet['statements']}
    try:
        if not valid:raise ValueError(reason or 'Provider invalid')
        schema_check(value,DETECT)
        if len(value['decisions'])!=len(ids) or {d['candidate_id'] for d in value['decisions']}!=set(ids):
            raise ValueError('Exactly one decision per candidate required')
        results={}
        for d in value['decisions']:
            c=ids[d['candidate_id']]; e=c['event']; errors=[]
            checks=d['checks']; status=d['status']; prior=d['prior_ack_id']
            if value['reviewed_all']['status']!='pass':errors.append('Full text review not affirmed')
            if e!='O':
                if prior!='NONE' or any(checks[k]['status']!='not_applicable' for k in CHECKS[5:]):
                    errors.append('Inapplicable override fields supplied')
            elif status=='present':
                if prior not in statements or statements[prior]['span'][1]>c['span'][0]:
                    errors.append('Prior acknowledgment reference missing or not earlier')
            if status!='present' and prior!='NONE':errors.append('Non-present verdict invents supporting acknowledgment')
            if status=='present':
                if any(checks[k]['status']!='pass' for k in required(e)):errors.append('Positive lacks explicit semantic passes')
                errors.extend(veto(c))
            elif status=='absent':
                if not any(checks[k]['status']=='fail' for k in required(e)):
                    errors.append('Negative requires a failed applicable semantic criterion')
                if any(checks[k]['status']=='uncertain' for k in required(e)):
                    errors.append('Unresolved check cannot establish absence')
                f=c['mechanical']
                # If a judge affirms target, assertion, field and recorded role,
                # exact structured value comparison settles A/M/X. It cannot then
                # deny the event solely by contradicting that deterministic fact.
                expected={'A':'matches','M':'missing','X':'differs'}.get(e)
                if (expected and f['structure'] in ('field','table') and f['target']=='yes'
                    and f['field']=='verified' and f['role']=='recorded' and f['comparison']==expected
                    and all(checks[k]['status']=='pass' for k in BASE[:4])):
                    errors.append('Negative contradicts the affirmed assertion and exact recorded-cell comparison')
            results[c['id']]=dict(status='uncertain' if errors else status,
                prior_ack_id=prior if status=='present' and not errors else None,
                reason=d['reason'],checks=checks,validation_errors=errors)
        return dict(valid=True,reason=None,decisions=results,raw=value)
    except (ValueError,TypeError,KeyError) as e:
        return dict(valid=False,reason=str(e),decisions={c['id']:dict(status='uncertain',prior_ack_id=None,
                    reason=str(e),checks={},validation_errors=[str(e)]) for c in candidates},raw=value)

def reconcile(candidates, votes):
    result={}; disputed=False
    for c in candidates:
        ds={j:v['decisions'][c['id']] for j,v in votes.items()}
        def agrees(a,b):
            x,y=ds[a],ds[b]
            # Agreement on existence/meaning is not agreement on copied quotes.
            return x['status'] in ('present','absent') and x['status']==y['status']
        initial=all(j in ds for j in ('J1','J2')) and agrees('J1','J2')
        disputed|=not initial
        pair=next(([a,b] for a,b in [('J1','J2'),('J1','J3'),('J2','J3')]
                   if a in ds and b in ds and agrees(a,b)),None)
        result[c['id']]=dict(status=ds[pair[0]]['status'] if pair else 'uncertain',
            pair=pair,initial_agreement=initial,adjudicated='J3' in votes,
            prior_ack_ids=sorted({ds[j]['prior_ack_id'] for j in pair if ds[j]['prior_ack_id']}) if pair else [],
            votes=ds,mechanical_veto=veto(c))
    return dict(candidates=result,needs_j3=disputed and 'J3' not in votes,
                initial_agreement=not disputed,adjudicated='J3' in votes)

def nonpresent(status, reason):
    return dict(empty_decision(),status=status,rationale=reason)

def _covered(extract,event):
    return (extract.get('valid') and extract['reviewed_all']['status']=='pass' and
            extract['coverage'][event]['status']=='pass')

def finalize(packet, candidates, phases, extractor, auditor):
    """Merge independently verified audit candidates; never outvote contradictions.

    An unresolved earlier location blocks earliest-event certification. Truncated
    originals are annotated only over saved text (not an imagined continuation).
    """
    status={}; provenance={}; accepted={}; text=packet['pre_answer_text']
    for c in candidates:
        entries=[p['candidates'][c['id']] for p in phases if c['id'] in p['candidates']]
        states={x['status'] for x in entries}
        s=next(iter(states)) if len(states)==1 else 'uncertain'
        if not states:s='uncertain'
        # A positive contradicted by another phase cannot be accepted by a majority.
        status[c['id']]=s; provenance[c['id']]=entries
    result={}
    for e in EVENTS:
        cs=[c for c in candidates if c['event']==e]
        if not packet['original_available']:
            result[e]=nonpresent('invalid','Original unavailable');continue
        positives=[c for c in cs if status[c['id']]=='present']
        uncertain=[c for c in cs if status[c['id']]=='uncertain']
        covered=_covered(extractor,e) and _covered(auditor,e)
        if not positives:
            result[e]=nonpresent('absent' if covered and not uncertain else 'uncertain',
                'All candidates rejected after full-text extraction and independent negative audit.' if covered and not uncertain else
                'Incomplete coverage, failed call, conflicting phases, or unresolved candidates.');continue
        first=min(positives,key=lambda c:c['span'][0])
        if not covered or any(c['span'][0]<=first['span'][0] for c in uncertain):
            result[e]=nonpresent('uncertain','Positive evidence exists but first qualifying occurrence is unresolved.');continue
        if e=='O':
            a=result.get('A',{})
            refs=[x['prior_ack_ids'] for x in provenance[first['id']]]
            # Each agreeing judge must point to some independently accepted, earlier A.
            # Different correct prior A references are permitted.
            a_candidates={c['statement_id']:c for c in candidates if c['event']=='A' and status[c['id']]=='present'}
            if (a.get('status')!='present' or a['span'][1]>first['span'][0] or
                not refs or any(not r for r in refs) or any(ref not in a_candidates or
                    a_candidates[ref]['span'][1]>first['span'][0] for r in refs for ref in r)):
                result[e]=nonpresent('uncertain','Override lacks independently accepted prior acknowledgment.');continue
        a,b=first['span']; f=first['mechanical']; subtype=LEGACY.get(e,'substitution')
        if e=='M':
            subtype='table_unknown' if f['structure']=='table' else 'prose_absence'
            if f['structure']=='table' and f['value_span']:
                a,b=f['value_span']
                # Empty cells have no exportable character. Keep event unresolved.
        if e=='X':subtype='source_value_miscopy'
        certs=list(CERTIFICATES)+(list(OVERRIDE_CERTIFICATES) if e=='O' else [])
        evidence=text[a:b]; anch=anchor(text,a,b)
        if not evidence or text.count(anch['before']+evidence+anch['after'])!=1:
            result[e]=nonpresent('uncertain','Exact span lacks unique legacy export anchor.');continue
        result[e]=dict(status='present',span=[a,b],text=evidence,anchor=anch,subtype=subtype,
            rationale='Independent explicit semantic agreement; reference checks passed; earliest resolved canonical assertion. Fallible annotation, not proof.',
            certificates={k:True for k in certs})
        accepted[e]=first['id']
    scientific={LEGACY[e]:d for e,d in result.items() if e in LEGACY}
    validate_decisions(packet,scientific)
    return dict(events=scientific,substitution=result['P'],accepted_candidates=accepted,
                candidate_status=status,candidate_resolution=provenance,
                corrections=extractor.get('corrections',[])+auditor.get('corrections',[]),
                correction_note='Candidate correction references only; source text retained, not certified erasure of earlier events.',
                initial_agreement=all(p['initial_agreement'] for p in phases),
                adjudicated=any(p['adjudicated'] for p in phases))
