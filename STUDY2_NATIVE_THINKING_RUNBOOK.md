# Native-thinking draft: existing RunPod environment

Review the design and pushed revision before authorizing any live run. No model was run during
implementation. Commands below use the existing checkout/venv/assets. Do not rerun historical
experiments, edit frozen plans, change a frozen cohort cap after its outcomes, or overwrite existing output directories.

## Setup

```bash
cd /workspace/exception-pilot
git status --short --branch
git fetch origin refs/heads/codex/study2-native-thinking-draft:refs/remotes/origin/codex/study2-native-thinking-draft
```

```bash
if git show-ref --verify --quiet refs/heads/codex/study2-native-thinking-draft; then git switch codex/study2-native-thinking-draft; else git switch --track -c codex/study2-native-thinking-draft origin/codex/study2-native-thinking-draft; fi
git merge --ff-only origin/codex/study2-native-thinking-draft
source /workspace/venvs/study2-qwen3/bin/activate
```

Stop on Git errors and preserve local changes. If authentication expires, use `gh auth login`
with GitHub.com, HTTPS and its browser/device flow, then `gh auth setup-git`; never an account
password. No reclone/reset/clean is needed. Reuse the environment pinned in
`requirements-study2-qwen3.txt` (torch 2.7.1 CUDA 12.6, transformers 4.51.3, tokenizers 0.21.1,
huggingface-hub 0.30.2, safetensors 0.5.3, Jinja2 3.1.6, numpy 2.2.4). No new live dependencies.
If those assets are absent, stop and arrange setup separately; these commands do not download weights.

```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
export V5_PLAN=/workspace/study2-v5-replication-v1/originals/plan-v5.json
export NATIVE_DESIGN=/workspace/study2-native-controlled-design-budget-review-v1
export NATIVE_RUN=/workspace/study2-native-controlled-pilot-budget-review-v1
export NATIVE_MAIN=/workspace/study2-native-controlled-main-budget-review-v1
```

## Offline generator audit and draft manifest

```bash
python -m exception_study2_native audit --v5-plan "$V5_PLAN" --output /workspace/study2-native-generator-audit-v1
python -m exception_study2_native design --kind controlled-draft --output "$NATIVE_DESIGN"
```

Review `generator-audit.json`, `design.json`, `constraints.json` and `sample-tables.md`.
The controlled draft has 960 responses (64 pilot, 896 main), with 13-row final tables and
exact class-independent distractor profiles. This is a proposed scientific change, not historical v5.
The manifest freezes every cell, full prompt, expected class and deterministic schedule/seed.

## Offline tokenizer preparation and inspection

```bash
python -m exception_study2_native prepare --design-dir "$NATIVE_DESIGN" --tokenizer-dir "$STUDY2_MODEL_DIR" --model-dir "$STUDY2_MODEL_DIR" --output "$NATIVE_RUN"
python -m exception_study2_native inspect --output "$NATIVE_RUN"
```

**Stop on any failure.** Preparation freezes only the 64 pilot requests, validating their exact
real-tokenizer contexts and the actual
thinking-mode template switch; it never reads/hashes/loads model weights or initializes CUDA.
Review `plan.json` and `contexts/` before live use. Prepare only once. If this output already exists,
inspect/resume it unchanged; do not create another output to resample returned answers.

## Separately authorized small live pilot

```bash
python -m exception_study2_native run --output "$NATIVE_RUN" --scope pilot --max-new 16 --live-qwen
```

This executes at most the first world's 16 cells and loads once only when work exists. Both
modes use BF16, the same sampler (0.6 / 0.95 / top-k 20 / min-p 0), and a 4,096-token cap.
This cap is provisional for the pilot, not frozen for main. The model generates native scratchpad text in thinking mode. No larger-budget retries occur.
Stop and review the outputs; the command does not advance to the remaining pilot or main.

## Resume and analyze

After review/authorization, the same command resumes the next at-most-16 never-started pilot
cells, not the already completed first world. To collect the remainder of the fixed four-world
pilot in one invocation, explicitly request this bound:

```bash
python -m exception_study2_native run --output "$NATIVE_RUN" --scope pilot --max-new 64 --live-qwen
python -m exception_study2_native analyze --output "$NATIVE_RUN"
```

There are only 64 pilot cells in total; completed cells are reused. `analysis.json` contains counts,
raw/parsed results, condition accuracy/validity, on-minus-off pairs and change in support-minus-conflict
penalty, with world-cluster intervals. `length_repetition` summarizes token lengths, truncation
and repeated-token windows by mode/wording/relation; each case includes raw output and its own
repetition metrics. Review the full raw traces as well. A repeated window can reflect legitimate
restatement and is not an automatic diagnosis. Truncated/malformed outputs are retained, not retried.

Backend exceptions stop the invocation. Normal resume skips failed/ambiguous attempts. Only if
the runtime issue is resolved and you explicitly authorize another attempt, first record why:

