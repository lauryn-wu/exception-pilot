# Study 2 v2: two linked experiments, one trajectory collection

This version supersedes v1 **for new runs only**. The original protocol, runbook,
previews and all prior output directories remain intact. V1 is reproducible at
GitHub commit `1be7551d058f5d7db64c16cb8ffa6e42ae01ac91`. V2 refuses to resume or
reinterpret a v1 plan; use a separate output directory and the versioned config.
No real-model validation has run in this implementation session: **PENDING**.

Reuse the existing worlds generator, one-shot collection, exact token-ID backend,
atomic operation journal, candidate sequence scoring and repair machinery.
No forced entry/slot, new-turn reconsideration, or new experiment using raw logits.
The four pending studies and Study 1's experimental design are unchanged.

## Shared collection, interface and selection

The unmodified response runs uninterrupted to EOS or its fixed 512-token cap.
A cap hit remains a retained truncated/invalid answer. No answer cue is inserted
into this response. Save original prompt and generated token IDs, full text,
termination status, model-file/tokenizer hashes, template, precision/device,
software versions and greedy decoding configuration. The original table and query
are fixed. The existing prompts have no preliminary entry. If a leading COPIED,
INITIAL, INITIAL_ANSWER or FIRST_VALUE entry is present, the edit checker protects
it. The same saved trajectories supply both 2A and 2B.

V2 supports **plain visible assistant prose only**. Apply the model's saved chat
template to the one original user message, with add_generation_prompt=True and
return_dict=False, exactly once. Resume with original prompt IDs followed by
saved assistant prefix IDs. There is no new role boundary or user message.
`enable_thinking=true` is rejected. For a template supporting that option, freeze
`enable_thinking=false`. Known open `<think>`, `[THINK]`, or analysis-channel
formatting is rejected rather than silently inserting closure/control tokens.
A different thinking interface requires a separately specified and calibrated
protocol. The exact template and kwargs are saved; this is not a universal claim
that every model template is supported.

Selection: 12 fresh worlds, seed 2026101321, G-prefixed plates. Confirmation:
24 fresh worlds, seed 2026101322, H-prefixed plates. Label-role/climate balancing,
two recorded variants, last-row target and direct/visible prompts are inherited.
V2 world IDs and draws are distinct from v1. There are 48 selection and 96
confirmation trajectories. Prompts/model/interface cannot change on confirmation
outcomes; config and source hashes enforce stage identity.

A selection model/interface must reproduce a relevant behavior before confirmation
can be prepared: by default at least 20/24 direct answers correct, at least three
matched pairs with direct correct and visible choosing the misleading pattern,
spread over at least two worlds. Invalids remain in denominators. These positive
minimum counts are configurable BEFORE selection and saved in the config; they
are a practical replication rule, not significance thresholds. A failed calibration
blocks confirmation. The lock includes the measured counts, thresholds, full
selection collection hash, backend identity and explicit selection note. Changing
these after looking at results is exploratory and needs a newly declared selection
protocol; it cannot turn old selection outcomes into prospective confirmation.

## 2A — Checkpoint answer preferences

After collection, branch from generated-token counts 0, 32, 64 and 128. Zero is
the pre-reasoning baseline. A cut is eligible only before termination and before
the first literal ANSWER: marker appears in the supplied prefix, with a stable
text boundary and no internal special tokens. Do not move unavailable cuts to
convenient locations. A cut may be mid-sentence or mid-word; this is why arbitrary
A/B/C next-token logits are NOT the answer-preference outcome.

Each disposable probe contains exactly:

`original_prompt_ids + original_response_ids[:k] + encode(cue, add_special_tokens=False)`

The primary cue is **`\nANSWER:`**. The optional small sensitivity check adds
**`\nFinal answer:`** at k=0 and k=64 by default. Config permits one primary plus
at most two alternatives and a subset of the existing checkpoints. Freeze cues
and cuts before collection; report every configured alternative. No future
reasoning or original final answer is in any probe context. Probe results never
enter a trajectory or a natural 2B continuation.

Candidate strings are exactly ` A\n`, ` B\n`, ` C\n`, including the leading space
and trailing newline. Validate both standalone and full-context decoding of cue
and candidate tokens, and reject added special tokens. Score ALL tokens by
teacher forcing and sum their conditional log probabilities, without length
normalization. Save candidate strings, token IDs, per-token log probabilities,
sequence log likelihoods, candidate log mass and probabilities normalized only
across these three candidates. Different candidate token counts are retained.

Primary 2A: world-mean change in gold-versus-pattern log odds, k=64 minus k=0,
requiring both variants in that world's comparison. Report all cuts, coverage,
cue-sensitivity changes and descriptive strata for correct, wrong and invalid
original final answers. Never choose checkpoints or cases because of their shift.
Outcome-stratified summaries are descriptive, not causal comparisons. Readouts
are **answer preferences under a checkpoint readout**, not internal beliefs or
probabilities of arbitrary natural completions. Outputs: measurements.json and
study-2a-summary.json, separately from 2B.

## 2B — Within-reasoning text interventions

