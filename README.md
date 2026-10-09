# Exception pilot

## Current follow-up: Mistral V2 word-boundary setup check

V1 stopped on its first returned capability response: `Cobalt Mape Lantern`.
The supplied prefix was preserved, but the exact required continuation was not.
V1's probe cut inside a word; the research replays always cut after whitespace.
V2 changes only that setup prefix to `Cobalt ` (one trailing ASCII space), keeps
the exact full-answer requirement, and preserves every research-case request,
sample size, replay rule, and scientific gate. Read the documented amendment in
[MISTRAL_PREFIX_V2_PROTOCOL.md](MISTRAL_PREFIX_V2_PROTOCOL.md).

Keep the failed V1 run. With `MISTRAL_API_KEY` already exported, first run one
request in a new directory:

```bash
python3 -m exception_mistral_prefix_v2 prepare --config configs/mistral_prefix_v2.json --output runs/mistral-prefix-v2-001
caffeinate -i python3 -m exception_mistral_prefix_v2 run --config configs/mistral_prefix_v2.json --output runs/mistral-prefix-v2-001 --max-calls 1
```

Inspect the output before collecting research cases. A returned invalid response
still stops the run and cannot be replaced by a retry.

## Archived V1: Mistral prefix-continuation feasibility

Use **`python3 -m exception_mistral_prefix`** with
**`configs/mistral_prefix.json`**. This uses **Mistral Small 4**
(`mistral-small-2603`) through Mistral's API. It replaces the proposed DeepSeek
collection because account funding failed. Model behavior has not yet been
established on Mistral. No GPU, local model download, or new dependencies are
required. Mistral documents Free-mode API access without a credit card, subject
to the account's usage and rate limits; the whole pilot is not guaranteed free.

The same bounded design has **at most 73 returned responses**: one prefix-contract
check, 48 direct-versus-visible-explanation requests on 12 worlds, and 24
unchanged continuations only if the behavioral gate passes. The cumulative cap
is 89 attempts. These are feasibility checks, not mechanism evidence; no edited
explanation experiment starts automatically. Read
[MISTRAL_PREFIX_PROTOCOL.md](MISTRAL_PREFIX_PROTOCOL.md) for the fixed design.

Mistral returns the supplied prefix as part of its response. This adapter checks
that exact prefix and scores the full completion once. The DeepSeek package's
suffix-only contract is separate; keep any old run directories unchanged.

