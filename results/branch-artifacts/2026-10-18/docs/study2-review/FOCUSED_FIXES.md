# Focused Study 2 corrections: acceptance and evidence

This audit implements the five findings in the user-supplied `Codex_Focused_Fixes.md`. The inspected worktree was clean at `90fe014a261c9bc6586efe66ad31c505456822ec` on `codex/reasoning-continuation-followup`. All five findings were present at that head; none was already resolved. They are now **fixed offline**. No push or merge was performed.

## Finding-by-finding result

All test names below are in `tests/test_review_focused.py`.

| Finding | Status | Implementation and evidence |
|---|---|---|
| 1. Semantic evaluation wall limit | **Fixed** | CLI forwards `--wall-seconds` to `evaluate` and the actual `Journal`. `test_actual_cli_wall_boundary_and_cache_resume` executes CLI parsing/dispatch with the real Journal and a fake clock: exactly two requests finish at the four-second boundary; none is dispatched afterward; completed responses are reused byte-for-byte. `test_wall_request_and_spend_budgets_are_independent` verifies all three limits independently. Invalid limits are rejected by subprocess CLI tests; interruption reports and terminal no-resend behavior are tested. In-flight cancellation is not promised. |
| 2. Edit-verifier semantics evaluation | **Fixed; live quality not tested** | Explicit `semantic-eval --stage edits`, separate frozen directory/plan, 10 authored fixtures × 3 judges = at most 30 logical calls. Two valid bundles plus isolated hint, false-control, wrong-entity/column/value, grammar/reference and outside-span defects. Complete evidence, accepted statement/prefix, fixed shared span and all three replacements use the production verifier rubric/schema. Independent expected labels are withheld from inputs. `test_complete_fixtures_and_independent_criterion_labels`, `test_all_pass_judges_report_false_approvals_not_consensus_quality`, `test_uncertain_malformed_refused_and_partial_coverage`, `test_oracle_and_false_rejection_labels_are_independent`, and the actual edit-stage CLI test verify coverage, false approvals/rejections, uncertain/malformed/refused outcomes, actual mocked usage/timing, incomplete runs and isolation. |
| 3. Aggregate event-reference workload | **Fixed** | Repeatable `qwen-timing-report --event-output` derives counts from each supplied frozen plan and model journal; identical cuts deduplicate within a plan, while distinct directories retain separate references. Without plans it explicitly shows conditional one-plan/two-plan scenarios: up to 48 references for 24 visible originals. All four `EventCountingTests` verify one/both plans, no eligible statement cuts, identical/overlapping cuts, completed/cache reuse, source-binding refusal, CLI and unmeasured timings. This does not imply twice the full runtime. |
| 4. Timed fixed 2A | **Fixed; real GPU timing not tested** | Separately opt-in `measure-fixed` delegates `exception_continuation.runner.measure` unchanged, with a scoped Session adapter and one timed backend. No originals, checkpoints, cues or model calls are added. `test_equal_legacy_artifacts_counts_and_calls_cache_reuse` proves identical model-call sequence, identical scientific collection/calibration/validation/execution/measurement bytes and identical operation records: 96 mock replays, 432 complete candidate sequence scores, then 240 cache hits and zero new model calls on resume. Remaining counts also consume completed untimed legacy journals. Tests cover partial sequence failure, KeyboardInterrupt, no-resend, explicit CLI authorization and safe reports. Source/backend/hardware identity and actual per-sequence timings are sidecar metadata. |
| 5. Per-arm intervention coverage | **Fixed** | Frozen cohort plus bound model journal determine planned, attempted, returned, syntax-valid/invalid, truncated, missing, unassessed and replay-excluded counts. Syntax and replay validity remain separate. `test_count_identities_partial_syntax_replay_and_missing` checks the count identities and truncation subset; `test_interrupted_scoring_retains_returned_but_unassessed` preserves partial returns without inventing scores. The secondary-arm-failure test keeps the primary contrast's three complete worlds while the value arm is missing; the zero-case test preserves null effects. |

## Before/after verification

