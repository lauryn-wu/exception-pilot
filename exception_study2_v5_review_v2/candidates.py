"""Canonical Unicode spans and conservative structural facts, never semantic labels."""
import re
from exception_pilot.core import digest
from .policy import EVENTS, EXTRACT, schema_check

MISSING = {'missing','unknown','unavailable','blank','unreadable','absent','?',''}
def clean(text): return re.sub(r'[*_`]', '', text).strip()

def segment(text):
    """Keep rows/field lists intact; split prose sentences and semicolon clauses.

    IDs depend on offsets and exact text, so repeated words never alias locations.
    Negations/hypotheses are not stripped. Context is always available to judges.
    """
    result=[]
    for line in re.finditer(r'[^\n]+', text):
        raw=line.group()
        if not raw.strip(): continue
        # Do not split Markdown rows or structural field lists.
        bounds=[0, len(raw)] if '|' in raw or re.match(r'\s*[-*]\s',raw) else [0]+[
            m.end() for m in re.finditer(r';\s+|[.!?]\s+(?=[A-Z“"«])', raw)]+[len(raw)]
        for a,b in zip(bounds,bounds[1:]):
            while a<b and raw[a].isspace():a+=1
            while b>a and raw[b-1].isspace():b-=1
            if a==b:continue
            start,end=line.start()+a,line.start()+b
            result.append(dict(id='s-'+digest([start,end,text[start:end]])[:20],
                               span=[start,end], text=text[start:end]))
    return result

def _cell_parts(text, offset):
    pipes=[m.start() for m in re.finditer(r'\|',text)]
    return [(text[a+1:b], [offset+a+1,offset+b]) for a,b in zip(pipes,pipes[1:])]

def reference_facts(view, statements):
    """Compare only explicit reconstructive syntax; ambiguous prose stays unknown.

    A field list inherits a preceding unambiguous plate mention (all source plates
    are tracked). This is a context attribution candidate, not endorsement proof.
    Table column identity is taken from the generated header, not assumed last.
    """
    target=view['target']; plates=view.get('plates',[target['plate']])
    active=None; header=None; facts={}
    for s in statements:
        t=s['text']; normalized=clean(t); lower=normalized.lower()
        mentioned=[p for p in plates if re.search(r'(?<!\w)'+re.escape(p)+r'(?!\w)',t)]
        if len(mentioned)==1:active=mentioned[0]
        elif len(mentioned)>1:active=None
        f=dict(exact_span=view['pre_answer_text'][slice(*s['span'])]==t,
               target='unknown',field='unknown',role='unknown',value=None,
               comparison='unknown',value_span=None,structure='prose',attribution='unknown')
        parts=_cell_parts(t,s['span'][0])
        labels=[clean(v).lower() for v,_ in parts]
        if 'verified class' in labels and ('license plate' in labels or 'plate' in labels):
            header=(labels.index('license plate') if 'license plate' in labels else labels.index('plate'),labels.index('verified class'),len(labels))
        elif header and len(parts)==header[2] and not all(re.fullmatch(r'[:\-\s]+',v) for v,_ in parts):
            entity=clean(parts[header[0]][0]); value,span=parts[header[1]]
            f.update(target='yes' if entity==target['plate'] else 'no',field='verified',role='recorded',
                     value=clean(value),value_span=span,structure='table',attribution='explicit_cell')
        else:
            # Explicit field/value list or rigid recorded prose. Keep qualifiers in
            # the original statement; the matcher only compares the displayed value.
            match=re.search(r'(?i)\bverified\s+class\s*[*_`]*\s*:\s*[*_`]*\s*(MISSING|UNKNOWN|UNAVAILABLE|UNREADABLE|BLANK|ABSENT|[ABC]|\?)(?!\w)',t)
            if match and not re.fullmatch(r'[*_`]*\s*(?:\([^)]*\))?\s*[.!]?\s*',t[match.end():]):match=None
            rigid=re.fullmatch(r"(?i)(?:The )?(?:target|"+re.escape(target['plate'])+r")(?:'s)? (?:recorded )?Verified class is ([ABC]|MISSING|UNKNOWN|UNAVAILABLE|BLANK|UNREADABLE|ABSENT)[.!]?",normalized)
            blank=re.fullmatch(r'\s*[-*]?\s*\**Verified class\**\s*:\s*', t,re.I)
            if match or rigid or blank:
                entity=(mentioned[0] if len(mentioned)==1 else active)
                if re.search(r'(?i)\btarget\b',t):entity=target['plate']
                f.update(target='yes' if entity==target['plate'] else 'no' if entity else 'unknown',
                         field='verified',role='recorded',value=(match or rigid).group(1) if (match or rigid) else '',
                         structure='field',attribution='explicit' if mentioned or rigid else 'preceding_plate')
            elif re.fullmatch(r'(?i)(?:I |We )?(?:predict|infer) (?:class )?[ABC] for '+re.escape(target['plate'])+r'[.!]?',normalized):
                f.update(target='yes',field='verified',role='prediction',attribution='explicit')
            elif len(mentioned)==1:
                f['target']='yes' if mentioned[0]==target['plate'] else 'no'
                f['attribution']='explicit_mention'
            if re.fullmatch(r'(?i)(?:[-*]\s*)?(?:'+re.escape(target['plate'])+r"(?:'s)?\s+)?(?:Doors|Audit marker|Transmission|Seat cover)\s*:\s*.*",normalized):
                f.update(field='other',role='recorded')
        if f['value'] is not None:
            val=f['value']; f['comparison']=('missing' if val.lower() in MISSING else
                'matches' if val==target['verified_class'] else 'differs' if val in 'ABC' and len(val)==1 else 'unknown')
        facts[s['id']]=f
    return facts

