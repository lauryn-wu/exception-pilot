# Answer order under a strict JSON interface

Protocol: `verified-facts-answer-order-v1`. Fixed world seed: `2026100893`.

## Question and motivation

Does asking for an explanation affect the answer before any explanatory text
has been generated, and does the order of explanation and answer matter?

The earlier cue study obtained 48/48 correct direct answers, 33/48 with a
reasoning cue, and 23/48 with an explicit request for written reasoning. All
48 cue responses wrote explanations despite the answer-only instruction.
The subsequent constrained-cue study obtained 48/48 in both arms, with every
output obeying its answer-only JSON schema. Those 96 calls reused the earlier
worlds. They did not establish that written explanations caused earlier errors:
the output instruction and constrained decoding also changed.

This new experiment restores an explanation field in two different positions,
with a contemporaneous answer-only control. It is a bounded order/format
diagnostic, not an isolated intervention on internal reasoning or a claim of
novelty. It does not resume the stopped target-availability replay study.

## Fixed design

- **12 fresh worlds × 2 target-record variants × 3 conditions = 72 calls.**
- The six permutations of recorded class 1, recorded class 2, and background
  pattern class each occur once for a cold target and once for a warm target.
- Fresh seed and license plates; no previous responses select cases or enter
  the requests. The task family and table generator remain closely related to
  the previous studies; this is not cross-task or cross-model confirmation.
- Ten accurate vehicle records per world. Both possible target classes
  conflict with the same-climate background pattern. The two variants change
  only the target's recorded class. All target cells are recorded.
- Preserve the earlier introduction, including its MISSING definition, table
  columns, query wording, and administrative audit-marker explanation.
- `gpt-4o-2024-08-06`, temperature 0, one completion per independent conversation,
  equal 1,000-token completion ceilings, 120-second request timeout.
- A deterministic random order of the six requests within each world.
- Hard cap of **88 total attempts**, allowing 16 explicit transport retries.
  An error-free run makes exactly 72 calls. There are no hidden API retries.

## Conditions and exact instructions

`answer_only` ends with:

```text
Output only a JSON object with one field, "answer", whose value is A, B, or C.
```

Both `reasoning_first` and `answer_first` end with the identical instruction:

```text
Output only a JSON object with two fields, "answer" and "reasoning". Set "answer" to A, B, or C and write your reasoning in "reasoning".
```

Every condition uses a strict JSON schema. The answer is a string enum of
`A`, `B`, or `C`; the reasoning field, when present, is a string. Extra fields
are forbidden. The two explanation conditions differ only in the ordering
of schema properties. Their required-field lists are identical:

| Condition | Required serialized order | Illustrative output |
|---|---|---|
| `answer_only` | answer | `{"answer":"A"}` |
| `reasoning_first` | reasoning, answer | `{"reasoning":"…","answer":"A"}` |
| `answer_first` | answer, reasoning | `{"answer":"A","reasoning":"…"}` |

These examples illustrate format; their answers are not included as examples
in model prompts. No instruction says to reason *before* answering in the
answer-first condition. The model knows the requested schema from the start.
Score the single answer field; do not ask for a revision or score a later
class label mentioned in the explanation. The explanation can be conditioned
on an already generated answer in the answer-first condition.

OpenAI documents that Structured Outputs follows schema key order:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
The parser verifies actual order in the raw response rather than relying on
ordinary dictionary equality. Saved request audits likewise preserve schema
order. `preview.json` contains all 72 exact requests; `preview.md` shows the
three schemas and the first world's six requests before collection.

## Output checks and retention

Parse the entire response as JSON, with no fallback answer extraction. Reject
duplicate keys, extra/missing keys, prose or code fences, wrong types or labels,
nonstandard JSON constants, and incorrect key order. Explanation conditions
must contain non-whitespace reasoning text. Nonempty text is an operational
check only: it does not establish substantive, correct, or faithful reasoning.
Record schema compliance, key-order compliance, nonempty reasoning, and text
length separately. Length is descriptive, not a randomized reasoning dose.

Retain every returned response, including wrong answers. A schema/order failure,
empty explanation, refusal, truncation, or model mismatch is retained and stops
collection. Do not retry that response or continue past it. In particular,
a truncated answer-first response is not accepted merely because its answer
field appeared before truncation. Such outcomes remain visible in the journal
and bounds; a failed manipulation does not support the intended comparison.

