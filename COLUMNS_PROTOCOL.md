# Which columns change the answer?

Status: implemented; no live results collected with this addition.
This is an exploratory experiment on the 24 previously inspected explanation-study
worlds. It investigates the existing anomalies; it is not a fresh-world confirmation.

## Question

Does reasoning depart from the target record because of the strong climate pattern,
incidental similarities in other attributes, or something that persists without
either? Do those attributes sometimes help the model justify a correct answer?

The original class-copy condition answered all 48 visible-record questions correctly,
but three explanations still called the class missing. In one paired example,
changing only the target class changed the similarities used to justify the answer.
The experiment therefore measures both answer changes and sensitivity to the target
class. It also exports every response for inspecting the explanations.

## Design

Always keep License plate and Verified class, with all ten original rows.

| Table version | Columns, in displayed order |
|---|---|
| `minimal` | License plate, Verified class |
| `description` | License plate, Description, Verified class |
| `other_attributes` | License plate, Transmission, Seat cover, Doors, Audit marker, Verified class |
| `full` | License plate, Description, Transmission, Seat cover, Doors, Audit marker, Verified class |

Cross those four versions with three response instructions:

- `direct`: answer only.
- `cot`: reason before the final answer.
- `copy_class`: copy the target's class first, then reason and answer.

Use both recorded-class variants from every world: **24 × 2 × 4 × 3 = 576 calls**.
There is no missing-class condition. The two target classes differ from the designed
climate-pattern label. Between record variants, only the target class cell changes.
Between column versions, only the specified columns are deleted. Remaining values,
row order, header spelling, query, instructions, and provider settings stay fixed.

The Description column groups vehicles by climate. The four other attributes were
assigned independently of class in the original generator. Individual tables can
still contain strong chance associations; they are not guaranteed uncorrelated.

The bundled `configs/column_worlds.json` contains all source worlds without filtering
on response outcomes. Source plan hash:
`81d29ff260b9b06999bd26f5cbea5611d3b5a9e507af31692b6ce0bff33c2a5a`.
Snapshot hash:
`a40ba696bfde0d863692f1f4ec53ca247aaf9378e76b16116a802256e69831c7`.
The raw source is `explanation-001`, archived in `results/explanation-001.zip`.
Historical responses are never pooled into the new estimates.

Keep source world order; shuffle each world's 24 requests deterministically with
seed 2026101201. Every request starts a separate conversation. Complete the fixed
schedule regardless of interim accuracy. The first 24 calls are an execution check,
not a scientific gate or a screen for choosing worlds.

## Prompts and model

Use `gpt-4o-2024-08-06`, the model from the original class-copy study, at temperature 0.
All three arms have the same 1,000-token completion cap. Use `OPENAI_API_KEY`, a
120-second timeout, and a cumulative cap of **608 attempts**, allowing at most
32 additional transport attempts if all 576 tasks return. There are no hidden retries.
The planned output caps sum to 576,000 tokens before retries; this is not a dollar estimate.

The target query is always `License plate: {target_id}`, followed by the unchanged
question, `Which class, A, B, or C, does this vehicle belong to?` Removed attributes
are never repeated in the query. The introduction and three response instructions
are verbatim from the explanation study. In particular, the shared introduction
still defines Audit marker and MISSING in every condition, including tables without
the marker column. No target class is actually missing.

The full-table arm is collected anew. It is a contemporaneous comparison, not an
exact reproduction of the earlier feature-profile query or its direct-answer token
cap. `prepare` writes all 576 provider requests to `preview.json`, and all 24 prompts
from the first world to `preview.md`. Preview headings and answer keys are not sent.
No assistant prefix or externally supplied answer is used.

## Outcomes

Report all 12 cell accuracies, answer counts, output adherence, invalid/unreturned
counts, and choices of the original background-pattern label. In tables without
Description, that last measure describes the chosen label, not observed climate inference.

For each world and cell, average the two record variants. Define
`H(table) = accuracy(direct) - accuracy(cot)`.
The two prespecified primary descriptive comparisons are:

```text
Description effect = [(H(description) - H(minimal))
                    + (H(full) - H(other_attributes))] / 2

Other-attribute effect = [(H(other_attributes) - H(minimal))
                        + (H(full) - H(description))] / 2
```

Positive means adding that column group increases reasoning harm. Negative effects
are equally relevant. Also report the interaction
`H(full) - H(description) - H(other_attributes) + H(minimal)`, every table's reasoning
harm and class-copy gain, and each reduced-versus-full contrast in every arm.

The secondary record-sensitivity score assigns +1 to the target's actual class,
−1 to the other record variant's class, and 0 to the background-pattern label.
Average across both variants, giving a range of [−1, 1]. A fixed answer across the
two variants scores 0; correctly following both classes scores 1. Also report the
number of paired worlds with both variants correct and with different answers.

