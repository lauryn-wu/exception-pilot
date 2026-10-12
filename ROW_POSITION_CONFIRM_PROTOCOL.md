# Fresh-world confirmation: target row × response instruction

Status: freeze the complete design, generated worlds, requests, analysis, and
coding instructions before any live collection. This study is a confirmation on
fresh draws from the existing generator family. Preparing, analyzing, or reviewing
traces does not make model calls or authorize another experiment.

## Question and scope

Does placing an explicit target record at the last rather than the first row
increase the accuracy cost of asking for visible reasoning on fresh worlds?
The development experiment relocated the same target among rows 1, 5, and 10 of
24 previously inspected worlds. This study uses 24 newly generated worlds and
all ten rows. The first-versus-last interaction is the sole primary contrast;
the other rows describe the shape of the position effect.

The intervention preserves the target record's contents and the relative order
of the other nine records. It changes the target's location and necessarily
shifts intervening rows. This identifies the effect of that specified
rearrangement under the frozen prompts. It does not isolate an internal attention
mechanism, prove that the last record is treated as an unlabeled query, or show
that position explains all reasoning errors.

Position sensitivity and contradictory explanations are known phenomena. The
specific question is a short-table position-by-response-instruction interaction
on explicit records that conflict with a background pattern. Neither a successful
confirmation nor contradictory traces establish a novelty claim. Fresh draws
test replication within this generator family, not generalization to new tasks,
table formats, wordings, providers, or model versions.

## Worlds, balance, and requests

Generate **24 fresh worlds** using seed **2026101202** and the existing query-form
generator family. Cross all six assignments of the three distinct labels to
`record_1`, `record_2`, and `pattern`, with two target climate categories and two
worlds per combination: **6 × 2 × 2 = 24**. Each world has a ten-record table and
two target-record variants. Changing the variant changes the target's recorded
class between its two assigned labels while the pattern label stays distinct.

Use the existing `U`-prefixed plate format, with new unique plate identities
excluded from the 24-world development cohort's identities. World identities are
also new.
Preserve the generator's nuisance-attribute and description rules. No historical
model response determines whether a generated world is retained, altered, or
replaced. Store every generated world, its original order, and provenance in the
frozen plan before collection; historical answers are not observations in this
study.

For each world and variant, remove the target from its original order and insert
it at displayed data row **1 through 10**, excluding the header and separator.
Preserve all other rows in their original relative order. Within each
world/variant/response arm, table row order is the only provider-request change
across positions.

Cross two target variants × ten positions × two response instructions:
**40 tasks per world, 960 planned responses**. Deterministically shuffle both the
world order and the 40 tasks within each world and freeze the resulting schedule.
Each task is an independent request with exactly one user message and no history
from other calls.

Retain the query-form study's `INTRO`, seven-column table, and `QUESTION`. Use only
the key query, `License plate: {target_id}`. There is no profile query or filler
arm. The two response instructions are unchanged:

- Direct: `Output only ANSWER: followed by A, B, or C.`
- Visible: `Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.`

Answer keys and preview annotations are never included in provider messages.
`prepare` writes the immutable plan and provider configuration, content hashes,
and machine-readable and readable request previews. The study is isolated in
`exception_row_position_confirm`, with configuration
`configs/row_position_confirm_mistral.json` and a distinct run directory.

## Provider and execution

Use **mistral-small-2603**, temperature **0**, `reasoning_effort="none"`, and
`max_tokens=1600` in both arms. The manipulation concerns visible response text;
the provider's hidden reasoning setting is disabled. Use the existing Mistral
endpoint, a **120-second timeout**, and a cumulative cap of **1056 attempts**.
Read credentials from `MISTRAL_API_KEY`; never save them in plans or journals.

Freeze the protocol, study source, imported generator dependencies, configuration,
worlds, schedule, and exact requests before the first API call. Resume must verify
the same immutable artifacts and the attempt journal. Keep this checkout's code
and configuration unchanged throughout collection. Do not resume a development
run as a confirmation run or combine their answers in the primary estimate.

The runner atomically records each attempt before and after its single provider
request. There are no hidden retries. Returned invalid or truncated answers are
terminal observations and cannot be replaced. Known transport errors may be
retried only with explicit `--resume --retry-errors`, within the attempt cap.
An unresolved started request requires review because a returned answer may
exist. A reported model mismatch stops collection; missing or wrong observed
model identity prevents a scientific confirmation decision.

The first **40 calls** are a technical check of one complete world. If execution
is sound, resume the remaining **920 planned tasks**, irrespective of interim
accuracy. Do not choose a smaller sample after observing a promising result or
extend the sample after an inconclusive result. A mock run is prominently marked
**SIMULATED**, cannot be resumed live, and cannot produce scientific confirmation.

