"""Whole-response parsing; invalid or truncated returns are never retried."""
import re
from . import PARSER,BUDGET

LABELS=('A','B','C','MISSING')


def parse_reply(raw,expected,tok):
    result=dict(parser_version=PARSER,valid=False,answer=None,correct=False,diagnostic_label=None,
        category='malformed',eos_observed=False,truncated=False,token_count=None,metadata_errors=[])
    if not isinstance(raw,dict):return dict(result,metadata_errors=['non_object_payload'])
    text=raw.get('text');ids=raw.get('tokens');errors=[]
    stripped=text.strip() if isinstance(text,str) else None
    result['diagnostic_label']=stripped if stripped in LABELS else None
    good_ids=isinstance(ids,list) and all(type(t) is int and t>=0 for t in ids)
    if good_ids:
        result['token_count']=len(ids);result['eos_observed']=bool(ids and ids[-1] in tok.eos_ids)
        if len(ids)>BUDGET:errors.append('budget_exceeded')
        if any(i in tok.special_ids for i in ids[:-1]) or ids and ids[-1] in tok.special_ids-tok.eos_ids:errors.append('unexpected_special_token')
        try:
            if not isinstance(text,str) or tok.decode(ids)!=text:errors.append('text_token_mismatch')
        except (ValueError,TypeError,OverflowError):errors.append('undecodable_token_array')
    else:errors.append('invalid_token_array')
    eos=result['eos_observed'];result['truncated']=raw.get('finish')=='length' and not eos
    if raw.get('stopped') is not eos or raw.get('finish')!=('eos' if eos else 'length'):errors.append('finish_eos_mismatch')
    if raw.get('next_token_logits') or raw.get('next_logits'):errors.append('unexpected_logits_capture')
    result['metadata_errors']=errors
    if result['truncated']:
        return dict(result,category='truncated')
    if errors or not eos:return result
    if stripped in LABELS:return dict(result,valid=True,answer=stripped,correct=stripped==expected,category=stripped)
    if stripped=='':return dict(result,category='empty')
    if re.fullmatch(r'(?:A|B|C|MISSING)(?:[\s,/]+(?:A|B|C|MISSING))+',stripped or ''):
        return dict(result,category='ambiguous')
    return dict(result,category='verbose')
