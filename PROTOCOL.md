# Exception pilot v1 — frozen before live data collection

Status: implementation and offline checks only. No real model results.
Date: 2026-10-08. Reference model: `gpt-4o-2024-08-06`.

## Research question and scope

Does explicit reasoning interfere with learning stable item-specific exceptions?
If it does, can fixed-history interventions narrow the explanation to evidence
access, task interpretation or reliance on the surrounding pattern?

The proposed longer-term explanation is that reasoning discounts some true
exceptions as if they were noisy observations. Neither stage here tests that
full explanation. Neither successful recall nor a persuasive rationale proves
that a fact was represented and actively rejected in the classification call.

## Prior evidence and deviations

Liu et al. (ICML 2025), Appendix C, use repeated classification with feedback,
unique item identifiers and mostly predictive features with exceptions. They
report slower learning under chain-of-thought prompting. Their appendix also
shows that explicit item-matching instructions can resolve the gap. These
findings and that remedy are prior work, not proposed novel contributions.

Our implementation is independent and uses newly generated stimuli following
that task structure. It has 20 lists, exactly three passes, no early stopping
when a list is perfect, newly worded climate descriptors and prompts, balanced
labels, one exception per climate, randomized climate-to-class mapping, and a
standard final-line A/B format. It fixes a dated model snapshot. These are
declared differences; numerical equality with the publication is not expected.
Failure of this abbreviated adaptation is not a refutation of the full study.

## Stage 1: repeated learning

Generate 20 independent lists, each containing ten vehicles. Five have cold-climate
descriptions and five warm-climate descriptions. Each list independently assigns
A/B to the two groups, then flips one label in each group. Thus eight vehicles
follow the group pattern, two are exceptions, and the final classes are five A
and five B. Labels and attributes never change during that list's three passes.
Transmission, upholstery and door count are independently sampled distractors;
their realized sample correlations are not deliberately filtered.

Every vehicle has a unique six-character license plate. All stage-1 plates begin
with R and stage-2 plates with D; the remaining characters are random and contain
no list, category or item-index encoding. Uniqueness is checked across a stage.
The constant stage prefixes make the two item pools disjoint. Each vehicle's
description is fixed, so both the descriptor and the plate can identify a seen
item. This pilot cannot attribute recall uniquely to license-plate processing.

Conditions:

1. **direct:** answer A/B only, cap 10 completion tokens.
2. **cot:** explain the classification before a final A/B line, cap 1,000 tokens.

Temperature is zero. Both use the same model and endpoint, no system prompt,
tools, response schema, reasoning-effort parameter or hidden previous-response
state. The question and uncertainty instruction are shared. The conditions differ
in the final response instruction and completion cap. This contrast is an explicit
reasoning-prompt intervention; it is not a clean intervention on all internal
computation. An answer-only instruction would not disable a reasoning model's
hidden reasoning, which is why this version accepts only dated GPT-4o models.

For each list, create one shuffled item order per pass and reuse it in both
conditions. Interleave the two conditions, randomizing which is requested first
for each item. The next prompt includes feedback for the immediately preceding
answer. The entire earlier user/assistant exchange remains in context. Each
condition has a separate conversation history, reset at the beginning of every
list. No answer from one condition appears in the other condition's history.

Because each vehicle is seen once per pass, its own first feedback always
precedes its second-pass query. Never attach the current answer key before the
model's prediction. Stop after the fixed third pass, even if a list was already
perfect. There are 1,200 planned requests in total.

## Stage-1 estimand and screen

For each list and condition, average correctness over its two exception vehicles
in passes 2 and 3 (four observations). Subtract reasoned from direct accuracy
within that list, then average the 20 differences. Report a percentile bootstrap
interval from 10,000 resamples of whole lists. Report the corresponding ordinary
vehicle contrast and a per-pass table. The independent unit is the list, not a
response or repeated occurrence of a vehicle.

The experimental unit for prompting is the whole list conversation. Earlier
reasoning, earlier errors, and history lengths can differ between conditions.
The stage-1 difference therefore measures the total effect of this conversation
policy, not just reasoning at the final decision. Stage 2 changes that design.

Predeclared exploratory budget gate:

- All 1,200 tasks valid and complete, with at least 20 independent lists.
- Exception accuracy gap (direct minus cot) at least **0.15**.
- Ordinary-item accuracy gap (direct minus cot) no greater than **0.05**.

The five-point ordinary-item tolerance operationalizes "ordinary performance
reasonably preserved." These are practical screening choices, not power-derived
thresholds or a claim of statistical significance. The bootstrap interval is
reported regardless of whether the gate is met. Selection on this screen means
its estimated effect may be optimistic; it needs confirmation on fresh data.
Do not change the thresholds after viewing results. A smaller effect may exist
even when this screen stops. Partial runs have no final decision.

