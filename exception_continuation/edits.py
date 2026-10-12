"""Exact-span manually certified repairs, frozen before edited continuations."""
import json
from pathlib import Path

from exception_pilot.core import digest, rng_for
from exception_pilot.storage import write_json, run_lock
from .core import read_plan, edit_prefix, final_score, letters, statement_cut
from .runner import sealed_read, sealed_write, validate_collection, get_backend, Session, validate_intervention_case
from .backend import readout
from .validation import replay_check


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
                         statement_span=None, statement='', grammar_certified=False, span=None, old='', replacements={'availability_repair': '', 'meaning_control': '', 'value_repair': ''}))
    # Source text/table visible; final outcome and readouts are not annotation fields.
    rng_for('continuation-review', plan['phase']).shuffle(rows)
    result = dict(plan_hash=plan['plan_hash'], collection_hash=collection['artifact_hash'],
                  selection_basis='predeclared_first_false_missingness', no_2a_selection_attested=False, rows=rows)
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
        review = json.loads(Path(review_file).read_text())
        if review['plan_hash'] != plan['plan_hash'] or review['collection_hash'] != collection['artifact_hash']:
            raise ValueError('Review belongs to another trajectory collection')
        if review.get('selection_basis') not in ('predeclared_first_false_missingness', '2A_informed_discovery'):
            raise ValueError('Declare the edit selection basis')
        if plan['phase'] == 'confirmation' and (review['selection_basis'] != 'predeclared_first_false_missingness' or review.get('no_2a_selection_attested') is not True):
            raise ValueError('2A-informed edits are discovery only; confirmation needs the frozen rule and no-2A-selection attestation')
        rows = {r['task']['id']: r for r in collection['rows'] if r['task']['arm'] == 'visible'}
        annotations = {a['task_id']: a for a in review['rows']}
        if len(annotations) != len(review['rows']) or set(rows) != set(annotations):
            raise ValueError('Review must include every visible output exactly once')
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
            if a.get('grammar_certified') is not True:
                raise ValueError('Certify grammatical factual repair and meaning-preserving control')
            edit_prefix(r['raw']['text'], a, r['task']['expected'])
            cut, reason = statement_cut(r, a)
            if cut is None:
                excluded.append(dict(task_id=tid, reason=reason)); continue
            texts = edit_prefix(cut['prefix'], a, r['task']['expected'])
            cases.append(dict(task_id=tid, k=cut['k'], prefix_ids=r['raw']['tokens'][:cut['k']],
                              trajectory_hash=digest(r), annotation=a, texts=texts, boundary_char_end=cut['char_end'],
                              trailing_whitespace=r['raw']['text'][a['statement_span'][1]:cut['char_end']],
                              suffix_budget=plan['config']['max_new_tokens']-cut['k']))
        value = dict(plan_hash=plan['plan_hash'], collection_hash=collection['artifact_hash'],
                     selection_basis=review['selection_basis'], no_2a_selection_attested=review['no_2a_selection_attested'], review_hash=digest(review),
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
        edits = sealed_read(out/'edit-plan.json')
        if (edits['collection_hash'] != collection['artifact_hash'] or
                edits['plan_hash'] != plan['plan_hash']):
            raise ValueError('Stale edit plan')
        backend = get_backend(plan, live, mock) if backend_override is None else backend_override
        session = Session(out, plan, backend)
        technical = sealed_read(out/'validation.json')
        if not technical['passed'] or technical['artifact_hash'] != collection['validation_hash']:
            raise ValueError('Technical replay validation must pass before interventions')
        rows = {r['task']['id']: r for r in collection['rows']}
        results = []
        for case in edits['cases']:
            row = rows[case['task_id']]; task = row['task']; original = case['prefix_ids']
            if digest(row) != case['trajectory_hash']: raise ValueError('Edited trajectory changed')
            if backend.encode(case['texts']['unchanged']) != original:
                raise ValueError('Original checkpoint no longer round trips')
            validation = validate_intervention_case(session, row, case)
            if not validation['passed']:
                results.append(dict(task_id=task['id'], eligible=True, reason='branch_validation_failed', validation=validation, unchanged_replay_passed=False))
                continue
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
                raw = session.generate(f"edit/{task['id']}/{arm}/continuation", row['input_ids'] + prefix_ids, case['suffix_budget'], capture_at=(0,))
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
            control_check = replay_check(validation['reference'], unchanged, case['k'], plan['config']['validation_tolerances'])
            replay_ok = control_check['passed']
            results.append(dict(task_id=task['id'], world=task['world'], k=case['k'], eligible=True,
                                unchanged_replay_passed=replay_ok, validation=validation, control_validation=control_check,
                                same_response_validated=not backend.simulated and replay_ok, arms=observations))
        artifact = sealed_write(out/'interventions.json', dict(plan_hash=plan['plan_hash'],
            edit_plan_hash=edits['artifact_hash'], collection_hash=collection['artifact_hash'],
            backend_hash=session.backend_hash,
            real_model_status='PENDING' if backend.simulated else ('VALIDATED_FOR_RECORDED_CASES' if results and all(r.get('same_response_validated') for r in results) else 'INCOMPLETE_OR_FAILED'),
            rows=results))
        sealed_write(out/'validation-status.json', dict(plan_hash=plan['plan_hash'],
            validation_hash=technical['artifact_hash'],
            real_model_status='PENDING' if backend.simulated else 'TECHNICAL_PASSED',
            per_intervention_validation=artifact['real_model_status'],
            interventions_hash=artifact['artifact_hash'], mode='SIMULATED' if backend.simulated else 'LIVE_LOCAL'))
        return artifact