Create a key in [Mistral Studio](https://console.mistral.ai/) under **API Keys**.
From your existing macOS checkout:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_mistral_prefix prepare --config configs/mistral_prefix.json --output runs/mistral-prefix-001
open runs/mistral-prefix-001/preview.md
```

In the same zsh terminal:

```zsh
read -s "MISTRAL_API_KEY?Paste your Mistral API key: "
export MISTRAL_API_KEY
```

Run five calls first. If they complete normally, resume the permitted remainder:

```bash
caffeinate -i python3 -m exception_mistral_prefix run --config configs/mistral_prefix.json --output runs/mistral-prefix-001 --max-calls 5
caffeinate -i python3 -m exception_mistral_prefix run --config configs/mistral_prefix.json --output runs/mistral-prefix-001 --max-calls 73 --resume
open runs/mistral-prefix-001/summary.md
zip -r mistral-prefix-001.zip runs/mistral-prefix-001
```

The first five calls count toward the total. A failed behavioral gate stops at
49 responses; otherwise the run attempts the 24 unchanged replays. A returned
technical/formatting failure is retained and stops collection. Only after a
retryable transport error, add `--retry-errors` to the resume command. For a rate
limit, wait for the account's limit to reset first. Preparation and analysis are
offline. Default mock runs are simulated and intentionally stop at 49 all-correct
responses. Never mix model providers in one run.

## Alternative provider: DeepSeek prefix-continuation feasibility

Use **`python3 -m exception_prefix`** with **`configs/prefix.json`**. This checks
whether one model reproduces the direct-versus-explanation failure and can
continue unchanged explanation prefixes reliably enough for a later causal
experiment. It uses the **DeepSeek API** (`deepseek-flash`, currently
DeepSeek-V4.1-Flash), with the provider's separate thinking mode disabled and
visible explanations requested explicitly. No local model or GPU is required.

The fixed maximum is **73 returned responses**: one prefix-contract check,
48 base requests on 12 fresh worlds, and 24 unchanged continuations if the base
behavior meets the fixed practical criteria. The attempt cap is 89, including
explicit transport retries. This is a feasibility check; it does not edit
reasoning, identify a mechanism, or automatically start another experiment.
Read [PREFIX_PROTOCOL.md](PREFIX_PROTOCOL.md) for exact prompts, cut rules,
thresholds, price assumptions, and interpretation limits.

From your existing macOS checkout:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_prefix prepare --config configs/prefix.json --output runs/prefix-001
open runs/prefix-001/preview.md
```

Use a **DeepSeek API key**, not an OpenAI key. In the same zsh terminal:

```zsh
read -s "DEEPSEEK_API_KEY?Paste your DeepSeek API key: "
export DEEPSEEK_API_KEY
```

```bash
caffeinate -i python3 -m exception_prefix run --config configs/prefix.json --output runs/prefix-001 --max-calls 5
caffeinate -i python3 -m exception_prefix run --config configs/prefix.json --output runs/prefix-001 --max-calls 73 --resume
open runs/prefix-001/summary.md
zip -r prefix-001.zip runs/prefix-001
```

The first five calls count toward the total. If there is insufficient target
behavior, collection stops after 49 responses; otherwise it completes all 24
unchanged replays. These are predefined investment checks, not significance
tests. Any returned technical or formatting failure is retained and stops the
run. Only retryable transport errors permit `--resume --retry-errors`; no
returned answer can be replaced. Preparation and analysis make no model calls.

The model name is a changing provider alias rather than a pinned snapshot;
returned metadata and timestamps are saved. Published peak rates on 2026-10-09
are $0.30/M uncached input tokens and $1.20/M output tokens. As an illustration,
100 requests averaging 2,000 input and 1,000 output tokens cost about $0.18.
The actual bill depends on usage and current provider pricing. No new Python
dependencies are required. Preserve older studies and run directories.

## Separate follow-up: 192-call answer-revision diagnostic

Use **`python3 -m exception_revision`** with **`configs/revision.json`**.
This asks whether a correct initial answer can be overturned after the model
generates reasoning. The original classification question is preserved.

| Arm | Required output order |
|---|---|
| Original reasoning-first | reasoning → answer |
| Original answer-first | answer → reasoning |
| New revision | initial_answer → reasoning → final_answer |
| New repeat control | initial_answer → final_answer → reasoning |

The new pair has identical instructions and fields; only schema property order
differs. Both permit the final answer to match or differ from the initial one.
The primary comparison is repeat-control minus revision **final accuracy**,
using every case, not only initially correct answers. The original order pair
checks replication on the same new worlds. Transition counts describe changes
between initial and final answers, including changes to the background pattern.

The fixed design is **24 fresh worlds × 2 recorded-class variants × 4 arms =
192 calls**, with the same GPT-4o snapshot and equal token ceilings. See
[REVISION_PROTOCOL.md](REVISION_PROTOCOL.md) for exact prompts, analysis, and
interpretation limits. This tests reasoning placement around a revisable
answer; it does not identify the effect of a specific reasoning statement.

From your existing checkout on macOS, using your existing `OPENAI_API_KEY`:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_revision prepare --config configs/revision.json --output runs/revision-001
open runs/revision-001/preview.md
caffeinate -i python3 -m exception_revision run --config configs/revision.json --output runs/revision-001 --max-calls 8
caffeinate -i python3 -m exception_revision run --config configs/revision.json --output runs/revision-001 --max-calls 192 --resume
open runs/revision-001/summary.md
zip -r revision-001.zip runs/revision-001
```

The first eight calls check execution and count toward 192; a normal resume
makes 184 more. Continue regardless of accuracy. Any returned schema/order
failure, empty reasoning, refusal, truncation, or model mismatch is retained
and stops collection. Valid wrong answers do not stop the run. Explicit
transport retries count toward the fixed cap of 224 attempts. Preparation and
analysis are offline; no new dependencies or GPU are required. Fetch/merge
preserves local commits; resolve any conflict before running.

## Completed follow-up: 72-call answer-order diagnostic

The supplied `order-001` run returned **24/24 correct for answer-only, 15/24
for reasoning-first, and 24/24 for answer-first**. All 72 outputs complied;
all nine errors followed the competing background pattern. Correct answers
in answer-first could still be followed by incorrect explanatory statements.
These are 12-world, single-model results. The commands below document that
earlier experiment.

Use **`python3 -m exception_order`** with **`configs/order.json`**. This tests
whether an answer changes when the model writes an explanation before versus
after it, with a contemporaneous answer-only control. All three conditions use
strict JSON; the two explanation conditions have identical prompts and fields,
with only the schema property order changed. The raw response order is checked.

The fixed design is **12 fresh worlds × 2 target-record variants × 3 conditions
= 72 planned calls**, using **`gpt-4o-2024-08-06`**. The independent sampling unit
is the world. This is a small diagnostic for large differences, not a definitive
mechanism test. Read [ORDER_PROTOCOL.md](ORDER_PROTOCOL.md) for exact prompts,
scoring, analysis, and interpretation limits.

From your existing checkout on macOS, using your existing `OPENAI_API_KEY`:

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

The initial six calls count toward 72; a normal resume makes 66 more. They check
execution and output compliance only. Finish the fixed plan regardless of
accuracy. A malformed response, wrong field order, empty explanation, refusal,
truncation, or wrong-model response is retained and stops the run; do not
resample it. Valid but incorrect answers are retained and do not stop collection.
Eligible transport retries require `--resume --retry-errors` and count toward
the cumulative cap of 88 attempts. No new dependencies or GPU are needed;
preparation and analysis make no model calls.

If Git reports a merge conflict, resolve it before running rather than
discarding local commits. The fetch/merge commands above preserve your history.

The primary contrast is answer-first minus reasoning-first accuracy. Answer-only
comparisons test whether asking for a future explanation can affect the answer
before explanatory text is written. An order effect does not distinguish
self-conditioning from changed strategy or early answer commitment. There is no
automatic scientific pass gate, claim of novelty, or outcome-driven expansion.

## Completed follow-up: 96-call cue test with enforced answer-only output

Collection returned **48/48 correct in both direct and cue conditions**, with
all 96 outputs complying with the single-answer schema. These reused the earlier
24 worlds. The disappearance of the observed cue gap under this interface does
not establish that written explanations caused the earlier errors. The commands
in this section are historical; use the separate revision study above next.

Use **`python3 -m exception_constrained_cue`** with
`configs/constrained_cue.json`. This compares direct answering with a
step-by-step instruction while **both conditions use the same strict JSON
schema permitting only an A/B/C answer**. It repairs the previous cue study's
failed answer-only control.

The design reuses all 24 cue worlds and both recorded-class variants:
**24 × 2 × 2 = 96 planned calls**. The model remains
**`gpt-4o-2024-08-06`**, with equal token ceilings and separate conversations.
These are previously examined worlds, not a fresh-item replication. Read
[CONSTRAINED_CUE_PROTOCOL.md](CONSTRAINED_CUE_PROTOCOL.md) for the exact schema,
prompts, paired analysis, and interpretation limits.

From your existing checkout on macOS, using your existing `OPENAI_API_KEY`:

```bash
git pull --ff-only
python3 -m exception_constrained_cue prepare --config configs/constrained_cue.json --output runs/constrained-cue-001
open runs/constrained-cue-001/preview.md
caffeinate -i python3 -m exception_constrained_cue run --config configs/constrained_cue.json --output runs/constrained-cue-001 --max-calls 4
caffeinate -i python3 -m exception_constrained_cue run --config configs/constrained_cue.json --output runs/constrained-cue-001 --max-calls 96 --resume
open runs/constrained-cue-001/summary.md
zip -r constrained-cue-001.zip runs/constrained-cue-001
```

The four-call execution check counts toward the total; an error-free resume
makes only 92 more calls. Continue based on correct execution, irrespective
of answer accuracy. No new dependencies or GPU are needed. Preparation and
analysis make no API calls. Transport retries require `--resume --retry-errors`
and count toward the hard cap of 112 attempts. Any schema violation, refusal,
truncation, or wrong-model response is retained and stops collection; it cannot
be resampled. Completed runs have 96 valid answers and zero invalid answers.

A harmful cue effect would show that a written explanation is unnecessary
under this interface. A null difference would not prove that written reasoning
caused the earlier errors: constraining output may also change task strategy.
This study does not identify hidden reasoning or a neural mechanism.

## Completed follow-up: 144-call reasoning instruction/output diagnostic

Collection returned 144 valid final answers: direct **48/48**, cue **33/48**,
and requested written reasoning **23/48**. All 48 cue responses wrote
explanations, so this study did not isolate the cue without generated text.
Preserve these results. The original run instructions below are historical;
use the separate constrained experiment above for the new follow-up.

Use **`python3 -m exception_cue`** with `configs/cue.json`. The model remains
**`gpt-4o-2024-08-06`**. This compares:

- **A:** answer only.
- **B:** a step-by-step instruction, with the same answer-only requirement.
- **C:** a step-by-step instruction requiring written reasoning before the answer.

There are **24 fresh worlds × 2 recorded-class variants × 3 conditions = 144
planned calls**. Every condition has the same 1,000-token completion allowance.
Answer correctness and output compliance are reported separately; violations
are retained and never retried. Read [CUE_PROTOCOL.md](CUE_PROTOCOL.md) for exact
prompts, fixed analysis, limitations, and error recovery.

From your existing Git checkout on macOS:

```bash
git pull --ff-only
python3 -m exception_cue prepare --config configs/cue.json --output runs/cue-001
open runs/cue-001/preview.md
caffeinate -i python3 -m exception_cue run --config configs/cue.json --output runs/cue-001 --max-calls 6
caffeinate -i python3 -m exception_cue run --config configs/cue.json --output runs/cue-001 --max-calls 144 --resume
open runs/cue-001/summary.md
zip -r cue-001.zip runs/cue-001
```

The first six calls count toward the total; the second command makes only 138
more if there are no errors. The six-call block checks execution, not whether
the result looks promising. Finish the fixed plan regardless of its accuracy.
Use your existing `OPENAI_API_KEY`; no new dependencies or GPU are needed.
Preparation and analysis make no API calls. A transport failure can be resumed
with `--resume --retry-errors`, within the hard cap of 160 total attempts.
Returned wrong or unscorable answers are never resampled.

This can narrow which prompt requirement matters; it does not by itself identify
an internal mechanism. If the A–C harm does not reappear, this run cannot explain
the earlier gap. There is no automatic sample extension or scientific pass gate.

## Stopped follow-up: false-missingness replay

The selected-case replay returned 10 valid answers and reproduced **7/10** saved
parent answers. It failed the fixed feasibility threshold of 8/10, so the
remaining 30 interventions were **not run**. Preserve `runs/missingness-001` as
`replay_gate_failed_stop`. Do not restart it, loosen the threshold, or run its
intervention phase. There are no causal arm contrasts from this stopped study.
The implementation and [MISSINGNESS_PROTOCOL.md](MISSINGNESS_PROTOCOL.md) remain
available for audit. The new cue diagnostic does not reuse its selected cases.

Earlier studies below are historical reference. Do not rerun them for this
new diagnostic.

## Completed follow-up: 384-call explanatory diagnostic

Collection is complete: 384 valid answers. On the 48 visible-record cases,
neutral CoT answered 25 correctly, class copying 48, and same-row marker copying
29. None of the 48 correct class copies was followed by a wrong final answer.
The selected false-missingness follow-up stopped at its replay gate; these
results alone do not identify an internal mechanism or establish novelty.

Use **`python3 -m exception_explanation`** with `configs/explanation.json`.
This asks whether failures persist after correctly copying a verified class,
and whether copying that class helps more than copying another field from the
same row. A three-label design changes only the target class cell while keeping
the surrounding pattern fixed. Original-format binary anchors check that the
earlier behavior still appears. The model remains **`gpt-4o-2024-08-06`**.

There are **24 independent worlds and 384 planned calls**, with a hard cap of
400 total attempts including transport errors. This is a bounded exploratory
diagnostic, not a claim of novelty or a guarantee of a publishable result.
Read [EXPLANATION_PROTOCOL.md](EXPLANATION_PROTOCOL.md) for the example, exact
design, contrasts, interpretation limits, and recovery instructions.

From your existing Git checkout on macOS:

```bash
git pull --ff-only
python3 -m exception_explanation prepare --config configs/explanation.json --output runs/explanation-001
open runs/explanation-001/preview.md
caffeinate -i python3 -m exception_explanation run --config configs/explanation.json --output runs/explanation-001 --max-calls 16
caffeinate -i python3 -m exception_explanation run --config configs/explanation.json --output runs/explanation-001 --max-calls 384 --resume
open runs/explanation-001/summary.md
zip -r explanation-001.zip runs/explanation-001
```

The first 16 calls count toward the 384 total. After an error-free first block,
resume makes only 368 additional calls. Use the same `OPENAI_API_KEY`; setup for
a new terminal is in the protocol. `prepare` makes no API calls. No new packages
or GPU are required. If using a source ZIP rather than Git, download the updated
source into a separate folder and keep your existing results.

Completed but unparseable answers are retained while the other tasks continue;
they are never sampled again. Copy errors are scored separately from final
answers. Missing-class cases have no accuracy score. The report uses world-paired
contrasts and reports uncertainty, not an automated scientific pass. For a
transport failure, add `--retry-errors` to the resume command. For an incomplete
provider response, preserve the run and inspect the report before continuing.

Earlier studies and their frozen source packages are preserved. Do not rerun
them for this diagnostic. All commands below are historical reference.

## Completed follow-up: 640-call question × uncertainty diagnostic

**If `factorial-001` stopped at attempt 596 on an invalid final-answer format:**
use the [documented continuation](FACTORIAL_RECOVERY.md). It preserves that
returned response and finishes only the 44 unattempted tasks. Do not restart
the study or resample the invalid answer. The original strict analysis stays
unchanged; the continuation is explicitly recorded as a post-result amendment.

Use **`python3 -m exception_factorial`** with `configs/factorial.json`. This study
separates two changes that were bundled in the completed wording experiment:
asking for the recorded class and removing the uncertainty sentence. It tests
all four combinations on 20 fresh lists, with direct and neutral reasoning
responses in supporting and conflicting backgrounds. The model remains
**`gpt-4o-2024-08-06`**. Collection is complete: 640 returned responses, 639
scorable final answers, and 19 complete worlds for the strict paired analysis.
The interaction interval included zero. The protocol below was fixed before
collection; the recovery amendment preserved the single unparseable response.

Read [FACTORIAL_PROTOCOL.md](FACTORIAL_PROTOCOL.md) for the exact prompts,
predefined contrasts, interpretation plan, and limitations. This is a separately
specified explanatory follow-up after inspecting earlier results. It preserves
the earlier `stop_explicit_record_boundary` decision and has no new pass gate.

From your Git checkout on macOS:

```bash
git pull --ff-only
python3 -m exception_factorial prepare --config configs/factorial.json --output runs/factorial-001
open runs/factorial-001/preview.md
caffeinate -i python3 -m exception_factorial run --config configs/factorial.json --output runs/factorial-001 --max-calls 32
caffeinate -i python3 -m exception_factorial run --config configs/factorial.json --output runs/factorial-001 --max-calls 640 --resume
zip -r factorial-001.zip runs/factorial-001
```

The first 32 calls are included in the **640 total**; the resume command makes
608 additional calls after an error-free check. Use the same `OPENAI_API_KEY`.
In a new zsh terminal, set it using the instructions below or in the protocol.
Prepare makes no API calls. No new dependencies or GPU are needed. On Linux,
omit `caffeinate -i`. If the folder came from a ZIP and is not a Git checkout,
download the updated source or clone the private repo into a separate folder;
keep all existing run folders.

Completion reports `complete_ready_for_interpretation`, not a scientific pass.
The report includes all 16 cell accuracies, the four extra conflict penalties,
the question-by-sentence interaction, and both factors' simple effects. Run
`python3 -m exception_factorial analyze --output runs/factorial-001` to regenerate
the report without API calls. Transport-error recovery uses the same run command
with `--resume --retry-errors`; returned invalid answers cannot be resampled.

Keep `reference-001`, `counterfactual-001`, and `wording-001` in their existing
folders. Their source packages, configs, protocols, and decisions are unchanged.
The new module rejects earlier run directories and preserves their source
fingerprints. No second model or further study starts automatically.

## Earlier follow-up: 480-call wording confirmation

Use **`python3 -m exception_wording`** with `configs/wording.json`. This separate
study tests the positive counterfactual pilot on 20 fresh lists, crossing the
original versus recorded-class question with direct answers, the original
reasoning instruction, and neutral “Think step by step” reasoning. The model
remains `gpt-4o-2024-08-06`. This study is now completed; its commands are retained
here for reference. Use the explanation commands above for the current follow-up.

Read [WORDING_PROTOCOL.md](WORDING_PROTOCOL.md) for all six wording combinations,
the primary contrast, ordered decision rules, limitations, and recovery steps.
From your Git checkout:

```bash
git pull --ff-only
python3 -m exception_wording prepare --config configs/wording.json --output runs/wording-001
open runs/wording-001/preview.md
caffeinate -i python3 -m exception_wording run --config configs/wording.json --output runs/wording-001 --max-calls 24
caffeinate -i python3 -m exception_wording run --config configs/wording.json --output runs/wording-001 --max-calls 480 --resume
zip -r wording-001.zip runs/wording-001
```

The first 24 calls count toward the **480 total**. Use the same `OPENAI_API_KEY`;
the protocol explains how to set it in a new terminal. Prepare makes no API
calls. On Linux omit `caffeinate -i`. No new dependencies or GPU are needed.
Keep `reference-001` and `counterfactual-001` in their existing folders. Their
source packages, protocols, and decisions are unchanged. The new study's source
fingerprint is separate, and it cannot resume either previous run.

## Earlier follow-up: 160-call verified-facts diagnostic

The new, separate experiment uses **`python3 -m exception_counterfactual`**, model
`gpt-4o-2024-08-06`, and `configs/counterfactual.json`. It changes only other
vehicles' labels while keeping both target records and the 20% exception rate
fixed. It contains no generated history. There are 20 independent matched lists
and 160 planned calls.

Read [COUNTERFACTUAL_PROTOCOL.md](COUNTERFACTUAL_PROTOCOL.md) for the exact design,
decision rule, preview, and recovery instructions. Keep the completed reference
run in its original folder. The original stage-1 stop decision and Stage 2 gate
remain intact; this follow-up is explicitly exploratory.

From this folder, prepare without API calls:

```bash
python3 -m exception_counterfactual prepare --config configs/counterfactual.json --output runs/counterfactual-001
```

After inspecting `runs/counterfactual-001/preview.md` and setting `OPENAI_API_KEY`,
run an eight-call check, then finish the same plan:

```bash
caffeinate -i python3 -m exception_counterfactual run --config configs/counterfactual.json --output runs/counterfactual-001 --max-calls 8
caffeinate -i python3 -m exception_counterfactual run --config configs/counterfactual.json --output runs/counterfactual-001 --max-calls 160 --resume
```

The second command skips completed calls. Open `runs/counterfactual-001/summary.md`
after completion. On Linux, omit `caffeinate -i`. No packages or GPU are required.
The new code shares the original provider and parsing helpers without modifying
any original Python source, so the original run's source fingerprint is preserved.

## Original staged experiment (preserved)

Does asking a model to reason make it repeatedly misclassify verified exceptions?
This repository implements a bounded replication screen followed by conditional
diagnostics. Raw model responses stay in ignored run folders and are not committed.
Simulated tests are explicitly labeled and cannot authorize a live diagnostic run.

**Historical starting instructions:** use the 1,200-call stage-1 configuration on
`gpt-4o-2024-08-06`. Run eight calls first to check access and formatting, then
resume the same run. Stage 2 is a separate 320-call command and only starts when
its completed stage-1 parent meets the predeclared exploratory gate.

Read [PROTOCOL.md](PROTOCOL.md) for the exact experiment, deviations from the
reference study, estimands, decision rule and limitations. This is a conceptual,
abbreviated replication, not a reproduction of the authors' exact dataset or
historical model service.

## 1. Open the project

Unzip the source package and open a terminal in its `exception-pilot` directory.
Python **3.10 or newer** on macOS or Linux is required. No packages, GPU or model
downloads are needed; the implementation uses Python's standard library.

```bash
cd exception-pilot
python3 --version
python3 -m unittest discover -s tests -v
```

If the folder is elsewhere, replace the `cd` path with its actual location.
The tests use fixtures only and do not read API credentials or contact OpenAI.
Installing the optional command-line entrypoint with `pip install -e .` is not
necessary for any command below.

## 2. Inspect the experiment without spending money

```bash
python3 -m exception_pilot prepare --config configs/stage1.json --output runs/reference-001
```

This makes no network requests. Inspect:

- `runs/reference-001/plan.json`: all generated data, ground truth, presentation
  orders, conditions, settings and immutable hashes.
- `runs/reference-001/preview.json`: the first real API request for each condition
  with a separate answer key. The answer key is **not** sent to the model.

The expected counts are 20 independent lists and 1,200 prediction calls. There
are 10 vehicles per list and three passes through each list in each condition.

## 3. Set the API key

In the default macOS **zsh** terminal, paste these lines one at a time. The first
line prompts for the key without displaying it; press Return after pasting.

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

For **bash** instead:

```bash
read -rsp "Paste your OpenAI API key: " OPENAI_API_KEY
export OPENAI_API_KEY
```

Do not put the key in a config, script, screenshot or chat. The code reads the
environment variable, does not load `.env` files, and never records the key or
HTTP authorization headers. The OpenAI API has separate billing from ChatGPT.

## 4. Run eight calls to check the connection and answer formatting

The commands are single lines to avoid accidental whitespace after shell line
continuations. `caffeinate` is optional and is available on macOS.

```bash
caffeinate -i python3 -m exception_pilot run --config configs/stage1.json --output runs/reference-001 --max-calls 8
```

On Linux, remove `caffeinate -i`.

Expected final status: `call_limit`, with eight valid answers. Look at the saved
attempt files to confirm that both direct and reasoned responses have a final
A/B answer. Eight calls are a technical check, not evidence for the hypothesis.
These calls remain part of the same planned dataset; do not change the prompts
after viewing them and then resume that run.

## 5. Finish the same stage-1 run

```bash
caffeinate -i python3 -m exception_pilot run --config configs/stage1.json --output runs/reference-001 --max-calls 1200 --resume
```

This skips the eight completed calls and makes at most 1,192 additional calls
when there have been no errors. `--max-calls` is a cap on **new attempts in this
invocation**, including failed requests; it is not a cumulative ceiling. There
are no automatic retries and no automatic transition into stage 2.

Press Ctrl-C once to stop. Completed attempts are preserved. A call interrupted
in flight may already have been billed; it is marked unresolved rather than
silently repeated. Never start two processes with the same output directory.

## 6. Read the results

```bash
python3 -m exception_pilot analyze --output runs/reference-001
```

Open `runs/reference-001/summary.md`. The primary result compares exception
accuracy during passes 2–3, after every vehicle has received feedback. The
summary includes ordinary-item accuracy, per-pass denominators and a paired
bootstrap interval over independent lists. Twenty lists are the sample size;
the 1,200 calls are not independent observations.

The screen returns `eligible_for_diagnostics` only for a complete run with at
least 20 lists, zero invalid responses, an exception gap of at least 15 percentage
points (direct minus reasoned), and an ordinary-item gap no greater than 5 points.
This budget gate is not a statistical significance test. A negative or uncertain
screen does not prove that the phenomenon is absent.

If the result is `stop_this_screen`, pause the project on this model rather than
tuning prompts to force the result. `incomplete`, `insufficient_lists` and
`technical_failure` are not substantive null findings.

## 7. Conditional diagnostics

Only after stage 1 qualifies:

```bash
python3 -m exception_pilot prepare --config configs/stage2.json --output runs/diagnostic-001
caffeinate -i python3 -m exception_pilot run --config configs/stage2.json --output runs/diagnostic-001 --stage1-run runs/reference-001 --max-calls 320
```

Stage 2 uses 20 fresh matched world pairs, two targets per pair, two backgrounds
and four query conditions. Target labels stay fixed while the eight other labels
change. Each call starts from a fixed, independent evidence context. Results
include the extra conflict penalty under reasoning and the effect of repeating
the target record. These results do not by themselves establish that reasoning
mistakes exceptions for noise; that hypothesis requires a later experiment.

To resume stage 2, repeat its `run` command with `--resume` and the same parent.

## Errors and recovery

| Status | What to do |
|---|---|
| Missing credential / whitespace in key | Set `OPENAI_API_KEY` in the same terminal. The key is checked before recording an attempt. |
| HTTP 401 / 403 | Check API credentials, project permissions and model access. |
| HTTP 404 | Check availability of the pinned snapshot. Do not silently replace the model mid-run. |
| HTTP 429 | Check quota, billing or rate limits; wait or fix the issue before retrying. |
| Network/server error | Fix the connection or wait. No request is automatically retried. |
| `retry_requires_flag` | A failed or interrupted call exists. Retry explicitly using the command below. |
| `invalid_response` | Execution stops. Inspect the raw response and finish reason. Invalid answers are never counted as classification errors or resampled until one happens to parse. |
| Config/code/plan mismatch | Preserve the old run and use a new directory for a changed protocol. |

After resolving a provider error, for stage 1:

```bash
caffeinate -i python3 -m exception_pilot run --config configs/stage1.json --output runs/reference-001 --max-calls 1200 --resume --retry-errors
```

`--retry-errors` permits another attempt for transport errors or an unresolved
in-flight request. It never retries a returned invalid answer. If a formatting
or token-limit change is needed, retain the old run, update the protocol/config
and start a new run. Do not delete inconvenient responses. Snapshot mismatches,
refusals and truncation are also invalid responses.

## Files produced

| File | Contents |
|---|---|
| `plan.json` | Frozen config, generated data, task schedule and code/data hashes |
| `preview.json` | Reviewable example requests and separate ground truth |
| `execution.json` | Live/mock identity and stage-1 parent for diagnostics |
| `attempts/000001.json`, etc. | Exact request, timestamps, status, raw response, model identity and token usage |
| `scores.csv` | One row per planned prediction, including pending/invalid status |
| `summary.json` / `summary.md` | Technical accounting and clustered summaries |

The request is written atomically before sending it and updated atomically after
the response. Complete results are never overwritten during resume. Entire
histories are retained, including the model's earlier explanations, with no
context truncation or automatic summarization.

`runs/` and local credential/config files are ignored by Git. Keep the full run
directory for auditing. To share results for review, zip it:

```bash
zip -r reference-001.zip runs/reference-001
```

## Offline end-to-end demonstration

These commands intentionally simulate a large effect and a successful record
reminder. They test the software, **not the scientific hypothesis**.

```bash
python3 -m exception_pilot run --config configs/stage1.json --output runs/demo-stage1 --max-calls 1200 --mock
python3 -m exception_pilot run --config configs/stage2.json --output runs/demo-stage2 --stage1-run runs/demo-stage1 --max-calls 320 --mock
```

The output is prominently marked `SIMULATED`. A mock parent cannot authorize a
live stage-2 run, and a directory cannot switch between mock and live modes.

## Private GitHub repository

This source package can be uploaded as a new **private** repository named
`exception-pilot`. It is separate from `dependence-pilot` and the other pilots.
If GitHub CLI is installed and authenticated on your machine, from this directory:

```bash
git init -b main
git add .
git commit -m "Implement exception-learning pilot"
gh repo create exception-pilot --private --source=. --remote=origin --push
```

Use a fresh repository; do not overwrite an existing project with that name.
The source archive contains no API key, experimental results or Git credentials.

## References

- [Liu et al., Mind Your Step (by Step), ICML 2025](https://proceedings.mlr.press/v267/liu25t.html)
- [Final paper, especially Appendix C](https://arxiv.org/html/2410.21333v4)
- [Reference implementation](https://github.com/JiayiGeng/CoT_overthinking)
- [Official GPT-4o documentation](https://developers.openai.com/api/docs/models/gpt-4o)
- [Official Chat Completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

API documentation was checked on 2026-10-08. Availability for a specific account
is established by its actual request. A pinned name improves reproducibility but
does not guarantee unchanged service behavior across time.
