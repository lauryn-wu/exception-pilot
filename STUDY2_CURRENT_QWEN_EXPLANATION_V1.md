# Matched explicit-explanation diagnostic, version 1

This follow-up asks whether an explicit written-explanation instruction causes
evidence-use errors on the completed Qwen3.8 screen's original-wording cases.
It is a matched diagnostic. It does not establish a novel mechanism or supply
sufficient evidence for a paper.

## Evidence and fixed population

The source is `results/current-qwen-screen-v1/screen-evidence-20261022T214422Z.zip`
at results commit `eb03109e85fe932c09e305b345275011e358dc71`.
Its SHA-256 is `bb0e059f8a44a69b33990998b672e245405c4ca67c2d7d9214113283a6c9d31a`;
the sealed source plan is `edda713e841caafcd34d86f299d60a07cbde93a1b3d563a27ecfd13b7a4f52f6`.
The unchanged source code contract is
`701262504d095b23d2d3320fb1ec794647b55b1064c07bb9788eb8a4547b9998`.

Preparation checks the ZIP digest, its full member inventory and checksums,
all sealed JSON members, the embedded design, official rendered requests,
request/start/return/dispatch/invocation bindings, actual returned input IDs,
resolved sampling settings, and raw token/text/EOS identity. Historical final
answers are rescored with the original parser. The expected class is checked
against the actual target table cell. Analysis summaries are not evidence for
these checks. The original eight passing technical-smoke records and their
saved-prefix bindings are verified; no further technical calls are scheduled.
The source is read directly from the ZIP. Archived absolute paths are never
followed to obtain source evidence. Preparation copies the ZIP, startup log,
and checksum inventory unchanged into the new output directory.

Select the 96 original-wording, thinking-OFF cases from the frozen source
request order: 24 worlds × two recorded-label variants × two background cues,
with 48 support and 48 conflict cases. Do not regenerate worlds. Retain the
matched 96 OFF/direct and 96 native-ON controls as completed evidence, scored
under their original answer-only rule. They never enter the new dispatch queue.

## The only prompt change

Assert the original answer-only suffix, then replace it with exactly:

> Think step by step before answering. Write your reasoning, then put a single uppercase letter—A, B, or C—alone on the final line.

All preceding UTF-8 bytes remain identical. There are no added answer cues,
MISSING clauses, scaffolds, minimum explanation lengths, or continuations.
Each new response is uninterrupted from the new prompt, with the official
thinking-OFF chat template and its original empty thinking block intact.
The explanation is ordinary assistant output. Each request has a separate
protocol/cell identity and hashes, and binds both source controls and the
source archive, operation, plan, startup-log, and smoke evidence.

All original settings are imported: Qwen/Qwen3.8-27B revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, BF16, no quantization,
one sampled response, temperature 1.0, top_p 0.95, top_k 20, min_p 0,
source per-request seed, 4096 output tokens, and every remaining sampling,
runtime, template, EOS and engine setting. This adds exactly 96 requests and
at most 393,216 generated tokens. There is no lookup arm, repetition, judge,
probe, steering, or native-ON-plus-explanation arm.

## Runtime and immutable execution

Reuse the existing pinned environment: Python 3.12, vLLM 0.26.0, torch 2.11.0,
transformers 5.8.0, tokenizers 0.22.2, huggingface-hub 1.7.1, jinja2 3.1.6.
Use the existing Tokenizer and Backend unchanged. Set
`VLLM_USE_FLASHINFER_SAMPLER=0` before vLLM initialization and record it in the
new plan, execution and invocation records. The historical startup log begins
with that setting (SHA-256
`0941eaab54b838e459e127caa53a7d7aa3cd6b25634778f309ab17738dc0b0a1`).
That log is separate evidence; the old backend identity omitted the setting
and remains unaltered.

Live execution requires the exact backend identity from the passing archived
smoke, including hardware/runtime metadata. The completed screen used an RTX
PRO 6000 Blackwell Server Edition with CUDA 13.0. A different backend identity
stops before generation. Do not silently loosen this check or run another smoke.
No package upgrades or model downloads are performed by this package.

