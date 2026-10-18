import json, pathlib, re, collections, math, hashlib, statistics
import numpy as np

BASE=pathlib.Path('/workspace/scratch/ea260d81d736/full_trace_audit')
ROOT=BASE/'input'
OD=ROOT/'study2-v5-replication-v1/originals'
originals=[json.loads(p.read_text()) for p in (OD/'originals-v5').glob('*.json')]
originals.sort(key=lambda o:o['task']['id'])
by_hash={o['artifact_hash']:o for o in originals}
by_id={o['task']['id']:o for o in originals}
plan=json.loads((OD/'plan-v5.json').read_text())
analysis=json.loads((ROOT/'replication-analysis.json').read_text())
measurements=json.loads((ROOT/'study2-v5-replication-v1/readouts-remaining-v1/measurements-v5.json').read_text())

def mean(xs): return statistics.mean(xs) if xs else None
def world_summary(values, complete=False):
    d=collections.defaultdict(list)
    for ident,v in values: d[ident.split('/')[0]].append(v)
    ds={k:mean(v) for k,v in d.items() if not complete or len(v)==2}
    xs=list(ds.values())
    result={'mean':mean(xs),'worlds':len(xs),'observations':sum(len(d[k]) for k in ds),'available_observations':len(values),'world_values':ds}
    if xs:
        samples=np.random.default_rng(20261016).choice(xs,(10000,len(xs)),replace=True).mean(axis=1)
        result['bootstrap_95ci']=np.quantile(samples,[.025,.975]).tolist()
    return result
def cohort(o):return 'pilot_4' if int(o['task']['world'][-3:])<4 else 'remaining_56'
def semantic_answer(o):
    # Only widen the explicit terminal ANSWER-line grammar, never infer an answer from intermediate prose.
    s=o['raw']['text'].strip().splitlines()[-1] if o['raw']['text'].strip() else ''
    s=re.sub(r'^[#\s]+','',s).replace('**','').replace('`','').strip()
    m=re.fullmatch(r'ANSWER:\s*([ABC])\s*[.]?',s,re.I)
    return m[1].upper() if m else None

result={'method':'Independent recomputation from saved raw generations, prompt tables, token contexts, and token logprobs. No model inference or tokenizer replay. Frozen scores preserved; widened terminal parser only a reported sensitivity. Bootstrap is newly seeded and thus CI endpoints need not match original file exactly.'}
errors=[]
behavior={}
invalid=[]
table_checks=[]
for o in originals:
    t=o['task']; rows=[l for l in t['prompt'].splitlines() if l.startswith('| '+t['target_plate']+' |')]
    if len(rows)!=1 or rows[0]!=t['target_row'] or rows[0].strip('| ').split('|')[-1].strip()!=t['expected']:
        table_checks.append(t['id'])
    if semantic_answer(o)!=o['score']['answer']:
        invalid.append({'id':t['id'],'expected':t['expected'],'frozen_score':o['score'],'terminal_line':o['raw']['text'].strip().splitlines()[-1],'semantic_explicit_answer':semantic_answer(o)})
for co in ['pilot_4','remaining_56']:
  behavior[co]={}
  for fr in ['original','lookup']:
    for arm in ['direct','visible']:
      os=[o for o in originals if cohort(o)==co and o['task']['framing']==fr and o['task']['arm']==arm]
      answers=[semantic_answer(o) for o in os]
      behavior[co][fr+'/'+arm]={'n':len(os),'frozen_valid':sum(o['score']['valid'] for o in os),'frozen_correct':sum(o['score']['correct'] is True for o in os),'semantic_known':sum(a is not None for a in answers),'semantic_correct':sum(a==o['task']['expected'] for a,o in zip(answers,os)),'pattern_wrong':sum(a==o['task']['pattern'] for a,o in zip(answers,os)),'truncated':sum(o['score']['truncated'] for o in os),'output_tokens_median':statistics.median(len(o['raw']['tokens']) for o in os),'output_tokens_min':min(len(o['raw']['tokens']) for o in os),'output_tokens_max':max(len(o['raw']['tokens']) for o in os)}
result['behavior']=behavior
result['parser_disagreements']=invalid
result['prompt_ground_truth_mismatches']=table_checks
result['original_count']=len(originals)
result['world_target_positions_1indexed']=dict(collections.Counter(o['task']['target_row_position']+1 for o in originals))

pair_errors=[]
for w in plan['worlds']:
  for fr in ['original','lookup']:
    for arm in ['direct','visible']:
      a=by_id[w['id']+'/v0/'+fr+'/'+arm]['task']; b=by_id[w['id']+'/v1/'+fr+'/'+arm]['task']
      ra,rb=a['table'].splitlines(),b['table'].splitlines()
      dif=[i for i,(x,y) in enumerate(zip(ra,rb)) if x!=y]
      if len(dif)!=1 or a['target_plate'] not in ra[dif[0]] or a['target_row_values'][:-1]!=b['target_row_values'][:-1] or a['expected']==b['expected'] or a['pattern']!=b['pattern'] or a['expected']==a['pattern'] or b['expected']==b['pattern']:
          pair_errors.append([w['id'],fr,arm])
