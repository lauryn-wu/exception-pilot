# Exception pilot

## Current follow-up: 384-call explanatory diagnostic

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
