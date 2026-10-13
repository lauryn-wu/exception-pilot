# Query form × response

**LIVE** — mistral-small-2603

Returned 288/288; valid 288; retained invalid 0; attempts 288/316.
Decision: `output_manipulation_inconclusive`. Local decision: `output_manipulation_inconclusive`. This is a predeclared spending rule, not a mechanism or equivalence claim. No extension or outcome-selected worlds.

Record sensitivity averages +1 (target label), −1 (other target label), 0 (pattern) across variants, range [−1,1]. Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples, seed 981723. Sign tests test sign balance among nontied complete worlds. Unadjusted secondary tests are descriptive. Full-plan bounds vary every missing/invalid answer over A/B/C; they are not confidence intervals. Constant samples have degenerate bootstrap intervals and do not prove equivalence.

## accuracy

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| profile/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| profile/visible | 0.417 | 0.250, 0.583 | 24 | 0.000 | 14 / 0 / 10 | 0.417, 0.417 |
| profile/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| key/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| key/visible | 0.688 | 0.521, 0.833 | 24 | 0.000 | 19 / 0 / 5 | 0.688, 0.688 |
| key/filler | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| profile_direct_minus_visible | 0.583 | 0.417, 0.750 | 24 | 0.000 | 18 / 0 / 6 | 0.583, 0.583 |
| profile_direct_minus_filler | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| key_direct_minus_visible | 0.312 | 0.167, 0.479 | 24 | 0.002 | 10 / 0 / 14 | 0.312, 0.312 |
| key_direct_minus_filler | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| interaction | 0.271 | 0.062, 0.479 | 24 | 0.143 | 12 / 5 / 7 | 0.271, 0.271 |
## record_sensitivity

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| profile/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| profile/visible | 0.375 | 0.208, 0.542 | 24 | 0.000 | 12 / 0 / 12 | 0.375, 0.375 |
| profile/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| key/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| key/visible | 0.667 | 0.479, 0.833 | 24 | 0.000 | 18 / 0 / 6 | 0.667, 0.667 |
| key/filler | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| profile_direct_minus_visible | 0.625 | 0.458, 0.792 | 24 | 0.000 | 18 / 0 / 6 | 0.625, 0.625 |
| profile_direct_minus_filler | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| key_direct_minus_visible | 0.333 | 0.167, 0.521 | 24 | 0.002 | 10 / 0 / 14 | 0.333, 0.333 |
| key_direct_minus_filler | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| interaction | 0.292 | 0.062, 0.521 | 24 | 0.077 | 12 / 4 / 8 | 0.292, 0.292 |

## Predictions alongside estimates

| Prediction | Predeclared statement | Estimate |
|---|---|---|
| P1 | Profile direct minus visible record sensitivity >= 0.30. | 0.625 |
| P2 | Key direct minus visible record sensitivity <= 0.10. | 0.333 |
| P3 | Record-sensitivity interaction >= 0.20 with exact two-sided sign-test p < 0.05. | 0.292; p=0.077 |
| P4 | Direct minus filler record sensitivity <= 0.10 in each query form. | profile=0.021; key=0.000 |
| P5 | Among wrong visible responses, never_stated plus relabeled_missing >= 75%; provisional automated text coding only, not a gate. | 0.907 (automated; not a gate) |
| P6 | Mistral has the same positive interaction sign and interaction >= 0.20. | 0.292 for this model; compare both live summaries |

## Output controls

| Cell | Pattern | Invalid | Unreturned | Contract met / 48 | Exact filler fraction | Median pre-answer words | Median completion tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| profile/direct | 0 | 0 | 0 | 48 | — | 0.000 | 6.000 |
| profile/visible | 26 | 0 | 0 | 48 | — | 241.500 | 416.500 |
| profile/filler | 1 | 0 | 0 | 36 | 0.750 | 320.000 | 377.000 |
| key/direct | 0 | 0 | 0 | 48 | — | 0.000 | 6.000 |
| key/visible | 14 | 0 | 0 | 48 | — | 182.000 | 300.000 |
| key/filler | 0 | 0 | 0 | 24 | 0.500 | 321.000 | 382.000 |

The filler is same-response neutral copying, not a pure token/computation control. Input length, instructions and generated content differ. Noncompliance remains data. Visible pretext need not be faithful reasoning; length is observed, not conditioned on.

## Provisional rationale coding

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| query-form-mistral-001 | key/visible | correct | never_stated | 4 | 12.1% |
| query-form-mistral-001 | key/visible | correct | relabeled_missing | 1 | 3.0% |
| query-form-mistral-001 | key/visible | correct | stated_then_overridden | 0 | 0.0% |
| query-form-mistral-001 | key/visible | correct | stated_and_followed | 28 | 84.8% |
| query-form-mistral-001 | key/visible | wrong | never_stated | 0 | 0.0% |
| query-form-mistral-001 | key/visible | wrong | relabeled_missing | 15 | 100.0% |
| query-form-mistral-001 | key/visible | wrong | stated_then_overridden | 0 | 0.0% |
| query-form-mistral-001 | key/visible | wrong | stated_and_followed | 0 | 0.0% |
| query-form-mistral-001 | profile/visible | correct | never_stated | 3 | 15.0% |
| query-form-mistral-001 | profile/visible | correct | relabeled_missing | 4 | 20.0% |
| query-form-mistral-001 | profile/visible | correct | stated_then_overridden | 0 | 0.0% |
| query-form-mistral-001 | profile/visible | correct | stated_and_followed | 13 | 65.0% |
| query-form-mistral-001 | profile/visible | wrong | never_stated | 9 | 32.1% |
| query-form-mistral-001 | profile/visible | wrong | relabeled_missing | 15 | 53.6% |
| query-form-mistral-001 | profile/visible | wrong | stated_then_overridden | 4 | 14.3% |
| query-form-mistral-001 | profile/visible | wrong | stated_and_followed | 0 | 0.0% |

See rationales/rationales.csv for legacy flags and evidence excerpts. Coding is a text audit and has not been validated by independent blinded human annotators.