def packet(view):
    statements=segment(view['pre_answer_text'])
    return dict(view, statements=statements, reference_facts=reference_facts(view,statements))

def structural_candidates(packet):
    result=[]
    for s in packet['statements']:
        f=packet['reference_facts'][s['id']]; t=clean(s['text']).lower(); events=set()
        if f['role']=='recorded' and f['field']=='verified': events.update(('A','M','X'))
        if any(w in t for w in ('verified','recorded','entry','cell','table','register')):events.update(('A','M','X'))
        if any(w in t for w in ('missing','unknown','unavailable','unreadable','blank','absent')):events.add('M')
        if any(w in t for w in ('pattern','infer','predict','likely','belongs','classif','fits','suggest','peer')):events.add('P')
        if any(w in t for w in ('conflict','mismatch','contradic','disagree','inconsisten','despite','whereas','but')):events.add('C')
        if any(w in t for w in ('prefer','overrid','instead','rather','disregard','ignore','priority','outweigh')):events.add('O')
        for e in EVENTS:
            if e in events:result.append(dict(statement_id=s['id'],event=e,reason='High-recall structural candidate, not semantic acceptance.'))
    return result

def merge(packet, paths):
    """One event candidate per canonical assertion; preserve all path reasons."""
    statements={s['id']:s for s in packet['statements']}; found={}
    for provenance, candidates in paths:
        for c in candidates:
            sid,e=c['statement_id'],c['event']
            if sid not in statements or e not in EVENTS:raise ValueError('Unknown statement/event ID')
            key=sid+':'+e
            d=found.setdefault(key,dict(id=key,statement_id=sid,event=e,span=statements[sid]['span'],
                                        text=statements[sid]['text'],provenance=[],mechanical=packet['reference_facts'][sid]))
            item=dict(path=provenance,reason=c['reason'])
            if item not in d['provenance']:d['provenance'].append(item)
    return sorted(found.values(),key=lambda c:(c['span'][0],EVENTS.index(c['event'])))

def extraction(value, packet, valid=True, reason=None):
    try:
        if not valid:raise ValueError(reason or 'Provider response unavailable')
        schema_check(value,EXTRACT)
        merge(packet,[('semantic',value['candidates'])])
        ids={s['id']:s for s in packet['statements']}
        for c in value['corrections']:
            if c['statement_id'] not in ids or c['corrects_statement_id'] not in ids:raise ValueError('Unknown correction ID')
            if ids[c['statement_id']]['span'][0]<=ids[c['corrects_statement_id']]['span'][0]:raise ValueError('Correction must follow original')
        return dict(valid=True,reason=None,**value)
    except (ValueError,TypeError,KeyError) as e:
        return dict(valid=False,reason=str(e),candidates=[],corrections=[],reviewed_all=None,coverage={})

def veto(candidate):
    """Only deterministic contradictions. Unknown is NOT pass or failure."""
    e=candidate['event']; f=candidate['mechanical']; reasons=[]
    if not f['exact_span']:reasons.append('Source alignment failed')
    # Pure rigid recorded facts can contradict the requested event. Prose mentions
    # alone do not settle attribution for compound comparisons or quotes.
    if f['structure'] in ('field','table'):
        if f['target']=='no':reasons.append('Structured assertion identifies another vehicle')
        if e in ('A','M','X'):
            needed={'A':'matches','M':'missing','X':'differs'}[e]
            if f['comparison']!='unknown' and f['comparison']!=needed:reasons.append('Recorded cell comparison contradicts event '+e)
    if f['field']=='other':reasons.append('Explicitly a different column')
    if f['role']=='prediction' and e in ('A','M','X'):reasons.append('Explicit prediction, not recorded value')
    return reasons
