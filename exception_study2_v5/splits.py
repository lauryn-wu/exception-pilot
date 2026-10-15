"""World-disjoint, outcome-blind assignment; no probing architecture or training."""
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from .core import read_plan
from . import PROTOCOL, ARMS, EVENTS

SCHEMA='v5-world-split-v1'

def make_splits(source, output, seed=20261015054, test_worlds=12, pilot_informed_design=True):
    plan=read_plan(source)
    approval_path=Path(source)/'remaining-approval-v5.json'
    approval=sealed_read(approval_path) if approval_path.exists() else None
    if approval and (approval.get('scientific_plan_hash')!=plan['plan_hash'] or
                     (approval['decisions']['pilot_informed_method_design'] and not pilot_informed_design)):
        raise ValueError('Split decision contradicts recorded pilot design use')
    if type(seed) is not int or type(test_worlds) is not int or not 1<=test_worlds<56:
        raise ValueError('Integer seed and 1..55 test worlds required')
    if type(pilot_informed_design) is not bool:raise ValueError('Explicit pilot design-use decision required')
    worlds=[w['id'] for w in plan['worlds']];pilot=set(worlds[:4])
    pool=[w for w in worlds if not pilot_informed_design or w not in pilot]
    heldout=set(sorted(pool,key=lambda w:digest([seed,w]))[:test_worlds])
    assignment={w:'evaluation' if w in heldout else 'train' for w in worlds}
    tasks={t['id']:dict(world=t['world'],split=assignment[t['world']]) for t in plan['tasks']}
    return freeze(Path(output),dict(protocol=PROTOCOL,schema=SCHEMA,plan_hash=plan['plan_hash'],
        source_hash=plan['source_hash'],seed=seed,test_worlds=test_worlds,pilot_informed_design=pilot_informed_design,
        worlds=assignment,tasks=tasks,pilot_worlds=sorted(pilot),
        descendant_rule='Every checkpoint, annotation and M/O intervention arm inherits its original task world and split',
        checkpoint_names=[f'fixed/{k}' for k in plan['checkpoints']]+['pre_answer']+[f'{e}/{s}' for e in EVENTS for s in ('before','after')],
        intervention_families=['M','O'],intervention_arms=list(ARMS),
        outcome_stratification=False,exploratory=False,training_performed=False))

def descendant_split(manifest_path, task_id, world, source):
    m=sealed_read(manifest_path);plan=read_plan(source)
    if m.get('schema')!=SCHEMA or m['plan_hash']!=plan['plan_hash'] or m['source_hash']!=plan['source_hash']:
        raise ValueError('Split source identity mismatch')
    if m['pilot_worlds']!=sorted(w['id'] for w in plan['worlds'][:4]) or type(m['pilot_informed_design']) is not bool:
        raise ValueError('Pilot split constraint changed')
    tasks={t['id']:t for t in plan['tasks']}
    if set(m['tasks'])!=set(tasks) or set(m['worlds'])!={w['id'] for w in plan['worlds']}:
        raise ValueError('Incomplete split population')
    pool=[w['id'] for w in plan['worlds'] if not m['pilot_informed_design'] or w['id'] not in m['pilot_worlds']]
    expected=set(sorted(pool,key=lambda w:digest([m['seed'],w]))[:m['test_worlds']])
    for tid,t in tasks.items():
        split='evaluation' if t['world'] in expected else 'train'
        if m['worlds'][t['world']]!=split or m['tasks'][tid]!=dict(world=t['world'],split=split):
            raise ValueError('World/descendant split changed')
    if task_id not in tasks or tasks[task_id]['world']!=world:
        raise ValueError('Descendant parent world mismatch')
    return m['worlds'][world]
