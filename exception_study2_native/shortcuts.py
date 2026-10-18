"""Offline shortcuts from final rendered tables; no model fitting dependency or inference."""
from collections import Counter, defaultdict
from .tables import parse, audit_table, association, DISTRACTORS


def choose(labels):
    labels=sorted(labels)
    return dict(prediction=labels[0] if len(labels)==1 else None,candidates=labels,
                abstention=None if len(labels)==1 else 'tie' if labels else 'no_candidate')


def extremum(counts,maximum=True):
    value=(max if maximum else min)(counts.values())
    return choose([c for c in 'ABC' if counts[c]==value])


def counts(rows):return {c:sum(r['label']==c for r in rows) for c in 'ABC'}


def predictions(rows,target):
    bg=[r for r in rows if r['plate']!=target['plate']];result={}
    for scope,rs in (('full',rows),('background',bg)):
        ns=counts(rs)
        result[scope+'/majority']=extremum(ns)
        result[scope+'/minority']=extremum(ns,False)
        for mod in (2,3,4):
            for remainder in range(mod):
                result[f'{scope}/mod{mod}-equals-{remainder}']=choose([c for c in 'ABC' if ns[c]%mod==remainder])
            hist=Counter(n%mod for n in ns.values())
            result[f'{scope}/mod{mod}-singleton-remainder']=choose([c for c in 'ABC' if hist[ns[c]%mod]==1])
        same=[r for r in rs if all(r[f]==target[f] for f in DISTRACTORS)]
        result[scope+'/joint-profile-majority']=extremum(counts(same)) if same else choose([])
    for f in DISTRACTORS:
        match=counts([r for r in bg if r[f]==target[f]]);totals=counts(bg)
        result['background/'+f+'-count']=extremum(match)
        rates={c:match[c]/totals[c] if totals[c] else 0 for c in 'ABC'}
        result['background/'+f+'-rate']=extremum(rates)
    return result


def held_out(rows,group):
    """Exact-histogram lookup and nearest L1 histogram, ties abstain; whole groups excluded."""
    all_votes=defaultdict(Counter);by_group=defaultdict(lambda:defaultdict(Counter))
    for x in rows:
        key=tuple(x['full_class_counts'][c] for c in 'ABC')
        all_votes[key][x['expected']]+=1;by_group[x[group]][key][x['expected']]+=1
    for held,excluded in by_group.items():
        train={key:votes-excluded[key] for key,votes in all_votes.items()}
        train={key:votes for key,votes in train.items() if votes}
        for x in (x for x in rows if x[group]==held):
            key=tuple(x['full_class_counts'][c] for c in 'ABC')
            vote=train.get(key,Counter())
            x['baselines'][group+'/histogram-exact']=extremum({c:vote[c] for c in 'ABC'}) if vote else choose([])
            if not train:nearest=choose([])
            else:
                distances={k:sum(abs(a-b) for a,b in zip(key,k)) for k in train}
                d=min(distances.values());vote=Counter()
                for k in train:
                    if distances[k]==d:vote.update(train[k])
                nearest=extremum({c:vote[c] for c in 'ABC'})
            x['baselines'][group+'/histogram-nearest-L1']=nearest


def summarize(rows):
    names=sorted({n for x in rows for n in x['baselines']});result={}
    for name in names:
        available=[x for x in rows if name in x['baselines']]
        predicted=[x for x in available if x['baselines'][name]['prediction'] is not None]
        correct=sum(x['baselines'][name]['prediction']==x['expected'] for x in predicted)
        result[name]=dict(tables=len(available),predicted=len(predicted),correct=correct,wrong=len(predicted)-correct,
            ties=sum(x['baselines'][name]['abstention']=='tie' for x in available),
            no_candidate=sum(x['baselines'][name]['abstention']=='no_candidate' for x in available),
            coverage=len(predicted)/len(available) if available else None,
            accuracy_when_predicted=correct/len(predicted) if predicted else None,
            correct_fraction_all=correct/len(available) if available else None,
            pattern_agreement=sum(x['baselines'][name]['prediction']==x['pattern'] for x in predicted),
            perfect_full_coverage=bool(available) and correct==len(available))
    return result


