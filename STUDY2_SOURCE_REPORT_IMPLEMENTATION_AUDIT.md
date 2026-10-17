# Source-report v1 implementation audit

Implemented offline on `codex/study2-v5-judge-review-v2`, based on
`237f3a395f4941fcdfa82edb63688703a3769d36`. The offline audit and frozen
preview were prepared before committing; their recorded preparation revision is
preserved, and the content contract identifies the implementation. No historical
file was edited. No live source-query results were
obtained, and no pretrained inference, paid calls, downloads or cloud work ran.

## What was reused and added

The sibling `exception_study2_source_report` package uses the historical read-only
`Source`, fixed checkpoint selection, replication readout validators, immutable
`Session.operation`, and existing backend loader/telemetry. It has its own frozen
protocol, tokenized plan, content identity, operations and output directory. It
never calls historical execution commands, including old `measure()`.

The supplied archive's 1,674 returned legacy readouts were validated once per
invocation and indexed; the new fixed population joins 664 of them. Original
first-token log probabilities are reused for preference and ABC mass. Old
whole-string scores remain sensitivity only. The new work is exclusively 12
calibration and up to 332 short source-query generations, gated and journaled.

## Actual saved-data preview

| Item | Verified count |
|---|---:|
| Remaining worlds / original-visible trajectories | 56 / 112 |
| Fixed/0, fixed/256, fixed/512 eligible contexts | 112 / 112 / 108 |
| Excluded fixed/512 cuts | 4 |
| Main source queries / existing cue entries reused | 332 / 664 |
| Calibration: source-present / genuine-MISSING | 8 / 4 |
| Total maximum new queries / generated tokens | 344 / 5,504 |
| Planned input-token occurrences | 236,974 |
| Model loads / inference calls during this audit | 0 / 0 |

The excluded cuts are `staged-v5-011/v1/original/visible`,
`staged-v5-026/v0/original/visible`, `staged-v5-027/v0/original/visible` and
`staged-v5-059/v1/original/visible`. All retain the saved reason
`short_or_at_answer_or_inexact_boundary`; no replacement cuts were introduced.

`audits/study2-source-report-v1/offline-plan.json.gz` contains the complete frozen
plan with all exact IDs, contexts and calibration edits. It is an audit artifact,
not a live run directory. `offline-preview.json` is the concise inspection view.
Prepare on RunPod with the actual sources and local paths using the runbook;
normal execution/resume always uses that same prepared output.

- Frozen offline plan hash: `2eb6c64bf5a1d7de2af005d6e115b9ccef603def620bba1710a326dd576e6de2`.
- Extension code/protocol contract: `3b391ebf5ad478fbd20e0f6bf45cfcc83cf1d820fcf6dc799d8eb7e4c84adb46`.
- Input archive SHA-256: `642fd12ae4a70be3063ff5605335fdc8aade766dde7df82dd959eb89316865da`.
- Exported measurement summary artifact hash: `b25e1bb6fa66b75e4d2a2a238b0d445e7511f26d2d278d10443a7292b9f30f7c`.
- Independently reproduced historical readout plan hash: `f0ca30685e003d5a4f9eed1aa12bc3761b74eef06c1fb2c8dd3b6ec954ab566e`.

The real input evidence mode is **exported_summary**. The archive lacks the old
readout plan and journals. The adapter verifies sealed content, population,
source-row/context/cue bindings, candidate IDs, finite per-token log probabilities
and arithmetic; it reproduces the plan hash independently. It does **not** claim
journal-level verification. Native-mode agreement and rejection of partial native
evidence passed synthetic-journal tests. Actual native journals were unavailable.

## Verification

Final targeted run: **40 tests passed, 0 failures, 0 errors, 0 skips, 39.080 s**.
This consists of 34 extension checks, including the actual archive/tokenizer test,
and six existing compatibility checks. The initial 30 extension tests also passed;
the final run followed report refinements and four additional regressions. The six
existing compatibility checks ran once. The full historical suite/pipeline was
not rerun. `audits/study2-source-report-v1/offline-tests.txt` preserves exact output.

