# Qwen3 Study 2 v4 RunPod runbook

This is the executable path for `study2-conditional-text-prefix-v4`. Read
[the v4 protocol](REASONING_CONTINUATION_V4_PROTOCOL.md) and
[the compatibility map](STUDY2_V4_COMPATIBILITY.md) first. The v3 audit remains a
failed **cross-path replay** test. v4 tests **identical-input fresh-prefill
repeatability** and estimates conditional textual-prefix effects.

The implementation has only been tested offline. Full-size Qwen repeatability,
behavioral calibration, eligible 2B cases and live runtimes are **PENDING**.
No confirmation, likelihood measurements, judge calls or interventions start as a
side effect of collection. Run each block separately; there is no outer heredoc.

## 1. Checkout and reuse the existing RunPod environment

The new branch is `codex/study2-conditional-prefix-v4`, based on
`bea5cc6ad01a954a13809674c31c97b49f4ecc09`. It is not published by this coding task.
Only after the reviewed v4 changes have been published with permission, fetch and
check out that branch in the existing RunPod checkout. Inspect any local changes
before switching; do not discard them or overwrite the failed v3 run.

```bash
cd /workspace/exception-pilot
git status --short --branch
git fetch origin codex/study2-conditional-prefix-v4
git switch --track origin/codex/study2-conditional-prefix-v4
```

For an already-created local v4 branch, use `git switch codex/study2-conditional-prefix-v4`
instead of the last command. Record the revision and verify the checked-out source
against the packaged acceptance source hash before preparing a run:

```bash
git log -1 --format='%H %s'
source /workspace/venvs/study2-qwen3/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
python -c 'import json; from exception_study2_v4.core import source_hash; a=json.load(open("audits/study2-v4/offline-acceptance.json")); assert source_hash()==a["v4_source_hash"]; print("v4 source hash:", source_hash())'
```

Use the existing Python 3.12 virtual environment and weights. **These commands do
not install dependencies or download models.** The unchanged dependency file is
`requirements-study2-qwen3.txt`: torch 2.7.1+cu126, transformers 4.51.3, tokenizers
0.21.1, huggingface-hub 0.30.2, safetensors 0.5.3, Jinja2 3.1.6 and numpy 2.2.4.
The existing loader verifies pinned file hashes, dependencies, BF16 parameters,
CUDA device, no quantization, greedy settings and eager attention. Stop on mismatch.

```bash
python --version
python -m pip check
nvidia-smi
python -c 'from exception_continuation.qwen3 import dependency_versions; print(dependency_versions())'
test -d "$STUDY2_MODEL_DIR"
```

One 80GB H100/A100 is the intended environment; actual v4 VRAM is not measured.
Planning allowance: approximately 61 GiB BF16 weights, roughly 65–75 GiB GPU memory
including runtime overhead at batch size 1; at least 128GB host RAM preferred for
the existing CPU-first loader. The pinned model files occupy about 66GB decimal.
A 200GB persistent workspace is a comfortable allocation for one model copy, the
existing environment and results. Full-vocabulary validation telemetry also uses
host memory and disk. These are capacity estimates, not a measured v4 benchmark.
Do not use quantization, CPU offload, multiple GPUs or a different backend to make
this protocol fit without a separately reviewed change.

## 2. Fresh machine-local configuration and plan — offline

The new configuration uses the actual GPU-local path. Do not modify any old Mac
plan or the failed RunPod plan. Keep this shell open so `RUN_V4` remains defined.

```bash
mkdir -p /workspace/exception-pilot/runs
export RUN_V4=$(mktemp -d /workspace/exception-pilot/runs/qwen3-32b-selection-v4-XXXXXXXX)
printf '%s\n' "$RUN_V4"
python -m exception_study2_v4 configure --model-dir "$STUDY2_MODEL_DIR" --config "$RUN_V4/config-v4.json"
python -m exception_study2_v4 prepare --config "$RUN_V4/config-v4.json" --output "$RUN_V4"
```

`configure` refuses to overwrite its output. `prepare` freezes the scientific
configuration, exact prompts/task order and code hashes. The template retains the
original empty thinking block. Neither command loads weights or makes a network
request. Save the printed run path; in a new terminal export `RUN_V4` to that exact
path to resume. Never create a replacement run to resample a failed operation.

## 3. Technical-only validation — explicit Qwen execution

The following command loads the local model and generates **non-scientific**
technical responses only. Budget ceiling: **33 generation operations / 3,882 new
tokens**; fewer operations if an original is too short for a planned cut. Each
fresh pair uses exactly the same IDs and `128-k` budget, with independent caches.
Full-vocabulary telemetry for this pinned model must contain 151,936 entries.

```bash
python -m exception_study2_v4 validate --output "$RUN_V4" --live-qwen
```

**STOP on any exception, `technical_same_input_passed: false`, or a status other
than `V4_SAME_INPUT_PASSED` for this live run.** Preserve the entire directory.
Do not edit statuses/tolerances or run collection after a failure. Reports can be
produced without loading a model:

