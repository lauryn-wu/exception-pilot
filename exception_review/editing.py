"""Automated edit mechanics, with no invented manual certifications."""
import re
from exception_continuation.core import letters
from .policy import ARMS,CRITERIA,DRAFT_SCHEMA,VERIFY_SCHEMA,schema_check
from .decisions import positions


def edit_view(row,statement):
    cut=statement['boundaries']['after_statement']; span=statement['span']
    return dict(original_prompt=row['task']['prompt'],queried_vehicle_id=row['task']['target_plate'],target_row=row['task']['target_row'],target_value=row['task']['expected'],accepted_statement=row['raw']['text'][span[0]:span[1]],original_prefix=row['raw']['text'][:cut['char_end']])


def align_edit(statement,payload):
    schema_check(payload,DRAFT_SCHEMA)
    hits=positions(statement['statement'],payload['edit_quote'])
    if len(hits)!=1: raise ValueError('edit_quote_not_unique_within_statement')
    start=statement['span'][0]+hits[0]
    return [start,start+len(payload['edit_quote'])]


def mechanical(prefix,span,quote,replacements,gold):
    errors=[]; start,end=span
    if not (0<=start<end<=len(prefix)) or prefix[start:end]!=quote: raise ValueError('Exact edit span mismatch')
    first_end=prefix.find('\n')
    if re.match(r'^(?:COPIED|INITIAL|INITIAL_ANSWER|FIRST_VALUE):',prefix) and start<=(first_end if first_end>=0 else len(prefix)): errors.append('preliminary_entry_protected')
    if set(replacements)!=set(ARMS): raise ValueError('Exactly three arms required')
    if any(not isinstance(v,str) or not v or v==quote for v in replacements.values()): errors.append('replacement_empty_or_unchanged')
    if any(letters(replacements['availability_repair']).values()): errors.append('availability_contains_class_letter')
    if letters(replacements['meaning_control'])!=letters(quote): errors.append('meaning_changes_class_counts')
    if not letters(replacements['value_repair'])[gold]: errors.append('value_missing_correct_class')
    texts={'unchanged':prefix,**{a:prefix[:start]+r+prefix[end:] for a,r in replacements.items()}}
    if any(letters(texts['availability_repair'])[c]>letters(prefix)[c] for c in 'ABC'): errors.append('availability_whole_prefix_class_boundary')
    return dict(passed=not errors,reasons=errors,texts=texts)


def verify_bundle(value):
    schema_check(value,VERIFY_SCHEMA)
    failures=[]
    if value['source_assertion_concern'] is not None: failures.append('source_assertion_concern: '+value['source_assertion_concern'])
    for arm in ARMS:
        for criterion in CRITERIA:
            rating=value['replacements'][arm][criterion]
            if rating['status']!='pass': failures.append(arm+'/'+criterion+': '+rating['status']+': '+rating['reason'])
    return dict(passed=not failures,reasons=failures)
