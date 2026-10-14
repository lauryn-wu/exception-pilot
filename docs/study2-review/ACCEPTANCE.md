# Automated-review contract: implementation and acceptance evidence

Contract: user-supplied `Study2_Codex_Patch_Prompt_With_Runtime_Pilot.md`, sections 1–10.5. This document reports offline implementation separately from public API contract inspection, real annotation quality, Qwen behavior and hardware timing. **No claim of full scientific validation is made.**

## Inspected starting state and isolation

- Worktree: `/Users/laurynwu/.codex/worktrees/study2-audit-fixes/exception-pilot`.
- Branch: `codex/reasoning-continuation-followup`.
- Inspected commit: `05a27993f2fcd6e540419dbcbbaebc8213f575f4`.
- Starting tracked diff: empty. Existing untracked `audits/` and `capability-checks/` were preserved and excluded from this commit.
- New version boundary: `exception_review`, `study2-automated-review-v1`, timing sidecar `study2-timing-sidecar-v1`. No existing scientific Python module, configuration, protocol, test, runbook or frozen source was edited. The new runbook supplements the existing executable legacy route.
- Legacy `source_hash()` before/after: `31c749811a37fc77cebd6bf6878eaa510306865347b374acc0f3099c5e261149`.
- The byte-preservation snapshot covers 57 files: legacy study package, existing audits/capability artifacts and existing frozen run files. See `preservation.json`; every listed byte hash must match. This includes all 36 entries in the failed Mistral directory. No credentials, weights or caches are part of the patch.

## Verification results

**Final: 473 tests passed (45 new methods), zero failures, zero errors, zero skips.** The full final run took 89.726 seconds; the isolated stdlib-only new suite passed all 45 tests in 22.273 seconds. The synthetic demo completed 29 mocked judge calls with five accepted edit cases and one rejected edit; none are scientific observations.

See `test-results.json` for the exact final method IDs, elapsed time, failures/errors/skips and preservation results, and `test-output.txt` for the final runner output. The baseline was **428 tests passed in 66.653 seconds**, with no failures/skips. New tests are in `tests/test_automated_review.py`; the resolver test additionally checks all 125 ordered combinations of five possible effective votes.

The first new test run exposed a wrong expected Unicode offset in the test fixture (the emoji is one Python character), which was corrected against the literal string. Integration testing also caught a missing `any_checkpoint_failed` diagnostic needed by the reused legacy event summarizer; the new adapter now supplies that existing diagnostic. No legacy assertion was deleted or relaxed. These were implementation/test corrections before acceptance, not changes to scientific criteria.

All full-suite checks blocked socket connections, used local tokenizer assets, and used no pretrained weights. Existing Qwen tests include a tiny randomly initialized CPU architecture; those test loader/greedy behavior and are not pretrained Qwen inference. The new suite and demo also run in an isolated standard-library-only environment with no torch/transformers installed. No paid calls, cloud provisioning or model download occurred.

## Requirement-to-evidence map

“Passed” below means offline software behavior verified by tests and/or preserved hashes. Live behavior is listed separately as not tested. Test names refer to `tests/test_automated_review.py` unless prefixed by an existing test module.

