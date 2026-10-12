"""Frozen inputs; invariant record inventory across all order comparisons."""
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import digest, rng_for, check_plan

PROTOCOL = 'evidence-order-followup-v1'
CONFIG = dict(protocol=PROTOCOL, seed=2026101211, n_worlds=24,
              model='mistral-small-2603', temperature=0, reasoning_effort='none',
              max_tokens=1600, timeout_seconds=120, api_key_env='MISTRAL_API_KEY')
SLOTS = {'before': (0, 1, 2, 3), 'after': (5, 6, 7, 8),
         'both_left_near': (2, 3, 7, 8), 'both_right_near': (0, 1, 5, 6)}
ARMS = {'direct': 'Output only ANSWER: followed by A, B, or C.',
        'visible': 'Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.'}
HEADER = '| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |\n|---|---|---|---|---|---|---|'


def source_hash():
    root = Path(__file__).resolve().parents[1]
    packages = ['exception_ordering', 'exception_pilot', 'exception_counterfactual',
                'exception_explanation', 'exception_factorial', 'exception_wording',
                'exception_mistral_prefix', 'exception_prefix', 'exception_cue']
    files = [p for package in packages for p in sorted((root / package).glob('*.py'))]
    files += [root / 'EVIDENCE_ORDER_FOLLOWUP_PROTOCOL.md']
    return digest({str(p.relative_to(root)): p.read_text() for p in files})


def worlds():
    used, out = set(), []
    assignments = [(p, climate, rep) for p in itertools.permutations('ABC')
                   for climate in ['cold', 'warm'] for rep in range(2)]
    rng_for(PROTOCOL, 'assignments').shuffle(assignments)
    for index, (roles, climate, rep) in enumerate(assignments):
        w = make_world(CONFIG, index, used)
        w['id'] = f'order-new-{index:03d}'
        for item in w['items']:
            item['id'] = 'O' + item['id'][1:]
        target = next(i for i in w['target_indices'] if w['items'][i]['climate'] == climate)
        support = [i for i in range(10) if i != target and w['items'][i]['climate'] == climate]
        other = [i for i in range(10) if w['items'][i]['climate'] != climate]
        rng = rng_for(PROTOCOL, CONFIG['seed'], index)
        rng.shuffle(support); rng.shuffle(other)
        if rep:
            support.reverse(); other.reverse()
        labels = [roles[2]] * 10
        other_labels = [roles[0]] * (2 if rep else 3) + [roles[1]] * (3 if rep else 2)
        rng.shuffle(other_labels)
        for i, value in zip(other, other_labels):
            labels[i] = value
        for item in w['items']:
            item['audit_marker'] = rng.choice('XYZ')
        out.append(dict(id=w['id'], items=w['items'], target=target, support=support,
                        other=other, labels=labels, roles=list(roles), replicate=rep))
    return out


def order_for(w, placement, rotation):
    s, n = w['support'], w['other']
    s = s[rotation % 4:] + s[:rotation % 4]
    n = n[rotation % 5:] + n[:rotation % 5]
    si, ni = iter(s), iter(n)
    return [w['target'] if slot == 4 else next(si) if slot in SLOTS[placement] else next(ni)
            for slot in range(10)]


def render(w, variant, placement, rotation, arm):
    order = order_for(w, placement, rotation)
    labels = w['labels'].copy(); labels[w['target']] = w['roles'][variant]
    text = INTRO + '\n\n' + HEADER + '\n'
    spans = {}
    for i in order:
        item = w['items'][i]
        fields = [item[k] for k in ['id', 'descriptor', 'transmission', 'seat_cover', 'doors', 'audit_marker']] + [labels[i]]
        row = '| ' + ' | '.join(fields) + ' |'
        if i == w['target']:
            start = len(text)
            spans['row'] = [start, start + len(row)]
            spans['plate'] = [start + 2, start + 2 + len(item['id'])]
            # Last field starts after the penultimate separator, before final " |".
            cs = start + len(row) - 3
            spans['class'] = [cs, cs + 1]
        text += row + '\n'
    text += '\nLicense plate: '
    start = len(text); plate = w['items'][w['target']]['id']
    text += plate
    spans['query_plate'] = [start, start + len(plate)]
    text += '\n' + QUESTION + '\n' + ARMS[arm]
    assert text[slice(*spans['class'])] == labels[w['target']]
    return text, spans, order


def token_audit(text, spans, tokenizer=None):
    result = {'scope': 'user_message_only', 'characters': len(text), 'spans': spans,
              'status': 'UNMEASURED', 'tokens': None}
    if tokenizer is None:
        return result
    encoded = tokenizer.encode(text, add_special_tokens=False)
    locations = {}
    for name, (start, end) in spans.items():
        overlap = [i for i, (a, b) in enumerate(encoded.offsets) if a < end and b > start]
        if not overlap:
            raise ValueError('Tokenizer supplied no offsets for target span')
        locations[name] = [overlap[0], overlap[-1] + 1]
    result.update(status='USER_ATTESTED_TOKENIZER', tokens=len(encoded.ids),
                  token_id_hash=digest(encoded.ids), token_spans=locations)
    return result


def make_plan(tokenizer=None, provenance=None):
    ws = worlds(); blocks = [(w, k) for w in ws for k in range(20)]
    rng_for(PROTOCOL, 'blocks').shuffle(blocks)
    tasks = []
    for w, k in blocks:
        cells = list(itertools.product(range(2), SLOTS, ARMS))
        rng_for(PROTOCOL, 'cells', w['id'], k).shuffle(cells)
        for variant, placement, arm in cells:
            text, spans, order = render(w, variant, placement, k, arm)
            request = {key: CONFIG[key] for key in ['model', 'temperature', 'max_tokens', 'reasoning_effort']}
            request['messages'] = [{'role': 'user', 'content': text}]
            tasks.append(dict(id=f"{w['id']}/v{variant}/r{k}/{placement}/{arm}",
                              world=w['id'], variant=variant, rotation=k, placement=placement,
                              arm=arm, expected=w['roles'][variant], pattern=w['roles'][2],
                              row=5, order=order, request=request, request_hash=digest(request),
                              position=token_audit(text, spans, tokenizer)))
    p = dict(protocol=PROTOCOL, config=CONFIG, source_hash=source_hash(), worlds=ws,
             tasks=tasks, tokenizer=provenance, planned_responses=len(tasks))
    p['plan_hash'] = digest(p)
    return p


def read_plan(output):
    p = json.loads((Path(output) / 'plan.json').read_text())
    check_plan(p)
    if p['config'] != CONFIG or p['source_hash'] != source_hash():
        raise ValueError('Config/source changed; preserve existing run')
    for t in p['tasks']:
        if digest(t['request']) != t['request_hash']:
            raise ValueError('Request changed')
    return p


def score(task, response):
    text = response.get('text', '')
    lines = text.strip().splitlines()
    match = re.fullmatch(r'ANSWER: ([ABC])', lines[-1].strip()) if lines else None
    valid = response.get('complete') and match is not None
    answer = match.group(1) if valid else None
    return dict(answer=answer, valid=bool(valid), correct=None if not valid else answer == task['expected'],
                pattern=None if not valid else answer == task['pattern'],
                adherence=bool(valid and (len(lines) == 1 if task['arm'] == 'direct' else bool('\n'.join(lines[:-1]).strip()))))
