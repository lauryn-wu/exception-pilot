# Exploratory continuation mapping

Protocol: `verified-facts-mistral-continuation-map-v1`.

## Question and scope

Where in a saved explanation does retaining additional text change the chance
of using the accurate target record versus the competing background pattern?
This first study maps continuations. It supplies no corrected reasoning,
fabricated conclusion, additional user instruction, or answer reminder.

The source is the completed `mistral-prefix-v2-001` run. That run remains
`replay_failed_stop`: 21/24 replay answers matched their parents (required 22),
and 7/9 pattern errors repeated (required 8). All 24 prefixes were preserved.
This new protocol was designed after seeing those results. It estimates new
continuation distributions and does not require matching one historical answer.
It neither overrides the old gate nor establishes independent confirmation.

All 24 visible parents from the 12 reused worlds are included: 15 originally
correct and 9 incorrect. No parent is selected or discarded according to a new
continuation, new baseline answer, replay agreement, or desired effect. New
baseline explanations do not replace the saved parents.

## Model and separate sampling check

Use `mistral-small-2603`, `reasoning_effort: none`, temperature **0.6**,
`top_p: 0.95`. The original V2 run used temperature zero. A fixed versioned ID
does not guarantee an immutable backend. Raw responses, model identifiers,
response IDs, usage, and any system fingerprint are saved. The requested model
must match, and returned IDs must be unique within the new run.

Before mapping, collect one exact prefix-contract probe and 48 new base
responses: direct and visible reasoning for both target variants in each world.
Prompts and 1,600-token limits remain the original ones. The probe has 32 tokens
and uses the original word-boundary prefix `Cobalt `, with the exact required
full response `Cobalt Maple Lantern`. All use the new sampling settings.

The check uses the previous practical thresholds: all base responses valid,
direct correct at least 20/24, direct minus visible correct at least 4/24,
at least four visible pattern errors spread across at least three worlds.
These are spending/feasibility rules, not significance tests. A failure stops
this map; it does not erase the temperature-zero result. Returned answers may
not be replaced to make the check pass.

The default `--stage check` stops after these 49 responses even if the invocation
budget is much larger. Starting mapping requires an explicit `--stage map`
invocation after a pass. This is a new experiment on previously examined worlds.

## Frozen checkpoint rule

Preparation audits and copies the parent plan, execution metadata, and attempt
journals into `source-parent/`. It reads the original directory without changing
it. The copied source, code, config, checkpoint offsets, schedule, and exact
requests are hashed. Resume and analysis revalidate them.

For every saved visible trace:

1. Include the empty prefix (the original visible user prompt alone).
2. Include boundaries before numbered reasoning steps.
3. Stop at the first numbered conclusion/summary, a standalone concluding
   introduction (`Therefore`, `Thus`, `Hence`, `Given that`, or `Given the
   verified class`), or the final `ANSWER:` line, whichever the rule finds first.
   Include the boundary just before that text, but not the concluding block.
4. Add cuts before and after the first explicit target-class line, if found
   before the stop. A bare verified-class field is eligible only in the opening
   target block before other vehicle IDs occur. A target-linked class statement
   can also be identified later. Other vehicles' class lines are excluded.
5. Merge identical cut offsets. End cuts at complete line/whitespace boundaries.

This is a reproducible syntactic rule, not a semantic claim that every numbered
block is one thought. For the uploaded source it produces **171 checkpoints**
across all 24 traces. There are target-class-line pairs in 23 traces; the other
trace remains in the overall map. Some lines combine a correct class with a
missingness claim or include multiple vehicle attributes. Their full text is
shown, so their contrasts must not be called pure availability interventions.
Prefixes can already contain class labels or answer-like statements in earlier
reasoning. Those are retained, rather than manually removed based on outcomes.

`preview.md` displays each original user prompt and every newly retained block.
`preview.json` records every exact request. At a nonempty checkpoint, send the
unchanged original user message followed by the exact retained assistant text
with `prefix: true`. Generate all later reasoning and the final answer anew.
Never append the old suffix or a new user message. Check the exact returned
prefix, then parse the full completion once. This conditions a new generation
on text; it does not restore the original hidden state.

## Budget and sampling

Six stochastic continuations per checkpoint give a **coarse exploratory map**:
171 × 6 = **1,026 mapping calls**, plus 49 check calls = **1,075 planned calls**.
The cumulative maximum is **1,107 attempts**, allowing at most 32 additional
transport attempts for this source. There is also a mandatory per-invocation
`--max-calls` cap. No seed is sent to the model; seed 2026100943 controls only the
schedule. Each of six rounds includes every checkpoint, shuffled within round.

Six draws do not give precise probabilities for a single checkpoint. Their
purpose is to locate candidate changes across traces within a limited budget.
Do not label the largest observed drop significant or confirmed. More precise
follow-up and fresh-world confirmation need a separately frozen protocol.

