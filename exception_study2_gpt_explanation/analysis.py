"""GPT-only matched outcomes using the unchanged follow-up estimators."""
from collections import Counter
from exception_pilot.core import digest
from exception_pilot.storage import write_json
from exception_continuation.runner import sealed_read
from exception_study2_native.recovery import state, summary as recovery_summary
from exception_study2_explanation.analysis import summarize, primary_contrast, paired_changes, sensitivity
from . import VERSION, STOP
from .execution import opid
from .parsing import parse_result, account

LIMITATIONS = [
    'Four construction blocks are the primary resampling units; the 24-world interval is a sensitivity analysis. The 192 responses are not independent worlds.',
    'An all-perfect [0, 0] bootstrap interval only resamples observed outcomes and does not establish population certainty.',
    'This tests an explanation request at fixed API reasoning.effort=none; that setting does not prove absence of internal reasoning.',
    'Written output and the instruction effect on task interpretation are not isolated. No mechanism, novelty, or project-success claim follows automatically.',
    'The requested model is an alias, not a dated snapshot. Returned identifiers and timestamps document what was observed, not snapshot-level reproducibility.',
    'Nonempty preceding text is only explanation-format compliance; semantic annotations remain not reviewed.',
    'Inputs and analysis were chosen after observing the Qwen screen. Qwen responses are not GPT controls.'
]


def cases(c, current):
    rows = []
    for r in c.requests:
        op = current[r['cell']['id']]; status = state(op); raw = op['result'] if status == 'returned' else None
        response = c.out/'responses'/(digest(opid(r))+'.json')
        if raw is None and response.exists(): raw = sealed_read(response)['raw']
        rows.append(dict(cell=r['cell'], request_hash=r['request_hash'], operation_status=status,
                         operation_hash=op['artifact_hash'] if op else None, raw=raw,
                         score=parse_result(raw,r['cell']) if status=='returned' else None,
                         usage_accounting=account(raw,c.plan['pricing']) if raw else None))
    return rows


def matched(rows):
    lookup = {(r['cell']['pair_id'],r['cell']['arm']):r for r in rows}
    if len(lookup) != 192: raise ValueError('Expected 192 GPT-only arm records')
    return [dict(r, controls={'direct':lookup[r['cell']['pair_id'],'direct']}) for r in rows if r['cell']['arm']=='explanation']


def outcomes(rows):
    pairs = matched(rows)
    unavailable = sum(r['score'] is None for r in rows)
    if unavailable:
        primary = dict(estimate=None, block_interval_95=None, world_sensitivity=None, unavailable=unavailable)
    else:
        primary = primary_contrast(pairs)
    primary['definition'] = '(explanation support - explanation conflict) - (answer-only support - answer-only conflict)'
    return dict(arms={arm:{rel:summarize([r for r in rows if r['cell']['arm']==arm and r['cell']['relation']==rel])
                           for rel in ('support','conflict')} for arm in ('direct','explanation')},
                primary=primary, paired_changes=paired_changes(pairs,'direct'),
                sensitivities={arm:{change:sensitivity([r for r in rows if r['cell']['arm']==arm],change)
                                   for change in ('record','cue')} for arm in ('direct','explanation')})


