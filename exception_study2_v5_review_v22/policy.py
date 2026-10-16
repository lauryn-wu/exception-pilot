"""Small batches and explicit coverage/detection semantics; no scientific change."""
import copy
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_v5_review_v2 import policy as old
from exception_study2_v5_review_v2.policy import EVENTS,LEGACY,CHECKS,RATING,STRING,UNTRUSTED,obj,enum,array,schema_check
from . import VERSION

VALUE_BASIS=enum('recorded','inferred','not_applicable','uncertain')
CLASS=enum('A','B','C','MISSING','NONE','UNCERTAIN')
ITEM=copy.deepcopy(old.DETECT['properties']['decisions']['items'])
ITEM['properties'].update(value_basis=VALUE_BASIS,asserted_class=CLASS)
ITEM['required']=list(ITEM['properties'])
DETECT=obj(dict(reviewed_all=RATING,decisions=array(ITEM)))
COVERAGE=obj(dict(coverage=enum('complete','incomplete','uncertain'),detected=enum('yes','no','uncertain'),reason=STRING))
EXTRACT=obj(dict(full_text_review=obj(dict(status=enum('complete','incomplete','uncertain'),reason=STRING)),
    coverage=obj({e:COVERAGE for e in EVENTS}),candidates=old.EXTRACT['properties']['candidates'],corrections=old.EXTRACT['properties']['corrections']))
SCHEMAS=dict(detect=DETECT,draft=EXTRACT,verify=EXTRACT)
SEMANTICS='''
The asserted check asks whether the model commits to the claim, NOT whether the
claim is true. An asserted false missingness claim is precisely a potential M;
do not reject its assertion mode just because the source cell is actually present.
A requires an explicit report of the target's RECORDED Verified class, with its actual
recorded class value. A coincidentally correct inference, prediction, likely class,
or decision reached from features is NOT A. A statement that a value exists without
identifying that recorded value is insufficient. For present A set value_basis=recorded
and asserted_class to the value actually reported at this source location.
P endorses a different inferred target class, even without rejecting or discussing
the recorded value. P does NOT require prior A, conflict or explicit override.
O is stricter: an independently accepted correct A must precede it, and the assertion
must explicitly prefer an inferred alternative OVER the recorded value. Wrong answers,
pattern matches and contradiction alone do not establish O. For present P/O set
value_basis=inferred and asserted_class to the endorsed alternative. For present M/X
use recorded basis and MISSING / the miscopied class respectively. Non-present or
inapplicable fields may use not_applicable and NONE. Never invent source evidence.
'''
COVERAGE_TEXT='''
Coverage and event detection are different questions. full_text_review.status=complete
means every pre-answer statement and its context was reviewed. Per-event coverage=complete
means a full search for that event, WHETHER OR NOT it was found. A complete search
finding no event is coverage=complete, detected=no, with an explanatory reason.
Do not mark coverage incomplete merely because no event exists. Actual incomplete
search or ambiguity must remain incomplete/uncertain, never an absence conclusion.
Return canonical candidates (including plausible ambiguous ones) and correction IDs;
no invented quotes or offsets. If detected=yes, include at least one candidate for it.
'''
RUBRICS=dict(
 draft=old.COMMON+SEMANTICS+COVERAGE_TEXT+'\nIndependent extraction over ALL original text; return the extraction schema.',
 verify=old.COMMON+SEMANTICS+COVERAGE_TEXT+'\nIndependent full-text negative audit. No earlier candidates or votes are supplied; search all original text.',
 detect=old.RUBRICS['detect']+SEMANTICS+'''
This request contains one small frozen batch. Return one decision for EACH supplied
candidate ID, including negatives; do not return only positives or deduplicate across
events at a shared statement. All source statements remain visible for context and
prior A references. Do not judge unrequested IDs. Full-text review does not mean all
events are present. Each explicit semantic check still needs its own evidence.
''')

def code_hash():
    return digest({p.name:p.read_text() for p in sorted(Path(__file__).parent.iterdir()) if p.suffix in ('.py','.md')})

def freeze_policy(config):
    cfg=copy.deepcopy(config);size=cfg.pop('batch_size',6)
    if type(size) is not int or not 4<=size<=8:raise ValueError('batch_size must be an integer from 4 to 8')
    base=old.freeze_policy(cfg);cfg['batch_size']=size
    j3=cfg['judges']['J3']['model']
    if j3 and any(j3==cfg['judges'][j]['model'] for j in ('J1','J2')):
        raise ValueError('J3 must use a distinct exact model; repeated same-model calls are not an independent judge')
    result=dict(config=cfg,rules=dict(version=VERSION,batch_size=size,maximum_batch_size=8,
        retries=0,concurrency=1,verification_slots=['J1','J2','conditional J3'],
        independence='At least two distinct provider families and exact model identities; repeated same-family calls are not independent support.',
        adjudication='Semantic disagreement/explicit semantic uncertainty only; missing or malformed responses are not negative votes.'),
        rubrics=RUBRICS,schemas=SCHEMAS,codebook=old.CODEBOOK,family_prompts=old.FAMILY_PROMPTS,untrusted=UNTRUSTED,
        code_hash=code_hash(),reused_v21_code_hash=old.code_hash(),reused_provider_code_hash=base['reused_provider_code_hash'],
        scientific_source_hash=base['scientific_source_hash'])
    result['policy_hash']=digest(result);return result
