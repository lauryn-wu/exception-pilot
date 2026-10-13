# Query form × response

**LIVE** — gpt-4o-2024-08-06

Returned 288/288; valid 288; retained invalid 0; attempts 288/316.
Decision: `stop_query_form`. Local decision: `stop_query_form`. This is a predeclared spending rule, not a mechanism or equivalence claim. No extension or outcome-selected worlds.

Record sensitivity averages +1 (target label), −1 (other target label), 0 (pattern) across variants, range [−1,1]. Intervals are descriptive 95% percentile intervals from 10,000 whole-world resamples, seed 981723. Sign tests test sign balance among nontied complete worlds. Unadjusted secondary tests are descriptive. Full-plan bounds vary every missing/invalid answer over A/B/C; they are not confidence intervals. Constant samples have degenerate bootstrap intervals and do not prove equivalence.

## accuracy

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| profile/direct | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| profile/visible | 0.583 | 0.438, 0.729 | 24 | 0.000 | 19 / 0 / 5 | 0.583, 0.583 |
| profile/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| key/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| key/visible | 0.521 | 0.354, 0.667 | 24 | 0.000 | 17 / 0 / 7 | 0.521, 0.521 |
| key/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| profile_direct_minus_visible | 0.396 | 0.250, 0.542 | 24 | 0.000 | 15 / 0 / 9 | 0.396, 0.396 |
| profile_direct_minus_filler | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| key_direct_minus_visible | 0.479 | 0.333, 0.646 | 24 | 0.000 | 16 / 0 / 8 | 0.479, 0.479 |
| key_direct_minus_filler | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| interaction | -0.083 | -0.271, 0.104 | 24 | 0.607 | 6 / 9 / 9 | -0.083, -0.083 |
## record_sensitivity

| Estimand | Mean | 95% interval | Complete worlds | Sign p | + / − / ties | Full-plan bounds |
|---|---:|---|---:|---:|---|---|
| profile/direct | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| profile/visible | 0.562 | 0.396, 0.708 | 24 | 0.000 | 18 / 0 / 6 | 0.562, 0.562 |
| profile/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| key/direct | 1.000 | 1.000, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 1.000, 1.000 |
| key/visible | 0.479 | 0.312, 0.646 | 24 | 0.000 | 15 / 0 / 9 | 0.479, 0.479 |
| key/filler | 0.979 | 0.938, 1.000 | 24 | 0.000 | 24 / 0 / 0 | 0.979, 0.979 |
| profile_direct_minus_visible | 0.417 | 0.271, 0.562 | 24 | 0.000 | 15 / 0 / 9 | 0.417, 0.417 |
| profile_direct_minus_filler | 0.000 | 0.000, 0.000 | 24 | 1.000 | 0 / 0 / 24 | 0.000, 0.000 |
| key_direct_minus_visible | 0.521 | 0.354, 0.688 | 24 | 0.000 | 16 / 0 / 8 | 0.521, 0.521 |
| key_direct_minus_filler | 0.021 | 0.000, 0.062 | 24 | 1.000 | 1 / 0 / 23 | 0.021, 0.021 |
| interaction | -0.104 | -0.312, 0.104 | 24 | 0.607 | 6 / 9 / 9 | -0.104, -0.104 |

## Predictions alongside estimates

| Prediction | Predeclared statement | Estimate |
|---|---|---|
| P1 | Profile direct minus visible record sensitivity >= 0.30. | 0.417 |
| P2 | Key direct minus visible record sensitivity <= 0.10. | 0.521 |
| P3 | Record-sensitivity interaction >= 0.20 with exact two-sided sign-test p < 0.05. | -0.104; p=0.607 |
| P4 | Direct minus filler record sensitivity <= 0.10 in each query form. | profile=0.000; key=0.021 |
| P5 | Among wrong visible responses, never_stated plus relabeled_missing >= 75%; provisional automated text coding only, not a gate. | 0.884 (automated; not a gate) |
| P6 | Mistral has the same positive interaction sign and interaction >= 0.20. | -0.104 for this model; compare both live summaries |

## Output controls

| Cell | Pattern | Invalid | Unreturned | Contract met / 48 | Exact filler fraction | Median pre-answer words | Median completion tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| profile/direct | 1 | 0 | 0 | 48 | — | 0.000 | 3.000 |
| profile/visible | 19 | 0 | 0 | 48 | — | 316.500 | 503.500 |
| profile/filler | 1 | 0 | 0 | 48 | 1.000 | 320.000 | 371.000 |
| key/direct | 0 | 0 | 0 | 48 | — | 0.000 | 3.000 |
| key/visible | 21 | 0 | 0 | 48 | — | 307.500 | 508.500 |
| key/filler | 1 | 0 | 0 | 48 | 1.000 | 320.000 | 371.000 |

The filler is same-response neutral copying, not a pure token/computation control. Input length, instructions and generated content differ. Noncompliance remains data. Visible pretext need not be faithful reasoning; length is observed, not conditioned on.

## Provisional rationale coding

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| query-form-gpt4o-001 | key/visible | correct | never_stated | 18 | 72.0% |
| query-form-gpt4o-001 | key/visible | correct | relabeled_missing | 5 | 20.0% |
| query-form-gpt4o-001 | key/visible | correct | stated_then_overridden | 0 | 0.0% |
| query-form-gpt4o-001 | key/visible | correct | stated_and_followed | 2 | 8.0% |
| query-form-gpt4o-001 | key/visible | wrong | never_stated | 9 | 39.1% |
| query-form-gpt4o-001 | key/visible | wrong | relabeled_missing | 10 | 43.5% |
| query-form-gpt4o-001 | key/visible | wrong | stated_then_overridden | 4 | 17.4% |
| query-form-gpt4o-001 | key/visible | wrong | stated_and_followed | 0 | 0.0% |
| query-form-gpt4o-001 | profile/visible | correct | never_stated | 14 | 50.0% |
| query-form-gpt4o-001 | profile/visible | correct | relabeled_missing | 2 | 7.1% |
| query-form-gpt4o-001 | profile/visible | correct | stated_then_overridden | 0 | 0.0% |
| query-form-gpt4o-001 | profile/visible | correct | stated_and_followed | 12 | 42.9% |
| query-form-gpt4o-001 | profile/visible | wrong | never_stated | 12 | 60.0% |
| query-form-gpt4o-001 | profile/visible | wrong | relabeled_missing | 7 | 35.0% |
| query-form-gpt4o-001 | profile/visible | wrong | stated_then_overridden | 1 | 5.0% |
| query-form-gpt4o-001 | profile/visible | wrong | stated_and_followed | 0 | 0.0% |

See rationales/rationales.csv for legacy flags and evidence excerpts. Coding is a text audit and has not been validated by independent blinded human annotators.
