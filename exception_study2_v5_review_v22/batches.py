"""Deterministic exclusions/batches; never discard unknown semantics."""
import math
import re
from exception_pilot.core import digest
from exception_study2_v5_review_v2.candidates import veto,clean


def filter_candidates(candidates):
    kept=[];excluded=[]
    for c in candidates:
        reasons=veto(c)
        f=c['mechanical']
        if (c['event'] in ('A','M','X') and f['target']=='no' and f['attribution']=='explicit_mention'
            and re.fullmatch(r"(?i)(?:The )?[\w-]+(?:'s)? (?:recorded )?Verified class is (?:[ABC]|MISSING|UNKNOWN|UNAVAILABLE|BLANK|UNREADABLE|ABSENT)[.!]?",clean(c['text']))):
            reasons.append('Explicit single other-vehicle recorded-class assertion')
        if reasons:excluded.append(dict(candidate=c,reasons=reasons,basis='Deterministic source/field/value contradiction; not a judge vote.'))
        else:kept.append(c)
    return kept,excluded


def partition(candidates,size=6):
    if type(size) is not int or not 4<=size<=8:raise ValueError('Batch target must be 4..8')
    items=sorted(candidates,key=lambda c:(c['span'][0],c['span'][1],c['id']))
    if not items:return []
    n=math.ceil(len(items)/size)
    while n>1 and len(items)//n<4:n-=1
    width,extra=divmod(len(items),n);result=[];start=0
    for i in range(n):
        end=start+width+(i<extra);result.append(items[start:end]);start=end
    assert all(len(x)<=8 for x in result)
    return result


def freeze_batches(packet,candidates,phase,source_ref,policy,size=6):
    from .providers import payload
    kept,excluded=filter_candidates(candidates);batches=[]
    for index,items in enumerate(partition(kept,size)):
        binding=dict(phase=phase,index=index,candidate_ids=[c['id'] for c in items],source=source_ref,packet_hash=digest(packet),policy_hash=policy['policy_hash'])
        batch_id='b-'+digest(binding)[:24]
        view=dict(packet,candidates=items,batch=dict(id=batch_id,**binding))
        requests={j:payload(config,policy['rubrics']['detect'],policy['schemas']['detect'],view) for j,config in policy['config']['judges'].items()}
        batches.append(dict(id=batch_id,binding=binding,candidates=items,view=view,requests=requests))
    return dict(phase=phase,kept=kept,excluded=excluded,batches=batches,maximum_calls=3*len(batches))
