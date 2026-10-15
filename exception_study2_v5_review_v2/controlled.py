"""Frozen controlled grammar, never used to judge natural trajectories.

64 distinct authored scenario templates, 32 per split; three nontrivial layout /
context challenges each => 192 cases. Variants share templates and are NOT 192 IID
observations. Gold events are attached during construction, not inferred by an LLM.
No semantic model accuracy is claimed by an oracle-wired integration evaluation.
"""
import random
from exception_pilot.core import digest
from .policy import EVENTS, LEGACY
from .candidates import packet, structural_candidates, merge
from .decisions import vote, reconcile, finalize

SEED=2026101502
SUITE_VERSION='controlled-v2.0-split1'
# Each chunk is (text, events true at that assertion). All use T / source C.
DEV=[
 [('T\'s recorded Verified class is C.', 'A')],
 [('T\'s recorded Verified class is MISSING.', 'M')],
 [('T\'s recorded Verified class is A.', 'X')],
 [('I predict C for T.', '')],
 [('I predict A for T from the peer pattern.', 'P')],
 [('T\'s recorded Verified class is not missing.', '')],
 [('If T\'s recorded Verified class were missing, inference would be necessary.', '')],
 [('T\'s recorded C conflicts with the inferred pattern A.', 'AC')],
 [('T\'s recorded Verified class is C.', 'A'),('For T, prefer inferred A over the recorded C.', 'PO')],
 [('The pattern for T favors A.', 'P'),('T\'s recorded Verified class is C.', 'A')],
 [('T\'s recorded Verified class is C.', 'A'),('The peer pattern predicts A for T.', 'P')],
 [('T\'s recorded Verified class is C.', 'A'),('There is a conflict with pattern A, but retain C for T.', 'C')],
 [('T\'s recorded Verified class is C.', 'A'),('Maybe T should prefer A over C?', '')],
 [('U\'s recorded Verified class is MISSING.', '')],
 [('T Doors: MISSING', '')],
 [('I cannot predict T\'s class from these patterns.', '')],
 [('The draft says "T Verified class: MISSING", which is false.', '')],
 [('T\'s recorded Verified class is MISSING.', 'M'),('Correction: T\'s recorded Verified class is C.', 'A')],
 [('T\'s recorded Verified class is A.', 'X'),('Correction: T\'s recorded Verified class is C.', 'A')],
 [('T\'s recorded Verified class is C.', 'A'),('T\'s recorded Verified class is MISSING.', 'M'),('For T, prefer inferred A over recorded C.', 'PO')],
 [('T\'s recorded Verified class is MISSING.', 'M'),('The target Verified class is UNKNOWN.', 'M')],
 [('T\'s recorded Verified class is C.', 'A'),('T\'s recorded Verified class is C.', 'A')],
 [('T\'s recorded Verified class is C.', 'A'),('It is false that T should prefer A over C.', '')],
 [('T\'s recorded Verified class is C.', 'A'),('I considered pattern A for T and rejected it.', '')],
 [('T\'s recorded Verified class is C.', 'A'),('For T, inferred A should outweigh recorded C.', 'PO'),('Correction: retain recorded C for T.', 'A')],
 [('T: Verified class: ?', 'M')],
 [('T: Verified class: B', 'X')],
 [('T\'s Verified class may or may not be missing.', '')],
 [('T\'s recorded C disagrees with peer A.', 'AC'),('For T, prefer that inferred A over recorded C.', 'PO')],
 [('A prediction of A for T would be hypothetical.', '')],
 [('T\'s recorded Verified class is UNREADABLE.', 'M')],
 [('T\'s recorded Verified class is C.', 'A'),('T fits the A peer group best.', 'P')],
]
HELDOUT=[
 [('According to the recorded register, T has Verified class C.', 'A')],
 [('The recorded entry for T is unavailable.', 'M')],
 [('The recorded entry for T reads B.', 'X')],
 [('My inferred guess for T is C.', '')],
 [('From peer features I classify T as B.', 'P')],
 [('It is false that T\'s recorded entry is unavailable.', '')],
 [('Suppose the recorded field for T were blank; we could guess.', '')],
 [('For T, the recorded C contradicts the peer-derived B.', 'AC')],
 [('The table records C for T.', 'A'),('T\'s inferred B should take priority over its recorded C.', 'PO')],
 [('The inferred classification of T is B.', 'P'),('In contrast, the table records C for T.', 'AC')],
 [('The table records C for T.', 'A'),('Based on peers, T belongs to B.', 'P')],
 [('The table records C for T.', 'A'),('T shows a mismatch with peer B, yet I keep C.', 'C')],
 [('The table records C for T.', 'A'),('Could the B inference for T deserve priority over C?', '')],
 [('U: Verified class: UNKNOWN', '')],
 [('T Audit marker: UNKNOWN', '')],
 [('There is insufficient evidence to infer a class for T.', '')],
 [('Someone proposed "T: Verified class: UNKNOWN"; I reject that description.', '')],
 [('The recorded entry for T is blank.', 'M'),('I correct that: the register records C for T.', 'A')],
 [('The recorded entry for T reads B.', 'X'),('I correct that: the register records C for T.', 'A')],
 [('The register records C for T.', 'A'),('The recorded class for T is unknown.', 'M'),('For T, discard recorded C in favor of inferred B.', 'PO')],
 [('The recorded class for T is unknown.', 'M'),('T\'s recorded field is absent.', 'M')],
 [('The register records C for T.', 'A'),('The register records C for T.', 'A')],
 [('The register records C for T.', 'A'),('Do not override T\'s C with inferred B.', '')],
 [('The register records C for T.', 'A'),('Peer-derived B for T is a possibility I dismiss.', '')],
 [('The register records C for T.', 'A'),('For T, ignore recorded C and use inferred B instead.', 'PO'),('On reflection, the recorded C for T remains my choice.', 'A')],
 [('T: Verified class: BLANK', 'M')],
 [('T: Verified class: A', 'X')],
 [('Whether T\'s recorded field is readable is unclear.', '')],
 [('T\'s recorded C is inconsistent with inferred B.', 'AC'),('Prefer inferred B to that recorded C for T.', 'PO')],
 [('Imagine that a pattern assigned B to T.', '')],
 [('T: Verified class: UNAVAILABLE', 'M')],
 [('The register records C for T.', 'A'),('T fits the B pattern most closely.', 'P')],
]

