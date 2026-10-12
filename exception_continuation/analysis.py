from collections import defaultdict
from pathlib import Path
from statistics import mean

from exception_pilot.core import rng_for
from .core import read_plan
from .runner import sealed_read, sealed_write, collection_summary, validate_collection


def clustered(values):
    means = [mean(v) for v in values.values() if v]
    if not means: return dict(estimate=None, worlds=0, bootstrap_95=None)
    rng = rng_for('continuation-bootstrap', 981723)
    boot = sorted(mean(rng.choices(means, k=len(means))) for _ in range(10000))
    return dict(estimate=mean(means), worlds=len(means), bootstrap_95=[boot[249], boot[9749]],
                world_values={k: mean(v) for k, v in values.items() if v},
                degenerate_interval=boot[249] == boot[9749])


def analyze(output):
    out = Path(output); plan = read_plan(out); collection = sealed_read(out/'collection.json')
    validate_collection(plan, collection)
    execution = sealed_read(out/'execution.json')
    tasks = {t['id']: t for t in plan['tasks']}
    result = dict(mode=execution['mode'], phase=plan['phase'], baseline=collection_summary(collection),
                  interpretation='Readouts are conditional on cue/prefix; edits are text interventions, not hidden-belief measurements.')
    if (out/'measurements.json').exists():
        ms = sealed_read(out/'measurements.json')
        if ms['collection_hash'] != collection['artifact_hash']: raise ValueError('Stale measurements')
        deltas = defaultdict(list); coverage = defaultdict(lambda: dict(planned=0, eligible=0, replay_valid=0, measured=0))
        paired = defaultdict(list)
        for row in ms['rows']:
            t = tasks[row['task_id']]
            cuts = {c['k']: c for c in row['cuts']}
            for k, c in cuts.items():
                coverage[k]['planned'] += 1; coverage[k]['eligible'] += c['eligible']
                coverage[k]['replay_valid'] += bool(c.get('exact_suffix_match'))
                coverage[k]['measured'] += 'readout' in c
            if all('readout' in cuts[k] for k in (0, 64)):
                paired[t['world']].append(cuts[64]['readout']['gold_pattern_log_odds']-cuts[0]['readout']['gold_pattern_log_odds'])
        # Require BOTH target variants for a world in the prespecified longitudinal estimate.
        deltas = {w: ds for w, ds in paired.items() if len(ds) == 2}
        result['longitudinal_primary_64_minus_0'] = clustered(deltas)
        result['readout_coverage'] = dict(coverage)
        by_cut = defaultdict(lambda: defaultdict(list))
        for row in ms['rows']:
            for c in row['cuts']:
                if 'readout' in c:
                    by_cut[c['k']][tasks[row['task_id']]['world']].append(c['readout']['gold_pattern_log_odds'])
        result['readout_by_checkpoint'] = {k: clustered({w: vs for w, vs in worlds.items() if len(vs) == 2})
                                           for k, worlds in by_cut.items()}
        result['replay_failures'] = sum(not r['replay_passed'] for r in ms['rows'])
    if (out/'interventions.json').exists():
        es = sealed_read(out/'edit-plan.json'); data = sealed_read(out/'interventions.json')
        if data['edit_plan_hash'] != es['artifact_hash']: raise ValueError('Stale interventions')
        byid = {r['task_id']: r for r in data['rows']}
        eligible_worlds = defaultdict(list)
        for case in es['cases']: eligible_worlds[tasks[case['task_id']]['world']].append(case['task_id'])
        comparisons = {}
        for name, left, right in [('primary_availability_minus_meaning', 'availability_repair', 'meaning_control'),
                                  ('availability_minus_unchanged', 'availability_repair', 'unchanged'),
                                  ('meaning_minus_unchanged', 'meaning_control', 'unchanged'),
                                  ('value_minus_unchanged', 'value_repair', 'unchanged')]:
            values, readouts, bounds = {}, {}, []
            for wid, tids in eligible_worlds.items():
                diffs, ps, lows, highs = [], [], [], []
                for tid in tids:
                    row = byid.get(tid, {})
                    arms = row.get('arms', {}) if row.get('unchanged_replay_passed') else {}
                    a = arms.get(left, {}).get('score', {}).get('correct')
                    b = arms.get(right, {}).get('score', {}).get('correct')
                    if a is not None and b is not None: diffs.append(int(a)-int(b))
                    lows.append((int(a) if a is not None else 0)-(int(b) if b is not None else 1))
                    highs.append((int(a) if a is not None else 1)-(int(b) if b is not None else 0))
                    if left in arms and right in arms:
                        ps.append(arms[left]['readout']['gold_pattern_log_odds']-arms[right]['readout']['gold_pattern_log_odds'])
                if len(diffs) == len(tids): values[wid] = diffs
                if len(ps) == len(tids): readouts[wid] = ps
                bounds.append([mean(lows), mean(highs)])
            comparisons[name] = dict(accuracy=clustered(values), readout=clustered(readouts),
                eligible_worlds=len(eligible_worlds), full_plan_accuracy_bounds=[mean(b[i] for b in bounds) for i in (0,1)] if bounds else None)
        result['interventions'] = dict(planned_cases=len(es['cases']), reviewed=es['reviewed'], excluded=es['excluded'],
            returned_cases=len(data['rows']), invalid_or_replay_failed=sum(not r.get('unchanged_replay_passed', False) for r in data['rows']), comparisons=comparisons)
    sealed_write(out/'summary.json', result)
    return result
