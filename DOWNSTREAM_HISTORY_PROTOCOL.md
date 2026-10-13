# Matched downstream history control

Protocol: `verified-facts-downstream-history-v1`.

This is a small exploratory follow-up to the completed downstream text-edit
experiment. It asks whether including the preceding classification exchange
changes the rate of false `MISSING` answers to the **same factual question**.
It reuses frozen source cases, collects both conditions contemporaneously, and
does not import any previous follow-up answers as observations in the new run.

## Question and two conditions

Both conditions ask this question verbatim, substituting only the case's plate:

> What is written in {plate}'s Verified class cell? Reply with exactly one of A, B, C, or MISSING.

| Condition | Messages sent |
|---|---|
| `history_present` | Original user message, including the intro, table, classification query and class-copy/reasoning instructions; the exact saved original assistant response; the factual question as a new user message. |
| `history_absent` | One user message containing the exact original intro and table, a blank line, and the identical factual question. The old classification query, response instructions and assistant response are omitted. |

The entire `history_present` request must match the old downstream `original`
request for that case: messages, model, temperature, token cap and other API
settings. There is no fresh classification generation or selection of a new
assistant answer. Each condition/repetition is an independent reconstructed
conversation, not a resumed hidden state or a branch of an earlier follow-up.

The no-history message preserves the complete intro/table substring byte for
byte. This includes the original MISSING definition and conditional prediction
rule, even when all target records in a cohort are present. The source tail is
validated against the original classification template before removing it.
For genuine-missing calibration cases, the old feature-profile query is removed
too. The target remains identified in the identical factual question.

**No wording factor is manipulated.** Both conditions list A/B/C/MISSING in the
same order. Neither adds a new exact-copy or retrieval instruction. In particular,
the proposed replacement "Reply with only the cell's exact contents" is not
used. The options-present/options-absent factorial is deferred.

## Frozen source cases and sample size

Reuse all 36 cases in `exception_downstream/source_snapshot.json`, validated by
the original downstream loader and its frozen digest. Keep all original cohort
labels and membership; no new keyword filtering, semantic annotation, source
replacement, or selection on old/new follow-up outcomes occurs.

| Cohort | Source cases | Worlds within cohort | New calls: 2 conditions × 3 repeats |
|---|---:|---:|---:|
| `contradiction` — correct original copy and final class, reviewed false missingness claim | 13 | 9 | 78 |
| `availability_control` — correct copy and final class, no reviewed false target-missingness claim | 13 | 9 | 78 |
| `genuine_missing_control` — literal MISSING table cells | 9 | 9 | 54 |
| `wrong_final_diagnostic` — correct copy, originally wrong final class | 1 | 1 | 6 |
| Total | 36 | Cohorts can share worlds; do not add these counts | **216** |

These are selected historical source traces, not a random population sample.
The availability controls are not certified fully factual explanations. The
genuine-missing sources originated in a different feature-profile query and
serve calibration, not a matched manipulation of source missingness. The single
wrong-final case remains a descriptive diagnostic. Never pool these cohorts
to create the primary estimate or treat a between-cohort difference as causal.

This protocol does not certify all 163 keyword-negative records in the parent
inventory as semantic negatives. Eligibility for this follow-up is simply the
already-frozen 36-case list; broad missingness prevalence is outside its scope.

## Collection and controls

- Model: `gpt-4o-2024-08-06`; temperature 0; `max_completion_tokens=64`;
  `n=1`; `store=false`. Same settings in both conditions and in the old
  original-text reference. No system prompt, schema or forced decoding is added.
- Three scheduled calls per case/condition, including at temperature zero.
  They measure possible endpoint variation and are not independent worlds.
- Freeze the entire plan and every exact request before any live call. Shuffle
  world blocks, then case/repetition pairs within each world. Keep each pair
  adjacent and randomize which condition is called first, using the frozen seed.
- All 216 calls are planned. The cumulative cap is 240 attempts to allow a
  bounded number of explicit transport retries. No outcome-based extension,
  scientific success gate, selective stopping or automatic answer resampling.
- Use the existing shared runner: journal requests before sending, retain raw
  returns before parsing, reject source/config/plan/request drift on resume,
  keep live/mock runs separate, and stop permanently on a model identity error.
- Refusals, truncation and malformed returned answers are retained as terminal
  invalid observations. They are not counted as ordinary incorrect classes.
  Transport errors require an explicit retry flag. An unresolved in-flight
  request blocks resume and must be reviewed rather than blindly resent.
- Existing experiments, protocols, saved source responses and result archives
  remain unchanged. Use a separate run directory and branch/worktree.

## Outcomes and analysis

