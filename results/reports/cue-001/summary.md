# Reasoning cue and written-output diagnostic

Status: **complete_ready_for_interpretation**

144/144 returned; 144 parseable final answers; 0 unscorable.

The fixed sample contains 24 fresh worlds. Partial results must not determine whether to extend collection. Parseable final answers remain in the analysis regardless of output compliance.

## Paired accuracy contrasts

The co-primary contrasts are direct minus cue and cue minus visible. Direct minus visible is the contemporaneous baseline replication. Positive values favor the first arm. Each world first averages its two target-cell variants, then each complete world receives equal weight.

| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |
|---|---:|---|---:|---:|
| direct_minus_cue | 0.312 | [0.167, 0.479] | 24/24 | 15 / 0 |
| cue_minus_visible | 0.208 | [0.062, 0.354] | 24/24 | 12 / 2 |
| direct_minus_visible | 0.521 | [0.375, 0.667] | 24/24 | 25 / 0 |

10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. The independent unit is the world, not an API call. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.

Each contrast excludes a world if any required answer is unscorable or pending. The JSON records exact excluded worlds and task IDs, all scorable paired-case counts, and full-plan bounds once every planned response has returned. Paired-case counts can include a scorable case from an otherwise incomplete world.

## Answer and output-compliance counts

| Arm | Parseable / planned | Correct | Accuracy among parseable | Pre-answer text / returned | Answer only / returned | Contract met / returned |
|---|---:|---:|---:|---:|---:|---:|
| direct | 48/48 | 48 | 1.000 | 0/48 | 48/48 | 48/48 |
| cue | 48/48 | 33 | 0.688 | 48/48 | 0/48 | 0/48 |
| visible | 48/48 | 23 | 0.479 | 48/48 | 0/48 | 48/48 |

Pre-answer text records the presence of text, not whether that text is a meaningful or faithful explanation. Missing/unknown compliance flags are counted separately in the JSON. If cue outputs contain pre-answer text, their errors cannot demonstrate harm in the absence of generated explanation. If visible outputs omit text, the intended output manipulation was not fully followed. No format-based exclusion or retry is applied.

## Secondary record sensitivity

| Effect | Mean | Descriptive 95% interval | Complete worlds |
|---|---:|---|---:|
| direct_minus_cue | 0.312 | [0.167, 0.479] | 24/24 |
| cue_minus_visible | 0.229 | [0.083, 0.375] | 24/24 |
| direct_minus_visible | 0.542 | [0.375, 0.708] | 24/24 |
| direct | 1.000 | [1.000, 1.000] | 24/24 |
| cue | 0.688 | [0.521, 0.833] | 24/24 |
| visible | 0.458 | [0.292, 0.625] | 24/24 |

For each world, each correctly followed target label contributes +0.5, the other target label −0.5, and the background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. An unchanged answer across the two target-cell values scores 0. Changed answers alone do not establish record retrieval: the edit also changes table-level label counts, and each cell has one sampled completion.

This fixed diagnostic compares prompt instructions and output requirements. The cue arm does not establish that hidden reasoning occurred; pre-answer text is not evidence of faithful internal reasoning. A cue-versus-visible difference does not uniquely identify self-conditioning. If contemporaneous direct-versus-visible harm is not reproduced, this run cannot locate the source of the earlier harm. No automatic scientific pass gate or sample extension is applied.
