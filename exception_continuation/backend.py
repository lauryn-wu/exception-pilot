"""No remote APIs; token arrays are the continuation contract."""
import hashlib
import importlib.metadata
import math
import os
from pathlib import Path
import platform

from exception_pilot.core import digest


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


class LocalBackend:
    simulated = False

    def __init__(self, config):
        if not config['model_dir'] or not Path(config['model_dir']).is_dir():
            raise ValueError('Supply an existing local model directory; no downloads are permitted')
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
        import torch
        import transformers
        from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
        self.torch = torch; self.config = config
        self.tokenizer = AutoTokenizer.from_pretrained(config['model_dir'], local_files_only=True, trust_remote_code=False)
        if not self.tokenizer.chat_template:
            raise ValueError('A frozen chat template is required')
        self.model = AutoModelForCausalLM.from_pretrained(config['model_dir'], local_files_only=True,
                    trust_remote_code=False, torch_dtype=getattr(torch, config['dtype']), attn_implementation='eager')
        if self.model.config.is_encoder_decoder:
            raise ValueError('Only decoder-only causal models support this protocol')
        self.model.to(config['device']); self.model.eval()
        torch.use_deterministic_algorithms(True)
        if hasattr(torch.backends, 'cuda'): torch.backends.cuda.matmul.allow_tf32 = False
        eos = self.model.generation_config.eos_token_id
        if eos is None: eos = self.tokenizer.eos_token_id
        if eos is None: raise ValueError('An explicit EOS token is required')
        self.eos_ids = {eos} if isinstance(eos, int) else set(eos)
        self.special_ids = set(self.tokenizer.all_special_ids) | self.eos_ids
        self.generation = GenerationConfig(do_sample=False, num_beams=1, use_cache=True,
                                          eos_token_id=eos, pad_token_id=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else min(self.eos_ids),
                                          bos_token_id=self.tokenizer.bos_token_id)
        root = Path(config['model_dir'])
        files = {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob('*'))
                 if p.is_file() and p.suffix in {'.safetensors', '.bin', '.json', '.model', '.txt', '.jinja', '.tiktoken'}}
        self.identity = dict(kind='LOCAL_HF_TOKEN_IDS', config=config, files=files,
                             torch=torch.__version__, transformers=transformers.__version__,
                             tokenizers=importlib.metadata.version('tokenizers'), python=platform.python_version(),
                             device=str(self.model.device), dtype=str(self.model.dtype),
                             hardware=torch.cuda.get_device_name(self.model.device) if str(self.model.device).startswith('cuda') else platform.machine(),
                             cuda=torch.version.cuda, cudnn=torch.backends.cudnn.version(),
                             chat_template=self.tokenizer.chat_template, special_ids=sorted(self.special_ids),
                             generation=self.generation.to_dict())

    def prompt(self, text):
        ids = self.tokenizer.apply_chat_template([{'role': 'user', 'content': text}], tokenize=True,
                    add_generation_prompt=True, return_dict=False, **self.config['chat_template_kwargs'])
        if not isinstance(ids, list) or not ids or not all(type(i) is int for i in ids):
            raise ValueError('Unsupported template return type')
        rendered = self.tokenizer.apply_chat_template([{'role': 'user', 'content': text}], tokenize=False,
                    add_generation_prompt=True, **self.config['chat_template_kwargs'])
        if text not in rendered:
            raise ValueError('Cannot audit this template serialization; unsupported interface')
        assert_plain_format(rendered.rsplit(text, 1)[-1])
        return ids

    def encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, ids):
        return self.tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)

    def tensor(self, ids):
        return self.torch.tensor([ids], dtype=self.torch.long, device=self.model.device)

    def generate(self, ids, budget, capture_at=()):
        if budget <= 0: raise ValueError('Positive remaining budget required')
        captured, step = {}, [0]
        # Observe the raw next-token logits in the uninterrupted generation itself.
        # A forward hook stores only requested steps; it does not alter any outputs.
        def capture(module, args, outputs):
            k = step[0]
            if k in capture_at:
                values = outputs.logits[0, -1].detach().float().cpu().tolist()
                # Preserve invalid telemetry in strict JSON; validation rejects it.
                captured[str(k)] = [v if math.isfinite(v) else str(v) for v in values]
            step[0] += 1
        handle = self.model.register_forward_hook(capture)
        try:
            with self.torch.inference_mode():
                x = self.tensor(ids)
                result = self.model.generate(input_ids=x, attention_mask=self.torch.ones_like(x),
                          generation_config=self.generation, max_new_tokens=budget)
        finally:
            handle.remove()

        all_ids = result[0].tolist()
        if all_ids[:len(ids)] != ids: raise ValueError('Backend changed input prefix')
        suffix = all_ids[len(ids):]
        return dict(tokens=suffix, stopped=bool(suffix and suffix[-1] in self.eos_ids),
                    text=self.decode(suffix), next_token_logits=captured, finish='eos' if suffix and suffix[-1] in self.eos_ids else 'length')

    def score(self, context, candidate):
        tokens = self.encode(candidate)
        if not tokens or any(t in self.special_ids for t in tokens): raise ValueError('Invalid candidate tokens')
        if self.decode(tokens) != candidate: raise ValueError('Candidate text does not round trip')
        with self.torch.inference_mode():
            logits = self.model(input_ids=self.tensor(context + tokens), use_cache=False).logits[0]
            lp = self.torch.log_softmax(logits[len(context)-1:len(context)+len(tokens)-1].float(), dim=-1)
            values = [lp[i, token].item() for i, token in enumerate(tokens)]
        if not all(math.isfinite(v) for v in values): raise ValueError('Nonfinite candidate probability')
        return dict(tokens=tokens, token_logprobs=values, logprob=sum(values))


