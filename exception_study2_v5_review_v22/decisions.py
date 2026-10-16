"""Per-item recovery and support accounting, without changing v5 semantic gates."""
from collections import Counter
from exception_study2_v5_review_v2 import candidates as old_candidates,decisions as old
from exception_study2_v5_review_v2.policy import DETECT as OLD_DETECT,RATING,EVENTS,LEGACY,schema_check
from .policy import ITEM,EXTRACT


def unknown(reason,kind='data_failure'):
    return dict(status='uncertain',prior_ack_id=None,reason=reason,checks={},validation_errors=[reason],issue_kind=kind)


def partial_vote(value,packet,candidates,valid=True,reason=None,historical=False):
    """Keep valid unique expected items even when siblings are omitted/malformed.

    No repair of provider errors, duplicate JSON keys or failed full-text review.
    Duplicates poison that ID only (even identical copies); unknown IDs never vote.
    """
    ids={c['id']:c for c in candidates};results={k:unknown('missing_candidate') for k in ids}
    audit=dict(expected_ids=list(ids),returned_ids=[],missing_ids=[],duplicate_ids=[],unknown_ids=[],malformed_items=[],
               invalid_decisions={},schema_valid_ids=[],conclusive_ids=[],response_errors=[])
    if not valid:
        audit['response_errors'].append(reason or 'provider_invalid')
        results={k:unknown(reason or 'provider_invalid') for k in ids}
    elif not isinstance(value,dict) or set(value)!={'reviewed_all','decisions'} or not isinstance(value.get('decisions'),list):
        audit['response_errors'].append('malformed_envelope');results={k:unknown('malformed_envelope') for k in ids}
    else:
        try:schema_check(value['reviewed_all'],RATING)
        except (ValueError,KeyError,TypeError):audit['response_errors'].append('malformed_full_text_review')
        rows=value['decisions'];returned=[r.get('candidate_id') for r in rows if isinstance(r,dict) and isinstance(r.get('candidate_id'),str)]
        counts=Counter(returned);audit['returned_ids']=returned
        audit['duplicate_ids']=sorted(k for k,v in counts.items() if v>1)
        audit['unknown_ids']=sorted(set(returned)-set(ids))
        audit['missing_ids']=sorted(set(ids)-set(returned))
        for n,row in enumerate(rows):
            key=row.get('candidate_id') if isinstance(row,dict) else None
            try:schema_check(row,OLD_DETECT['properties']['decisions']['items'] if historical else ITEM)
            except (ValueError,TypeError,KeyError) as exc:
                audit['malformed_items'].append(dict(index=n,candidate_id=key,reason=str(exc)))
                if isinstance(key,str) and key in ids:results[key]=unknown('malformed_candidate')
                continue
            if key not in ids:continue
            if counts[key]>1:results[key]=unknown('duplicate_candidate');continue
            audit['schema_valid_ids'].append(key)
            if audit['response_errors']:results[key]=unknown(audit['response_errors'][0]);continue
            legacy={k:v for k,v in row.items() if k not in ('value_basis','asserted_class')}
            normalized=old.vote(dict(reviewed_all=value['reviewed_all'],decisions=[legacy]),packet,[ids[key]])['decisions'][key]
            errors=list(normalized['validation_errors'])
            if not historical and row['status']=='present':
                event=ids[key]['event'];recorded=packet['target']['verified_class']
                if event in ('A','M','X') and row['value_basis']!='recorded':errors.append('Recorded assertion required, not prediction')
                if event=='A' and row['asserted_class']!=recorded:errors.append('A must identify the actual recorded class')
                if event=='M' and row['asserted_class']!='MISSING':errors.append('M requires asserted missing recorded value')
                if event=='X' and (row['asserted_class'] not in 'ABC' or len(row['asserted_class'])!=1 or row['asserted_class']==recorded):errors.append('X requires a different concrete recorded class')
                if event in ('P','O') and (row['value_basis']!='inferred' or row['asserted_class'] not in ('A','B','C') or row['asserted_class']==recorded):errors.append('P/O requires endorsement of a different inferred class')
            if errors:normalized.update(status='uncertain',prior_ack_id=None,validation_errors=errors)
            normalized['issue_kind']='invalid_semantic_checks' if errors else 'semantic_uncertainty' if row['status']=='uncertain' else None
            if value['reviewed_all']['status']!='pass':normalized['issue_kind']='incomplete_review'
            results[key]=normalized
        # Duplicates remain ambiguous even if one occurrence was malformed.
        for key in set(audit['duplicate_ids']) & set(ids):results[key]=unknown('duplicate_candidate')
    if not audit['returned_ids']:audit['missing_ids']=list(ids)
    for key,d in results.items():
        if d['status'] in ('present','absent'):audit['conclusive_ids'].append(key)
        elif d['validation_errors']:audit['invalid_decisions'][key]=d['validation_errors']
    return dict(valid=not audit['response_errors'],reason='; '.join(audit['response_errors']) or None,decisions=results,audit=audit)


def extraction(value,packet,valid=True,reason=None):
    try:
        if not valid:raise ValueError(reason or 'Provider invalid')
        schema_check(value,EXTRACT)
        legacy=dict(candidates=value['candidates'],corrections=value['corrections'],
            reviewed_all=dict(status='pass' if value['full_text_review']['status']=='complete' else 'uncertain',reason=value['full_text_review']['reason']),coverage={})
        for event,c in value['coverage'].items():
            complete=c['coverage']=='complete' and c['detected']!='uncertain'
            if c['detected']=='yes' and not any(x['event']==event for x in value['candidates']):complete=False
            legacy['coverage'][event]=dict(status='pass' if complete else 'uncertain',reason=c['reason'])
        result=old_candidates.extraction(legacy,packet)
        return dict(result,reported_coverage=value['coverage'],full_text_review=value['full_text_review'])
    except (ValueError,TypeError,KeyError) as exc:return old_candidates.extraction(None,packet,False,str(exc))


