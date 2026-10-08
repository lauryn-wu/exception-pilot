# Target-record availability: selected-case continuation diagnostic

Specified 2026-10-08 after reviewing the completed `explanation-001` run and
before collecting this diagnostic. This is a post hoc experiment on selected
reasoning traces, not an independent confirmation or a claim of novelty.

## Question

Some neutral-CoT responses describe the target's class as `MISSING` even though
the prompt contains its verified class. Does changing that availability claim,
without supplying the correct class, change the subsequent answer?

The intervention tests the causal influence of a sentence in supplied assistant
history. It does not identify a hidden belief or show that false missingness
caused the original spontaneous error. An earlier commitment to a pattern-based
answer could have produced both the false availability statement and the wrong
answer. The original task also defines `MISSING` for genuinely unrecorded cells;
that instruction may have primed use of the word in these visible-record cases.

## Frozen source selection

The parent run has 384 completed calls. This diagnostic uses ten visible-record,
neutral-CoT traces containing a target-specific `MISSING` line without a clear
correct-class statement in the audited trace. They come from nine parent worlds:
eight originally answered incorrectly and two correctly. The two correct cases
remain included. Source attempt 60 contained mixed evidence, including a correct
class statement, and is excluded from this narrower selection.

The fixed source attempt numbers are **2, 22, 82, 105, 129, 167, 170, 240, 297,
and 329**. These are selected cases, not a random sample of all CoT errors, and
the experiment cannot estimate the prevalence of this behavior. The selected
cases, parent plan, and source-record hashes are fixed in
`exception_missingness/core.py`. Preparation verifies the complete parent run
and each selected source. Do not replace a source or add cases after seeing
continuation outcomes.

The prefix ends immediately after the first line that contains both the target
ID and `MISSING`. All earlier text is retained. Original text after that line,
including the final answer, is omitted. The source prompt and its correct table
remain available in every arm.

## Four interventions

Only the single `MISSING` token at the frozen edit location is replaced. The
prefix before that line, all other text on the line, and the original prompt
remain unchanged.

For example, one selected case concerns target **EHZ5TN**, whose verified class
is **A** and whose same-climate pattern suggests **B**. Its original answer was
B. The edited line is:

| Arm | Line in the supplied assistant prefix | Information added |
|---|---|---|
| `original` | `- EHZ5TN: MISSING` | None; unchanged prefix for replay |
| `unavailable` | `- EHZ5TN: NOT RECORDED IN THE TABLE` | An explicit claim that the record is absent |
| `available` | `- EHZ5TN: RECORDED IN THE TABLE` | A claim that the record exists, without its class |
| `gold` | `- EHZ5TN: A` | The verified class itself |

The primary comparison is `available` versus `unavailable`. These two edits
differ only by the word `NOT`; neither supplies A, B, or C at the edit location.
They test whether the stated availability of the target's record affects the
answer. The gold arm additionally supplies its value, so a gold-only improvement
would leave answer priming, fact salience, and retrieval unresolved.

For each call, the runner sends:

1. The original saved prompt messages, including the accurate table.
2. An assistant message containing the frozen prefix for that arm.
3. This identical new user message:

```text
Continue the reasoning from these notes. Then put ANSWER: followed by A, B, or C alone on the final line.
```

This is **assistant-history replay followed by a new user turn**. It is not native
continuation of an unfinished assistant generation and does not preserve an
unobserved internal state. The unchanged-prefix arm measures how much this
replay procedure reproduces the original answers before interventions proceed.

## Budget and replay gate

- Model: `gpt-4o-2024-08-06`; temperature 0; one choice per request.
- Each completion is capped at 1,000 tokens; timeout defaults to 120 seconds.
- First phase: ten `original` replays, one for each selected case.
- Second phase: thirty interventions, one per case in each of the other arms.
- Maximum: **40 planned calls and 48 total attempts**, including transport errors
  and interrupted unresolved requests. No hidden retries are made.
- Intervention order is shuffled once using the fixed seed 2026100891 and saved
  in the plan. Each request is independent of the other continuation responses.
- No new case, prompt variant, model, or sampling block is added automatically.

The intervention phase requires all ten original replays to have complete,
scorable answers and **at least eight to exactly match their saved parent final
labels**. This is a practical feasibility threshold, not a significance test or
evidence that the replay process is identical to the original generation.

If the gate fails, **stop this branch**. Do not lower the threshold, change the
continuation instruction, select only successful replays, or restart the run to
replace unfavorable answers. If it passes, retain all ten cases, including any
whose replay answer differed from the parent, and run the fixed thirty edits.
The gate cannot be overridden by the intervention command.

The saved parent answer is used to assess replay fidelity. Comparisons with the
`original` arm use the new replay response, not the historical parent answer.
The original replays are collected before the shuffled interventions, so
comparisons against that arm also have a collection-order limitation. The
primary available-versus-unavailable comparison is within the shuffled phase.
There is one completion per case and arm; temperature zero does not guarantee
identical answers on repeat requests, and this diagnostic does not estimate
within-case sampling variability.

## Outcomes and analysis

