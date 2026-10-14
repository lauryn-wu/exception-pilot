# Study 2 automated review v1 and bounded timing

This is a separate execution path on `codex/reasoning-continuation-followup`, built on the unchanged Study 2 v3 scientific implementation. **No paid requests or pretrained inference were run to implement it. Judge annotation quality and Qwen replay/behavior remain unvalidated.** No evidence probes are implemented.

Read [the acceptance evidence](docs/study2-review/ACCEPTANCE.md) and [provider contracts](docs/study2-review/PROVIDER_CONTRACTS.md). The supplied policy is deliberately **offline and unconfigured**. Default commands cannot send requests, even if API keys exist in the environment.

## Version and source boundaries

`exception_review` is outside the legacy `source_hash()` file set. Existing plans, protocols, prompts, model settings, original token arrays, validation thresholds and Mistral failures are untouched. The executable legacy route remains `python -m exception_continuation` with [QWEN3_STUDY2_RUNBOOK.md](QWEN3_STUDY2_RUNBOOK.md) and its existing manual-review commands. Old manual reviews are not reinterpreted as automated judgments.

Use **separate sibling directories** for the source collection, automated review, and each event plan. Preparation verifies the original plan through its original hash gate and binds the collection, trajectory, backend and technical-validation hashes. It requires a complete source collection, including invalid/truncated outputs. It never modifies those sources. Every new frozen artifact binds the new code and policy. Changing code, prompts, schemas, models, settings or policy requires a new review directory/policy; incompatible resume fails. Reports are regenerable views; manifests, decisions, edit attempts and operation history are immutable.

The focused-corrections acceptance addendum is in [FOCUSED_FIXES.md](docs/study2-review/FOCUSED_FIXES.md). This update changes the review code hash: preserve old frozen policies/results as historical artifacts and prepare fresh review/event/semantic-evaluation directories. Do not edit hashes to resume an incompatible frozen review. Legacy source plans/collections remain unchanged and compatible.

All 24 visible originals in selection are reviewed, regardless of answer correctness. Detection uses the text before the first literal case-sensitive `ANSWER:`; without that marker it uses the whole response. This is a formal-marker boundary, not the first answer expressed in prose. The original evidence table contains the true class: the judges are not perfectly outcome-blind. Edits see only the original prefix through the accepted statement cut, never the future suffix.

Two independent initial judges must agree on **the exact whitespace-trimmed character span on the same trajectory** or both vote negative. Otherwise a third independent judge is requested once. Equivalent but differently punctuated/overlapping quotes can remain unresolved. Failures never vote negative. Offset alignment does not establish semantic correctness: omission of a negation can still be an exactly aligned but wrong annotation. That is part of the unmeasured judge-quality evaluation.

Before/after statement boundaries are independent. Before-answer events need only the source collection. Statement events require frozen statements, not accepted edits. Only positive statements with a valid after cut enter editing. The agreeing pair determines the drafter and verifier. One revision is possible; all three replacement strings are reverified together, with the statement and edit span fixed. An unusable response terminates editing; it is not a license to resample. A source-assertion concern excludes the edit without changing the frozen assertion. The first semantic pass is final, subject to explicit tokenizer checks before edit freeze. Token failures are exclusions; no extra drafts are generated to fix them.

## Isolated judge environment and offline checks

The review engine and real HTTP adapters use Python 3.12's standard library; there are **no judge SDK dependencies**. HTTP attempts have no retry loop or redirect following. This environment is separate from the pinned Qwen environment. The explicit tokenizer-check stage runs later in the latter environment, with local tokenizer files only.

```bash
cd /absolute/path/to/exception-pilot
python3.12 -m venv /absolute/path/to/venvs/study2-review
source /absolute/path/to/venvs/study2-review/bin/activate
python -m exception_review --help
python -m unittest discover -s tests -p test_automated_review.py -v

# Entirely synthetic, CPU-only example; no provider credentials are needed.
python -m exception_review.demo --output /tmp/study2-review-demo-fresh
```

The demo performs a budget pause/resume, one adjudicated/revised accepted case, one rejected edit, independent event measurements and mock interventions. Its five accepted cases are software fixtures, not scientific results. Snapshot examples are in `docs/study2-review/examples/`; their temporary source locations are illustrative. Regenerate a runnable example with the command above.

## Configure before any live judging

Copy `configs/study2_review_offline.json` to a **new local configuration outside tracked paths**. Select exact J1/J2/J3 model identities, verify their documented settings and output limits, and verify account access without running this workflow. Record appropriate rates in every judge entry, including cached input/cache writes if applicable. Set `contract_verified` and `access_verified` true only after those checks, give the policy a new name, and enable `live_enabled`. The shipped file has null models and false verification flags; it cannot run live. See the provider notes for verified documentation and the limitations of that verification. No model is silently selected or substituted.

