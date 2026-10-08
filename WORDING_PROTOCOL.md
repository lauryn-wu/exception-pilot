# Fresh-data wording confirmation v1

Protocol: `verified-facts-wording-v1`. Specified 2026-10-08 after inspecting the
positive counterfactual pilot and before collecting any live wording-study data.
This is a bounded follow-up, not a claim that the original hypothesis was novel
or a formally registered significance test. No previous observations enter its
estimates. Both earlier protocols, their Python packages, decisions, and saved
run directories remain unchanged.

## Question and design

Does the extra conflict penalty under explicit reasoning persist when the
reasoning instruction is neutral and the question explicitly asks for the
recorded class?

Use 20 fresh independent lists, seed `2026100848`, with unique W-prefixed vehicle
plates (disjoint from the previous R/D/V namespaces). The same world generator
and feature vocabulary as the counterfactual pilot are used with the fresh seed.
New lists vary attributes, label mappings, targets, exceptions, and record order;
the task family is deliberately unchanged. No list is selected using responses.

Each list has ten verified records and two preselected targets. As before:

- Each background has five A and five B labels, and exactly two exceptions to
  its majority climate rule (80% conformity).
- The queried target records and their verified labels are identical in both
  backgrounds. Six of the other eight record labels change.
- Targets oppose the majority pattern in conflict and follow it in support.
- Each request is one fresh user message. There is no prior generated response,
  explanation, feedback history, or output from another condition in the input.

Cross **two question wordings × three response instructions** on the same
target/background pairs. Each factor changes only the text documented below.
This is 20 lists × 2 targets × 2 backgrounds × 2 questions × 3 instructions =
**480 requests**, including 160 direct and 320 reasoning responses.

Within every list, randomize all 24 calls using a separate deterministic schedule
seed. The plan is frozen before any calls. A 24-call access/format check is part
of the same dataset; it is not a screen for choosing which prompts to finish.

## Exact wording

The evidence introduction is identical in every condition:

> These are records of previously observed vehicles. Every record is accurate.
> An individual vehicle's class is fixed, and its license plate identifies it.

Follow it with the same ten-row table, including the Verified class column, and
repeat the queried vehicle's plate, description, transmission, seat cover, and
doors. The target's class is intentionally visible in the table in every cell.
Condition names and separate scoring metadata are not sent to the model.

Question factor:

| Name | Exact question text |
|---|---|
| original | Which class, A or B, does this vehicle belong to? **[newline]** Choose the more likely class even if uncertain. |
| recorded | Which class, A or B, is recorded for this vehicle in the table above? |

The recorded question removes the original uncertainty clause as well as asking
explicitly about the table. Treat this as a task-wording manipulation; do not
attribute its effect uniquely to one word or clause.

Response-instruction factor (appended after either question):

| Name | Exact final instruction |
|---|---|
| direct | Reply with only A or B. |
| cot_classification | Work through the classification, then put A or B alone on the final line. |
| cot_neutral | Think step by step, then put A or B alone on the final line. |

Original/direct and original/cot_classification reproduce the previous prompt
templates exactly on new records. The neutral instruction changes only the
reasoning phrase. The recorded/cot_classification cell completes the factorial
design but is not eligible to rescue a failed neutral-wording check.

Use `gpt-4o-2024-08-06`, temperature 0, caps direct=10 and both reasoning arms=1000,
and the same stateless Chat Completions provider. No model replacement, adaptive
prompt change, automatic retry, or best-of-N selection is permitted. This tests
explicit answer instructions and their associated output budgets, not a switch
that disables all internal reasoning.

## Estimands and independent sample size

For every list, average its two targets in each of the twelve
question/instruction/background cells. For question q and reasoning arm r:

`extra penalty(q,r) = [accuracy(q,r,support) - accuracy(q,r,conflict)]`

`                   - [accuracy(q,direct,support) - accuracy(q,direct,conflict)]`

Average these list-level contrasts over complete lists. The independent sample
size is **20 lists**, not 480 calls or 40 targets. The primary robustness contrast
is **recorded/cot_neutral**. Also report all four reasoning-versus-direct
contrasts, all twelve cell accuracies, list effects, and positive/zero/negative
list counts. No response subgroup is selected after seeing its accuracy.

Report the following paired differences in extra penalties:

- neutral minus classification, within each question (two contrasts);
- original minus recorded, within neutral reasoning (one contrast).

These differences use the same list pairs. They are descriptive comparisons,
not independent samples. Positive original-minus-recorded means the explicit
record question reduces the extra penalty. A difference in significance between
cells is not evidence of a significant difference between the cells.

Uncertainty: 10,000 percentile bootstrap resamples of entire lists, fixed analysis
seed 981723. Intervals are descriptive, without a simultaneous-coverage claim.
A constant list-effect vector has its exact degenerate bootstrap interval;
this does not establish population certainty. Partial paired analysis uses only
lists with all 24 valid responses; separate valid-only tables disclose all cell
denominators. Missing or invalid answers are never counted as incorrect.

