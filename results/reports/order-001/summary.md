# Structured answer order: fresh-world diagnostic

Status: **complete_ready_for_interpretation**

72/72 returned; 72 valid; 0 invalid; 0 pending.

The fixed sample contains 12 fresh worlds, two target-record variants, and three arms per world. These worlds come from the same task family and model. Partial outcomes must not determine whether to extend collection.

## Output compliance

Answer-only requires one answer field. The other arms require answer and reasoning fields in the assigned order, with a nonempty reasoning string. Wrong schema, wrong key order, empty required reasoning, or another returned invalidity causes a technical/output-manipulation stop. The returned output is retained and never resampled. Only the first structured answer is scored; an answer mentioned later in reasoning cannot revise it.

| Arm | Returned / planned | Valid | Schema valid / returned | Key order valid / returned | Nonempty reasoning / required returned | Invalid |
|---|---:|---:|---:|---:|---:|---:|
| answer_only | 24/24 | 24 | 24/24 | 24/24 | not required | 0 |
| reasoning_first | 24/24 | 24 | 24/24 | 24/24 | 24/24 | 0 |
| answer_first | 24/24 | 24 | 24/24 | 24/24 | 24/24 | 0 |

Schema validity is structural and can be true even when the required key order or reasoning presence fails. Nonempty reasoning is an output check; it does not establish substantive reasoning or a faithful description of internal computation. Unknown checks are counted separately in the JSON.

## Descriptive reasoning lengths

| Arm | Measured returned outputs | Mean characters | Median characters | Mean whitespace-separated words |
|---|---:|---:|---:|---:|
| answer_only | 0 | — | — | — |
| reasoning_first | 24 | 1313.625 | 1312.000 | 210.958 |
| answer_first | 24 | 1185.792 | 1211.000 | 191.125 |

Lengths describe validated reasoning strings, including any present in outputs with another compliance failure. Answer-only has no reasoning field. Lengths are not evidence of reasoning quality, a causal mediator, or a reason to exclude or resample outputs.

## Paired accuracy contrasts

Answer-first minus reasoning-first is primary. The answer-only comparisons are secondary. Positive values favor the first arm. Each world first averages its two target-record variants; complete worlds then receive equal weight.

| Contrast | Role | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |
|---|---|---:|---|---:|---:|
| answer_first_minus_reasoning_first | primary | 0.375 | [0.167, 0.583] | 12/12 | 9 / 0 |
| answer_only_minus_answer_first | secondary | 0.000 | [0.000, 0.000] | 12/12 | 0 / 0 |
| answer_only_minus_reasoning_first | secondary | 0.375 | [0.167, 0.583] | 12/12 | 9 / 0 |

## Answer counts

| Arm | Correct / valid | Accuracy | Pattern choices |
|---|---:|---:|---:|
| answer_only | 24/24 | 1.000 | 0 |
| reasoning_first | 15/24 | 0.625 | 9 |
| answer_first | 24/24 | 1.000 | 0 |

## Secondary signed record sensitivity

| Effect | Mean | Descriptive 95% interval | Complete worlds |
|---|---:|---|---:|
| answer_first_minus_reasoning_first | 0.375 | [0.167, 0.583] | 12/12 |
| answer_only_minus_answer_first | 0.000 | [0.000, 0.000] | 12/12 |
| answer_only_minus_reasoning_first | 0.375 | [0.167, 0.583] | 12/12 |
| answer_only | 1.000 | [1.000, 1.000] | 12/12 |
| reasoning_first | 0.625 | [0.417, 0.833] | 12/12 |
| answer_first | 1.000 | [1.000, 1.000] | 12/12 |

Each followed target label contributes +0.5, the other target label −0.5, and the background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. An unchanged answer across target-record variants scores 0. This score is not accuracy.

## Target-record pairs

| Arm | Complete worlds | Both correct | Both wrong | Answer changed | Answer unchanged | Pattern both |
|---|---:|---:|---:|---:|---:|---:|
| answer_only | 12 | 12 | 0 | 12 | 0 | 0 |
| reasoning_first | 12 | 5 | 2 | 10 | 2 | 2 |
| answer_first | 12 | 12 | 0 | 12 | 0 | 0 |

Changed answers alone do not establish record retrieval: editing the target also changes table-level label counts, and each cell has one sampled completion.

If all outputs comply, lower answer-first accuracy than answer-only can show harm before a written explanation is generated, but the requested task and output schema also differ. Lower reasoning-first accuracy than answer-first supports an effect of generation order, potentially including early answer commitment, in this interface, not a unique effect of text self-conditioning or an identified internal mechanism. Reasoning-field nonemptiness does not establish substantive or faithful reasoning. The first structured answer is final; no later answer inside reasoning is scored as a revision. An accurate result in all arms of this small study does not establish equivalence. The changed structured interface does not directly explain earlier unconstrained results. No scientific pass threshold or outcome-dependent sample extension is applied.

10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. The sampling unit is the world, not an API call. There are 12 fresh worlds from the same task family and one model; this is not a cross-model replication. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.

Each estimate excludes a world if any required answer is pending or invalid. The JSON records excluded worlds and task IDs, paired-case counts for every contrast, and full-plan bounds once all planned responses return. An invalid answer cannot be assigned a class by extracting one from malformed or noncompliant text. Estimates are audit diagnostics only whenever interpretation_allowed is false. No automatic scientific pass gate or sample extension is applied.
