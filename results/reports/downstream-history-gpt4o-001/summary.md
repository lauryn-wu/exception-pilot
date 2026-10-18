# Downstream history control

Status: exploratory_complete_with_invalid.
Returned 216/216; valid 212; invalid retained 4; pending 0.

Counts below describe calls; the paired estimates weight worlds equally.

| Cohort | Arm | Correct / valid | False MISSING / valid | Invalid | Pending |
|---|---|---:|---:|---:|---:|
| contradiction | history_present | 16/39 | 23/39 | 0 | 0 |
| contradiction | history_absent | 31/38 | 7/38 | 1 | 0 |
| availability_control | history_present | 25/39 | 14/39 | 0 | 0 |
| availability_control | history_absent | 31/36 | 5/36 | 3 | 0 |
| genuine_missing_control | history_present | 27/27 | 0/27 | 0 | 0 |
| genuine_missing_control | history_absent | 0/27 | 0/27 | 0 | 0 |
| wrong_final_diagnostic | history_present | 0/3 | 3/3 | 0 | 0 |
| wrong_final_diagnostic | history_absent | 0/3 | 3/3 | 0 | 0 |

Primary: history-present minus history-absent false-MISSING rate in the contradiction cohort.
Paired complete worlds: 8/9.
World-weighted rates on those same worlds: history-present 0.5208333333333334; history-absent 0.125.
Difference: 0.3958333333333333; descriptive 95% world-bootstrap interval: [0.125, 0.7083333333333334]; full-plan difference bounds: [0.3888888888888889, 0.39814814814814814].

All secondary contrasts, arm rates, complete-world denominators and full-plan bounds are in summary.json and world-contrasts.csv. Responses are in responses.jsonl and responses.csv; paired responses are in paired-transitions.csv.

- Primary: false-MISSING rate with history minus without history in the frozen contradiction cohort.
- All other cohort and accuracy comparisons are secondary and unadjusted; cohorts are never pooled.
- Weights: mean repetitions within case, mean cases within world, then equal world weight. Calls and cases are not independent worlds.
- Arm rates and deltas use the same paired complete-world membership: every planned case and repetition in both arms must be valid.
- Invalid and absent responses are unknown, retained in full-plan worst-case bounds, and never silently scored incorrect.
- A truly MISSING cell has false-missingness bounded at zero even when its response is invalid; its accuracy remains unknown.
- The 95% bootstrap intervals resample worlds and are descriptive for these selected historical cases; they do not estimate semantic missingness prevalence or population effects.
- Three temperature-zero repetitions can expose endpoint variation but do not create independent cases or worlds.
- Both arms contain fresh follow-up calls. Historical follow-up answers are not imported into this comparison; source classification responses are frozen.
- History removal removes the classification question, its output instructions and assistant response, and changes conversation length and turn structure. The contrast concerns that entire history package, not the explanation alone.
- Similar observed arm rates or an interval containing zero do not establish equivalence or absence of a history effect; no equivalence margin is specified.
- A degenerate bootstrap interval, especially for a single-world diagnostic, does not show an exactly known population effect.
- Availability controls have reviewed absence of a false target-missingness claim, not certified factual reasoning throughout.
- Genuine-missing controls use a different historical feature-profile query and provide separate calibration, not a matched missingness counterfactual.
- No significance threshold, success gate, or outcome-dependent expansion is applied.
