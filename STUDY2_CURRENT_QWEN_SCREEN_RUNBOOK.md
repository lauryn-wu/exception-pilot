# Run the current Qwen native-thinking screen

This runbook is for `current-qwen-native-screen-v1`, not the old Qwen3-32B pilot/main. The implementation task does not execute the live commands below. Stop after export; there is no automatic follow-up.

Use one BF16-capable NVIDIA GPU with **80 GB VRAM**, preferably H100, and about **150 GB disk** (200 GB gives more installation/cache room), with **at least 64 GB system RAM; 128 GB preferred**. The official shards total 55,563,006,776 bytes (about 51.75 GiB), including the vision weights, although this backend uses text only. vLLM reserves up to 90% of GPU memory. This is a planning allowance, not measured peak use. A 48 GB card cannot hold these unquantized weights. H200 provides more headroom, but is not required by the configured 8,192-token context. Verify actual fit, runtime and channel behavior with smoke before scientific work. No quantization or reduced precision fallback is permitted.

Use Linux x86-64, Python 3.12 and an NVIDIA driver from the R580 series or newer as a conservative requirement for this installation. The driver must support the CUDA build reported by torch 2.11.0/vLLM 0.26.0; do not reuse an older pod solely because it ran torch 2.7.1. See the [versioned vLLM installation guidance](https://docs.vllm.ai/en/v0.26.0/getting_started/installation/gpu/) for wheel/driver compatibility. Use a fresh environment; do not upgrade the historical `study2-qwen3` environment. Runtime pins were checked against official metadata and source interfaces, but have not been run on a GPU. If installation, loading or smoke fails, stop and preserve the errors. Do not silently change pins or the model.

Paste each block separately. Commands that load weights or generate responses are explicitly labeled. Setup/model download can take minutes; loading also verifies every weight shard and may compile kernels. No download or inference occurs in inspect/analyze/export.

## 1. GitHub authentication and checkout

If the repository is already accessible, reuse its existing credentials. Otherwise, with GitHub CLI installed, use device/browser authentication:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

An existing SSH key is also suitable (`git@github.com:lauryn-wu/exception-pilot.git`). Never enter a GitHub account password into Git. Do not store a token in the clone URL, run directory, shell script or exported bundle.

For a fresh pod without `/workspace/exception-pilot`:

```bash
git clone --single-branch --branch current-qwen-native-screen-v1 https://github.com/lauryn-wu/exception-pilot.git /workspace/exception-pilot
cd /workspace/exception-pilot
git log -1 --oneline
```

For an existing checkout, inspect `git status --short` first. If there are local edits, preserve them and stop before switching. With a clean checkout:

```bash
cd /workspace/exception-pilot
git fetch origin current-qwen-native-screen-v1
if git show-ref --verify --quiet refs/heads/current-qwen-native-screen-v1; then
  git switch current-qwen-native-screen-v1
  git merge --ff-only origin/current-qwen-native-screen-v1
else
  git switch --track -c current-qwen-native-screen-v1 origin/current-qwen-native-screen-v1
fi
git log -1 --oneline
```

Do not pull or edit scientific code after preparing a run. The frozen code contract intentionally rejects changes.

## 2. Install the separate pinned environment

```bash
python3.12 --version
nvidia-smi
python3.12 -m venv /workspace/venvs/current-qwen-screen-v1
source /workspace/venvs/current-qwen-screen-v1/bin/activate
python -m pip install -r requirements-current-qwen-screen-v1.txt
python -m pip check
python -c 'import torch, vllm; print("torch", torch.__version__, "CUDA", torch.version.cuda, "vLLM", vllm.__version__); assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()'
```

Do not reuse the old torch 2.7.1 environment. PyTorch and CUDA binaries are large; installation produces progress output. A driver or wheel incompatibility is a setup failure to resolve before continuing, not a reason to substitute a model.

## 3. Download or reuse the exact revision

This is a roughly 55.6 GB model download. Run only on the intended pod after choosing storage. If the identical revision is already complete at this path, the command reuses it. Do not point to the old Qwen3-32B directory.

```bash
export CURRENT_QWEN_REV=1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0
export CURRENT_QWEN_MODEL_DIR=/workspace/models/Qwen3.8-27B/$CURRENT_QWEN_REV
HF_HUB_OFFLINE=0 hf download Qwen/Qwen3.8-27B --revision "$CURRENT_QWEN_REV" --local-dir "$CURRENT_QWEN_MODEL_DIR"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
export CURRENT_QWEN_TOKENIZER_DIR="$CURRENT_QWEN_MODEL_DIR"
```

The adapter checks all pinned small files whenever a plan is opened. Full shard SHA-256 verification happens before each actual model load; cached runs do not read weights. Downloaded files remain outside the repository and evidence directories.

## 4. Freeze fresh local plans (offline)

Use a new explicitly named directory; do not edit a Mac-prepared plan or reuse a prior failed output. Save this shell assignment so another shell can resume the same run.

```bash
export CURRENT_QWEN_RUN_ROOT=/workspace/runs/current-qwen-screen-v1-$(date -u +%Y%m%dT%H%M%SZ)
printf '%s\n' "$CURRENT_QWEN_RUN_ROOT"
python -m exception_study2_current design --output "$CURRENT_QWEN_RUN_ROOT/design"
python -m exception_study2_current prepare-smoke --output "$CURRENT_QWEN_RUN_ROOT/smoke" --tokenizer-dir "$CURRENT_QWEN_MODEL_DIR" --model-dir "$CURRENT_QWEN_MODEL_DIR"
python -m exception_study2_current prepare --output "$CURRENT_QWEN_RUN_ROOT/screen" --design "$CURRENT_QWEN_RUN_ROOT/design" --smoke "$CURRENT_QWEN_RUN_ROOT/smoke" --tokenizer-dir "$CURRENT_QWEN_MODEL_DIR" --model-dir "$CURRENT_QWEN_MODEL_DIR"
python -m exception_study2_current inspect --output "$CURRENT_QWEN_RUN_ROOT/screen"
```

The screen plan contains all 384 rendered input sequences, source tables, seeds and settings before its first generation. Input-token totals and the 1,572,864 scientific output-token ceiling are printed. It binds this separate smoke plan. All cells use a 4,096-token output cap.

Optional offline tests with the real tokenizer (no weight loads):

```bash
python -m unittest discover -s tests -p test_study2_current.py -v
```

## 5. Technical smoke — live GPU use, at most eight calls

Only this step begins generation. Four short synthetic originals cover both modes; four prefix checks follow. The prefix requests use exact saved IDs and do not claim identical sampled suffixes. All smoke operations are outside the scientific collection.

```bash
python -m exception_study2_current smoke --output "$CURRENT_QWEN_RUN_ROOT/smoke" --live-qwen --max-new 8
python -m exception_study2_current inspect --output "$CURRENT_QWEN_RUN_ROOT/smoke"
```

**Stop if smoke exits nonzero or `technical_passed` is not `true`.** Inspect `smoke/analysis.json`, `smoke/analysis.md` and immutable operations. Scientific execution independently enforces this gate, including a real versus mock distinction. Do not replace failed calls, delete journals, relax parsing or rerun in a fresh directory to hide failure. Technical failure does not become a scientific finding.

A successful smoke does not measure the experimental effect. Review timing/memory and complete traces before choosing how many scientific requests to run per invocation. This is a fixed-budget screen; truncation does not authorize changing 4,096.

## 6. Collect the screen — live GPU use

The first bounded invocation can collect 16 cells. It loads the model once, uses the passing smoke's backend identity, and prints each dispatch. It stops at the first newly raised backend exception. Returned invalid, wrong or truncated answers remain cached and collection continues.

```bash
python -m exception_study2_current run --output "$CURRENT_QWEN_RUN_ROOT/screen" --live-qwen --max-new 16
python -m exception_study2_current inspect --output "$CURRENT_QWEN_RUN_ROOT/screen"
```

Resume the **same** directory, never a new timestamp. A later invocation can request the remaining work with a ceiling of 384 new dispatches; the frozen plan prevents more than 384 scientific requests in total:

```bash
python -m exception_study2_current run --output "$CURRENT_QWEN_RUN_ROOT/screen" --live-qwen --max-new 384
```

The same command on a fully cached run loads no model. Inspection and analysis remain offline even with incomplete work. A failed/ambiguous operation is held; resume skips it and can run never-started work after the runtime problem has been addressed. The report will remain incomplete rather than replacing that sample. Preserve logs and seek forensic review for held calls. Do not assume all 384 returned merely because the command exited.

If inspect reports recognized atomic-write debris, quarantine it without resampling:

```bash
python -m exception_study2_current recover --output "$CURRENT_QWEN_RUN_ROOT/screen" --reason 'Describe the actual interruption and retain this evidence for review'
```

Quarantine preserves bytes and provenance. It does not promote temporary results or release held operations. Unknown/mismatched files require review; do not delete them.

## 7. Analyze and export — offline, then stop

```bash
python -m exception_study2_current analyze --output "$CURRENT_QWEN_RUN_ROOT/screen"
python -m exception_study2_current export --output "$CURRENT_QWEN_RUN_ROOT/screen" --destination "$CURRENT_QWEN_RUN_ROOT/screen-evidence.zip"
sha256sum "$CURRENT_QWEN_RUN_ROOT/screen-evidence.zip"
```

Use a new destination name for a later export; bundles are not overwritten. The ZIP contains checksummed requests/journals, the bound technical-smoke evidence, channel-level analysis, full traces and `manual-review.csv`. Keep the frozen design directory too: it contains the detailed final-table shortcut audit. Bundle metadata includes the full design and a regenerated audit. Copy the ZIP off the pod before terminating storage. It excludes model files, `.env`, Git credentials and arbitrary extra files.

Manual fields start `not_reviewed`. Set each independently to `present` or `absent` after reading the text; supply its supporting quote and zero-based half-open character offsets. The package is auditable offline using `bundle-manifest.json`. It does not contain inferred semantic judgments. Stop here.