The default is offline. `run --live-qwen` loads the model once when pending
work exists, then attempts the full fixed set. `--max-new` may bound an
invocation; its requests count toward the same 96. Only never-started requests
are resumed. Returned wrong, verbose, malformed or truncated outputs remain
cached. The first new backend exception stops that invocation. Failed and
ambiguous attempts remain visible and held; later never-started work can run
after the runtime problem is fixed. Explicit `recover` only quarantines
recognized atomic-write debris. It never promotes an uncertain return,
resends an attempt, or supplies a replacement. A complete queue loads no model.

Reports distinguish historical controls, newly dispatched and newly returned
explanations, cached explanations, never-started work, failed calls, and
ambiguous calls. Changed prompts are never cache hits on source responses.

## Parsing

The explanation parser is separate from the answer-only parser. It verifies
actual input IDs, token/text identity, full resolved sampling, output budget,
EOS and backend finish/stop reasons. Unexpected structural tokens (including
native thinking markers) make the output malformed. Only a trailing EOS token
may be removed for scoring; it remains in the raw return.

The last nonempty line must be exactly `A`, `B`, or `C`. A line terminator is
allowed; surrounding spaces, punctuation, prefixes and earlier letters are
not answer fallbacks. A truncated return never yields a valid final answer.
The complete raw tokens/text, ordinary text, preceding explanation, final
line, and its character offset are retained. Wrong labels, invalid format,
malformed channels/metadata, missing answers, truncation and unavailable
infrastructure are reported separately (flags may overlap).

Answer correctness and explanation format are separate. A label-only output
can be correct while `explanation_format_compliant` is false. Nonempty text
before a valid final line satisfies the observable format check; no minimum
length is imposed. A brief record lookup is allowed. Whether the text actually
provides an explanation is a separate manual annotation, initially
`not_reviewed`; arbitrary preceding text is not automatically certified.

## Predeclared analysis

The primary contrast is

`(explanation support accuracy − explanation conflict accuracy) − (OFF/direct support accuracy − OFF/direct conflict accuracy)`.

Positive values mean an additional conflict penalty under the explanation
instruction. Report all three arms' support/conflict accuracies, paired
correctness transitions against each control, and conflict errors that choose
the pattern label versus the other wrong label. Native-ON comparisons are
descriptive. Without native-ON-plus-explanation, this design cannot show that
native thinking protects against an explanation request. It also does not
separate the written text from the instruction's effect on task interpretation.

Record sensitivity compares variants at fixed **world and cue_state**.
Support/conflict changes across those variants and is not the pairing key.
Cue sensitivity compares cue states at fixed **world and variant**. Each arm
has 48 planned pairs per measure. Show eligible, unscorable and unavailable
pairs, label changes and the eligible denominator. Invalid or truncated output
is unscorable, never silently counted as a label change.

Use fixed-budget denominators. Invalid/truncated returned answers are
unsuccessful outcomes. Infrastructure-unavailable cases are conspicuous;
incomplete arm accuracies and the primary contrast stay undefined, with
accuracy bounds reported. The primary uncertainty calculation retains the
source's four construction-block bootstrap (six worlds per block). The
24-world bootstrap is a sensitivity analysis. Ninety-six responses are not
96 independent worlds. An all-perfect bootstrap interval reflects the observed
sample; it does not establish population certainty.

## Exploratory review and interpretation

The export includes all new raw returns, matched control evidence, prompts,
provenance, journals, checksums, a readable trace file, and a review CSV.
Five overlapping annotations start as `not_reviewed`: correct record mention,
factual false-absence claim, induced-rule justification, target row used as
evidence for a rule, and explanation compliance. Quote fields use zero-based,
half-open Unicode offsets in raw_explanation. No automated semantic judge or
keyword classifier is added.

These are interpretation guidelines, not an automatic gate:

- Near-perfect conflict accuracy with record-based explanations weakens the
  current mechanism direction.
- A substantial, mostly pattern-directed conflict decline across multiple
  worlds, with support accuracy retained, supports further investigation.
- Formatting/truncation problems, or similar support and conflict degradation,
  do not establish the proposed phenomenon.
- A few scattered errors are inconclusive.

Stop after the fixed 96 requests. Preserve failed and null outcomes. Do not
expand the experiment automatically in response to the results.
