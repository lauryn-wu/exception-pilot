# Source-report v2 offline implementation audit

Prepared on `codex/study2-v5-judge-review-v2` from reviewed baseline
`bef2c09d60107ec01f0e0b2bc54a8ff5271b178b`. This audit describes an additive working
tree; exact implementation content is identified by the frozen v2 contract.
No live v2 measurements were collected. No model weights were loaded, assets
downloaded, paid calls made, hardware provisioned, or historical experiments rerun.
Publication requires separate authorization.

## Additions and preserved inputs

New package: `exception_study2_source_report_v2/` (constants, field parser,
read-only prior provenance, integrity, planning, execution, reporting, CLI).
New protocol/runbook: `STUDY2_SOURCE_REPORT_V2_PROTOCOL.md` and
`STUDY2_SOURCE_REPORT_V2_RUNBOOK.md`. New focused test file:
`tests/test_study2_source_report_v2.py`. Frozen preview, compressed complete plan,
test log and preservation evidence are in `audits/study2-source-report-v2/`.

No preexisting tracked files changed. SHA-256 checks verified all 535 tracked
files, all 76 extracted v1 archive files and all 2,108 saved original-source files
unchanged. The v1 contract before and after is identical:
`ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d`.
The v1 package/protocol and historical/shared dependencies remain byte-identical.
V2 hashes its own code/protocol and the complete reused v1 dependency contract.

The locally available `study2-source-report-v1-results.tar.gz` was inspected
read-only, with archive SHA-256
`6e3651468dbf0b8bff0fb2ebe53867a57aeca8ca1081799816f22f15178c3190`.
Its actual plan matches the supplied reference:
`a5f38dc97c35a3ace5dfee579627aaa40599a48c482ecf63bc8eb366cbfdfc70`.
All twelve calibrations returned at the 16-token length limit, zero passed the
unchanged v1 parser, and all 332 main operations remain never-started. V1 is FAILED.
V2 provenance records SHA-256 hashes of 75 actual artifacts (excluding run.lock)
and sealed hashes where present. These are actual evidence, not fabricated
journals. The stated 8/8 present and 2/4 missing prose observations are retained
as user-reported post hoc diagnostics, never passing v1 results.

The old original-answer measurements available locally remain exported-summary
evidence; their 664 matched entries were validated/reused without rescoring.
Their independently reproduced historical plan binding is retained. V1 calibration
journal availability does not imply availability of the old answer-readout journals.

## Frozen v2 preview

- Offline v2 plan hash: `9e8292b0cfe4ad11da9bad94fb92f558f661e43aeb7ef04c9741ac2038496cba`.
- V2 contract: `163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675`.
- 56 remaining worlds, both variants, original-visible only: 112 trajectories.
- Eligible k=0/256/512: 112/112/108; all four prior exclusions preserved.
- Reuse: all saved prompt/prefix IDs, calibration table controls, 664 old cue entries,
  model/hardware identities and analysis rules. No new original generations/scores.
- New work: 12 v2 calibration calls plus 332 main calls only if all twelve pass.
- Maximum work: 344 short calls, 5,504 generated tokens, at most one model load.
- Planned input-token occurrences: 238,006, including calibration.
- Fully cached or blocked invocation: zero loads/calls.
- Current v2 state: all 344 never-started; calibration PENDING; no live results.

The compressed frozen plan is an audit artifact, not a RunPod run directory. Use
the runbook to prepare with actual RunPod source paths and native legacy evidence
where available. V2 has its own namespace, plan, journals and reports; v1 replies
are not cache hits. Existing v1 data must never be moved into the v2 operation tree.

## Focused verification

**27 tests passed in 34.025 seconds: 0 failures, 0 errors, 0 skips.** This includes
25 new v2 tests and two compatibility checks: the existing pinned-template/token
mapping test and the existing v1 persistent-failure/resume regression. This targeted
set ran once. No broad historical suite or experimental pipeline was run.