Only transport errors or interrupted requests without a saved returned response
can be retried, explicitly with `--resume --retry-errors`, within the fixed cap.
An interrupted request may already have incurred a charge. Never delete an
attempt to obtain a replacement answer. Mock runs need no credentials, make
no model calls, are marked simulated, and cannot be resumed as live evidence.

## Analysis fixed before collection

The **primary contrast** is accuracy `answer_first minus reasoning_first`.
Each world first averages its two target-record variants. Complete worlds
receive equal weight. Positive values favor answering before explaining.

Secondary accuracy contrasts are `answer_only minus answer_first` and
`answer_only minus reasoning_first`. Positive values favor answer-only.
Report all three, not only the most favorable contrast. Also report per-arm
accuracy, pattern choices, paired improvement/worsening counts, and record
sensitivity. For target labels r1/r2 and corresponding answers y1/y2:

`S = [I(y1=r1) - I(y1=r2) + I(y2=r2) - I(y2=r1)] / 2`.

S is 1 for correct tracking, 0 for a constant answer, and -1 for reversed
tracking. Changing the target record also changes table label counts, so this
behavior alone does not establish an internal retrieval operation.

Use 10,000 whole-world bootstrap resamples, seed `981723`, for descriptive,
unadjusted 95% percentile intervals. There are **12 sampling units**, not 72.
This small diagnostic targets large differences; uncertain results remain
uncertain. Degenerate intervals do not establish equivalence or certainty.
Each contrast excludes a world if any required response is missing/invalid;
reports expose these exclusions. Bounds for unscorable responses are available
only once all planned responses have returned and are not confidence intervals.
Incomplete, simulated, and failed-manipulation reports cannot establish the
intended scientific contrast.

There is no accuracy-based pass gate and no automatic sample extension. The
first six calls are an execution/order check, not a scientific stopping rule.
Finish the fixed plan irrespective of accuracy unless an operational failure
requires stopping. Temperature zero is not a reproducibility guarantee.

## Interpretation

- If answer-first is worse than answer-only, an explanation request/schema can
  affect an answer before the written explanation exists. This would show that
  already generated explanatory text is not necessary for that specific
  difference. It does not isolate which part of the request/schema caused it,
  show an internal task choice, or prove the cause of the old free-text errors.
- If reasoning-first is worse than answer-first, generation order or early
  answer commitment matters. That does not distinguish textual self-conditioning
  from order-induced strategy or anchoring. A result in the opposite direction
  must also be reported and would contradict the predicted protective effect.
- If all arms are accurate, allowing explanations inside JSON did not restore
  the failure on these cases. Do not interpret that as equivalence everywhere or
  keep changing prompts until the desired effect appears.
- The explanations in the two order conditions need not be identical. This is
  not the same internal computation with text moved, and it is not a neural
  mechanism experiment. Comparisons to earlier runs remain descriptive.

Prior work includes [Order Matters in Hallucination](https://arxiv.org/abs/2408.05093)
and [Measuring Faithfulness in Chain-of-Thought Reasoning](https://arxiv.org/abs/2307.13702).
The present diagnostic uses order to narrow explanations of this task's
behavior; order effects alone are not a new phenomenon.

## Run on macOS

Use the existing checkout and `OPENAI_API_KEY`. No new dependencies or GPU
are required. Preserve older run directories and use `runs/order-001`.

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_order prepare --config configs/order.json --output runs/order-001
open runs/order-001/preview.md
caffeinate -i python3 -m exception_order run --config configs/order.json --output runs/order-001 --max-calls 6
caffeinate -i python3 -m exception_order run --config configs/order.json --output runs/order-001 --max-calls 72 --resume
open runs/order-001/summary.md
zip -r order-001.zip runs/order-001
```

If Git reports a merge conflict, resolve that before running; do not reset or
force-push to discard local work. The first six calls count toward 72. An
error-free resume makes 66 more, even though its per-invocation ceiling is 72.
Completion should report 72 returned and valid answers, zero invalid answers,
and `stopped: complete`.

For an eligible transport failure, continue the same run with:

```bash
caffeinate -i python3 -m exception_order run --config configs/order.json --output runs/order-001 --max-calls 72 --resume --retry-errors
```

Preparation and reanalysis make no API calls:

```bash
python3 -m exception_order analyze --output runs/order-001
```

Outputs include the frozen plan/source fingerprint, preview, execution identity,
raw request/response journal, `summary.json`, `summary.md`, and `answers.csv`.
Analysis verifies saved requests, schedule, raw responses, and scoring. Optional
software-only runs use `--mock` and a separate directory such as
`runs/order-mock`; their all-correct fixtures are not predictions or evidence.
