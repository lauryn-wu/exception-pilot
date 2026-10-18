# Native-thinking comparison — draft v1

Protocol/module: `study2-native-thinking-draft-v1` / `exception_study2_native`.
Separate operation namespace: `v5/native-thinking-draft-v1/` in a new output directory.
**DRAFT_FOR_REVIEW**, not an amendment to frozen Study 2 v5. No model outcomes informed
this design. Historical tables, prompts, results and validators remain unchanged.

## Question and factorial

Does native thinking change final classification accuracy, particularly the support-versus-conflict
gap, when the recorded target class is present? Compare thinking off/on on the SAME new worlds,
both with a label-only final response. Native thinking still generates a scratchpad; it is not
reasoning without generated text. No probes, activation steering, activation cache, within-reasoning
edits, additional source-report turns, or LLM judges are part of this protocol.

The controlled draft contains 60 worlds, each with two target-record variants, two cue contexts,
two question wordings and two thinking modes: **960 responses**. The first four worlds are
development pilot worlds (64 responses); the other 56 are the main cohort (896 responses).
The original and explicit lookup questions form a FULL factorial, each 480 responses. Counts
are calculated from the cell manifest, not from a prior 560-response estimate. One first-world
bounded pilot invocation comprises 16 cells; it is not the entire four-world pilot.

Original question wording is reused verbatim from `exception_continuation.core.QUESTION`.
Lookup wording is reused from `exception_study2_v5.core.LOOKUP`. Both share the original
introduction and the same new final-format instruction:

> In your final response, return only A, B, or C. Do not include an answer label or explanation in the final response.

This output interface differs from historical visible explanations; those responses cannot
serve as thinking-off controls or exact-cache hits.

## Concrete data design and incompatible constraints

Historical v5 target-excluded totals are 4 pattern / 3 role-0 / 2 role-1. Both recorded variants
oppose the same four-peer climate cue. Four peers cannot all support a class represented only
three or two times in that background. Also, for a binary nonconstant feature to have identical
rates in classes of sizes 4,3,2, its count fractions must share denominator dividing gcd(4,3,2)=1:
only rates zero or one work. Exact half/half balance fails for odd class sizes. A balanced binary
generator does not guarantee balance after v5's ternary reassignment.

The draft uses the smallest equal background class size that retains four unanimous climate
peers: **4 A + 4 B + 4 C = 12 background rows**, plus one target = **13 rows**. Target remains last,
now row 13 (one-based, excluding header/separator). Full-table totals are 5/4/4, with five of the
recorded target class. All evidence/balance calculations exclude the queried target.

Each world assigns ordered distinct labels `(L0,L1,L2)` and a target climate. There are two cue
contexts. In cue context j, four target-climate peers have label Lj, four opposite-climate rows
have label L(1-j), and four other opposite-climate rows have L2. The target's descriptor is the fifth
descriptor of its climate. Opposite-climate descriptors are repeated once under each alternative
class, retaining the historical climate vocabulary without inventing descriptors.

Within a fixed cue context, variant 0/1 changes ONLY the target's recorded class L0/L1. One is
support and one conflict. Thus these valid one-cell pairs cross support/conflict; two support
variants are not falsely advertised as a one-cell pair. Within a fixed target variant, switching
cue contexts swaps exactly eight background labels and preserves the target record. The third
class is fixed. Both support and conflict have four unanimous same-climate peers. This retains
v5's 4/4 conflict cue, but strengthens support relative to the earlier binary generator's 3/4
target-excluded support peers. Class priors and number of opposite-climate rows change explicitly.

Distractor profiles are three binary columns with bit patterns 000,011,101,110. The four audit-marker
values are a permutation of X,X,Y,Z (rotated doubled level across worlds). Each complete four-column
profile occurs once under EVERY background class. Therefore every distractor value and EVERY
joint subset has exactly equal P(value|class), and P(class|value)=1/3. Binary columns are 2/2 within
each class. Marker counts are 2/1/1 within each class: exactly class-independent, not uniform across
marker levels. The distractors need not be mutually independent; their complete profiles are
class-independent. The target uses one of these profiles, so its full distractor match is also tied.

An 11-row alternative with background counts 4/4/2 could use two shared profiles, but would have
to omit at least one of the three marker levels to maintain exact class independence. With four
peers for either target class and all three marker levels present, 13 rows is the smallest
nonconstant exactly class-independent option. We prefer retaining the existing distractor vocabulary
and four transparent profiles; the row-count change still requires scientific review.

All final rendered tables are parsed and validated, including the one-cell and eight-cell
transformations. The cell manifest embeds those exact tables in every prompt. No validation
silently drops or repairs a condition. License plates are opaque deterministic random identifiers;
background rows are shuffled. Exact within-table positional/identifier balance is not claimed.
Position effects are not estimated with a fixed last-row target. Duplicate opposite-climate
descriptions and repeated distractor profiles may make the structure conspicuous; this is a
tradeoff of the transparent exact-balance design and is explicitly open for review.