Resample **whole worlds**, retaining paired conditions and variants, 10,000 times
with seed 981723. Report descriptive, unadjusted 95% percentile intervals. These are
multiple exploratory comparisons, not confirmatory significance tests. A constant
sample produces a degenerate interval; it does not establish precision or equivalence.
Use the complete worlds required by each particular contrast and show its denominator.
For full-plan bounds, retain valid scores and let each missing or invalid answer range
over A/B/C, preserving coefficient signs. Bounds are not confidence intervals.

For each reduced table versus the full table, export every matched case: wrong→correct,
correct→wrong, both correct, both wrong, changed labels, and unresolved comparisons.
These pairs are independent model completions, not an edited continuation of one
hidden state. Inspect the full set of transitions rather than choosing a few examples.

Copy format, copy correctness, and final-answer correctness are separate. A correct
copy followed by a wrong final answer is retained as an error. A malformed or incorrect
copy never excludes a valid final answer. Copying the class alone is not counted as
reasoning. The raw text is available for later review of false missingness, invented
feature matches, and whether explanations change with the recorded class. No automatic
semantic classifier or claim about hidden beliefs is part of this addition.

## Collection and integrity

Only `run` without `--mock` contacts the provider. Plan, source, configuration,
schedule, requests, and journal scoring are checked on resume and analysis. The
runner records each attempt before its HTTP request and saves the raw returned body.
Each output directory has its own lock.

Use the existing correctness-blind terminal-answer grammar from
`exception_mistral_map_v3.parser`, including its bounded Markdown allowances.
Record exact `ANSWER: X` formatting separately. The first class-copy line must be
`COPIED: A`, `COPIED: B`, `COPIED: C`, or `COPIED: MISSING`; MISSING is an incorrect
copy here. Never recover an answer by searching the explanation for the expected label.

Returned refusals, truncated responses, and invalid answers remain terminal data;
continue the other scheduled tasks. A model-identity failure is retained and stops
collection. A successful HTTP response with malformed content is retained, not
converted into a retryable transport error. Recorded HTTP/network errors can be
retried only with `--resume --retry-errors`; these attempts count toward 608.
An unresolved `started` request after interruption cannot be automatically retried.
Completed or invalid returned tasks are never resampled.

Mock runs are labeled **SIMULATED — NOT MODEL EVIDENCE** and cannot resume as live
runs. There is no automatic success gate, paid follow-up, or outcome-dependent extension.

Column deletion also changes input length, table width, and class-cell position.
Removing Description does not remove the background's class frequencies or chance
associations in remaining columns. These comparisons identify effects of the stated
column deletions; a later matched-width/content intervention would be needed to
separate their contributors. Generated explanations are observable text, not faithful
measurements of internal computation. Any broader claim needs fresh worlds.

## Commands

Python 3.10+ and the standard library are sufficient. Run from this checkout's root.
To use a separate checkout while another study is running:

```sh
cd ~/exception-pilot
git fetch origin
git worktree add ../exception-pilot-columns -b codex/column-study origin/codex/column-study
cd ../exception-pilot-columns
```

Offline checks and preparation:

```sh
python3 -m unittest discover -s tests -p 'test_columns*.py' -v
python3 -m exception_columns prepare \
  --config configs/columns_gpt4o.json --output runs/columns-gpt4o-001
```

With `OPENAI_API_KEY` already set in the terminal, on macOS:

```sh
caffeinate -i python3 -m exception_columns run \
  --config configs/columns_gpt4o.json --output runs/columns-gpt4o-001 \
  --max-calls 24

caffeinate -i python3 -m exception_columns run \
  --config configs/columns_gpt4o.json --output runs/columns-gpt4o-001 \
  --max-calls 552 --resume

python3 -m exception_columns analyze --output runs/columns-gpt4o-001
zip -r columns-gpt4o-001-results.zip runs/columns-gpt4o-001
```

`--max-calls` limits new attempts in that invocation. With no transport errors, the
two invocations make 24 then 552 calls. If a transport error occurs, address it and
explicitly resume with `--retry-errors`; the cumulative cap still applies. Omit
`caffeinate -i` outside macOS. Keep this checkout's experiment code and configuration
unchanged during collection and resume.

For a completely offline integration check, use a separate directory:

```sh
python3 -m exception_columns run \
  --config configs/columns_gpt4o.json --output runs/columns-SIMULATED \
  --mock --max-calls 576
```

Outputs include `summary.md`, `summary.json`, `column-transitions.csv`,
`record-pairs.csv`, `responses.csv`, and `responses.jsonl`, alongside the frozen
plan, previews, execution identity, and raw attempt journal.