result['matched_variant_pair_errors']=pair_errors
stable_hash=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
result['saved_hash_checks']={
  'original_artifact_mismatches':sum(stable_hash({k:v for k,v in o.items() if k!='artifact_hash'})!=o['artifact_hash'] for o in originals),
  'input_token_hash_mismatches':sum(stable_hash(o['input_ids'])!=o['input_hash'] for o in originals),
  'output_token_hash_mismatches':sum(stable_hash(o['raw']['tokens'])!=o['output_hash'] for o in originals),
}
result['nonpattern_errors']=[{'id':o['task']['id'],'expected':o['task']['expected'],'pattern':o['task']['pattern'],'answer':o['score']['answer']} for o in originals if o['score']['correct'] is False and o['score']['answer']!=o['task']['pattern']]

ms=[];mp=collections.defaultdict(list);context_issues=[];score_issues=[]
for key,m in measurements['results'].items():
    o=by_hash.get(m['source_row_hash']);v=m['value']
    if o is None:context_issues.append([key,'unknown_source']);continue
    t=o['task'];cue=v['cue_text'];cueids=v['cue_ids'];ids=v['context_ids'];k=len(ids)-len(o['input_ids'])-len(cueids)
    want=o['input_ids']+o['raw']['tokens'][:k]+cueids
    if ids!=want or k<0:context_issues.append([key,'prefix_token_mismatch'])
    if m['world']!=t['world']:context_issues.append([key,'world_mismatch'])
    bd={b['k']:b for b in o['boundaries']}
    if k not in bd:context_issues.append([key,'no_saved_boundary'])
    else:
      if not bd[k]['roundtrip_exact']:context_issues.append([key,'boundary_not_roundtrip_exact'])
      if stable_hash(o['raw']['tokens'][:k])!=bd[k]['token_hash']:context_issues.append([key,'boundary_token_hash_mismatch'])
      if stable_hash(o['raw']['text'][:bd[k]['char_end']])!=bd[k]['text_hash']:context_issues.append([key,'boundary_text_hash_mismatch'])
    sc=v['scores'];lp={x:s['logprob'] for x,s in sc.items()};first={x:s['token_logprobs'][0] for x,s in sc.items()};end={x:s['token_logprobs'][1] for x,s in sc.items()}
    for x,s in sc.items():
      if len(s['tokens'])!=2 or s['tokens'][-1]!=198 or abs(sum(s['token_logprobs'])-s['logprob'])>1e-8:score_issues.append([key,x,'token_score_mismatch'])
    odds=lp[t['expected']]-lp[t['pattern']]
    pred=max(lp,key=lp.get);firstpred=max(first,key=first.get)
    if abs(odds-v['gold_pattern_log_odds'])>1e-8 or pred!=v['preferred_class']:score_issues.append([key,'stored_result_mismatch'])
    norm={x:math.exp(y-max(lp.values())) for x,y in lp.items()};z=sum(norm.values());norm={x:y/z for x,y in norm.items()}
    if max(abs(norm[x]-v['normalized'][x]) for x in norm)>1e-8:score_issues.append([key,'normalization_mismatch'])
    first_mass=sum(math.exp(x) for x in first.values());mass=math.exp(v['candidate_log_mass'])
    char=bd.get(k,{}).get('char_end');txt=o['raw']['text'];suffix=txt[char:] if char is not None else None
    at_answer=suffix is not None and re.fullmatch(r'(?:\*\*)?ANSWER:\s*[ABC](?:\*\*)?\s*',suffix) is not None
    fixed=k in [0,128,256,512,1024] and not at_answer
    # Two lookup pre-answer cuts fall exactly at k=128. Use the textual suffix to disambiguate.
    typ='fixed/'+str(k) if fixed else 'pre_answer'
    r={'measurement_id':key,'id':t['id'],'world':t['world'],'framing':t['framing'],'cue':cue,'k':k,'char_end':char,'type':typ,'expected':t['expected'],'pattern':t['pattern'],'natural_answer':o['score']['answer'],'natural_correct':o['score']['correct'],'preferred':pred,'first_token_preferred':firstpred,'odds':odds,'first_token_odds':first[t['expected']]-first[t['pattern']],'newline_odds':end[t['expected']]-end[t['pattern']],'candidate_sequence_mass':mass,'class_token_mass':first_mass,'prefix_tail':txt[max(0,char-100):char] if char is not None else None,'suffix_head':suffix[:60] if suffix is not None else None}
    ms.append(r);mp[(t['id'],cue)].append(r)
