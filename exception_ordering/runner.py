"""Offline preparation and explicit single-attempt collection."""
import hashlib
import json
from pathlib import Path

from exception_pilot.core import digest
from exception_pilot.storage import write_json, run_lock
from exception_mistral_prefix.provider import complete
from .core import make_plan, read_plan, score, CONFIG


def prepare(output, tokenizer_file=None, tokenizer_model=None):
    tokenizer = provenance = None
    if tokenizer_file:
        if tokenizer_model != CONFIG['model']:
            raise ValueError('Attest the matching model using --tokenizer-model')
        from tokenizers import Tokenizer
        p = Path(tokenizer_file)
        tokenizer = Tokenizer.from_file(str(p))
        tokenizer.no_truncation(); tokenizer.no_padding()
        provenance = dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                          model=tokenizer_model, truncation=False, padding=False,
                          attestation='user_supplied_not_server_verified')
    elif tokenizer_model:
        raise ValueError('--tokenizer-model requires --tokenizer-json')
    plan = make_plan(tokenizer, provenance)
    with run_lock(output) as out:
        path = out / 'plan.json'
        if path.exists():
            if json.loads(path.read_text()) != plan:
                raise ValueError('Refusing to overwrite a different plan')
            return plan
        write_json(path, plan)
        write_json(out / 'preview.json', [dict(id=t['id'], request=t['request']) for t in plan['tasks']])
        (out / 'preview.md').write_text('# Exact request sample; no model results\n\n' + '\n\n'.join(
            '## ' + t['id'] + '\n\n```text\n' + t['request']['messages'][0]['content'] + '\n```'
            for t in plan['tasks'][:16]))
        write_json(out / 'position-audit.json', position_report(plan))
    return plan


def position_report(plan):
    groups = {}
    for t in plan['tasks']:
        groups.setdefault((t['world'], t['variant'], t['rotation']), {})[t['placement'] + '/' + t['arm']] = t
    entries = []
    for key, g in groups.items():
        measured = all(t['position']['status'] != 'UNMEASURED' for t in g.values())
        def pos(t):
            return tuple(t['position']['token_spans'][s][0] for s in ('plate', 'class'))
        details = {}
        for name, task in g.items():
            p = dict(task['position'])
            p['target_to_query_tokens'] = None
            if p['status'] != 'UNMEASURED':
                spans = p['token_spans']; query = spans['query_plate'][0]
                p['target_to_query_tokens'] = dict(
                    plate_start_to_query_start=query-spans['plate'][0],
                    class_start_to_query_start=query-spans['class'][0],
                    row_end_to_query_start=query-spans['row'][1])
            details[name] = p
        deltas = {}
        for arm in ('direct', 'visible'):
            before, after = details['before/'+arm], details['after/'+arm]
            deltas[arm] = None if not measured else dict(
                plate_start=after['token_spans']['plate'][0]-before['token_spans']['plate'][0],
                class_start=after['token_spans']['class'][0]-before['token_spans']['class'][0],
                user_message_tokens=after['tokens']-before['tokens'],
                target_to_query_tokens={k: after['target_to_query_tokens'][k]-v
                                        for k,v in before['target_to_query_tokens'].items()})
        entries.append(dict(world=key[0], variant=key[1], rotation=key[2],
                            before_after_match=len({pos(g[p + '/' + a]) for p in ('before', 'after') for a in ('direct', 'visible')}) == 1 if measured else None,
                            quartet_match=len({pos(t) for t in g.values()}) == 1 if measured else None,
                            positions=details, after_minus_before=deltas))
    worlds = {}
    for e in entries:
        w = worlds.setdefault(e['world'], dict(planned_blocks=0, measured_blocks=0, matched_blocks=0,
                                              matched_rotations_by_variant={'0': [], '1': []}))
        w['planned_blocks'] += 1
        w['measured_blocks'] += e['before_after_match'] is not None
        if e['before_after_match']:
            w['matched_blocks'] += 1
            w['matched_rotations_by_variant'][str(e['variant'])].append(e['rotation'])
    for w in worlds.values():
        rotations = w['matched_rotations_by_variant']
        w['matched_rotations_with_both_variants'] = sorted(set(rotations['0']) & set(rotations['1']))
    measured_count = sum(e['before_after_match'] is not None for e in entries)
    matched_count = sum(e['before_after_match'] is True for e in entries)
    coverage = dict(planned_blocks=len(entries), measured_blocks=measured_count,
        matched_blocks=matched_count, unmatched_blocks=measured_count-matched_count,
        unmeasured_blocks=len(entries)-measured_count, planned_worlds=len(worlds),
        worlds_with_any_match=sum(w['matched_blocks'] > 0 for w in worlds.values()),
        worlds_with_both_variants_at_a_matched_rotation=sum(bool(w['matched_rotations_with_both_variants']) for w in worlds.values()),
        worlds_with_all_blocks_matched=sum(w['matched_blocks'] == w['planned_blocks'] for w in worlds.values()),
        matched_fraction_of_measured=matched_count/measured_count if measured_count else None,
        by_world=worlds)
    status = 'PENDING' if not measured_count else 'INPUT_ONLY_USER_ATTESTED'
    assessment = ('Cannot assess useful matched coverage: model-matched tokenizer unavailable; zero measured blocks is not evidence of zero matches.'
                  if not measured_count else 'No matched before/after blocks; token-matched secondary analysis unavailable.'
                  if not matched_count else 'Input-matched subset available; inspect block/world and both-variant coverage. No sufficiency threshold or primary-design change is implied.')
    return dict(report_version='ordering-input-audit-v2', status=status,
                scope='Complete user message only; provider chat serialization is NOT verified.',
                primary_control='Fixed target row 5; target token position is not guaranteed.',
                matched_subset_role='Secondary diagnostic only; full planned sample remains primary.',
                planned_responses=len(plan['tasks']), execution='Sequential, one response at a time; no automatic sample reduction or extension.',
                coverage=coverage, coverage_assessment=assessment,
                tokenizer=plan['tokenizer'], comparisons=entries,
                matched_before_after=sum(e['before_after_match'] is True for e in entries),
                measured=sum(e['before_after_match'] is not None for e in entries))


