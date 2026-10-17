# Frozen source-report follow-up v2

VERSION: `study2-source-report-v2`.
INTERFACE: `same-assistant-quoted-source-query-v2`.
PARSER: `first-closed-quoted-field-four-labels-v2`.
Operation namespace: `v5/source-report-v2/`.

This is a pilot-informed revision after source-report v1 FAILED. Reference plan:
`a5f38dc97c35a3ace5dfee579627aaa40599a48c482ecf63bc8eb366cbfdfc70`.
All twelve v1 calibrations reached 16 tokens without EOS; none passed the v1
whole-response parser. Post hoc prose observations (8/8 present values correct,
2/4 missing controls stating MISSING) are diagnostics, not passing measurements.
V1 and its 332 never-started main queries remain unchanged. V2 may also fail.

## Fixed interface and generation

Append this exact suffix, with two leading newlines and no trailing newline:

```python
SUFFIX = (
    '\n\nWhat value is written in the Verified class cell for license plate {plate}?\n'
    'Complete the quoted cell value with A, B, C, or MISSING.\n'
    'SOURCE_REPORT: "'
)
```

Only the trusted target plate is substituted. The opening ASCII quote is already
in the prompt. Context IDs are saved prompt IDs + saved first k generated IDs +
independently encoded suffix IDs. Preserve exact saved cuts/hashes, suffix
round-trip/no-special-token checks and decoded concatenation. Never re-encode the
combined context, add another thinking block or user turn, close/reopen the
assistant, add the answer, or remove the original instructions.

Use the original pinned Qwen3-32B revision
`9216db5781bf21249d130ec9da846c4624c16137`, BF16 without quantization,
enable_thinking=False, eager attention, batch one, greedy overrides and original
hardware/byte/dependency checks. Each uncached query has exactly the existing
maximum budget of 16 and capture_at=(). No custom stopping, candidate scoring,
logits/hidden-state collection, judges or original trajectories are added.

## Field parser

Validate the entire raw return: integer nonnegative token IDs, at most 16 tokens,
exact decoded text, finish/EOS consistency, no unexpected special tokens and no
logits capture. A no-EOS length stop must contain exactly 16 tokens. A malformed
payload cannot be a valid measurement even if it contains a plausible field.

Parse generated text only. Its first ASCII double quote closes the prompt's open
field. No quote means an incomplete invalid field, including an exact label
followed by EOS. Strip whitespace from everything before the first quote and
accept only exact uppercase A, B, C or MISSING. A valid wrong label is incorrect.
An empty field, prose, multiple labels, or curly quote cannot pass. Later answers
cannot rescue the first field; never extract convenient letters or default to
MISSING. Preserve complete raw text and the text after the first closing quote.
Trailing ordinary text is diagnostic and cannot change the first-field score;
payload-integrity checks still apply to the whole return.

A completed valid field does not require EOS and stays valid if the whole
generation reaches its 16-token limit after closing the field. Report field
completion, validity, correctness, EOS, generation length stop, token count and
metadata errors separately. Incomplete fields and length-stopped generations are
different properties. No post hoc parser relaxation or budget/wording adaptation.

## Same population, calibration and analysis

Reuse the 56 worlds 004–059, both variants, original framing, visible reasoning:
112 trajectories. Use only existing eligible fixed/0 (112), fixed/256 (112) and
fixed/512 (108) contexts: 332 main queries, four unchanged exclusion entries, and
664 existing legacy cue readouts. Do not select by answer or preference. Do not
rerun original reasoning, original-question scoring, judgments or Study 2B.

The four pilot worlds remain excluded from main. Calibration is twelve new v2
queries: eight source-present original-visible k=0 contexts and four deduplicated
literal-MISSING controls. Only the target Verified cell changes; both modified
variants must be byte-identical. Only those four prompts are rendered with the
original template. All calibration prefixes are empty. All twelve raw payloads
must be well-formed with complete valid correct first fields before main starts.
Any incorrect, invalid, failed or ambiguous calibration blocks main permanently
under this version. No automatic tuning, reruns or alternate interface.

Keep both old cue analyses, class-token-only preferences, exact tie handling,
ABC mass, newline-inclusive sensitivity, and distinct saved natural answers.
Accuracy uses all returned payloads, including incorrect/invalid/incomplete
fields; unavailable calls are excluded with coverage reported. Length stop alone
does not make a completed valid field incorrect. Paired comparisons use identical
eligible trajectories and jointly preserve variants, cuts and cues. Bootstrap
2,000 whole-world resamples with seed 2026101601. The 108-case 512-token cohort
must use its own paired baseline; no favorable-cue selection.

## Identity, failure and resume

V2 has independent content-bound plans, journals, reports and output, outside both
source trees and v1 output. Include the v1 reference and reason for revision in
provenance. If available, inspect v1 artifacts read-only, retain actual hashes,
validate its old journal/old-parser verdict and preserve FAILED. If absent, mark
actual evidence unavailable without inventing hashes. V1 replies are not v2 cache
hits. V2's contract covers its code/protocol plus the unchanged v1 contract and
all helpers/dependencies it covers. Do not change historical or v1 hash checks.

Lock v2 output and validate/index its worklist before weights/CUDA. No executable
work means zero loads. One fresh invocation can load once, run calibration and
then main only if all twelve pass. Each backend exception durably records its
failed operation and immediately ends further dispatch. Subsequent operations
stay never-started. Resume skips failed/ambiguous and returned operations and
executes only genuinely never-started work; unresolved calibration still blocks
main. Wrong, invalid and length-stopped returns are terminal cached returns, not
backend exceptions. Persist raw returns before parsing and reporting; interrupted
report creation recovers from raw journals without inference. Never change output
to evade a cache. No live operation or archive command overwrites v1.

Maximum fresh work: 344 short generations, 5,504 output tokens, at most one model
load. A calibration failure prevents all 332 main calls. Fully cached runs load
zero models. Timing comes only from planned operations. These are work bounds,
not elapsed-time or price predictions.

Interpretation: this measures source-cell recoverability under an explicit query
at a saved prefix. The model may reread the table; it does not establish retention
and deliberate overriding during uninterrupted reasoning or an endogenous causal
mechanism. Disclose v1's failed calibration and the pilot-informed v2 revision.
