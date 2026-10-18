import json,collections
from pathlib import Path
base=Path('/workspace/scratch/ea260d81d736/full_trace_audit')
x=json.load(open(base/'wrong_traces.json'))
# Manually read all 36 full traces before assigning the following labels.
# P/A/U = present/absent/uncertain. Fields: recognized_record, recognition_kind,
# false_missingness, miscopied_record, explicit_override, task_reinterpretation.
spec=[
('A','none','P','A','A','P','Replaces supplied B with MISSING in copied table; no correct target-class mention.'),
('A','none','P','A','A','P','Replaces supplied B with MISSING in copied table; no correct target-class mention.'),
('P','prose','P','A','A','P','Target listed under A, then asserted MISSING. Final C uses audit-marker correlation, not assigned description-pattern B.'),
('P','prose','A','A','A','A','Target correctly listed under A. No explicit missingness, verification reinterpretation, or record-pattern conflict acknowledgment. Chooses C from description; comparing description versus audit marker is not comparing description versus record.'),
('P','prose','P','A','A','P','Falsely asserts missing first, then repeatedly lists target under correct B; therefore not solely recognition followed by erasure.'),
('P','both','A','A','U','P','Correct table and explicit A recognition; asks to verify via patterns. Chooses C but does not directly state record-pattern conflict or priority.'),
('P','prose','P','A','A','P','Correct B group includes target with (MISSING); later C groups also include target with (MISSING). Weak recognition via contradictory group membership, not confident label assertion. C placements may already be inference; not definite miscopy.'),
('P','prose','A','A','U','P','Explicit correct C recognition and verification reinterpretation, then chooses A without direct record-priority statement.'),
('P','prose','P','A','A','P','Falsely asserts missing before correctly grouping target under B. Multiple feature/count errors.'),
('P','prose','A','A','U','P','Explicitly knows A then predicts as if missing. Hypothetical missingness does not count as literal false absence. Uses incidental feature match to B.'),
('P','both','A','A','U','P','Correct B table and prose; explicitly assumes missing counterfactually. No literal false absence claim. Final C selects prediction without directly disputing recorded B.'),
('A','none','P','A','A','P','Copied target class becomes MISSING.'),
('P','prose','A','P','A','P','Initial prose falsely claims table A though actual B. Later correctly groups under B repeatedly. Final A equals misread recorded label, not description-pattern C. Also says Vinyl present though target is Cloth.'),
('P','prose','P','A','A','P','Target in correct A group simultaneously tagged MISSING. Infers B from other feature matches.'),
('P','prose','P','A','A','P','Correct C group with MISSING tag. Compares typical class features and favors A without explicit direct-record priority statement.'),
('P','prose','P','A','A','P','Correct B group with MISSING tag. Feature tallies and frequencies are errorful.'),
('P','prose','P','A','A','P','Correct C group then literal MISSING. Other feature associations drive A.'),
('A','none','P','A','A','P','Copied target class becomes MISSING.'),
('A','none','P','A','A','P','Target omitted from class groups and asserted MISSING; no literal correct C recognition.'),
('A','none','P','A','A','P','Copied target class becomes MISSING.'),
('P','prose','A','A','P','P','Explicit correct C recognition, deliberately treats as missing, then directly says hot description means target does not belong to C.'),
('A','none','P','A','A','P','Copied target class becomes MISSING; labels target unknown record.'),
('P','both','A','A','U','P','Correct C copied and explicitly to be confirmed. Patterns lead A without explicit record conflict or priority sentence.'),
('P','prose','A','A','U','P','Says already known B, simulates prediction, chooses C. No literal false missingness and no direct contradiction-resolution statement.'),
('P','both','U','A','A','U','Correct A in table and unique-description mapping. Only evidence of treating unlabeled is heading Apply the pattern to the unknown record; ambiguous whether unknown means class absent or generic question target.'),
('P','both','A','A','A','A','Correct B in table and description group; then C from similar descriptions. No explicit reinterpretation, missingness, or conflict acknowledgment.'),
('P','both','P','A','P','P','Correct target B group table, literal MISSING, then repeatedly says target is Class B outlier and nevertheless chooses A. Missingness and override co-occur; cannot fit clean mutually exclusive erasure/override classes.'),
('P','prose','A','A','P','P','Explicit B recognized repeatedly, task recast as verification, and directly weighs sole hot B record against more hot C records before C choice.'),
('P','prose','P','A','A','P','Falsely asserts MISSING; correct B grouping with MISSING annotation. Pattern synthesis contains multiple contradictory claims.'),
('A','none','P','A','A','P','Target class replaced by question mark throughout; conflict discussed is A/B features, not supplied C versus pattern.'),
('P','prose','P','A','A','P','Correct B group then MISSING. Duplication of another vehicle ID under C, feature-versus-feature conflict rather than explicit record conflict.'),
('P','prose','U','A','A','U','Target correctly grouped A but description corrupted from Built for subzero temperatures to Equipped for hot sand twice. Third-class C error follows corrupt description. Only missingness/interpretation signal is unknown record heading.'),
('P','prose','P','A','A','P','Correct C group simultaneously tagged MISSING. Final reasoning internally inconsistent about target features supporting A vs C.'),
('P','prose','P','A','A','P','Correct B group simultaneously tagged MISSING. Concludes Manual only C despite target Manual in B.'),
('A','none','P','P','A','P','Target incorrectly grouped in B (actual A), later MISSING. Claims two doors only B despite earlier explicit A two-door count. Wrong final B need not reflect overriding a recognized correct record.'),
('P','prose','P','A','A','P','Correct A group simultaneously marked MISSING; false missingness is asserted first, before group recognition.')
]
status={'P':'present','A':'absent','U':'uncertain'}
keys=['recognized_record','recognition_kind','false_missingness','miscopied_record','explicit_override','task_reinterpretation']
out=[]
for i,s in enumerate(spec):
 z=x[i];r={'id':z['id'],'expected':z['expected'],'pattern':z['pattern'],'answer':z['score']['answer']}
 r.update({k:(v if k=='recognition_kind' else status[v]) for k,v in zip(keys,s[:6])});r['evidence']={};r['notes']=s[6];out.append(r)
