# Offline verification: current Qwen screen v1

These files contain **no model responses**. They freeze the new design and exact tokenized requests and record offline checks. They are not a live run or evidence of a thinking effect.

- `manifest.json.gz`: all 96 rendered tables and 384 unique scientific requests, including exact prompts/token IDs, paired seeds, template arguments, sampling settings and the implementation contract.
- `shortcut-audit.json.gz`: the unchanged controlled-v2 audit applied to the new final rendered tables, including target-excluded nuisance associations and shortcut baselines.
- `verification.json`: content hashes, model/tokenizer identity, exact token counts and counterbalance summaries.
- `targeted-tests.log.gz`, `full-offline-tests.log.gz` and `legacy-dependency-retest.log.gz`: captured unittest output. `test-results.json` records commands, counts, skips and hashes.

The manifest has **217,328 input-token occurrences**, 550–579 per request. Each of the 384 responses is capped at 4,096 new tokens, for **1,572,864** scientific output tokens maximum. The separate smoke permits at most eight requests, bounded conservatively by another 2,048 output tokens. Its source prefixes are determined only after its four technical originals return; these are not part of the scientific manifest.

## What was checked

| Requirement | Status and evidence |
|---|---|
| 384 unique paired cells, 24 fresh layouts, source-label and eight-background-label transformations | Passed: `DesignTests`; complete manifest |
| Class/climate/profile counterbalances; target remains row 16 | Passed: generator assertions and rendered-table audits |
| No absence clause; identical instructions across modes | Passed for all 384 rendered prompts, using the real tokenizer |
| Residual shortcut correlations disclosed | Passed: no audited perfect shortcut; histogram-only in-sample upper bound 0.625 |
| Official new-model template and medium effort | Passed with the pinned real tokenizer; medium differs from low/xhigh and unsupported effort is rejected |
| Final-only scoring, contradictory thinking, strict format, EOS/truncation separation | Passed with real-tokenizer constructed strings; these are parser fixtures, not model responses |
| Exact supplied prefix IDs; unchanged source operations | Passed offline with immutable mock dispatches and real token IDs; actual GPU continuation remains untested |
| Shared settings, fixed budget, model/seed/token/source cache identity | Passed: frozen request checks and mismatch tests |
| Model loading only with pending work; one load per invocation; no load for inspect/analyze/complete cache | Passed with a mock backend only |
| First exception stops dispatch; failed/ambiguous calls held; invalid/truncated returns cached | Passed with a mock backend only |
| Exclusive lock, preserved interrupted journals and immutable export | Passed: execution-control regression tests |
| Paired contrast sign and construction-block interval | Passed on analytic outcomes; four construction clusters, with 24-world sensitivity labeled separately |
| Separate manual annotations with not-reviewed state and quote offsets | Passed: exported sheet tests; no automatic semantic labeling |
| Historical files | Preserved: no modifications to files tracked in base `f880581ed2cc29fca4f204f6b52777c6232c1c6c` |
| GPU/model loading, resolved runtime kernels, real EOS/channels/prefix behavior, memory and speed | **Not tested**; requires the separately authorized technical smoke |
| Scientific thinking effect | **Not tested**; zero scientific generations |

The focused suite has **27 tests, all passing**. Combined full-suite verification: **941 passed, 12 skipped, no unresolved failures**. The first full invocation ran 953 tests: 940 passed, 12 skipped, and one legacy test could not import `torch` to patch its GPU-query functions. Installing torch 2.11.0 in the temporary test environment and rerunning that one test resolved the import error. Both the initial failure log and passing rerun are retained; no historical code was changed. See `test-results.json` for exact commands and every skip. No new test uses a fake tokenizer. Backend mocks are limited to execution-control fixtures; design and parser checks use actual deterministic tables and the pinned Qwen3.8 tokenizer. The 27 new tests first passed in a tokenizer-only environment. PyTorch was then installed solely to resolve the legacy test import; its GPU methods were patched to fail if called. No vLLM engine or Qwen model was loaded. The complete tokenized manifest was reproduced byte-for-byte after installing torch. No model weights were downloaded.

## Reproduce and inspect offline

From the repository root, activate an environment with the pinned tokenizer dependencies. `CURRENT_QWEN_TOKENIZER_DIR` must point to local files matching `exception_study2_current/assets.json`. No automatic downloads occur.

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python -m unittest discover -s tests -p test_study2_current.py -v
python -m unittest discover -s tests -v
PYTHONPATH=. python audits/current-qwen-screen-v1/reproduce.py --tokenizer-dir "$CURRENT_QWEN_TOKENIZER_DIR" --output /tmp/current-qwen-screen-preview-new
python -m json.tool audits/current-qwen-screen-v1/verification.json
```

Use a fresh output path for reproduction. Compare content/file hashes with `verification.json`; gzip timestamps are fixed. The preview is portable and contains no Mac model paths. Prepare actual RunPod plans in fresh Linux directories using [the runbook](../../STUDY2_CURRENT_QWEN_SCREEN_RUNBOOK.md). Do not edit an already frozen plan in place.

This implementation reuses the historical table parser/audits, immutable Session, atomic writers, run lock, conservative journal recovery, repetition summaries and bootstrap code. It adds only this manifest, the new-model adapter, fixed-screen orchestration, analysis/export and associated tests. Neither the old 960-response protocol nor any result artifact is rewritten.

Static backend inspection also checked two details that differ from a plain Transformer: the pinned vLLM [model configuration hook](https://github.com/vllm-project/vllm/blob/v0.26.0/vllm/model_executor/models/config.py) reads the checkpoint's `mamba_ssm_dtype` for Qwen3.5-family architectures, and its [output processor](https://github.com/vllm-project/vllm/blob/v0.26.0/vllm/v1/engine/output_processor.py) and [detokenizer](https://github.com/vllm-project/vllm/blob/v0.26.0/vllm/v1/engine/detokenizer.py) retain generated token IDs, including stop IDs, when detokenization is disabled. These source checks support the adapter choices; they are not a substitute for the real-model smoke.