result['readout_validation']={'n':len(ms),'source_originals':len({r['id'] for r in ms}),'context_issues':context_issues,'score_issues':score_issues,'types':dict(collections.Counter(r['type'] for r in ms)),'pre_answer_suffix_counts':dict(collections.Counter(r['suffix_head'] for r in ms if r['type']=='pre_answer'))}
result['candidate_format_sensitivity']={'all_readouts':{'winner_changes':sum(r['preferred']!=r['first_token_preferred'] for r in ms),'median_candidate_sequence_mass':statistics.median(r['candidate_sequence_mass'] for r in ms),'median_class_token_mass':statistics.median(r['class_token_mass'] for r in ms)},'by_framing_cue_checkpoint':{}}
for fr in ['original','lookup']:
  for cue in ['\nANSWER:','\nFinal answer:']:
    for typ in sorted({r['type'] for r in ms}):
      rs=[r for r in ms if r['framing']==fr and r['cue']==cue and r['type']==typ]
      if not rs:continue
      result['candidate_format_sensitivity']['by_framing_cue_checkpoint'][fr+'/'+cue.strip()+'/'+typ]={'n':len(rs),'winner_changes':sum(r['preferred']!=r['first_token_preferred'] for r in rs),'candidate_mass_median':statistics.median(r['candidate_sequence_mass'] for r in rs),'class_token_mass_median':statistics.median(r['class_token_mass'] for r in rs),'natural_final_agreement_sequence':sum(r['preferred']==r['natural_answer'] for r in rs),'natural_final_agreement_class_only':sum(r['first_token_preferred']==r['natural_answer'] for r in rs),'valid_natural_answers':sum(r['natural_answer'] is not None for r in rs)}

trajectories=[];endpoint={};reversals={}
for (ident,cue),rs in mp.items():
    rs.sort(key=lambda r:r['k']); d={r['type']:r for r in rs};o=by_id[ident]; gold=o['task']['expected'];pat=o['task']['pattern'];start=d.get('fixed/0');last=d.get('pre_answer')
    q={'id':ident,'framing':o['task']['framing'],'cue':cue,'natural_answer':o['score']['answer'],'natural_correct':o['score']['correct'],'has_pre_answer':last is not None,'first':start,'last':last,'checkpoints':rs}
    for key,pkey,okey in [('sequence','preferred','odds'),('class_only','first_token_preferred','first_token_odds')]:
        preds=[r[pkey] for r in rs];seen_gold=False;rev=False;rec=False
        for pred in preds:
            if pred==pat and seen_gold:rev=True
            if pred==gold and rev:rec=True
            if pred==gold:seen_gold=True
        q[key]={'any_gold_to_pattern':rev,'subsequent_recovery':rec,'start_gold':start[pkey]==gold,'pre_answer_gold':last[pkey]==gold if last else None,'pre_answer_pattern':last[pkey]==pat if last else None,'delta':last[okey]-start[okey] if last else None}
    trajectories.append(q)
for fr in ['original','lookup']:
  for cue in ['\nANSWER:','\nFinal answer:']:
    for metric in ['sequence','class_only']:
      qs=[q for q in trajectories if q['framing']==fr and q['cue']==cue];key=fr+'/'+cue.strip()+'/'+metric
      vals=[(q['id'],q[metric]['delta']) for q in qs if q['has_pre_answer']]
      endpoint[key]={'complete_worlds':world_summary(vals,True),'available_worlds':world_summary(vals),'strata':{}}
      for outcome in ['correct','wrong','unknown']:
          ss=[(q['id'],q[metric]['delta']) for q in qs if q['has_pre_answer'] and ('unknown' if q['natural_correct'] is None else 'correct' if q['natural_correct'] else 'wrong')==outcome]
          endpoint[key]['strata'][outcome]=world_summary(ss)
      reversals[key]={'n':len(qs),'any_gold_to_pattern':sum(q[metric]['any_gold_to_pattern'] for q in qs),'subsequent_recovery':sum(q[metric]['subsequent_recovery'] for q in qs),'start_gold':sum(q[metric]['start_gold'] for q in qs),'pre_answer_n':sum(q['has_pre_answer'] for q in qs),'start_gold_pre_answer_pattern':sum(q[metric]['start_gold'] and q[metric]['pre_answer_pattern'] is True for q in qs),'pre_answer_gold':sum(q[metric]['pre_answer_gold'] is True for q in qs)}
result['endpoint_changes']=endpoint;result['reversals']=reversals
result['readout_rows']=ms
result['trajectory_summaries']=[{k:v for k,v in q.items() if k not in ['first','last','checkpoints']} for q in trajectories]

(BASE/'quantitative_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['readout_rows','trajectory_summaries','endpoint_changes','candidate_format_sensitivity']},indent=2))
print('ENDPOINTS',json.dumps({k:{'complete_world_mean':v['complete_worlds']['mean'],'complete_world_ci':v['complete_worlds'].get('bootstrap_95ci'),'available_world_mean':v['available_worlds']['mean'],'strata_means':{s:x['mean'] for s,x in v['strata'].items()}} for k,v in endpoint.items()},indent=2))
print('FORMAT',json.dumps(result['candidate_format_sensitivity'],indent=2))
