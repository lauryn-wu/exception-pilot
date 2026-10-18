"""Native-thinking renderer/parser and a thin separate interface to the pinned loader."""
import copy
import time
from exception_pilot.core import digest
from exception_continuation.core import DEFAULT_CONFIG
from exception_continuation.qwen3 import PROFILE, ASSISTANT_SUFFIX
from exception_study2_source_report.tokenizer import Tokenizer as AssetTokenizer
from . import DECODING, BUDGET_POLICY

OPEN, CLOSE = 151667, 151668
ON_SUFFIX = '<|im_start|>assistant\n'


class NativeTokenizer(AssetTokenizer):
    """Reuse only pinned asset checks/encode/decode. Never the plain-visible prompt method."""
    def render(self, text, thinking):
        if type(thinking) is not bool: raise ValueError('Explicit boolean thinking mode required')
        args=dict(tokenize=True,add_generation_prompt=True,return_dict=False,enable_thinking=thinking)
        ids=self.tokenizer.apply_chat_template([{'role':'user','content':text}],**args)
        rendered=self.tokenizer.apply_chat_template([{'role':'user','content':text}],**dict(args,tokenize=False))
        suffix=ON_SUFFIX if thinking else ASSISTANT_SUFFIX
        if (not isinstance(ids,list) or not ids or any(type(i) is not int for i in ids)
            or not rendered.endswith(suffix) or text not in rendered
            or self.encode(rendered)!=ids or self.decode_all(ids)!=rendered
            or self.encode('<think>')!=[OPEN] or self.encode('</think>')!=[CLOSE]):
            raise ValueError('Pinned native chat-template/token identity check failed')
        # Check the actual behavior of the switch for every prompt, not merely its kwarg.
        other=self.tokenizer.apply_chat_template([{'role':'user','content':text}],**dict(args,enable_thinking=not thinking))
        off, on=(other,ids) if thinking else (ids,other)
        if off==on or self.decode_all(off)!=self.decode_all(on)+'<think>\n\n</think>\n\n':
            raise ValueError('enable_thinking did not produce the pinned template difference')
        return ids


def loader_config(model_dir):
    # This unmodified, historically valid profile is used ONLY to load pinned weights.
    # Its plain-visible prompt() and greedy generate() are never called by this module.
    return dict(copy.deepcopy(DEFAULT_CONFIG),model_dir=str(model_dir),device='cuda:0',dtype='bfloat16',
                chat_template_kwargs={'enable_thinking':False},model_profile=copy.deepcopy(PROFILE))


class NativeBackend:
    simulated=False
    def __init__(self, model_dir, tokenizer):
        from exception_continuation.backend import LocalBackend
        from transformers import GenerationConfig
        self.loaded=LocalBackend(loader_config(model_dir))
        tokenizer.verify_backend(self.loaded.identity)
        self.tok=tokenizer;self.torch=self.loaded.torch
        self.generation=GenerationConfig(**DECODING,eos_token_id=sorted(tokenizer.eos_ids),
            pad_token_id=self.loaded.tokenizer.pad_token_id,bos_token_id=self.loaded.tokenizer.bos_token_id)
        self.identity=dict(interface='NATIVE_THINKING_LABEL_FINAL_V1',loader=self.loaded.identity,
            tokenizer=tokenizer.identity,resolved_generation=self.generation.to_dict(),
            call_overrides=dict(DECODING,use_model_defaults=False),precision='BF16',quantization=None,attention='eager')

    def generate(self, request):
        torch=self.torch;ids=request['input_ids'];budget=request['budget']
        if (request['decoding']!=DECODING or request.get('budget_policy')!=BUDGET_POLICY
            or type(budget) is not int or budget<1 or len(ids)+budget>32768
            or type(request.get('seed')) is not int or not 0<=request['seed']<2**32):
            raise ValueError('Frozen generation parameters differ')
        torch.manual_seed(request['seed']);torch.cuda.manual_seed_all(request['seed'])
        torch.cuda.synchronize();start=time.perf_counter()
        with torch.inference_mode():
            x=self.loaded.tensor(ids)
            output=self.loaded.model.generate(input_ids=x,attention_mask=torch.ones_like(x),
                generation_config=self.generation,max_new_tokens=budget,**DECODING,use_model_defaults=False)
        torch.cuda.synchronize();elapsed=time.perf_counter()-start
        all_ids=output[0].tolist()
        if all_ids[:len(ids)]!=ids: raise ValueError('Model changed exact input IDs')
        tokens=all_ids[len(ids):];eos=bool(tokens and tokens[-1] in self.tok.eos_ids)
        return dict(tokens=tokens,raw_text=self.tok.decode_all(tokens),text=self.tok.decode(tokens),
                    stopped=eos,finish='eos' if eos else 'length',elapsed_seconds=elapsed)


