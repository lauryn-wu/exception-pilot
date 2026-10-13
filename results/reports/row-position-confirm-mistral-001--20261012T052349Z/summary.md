# Target row position: fresh-world confirmation

**LIVE** — mistral-small-2603

Returned 960/960; valid 960; retained invalid 0; attempts 961/1056.
Decision: `confirm_positive_interaction`. Observed direction: `last_more_harm`.

Primary: accuracy interaction (direct − visible at row 10) − (direct − visible at row 1). Positive values mean more reasoning harm at the last row. Each world averages both recorded-label variants; the endpoint interaction requires its eight endpoint responses, not the intermediate-row responses.

This confirmation uses 24 fresh worlds and all ten target positions. The single primary contrast was selected before this collection. It does not establish a retrieval mechanism, model-wide generality, or equivalence. No decision automatically runs further calls. smaller_than_target describes the frozen practical threshold, not proof of no position effect.

Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples (seed 981723). Sign tests describe sign balance among nonzero world contrasts, not mean magnitude, and never gate spending. Full-plan bounds hold valid answers fixed and range missing/invalid answers over all three labels; they are not confidence intervals. A degenerate bootstrap interval cannot calibrate precision: a large uniform observed effect can meet the directional decision rule, but the interval does not establish population precision. A zero or small degenerate effect cannot trigger smaller_than_target.

The row curve and all secondary intervals are pointwise and unadjusted; they do not identify an optimal row or support ten separate confirmatory tests. Prespecified shape contrasts are H2 − H1, H10 − H9, and (H5 + H6)/2 − (H1 + H10)/2, where Hr is direct-minus-visible accuracy.

![Descriptive valid-answer accuracy by row](row_curve.svg)

row_curve.csv retains valid and planned denominators, paired-world cell estimates, pointwise intervals and full-plan bounds; the plotted rates use valid answers only.

## Per-cell results

| Row / arm | Correct / valid / planned | Wrong: pattern / other | Invalid / unreturned | Manipulation adherence / planned | Median words / tokens |
|---|---:|---:|---:|---:|---:|
| 1/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 1/visible | 46 / 48 / 48 | 2 / 0 | 0 / 0 | 48 / 48 | 106.000 / 161.500 |
| 2/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 2/visible | 38 / 48 / 48 | 7 / 3 | 0 / 0 | 48 / 48 | 154.500 / 265.500 |
| 3/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 3/visible | 32 / 48 / 48 | 15 / 1 | 0 / 0 | 48 / 48 | 167.000 / 267.000 |
| 4/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 4/visible | 37 / 48 / 48 | 11 / 0 | 0 / 0 | 48 / 48 | 162.500 / 274.500 |
| 5/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 5/visible | 35 / 48 / 48 | 10 / 3 | 0 / 0 | 48 / 48 | 165.000 / 288.000 |
| 6/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 6/visible | 37 / 48 / 48 | 8 / 3 | 0 / 0 | 48 / 48 | 172.000 / 272.500 |
| 7/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 7/visible | 25 / 48 / 48 | 20 / 3 | 0 / 0 | 48 / 48 | 210.500 / 370.500 |
| 8/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 8/visible | 32 / 48 / 48 | 15 / 1 | 0 / 0 | 48 / 48 | 187.000 / 310.000 |
| 9/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 9/visible | 25 / 48 / 48 | 19 / 4 | 0 / 0 | 48 / 48 | 234.000 / 389.000 |
| 10/direct | 48 / 48 / 48 | 0 / 0 | 0 / 0 | 48 / 48 | 0.000 / 6.000 |
| 10/visible | 19 / 48 / 48 | 26 / 3 | 0 / 0 | 48 / 48 | 273.000 / 462.500 |

