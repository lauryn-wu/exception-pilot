# Reasoning instruction and written-output diagnostic

Protocol: `verified-facts-reasoning-cue-v1`. Fixed seed: `2026100892`.

## Question and scope

Does adding a reasoning instruction change verified-record accuracy when the
response must still contain only the answer? Does requiring pre-answer text
introduce an additional difference?

This follows the completed explanation study (direct 47/48; neutral CoT 25/48
on visible records). The selected-case missingness replay stopped at 7/10 exact
matches, below its fixed 8/10 feasibility threshold. Its 30 interventions were
not run. This new study uses fresh tables and conversations, without replaying
selected explanations or changing that stopped study.

This is a bounded explanatory diagnostic. It does not establish a neural
mechanism, faithful reasoning, novelty, or publication potential.

## Fixed design

- Model: `gpt-4o-2024-08-06`, temperature 0, one completion per request.
- 24 fresh worlds, two recorded-class variants, three conditions: **144 calls**.
- Each world contains ten vehicle records. A target's climate peers have a
  common class different from both possible recorded target classes.
- Within a world, only the target's Verified class cell changes between the
  two variants. All descriptions, row order, irrelevant features, and markers
  stay fixed. The recorded target class is the correct answer.
- All six assignments of A/B/C to the two records and competing pattern occur
  four times, twice for each target climate. Conditions and variants are
  randomized within each world using a saved, deterministic schedule.
- Each request is one independent user message. No previous responses,
  assistant prefixes, or separate answer keys are supplied.
- Every condition has the **same 1,000-completion-token allowance**. This is a
  ceiling, not a request to produce 1,000 tokens. Only 48 requests require text
  before the answer. All 144 could consume their allowance if noncompliant.
- Hard cumulative limit: **160 attempts**. This leaves room for 16 extra
  attempts while completing all 144 tasks. Retries after transport failures
  or unresolved requests require an explicit flag; repeated failures can
  exhaust the cap before collection finishes. Temperature zero does not
  guarantee determinism.

The shared introduction, table columns, and question match the previous
three-label diagnostic. In particular, its definition of `MISSING` remains in
the introduction even though every target here has a recorded class. Removing
it would bundle another intervention into this comparison. Conclusions are
initially specific to this task wording.

## Exact prompt endings

The same table and question are followed by exactly one of these endings.

**A — direct (`direct`)**

```text
Output only ANSWER: followed by A, B, or C.
```

**B — reasoning cue with answer-only output (`cue`)**

```text
Think step by step before answering. Output only ANSWER: followed by A, B, or C.
```

**C — requested written reasoning (`visible`)**