| Requirement | Status and evidence |
|---|---|
| Historical preservation | Passed: SHA-256 equality for all 516 preexisting tracked files, all 2,108 extracted source files, and the input archive; see `preservation.json`. |
| Exact cohort, joins and exclusions | Passed with the actual archive and pinned tokenizer; synthetic inventory/tamper tests also pass. |
| Native/export evidence distinction | Passed offline; actual export validated, native path tested with synthetic immutable journals only. Missing required content and partial native evidence fail closed. |
| Saved prompt/prefix IDs and suffix | Passed; independently encoded suffix, no combined-context reencoding, no old cue, four modified-prompt renders only. Noncanonical combined BPE fixture passes without altering saved IDs. |
| Calibration construction and gate | Passed offline: 8 present + 4 deduplicated MISSING controls, empty prefixes, only the target cell changed; wrong EOS-terminated labels and unresolved calls block main. |
| Strict whole-response parsing | Passed for A/B/C/MISSING, whitespace, empty/prose/ambiguous/malformed replies, EOS and length truncation; unavailable is distinct from literal MISSING. |
| Short generation only | Passed with counting backend: exactly budget 16 and capture_at=(); score() and historical execution hooks are forbidden in extension tests. |
| One-load fresh run / zero-load resume | Passed: 344 unique mock calls and one construction, then a raising factory remains unused with zero calls/loads. |
| Partial cache, interruption and locking | Passed: request-only entries can start; failed/ambiguous calls never resend; raw-return-before-report interruption recovers offline; same-output lock blocks concurrent execution. |
| Identity and provenance | Passed: source/context/query/model/plan/code mismatch stops; ordinary HEAD changes preserve content-compatible caches and record actual dispatch revision. |
| Efficient indexing | Passed: one Evidence construction and one new-journal index per invocation; indexes updated incrementally, not rebuilt per query. |
| Legacy analysis and denominators | Passed: adversarial newline fixture chooses the first-token winner; ties/mass, returned-only accuracy, unavailable coverage and paired 108-case comparisons are explicit. |
| Reports and uncertainty | Passed: separate calibration, readable confusion/joint/paired results, natural answers distinct; fixed 2,000-draw world bootstrap preserves correlated descendants. Unfinished invocations make cumulative load accounting explicitly a lower bound. |
| Offline CLI | Passed: prepare, inspect, dry-run, run without --live-qwen, and analyze on the real source; zero model loads, calls and new operations. |
| Live calibration or main outcomes | Not tested, intentionally. All 344 new operations are never-started; calibration is PENDING. |
| Real GPU/model bytes in this environment | Not tested: only pinned tokenizer assets are present locally. The original model path, full model bytes, runtime versions and `NVIDIA H100 80GB HBM3` identity must match at live load. |

The real-data check verified seven pinned metadata/tokenizer files and prohibited
weight-shard hashing and model construction. The whole acceptance run blocked
network connections and pretrained model construction. Synthetic generations are
explicitly marked MOCK; they are not scientific results.

To reproduce the same targeted set in the existing pinned environment, set the
three local-path variables documented in the runbook, then run:

```bash
PYTHONPATH=tests:. python -m unittest -v \
  test_study2_source_report test_study2_source_report_evidence \
  test_study2_v5.DesignTests.test_cap_envelope_and_source_identity \
  test_study2_v5.OperationTests.test_failed_and_ambiguous_operations_never_retry \
  test_study2_v5.SemanticTests.test_roundtrip_boundaries_and_no_answer \
  test_study2_v5.TokenizerTests.test_pinned_v5_templates_candidates_and_no_block_reinsertion \
  test_study2_v5_staged.ReconstructionTests.test_uncued_roundtrip_exact_ids_and_readout_linkage \
  test_study2_v5_replication.AnalysisTests.test_exact_checkpoint_rules_and_aliases_unchanged
```

## Remaining limitations and stopping point

The exported archive cannot provide missing journal-level evidence. Live hardware
compatibility and the 12-control calibration remain pending; a failed gate retains
its evidence and blocks all main calls. No automatic retry, paraphrase search,
budget change, inference-server switch or backend substitution is provided.

Source accuracy measures explicit recoverability under the new suffix. It may
reflect rereading, and cannot establish uninterrupted retention, deliberate
overriding or an endogenous causal mechanism. The two old cues remain separate
analyses; no favorable-cue selection or broad newline-based confidence claim is
made. Run only the source-report commands in `STUDY2_SOURCE_REPORT_RUNBOOK.md`,
then stop; the existing experiments and Study 2B are outside this path.