`limits.max_calls` is the cumulative review-wide attempt budget across pilot and full review; an invocation's `--max-calls` cannot exceed it. The per-case ceiling remains seven. `limits.max_estimated_usd` uses a byte-based input allowance plus capped output reservation before every attempt, then reconciles returned usage. It is an **estimate, not a billing guarantee**. Ambiguous failures can incur charges without usage. Billed reasoning is included in output totals, not added twice. `--wall-seconds` stops scheduling new requests at boundaries; it cannot guarantee cancellation of a request already sent. Concurrency is fixed at one.

Credentials are read only from `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Set them privately in your environment; do not put them in configuration files, shell scripts, Git, or reports. Any required missing credential blocks live execution before a request. Raw saved requests omit authorization headers; responses/errors are sanitized. Returned model identity must match the configured exact identity.

## Optional semantic evaluation — live command, NOT executed

Detection uses 16 rubric-authored fixtures. The separate opt-in `edits` stage uses 10 complete verifier fixtures: two valid bundles and isolated indirect hints, false meaning-control, wrong entity, wrong column, wrong explicit value, grammar, reference, and outside-span defects. Every request has the original evidence, accepted statement/prefix, shared edit span, and all three replacements, using the production verifier rubric/schema. Expected criteria are fixed independently of judge agreement and are never sent to the judge. Canned test replies demonstrate software behavior only.

```bash
# Explicitly paid if --live is supplied. 16 detection fixtures × 3 judges = 48 maximum calls.
python -m exception_review semantic-eval \
  --output /absolute/path/to/new-semantic-eval \
  --policy /absolute/path/to/local-review-policy.json \
  --stage detection --max-calls 48 --wall-seconds 600 --live

# Separately authorized, distinct NEW output directory. 10 edit fixtures × 3 judges = 30 calls.
python -m exception_review semantic-eval \
  --stage edits --output /absolute/path/to/new-edit-semantic-eval \
  --policy /absolute/path/to/local-review-policy.json \
  --max-calls 30 --wall-seconds 600 --live
```

Inspect `semantic-evaluation-report.json` and `.md`. Per-model/per-criterion tables report coverage, false approvals/rejections, uncertainty, malformed/refused/unusable responses, usage and timing. Pending and failed attempts remain visible; completion is not semantic correctness. `--wall-seconds` stops scheduling new requests at the boundary, without promising cancellation of a request already in flight. Request and estimated-spend budgets remain independent. Resume an unchanged stage/policy/output to reuse terminal responses without resending; use a fresh directory for the other stage. Omitting `--live` makes no network calls. This fixture report is separate from natural-trajectory timing. No scientific prompts, thresholds or outcomes are tuned by this command. It does not establish natural-trajectory precision/recall.

## Six-response judge timing pilot — live command, NOT executed

Prerequisite: a **completed selection/development collection**, not unseen confirmation. The first three worlds in frozen plan order and their two visible variants are frozen before judging. Fewer available complete worlds are reported, not replaced based on outcomes.

```bash
export STUDY2_SOURCE=/absolute/path/to/completed-qwen-selection
export STUDY2_REVIEW=/absolute/path/to/new-qwen-review-v1
export STUDY2_POLICY=/absolute/path/to/local-review-policy.json

# This preparation is offline and makes zero requests.
python -m exception_review prepare --source "$STUDY2_SOURCE" \
  --output "$STUDY2_REVIEW" --policy "$STUDY2_POLICY" --scope pilot

# Explicitly paid only with --live. At most 42 logical calls (6 × 7), often fewer.
python -m exception_review judge-pilot --source "$STUDY2_SOURCE" \
  --output "$STUDY2_REVIEW" --policy "$STUDY2_POLICY" \
  --max-calls 42 --wall-seconds 900 --live

# Offline report inspection; no Qwen, no remaining-case judging.
python -m exception_review report --output "$STUDY2_REVIEW" --scope pilot
```

**STOP and inspect `reports/pilot-report.md` and `.json`.** A pause leaves requests pending; it never labels unreviewed cases absent. The pilot does not process the other 18 visible responses, load Qwen, run confirmation, perform tokenization, freeze a scientific intervention cohort, or launch edited continuations. It may leave semantic passes pending explicit tokenizer checks. Unreached adjudication/edit stages are UNMEASURED. The report separates live versus mock latency, cache hits, this invocation versus cumulative timing, local/provider/stage time, tokens and estimated charges. It shows frozen-plan workload ceilings and conditional serial scenarios; an original-generation timing is not a full 2A/2B runtime estimate.

For a budget pause, rerun the same command with unchanged policy and source. Completed/failed operations are reused; ambiguous started operations become terminal-unavailable and are never resent. You can change invocation limits within the frozen run limits. Changing the cumulative policy budget changes policy identity; do not silently rewrite it in place.

## Explicit full review continuation and separately invocable stages

Only after inspecting the pilot, expand the declared scope. The full scope uses the same case/request identities and reuses pilot responses, resolutions and edit attempts without paying again.

```bash
python -m exception_review prepare --source "$STUDY2_SOURCE" \
  --output "$STUDY2_REVIEW" --policy "$STUDY2_POLICY" --scope full
