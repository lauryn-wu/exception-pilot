"""Pinned Qwen3.8 tokenizer and one vLLM token-ID backend. No imports load weights."""
import importlib.metadata
import json
import time
from pathlib import Path
from exception_pilot.core import digest
from exception_review.artifacts import sha
from . import MODEL, REVISION, RUNTIME, ENGINE, SAMPLER, SAMPLING_OPTIONS, BUDGET, SEED

ASSET_LOCK = Path(__file__).with_name('assets.json')


def check_versions(live=False):
    wanted=RUNTIME if live else {k:v for k,v in RUNTIME.items() if k not in ('vllm','torch')}
    actual={k:importlib.metadata.version(k) for k in wanted}
    if any(actual[k].split('+')[0]!=v for k,v in wanted.items()):
        raise ValueError('Pinned runtime differs: '+repr(actual))
    return actual


class Tokenizer:
    def __init__(self, root):
        from transformers import AutoTokenizer
        self.root=Path(root).resolve(); lock=json.loads(ASSET_LOCK.read_text())
        for name,expected in lock['assets'].items():
            if sha(self.root/name)!=expected: raise ValueError('Pinned tokenizer/config asset differs: '+name)
        versions=check_versions()
        self.tokenizer=AutoTokenizer.from_pretrained(str(self.root),local_files_only=True,trust_remote_code=False)
        self.vocabulary_size=len(self.tokenizer)
        self.template=(self.root/'chat_template.jinja').read_text()
        if self.tokenizer.chat_template!=self.template: raise ValueError('Official template changed')
        self.open_id=self.one('<think>');self.close_id=self.one('</think>')
        self.eos_ids=set(json.loads((self.root/'generation_config.json').read_text())['eos_token_id'])
        self.special_ids=set(self.tokenizer.all_special_ids)|{self.open_id,self.close_id}
        config=json.loads((self.root/'config.json').read_text())
        if config['model_type']!='qwen3_5' or config.get('quantization_config'):
            raise ValueError('Expected official unquantized Qwen3.8 architecture')
        self.context_limit=config['text_config']['max_position_embeddings']
        self.identity=dict(model=MODEL,revision=REVISION,processor_revision=REVISION,
            assets=lock['assets'],template_sha256=sha(self.root/'chat_template.jinja'),
            thinking_open_id=self.open_id,thinking_close_id=self.close_id,eos_ids=sorted(self.eos_ids),
            pad_id=self.tokenizer.pad_token_id,native_context_limit=self.context_limit,versions=versions)
        probe=[{'role':'user','content':'Return A.'}]
        medium=self._template(probe,True,'medium')
        if medium==self._template(probe,True,'xhigh') or medium==self._template(probe,True,'low'):
            raise ValueError('reasoning_effort was silently ignored')
        try:self._template(probe,True,'unsupported')
        except Exception as e:
            if 'reasoning effort' not in str(e).lower(): raise
        else: raise ValueError('Template accepts unsupported effort')
        self.render('Return A.',True);self.render('Return A.',False)

    def one(self,text):
        ids=self.encode(text)
        if len(ids)!=1: raise ValueError('Thinking marker is not one actual model token')
        return ids[0]

    def encode(self,text): return self.tokenizer.encode(text,add_special_tokens=False)
    def decode_all(self,ids):
        if any(type(i) is not int or not 0<=i<self.vocabulary_size for i in ids): raise ValueError('Invalid token IDs')
        return self.tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    def decode(self,ids): return self.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    def _template(self,messages,thinking,effort=None):
        kwargs=dict(enable_thinking=thinking,preserve_thinking=True)
        if effort is not None:kwargs['reasoning_effort']=effort
        return self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,**kwargs)
    def render(self,text,thinking):
        if type(thinking) is not bool: raise ValueError('Explicit thinking boolean required')
        messages=[{'role':'user','content':text}]
        on=self._template(messages,True,'medium');off=self._template(messages,False)
        if not off.startswith(on) or self.close_id not in self.encode(off[len(on):]):
            raise ValueError('Actual thinking mode boundary differs')
        suffix=self.encode(off[len(on):])
        if suffix.count(self.close_id)!=1 or self.decode_all([i for i in suffix if i!=self.close_id]).strip():
            raise ValueError('Unexpected disabled-thinking scaffold')
        rendered=on if thinking else off;ids=self.encode(rendered)
        args=dict(enable_thinking=thinking,preserve_thinking=True)
        if thinking:args['reasoning_effort']='medium'
        direct=self.tokenizer.apply_chat_template(messages,tokenize=True,return_dict=False,add_generation_prompt=True,**args)
        if direct!=ids or self.decode_all(ids)!=rendered or text not in rendered:
            raise ValueError('Official prompt token/text identity differs')
        return ids


