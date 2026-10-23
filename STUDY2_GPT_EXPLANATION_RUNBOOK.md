# Run the GPT matched explanation experiment on a laptop

This uses the existing 96 inputs for 192 fresh API responses. It does not need RunPod, a GPU, Qwen weights, a tokenizer, an OpenAI SDK or the Qwen explanation run. The package uses Python's standard library; Python 3.12 is the tested version. Official parameter support was checked, but no live API request was made during implementation.

Use the working follow-up checkout containing this commit. The local checkout below is on `codex/current-qwen-explicit-explanation-v1`. If moving to another laptop, copy or check out that same commit before preparing a plan. Do not update code during a frozen run.

## 1. Install the local environment

```sh
cd /Users/laurynwu/.codex/worktrees/study2-audit-fixes/exception-pilot
python3.12 -m venv "$HOME/.venvs/study2-gpt-explanation"
source "$HOME/.venvs/study2-gpt-explanation/bin/activate"
python --version
git log -1 --oneline
```

No `pip install` is required. Optional offline tests:

```sh
python -S -m unittest discover -s tests -p 'test_study2_gpt_explanation.py' -v
```

## 2. Prepare and inspect offline

```sh
export GPT_RUN="$HOME/study2-runs/gpt-explanation-v1-$(date -u +%Y%m%dT%H%M%SZ)"
python -m exception_study2_gpt_explanation prepare \
  --source results/current-qwen-screen-v1/screen-evidence-20261022T214422Z.zip \
  --output "$GPT_RUN"
python -m exception_study2_gpt_explanation inspect --output "$GPT_RUN"
```

Expect 192 pending requests, 96 matched pairs, zero completed GPT responses and zero Qwen outputs reused. The original archive is copied into the new run, and its absolute historical paths are never opened. Preserve this directory. For a new shell, set `GPT_RUN` to this same directory to resume; do not run `prepare` again. `run` without its live flag is also an offline preview.

## 3. Set the key in this shell, then opt in to the run

This prompts without displaying the key and does not write a credential file in the repository. Do not use a shell with tracing enabled.

```sh
export OPENAI_API_KEY="$(python -c 'import getpass; print(getpass.getpass("OpenAI API key: "))')"
```

The next command makes paid requests. Start with four of the scheduled 192 if you want to check timing. These are scientific responses in the main plan, not extra smoke calls.

```sh
python -m exception_study2_gpt_explanation run \
  --output "$GPT_RUN" --live-openai --max-new 4
python -m exception_study2_gpt_explanation inspect --output "$GPT_RUN"
```

Each call prints `Dispatching` and then `Returned` when a non-infrastructure response is received. A single response may take some time; the transport timeout is 180 seconds. Four calls are not enough to interpret the experiment. They do provide measured elapsed time and any reported usage in the saved journals.

## 4. Resume the same plan

```sh
python -m exception_study2_gpt_explanation run \
  --output "$GPT_RUN" --live-openai --max-new 192
```

This executes only the remaining never-started requests. It cannot exceed the 192-request plan. Returned wrong, invalid, refused or truncated answers stay cached. A complete resume makes zero calls and does not require an API key.

**On an infrastructure failure, stop and inspect the error and saved raw response before resolving the runtime problem.** The invocation stops after the first newly raised failure; later requests remain never-started. A later resume can execute those later requests but cannot resend the failed or ambiguously interrupted call. Failed/ambiguous cases remain visible and prevent a complete scientific result. Do not delete journals, create replacement attempts, or prepare a new run just to replace an unfavorable result.

If inspection reports recognized atomic-write debris, an optional offline quarantine is available:

```sh
python -m exception_study2_gpt_explanation recover \
  --output "$GPT_RUN" --reason 'Interrupted local atomic write; preserve the held call without resending it.'
```

This preserves debris and holds ambiguity; it does not retry or promote a temporary response. Other corruption requires inspection rather than an automatic repair.

## 5. Analyze, export, stop

```sh
python -m exception_study2_gpt_explanation analyze --output "$GPT_RUN"
python -m exception_study2_gpt_explanation export \
  --output "$GPT_RUN" --destination "${GPT_RUN}-evidence.zip"
unset OPENAI_API_KEY
```

The export destination must be fresh and outside the run directory. It contains frozen source evidence, requests and journals, full raw API responses, model identities, usage, analysis, traces, and a manual-review CSV. Semantic fields begin as `not_reviewed`. Inspection and export also work before any live calls and label the run incomplete.

Inspect `analysis.md` for the paired contrast and `analysis.json` for categories, uncertainty, unscorable pairs and detailed accounting. Prices are dated assumptions, not a spending guarantee. The maximum short-context output charge is $7.86432 plus input/cache charges; actual cost depends on usage. Missing usage or unknown billing details remain unknown. No result establishes a mechanism automatically, and `reasoning.effort=none` is an API setting rather than proof of no internal reasoning.

Stop after these 192 requests. This workflow does not launch Qwen, judges, confirmation or other Study 2 experiments.