| Requirement | Evidence / status |
|---|---|
| First ASCII quote only; exact labels | Passed: A/B/C/MISSING, whitespace, EOS and length stops, wrong labels, empty first field, prose, multiple labels, curly quotes and later answers. |
| Full payload integrity | Passed: token count/budget/type, decoded text, EOS/finish, special tokens and logits; short no-EOS returns rejected even with a correct closed field. |
| Trailing text | Passed: preserved exactly as diagnostic; cannot rescue or change the first field. |
| V1 preservation | Passed: unchanged dependency contract and file bytes; actual saved verdict remains FAILED with 0/12 valid and 332 main never-started. |
| Inventory and joins | Passed on synthetic fixtures and actual saved source/pinned tokenizer: 332 contexts, 664 joins, unchanged prefixes/controls/exclusions. |
| Version isolation | Passed: distinct suffix/context/operation hashes; v1 plans and v1-namespaced journals rejected by v2. |
| Calibration gate | Passed: invalid or valid-but-wrong calibration blocks main; complete correct fields can pass after a 16-token generation length stop. |
| Single load and cached exit | Passed: fake fresh run dispatches 344 with one construction; completed resume succeeds with a factory that would raise if constructed. |
| Fail-fast and resume | Passed: after twelve good calibrations, persistent failure causes one failed main dispatch and 331 never-started; resume executes exactly those 331, preserves previous records and skips the failure. |
| Returned invalid answer | Passed: terminal cached result, does not act as a backend exception or trigger resampling. |
| Partial/ambiguous cache | Passed: request-only operation can start; ambiguous starts are skipped. |
| Durable raw recovery | Passed: interruption after durable returns and before reporting recovers without model construction/calls. |
| Content identity and locking | Passed: source/context/model/plan mismatch rejects; concurrent lock rejects; compatible HEAD change records truthful provenance. |
| Archive | Passed: locked offline snapshot, rejects existing archive path and source/output overlap; original artifacts remain unchanged. |
| Live v2 behavior | Not tested, intentionally. Passing offline tests does not establish that real calibration will pass. |

The real-data test used seven pinned tokenizer/metadata files and explicitly
forbade weight-shard hashing and model construction. Fixtures and counting backends
are labeled synthetic/MOCK. Parser tests accept a completed field after a length
stop only when all payload checks pass, including exactly sixteen generated tokens.
Reports distinguish field completeness/validity/correctness from EOS and whole
length stop; invalid/incomplete returned measurements remain in the denominator,
while unavailable operations contribute coverage missingness.

To reproduce the targeted set using only existing local assets, set
`QWEN3_TOKENIZER_DIR`, `STUDY2_SOURCE_REPORT_ORIGINALS`,
`STUDY2_SOURCE_REPORT_READOUTS` and `STUDY2_SOURCE_REPORT_V1_OUTPUT`, then use:

```bash
PYTHONPATH=tests:. python -m unittest -v \
  test_study2_source_report_v2 \
  test_study2_v5.TokenizerTests.test_pinned_v5_templates_candidates_and_no_block_reinsertion \
  test_study2_source_report.SourceReportTests.test_persistent_main_backend_failure_stops_once_and_resume_skips_it
```

If explicit tokenizer/saved-data paths are unavailable, their integration checks
skip with a stated reason; do not download assets to satisfy the tests.

## Operator handoff and limitations

The exact Git browser/device authentication, existing environment, conditional
prepare, single inspect, full run/resume and archive commands are in
`STUDY2_SOURCE_REPORT_V2_RUNBOOK.md`. No dependency reinstall, model download,
redundant analyze, repeated historical validation, or Study 2B is required.
Preparation, inspect, run without --live-qwen, and archive were exercised offline
against the saved inputs with zero model loads/calls and no v2 operation journals.

The required original hardware remains `NVIDIA H100 80GB HBM3`; real GPU/model-byte
compatibility is checked by the existing loader only if live work is executable.
Local tokenizer-only preparation does not certify live compatibility. Preserve any
failed v2 calibration; do not tune or retry it. A backend exception ends dispatch,
not the immutable failed evidence, and unresolved calibration still blocks main.

This pilot-informed change measures source-cell recovery under an explicit query.
The model may reread the table; success does not establish that uninterrupted
reasoning retained and deliberately overrode the fact or identify a causal
mechanism. Disclose the failed v1 calibration alongside any later v2 results.
