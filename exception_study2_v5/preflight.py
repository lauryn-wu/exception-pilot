"""Weight-free, local-only machine checks; no CUDA/model execution."""
import os
import importlib.metadata
import shutil
import sys
from pathlib import Path
from exception_continuation.qwen3 import dependency_versions, verify_local_snapshot, manifest, ASSISTANT_SUFFIX
from exception_continuation.backend import LocalBackend
from .core import read_plan

def preflight(output):
    plan=read_plan(output);root=Path(plan['config']['model_dir'])
    if os.environ.get('HF_HUB_OFFLINE')!='1' or os.environ.get('TRANSFORMERS_OFFLINE')!='1':
        raise ValueError('Set both Hugging Face offline environment variables to 1')
    if sys.version_info[:2]!=(3,12):raise ValueError('Use the pinned Python 3.12 environment')
    versions=dependency_versions()
    versions['numpy']=importlib.metadata.version('numpy')
    if versions['numpy']!='2.2.4':raise ValueError('Pinned environment requires numpy==2.2.4')
    files=verify_local_snapshot(root,tokenizer_only=True)
    missing=[name for name,item in manifest()['files'].items() if not (root/name).is_file() or (root/name).stat().st_size!=item['size']]
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(root,local_files_only=True,trust_remote_code=False)
    backend=LocalBackend.__new__(LocalBackend);backend.tokenizer=tokenizer;backend.config=plan['config']
    prompt_counts=[]
    for task in plan['tasks']:
        ids=backend.prompt(task['prompt'])
        rendered=tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if not rendered.endswith(ASSISTANT_SUFFIX) or rendered.count('<think>')!=1 or tokenizer.encode(rendered,add_special_tokens=False)!=ids:
            raise ValueError('Official prompt template/empty thinking block changed')
        prompt_counts.append(len(ids))
    if missing:raise ValueError('Missing/wrong-size pinned local files: '+', '.join(missing))
    return dict(status='OFFLINE_PREFLIGHT_PASSED',dependencies=versions,tokenizer_files=files,
                original_input_tokens=sum(prompt_counts),min_prompt_tokens=min(prompt_counts),max_prompt_tokens=max(prompt_counts),
                free_disk_bytes=shutil.disk_usage(root).free,model_weight_hashes='Checked only by explicit technical loader',
                gpu_status='NOT_TESTED',real_model_status='PENDING_FRESH_V5_TECHNICAL_GATE',inference_calls=0,next_stage='STOP')
