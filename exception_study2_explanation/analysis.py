"""Predeclared matched contrasts, with explicit unavailable and unscorable counts."""
from collections import Counter, defaultdict
from statistics import mean
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_study2_native.recovery import state, summary as recovery_summary
from exception_study2_source_report.reporting import WorldBootstrap
from . import VERSION, STOP
from .parsing import parse_result

ARMS = ('explanation', 'direct', 'native_on')
LIMITATIONS = [
    'Matched diagnostic; not a novel mechanism or sufficient evidence for a paper.',
    'Four shared construction blocks are the primary resampling units. The 24-world interval is a sensitivity analysis; 96 responses are not 96 independent worlds.',
    'An all-perfect [0, 0] bootstrap interval only resamples these observed outcomes; it does not establish population certainty.',
    'Native-ON comparisons are descriptive. There is no native-ON-plus-explanation arm, so this experiment cannot show native thinking protects against an explanation request.',
    'Written output and the instruction effect on task interpretation are not isolated.',
    'Semantic trace annotations remain not reviewed; nonempty preceding text is only an explanation-format observation.'
]


def cases(c, current):
    rows = []
    originals = {r['cell']['id']: r for r in c.source.plan['requests']}
    for r in c.requests:
        op = current[r['cell']['id']]; status = state(op)
        raw = op['result'] if status == 'returned' else None
        controls = {}
        for arm, ref in r['request']['controls'].items():
            key = ref['cell_id']
            controls[arm] = dict(reference=ref, cell=originals[key]['cell'], score=c.source.scores[key],
                                 raw=c.source.operations[key]['result'], operation_status='historical_returned')
        rows.append(dict(cell=r['cell'], request_hash=r['request_hash'], operation_status=status,
                         operation_hash=op['artifact_hash'] if op else None, raw=raw,
                         score=parse_result(raw, r['request'], c.tok) if status == 'returned' else None,
                         controls=controls))
    return rows


def arm_rows(rows, arm):
    return rows if arm == 'explanation' else [r['controls'][arm] for r in rows]


def summarize(rows):
    n = len(rows); returned = [r for r in rows if r['score'] is not None]
    unavailable = n-len(returned); correct = sum(bool(r['score']['correct']) for r in returned)
    wrong = [r for r in returned if r['score']['valid'] and not r['score']['correct']]
    conflict = [r for r in wrong if r['cell']['relation'] == 'conflict']
    pattern = sum(r['score']['answer'] == r['cell']['pattern'] for r in conflict)
    categories = Counter(r['score'].get('category', r['score'].get('parsing_status')) for r in returned)
    return dict(planned=n, returned=len(returned), unavailable=unavailable, correct=correct,
                accuracy=correct/n if n and not unavailable else None,
                accuracy_bounds=[correct/n, (correct+unavailable)/n] if n else None,
                valid_wrong_labels=len(wrong), conflict_pattern_errors=pattern,
                conflict_other_wrong_labels=len(conflict)-pattern,
                invalid=sum(not r['score']['valid'] for r in returned),
                truncated=sum(r['score']['truncated'] for r in returned),
                malformed=sum(r['score']['malformed'] for r in returned),
                missing_answer=sum(r['score'].get('missing_answer', r['score'].get('missing_final', False)) for r in returned),
                explanation_format_compliant=sum(r['score'].get('explanation_format_compliant', False) for r in returned),
                categories=dict(categories))


