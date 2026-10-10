# Record-status wording intervention

Protocol: `verified-facts-mistral-record-framing-v1`.

## Question and scope

Does describing a correctly copied record as something still to confirm or
predict cause the model to abandon that record while completing an explanation?

This is a new experiment, designed after inspecting the exploratory mapping
results. It uses fresh generated worlds and researcher-supplied early prefixes.
The supplied prefix is not a saved internal state or a fresh model-generated
explanation. The `original` arm contains wording observed in an earlier trace;
its name does not mean that the whole prefix was naturally generated here.

The mapping did not identify a consistent harmful target-class-line effect.
This experiment tests one candidate explanation suggested by qualitative
examples. It does not assume that the candidate is correct or explains all
failures. Existing runs and frozen packages are unchanged.

## Exact manipulation

For each case, preserve the table, original visible-reasoning question, target
attributes, correct copied class, and all preceding assistant text. Change only
the parenthetical after the copied class. For a case whose recorded class is B:

| Arm | Final supplied line |
|---|---|
| `original` — observed prediction wording | `- Verified class: B (This is the value we are trying to confirm or predict.)` |
| `paraphrase` — second prediction wording | `- Verified class: B (This is the value we are trying to verify or infer.)` |
| `recorded` — explicitly recorded fact | `- Verified class: B (This is the value already recorded for this vehicle.)` |
| `bare` — factual statement alone | `- Verified class: B` |

Every prefix ends with the same two newline characters. No comparison with another vehicle,
conclusion, or final answer is supplied afterward. The API receives the prefix
as an assistant message with `prefix: true`; the model generates all subsequent
text. No corrective user message is appended. The known class remains identical
in all four arms within a case. The two record variants change the target cell
and the corresponding copied class together.

`preview.md` shows each complete user prompt and each complete assistant prefix.
`preview.json` records every exact request, including repeated draws. This is
the authoritative inspection surface for the full template, spacing, and cuts.

## Fixed collection

- Model: `mistral-small-2603`, visible output, `reasoning_effort: none`.
- Temperature 0.6 and top_p 0.95 for all research arms; no model RNG seed is
  claimed. The fixed design seed controls world generation and request order.
- 24 new worlds, with balanced A/B/C role assignments and target climates.
- Two conflicting recorded-class variants per world: 48 cases.
- One direct and one naturally generated visible explanation per case:
  96 baseline calls. These receive no assistant prefix.
- Four wording arms, three independent API draws per case and arm:
  576 intervention calls, or 144 draws per arm.
- One exact prefix-capability call: **673 planned calls total**, capped at
  **705 total attempts**, including transport retries.
- Each research request has a 1,600-token ceiling, with at least ten seconds
  between request starts. This is API compute, not a local GPU workload.

The baseline stage stops after 97 returned responses, including the capability
probe. The intervention stage requires an explicit command. There is no
baseline accuracy threshold, and no worlds are selected, dropped, replaced, or
extended based on observed answers. An invalid answer format is retained as
unscorable and does not remove its world from future collection.

Intervention arms are shuffled within paired case/repetition blocks, with block
order randomized across repeat rounds. Requests do not share a conversation or
API random seed. The repeats estimate continuation variability; they are not
additional independent worlds.

## Analysis specified before these results

**Primary:** accuracy in `bare` minus accuracy in `original`. A positive value
means adding the observed parenthetical reduced accuracy under this supplied
prefix. This contrast distinguishes damage from the suspect wording from the
possibility that an explicit record reminder merely helps.

Secondary contrasts, all reported separately:

- `bare - paraphrase`: a second wording with similar meaning.
- `recorded - original` and `recorded - paraphrase`: repair comparisons.
- `recorded - bare`: benefit of explicitly emphasizing the record.
- `original - paraphrase`: sensitivity to the particular wording.
- Baseline `direct - visible`: whether spontaneous explanation-associated
  errors occur on these fresh worlds under these settings.

Report accuracy, competing-pattern choices, other labels, and unscorable
responses. Average repeated draws within each variant and then average the two
variants within each world. Give each complete world equal weight. Uncertainty
uses 10,000 whole-world bootstrap resamples with seed 981723 and descriptive,
unadjusted 95% percentile intervals. Twenty-four worlds, not 576 calls, are the
independent sampling units. This sample size is a pilot budget, not a power
guarantee for a prespecified small effect.

