# Explicit-explanation implementation audit

Offline acceptance completed on 22 October 2026. No new Qwen responses,
paid API calls, weight downloads, or GPU initialization occurred. This is a
preparation preview, not an experiment result. Real explanation behavior and
runtime remain untested.

The archive SHA-256 and all manifest members verified. All 1,582 sealed
members, 384 original operations, and eight smoke operations passed their
binding checks. Raw input IDs, token/text identity, EOS/finish status and
resolved sampling were checked independently of the archived analysis flags.
The target's expected class was checked against its actual table cell.
Selected original-wording controls remain 96/96 correct for OFF/direct and
96/96 for native ON under the original parser.

The preview contains exactly 96 new requests and 192 control references.
Prompts differ only in the required final suffix. They retain the source
seeds, model/tokenizer revision, native-OFF template, sampling, 4096-token
budget and engine settings. The new inputs total 54,264 tokens; the maximum
new output budget is 393,216 tokens. Historical controls and smoke responses
are not dispatchable requests.

| Check | Result | Evidence |
|---|---|---|
| New focused acceptance | 31 passed, 0 skipped | `explanation-tests.log.gz` |
| Unchanged current screen | 27 passed, 0 skipped | `current-screen-tests.log.gz` |
| Reused native journal/recovery suite | 33 passed, 3 skipped | `native-tests.log.gz` |
| Source identity, raw returns, 96/192 matching | Passed | `preview.json`, request manifest, focused tests |
| Suffix-only bytes and unchanged settings | Passed | Focused tests over all 96 requests |
| Last-line parser, EOS, structural tokens, malformed payload caching | Passed | Focused parser/execution tests |
| Four-block contrast and correct sensitivity pairing | Passed | Analytic fixture tests |
| Failure, interruption, no resampling, complete-run zero loads | Passed | Mock execution tests |
| Relocation and portable checksums | Passed | Relocated archive/export tests |
| Offline CLI prepare/inspect/run/analyze/export | Passed | `test-results.json` |
| Frozen source code contract and archive bytes | Unchanged | `preview.json` and Git diff against source commit |
| New real-model behavior and live runtime | Not tested | No live execution authorized here |

Combined: **91 passed, 3 skipped, 0 failures** across these three suites.
The skipped legacy tests need the older Qwen3-32B tokenizer, a saved v5 plan,
or its saved template. They do not skip any new acceptance test. The full
repository suite was not rerun for this isolated addition.

An initial development test exposed that the tokenizer's `all_special_ids`
omits `<|im_start|>`. The new parser now checks the entire pinned added-token
inventory, including tool/FIM/multimodal delimiters. All those markers are
covered by the final regression test. The original parser and tokenizer were
not edited.

`request-manifest.json.gz` contains all exact new requests and both matched
control references for every case. It is portable and has no runtime paths.
`preview.json` is the machine-readable, unexecuted analysis; `preview.md` is
its short report. These are not frozen RunPod execution plans. Prepare a
fresh run with its actual GPU-local paths using the runbook. Live output will
have its own plan hash and code revision.

To reproduce the audit without weights or CUDA, from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python audits/current-qwen-explanation-v1/reproduce.py \
  --tokenizer-dir "$STUDY2_MODEL_DIR" \
  --output /tmp/current-qwen-explanation-audit-new
```

Use a fresh output path. To run the selected suites with existing tokenizer
assets:

```bash
export CURRENT_QWEN_TOKENIZER_DIR="$STUDY2_MODEL_DIR"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
python -m unittest discover -s tests -p 'test_study2_explanation.py' -v
python -m unittest discover -s tests -p 'test_study2_current.py' -v
python -m unittest discover -s tests -p 'test_study2_native.py' -v
```

The original evidence stays in `results/current-qwen-screen-v1/`. A future
live export includes it unchanged, the separately bound startup log, all new
raw returns and journals, a checksum inventory, and a blank semantic review
sheet. Interpretation remains limited to this matched diagnostic; no automatic
success gate or expansion is implemented.
