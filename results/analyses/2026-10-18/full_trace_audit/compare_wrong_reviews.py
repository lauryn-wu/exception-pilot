import json,collections
from pathlib import Path
p=Path('/workspace/scratch/ea260d81d736/full_trace_audit')
raw=json.load(open(p/'wrong_traces.json'))
ind=json.load(open(p/'independent_wrong_review.json'))
primary={r['id']:dict(r,source_file=f.name) for f in sorted(p.glob('annotations_?.json')) for r in json.load(open(f))}
quotes={'recognized_record':'recognition_quote','false_missingness':'missingness_quote','miscopied_record':'miscopy_quote','explicit_override':'override_quote','recognition_kind':'recognition_quote'}
# Known-label recasting is separately coded and NEVER inferred from literal missingness.
direct={5,7,9,10,12,20,22,23,27}
# The seven cases with only correct heading membership plus simultaneous MISSING.
qualified_only={6,13,15,28,32,33,35}
changes={
(10,'explicit_override'):('uncertain','Deliberately masks B then predicts C, but does not explicitly say the pattern is more authoritative than the recorded B. Record disregard is explicit, conflict-resolution priority is not. Keep uncertain under strict record-priority rubric.'),
(13,'recognized_record'):('uncertain','Only correct-class association is heading A plus same-line MISSING. Treat uniformly with other simultaneous heading-plus-missing cases.'),
(15,'recognized_record'):('uncertain','Only correct-class association is heading B plus same-line MISSING. Treat uniformly with other simultaneous heading-plus-missing cases.'),
(22,'explicit_override'):('uncertain','Correct C is a value to confirm, followed by inferred A, but no explicit record-pattern priority statement. Exclude from definite explicit-override count.'),
(23,'explicit_override'):('uncertain','Knows B and simulates prediction, then C. This directly supports recasting; explicit priority over B remains ambiguous. Exclude from definite explicit-override count.'),
(24,'recognition_kind'):('both','Correct target table row and separate unique-description-to-A mapping both occur. If prose recognition requires the plate to recur, table_copy is acceptable; this affects only subtype, not recognized-record presence.'),
(25,'recognition_kind'):('both','Correct table B and unique-description membership under B both occur. Same subtype convention as 038v0; presence is unaffected.'),
(26,'recognition_kind'):('prose','Grouped table lacks a Verified-class cell; group heading is class-membership evidence akin to a prose group list. Later explicit Class-B-outlier prose is definite recognition. Full record copying is not needed to establish recognition.'),
(28,'recognized_record'):('uncertain','Only correct-class association is heading B plus same-line MISSING. Treat uniformly with other simultaneous heading-plus-missing cases.')
}
diffs=[]
for i,r in enumerate(ind):
 o=primary[r['id']]
 for key in quotes:
  if r[key]!=o[key]:
   rec,reason=changes.get((i,key), ('uncertain','Correct class group membership is simultaneously qualified as MISSING; use uncertain consistently.'))
   diffs.append({'id':r['id'],'field':key,'independent_original':r[key],'primary':o[key],'primary_file':o['source_file'],'independent_exact_quotes':r['evidence'].get(key,r['evidence'].get('recognized_record',[])),'primary_exact_quote':o[quotes[key]],'recommended_conservative':rec,'reason':reason})
# Agreements can still hide inconsistent application across batches. Flag them separately.
consistency=[]
for i in sorted(qualified_only):
 r=ind[i];o=primary[r['id']]
 consistency.append({'id':r['id'],'field':'recognized_record','independent_original':r['recognized_record'],'primary':o['recognized_record'],'recommended_conservative':'uncertain','exact_quotes':r['evidence']['recognized_record'],'reason':'Only target-class evidence is correct group membership while target is explicitly marked MISSING. Preserve broad correct-label association separately; do not treat as definite unqualified recognition.'})
# Revise independent review to use the conservative convention, preserving original label.
for i,r in enumerate(ind):
 r['original_independent_recognized_record']=r['recognized_record']
 r['correct_label_association_any']=r['recognized_record']=='present'
 if i in qualified_only:
  r['recognized_record']='uncertain'
  r['notes']+=' Conservative adjudication: group membership plus simultaneous MISSING is uncertain recognition; correct-label association remains true.'
 r['directly_recaste_known_label']='present' if i in direct else 'absent'
 if i in direct:
  r['evidence']['directly_recaste_known_label']=r['evidence']['task_reinterpretation'].copy()
  r['directly_recast_initial_label_correct']=i!=12
 r['answer_equals_designated_pattern']=r['answer']==r['pattern']
 if i==26:r['recognition_kind']='prose'
 if i==2:r['notes']+=' This is one of the three non-pattern errors: expected A, designated pattern B, final C.'
 if i==34:r['notes']+=' This IS a pattern-class error (final B equals designated pattern B), despite the mixed miscopy/missingness route.'
# Exact quote check for primary and independent evidence.
raw_by_id={z['id']:z for z in raw}
for d in diffs:
 text=raw_by_id[d['id']]['text']
 assert not d['primary_exact_quote'] or d['primary_exact_quote'] in text,d
 for q in d['independent_exact_quotes']:assert q in text,d
for r in ind:
 for qs in r['evidence'].values():
  for q in qs:assert q in raw_by_id[r['id']]['text']
summary={k:dict(collections.Counter(r[k] for r in ind)) for k in ['recognized_record','false_missingness','miscopied_record','explicit_override','directly_recaste_known_label']}
report={'scope':'36 wrong original-question visible-reasoning traces; independent full reading compared with annotations_0..3','summary_after_conservative_independent_adjudication':summary,'direct_known_label_recasting_ids':[r['id'] for r in ind if r['directly_recaste_known_label']=='present'],'direct_recast_caveat':'Nine explicitly recast an already supplied label. Eight initially acknowledge the correct label; 023v1 initially misstates supplied B as A but later has correct B groupings. Literal missingness alone does not qualify.','nonpattern_error_ids':[r['id'] for r in ind if not r['answer_equals_designated_pattern']],'actual_disagreements':diffs,'cross_batch_consistency_flags':consistency,'recognition_bounds':'20 definite, 7 uncertain qualified group associations, 9 absent. Broad any correct association =27/36. Do not conflate this with 27 explicit acknowledgments of the authoritative supplied value.','override_bounds':'3 definite, 6 uncertain,27 absent under independent strict coding. Unknown/uncertain cases should not count as definite override.'}
(p/'independent_wrong_review.json').write_text(json.dumps(ind,ensure_ascii=False,indent=2))
(p/'wrong_review_disagreements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(summary,indent=2));print('Actual disagreements:',len(diffs));print('Non-pattern:',report['nonpattern_error_ids'])