def parse_result(raw, request, tok):
    """Offsets are half-open token indices in prefix+new output, not prompt tokens."""
    empty=dict(answer=None,correct=False,valid=False,malformed=True,truncated=False,
        missing_final=True,parsing_status='metadata_malformed',thinking_text=None,final_text=None,
        token_count=None,thinking_tokens=None,final_tokens=None,token_boundaries=None)
    if not isinstance(raw,dict) or not isinstance(raw.get('tokens'),list):return dict(empty,errors=['invalid payload'])
    generated=raw['tokens']; prefix=request.get('prefix_token_ids',[]); tokens=prefix+generated;errors=[]
    try:text=tok.decode_all(generated); combined=tok.decode_all(tokens)
    except (ValueError,TypeError,OverflowError,IndexError):return dict(empty,errors=['invalid tokens'])
    eos=bool(tokens and tokens[-1] in tok.eos_ids)
    if raw.get('input_ids_verified') is not True:errors.append('input token identity not verified')
    if raw.get('raw_text')!=text or raw.get('text')!=tok.decode(generated):errors.append('token/text mismatch')
    if raw.get('backend_finish_reason') not in (None,'stop' if eos else 'length'):errors.append('backend finish mismatch')
    if raw.get('stopped') is not eos or raw.get('finish')!=('eos' if eos else 'length'):errors.append('finish/EOS mismatch')
    if not generated or len(generated)>request['budget']:errors.append('invalid generation length')
    body=tokens[:-1] if eos else tokens
    if any(i in tok.special_ids-{tok.open_id,tok.close_id} for i in body):errors.append('unexpected structural token')
    truncated=not eos and len(generated)==request['budget']
    if not eos and not truncated:errors.append('unfinished return below cap')
    boundary=0;structure=True
    if request['thinking']:
        # The OFFICIAL prompt already contains the opening marker. Never require it again.
        if tok.open_id in body or body.count(tok.close_id)!=1:
            structure=False;boundary=len(body)
        else:boundary=body.index(tok.close_id)
        think=body[:boundary];start=boundary+1 if structure else len(body)
    else:
        think=[];start=0
        if tok.open_id in body or tok.close_id in body:structure=False
    final=body[start:];final_text=tok.decode_all(final);label=final_text.strip()
    valid=not errors and structure and eos and label in ('A','B','C')
    return dict(answer=label if valid else None,correct=valid and label==request.get('expected'),valid=valid,
        malformed=bool(errors or not structure and not truncated or eos and label not in ('A','B','C')),
        truncated=truncated,missing_final=not final_text.strip(),eos_observed=eos,errors=errors,
        parsing_status='metadata_malformed' if errors else 'truncated' if truncated else 'malformed_channel' if not structure else 'valid' if valid else 'invalid_final',
        thinking_text=tok.decode_all(think),final_text=final_text,raw_combined_text=combined,
        token_count=len(generated),thinking_tokens=len(think),final_tokens=len(final),
        token_boundaries=dict(thinking=[0,len(think)],final=[start,len(body)],eos=[len(body),len(tokens)],
                              supplied_prefix_tokens=len(prefix),units='half-open indices in prefix plus new output'))


def verify_weights(root):
    lock=json.loads(ASSET_LOCK.read_text())
    for number,(name,info) in enumerate(lock['weights'].items(),1):
        import sys
        print(f'Verifying pinned model shard {number}/{len(lock["weights"])}: {name}',file=sys.stderr,flush=True)
        p=Path(root)/name
        import hashlib
        h=hashlib.sha256()
        with p.open('rb') as handle:
            for chunk in iter(lambda:handle.read(8*1024*1024),b''):h.update(chunk)
        if p.stat().st_size!=info['bytes'] or h.hexdigest()!=info['sha256']:
            raise ValueError('Pinned model shard differs: '+name)
    return digest(lock['weights'])