```bash
python -m exception_study2_native retry --output "$NATIVE_RUN" --cell-id 'PASTE_EXACT_FAILED_OR_INTERRUPTED_CELL_ID_FROM_ANALYSIS' --reason 'Describe the resolved runtime issue and explicit retry authorization'
```

This command makes no calls, preserves the previous attempt, and refuses completed returns.
Then use the same bounded live command. Do not remove journals or retry ordinary scientific failures.
For an externally killed invocation, the started-only operation remains ambiguous and requires
this explicit authorization; partial generated tokens not durably returned cannot be recovered.

## Stop: review pilot lengths and repetition before freezing main

The main cohort **cannot run from the pilot directory**. Do not select its budget until all pilot
requests have returned and you have inspected `analysis.json`, including `length_repetition` and
complete raw traces. Failed, ambiguous or never-started pilot cells block main preparation.
No accuracy criterion or automatic repetition threshold determines advancement.

After review, set one shared main cap and record concrete observations. These interactive prompts
avoid embedding an unreviewed default budget in a copy-paste command:

```bash
read -r -p 'Reviewed main token cap (integer, same for on/off): ' NATIVE_MAIN_BUDGET
read -r -p 'Pilot truncation/length findings by thinking mode: ' NATIVE_TRUNCATION_REVIEW
read -r -p 'Pilot repetition findings and raw-trace review: ' NATIVE_REPETITION_REVIEW
read -r -p 'Reason for this main budget after the pilot review: ' NATIVE_BUDGET_REASON
```

```bash
python -m exception_study2_native freeze-main --pilot-output "$NATIVE_RUN" --output "$NATIVE_MAIN" --budget "$NATIVE_MAIN_BUDGET" --truncation-review "$NATIVE_TRUNCATION_REVIEW" --repetition-review "$NATIVE_REPETITION_REVIEW" --reason "$NATIVE_BUDGET_REASON"
python -m exception_study2_native inspect --output "$NATIVE_MAIN"
```

This is offline. It preserves the pilot, freezes 896 main requests in a fresh directory, checks
all exact main-tokenizer contexts plus the chosen cap against the context limit, and binds the
review to the complete immutable pilot evidence. It never increases a cap automatically. Review
this main plan before separately authorizing execution. A synthetic pilot cannot unlock live main.
If a main directory already exists, inspect/resume its frozen plan; do not create a second main
plan to change the budget or obtain replacement samples. Keep the pilot directory in place:
main preparation and every main invocation verify the referenced pilot evidence there.

Only after the main budget is reviewed and frozen, the separately authorized main command is:

```bash
python -m exception_study2_native run --output "$NATIVE_MAIN" --scope main --max-new 896 --live-qwen
python -m exception_study2_native analyze --output "$NATIVE_MAIN"
```

Do not automatically run that block. Pilot and main reports stay separate; a different main cap
does not alter pilot scores. Preserve both complete directories, including operations, retry
authorizations, dispatches, invocations, plans, contexts and analyses. No activation data is
collected. **STOP_REVIEW_NATIVE_THINKING_DRAFT.**

## Optional historical-table replication (a separate experiment/output)

```bash
python -m exception_study2_native design --kind historical-v5 --v5-plan "$V5_PLAN" --output /workspace/study2-native-historical-design-v1
python -m exception_study2_native prepare --design-dir /workspace/study2-native-historical-design-v1 --tokenizer-dir "$STUDY2_MODEL_DIR" --model-dir "$STUDY2_MODEL_DIR" --output /workspace/study2-native-historical-run-v1
python -m exception_study2_native inspect --output /workspace/study2-native-historical-run-v1
```

This has 480 fresh cells (32 pilot, 448 main), all conflict. Preparation freezes only its 32
pilot requests; a separate reviewed `freeze-main` is required for its 448 main requests. It cannot estimate a support gap.
Use that output explicitly with the same run/analyze CLI if separately authorized. Never use its
thinking-on results as substitutes for thinking-on/off pairs on new controlled worlds.

## Matched sampling and historical results

Every request explicitly sets `do_sample=True, temperature=0.6, top_p=0.95, top_k=20, min_p=0`.
The per-request seed is part of request identity and is applied to CPU/CUDA RNGs before each call;
matched on/off pairs share that seed. The historical greedy `LocalBackend.generate` is not used.
Qwen recommends temperature 0.7 and top_p 0.8 (with top_k 20, min_p 0) for non-thinking deployment.
Our primary comparison deliberately matches the sampler, rather than optimizing each mode
separately. [Official Qwen model card](https://huggingface.co/Qwen/Qwen3-32B).
Historical greedy/visible-reasoning outputs remain separate and are never cache hits or substitutes.

## Focused offline tests

```bash
PYTHONPATH=tests:. python -m unittest -v test_study2_native
```

Optional actual-asset tests use `STUDY2_V5_PLAN` and `QWEN3_TOKENIZER_DIR`; absent assets produce
clearly labeled integration skips. Production preparation never skips tokenizer checks.