def primary_contrast(rows):
    result = dict(definition='(explanation support - explanation conflict) - (OFF/direct support - OFF/direct conflict)',
                  sign='Positive means an additional conflict penalty under the explanation instruction.',
                  estimate=None, block_interval_95=None, world_sensitivity=None, unavailable=sum(r['score'] is None for r in rows))
    if result['unavailable']:
        return result
    worlds = defaultdict(list)
    for row in rows:
        worlds[row['cell']['world']].append(row)
    values = []; world_values = []
    for world, xs in sorted(worlds.items()):
        rates = {}
        for arm in ('explanation', 'direct'):
            for relation in ('support', 'conflict'):
                pair = [r for r in arm_rows(xs, arm) if r['cell']['relation'] == relation]
                if len(pair) != 2 or {r['cell']['variant'] for r in pair} != {0, 1}:
                    raise ValueError('Incomplete world contrast')
                rates[arm, relation] = mean(int(r['score']['correct']) for r in pair)
        effect = rates['explanation', 'support']-rates['explanation', 'conflict']-rates['direct', 'support']+rates['direct', 'conflict']
        values.append((xs[0]['cell']['block'], effect)); world_values.append((world, effect))
    if len(worlds) != 24 or set(b for b, _ in values) != set(range(4)):
        raise ValueError('Expected the four original construction blocks and 24 worlds')
    blocks = WorldBootstrap(range(4)).estimate(values)
    blocks.update(unit='construction_block', observed_clusters=blocks.pop('observed_worlds'),
                  planned_clusters=blocks.pop('planned_worlds'),
                  method='Resample four construction blocks; retain six worlds and both variants in each; average paired world contrasts.')
    sensitivity = WorldBootstrap(sorted(worlds)).estimate(world_values)
    return dict(result, estimate=blocks['estimate'], block_interval_95=blocks['interval_95'], block_bootstrap=blocks,
                world_sensitivity=dict(sensitivity, label='24-world sensitivity analysis; ignores shared construction-family dependence'),
                world_contrasts=dict(world_values))


def paired_changes(rows, control):
    result = {}
    for relation in ('support', 'conflict'):
        selected = [r for r in rows if r['cell']['relation'] == relation]; counts = Counter()
        for row in selected:
            a, b = row['score'], row['controls'][control]['score']
            if a is None or b is None:
                counts['unavailable'] += 1
            else:
                key = ('both_correct' if a['correct'] and b['correct'] else 'explanation_only_correct' if a['correct']
                       else 'control_only_correct' if b['correct'] else 'both_unsuccessful')
                counts[key] += 1
        result[relation] = dict(planned_pairs=len(selected), **{k: counts[k] for k in
            ('both_correct', 'explanation_only_correct', 'control_only_correct', 'both_unsuccessful', 'unavailable')},
            paired_accuracy_change=(counts['explanation_only_correct']-counts['control_only_correct'])/len(selected)
                if selected and not counts['unavailable'] else None)
    return result


def sensitivity(rows, change):
    # Record changes pair by world/cue, NEVER by support/conflict relation.
    fixed = 'cue_state' if change == 'record' else 'variant'
    varying = 'variant' if change == 'record' else 'cue_state'
    pairs = defaultdict(dict)
    for row in rows:
        key = row['cell']['world'], row['cell'][fixed]
        if row['cell'][varying] in pairs[key]:
            raise ValueError('Duplicate sensitivity cell')
        pairs[key][row['cell'][varying]] = row
    details = []
    for key, pair in sorted(pairs.items()):
        if set(pair) != {0, 1}:
            raise ValueError('Incomplete sensitivity pairing')
        a, b = pair[0], pair[1]; sa, sb = a['score'], b['score']
        eligible = sa is not None and sb is not None and sa['valid'] and sb['valid']
        details.append(dict(world=key[0], fixed_field=fixed, fixed_value=key[1],
                            cell_ids=[a['cell']['id'], b['cell']['id']], eligible=eligible,
                            unavailable=sa is None or sb is None,
                            answers=[sa['answer'] if sa else None, sb['answer'] if sb else None],
                            label_changed=(sa['answer'] != sb['answer']) if eligible else None))
    eligible = sum(p['eligible'] for p in details); changed = sum(p['label_changed'] is True for p in details)
    return dict(planned_pairs=len(details), eligible_pairs=eligible, unscorable_pairs=len(details)-eligible,
                unavailable_pairs=sum(p['unavailable'] for p in details), label_changes=changed,
                change_rate_among_eligible=changed/eligible if eligible else None,
                denominator=eligible, fixed_budget_pair_denominator=len(details), pairs=details,
                note='Invalid or truncated outputs are unscorable, not label changes; eligible-pair rates may be selected.')