def resolved_sampling(params):
    # SamplingParams is a msgspec Struct, not a dataclass. Preserve default fields too.
    import msgspec
    return {f.name:msgspec.to_builtins(sorted(v) if isinstance(v,set) else v)
            for f in msgspec.structs.fields(params) for v in [getattr(params,f.name)]}


class Backend:
    simulated=False
    def __init__(self,model_dir,tok):
        versions=check_versions(live=True)
        # Verify exact shards before CUDA/model initialization; never read weights for inspection.
        weights_hash=verify_weights(model_dir)
        model_tok=Tokenizer(model_dir)
        if model_tok.identity!=tok.identity: raise ValueError('Model and tokenizer assets differ')
        import torch
        from vllm import LLM, SamplingParams
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise ValueError('BF16 CUDA GPU required')
        self.torch=torch;self.tok=tok
        print('Loading pinned BF16 Qwen3.8 with vLLM; initialization may take several minutes.',flush=True)
        self.model=LLM(model=str(model_dir),tokenizer=str(tok.root),revision=REVISION,tokenizer_revision=REVISION,**ENGINE)
        cfg=self.model.llm_engine.vllm_config.model_config
        if cfg.dtype!=torch.bfloat16 or cfg.quantization is not None:raise ValueError('Resolved precision differs')
        self.identity=dict(backend='vllm-offline-token-ids',tokenizer=tok.identity,model=MODEL,revision=REVISION,
            weights_hash=weights_hash,engine=ENGINE,versions=versions,cuda=torch.version.cuda,
            hardware=torch.cuda.get_device_name(0),precision='BF16',quantization=None,
            recurrent_state_dtype='float32 per official text_config',batch_size=1,
            resolved_sampling_defaults=resolved_sampling(SamplingParams(**SAMPLER,**SAMPLING_OPTIONS,seed=SEED,max_tokens=BUDGET,stop_token_ids=sorted(tok.eos_ids))))
    def generate(self,r):
        from vllm import SamplingParams
        if r['sampler']!=SAMPLER or r['sampling_options']!=SAMPLING_OPTIONS or r['engine']!=ENGINE or r['model_revision']!=REVISION:
            raise ValueError('Frozen generation settings differ')
        params=SamplingParams(**r['sampler'],**r['sampling_options'],seed=r['seed'],max_tokens=r['budget'],
            stop_token_ids=sorted(self.tok.eos_ids))
        resolved=resolved_sampling(params)
        self.torch.cuda.synchronize();self.torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
        result=self.model.generate([{'prompt_token_ids':r['input_ids']}],params,use_tqdm=False)[0]
        self.torch.cuda.synchronize();elapsed=time.perf_counter()-start
        input_ok=list(result.prompt_token_ids)==r['input_ids']
        if len(result.outputs)!=1:
            return dict(tokens=[],raw_text='',text='',input_ids_verified=input_ok,
                malformed_backend_outputs=[list(x.token_ids) for x in result.outputs],
                backend_error='Expected one returned sequence',elapsed_seconds=elapsed)
        output=result.outputs[0];tokens=list(output.token_ids);eos=bool(tokens and tokens[-1] in self.tok.eos_ids)
        return dict(tokens=tokens,raw_text=self.tok.decode_all(tokens),text=self.tok.decode(tokens),
            stopped=eos,finish='eos' if eos else 'length',backend_finish_reason=output.finish_reason,
            backend_stop_reason=output.stop_reason,elapsed_seconds=elapsed,
            input_ids_verified=input_ok,actual_input_ids=list(result.prompt_token_ids),resolved_sampling=resolved,peak_process_allocated_bytes=self.torch.cuda.max_memory_allocated(),
            gpu_memory_used_bytes=self.torch.cuda.mem_get_info()[1]-self.torch.cuda.mem_get_info()[0])