def q(i,k,t):
 assert t in x[i]['text'],(i,k,t)
 out[i]['evidence'].setdefault(k,[]).append(t)
def between(i,k,start,end):
 t=x[i]['text'];a=t.index(start);b=t.index(end,a)+len(end);q(i,k,t[a:b])
def line(i,k,needle):
 lines=x[i]['text'].splitlines();a=next(j for j,l in enumerate(lines) if needle in l);q(i,k,lines[a])
def group(i,k,header,needle):
 t=x[i]['text'];a=t.index(header);b=t.index(needle,a);e=t.find('\n',b);q(i,k,t[a:e if e!=-1 else len(t)])
# Evidence for literal missingness; all marked P by manual reading.
for i in [0,1,6,11,17,19,21]:line(i,'false_missingness',x[i]['target_plate']+' |')
for i in [2,13,14,15,16,18,26,30,32,34]:line(i,'false_missingness','**Verified class**: MISSING')
for i in [4,8,28]:between(i,'false_missingness','We are given that the','other records.')
line(33,'false_missingness','We are given that the')
line(35,'false_missingness','Since the **Verified class**')
line(29,'false_missingness','| V5TF7AU5')
# Pure false absence entails treating target as unlabelled; keep shared evidence transparent.
for i in range(36):
 if out[i]['task_reinterpretation']=='present' and 'false_missingness' in out[i]['evidence']:
  out[i]['evidence']['task_reinterpretation']=out[i]['evidence']['false_missingness'].copy()
