# Run the 96-response explicit-explanation follow-up

Use the existing RunPod checkout and venv. This adds 96 new responses; the
192 controls and eight smoke returns are already in the source archive.
It uses the same model files and pinned dependencies as the completed screen.
Do not reinstall packages or download weights for this follow-up.

The commands below are for execution by the operator. Implementation and
acceptance testing do not run them. If the new branch has not been published,
first run this in the **development checkout**, not RunPod:

```bash
git push -u origin codex/current-qwen-explicit-explanation-v1
```

On RunPod, use a fresh terminal. Paste each block separately. Keep the existing
RTX PRO 6000 Blackwell environment that passed the original smoke; backend
identity changes stop generation rather than scheduling another smoke.

## 1. Check out the implementation and use the existing environment

```bash
cd /workspace/exception-pilot-current-qwen-screen-v1
git status --short --branch
```

If there are local modifications, preserve them before switching branches.
Then:

```bash
git fetch origin codex/current-qwen-explicit-explanation-v1
git switch --track origin/codex/current-qwen-explicit-explanation-v1
source /workspace/venvs/current-qwen-screen-v1/bin/activate
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER=0
python --version
python -m pip check
python -c 'from exception_study2_current.adapter import check_versions; print(check_versions(live=True))'
```

If this local branch already exists, use
`git switch codex/current-qwen-explicit-explanation-v1` instead of `--track`.
Do not pull later code changes into an already frozen experiment. Record
`git rev-parse HEAD` alongside the run. The plan also freezes the code contract.

## 2. Derive the existing model path and prepare offline

```bash
export EXPLANATION_SOURCE="$PWD/results/current-qwen-screen-v1/screen-evidence-20261022T214422Z.zip"
export STUDY2_MODEL_DIR="$(python -c 'import json,os,zipfile; z=zipfile.ZipFile(os.environ["EXPLANATION_SOURCE"]); print(json.loads(z.read("locations.json"))["model"])')"
test -d "$STUDY2_MODEL_DIR"
export EXPLANATION_RUN=/workspace/runs/current-qwen-explicit-explanation-v1
python -m exception_study2_explanation prepare --source "$EXPLANATION_SOURCE" --output "$EXPLANATION_RUN"
python -m exception_study2_explanation inspect --output "$EXPLANATION_RUN"
```

Preparation derives **both** model and tokenizer paths from the archived
configuration. It verifies the pinned tokenizer/config bytes, all source
checksums and journal bindings, and the eight smoke records. It freezes
96 requests (54,264 input tokens; at most 393,216 output tokens) and 192
control references. It copies source evidence without rewriting its paths or
sealed contents. The new output must be fresh. If it already contains a plan,
inspect/resume that plan rather than preparing over it.

If the same pinned assets were relocated, explicitly supply the actual paths
with `prepare --tokenizer-dir ACTUAL_TOKENIZER_DIR --model-dir ACTUAL_MODEL_DIR`.
For offline inspection of a moved run or extracted export, pass
`--tokenizer-dir ACTUAL_TOKENIZER_DIR`; no old RunPod filesystem or weights
are required. Tiny pinned tokenizer/config assets are required for independent
raw token verification. Do not edit sealed paths in historical artifacts.

Stop if preparation or identity checks fail. Do not change model versions,
thresholds, the frozen request population, or the smoke evidence to proceed.

## 3. Run the complete fixed experiment

This is the only command below that loads the GPU model:

```bash
python -u -m exception_study2_explanation run --output "$EXPLANATION_RUN" --live-qwen
```

It checks model shard hashes, loads the model once, and dispatches up to the
remaining 96 requests. Initialization may be quiet between model-library
messages. The runner prints each dispatch and return. There is no extra
calibration or smoke call. A deliberately bounded first invocation may add
`--max-new 8`; those eight count toward the same 96, not a separate pilot.
The default is the full fixed run in one invocation.

On a backend exception, stop and resolve the runtime problem. The invocation
stops after the first failed call, and its journal is retained. Inspect first:

```bash
python -m exception_study2_explanation inspect --output "$EXPLANATION_RUN"
```

Once the runtime problem is resolved, the **same run command** resumes only
never-started requests. Wrong, invalid and truncated returns are cached.
Failed and ambiguous attempts stay held and cannot be replaced automatically;
the report remains incomplete if any are unavailable. An all-returned run exits
without a model load. Explicit recovery, only when inspection reports debris:

```bash
python -m exception_study2_explanation recover --output "$EXPLANATION_RUN" --reason 'Describe the inspected interruption and why these temporary files are being quarantined'
```

Recovery only quarantines evidence. It does not retry, certify, or promote an
ambiguous attempt. Do not delete journals to make a request run again.

## 4. Analyze, export, and stop

```bash
python -m exception_study2_explanation analyze --output "$EXPLANATION_RUN"
export EXPLANATION_EXPORT="/workspace/runs/current-qwen-explicit-explanation-v1-evidence-$(date -u +%Y%m%dT%H%M%SZ).zip"
python -m exception_study2_explanation export --output "$EXPLANATION_RUN" --destination "$EXPLANATION_EXPORT"
```

Read `analysis.md` and `analysis.json` in the run directory. The ZIP contains
new raw token/text returns, complete source evidence, matched controls,
checksums, `explanation-traces.txt`, and `manual-review.csv`. All five semantic
annotations start as `not_reviewed`; indicators may overlap. Correct final
answers and the presence of preceding text are reported separately.

Stop here. This protocol authorizes exactly 96 new responses. It does not
launch judges, probes, another arm, or an expanded run.

## Offline regression command

With the pinned tokenizer assets already present, from the repository root:

```bash
export CURRENT_QWEN_TOKENIZER_DIR="$STUDY2_MODEL_DIR"
python -m unittest discover -s tests -p 'test_study2_explanation.py' -v
python -m unittest discover -s tests -p 'test_study2_current.py' -v
```

Generation is mocked. The tests do not download weights or initialize CUDA.
