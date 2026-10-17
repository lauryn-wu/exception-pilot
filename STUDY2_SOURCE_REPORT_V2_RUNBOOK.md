# Source-report v2: existing RunPod environment

This version changes only the elicitation suffix and response boundary. V1 remains
FAILED (12/12 calibration replies stopped at 16 tokens, no main calls). Its prose
observations motivated this revision and are not passing results. V2 requires all
12 new quoted-field calibrations to pass; it may still fail. No live v2 measurements
were collected during implementation.

Expected work: 12 new calibration + 332 new main short generations, with main
conditional on calibration; reuse 664 old cue readouts and all saved trajectories.
Maximum output is 5,504 tokens. Counts at k=0/256/512 remain 112/112/108, with the
same four exclusions. BF16, thinking disabled, eager attention, batch one, greedy
settings, 16-token cap and pinned original backend identity remain unchanged.

## Update code after separate publication authorization

The implementation is not pushed automatically. Use this update block only after
the v2 patch has been published on the existing branch. Use the available gh; do
not reinstall it or enter a GitHub account password.

```bash
cd /workspace/exception-pilot
if ! gh auth status --hostname github.com; then
  gh auth login --hostname github.com --git-protocol https --web
fi
gh auth setup-git --hostname github.com
GIT_TERMINAL_PROMPT=0 git fetch origin codex/study2-v5-judge-review-v2
git switch codex/study2-v5-judge-review-v2
GIT_TERMINAL_PROMPT=0 git pull --ff-only origin codex/study2-v5-judge-review-v2
```

Stop on an update error; preserve local changes. No environment reinstalls, model
downloads, old technical validation, original collections or readout reruns follow.

## Prepare once, inspect once

```bash
source /workspace/venvs/study2-qwen3/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export ORIGINALS=/workspace/study2-v5-replication-v1/originals
export LEGACY_READOUTS=/workspace/study2-v5-replication-v1/readouts-remaining-v1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
export SOURCE_REPORT_V1=/workspace/study2-source-report-v1
export SOURCE_REPORT=/workspace/study2-source-report-v2

if [ ! -f "$SOURCE_REPORT/source-report-plan.json" ]; then
  python -m exception_study2_source_report_v2 prepare \
    --originals "$ORIGINALS" --readouts "$LEGACY_READOUTS" \
    --tokenizer-dir "$STUDY2_MODEL_DIR" --v1-output "$SOURCE_REPORT_V1" \
    --output "$SOURCE_REPORT"
fi
python -m exception_study2_source_report_v2 inspect --output "$SOURCE_REPORT"
```

These commands are offline and verify local tokenizer assets without reading
weights or constructing a model. Stop on any mismatch. Expect 12 executable
calibration queries and 332 conditional main queries on a fresh plan. The required
saved hardware is `NVIDIA H100 80GB HBM3`; the original model path, dependencies,
byte hashes and backend identity must match at a necessary live load. Native old
readout journals are preferred; exported-summary validation is explicitly labeled.
The v1 output is inspected read-only for provenance. If unavailable, its reference
hash is retained and actual artifacts are explicitly unavailable, never fabricated.

Preparation refuses an already occupied output. Preserve interrupted preparation
and investigate; do not clear it or create another directory to resample. V1 and
v2 directories and caches must remain separate. An incompatible code/protocol
change fails the frozen content check; an ordinary content-compatible Git revision
change is recorded truthfully without invalidating the cache.

## Explicit live run, then stop

```bash
python -m exception_study2_source_report_v2 run --output "$SOURCE_REPORT" --live-qwen
```

This is the recommended full invocation: passing calibration and main share one
model load. Every first quoted field must be complete, valid and correct. A closing
quote can make a field valid even when generation subsequently reaches 16 tokens;
EOS is not required after the field. Whole-payload metadata must still be valid.
No quote, an empty first field, prose or a later apparent answer cannot pass.

**If calibration fails, stop and retain it.** Do not edit prompts/parser/budget or
retry returned answers. The run writes `report.json` and `report.md`; no redundant
analyze command is needed. Reports separate field completion, validity, correctness,
EOS, generation length stop, token counts and metadata errors. Raw returns retain
all trailing text, which does not alter the first field's score.

A backend exception stops dispatch immediately and preserves the failed operation.
After fixing the runtime issue, normal resume uses exactly the same command:

```bash
python -m exception_study2_source_report_v2 run --output "$SOURCE_REPORT" --live-qwen
```

Use that resume block only when needed, not as a second planned measurement.
Returned wrong/invalid/length-stopped answers, failed calls and ambiguous starts
are never resent. Only never-started work executes; unresolved calibration keeps
main blocked. A fully cached/blocked run performs zero model loads and calls.
Optional `--calibration-only` is supported but not required and would require a
second load for main. Omitting `--live-qwen` keeps run offline.

## Archive without changing either version

After the run has stopped, create a new local archive:

```bash
python -m exception_study2_source_report_v2 archive --output "$SOURCE_REPORT" \
  --archive "/workspace/study2-source-report-v2-results-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
```

This offline command locks the output, verifies its plan/journals, snapshots the
v2 artifacts, prints the archive SHA-256 and refuses an existing archive path.
It does not upload anything, delete output, archive model weights, or alter v1.
Keep the existing `/workspace/study2-source-report-v1` intact as the failed study.
No further historical experiment, judge stage or Study 2B starts from this module.

Interpretation remains explicit source recovery, possibly by rereading. It does
not prove that uninterrupted reasoning retained and deliberately overrode the
fact. Report the failed v1 calibration and pilot-informed nature of v2 alongside
any future v2 results.