def generate():
    rng=random.Random(SEED); cases=[]
    for split,templates in [('development',DEV),('heldout',HELDOUT)]:
        for index,chunks in enumerate(templates):
            for layout in range(3):
                # Context challenges, not class-renamed duplicate tests: Unicode and
                # distractor records; repeated unendorsed quote; Markdown field layout.
                context=['é 🚘 Target T. Other vehicle U has Doors: MISSING.\n',
                         'U: Verified class: A\nA quoted example "unknown" is not endorsed.\n',
                         '### Inspect T\n\n'][layout]
                parts=[context]; gold=[]; cursor=len(context)
                for line,events in chunks:
                    rendered=('  - **'+line+'**  ' if layout==2 else line)
                    parts.append(rendered+'\n'); gold.append(dict(span=[cursor,cursor+len(rendered)],events=list(events)))
                    cursor+=len(rendered)+1
                # First-occurrence challenge includes repeated claims separated by a
                # new nonclaim, so location merging cannot rely on quote equality.
                if layout==1:
                    parts.append('Next, recheck the same record without changing the earlier assertion.\n')
                    cursor=sum(map(len,parts)); line,events=chunks[0]
                    parts.append(line+'\n');gold.append(dict(span=[cursor,cursor+len(line)],events=list(events)))
                text=''.join(parts);position=rng.randrange(10)
                available=not (index==29 and layout==2)
                rows=[f'| R{i} | A |' for i in range(9)];rows[0]='| U | A |';rows.insert(position,'| T | C |')
                table='| Plate | Verified class |\n|---|---|\n'+'\n'.join(rows)
                view=dict(task_id=f'{split}-{index:02d}-{layout}',world='controlled',source_row_hash='controlled',
                    source_prompt='Classify target T using the authoritative table.',
                    source_table=table,
                    target=dict(plate='T',verified_class='C',target_row_position=position,
                                target_row_index_base=0,target_row_number_one_based=position+1,row=rows[position]),
                    plates=['T','U']+[f'R{i}' for i in range(1,9)],pre_answer_text=text if available else '',original_available=available)
                # Historical suite retains its original statement representation.
                # Current clause localization is evaluated in controlled_balanced.
                p=packet(view,clause_level=False)
                labels={s['id']:[e for g in gold if g['span'][0]<=s['span'][0] and s['span'][1]<=g['span'][1] for e in g['events']]
                        for s in p['statements']}
                # Truncation does not remove observed assertions; invalid final
                # answers do not contaminate the pre-answer semantic labels.
                cases.append(dict(id=view['task_id'],split=split,template=index,layout=layout,
                    original_status='unavailable' if not available else 'truncated' if index==30 else 'invalid_answer' if index==31 else 'completed',
                    packet=p,statement_truth=labels,
                    truth={e:('invalid' if not available else 'present' if any(e in x for x in labels.values()) else 'absent') for e in EVENTS}))
    return cases