## Scoring, primary contrast, and uncertainty

Parse final labels without consulting the answer key. Retain raw requests and
responses, returned model identity, parse validity, strict final-answer format,
direct answer-only adherence, visible pre-answer-text adherence, output lengths,
token usage, and pattern-label choices. Formatting or correctness cannot be used
to select a preferred retry.

For a valid answer, accuracy is 1 for the recorded target class and 0 for either
other class. Missing or invalid answers remain unknown. For world `w`, position
`p`, and arm `a`, let `A(w,p,a)` average accuracy over its two target variants.
Define reasoning harm and the primary interaction as:

`H(w,p) = A(w,p,direct) - A(w,p,visible)`

`Delta(w) = H(w,10) - H(w,1)`.

The primary estimate is the mean of `Delta(w)` over complete endpoint worlds.
Positive values mean more reasoning-related harm at the last row. The contrast
ranges from -2 to 2; **0.20 is 20 percentage points**. It is an accuracy
interaction, not a correlation between original position and world difficulty.

A complete primary world needs only its **eight endpoint responses**: two
variants × rows 1 and 10 × two arms, all valid. An invalid or missing intermediate
response must not discard an otherwise complete primary world. Each secondary
contrast uses its own required cells and reports its own complete-world count.
Variants are averaged within world before analysis; they are not independent
replicates.

Bootstrap **whole worlds** 10,000 times with seed **981723**, preserving all paired
variants, positions, and arms. Report 95% percentile intervals, per-world
contrasts, and the complete-world denominator. Report the exact two-sided sign
test on nonzero world contrasts with ties separately. The sign test describes
sign balance, not whether the mean is zero or exceeds 0.20; it is not a decision
gate. Secondary intervals are descriptive and unadjusted for multiple comparisons.

Also compute full-plan bounds across **all 24 worlds**: hold valid observations
fixed and allow each missing or invalid accuracy independently to range from 0
to 1, retaining the sign and magnitude of every contrast coefficient. These are
missing-data bounds, not confidence intervals. They neither count unknown
answers as observed mistakes nor authorize resampling them.

## Secondary analyses

Report the 20 position/arm cells and all ten `H(p)` values, including correct,
wrong-pattern, other-wrong, invalid, and unreturned counts. Display both direct
and visible accuracy so their contributions to the interaction are apparent.
Prespecify the following shape checks, averaged within worlds:

- First-row boundary: `H(2) - H(1)`.
- Last-row boundary: `H(10) - H(9)`.
- Middle versus endpoints: `(H(5)+H(6))/2 - (H(1)+H(10))/2`.
- Each arm's endpoint shift: `A(10,a) - A(1,a)`.

Report record sensitivity as a separate secondary score: +1 for the target's
recorded class, 0 for the pattern class, and -1 for the other target-variant
class. Apply the same pairing and signed unknown-answer bounds. This score does
not replace primary accuracy or determine the confirmation decision.

The row curve can distinguish gradual change from sharp boundary effects within
these ten-row tables. It cannot alone distinguish table parsing, example/query
role confusion, competing label patterns, or a particular internal mechanism.
Any further mechanistic manipulation requires a separate proposal and freeze.

## Fixed decision rule

Require all **960 tasks** to have returned responses, valid or invalid, before a
scientific decision. Transport errors alone do not complete a task. Evaluate
the following rules in order; integrity failures are hard errors:

| Condition | Decision |
|---|---|
| Mock execution | `simulated_only` |
| No execution | `not_started` |
| Fewer than 960 returned task responses | `incomplete` |
| Missing or wrong returned model identity | `model_identity_failure` |
| Any of the 20 position/arm cells has less than 95% planned output adherence | `output_manipulation_inconclusive` |
| Fewer than 22 complete endpoint worlds | `insufficient_complete_worlds` |
| Primary estimate >= 0.20, full-plan lower bound >= 0.20, and interval lower endpoint > 0 | `confirm_positive_interaction` |
| Primary estimate <= -0.20, full-plan upper bound <= -0.20, and interval upper endpoint < 0 | `reverse_effect` |
| Degenerate primary bootstrap interval, with neither large-effect condition met | `inconclusive` |
| Nondegenerate interval and full-plan bounds both strictly inside (-0.20, 0.20) | `smaller_than_target` |
| All other complete outcomes | `inconclusive` |

Each adherence denominator is the **48 planned responses** in that position/arm
cell. Direct requires answer-only output and visible requires pre-answer text;
each cell therefore needs **at least 46/48** adherent outputs. Adherence measures
the output manipulation rather than cosmetic strict-format matching. Retained
invalid outputs remain in the audit and may prevent adherence or endpoint-world
gates from passing. Missing intermediate rows can block completion and adherence
even though they do not remove complete endpoint worlds from the primary estimate.

