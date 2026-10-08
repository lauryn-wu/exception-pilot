# Question × uncertainty diagnostic v1

Protocol: `verified-facts-factorial-v1`. Specified 2026-10-08 after inspecting the
completed wording study and before collecting any live data for this study.
This is a post-result explanatory follow-up, not a preregistered discovery or a
replacement for any previous decision rule. The earlier
`stop_explicit_record_boundary` decision remains intact. Earlier Python packages,
configs, protocols, and saved runs are frozen. No prior responses enter these
estimates.

## Why this experiment

The completed wording study reproduced a reasoning-specific conflict penalty
under the original question, including neutral "Think step by step" wording.
The penalty was not observed with neutral reasoning and the explicit
recorded-class question. But that question change also removed the sentence
"Choose the more likely class even if uncertain." The existing contrast cannot
separate the contributions of the question and that sentence.

This study changes those two factors independently. It is the final planned
prompt-level diagnostic before reassessing whether broader investment is
justified. It does not automatically authorize another study or revive Stage 2.

## Fixed design and exact wording

Use **20 fresh independent lists**, seed `2026100864`, with unique F-prefixed
plates. The seed changes the generated records; the new namespace prevents
plate overlap with previous studies. Use the same matched-world generator and
feature vocabulary, without selecting lists based on model responses.

Each list has ten verified records and two preselected targets, one per climate.
Both backgrounds contain five A and five B labels and two exceptions (80%
conformity to the majority climate rule). Both target records and labels remain
fixed. Exactly six of the other eight labels change: the targets oppose the
background majority in conflict and follow it in support. Record order, target
positions, descriptions, and all other attributes stay fixed within each list.

Cross all factors on the same lists and targets:

| Factor | Levels |
|---|---|
| Background | support; conflict |
| Question | original; recorded |
| Uncertainty sentence | absent; present |
| Response instruction | direct; cot_neutral |

**20 lists × 2 targets × 2 backgrounds × 2 questions × 2 sentence levels ×
2 response instructions = 640 requests**, including 320 direct and 320 reasoning
responses. There are 32 calls per list and 40 target responses in each of the
16 factor cells. The independent sample size is 20 lists, not 640 calls.

Every call is a fresh conversation with one user message. The identical opening
is:

> These are records of previously observed vehicles. Every record is accurate.
> An individual vehicle's class is fixed, and its license plate identifies it.

Next comes the ten-row table, including the Verified class column, followed by
the queried vehicle's plate, description, transmission, seat cover, and doors.
The correct target label is intentionally visible in the table in every cell.
Condition labels and separate answer-key metadata are never sent to the model.

Append exactly one question:

| Name | Exact text |
|---|---|
| original | Which class, A or B, does this vehicle belong to? |
| recorded | Which class, A or B, is recorded for this vehicle in the table above? |

If the uncertainty factor is present, append the following on a new line:

> Choose the more likely class even if uncertain.

If absent, omit that line entirely. Then append the response instruction:

| Name | Exact text |
|---|---|
| direct | Reply with only A or B. |
| cot_neutral | Think step by step, then put A or B alone on the final line. |

Original/present and recorded/absent reproduce the preceding study's direct and
neutral prompt templates exactly on fresh records. Original/absent and
recorded/present fill in the two previously untested combinations. The recorded
question with the uncertainty sentence is deliberately included even if it
sounds redundant; do not rewrite it after inspecting responses.

Use `gpt-4o-2024-08-06`, temperature 0, completion caps direct=10 and
cot_neutral=1000, and the unchanged stateless Chat Completions provider.
No model substitution, adaptive prompt editing, best-of-N, or automatic retry.
This compares output instructions and their associated token budgets; it does
not claim to switch all internal reasoning on or off.

All 32 calls within a list are shuffled with a separate deterministic schedule.
Freeze the full plan before calling the model. The initial 32-call check is for
access and formatting and remains part of the dataset. Do not use its behavioral
results to select prompts, seeds, or which cells to complete.

## Estimands fixed before collection

For each list, average its two targets in every question/sentence/arm/background
cell. Define the reasoning-specific extra conflict penalty for question q and
uncertainty level u:

`E(q,u) = [accuracy(q,u,cot_neutral,support) - accuracy(q,u,cot_neutral,conflict)]`

`       - [accuracy(q,u,direct,support) - accuracy(q,u,direct,conflict)]`

Positive E means background conflict hurts reasoning more than direct answers.
Report all four E estimates, all 16 cell accuracies, direct and reasoning
conflict penalties separately, and direct-minus-reasoning accuracy in conflict.
These components distinguish actual reasoning errors from changes confined to
direct answers or the supporting background. A positive E alone does not show
that reasoning is worse than direct answers under conflict.

The **primary contrast** is the question-by-uncertainty interaction in E:

`I = [E(original,present) - E(original,absent)]`

`  - [E(recorded,present) - E(recorded,absent)]`

Positive I means adding the uncertainty sentence increases E more under the
original question. Zero I does not imply no wording effects: equal additive
effects can cancel in this interaction. In terms of the raw accuracies this is
a four-factor contrast, so report its uncertainty and components rather than
interpreting its sign alone.

Always report the following secondary paired contrasts, regardless of I:

