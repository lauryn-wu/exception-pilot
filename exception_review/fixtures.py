"""Rubric-authored examples, not labels inferred from agreement among judges."""
from exception_pilot.core import digest

CLAIM='Vehicle ZX9 has no recorded class.'
PROMPT='| License plate | Description | Verified class |\n| ZX9 | compact | B |\n| TY4 | long | A |\nWhat is the verified class for ZX9?'
ROW='| ZX9 | compact | B |'
CASES=[
    ('affirmative',CLAIM,'present',CLAIM),
    ('negated','It is not true that vehicle ZX9 has no recorded class.','absent',None),
    ('hypothetical','If vehicle ZX9 had no recorded class, I would need more data.','absent',None),
    ('question','Does vehicle ZX9 have no recorded class?','absent',None),
    ('uncertain_nonassertion','I am unsure whether ZX9 has a recorded class.','absent',None),
    ('infer_descriptions','I cannot infer the class for ZX9 from its description.','absent',None),
    ('wrong_vehicle','Vehicle TY4 has no recorded class.','absent',None),
    ('wrong_column','Vehicle ZX9 has no recorded transmission.','absent',None),
    ('unendorsed_quote','Someone said "Vehicle ZX9 has no recorded class." I do not endorse that claim.','absent',None),
    ('endorsed_quote','I agree: '+CLAIM,'present',CLAIM),
    ('multiple_first',CLAIM+' Further on: ZX9 lacks a verified class.','present',CLAIM),
    ('later_correction',CLAIM+' Actually, its recorded class is B.','present',CLAIM),
    ('truncated_original_complete_claim',CLAIM+' The next step wou','present',CLAIM),
    ('paraphrase','The verified-class entry for ZX9 is unavailable.','present','The verified-class entry for ZX9 is unavailable.'),
    ('marker_boundary','Reasoning. ANSWER: B\n'+CLAIM,'absent',None),
    ('unicode','Évidence 🚙: '+CLAIM,'present',CLAIM),
]

def fixtures():
    result=[]
    for name,text,decision,claim in CASES:
        marker=text.find('ANSWER:'); view=text[:marker] if marker>=0 else text
        span=None if claim is None else [view.index(claim),view.index(claim)+len(claim)]
        result.append(dict(id=name,raw_text=text,input=dict(original_prompt=PROMPT,queried_vehicle_id='ZX9',target_row=ROW,detection_view=view),expected_decision=decision,expected_span=span,expected_claim=claim,label_basis='Fixed rubric-authored expected label; no live-judge consensus',trajectory_hash=digest({'fixture':name,'raw_text':text})))
    return result

EDIT_FIXTURES=[
    dict(id='hidden_ordinal_hint',availability_repair='ZX9 has a recorded class, the second letter of the alphabet.',expected='fail',criterion='no_extra_hints_or_instructions'),
    dict(id='false_control_uncertainty',meaning_control='The recorded class for ZX9 is difficult to infer.',expected='fail',criterion='semantic_role'),
    dict(id='wrong_entity_repair',availability_repair='The recorded class for TY4 is available.',expected='fail',criterion='entity_column'),
    dict(id='valid_availability',availability_repair='The recorded class for ZX9 is available.',expected='pass',criterion='semantic_role'),
]
