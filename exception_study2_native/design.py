"""Concrete draft design plus a separate historical-table replication option."""
from collections import Counter
import copy
import itertools
from pathlib import Path
from exception_pilot.core import DESCRIPTORS, digest, rng_for
from exception_continuation.core import INTRO, QUESTION
from exception_study2_v5.core import LOOKUP, read_plan as read_v5
from . import VERSION, SEED, PILOT_BUDGET, PILOT_WORLDS, FINAL_INSTRUCTION
from .tables import FIELDS, DISTRACTORS, render, parse, audit_table


def historical_plan(path):
    path = Path(path).resolve()
    if path.name != 'plan-v5.json': raise ValueError('Supply the saved plan-v5.json')
    return read_v5(path.parent)


def controlled_tables():
    roles = list(itertools.product(itertools.permutations('ABC'), ('cold','warm'), range(5)))
    rng_for(VERSION, SEED, 'worlds').shuffle(roles)
    tables = []
    profiles = ((0,0,0),(0,1,1),(1,0,1),(1,1,0))
    for index,(labels,climate,rep) in enumerate(roles):
        rng = rng_for(VERSION, SEED, index)
        wid = f'native-draft-{index:03d}'
        doubled = 'XYZ'[index % 3]
        others = [x for x in 'XYZ' if x != doubled]
        marks = [doubled,doubled]+others
        descriptors = {c:rng.sample(DESCRIPTORS[c],5) for c in ('cold','warm')}
        rows = []
        for group in range(3):
            c = climate if group == 0 else ('warm' if climate == 'cold' else 'cold')
            for j,bits in enumerate(profiles):
                # Opaque identifiers are assigned independently of group/class/profile.
                plate = 'N'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=7))
                rows.append(dict(plate=plate,description=descriptors[c][j],
                    transmission=('Manual','Automatic')[bits[0]],seat_cover=('Cloth','Vinyl')[bits[1]],
                    doors=('Two','Four')[bits[2]],audit_marker=marks[j],label=labels[group],group=group))
        rng.shuffle(rows)
        target_profile = index % 4; bits = profiles[target_profile]
        target = dict(plate='N'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=7)),
            description=descriptors[climate][4],transmission=('Manual','Automatic')[bits[0]],
            seat_cover=('Cloth','Vinyl')[bits[1]],doors=('Two','Four')[bits[2]],
            audit_marker=marks[target_profile],label=labels[0])
        for cue_state,variant in itertools.product(range(2),repeat=2):
            values = copy.deepcopy(rows)
            for r in values: r['label'] = labels[cue_state] if r['group']==0 else labels[1-cue_state] if r['group']==1 else labels[2]
            t = dict(target,label=labels[variant]); values.append(t)
            tables.append(dict(world=wid,cohort='pilot' if index<PILOT_WORLDS else 'main',
                variant=variant,cue_state=cue_state,relation='support' if cue_state==variant else 'conflict',
                expected=labels[variant],pattern=labels[cue_state],roles=list(labels),target_plate=t['plate'],
                climate=climate,replicate=rep,target_profile=target_profile,doubled_marker=doubled,table=render(values)))
    validate_controlled(tables)
    return tables


def validate_controlled(tables):
    if len(tables)!=240 or len({t['world'] for t in tables})!=60: raise ValueError('Draft fixed population changed')
    worlds = {}
    for t in tables:
        rows = parse(t['table']); a = audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
        if len(rows)!=13 or a['target_row_1based']!=13 or a['background_class_counts']!={'A':4,'B':4,'C':4}:
            raise ValueError('Final rendered class/position constraint failed')
        if a['same_climate_peer_classes']!={t['pattern']:4}: raise ValueError('Four unanimous climate peers required')
        if t['relation']!=('support' if t['expected']==t['pattern'] else 'conflict'):
            raise ValueError('Support/conflict incorrectly labeled')
        if any(not a['features'][f]['exact_class_independence'] for f in DISTRACTORS) or any(not v['exact_class_independence'] for v in a['joint_distractors'].values()):
            raise ValueError('Final-table distractors must be exactly class-independent')
        worlds.setdefault(t['world'],{})[(t['cue_state'],t['variant'])]=t
    for cases in worlds.values():
        if set(cases)!={(0,0),(0,1),(1,0),(1,1)}: raise ValueError('Missing factorial table')
        for cue in (0,1):
            a,b=[parse(cases[(cue,v)]['table']) for v in (0,1)]
            changed=[(i,k) for i in range(13) for k in FIELDS if a[i][k]!=b[i][k]]
            if changed!=[(12,'label')]: raise ValueError('Record variants must change only the target cell within cue context')
        for variant in (0,1):
            a,b=[parse(cases[(c,variant)]['table']) for c in (0,1)]
            changed=[(i,k) for i in range(13) for k in FIELDS if a[i][k]!=b[i][k]]
            if len(changed)!=8 or any(i==12 or k!='label' for i,k in changed):
                raise ValueError('Cue context must swap exactly eight background labels, preserving target')


