# Source-report measurement v1

Mode: LIVE_LOCAL; calibration: FAILED; legacy evidence: native_journals.
Plan: `a5f38dc97c35a3ace5dfee579627aaa40599a48c482ecf63bc8eb366cbfdfc70`. Backend: `a7a7eb1cd399fd4a3a74c0cee48546c6db219840c5ccc960d4c984dc04a3b1c4`.
Source hashes: {"historical_execution_hash": "3401d13fb53a22b06c69f5c97c875a0843cd592c42e943533210bdec7f02b976", "historical_revision": "07e4b6552509f955f62d234c7a9ee8a634cf649b", "legacy": {"checks": ["sealed_native_plan_execution_and_operations", "reconstructed_computation_ids", "source_row_bindings", "exact_context_ids_and_hashes", "cue_text_and_ids", "pinned_candidate_tokens", "finite_nonpositive_token_logprobs", "sequence_sums", "normalized_probabilities", "verified_pattern_log_odds", "class_token_abc_mass"], "evidence_hash": "9df350376fad7555a01e29fb93cbd808b50e472fbb9307b55d199d5319e160f9", "historical_plan_hash": "f0ca30685e003d5a4f9eed1aa12bc3761b74eef06c1fb2c8dd3b6ec954ab566e", "journal_level_verified": true, "legacy_provenance_mode": "native_journals", "plan_hash_independently_reproduced": true, "plan_reference_limit": null, "plan_reference_status": "independently_reproduced", "reconstructed_plan_hash": "f0ca30685e003d5a4f9eed1aa12bc3761b74eef06c1fb2c8dd3b6ec954ab566e"}, "pilot": {"backend_hash": "a7a7eb1cd399fd4a3a74c0cee48546c6db219840c5ccc960d4c984dc04a3b1c4", "plan_hash": "7a7ad23ac63d8c06c1e68fd2a1232f159da7f1201ac1d970a07618394cedfc22", "scope": "pilot", "source_hash": "4a9aff2291c6a99c4e770d841dd98a4812b995d46a47232c88d773d3649b925b"}, "remaining": {"backend_hash": "a7a7eb1cd399fd4a3a74c0cee48546c6db219840c5ccc960d4c984dc04a3b1c4", "plan_hash": "7a7ad23ac63d8c06c1e68fd2a1232f159da7f1201ac1d970a07618394cedfc22", "scope": "remaining", "source_hash": "e35ee9fb0e61276bddf83192c9e204b22918fa84b8575e98cb2ab0b00ea48a90"}, "technical_hash": "d8c4e297cb894e6106c58447c588ac38a229d3679c2925c94c14b70435b0980f"}
Inventory: {"calibration": 12, "calibration_missing": 4, "calibration_present": 8, "eligible_by_checkpoint": {"0": 112, "256": 112, "512": 108}, "excluded": 4, "legacy_entries": 664, "main": 332, "maximum_generations": 344, "maximum_output_tokens": 5504, "trajectories": 112}
Operations: {"all": {"ambiguous": 0, "failed": 0, "never_started": 332, "planned": 344, "returned": 12}, "calibration": {"ambiguous": 0, "failed": 0, "never_started": 0, "planned": 12, "returned": 12}, "main": {"ambiguous": 0, "failed": 0, "never_started": 332, "planned": 332, "returned": 0}}
This invocation: {"calibration_only": false, "extension_revision": "bef2c09d60107ec01f0e0b2bc54a8ff5271b178b", "model_load_attempts": 1, "model_loads": 1, "new_generations": 12, "reused_returns": 0}
Cumulative backend loads: 1 (complete accounting: True). Finished-invocation sum; a lower bound if unfinished invocations exist.
Timing: {"generated_output_tokens": 192, "recorded_finished_invocations": 1, "returned_generation_events": 12, "returned_generation_seconds": 14.3839719183743, "unfinished_invocations": 0}
Backend requirements: {"cuda_initialized": false, "missing_model_files": [], "model_dir": "/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137", "model_directory_present": true, "model_weight_bytes_checked": false, "note": "Offline metadata and file-presence inspection only. Original model bytes and full backend identity are checked by the existing loader only when there is executable live work.", "required_device": "cuda:0", "required_hardware": "NVIDIA H100 80GB HBM3", "required_versions": {"cuda": "12.6", "cudnn": 90501, "python": "3.12.3", "tokenizers": "0.21.1", "torch": "2.7.1+cu126", "transformers": "4.51.3"}}