Requests run sequentially, with ten seconds between start times.
Mapping therefore has a pacing floor of roughly 171 minutes; response latency,
interruptions, and provider limits can make it longer. This spacing is not a
guarantee against account rate limits. A 429 or timeout stops without hidden
retries. Returned invalid answers are never retried. Only transport errors or
unresolved requests may be retried with `--retry-errors`, counting every attempt.
Usage is reported; no dollar price or billing cap is promised. Timed-out calls
may still be billable.

## Scoring and interpretation

- Report A/B/C counts, correctness, pattern-following, invalid, and pending
  outcomes at every checkpoint. Retain all returned responses.
- A mapping answer-format failure is unscorable and retained; collection can
  continue. A prefix mismatch, model drift, missing/duplicate response ID,
  unexpected reasoning content, or incomplete provider response stops collection.
- Report adjacent checkpoint changes only when both cells have all six valid
  draws. These differences concern the entire intervening text block, including
  its length, wording, and any repeated answer. They do not isolate semantics.
- For the target-record-line contrast, compute after minus before accuracy
  within a case, average eligible cases within each world, then weight complete
  worlds equally. Exclude a world if any eligible pair is incomplete/unscorable,
  and explicitly report those exclusions. Show all lines and the two exploratory
  lexical subgroups with/without the word MISSING.
- World contrasts use 10,000 whole-world bootstrap draws, seed 981723, with
  descriptive unadjusted 95% intervals. No multiplicity correction or definitive
  per-checkpoint test is performed. There are 12 world-level units, not 1,026
  independent cases. Degenerate intervals do not establish certainty/equivalence.
- Full-plan bounds assign every pending/unscorable slot incorrect versus correct.
  These are point-estimate bounds, not confidence intervals. Valid-only rates are
  explicitly labeled, not silently treated as complete-data rates.
- The new suffix's MISSING-word flag is only a lexical screen. Manually inspect
  whether the model actually claims the target is missing, trusts the record,
  uses the pattern, or changes procedure. `continuations-to-code.csv` is a
  regenerated export; copy it to a different filename before adding annotations.

The report never automatically declares a mechanism, novelty, or a winning edit.
A candidate step would next need a matched content intervention/paraphrase
comparison, potentially testing both insertion and repair, and fresh-world
confirmation. No such study runs automatically after this map.

## Run on macOS

From the existing checkout, update without discarding local history:

```bash
git fetch origin
git merge --no-edit origin/main
```

Keep the completed source at `runs/mistral-prefix-v2-001`. Preparation is offline:

```bash
python3 -m exception_mistral_map prepare --config configs/mistral_map.json --source runs/mistral-prefix-v2-001 --output runs/mistral-map-001
open runs/mistral-map-001/preview.md
```

With `MISTRAL_API_KEY` exported in this terminal, run the 49-call check:

```bash
caffeinate -i python3 -m exception_mistral_map run --config configs/mistral_map.json --output runs/mistral-map-001 --max-calls 49
```

Only after `stopped: sampling_check_passed`, run six mapping calls and inspect:

```bash
caffeinate -i python3 -m exception_mistral_map run --config configs/mistral_map.json --output runs/mistral-map-001 --stage map --max-calls 6 --resume
open runs/mistral-map-001/summary.md
```

If these return normally, collect the remaining planned map (already returned
calls are skipped; the frozen cumulative cap still applies):

```bash
caffeinate -i python3 -m exception_mistral_map run --config configs/mistral_map.json --output runs/mistral-map-001 --stage map --max-calls 1107 --resume
python3 -m exception_mistral_map analyze --output runs/mistral-map-001
zip -r mistral-map-001.zip runs/mistral-map-001
```

After an interruption or transport error, resume the same directory and stage.
Add `--retry-errors` only when retrying a transport error/unresolved request.
For 429, wait for the account limit to reset before that retry. Preserve any
returned operational failure for inspection. Do not edit or delete the journal.

`--mock` makes no API calls and is labeled simulated. Use a separate output
directory; live and simulated runs cannot be mixed. Python 3.10+ and the standard
library suffice; no GPU or additional provider subscription is required.

## Method references

- Lanham et al. (2023), [Measuring Faithfulness in Chain-of-Thought Reasoning](https://arxiv.org/abs/2307.13702): intermediate edits and regenerated suffixes; paraphrase controls.
- Bigelow et al. (ICLR 2025), [Forking Paths in Neural Text Generation](https://arxiv.org/abs/2412.07961): distributions of outcomes from partial responses.
- Bogdan et al. (2025), [Thought Anchors](https://arxiv.org/abs/2506.19143): before/after sentence resampling; 100 rollouts for more precise single-position estimates, with fewer potentially sufficient for aggregate analyses.
- Macar et al. (2026 revision), [Thought Branches](https://arxiv.org/abs/2510.27484): naturally sampled alternatives, artificial-edit limitations, and downstream regeneration of removed ideas.
- [Mistral Chat API](https://docs.mistral.ai/api/endpoint/chat) and [prefix documentation](https://docs.mistral.ai/studio/conversations/chat-completion): native assistant prefixes and sampling parameters.

The particular six-draw budget, checkpoint rule, and check thresholds are our
exploratory design choices, not a validated recipe prescribed by these papers.