## accuracy

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| 1/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 1/visible | 0.958 | 0.896, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.958, 0.958 |
| 2/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 2/visible | 0.792 | 0.688, 0.896 | 24 | 0.000 | 24 / 0 / 0 | 0.792, 0.792 |
| 3/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 3/visible | 0.667 | 0.521, 0.792 | 24 | 0.000 | 21 / 0 / 3 | 0.667, 0.667 |
| 4/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 4/visible | 0.771 | 0.646, 0.875 | 24 | 0.000 | 23 / 0 / 1 | 0.771, 0.771 |
| 5/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 5/visible | 0.729 | 0.604, 0.854 | 24 | 0.000 | 22 / 0 / 2 | 0.729, 0.729 |
| 6/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 6/visible | 0.771 | 0.625, 0.896 | 24 | 0.000 | 21 / 0 / 3 | 0.771, 0.771 |
| 7/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 7/visible | 0.521 | 0.375, 0.667 | 24 | 0.000 | 18 / 0 / 6 | 0.521, 0.521 |
| 8/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 8/visible | 0.667 | 0.542, 0.792 | 24 | 0.000 | 22 / 0 / 2 | 0.667, 0.667 |
| 9/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 9/visible | 0.521 | 0.375, 0.667 | 24 | 0.000 | 18 / 0 / 6 | 0.521, 0.521 |
| 10/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 10/visible | 0.396 | 0.250, 0.542 | 24 | 0.000 | 15 / 0 / 9 | 0.396, 0.396 |
| 1_direct_minus_visible | 0.042 | 0.000, 0.104 | 24 | 0.500 | 2 / 0 / 22 | 0.042, 0.042 |
| 2_direct_minus_visible | 0.208 | 0.104, 0.312 | 24 | 0.002 | 10 / 0 / 14 | 0.208, 0.208 |
| 3_direct_minus_visible | 0.333 | 0.208, 0.479 | 24 | 0.000 | 13 / 0 / 11 | 0.333, 0.333 |
| 4_direct_minus_visible | 0.229 | 0.125, 0.354 | 24 | 0.002 | 10 / 0 / 14 | 0.229, 0.229 |
| 5_direct_minus_visible | 0.271 | 0.146, 0.396 | 24 | 0.001 | 11 / 0 / 13 | 0.271, 0.271 |
| 6_direct_minus_visible | 0.229 | 0.104, 0.375 | 24 | 0.008 | 8 / 0 / 16 | 0.229, 0.229 |
| 7_direct_minus_visible | 0.479 | 0.333, 0.625 | 24 | 0.000 | 17 / 0 / 7 | 0.479, 0.479 |
| 8_direct_minus_visible | 0.333 | 0.208, 0.458 | 24 | 0.000 | 14 / 0 / 10 | 0.333, 0.333 |
| 9_direct_minus_visible | 0.479 | 0.333, 0.625 | 24 | 0.000 | 17 / 0 / 7 | 0.479, 0.479 |
| 10_direct_minus_visible | 0.604 | 0.458, 0.750 | 24 | 0.000 | 20 / 0 / 4 | 0.604, 0.604 |
| direct_last_minus_first | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| visible_last_minus_first | -0.562 | -0.708, -0.396 | 24 | 0.000 | 1 / 20 / 3 | -0.562, -0.562 |
| first_boundary_harm_2_minus_1 | 0.167 | 0.083, 0.271 | 24 | 0.008 | 8 / 0 / 16 | 0.167, 0.167 |
| last_boundary_harm_10_minus_9 | 0.125 | -0.083, 0.333 | 24 | 0.629 | 10 / 7 / 7 | 0.125, 0.125 |
| middle_harm_minus_endpoint_average | -0.073 | -0.167, 0.021 | 24 | 0.332 | 6 / 11 / 7 | -0.073, -0.073 |
| interaction | 0.562 | 0.396, 0.708 | 24 | 0.000 | 20 / 1 / 3 | 0.562, 0.562 |