# Correct-record recognition.
group(2,'recognized_record','#### Class A:','**V5TYDYNE**')
group(3,'recognized_record','#### Class A:','V5TRNRPT:')
group(4,'recognized_record','- **Class B**:','V5T29QTZ: Manual')
line(5,'recognized_record','| V5TCPVCB')
line(5,'recognized_record','which is already listed as')
group(6,'recognized_record','- **Manual**:','B: V5TCPVCB')
line(7,'recognized_record','which is already listed as')
group(8,'recognized_record','- **Class B**:','V5TE3K3B (Automatic)')
line(9,'recognized_record','which is already listed as')
line(10,'recognized_record','| V5TPLQNQ')
line(10,'recognized_record','**Verified class**: B')
group(12,'recognized_record','- **Class B**:','V5T5NTA7: Manual')
for i,header,needle in [(13,'#### Class A:','**V5T2NNRW**'),(14,'#### Class C:','**V5TMRJ59**'),(15,'#### Class B:','**V5TMRJ59**'),(16,'#### Class C:','**V5TP4TYU**')]:group(i,'recognized_record',header,needle)
line(20,'recognized_record','which is already listed in the table')
line(22,'recognized_record','| V5TG4FVG')
line(22,'recognized_record','**Verified class**: C')
line(23,'recognized_record','which is already known to be')
line(24,'recognized_record','| V5TH425T')
line(24,'recognized_record','**Equipped for hot sand** → A')
line(25,'recognized_record','| V5TH425T')
between(25,'recognized_record','- **Class B** is associated with:', '  - "Equipped for hot sand"')
group(26,'recognized_record','#### Class B:','| V5T7E3BU')
line(26,'recognized_record','only Class B vehicle with a hot environment description')
line(27,'recognized_record','which is already listed as')
group(28,'recognized_record','#### Class B:','**V5TF7AU5**')
group(30,'recognized_record','#### Class B:','**V5TC7BYD**')
group(31,'recognized_record','#### Class A:','**V5T2LVLF**')
group(32,'recognized_record','#### Class C:','V5TKP93F:')
group(33,'recognized_record','#### Class B:','V5TS6T5D:')
group(35,'recognized_record','#### **Class A**','**V5TLMNAC**')
# Explicit task reinterpretation, including counterfactual masking (not false absence).
for i,needle in [(5,'which is already listed as'),(7,'which is already listed as'),(9,'which is already listed as'),(12,'which is already listed as'),(20,'which is already listed in the table'),(23,'which is already known to be'),(27,'which is already listed as')]:line(i,'task_reinterpretation',needle)
line(10,'task_reinterpretation','Let’s assume the **Verified class**')
line(22,'task_reinterpretation','this is the value we are trying to confirm')
for i in [24,31]:line(i,'task_reinterpretation','unknown record');line(i,'false_missingness','unknown record')
# Misread recorded label.
line(12,'miscopied_record','which is already listed as')
group(34,'miscopied_record','#### Class B:','**V5TPUL64**')
# Strict explicit record-pattern override.
line(20,'explicit_override','This is a **strong indicator** that')
line(26,'explicit_override','only Class B vehicle with a hot environment description')
between(27,'explicit_override','### Step 4: Conclusion','### Final Answer:')
# Ambiguous override evidence: correct recognition + verification is not itself direct priority statement.
for i in [5,7,9,10,22,23]:
 out[i]['evidence']['explicit_override']=out[i]['evidence']['task_reinterpretation'].copy()
# Key corruption example distinct from incorrect class copying.
line(31,'description_corruption','- **Description**: Equipped for hot sand')
# Verify completeness of exact quotes and present labels.
for i,r in enumerate(out):
 for k in ['recognized_record','false_missingness','miscopied_record','explicit_override','task_reinterpretation']:
  assert r[k]!='present' or k in r['evidence'],(i,k)
 for qs in r['evidence'].values():
  assert all(t in x[i]['text'] for t in qs)
p=base/'independent_wrong_review.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
for k in keys: print(k,dict(collections.Counter(r[k] for r in out)))
print(p)
