# Reasoning cue with enforced answer-only output

Protocol: `verified-facts-constrained-cue-v1`. World seed: `2026100892`.

## Question

Can adding a reasoning instruction reduce verified-record accuracy when the
output interface prevents a written explanation?

The completed cue experiment returned 144 valid final answers: direct 48/48,
cue 33/48, and requested written reasoning 23/48. Every cue response wrote
an explanation despite the answer-only instruction. That comparison therefore
did not isolate an instruction effect without written reasoning.

This follow-up enforces an answer-only JSON schema in both conditions. It
reuses all 24 cue worlds and both recorded-class variants, without selecting
cases based on whether a previous response was correct. These are previously
examined worlds, not an independent replication on fresh items. No saved
responses or explanations enter the new prompts.

## Fixed design

- 24 worlds × 2 target-class variants × 2 conditions = **96 planned calls**.
- Model `gpt-4o-2024-08-06`, temperature 0, one completion per request.
- Identical completion ceiling of 1,000 tokens in both conditions, preserving
  the previous ceiling. The schema only permits a short JSON answer.
- Same introduction, table, query, row order, target features, and class-role
  balance as the cue study. This includes the shared `MISSING` definition,
  although every target has a recorded class.
- Between the two record variants, only the target's Verified class cell
  changes. Each possible recorded class differs from the background pattern.
- A new deterministic schedule shuffles the four requests within each world.
  Each request starts an independent conversation.
- A hard cumulative limit of **112 attempts**, including any explicitly
  requested transport retries. A normal complete run makes 96 calls.

The world generator is reused from the frozen cue implementation. Source
fingerprints, config, worlds, schedule, and analysis specification are saved
before collection. The old study packages and their run directories remain
separate. This study does not resume the stopped missingness experiment.

## Only experimental prompt difference

**A′ — direct (`direct`)**

```text
Output only a JSON object with one field, "answer", whose value is A, B, or C.
```

**B′ — reasoning cue (`cue`)**

```text
Think step by step before answering. Output only a JSON object with one field, "answer", whose value is A, B, or C.
```

