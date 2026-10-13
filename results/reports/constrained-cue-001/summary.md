# Reasoning cue under a constrained answer-only interface

Status: **complete_ready_for_interpretation**

96/96 returned; 96 valid; 0 invalid; 0 pending.

This exploratory follow-up reuses the 24 earlier cue worlds, with two target-record variants and two arms per world. It is not a fresh-data replication. Partial outcomes must not determine whether to extend collection.

## Output compliance

Both arms require one JSON object containing only an answer field with A, B, or C. Any returned invalid output causes a technical/output-manipulation stop; it is retained and never resampled.

| Arm | Returned / planned | Valid | Schema valid / returned | Invalid | Pending |
|---|---:|---:|---:|---:|---:|
| direct | 48/48 | 48 | 48/48 | 0 | 0 |
| cue | 48/48 | 48 | 48/48 | 0 | 0 |

## Primary paired accuracy contrast

Positive direct minus cue favors direct. Each world first averages its two target-record variants; complete worlds then receive equal weight.

| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |
|---|---:|---|---:|---:|
| direct_minus_cue | 0.000 | [0.000, 0.000] | 24/24 | 0 / 0 |

## Answer counts

| Arm | Correct / valid | Accuracy | Pattern choices |
|---|---:|---:|---:|
| direct | 48/48 | 1.000 | 0 |
| cue | 48/48 | 1.000 | 0 |

## Secondary signed record sensitivity

| Effect | Mean | Descriptive 95% interval | Complete worlds |
|---|---:|---|---:|
| direct_minus_cue | 0.000 | [0.000, 0.000] | 24/24 |
| direct | 1.000 | [1.000, 1.000] | 24/24 |
| cue | 1.000 | [1.000, 1.000] | 24/24 |

Each followed target label contributes +0.5, the other target label −0.5, and the background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. An unchanged answer across target-record variants scores 0. This score is not accuracy.

## Target-record pairs

| Arm | Complete worlds | Both correct | Both wrong | Answer changed | Answer unchanged | Pattern both |
|---|---:|---:|---:|---:|---:|---:|
| direct | 24 | 24 | 0 | 24 | 0 | 0 |
| cue | 24 | 24 | 0 | 24 | 0 | 0 |

Changed answers alone do not establish record retrieval: editing the target also changes table-level label counts, and each cell has one sampled completion.

10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. The sampling unit is the world, not an API call. These reuse the earlier cue worlds, so this is an exploratory follow-up, not a fresh-data replication. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.

Each estimate excludes a world if any required answer is pending or invalid. The JSON records excluded worlds and task IDs, paired-case counts, and full-plan bounds once all planned responses return. An invalid answer cannot be assigned a class by extracting one from malformed text.

If every output complies, a positive direct-minus-cue effect under this constrained interface would show that a generated written explanation is not necessary for the instruction effect in this interface. A null or uncertain effect does not show that written reasoning caused the earlier harm: the constrained format can change strategy. Neither result identifies hidden reasoning, task selection, or a neural mechanism. Correct answers do not by themselves establish record retrieval. No scientific pass threshold, automatic sample extension, or comparison to an unconstrained visible-explanation arm is applied.
