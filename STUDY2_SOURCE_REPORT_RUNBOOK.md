# Source-report follow-up v1

This additive module asks the saved Qwen trajectories a short, explicit question
about the target's recorded Verified class. It joins the response to the two
already measured original-question cues at the same prefix. It does not rerun
reasoning, candidate scoring, technical validation, judging or Study 2B.

The protocol is frozen in `STUDY2_SOURCE_REPORT_V1_PROTOCOL.md`. Every operation
uses saved prompt/prefix IDs plus the independently tokenized literal suffix, a
16-token greedy budget, BF16, eager attention, batch one and thinking disabled.
Only four changed-table calibration prompts are rendered anew. Real source-query
behavior and the calibration gate have **not** been tested by this implementation.

## Expected scope

| Item | Count |
|---|---:|
| Remaining worlds / original-visible trajectories | 56 / 112 |
| Eligible main contexts at 0 / 256 / 512 tokens | 112 / 112 / 108 |
| Main short generations | 332 |
| Existing cue entries reused | 664 |
| Pilot calibration: source-present / literal-MISSING | 8 / 4 |
| Maximum new generations / generated tokens | 344 / 5,504 |
| Planned input-token occurrences for the supplied snapshot | 236,974 |
| Fresh invocation backend loads / completed-cache loads | at most 1 / 0 |

These are bounds, not elapsed-time or cost estimates. Timing is recorded within
the planned calls; no benchmark calls are added. The four excluded fixed/512 cuts
are worlds 011/v1, 026/v0, 027/v0 and 059/v1. The frozen plan records their reasons.

## Existing RunPod checkout and files

Use the checkout containing this patch and the existing environment/model files.
Do not reinstall dependencies, download weights, or repeat old experiment stages.
These commands are supplied for a later explicitly chosen live run; none were
executed against a GPU during implementation.

```bash
cd /workspace/exception-pilot
source /workspace/venvs/study2-qwen3/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export ORIGINALS=/workspace/study2-v5-replication-v1/originals
export LEGACY_READOUTS=/workspace/study2-v5-replication-v1/readouts-remaining-v1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
export SOURCE_REPORT=/workspace/study2-source-report-v1
```

Confirm those source paths refer to your existing run. The model path is the
original frozen configuration's path. Inspect reports the exact required device,
hardware and versions, plus missing model files, without reading weight shards or
initializing CUDA. The supplied snapshot requires `NVIDIA H100 80GB HBM3`. Actual
weight hashes and full backend identity are verified once when live work requires
a load. A different backend is an incompatibility, not permission to rewrite the
historical plan. An offline Mac audit with tokenizer-only assets does not certify
that the RunPod model files or GPU are present.

Prepare **once**, in the separate new output, using the actual RunPod sources.
Do not copy/edit a Mac-specific frozen locations file. If this output already has
a plan, skip preparation and inspect/resume it. A new directory is never a remedy
for a failed or ambiguous call.

```bash
python -m exception_study2_source_report prepare \
  --originals "$ORIGINALS" --readouts "$LEGACY_READOUTS" \
  --tokenizer-dir "$STUDY2_MODEL_DIR" --output "$SOURCE_REPORT"
python -m exception_study2_source_report inspect --output "$SOURCE_REPORT"
python -m exception_study2_source_report dry-run --output "$SOURCE_REPORT"
```

**Stop on any preparation/content mismatch.** Expect exactly 12 executable
calibration queries and 332 main queries conditional on calibration. Native
readout journals are preferred. If only the sealed exported summary exists, the
module labels it `exported_summary`, checks its source/context/cue/token/probability
content, and records whether the historical plan hash was independently
reproduced. It never fabricates journals. This implementation validated the
provided export and independently reproduced that hash; native mode was tested
using synthetic journals, not the missing real journals.

The following explicit live command is also the normal resume command:

```bash
python -m exception_study2_source_report run --output "$SOURCE_REPORT" --live-qwen
```

It loads once only if work is executable, runs uncached calibration, and starts
main queries only if all 12 controls terminate with exactly the correct label.
**If calibration is FAILED or unresolved, stop.** Keep the directory and raw
returns; do not change the suffix, budget, model, gate or output to try again.
Wrong, verbose and truncated returns are cached. Failed/ambiguously started calls
are never automatically resent. Request-only calls may execute. Other genuinely
never-started main queries may finish during normal resume. A fully cached or
blocked invocation exits without model construction, shard hashing or inference.

Optional inspection before any main work uses the same directory and command with
`--calibration-only` added. It is not required and a later main invocation needs a
second model load. `run` without `--live-qwen` is offline.

```bash
python -m exception_study2_source_report analyze --output "$SOURCE_REPORT"
```

Then stop. `report.json` and `report.md` are atomically replaceable derived reports;
`source-report-plan.json`, `operations-v5/`, `operation-execution/`, and invocation
records retain immutable content/provenance. Partial coverage is supported. The
parser accepts only EOS-terminated whole-response A/B/C/MISSING after stripping
whitespace. All returned invalid/truncated responses count as incorrect; unavailable
operations are excluded from accuracy and reported as missing coverage.

The primary legacy preference uses only saved class-token log probabilities.
Newline-inclusive scores remain labeled sensitivity; ABC mass and exact ties are
reported separately. Paired analyses use the same trajectories and resample whole
worlds. The saved natural answer is a separate outcome. Correct source reporting
shows recovery under this query, possibly by rereading the table; it does not show
uninterrupted retention, deliberate overriding or an endogenous causal mechanism.

## Offline verification

Use the existing pinned environment and locally cached tokenizer. Set
`QWEN3_TOKENIZER_DIR`, `STUDY2_SOURCE_REPORT_ORIGINALS` and
`STUDY2_SOURCE_REPORT_READOUTS` to include the saved-data acceptance test; otherwise
that one test explicitly skips. No downloaded model or CUDA is needed.

```bash
python -m unittest discover -s tests -p 'test_study2_source_report*.py' -v
```

The counting-backend test asserts 344 calls and one construction on an empty
cache, then zero calls and zero constructions with a factory that raises if used.
The implementation audit records the focused suite plus the six relevant existing
source/tokenizer/readout compatibility checks; the historical full suite and
scientific pipeline were not rerun.
