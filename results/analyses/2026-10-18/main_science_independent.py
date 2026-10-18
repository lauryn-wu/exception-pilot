import json,math,random,statistics
from pathlib import Path
from collections import Counter,defaultdict
P=Path('/workspace/scratch/ea260d81d736/source_user_main_results_audit/study2-source-user-main-v1')
plan=json.loads((P/'main-plan.json').read_text());report=json.loads((P/'report.json').read_text()); qs=plan['queries']
returns={v['id']:v for f in (P/'operations-v5').rglob('returned.json') for v in [json.loads(f.read_text())]}
rawlegacy=json.loads((P/'legacy-values.json').read_text())['values']
R=[]; errors=[]
tok={'A':[32,151645],'B':[33,151645],'C':[34,151645],'MISSING':[79470,1718,151645]}
for q in qs:
 lines=[line for line in q['original_user_prompt'].splitlines() if line.startswith('|') and line.split('|')[1].strip()==q['target_plate']]
 assert len(lines)==1
 truth=lines[0].split('|')[-2].strip();assert truth==q['expected']
 rr=returns[q['id']]['result'];a=rr['text'];assert rr['tokens']==tok[a] and rr['stopped'] is True and rr['finish']=='eos' and not rr['next_token_logits']
 r={'id':q['id'],'task':q['task_id'],'world':q['world'],'k':q['checkpoint'],'truth':truth,'answer':a,'correct':a==truth,'pattern':q['pattern'],'natural':q['natural_final_answer'],'pref':{},'sequence':{},'mass':{}}
 for cue in ('0','1'):
  v=rawlegacy[q['legacy'][cue]['computation_id']]['value']; scores=v['scores']; cls={a:x['token_logprobs'][0] for a,x in scores.items()}; seq={a:sum(x['token_logprobs']) for a,x in scores.items()}
  for target,mode,vals in [('pref','class_token',cls),('sequence','whole_sequence_sensitivity',seq)]:
   tied=[a for a,x in vals.items() if x==max(vals.values())]; pred=tied[0] if len(tied)==1 else None
   assert pred==q['legacy'][cue][mode]['preferred_class']
   assert q['legacy'][cue][mode]['logprobs']==vals
   assert math.isclose(sum(math.exp(x) for x in vals.values()),q['legacy'][cue][mode]['abc_mass'],rel_tol=1e-12)
   r[target][cue]='tie' if pred is None else 'verified' if pred==truth else 'pattern' if pred==q['pattern'] else 'other'
  r['mass'][cue]=sum(math.exp(x) for x in cls.values())
 R.append(r)
 print('',end='')
by=defaultdict(dict)
for r in R:by[r['task']][r['k']]=r
out={}
for k in (0,256,512):
 rows=[r for r in R if r['k']==k]
 cnt=Counter('correct' if r['correct'] else 'MISSING' if r['answer']=='MISSING' else 'wrong_label' for r in rows)
 assert cnt==report['checkpoints'][str(k)]['categories']
 out[str(k)]={'N':len(rows),'categories':dict(cnt),'errors':[(r['task'],r['truth'],r['answer']) for r in rows if not r['correct']],'worlds_with_errors':len({r['world'] for r in rows if not r['correct']}),'cues':{}}
 for cue in ('0','1'):
  cr={}
  for field,key in [('pref','first_class_token'),('sequence','newline_inclusive_sensitivity')]:
   prefcounts=Counter(r[field][cue] for r in rows);cross=Counter(r[field][cue]+'/'+('correct' if r['correct'] else 'MISSING' if r['answer']=='MISSING' else 'wrong_label') for r in rows)
   assert prefcounts==report['cached_preference_comparisons'][str(k)][cue][key]['preference_counts']
   assert cross==report['cached_preference_comparisons'][str(k)][cue][key]['cross_counts']
   cr[field]={'counts':dict(prefcounts),'cross':dict(cross)}
  cr['mass']={'mean':statistics.mean(r['mass'][cue] for r in rows),'median':statistics.median(r['mass'][cue] for r in rows),'min':min(r['mass'][cue] for r in rows)}
  out[str(k)]['cues'][cue]=cr
 out[str(k)]['natural_cross']=dict(Counter(('natural_correct' if r['natural']['correct'] else 'natural_wrong' if r['natural']['valid'] else 'natural_invalid')+'/'+('source_correct' if r['correct'] else r['answer']) for r in rows))
 out[str(k)]['both_cues_cross']=dict(Counter(r['pref']['0']+'/'+r['pref']['1']+'/'+('source_correct' if r['correct'] else r['answer']) for r in rows))
worlds=sorted({r['world'] for r in R});rng=random.Random(2026101601);draws=[rng.choices(worlds,k=len(worlds)) for _ in range(2000)]
paired={}
for a,b in [(0,256),(0,512),(256,512)]:
 vals=[v for v in by.values() if a in v and b in v];trans=Counter(str(int(v[a]['correct']))+'->'+str(int(v[b]['correct'])) for v in vals)
 d=[(v[a]['world'],int(v[b]['correct'])-int(v[a]['correct'])) for v in vals];grp=defaultdict(list)
 for w,x in d:grp[w].append(x)
 boot=sorted(sum(sum(grp.get(w,[])) for w in draw)/sum(len(grp.get(w,[])) for w in draw) for draw in draws)
 ci=[boot[50],boot[1950]]
 assert ci==report['paired'][f'{a}->{b}']['paired_accuracy_change_bootstrap']['interval_95']
 paired[f'{a}->{b}']={'N':len(vals),'earlier_correct':sum(v[a]['correct'] for v in vals),'later_correct':sum(v[b]['correct'] for v in vals),'change':sum(x for w,x in d)/len(d),'transition':dict(trans),'ci':ci,'worlds_decline':len({v[a]['world'] for v in vals if v[a]['correct'] and not v[b]['correct']})}
common=[v for v in by.values() if len(v)==3]
out['paired']=paired;out['common108']={str(k):dict(Counter('correct' if v[k]['correct'] else v[k]['answer'] for v in common)) for k in (0,256,512)}
out['three_checkpoint_transitions']=dict(Counter('/'.join('correct' if v[k]['correct'] else v[k]['answer'] for k in (0,256,512)) for v in common))
nat=Counter(('correct' if v[0]['natural']['correct'] else 'wrong' if v[0]['natural']['valid'] else 'invalid') for v in by.values());out['natural']=dict(nat)
json.dump(out,open('/workspace/scratch/ea260d81d736/main_science_independent_results.json','w'),indent=2)
print(json.dumps(out,indent=2))