- Sentence effect within each question: present minus absent (two contrasts).
- Question effect at each sentence level: original minus recorded (two contrasts).
- Average sentence effect: the mean of its two simple effects.
- Average question effect: the mean of its two simple effects.

Compute every contrast within a list before averaging or bootstrapping. Use
10,000 percentile bootstrap resamples of whole lists, fixed seed 981723. These
are descriptive intervals without multiplicity adjustment or a simultaneous
coverage claim. Do not infer a difference because one interval excludes zero
and another does not; use the paired difference itself. A constant vector gives
a degenerate bootstrap interval, which does not establish population certainty.
With 20 lists, modest effects or interactions may remain unresolved. This budget
is a bounded diagnostic, not a formal power calculation.

For paired analysis, include only lists with all 32 valid answers. Separate
valid-only tables disclose every returned cell's numerator and denominator.
Invalid or missing answers are never scored as incorrect. No response subgroup
is selected after seeing performance. Final A/B choices are the endpoints;
rationales can illustrate an error but are not evidence of hidden beliefs.

## Interpretation and stopping

This study has **no numerical pass threshold and no automatic go decision**.
Completion is `complete_ready_for_interpretation`, not a claim of success.
Incomplete, invalid, and undersized datasets have distinct technical statuses;
mock runs always say `simulated_not_evidence`.

Interpret the complete pattern, with intervals and raw accuracies:

| Observed pattern | Supported interpretation, conditional on replication |
|---|---|
| Removing the sentence sharply reduces original-question E | The sentence contributes to the earlier bundled wording effect. |
| Original/absent still has substantial E while recorded/present has little E | Stronger evidence for a question-framing contribution that is not dependent on sentence removal. |
| Sentence effects differ across questions | The wording factors interact; neither should be treated as a universal explanation. |
| Similar sentence effects and little question effect | The uncertainty sentence explains more of the boundary than the question distinction in this setting. |
| Both original/present and recorded/absent differ materially from their earlier results | Reassess reproducibility before explaining the earlier boundary. |
| Effects are small or intervals are broad | The explanatory question may remain unresolved; do not search for another favorable wording. |

These are interpretive guides, not additional thresholds, mutually exclusive
mechanism labels, or permission to make more calls. Do not pool old results into
this fresh-data analysis. No outcome establishes a novel phenomenon or a
conference-paper contribution by itself. Preserve the earlier positive effect
and the failed broader robustness check as separate observations.

## Scope and remaining limitations

This is one model snapshot and one synthetic task family. "Original question"
is a label for the exact tested text; it is not a validated measurement of an
internal classification process. The sentence combines uncertainty and
"more likely" wording, and adding it also increases prompt length. This design
identifies effects of the exact prompt interventions, not isolated semantic
features or a latent mechanism.

Although full-table pattern strength and exception rate are fixed, the target's
same-climate peers split 4:0 in conflict and 3:1 in support. Their consensus
strength is not fixed. Changing labels can also change incidental correlations
with other attributes. Unique descriptions permit record matching through
features other than license plates. Independent calls are not chronological
answer revisions.

The closest vehicle-exception paper remains
[Mind Your Step (ICML 2025)](https://proceedings.mlr.press/v267/liu25t.html),
including its retrieval-steering experiments. The present diagnostic resolves a
confound in our wording manipulation; it does not establish novelty over that
work. See the earlier protocols for literature context.

## Run and recover

From the updated Git checkout on macOS, using Python 3.10 or newer:

```bash
git pull --ff-only
python3 -m exception_factorial prepare --config configs/factorial.json --output runs/factorial-001
open runs/factorial-001/preview.md
```

Preparation makes zero API calls. The preview includes all 32 exact first-list
requests and separate answer keys. The plan contains all 640 requests' task
specifications. No additional packages or GPU are needed.

In a new macOS zsh terminal, set the key if needed:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Check access and formatting, then finish the same dataset:

```bash
caffeinate -i python3 -m exception_factorial run --config configs/factorial.json --output runs/factorial-001 --max-calls 32
caffeinate -i python3 -m exception_factorial run --config configs/factorial.json --output runs/factorial-001 --max-calls 640 --resume
```

The second command skips completed tasks. After an error-free check it makes
608 additional calls, for 640 total. On Linux omit `caffeinate -i`. The cap
counts new attempts in that invocation, including errors. No automatic retries.

After resolving a transport error, or resuming a request interrupted in flight:

```bash
caffeinate -i python3 -m exception_factorial run --config configs/factorial.json --output runs/factorial-001 --max-calls 640 --resume --retry-errors
```

A request interrupted in flight may already have been billed. Completed answers
are never called again. Invalid returned answers cannot be resampled; preserve
the run and inspect the response before documenting any separate protocol fix.

```bash
python3 -m exception_factorial analyze --output runs/factorial-001
open runs/factorial-001/summary.md
zip -r factorial-001.zip runs/factorial-001
```

The journal saves raw requests, raw responses, scores, usage, config, source and
plan fingerprints, and execution mode. Credentials are never saved. Old run
directories are rejected; changing source or config blocks resume. Live and
mock data cannot mix. Offline checks use
`python3 -m unittest discover -s tests -v`. An optional `--mock` run must use a
separate directory and provides no scientific evidence.