def report(c, current, invocation):
    rows = cases(c, current); counts = Counter(r['operation_status'] for r in rows)
    complete = counts['returned'] == 96
    invocation = dict(dict(new_dispatches=0, newly_returned=0,
                           cached_explanation_responses=counts['returned'],
                           historical_controls_reused=192, model_loads=0), **invocation)
    groups = {arm: {rel: summarize([r for r in arm_rows(rows, arm) if r['cell']['relation'] == rel])
                   for rel in ('support', 'conflict')} for arm in ARMS}
    recovery = recovery_summary(c)
    recovery['action'] = 'Explicit recover quarantines debris only. Failed/ambiguous attempts remain held; no automatic resend.'
    finished = [sealed_read(p) for p in sorted((c.out/'invocations').glob('*/finished.json'))]
    starts = list((c.out/'invocations').glob('*/started.json'))
    raw = [r['raw'] for r in rows if isinstance(r['raw'], dict)]
    def numeric(row, key):
        value = row.get(key)
        return value if type(value) in (int, float) else 0
    return dict(protocol=VERSION, plan_hash=c.plan['artifact_hash'], source=c.plan['source'],
                measurement_mode=sealed_read(c.out/'execution.json')['measurement_mode'] if (c.out/'execution.json').exists() else 'UNEXECUTED',
                complete=complete, totals=dict(planned_explanations=96, historical_controls_reused=192,
                    **{k: counts[k] for k in ('returned', 'never_started', 'failed', 'ambiguous')},
                    scientific_dispatches=len(list((c.out/'dispatches').glob('*.json'))),
                    model_loads=sum(x.get('model_loads', 0) for x in finished),
                    model_load_attempts=sum(x.get('model_load_attempts', 0) for x in finished),
                    unresolved_invocations=len(starts)-len(finished)), this_invocation=invocation,
                arms=groups, primary=primary_contrast(rows),
                paired_changes={arm: paired_changes(rows, arm) for arm in ('direct', 'native_on')},
                sensitivities={arm: {change: sensitivity(arm_rows(rows, arm), change) for change in ('record', 'cue')} for arm in ARMS},
                resource_summary=dict(planned_new_input_tokens=c.plan['total_input_token_occurrences'],
                    maximum_new_output_tokens=c.plan['maximum_output_tokens'],
                    returned_output_tokens=sum(len(r['tokens']) for r in raw if isinstance(r.get('tokens'), list)),
                    generation_seconds=sum(numeric(r, 'elapsed_seconds') for r in raw),
                    invocation_seconds=sum(x.get('elapsed_seconds', 0) for x in finished),
                    peak_process_allocated_bytes=max((numeric(r, 'peak_process_allocated_bytes') for r in raw), default=0),
                    max_device_used_snapshot_bytes=max((numeric(r, 'gpu_memory_used_bytes') for r in raw), default=0),
                    memory_note='Parent-process peak may omit vLLM workers; device-used snapshots are not a continuous peak.'),
                accounting='Fixed budgets: invalid/truncated returned responses are unsuccessful; unavailable infrastructure outcomes are not wrong answers. Incomplete arm accuracies and the primary contrast stay undefined, with accuracy bounds shown.',
                limitations=LIMITATIONS, cases=rows, recovery=recovery, stop=STOP)


def markdown(value):
    lines = ['# Matched explicit-explanation diagnostic', '',
             f"{value['measurement_mode']}: {value['totals']['returned']}/96 new responses returned; 192 historical controls reused.",
             'Complete.' if value['complete'] else '**INCOMPLETE: do not interpret as a completed experiment.**', '', value['accounting'], '',
             '| Arm | Background | Correct / fixed denominator | Unavailable | Invalid | Truncated |',
             '|---|---|---:|---:|---:|---:|']
    for arm, groups in value['arms'].items():
        for rel, s in groups.items():
            lines.append(f"| {arm} | {rel} | {s['correct']}/{s['planned']} | {s['unavailable']} | {s['invalid']} | {s['truncated']} |")
    p = value['primary']
    lines += ['', f"Primary contrast: {p['estimate']}; four-block 95% interval: {p['block_interval_95']}.",
              f"Never started: {value['totals']['never_started']}; failed: {value['totals']['failed']}; ambiguous: {value['totals']['ambiguous']}.", '',
              'Paired outcomes, sensitivity-pair eligibility, and raw traces are in analysis.json.', '']
    lines += ['- ' + x for x in value['limitations']]
    lines += ['', STOP, '']
    return '\n'.join(lines)


def save_report(c, current, invocation):
    value = report(c, current, invocation)
    write_json(c.out/'analysis.json', value)
    # Only these derived reports are replaceable; all scientific journals remain frozen.
    from tempfile import NamedTemporaryFile
    import os
    with NamedTemporaryFile('w', dir=c.out, encoding='utf-8', delete=False) as f:
        f.write(markdown(value)); f.flush(); os.fsync(f.fileno()); name = f.name
    os.replace(name, c.out/'analysis.md')
    return value
