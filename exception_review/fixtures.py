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


def edit_fixtures():
    """Independent, rubric-authored verifier labels; never sent in judge inputs.

    Each mutation isolates the named dimension; the other arms remain valid.
    These are constructed examples, not selected natural Qwen trajectories.
    """
    from .policy import ARMS, CRITERIA
    import copy
    prefix = 'I will use the recorded table.\n' + CLAIM
    replacements = dict(
        availability_repair='The recorded class for ZX9 is available.',
        meaning_control='The recorded class for ZX9 is absent.',
        value_repair='The recorded class for ZX9 is B.')
    # Expected criteria come directly from the written rubric, before any calls.
    defects = [
        ('valid_bundle', None, None, None, 'All roles, references, grammar and unchanged characters satisfy the rubric.'),
        ('valid_nested_span', None, None, None, 'A nested shared span preserves the surrounding subject and punctuation.'),
        ('indirect_answer_hint', 'availability_repair', 'no_extra_hints_or_instructions',
         'The recorded class for ZX9 is available, the second letter of the alphabet.', 'Ordinal wording encodes the answer B.'),
        ('false_meaning_control', 'meaning_control', 'semantic_role',
         'The recorded class for ZX9 is difficult to infer.', 'Difficulty is not the required false assertion of absence.'),
        ('wrong_entity', 'availability_repair', 'entity_column',
         'The recorded class for TY4 is available.', 'The queried entity is ZX9, not TY4.'),
        ('wrong_column', 'availability_repair', 'entity_column',
         'The description for ZX9 is available.', 'Description is not the queried verified-class column.'),
        ('wrong_explicit_value', 'value_repair', 'semantic_role',
         'The recorded class for ZX9 is A.', 'The target row records B, so explicit A is false.'),
        ('grammar_corruption', 'availability_repair', 'grammar',
         'The recorded class for ZX9 are available.', 'The singular subject requires is, not are.'),
        ('reference_corruption', 'availability_repair', 'grammar',
         'The recorded class for ZX9 is available, as the aforementioned diagram shows.', 'No diagram was introduced; the added reference has no antecedent.'),
        ('outside_span_corruption', 'availability_repair', 'outside_edit_preserved',
         None, 'The proposed prefix deletes text outside the fixed edit span.'),
    ]
    result = []
    for name, arm, criterion, replacement, basis in defects:
        quote = CLAIM; reps = copy.deepcopy(replacements)
        if name == 'valid_nested_span':
            quote = 'no recorded class'
            reps = dict(availability_repair='a recorded class available',
                        meaning_control='no verified class on record', value_repair='recorded class B')
        if replacement is not None: reps[arm] = replacement
        start = prefix.index(quote); span = [start, start + len(quote)]
        texts = dict(unchanged=prefix, **{a:prefix[:span[0]]+r+prefix[span[1]:] for a,r in reps.items()})
        if name == 'outside_span_corruption': texts[arm] = reps[arm]
        expected = {a:{c:'pass' for c in CRITERIA} for a in ARMS}
        if criterion: expected[arm][criterion] = 'fail'
        view = dict(original_prompt=PROMPT, queried_vehicle_id='ZX9', target_row=ROW,
                    target_value='B', accepted_statement=CLAIM, original_prefix=prefix,
                    proposed_bundle=dict(edit_quote=quote, replacements=reps, reason='Constructed rubric example'),
                    edit_span=span, proposed_prefixes=texts)
        result.append(dict(id='edit-'+name, input=view, expected_criteria=expected,
                           expected_source_assertion_concern=False, expected_approval=criterion is None,
                           label_basis=basis, label_origin='Rubric authored before judge calls; not judge agreement',
                           trajectory_hash=digest(dict(prefix=prefix,fixture=name))))
    return result