- Baseline: **473 tests passed**, no failures/errors/skips; 88.362 seconds runner wall time.
- Focused regression suite in the standard-library-only environment: **20 passed**, no failures/errors/skips; 10.984 seconds.
- Full offline suite: **493 passed**, no failures/errors/skips; 94.356 seconds.
- First focused development run: 20 tests, four fixture-construction errors (duplicated `event` key in synthetic statement boundaries), no assertion failures. The fixture was corrected; the scientific implementation and existing tests were not weakened. The next focused run and full run passed.
- Full-suite log includes tokenizer fork/parallelism warnings from CLI subprocess tests; these were warnings, not failures or skips.
- Socket connections were blocked in the test runner. Existing tokenizer assets were used offline. Existing tests include a tiny randomly initialized CPU architecture; no pretrained Qwen inference or large weights were used.
- Legacy scientific source hash stayed `31c749811a37fc77cebd6bf6878eaa510306865347b374acc0f3099c5e261149`. A post-suite check confirms **272 protected files unchanged**, including scientific modules/configs/protocols and existing results, Mistral capability artifacts and source plans. See the preservation map.

Evidence: [baseline output](focused-fixes/baseline.log), [baseline results](focused-fixes/baseline.json), [focused output](focused-fixes/regressions.log), [focused results](focused-fixes/regressions.json), [full output](focused-fixes/final.log), [full results and method IDs](focused-fixes/final.json), [preservation map](focused-fixes/preservation.json).

## Exact executed commands

Working directory: `/Users/laurynwu/.codex/worktrees/study2-audit-fixes/exception-pilot`. The wrapper is saved as [verification-script.py.txt](focused-fixes/verification-script.py.txt). It snapshots protected files, blocks sockets, discovers tests and writes structured results. Its `/tmp` paths are audit evidence locations, not scientific run dependencies.

```bash
# Baseline, before edits:
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QWEN3_TOKENIZER_DIR=/tmp/study2-qwen3-tokenizer \
RESULT_PATH=/tmp/study2-focused-baseline.json \
/tmp/study2-qwen3-venv/bin/python /tmp/study2-focused-verify.py \
  > /tmp/study2-focused-baseline.log 2>&1

# New focused regressions (run again after the fixture correction):
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
TEST_PATTERN=test_review_focused.py RESULT_PATH=/tmp/study2-focused-regressions.json \
/tmp/study2-review-stdlib-env/bin/python /tmp/study2-focused-verify.py \
  > /tmp/study2-focused-regressions.log 2>&1

# Full final suite:
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QWEN3_TOKENIZER_DIR=/tmp/study2-qwen3-tokenizer \
RESULT_PATH=/tmp/study2-focused-final.json \
/tmp/study2-qwen3-venv/bin/python /tmp/study2-focused-verify.py \
  > /tmp/study2-focused-final.log 2>&1

git diff --check
```

For a portable rerun after following the existing pinned Qwen environment setup:

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QWEN3_TOKENIZER_DIR=/absolute/path/to/already-present-pinned-tokenizer python - <<'PYTEST'
import socket, unittest
socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('Offline test network blocked'))
socket.socket.connect = socket.create_connection
result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests'))
raise SystemExit(not result.wasSuccessful())
PYTEST
```

## Changes and boundaries

The diff is confined to the sibling review package (CLI, semantic fixtures/evaluator, telemetry and reports, two small accounting modules), one focused test file, the existing review runbook and this acceptance evidence. Legacy scientific algorithms, Qwen BF16/no-quantization/thinking-disabled configuration, exact original prompts/tokens, replay tolerances, both-variant 2A rules and conditional 2B cohort are unchanged. The original legacy route remains separate. No evidence probes or activation work was added.

The new code hash intentionally invalidates incompatible frozen review-policy resumes. Historical examples, policies, capability failures and results are preserved, not rehashed. Prepare fresh review/event/semantic-evaluation outputs with this code. Legacy source collections remain usable because their source hash is unchanged. See the [updated runbook](../../STUDY2_AUTOMATED_REVIEW_RUNBOOK.md) for supplied, unexecuted live commands and explicit stop boundaries.

**Not tested:** actual judge annotation quality/access, paid API behavior, real GPU latency/throughput, pretrained Qwen replay/calibration/behavior. No paid judge calls, weight downloads, cloud launches or pretrained inference were performed. Constructed/mock results do not establish any of these capabilities.
