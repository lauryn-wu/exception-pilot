# Target row position

**LIVE** — mistral-small-2603

Returned 288/288; valid 288; retained invalid 0; attempts 288/316.
Decision: `review_fresh_world_confirmation`. Observed direction: `last_more_harm`.

Primary: accuracy interaction (direct − visible at row 10) − (direct − visible at row 1). Positive values mean more reasoning harm at the last row. Each world averages both recorded-label variants; the endpoint interaction requires its eight endpoint responses, not the row-5 responses.

This reuses all 24 development worlds and tests a record-order intervention. It does not establish a retrieval mechanism, generality to fresh worlds, or equivalence. No decision automatically runs further calls. Deprioritizing is a spending decision, not proof of no position effect.

Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples (seed 981723). Sign tests describe sign balance among nonzero world contrasts, not mean magnitude, and never gate spending. Full-plan bounds hold valid answers fixed and range missing/invalid answers over all three labels; they are not confidence intervals. A degenerate bootstrap interval cannot calibrate precision: a large uniform development effect can prompt fresh-world review, but a zero or small degenerate effect cannot trigger deprioritization.

## Per-cell results

| Row / arm | Correct / valid / planned | Wrong: pattern / other | Invalid / unreturned | Manipulation adherence / planned | Median words / tokens |
|---|---:|---:|---:|---:|---:|
| 1/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 1/visible | 47 / 48 / 48 | 1 / 0 | 0 / 0 | 48 / 48 | 94.500 / 144.500 |
| 5/direct | 47 / 48 / 48 | 1 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 5/visible | 40 / 48 / 48 | 8 / 0 | 0 / 0 | 48 / 48 | 179.500 / 286.000 |
| 10/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 10/visible | 19 / 48 / 48 | 26 / 3 | 0 / 0 | 48 / 48 | 259.500 / 470.000 |

## accuracy

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| 1/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 1/visible | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| 5/direct | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| 5/visible | 0.833 | 0.729, 0.917 | 24 | 0.000 | 24 / 0 / 0 | 0.833, 0.833 |
| 10/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 10/visible | 0.396 | 0.250, 0.542 | 24 | 0.000 | 14 / 0 / 10 | 0.396, 0.396 |
| 1_direct_minus_visible | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| 5_direct_minus_visible | 0.146 | 0.062, 0.250 | 24 | 0.016 | 7 / 0 / 17 | 0.146, 0.146 |
| 10_direct_minus_visible | 0.604 | 0.458, 0.750 | 24 | 0.000 | 19 / 0 / 5 | 0.604, 0.604 |
| direct_last_minus_first | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| visible_last_minus_first | -0.583 | -0.729, -0.438 | 24 | 0.000 | 0 / 19 / 5 | -0.583, -0.583 |
| middle_harm_minus_endpoint_average | -0.167 | -0.281, -0.052 | 24 | 0.008 | 3 / 15 / 6 | -0.167, -0.167 |
| interaction | 0.583 | 0.438, 0.729 | 24 | 0.000 | 19 / 0 / 5 | 0.583, 0.583 |

## record_sensitivity

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| 1/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 1/visible | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| 5/direct | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| 5/visible | 0.833 | 0.729, 0.917 | 24 | 0.000 | 24 / 0 / 0 | 0.833, 0.833 |
| 10/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 10/visible | 0.333 | 0.146, 0.500 | 24 | 0.007 | 13 / 2 / 9 | 0.333, 0.333 |
| 1_direct_minus_visible | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| 5_direct_minus_visible | 0.146 | 0.062, 0.250 | 24 | 0.016 | 7 / 0 / 17 | 0.146, 0.146 |
| 10_direct_minus_visible | 0.667 | 0.500, 0.854 | 24 | 0.000 | 19 / 0 / 5 | 0.667, 0.667 |
| direct_last_minus_first | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| visible_last_minus_first | -0.646 | -0.812, -0.479 | 24 | 0.000 | 0 / 19 / 5 | -0.646, -0.646 |
| middle_harm_minus_endpoint_average | -0.198 | -0.323, -0.062 | 24 | 0.008 | 3 / 15 / 6 | -0.198, -0.198 |
| interaction | 0.646 | 0.479, 0.812 | 24 | 0.000 | 19 / 0 / 5 | 0.646, 0.646 |

Secondary record sensitivity averages +1 (correct target label), −1 (other target label), 0 (pattern label), over both variants. Its range is [−1, 1]; it does not enter the spending decision.

Controls count every planned response in their denominators: direct requires answer-only output; visible requires pre-answer text. Noncompliance is retained in all scorable-answer estimates. Written text need not reflect hidden computation. Missing answers remain unknown in paired estimates.
