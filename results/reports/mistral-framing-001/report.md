# Record-status framing intervention — exploratory

Status: **exploratory_intervention_complete**. SIMULATED: **False**.

673/673 returned; 673 valid; 0 unscorable. 24 independent worlds, with two target variants per world.

The intervention keeps the correct copied class fixed and changes only the parenthetical. The primary comparison is bare minus original accuracy. Positive values indicate lower accuracy with the original prediction wording.

## Collection and interpretation

Capability: pass. Baseline returned: 96/96. Intervention returned: 576/576.

Collection of the full baseline permits the intervention regardless of baseline accuracy; there is no behavioral pass gate.

Intervention interpretation permitted: **True**. Complete-baseline descriptive interpretation permitted: **True**.

## Arm counts

| Arm | Returned / planned | Valid | Correct | Pattern | Other | Invalid | Pending | Accuracy among valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 48/48 | 48 | 48 | 0 | 0 | 0 | 0 | 1.000 |
| visible | 48/48 | 48 | 25 | 20 | 3 | 0 | 0 | 0.521 |
| original | 144/144 | 144 | 104 | 36 | 4 | 0 | 0 | 0.722 |
| paraphrase | 144/144 | 144 | 100 | 41 | 3 | 0 | 0 | 0.694 |
| recorded | 144/144 | 144 | 141 | 3 | 0 | 0 | 0 | 0.979 |
| bare | 144/144 | 144 | 132 | 10 | 2 | 0 | 0 | 0.917 |

## Accuracy contrasts

Positive values mean a higher rate in the first arm. Average repeats within each variant, then the two variants within each world, then give each complete world equal weight.

| Contrast | World-weighted difference | Descriptive 95% interval | Complete / planned worlds | Full-plan unscorable bounds |
|---|---:|---|---:|---|
| bare_minus_original (primary) | 0.194 | [0.125, 0.264] | 24/24 | [0.194, 0.194] |
| bare_minus_paraphrase | 0.222 | [0.139, 0.312] | 24/24 | [0.222, 0.222] |
| recorded_minus_original | 0.257 | [0.194, 0.319] | 24/24 | [0.257, 0.257] |
| recorded_minus_paraphrase | 0.285 | [0.194, 0.382] | 24/24 | [0.285, 0.285] |
| recorded_minus_bare | 0.063 | [0.014, 0.111] | 24/24 | [0.063, 0.063] |
| original_minus_paraphrase | 0.028 | [-0.056, 0.111] | 24/24 | [0.028, 0.028] |
| direct_minus_visible | 0.479 | [0.333, 0.604] | 24/24 | [0.479, 0.479] |

## Pattern-choice contrasts (secondary)

Positive values mean a higher rate in the first arm. Average repeats within each variant, then the two variants within each world, then give each complete world equal weight.

| Contrast | World-weighted difference | Descriptive 95% interval | Complete / planned worlds | Full-plan unscorable bounds |
|---|---:|---|---:|---|
| bare_minus_original | -0.181 | [-0.250, -0.111] | 24/24 | [-0.181, -0.181] |
| bare_minus_paraphrase | -0.215 | [-0.306, -0.132] | 24/24 | [-0.215, -0.215] |
| recorded_minus_original | -0.229 | [-0.292, -0.167] | 24/24 | [-0.229, -0.229] |
| recorded_minus_paraphrase | -0.264 | [-0.368, -0.167] | 24/24 | [-0.264, -0.264] |
| recorded_minus_bare | -0.049 | [-0.090, -0.007] | 24/24 | [-0.049, -0.049] |
| original_minus_paraphrase | -0.035 | [-0.118, 0.042] | 24/24 | [-0.035, -0.035] |
| direct_minus_visible | -0.417 | [-0.562, -0.271] | 24/24 | [-0.417, -0.417] |

Intervals use 10,000 whole-world bootstrap resamples, seed 981723; unadjusted and descriptive. They are withheld until all planned responses in a contrast have returned and at least two complete worlds remain. Unscorable bounds are point-estimate bounds, not confidence intervals. Every excluded world, case and task is listed in summary.json.

## Interpretation limits

- The primary estimand is bare minus original accuracy. Prediction-wording arms are not pooled. All other contrasts and pattern-choice outcomes are descriptive secondary analyses.
- Fresh worlds use supplied early explanation prefixes. This tests the effect of the supplied wording, not whether the wording mediates the model's spontaneous failures or identifies an internal mechanism.
- The recorded-fact wording adds semantic guidance and the bare statement changes length. Paraphrase comparisons check wording sensitivity but cannot eliminate all lexical or length differences.
- Worlds are the independent units; repeated continuations and two target variants are nested observations. Intervals are unadjusted descriptive whole-world bootstrap intervals, not a significance or pass/fail gate.
- Incomplete estimates cannot support the intervention conclusion. Intervals are withheld until every planned response for that contrast has returned. A complete fresh baseline may be described separately while interventions remain incomplete.
- Returned invalid answers are retained without replacement. Complete-world comparisons exclude an entire world when a required answer is unscorable. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.
- Intervals require at least two complete worlds. Degenerate intervals do not establish certainty or equivalence; no threshold was set for proceeding based on baseline accuracy or intervention effect.
- Spontaneous visible explanations are exported without automatic interpretation or selection. Their prose is not a faithful readout of internal model state; subsequent annotations and natural-prefix interventions require a separate fixed protocol.

rows.json contains all planned task rows, including pending/invalid answers and exact generated text. spontaneous-visible-traces.md exports every baseline visible explanation without outcome selection. These files are regenerated; save human annotations under a different filename.