## record_sensitivity

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| 1/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 1/visible | 0.958 | 0.896, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.958, 0.958 |
| 2/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 2/visible | 0.729 | 0.583, 0.854 | 24 | 0.000 | 21 / 0 / 3 | 0.729, 0.729 |
| 3/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 3/visible | 0.646 | 0.500, 0.792 | 24 | 0.000 | 20 / 0 / 4 | 0.646, 0.646 |
| 4/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 4/visible | 0.771 | 0.646, 0.875 | 24 | 0.000 | 23 / 0 / 1 | 0.771, 0.771 |
| 5/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 5/visible | 0.667 | 0.500, 0.812 | 24 | 0.000 | 19 / 0 / 5 | 0.667, 0.667 |
| 6/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 6/visible | 0.708 | 0.521, 0.875 | 24 | 0.000 | 18 / 0 / 6 | 0.708, 0.708 |
| 7/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 7/visible | 0.458 | 0.292, 0.625 | 24 | 0.000 | 16 / 1 / 7 | 0.458, 0.458 |
| 8/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 8/visible | 0.646 | 0.500, 0.792 | 24 | 0.000 | 22 / 1 / 1 | 0.646, 0.646 |
| 9/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 9/visible | 0.438 | 0.270, 0.604 | 24 | 0.001 | 15 / 1 / 8 | 0.438, 0.438 |
| 10/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| 10/visible | 0.333 | 0.188, 0.500 | 24 | 0.002 | 13 / 1 / 10 | 0.333, 0.333 |
| 1_direct_minus_visible | 0.042 | 0.000, 0.104 | 24 | 0.500 | 2 / 0 / 22 | 0.042, 0.042 |
| 2_direct_minus_visible | 0.271 | 0.146, 0.417 | 24 | 0.002 | 10 / 0 / 14 | 0.271, 0.271 |
| 3_direct_minus_visible | 0.354 | 0.208, 0.500 | 24 | 0.000 | 13 / 0 / 11 | 0.354, 0.354 |
| 4_direct_minus_visible | 0.229 | 0.125, 0.354 | 24 | 0.002 | 10 / 0 / 14 | 0.229, 0.229 |
| 5_direct_minus_visible | 0.333 | 0.188, 0.500 | 24 | 0.001 | 11 / 0 / 13 | 0.333, 0.333 |
| 6_direct_minus_visible | 0.292 | 0.125, 0.479 | 24 | 0.008 | 8 / 0 / 16 | 0.292, 0.292 |
| 7_direct_minus_visible | 0.542 | 0.375, 0.708 | 24 | 0.000 | 17 / 0 / 7 | 0.542, 0.542 |
| 8_direct_minus_visible | 0.354 | 0.208, 0.500 | 24 | 0.000 | 14 / 0 / 10 | 0.354, 0.354 |
| 9_direct_minus_visible | 0.562 | 0.396, 0.730 | 24 | 0.000 | 17 / 0 / 7 | 0.562, 0.562 |
| 10_direct_minus_visible | 0.667 | 0.500, 0.812 | 24 | 0.000 | 20 / 0 / 4 | 0.667, 0.667 |
| direct_last_minus_first | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| visible_last_minus_first | -0.625 | -0.792, -0.438 | 24 | 0.000 | 1 / 20 / 3 | -0.625, -0.625 |
| first_boundary_harm_2_minus_1 | 0.229 | 0.104, 0.375 | 24 | 0.008 | 8 / 0 / 16 | 0.229, 0.229 |
| last_boundary_harm_10_minus_9 | 0.104 | -0.146, 0.333 | 24 | 0.503 | 12 / 8 / 4 | 0.104, 0.104 |
| middle_harm_minus_endpoint_average | -0.042 | -0.167, 0.083 | 24 | 0.629 | 7 / 10 / 7 | -0.042, -0.042 |
| interaction | 0.625 | 0.438, 0.792 | 24 | 0.000 | 20 / 1 / 3 | 0.625, 0.625 |

Secondary record sensitivity averages +1 (correct target label), −1 (other target label), 0 (pattern label), over both variants. Its range is [−1, 1]; it does not enter the primary scientific decision.

Controls count every planned response in their denominators: direct requires answer-only output; visible requires pre-answer text. Noncompliance is retained in all scorable-answer estimates. Written text need not reflect hidden computation. Missing answers remain unknown in paired estimates.
