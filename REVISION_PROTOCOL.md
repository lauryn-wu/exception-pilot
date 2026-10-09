# Can reasoning overturn an initially correct answer?

Protocol: `verified-facts-answer-revision-v1`. World seed: `2026100894`.

## Motivation and scope

In the supplied `order-001` results, answer-only and answer-first each returned
24/24 correct answers; reasoning-first returned 15/24, with all nine errors
choosing the competing background pattern. Every response satisfied the output
checks. Those results concern 12 worlds and one model. Answer-first explanations
could still contain incorrect statements. A correct answer emitted before an
explanation cannot be revised by subsequent text under that scoring rule.

This follow-up asks whether the advantage of answering first survives an
opportunity to issue another answer. It keeps the original classification
question and includes contemporaneous copies of the two original order arms.
It does not use an explicit recorded-class query, select previously failing
items, or resume the stopped missingness replay. It is an output-order
intervention, not an intervention on a specific sentence or an internal state.

## Fixed design

- **24 fresh worlds × 2 recorded-class variants × 4 conditions = 192 calls.**
- Each of the six permutations of two recorded labels and the pattern label
  occurs twice for a cold target and twice for a warm target: 12 balanced cells
  with two worlds each. Fresh plates and a fixed new seed are used.
- Each world contains ten accurate records. Both target-record variants
  conflict with the same-climate pattern. The variants differ only in the
  target's recorded class. All target cells are recorded.
- Preserve the earlier introduction, including its MISSING definition, table
  columns, administrative audit marker, target description, and original
  classification question. No recorded-class question or reminder is added.
- `gpt-4o-2024-08-06`, temperature 0, one completion per independent
  conversation, equal 1,000-token ceilings, 120-second timeout.
- Deterministically randomize all eight requests within each world.
- Fix **224 total attempts**, allowing at most 32 explicit transport retries.
  There are no hidden retries. An error-free collection makes 192 calls.

## Conditions and exact instructions

| Arm | Required serialized field order | Scored answer |
|---|---|---|
| `reasoning_first` | reasoning → answer | answer |
| `answer_first` | answer → reasoning | answer |
| `revision` | initial_answer → reasoning → final_answer | final_answer |
| `repeat_control` | initial_answer → final_answer → reasoning | final_answer |

Both original order arms retain their exact earlier instruction and schema:

```text
Output only a JSON object with two fields, "answer" and "reasoning". Set "answer" to A, B, or C and write your reasoning in "reasoning".
```

Both new arms receive this identical instruction:

```text
Output only a JSON object with three fields, "initial_answer", "reasoning", and "final_answer". Set both answer fields to A, B, or C and write your reasoning in "reasoning". Your final answer may match or differ from your initial answer.
```

All arms use strict JSON with answer fields restricted to the string enum
`A`, `B`, or `C`, a string reasoning field, and no additional properties.
Within each pair, schemas differ only in the serialized order of properties;
the required-field list is identical. For the new pair it is
`["initial_answer", "reasoning", "final_answer"]` in both arms. There are no
field descriptions that differ between conditions, no forced initial value,
and no instruction to agree with or overturn the initial answer.

Both answers may differ, including two different incorrect answers. A class
mentioned inside the reasoning string is not an answer field and is never
rescored as one. `initial_answer` is absent, rather than imputed, for anchors.
The parser exposes `answer` as the scored answer for every arm and also
retains explicit initial/final fields for the new arms.

The model sees its complete schema in advance. Thus even initial answers can
differ between the two new conditions. The control requests a second answer
before any explanatory text is emitted; it controls for requesting two answer
fields, not every consequence of answer position, elapsed generation, or
anticipated task structure. The reasoning strings need not be identical.

`prepare` saves all 192 exact requests in `preview.json`. `preview.md` contains
all four schemas, common settings, and the first world's eight exact messages.
Ground-truth metadata in those files is not appended separately to API prompts.

## Output validation and retention

Parse the entire returned JSON object. Reject duplicate/extra/missing fields,
wrong types, labels outside A/B/C, incorrect serialized order, nonstandard JSON
constants, code fences or surrounding prose, and empty/whitespace-only reasoning.
Nonempty reasoning is a format check, not proof of correct or faithful thought.
Record schema/order compliance and reasoning length separately.

Retain every returned response. A wrong but valid answer does not stop the run.
A malformed response, wrong order, empty reasoning, refusal, truncation, or
model mismatch is retained and stops collection. Do not accept a truncated
response merely because an answer appeared before truncation. Do not extract
answers from an invalid response or resample until one passes. Validity applies
to the entire output, including both answer fields in the new arms.