## Stage 2: fixed-history diagnostics

Generate 20 fresh base lists using a stage-specific random namespace. Each has
two target vehicles corresponding to its original exceptions. Construct a pair:

- **conflict:** the eight ordinary vehicle labels establish a pattern opposing
  each target's own verified label.
- **support:** flip only those eight labels. The two target records and all
  features stay fixed, the overall A/B counts stay balanced, and the background
  pattern now supports both targets.

This intentionally changes the population pattern from 80% to 100% consistent
with the corresponding grouping. It is not a manipulation of retrieval distance
or of the target label. It does not hold pattern strength constant.

Each query presents one fixed set of ten labeled records in a shared order. It
explicitly states that records are accurate and each vehicle's class is fixed.
No invented assistant predictions are inserted into this history. The four arms
are direct classification, reasoned classification, recall of the recorded target
label, and reasoned classification with a duplicate of the exact target record
immediately before the question. The repeat is presented as the same record,
not as independent corroborating evidence.

Every target/background/arm is a fresh independent API call. No answer feeds
another arm. The two targets and all eight cells share one independent list-pair
unit for uncertainty calculations: 20 × 2 × 2 × 4 = 320 planned requests.
The model, temperature and caps must match the eligible stage-1 parent. There is
no automatic paid stage-2 run; it requires a separate command.

For each pair, average over its two targets. The prespecified descriptive
contrasts are:

1. **Extra conflict penalty under reasoning:**
   (cot support accuracy − cot conflict accuracy) −
   (direct support accuracy − direct conflict accuracy).
2. **Record-repeat benefit in conflict:**
   cot-with-record conflict accuracy − cot conflict accuracy.

Report per-arm and per-background accuracies and bootstrap intervals over whole
pairs. These are diagnostic comparisons, not multiple opportunities to declare
a confirmatory significant result. No p-value-based best-arm selection is used.

## Interpretation and stopping

- A stage-1 gap warrants diagnostics, not a novelty claim.
- A record-repeat benefit is compatible with easier retrieval, added salience or
  clearer task interpretation. There is no length-matched sham-repeat arm in this
  small pilot, so it does not uniquely identify one mechanism.
- Accurate recall and inaccurate classification are measured in different calls.
  They show a task-dependent capability gap, not direct evidence of an internal
  belief being overridden.
- Stage 2 changes the history format and makes the task semantics explicit. If
  its conflict effect vanishes, that does not separately identify which change
  removed stage 1's failure. A later crossed design would be needed.
- Persistent conflict errors with an immediately supplied verified record would
  justify investigating evidence discounting, including matched noisy-observation
  worlds and unseen-item generalization. Those experiments are not implemented.
- Stop expanding this route on the screened model if both conditions are near
  perfect or the material exception-specific gap is absent. Do not search prompts
  until a failure appears. Incomplete or technically invalid runs are not nulls.
- Before a paper claim, reproduce on a current model and confirm on independent
  lists with a sample-size decision informed by this pilot. A reference-model-only
  replication and an already known retrieval reminder are insufficient novelty.

## Parsing, missingness, retry policy and reproducibility

Require a terminal A/B line, allowing simple quotation/Markdown decoration and
an explicit "Answer:" prefix. Never scan the rationale for the last occurrence
of A or B. A non-stop finish reason, refusal, tool call, unexpected model snapshot
or unparseable terminal answer is invalid even if an A/B token appears elsewhere.

The run stops on an invalid returned answer. It is recorded as missing, never as
a model classification error, and never automatically resampled. The primary
paired summary uses only fully completed lists and discloses the count; the gate
is disabled unless the whole planned run is valid. Preserve an invalid run when
fixing a technical problem; use a new output directory for protocol changes.

Transport errors and in-flight interruptions can be retried only with an explicit
flag. Every attempt counts against the invocation's call cap and retains its
request/status. Interrupted requests may be billed despite no saved response.
The first completed returned response is used; there is no best-of-N selection.

Each run stores its config, source fingerprint, full generated data, schedule,
requests, raw responses, returned model name and usage. Changes to config, plan,
code or mock/live mode block resume. Files are written atomically and a process
lock prevents concurrent writers. Credentials are environment-only. Temperature
zero does not guarantee bit-for-bit service determinism.

## Sources

Liu et al. (2025), [ICML proceedings](https://proceedings.mlr.press/v267/liu25t.html),
[final paper Appendix C](https://arxiv.org/html/2410.21333v4),
[authors' code](https://github.com/JiayiGeng/CoT_overthinking).
The exception/noise mechanism remains a hypothesis, and the novelty review is
provisional. This pilot is deliberately smaller than the full research agenda.
