"""Frozen secondary event cuts on original trajectories, never edited streams."""
from collections import Counter, defaultdict
from pathlib import Path

from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from .core import read_plan, statement_cut, EVENT_VERSION
from .runner import sealed_read, sealed_write, validate_collection, get_backend, Session
from .backend import readout
from .validation import replay_check


def before_boundary(row, position):
    """Latest exact prefix before position, allowing only intervening whitespace."""
    text = row['raw']['text']
    boundaries = [dict(k=0, char_end=0, roundtrip_exact=True)] + row['boundaries']
    for cut in reversed(boundaries):
        n = cut['char_end']
        if n > position: continue
        if text[n:position].strip(): return None, 'no_token_boundary_immediately_before_event'
        if not cut['roundtrip_exact']: return None, 'prefix_token_roundtrip_failed'
        return dict(cut, prefix=text[:n]), None
    return None, 'no_token_boundary_immediately_before_event'


def event_cuts(row, annotation, names):
    text = row['raw']['text']; marker = text.find('ANSWER:')
    result = []
    for name in names:
        cut = None; reason = None
        if name == 'before_answer':
            if marker < 0: reason = 'no_answer_marker'
            else: cut, reason = before_boundary(row, marker)
        elif not annotation['false_missing']:
            reason = 'reviewed_no_false_missing'
        elif marker >= 0 and annotation['statement_span'][1] > marker:
            reason = 'statement_not_before_final_answer'
        elif name == 'before_statement':
            cut, reason = before_boundary(row, annotation['statement_span'][0])
        else:
            cut, reason = statement_cut(row, annotation)
        result.append(dict(event=name, eligible=cut is not None, reason=reason,
                           **(cut or {'k': None, 'char_end': None})))
    return result


def freeze_events(output):
    with run_lock(output) as out:
        plan = read_plan(out); collection = sealed_read(out/'collection.json')
        validate_collection(plan, collection)
        edits = sealed_read(out/'edit-plan.json')
        if edits['plan_hash'] != plan['plan_hash'] or edits['collection_hash'] != collection['artifact_hash']:
            raise ValueError('Stale event annotations')
        annotations = {a['task_id']: a for a in edits['review_rows']}
        rows = []
        for row in collection['rows']:
            if row['task']['arm'] != 'visible': continue
            a = annotations[row['task']['id']]
            if a['trajectory_hash'] != digest(row): raise ValueError('Event annotation source changed')
            rows.append(dict(task_id=row['task']['id'], trajectory_hash=digest(row),
                cuts=event_cuts(row, a, plan['config']['event_checkpoints'])))
        value = dict(version=EVENT_VERSION, plan_hash=plan['plan_hash'],
                     collection_hash=collection['artifact_hash'], edit_plan_hash=edits['artifact_hash'], rows=rows)
        path = out/'event-plan.json'
        if path.exists():
            old = sealed_read(path); old.pop('artifact_hash')
            if old != value: raise ValueError('Event annotations already frozen')
        else:
            for p in (out/'operations').glob('*.json'):
                if sealed_read(p)['id'].startswith('event/'):
                    raise ValueError('Cannot freeze annotations after event operations started')
        return sealed_write(path, value)