```bash
python -m exception_study2_v4 selection-report --output "$RUN_V4"
python -m exception_study2_v4 timing-report --output "$RUN_V4"
```

A technical success says nothing about behavioral calibration or 2B eligibility.
Original-versus-fresh suffix differences are diagnostic and do not fail v4.
The original v3 result stays failed. Failed/dispatched/ambiguous operations cannot
be automatically resent; a re-invocation preserves their terminal status.

## 4. Eight-original timing pilot, then STOP

Run only after live technical success:

```bash
python -m exception_study2_v4 collect --output "$RUN_V4" --live-qwen --limit-originals 8
python -m exception_study2_v4 selection-report --output "$RUN_V4"
python -m exception_study2_v4 timing-report --output "$RUN_V4"
```

Expected successful state is `PAUSED`, eight originals in the original frozen
order, and `next_stage: STOP`. At most 4,096 scientific output tokens are budgeted
in this pilot. The passed technical journal is reused with no additional technical
inference. This command does not silently continue to 48. Stop and inspect outputs,
validity and measured timings. Separate invocations reload/reverify the model;
those overheads are measured separately from operation throughput. Never interpret
MOCK timings as GPU performance or add nested setup spans twice.

## 5. Explicit completion to 48 originals, calibration, then STOP

After accepting the timing pilot, resume the **same directory**:

```bash
python -m exception_study2_v4 collect --output "$RUN_V4" --live-qwen --complete
python -m exception_study2_v4 selection-report --output "$RUN_V4"
python -m exception_study2_v4 timing-report --output "$RUN_V4"
```

The eight successful originals are cache hits. Exactly 40 remaining originals are
planned, with at most 20,480 additional output tokens. Total selection: 48 originals,
24 direct and 24 visible; original output ceiling 24,576 tokens. Failed or ambiguous
requests are not resampled. An incomplete collection cannot become a review source.

Inspect `selection-report-v4.json` and `calibration-v4.json`. Direct accuracy,
matched reasoning errors, matched pattern errors, invalids, truncations, missing
responses, unknown-outcome bounds and error-world counts are separate. Preserve a
null/failed calibration. Passing requires the unchanged 20 direct correct, three
matched pattern errors and two worlds. **Passing this criterion does not establish
an eligible 2B cohort.** The independent review report supplies those case/world
counts. Stop here unless separately choosing one of the stages below.

## 6. Independent review and policy lock — explicit, separate stage

Use the existing review policy schema and provider setup described in
`STUDY2_AUTOMATED_REVIEW_RUNBOOK.md`. Do not invent a judge model or change frozen
policy. `configs/study2_review_offline.json` is disabled/unconfigured by design;
copy it to a new ignored local config, configure exact intended judge identities,
verified provider contracts/access, limits and rates before preparing a live review.
Credentials belong in environment variables, never in JSON or Git.

The six-case pilot is the same first three worlds/two variants. This offline
preparation and cache-only inspection makes **no paid calls**:

```bash
export REVIEW_V4=$(mktemp -d /workspace/exception-pilot/runs/qwen3-review-v4-XXXXXXXX)
export REVIEW_POLICY=/workspace/exception-pilot/configs/local-study2-review-v4.json
python -m exception_study2_v4.review prepare --source "$RUN_V4" --output "$REVIEW_V4" --policy "$REVIEW_POLICY" --scope pilot
python -m exception_study2_v4.review judge --output "$REVIEW_V4" --scope pilot --max-calls 42
python -m exception_study2_v4.review report --output "$REVIEW_V4" --scope pilot
```

Only when explicitly choosing to spend on judges, add `--live`:

```bash
python -m exception_study2_v4.review judge --output "$REVIEW_V4" --scope pilot --live --max-calls 42
```

Same two initial judges, conditional J3, one edit revision and independent semantic
checks; no classifier substitution. Budgets reserve per-call allowance and retain
failed/refused/ambiguous requests. Do not use mock results as semantic-quality evidence.
Constructed semantic evaluation is separate (`semantic-eval --stage detection` or
`--stage edits`) and is offline by default; explicit `--live` and configured policy
are required for actual judge calls.

After pilot review, explicitly prepare/review all 24 visible originals, then perform
local tokenizer checks and freeze the cohort. `tokenize-edits` loads tokenizer
assets only; it does not load model weights or generate responses.

```bash
python -m exception_study2_v4.review prepare --source "$RUN_V4" --output "$REVIEW_V4" --policy "$REVIEW_POLICY" --scope full
python -m exception_study2_v4.review judge --output "$REVIEW_V4" --scope full --live --max-calls 168
python -m exception_study2_v4.review tokenize-edits --output "$REVIEW_V4" --scope full --tokenizer-dir "$STUDY2_MODEL_DIR"
python -m exception_study2_v4.review freeze-edits --output "$REVIEW_V4" --scope full
python -m exception_study2_v4.review report --output "$REVIEW_V4" --scope full
```

