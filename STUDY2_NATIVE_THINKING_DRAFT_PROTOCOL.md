# Native-thinking comparison — draft v2

Protocol/module: `study2-native-thinking-draft-v2` / `exception_study2_native`.
Separate operation namespace: `v5/native-thinking-draft-v2/pilot-budget-review-v1/` in a new output directory.
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

> Your final answer must be a single uppercase letter: A, B, or C. Do not add any prefix, punctuation, or explanation.

This instruction constrains the final answer, not the native thinking trace.
This output interface differs from historical visible explanations; those responses cannot
serve as thinking-off controls or exact-cache hits.

## Concrete data design and incompatible constraints

Historical v5 target-excluded totals are 4 pattern / 3 role-0 / 2 role-1. Both recorded variants
oppose the same four-peer climate cue. Four peers cannot all support a class represented only
three or two times in that background. Also, for a binary nonconstant feature to have identical
rates in classes of sizes 4,3,2, its count fractions must share denominator dividing gcd(4,3,2)=1:
only rates zero or one work. Exact half/half balance fails for odd class sizes. A balanced binary
generator does not guarantee balance after v5's ternary reassignment.

The reviewed 13-row v1 draft is rejected: a 4/4/4 background plus the queried row produces 5/4/4,
so the unique full-table majority and unique odd-count class reveal every answer. Equal background
counts and exact per-table distractor independence are insufficient protections. Preserve that
frozen draft and its audits; never use it as the v2 execution plan.

V2 uses **16 rows: 15 background rows plus the target last at row 16**. There are ten count/feature
blocks, each crossed with all six ordered ABC role assignments `(L0,L1,L2)`:

- Six blocks have the six permutations of background role counts `(4,5,6)`.
- Three separate feature blocks have `(4,4,7)`; the seven-count class is L2, which is not a target
  record variant. This prevents the deterministic count-eight answers produced when a seven-count
  background class itself receives the target. Those alternative blocks were rejected offline.
- One block has `(5,5,5)`.

Each block contains six worlds, for 60 total. Block climates alternate cold/warm: five blocks each.
Within a world, four same-climate peers and four opposite-climate rows exchange L0/L1 across the
two cue contexts. Four more opposite-climate rows have L2; three extra opposite-climate rows
supply the remaining counts. Those extra labels stay fixed across cue contexts. Exactly eight
background label cells change. Target record variants change ONLY the target Verified-class cell
L0/L1. Thus cue=variant is support; cue!=variant is conflict; the target is preserved across cues.
Four unanimous same-climate peers remain in every condition. This retains the v5 cue strength,
including the disclosed strengthening of support relative to the earlier binary generator.

Full-table totals equal background totals plus one in the recorded class; they necessarily differ
across target-only flips. They are not claimed constant or balanced within a table. Count blocks
vary which labels are majorities, including labels agreeing with the recorded class, the climate
pattern, or neither. In the full 240-table grid, unique full-table majority covers 192 tables,
agrees with the record on 72 and the pattern on 48 (support overlaps those categories), and ties
on 48. Support/conflict-specific agreement is reported by the audit, not hidden in a pooled rate.

Distractor profiles retain binary patterns 000,011,101,110 and marker values X,X,Y,Z, with the doubled
marker rotated by block. The 15 background profiles have multiplicities 4/4/4/3 and a deterministic
shuffle independent of label names. Profile assignments to row roles are fixed within a block
across all six label permutations; target profile is block modulo four. Per-table marginal and
joint associations remain and are measured. Pooling a COMPLETE six-world label-permutation block
produces exact raw-A/B/C joint independence for both target-excluded and full-table rows. This is
an aggregate property, not per-table balance or proof of no recorded/pattern-role association.
The audit reports relative-role associations separately. Pilot/main subsets need not retain exact
block balance; both are audited separately.

All final rendered tables and paired transformations are checked. Opaque identifiers, descriptor
assignments and background order vary deterministically by world. The target is fixed last, so a
last-row copying heuristic remains possible. There are eleven opposite-climate background rows,
with repeated descriptions. Six worlds in a block share a profile/count scaffold; world-held-out
histogram checks are supplemented by holding out the entire six-world block. Existing world-cluster
outcome intervals remain descriptive and do not turn these counterbalanced cells into IID samples.

V2 preserves 60 worlds, 240 tables, 960 response cells, the four-world/64-response pilot, and the
896-response main cohort. All label-role assignments occur ten times and each climate occurs 30
times. Doubled marker counts are X=24/Y=18/Z=18 worlds; target profiles occur 18/18/12/12 times.
These are disclosed counts, not claims of exact counterbalance for every factor. The scientific
question/lookup wording, matched sampler and native-mode handling are unchanged. A new protocol,
world IDs and frozen prompt/request hashes distinguish v2 from v1; never edit a v1 plan in place.

