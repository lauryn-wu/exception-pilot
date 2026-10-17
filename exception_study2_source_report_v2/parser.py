"""Parse only the first ASCII-quote-closed field; validate the entire raw payload."""
from . import PARSER,BUDGET

LABELS=('A','B','C','MISSING')


def parse_reply(raw,expected,tok):
    result=dict(parser_version=PARSER,field_complete=False,field_valid=False,valid=False,
        field_text=None,field_value=None,closing_quote_offset=None,trailing_text=None,
        answer=None,correct=False,diagnostic_label=None,category='malformed',
        eos_observed=False,generation_length_stop=False,token_count=None,metadata_errors=[])
    if not isinstance(raw,dict):return dict(result,metadata_errors=['non_object_payload'])
    text=raw.get('text');ids=raw.get('tokens');errors=[]
    if isinstance(text,str):
        closing=text.find('"');complete=closing>=0
        field=text[:closing] if complete else text
        result.update(field_complete=complete,closing_quote_offset=closing if complete else None,
            field_text=field,field_value=field.strip(),trailing_text=text[closing+1:] if complete else None,
            diagnostic_label=field.strip() if field.strip() in LABELS else None)
    else:errors.append('invalid_text')
    good_ids=isinstance(ids,list) and all(type(t) is int and t>=0 for t in ids)
    if good_ids:
        result['token_count']=len(ids);result['eos_observed']=bool(ids and ids[-1] in tok.eos_ids)
        if len(ids)>BUDGET:errors.append('budget_exceeded')
        if any(i in tok.special_ids for i in ids[:-1]) or ids and ids[-1] in tok.special_ids-tok.eos_ids:
            errors.append('unexpected_special_token')
        try:
            if not isinstance(text,str) or tok.decode(ids)!=text:errors.append('text_token_mismatch')
        except (ValueError,TypeError,OverflowError):errors.append('undecodable_token_array')
    else:errors.append('invalid_token_array')
    eos=result['eos_observed'];result['generation_length_stop']=raw.get('finish')=='length' and not eos
    if raw.get('stopped') is not eos or raw.get('finish')!=('eos' if eos else 'length'):
        errors.append('finish_eos_mismatch')
    if good_ids and not eos and raw.get('finish')=='length' and len(ids)!=BUDGET:
        errors.append('length_stop_token_count_not_budget')
    if raw.get('next_token_logits') or raw.get('next_logits'):errors.append('unexpected_logits_capture')
    result['metadata_errors']=errors
    if errors:return result
    if not result['field_complete']:return dict(result,category='incomplete_field')
    label=result['field_value']
    if label in LABELS:return dict(result,field_valid=True,valid=True,answer=label,correct=label==expected,category=label)
    return dict(result,category='empty_field' if label=='' else 'invalid_field')