Review detection outcomes, exact source spans, semantic exclusions, tokenizer
checks, accepted cases/worlds, pending states and unreviewed scope separately.
Zero eligible cases is a retained result, not a reason to tune prompts or rerun
originals. Human review is not implied by machine acceptance; judge annotation
quality stays `UNVALIDATED` unless independently established.

A new confirmation plan requires passed selection calibration and the exact frozen
review/model policy. This block **only prepares** confirmation; it does not collect:

```bash
python -m exception_study2_v4.review freeze-policy-lock --output "$REVIEW_V4"
export CONFIRM_V4=$(mktemp -d /workspace/exception-pilot/runs/qwen3-confirmation-v4-XXXXXXXX)
python -m exception_study2_v4 prepare --phase confirmation --config "$RUN_V4/config-v4.json" --selection-output "$RUN_V4" --policy-lock "$REVIEW_V4/policy-lock.json" --output "$CONFIRM_V4"
```

Stop for confirmation review. If later explicitly authorized, its technical gate
uses `validate --output "$CONFIRM_V4" --live-qwen`; its 96 originals require a
separate `collect --output "$CONFIRM_V4" --live-qwen --complete`. Its review must be
prepared with the identical policy and `--policy-lock "$REVIEW_V4/policy-lock.json"`.
Never pool selection and confirmation by moving files between directories.

## 7. Explicit 2A and 2B measurements — never launched by collection

Only after the relevant review/analysis decision, use the intended selection OR
confirmation source by assigning `SOURCE_V4` and its matching `REVIEW_V4`.
Selection readouts must not be used to tune policy or select an intervention effect.
Fixed 2A performs no reference/suffix generations:

```bash
export SOURCE_V4="$RUN_V4"
python -m exception_study2_v4 measure-fixed --output "$SOURCE_V4" --live-qwen
```

This writes `fixed-v4/measurements-v4.json` and `fixed-v4/summary-v4.json`. Eligible
fixed cuts are 0/32/64/128. There are at most 144 logical cue readouts / 432 complete
candidate-sequence evaluations for selection (double for confirmation); early
answers and ineligible boundaries reduce counts. No original is resampled.

Before-answer events can be frozen without any qualifying statement or edit:

```bash
export ANSWER_EVENTS_V4=$(mktemp -d /workspace/exception-pilot/runs/qwen3-answer-events-v4-XXXXXXXX)
python -m exception_study2_v4.review freeze-events --source "$SOURCE_V4" --output "$ANSWER_EVENTS_V4"
```

To include statement-aligned events, freeze a separate annotated plan. It still
retains before-answer readouts for negatives, unresolved cases and edit exclusions:

```bash
export EVENTS_V4=$(mktemp -d /workspace/exception-pilot/runs/qwen3-statement-events-v4-XXXXXXXX)
python -m exception_study2_v4.review freeze-events --source "$SOURCE_V4" --output "$EVENTS_V4" --statements "$REVIEW_V4/manifests/full-statements.json"
python -m exception_study2_v4.review measure-events --output "$EVENTS_V4" --live-qwen
```

Choose the intended event plan(s) explicitly; do not automatically measure both.
Each measurement uses frozen original cuts, without suffix replay or future tokens.
Independent event-plan costs count separately; identical cuts within a plan are
deduplicated. `before_answer` alone is at most 72 candidate sequences for selection;
three event labels are at most 216, before boundary/dedup reductions.

Once edits and exact token arrays are frozen, the explicit intervention command is:

```bash
python -m exception_study2_v4.review intervene --output "$REVIEW_V4" --scope full --live-qwen
python -m exception_study2_v4.review report --output "$REVIEW_V4" --scope full
python -m exception_study2_v4.review model-timing-report --output "$REVIEW_V4/interventions-v4/full"
```

Per eligible case: four fresh continuations, each budget `512-original_k`, and up
to 12 candidate-sequence evaluations; no original/reference reconstruction. All
arm inputs/length deltas/order are frozen. Unavailable arms affect only contrasts
using them. `unchanged` means fresh-prefix control, not restored original suffix.
The report preserves the frozen denominator, world weighting, initially-agreed
sensitivity and unknown-outcome bounds. Do not tune prompts/thresholds after effects.

## 8. Offline verification and reports

```bash
python -m unittest tests.test_study2_v4 -v
python -m unittest discover -s tests -v
python -m exception_study2_v4.demo --output /tmp/study2-v4-mock-demo-unique
```

Use a fresh demo directory. To include the optional real-tokenizer-only test, set
`QWEN3_TOKENIZER_DIR` to an existing pinned local model/tokenizer directory. Tests
never download assets. The end-to-end demo is a character-model fixture, clearly
MOCK; it deliberately diverges from original suffixes and exercises J3/revision,
eight/48 staging, readouts, event cuts and four arms.

Reports remain usable after interruption without loading a model. Timing estimates
are conditional on frozen workload/eligibility and observed LIVE stage durations;
unobserved stages and full-study runtime stay `null`. Successful cache hits add no
inference samples. Preserve `operations-v4`, telemetry, all failures and old audit
files when archiving a run; do not commit weights, caches, environments or secrets.