Review all visible outputs, including correct, wrong and invalid answers. The
prespecified candidate is the FIRST explicit false assertion that the target's
verified class is absent. Annotate exact original `statement_span` and `statement`,
plus the potentially narrower replacement `span` and `old` text. Require manual
truth-based justification, first-statement certification, grammatical-repair and
meaning-control certification. Automated string checks cannot certify semantics.

**Branch immediately after the candidate statement**, independently of 2A cuts.
Use the first original-token boundary at the statement end; it may include only
trailing whitespace if the tokenizer joins that whitespace to the statement.
Never include any subsequent non-whitespace reasoning. If no such stable token
boundary exists, record the case as ineligible, without moving the cut. Require
unchanged text/token round-trip identity. The boundary catalog is computed AFTER
original generation. A statement after the original final-answer marker is
ineligible. Statements beyond token 128 can qualify if before that marker.

Preserve the complete table/prompt, preliminary entry and every preceding
character outside the exact edit. Four arms reuse v1: unchanged; availability
repair; meaning-preserving rewording of the original false statement; explicit
value repair (secondary). Example availability repair: “Its verified class is
recorded in the table.” It adds no standalone A/B/C letter, and whole-prefix class
letter counts cannot increase. The meaning control preserves the original claim,
not its truth; example “Its verified class is absent from the table.”

Each arm generates a FRESH natural suffix from its own prefix, with the same
remaining budget 512-k. Never paste back the original subsequent reasoning/final
answer. Never put a 2A cue into these generation inputs. No past_key_values are
passed between calls: recompute the entire edited prefix, which includes every
position from the first changed token onward. Save both spans, boundary, edited
strings, exact tokens, token-span/length changes, raw new suffix, full decoded
response, termination and final-answer validity. A separately scored conditional
readout at the edited boundary remains a secondary measurement branch.

Freeze the edit manifest before any edited generation. 2B no longer requires 2A
to run first. If 2A results guided edit choices, label the review
`2A_informed_discovery`; that is accepted only for selection/discovery. Confirmation
requires the predeclared first-statement rule and explicit attestation that 2A did
not determine selection. Prefer freezing confirmation edits before running 2A.
No final-correctness filtering. Retain every eligible case and every branch,
including wrong, invalid, unchanged and harmful outcomes and validation failures.

Primary 2B: availability-repair minus meaning-control final accuracy, averaged
within world then across complete worlds. Unchanged and value-repair comparisons
are secondary. Report contrast-specific coverage and full-plan accuracy bounds,
allowing unknown scores to be 0 or 1. Report paired readout differences separately.
Use the existing 10,000 whole-world descriptive bootstrap; degenerate intervals
do not establish certainty. The selected error cohort does not estimate prevalence.
Changing text also changes phrasing, tokenization and potentially length: effects
are conditional continuation effects, not proof of an internal belief or mechanism.
Outputs: edit-plan.json, interventions.json and study-2b-summary.json.

## Shared real-model replay validation (supporting infrastructure)

`validate` explicitly runs the existing three technical prompts. A forward hook
observes selected raw next-token logits DURING uninterrupted greedy generation;
it returns no replacement output and inserts no probe. Save vectors only at
requested cuts (technical 1/8/16/32; original trajectories 0/32/64/128). These
un-cued logits are used to test replay fidelity, not reported as answer preferences.
This increases disk usage but does not save all vocabulary vectors at all tokens.

Compare raw logits and softmax probabilities over the ENTIRE vocabulary with a
fresh exact-prefix replay; do not compare just top-k or A/B/C. Defaults, frozen in
config: logit atol=1e-4, rtol=1e-4; probability atol=1e-5, rtol=1e-3; total variation
<=1e-4. Elementwise comparison uses atol+rtol*abs(reference). Record max errors,
allclose flags, total variation and argmax agreement. Also require exact whole
suffix token identity, EOS/finish agreement and exact original prompt/prefix IDs.
All available technical cuts must pass, with at least one per prompt. Missing,
nonfinite or malformed vectors fail validation. Greedy token agreement alone is
insufficient. Do not relax tolerances after inspecting edited outcomes.

2A repeats both distribution and suffix checks at each eligible scientific cut.
2B's statement cuts are not known during original collection: regenerate a fresh
UNINTERRUPTED reference from the original prompt, capturing the distribution at
that cut, require its entire output to match the saved original, and compare a
fresh unchanged-prefix replay. Then generate the randomized four-arm branches;
also validate the unchanged arm's distribution/suffix. This extra reference is
validation only; none of its later tokens are supplied as edited continuation.
Failure retains the case but blocks interpreting it as a validated intervention.

Prepare/analysis mark real validation PENDING until real checks run. Mock reports
always retain real-model status PENDING and validated_same_response_interventions
=false, regardless of mock test success. Real technical success is not a universal
certificate: each intervention must also pass its own checks. Local model weights,
GPU resources and real behavior remain untested here. Exact commands are in
CONTINUATION_V2_RUNBOOK.md. No paid API, cloud launch or model download is authorized.
