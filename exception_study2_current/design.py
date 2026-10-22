"""Fresh controlled-v2 scaffolds, audited with the unchanged historical helpers."""
import copy
import itertools
from collections import Counter
from exception_pilot.core import DESCRIPTORS, digest, rng_for
from exception_continuation.core import INTRO, QUESTION
from exception_study2_v5.core import LOOKUP
from exception_study2_native import FINAL_INSTRUCTION
from exception_study2_native.design import PROFILES
from exception_study2_native.tables import FIELDS, DISTRACTORS, parse, render, audit_table
from exception_study2_native.shortcuts import audit_shortcuts, require_no_perfect_shortcut
from . import VERSION, SEED, BUDGET

# Four prespecified count families, each crossed with all six label-role assignments.
# Feature assignment and target profile are fresh by WORLD, not copies under relabeling.
COUNTS = ((4,5,6), (6,5,4), (4,4,7), (5,5,5))
ABSENCE_CLAUSE = (' MISSING means the verified class has not been recorded. If that cell is '
                  'MISSING, make your best prediction from the other records.')


def tables():
    result=[]
    for index,(block,labels) in enumerate(itertools.product(range(4),itertools.permutations('ABC'))):
        rng=rng_for(VERSION,SEED,'world',index)
        climate=('cold','warm')[block%2]; counts=COUNTS[block]
        doubled='XYZ'[index%3]; marks=[doubled,doubled]+[m for m in 'XYZ' if m!=doubled]
        descriptors={c:rng.sample(DESCRIPTORS[c],5) for c in ('cold','warm')}
        profiles=[j%4 for j in range(15)]; rng.shuffle(profiles)
        specs=[(g,g) for g in range(3) for _ in range(4)]
        specs += [(3,g) for g in range(3) for _ in range(counts[g]-4)]
        rows=[]
        for j,(group,role) in enumerate(specs):
            c=climate if group==0 else ('warm' if climate=='cold' else 'cold')
            profile=profiles[j]; bits=PROFILES[profile]
            rows.append(dict(plate='S'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=9)),
                description=descriptors[c][j%4 if group==0 else j%5],
                transmission=('Manual','Automatic')[bits[0]],seat_cover=('Cloth','Vinyl')[bits[1]],
                doors=('Two','Four')[bits[2]],audit_marker=marks[profile],group=group,role=role))
        rng.shuffle(rows); profile=index%4; bits=PROFILES[profile]
        target=dict(plate='S'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=9)),
            description=descriptors[climate][4],transmission=('Manual','Automatic')[bits[0]],
            seat_cover=('Cloth','Vinyl')[bits[1]],doors=('Two','Four')[bits[2]],audit_marker=marks[profile])
        # Removes opaque IDs, label names and descriptor synonyms; proves distinct scaffolds.
        fingerprint=digest([[r['group'],r['role'],*[r[f] for f in DISTRACTORS]] for r in rows])
        for cue,variant in itertools.product(range(2),repeat=2):
            values=copy.deepcopy(rows)
            for r in values:
                role=cue if r['group']==0 else 1-cue if r['group']==1 else r['role']
                r['label']=labels[role]
            values.append(dict(target,label=labels[variant]))
            result.append(dict(world=f'current-qwen-v1-{index:03d}',block=block,cohort='screen',
                variant=variant,cue_state=cue,relation='support' if cue==variant else 'conflict',
                expected=labels[variant],pattern=labels[cue],roles=list(labels),
                background_role_counts=list(counts),target_plate=target['plate'],climate=climate,
                target_profile=profile,doubled_marker=doubled,scaffold_hash=fingerprint,table=render(values)))
    validate(result)
    return result