def historical_tables(plan):
    tables=[]
    for w in plan['worlds']:
        for v in (0,1):
            tasks=[t for t in plan['tasks'] if t['world']==w['id'] and t['variant']==v]
            if len(tasks)!=4 or len({t['table'] for t in tasks})!=1: raise ValueError('Historical table identity differs across interfaces')
            t=tasks[0]
            a=audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
            if a['same_climate_peer_classes']!={t['pattern']:4}: raise ValueError('Historical cue changed')
            tables.append(dict(world=w['id'],cohort='pilot' if w in plan['worlds'][:4] else 'main',variant=v,
                cue_state=0,relation='conflict',expected=t['expected'],pattern=t['pattern'],roles=w['roles'],
                target_plate=t['target_plate'],table=t['table'],origin_task_ids=[x['id'] for x in tasks]))
    return tables


def make_design(kind='controlled-draft', v5=None):
    if kind not in ('controlled-draft','historical-v5'): raise ValueError('Unknown design')
    if kind=='historical-v5' and v5 is None: raise ValueError('Historical option requires saved v5 plan')
    tables=controlled_tables() if kind=='controlled-draft' else historical_tables(v5)
    cells=[]
    for t in tables:
        for wording,thinking in itertools.product(('original','lookup'),(False,True)):
            question=QUESTION if wording=='original' else LOOKUP.format(plate=t['target_plate'])
            prompt=INTRO+'\n\n'+t['table']+'\n\nLicense plate: '+t['target_plate']+'\n'+question+'\n'+FINAL_INSTRUCTION
            pair=[t['world'],t['variant'],t['cue_state'],wording]
            cell=dict(t,wording=wording,thinking=thinking,prompt=prompt,prompt_hash=digest(prompt),
                seed=int(digest([SEED,t['world'],wording])[:8],16),pair_id=digest(pair))
            cell['id']=f"{t['world']}/v{t['variant']}/cue{t['cue_state']}/{wording}/thinking-{int(thinking)}"
            cells.append(cell)
    # Randomized within each world, fixed order thereafter; pilot/main never mix.
    ordered=[]
    for w in dict.fromkeys(t['world'] for t in tables):
        group=[c for c in cells if c['world']==w]; rng_for(VERSION,'schedule',w).shuffle(group);ordered.extend(group)
    counts={s:sum(c['cohort']==s for c in ordered) for s in ('pilot','main')}
    first_world_tables={t['world']:t for t in tables}
    counterbalance={}
    for cohort in ('pilot','main','all'):
        ws=[t for t in first_world_tables.values() if cohort=='all' or t['cohort']==cohort]
        counterbalance[cohort]=dict(worlds=len(ws),label_roles=dict(Counter('/'.join(t['roles']) for t in ws)),
            target_climate=dict(Counter(t.get('climate','see_saved_table') for t in ws)),
            doubled_marker=dict(Counter(t.get('doubled_marker','historical_random') for t in ws)),
            target_profile=dict(Counter(str(t.get('target_profile','historical_random')) for t in ws)))
    constraints=dict(validated_unique_final_tables=len(tables),final_manifest_cells=len(ordered),
        per_table_exact_distractor_class_independence=kind=='controlled-draft',
        full_joint_distractor_class_independence=kind=='controlled-draft',counterbalance=counterbalance,
        changes=('13 rows, target last at 13, background 4/4/4, four unanimous same-climate peers. '
                 'Identical four joint distractor profiles under each class. Marker counts 2/1/1 per class, not uniform across values. '
                 'Two fixed cue contexts: within each context target variants change one cell and swap support/conflict. '
                 'Within a target variant cue contexts swap eight background labels. Third class remains fixed. '
                 'Four same-climate peers and two conflicting recorded labels cannot all be supported under the historical 4/3/2 totals. '
                 'Counterbalancing is documented separately; no claim of exact row-position/identifier balance.') if kind=='controlled-draft' else
                 'Historical final tables unchanged. All conflict; no support gap. New thinking-off/on label-only-final outputs are required.')
    return dict(protocol=VERSION,design=kind,status='DRAFT_FOR_REVIEW',seed=SEED,
        origin_plan_hash=v5['plan_hash'] if v5 else None,tables=tables,cells=ordered,
        constraints=constraints,
        counts=dict(worlds=len({t['world'] for t in tables}),tables=len(tables),responses=len(ordered),by_cohort=counts,
                    pilot_maximum_output_tokens=counts['pilot']*PILOT_BUDGET,
                    main_budget=None,maximum_output_tokens=None),
        note='All conditions are fresh label-only-final generations. Historical visible explanations are not cache-compatible. Controlled and historical outcomes must never be pooled.')