The 60 worlds cross all six label-role assignments, two climates and five replicates. Overall
roles occur ten times each; climates 30 each; doubled marker levels 20 each; target profiles 15
each. The first-four/remaining split is not separately exactly counterbalanced: the manifest
reports actual counts by cohort. Per-table balance and cross-world counterbalancing are distinct.

## Historical replication option

`--kind historical-v5` uses the saved 60-world plan's exact final tables (120 world/variant tables),
with both original/lookup wording and native thinking off/on. It produces **480 fresh responses**:
32 pilot and 448 main. All are conflict. A support-versus-conflict contrast is unavailable, not
imputed. It has a separate manifest/output and must not be pooled with controlled-world outcomes.
It preserves the saved table and original question, but uses this new final interface and matched
sampling settings. It is a table/wording replication, not a rerun of historical visible reasoning.

## Generator audit

Audit the actual saved final v5 tables after remapping, deduplicating wording/response-arm copies
to 120 world/variant tables. Reconstruct the relevant earlier `exception_counterfactual.make_world`
with the saved seed, verifying its feature fields match the saved v5 base items. Audit both queried
targets and both support/conflict backgrounds (240 queried tables). Label reconstructed earlier
data as such, not as saved inference outcomes. The earlier generator has no audit-marker column.

For every queried table, exclude that target; report totals, role assignments, target and peer
positions, value-by-class counts, P(class|value), P(value|class), descriptive mutual information,
and every 2/3/4-way distractor association. Count votes choose a unique maximum number of matching
rows (empirical P(class|value)); equal-prior rate votes choose a unique maximum P(value|class).
Ties abstain. Report signed pattern-minus-recorded rate margins, absolute margins, and full-joint
matches. Signed margins or net votes can cancel while marginal/joint signal remains. No judge or
model is used. Descriptive MI is not a significance test; cases within a world are not independent.

## Model interface, decoding and truncation

Use Qwen/Qwen3-32B revision `9216db5781bf21249d130ec9da846c4624c16137` for BOTH modes,
BF16, no additional quantization, eager attention, batch one, fresh prefill. Reuse the unchanged
local loader's pinned-file/dependency/CUDA/BF16 checks. Its historical non-thinking configuration
is used solely for loading; neither its plain-visible prompt method nor greedy generation method
is used here. A separate native renderer calls the pinned template with the explicit mode.
Do not relax the historical v5 validation checks.

Thinking on ends the prompt at `<|im_start|>assistant\n`; the model generates its thinking block.
Thinking off appends the official empty `<think>\n\n</think>\n\n` scaffold inside the prompt.
Preparation checks actual tokenized renderings and the switch difference for every prompt.
The frozen plan contains exact prompt IDs, rendered context files, template/tokenizer hashes,
model revision, protocol/code identity, settings, and seeds. No weight read/hash/load or CUDA
initialization occurs during design/prepare/inspect/analysis.

