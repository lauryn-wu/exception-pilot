import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_cue.core import INSTRUCTIONS
from exception_explanation.core import INTRO, QUESTION
from exception_pilot.core import digest, rng_for, check_plan

PROTOCOL = 'within-reasoning-continuation-v1'
CHECKPOINTS = (0, 32, 64, 128)
DEFAULT_CONFIG = dict(model_dir=None, device='cpu', dtype='float32', max_new_tokens=512,
                      chat_template_kwargs={})
TECHNICAL = [
    'Write a paragraph of at least 80 words describing the steps for organizing a bookshelf.',
    'Write a paragraph of at least 80 words describing the steps for preparing a garden.',
    'Write a paragraph of at least 80 words describing the steps for packing a suitcase.']


def source_hash():
    root = Path(__file__).resolve().parents[1]
    packages = ['exception_continuation', 'exception_pilot', 'exception_counterfactual',
                'exception_explanation', 'exception_cue', 'exception_factorial', 'exception_wording']
    files = [p for package in packages for p in sorted((root/package).glob('*.py'))]
    files += [root/'REASONING_CONTINUATION_PROTOCOL.md']
    return digest({str(p.relative_to(root)): p.read_text() for p in files})


def validate_config(c):
    if set(c) != set(DEFAULT_CONFIG) or c['max_new_tokens'] != 512:
        raise ValueError('Use exact config fields; fixed 512-token cap')
    if c['dtype'] not in ('float32', 'float16', 'bfloat16') or not isinstance(c['device'], str):
        raise ValueError('Invalid device/dtype')
    if c['model_dir'] is not None and not isinstance(c['model_dir'], str):
        raise ValueError('model_dir must be a local path or null for preview')
    if not isinstance(c['chat_template_kwargs'], dict):
        raise ValueError('chat_template_kwargs must be an object')
    if set(c['chat_template_kwargs']) - {'enable_thinking'}:
        raise ValueError('Only optional enable_thinking is supported; freeze its setting')
    if 'enable_thinking' in c['chat_template_kwargs'] and type(c['chat_template_kwargs']['enable_thinking']) is not bool:
        raise ValueError('enable_thinking must be boolean')
    return c


def make_plan(phase, config=None, selection_lock=None):
    if phase not in ('selection', 'confirmation'):
        raise ValueError('Unknown phase')
    c = validate_config(dict(DEFAULT_CONFIG if config is None else config))
    if phase == 'confirmation' and not selection_lock:
        raise ValueError('Confirmation requires a completed selection lock')
    seed, reps, prefix = (2026101221, 1, 'S') if phase == 'selection' else (2026101222, 2, 'T')
    assignments = [(roles, climate, rep) for roles in itertools.permutations('ABC')
                   for climate in ('cold', 'warm') for rep in range(reps)]
    rng_for(PROTOCOL, phase).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate, rep) in enumerate(assignments):
        w = make_world({'seed': seed}, index, used)
        w['id'] = f'{phase}-continuation-{index:03d}'
        for item in w['items']:
            item['id'] = prefix + item['id'][1:]
        target = next(i for i in w['target_indices'] if w['items'][i]['climate'] == climate)
        labels = [roles[2]] * 10
        other = [roles[0]] * 3 + [roles[1]] * 2
        rng = rng_for(PROTOCOL, phase, index); rng.shuffle(other)
        for i, item in enumerate(w['items']):
            item['audit_marker'] = rng.choice('XYZ')
            if item['climate'] != climate: labels[i] = other.pop()
        order = [i for i in w['order'] if i != target] + [target]
        cells = []
        for v, arm in itertools.product(range(2), ('direct', 'visible')):
            ls = labels.copy(); ls[target] = roles[v]
            rows = ['| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |',
                    '|---|---|---|---|---|---|---|']
            for i in order:
                item = w['items'][i]
                rows.append('| ' + ' | '.join([item[k] for k in ('id', 'descriptor', 'transmission', 'seat_cover', 'doors', 'audit_marker')] + [ls[i]]) + ' |')
            prompt = INTRO + '\n\n' + '\n'.join(rows) + '\n\nLicense plate: ' + w['items'][target]['id'] + '\n' + QUESTION + '\n' + INSTRUCTIONS[arm]
            cells.append(dict(id=f"{w['id']}/v{v}/{arm}", world=w['id'], variant=v, arm=arm,
                              expected=roles[v], pattern=roles[2], prompt=prompt,
                              target_plate=w['items'][target]['id'], target_row=rows[-1]))
        rng.shuffle(cells); tasks.extend(cells)
        worlds.append(dict(id=w['id'], items=w['items'], target=target, order=order, roles=list(roles)))
    plan = dict(protocol=PROTOCOL, phase=phase, config=c, seed=seed, worlds=worlds,
                tasks=tasks, checkpoints=list(CHECKPOINTS), source_hash=source_hash(), selection_lock=selection_lock)
    plan['plan_hash'] = digest(plan)
    return plan