python -m exception_review judge --output "$STUDY2_REVIEW" \
  --scope full --stage all --max-calls 168 --live
python -m exception_review report --output "$STUDY2_REVIEW" --scope full
```

For selection, 24 visible cases × seven = at most 168 total logical calls, including reused pilot work. Counts are read from each actual source plan; confirmation has a different denominator. Every source case remains in coverage. `--stage initial`, `adjudicate`, `freeze-statements`, `draft`, and `verify` are individually invocable. `verify` includes the one permitted revision/reverification. Omitting `--live` permits only cached/offline work. The `all` command runs judge stages only and never launches Qwen.

## Explicit token checks and edit freeze (no model generation)

Use the original pinned Qwen environment and a directory containing its **exact local tokenizer assets**. This stage verifies them against the source backend file hashes, checks the chat template and special IDs, then checks all four prefixes. It never loads model weights. No approximate tokenizer fallback exists.

```bash
source /workspace/venvs/study2-qwen3/bin/activate
python -m exception_review tokenize-edits --output "$STUDY2_REVIEW" \
  --scope full --tokenizer-dir "$STUDY2_MODEL_DIR"
python -m exception_review freeze-edits --output "$STUDY2_REVIEW" --scope full
python -m exception_review report --output "$STUDY2_REVIEW" --scope full
```

Inspect `manifests/full-statements.json`, `manifests/full-edits.json`, and `reports/full-report.md`. Pre-freeze semantic/boundary/edit/token exclusions are separate from the frozen 2B cohort. Within that cohort, missing/invalid outcomes and failed replays remain unknown. Estimates average paired case differences within each world, then across contrast-complete worlds. Bounds include every frozen case/world. The initially agreed-only sensitivity uses the fixed J1+J2-positive subset. A missing secondary arm does not erase a valid primary comparison. The report now includes explicit per-arm planned, attempted, returned, syntactically valid/invalid, truncated, missing, unassessed, and replay-excluded counts from the frozen edit manifest and model journal. Truncation is a subset of assessed invalid answers; returned but unscored outputs remain unassessed (including a separate unassessed-truncation diagnostic). Candidate-likelihood scoring returns are tracked separately. Replay exclusions overlap the syntax/missing counts. Count identities and per-case details are in JSON; partial returns are never counted as wrong. Zero accepted cases produce `NO_ELIGIBLE_CASES` and a null effect, without loading a model.

A later confirmation run additionally requires the policy lock from the selected discovery collection:

```bash
python -m exception_review freeze-policy-lock --output "$STUDY2_REVIEW"
# For an already separately authorized, completed confirmation source:
# prepare --source CONFIRMATION_SOURCE --output NEW_REVIEW --policy SAME_POLICY \
#   --policy-lock "$STUDY2_REVIEW/policy-lock.json" --scope full
```

This does not prepare or run confirmation. The existing calibration/selection-lock gates remain unchanged. Freeze policy before confirmation and keep 2A readouts out of statement selection; all cases and the predeclared rule are used. A different policy is a new version, never an overwrite.

## Event and intervention commands — later explicit stages, NOT executed

```bash
# Source-only before-answer events; no review or edit manifest required.
python -m exception_review freeze-events --source "$STUDY2_SOURCE" \
  --output /absolute/path/to/new-before-answer-events

# Statement events depend on frozen statements, even if every edit was rejected.
python -m exception_review freeze-events --source "$STUDY2_SOURCE" \
  --output /absolute/path/to/new-statement-events \
  --statements "$STUDY2_REVIEW/manifests/full-statements.json"

# Inference requires a separate explicit flag, original compatible backend, and gate.
python -m exception_review measure-events \
  --output /absolute/path/to/new-before-answer-events --live-qwen
python -m exception_review measure-events \
  --output /absolute/path/to/new-statement-events --live-qwen
python -m exception_review intervene --output "$STUDY2_REVIEW" \
  --scope full --live-qwen
python -m exception_review report --output "$STUDY2_REVIEW" --scope full
python -m exception_review model-timing-report \
  --output "$STUDY2_REVIEW/interventions/full"