Both modes use **sampling: temperature 0.6, top-p 0.95, top-k 20, min-p 0**, one beam/return,
repetition penalty 1.0, cache enabled, `use_model_defaults=False`. This deliberately matches the
thinking recommendation across modes rather than using mode-dependent settings. Qwen discourages
greedy thinking; its non-thinking deployment recommendation is temperature=0.7, top_p=0.8,
top_k=20, min_p=0. We deliberately keep temperature=0.6, top_p=0.95, top_k=20, min_p=0
for both modes in this primary comparison. This comparison isolates the template
switch under a shared sampler, not separately optimized performance. [Official model card](https://huggingface.co/Qwen/Qwen3-32B).

One seed per world/wording is derived from the frozen seed 2026101801 and shared across
variants, cue contexts and on/off, so paired one-cell tables do not also change their sampling seed.
Seeds and complete resolved generation settings/runtime identity are retained. This does
not promise identical samples across different hardware/library kernels.

Both modes have a provisional **4,096 generated-token pilot cap**, including thinking
delimiters/scratchpad/final/EOS. Only the 64 controlled pilot requests (32 for the separate
historical-table option) receive this budget. Their output ceilings are 262,144 and 131,072 tokens.
The main scientific cell manifest and seeds are fixed now, but its budget and executable requests
remain **unfrozen**. There is no fixed full-experiment token ceiling until main preparation.

Review pilot token lengths (minimum, median, nearest-rank p90/p95, maximum), truncation, EOS and
malformed counts by thinking mode, wording and support/conflict. Assess repetition using complete
raw traces and descriptive 16-token repeated-window statistics. For generated tokens excluding
special tokens, count every sliding 16-token window, including overlapping windows. Repeated
occurrences are total windows minus distinct windows; their fraction divides by total windows.
Shorter outputs have no fraction (null), not zero. Also report the most frequent window's occurrence
count and longest run of a single identical token. These are observational diagnostics, not semantic
classifiers or automatic failure thresholds. Missing/invalid token payloads are not called repetition-free.

After the complete pilot returns, the operator must explicitly record truncation review,
repetition review and a budget rationale. `freeze-main` binds these notes, the pilot plan/backend,
all historical operation hashes, current result hashes and recomputed diagnostics to a **fresh main
output directory**, with one explicitly selected cap shared across both modes. It never chooses a
budget automatically. It rejects incomplete pilots; failed or interrupted attempts need resolution
under the existing retry rules. Returned truncated/malformed answers count as available pilot
evidence and remain unchanged. MOCK evidence cannot authorize a LIVE_LOCAL main run.

The pilot may reveal that a larger cap is needed, or that repetition makes advancement inappropriate.
Do not tune scientific prompts, sampler or accuracy criteria after seeing pilot outcomes. Record
any budget choice before any main response; never edit or re-freeze a main plan to resample outputs.
This pilot-driven choice is disclosed, and the pilot remains separate from main inference/analysis.

The provisional pilot cap is below Qwen's general long-output recommendation and may truncate valid
reasoning. No forced answer cue, token reallocation, soft stop, repetition penalty adjustment, or
automatic larger-budget retry occurs. A truncated answer remains unsuccessful in the primary
endpoint, with truncation separately reported. Main request identity includes its reviewed budget,
the budget-policy version, seed and the complete matched sampling configuration.

Deterministic parsing checks raw token/text/EOS/finish/budget consistency. Thinking-on requires one
generated `<think>...</think>` block (optional leading whitespace only) followed by a final channel; off requires no generated thinking
block. The whole stripped final text must be A/B/C, with terminal EOS. Prose, `ANSWER: A`, missing
or repeated delimiters, malformed metadata and truncation remain visible, never salvaged by a judge.
Save raw complete output, tokens, separated thinking/final text and token counts, parsing status,
timing, exact request, model/tokenizer/template identity and dispatch/attempt provenance for later
activation replay. Do not save activations now.

## Execution and resumption

Offline `design` freezes the scientific manifest; `prepare` requires existing pinned tokenizer
assets and freezes exact **pilot** requests in a new run directory.
The budget-policy version is `pilot-budget-review-v1`. `freeze-main` is an offline command requiring
completed pilot evidence and explicit review; it freezes main requests and their cap separately. `inspect` and `analyze` are offline.
`run --live-qwen --scope pilot|main --max-new N` is the only live path. An omitted live flag gives
an offline report. No stage automatically advances. Determine executable never-started work and
validate all cached requests before loading once. `--scope` must match the frozen plan cohort;
`--scope main` on a pilot plan fails before loading or dispatch. Main execution revalidates its pilot
evidence against immutable journals, not a derived analysis file. Completed/blocked invocations load zero models.
Historical visible outputs and different scientific requests cannot be cache hits.

Use the existing immutable request/start/return/failure journal primitive under this new namespace.
Returns are durable before analysis, including malformed/truncated answers. Stop the invocation
at its first backend exception. Failed/ambiguous attempts are not automatically resubmitted.
`retry --cell-id ... --reason ...` records an explicit authorization for a new attempt referring to
the immutable previous failure/interruption; it makes no model call. It refuses returned outcomes.
Normal resume then runs the authorized attempt and never-started work. Preserve all earlier attempts.
An interrupted invocation is retained with a started record and no fabricated finish record.
Model-load/call counts and bounded-invocation timing are separate from scientific outcomes.

## Primary analysis and signs

Report pilot and main cohorts separately, and original and lookup wordings separately. Lookup is
a full factorial in this draft. Each condition reports eligible/planned, returned/completed,
unavailable, correct, valid, malformed and truncated counts. All returned responses are in accuracy
denominators; failed/interrupted/never-started work is unavailable, not incorrect.

Paired thinking contrast = accuracy(on) minus accuracy(off), on common returned pairs with the same
world, target variant, cue context and wording. Positive means higher accuracy with thinking.
Conflict penalty = accuracy(support) minus accuracy(conflict). The interaction = penalty(on)
minus penalty(off), using complete matched four-cell quartets per world/variant/wording. Positive
means a larger conflict penalty with thinking. No arbitrary absolute accuracy threshold establishes
harm, and incomplete paired denominators are explicit.

Use the existing world-cluster bootstrap: 2,000 draws, seed 2026101601, common draws retaining all
variants/conditions within worlds. Do not treat response cells as independent samples. A degenerate
interval reflects no observed variation in this sample, not population certainty. No final accuracy
or mechanism claim is possible before live data. Finish at **STOP_REVIEW_NATIVE_THINKING_DRAFT**.
