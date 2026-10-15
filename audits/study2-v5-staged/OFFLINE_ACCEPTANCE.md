# Staged v5 amendment acceptance

Base: `40d548d12ee306fe670128a8516001f4e848e053` on
`codex/study2-v5-evidence-interventions`. All implementation work is offline.
This directory supplements, and does not overwrite, the original v5 acceptance audit.
The synthetic context was generated from this amended working tree before commit;
its recorded Git HEAD is the base revision, while its v5 source hash identifies the
actual amended code and protocol. It is a demonstration, not a live run.

## Reused and preserved

The original v5 package already implemented the two framings, eight matched conditions,
2048 budgets, pinned BF16 backend/template, same-input technical gate, strict/tolerant
parsers, complete-candidate readouts, M/O independent semantic review, four-arm edits,
immutable journals, timing and world-grouped statistics. Those scientific components
remain. The 353-file pre-v5 baseline, all v3/v4 scientific files, failed validation and
Mistral artifacts remain byte-identical. No old run has been changed or relabeled.

## Changes and evidence

| Requirement | Offline result | Supporting evidence |
|---|---|---|
| One fixed 60-world schedule, 32 pilot then 448 later originals | Passed | `DesignTests`, `StagedTests.test_fixed_sixty_and_initial_four_complete_worlds` |
| Pilot stop; no outcome selection; explicit remaining approval | Passed | `test_remaining_requires_completed_pilot_review_and_no_implicit_stage`, `NullPilotTests` |
| Resume only unattempted operations, retain failed/ambiguous/invalid | Passed | `OperationTests`, `test_approved_remaining_preserves_pilot_snapshot_and_only_unattempted_calls`, `MalformedOriginalTests` |
| Identical frozen settings across batches; old plans preserved | Passed | Plan hash checks; `test_historical_plan_rejected_without_mutation` |
| Pilot downstream snapshots remain valid after remaining batch | Passed | 480-attempt mock resume test and cached pilot readouts/review |
| Source table/prompt/target/model provenance and exact token serialization | Passed | Source/journal seals, `ReconstructionTests.test_uncued_roundtrip_exact_ids_and_readout_linkage` |
| Original + fixed/event 2A + independent annotations + M/O linkage | Passed | `PipelineTests`, `EventStageTests`, pilot evidence checklist |
| Exact original uncued context; no retokenization/weights/GPU | Passed | Reconstruction tests patch tokenizer-like encode, model loader, generation and CUDA calls to fail |
| Explicit unavailable cuts; corrupt tokens/stale hashes/missing manifest rejection | Passed | `test_stale_tokens_hashes_and_malformed_checkpoints_fail`, boundary and resume corruption tests |
| Original prefixes cannot be replaced by intervention arms | Passed | `test_original_only_never_uses_intervention_arm_ids` |
| Portable references and no same-GPU requirement for offline replay preparation | Passed | Move-copy test removes old synthetic source directory; CUDA initialization/device query forbidden |
| Frozen world-disjoint splits, all descendants inherit parent world | Passed | `SplitTests`, including recorded pilot design-use contradiction rejection |
| Scientific repairs/inclusion/adaptive stopping distinction | Passed (documentation and gates) | Protocol, human checklist; changed scientific-protocol approval refused |
| No hidden activations or dense per-step scientific logits | Passed | Scientific calls use empty capture list; reconstruction metadata false; no extractor |
| Storage/counts and explicit CPU/GPU RunPod stages | Passed (planning estimates) | Workload command, runbook, storage document, pinned-tokenizer audit |
| Real v5 Qwen repeatability, peak VRAM/throughput and behavioral effects | Not tested | No Qwen weights/inference/GPU execution |
| Live semantic judge reliability, M/O prevalence and edit validity | Not tested | Manual structured imports only; no paid judge calls |
| Sample size confirmation and live pilot approval | Pending human execution | `confirm-design` and evidence-bound `approve-remaining` commands |

**Final verification: 584 tests, 0 failures, 0 errors, 0 skips; 55 v5 tests included.**
The full runner completed in 296.29 seconds.

See `full-offline-tests.txt` and `offline-results.json` for exact suite totals, timing
and failure counts. The suite blocks socket connection functions and uses only mock
backends plus existing small CPU fixtures and local tokenizer files. No models were
downloaded, no cloud resources launched, and no hidden activations collected.

V4 scientific source hash:
`913f64efa3f12a1a787575c14c7670e072e250d7e8a3690a9957cfa70bb88e78`.

## Interpretation and remaining uncertainty

Pilot data can enter the full analysis if the scientific protocol remains unchanged
and the fixed full sample is completed. Scientific modifications make affected pilot
data exploratory. Outcome-dependent stopping or world replacement invalidates naive
fixed-sample interpretation. Pilot-informed probe design excludes the pilot from held-out
evaluation. These rules do not establish adequate power or guarantee any M/O cases.

The strict code fingerprint deliberately rejects in-place resumes after code changes,
even technical ones; any migration needs its own documented compatibility review.
Offline portability does not imply live cross-GPU identity compatibility. Semantic
certifications remain fallible manual judgments. Operational review time, actual event
counts and unusually long edited prefixes remain important runtime/storage uncertainties.

## Reproduce offline acceptance

Use the existing pinned Python 3.12 environment and local tokenizer assets:

```bash
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export QWEN3_TOKENIZER_DIR="$STUDY2_MODEL_DIR"
python - <<'PYTEST'
import socket, unittest
from unittest.mock import patch
def forbidden(*args, **kwargs):
    raise AssertionError("Network forbidden during offline acceptance")
with patch.object(socket.socket, "connect", forbidden), patch("socket.create_connection", forbidden):
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover("tests"))
raise SystemExit(not result.wasSuccessful())
PYTEST
```

Tokenizers are loaded locally; pretrained Qwen weights are not. Existing legacy
tests may instantiate tiny randomly initialized CPU fixtures. No GPU experiment runs.
