"""Stage-separated, hash-bound operation journal. No implicit generation."""
import json
from pathlib import Path

from exception_pilot.core import digest
from exception_pilot.storage import write_json, run_lock
from .core import make_plan, read_plan, final_score, eligible_cuts, TECHNICAL
from .backend import LocalBackend, MockBackend, readout


def sealed_write(path, value):
    value = dict(value)
    value['artifact_hash'] = digest({k: v for k, v in value.items() if k != 'artifact_hash'})
    write_json(path, value)
    return value


def sealed_read(path):
    value = json.loads(Path(path).read_text())
    if value.get('artifact_hash') != digest({k: v for k, v in value.items() if k != 'artifact_hash'}):
        raise ValueError('Artifact integrity failure: ' + str(path))
    return value


def prepare(output, phase, config=None, selection_output=None, selection_note=None):
    lock = None
    if phase == 'confirmation':
        if not selection_output or not selection_note:
            raise ValueError('Confirmation needs --selection-output and --selection-note')
        old = read_plan(selection_output)
        if old['phase'] != 'selection': raise ValueError('Expected a selection run')
        collection = sealed_read(Path(selection_output)/'collection.json')
        backend = sealed_read(Path(selection_output)/'execution.json')
        validate_collection(old, collection)
        if config != old['config']: raise ValueError('Chosen configuration must match selection')
        lock = dict(plan_hash=old['plan_hash'], collection_hash=collection['artifact_hash'],
                    backend_hash=backend['backend_hash'], mode=backend['mode'], note=selection_note,
                    selection_descriptives=collection_summary(collection))
    plan = make_plan(phase, config, lock)
    with run_lock(output) as out:
        path = out/'plan.json'
        if path.exists() and json.loads(path.read_text()) != plan:
            raise ValueError('Refusing to overwrite plan')
        write_json(path, plan)
        write_json(out/'preview.json', [{'id': t['id'], 'messages': [{'role': 'user', 'content': t['prompt']}]} for t in plan['tasks']])
        (out/'preview.md').write_text('# Unmodified trajectory prompts; no outputs\n\n' + '\n\n'.join(
            '## ' + t['id'] + '\n\n```text\n' + t['prompt'] + '\n```' for t in plan['tasks'][:4]))
    return plan


class Session:
    def __init__(self, output, plan, backend):
        self.out, self.plan, self.backend = Path(output), plan, backend
        self.backend_hash = digest(backend.identity)
        mode = 'SIMULATED' if backend.simulated else 'LIVE_LOCAL'
        identity = dict(plan_hash=plan['plan_hash'], mode=mode, backend=backend.identity, backend_hash=self.backend_hash)
        path = self.out/'execution.json'
        if path.exists():
            old = sealed_read(path); old.pop('artifact_hash')
            if old != identity: raise ValueError('Backend/config/live-mock identity changed')
        else:
            if plan['phase'] == 'confirmation' and (plan['selection_lock']['backend_hash'] != self.backend_hash or plan['selection_lock']['mode'] != mode):
                raise ValueError('Confirmation backend does not match selected backend')
            sealed_write(path, identity)
        for f in sorted((self.out/'operations').glob('*.json')):
            e = sealed_read(f)
            if e['plan_hash'] != plan['plan_hash'] or e['backend_hash'] != self.backend_hash:
                raise ValueError('Operation identity changed')
            if e['status'] != 'returned':
                raise ValueError('Unresolved operation; no automatic retry: ' + e['id'])

    def operation(self, op_id, request, fn):
        path = self.out/'operations'/(digest(op_id) + '.json')
        identity = dict(id=op_id, plan_hash=self.plan['plan_hash'], backend_hash=self.backend_hash, request=request)
        if path.exists():
            old = sealed_read(path)
            if any(old[k] != v for k, v in identity.items()) or old['status'] != 'returned':
                raise ValueError('Operation changed or unresolved')
            return old['result']
        e = dict(identity, status='started'); sealed_write(path, e)
        try:
            result = fn()
        except Exception as exc:
            e.update(status='error', error_type=type(exc).__name__); sealed_write(path, e); raise
        e.update(status='returned', result=result); sealed_write(path, e)
        return result

    def generate(self, op_id, ids, budget):
        return self.operation(op_id, {'input_ids': ids, 'budget': budget}, lambda: self.backend.generate(ids, budget))


def get_backend(plan, live=False, mock=False):
    if live == mock: raise ValueError('Choose exactly one of --mock or --live')
    return MockBackend() if mock else LocalBackend(plan['config'])


