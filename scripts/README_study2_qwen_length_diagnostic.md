# Qwen3 pilot generation-length diagnostic

This independent diagnostic asks whether the four visible-reasoning tasks among
the **first eight frozen v4 originals** produce valid final answers with a
2,048-token generation budget. It requires their saved original responses to have
hit the 512-token cap and the original run to have passed **real-model** v4
technical validation. It reads incomplete pilots directly, without requiring the
48-response collection.

Each response is regenerated uninterrupted **from the original rendered prompt
IDs only**. The saved 512-token response is not supplied as a prefix. The pinned
Qwen model/tokenizer, BF16, greedy settings, official template and
`enable_thinking=False` remain unchanged. The original v4 config still has its
512-token cap; only this diagnostic's explicit `generate(..., budget=2048)` differs.
The diagnostic checks the loaded backend fingerprint and re-rendered prompt IDs
against the original run before making any generation call.

This is a four-case length diagnostic, not calibration, confirmation, a new v4
collection, or evidence of false-missingness. **If the first 512 output token IDs
differ, the report states the first differing position and explicitly rejects an
exact-continuation interpretation.** Even matching prefixes are from a fresh
uninterrupted generation, with no old KV cache. Complete text is retained for
manual review; no keyword-based false-missingness classifier is applied.

## RunPod: checkout and preflight, without inference

Run these blocks separately in the existing Pod. Keep the same environment/GPU
identity used by the v4 run. Inspect local Git changes before switching; preserve
any files if Git refuses the switch.

```bash
cd /workspace/exception-pilot
git status --short --branch
git fetch origin codex/study2-qwen-length-diagnostic
git switch --no-track -c codex/study2-qwen-length-diagnostic FETCH_HEAD
source /workspace/venvs/study2-qwen3/bin/activate
```

The explicit `FETCH_HEAD` checkout also works with the earlier single-branch
clone. If this diagnostic branch already exists, use
`git switch codex/study2-qwen-length-diagnostic` instead of creating it again.
For a resumed diagnostic, keep the exact code revision recorded in its manifest.

Reuse your existing variables; **do not prepare a new v4 source run**:

```bash
: "${RUN_V4:?Set RUN_V4 to the existing eight-response v4 run}"
: "${STUDY2_MODEL_DIR:?Set STUDY2_MODEL_DIR to the existing pinned model directory}"
export RUN_V4 STUDY2_MODEL_DIR
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
test -d "$RUN_V4"
test -d "$STUDY2_MODEL_DIR"
python -c 'import os; from pathlib import Path; from exception_study2_v4.core import read_plan; assert Path(read_plan(os.environ["RUN_V4"])["config"]["model_dir"]).resolve() == Path(os.environ["STUDY2_MODEL_DIR"]).resolve(), "Model path differs from frozen source"'
```

Create a **separate** output directory and save its printed path:

```bash
export LENGTH_DIAG=$(mktemp -d /workspace/exception-pilot/runs/qwen3-length-diagnostic-XXXXXXXX)
printf '%s\n' "$LENGTH_DIAG"
python scripts/study2_qwen_length_diagnostic.py --source "$RUN_V4" --output "$LENGTH_DIAG"
```

Expected status: `PREPARED_NO_INFERENCE`. This checks the frozen source, technical
evidence and original journals, and writes the diagnostic manifest. No model is
loaded, and no network requests are made. A completed 48-response collection is
not needed. Stop on any source/provenance mismatch; do not edit a frozen source.
The actual model/tokenizer and prompt-ID checks occur again after local loading in
the explicitly opted-in command below.

## Explicitly run the four new generations

The following command executes Qwen on the Pod. **It is provided for you to run;
it was not executed during implementation.** Maximum budget is four calls and
8,192 new tokens total. It performs no extra technical generation, likelihood
scoring, judge requests, or model downloads.

```bash
python scripts/study2_qwen_length_diagnostic.py --source "$RUN_V4" --output "$LENGTH_DIAG" --live-qwen
```

Progress prints before model loading and each case. Results are saved after each
return. To resume, set `LENGTH_DIAG` to the **same** output directory and repeat the
command. Completed calls are reused. Once all four returns exist, reporting/cache
reuse does not load the model. Failed or ambiguously started calls block further
execution and are never automatically resent. Preserve and inspect such a run;
do not create another directory merely to retry or replace an outcome.

## Outputs and interpretation

- `diagnostic-plan.json`: code revision and script hash, frozen v4 source/file
  hashes, exact prompts and input IDs, old responses, model identity, settings and
  fixed four-case selection. Source/config/code changes reject incompatible resume.
- `operations/`: immutable request/start/returned/failed records, raw new text and
  generated token IDs, timing and LIVE/MOCK label. No writes enter the source run.
- `diagnostic-results.json`: expected/pattern classes; prompt/original hashes;
  token count, EOS/finish and truncation; existing `final_score` answer/correctness;
  any `ANSWER:` marker; first-512 identity and first difference (zero-based index
  and one-based position). Invalid and length-capped answers have unknown correctness.
- `diagnostic-traces.txt`: all four complete returned texts and metadata, including
  an explicit divergence warning. Missing/interrupted returns remain visible.

Reports are projections of the immutable journal and can be refreshed with the
same command **without** `--live-qwen`. Nothing is imported into the scientific
v4 collection. No results or failed v3 validation artifacts are relabeled.

## Offline tests

```bash
python -m unittest tests.test_qwen_length_diagnostic -v
```

All responses in these tests are mocks, including synthetic LIVE-shaped source
journals used to exercise the real-source gate. The diagnostic results from those
tests are labelled MOCK. No pretrained model, downloads, GPU inference or paid
providers are used. Tests cover exact task/prompt selection, 2,048-token budget,
answer/stop/prefix distinctions, source preservation, identity failures and safe
cache/interruption behavior.

Implementation verification: **14 targeted mock tests passed**, and the full
**529-test offline suite passed with zero failures, errors or skips**. Outbound
connections were blocked for the full-suite run. All 348 pre-existing tracked
files remain byte-for-byte unchanged. The v4 scientific source hash remains
`913f64efa3f12a1a787575c14c7670e072e250d7e8a3690a9957cfa70bb88e78`.
Live diagnostic outcomes remain untested until you run the explicit command.