def validate(ts):
    if len(ts)!=96 or len({t['world'] for t in ts})!=24: raise ValueError('Expected 24 worlds / 96 tables')
    worlds={}
    for t in ts:
        a=audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
        if (len(parse(t['table']))!=16 or a['target_row_1based']!=16 or
            a['background_class_counts']!=dict(zip(t['roles'],COUNTS[t['block']])) or
            a['same_climate_peer_classes']!={t['pattern']:4} or
            t['relation']!=('support' if t['expected']==t['pattern'] else 'conflict')):
            raise ValueError('Controlled-v2 count, cue, source or position invariant failed')
        if 'MISSING' in t['table'].upper(): raise ValueError('Forbidden absence clause')
        worlds.setdefault(t['world'],{})[(t['cue_state'],t['variant'])]=t
    for cases in worlds.values():
        if set(cases)!={(0,0),(0,1),(1,0),(1,1)}: raise ValueError('Incomplete table pairing')
        for cue in (0,1):
            a,b=[parse(cases[cue,v]['table']) for v in (0,1)]
            if [(i,k) for i in range(16) for k in FIELDS if a[i][k]!=b[i][k]]!=[(15,'label')]:
                raise ValueError('Target variant changes more than its recorded cell')
        for v in (0,1):
            a,b=[parse(cases[c,v]['table']) for c in (0,1)]
            changed=[(i,k) for i in range(16) for k in FIELDS if a[i][k]!=b[i][k]]
            if len(changed)!=8 or any(i==15 or k!='label' for i,k in changed):
                raise ValueError('Background change must swap eight labels, preserving target')
    first=[cs[0,0] for cs in worlds.values()]
    if len({t['scaffold_hash'] for t in first})!=24: raise ValueError('Relabeled copies are not fresh worlds')
    if Counter(t['climate'] for t in first)!={'cold':12,'warm':12}: raise ValueError('Climate balance')
    for block in range(4):
        if {tuple(t['roles']) for t in first if t['block']==block}!=set(itertools.permutations('ABC')):
            raise ValueError('Label-role counterbalance')
    for relation,variant in itertools.product(('support','conflict'),range(2)):
        selected=[t for t in ts if t['relation']==relation and t['variant']==variant]
        if Counter(t['expected'] for t in selected)!={'A':8,'B':8,'C':8}: raise ValueError('Recorded-label balance')
        if Counter(t['pattern'] for t in selected)!={'A':8,'B':8,'C':8}: raise ValueError('Pattern-label balance')
    require_no_perfect_shortcut(audit_shortcuts(ts,details=False))


def make_design():
    if not INTRO.endswith(ABSENCE_CLAUSE): raise ValueError('Historical introduction changed; inspect explicitly')
    intro=INTRO[:-len(ABSENCE_CLAUSE)]; ts=tables(); cells=[]
    for t in ts:
        for wording,thinking in itertools.product(('original','lookup'),(False,True)):
            question=QUESTION if wording=='original' else LOOKUP.format(plate=t['target_plate'])
            prompt=intro+'\n\n'+t['table']+'\n\nLicense plate: '+t['target_plate']+'\n'+question+'\n'+FINAL_INSTRUCTION
            if 'MISSING' in prompt.upper(): raise ValueError('No absence language in experimental prompts')
            cell=dict(t,wording=wording,thinking=thinking,prompt=prompt,prompt_hash=digest(prompt),
                seed=int(digest([VERSION,SEED,t['world'],wording])[:8],16))
            cell['id']=f"{t['world']}/v{t['variant']}/{t['relation']}/{wording}/thinking-{int(thinking)}"
            cells.append(cell)
    rng_for(VERSION,SEED,'schedule').shuffle(cells)
    return dict(protocol=VERSION,seed=SEED,tables=ts,cells=cells,
        counterbalance={f'{relation}/v{variant}':{key:dict(Counter(str(t[key]) for t in ts if t['relation']==relation and t['variant']==variant))
            for key in ('expected','pattern','climate','target_profile','doubled_marker')}
            for relation in ('support','conflict') for variant in (0,1)},
        counts=dict(worlds=24,construction_blocks=4,tables=96,responses=384,maximum_output_tokens=384*BUDGET),
        construction='24 unique feature/row scaffolds in four shared count families. Controlled-v2 extension, not historical-table replication. Target remains last. Per-table and pooled nuisance correlations are audited, not assumed absent.',
        clustering='Primary intervals resample the four prespecified construction blocks; 24-world intervals are descriptive sensitivity estimates. Six counterbalanced worlds per block are not six independent construction families.')
