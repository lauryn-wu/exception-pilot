"""Pinned tokenizer assets only. Never load, hash, or download model weights."""
import json
from pathlib import Path
from exception_continuation.qwen3 import REVISION,PROFILE,verify_local_snapshot,dependency_versions
from exception_continuation.backend import LocalBackend
from . import CANDIDATES


class Tokenizer:
    def __init__(self,root):
        self.root=Path(root).resolve()
        if not self.root.is_dir():raise ValueError('Missing pinned local tokenizer assets: '+str(self.root))
        versions=dependency_versions(require_torch=False)
        files=verify_local_snapshot(self.root,tokenizer_only=True)
        from transformers import AutoTokenizer
        self.tokenizer=AutoTokenizer.from_pretrained(str(self.root),revision=REVISION,
            local_files_only=True,trust_remote_code=False)
        self.config={'chat_template_kwargs':{'enable_thinking':False}}
        generation=json.loads((self.root/'generation_config.json').read_text())
        self.eos_ids=set(generation['eos_token_id']);self.special_ids=set(self.tokenizer.all_special_ids)|self.eos_ids
        if self.eos_ids!={151645,151643}:raise ValueError('Pinned EOS IDs changed')
        if {c:self.encode(' '+c+'\n') for c in 'ABC'}!=CANDIDATES:raise ValueError('Unsupported candidate tokenization')
        self.identity=dict(profile=PROFILE,files=files,dependencies=versions,chat_template=self.tokenizer.chat_template,
            eos_ids=sorted(self.eos_ids),special_ids=sorted(self.special_ids),candidates=CANDIDATES)

    def encode(self,text):return self.tokenizer.encode(text,add_special_tokens=False)
    def decode(self,ids):return self.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    def decode_all(self,ids):return self.tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    def prompt(self,text):return LocalBackend.prompt(self,text)

    def verify_backend(self,backend):
        if (backend.get('config',{}).get('model_profile')!=PROFILE
            or backend['config'].get('dtype')!='bfloat16'
            or backend['config'].get('chat_template_kwargs')!={'enable_thinking':False}
            or backend.get('dtype')!='torch.bfloat16'
            or backend.get('chat_template')!=self.identity['chat_template']
            or backend.get('special_ids')!=self.identity['special_ids']
            or any(backend.get('files',{}).get(k)!=v for k,v in self.identity['files'].items())):
            raise ValueError('Pinned tokenizer/model/backend identity mismatch')
        if backend.get('generation_overrides')!={'do_sample':False,'num_beams':1,'use_model_defaults':False}:
            raise ValueError('Original greedy generation overrides differ')


def concatenate(tok,base_ids,suffix):
    ids=tok.encode(suffix)
    if tok.decode_all(ids)!=suffix or any(t in tok.special_ids for t in ids):
        raise ValueError('Suffix must round trip exactly without special tokens')
    context=list(base_ids)+ids
    if tok.decode_all(context)!=tok.decode_all(base_ids)+suffix:
        raise ValueError('Decoded prefix/suffix concatenation differs')
    # Deliberately do NOT re-encode the combined context: suffix BPE is independent.
    return ids,context