| Contract requirement | Status | Supporting evidence |
|---|---|---|
| §1 Inspect current worktree, preserve existing work, implement rather than only document | **Passed** | Starting SHA/status above; all additions listed in `changed-files.txt`; working CLI, real adapters, independent offline tests and runnable synthetic demo. No evidence-probing package/arms added. |
| §2 Scientific inputs, loader precision/template, checkpoints, candidates, replay gates and legacy route | **Passed** | Same legacy source hash; `preservation.json`; all original 428 tests retained/passed; existing Qwen tests unchanged. `test_eight_pause_full_gate_resume_equal_normal_legacy` compares complete collection/calibration bytes. |
| §2 Original branch point and fresh suffix budget; no original future pasted | **Passed** | `test_end_to_end_interruption_resume_adjudication_revision_rejection`, `test_payload_allowlists_and_no_future_suffix`: every arm uses 512−original k and saved input/prefix IDs, records character/token deltas, excludes future suffix. |
| §3 All visible originals, first literal marker, no normalization, allowlisted independent payloads | **Passed** | `test_missing_marker_invalid_truncated_originals_still_reviewed`, `test_source_no_marker_no_normalization`, `test_payload_allowlists_and_no_future_suffix`. |
| §3 Strict schema, unique exact quotes, Unicode/whitespace offsets, punctuation/overlap identity, invalid not negative | **Passed** | `test_alignment_unicode_whitespace_repeats_punctuation`, `test_strict_output_invalid_not_negative`, `test_wrong_source_citations_and_changed_request_are_rejected`; overlapping repeated quotes, canonically distinct Unicode, hallucinations and raw spans are checked. |
| §3 Semantic rubric and first qualifying claim | **Passed (implementation/fixtures); not tested live** | Frozen detector rubric and rubric-authored expected decisions/spans in `fixtures.py`; `test_semantic_fixtures_rubric_labels_not_canned_quality`. An aligned partial clause can still be semantically wrong; the implementation explicitly does not equate alignment with annotation quality. |
| §4 Two independent judges, exact-pair resolver, one conditional J3, pending distinct from unresolved | **Passed** | `test_exhaustive_125_combinations_and_permutations`, `test_required_table_pending_and_source_identity`, `test_default_offline_zero_calls_and_pending_not_negative`, `test_six_pilot_frozen_first_worlds_full_reuse_and_no_next_stage`, `test_all_pair_routing_and_adjudication`. |
| §5 Statement decisions separated from independent before/after boundaries and edits | **Passed** | `test_independent_before_after_cuts_no_edit_fields`, `test_separate_boundaries_integrate_without_fake_edit_metadata`. Pure boundary function takes only original row/span; no fake manual certificates or edit span. |
| §5 Source-only before-answer events; negative/unresolved/no-marker cases; rejected edits retain original events | **Passed** | `test_before_answer_without_any_review_and_source_preserved`, `test_negative_unresolved_and_boundary_states_are_separate`, `test_missing_marker_invalid_truncated_originals_still_reviewed`, `test_rejected_edits_keep_statement_events_and_zero_interventions`. |
| §5 Zero cases means no intervention model calls and null estimate | **Passed** | `test_rejected_edits_keep_statement_events_and_zero_interventions`, `test_missing_arm_worlds_and_no_eligible_null`: explicit `NO_ELIGIBLE_CASES`, not a zero effect. |
| §6 Pair routing, one unique nested edit span, matched arm meanings, verifier criteria | **Passed (workflow); not tested live semantics** | `test_all_pair_routing_and_adjudication`, `test_fixed_edit_span_hallucinations_repeats`, `test_mechanical_rules_equal_legacy_without_fake_certifications`, fixed hidden-hint/false-control fixtures. Semantic verifier requests rate every criterion for every arm. |
| §6 At most one complete revision, fixed span, all replacements reverified, operational failure not extra sampling | **Passed** | `test_one_revision_complete_fixed_bundle_and_edit_rejection`, `test_changed_revision_span_is_terminal_and_whole_bundle_reverified`, `test_alignment_failure_no_revision_operational_failure_no_resampling`. Accepted semantic pass prohibits later drafts. |
| §6 Mechanical class checks, preliminary-entry protection, explicit tokenizer/special-token checks | **Passed offline** | `test_mechanical_rules_equal_legacy_without_fake_certifications`, `test_edit_special_tokens_and_whole_prefix_class_checks`; mock token checks and exact source-bound tokenizer adapter. Real-source tokenizer stage remains not tested without a real collection. |
| §6 Source-assertion concerns do not rewrite statements; secondary failures preserve primary | **Passed** | `test_alignment_failure_no_revision_operational_failure_no_resampling`, `test_secondary_failure_does_not_erase_primary`. |
| §7 Real OpenAI/Anthropic adapter contracts | **Passed: documented contracts and mocked transport** | `PROVIDER_CONTRACTS.md`, `test_documented_requests_no_history_tools_and_strict_response_checks`, `test_http_adapter_single_attempt_no_resend_or_secret_persistence`, `test_returned_wrong_model_refused_and_http_failure_not_latency_sample`. Production identity/settings/access are not tested; shipped configuration disabled. |
| §7 Separate environment, opt-in/default offline, credentials, finite calls/tokens/estimated spend | **Passed** | Clean stdlib environment/import test; `test_import_judge_cli_does_not_load_torch`, `test_config_live_gates_and_secret_redaction`, `test_live_gates_need_credentials_and_no_model_loading`, `test_spending_and_seven_call_ceilings`. |
| §7 Atomic separate journal/locks, identity, sanitized raw records, no resend/cache reuse, pending budgets | **Passed** | `test_budget_pause_and_ambiguous_recovery_no_resend`, `test_keyboard_interrupt_is_terminal_and_resume_does_not_resend`, `test_changed_policy_prompt_schema_and_source_refuse_resume`, `test_wrong_source_citations_and_changed_request_are_rejected`, `test_six_pilot_frozen_first_worlds_full_reuse_and_no_next_stage`; source model journal unchanged. |
| §7 Individually invocable stages and no implicit Qwen/confirmation | **Passed** | CLI stage dispatch and `test_six_pilot_frozen_first_worlds_full_reuse_and_no_next_stage`; demo/checkpoints use explicit mock commands. Runbook lists all stage commands. |
| §8 Frozen policies and separate discovery/confirmation; no 2A-informed selection | **Passed offline** | Policy and confirmation source-lock checks; all-case payload allowlists; incompatible policy resume tests; unchanged legacy selection/calibration tests. Code never reads a measurement/probe artifact to select claims. Real confirmation not executed. |
| §8 Cohort, contrast-specific world aggregation, unknown bounds, initially-agreed sensitivity | **Passed** | `test_world_weighted_minus_quarter_not_zero` gives −0.25, includes equality to legacy bootstrap output; `test_missing_arm_worlds_and_no_eligible_null`; `test_secondary_failure_does_not_erase_primary`. Existing bootstrap and conditional-readout summaries are reused. |
| §8 Disjoint terminal states plus overlapping diagnostic reasons, all planned/pending cases | **Passed** | End-to-end and negative/unresolved/failed-alignment tests inspect reports. `reporting.py` reports judge/alignment/before/after/edit/replay/invalid-answer diagnostics separately, with accepted cohort and outside-pilot counts. No broad prevalence claim. |
| §9 Existing tests, genuine CPU-only mocked end-to-end, immutable sources, fixed semantic examples and explicit live-eval command | **Passed offline** | Full test log/IDs; end-to-end test and `python -m exception_review.demo`; semantic fixtures and opt-in evaluation. Actual judge annotation quality is **not tested**. |
| §10.1 UTC/monotonic timing, preparation/provider/stage/wait, usage/rates/reasoning, failures/cache/mocks | **Passed offline** | `test_timing_fake_clocks_cache_and_limits`, `test_usage_reasoning_not_double_counted`, `test_returned_wrong_model_refused_and_http_failure_not_latency_sample`. Separate immutable execution mode prevents treating a mock journal as live evidence. |
| §10.1 Non-mutating Qwen timing, loader components, GPU synchronization, token counts | **Passed offline; real hardware not tested** | Versioned sidecar/delegating wrappers; `test_completed_gpu_timer_synchronizes_without_extra_generation`; source hash and collection-byte equivalence. Actual model loading/download/setup/GPU elapsed times are unmeasured. |
| §10.2 First-three-worlds/six-response pilot, ≤42 calls, safe scheduling limits, no forced branches or full review | **Passed** | Six-case/full-reuse test; request/spend/wall-limit tests; frozen pilot plan in examples; default configured policy remains offline. |
| §10.3 Full technical gate then eight originals, pause/resume/no resampling, partial cannot calibrate | **Passed offline** | `test_eight_pause_full_gate_resume_equal_normal_legacy`, `test_technical_failure_stops_originals`; returned operation bytes preserved and complete output matches legacy. No Qwen inference executed. |
| §10.4 JSON/Markdown, means/medians/ranges, frozen-plan counts/branching, unknown stages not zero, serial scenarios | **Passed offline** | `test_timing_fake_clocks_cache_and_limits`, `test_completed_branches_remove_impossible_future_requests`, `test_event_intervention_timing_counts_from_frozen_plans`; reports use actual plan/case counts and do not invent a measured full-study total. |
| §10.5 Fake clocks/transports, invocation vs cumulative timing, six-case expansion, eight-original equivalence, stop boundaries and runbook | **Passed** | Named timing/pilot/pause/cache tests plus new runbook and synthetic reports. |

