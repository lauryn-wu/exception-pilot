# RunPod: Study 2 v5, explicit stages

Do not use this runbook to resume or relabel v4/expanded-screen results. This task
only packaged code; no commands below involving `--live-qwen` were executed.
Use a newly deployed Pod already attached to your persistent Network Volume at
`/workspace`. No cloud launch, model download, judge request or experiment is
performed by this document. Keep the volume and all historical runs.

Recommended starting configuration: one H100 80 GB (PCIe is cost-effective),
128 GB host RAM minimum practical target, preferably 192 GB; 150–200 GB persistent
volume with at least 25 GB free after weights/environment/history. H200 141 GB
provides more memory headroom. See `STUDY2_V5_WORKLOAD_COST.md` for assumptions.
The existing serial eager BF16 backend is unchanged. No quantization, vLLM, batching,
or multiple GPUs. Freeze the actual new Pod fingerprint at validation.

## 1. Checkout and reuse the persistent pinned environment

Run small blocks individually. Stop on any error; do not paste all stages at once.
Check the volume contains the repository, environment, and pinned model first.

```bash
cd /workspace/exception-pilot
git status --short
git fetch origin codex/study2-v5-evidence-interventions
git switch --no-track -c codex/study2-v5-evidence-interventions FETCH_HEAD
source /workspace/venvs/study2-qwen3/bin/activate
python --version
python -m pip check
nvidia-smi
```

The `git switch -c` command is for first checkout; if this branch already exists,
use `git switch codex/study2-v5-evidence-interventions` and inspect its commit.
Never overwrite unrelated working changes. The environment must run Python 3.12,
torch 2.7.1+cu126, transformers 4.51.3, tokenizers 0.21.1,
huggingface-hub 0.30.2, safetensors 0.5.3, Jinja2 3.1.6, numpy 2.2.4.
A copied venv can depend on an interpreter path from the old image: if activation
or Python fails, stop and use a compatible Python 3.12/CUDA 12.6 image. Do not
silently upgrade packages or switch inference backends. The existing pinned
`requirements-study2-qwen3.txt` remains authoritative. No reinstallation/download
is needed when the preserved environment passes. New Pod driver must support
CUDA 12.6/native BF16; `nvidia-smi`'s CUDA label alone does not verify PyTorch.

```bash
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
test -d "$STUDY2_MODEL_DIR"
export V5_HOME=$(mktemp -d /workspace/study2-v5-XXXXXXXX)
export RUN_V5="$V5_HOME/selection"
printf '%s\n' "$V5_HOME" > /workspace/study2-v5-home-path.txt
python -m exception_study2_v5 configure --model-dir "$STUDY2_MODEL_DIR" --config "$V5_HOME/config.json"
python -m exception_study2_v5 prepare --config "$V5_HOME/config.json" --output "$RUN_V5"
```

No Mac paths are copied into the plan. The config points at the actual persistent
GPU-local directory. Reconnect later with:

```bash
export V5_HOME=$(cat /workspace/study2-v5-home-path.txt)
export RUN_V5="$V5_HOME/selection"
```

## 2. Offline preflight — no inference

```bash
python -m exception_study2_v5 preflight --output "$RUN_V5"
python -m exception_study2_v5 workload
```

Preflight verifies dependencies, local tokenizer hashes/EOS settings and exact v5
prompt-template roundtrips, including the original empty thinking block. It checks
weight filenames/sizes, without loading weights or running CUDA. Full weight hashes,
native BF16, GPU/driver, model parameters, greedy overrides and model behavior are
checked by the explicit loader/gate below. Offline success leaves these pending.
The model weights total 65.52 GB (61.02 GiB); do not download a second copy.

## 3. Fresh v5 technical gate — first explicitly authorized inference

```bash
python -m exception_study2_v5 validate --output "$RUN_V5" --live-qwen
```

**STOP on exception, failed gate, or any status other than
`V5_SAME_INPUT_PASSED`. Do not collect scientific responses.** Preserve the whole
run, especially `technical-v5.json`, `technical-status-v5.json`, `execution-v5.json`,
`operations-v5/`, and `timing-v5/`. Never delete journals to retry. Maximum 33
technical calls/3882 generated tokens; short outputs can reduce this. First model
loading/hash verification may take minutes; see timing artifacts. Scientific
collection checks the genuine journals, not just a status flag. V4 success is not
accepted as evidence for this new Pod.