def oracle(rows):
    votes=defaultdict(Counter)
    for x in rows:votes[tuple(x['full_class_counts'][c] for c in 'ABC')][x['expected']]+=1
    correct=sum(max(v.values()) for v in votes.values())
    return dict(histograms=len(votes),tables=len(rows),maximum_correct=correct,
        accuracy=correct/len(rows) if rows else None,
        limitation='In-sample histogram-only upper bound on this fixed manifest, not held-out accuracy or evidence of model use.',
        label_counts_by_histogram={'/'.join(map(str,k)):dict(v) for k,v in sorted(votes.items())})


def audit_shortcuts(tables,details=True):
    cases=[]
    for t in tables:
        rows=parse(t['table']);target=next(r for r in rows if r['plate']==t['target_plate'])
        if target['label']!=t['expected']:raise ValueError('Shortcut audit source truth mismatch')
        bg=[r for r in rows if r is not target]
        x={k:t[k] for k in ('world','cohort','cue_state','variant','relation','expected','pattern')}
        if 'block' in t:x['block']=t['block']
        x.update(full_class_counts=counts(rows),background_class_counts=counts(bg),baselines=predictions(rows,target))
        if details:x['associations_and_covariates']=audit_table(t['table'],t['target_plate'],t['expected'],t['pattern'])
        cases.append(x)
    held_out(cases,'world')
    if cases and all('block' in x for x in cases):held_out(cases,'block')
    groups={}
    for cohort in ('all','pilot','main'):
        for relation in ('all','support','conflict'):
            selected=[x for x in cases if (cohort=='all' or x['cohort']==cohort) and (relation=='all' or x['relation']==relation)]
            if selected:groups[cohort+'/'+relation]=summarize(selected)
    result=dict(kind='FINAL_RENDERED_SHORTCUT_AUDIT_V2',tables=len(cases),worlds=len({t['world'] for t in tables}),
        groups=groups,histogram_only_upper_bound=oracle(cases),cases=cases,
        gate='Reject audited baselines with perfect accuracy on any nonempty covered set of the full manifest, and histograms identifying a unique answer across the full manifest. Subgroup/small-sample predictability is disclosed; no chance-level requirement.',
        cv='World-held-out folds exclude every variant/cue of that world. Block-held-out additionally excludes all six label-permutation worlds; no hyperparameter search. Fit on other worlds/blocks only; pilot/main metrics are descriptive slices of those predictions, not a preregistered pilot-to-main learner.',
        limitations='A finite audit cannot rule out all shortcuts. Partial-coverage perfect rules and richer interactions remain possible; histogram bounds describe this sample only. Same-world cells are not independent. Target remains last, so position-based copying remains possible and is disclosed.')
    result['perfect_shortcuts']=[n for n,v in groups['all/all'].items() if v['accuracy_when_predicted']==1]
    if any(len(v)==1 for v in result['histogram_only_upper_bound']['label_counts_by_histogram'].values()):
        result['perfect_shortcuts'].append('histogram-identifies-unique-answer')
    if details:
        pooled={}
        for cohort in ('all','pilot','main'):
            selected=[t for t in tables if cohort=='all' or t['cohort']==cohort]
            if not selected:continue
            for scope in ('background','full'):
                rows=[r for t in selected for r in parse(t['table']) if scope=='full' or r['plate']!=t['target_plate']]
                pooled[cohort+'/'+scope]=dict(rows=len(rows),features={f:association(rows,(f,)) for f in DISTRACTORS},
                    joint=association(rows,DISTRACTORS))
            for relation in ('support','conflict'):
                role_rows=[]
                for t in selected:
                    if t['relation']!=relation:continue
                    alternative=t['roles'][1-t['variant']]
                    role_map={t['expected']:'recorded',alternative:'other_record_variant',t['roles'][2]:'third'}
                    role_rows.extend(dict(r,label=role_map[r['label']]) for r in parse(t['table']) if r['plate']!=t['target_plate'])
                if role_rows:pooled[cohort+'/'+relation+'/relative-role-background']=dict(rows=len(role_rows),joint=association(role_rows,DISTRACTORS))
        result['pooled_associations']=pooled
        result['pooled_caveat']='Raw A/B/C independence after pooling label permutations does not imply per-table independence or absence of association with recorded/pattern roles. Relative-role associations are separately shown.'
    return result


def require_no_perfect_shortcut(report):
    if report['perfect_shortcuts']:
        raise ValueError('Draft blocked by perfect shortcut: '+', '.join(report['perfect_shortcuts']))
