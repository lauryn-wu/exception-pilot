from collections import defaultdict
from pathlib import Path
from statistics import mean

from exception_pilot.core import rng_for
from .core import read_plan
from .runner import sealed_read, sealed_write, collection_summary, validate_collection
from .validation import calibration_result
from .reporting import intervention_coverage


def measured(cut):
    return cut.get('eligible') is True and cut.get('passed') is True and 'readout' in cut


def clustered(values):
    means = [mean(v) for v in values.values() if v]
    if not means: return dict(estimate=None, worlds=0, bootstrap_95=None)
    rng = rng_for('continuation-bootstrap', 981723)
    boot = sorted(mean(rng.choices(means, k=len(means))) for _ in range(10000))
    return dict(estimate=mean(means), worlds=len(means), bootstrap_95=[boot[249], boot[9749]],
                world_values={k: mean(v) for k, v in values.items() if v},
                degenerate_interval=boot[249] == boot[9749])


def analyze(output):
    out = Path(output); plan = read_plan(out)
    if not (out/'collection.json').exists():
        result = dict(mode='NOT_COLLECTED', phase=plan['phase'], real_model_validation='PENDING',
                      study_2a={'status': 'PENDING'}, study_2b={'status': 'PENDING', 'validated_same_response_interventions': False})
        sealed_write(out/'summary.json', result)
        return result
    collection = sealed_read(out/'collection.json')
    validate_collection(plan, collection)
    execution = sealed_read(out/'execution.json')
    technical = sealed_read(out/'validation.json')
    if (technical['artifact_hash'] != collection['validation_hash'] or
            technical['backend_hash'] != execution['backend_hash'] or
            collection['backend_hash'] != execution['backend_hash']):
        raise ValueError('Validation/backend identity mismatch')
    tasks = {t['id']: t for t in plan['tasks']}
    result = dict(mode=execution['mode'], phase=plan['phase'], baseline=collection_summary(collection),
                  interpretation='Answer preferences under a checkpoint readout; not direct internal beliefs.',
                  behavioral_calibration=calibration_result(plan, collection),
                  real_model_validation='PENDING' if execution['mode'] == 'SIMULATED' else ('TECHNICAL_PASSED' if technical['passed'] else 'FAILED'),
                  study_2a={'status': 'PENDING'}, study_2b={'status': 'PENDING', 'validated_same_response_interventions': False})
    if (out/'measurements.json').exists():
        ms = sealed_read(out/'measurements.json')
        if ms['collection_hash'] != collection['artifact_hash']: raise ValueError('Stale measurements')
        deltas = defaultdict(list); coverage = defaultdict(lambda: dict(planned=0, eligible=0, replay_valid=0, measured=0))
        paired = defaultdict(dict)
        for row in ms['rows']:
            t = tasks[row['task_id']]
            cuts = {c['k']: c for c in row['cuts']}
            for k, c in cuts.items():
                coverage[k]['planned'] += 1; coverage[k]['eligible'] += c['eligible']
                coverage[k]['replay_valid'] += bool(c.get('passed'))
                coverage[k]['measured'] += measured(c)
            if all(measured(cuts.get(k, {})) for k in (0, 64)):
                paired[t['world']][t['variant']] = cuts[64]['readout']['gold_pattern_log_odds']-cuts[0]['readout']['gold_pattern_log_odds']
        # Require BOTH target variants for a world in the prespecified longitudinal estimate.
        deltas = {w: list(ds.values()) for w, ds in paired.items() if set(ds) == {0, 1}}
        result['longitudinal_primary_64_minus_0'] = clustered(deltas)
        result['readout_coverage'] = dict(coverage)
        by_cut = defaultdict(lambda: defaultdict(list))
        for row in ms['rows']:
            for c in row['cuts']:
                if measured(c):
                    by_cut[c['k']][tasks[row['task_id']]['world']].append(c['readout']['gold_pattern_log_odds'])
        result['readout_by_checkpoint'] = {k: clustered({w: vs for w, vs in worlds.items() if len(vs) == 2})
                                           for k, worlds in by_cut.items()}
        result['replay_failures'] = sum(not r['replay_passed'] for r in ms['rows'])
        original = {r['task']['id']: r for r in collection['rows']}
        strata, sensitivity = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
        for row in ms['rows']:
            saved = original[row['task_id']]
            outcome = 'correct' if saved['score']['correct'] is True else 'wrong' if saved['score']['valid'] else 'invalid'
            wid = saved['task']['world']
            for c in row['cuts']:
                if not measured(c): continue
                base = c['readout']['gold_pattern_log_odds']
                strata[f"{outcome}/k{c['k']}" ][wid].append(base)
                for ci, probe in c.get('readouts', {}).items():
                    if ci != '0': sensitivity[f"cue{ci}/k{c['k']}" ][wid].append(probe['gold_pattern_log_odds']-base)
        result['study_2a'] = dict(analysis_version='fixed-checkpoints-v3', primary=result['longitudinal_primary_64_minus_0'],
            trajectories_with_any_failed_checkpoint=result['replay_failures'],
            trajectory_denominator=len(ms['rows']),
            checkpoint_replay_failures={k: c['eligible']-c['replay_valid'] for k, c in coverage.items()},
            coverage=result['readout_coverage'], checkpoint_means=result['readout_by_checkpoint'],
            by_final_outcome_descriptive={name: clustered(values) for name, values in strata.items()},
            cue_sensitivity={name: clustered(values) for name, values in sensitivity.items()},
            cues=plan['config']['readout_cues'], interpretation='Answer preferences under a checkpoint readout')
        sealed_write(out/'study-2a-summary.json', result['study_2a'])

    if (out/'event-measurements.json').exists():
        from .events import summarize_events
        event_plan = sealed_read(out/'event-plan.json'); events = sealed_read(out/'event-measurements.json')
        if (events['event_plan_hash'] != event_plan['artifact_hash']
                or events['collection_hash'] != collection['artifact_hash']
                or events['backend_hash'] != execution['backend_hash']
                or event_plan['edit_plan_hash'] != sealed_read(out/'edit-plan.json')['artifact_hash']):
            raise ValueError('Stale event measurements')
        result['study_2a_events_secondary'] = summarize_events(plan, events)
        sealed_write(out/'study-2a-events-summary.json', result['study_2a_events_secondary'])

    if (out/'edit-plan.json').exists():
        es = sealed_read(out/'edit-plan.json')
        data = sealed_read(out/'interventions.json') if (out/'interventions.json').exists() else dict(
            edit_plan_hash=es['artifact_hash'], collection_hash=collection['artifact_hash'],
            backend_hash=execution['backend_hash'], rows=[], real_model_status='PENDING')
        if (data['edit_plan_hash'] != es['artifact_hash'] or
                data['collection_hash'] != collection['artifact_hash'] or
                es['collection_hash'] != collection['artifact_hash'] or
                data['backend_hash'] != execution['backend_hash']):
            raise ValueError('Stale interventions')
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
                planned_cases=len(es['cases']), complete_accuracy_cases=sum(len(v) for v in values.values()),
                bounds_denominator='All cases in the frozen edit plan, averaged within world then across eligible worlds.',
                eligible_worlds=len(eligible_worlds), full_plan_accuracy_bounds=[mean(b[i] for b in bounds) for i in (0,1)] if bounds else None)
        result['interventions'] = dict(real_model_status=data['real_model_status'],
            validated_same_response_interventions=bool(execution['mode'] == 'LIVE_LOCAL' and technical['passed']
                and data['real_model_status'] == 'VALIDATED_FOR_RECORDED_CASES' and es['cases']
                and set(byid) == {c['task_id'] for c in es['cases']}
                and all(r.get('same_response_validated') and r.get('validation', {}).get('passed')
                        and r.get('control_validation', {}).get('passed') for r in data['rows'])),
            planned_cases=len(es['cases']), reviewed=es['reviewed'], excluded=es['excluded'],
            returned_cases=len(data['rows']), coverage=intervention_coverage(out, es, data),
            deprecated_fields={'invalid_or_replay_failed': 'Removed: conflated replay failures with final-answer validity. Use coverage.replay_failures and coverage.per_arm.'},
            comparisons=comparisons)
    if 'interventions' in result:
        result['study_2b'] = result['interventions']
        sealed_write(out/'study-2b-summary.json', result['study_2b'])
    sealed_write(out/'summary.json', result)
    return result