## 4. Four-world pilot only, then stop

Only after the technical gate passes:

```bash
python -m exception_study2_v5 collect --output "$RUN_V5" --live-qwen
python -m exception_study2_v5 summary --output "$RUN_V5"
python -m exception_study2_v5 timing --output "$RUN_V5"
```

Exactly the first four frozen worlds: 32 originals (16 direct/16 visible), each
budget 2048, no probes or judges. No threshold/prompt edits after inspection.
**STOP.** Continue only by separately deciding to finish the frozen selection.

## 5. Explicitly finish selection, summarize, then stop

```bash
python -m exception_study2_v5 collect --output "$RUN_V5" --complete --live-qwen
python -m exception_study2_v5 summary --output "$RUN_V5"
```

Reuses the first 32; at most 64 additional originals. Failed/ambiguous originals
are preserved as unavailable, not replaced. `behavioral-summary-v5.json` reports
strict/tolerant outcomes, matched errors, missingness, unknown bounds, both framings
and calibration. Calibration failure stops confirmation; it is a valid null result.
It never proves sufficient erasure/override coverage.

## 6. Offline independent annotations

```bash
export REVIEW_V5="$V5_HOME/review"
python -m exception_study2_v5 prepare-review --source "$RUN_V5" --output "$REVIEW_V5"
```

`review-plan-v5.json` contains blinded views of every visible response and the rubric.
Give each reviewer only their view and blank template. Copy templates to
`reviewer-1.json` and `reviewer-2.json`; each independently fills a named reviewer ID,
all event decisions, exact Python/Unicode code-point `[start,end]` spans, exact text,
40-character `before`/`after` anchors, subtypes, rationale and certificates.
Offsets refer to `pre_answer_text`, never the prompt. Use `null` span/text/anchor/
subtype for absent, uncertain, excluded and invalid events. Blank/unreviewed values
cannot freeze. A reconstructed-cell event can span only `?`/blank/unknown with the
unique complete row context in its anchor. Human semantic review is mandatory;
no paid judge integration is automatically invoked. Negative decisions are data.

```bash
python -m exception_study2_v5 freeze-annotations --output "$REVIEW_V5" --first "$REVIEW_V5/reviewer-1.json" --second "$REVIEW_V5/reviewer-2.json"
```

On disagreement this stops. Have a third independent reviewer fill the same schema
for exactly the disputed cases, with a distinct ID and the same review-plan hash.
Then rerun the command adding `--adjudication "$REVIEW_V5/adjudication.json"`.
Existing independent decisions remain in the final frozen manifest.

```bash
export ANNOTATIONS_V5="$REVIEW_V5/annotation-manifest-v5.json"
python -m exception_study2_v5 annotation-summary --source "$RUN_V5" --annotations "$ANNOTATIONS_V5"
```

### Freeze selection decisions before downstream outcomes

Write `$V5_HOME/selection-decisions.json` with reviewer, rationale,
`criteria_unchanged: true`, `no_selection_on_2a_or_interventions: true`, and
`families: {"M": true/false, "O": true/false}`. Decisions concern predeclared selection
calibration/annotation coverage, never observed intervention effectiveness. A family
with inadequate coverage must remain false; do not relax criteria to enable it.
Freeze this before analyzing intervention outcomes or starting confirmation.

```bash
python -m exception_study2_v5 freeze-lock --source "$RUN_V5" --annotations "$ANNOTATIONS_V5" --decisions "$V5_HOME/selection-decisions.json" --output "$V5_HOME/selection-lock.json"
```

## 7. Freeze one combined 2A plan, then explicitly measure

```bash
export MEASURE_V5="$V5_HOME/measurements"
python -m exception_study2_v5 prepare-measurements --source "$RUN_V5" --output "$MEASURE_V5" --annotations "$ANNOTATIONS_V5"
```

Inspect the ceiling and eligibility. Then, only when authorized:

