"""Descriptive length/repetition readouts for budget review; no semantic judgments."""
from collections import Counter
from statistics import mean, median
from math import ceil
from .interface import parse_result

REPETITION_N = 16
DEFINITION = ('Repeated-token-window diagnostics use generated tokens excluding special tokens: '
    '16-token sliding windows, counting occurrences after the first identical window. '
    'Fractions divide by all eligible windows; no windows means null, not zero. '
    'Overlapping windows count separately. These metrics do not establish pathological repetition; '
    'review the complete raw traces. They never change sampling, scoring, stopping or retries.')


def repetition(raw,tok):
    tokens=raw.get('tokens') if isinstance(raw,dict) else None
    if not isinstance(tokens,list) or any(type(t) is not int or t<0 for t in tokens):return None
    ids=[t for t in tokens if t not in tok.special_ids]
    counts=Counter(tuple(ids[i:i+REPETITION_N]) for i in range(max(0,len(ids)-REPETITION_N+1)))
    windows=sum(counts.values());repeated=windows-len(counts)
    longest=run=0;previous=None
    for t in ids:
        run=run+1 if t==previous else 1;previous=t;longest=max(longest,run)
    return dict(ngram_size=REPETITION_N,eligible_windows=windows,repeated_windows=repeated,
        repeated_window_fraction=repeated/windows if windows else None,
        max_identical_window_occurrences=max(counts.values(),default=0),longest_identical_token_run=longest)


def cases(c,current):
    result=[]
    for r in c.plan['requests']:
        entry=current[r['cell']['id']];op=entry['operation']
        status='never_started' if op is None or op['status']=='planned' else 'ambiguous' if op['status']=='started' else op['status']
        returned=status=='returned';raw=op['result'] if returned else None
        score=parse_result(raw,r['request'],c.tok) if returned else None
        result.append(dict(cell=r['cell'],request_hash=r['request_hash'],operation_status=status,attempt=entry['attempt'],
            operation_hash=op['artifact_hash'] if op else None,score=score,raw=raw,
            repetition=repetition(raw,c.tok) if returned else None))
    return result


def distribution(values):
    xs=sorted(x for x in values if x is not None)
    return dict(n=len(xs),minimum=min(xs),median=median(xs),p90=xs[ceil(.90*len(xs))-1],
                p95=xs[ceil(.95*len(xs))-1],maximum=max(xs)) if xs else dict(n=0)


def summarize(rows):
    groups={}
    for cohort in sorted({x['cell']['cohort'] for x in rows}):
        for thinking in (False,True):
            for wording in ('all','original','lookup'):
                for relation in ('all','support','conflict'):
                    selected=[x for x in rows if x['cell']['cohort']==cohort and x['cell']['thinking']==thinking
                        and (wording=='all' or x['cell']['wording']==wording) and (relation=='all' or x['cell']['relation']==relation)]
                    if not selected:continue
                    returned=[x for x in selected if x['score'] is not None]
                    rep=[x['repetition'] for x in returned if x['repetition'] is not None]
                    fractions=[x['repeated_window_fraction'] for x in rep if x['repeated_window_fraction'] is not None]
                    groups[f'{cohort}/thinking-{int(thinking)}/{wording}/{relation}']=dict(
                        planned=len(selected),returned=len(returned),unavailable=len(selected)-len(returned),
                        truncated=sum(x['score']['truncated'] for x in returned),
                        eos=sum(x['score'].get('eos_observed',False) for x in returned),
                        malformed=sum(x['score']['malformed'] for x in returned),
                        token_counts={k:distribution([x['score'][k] for x in returned]) for k in ('token_count','thinking_tokens','final_tokens')},
                        repetition_observed=len(rep),responses_with_repeated_windows=sum(x['repeated_windows']>0 for x in rep),
                        repetition_fraction_available=len(fractions),mean_repeated_window_fraction=mean(fractions) if fractions else None,
                        max_identical_window_occurrences=max((x['max_identical_window_occurrences'] for x in rep),default=None),
                        longest_identical_token_run=max((x['longest_identical_token_run'] for x in rep),default=None))
    return dict(definition=DEFINITION,groups=groups,
        interpretation='Readouts for human truncation/repetition review, not an automatic budget choice or a failure-family classifier.')