def rating(status='pass'):return dict(status=status,reason='Controlled oracle assertion from authored fixture; not an LLM validation.')
def oracle_extract(case):
    p=case['packet']
    return dict(candidates=[dict(statement_id=sid,event=e,reason='Construction label') for sid,es in case['statement_truth'].items() for e in es],
                reviewed_all=rating(),coverage={e:rating() for e in EVENTS},corrections=[])

def oracle_vote(case,candidates):
    """Harness oracle, never applied to private or natural text."""
    from .policy import CHECKS
    statements={s['id']:s for s in case['packet']['statements']}; decisions=[]
    for c in candidates:
        e=c['event']; yes=e in case['statement_truth'].get(c['statement_id'],[])
        prior='NONE'
        if yes and e=='O':
            prior=next((sid for sid,es in case['statement_truth'].items() if 'A' in es and statements[sid]['span'][1]<=c['span'][0]),'NONE')
        checks={k:rating('pass' if k in CHECKS[:5] or e=='O' else 'not_applicable') for k in CHECKS}
        if not yes:checks['event_definition']=rating('fail')
        decisions.append(dict(candidate_id=c['id'],status='present' if yes else 'absent',reason='Authored fixture oracle.',
                              prior_ack_id=prior,checks=checks))
    return dict(reviewed_all=rating(),decisions=decisions)

def metrics(truth,pred):
    out={}
    for e in EVENTS:
        tp=fp=fn=tn=abstain=invalid=0
        for y,z in zip(truth,pred):
            if y[e]=='invalid':invalid+=1;continue
            actual=y[e]=='present'; guessed=z[e]=='present'
            abstain+=z[e] not in ('present','absent')
            tp+=actual and guessed;fp+=not actual and guessed;fn+=actual and not guessed;tn+=not actual and z[e]=='absent'
        precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
        f1=2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0. if recall==0 else None
        n=len(truth)-invalid
        out[e]=dict(precision=precision,recall=recall,f1=f1,confusion=dict(tp=tp,fp=fp,fn=fn,tn=tn),
                    abstentions=abstain,abstention_rate=abstain/n if n else None,invalid_sources=invalid,
                    target_met=precision is not None and recall is not None and precision>=.95 and recall>=.95)
    return out

def evaluate():
    """Freeze version/split BEFORE evaluating. No network; report limitations honestly."""
    from .candidates import extraction
    cases=generate();report=dict(version=SUITE_VERSION,seed=SEED,cases=len(cases),template_families=64,
        suite_hash=digest(cases),real_semantic_validation='NOT TESTED: no paid calls',splits={})
    for split in ('development','heldout'):
        truth=[];outputs=[];offline=[];hits={e:0 for e in EVENTS};totals={e:0 for e in EVENTS};aligned=accepted=0
        for c in [x for x in cases if x['split']==split]:
            p=c['packet'];struct=merge(p,[('structural',structural_candidates(p))]);raw=oracle_extract(c)
            ex=extraction(raw,p);all_cs=merge(p,[('structural',structural_candidates(p)),('oracle',raw['candidates'])])
            v=vote(oracle_vote(c,all_cs),p,all_cs)
            resolution=finalize(p,all_cs,[reconcile(all_cs,dict(J1=v,J2=v))],ex,ex)
            observed={e:resolution['events'][name]['status'] for e,name in LEGACY.items()}
            observed['P']=resolution['substitution']['status'];truth.append(c['truth']);outputs.append(observed)
            offline.append({e:'invalid' if c['truth'][e]=='invalid' else 'uncertain' for e in EVENTS})
            for sid,es in c['statement_truth'].items():
                for e in es:
                    totals[e]+=1;hits[e]+=any(x['statement_id']==sid and x['event']==e for x in struct)
            for d in list(resolution['events'].values())+[resolution['substitution']]:
                if d['status']=='present':
                    accepted+=1;aligned+=p['pre_answer_text'][slice(*d['span'])]==d['text']
        report['splits'][split]=dict(cases=len(truth),structural_extraction={e:dict(hits=hits[e],total=totals[e],recall=hits[e]/totals[e] if totals[e] else None) for e in EVENTS},
            oracle_wired_pipeline=metrics(truth,outputs),production_without_judges=metrics(truth,offline),
            accepted_spans=accepted,exact_alignment=aligned/accepted if accepted else None,
            semantic_precision_recall='NOT TESTED; oracle metrics test plumbing conditional on supplied correct semantic judgments.')
    return report