```text
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

These are the newly agreed endings, not exact replicas of the old direct/CoT
endings. A versus C is a contemporaneous check for the earlier type of harm.
`prepare` writes all 144 full API requests to `preview.json` and the first
world's six prompts to `preview.md`. The plan freezes all prompts, the schedule,
config, analysis specification, and source fingerprint before collection.

## Scoring and analysis fixed before collection

The final nonblank line must be exactly `ANSWER: A`, `ANSWER: B`, or `ANSWER: C`
(surrounding whitespace is ignored). A parseable answer is scored even if
there is unwanted text before it, or if C omits its explanation. Other final
formats are retained as unscorable; they are never retried or silently dropped.

Structural compliance is separate: A/B require answer-only output; C requires
nonempty text before a valid final answer. Text presence is not a judgment that
the text contains reasoning or faithfully reports internal computation. Reports
show answer-only and pre-answer-text counts, unknown flags for unparseable
finals, and compliance violations by condition. The main contrasts keep every
parseable answer regardless of these flags; there is no compliant-only primary
analysis.

The two co-primary descriptive contrasts are world-paired accuracy **A minus
B** and **B minus C**. **A minus C** checks whether the earlier kind of harm
appears in this run. Positive values favor the first condition. Each world
contributes its mean over its two recorded-class variants. The independent
analysis unit is the **world (24)**, not 144 calls or 48 independent cases.

Secondary record sensitivity is

`S = [I(y1 = r1) - I(y1 = r2) + I(y2 = r2) - I(y2 = r1)] / 2`.

Here `r1/r2` are the two target classes and `y1/y2` their answers. Correct
tracking gives 1, a constant answer gives 0, and reversing the records gives
-1. Accuracy and sensitivity answer different questions; an answer change
alone does not demonstrate successful lookup. Changing the target cell can
also affect whole-table statistics.

Intervals use 10,000 whole-world bootstrap resamples, seed `981723`, giving
descriptive, unadjusted 95% percentile intervals. They are not multiplicity-
adjusted confirmatory tests. Each contrast excludes a world if any answer it
requires is unscorable or not yet returned; reports identify exclusions.
After all planned requests return, worst-case full-plan bounds account for
unscorable answers. These bounds are point-estimate bounds, not confidence
intervals. A degenerate bootstrap interval does not prove certainty.

Collection has no outcome-based pass gate or automatic extension. The first
six-call block is only an operational check; do not select continuation based
on its accuracy. Finish the fixed plan unless a technical fault requires a
stop. Small or inconclusive differences do not establish equivalence.

## Interpretation

- If B is worse than A and B reliably obeys answer-only output, a generated
  pre-answer explanation is not necessary for the harm. B is an instruction
  control; it does not establish that hidden step-by-step reasoning occurred.
- If B is close to A and C is worse, the requirement to produce written text
  matters in this task. B versus C changes an output instruction and may change
  strategy; it does not uniquely identify self-conditioning or a specific
  internal mechanism. Similar point estimates alone do not establish B=A.
- If both contrasts show harm, they identify two prompt differences worth
  investigating. Their arithmetic sum is not a causal mediation analysis.
- If B produces pre-answer text, we cannot use those responses to claim harm
  without generated text. Report this limitation without excluding or retrying
  those responses. If C often omits text, the intended contrast is weakened.
- If A versus C does not reproduce the earlier harm, this run cannot localize
  that harm. Report the result and stop this screen; do not search for a new
  seed or wording that produces the desired outcome.

## Run on macOS

Use your existing Git checkout. No new dependencies or GPU are needed.

```bash
git pull --ff-only
python3 -m exception_cue prepare --config configs/cue.json --output runs/cue-001
open runs/cue-001/preview.md
```

If the key is not already set in this terminal, enter it without echoing it
(the following syntax is for macOS's default zsh):

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Check execution for one complete world, then finish the fixed plan:

```bash
caffeinate -i python3 -m exception_cue run --config configs/cue.json --output runs/cue-001 --max-calls 6
caffeinate -i python3 -m exception_cue run --config configs/cue.json --output runs/cue-001 --max-calls 144 --resume
open runs/cue-001/summary.md
zip -r cue-001.zip runs/cue-001
```

The first six count toward 144; an error-free resume makes only 138 more calls.
The completion report must say `stopped: complete` and `returned_answers: 144`.
It may contain fewer than 144 valid answers because format failures stay data.
Do not rerun the old missingness, explanation, or other studies.

After a transport error such as a timeout, resume the same directory:

```bash
caffeinate -i python3 -m exception_cue run --config configs/cue.json --output runs/cue-001 --max-calls 144 --resume --retry-errors
```

This retries only requests without a saved returned response. It never retries
a wrong answer, formatting violation, or returned unscorable response. An
interrupted in-flight request may have reached the provider; retrying it can
incur another charge. All attempts count against the fixed cumulative cap.
A returned truncated, refused, or wrong-model response stops the runner and
blocks resampling; preserve and share the run for inspection. Do not raise
token limits or change prompts midway through the study.

Recompute reports without API calls:

```bash
python3 -m exception_cue analyze --output runs/cue-001
```

The report includes `summary.json`, `summary.md`, and `answers.csv`; original
requests and raw responses are in the attempt journal. Analysis validates the
saved plan, source identity, schedule, response normalization, and scoring.

For an optional software check, use a separate output directory with `--mock`.
Mock runs are labeled simulated, never read credentials or call the API, and
cannot be resumed as live runs. They deliberately produce all-correct answers
and zero between-condition differences; they are not evidence for a hypothesis.
