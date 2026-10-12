# Target row × response: verified-facts-row-position-v1

Status: freeze this plan before new collection. This is a **development experiment
on previously inspected worlds**, motivated by the retrospective row audit. It
is not a fresh-world confirmation. No live calls or subsequent experiment are
launched by preparing or analyzing this study.

## Question and scope

Does moving the same target record from the first to the last row change the
accuracy cost of asking for visible reasoning? The intervention changes the
target's displayed location while preserving its content and the relative order
of all other records. This tests a causal effect of the specified rearrangement
within the reused worlds. It does not identify an internal retrieval failure or
establish that position explains every reasoning error in the project.

The retrospective audit found lower late-row accuracy in several reasoning
conditions, with important contrary cases. In those runs, each world's table was
shuffled once and then held fixed. Between-world row comparisons could therefore
mix position with plate identity, attributes, label assignments, and surrounding
records. The present study makes position a within-world intervention.

Position sensitivity is already a literature topic; the project cites Liu et al.,
[Lost in the Middle](https://arxiv.org/abs/2307.03172). The narrower question here
is the interaction between target relocation and visible-reasoning instructions
on explicit conflicting records. Neither a positive result nor this citation
establishes a broad novelty claim.

## Worlds and provenance

Use all 24 raw worlds from the query-form source plan with hash
`110bbe5e3f1dd1cc1b5967c3c2cdd8e52a35c6f266fec6d2215107de019cd74a`,
retaining their original identities and data. Their source identifiers are
`qf-list-000` through `qf-list-023`. Bundle the snapshot in
`configs/row_position_worlds.json`; no historical response is used to select,
filter, relabel, or replace a world. The study does not reuse historical responses
as observations in the new contrast.

The source plan's two target-record variants and background labels are unchanged.
All six record_1/record_2/pattern role permutations remain represented. Copying the
raw worlds preserves their source order; only the rendered table order is changed
for each position condition. Preserve the snapshot provenance and content hash in
the new frozen plan so future runs do not depend on a mutable historical run
directory.

For each source world and target-record variant, remove the target from its
original row order, retaining the other nine records in exactly their original
relative order. Insert the target at displayed data row **1, 5, or 10**, excluding
the header and separator. No class, description, plate, nuisance attribute, table
header, or query text changes across positions. Inserting the target necessarily
shifts intervening rows; this is the defined relocation intervention, not a
claim that all absolute row positions remain fixed.

## Design and prompts

Cross two target-record variants × three displayed positions × two response
instructions in each world: **12 tasks per world, 288 planned calls**. Keep the
24-world order fixed and randomize the 12 tasks within each world using the
frozen deterministic schedule. Each task is a fresh request containing exactly
one user message, with no cross-call conversation history.

Use the same `INTRO`, seven-column evidence table, `QUESTION`, and direct/visible
instructions as the query-form study. The only query form is the license-plate
key: `License plate: {target_id}`. There is no feature-profile query and no filler
arm in this experiment.

Direct instruction:

`Output only ANSWER: followed by A, B, or C.`

Visible instruction:

`Think step by step before answering. Write your reasoning, then put ANSWER:
followed by A, B, or C alone on the final line.`

The exact instruction string has the same spaces and punctuation as query-form;
the line wrapping above is documentation only. Within a world, record variant,
and arm, the three provider requests differ only in the table's row ordering.
Answer keys or preview annotations are never sent to the model.

`prepare` freezes `plan.json` and provider configuration with hashes and writes
human-readable and machine-readable request previews. The new package is
`exception_row_position`; the live configuration is
`configs/row_position_mistral.json`. Existing study packages, configurations,
protocols, and run directories are not changed.

## Provider, scoring, and retention

Use `mistral-small-2603`, temperature 0, `reasoning_effort="none"`, and
`max_tokens=1600` in both response arms. This is a visible-output manipulation
with the provider's hidden reasoning disabled. Use the existing Mistral endpoint,
a 120-second request timeout, and a cumulative cap of **316 attempts**. Credentials
come from `MISTRAL_API_KEY` and are never written to plans or attempt records.

Parse terminal answers without consulting correctness. Preserve the original raw
response and record answer validity, model identity, strict final-answer format,
whether direct output is answer-only, whether visible output contains pre-answer
text, output lengths, token usage, and pattern-label choices. Formatting controls
do not authorize selecting or resampling a more convenient answer.

Returned invalid outputs, including unparseable or truncated responses, are
retained terminal observations and are never replaced. Missing/model-mismatched
identity cannot support a positive scientific decision. Known transport errors
may be retried only by explicit `--resume --retry-errors`; every attempt counts
toward the cumulative cap. There are no hidden retries. An unresolved started
attempt after interruption requires review because it is unknown whether the
request returned an answer.

Write attempt records atomically before and after each single provider request.
Resume checks the frozen design, source, configuration, request, and journal
integrity. A mock run is prominently labeled **SIMULATED**, cannot be resumed
live, and cannot yield a scientific spending decision.

## Estimands and denominators

Let `A(w, p, a)` be accuracy averaged over the two record variants in world `w`,
at position `p` and arm `a`. A correct parsed answer scores 1; an ordinary wrong
parsed answer scores 0. Define reasoning harm at each position as:

`H(w, p) = A(w, p, direct) - A(w, p, visible)`.

The **primary estimand** is the world mean of:

`Delta(w) = H(w, 10) - H(w, 1)`.

A positive value means a larger reasoning-related accuracy loss at the last row;
a negative value means a larger loss at the first row. A value of 0.20 is
20 percentage points. The interaction can range from -2 to 2. This is an accuracy
interaction, not the earlier +1/0/-1 record-sensitivity metric.

The primary complete-world analysis requires only its **eight endpoint cells**:
two variants × rows 1 and 10 × direct and visible. A missing or invalid row-5
response must not discard an otherwise complete primary world. For every
secondary contrast, use and report the worlds complete on that contrast's own
required cells. Do not silently use a common denominator across contrasts.

Report all six cell accuracies, direct-minus-visible harm at each position,
visible and direct first/last contrasts, and `H(w,5) - (H(w,1)+H(w,10))/2`
as the secondary middle-row shape check. Report pattern choices, invalid and unreturned counts, output adherence,
and observed output lengths separately. A pattern-label answer describes a
choice; it does not establish a hidden reasoning mechanism.

Resample **whole worlds**, preserving variants, positions, and arms, 10,000 times
with bootstrap seed `981723`. Report descriptive, unadjusted 95% percentile
intervals and each contrast's complete-world denominator. The secondary exact
two-sided sign test uses nonzero world differences and reports ties separately.
It tests sign balance, not whether the mean interaction is zero or exceeds
20 percentage points. Its p-value is not a spending gate.

Also report full-plan effect bounds across all 24 worlds: hold valid answers
fixed, allow each missing or invalid answer's accuracy to range independently
from 0 to 1, and retain the signs of all contrast coefficients. These bounds are
not confidence intervals. Invalid responses remain visible in all denominators
and audits; assigning their possible scores for bounds does not resample them.

Worlds were inspected before this question and these positions were chosen.
Bootstrap intervals describe variation within this development design; they do
not account for all post-hoc design choices or establish generalization to new
worlds, wordings, model versions, or backend runs.

## Fixed completion and decision rule

Complete the fixed schedule of 288 tasks regardless of interim accuracy. The
first 12 calls are a technical execution check containing one world's complete
12-cell design, not a screen for scientific promise. Do not add worlds, select
successful positions, drop difficult cases, or revise thresholds after observing
the outcomes.

The following is a practical rule for deciding what deserves later review. It
never starts another experiment automatically. The meaningful interaction
threshold is two-sided: **20 percentage points in either direction**.

| Condition, in precedence order | Decision |
|---|---|
| Mock execution | `simulated_only` |
| No execution or incomplete returned schedule | `not_started` or `incomplete` |
| Invalid model/design/configuration identity | `model_identity_failure` or a hard integrity failure |
| Any position/arm has less than 95% planned output adherence | `output_manipulation_inconclusive` |
| Fewer than 22 complete primary worlds | `insufficient_complete_worlds` |
| Estimate >= 0.20, full-plan lower bound >= 0.20, and interval lower endpoint > 0 | `review_fresh_world_confirmation`; last row has more harm |
| Estimate <= -0.20, full-plan upper bound <= -0.20, and interval upper endpoint < 0 | `review_fresh_world_confirmation`; first row has more harm |
| Primary bootstrap interval is degenerate and neither large-effect condition applies | `inconclusive` |
| Nondegenerate interval and full-plan bounds both lie strictly inside (-0.20, 0.20) | `deprioritize_first_last` |
| Other complete outcomes | `inconclusive` |

The returned-schedule requirement means all 288 planned tasks have a recorded
returned response, valid or invalid; transport errors alone do not complete a
task. Output-adherence denominators are **all 48 planned responses in each
position/arm cell**. Direct requires answer-only output; visible requires
pre-answer text. Thus each cell needs at least 46/48 compliant outputs. Retained
invalid responses can still prevent the adherence or complete-world gates from
passing. Row-5 failures can affect the full-schedule/adherence gates even though
they do not remove complete endpoint worlds from the primary estimate.

The small-interaction rule uses the envelope of both intervals: its minimum
lower endpoint must exceed -0.20 and its maximum upper endpoint must be below
0.20. Passing it deprioritizes this first-versus-last interaction on these worlds;
it is not proof of equivalence, a claim that all positions are interchangeable,
or a reason to disregard a secondary middle-row pattern. A confirmation candidate
requires a separately frozen fresh-world study before a general claim. Inspect
all cell means to understand whether either direct or visible accuracy changed.
A constant large contrast across the observed worlds can justify confirmation
review. Its degenerate bootstrap interval is flagged and cannot establish
population precision. A constant small or zero contrast cannot trigger
deprioritization. This distinction avoids discarding a uniform large development
effect while keeping a zero-width bootstrap interval from being treated as
evidence of equivalence.

## Commands

Run from the repository root with Python 3.10 or later. Offline tests and
preparation do not make model calls:

```sh
python3 -m unittest discover -s tests -p 'test_row_position*.py' -v
python3 -m exception_row_position prepare \
  --config configs/row_position_mistral.json \
  --output runs/row-position-mistral-001
```

With `MISTRAL_API_KEY` already set, execute the fixed schedule on macOS:

```sh
caffeinate -i python3 -m exception_row_position run \
  --config configs/row_position_mistral.json \
  --output runs/row-position-mistral-001 \
  --max-calls 12

caffeinate -i python3 -m exception_row_position run \
  --config configs/row_position_mistral.json \
  --output runs/row-position-mistral-001 \
  --max-calls 276 --resume

python3 -m exception_row_position analyze \
  --output runs/row-position-mistral-001
```

Omit `caffeinate -i` outside macOS. `--max-calls` limits **new attempts in that
invocation**, not the cumulative run. With no transport errors, the commands make
12 then 276 calls. Explicit transport retries also consume attempts and may
require another resume within the cumulative 316-attempt cap. Never retry a
returned invalid output. `analyze` performs no live calls.

For an entirely offline smoke run, use a separate directory:

```sh
python3 -m exception_row_position prepare \
  --config configs/row_position_mistral.json \
  --output runs/row-position-mistral-SIMULATED
python3 -m exception_row_position run \
  --config configs/row_position_mistral.json \
  --output runs/row-position-mistral-SIMULATED \
  --mock --max-calls 288
python3 -m exception_row_position analyze \
  --output runs/row-position-mistral-SIMULATED
```

Never reuse the simulated output directory for live collection. Use distinct
output directories for simultaneous experiments, and keep this checkout's code
and configuration unchanged throughout collection and resume.
