#!/usr/bin/env bash
# Environment/model preparation ONLY. No Qwen generation or paid judge requests.
# Run on the fresh GPU Pod after cloning the private repository as documented.
set -Eeuo pipefail
umask 077

REPO=/workspace/exception-pilot
COMMIT=21981f56f7d9a142e7a15ee4ba8b2f79cf872e32
REVISION=9216db5781bf21249d130ec9da846c4624c16137
VENV=/workspace/venvs/study2-qwen3
SESSION=/workspace/study2-session.env
export STUDY2_MODEL_DIR="/workspace/models/Qwen3-32B/$REVISION"
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
export HF_HOME=/workspace/.cache/study2-huggingface
export TMPDIR=/workspace/study2-tmp

fail() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }
trap 'printf "\nSETUP STOPPED at line %s. No scientific inference was launched. Preserve the files and inspect the error.\n" "$LINENO" >&2' ERR

[[ ! -e "$SESSION" ]] || fail "$SESSION already exists. Do not create a second run; source it to inspect/resume the existing one."
[[ -d "$REPO/.git" ]] || fail "Clone the study branch to $REPO first."
command -v python3.12 >/dev/null || fail "Python 3.12 is missing. Use the documented Ubuntu 24.04 template and install python3.12-venv."
command -v nvidia-smi >/dev/null || fail "nvidia-smi is missing; check that this is a GPU Pod."
cd "$REPO"
[[ "$(git rev-parse HEAD)" == "$COMMIT" ]] || fail "Checkout is not the reviewed commit $COMMIT. Do not reset unrelated work."
git diff --quiet HEAD -- || fail "Tracked repository files have local edits. Preserve and inspect them before setup."

mkdir -p "$TMPDIR" "$HF_HOME" /workspace/venvs /workspace/models
printf '\n--- Host and storage ---\n'
nvidia-smi
free -h
df -h /workspace

python3.12 - <<'PY'
import os
from pathlib import Path
import shutil
import sys
assert sys.version_info[:2] == (3, 12), sys.version
limits = []
for line in Path('/proc/meminfo').read_text().splitlines():
    if line.startswith('MemTotal:'):
        limits.append(int(line.split()[1]) * 1024)
for name in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
    p = Path(name)
    if p.exists():
        value = p.read_text().strip()
        if value.isdigit() and 0 < int(value) < 2**60:
            limits.append(int(value))
if not limits or min(limits) < 128_000_000_000:
    raise SystemExit('Need at least 128 GB allocated host RAM for this setup; check the Pod configuration.')
model = Path(os.environ['STUDY2_MODEL_DIR'])
# Allow retrying an incomplete setup/download without demanding duplicate storage.
already = sum(p.stat().st_size for p in model.rglob('*') if p.is_file()) if model.exists() else 0
free = shutil.disk_usage('/workspace').free
print(f'Effective host capacity: {min(limits)/1e9:.1f} GB; free workspace: {free/1e9:.1f} GB')
if free + already < 150_000_000_000:
    raise SystemExit('Insufficient workspace headroom. Use a 200 GB persistent /workspace volume.')
PY

if [[ ! -f "$VENV/bin/activate" ]]; then
  python3.12 -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126
python -m pip install --no-cache-dir -r requirements-study2-qwen3.txt
python -m pip check

python - <<'PY'
import torch
from exception_continuation.qwen3 import dependency_versions
print(dependency_versions())
assert torch.__version__.split('+')[0] == '2.7.1', torch.__version__
assert torch.version.cuda == '12.6', torch.version.cuda
assert torch.cuda.is_available(), 'CUDA is not available'
assert torch.cuda.device_count() == 1, 'This setup requires exactly one visible GPU'
assert torch.cuda.is_bf16_supported(including_emulation=False), 'Native BF16 is required'
p = torch.cuda.get_device_properties(0)
assert p.total_memory >= 75 * 1024**3, f'Insufficient GPU memory: {p.total_memory/1024**3:.1f} GiB'
print(f'GPU: {p.name}; VRAM: {p.total_memory/1024**3:.1f} GiB; PyTorch: {torch.__version__}')
PY

printf '\n--- Download pinned model and tokenizer (about 65.5 GB) ---\n'
HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 huggingface-cli download Qwen/Qwen3-32B \
  --revision "$REVISION" \
  --local-dir "$STUDY2_MODEL_DIR" \
  --include '*.safetensors' '*.json' merges.txt vocab.json LICENSE README.md

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
mkdir -p runs
export STUDY2_RUN="$(mktemp -d "$REPO/runs/qwen3-32b-selection-runpod-XXXXXXXX")"
export STUDY2_CONFIG="$REPO/configs/local-$(basename "$STUDY2_RUN").json"

python - <<'PY'
import json
import os
from pathlib import Path
from exception_continuation.core import validate_config
config = json.loads(Path('configs/continuation_v3_qwen3_32b.json').read_text())
config['model_dir'] = str(Path(os.environ['STUDY2_MODEL_DIR']).resolve(strict=True))
config['device'] = 'cuda:0'
validate_config(config)
with Path(os.environ['STUDY2_CONFIG']).open('x') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
PY

git rev-parse HEAD > "$STUDY2_RUN/code-commit.txt"
python -m pip freeze > "$STUDY2_RUN/environment-pip-freeze.txt"
nvidia-smi -q > "$STUDY2_RUN/hardware-nvidia-smi.txt"
python -m exception_continuation.qwen3 \
  --model-dir "$STUDY2_MODEL_DIR" --output "$STUDY2_RUN/tokenizer-audit.json"
python -m exception_continuation prepare --phase selection \
  --config "$STUDY2_CONFIG" --output "$STUDY2_RUN"

# A non-secret shell file to recover the exact run paths in another terminal.
python - <<'PY'
import os
import shlex
from pathlib import Path
lines = [
    '# Generated preparation state: paths only, no API credentials.',
    'source /workspace/venvs/study2-qwen3/bin/activate',
    'cd /workspace/exception-pilot',
    'export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUBLAS_WORKSPACE_CONFIG=:4096:8',
    'export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1',
    'export HF_HOME=/workspace/.cache/study2-huggingface',
    'export TMPDIR=/workspace/study2-tmp',
]
for key in ('STUDY2_RUN', 'STUDY2_CONFIG', 'STUDY2_MODEL_DIR'):
    lines.append(f'export {key}={shlex.quote(os.environ[key])}')
with Path('/workspace/study2-session.env').open('x') as f:
    f.write('\n'.join(lines) + '\n')
PY

printf '\nPREPARED: %s\nNo original model responses have been generated.\n' "$STUDY2_RUN"
printf 'Next: source /workspace/study2-session.env\nThen run the separately authorized eight-response pilot.\n'