class MockBackend:
    """Deterministic character model for SOFTWARE TESTS ONLY."""
    simulated = True
    special_ids = {0, 1000000}
    identity = {'kind': 'SIMULATED_CHARACTER_MODEL_NOT_SCIENTIFIC_EVIDENCE'}
    script = 'Its verified class is missing. ' + 'Consider the table carefully. ' * 5 + '\nANSWER: A'

    def encode(self, text): return [ord(c) for c in text]
    def decode(self, tokens): return ''.join(chr(t) for t in tokens if t not in self.special_ids)
    def prompt(self, text): return self.encode(text) + [1000000]
    def generate(self, ids, budget, capture_at=()):
        body = ids[ids.index(1000000)+1:]
        source = self.encode(self.script) + [0]
        if source[:len(body)] == body: suffix = source[len(body):][:budget]
        else: suffix = (self.encode('\nANSWER: A') + [0])[:budget]
        captured = {str(k): [0.0, -1.0, -2.0] for k in capture_at if k < len(suffix)}
        return dict(tokens=suffix, stopped=bool(suffix and suffix[-1] == 0), text=self.decode(suffix), next_token_logits=captured,
                    finish='eos' if suffix and suffix[-1] == 0 else 'length')
    def score(self, context, candidate):
        tokens = self.encode(candidate)
        lp = [-1.0 - ('ABC'.index(candidate.strip()) / 10)] * len(tokens)
        return dict(tokens=tokens, token_logprobs=lp, logprob=sum(lp))


def assert_plain_format(text):
    if text.count('<think>') > text.count('</think>') or '<|channel|>analysis' in text or '[THINK]' in text:
        raise ValueError('Open thinking/channel formatting is unsupported by this plain-visible interface')


def readout(backend, input_ids, prefix_ids, gold, pattern, cue_text='\nANSWER:'):
    assert_plain_format(backend.decode(prefix_ids))
    cue = backend.encode(cue_text)
    if any(t in backend.special_ids for t in cue) or backend.decode(cue) != cue_text:
        raise ValueError('Readout cue must round trip without special tokens')
    context = input_ids + prefix_ids + cue
    if backend.decode(context) != backend.decode(input_ids + prefix_ids) + cue_text:
        raise ValueError('Cue tokens do not preserve the intended concatenated text')
    for label in 'ABC':
        candidate = ' ' + label + '\n'
        if backend.decode(context + backend.encode(candidate)) != backend.decode(context) + candidate:
            raise ValueError('Candidate tokens do not preserve the intended concatenated text')
    scores = {label: backend.score(context, ' ' + label + '\n') for label in 'ABC'}
    top = max(s['logprob'] for s in scores.values())
    z = top + math.log(sum(math.exp(s['logprob']-top) for s in scores.values()))
    return dict(cue_text=cue_text, cue_ids=cue, candidate_texts={c: ' ' + c + '\n' for c in 'ABC'}, context_hash=digest(context), scores=scores,
                normalized={c: math.exp(s['logprob']-z) for c, s in scores.items()},
                candidate_log_mass=z, gold_pattern_log_odds=scores[gold]['logprob']-scores[pattern]['logprob'],
                interpretation='ANSWER_PREFERENCES_UNDER_A_CHECKPOINT_READOUT_NOT_INTERNAL_BELIEFS')
