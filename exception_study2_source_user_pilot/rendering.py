"""Append verified template role tokens without reserializing historical IDs."""
from exception_pilot.core import digest
from . import MESSAGE
SENTINEL = 'STUDY2_BRIDGE_SENTINEL_7c938b06'
SCAFFOLD = '<|im_start|>assistant\n<think>\n\n</think>\n\n'


def bridge(tok, original_user, plate, saved_ids):
    message=MESSAGE.format(plate=plate)
    for text in (original_user,message):
        if SENTINEL in text:raise ValueError('Assistant sentinel must be unique')
        ids=tok.encode(text)
        if tok.decode_all(ids)!=text or any(i in tok.special_ids for i in ids):
            raise ValueError('Ordinary user text must round trip without structural control tokens')
    if tok.prompt(original_user)!=saved_ids:
        raise ValueError('Original prompt renderer does not reproduce parent input_ids')
    old_text=tok.decode_all(saved_ids)
    if not old_text.endswith(SCAFFOLD):raise ValueError('Original empty thinking scaffold missing')
    tokenizer=tok.tokenizer
    def render(messages,tokenize):
        return tokenizer.apply_chat_template(messages,tokenize=tokenize,add_generation_prompt=True,enable_thinking=False)
    messages=[dict(role='user',content=original_user),dict(role='assistant',content=SENTINEL),dict(role='user',content=message)]
    rendered=render(messages,False)
    if rendered.count(SENTINEL)!=1:raise ValueError('Template must render the sentinel exactly once')
    before,after=rendered.split(SENTINEL)
    expected='<|im_end|>\n<|im_start|>user\n'+message+'<|im_end|>\n'+SCAFFOLD
    if after!=expected:raise ValueError('Pinned template bridge structure differs')
    ids=tok.encode(after);template_ids=render(messages,True)
    if tok.decode_all(ids)!=after or tok.decode_all(template_ids)!=rendered:
        raise ValueError('Bridge/template exact round trip failed')
    # The special im_end boundary must isolate the sentinel from the suffix BPE.
    head_ids=tok.encode(before+SENTINEL)
    if template_ids!=head_ids+ids:raise ValueError('Tokenized template suffix differs from bridge IDs')
    closing=tok.encode('<|im_end|>\n')
    single=[dict(role='user',content=message)]
    if after[len('<|im_end|>\n'):]!=render(single,False) or ids!=closing+render(single,True):
        raise ValueError('New user/assistant portion differs from independent template render')
    controls={}
    for marker in ('<|im_start|>','<|im_end|>'):
        encoded=tok.encode(marker)
        if len(encoded)!=1 or encoded[0] not in tok.special_ids or tok.decode_all(encoded)!=marker:
            raise ValueError('Role marker is not a tokenizer control token')
        if tokenizer.convert_tokens_to_ids(marker)!=encoded[0]:raise ValueError('Control-token identity mismatch')
        controls[marker]=encoded[0]
    if controls['<|im_start|>']==controls['<|im_end|>'] or controls['<|im_end|>'] not in tok.eos_ids:
        raise ValueError('Distinct start and permitted terminal end required')
    positions=[(i,t) for i,t in enumerate(ids) if t in tok.special_ids]
    if [t for i,t in positions]!=[controls[x] for x in ('<|im_end|>','<|im_start|>','<|im_end|>','<|im_start|>')]:
        raise ValueError('Unexpected bridge control token or duplicate role header')
    offsets=[dict(role=role,bridge_token_offset=i,context_token_offset=len(saved_ids)+i,
                  bridge_char_offset=len(tok.decode_all(ids[:i])),token_id=t)
             for (i,t),role in zip(positions,('old_assistant_end','new_user_start','new_user_end','new_assistant_start'))]
    context=list(saved_ids)+ids
    if context[:len(saved_ids)]!=saved_ids or tok.decode_all(context)!=old_text+after or SENTINEL in tok.decode_all(context):
        raise ValueError('Append-only context preservation failed')
    return dict(new_user_message=message,new_user_hash=digest(message),old_context_ids=list(saved_ids),
        old_context_hash=digest(saved_ids),bridge_text=after,bridge_ids=ids,bridge_hash=digest(dict(text=after,ids=ids)),
        role_boundaries=offsets,control_token_ids=controls,context_ids=context,context_hash=digest(context),
        template_hash=digest(tokenizer.chat_template),tokenized_template_suffix_verified=True,
        full_conversation_rerender_used=False,empty_old_assistant_closed=True)
