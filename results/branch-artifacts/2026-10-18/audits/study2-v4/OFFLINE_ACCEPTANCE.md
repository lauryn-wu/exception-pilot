# Study 2 v4 offline acceptance

Implemented on `codex/study2-conditional-prefix-v4`, based on `bea5cc6ad01a954a13809674c31c97b49f4ecc09`. No push or merge.
All 318 pre-existing tracked files remain byte-for-byte unchanged.

v4 source lock: `913f64efa3f12a1a787575c14c7670e072e250d7e8a3690a9957cfa70bb88e78`. Model and tokenizer:
`Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`. Configuration equals the v3
Qwen configuration; the new envelope and source contract identify v4 explicitly.

## Requirements and evidence

| Specification requirement | Status | Evidence |
| --- | --- | --- |
| New conditional-text estimand; historical v3 failure remains failed | PASSED (offline) | New protocol, versioned source contract and runbook; all prior tracked-file SHA256 hashes match the base. |
| Scientific prompts/worlds/order/roles/seeds/caps/calibration/arms/statistics preserved | PASSED (offline) | Selection and confirmation exact-object equality and prompt hashes in `offline-acceptance.json`; `test_scientific_design_and_prompts_unchanged`; independent v3/v4 four-contrast statistical equality including initially-agreed sensitivity. |
| Same-input gate; original-vs-fresh diagnostic only | PASSED (offline); QWEN NOT TESTED | `test_technical_same_input_passes_despite_original_divergence`, every failure dimension, complete-vocabulary check, false-gate rejection. At most 33 generation operations / 3,882 tokens. |
| Technical-only → eight → explicit48; immutable journals and confirmation locks | PASSED (offline) | Staging/cache/timed-parity, failed/ambiguous no-resend, policy/config/backend mismatch and confirmation-lock tests; CLI smoke. |
| 2A fresh saved prefixes, full A/B/C likelihoods, unchanged analysis and earlier-cut preservation | PASSED (offline) | Fixed-readout regression checks every request/context, summed candidate logprobs and 64-minus-0 world estimate; forced k128 failure; zero generation calls. |
| Statement/answer events independent of edit eligibility | PASSED (offline) | Negative and no-edit cases retain before-answer; deliberately edit-excluded positive retains all eligible event cuts; no reference/suffix generation. |
| Four fair fresh 2B arms; same original-k budget; independent failures; unknown bounds | PASSED (offline) | Frozen input/context/budget assertions, deliberately divergent unchanged controls, unavailable unchanged arm does not erase primary, world weighting/unknown bounds/initially-agreed tests. |
| Shared two judges/J3/revision/semantic verification/budgets/cache on genuine v4 sources | PASSED (offline); JUDGE QUALITY NOT TESTED | Adapter identity test, J3 and revision assertions, synthetic semantic evaluation with budget/cache, full mock flow. No old reader is fed fabricated v3 validation files. |
| Timing parity, CUDA sync, truthful conditional workloads and tokens | PASSED (offline); LIVE PERFORMANCE NOT TESTED | Identical scientific operations timed/untimed, fake CUDA sync order, cache-hit accounting, zero readout generations, separate teacher-forced/scientifically generated token counters, MOCK never extrapolated as LIVE. |
| Full mock pipeline and original regressions | PASSED | 515 full-suite tests; 22 targeted v4 tests; zero failures/errors/skips. Standalone smoke: 33 technical operations, eight/48 staging, 24 fixed and 24 event rows, five frozen mock cases, 20 fresh arm continuations, 29 mocked judge calls and five divergent unchanged controls. |
| RunPod CLI/runbook, compatibility map, hashes and files inventory | PASSED (offline) | `QWEN3_STUDY2_V4_RUNBOOK.md`, `STUDY2_V4_COMPATIBILITY.md`, `files.sha256.json`, CLI smoke. Actual paths configured before fresh plan; no frozen Mac plan edits. |
| Real Qwen repeatability/behavior/memory/runtime, natural 2B cohort, paid semantic quality | NOT TESTED | Intentionally no pretrained inference, paid judge calls, cloud resources or weights downloads. Pending explicit bounded execution. |

No implementation requirement remains known-failed, and no scientific-design
conflict was found. Offline success cannot establish real model feasibility.
Stop on an actual identical-input gate failure; preserve all failed/null results.

## Validation performed

- Before changes: 493 tests, 0 failures, 0 errors, 0 skips.
- Full offline suite after implementation: 515 tests, 0 failures,
  0 errors, 0 skips, 120.83 seconds on this Mac.
- Final targeted v4 suite: 22 tests, 0 failures, 0 errors,
  0 skips, 26.34 seconds. These runtimes describe tests, not Qwen inference.
- Outbound socket connections were blocked during full/targeted acceptance and
  smoke execution. V4 tests additionally forbid the pretrained loader. Existing
  legacy CPU tests may instantiate tiny random models; no pretrained Qwen ran.
- The installed, pinned tokenizer was tested offline across all 48 selection
  prompts. The official closed empty thinking block and candidate concatenation
  round trips passed. No model weights were loaded for this check.

Test commands:

```bash
PYTHONDONTWRITEBYTECODE=1 QWEN3_TOKENIZER_DIR=/path/to/existing/pinned/tokenizer python -m unittest tests.test_study2_v4 -v
PYTHONDONTWRITEBYTECODE=1 QWEN3_TOKENIZER_DIR=/path/to/existing/pinned/tokenizer python -m unittest discover -s tests -v
python -m exception_study2_v4.demo --output /tmp/new-unique-v4-mock-directory
```

The recorded acceptance runs wrapped the test runner in `unittest.mock.patch`
for `socket.socket.connect` and `socket.create_connection`, raising on any outbound
connection. Use the existing pinned environment; no asset download is part of a test.

## Changes and artifacts

23 new implementation/config/test/document files (2140
lines), plus this small audit evidence directory. No old tracked file changed.
The exact new-file SHA256 inventory is `files.sha256.json`; test logs are
`full-offline-tests.txt` and `targeted-v4-tests.txt`. Full preservation hashes,
scientific before/after hashes, dependency versions and test summaries are in
`offline-acceptance.json`. `mock-smoke.json` and `cli-smoke.json` are explicitly
synthetic software evidence, separate from scientific run outputs.

The local v4 commit contains this evidence; its SHA is returned with the implementation.
No result from the failed v3 run is relabeled. No paid calls, pretrained Qwen runs,
weights downloads, Pod launches, pushes, evidence probes or factual-question
extensions were performed or added.