Only errors or interrupted requests without a saved returned response can be
retried using `--resume --retry-errors`, within the total attempt cap. Each
attempt is journaled before the request; every returned response is preserved.
An interrupted request may already have incurred a charge. Saved plans,
requests (including schema order), raw responses, normalized responses, and
scoring are checked on resume and analysis. Code or config changes require a
separate protocol/run. Mock runs are visibly simulated and cannot become live
runs. Preparation, analysis, and offline tests make no model calls.

## Analysis fixed before collection

The primary contrast is **final-answer accuracy in `repeat_control` minus
`revision`**. Positive values indicate worse final accuracy when reasoning is
placed between the answers. Average the two recorded-class variants within
each world, then give worlds equal weight. Do not condition the primary
comparison on initial correctness: the assigned schema can affect that too.

The secondary accuracy contrast is `answer_first minus reasoning_first`, to
check the earlier order effect on these new worlds. There is no significance
threshold that authorizes selecting cases, extending the sample, or suppressing
the primary result. Report the two contrasts regardless of direction.

Report final accuracy and background-pattern choices for every arm. For the
two new arms, also report initial accuracy, the four correctness transitions
(correct→correct, correct→wrong, wrong→correct, wrong→wrong), whether the answer
changed, and correct→background-pattern transitions. Retain a complete
gold/pattern/other transition matrix. These are descriptive observations;
initially correct subsets are not randomized groups or causal mediators.

Signed record sensitivity and target-record pair counts are secondary
descriptions. The sensitivity score is
`S = [I(y1=r1) - I(y1=r2) + I(y2=r2) - I(y2=r1)] / 2`.
It is 1 for correct tracking, 0 for a constant answer, and -1 for reversed
tracking. Editing the target record also changes class counts in the table;
sensitivity alone does not prove internal record retrieval.

Use 10,000 whole-world bootstrap resamples, seed `981723`, for descriptive,
unadjusted 95% percentile intervals. There are **24 sampling units**, not 192.
This fixed diagnostic has not been claimed to be powered for a small effect.
Degenerate intervals, particularly at ceiling, do not establish equivalence.
Each estimate exposes missing/invalid cases and excluded worlds. Full-plan
unscorable bounds, when available after all returns, are not confidence
intervals. Partial, simulated, or failed-manipulation runs do not establish the
intended comparison. No outcome-dependent sample extension is allowed.

## Interpretation

- A lower final accuracy in `revision`, together with correct→pattern changes,
  would show that placing reasoning between two answers can harm a revisable
  decision even after a correct label was explicitly emitted. It would not
  isolate misleading text from answer position, delay, or schema anticipation.
- If both new arms remain accurate while the original order gap replicates,
  an explicit initial answer protects performance through a later opportunity
  to revise in this protocol. Copying, anchoring, altered task interpretation,
  and rationalization remain possible. A ceiling result may delimit the
  behavior without explaining the original failures.
- If the original order gap does not recur, report that result and the primary
  comparison. The connection to the earlier failure is weaker; do not change
  prompts or select cases to manufacture a replication.
- If initial answers differ systematically across the new arms, report it:
  the model can anticipate later fields. A within-response transition is an
  observable sequence, not proof of a particular latent belief trajectory.
- Opposite-direction effects and wrong→correct revisions are equally relevant.

Specific reasoning-content interventions would require their own valid
continuation or explicitly defined two-stage protocol. Related methodology:
[Measuring Faithfulness in Chain-of-Thought Reasoning](https://arxiv.org/abs/2307.13702).
Order effects themselves are already studied, for example in
[Order Matters in Hallucination](https://arxiv.org/abs/2408.05093).

## Run on macOS

From the existing checkout, with the existing `OPENAI_API_KEY` in this terminal:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_revision prepare --config configs/revision.json --output runs/revision-001
open runs/revision-001/preview.md
caffeinate -i python3 -m exception_revision run --config configs/revision.json --output runs/revision-001 --max-calls 8
caffeinate -i python3 -m exception_revision run --config configs/revision.json --output runs/revision-001 --max-calls 192 --resume
python3 -m exception_revision analyze --output runs/revision-001
open runs/revision-001/summary.md
zip -r revision-001.zip runs/revision-001
```

The first eight calls count toward 192. With no errors, resume makes the
remaining 184 calls. This first block checks execution and field order only;
continue regardless of accuracy. If a Git merge conflicts, resolve it before
running, preserving local commits. Do not discard local results.

After fixing a transport error, explicitly retry within the original cap:

```bash
caffeinate -i python3 -m exception_revision run --config configs/revision.json --output runs/revision-001 --max-calls 224 --resume --retry-errors
```

This cannot retry a returned invalid response. An offline software demonstration
uses a separate directory:

```bash
python3 -m exception_revision run --config configs/revision.json --output runs/revision-mock --max-calls 192 --mock
```

Mock outputs are fixtures, not observations of model behavior. No new
dependencies or GPU are required. Keep the complete run directory for audit.