Both API requests use this identical response format:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "class_answer",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string", "enum": ["A", "B", "C"]}
      },
      "required": ["answer"],
      "additionalProperties": false
    }
  }
}
```

There is no reasoning field, free-text field, or tool call. Example valid
output: `{"answer":"C"}`. The JSON requirement replaces the previous
`ANSWER: C` format in both arms. The new contrast estimates the instruction
effect under this shared constrained interface.

OpenAI documents strict JSON schema support for this model snapshot:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
Refusals and incomplete responses still require explicit handling. Preparation
prints no credentials and writes all 96 exact requests to `preview.json`,
plus the first world's four requests and the schema to `preview.md`.

## Scoring and analysis

The parser accepts only a complete response whose entire content is a JSON
object with exactly one `answer` key and value `A`, `B`, or `C`. JSON whitespace
is permitted. Duplicate keys, additional keys, prose, code fences, wrong value
types, and invalid labels are rejected. There is no fallback answer extraction.

Every returned response is saved, including wrong answers and invalid output.
Wrong schema-valid answers remain in the analysis. **Any schema violation,
refusal, truncation, or wrong-model response stops collection and blocks
resampling.** Such a run is a failed operational/control check; preserve it
for inspection. An invalid response is not counted as a classification error
or silently excluded to make the control appear successful. Summaries expose
invalid reasons and incomplete pairs.

The primary contrast is accuracy **direct minus cue**. Each world's accuracy
first averages its two target variants; the contrast then averages across
complete worlds with equal weights. The independent unit is the **world (24)**,
not the 96 requests or 48 target variants. Positive values favor direct.

Secondary record sensitivity is

`S = [I(y1 = r1) - I(y1 = r2) + I(y2 = r2) - I(y2 = r1)] / 2`.

Here `r1/r2` are the two recorded target labels and `y1/y2` their answers.
Correct tracking scores 1, a constant answer scores 0, and reversed tracking
scores −1. Report S in both arms and direct minus cue, along with accuracy,
pattern-choice counts, answer-change counts, and schema compliance. Changing
the target class also changes whole-table label counts, so answer sensitivity
alone does not prove an internal lookup operation.

Descriptive 95% percentile intervals use 10,000 whole-world bootstrap
resamples, seed `981723`. Each contrast requires all four answers in its world;
reports identify excluded worlds and tasks. Full-plan bounds for unscorable
answers are available only if every planned response has returned. They are
point-estimate bounds, not confidence intervals. A narrow or degenerate
bootstrap interval on 24 previously examined worlds does not establish
certainty or equivalence.

There is no accuracy-based continuation gate or automatic sample extension.
The first four-call block checks execution and schema compliance only. Finish
the fixed plan irrespective of accuracy unless a technical failure requires
a stop. Temperature zero does not guarantee deterministic answers.

## Interpretation fixed before collection

- If the cue reduces accuracy while the schema is obeyed, a written
  explanation is unnecessary for that instruction effect under this
  constrained interface. Its magnitude need not match the earlier effect.
- If the difference disappears, that does not prove generated reasoning
  caused the earlier errors. The output constraint may itself change how
  the model approaches the task. A small observed difference is not evidence
  of equivalence.
- If both arms fail similarly, the new interface reveals a shared failure
  without isolating a cue effect.
- This does not establish that hidden step-by-step reasoning occurred, that
  the model chose a particular internal task, or when an internal decision
  was made. It does not identify a neural mechanism or a mediated effect.
- Comparisons with the previous unconstrained study are descriptive. They
  change output format and collection time; this design has no contemporaneous
  written-reasoning arm.

## Run on macOS

Use your existing checkout and `OPENAI_API_KEY`. No new dependencies or GPU
are needed. Use a new directory, not `runs/cue-001`.

```bash
git pull --ff-only
python3 -m exception_constrained_cue prepare --config configs/constrained_cue.json --output runs/constrained-cue-001
open runs/constrained-cue-001/preview.md
caffeinate -i python3 -m exception_constrained_cue run --config configs/constrained_cue.json --output runs/constrained-cue-001 --max-calls 4
caffeinate -i python3 -m exception_constrained_cue run --config configs/constrained_cue.json --output runs/constrained-cue-001 --max-calls 96 --resume
open runs/constrained-cue-001/summary.md
zip -r constrained-cue-001.zip runs/constrained-cue-001
```

The first four calls count toward 96; an error-free resume makes only 92 more.
Completion should report `stopped: complete`, `returned_answers: 96`,
`valid_answers: 96`, and `invalid_answers_retained: 0`.

If you need to set the key in macOS's default zsh, enter it without echoing:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Only transport errors or interrupted requests without a saved returned
response can be explicitly retried, within the 112-attempt cumulative cap:

```bash
caffeinate -i python3 -m exception_constrained_cue run --config configs/constrained_cue.json --output runs/constrained-cue-001 --max-calls 96 --resume --retry-errors
```

An interrupted in-flight request may have reached the provider and a retry
can incur another charge. Never delete journal entries, change the config
mid-run, or retry a returned invalid/wrong answer.

Preparation and analysis do not call the model API:

```bash
python3 -m exception_constrained_cue analyze --output runs/constrained-cue-001
```

Outputs include `plan.json`, `preview.json`, `preview.md`, `execution.json`,
the raw request/response attempt journal, `summary.json`, `summary.md`, and
`answers.csv`. Analysis revalidates the plan, source fingerprint, request
schedule, response normalization, and scoring against the raw responses.

For an optional offline software check, use `--mock` with a separate output
directory. Mock outputs are marked simulated, require no credentials, make no
API calls, and cannot be resumed as live evidence. Their all-correct fixture
does not predict the experimental result.
