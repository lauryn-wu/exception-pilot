"""Strict whole answer, terminal EOS, and independent raw-integrity checks."""
from . import PARSER, BUDGET
LABELS=('A','B','C','MISSING')


def parse_reply(raw,expected,tok):
    result=dict(parser_version=PARSER,raw_integrity=False,complete=False,format_valid=False,
        valid=False,answer=None,correct=False,eos_observed=False,generation_length_stop=False,
        token_count=None,finish=None,metadata_errors=[],category='malformed')
    if not isinstance(raw,dict):return dict(result,metadata_errors=['non_object_payload'])
    ids=raw.get('tokens');text=raw.get('text');errors=[]
    result['finish']=raw.get('finish')
    if not isinstance(text,str):errors.append('invalid_text')
    label=text.strip() if isinstance(text,str) else None
    result['format_valid']=label in LABELS
    good_ids=isinstance(ids,list) and all(type(i) is int and i>=0 for i in ids)
    if not good_ids:errors.append('invalid_token_array')
    else:
        result['token_count']=len(ids);result['eos_observed']=bool(ids and ids[-1] in tok.eos_ids)
        if len(ids)>BUDGET:errors.append('budget_exceeded')
        if any(i in tok.special_ids for i in ids[:-1]) or ids and ids[-1] in tok.special_ids-tok.eos_ids:
            errors.append('unexpected_special_token')
        try:
            if not isinstance(text,str) or tok.decode(ids)!=text:errors.append('text_token_mismatch')
        except (ValueError,TypeError,OverflowError,IndexError,KeyError):errors.append('undecodable_token_array')
    eos=result['eos_observed'];result['generation_length_stop']=raw.get('finish')=='length' and not eos
    if raw.get('stopped') is not eos or raw.get('finish')!=('eos' if eos else 'length'):
        errors.append('finish_eos_mismatch')
    if good_ids and not eos and raw.get('finish')=='length' and len(ids)!=BUDGET:
        errors.append('length_stop_token_count_not_budget')
    for key in ('next_token_logits','next_logits'):
        if key in raw and raw[key] not in ({},[],None):errors.append('unexpected_logits_capture')
    result.update(metadata_errors=errors,raw_integrity=not errors,complete=not errors and eos)
    result['valid']=result['complete'] and result['format_valid']
    if result['valid']:
        result.update(answer=label,correct=label==expected,category='correct' if label==expected else 'wrong')
    elif not errors:result['category']='incomplete' if not eos else 'invalid_format'
    return result
