# Mistral native-prefix feasibility bridge

Status: **capability_failed_stop**

1/73 maximum planned calls returned; 0 valid; 1 invalid. The 24 replays are conditional on passing the capability and base feasibility checks.

All thresholds are fixed practical feasibility rules, not significance thresholds or evidence of a mechanism. Passing permits design review only; no intervention or stage 2 starts automatically. A native-prefix replay is a new generation conditioned on saved text, not restoration of the original hidden state. A versioned model ID does not guarantee an immutable backend implementation.

## Fixed feasibility checks

| Check | Status | Fixed practical requirement |
|---|---|---|
| Native-prefix capability | fail | Exact fixed synthetic full completion, including the supplied prefix |
| Base phenomenon | incomplete | All 48 valid; direct at least 20/24 correct; direct minus visible at least 4 correct answers; at least 4 visible pattern errors across at least 3 worlds |
| Unchanged prefix replay | not eligible: earlier check failed | All 24 valid; at least 22 exact parent-answer matches; at least ceiling(0.8 × original visible pattern errors) reproduced |

## Base collection and format checks

| Arm | Correct / valid / planned | Pattern choices | Format valid / returned | Pre-answer text / returned |
|---|---:|---:|---:|---:|
| direct | 0/0/24 | 0 | 0/0 | 0/0 |
| visible | 0/0/24 | 0 | 0/0 | 0/0 |

**The fixed native-prefix contract check failed.** The exact required full completion was not confirmed, so collection stops. This does not show that the provider can never support continuation.

## Replay collection

0/24 returned; 0 valid. All visible cases were prespecified for replay, including originally correct answers.

Mistral returns the full completion including the supplied prefix. The returned prefix must match exactly; the full returned text is scored without adding that prefix again. Only after exact prefix validation is the prefix removed once to obtain the suffix for the secondary exact-suffix comparison.

Exact returned prefixes: 0/0; mismatches: 0; unknown/unvalidated: 0.

The earlier fixed check failed, so replay is not eligible. The unrun conditional calls are a protocol stop, not additional missing observations to collect.

## Model and estimated cost

Provider documentation recorded with this plan: **Mistral Small 4**, as of **2026-10-09**. 
Requested versioned model ID: `mistral-small-2603`. This versioned ID does not guarantee an immutable backend. Requested reasoning effort: `none`; this does not establish an absence of internal computation.

Observed returned model strings: {'mistral-small-2603': 1}. Observed fingerprints: none reported. Per-attempt provider and local timestamps are saved in summary.json.

Reported-token estimate at the recorded rates: **$0.0000**. 6 attempts have unknown reported usage.

Rates used: $0.15 per million input tokens and $0.60 per million output tokens. Estimated from reported token usage at the recorded published input and output rates. This is not a guaranteed bill, cost cap, or promise of a free quota. Unreported usage, including timed-out requests, can be billable. Account-specific charges or discounts can differ, and rates can change.

Base contrasts use 10,000 whole-world bootstrap resamples, seed 981723, and descriptive unadjusted 95% intervals. There are 12 world-level units, not 73 independent observations. These reuse the prespecified worlds from the DeepSeek feasibility design; a provider change does not add independent task worlds. Degenerate intervals do not establish certainty or equivalence. Full-base unscorable bounds are point-estimate bounds, not confidence intervals. Replay agreement on the original pattern-error subset is a conditional diagnostic, not an estimate of error prevalence.
