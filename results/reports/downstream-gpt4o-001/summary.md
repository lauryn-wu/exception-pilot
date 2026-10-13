# Downstream factual follow-up

Status: exploratory_complete.
Returned 342/342; valid 342; invalid retained 0.

| Cohort | Arm | Correct / valid | False MISSING | Invalid | Pending |
|---|---|---:|---:|---:|---:|
| contradiction | original | 15/39 | 24 | 0 | 0 |
| contradiction | availability_repair | 31/39 | 8 | 0 | 0 |
| contradiction | missing_synonym | 29/39 | 10 | 0 | 0 |
| contradiction | value_repair | 35/39 | 4 | 0 | 0 |
| contradiction | endpoints_only | 8/39 | 31 | 0 | 0 |
| availability_control | original | 23/39 | 16 | 0 | 0 |
| availability_control | endpoints_only | 23/39 | 16 | 0 | 0 |
| genuine_missing_control | original | 27/27 | 0 | 0 | 0 |
| genuine_missing_control | endpoints_only | 27/27 | 0 | 0 | 0 |
| wrong_final_diagnostic | original | 0/3 | 3 | 0 | 0 |
| wrong_final_diagnostic | availability_repair | 0/3 | 3 | 0 | 0 |
| wrong_final_diagnostic | missing_synonym | 0/3 | 3 | 0 | 0 |
| wrong_final_diagnostic | value_repair | 1/3 | 2 | 0 | 0 |
| wrong_final_diagnostic | endpoints_only | 2/3 | 1 | 0 | 0 |

Primary: original minus availability-repair false-MISSING rate.
Complete worlds: 9/9; estimate: 0.2685185185185185; descriptive 95% world-bootstrap interval: [0.07407407407407407, 0.48148148148148145]; full-plan bounds: [0.2685185185185185, 0.2685185185185185].

All paired comparisons, their own complete-world denominators and bounds are in summary.json. Raw answers are in responses.jsonl; transitions are in paired-transitions.csv.

- All comparisons except the named primary are secondary and unadjusted.
- Primary weights: average three repetitions within each case, then cases within each world, then equal weight each of nine worlds.
- Complete-world estimates require every planned case and repetition in both arms valid; other worlds remain in full-plan bounds.
- Bootstrap intervals describe selected observed worlds; nine worlds and outcome-selected historical traces do not establish population prevalence.
- A degenerate all-zero bootstrap interval is not evidence that the population effect is exactly zero.
- Availability controls have no reviewed false target-missingness claim; their other reasoning is not certified factual.
- Genuine-missing controls originate in a different feature-profile query and calibrate literal retrieval; do not pool cohorts.
- Temperature-zero repetitions measure possible endpoint variation and are not independent worlds.
- No significance threshold, success gate, or outcome-dependent expansion is applied.
