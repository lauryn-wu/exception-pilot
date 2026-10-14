# Downstream history × introductory prediction-rule control

Protocol: `verified-facts-downstream-rule-v1`.

This exploratory follow-up crosses the presence of the saved classification
exchange with the presence of one introductory prediction sentence. It tests
whether that sentence contributes to answering a factual cell question with an
inferred class, and whether it changes the effect of the preceding exchange.

The design was specified after inspecting `downstream-history-gpt4o-001`: all
27 standalone answers on genuine-MISSING cases gave A/B/C, while all 27 answers
with history correctly gave MISSING. Removing history also reduced false
MISSING answers on recorded-class cases. Those observations motivate this
follow-up; they are not observations in its new analysis. This is not a
preregistered population confirmation or a new sample of source responses.

## Exact question and four conditions

The factual question is identical in every condition, substituting only the
target plate:

> What is written in {plate}'s Verified class cell? Reply with exactly one of A, B, C, or MISSING.

| Arm | Classification history | Introductory prediction sentence |
|---|---|---|
| `history_present_rule_present` | Present | Present |
| `history_absent_rule_present` | Absent | Present |
| `history_present_rule_absent` | Present | Removed |
| `history_absent_rule_absent` | Absent | Removed |

The exact sentence manipulated is:

> If that cell is MISSING, make your best prediction from the other records.

The complete original introduction is:

> These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

In rule-absent arms, remove only the last sentence and its single leading space.
The modified introduction ends exactly with:

> MISSING means the verified class has not been recorded.

No replacement instruction is added. In particular, do not add "copy exactly,"
"ignore previous instructions," a new system message, or a new answer format.
The definition of MISSING, full table, table formatting, target identifier,
factual question, and A/B/C/MISSING option order remain unchanged.

History-present requests contain three messages:

1. The original user message: introduction, table, and original classification
   question and copying/reasoning instructions. Modify only the validated
   introductory sentence when the rule is absent.
2. The exact saved original assistant response, including its copied value,
   explanation, and final answer.
3. The identical factual question as a new user message.

History-absent requests contain one user message: introduction, table, a blank
line, and the identical factual question. Remove the original classification
question, copying/reasoning instructions, and assistant response. The historical
feature-profile query in genuine-MISSING cases is removed too; its values remain
in the table. Validate the original source boundaries and removed tail before
constructing either condition.

**The saved assistant response is fixed across rule conditions.** It is not
regenerated and may still contain prediction language. The rule manipulation is
only in the initial user introduction, not a global deletion from the conversation.
This evaluates the follow-up under edited visible context. It does not estimate
how removing the rule would change the original generation or the total effect
of a different end-to-end classification policy.

Both rule-present arms must reproduce the corresponding requests from
`exception_downstream_history` byte for byte, including non-message settings.
Each rule-absent request must differ from its rule-present counterpart solely
by the specified introductory deletion. Every new call is an independently
reconstructed conversation; no hidden state is carried between calls.

## Frozen cases, cohorts, and schedule

Reuse every case in `exception_downstream/source_snapshot.json`, preserving its
digest, original prompts/responses, cohort, and answer key. Do not filter on the
previous history-control outputs or recruit only errors from that run.

| Cohort | Cases | Worlds within cohort | Four arms × three repetitions |
|---|---:|---:|---:|
| `contradiction`: correct original copy/final, reviewed false target-missingness claim | 13 | 9 | 156 |
| `availability_control`: correct original copy/final, no reviewed false target-missingness claim | 13 | 9 | 156 |
| `genuine_missing_control`: literal MISSING target cells | 9 | 9 | 108 |
| `wrong_final_diagnostic`: correct copy, originally wrong final class | 1 | 1 | 12 |
| Total | **36** | Cohorts share worlds; do not add world counts | **432** |

These are selected historical traces. The availability controls are not certified
fully factual explanations. Genuine-missing sources came from a different
historical feature-profile query, so cross-cohort differences do not isolate
missingness. Keep all cohorts separate; the single wrong-final case is descriptive.

Freeze all 432 exact requests before live collection. Shuffle world blocks, then
case/repetition blocks within each world. Keep all four conditions for one
case/repetition adjacent, with their order randomized by the fixed schedule seed.
There are 108 such blocks, 108 calls per arm, and 15 unique worlds overall.
Repetitions are not independent cases or worlds.

All four arms are collected fresh in this run. Do not substitute either completed
history-control arm for the contemporaneous rule-present reference.

## Collection and scoring

- Model `gpt-4o-2024-08-06`; temperature 0; `max_completion_tokens=64`;
  `n=1`; `store=false`; timeout 120 seconds. All settings match across arms.
- Fixed three repetitions and schedule seed 728141. The cumulative cap is 480
  attempts for 432 planned returns plus bounded explicit transport retries.
- Reuse the shared runner. Retain requests and raw provider returns, reject
  configuration/source/plan/request drift, and keep mock and live output separate.
  Stop on a model identity error. Unresolved in-flight requests block automatic
  retry. Refusals, truncations, and malformed returned answers are terminal data.
- Use the unchanged strict downstream scorer. After outer whitespace trimming,
  only exactly A, B, C, or MISSING is valid. Extra prose is format-invalid even if
  it mentions the correct class. Preserve it in raw output and unknown-outcome
  bounds; never reissue a returned answer to obtain a valid one.
- Verify gold values against the actual target cells. Accuracy means the returned
  value equals the cell. False missingness means a valid MISSING answer when that
  cell contains A/B/C. On genuine-MISSING cases, accuracy is the useful outcome;
  false missingness is structurally zero and does not measure reliability.

