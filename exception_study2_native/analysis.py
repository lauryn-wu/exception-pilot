"""Descriptive, world-clustered paired contrasts; no arbitrary harm threshold."""
from collections import Counter,defaultdict
from exception_pilot.storage import write_json
from exception_study2_source_report_v2.reporting import WorldBootstrap
from . import STOP
from .diagnostics import cases as case_diagnostics, summarize
from .recovery import summary as recovery_summary


def boot(b,values):
    x=b.estimate(values)
    if x['interval_95'] and x['interval_95'][0]==x['interval_95'][1]:
        x['caveat']='Degenerate interval means no observed variation here, not population certainty.'
    return x


def report(c,current,invocation,write=True):
    cells=[r['cell'] for r in c.plan['requests']];cases=case_diagnostics(c,current)
    parsed={x['cell']['id']:x['score'] for x in cases if x['score'] is not None}
    conditions={};pairs={};gaps={}
    for cohort in ('pilot','main'):
        group=[x for x in cells if x['cohort']==cohort];b=WorldBootstrap(sorted({x['world'] for x in group}))
        for wording in ('original','lookup'):
            for relation in sorted({x['relation'] for x in group}):
                both=[x for x in group if x['wording']==wording and x['relation']==relation]
                for thinking in (False,True):
                    selected=[x for x in both if x['thinking']==thinking];returned=[x for x in selected if x['id'] in parsed]
                    key=f'{cohort}/{wording}/{relation}/thinking-{int(thinking)}'
                    conditions[key]=dict(planned=len(selected),completed=len(returned),unavailable=len(selected)-len(returned),
                        correct=sum(parsed[x['id']]['correct'] for x in returned),valid=sum(parsed[x['id']]['valid'] for x in returned),
                        malformed=sum(parsed[x['id']]['malformed'] for x in returned),truncated=sum(parsed[x['id']]['truncated'] for x in returned),
                        accuracy=boot(b,[(x['world'],parsed[x['id']]['correct']) for x in returned]),
                        validity=boot(b,[(x['world'],parsed[x['id']]['valid']) for x in returned]))
                matched=defaultdict(dict)
                for x in both:matched[x['pair_id']][x['thinking']]=x
                eligible=[p for p in matched.values() if set(p)=={False,True}]
                complete=[p for p in eligible if all(x['id'] in parsed for x in p.values())]
                pairs[f'{cohort}/{wording}/{relation}']=dict(eligible_pairs=len(eligible),completed_pairs=len(complete),
                    contrast='accuracy(thinking on) - accuracy(thinking off); positive means higher on accuracy',
                    estimate=boot(b,[(p[False]['world'],int(parsed[p[True]['id']]['correct'])-int(parsed[p[False]['id']]['correct'])) for p in complete]),
                    transitions=dict(Counter(str(parsed[p[False]['id']]['correct'])+'->'+str(parsed[p[True]['id']]['correct']) for p in complete)))
            quartets=defaultdict(dict)
            for x in group:
                if x['wording']==wording:quartets[(x['world'],x['variant'])][(x['relation'],x['thinking'])]=x
            keys={('support',False),('support',True),('conflict',False),('conflict',True)}
            eligible=[q for q in quartets.values() if set(q)==keys]
            complete=[q for q in eligible if all(x['id'] in parsed for x in q.values())]
            off=[];on=[];change=[]
            for q in complete:
                world=q[('support',False)]['world']
                penalty={t:int(parsed[q[('support',t)]['id']]['correct'])-int(parsed[q[('conflict',t)]['id']]['correct']) for t in (False,True)}
                off.append((world,penalty[False]));on.append((world,penalty[True]));change.append((world,penalty[True]-penalty[False]))
            gaps[f'{cohort}/{wording}']=dict(eligible_quartets=len(eligible),completed_quartets=len(complete),
                contrast='(support - conflict) on minus (support - conflict) off; positive means a larger conflict penalty with thinking',
                off_penalty=boot(b,off),on_penalty=boot(b,on),change=boot(b,change),
                limitation='Historical option has no support condition; gap is not estimable.' if not eligible else None)
    statuses=Counter(x['operation_status'] for x in cases)
    summary=dict(planned=len(cells),completed=statuses['returned'],reused=invocation['reused'],
        pending=len(cells)-statuses['returned'],executable_pending=statuses['never_started'],failed=statuses['failed'],interrupted=statuses['ambiguous'],
        malformed=sum(x['malformed'] for x in parsed.values()),truncated=sum(x['truncated'] for x in parsed.values()))
    r=dict(protocol=c.plan['protocol'],plan_hash=c.plan['artifact_hash'],design=c.plan['design']['design'],
        cohort=c.plan['cohort'],budget=c.plan['budget'],budget_policy=c.plan['budget_policy'],
        main_budget_status='AWAITING_PILOT_REVIEW' if c.plan['cohort']=='pilot' else 'FROZEN_AFTER_PILOT_REVIEW',
        length_repetition=summarize(cases),journal_recovery=recovery_summary(c),counts=summary,this_invocation=invocation,conditions=conditions,paired_thinking=pairs,conflict_penalty_change=gaps,cases=cases,
        denominator='All returned outputs, including malformed/truncated, are in accuracy denominators. Failed/interrupted/pending attempts are unavailable, not incorrect. Paired contrasts use common returned cells.',
        interpretation='Draft full-factorial lookup control reported separately. Cluster unit is world; variants/conditions are not independent samples. No absolute accuracy threshold proves harm. Historical visible-explanation results are never reused.',next_stage=STOP)
    if write:write_json(c.out/'analysis.json',r)
    return r