## Calibration (pilot worlds only)

| World | Control | Expected | Operation | Reply category | Correct |
|---|---|---|---|---|---|
| staged-v5-000 | calibration_present | C | returned | truncated | False |
| staged-v5-000 | calibration_present | A | returned | truncated | False |
| staged-v5-000 | calibration_missing | MISSING | returned | truncated | False |
| staged-v5-001 | calibration_present | A | returned | truncated | False |
| staged-v5-001 | calibration_present | C | returned | truncated | False |
| staged-v5-001 | calibration_missing | MISSING | returned | truncated | False |
| staged-v5-002 | calibration_present | A | returned | truncated | False |
| staged-v5-002 | calibration_present | B | returned | truncated | False |
| staged-v5-002 | calibration_missing | MISSING | returned | truncated | False |
| staged-v5-003 | calibration_present | A | returned | truncated | False |
| staged-v5-003 | calibration_present | C | returned | truncated | False |
| staged-v5-003 | calibration_missing | MISSING | returned | truncated | False |

## Main results

| Prefix | Cue | Returned / eligible | Correct / returned | MISSING | Truncated | ABC mass mean |
|---|---|---:|---:|---:|---:|---:|
| 0 | 0 | 0/112 | 0/0 | 0 | 0 | 0.998026 |
| 0 | 1 | 0/112 | 0/0 | 0 | 0 | 0.515607 |
| 256 | 0 | 0/112 | 0/0 | 0 | 0 | 0.986712 |
| 256 | 1 | 0/112 | 0/0 | 0 | 0 | 0.318303 |
| 512 | 0 | 0/108 | 0/0 | 0 | 0 | 0.970414 |
| 512 | 1 | 0/108 | 0/0 | 0 | 0 | 0.334088 |

Unavailable measurements are excluded from accuracy and reported as coverage; invalid/truncated returned replies count as incorrect.
Both legacy cues reuse the same single source reply. Preferences use class-token log probabilities; newline-inclusive values are sensitivity only.

## Joint outcomes

Each fraction is confirmed source-correct / denominator. Eligible fractions are lower bounds while relevant source results are unavailable.

| Prefix | Cue | Wrong preference: all eligible | Wrong preference: returned conditional | Pattern: all eligible | Pattern: returned conditional |
|---|---|---:|---:|---:|---:|
| 0 | 0 | 0/112 | 0/0 | 0/112 | 0/0 |
| 0 | 1 | 0/112 | 0/0 | 0/112 | 0/0 |
| 256 | 0 | 0/112 | 0/0 | 0/112 | 0/0 |
| 256 | 1 | 0/112 | 0/0 | 0/112 | 0/0 |
| 512 | 0 | 0/108 | 0/0 | 0/108 | 0/0 |
| 512 | 1 | 0/108 | 0/0 | 0/108 | 0/0 |

Zero denominators mean unavailable, not zero accuracy. Exact preference ties are separate. Detailed confusion, preference and joint counts:

