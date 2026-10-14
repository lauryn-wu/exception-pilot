"""Versioned pure statement cuts, deliberately independent of all edit data."""
from exception_continuation.events import before_boundary


def statement_boundaries(row, span):
    text=row['raw']['text']; start,end=span
    if not (type(start) is int and type(end) is int and 0<=start<end<=len(text)): raise ValueError('Invalid statement span')
    marker=text.find('ANSWER:')
    if marker>=0 and end>marker: return {n:dict(eligible=False,reason='statement_not_before_final_answer',k=None) for n in ('before_statement','after_statement')}
    before,reason=before_boundary(row,start)
    result={'before_statement':dict(eligible=before is not None,reason=reason,**(before or {'k':None}))}
    after=None; reason='no_token_boundary_immediately_after_statement'
    for cut in row['boundaries']:
        n=cut['char_end']
        if n<end: continue
        if text[end:n].strip(): break
        if not cut['roundtrip_exact']:
            reason='unchanged_prefix_token_roundtrip_failed'; break
        after=dict(cut,prefix=text[:n]); reason=None; break
    result['after_statement']=dict(eligible=after is not None,reason=reason,**(after or {'k':None}))
    return result


def answer_boundary(row):
    marker=row['raw']['text'].find('ANSWER:')
    cut,reason=(None,'no_answer_marker') if marker<0 else before_boundary(row,marker)
    return dict(event='before_answer',eligible=cut is not None,reason=reason,**(cut or {'k':None,'char_end':None}))