def journal(out, plan):
    entries = []
    by_id = {t['id']: t for t in plan['tasks']}
    seen = set()
    for file in sorted((Path(out) / 'attempts').glob('*.json')):
        e = json.loads(file.read_text())
        if (e['task_id'] not in by_id or e['task_id'] in seen or e['plan_hash'] != plan['plan_hash']
                or e['request'] != by_id[e['task_id']]['request'] or
                e.get('entry_hash') != digest({k: v for k, v in e.items() if k != 'entry_hash'})):
            raise ValueError('Attempt journal changed')
        seen.add(e['task_id']); entries.append(e)
    return entries


def save(path, entry):
    entry['entry_hash'] = digest({k: v for k, v in entry.items() if k != 'entry_hash'})
    write_json(path, entry)


def run(output, *, live=False, mock=False, max_calls=0, accept_provenance=False, transport=None):
    if live == mock or max_calls <= 0:
        raise ValueError('Choose exactly --mock or --live, and a positive --max-calls')
    with run_lock(output) as out:
        p = read_plan(out)
        if live and (not p['tokenizer'] or not accept_provenance):
            raise ValueError('Live needs a measured tokenizer audit and --accept-tokenizer-provenance')
        mode = 'SIMULATED' if mock else 'LIVE'
        identity = dict(mode=mode, plan_hash=p['plan_hash'])
        ep = out / 'execution.json'
        if ep.exists() and json.loads(ep.read_text()) != identity:
            raise ValueError('Cannot mix live/mock or plans')
        write_json(ep, identity)
        entries = journal(out, p)
        if any(e['status'] != 'returned' or e.get('identity_failure') for e in entries):
            raise ValueError('Unresolved attempt or model mismatch; manual review required')
        done = {e['task_id'] for e in entries}; calls = 0
        for task in p['tasks']:
            if task['id'] in done:
                continue
            if calls >= max_calls:
                break
            index = len(entries) + calls + 1
            e = dict(task_id=task['id'], plan_hash=p['plan_hash'], mode=mode,
                     request=task['request'], status='started')
            path = out / 'attempts' / f'{index:06d}.json'
            save(path, e)
            try:
                if mock:
                    text = ('Simulated reasoning.\n' if task['arm'] == 'visible' else '') + 'ANSWER: ' + task['expected']
                    response = dict(text=text, complete=True, model=p['config']['model'],
                                    raw_response={'SIMULATED': True, 'text': text})
                else:
                    config = dict(p['config'], endpoint='https://api.mistral.ai/v1/chat/completions')
                    response = (transport or complete)(config, task['request'])
                e.update(status='returned', response=response,
                         identity_failure=response.get('model') != p['config']['model'])
                if e['identity_failure']:
                    response['complete'] = False
                e['score'] = score(task, response)
                save(path, e)
                calls += 1
                if e['identity_failure']:
                    raise ValueError('Model identity mismatch; stopped')
            except Exception as exc:
                if e['status'] == 'started':
                    e.update(status='error', error_type=type(exc).__name__)
                    save(path, e)
                raise
        return dict(mode=mode, new_calls=calls, planned=len(p['tasks']))