Each contrast excludes a world if any required response is unscorable or
pending; exclusions are disclosed. Once all required responses have returned,
also report full-plan worst/best-case point-estimate bounds for unscorable
answers. These bounds are not confidence intervals. Bootstrap intervals are
withheld until the contrast's collection is complete. Partial summaries are
for monitoring collection, not deciding when to stop for significance.

All planned outcomes are retained; no significance gate, resampling until
correct, or outcome-dependent extension is implemented. A narrow or degenerate
interval does not establish certainty or equivalence. Secondary contrasts are
not multiplicity-adjusted confirmatory tests.

## What would establish a cause of the natural failures?

This experiment can establish a causal effect of the supplied wording on
continuation distributions. A result in which both prediction wordings hurt
relative to the bare line, and recorded-fact wording reduces those errors,
would support the candidate explanation. A benefit only from `recorded` would
instead show that a record reminder helps; it would not show that the observed
parenthetical caused the original failures.

Deletion also changes text length and the distance from the copied answer.
The four arms help distinguish explanations but do not perfectly isolate
semantics. Stronger follow-up would use additional matched-length neutral
wordings and more than one common prefix template.

To connect a positive result to naturally occurring failures, a separate
follow-up would:

1. Collect fresh natural explanations and identify candidate statements using
   a fixed content rule without examining final-answer correctness. Include
   eligible correct and incorrect traces, and report how often they occur.
2. At the actual statement, compare the untouched prefix with a minimal neutral
   or recorded-status edit and a meaning-preserving control. Keep all upstream
   text fixed and regenerate every continuation.
3. Test the reverse intervention: insert candidate prediction framing into
   otherwise neutral natural prefixes and measure whether errors increase.
4. Check whether removed prediction framing reappears in the generated suffix;
   a null deletion effect alone does not establish that the idea is irrelevant.
5. Replicate the locked comparisons on held-out worlds. Report both effect size
   and the prevalence of eligible traces; an effect on rare traces cannot
   explain most observed failures.

Those tests would support a causal contribution of this explanation content.
They would not establish a unique cause, strict necessity or sufficiency, or a
particular neural mechanism. The current baseline traces are exported for
inspection; any rule developed from them remains exploratory and requires
fresh confirmation. No natural-trace edits or later experiments run automatically.

Methodological references:

- [Lanham et al., Measuring Faithfulness in Chain-of-Thought Reasoning](https://arxiv.org/abs/2307.13702): intervene on intermediate text and examine newly generated continuations; written explanations are not automatically faithful accounts of internal computation.
- [Macar et al., Thought Branches](https://arxiv.org/html/2510.27484v2): compare distributions of continuations, consider whether edited text fits its context, and account for removed ideas reappearing downstream.

## Terminal instructions

From the existing repository, with `MISTRAL_API_KEY` already exported:

```bash
git pull --ff-only
python3 -m exception_mistral_framing prepare --config configs/mistral_framing.json --output runs/mistral-framing-001
open runs/mistral-framing-001/preview.md
```

Preparation is offline. Start the capability probe and fresh baselines:

```bash
caffeinate -i python3 -m exception_mistral_framing run --config configs/mistral_framing.json --output runs/mistral-framing-001 --stage baseline --max-calls 97
```

After baseline collection finishes, run the fixed intervention stage:

```bash
caffeinate -i python3 -m exception_mistral_framing run --config configs/mistral_framing.json --output runs/mistral-framing-001 --stage intervene --max-calls 576 --resume
```

If an invocation stops on a transport error, use the same stage and output
directory and add `--resume --retry-errors`. For example:

```bash
caffeinate -i python3 -m exception_mistral_framing run --config configs/mistral_framing.json --output runs/mistral-framing-001 --stage intervene --max-calls 576 --resume --retry-errors
```

The command resumes unfinished tasks; it does not repeat returned answers or
reset the cumulative attempt cap. A prefix mismatch, failed capability probe,
model change, incomplete provider response, or duplicate response ID stops the
run and must be inspected. Such responses are not silently retried.

```bash
python3 -m exception_mistral_framing analyze --output runs/mistral-framing-001
open runs/mistral-framing-001/report.md
```

Mock mode is an offline software fixture, prominently labeled simulated. It
does not predict a scientific effect and cannot be mixed with live results.
Run mocks in a separate output directory. All exact requests, raw responses,
execution settings, and scoring are journaled and checked on resume. Do not
edit an existing plan, config, or frozen source after starting a run.
