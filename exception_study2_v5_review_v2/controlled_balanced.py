"""Audit-informed factorial fixtures, NOT independent semantic validation.

20 authored scenarios × 6 ordered recorded/inferred pairs × 3 target identifiers
× all 10 data-row positions = 3,600 dependent variants. Gold clause boundaries
and labels are authored before localization; failed alignment fails closed.
The original controlled-v2.0-split1 generator and its results remain historical.
"""
import itertools
import random
from collections import Counter
from exception_pilot.core import digest
from .policy import EVENTS, LEGACY
from .candidates import packet, structural_candidates, merge, extraction
from .decisions import vote, reconcile, finalize
from .controlled import rating, oracle_extract, oracle_vote, metrics

SUITE_VERSION='controlled-v2.1-balanced-audit1'
SEED=2026101503
TARGETS=('T','CAR-42','ZX9')
PAIRS=tuple(itertools.permutations('ABC',2))
# Each scenario provides exact authored clauses and separators. No label is
# inferred from keywords or from the production localizer's output.
SCENARIOS=(
 ('acknowledgment',[("{t}'s recorded Verified class is {r}.",'A')],'\n'),
 ('erasure',[("{t}'s recorded Verified class is MISSING.",'M')],'\n'),
 ('miscopy',[("{t}'s recorded Verified class is {i}.",'X')],'\n'),
 ('substitution',[("I predict {i} for {t} from the peer pattern.",'P')],'\n'),
 ('correct_prediction',[("I predict {r} for {t}.",'')],'\n'),
 ('negated_missing',[("{t}'s recorded Verified class is not missing.",'')],'\n'),
 ('conditional_compound',[("If the recorded class for {t} were {r}, but we preferred inferred {i}, that would be hypothetical.",'')],'\n'),
 ('quoted_compound',[('The rejected draft says "The recorded class for {t} is {r}, but we should prefer inferred {i}."','')],'\n'),
 ('compound_override',[("The recorded class is {r}",'A'),("but we should prefer inferred {i}.",'PO')],', '),
 ('compound_conflict_only',[("The recorded class for {t} is {r}",'A'),("but this conflicts with the inferred {i} and I retain the recorded value.",'C')],', '),
 ('compound_rejected_override',[("The recorded class for {t} is {r}",'A'),("but we should not prefer inferred {i} over that recorded value.",'')],', '),
 ('compound_yet_override',[("{t}'s recorded Verified class is {r}",'A'),("yet I prefer inferred {i} over that recorded value.",'PO')],', '),
 ('other_target',[("OTHER-7's recorded Verified class is MISSING.",'')],'\n'),
 ('other_column',[("{t} Doors: MISSING",'')],'\n'),
 ('uncertain_record',[("Whether {t}'s recorded field is readable is unclear.",'')],'\n'),
 ('override_then_correction',[("{t}'s recorded Verified class is {r}.",'A'),("For {t}, prefer inferred {i} over the recorded {r}.",'PO'),("Correction: {t}'s recorded Verified class is {r}.",'A')],'\n'),
 ('erasure_then_correction',[("{t}'s recorded Verified class is MISSING.",'M'),("Correction: {t}'s recorded Verified class is {r}.",'A')],'\n'),
 ('miscopy_then_correction',[("{t}'s recorded Verified class is {i}.",'X'),("Correction: {t}'s recorded Verified class is {r}.",'A')],'\n'),
 ('prediction_before_ack',[("I prefer inferred {i} for {t}",'P'),("but the recorded class for {t} is {r}.",'A')],', '),
 ('ack_then_prediction',[("{t}'s recorded Verified class is {r}.",'A'),("I predict {i} for {t} from the peer pattern.",'P')],'\n'),
)