Use the existing downstream strict scorer. After trimming outer whitespace, a
complete response must be exactly `A`, `B`, `C`, or `MISSING`, with a matching
model identity. Verify the answer key independently against the target's cell
in the original table.

`false_missing` means the returned answer is literally `MISSING` when the table
contains A/B/C. It is an objective answer outcome, not a semantic judgment of
the rationale. `accuracy` means the returned value matches the actual cell.
On genuine-MISSING cases, report accuracy: false missingness is impossible by
definition, so an all-zero false-MISSING contrast is not evidence of reliability.

**Primary:** in the 13-case contradiction cohort, estimate

`false_missing(history_present) - false_missing(history_absent)`.

Average the three repetitions within case/condition, then cases within world,
then give each of the nine worlds equal weight. Positive values mean more false
MISSING answers after the saved classification exchange. Report both condition
rates using the same complete-world membership alongside the paired difference.
Raw call counts are descriptive and need not equal the world-weighted rate.

Secondary analyses report accuracy and false-MISSING differences separately
for each cohort, plus response distributions and paired transitions. All such
comparisons and 95% world-bootstrap intervals are descriptive and unadjusted;
the lone wrong-final world cannot supply a useful population uncertainty estimate.

Use 10,000 whole-world bootstrap resamples, keeping all cases, conditions and
repetitions for a world together. A contrast-complete world requires every
planned case/repetition in both conditions to have a valid answer. Report each
contrast's own complete/planned world counts. Retain every invalid or absent
cell as unknown in full-plan lower/upper bounds; those bounds are not confidence
intervals. A zero or narrow bootstrap interval does not establish equivalence.

Export `summary.json`, `summary.md`, `responses.jsonl`, `responses.csv`,
`paired-transitions.csv`, and `world-contrasts.csv`, together with the source-bound
plan, all 216 requests in `preview.json`, execution identity, and raw attempts.
Mock output must be prominently labeled simulated and never reported as model
evidence. A prepared but unstarted run is labeled not started.

## What the comparison identifies

This tests the complete preceding-classification-exchange package under a fixed
factual question. Removing it changes the old classification task/instructions,
assistant text, input length, distance to the table, role/message structure and
turn count together. That is the declared intervention, not an isolated edit of
the false missingness sentence. The two arms do not isolate which of those
components causes a difference.

If history-present has materially more errors, the saved exchange contributes
to factual follow-up failure in this selected setting. That alone does not show
that the false missingness claim specifically caused the error. If false MISSING
answers also occur without history, the preceding explanation is not necessary
for those errors. Similar measured rates do not establish equality or rule out
offsetting case-specific effects. Neither outcome identifies an internal belief,
the effect of the listed options, or behavior without the shared MISSING rule.

## Run from a separate checkout

Python 3.10+ and the standard library are sufficient. Run from the repository
root. Creating the plan, inspecting requests, mock execution, tests and analysis
are offline. Only `run` without `--mock` makes paid API calls.

```bash
git clone --branch codex/downstream-history-control --single-branch \
  https://github.com/lauryn-wu/exception-pilot.git exception-pilot-downstream-history
cd exception-pilot-downstream-history

python3 -m exception_downstream_history prepare \
  --config configs/downstream_history_gpt4o.json \
  --output runs/downstream-history-gpt4o-001
```

Inspect `runs/downstream-history-gpt4o-001/preview.json` for all requests and
`preview.md` for a readable sample. The output-only metadata is not sent to the
model. Set `OPENAI_API_KEY` in your environment without putting it in the config.
Then collect the fixed study:

```bash
python3 -m exception_downstream_history run \
  --config configs/downstream_history_gpt4o.json \
  --output runs/downstream-history-gpt4o-001 \
  --max-calls 216
```

After a normal `--max-calls` pause, resume with the same code and configuration:

```bash
python3 -m exception_downstream_history run \
  --config configs/downstream_history_gpt4o.json \
  --output runs/downstream-history-gpt4o-001 \
  --max-calls 216 --resume
```

Only for a recorded transport error, add `--retry-errors` to that resume command.
The 240-attempt total cap still applies. Never reuse a mock output directory for
live collection or manually delete an invalid return to obtain a new answer.

```bash
python3 -m exception_downstream_history analyze \
  --output runs/downstream-history-gpt4o-001

python3 -m unittest discover -s tests -p 'test_downstream_history.py' -v
```

To exercise the complete workflow offline, use a different output directory:

```bash
python3 -m exception_downstream_history run \
  --config configs/downstream_history_gpt4o.json \
  --output runs/downstream-history-MOCK \
  --max-calls 216 --mock
```
