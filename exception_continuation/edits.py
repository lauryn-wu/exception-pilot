"""Exact-span manually certified repairs, frozen before edited continuations."""
import json
from pathlib import Path

from exception_pilot.core import digest, rng_for
from exception_pilot.storage import write_json, run_lock
from .core import read_plan, edit_prefix, final_score, letters
from .runner import sealed_read, sealed_write, validate_collection, get_backend, Session
from .backend import readout


def review_export(output, review_file=None):
    out = Path(output); plan = read_plan(out)
    collection = sealed_read(out/'collection.json'); validate_collection(plan, collection)
    path = Path(review_file) if review_file else out/'review.json'
    if path.exists(): raise ValueError('Refusing to overwrite manual review')
    rows = []
    for r in collection['rows']:
        if r['task']['arm'] != 'visible': continue
        rows.append(dict(task_id=r['task']['id'], trajectory_hash=digest(r), text=r['raw']['text'],
                         prompt=r['task']['prompt'], target_row=r['task']['target_row'],
                         reviewed=False, false_missing=None, reviewer='', justification='',
                         first_false_missing_certified=False, semantic_certified=False,
                         span=None, old='', replacements={'availability_repair': '', 'meaning_control': '', 'value_repair': ''}))
    # Source text/table visible; final outcome and readouts are not annotation fields.
    rng_for('continuation-review', plan['phase']).shuffle(rows)
    result = dict(plan_hash=plan['plan_hash'], collection_hash=collection['artifact_hash'], rows=rows)
    write_json(path, result)
    return path


def freeze_edits(output, review_file):
    with run_lock(output) as out:
        plan = read_plan(out)
        if list((out/'operations').glob('*.json')):
            # Only interventions are forbidden; collection and probes are expected.
            for file in (out/'operations').glob('*.json'):
                if sealed_read(file)['id'].startswith('edit/'):
                    raise ValueError('Edits already started; cannot freeze a new annotation plan')
        collection = sealed_read(out/'collection.json'); validate_collection(plan, collection)
        measured = sealed_read(out/'measurements.json')
        if measured['collection_hash'] != collection['artifact_hash']: raise ValueError('Measurements stale')
        review = json.loads(Path(review_file).read_text())
        if review['plan_hash'] != plan['plan_hash'] or review['collection_hash'] != collection['artifact_hash']:
            raise ValueError('Review belongs to another trajectory collection')
        rows = {r['task']['id']: r for r in collection['rows'] if r['task']['arm'] == 'visible'}
        annotations = {a['task_id']: a for a in review['rows']}
        if len(annotations) != len(review['rows']) or set(rows) != set(annotations):
            raise ValueError('Review must include every visible output exactly once')
        measures = {m['task_id']: m for m in measured['rows']}
        cases = []; excluded = []
        for tid, r in rows.items():
            a = annotations[tid]
            if (a['trajectory_hash'] != digest(r) or a['text'] != r['raw']['text'] or
                    a['prompt'] != r['task']['prompt'] or a['target_row'] != r['task']['target_row']):
                raise ValueError('Review source was changed')
            if a['reviewed'] is not True or type(a['false_missing']) is not bool or not a['reviewer'] or not a['justification']:
                raise ValueError('Review ALL outputs explicitly, including negatives and invalid answers')
            if not a['false_missing']:
                excluded.append(dict(task_id=tid, reason='reviewed_no_false_missing')); continue
            if a['first_false_missing_certified'] is not True:
                raise ValueError('Certify this is the first explicit false-missingness claim')
            # Check the annotation against full original text before choosing the fixed cut.
            edit_prefix(r['raw']['text'], a, r['task']['expected'])
            m = measures[tid]
            if m['trajectory_hash'] != digest(r): raise ValueError('Measurement trajectory changed')
            if not m['replay_passed']:
                excluded.append(dict(task_id=tid, reason='replay_failed')); continue
            options = [c for c in m['cuts'] if c['k'] > 0 and c['eligible'] and len(c['prefix']) >= a['span'][1]]
            if not options:
                excluded.append(dict(task_id=tid, reason='no_prespecified_cut_after_claim')); continue
            cut = options[0]
            if not cut['roundtrip_exact']:
                excluded.append(dict(task_id=tid, reason='unchanged_prefix_token_roundtrip_failed')); continue
            texts = edit_prefix(cut['prefix'], a, r['task']['expected'])
            cases.append(dict(task_id=tid, k=cut['k'], prefix_ids=r['raw']['tokens'][:cut['k']],
                              trajectory_hash=digest(r), annotation=a, texts=texts,
                              suffix_budget=plan['config']['max_new_tokens']-cut['k']))
        value = dict(plan_hash=plan['plan_hash'], collection_hash=collection['artifact_hash'],
                     measurements_hash=measured['artifact_hash'], review_hash=digest(review),
                     reviewed=len(rows), cases=cases, excluded=excluded)
        path = out/'edit-plan.json'
        if path.exists():
            old = sealed_read(path); old.pop('artifact_hash')
            if old != value: raise ValueError('Edit plan already frozen differently')
        return sealed_write(path, value)