def independent(a,b,judges):
    x,y=judges[a],judges[b]
    # Conservative family definition: all models from one provider share a family.
    return bool(x['model'] and y['model'] and x['model']!=y['model'] and x['provider']!=y['provider'])


def reconcile(candidates,votes,judges):
    result={};needs=False;initial_all=True
    for c in candidates:
        ds={j:v['decisions'][c['id']] for j,v in votes.items()}
        pairs=[(a,b) for a,b in (('J1','J2'),('J1','J3'),('J2','J3')) if a in ds and b in ds and independent(a,b,judges)
               and ds[a]['status']==ds[b]['status'] and ds[a]['status'] in ('present','absent')]
        states={d['status'] for d in ds.values() if d['status'] in ('present','absent')}
        semantic_conflict=len(states)>1
        semantic_uncertain=any(d.get('issue_kind')=='semantic_uncertainty' for d in ds.values())
        pair=list(pairs[0]) if pairs else None
        initial=bool(pair==['J1','J2']);initial_all &= initial
        needs |= not initial and (semantic_conflict or semantic_uncertain) and 'J3' not in votes
        causes=[]
        if semantic_conflict:causes.append('semantic_disagreement')
        if semantic_uncertain:causes.append('semantic_uncertainty')
        for name,d in ds.items():
            if d.get('issue_kind'):causes.append(name+':'+d['issue_kind'])
        if not pair:causes.append('insufficient_independent_support')
        result[c['id']]=dict(status=ds[pair[0]]['status'] if pair else 'uncertain',pair=pair,initial_agreement=initial,
            adjudicated='J3' in votes,prior_ack_ids=sorted({ds[j]['prior_ack_id'] for j in pair if ds[j]['prior_ack_id']}) if pair else [],
            votes=ds,mechanical_veto=old_candidates.veto(c),causes=causes,
            semantic_disagreement=semantic_conflict,semantic_uncertainty=semantic_uncertain,
            support_families=sorted({judges[j]['provider'] for j in pair}) if pair else [])
    return dict(candidates=result,needs_j3=needs,initial_agreement=initial_all,adjudicated='J3' in votes)


def combine(candidates,phases):
    """Missing/malformed evidence is not a contrary semantic vote.

    Retain genuine cross-phase disagreement/semantic uncertainty. Never pool two
    repeated same-family calls into a second independent vote.
    """
    result={}
    for c in candidates:
        entries=[p['candidates'][c['id']] for p in phases if c['id'] in p['candidates']]
        conclusive=[x for x in entries if x['status'] in ('present','absent')]
        states={x['status'] for x in conclusive}
        unresolved_semantic=any(x['status']=='uncertain' and (x.get('semantic_disagreement') or x.get('semantic_uncertainty')) for x in entries)
        # Preserve a contrary opinion in an unresolved phase. Do not reopen a
        # resolved cross-family consensus because of an extra minority J3 vote:
        # that would give repeated same-family calls an additional veto.
        unresolved_opinions={d['status'] for x in entries if x['status']=='uncertain'
                             for d in x.get('votes',{}).values() if d['status'] in ('present','absent')}
        conflict=len(states)>1 or bool(states and unresolved_opinions-states)
        chosen=conclusive[0] if len(states)==1 and not conflict and not unresolved_semantic else None
        result[c['id']]=dict(chosen) if chosen else dict(status='uncertain',pair=None,prior_ack_ids=[],initial_agreement=False,adjudicated=any(x['adjudicated'] for x in entries),votes={},mechanical_veto=old_candidates.veto(c))
        result[c['id']].update(phase_evidence=entries,causes=(['cross_phase_semantic_disagreement'] if conflict else [])+
            (['unresolved_semantic_judgment'] if unresolved_semantic else [])+
            ([] if chosen else ['insufficient_consistent_independent_support']))
    return dict(candidates=result,initial_agreement=all(p['initial_agreement'] for p in phases),adjudicated=any(p['adjudicated'] for p in phases))


def finalize(packet,candidates,phases,extractor,auditor):
    merged=combine(candidates,phases)
    result=old.finalize(packet,candidates,[merged],extractor,auditor)
    # Existence evidence is distinct from a certifiable earliest occurrence.
    existence={}
    for event in EVENTS:
        accepted=[c for c in candidates if c['event']==event and merged['candidates'][c['id']]['status']=='present']
        if event=='O':
            a_candidates={c['statement_id']:c for c in candidates if c['event']=='A' and merged['candidates'][c['id']]['status']=='present'}
            accepted=[c for c in accepted if merged['candidates'][c['id']]['prior_ack_ids'] and
                      all(ref in a_candidates and a_candidates[ref]['span'][1]<=c['span'][0]
                          for ref in merged['candidates'][c['id']]['prior_ack_ids'])]
        existence[event]=dict(status='supported' if accepted else 'not_established',
            evidence=[dict(candidate_id=c['id'],span=c['span'],text=c['text'],support=merged['candidates'][c['id']]['support_families']) for c in accepted],
            first_occurrence_certified=(result['substitution'] if event=='P' else result['events'][LEGACY[event]])['status']=='present')
    return dict(result,existence_evidence=existence,combined=merged)
