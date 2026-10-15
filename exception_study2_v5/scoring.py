"""Tolerant terminal answers; format, truncation and semantic outcomes stay separate."""
import re
from exception_pilot.core import digest
from exception_continuation.backend import assert_plain_format

# Balanced Markdown only. A marker in prose is never a final answer.
LINE = r'(?:ANSWER: ([ABC])|\*\*ANSWER: ([ABC])\*\*|ANSWER: \*\*([ABC])\*\*|\*\*ANSWER:\*\* ([ABC])|\*\*ANSWER:\*\* \*\*([ABC])\*\*)'
MARKER = re.compile(r'(?m)^[ \t]*(?:\*\*)?ANSWER:')

def marker_start(text):
    match = MARKER.search(text)
    return None if match is None else match.start()

def final_score(text, stopped, expected, arm='visible'):
    lines = text.strip().splitlines() if isinstance(text, str) else []
    terminal = lines[-1].strip() if lines else ''
    match = re.fullmatch(LINE, terminal)
    candidate = next((x for x in match.groups() if x), None) if match else None
    answer = candidate if stopped else None
    strict_terminal = bool(re.fullmatch(r'ANSWER: [ABC]', terminal))
    strict = bool(stopped and strict_terminal and (arm != 'direct' or len(lines) == 1))
    return dict(answer=answer, valid=answer is not None, correct=None if answer is None else answer == expected,
                strict_format=strict, strict_terminal=strict_terminal,
                strict_correct=(answer == expected) if strict else None,
                terminal_candidate=candidate, truncated=not stopped,
                outcome='unknown' if answer is None else 'correct' if answer == expected else 'wrong')

def validate_raw(raw, backend, budget):
    if not isinstance(raw,dict):raise ValueError('Invalid generated response shape')
    tokens = raw.get('tokens')
    if (not isinstance(tokens, list) or not tokens or len(tokens)>budget
            or any(type(t) is not int or t<0 for t in tokens)):
        raise ValueError('Invalid generated token array')
    eos = tokens[-1] in backend.eos_ids
    if (raw.get('stopped') is not eos or raw.get('finish') != ('eos' if eos else 'length')
            or any(t in backend.eos_ids for t in tokens[:-1]) or (not eos and len(tokens)!=budget)):
        raise ValueError('EOS/finish/budget metadata mismatch')
    if backend.decode(tokens) != raw.get('text'):
        raise ValueError('Text/token mismatch')
    assert_plain_format(raw['text'])

def boundaries(backend, raw):
    text = raw['text']; marker = marker_start(text)
    limit = len(text) if marker is None else marker
    result = [dict(k=0, char_end=0, text_hash=digest(''), token_hash=digest([]), roundtrip_exact=True)]
    for k in range(1, len(raw['tokens'])+1):
        ids = raw['tokens'][:k]
        if ids[-1] in backend.special_ids:
            break
        prefix = backend.decode(ids)
        if len(prefix)>limit:
            break
        if '\ufffd' not in prefix and text.startswith(prefix) and backend.encode(prefix)==ids:
            result.append(dict(k=k, char_end=len(prefix), text_hash=digest(prefix), token_hash=digest(ids), roundtrip_exact=True))
    return result

def boundary(row, position, side):
    text = row['raw']['text']; cuts = row['boundaries']
    if side == 'before':
        eligible = [c for c in cuts if c['char_end']<=position and not text[c['char_end']:position].strip()]
        cut = max(eligible, key=lambda c:c['char_end']) if eligible else None
    else:
        eligible = [c for c in cuts if c['char_end']>=position and not text[position:c['char_end']].strip()]
        cut = min(eligible, key=lambda c:c['char_end']) if eligible else None
    return dict(eligible=cut is not None, reason=None if cut else 'no_exact_adjacent_token_boundary', **(cut or dict(k=None)))

def checkpoints(row, annotations=None):
    from .core import CHECKPOINTS
    marker = marker_start(row['raw']['text']); found = {c['k']:c for c in row['boundaries']}
    out = []
    for k in CHECKPOINTS:
        cut = found.get(k)
        ok = cut is not None and k < len(row['raw']['tokens']) and (marker is None or cut['char_end'] < marker)
        out.append(dict(name=f'fixed/{k}', eligible=ok,
                        reason=None if ok else 'short_or_at_answer_or_inexact_boundary',
                        **(cut if ok else dict(k=None))))
    before = dict(eligible=False, k=None, reason='no_answer_marker') if marker is None else boundary(row, marker, 'before')
    out.append(dict(name='pre_answer', **before))
    if annotations:
        for event, decision in annotations.items():
            if event == 'miscopy':
                continue
            for side in ('before','after'):
                cut = (boundary(row, decision['span'][0 if side=='before' else 1], side)
                       if decision['status']=='present' else dict(eligible=False,k=None,reason='annotation_'+decision['status']))
                out.append(dict(name=f'{event}/{side}', **cut))
    return out


def raw_metadata(raw, input_ids):
    ids=raw.get('tokens') if isinstance(raw,dict) else None
    return dict(output_hash=digest(ids if isinstance(raw,dict) else raw) if raw is not None else None,
                lengths=dict(input=len(input_ids),output=len(ids) if isinstance(ids,list) else None))