# The same model-timing-report command accepts an event output directory.
```

No original future suffix is pasted after an edit. Every natural continuation starts from original input IDs plus that arm's prefix IDs, with **512−original k** new tokens, identical across arms. Answer cues are supplied only to disposable candidate readouts. New model-operation journals live outside the source and outside judge journals. They record terminal failures without resampling. Per-branch reference equality and the unchanged full-distribution replay checks gate readouts/interventions. Source-only fixed 2A remains available through the unchanged `exception_continuation measure` route; its primary stays 64-minus-0 and retains its both-variant rule. The separately authorized timed route below delegates that exact algorithm and operation journal, adds no originals/checkpoints/cues, and preserves the scientific artifacts. It is not part of the selection sequence:

```bash
# Execute ONLY when fixed-2A measurements are separately authorized; not executed for this patch.
python -m exception_review measure-fixed --output "$STUDY2_SOURCE" --live-qwen
# Read-only scientific accounting / regenerable reports, no inference:
python -m exception_review qwen-timing-report --output "$STUDY2_SOURCE"
```

Inspect `timing-sidecar/fixed-2a-report.json` and `.md`; raw timing events/invocations live under `timing-sidecar/fixed-2a/`. It records unchanged-prefix replay, each complete candidate sequence, actual call counts, cache hits/failures, source/backend identity and hardware/software metadata. A report is written on interruption. **STOP on failure or a started/unresolved legacy operation; do not delete the journal or retry it automatically.** Completed cached work has zero remaining calls even if no historical timings exist; those durations stay unmeasured.

After requesting/freezing event directories, include precisely those directories in aggregate workload accounting:

```bash
python -m exception_review qwen-timing-report --output "$STUDY2_SOURCE" \
  --event-output /absolute/path/to/new-before-answer-events \
  --event-output /absolute/path/to/new-statement-events
```

Supply one flag for one plan or both for both plans. Repeating the same directory is deduplicated; two distinct directories retain separate uninterrupted references even for overlapping cuts. Without these flags, reports explicitly show conditional before-answer-only, statement-only and combined scenarios. For 24 visible selection originals, the combined reference ceiling is 48 (not 24); replay/scoring counts still deduplicate identical cuts within each plan. This does not double the whole experiment's runtime. Frozen eligibility and completed/failed operation journals determine remaining counts when directories are supplied. Mock or absent timings do not yield live runtime estimates.

## Initial Qwen timing: full validation, eight originals, then stop

Use [the existing pinned Qwen setup](QWEN3_STUDY2_RUNBOOK.md) through creation of the actual GPU-host configuration and **fresh selection plan**. Do not edit an already frozen Mac plan. Do not run its unbounded `collect` command if you want this pilot. This adds no alternative install/download setup, scientific condition, backend or precision.

```bash
# Pinned Qwen environment, freshly prepared STUDY2_RUN from the existing runbook.
# BF16, no quantization, enable_thinking=False; one sequential local HF backend.
# Runs the FULL existing technical validation first. Any failure exits nonzero.
python -m exception_review qwen-collect --output "$STUDY2_RUN" \
  --limit-originals 8 --live-qwen
python -m exception_review qwen-timing-report --output "$STUDY2_RUN"
```

**STOP on technical failure and preserve the directory. Do not change tolerances.** Otherwise inspect `timing-sidecar/report.md` and `.json` before continuing. Eight completed originals use the frozen task order; the technical gate is not abbreviated. The partial run is INCOMPLETE: it has no full `collection.json` or behavioral calibration and cannot supply a confirmation lock or an intervention source. A report can still be generated from its journal. Returned originals and technical checks are reused on resume.

```bash
# Later, only after inspecting the pilot:
python -m exception_review qwen-collect --output "$STUDY2_RUN" \
  --complete --live-qwen
python -m exception_continuation selection-report --output "$STUDY2_RUN"
python -m exception_review qwen-timing-report --output "$STUDY2_RUN"
# STOP for calibration/eligibility review. No confirmation/checkpoints/interventions.
```

Timing is a separate versioned sidecar; timestamps are not added to scientific results. Generation/scoring timers synchronize the selected CUDA device before and after the existing operation, so they measure completed wall time. Loader wrappers call the original functions once with unchanged arguments and restore their bindings; they do not touch random state or generation. File verification, tokenizer initialization, CPU model load and device transfer are separate components of initialization total (do not double-count). Downloads/setup are UNMEASURED unless actually observed; this implementation never downloads anything. Hardware/software/precision and token counts are recorded. Mock timings are labeled MOCK and excluded from live estimates. Unobserved replays, three-candidate scoring, event references and four-arm interventions remain NOT YET MEASURED. Timed fixed-2A and explicitly requested event directories supply their own measurements; their elapsed time is separate from collection-only totals. These timings do not establish cross-hardware numerical compatibility.