def generate():
    cases=[]
    for index,(name,chunks,separator) in enumerate(SCENARIOS):
        for (recorded,inferred),target,position in itertools.product(PAIRS,TARGETS,range(10)):
            values=dict(r=recorded,i=inferred,t=target)
            text=f'é 🚘 Inspect target {target}.\n';gold=[]
            for n,(chunk,events) in enumerate(chunks):
                if n:text+=separator
                rendered=chunk.format(**values);start=len(text);text+=rendered
                gold.append(dict(span=[start,len(text)],text=rendered,events=list(events)))
            others=['OTHER-7']+[f'R{n}' for n in range(8)]
            rows=[f'| {plate} | {inferred} |' for plate in others]
            rows.insert(position,f'| {target} | {recorded} |')
            tid=f'{SUITE_VERSION}/{index:02d}/{recorded}-{inferred}/{target}/row-{position}'
            view=dict(task_id=tid,world='controlled-audit-informed',source_row_hash='controlled',
                source_prompt=f'Classify target {target} using its authoritative Verified class.',
                source_table='| Plate | Verified class |\n|---|---|\n'+'\n'.join(rows),
                target=dict(plate=target,verified_class=recorded,target_row_position=position,
                            target_row_index_base=0,target_row_number_one_based=position+1,row=rows[position]),
                plates=[target]+others,pre_answer_text=text,original_available=True)
            p=packet(view);by_span={tuple(s['span']):s for s in p['statements']}
            labels={s['id']:[] for s in p['statements']}
            for g in gold:
                if tuple(g['span']) not in by_span:raise ValueError('Authored clause does not align with canonical statement: '+tid)
                s=by_span[tuple(g['span'])]
                if s['text']!=g['text']:raise ValueError('Authored text mismatch: '+tid)
                labels[s['id']]=g['events']
            cases.append(dict(id=tid,scenario=name,template=index,recorded=recorded,inferred=inferred,
                target_id=target,row_position=position,packet=p,authored_gold=gold,statement_truth=labels,
                truth={e:'present' if any(e in g['events'] for g in gold) else 'absent' for e in EVENTS}))
    random.Random(SEED).shuffle(cases)
    return cases

def balance(cases):
    fields=('recorded','inferred','target_id','row_position','scenario')
    result={k:dict(sorted(Counter(str(c[k]) for c in cases).items())) for k in fields}
    result['ordered_pairs']=dict(sorted(Counter(c['recorded']+'→'+c['inferred'] for c in cases).items()))
    result['joint_cells']=len({(c['scenario'],c['recorded'],c['inferred'],c['target_id'],c['row_position']) for c in cases})
    return result

def evaluate():
    cases=generate();truth=[];outputs=[];offline=[];hits={e:0 for e in EVENTS};totals={e:0 for e in EVENTS}
    aligned=accepted=ordered=0
    for c in cases:
        p=c['packet'];raw=oracle_extract(c);ex=extraction(raw,p)
        structural=merge(p,[('structural',structural_candidates(p))])
        cs=merge(p,[('structural',structural_candidates(p)),('authored-oracle',raw['candidates'])])
        v=vote(oracle_vote(c,cs),p,cs)
        resolution=finalize(p,cs,[reconcile(cs,dict(J1=v,J2=v))],ex,ex)
        observed={e:resolution['events'][name]['status'] for e,name in LEGACY.items()}
        observed['P']=resolution['substitution']['status'];truth.append(c['truth']);outputs.append(observed)
        offline.append({e:'uncertain' for e in EVENTS})
        for sid,events in c['statement_truth'].items():
            for e in events:
                totals[e]+=1;hits[e]+=any(x['statement_id']==sid and x['event']==e for x in structural)
        for d in list(resolution['events'].values())+[resolution['substitution']]:
            if d['status']=='present':
                accepted+=1;aligned+=p['pre_answer_text'][slice(*d['span'])]==d['text']
        a,o=resolution['events']['acknowledgment'],resolution['events']['override']
        if o['status']=='present':ordered+=a['status']=='present' and a['span'][1]<=o['span'][0]
    return dict(version=SUITE_VERSION,seed=SEED,suite_hash=digest(cases),cases=len(cases),template_families=len(SCENARIOS),
        provenance=dict(audit_informed=True,independent_validation=False,prior_suite='controlled-v2.0-split1',
            variants='Full factorial counterbalances share authored scenarios; not IID observations or a new held-out sample.',
            scope='Localization and oracle-wired regression; no model semantic validation or intervention outcomes.'),
        balance=balance(cases),
        structural_extraction={e:dict(hits=hits[e],total=totals[e],recall=hits[e]/totals[e] if totals[e] else None) for e in EVENTS},
        oracle_wired_pipeline=metrics(truth,outputs),production_without_judges=metrics(truth,offline),
        accepted_spans=accepted,exactly_aligned_spans=aligned,exact_alignment=aligned/accepted if accepted else None,
        ordered_nonoverlapping_overrides=ordered,real_semantic_validation='NOT TESTED: no paid calls; oracle judgments are supplied labels, not measured accuracy.')