```bash
python -m exception_study2_v5 measure --output "$MEASURE_V5" --live-qwen
```

No generated answers. At most 4032 full-candidate sequence evaluations for selection,
usually fewer because short/no-answer/missing events and deduplication reduce cuts.
`trajectory-summary-v5.json` preserves coverage and cue sensitivity. Do not use its
scores to choose events or edits. A fixed-only plan is possible without `--annotations`,
but adding events later requires a separate directory and duplicates common work.

## 8. Freeze each 2B family independently

```bash
export M_V5="$V5_HOME/interventions-M"
export O_V5="$V5_HOME/interventions-O"
python -m exception_study2_v5 prepare-edits --source "$RUN_V5" --annotations "$ANNOTATIONS_V5" --output "$M_V5" --family M
python -m exception_study2_v5 prepare-edits --source "$RUN_V5" --annotations "$ANNOTATIONS_V5" --output "$O_V5" --family O
```

For each directory copy the draft template to `drafts.json` and fill author,
proposed/excluded, rationale and the three replacements. An independent verifier
fills `verification.json`: accepted/excluded/uncertain/invalid, rationale, all
semantic checks, and each exact draft hash. Compute a draft hash with the existing
canonical `exception_pilot.core.digest`, never a hash of arbitrary JSON formatting.
For example print hashes for a completed M draft (does not certify it):

```bash
python -c 'import json,os; from pathlib import Path; from exception_pilot.core import digest; d=json.loads((Path(os.environ["M_V5"])/"drafts.json").read_text()); print(json.dumps({t:digest(v) for t,v in d["cases"].items()},indent=2))'
```

Verifier must be different from the drafter. Check complete table structure and
value-blind meaning, not only label absence. Exclude impossible edits with reasons.
Then tokenize/freeze using only existing local tokenizer assets, no weights loaded:

```bash
python -m exception_study2_v5 freeze-edits --output "$M_V5" --drafts "$M_V5/drafts.json" --verification "$M_V5/verification.json" --tokenizer-dir "$STUDY2_MODEL_DIR"
python -m exception_study2_v5 freeze-edits --output "$O_V5" --drafts "$O_V5/drafts.json" --verification "$O_V5/verification.json" --tokenizer-dir "$STUDY2_MODEL_DIR"
```

Inspect each manifest's frozen eligible/excluded cases, family and order. Preserve
insufficient clean O coverage; never pool mixed cases to claim a clean-override effect.

## 9. Explicit separate 2B execution commands

Run each only after its own manifest review and authorization:

```bash
python -m exception_study2_v5 intervene --output "$M_V5" --live-qwen
```

Stop and preserve outputs. O is a separate command:

```bash
python -m exception_study2_v5 intervene --output "$O_V5" --live-qwen
```

Every arm gets 2048-original_k tokens. Readouts and generations use independent
journals; no answer cues or future tokens enter a continuation. No original suffix
agreement gate. `intervention-summary-v5.json` reports independent contrasts,
failures, full-cohort bounds, initial outcomes, clean/mixed O and clustered intervals.

## 10. Selection decisions and held-out confirmation, separately authorized

Use the selection lock frozen after Step 6, before readouts/interventions.

```bash
export CONFIRM_V5="$V5_HOME/confirmation"
python -m exception_study2_v5 prepare --phase confirmation --config "$V5_HOME/config.json" --output "$CONFIRM_V5" --selection-output "$RUN_V5" --policy-lock "$V5_HOME/selection-lock.json"
```

Preparation does not collect. Confirmation also needs its own explicit gate and
collection commands, only after review/authorization:

```bash
python -m exception_study2_v5 validate --output "$CONFIRM_V5" --live-qwen
```

**STOP on failure.** Only after success:

```bash
python -m exception_study2_v5 collect --output "$CONFIRM_V5" --complete --live-qwen
```

384 held-out originals, no automatic review/readouts/interventions. Repeat separately
staged downstream commands with new confirmation directories. Keep the same backend
fingerprint/config. A different GPU/dependency fingerprint is incompatible with a
resume; retain old outputs and seek a newly documented run instead of editing seals.
No evidence probes, alignment control, row-position extension or other models start.