The small-effect rule requires the envelope of the interval and full-plan bounds
to lie strictly inside (-0.20, 0.20). It means the observed endpoint interaction
is smaller than the prespecified practical target under this rule; it is not
equivalence, absence of any position effect, or evidence that all rows behave
alike. A reversed interaction is reported explicitly rather than called support
for the predicted direction.

A uniform large interaction may meet a large-effect decision despite a degenerate
bootstrap interval, but must retain a warning that the interval cannot calibrate
population precision. A uniform small or zero result cannot pass the
`smaller_than_target` gate. No result automatically starts another experiment.

## Manual trace audit

The trace review is separate from accuracy scoring and the primary decision.
Its scope is the **480 planned visible responses**. Export raw response text,
the target's actual supplied input row, task metadata, and answer outcome for
manual review, including correct, incorrect, and invalid returned visible
outputs. Use the linked raw attempt to inspect the full request when needed.
Do not prefilter to traces containing a keyword or to model mistakes. Direct
responses remain in the accuracy and adherence analyses, outside this trace
review denominator.

Code three observations independently:

- `false_missing`: an affirmative assertion that the target's recorded class is
  absent or unknown, contradicted by the actual supplied table. Exclude negated
  assertions, hypothetical conditions, and statements that a repeated query omits
  a class while acknowledging that the table supplies it.
- `self_contradiction`: two incompatible claims about the same target's class
  within one generated response, supported by two exact excerpts. Distinguish an unresolved
  contradiction from an explicitly acknowledged correction; do not count a
  transparent correction as an unresolved contradiction.
- `gold_then_override`: the response correctly identifies the target's recorded
  class and later chooses a different final answer, with exact evidence for the
  identification and the incompatible answer. Reading the gold value followed
  by a correct answer does not qualify.

Review against the actual request, not only expected-label metadata or a keyword
coder. The JSON annotation contains one nullable boolean per code plus separate
evidence arrays, an annotator, and a comment. Positive labels require exact
response quotations; contradictions require at least two distinct exact excerpts.
Any positive or negative judgment requires a nonempty annotator and comment.
Unsupported, ambiguous, unreviewed, or unavailable cases remain `null` (unknown)
rather than false. Record explicit negative judgments only after review. An
output can receive more than one positive label. No LLM judge is used.

Report planned, returned, reviewed, positive, negative, and unknown denominators
for each code, by position and correct/wrong/invalid answer outcome. A partial
review describes only the reviewed subset; do not divide its positives by all
480 planned visible responses as a prevalence estimate. Traces show what the
text asserts, not which hidden computation caused the final answer. Preserve
the raw run and keep review annotations in a separate review file.

The review file binds to the frozen plan, configuration, and complete attempt
journal digest. Export refuses to overwrite an existing review file. Additional
attempts make an earlier export stale; export to a new path and review the new
snapshot instead of silently merging annotations across different journals.

## Commands

Run from the repository root with Python 3.10 or later. Tests and preparation
are offline:

```sh
python3 -m unittest discover -s tests -p 'test_row_position_confirm*.py' -v
python3 -m exception_row_position_confirm prepare \
  --config configs/row_position_confirm_mistral.json \
  --output runs/row-position-confirm-mistral-001
```

With `MISTRAL_API_KEY` already set, run the fixed collection on macOS:

```sh
caffeinate -i python3 -m exception_row_position_confirm run \
  --config configs/row_position_confirm_mistral.json \
  --output runs/row-position-confirm-mistral-001 \
  --max-calls 40

caffeinate -i python3 -m exception_row_position_confirm run \
  --config configs/row_position_confirm_mistral.json \
  --output runs/row-position-confirm-mistral-001 \
  --max-calls 920 --resume

python3 -m exception_row_position_confirm analyze \
  --output runs/row-position-confirm-mistral-001
```

Omit `caffeinate -i` outside macOS. `--max-calls` limits new attempts in that
invocation. With no transport errors, the two commands make 40 and 920 calls.
Explicit retries consume attempts too and may require another resume within the
1056-attempt cap. Never retry a returned invalid answer. Analysis is offline.

Export a separate manual review file, complete its judgments, then summarize it:

```sh
python3 -m exception_row_position_confirm trace-export \
  --output runs/row-position-confirm-mistral-001 \
  --review-file runs/row-position-confirm-mistral-001/trace-review.json

python3 -m exception_row_position_confirm trace-summarize \
  --output runs/row-position-confirm-mistral-001 \
  --review-file runs/row-position-confirm-mistral-001/trace-review.json
```

For a wholly offline integration run, prepare a separate directory such as
`runs/row-position-confirm-mistral-SIMULATED`, then use `run --mock` with that
directory for all 960 tasks. Never reuse it for live collection. Keep concurrent
experiments in separate output directories.