The final nonempty line must be exactly `ANSWER: A`, `ANSWER: B`, or `ANSWER: C`,
allowing surrounding whitespace. Answers are scored against the verified class
in the original table. The analysis also reports pattern-label choices, final
label distributions, and each selected case's answers in all four arms.

**Primary contrast:** correctness under `available` minus correctness under
`unavailable`. First average paired case differences within each parent world,
then give the nine worlds equal weight. This prevents the world contributing
two selected cases from receiving twice the weight of other worlds.

Secondary contrasts, with the same weighting, are:

- `available` minus `original`: correcting the availability claim relative to
  the unchanged-prefix replay.
- `gold` minus `available`: supplying the actual class beyond stating that it
  exists.
- `unavailable` minus `original`: sensitivity to expressing the same absence
  claim as words rather than `MISSING`.

Report all arms and contrasts, not only favorable ones. Case-weighted estimates
are supplementary. Each paired contrast excludes a world if any of its selected
cases lacks a scorable answer in either required arm; exclusions are reported.
All returned answers remain in the run and arm-level counts.

Intervals use 10,000 bootstrap resamples of whole worlds, seed 981723. With only
nine worlds selected after examining the parent data, these are small-sample,
descriptive, unadjusted intervals. They are not confirmatory population
inference. A degenerate interval does not establish certainty or equivalence.
After all forty planned responses have returned, full-plan bounds assign each
unscorable outcome either correct or incorrect to bound each world-weighted
contrast. These are point-estimate bounds, not confidence intervals.

The runner saves the plan, exact requests, raw responses, attempts, and token
usage. Analysis writes `summary.json`, `summary.md`, and `answers.csv` without
making model calls. The forty calls are not forty independent experimental
units.

## Interpretation and stopping

| Result | Supported interpretation | Remaining limit |
|---|---|---|
| Replay gate fails | This continuation format does not adequately reproduce the selected original answers | Stop; no conclusion about the original mechanism |
| `available` improves over `unavailable` | The stated availability of the record causally affects answers under this replay procedure | Does not establish that false missingness caused the original spontaneous error |
| Only `gold` improves | Giving the actual class changes the continuation | Retrieval assistance, answer priming, and commitment remain unresolved |
| `unavailable` differs strongly from `original` | The continuation is sensitive to how absence is expressed | `MISSING` and prose absence claims are not behaviorally interchangeable |
| No clear differences | This small selected-case test supplies little evidence for the proposed text-level pathway | It does not prove equivalence or rule out other causes of CoT harm |

Even a positive primary contrast identifies a behavioral effect of the edited
assistant-history text in this selected subset. It does not prove that an
internal representation became missing, explain every CoT error, or establish
a novel mechanism. Any broader claim would require fresh examples, an
independent replication design, and another literature check. Finish this fixed
diagnostic if the replay gate passes, then review it before proposing more runs.

## Run on macOS

Keep the original `runs/explanation-001` folder unchanged. Preparation reads its
saved 384-call run locally and creates a separate `runs/missingness-001` folder.
No parent prompts need to be rerun.

From the repository folder, update the code:

```bash
git pull --ff-only
```

If using a GitHub ZIP download rather than a Git checkout, download and extract
the updated private repository instead of running `git pull`. Copy the original
`runs/explanation-001` directory into the new repository's `runs` directory,
preserving all its files. If using `explanation-001.zip`, extract it and locate
the folder containing `plan.json`, `execution.json`, and `attempts`; the final
path must be `runs/explanation-001`, without an extra nested `runs` folder.

Prepare the plan and inspect the generated preview:

```bash
python3 -m exception_missingness prepare --parent runs/explanation-001 --config configs/missingness.json --output runs/missingness-001
open runs/missingness-001/preview.md
```

In a new zsh terminal, set the API key without printing it:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Run only the ten original replays first:

```bash
caffeinate -i python3 -m exception_missingness run --output runs/missingness-001 --phase replay --max-calls 10
python3 -m exception_missingness analyze --output runs/missingness-001
open runs/missingness-001/summary.md
```

Run the intervention phase **only if `replay_gate.status` is `pass`**:

```bash
caffeinate -i python3 -m exception_missingness run --output runs/missingness-001 --phase interventions --max-calls 30 --resume
python3 -m exception_missingness analyze --output runs/missingness-001
```

If a transport error interrupts either phase, resume the same phase with
`--resume --retry-errors`, keeping the same output directory. For example:

```bash
caffeinate -i python3 -m exception_missingness run --output runs/missingness-001 --phase replay --max-calls 10 --resume --retry-errors
caffeinate -i python3 -m exception_missingness run --output runs/missingness-001 --phase interventions --max-calls 30 --resume --retry-errors
```

Use only the command for the interrupted phase; the second still requires a
passing replay gate. Already returned responses are skipped. The per-invocation
call limit does not override the cumulative 48-attempt cap. Completed responses
with invalid formatting are retained and never resampled. Incomplete provider
responses, including truncation or model mismatch, require inspection rather
than replacement as transport failures. Preserve the run if the gate fails, an
incomplete response blocks it, or the total attempt cap is reached.

To share the diagnostic, from the repository folder:

```bash
zip -r missingness-001.zip runs/missingness-001
```