- Prefix 0, cue 0: confusion={}; categories={}; preference={"verified": 112}; joint={"verified/unavailable": 112}; source accuracy 95% interval=null.
- Prefix 0, cue 1: confusion={}; categories={}; preference={"other": 2, "pattern": 7, "verified": 103}; joint={"other/unavailable": 2, "pattern/unavailable": 7, "verified/unavailable": 103}; source accuracy 95% interval=null.
- Prefix 256, cue 0: confusion={}; categories={}; preference={"other": 1, "pattern": 6, "verified": 105}; joint={"other/unavailable": 1, "pattern/unavailable": 6, "verified/unavailable": 105}; source accuracy 95% interval=null.
- Prefix 256, cue 1: confusion={}; categories={}; preference={"other": 3, "pattern": 13, "tie": 4, "verified": 92}; joint={"other/unavailable": 3, "pattern/unavailable": 13, "tie/unavailable": 4, "verified/unavailable": 92}; source accuracy 95% interval=null.
- Prefix 512, cue 0: confusion={}; categories={}; preference={"other": 2, "pattern": 6, "verified": 100}; joint={"other/unavailable": 2, "pattern/unavailable": 6, "verified/unavailable": 100}; source accuracy 95% interval=null.
- Prefix 512, cue 1: confusion={}; categories={}; preference={"other": 6, "pattern": 13, "tie": 1, "verified": 88}; joint={"other/unavailable": 6, "pattern/unavailable": 13, "tie/unavailable": 1, "verified/unavailable": 88}; source accuracy 95% interval=null.

## Paired changes

Identical eligible trajectories at both cuts; both replies must be returned. Common world-block bootstrap draws preserve variants, checkpoints and cues.

| Cuts | Returned / eligible pairs | Source accuracy change | 95% interval |
|---|---:|---:|---|
| 0->256 | 0/112 | unavailable | null |
| 0->256, cue 0: source-correct/wrong-preference change | 0/112 | unavailable | null |
| 0->256, cue 1: source-correct/wrong-preference change | 0/112 | unavailable | null |
| 0->512 | 0/108 | unavailable | null |
| 0->512, cue 0: source-correct/wrong-preference change | 0/108 | unavailable | null |
| 0->512, cue 1: source-correct/wrong-preference change | 0/108 | unavailable | null |
| 256->512 | 0/108 | unavailable | null |
| 256->512, cue 0: source-correct/wrong-preference change | 0/108 | unavailable | null |
| 256->512, cue 1: source-correct/wrong-preference change | 0/108 | unavailable | null |

Cue sensitivity: {"0": {"contexts": 112, "contexts_with_ties": 0, "source_query_repeated_for_second_cue": false, "unique_preference_agreements": 103, "unique_preference_disagreements": 9}, "256": {"contexts": 112, "contexts_with_ties": 4, "source_query_repeated_for_second_cue": false, "unique_preference_agreements": 92, "unique_preference_disagreements": 16}, "512": {"contexts": 108, "contexts_with_ties": 1, "source_query_repeated_for_second_cue": false, "unique_preference_agreements": 92, "unique_preference_disagreements": 15}}
Saved natural final answers (separate): {"answers": {"A": 38, "B": 29, "C": 44, "None": 1}, "correct": 75, "note": "Unique original trajectories, not checkpoint queries. These are saved natural final answers, not new source-report results or conditional class preferences.", "trajectories": 112, "truncated": 1, "valid": 111}

## Excluded contexts

- staged-v5-011/v1/original/visible, fixed/512: short_or_at_answer_or_inexact_boundary.
- staged-v5-026/v0/original/visible, fixed/512: short_or_at_answer_or_inexact_boundary.
- staged-v5-027/v0/original/visible, fixed/512: short_or_at_answer_or_inexact_boundary.
- staged-v5-059/v1/original/visible, fixed/512: short_or_at_answer_or_inexact_boundary.

Correct source reporting establishes recovery under this explicit same-assistant query. The model may reread the table. It does not establish uninterrupted retention, deliberate overriding, an endogenous causal mechanism, or novelty. Source accuracy and legacy probabilities are different measurements.

See report.json for every source context, exact denominators/bounds, complete ABC mass statistics, and labeled newline-inclusive sensitivity.
STOP. No original generations, old readout reruns, judges or Study 2B are invoked.
