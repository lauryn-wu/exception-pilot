# Frozen source-report follow-up v1

This additive measurement asks whether the literal recorded class can be reported
under an explicit same-assistant source query after saved original reasoning.
The 56 remaining worlds, both variants, original framing and visible reasoning
are fixed. All 112 trajectories are included irrespective of answer correctness,
annotations, truncation after the cut, or prior class preference. The four examined
pilot worlds are calibration only; lookup and direct trajectories are excluded.

Only existing eligible exact fixed/0, fixed/256 and fixed/512 boundaries are used.
Expected inventory: 112, 112 and 108 contexts, four excluded 512-token cuts, 332
unique main queries and 664 joined old cue entries. A mismatch stops preparation.
No cut is moved, snapped, extended or substituted with pre-answer.

The exact suffix starts with two newlines and has no trailing newline:

```
\n\nWhat value is written in the Verified class cell for license plate {plate}? Return exactly one of A, B, C, or MISSING.\nSOURCE_REPORT:
```

Only the plate is substituted from trusted metadata. The context is saved prompt
IDs + saved first k generated IDs + independently encoded suffix IDs. Verify the
saved exact boundary, prefix hash, suffix round-trip/no-special-token property and
decoded concatenation. Never re-encode the combined context or rebuild a saved
conversation. The original empty thinking block stays in the saved prompt.

Preparation requires locally available pinned tokenizer assets at revision
`9216db5781bf21249d130ec9da846c4624c16137`, verifies their bytes without reading
weight shards, and freezes every query ID/context, parser/interface version,
source binding and generation setting. It does not load a model or download files.

Each uncached query is one greedy generation with budget 16, capture_at=(), pinned
Qwen3-32B BF16, eager attention, batch one and enable_thinking=False. The original
model, hardware, configuration, dependencies, tokenizer and byte hashes must match.
No candidate scoring, logits/hidden-state capture, original-answer generation,
longer CoT, old measurement rerun, judges, probes or Study 2B occur in this path.

Strict parsing requires observed EOS, consistent saved metadata/text/token IDs,
and whitespace-trimmed whole text exactly A, B, C or MISSING. Empty, verbose,
ambiguous, malformed and truncated returns are separate categories. A label in an
unterminated reply is diagnostic only. No letters are extracted from prose.
Returned invalid/incorrect replies are never a reason to retry.

Calibration comprises eight k=0 source-present pilot contexts (both original/
visible variants in each world) and four genuine-MISSING controls. For each world,
change only the target Verified class cell to literal MISSING; prove both variant
prompts become byte-identical and deduplicate. Only these four changed prompts use
the original template to render new prompt IDs. Every calibration prefix is empty.
All twelve replies must terminate, parse and report their literal source value
correctly. Any failed/ambiguous operation or incorrect return blocks main work.
One live invocation may run calibration and then main using one already-loaded
model. A terminally failed cached calibration stops offline. No automatic interface
changes, budget increases, reruns or additional adjudication are allowed.

Native evidence uses existing read-only Source and read_data validators. An
export containing only the sealed legacy summary is supported explicitly: verify
all expected computation IDs, source-row/world bindings, contexts/hashes, cues,
candidate IDs, finite token log probabilities and arithmetic. Missing journals
are not evidence of missing measurements. Reproduce the old measurement-plan
hash when possible; otherwise label it an unverified historical reference and
explain the absent path/plan information. Never fabricate historical journals.

The primary legacy preference uses saved class-token log probabilities only:
A=[362,198], B=[425,198], C=[356,198]; validate these exact mappings before using
token_logprobs[0]. No scoring forwards are performed. Preserve old sequence scores
as labeled newline-inclusive sensitivity. Save class-token ABC mass and restricted
probabilities separately. Exact maximum ties have no preferred class and are
neither correct nor wrong preferences. Do not select a favorable legacy cue.

Source accuracy uses all returned replies: correct exact labels count as correct;
MISSING on a source-present main case and invalid/verbose/truncated returns count
as incorrect. Never-started, failed and ambiguous calls are unavailable, excluded
from that denominator and reported against all eligible contexts. MISSING is an
answer, not an unavailable operation. Report source confusion and joint outcomes
separately per checkpoint and old cue, including correct-source/wrong-preference
and correct-source/pattern-preference fractions with explicit eligible, returned
and conditional denominators. With missing source results, observed confirmations
per eligible context are lower bounds; report upper bounds as well.

Paired changes require the identical eligible trajectory and both returned source
replies. The 108-context 512-token population is paired with its own baseline.
Bootstrap 2,000 times with seed 2026101601, resampling the 56 independent worlds.
Use common world draws across metrics, variants, checkpoints and cues. The point
estimate of source accuracy is the all-returned response ratio; bootstrap ratios
retain world blocks and the actual available denominators. Saved natural final
answers are separate from checkpoint conditional preference. Do not infer a broad
confidence decline from newline-inclusive scores or compare source reply
probability magnitudes with legacy conditional ABC probabilities.

Acquire an output lock and validate/index source, plan and caches before loading
weights, hashing shards or initializing CUDA. Returned operations are reused;
request-only records may start; failed/ambiguous started records never resend.
Only genuinely executable work permits one backend load. Fully cached or blocked
runs load zero models. Save raw returns durably before parsing. Immutable journals
are authoritative; derived reports may be atomically replaced. Source/index
construction occurs once per scope/invocation, never per query. The new operation
namespace is v5/source-report/<digest>. Freeze content identity independently of
Git HEAD; record actual extension and historical revisions separately at dispatch.
An incompatible content change stops; an ordinary revision change with identical
content may reuse caches with truthful provenance. Resume uses the same output;
new directories are not a remedy for failed caches or a way to resample.

Maximum new work if calibration passes: 12 + 332 = 344 short generations and
5,504 generated tokens; at most one backend load. Fully cached: zero loads/calls.
Measure timing only within these operations; no benchmark generations. These
bounds are not runtime or rental-price estimates.

Interpretation: success shows explicit source recoverability after that prefix.
The model may reread the table; the suffix changes elicitation. This does not
establish uninterrupted retention, deliberate overriding, an endogenous causal
mechanism, or a novelty claim. Historical studies, hashes, outputs and Study 2B
remain unchanged and outside this workflow.