def token_change(old, new):
    left = 0
    while left < min(len(old), len(new)) and old[left] == new[left]: left += 1
    right = 0
    while right < min(len(old)-left, len(new)-left) and old[len(old)-1-right] == new[len(new)-1-right]: right += 1
    return dict(old_span=[left, len(old)-right], new_span=[left, len(new)-right], delta=len(new)-len(old))


def intervene(output, live=False, mock=False, backend_override=None):
    with run_lock(output) as out:
        plan = read_plan(out); collection = sealed_read(out/'collection.json'); validate_collection(plan, collection)
        measured = sealed_read(out/'measurements.json'); edits = sealed_read(out/'edit-plan.json')
        if (edits['collection_hash'] != collection['artifact_hash'] or
                edits['measurements_hash'] != measured['artifact_hash'] or edits['plan_hash'] != plan['plan_hash']):
            raise ValueError('Stale edit plan')
        backend = get_backend(plan, live, mock) if backend_override is None else backend_override
        session = Session(out, plan, backend)
        rows = {r['task']['id']: r for r in collection['rows']}
        results = []
        for case in edits['cases']:
            row = rows[case['task_id']]; task = row['task']; original = case['prefix_ids']
            if digest(row) != case['trajectory_hash']: raise ValueError('Edited trajectory changed')
            if backend.encode(case['texts']['unchanged']) != original:
                raise ValueError('Original checkpoint no longer round trips')
            tokenized = {}; reason = None
            for arm, text in case['texts'].items():
                ids = original if arm == 'unchanged' else backend.encode(text)
                if backend.decode(ids) != text or any(t in backend.special_ids for t in ids):
                    reason = 'edited_text_roundtrip_or_special_token_failure'
                tokenized[arm] = ids
            if reason:
                results.append(dict(task_id=task['id'], eligible=False, reason=reason)); continue
            arms = list(case['texts']); rng_for('edit-order', task['id']).shuffle(arms)
            observations = {}
            for arm in arms:
                prefix_ids = tokenized[arm]
                raw = session.generate(f"edit/{task['id']}/{arm}/continuation", row['input_ids'] + prefix_ids, case['suffix_budget'])
                full_text = backend.decode(prefix_ids + raw['tokens'])
                prefix_preserved = full_text.startswith(case['texts'][arm])
                req = dict(input_ids=row['input_ids'], prefix_ids=prefix_ids, gold=task['expected'], pattern=task['pattern'])
                probe = session.operation(f"edit/{task['id']}/{arm}/readout", req, lambda req=req: readout(backend, **req))
                observations[arm] = dict(prefix_ids=prefix_ids, prefix_text=case['texts'][arm], raw=raw,
                    full_text=full_text, full_tokens=prefix_ids + raw['tokens'], prefix_text_preserved=prefix_preserved, readout=probe,
                    score=final_score(full_text, raw['stopped'] and prefix_preserved, task['expected']),
                    changed_tokens=token_change(original, prefix_ids), class_counts=letters(case['texts'][arm]),
                    character_delta=len(case['texts'][arm])-len(case['texts']['unchanged']))
            unchanged = observations['unchanged']['raw']
            replay_ok = unchanged['tokens'] == row['raw']['tokens'][case['k']:] and unchanged['stopped'] == row['raw']['stopped']
            results.append(dict(task_id=task['id'], world=task['world'], k=case['k'], eligible=True,
                                unchanged_replay_passed=replay_ok, arms=observations))
        return sealed_write(out/'interventions.json', dict(plan_hash=plan['plan_hash'],
            edit_plan_hash=edits['artifact_hash'], collection_hash=collection['artifact_hash'],
            backend_hash=session.backend_hash, rows=results))
