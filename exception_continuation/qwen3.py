"""Pinned local Qwen3-32B profile and weight-free tokenizer audit. No downloads."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

MODEL_ID = 'Qwen/Qwen3-32B'
REVISION = '9216db5781bf21249d130ec9da846c4624c16137'
PROFILE = dict(repo_id=MODEL_ID, revision=REVISION, tokenizer_revision=REVISION)
MANIFEST_SHA256 = '374fed8675583d337b506d615d0e9176da811467c2bd06902d8ee1285ebe71fb'
MANIFEST_PATH = Path(__file__).with_name('data')/'qwen3_32b_revision.json'
ASSISTANT_SUFFIX = '<|im_start|>assistant\n<think>\n\n</think>\n\n'
DEPENDENCIES = {'torch': '2.7.1', 'transformers': '4.51.3', 'tokenizers': '0.21.1',
                'huggingface-hub': '0.30.2', 'safetensors': '0.5.3', 'Jinja2': '3.1.6'}


def manifest():
    raw = MANIFEST_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Pinned Qwen revision manifest changed')
    result = json.loads(raw)
    if any(result[k] != v for k, v in PROFILE.items()):
        raise ValueError('Qwen revision identity differs')
    return result


def validate_profile(config, defaults):
    if config.get('model_profile') != PROFILE:
        raise ValueError('Use the pinned Qwen/Qwen3-32B model and tokenizer revision')
    if (config['dtype'] != 'bfloat16' or not re.fullmatch(r'cuda(?::\d+)?', config['device'])
            or config['chat_template_kwargs'] != {'enable_thinking': False}):
        raise ValueError('Qwen profile requires BF16, one CUDA device and enable_thinking=False')
    for key in ('max_new_tokens', 'interface', 'readout_cues', 'cue_check_checkpoints',
                'event_checkpoints', 'validation_tolerances', 'calibration'):
        if config[key] != defaults[key]:
            raise ValueError('Qwen profile preserves the existing protocol setting: ' + key)
    manifest()


def dependency_versions(require_torch=True):
    versions = {}
    for name, expected in DEPENDENCIES.items():
        if name == 'torch' and not require_torch:
            continue
        actual = importlib.metadata.version(name)
        if actual.split('+')[0] != expected:
            raise ValueError(f'Pinned Qwen environment requires {name}=={expected}; found {actual}')
        versions[name] = actual
    return versions


def verify_local_snapshot(root, tokenizer_only=False):
    """Compare local bytes to official metadata; revision= alone cannot pin a local path."""
    from .backend import file_hash
    root = Path(root)
    locked = manifest()
    required = {name: info for name, info in locked['files'].items()
                if not tokenizer_only or not name.endswith('.safetensors')}
    # Extra loader overrides must not silently supersede the official files.
    sensitive = {'.json', '.jinja', '.model', '.txt', '.tiktoken', '.safetensors', '.bin', '.gguf', '.py'}
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if any(part.startswith('.') for part in relative.parts):
            continue  # HF download/cache bookkeeping is not a loader input.
        if path.is_file() and path.suffix in sensitive and str(relative) not in locked['files']:
            raise ValueError('Unpinned model/tokenizer override: ' + str(relative))
    hashes = {}
    for name, expected in required.items():
        path = root/name
        if not path.is_file() or path.stat().st_size != expected['size']:
            raise ValueError('Missing or wrong-size pinned Qwen file: ' + name)
        hashes[name] = file_hash(path)
        if hashes[name] != expected['sha256']:
            raise ValueError('Pinned Qwen content hash differs: ' + name)
    return hashes


def tokenizer_check(model_dir):
    """Real tokenizer/template checks only; no model load, forward pass or generation."""
    versions = dependency_versions(require_torch=False)
    hashes = verify_local_snapshot(model_dir, tokenizer_only=True)
    from transformers import AutoTokenizer
    from .backend import LocalBackend
    from .core import DEFAULT_CONFIG, make_plan
    tokenizer = AutoTokenizer.from_pretrained(model_dir, revision=REVISION,
                                             local_files_only=True, trust_remote_code=False)
    backend = LocalBackend.__new__(LocalBackend)
    backend.tokenizer = tokenizer
    backend.config = dict(chat_template_kwargs={'enable_thinking': False})
    config = dict(DEFAULT_CONFIG, model_dir=str(model_dir), device='cuda:0', dtype='bfloat16',
                  chat_template_kwargs={'enable_thinking': False}, model_profile=dict(PROFILE))
    plan = make_plan('selection', config)
    generation = json.loads((Path(model_dir)/'generation_config.json').read_text())
    eos = generation['eos_token_id']
    if eos != [151645, 151643] or tokenizer.eos_token_id != 151645 or tokenizer.pad_token_id != 151643:
        raise ValueError('Qwen EOS/PAD identities changed')
    specials = set(tokenizer.all_special_ids) | set(eos)
    candidates = {label: backend.encode(' ' + label + '\n') for label in 'ABC'}
    for label, tokens in candidates.items():
        if any(t in specials for t in tokens) or backend.decode(tokens) != ' ' + label + '\n':
            raise ValueError('Complete candidate does not round trip')
    rows = []
    # Synthetic prefix is a tokenization fixture, never a natural Qwen trajectory.
    prefix = backend.encode('The supplied record is being considered.')
    for task in plan['tasks']:
        ids = backend.prompt(task['prompt'])  # Uses the existing interface validator, unchanged.
        rendered = tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if not rendered.endswith(ASSISTANT_SUFFIX) or rendered.count('<think>') != 1:
            raise ValueError('Official empty thinking block missing or duplicated')
        if tokenizer.encode(rendered, add_special_tokens=False) != ids:
            raise ValueError('Original prompt tokens do not round trip')
        for cue in config['readout_cues']:
            context = ids + prefix + backend.encode(cue)
            if backend.decode(context) != backend.decode(ids + prefix) + cue:
                raise ValueError('Cue concatenation changed')
            for label, tokens in candidates.items():
                if backend.decode(context + tokens) != backend.decode(context) + ' ' + label + '\n':
                    raise ValueError('Candidate concatenation changed')
        rows.append(dict(task_id=task['id'], prompt_tokens=len(ids)))
    return dict(model_profile=PROFILE, status='TOKENIZER_ONLY_PASSED', files=hashes,
                dependencies=versions, prompt_suffix=ASSISTANT_SUFFIX,
                empty_block_token_ids=tokenizer.encode('<think>\n\n</think>\n\n', add_special_tokens=False),
                eos_token_ids=eos, pad_token_id=tokenizer.pad_token_id, candidates=candidates,
                selection_prompts=rows, original_model_responses=0, inference_calls=0,
                real_model_compatibility='PENDING', behavioral_replication='PENDING',
                caveat='No weights loaded. No logits, probabilities, replay equivalence or behavior tested.')


def main():
    import argparse
    from exception_pilot.storage import write_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise ValueError('Preserve the existing tokenizer audit; choose a new output file')
    result = tokenizer_check(args.model_dir)
    write_json(target, result)
    print(json.dumps({k: result[k] for k in ('status', 'inference_calls', 'real_model_compatibility', 'behavioral_replication')}))


if __name__ == '__main__':
    main()