def report(c, current, invocation):
    rows = cases(c,current); counts = Counter(r['operation_status'] for r in rows)
    ex = c.out/'execution.json'; mode = sealed_read(ex)['measurement_mode'] if ex.exists() else 'UNEXECUTED'
    invoked = dict(new_dispatches=0, newly_returned=0, cached=counts['returned'], **{k:v for k,v in invocation.items() if k not in ('new_dispatches','newly_returned','cached')})
    invoked.update({k:invocation[k] for k in ('new_dispatches','newly_returned','cached') if k in invocation})
    accounting = [r['usage_accounting'] for r in rows if r['usage_accounting'] is not None]
    priced = [a for a in accounting if a['estimated_usd'] is not None]
    dispatches = len(list((c.out/'dispatches').glob('*.json')))
    def known_sum(key):
        values = [a[key] for a in accounting if type(a.get(key)) is int and a[key]>=0]
        return dict(observed_sum=sum(values), responses_reporting=len(values))
    recovery = recovery_summary(c)
    recovery['action'] = 'Quarantine debris with recover only; failed/ambiguous calls stay held, with no resend or promotion.'
    return dict(protocol=VERSION, plan_hash=c.plan['artifact_hash'], source=c.plan['source'], measurement_mode=mode,
                complete=counts['returned']==192,
                totals=dict(planned=192, matched_pairs=96, completed=counts['returned'], cached=invoked['cached'],
                            pending=counts['never_started'], failed=counts['failed'], ambiguous=counts['ambiguous'],
                            scientific_dispatches=dispatches, qwen_outputs_reused=0), this_invocation=invoked,
                resource_summary=dict(pricing=c.plan['pricing'], maximum_output_tokens=c.plan['maximum_output_tokens'],
                    **{key:known_sum(key) for key in ('input_tokens','output_tokens','reasoning_tokens','cached_input_tokens','cache_write_input_tokens')},
                    priced_responses=len(priced), dispatches_without_complete_cost=dispatches-len(priced),
                    observed_estimated_usd=sum(a['estimated_usd'] for a in priced),
                    total_estimated_usd=sum(a['estimated_usd'] for a in priced) if len(priced)==dispatches else None,
                    note='Observed totals omit missing usage; they are not imputed zeros. Failed/ambiguous calls may have incurred charges. Output includes reasoning; no double-counting.'),
                returned_models=dict(Counter(r['score']['returned_model'] for r in rows if r['score'] and isinstance(r['score']['returned_model'],str) and r['score']['returned_model'])),
                accounting='Fixed-budget invalid/truncated/refusal returns count as unsuccessful. Infrastructure-unavailable outcomes remain unavailable: incomplete arm accuracies and primary contrast are undefined, with accuracy bounds shown.',
                **outcomes(rows), cases=rows, limitations=LIMITATIONS, recovery=recovery, stop=STOP)


def markdown(value):
    t = value['totals']; p = value['primary']; cost = value['resource_summary']
    lines = ['# GPT matched explanation diagnostic','',
             f"{value['measurement_mode']}: {t['completed']}/192 fresh GPT responses returned.",
             'Complete.' if value['complete'] else '**INCOMPLETE: not a completed experiment.**','',
             f"Pending: {t['pending']}; failed: {t['failed']}; ambiguous: {t['ambiguous']}; cached in this invocation: {t['cached']}.",
             value['accounting'],'',
             '| Arm | Background | Correct / planned | Unavailable | Invalid | Truncated |',
             '|---|---|---:|---:|---:|---:|']
    for arm,groups in value['arms'].items():
        for rel,s in groups.items():
            lines.append(f"| {arm} | {rel} | {s['correct']}/{s['planned']} | {s['unavailable']} | {s['invalid']} | {s['truncated']} |")
    lines += ['',f"Primary contrast: {p['estimate']}; four-block 95% interval: {p['block_interval_95']}.",
              f"Observed priced usage: ${cost['observed_estimated_usd']:.6f}; dispatches missing a complete cost estimate: {cost['dispatches_without_complete_cost']}.",
              'Category counts, paired changes, eligibility, model identities and ordered output messages are in analysis.json.','']
    lines += ['- '+x for x in value['limitations']]
    return '\n'.join(lines+['',STOP,''])


def save_report(c, current, invocation):
    value = report(c,current,invocation)
    write_json(c.out/'analysis.json',value)
    # Derived reports can be regenerated; scientific journals are immutable.
    from tempfile import NamedTemporaryFile
    import os
    with NamedTemporaryFile('w',dir=c.out,encoding='utf-8',delete=False) as f:
        f.write(markdown(value)); f.flush(); os.fsync(f.fileno()); name=f.name
    os.replace(name,c.out/'analysis.md')
    return value