def parse_result(raw, request, tok):
    """Strict final channel; preserve malformed/truncated raw evidence without salvage."""
    errors=[];tokens=raw.get('tokens') if isinstance(raw,dict) else None
    valid_tokens=isinstance(tokens,list) and all(type(t) is int and t>=0 for t in tokens)
    if not valid_tokens:
        return dict(answer=None,correct=False,valid=False,malformed=True,truncated=False,
            parsing_status='metadata_malformed',errors=['invalid raw token payload'],thinking_text=None,final_text=None,
            token_count=None,thinking_tokens=None,final_tokens=None)
    try: text=tok.decode_all(tokens)
    except (ValueError,TypeError,OverflowError,IndexError):
        return dict(answer=None,correct=False,valid=False,malformed=True,truncated=False,
            parsing_status='metadata_malformed',errors=['undecodable token IDs'],thinking_text=None,final_text=None,
            token_count=len(tokens),thinking_tokens=None,final_tokens=None)
    eos=bool(tokens and tokens[-1] in tok.eos_ids)
    if raw.get('raw_text')!=text or raw.get('text')!=tok.decode(tokens): errors.append('token/text mismatch')
    if type(raw.get('stopped')) is not bool or raw['stopped']!=eos or raw.get('finish')!=('eos' if eos else 'length'):
        errors.append('finish/EOS mismatch')
    if not tokens or len(tokens)>request['budget']: errors.append('invalid token length')
    body=tokens[:-1] if eos else tokens
    if any(t in tok.special_ids-{OPEN,CLOSE} for t in body): errors.append('structural token in response')
    thinking=[];final=body;structure=True
    if request['thinking']:
        # The pinned thinking-on prompt ends before <think>; it must be generated.
        if (body.count(OPEN)!=1 or body.count(CLOSE)!=1 or body.index(CLOSE)<body.index(OPEN)
            or tok.decode_all(body[:body.index(OPEN)]).strip()):
            structure=False;thinking=body[1:] if body and body[0]==OPEN else body;final=[]
        else:
            start=body.index(OPEN);end=body.index(CLOSE);thinking=body[start+1:end];final=body[end+1:]
    elif OPEN in body or CLOSE in body:
        structure=False
    thinking_text=tok.decode_all(thinking);final_text=tok.decode_all(final)
    truncated=raw.get('finish')=='length' or (not eos and len(tokens)>=request['budget'])
    label=final_text.strip() if final_text.strip() in ('A','B','C') else None
    valid=not errors and structure and eos and not truncated and label is not None
    status='metadata_malformed' if errors else 'truncated' if truncated else 'malformed_channel' if not structure else 'invalid_final' if not valid else 'valid'
    return dict(answer=label if valid else None,final_candidate=label,correct=bool(valid and label==request['expected']),
        valid=valid,malformed=bool(errors or not structure or (not valid and not truncated)),truncated=truncated,
        parsing_status=status,errors=errors,eos_observed=eos,thinking_text=thinking_text,final_text=final_text,
        token_count=len(tokens),thinking_tokens=len(thinking),final_tokens=len(final),
        note='Thinking is generated scratchpad text; label-only final does not mean no generated reasoning.')