def read_plan(out):
    p = json.loads((Path(out)/'plan.json').read_text()); check_plan(p)
    if p['source_hash'] != source_hash(): raise ValueError('Source/protocol changed')
    if p != make_plan(p['phase'], p['config'], p['selection_lock']):
        raise ValueError('Frozen inputs changed')
    return p


def final_score(text, stopped, expected):
    lines = text.strip().splitlines()
    match = re.fullmatch(r'ANSWER: ([ABC])', lines[-1].strip()) if lines else None
    answer = match.group(1) if stopped and match else None
    return dict(answer=answer, valid=answer is not None, correct=None if answer is None else answer == expected)


def eligible_cuts(backend, tokens):
    full = backend.decode(tokens)
    marker = full.find('ANSWER:')
    results = []
    for k in CHECKPOINTS:
        prefix = backend.decode(tokens[:k])
        reason = None
        if k >= len(tokens) or any(t in backend.special_ids for t in tokens[:k]): reason = 'at_or_after_termination'
        elif marker >= 0 and len(prefix) > marker: reason = 'at_or_after_first_answer_marker'
        elif '\ufffd' in prefix or not full.startswith(prefix): reason = 'partial_text_token_boundary'
        results.append(dict(k=k, eligible=reason is None, reason=reason, prefix=prefix))
    return results


def letters(text):
    return {label: len(re.findall(r'(?<!\w)' + label + r'(?!\w)', text)) for label in 'ABC'}


def edit_prefix(prefix, annotation, gold):
    start, end = annotation['span']
    if not (type(start) is int and type(end) is int and 0 <= start < end <= len(prefix)):
        raise ValueError('Invalid exact span')
    if prefix[start:end] != annotation['old']:
        raise ValueError('Old text does not match exact span')
    if not annotation.get('reviewer') or not annotation.get('justification') or annotation.get('semantic_certified') is not True:
        raise ValueError('Manual semantic certification and truth-based justification required')
    replacements = annotation['replacements']
    if set(replacements) != {'availability_repair', 'meaning_control', 'value_repair'}:
        raise ValueError('Exactly three matched edit arms required')
    if any(not isinstance(v, str) or not v or v == annotation['old'] for v in replacements.values()):
        raise ValueError('Each replacement must be nonempty and actually change the span')
    if any(letters(replacements['availability_repair']).values()):
        raise ValueError('Availability-only repair must not contain any standalone class letter')
    if letters(replacements['meaning_control']) != letters(annotation['old']):
        raise ValueError('Meaning control must preserve standalone class counts')
    if not letters(replacements['value_repair'])[gold]:
        raise ValueError('Value repair must explicitly contain the correct class')
    result = {'unchanged': prefix}
    for arm, text in replacements.items():
        result[arm] = prefix[:start] + text + prefix[end:]
    if any(letters(result['availability_repair'])[c] > letters(prefix)[c] for c in 'ABC'):
        raise ValueError('Availability repair adds a class letter at a text boundary')
    return result
