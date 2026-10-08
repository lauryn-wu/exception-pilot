# Verified-facts counterfactual diagnostic v1

Protocol: `verified-facts-counterfactual-v1`.
Date: 2026-10-08. Status: implemented and tested offline; no live results from this study.

## Scope and relationship to the original run

This is a **separate exploratory experiment**, designed after inspecting the
original stage-1 result, which returned `stop_this_screen`. It does not change
that decision, meet the old gate retroactively, or authorize the old Stage 2.
The original `exception_pilot` source, both stage configs, and `PROTOCOL.md`
remain unchanged. Use the new `exception_counterfactual` command and a new output
directory. No original run directory is an input to this diagnostic.

Question: does changing the labels of other vehicles make a model misclassify a
target whose own verified label is unchanged, and is that conflict penalty
greater under explicit reasoning than direct answers?

This is a behavioral intervention on prompt content and response instructions.
It is not an intervention on all internal computation and cannot establish an
internal belief, deliberate rejection of a known fact, or an exception-as-noise
mechanism. No claim of novelty is established by this protocol.

## Matched worlds

Generate 20 fresh independent lists, using seed `2026100816` and a new random
namespace. Each list contains five cold-climate and five warm-climate vehicles,
each with a unique plate, a descriptive climate cue, and three randomized
distractors. Plates start with V, disjoint from the original R/D item pools.
The prefix is constant and gives no class information. Descriptors are unique
within a list, so matching cannot be attributed uniquely to plate processing.

Randomly choose one target per climate before querying any model. Each list
defines two counterfactual versions:

1. **Conflict.** Four vehicles per climate have the majority class. The target
   has the opposite class. There are exactly two exceptions and five A/five B.
2. **Support.** Reverse the majority class within each climate, keep the target's
   own class fixed, and randomly choose a different vehicle in that climate to
   be the exception. There are again exactly two exceptions and five A/five B.

Consequently, exactly **six of the eight non-target labels change**. The two
target records, every attribute, the record order, the target positions, the
class balance and the full-table pattern strength are unchanged. In both
versions the majority climate rule describes exactly eight of ten records.
The versions are separate prompts, never contradictory evidence within one call.
Each queried target is exceptional in conflict and ordinary in support.

The 80% constraint applies to the full table. Within a target's climate group,
the other four records are unanimous in conflict and split 3:1 in support.
Thus this design does not hold leave-target-out consensus strength constant;
interpret it as a matched change in the surrounding labeled evidence.

The random distractors are not filtered based on incidental sample correlations.
The intervention changes the background labels, and hence may change their
realized correlations with those distractors too. This is not a selective
intervention on a single latent representation of climate.

## Prompts and schedule

Every call contains one user message: a short Markdown table of ten verified
records followed by a question about one of its two selected targets. The shared
introduction is:

> These are records of previously observed vehicles. Every record is accurate.
> An individual vehicle's class is fixed, and its license plate identifies it.

The target's true class is intentionally present in the record table. There is
no separate answer-key field in the API request. No prior assistant answer,
generated explanation, feedback history, or output from another condition is
included. The prompt never names the experimental condition, exception rate,
target status, or hypothesis.

Both conditions use the original classification question and uncertainty clause.
They differ only in the final output instruction and completion cap:

- **direct:** `Reply with only A or B.` Cap: 10 tokens.
- **cot:** `Work through the classification, then put A or B alone on the final line.`
  Cap: 1,000 tokens.

Use `gpt-4o-2024-08-06`, temperature 0, the same Chat Completions provider as the
reference run, and no tools or hidden conversation state. This is a test of
explicit reasoning prompts on that snapshot, not reasoning on/off in a model
with hidden reasoning. Do not silently switch snapshots if access fails.

Within each list, randomly interleave its eight target/background/instruction
cells. Every cell is stateless. There are **20 × 2 × 2 × 2 = 160 requests**.
All cells are planned before the first request; neither sample inclusion nor
stopping depends on observing a desired model response.

## Estimand, uncertainty and investment rule

For each independent list, average accuracy over its two targets within each
response/background cell. Define:

`direct conflict penalty = direct_support - direct_conflict`

`CoT conflict penalty = cot_support - cot_conflict`

**Primary contrast:**

`extra conflict penalty = (cot_support - cot_conflict) - (direct_support - direct_conflict)`

Average this contrast across the 20 lists. Report a descriptive percentile
bootstrap interval from 10,000 resamples of whole list pairs (fixed analysis
seed), all four cell accuracies, both simple conflict penalties, the list-level
effects, and their positive/zero/negative counts. The effective independent
sample size is 20 lists, not 160 calls or 40 independent targets.