No new annotation, source-selection pass, judge-model calls, or live explanation
generation is part of this experiment. Do not modify the completed studies or
their output folders. The new module uses the existing packaging wildcard and
requires no edit to the old source-hashed `pyproject.toml`.

## Planned analysis

**Primary diagnostic:** accuracy in the nine genuine-missing cases/worlds,
without classification history, with the prediction sentence removed minus
present:

`accuracy(history_absent_rule_absent) - accuracy(history_absent_rule_present)`.

A positive difference means deleting the sentence increases literal-MISSING
answers in the standalone condition. It would support a contribution of the
introductory instruction to the earlier calibration failure. It would not prove
that the model failed to perceive the cell or locate an internal mechanism.

For each cohort and each metric (`accuracy`, `false_missing`), report these four
paired contrasts, with their directions explicit:

| Contrast | Subtraction |
|---|---|
| `rule_effect_without_history` | history_absent_rule_absent − history_absent_rule_present |
| `rule_effect_with_history` | history_present_rule_absent − history_present_rule_present |
| `history_effect_rule_present` | history_present_rule_present − history_absent_rule_present |
| `history_effect_rule_absent` | history_present_rule_absent − history_absent_rule_absent |

Also report `history_by_rule_interaction`:

`(history_present_rule_present - history_absent_rule_present)`
`- (history_present_rule_absent - history_absent_rule_absent)`.

Compute this interaction directly within each world on the same four-arm
complete data. Do not subtract estimates based on different complete-world sets
or subtract two confidence intervals. Positive values mean rule presence
increases the history effect on the selected metric. On false missingness this
is an increase in error; on accuracy it is an increase in correctness.

The key secondary question is whether the history effect on false missingness
in the contradiction cohort persists after deleting the prediction sentence.
All other contrasts and cohorts are descriptive secondary analyses. There is
no pooled primary estimate, significance gate, or outcome-dependent extension.

For every contrast: average repetitions within case/arm, then cases within a
world, then give each world equal weight. Both rates for a pair use the same
complete worlds, requiring all planned cases and repetitions in those two arms
to be valid. An interaction requires all four arms to be complete in that world;
report its four rates on that identical membership. Always report denominators.

Use 10,000 whole-world bootstrap resamples with seed 481603 for descriptive 95%
intervals. Bootstrap world-level differences or interactions while retaining
their pairing. Report full-plan lower/upper bounds for unknown invalid or absent
outcomes, with the signs of contrast coefficients respected. Those bounds are
not confidence intervals. Unknown false missingness on a genuine-MISSING cell
has bounds [0, 0]; unknown accuracy has bounds [0, 1].

Intervals are unadjusted and concern these selected source cases. A zero or
narrow interval does not establish population equality, particularly for the
single-world diagnostic. Similar rates do not establish equivalence. Code
completion, a successful mock run, and scientific evidence are separate statuses.

Export summary JSON/Markdown, per-response JSONL/CSV with raw text and both
factor labels, paired transitions for all four pair contrasts, and world-level
contrasts including the interaction. Preserve all attempts, the source-bound
plan, exact request preview, and execution identity.

## Interpretation limits

The history comparison still removes the entire classification exchange:
classification task/instructions, assistant text, context length, distance to
the table, and message/role structure change together. It does not isolate the
false missingness sentence or the explanation alone. The prediction-rule
comparison within either history level is a targeted introductory deletion;
it also shortens that introduction. The options and MISSING definition remain.

Removing the rule does not guarantee perfect retrieval or eliminate every
possible task cue. The genuine-missing accuracy result and recorded-cell false
missingness results must both be inspected. A repair of the former alone does
not establish repair of the latter, and no behavioral outcome establishes an
internal belief or an unobserved reasoning process.

## Run commands

Python 3.10+ and the standard library are sufficient from the repository root.
Prepare, previews, tests, mock execution, and analysis are offline. Only `run`
without `--mock` makes paid API calls. Use a fresh checkout and output folder:

```bash
git clone --branch codex/downstream-prediction-control --single-branch \
  https://github.com/lauryn-wu/exception-pilot.git exception-pilot-downstream-rule
cd exception-pilot-downstream-rule

python3 -m exception_downstream_rule prepare \
  --config configs/downstream_rule_gpt4o.json \
  --output runs/downstream-rule-gpt4o-001
```

Inspect `preview.json` for all requests and `preview.md` for a readable sample.
Set `OPENAI_API_KEY` in your environment. Then collect the fixed study:

```bash
python3 -m exception_downstream_rule run \
  --config configs/downstream_rule_gpt4o.json \
  --output runs/downstream-rule-gpt4o-001 \
  --max-calls 432
```

After a normal pause, resume with the same code and configuration:

```bash
python3 -m exception_downstream_rule run \
  --config configs/downstream_rule_gpt4o.json \
  --output runs/downstream-rule-gpt4o-001 \
  --max-calls 432 --resume
```

`--max-calls` counts new attempts in that invocation; completed tasks are skipped
and the 480-attempt cumulative cap remains. Only for a recorded transport error,
add `--retry-errors`. An unresolved started request must be reviewed, not resent.

```bash
python3 -m exception_downstream_rule analyze \
  --output runs/downstream-rule-gpt4o-001

zip -r downstream-rule-gpt4o-001-results.zip runs/downstream-rule-gpt4o-001
```

An optional complete offline exercise uses a different output folder:

```bash
python3 -m exception_downstream_rule run \
  --config configs/downstream_rule_gpt4o.json \
  --output runs/downstream-rule-MOCK \
  --max-calls 432 --mock

python3 -m unittest tests.test_downstream_rule -v
```

Never reuse a mock directory for live collection or label simulated responses as
model results. Keep prior runs on their original source versions; this addition
preserves the existing history-control source/config/protocol files unchanged.