def validate(session):
    backend = session.backend
    records, passed = [], True
    for i, prompt in enumerate(TECHNICAL):
        ids = backend.prompt(prompt)
        base = session.generate(f'technical/{i}/base', ids, 128)
        cuts = [k for k in (1, 8, 16, 32) if k < len(base['tokens']) and not any(t in backend.special_ids for t in base['tokens'][:k])]
        if not cuts: passed = False
        replays = []
        for k in cuts:
            r = session.generate(f'technical/{i}/replay/{k}', ids + base['tokens'][:k], 128-k)
            same = r['tokens'] == base['tokens'][k:] and r['stopped'] == base['stopped']
            passed = passed and same
            replays.append(dict(k=k, exact_suffix_match=same, response=r))
        records.append(dict(input_ids=ids, base=base, replays=replays))
    report = sealed_write(session.out/'validation.json', dict(plan_hash=session.plan['plan_hash'],
        backend_hash=session.backend_hash, passed=passed, mode='SIMULATED' if backend.simulated else 'LIVE_LOCAL', records=records))
    if not passed: raise ValueError('Exact continuation validation FAILED; collection blocked')
    return report


def collect(output, live=False, mock=False, backend_override=None):
    with run_lock(output) as out:
        plan = read_plan(out)
        backend = get_backend(plan, live, mock) if backend_override is None else backend_override
        session = Session(out, plan, backend); validation = validate(session)
        rows = []
        for task in plan['tasks']:
            ids = backend.prompt(task['prompt'])
            raw = session.generate('trajectory/' + task['id'], ids, plan['config']['max_new_tokens'])
            rows.append(dict(task=task, input_ids=ids, raw=raw, score=final_score(raw['text'], raw['stopped'], task['expected'])))
        collection = dict(plan_hash=plan['plan_hash'], backend_hash=session.backend_hash,
                          validation_hash=validation['artifact_hash'], rows=rows)
        return sealed_write(out/'collection.json', collection)


def validate_collection(plan, collection):
    if collection['plan_hash'] != plan['plan_hash'] or [r['task'] for r in collection['rows']] != plan['tasks']:
        raise ValueError('Collection does not contain the exact full plan')


def collection_summary(collection):
    result = {}
    for arm in ('direct', 'visible'):
        rows = [r for r in collection['rows'] if r['task']['arm'] == arm]
        result[arm] = dict(planned=len(rows), valid=sum(r['score']['valid'] for r in rows),
                           correct=sum(r['score']['correct'] is True for r in rows),
                           pattern=sum(r['score']['answer'] == r['task']['pattern'] for r in rows))
    return result


def measure(output, live=False, mock=False, backend_override=None):
    with run_lock(output) as out:
        plan = read_plan(out); collection = sealed_read(out/'collection.json'); validate_collection(plan, collection)
        backend = get_backend(plan, live, mock) if backend_override is None else backend_override
        session = Session(out, plan, backend)
        if collection['backend_hash'] != session.backend_hash: raise ValueError('Collection backend changed')
        validation = sealed_read(out/'validation.json')
        if not validation['passed'] or validation['artifact_hash'] != collection['validation_hash']:
            raise ValueError('Unchanged-prefix validation not passed')
        rows = []
        for row in collection['rows']:
            t = row['task']
            if t['arm'] != 'visible': continue
            tokens, ids = row['raw']['tokens'], row['input_ids']
            cuts = eligible_cuts(backend, tokens)
            passed = True
            for cut in cuts:
                k = cut['k']
                if not cut['eligible']: continue
                response = session.generate(f"replay/{t['id']}/{k}", ids + tokens[:k], plan['config']['max_new_tokens']-k)
                cut['replay'] = response
                cut['exact_suffix_match'] = response['tokens'] == tokens[k:] and response['stopped'] == row['raw']['stopped']
                cut['roundtrip_exact'] = backend.encode(cut['prefix']) == tokens[:k]
                passed = passed and cut['exact_suffix_match']
            # Validation completes for ALL cuts before any readout on this trajectory.
            if passed:
                for cut in cuts:
                    if not cut['eligible']: continue
                    k = cut['k']
                    req = dict(input_ids=ids, prefix_ids=tokens[:k], gold=t['expected'], pattern=t['pattern'])
                    cut['readout'] = session.operation(f"readout/{t['id']}/{k}", req,
                        lambda req=req: readout(backend, **req))
            rows.append(dict(task_id=t['id'], trajectory_hash=digest(row), replay_passed=passed, cuts=cuts))
        return sealed_write(out/'measurements.json', dict(plan_hash=plan['plan_hash'],
             collection_hash=collection['artifact_hash'], backend_hash=session.backend_hash, rows=rows))