## Ordered investment checks and stopping

After all 480 planned answers are valid, with at least 20 complete lists, inspect
these checks in the following predeclared order:

1. **Fresh replication:** original/cot_classification.
2. **Neutral reasoning wording:** original/cot_neutral.
3. **Explicit recorded-class question:** recorded/cot_neutral.

Each check requires an extra penalty of at least **15 percentage points**, a
strictly positive accuracy loss under conflict in that reasoning arm, and lower
reasoning than direct accuracy under conflict. A positive interaction caused
solely by direct-answer improvement or a shrinking reasoning benefit fails the
direction requirements. The same numerical investment threshold is retained
from the prior counterfactual protocol; it is not a power calculation or a
significance threshold.

| First failed check | Decision | Interpretation |
|---|---|---|
| Fresh replication | stop_replication_failed | The original magnitude did not reproduce sufficiently on fresh lists. Stop this extension. |
| Neutral reasoning | stop_neutral_wording_failed | The broader neutral-reasoning claim did not pass. Preserve the narrower original result. |
| Explicit record question | stop_explicit_record_boundary | The broader wording-robust claim did not pass. Preserve the observed task-wording boundary. |
| All pass | review_for_second_model | Inspect intervals and spread across lists before a separately specified second-model study. |

Small, incomplete, and technically invalid runs have separate decisions. Mock
always returns `simulated_not_evidence`, even if its engineered fixture passes
the numerical checks. All four contrasts are reported regardless of the ordered
decision. No favorable diagnostic cell overrides a failed ordered check.

An effect below 15 points is not proof of absence. A wording boundary is useful
information, but does not by itself warrant a new paper, more favorable prompts,
or another paid search. A pass does not establish an internal mechanism, novelty,
or generalization to other models/tasks. No next experiment runs automatically.

## Scope limitations carried forward

The full-table exception rate and class balance are fixed. Among a target's four
same-climate peers, conflict has a 4:0 split while support has 3:1. Consequently
leave-target-out consensus strength is not held fixed. Changing labels can also
change incidental correlations with transmission, seat cover, and doors. This
intervention is on surrounding labeled records, not a selective manipulation of
a latent climate representation. Descriptions are unique within a list, so any
successful matching cannot be attributed uniquely to license-plate processing.

Explanations are observed outputs, not a faithful readout of an internal belief.
The primary endpoints are final A/B answers. Different question wordings may
change the task the model attempts; that is precisely the boundary being tested.

The closest existing vehicle-exception work remains
[Mind Your Step (ICML 2025)](https://proceedings.mlr.press/v267/liu25t.html).
Its retrieval-steering results limit novelty claims about simply improving the
task with lookup instructions. See the preceding
[counterfactual protocol](COUNTERFACTUAL_PROTOCOL.md) for the broader literature
context. This study is a decision about robustness, not a new novelty claim.

## Run, recover, and share

From the updated Git checkout on macOS:

```bash
git pull --ff-only
python3 -m exception_wording prepare --config configs/wording.json --output runs/wording-001
open runs/wording-001/preview.md
```

Prepare and preview make no API calls. The Markdown and JSON previews contain
all 24 exact first-list requests. The frozen plan contains all 480 tasks.

Use the same `OPENAI_API_KEY`. If this is a new macOS zsh terminal:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Run one complete list to check access and output validity, then finish the plan:

```bash
caffeinate -i python3 -m exception_wording run --config configs/wording.json --output runs/wording-001 --max-calls 24
caffeinate -i python3 -m exception_wording run --config configs/wording.json --output runs/wording-001 --max-calls 480 --resume
```

The second command skips completed tasks; after an error-free 24-call check it
makes 456 calls, for **480 total**. On Linux omit `caffeinate -i`. Python >=3.10;
no new packages or GPU. Neither command launches a second model.

After a resolved transport error, resume the same command with `--retry-errors`.
The call cap counts all new attempts, including failures. Invalid returned
answers cannot be resampled. Inspect such a response, preserve the run, and
document any required protocol fix as a separate study. No automatic retries.

```bash
python3 -m exception_wording analyze --output runs/wording-001
open runs/wording-001/summary.md
zip -r wording-001.zip runs/wording-001
```

The source fingerprint covers the new module and shared helpers. Frozen config,
plan, request journal, raw responses, and execution mode are saved. Config/source
changes block resume; live and mock runs cannot mix. Previous run folders are
rejected. Credentials and run data are untracked. No old Stage 2 is authorized.

Offline checks: `python3 -m unittest discover -s tests -v`. For a simulated
software demonstration, use `--mock` and a separate output folder. Its deliberately
engineered positive fixture is not a forecast or model observation.