## Explicitly not tested

- Availability/access and structured-output behavior of the user's eventual exact production judge models/settings. Public documentation is not an account capability test; model IDs remain unconfigured in the shipped policy.
- Live detector precision/recall, first-claim/span accuracy, edit semantic quality, refusal rates and actual branch frequencies. The optional evaluation command has not been run against a provider.
- Pretrained Qwen3-32B technical replay, behavioral calibration, false-missingness eligibility, or a real event/intervention. Real GPU loader timing and tokenizer checks against a real saved collection remain pending.
- Actual provider latency/charges and GPU/download/setup runtime. All included example timings and usage are synthetic; untimed stages remain UNMEASURED/NOT YET MEASURED.

These are deliberate live-validation boundaries, not silently counted as passing tests. No paid or pretrained execution is needed to inspect the implementation. Full API/backend activation, confirmation, checkpoint measurements and interventions require separate explicit commands and applicable gates.

## Commands used and reproducibility

Baseline/final working directory was the Study 2 worktree above. Environment:

```bash
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export QWEN3_TOKENIZER_DIR=/tmp/study2-qwen3-tokenizer
/tmp/study2-qwen3-venv/bin/python - <<'PY'
import socket, unittest
socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('Offline test network blocked'))
socket.socket.connect = socket.create_connection
result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests'))
raise SystemExit(not result.wasSuccessful())
PY
```