## Historical replication option

`--kind historical-v5` uses the saved 60-world plan's exact final tables (120 world/variant tables),
with both original/lookup wording and native thinking off/on. It produces **480 fresh responses**:
32 pilot and 448 main. All are conflict. A support-versus-conflict contrast is unavailable, not
imputed. It has a separate manifest/output and must not be pooled with controlled-world outcomes.
It preserves the saved table and original question, but uses this new final interface and matched
sampling settings. It is a table/wording replication, not a rerun of historical visible reasoning.

## Generator and shortcut audit

The earlier final-table audit is preserved under `audits/study2-native-thinking-draft-v1/`; the
budget amendment remains under `audits/study2-native-thinking-budget-review-v1/`. V2 regenerates only
its affected controlled draft/shortcut evidence in a new output. It does not rerun historical
model experiments. The offline `audit-shortcuts` command reads the frozen final rendered tables.

For each of the 240 unique tables, report target-excluded AND full-table class totals; majority and
minority rules; parity and remainders modulo 2/3/4 (each specified residue and unique-residue class);
and full-profile matching majorities both including and excluding the target. Also retain feature
count/rate votes, their signed/absolute margins, P(class|value), P(value|class), and all 2/3/4-way
joint associations from the existing table audit. Signed votes may cancel despite real association.
Tied candidate sets abstain; empty sets are separately counted. Report coverage, correct/wrong,
accuracy among predictions, correct fraction of all tables, and pattern agreement for all,
pilot/main, and support/conflict intersections. Wording/mode copies do not quadruple table counts.

Histogram-only exact lookup and nearest-L1-histogram voting use no new dependencies. Each fold
holds out every variant/cue of one world; the block version holds out all six label-permutation
worlds. Ties abstain and absent exact matches are explicit. There is no parameter search. These
are descriptive cross-validation diagnostics across the fixed manifest, not a pilot-trained model
promised to generalize to main. An additional in-sample histogram upper bound groups identical
(A,B,C) full counts and sums each group's largest answer frequency.

Reject a draft if any audited baseline is perfectly correct on its nonempty covered set over the
full manifest, or if any observed full-table histogram identifies only one answer. V1 fails these
gates. V2 passes, with a histogram-only upper bound of 50%; all 12 observed histograms have multiple
possible recorded answers. This finite audit cannot eliminate richer shortcuts. Subgroup or small
selective successes are disclosed, not suppressed or forced to chance. In particular, profile
majority retains substantial predictability, and target position is still a possible shortcut.
These tradeoffs require review before a live pilot; passing the audit is not behavioral validation.

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
completed pilot evidence and explicit review; it freezes main requests and their cap separately. `inspect` is read-only, including in the presence of recognized interrupted-write debris.
`analyze` is offline and writes the derived report under the run lock.
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

## Interrupted atomic writes: native-only recovery

Historical `operation_tree`/journal/storage functions are unchanged. The native reader accepts only
canonical request/start/return/failure files and their exact atomic-writer temporary filename shape:
`{request,started,returned,failed}.json.[a-z0-9_]{8}.tmp`. Unknown files, symlinks, malformed canonical
JSON/hashes, wrong request/backend identities and contradictory canonical states still fail closed.
A temporary file is opaque evidence, even if it contains a complete valid JSON return. Never promote it.

A canonical completed return plus leftover recognized debris remains completed and is reused with
zero model loads if no work remains. Canonical failures remain failed. A temp-only/empty known
operation folder, a partially written request/start, or a canonical start with only a temporary
return is conservatively ambiguous. Even a request-only interruption that likely preceded dispatch
requires explicit recovery/retry; no potentially dispatched attempt is made never-started. Orphan
dispatch evidence also creates a hold. Unrecognized orphan folders and orphan canonical terminal
states without a request require forensic review; the tool does not guess their scientific identity.

`recover --reason ...` is offline and takes the run lock. It first freezes a manifest binding the
plan, operation IDs, canonical hashes, temporary-byte hashes and ambiguity holds, then moves only
those temporary files into `journal-recovery/.../files/`. Canonical files are never changed. Empty
orphan folders retain an explicit hold. Recovery intent exists before any move; interrupted moves
resume against their manifest with no overwriting. Incomplete manifest writes before any move are
reported as uncommitted recovery intents and preserved, not promoted.

Inspect performs no mutation. Run may reuse canonical returns and execute other never-started work;
it skips ambiguous attempts. Explicit retry requires recovery to finish first, retains all prior
evidence, and creates a separate attempt. Ordinary returned wrong/malformed/truncated responses
remain cached. Recovery never authorizes inference or automatically retries a call.

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