Also report correct-to-wrong and wrong-to-correct target pairs across supporting
versus conflicting backgrounds. These are counterfactual comparisons, not
chronological revisions. Partial analyses use complete lists for paired effects;
separate valid-only tables disclose all cell denominators. Missing or invalid
responses are never scored as incorrect answers.

The exploratory investment screen is fixed before new data collection:

- All planned predictions must be valid and complete, with at least 20 lists.
- The mean extra conflict penalty must be **at least 15 percentage points**.
- CoT must actually lose accuracy under conflict, and its conflict accuracy must
  be lower than direct conflict accuracy. These direction checks prevent a
  positive interaction caused only by a direct-answer benefit from being called
  CoT harm.

If these hold, return `review_for_confirmation`. Otherwise return
`stop_this_extension`, or `stop_direction_mismatch` if the numerical contrast
passes but the simple effects do not match. Technical failures and incomplete
runs have separate statuses. Mock runs always return `simulated_not_evidence`.

This is an investment rule, not a significance test or a power calculation.
Inspect the interval and distribution across lists before extending the study.
Passing may reflect a small number of affected lists and does not establish
replicability. No paid follow-up begins automatically. A stop decision does not
prove the absence of modest effects.

## Interpretation and next decision

- Near-perfect performance in both arms stops this extension even if the earlier
  multi-turn effect was large. Several features changed together from Stage 1
  (history, presentation and explicit task semantics), so this null does not
  identify which change removed that earlier effect.
- Similar conflict penalties in both arms do not support the proposed
  reasoning-specific effect.
- A qualifying extra CoT penalty warrants independent confirmation and a
  contemporary-model check. It does not yet demonstrate evidence discounting or
  a new paper contribution.
- A subsequent exception-versus-noise study would need to manipulate observation
  reliability with defensible reference answers. That study is not implemented
  or automatically authorized by this screen.

## Run and recovery

From the updated source folder, on macOS:

```bash
python3 -m unittest discover -s tests -v
python3 -m exception_counterfactual prepare --config configs/counterfactual.json --output runs/counterfactual-001
open runs/counterfactual-001/preview.md
```

These commands make zero API calls. The preview compares the actual first
matched list and shows an exact request. All eight first-list requests, plus
separate scoring metadata, are in `preview.json`.

If the API key is not already set in this Terminal, use macOS zsh:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Run eight calls to check access and formatting; these count toward the 160:

```bash
caffeinate -i python3 -m exception_counterfactual run --config configs/counterfactual.json --output runs/counterfactual-001 --max-calls 8
```

Then finish the frozen plan:

```bash
caffeinate -i python3 -m exception_counterfactual run --config configs/counterfactual.json --output runs/counterfactual-001 --max-calls 160 --resume
```

The cap is new attempts per invocation, including failed requests. Successful
tasks are skipped, so an error-free resume after eight uses 152 further calls.
On Linux omit `caffeinate -i`. No dependencies or GPU are needed; Python >=3.10.

After a resolved timeout/network/credential error, use the same resume command
with `--retry-errors`. Never retry an invalid returned answer: inspect the saved
response, preserve the run, and start a separately documented run if a fix is
needed. No automatic retry or best-of-N answer selection is performed.

```bash
python3 -m exception_counterfactual analyze --output runs/counterfactual-001
open runs/counterfactual-001/summary.md
zip -r counterfactual-001.zip runs/counterfactual-001
```

The plan, source fingerprint, request journal, raw responses and execution mode
are saved. Config/source changes block resume. Results and credentials are not
tracked in Git. Do not reuse `runs/reference-001`, and do not pass `--stage1-run`.
The new command cannot authorize or resume the original Stage 2.

For a software-only demonstration, run the same command with `--mock` and a
different directory such as `runs/counterfactual-demo`. Its deliberately
engineered positive fixture is prominently labeled simulated; it is not a
prediction about any model.

## Closest prior work

- [Mind Your Step, ICML 2025](https://proceedings.mlr.press/v267/liu25t.html):
  repeated exception learning and retrieval steering are prior work.
- [Contextual Drag, February 2026 preprint](https://arxiv.org/abs/2602.04288):
  incorrect previous solutions influence later reasoning despite error signals.
- [No Need for Explanations, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1686/):
  removing corrective rationales can improve learning from examples; those
  corrective rationales differ from the model's own earlier attempted answers.
- [Patterns Over Principles](https://arxiv.org/abs/2502.16169):
  robust rule induction under noisy observations is already studied.

The controlled question here is background-label dependence while a target's
authoritative record and overall exception rate are fixed. A positive result
would still need a precise novelty assessment against these and adjacent papers.