The final execution additionally collected method IDs/results into `test-results.json` and asserted the before/after preservation SHA map. No scientific files were edited by that wrapper.

```bash
# New engine in an isolated environment with no third-party dependencies.
python3 -m venv /tmp/study2-review-stdlib-env
PYTHONDONTWRITEBYTECODE=1 /tmp/study2-review-stdlib-env/bin/python \
  -m unittest discover -s tests -p test_automated_review.py -v

# Reproduce a synthetic run (use a fresh path with the final code).
PYTHONDONTWRITEBYTECODE=1 /tmp/study2-review-stdlib-env/bin/python \
  -m exception_review.demo --output /tmp/study2-review-demo-fresh

# Executable legacy and new entry points, no inference:
python -m exception_continuation --help
python -m exception_review --help
git diff --check
```

The exact final audit wrapper is saved as `verification-script.py.txt`; its `/tmp` preservation-map path is local evidence, not a portable scientific run dependency. Diagnostic judge/alignment counts count requests; invalid-Qwen counts count arm responses; boundary/edit counts count cases. The terminal-state partition always counts cases.

See [the new runbook](../../STUDY2_AUTOMATED_REVIEW_RUNBOOK.md) for supplied-but-unexecuted live commands. A local task-only commit may be created; this patch is **not pushed or merged**. The final response identifies its commit. `changed-files.txt` lists all task-owned additions; preservation snapshots and the original capability-check artifacts are separate.
