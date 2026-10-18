"""Deterministic, target-excluded audits of saved final v5 and earlier generator tables."""
from collections import Counter
from pathlib import Path
from exception_pilot.core import digest
from exception_counterfactual.core import make_world as earlier_world
from exception_review.artifacts import freeze, sha
from .design import historical_plan, historical_tables
from .tables import audit_table, render, parse, DISTRACTORS
from .planning import contract


def summarize(cases):
    return dict(tables=len(cases),target_positions=dict(Counter(str(c['target_row_1based']) for c in cases)),
        same_climate_peer_positions=dict(Counter(str(i) for c in cases for i in c['same_climate_peer_positions_1based'])),
        background_counts=dict(Counter('/'.join(str(c['background_class_counts'].get(x,0)) for x in 'ABC') for c in cases)),
        nonindependent_distractor_tables=sum(any(not c['features'][f]['exact_class_independence'] for f in DISTRACTORS) for c in cases),
        nonindependent_joint_tables=sum(any(not v['exact_class_independence'] for v in c['joint_distractors'].values()) for c in cases),
        zero_signed_margin_nonzero_absolute=sum(abs(c['signed_rate_margin_sum'])<1e-12 and c['absolute_rate_margin_sum']>1e-12 for c in cases),
        zero_signed_margin_with_joint_signal=sum(abs(c['signed_rate_margin_sum'])<1e-12 and not c['joint_distractors']['+'.join(DISTRACTORS)]['exact_class_independence'] for c in cases),
        mean_distractor_mi={f:sum(c['features'][f]['mutual_information_bits'] for c in cases)/len(cases) for f in DISTRACTORS})


def audit(v5_path, output):
    p=historical_plan(v5_path); cases=[];earlier=[];used=set()
    tables=historical_tables(p)
    by_world={w['id']:[t for t in tables if t['world']==w['id']] for w in p['worlds']}
    for t in tables:
        a=audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
        a.update(world=t['world'],variant=t['variant'],roles=t['roles'],origin_task_ids=t['origin_task_ids'])
        cases.append(a)
    one_cell=[];role_counts=Counter()
    for w in p['worlds']:
        ts=by_world[w['id']]
        a,b=[parse(t['table']) for t in ts]
        changes=[(i,k) for i in range(10) for k in a[i] if a[i][k]!=b[i][k]]
        one_cell.append(changes==[(9,'label')]);role_counts['/'.join(w['roles'])]+=1
    for i,w in enumerate(p['worlds']):
        base=earlier_world({'seed':p['seed']},i,used)
        for old,new in zip(base['items'],w['items']):
            if any(old[k]!=new[k] for k in ('descriptor','transmission','seat_cover','doors','climate')):
                raise ValueError('Earlier-generator reconstruction differs from saved v5 source fields')
        for target in base['target_indices']:
            for condition in ('support','conflict'):
                rows=[]
                for j in base['order']:
                    r=base['items'][j]
                    rows.append(dict(plate=r['id'],description=r['descriptor'],transmission=r['transmission'],
                        seat_cover=r['seat_cover'],doors=r['doors'],audit_marker='NOT_PRESENT_IN_EARLIER_GENERATOR',label=base['labels'][condition][j]))
                a=audit_table(render(rows),base['items'][target]['id'],base['labels'][condition][target],
                              base['majority_labels'][condition][base['items'][target]['climate']])
                a.update(world=w['id'],condition=condition,reconstructed=True)
                earlier.append(a)
    facts=dict(worlds=len(p['worlds']),pilot_worlds=p['pilot_worlds'],remaining_worlds=len(p['worlds'])-p['pilot_worlds'],
        both_variants_conflict=all(c['recorded_class']!=c['pattern_class'] for c in cases),
        one_target_cell_only=all(one_cell),target_row_10=all(c['target_row_1based']==10 for c in cases),
        background_4_pattern_3_role0_2_role1=all(c['background_class_counts']=={c['roles'][0]:3,c['roles'][1]:2,c['roles'][2]:4} for c in cases),
        ternary_final_labels=all(set(c['full_class_counts'])==set('ABC') for c in cases),
        role_assignments=dict(role_counts),random_assignment='Source inspection: earlier make_world assigns transmission/seat_cover/doors independently with rng.choice; v5 independently assigns audit_marker with rng.choice. This does not imply independence in finite rendered tables.')
    if not all(facts[k] for k in ('both_variants_conflict','one_target_cell_only','target_row_10','background_4_pattern_3_role0_2_role1','ternary_final_labels')):
        raise ValueError('Previously stated v5 facts failed verification')
    out=Path(output)
    if out.exists() and any(out.iterdir()): raise ValueError('Use a fresh audit directory')
    return freeze(out/'generator-audit.json',dict(kind='OFFLINE_FINAL_TABLE_AUDIT',audit_code_contract=contract(),v5_plan_hash=p['plan_hash'],
        v5_file_sha256=sha(v5_path),facts=facts,v5_summary=summarize(cases),v5_tables=cases,
        earlier_summary=summarize(earlier),earlier_tables=earlier,
        earlier_scope='Deterministically reconstructed 60 base worlds using the saved v5 seed; both targets and support/conflict. Not represented as saved historical model outcomes. Earlier marker absent; constant placeholder has zero signal.',
        counting='V5: 120 unique world/variant tables; wording and response instructions do not duplicate tables. Earlier: 240 queried-target/background tables. Counts/rates and joint subsets exclude that queried target only.',
        model_calls=0))
