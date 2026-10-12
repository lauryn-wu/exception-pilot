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
        entries.append(dict(world=key[0], variant=key[1], rotation=key[2],
                            before_after_match=len({pos(g[p + '/' + a]) for p in ('before', 'after') for a in ('direct', 'visible')}) == 1 if measured else None,
                            quartet_match=len({pos(t) for t in g.values()}) == 1 if measured else None,
                            positions={o: t['position'] for o, t in g.items()}))
    return dict(tokenizer=plan['tokenizer'], comparisons=entries,
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
