# Study 2 v4: conditional textual-prefix interventions

Protocol ID: `study2-conditional-text-prefix-v4`. Technical gate:
`same-input-fresh-prefill-v4`. This is a new methodological version. The v3
failure at `bea5cc6` remains a failure, with its original artifacts and tolerances.

The estimand is the effect on subsequent answer choices, conditional on the
original prompt and a controlled textual reasoning prefix, of changing one
statement in that prefix. Freshly processing text changes its computed internal
state. The experiment does not restore an identical latent/KV state, identify an
initial latent belief, or establish that the original statement caused the error.

## Unchanged scientific design

Reuse v3's exact worlds, task order, target-last tables, role randomization, seeds,
direct and visible instructions, 48 selection originals, 96 confirmation originals,
512-token cap, answer syntax and calibration (20/24 direct correct, 3 matched
pattern errors across 2 worlds). Preserve Qwen/Qwen3-32B model/tokenizer revision
`9216db5781bf21249d130ec9da846c4624c16137`, BF16, no quantization, one CUDA device,
eager attention, greedy decoding, and `enable_thinking=False`. The official closed
empty thinking block stays in the original prompt. Continuations concatenate saved
token IDs; no new assistant/user turn or chat-template application occurs.

Originals are generated normally, uninterrupted, with no answer cues or judge
prompts. Complete original IDs, rendered input IDs, text, EOS/finish metadata,
boundary catalogs, and backend/source fingerprints are retained.

## Independent technical gate

For each of v3's three non-scientific prompts, generate one original with budget
128. At every eligible k in 0,1,8,16,32, form original input IDs plus the first k
saved output IDs. Generate two independent fresh-prefill continuations, each with
budget 128-k and first-next-token full-vocabulary telemetry. New generate calls
have independent caches. Same-input pairs must agree in all suffix tokens,
stopping/finish, and next-token argmax; telemetry must be finite and satisfy the
original probability-allclose and TV <= 1e-4 checks. Original probability tolerances
remain prob_atol=1e-5, prob_rtol=1e-3. Raw-logit allclose and discrepancy metrics
retain logit_atol=1e-4 and logit_rtol=1e-4 and are reported separately, non-gating.
LIVE telemetry must contain the pinned model’s 151,936 vocabulary entries;
truncated/top-k telemetry cannot pass. Original-versus-fresh suffix agreement is descriptive only. No original/fresh
cross-path comparison is an eligibility gate.

Ceiling: 3 originals plus 30 fresh continuations = 33 generation operations and
3 * [128 + 2 * (128+127+120+112+96)] = 3,882 generated tokens. Short originals may
reduce eligible cuts. Technical evidence is not behavioral calibration. MOCK
success leaves full-size Qwen status PENDING. Any same-input failure blocks
collection. Failed/interrupted operations remain terminal and are not resampled.

## Conditional readouts (2A)

Use exact pre-answer original-token prefixes at fixed cuts 0,32,64,128. Append the
separately encoded frozen answer cue only to a disposable readout context. Score
the complete candidates ` A\n`, ` B\n`, ` C\n` by summed conditional token log
probabilities, without length normalization. A fresh forward evaluation uses no
future original tokens. No reference or suffix-replay generation is needed.
Primary: world-grouped 64-minus-0 gold-versus-pattern log odds, requiring both
recorded-value variants per world. Preserve cue sensitivity and final-outcome
strata. Later unavailable cuts do not discard earlier valid measurements.

Statement and before-answer events use frozen annotations and original token
boundaries. Every visible response can receive a before-answer readout regardless
of false-missingness or edit eligibility. Identical event cuts share one readout
within a plan; separate plans are counted separately. After-minus-before-statement
is secondary and does not identify a sentence-caused internal-state transition.

## Conditional interventions (2B)

Review every visible original, including invalid, truncated, correct and negative
cases. Keep first explicit false target-class-absence detection, exact Unicode
spans and original boundary rules. Reuse two initial judges, conditional J3, one
edit revision and independent semantic verification of all three edits. Preserve
source assertion concerns as edit exclusions without relabeling statements.

Freeze four complete texts and token arrays: unchanged, meaning_control,
availability_repair, value_repair. Unchanged uses exactly the saved original prefix
IDs. The three edits replace the same exact span and preserve all other characters.
Freeze the existing `rng_for('edit-order', task_id)` arm order. Each arm independently
freshly processes original prompt IDs plus its own prefix IDs. Every arm receives
512-original_k new tokens, regardless of edited prefix token length; record deltas.
No original future tokens or other-arm KV cache may enter an arm.

Unchanged is a fresh-prefix experimental control. It can differ from the original
uninterrupted suffix. Such differences are diagnostic and non-gating. Input validity,
syntax, truncation, generation availability and readout availability are separate.
An unavailable arm affects only contrasts using that arm. Invalid/truncated/unscored
correctness stays unknown, not wrong. Primary is availability minus meaning;
availability-minus-unchanged, meaning-minus-unchanged and value-minus-unchanged
remain secondary. Preserve world weighting, full frozen-cohort denominators,
unknown-in-[0,1] bounds and initially-agreed-only sensitivity. No selection by effect.

## Staging and provenance

Use new v4 config envelopes, plans, source hashes, filenames, journal namespaces
and directories. Never forge legacy validation fields or change legacy hashes.
All request/start/returned/failed journal files are immutable. No automatic retry
of dispatched failed/ambiguous operations; successful caches are reused. Timings
synchronize CUDA around operations and distinguish MOCK from measured LIVE values.
Unmeasured startup/download/inference stages do not receive zero-time estimates.

Prepare -> technical-only gate -> first eight originals -> STOP -> explicit 48
completion -> calibration and independent review. Confirmation needs passed
selection calibration, identical model configuration/backend, and the exact frozen
selection review-policy lock. Every downstream measurement/intervention is an
explicit command. No evidence probes or downstream factual-question extension.

The shared judge code executes under an explicit v4 source adapter, with both
shared and adapter files hashed. v3 artifacts and semantics remain untouched.
