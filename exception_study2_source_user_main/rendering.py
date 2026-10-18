"""Thin adapter: preserve original input and nonempty saved reasoning prefixes."""
import copy
from exception_pilot.core import digest
from exception_study2_v5.scoring import checkpoints
from exception_study2_source_user_pilot.rendering import bridge,SENTINEL
from . import CUTS,RENDERER


def append_prefix(tok,row,origin,verified_bridge):
    k=origin['checkpoint'];ids=row['input_ids'];prefix=row['raw']['tokens'][:k]
    cuts={x['name']:x for x in checkpoints(row)};cut=cuts.get('fixed/'+str(k))
    if k not in CUTS or not cut or not cut['eligible'] or origin['boundary']!=cut:
        raise ValueError('Required original checkpoint is ineligible or its boundary changed')
    if origin['input_ids']!=ids or origin['prefix_ids']!=prefix or len(prefix)!=k:
        raise ValueError('Saved original prompt/prefix IDs differ')
    text=tok.decode_all(prefix)
    if (any(t in tok.special_ids for t in prefix) or tok.encode(text)!=prefix
        or digest(prefix)!=cut['token_hash'] or digest(text)!=cut['text_hash']
        or text!=row['raw']['text'][:cut['char_end']]):
        raise ValueError('Exact saved token/text prefix boundary differs')
    b=copy.deepcopy(verified_bridge)
    if b['old_context_ids']!=ids:raise ValueError('Pilot bridge must be validated on original input IDs only')
    old=list(ids)+list(prefix);context=old+b['bridge_ids']
    if (context[:len(old)]!=old or tok.decode_all(context)!=tok.decode_all(old)+b['bridge_text']
        or SENTINEL in tok.decode_all(context)):
        raise ValueError('Append-only main context preservation failed')
    b.update(old_context_ids=old,old_context_hash=digest(old),context_ids=context,context_hash=digest(context),
        empty_old_assistant_closed=k==0,assistant_explicitly_closed=True,renderer_version=RENDERER,
        original_input_ids=list(ids),original_input_hash=digest(ids),prefix_ids=list(prefix),prefix_hash=digest(prefix))
    for offset in b['role_boundaries']:
        offset['context_token_offset']=len(old)+offset['bridge_token_offset']
    return b