def measure_events(output, live=False, mock=False, backend_override=None):
    with run_lock(output) as out:
        plan = read_plan(out); collection = sealed_read(out/'collection.json')
        validate_collection(plan, collection)
        frozen = sealed_read(out/'event-plan.json'); edits = sealed_read(out/'edit-plan.json')
        if (frozen['version'] != EVENT_VERSION or frozen['plan_hash'] != plan['plan_hash']
                or frozen['collection_hash'] != collection['artifact_hash']
                or frozen['edit_plan_hash'] != edits['artifact_hash']):
            raise ValueError('Stale frozen event plan')
        backend = get_backend(plan, live, mock) if backend_override is None else backend_override
        session = Session(out, plan, backend)
        technical = sealed_read(out/'validation.json')
        if (not technical['passed'] or technical['artifact_hash'] != collection['validation_hash']
                or collection['backend_hash'] != session.backend_hash):
            raise ValueError('Technical validation/backend mismatch')
        originals = {r['task']['id']: r for r in collection['rows']}
        results = []
        for item in frozen['rows']:
            tid = item['task_id']; row = originals[tid]; task = row['task']
            if item['trajectory_hash'] != digest(row): raise ValueError('Event trajectory changed')
            ks = sorted({c['k'] for c in item['cuts'] if c['eligible']})
            bycut = {}; reference = None
            if ks:
                reference = session.generate(f'event/{tid}/reference', row['input_ids'], 512, capture_at=ks)
                matches = all(reference[key] == row['raw'][key] for key in ('tokens', 'finish', 'stopped'))
                for k in ks:
                    replay = session.generate(f'event/{tid}/replay/{k}', row['input_ids'] + row['raw']['tokens'][:k], 512-k, capture_at=(0,))
                    check = replay_check(reference, replay, k, plan['config']['validation_tolerances'])
                    check.update(passed=matches and check['passed'], uninterrupted_matches_saved=matches, replay=replay)
                    if check['passed']:
                        req = dict(input_ids=row['input_ids'], prefix_ids=row['raw']['tokens'][:k],
                                   gold=task['expected'], pattern=task['pattern'])
                        check['readout'] = session.operation(f'event/{tid}/readout/{k}', req,
                                                             lambda req=req: readout(backend, **req))
                    bycut[k] = check
            cuts = [dict(c, **bycut[c['k']]) if c['eligible'] else dict(c) for c in item['cuts']]
            results.append(dict(task_id=tid, reference=reference, cuts=cuts,
                                any_checkpoint_failed=any(c['eligible'] and not c.get('passed') for c in cuts)))
        return sealed_write(out/'event-measurements.json', dict(version=EVENT_VERSION,
            event_plan_hash=frozen['artifact_hash'], collection_hash=collection['artifact_hash'],
            backend_hash=session.backend_hash,
            real_model_status='PENDING' if backend.simulated else 'SEE_PER_CHECKPOINT_VALIDATION', rows=results))


def summarize_events(plan, data):
    from .analysis import clustered
    tasks = {t['id']: t for t in plan['tasks']}
    coverage = {name: dict(planned=0, eligible=0, replay_valid=0, measured=0, unavailable_reasons={})
                for name in plan['config']['event_checkpoints']}
    values = defaultdict(lambda: defaultdict(dict)); changes = defaultdict(dict)
    for row in data['rows']:
        task = tasks[row['task_id']]; cuts = {c['event']: c for c in row['cuts']}
        for name, c in cuts.items():
            n = coverage[name]; n['planned'] += 1; n['eligible'] += c['eligible']
            n['replay_valid'] += c.get('passed') is True
            if c.get('passed') and 'readout' in c:
                n['measured'] += 1
                values[name][task['world']][task['variant']] = c['readout']['gold_pattern_log_odds']
            else:
                reason = c.get('reason') or 'replay_failed'
                n['unavailable_reasons'][reason] = n['unavailable_reasons'].get(reason, 0) + 1
        if all(cuts.get(n, {}).get('passed') and 'readout' in cuts[n] for n in ('before_statement', 'after_statement')):
            changes[task['world']][task['variant']] = (cuts['after_statement']['readout']['gold_pattern_log_odds']
                                                       - cuts['before_statement']['readout']['gold_pattern_log_odds'])
    complete = lambda worlds: {w: list(v.values()) for w, v in worlds.items() if set(v) == {0, 1}}
    return dict(version=EVENT_VERSION, secondary=True, real_model_status=data['real_model_status'],
                coverage=coverage, checkpoint_means={n: clustered(complete(v)) for n, v in values.items()},
                after_minus_before_statement=clustered(complete(changes)),
                trajectories_with_any_failed_checkpoint=sum(r['any_checkpoint_failed'] for r in data['rows']),
                interpretation='Secondary event-conditioned answer preferences; fixed 64-minus-0 remains primary.')
