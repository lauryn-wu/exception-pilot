# Downstream history by prediction-rule control

Status: exploratory_complete_with_invalid.
Returned 432/432; valid 414; invalid retained 18; pending 0.

Counts below describe calls; the paired estimates weight worlds equally.

| Cohort | Arm | Correct / valid | False MISSING / valid | Invalid | Pending |
|---|---|---:|---:|---:|---:|
| contradiction | history_present_rule_present | 14/39 | 25/39 | 0 | 0 |
| contradiction | history_absent_rule_present | 31/39 | 8/39 | 0 | 0 |
| contradiction | history_present_rule_absent | 5/39 | 34/39 | 0 | 0 |
| contradiction | history_absent_rule_absent | 39/39 | 0/39 | 0 | 0 |
| availability_control | history_present_rule_present | 24/39 | 15/39 | 0 | 0 |
| availability_control | history_absent_rule_present | 30/36 | 6/36 | 3 | 0 |
| availability_control | history_present_rule_absent | 27/37 | 10/37 | 2 | 0 |
| availability_control | history_absent_rule_absent | 31/35 | 4/35 | 4 | 0 |
| genuine_missing_control | history_present_rule_present | 27/27 | 0/27 | 0 | 0 |
| genuine_missing_control | history_absent_rule_present | 0/26 | 0/26 | 1 | 0 |
| genuine_missing_control | history_present_rule_absent | 25/25 | 0/25 | 2 | 0 |
| genuine_missing_control | history_absent_rule_absent | 0/22 | 0/22 | 5 | 0 |
| wrong_final_diagnostic | history_present_rule_present | 0/3 | 3/3 | 0 | 0 |
| wrong_final_diagnostic | history_absent_rule_present | 0/3 | 3/3 | 0 | 0 |
| wrong_final_diagnostic | history_present_rule_absent | 0/2 | 2/2 | 1 | 0 |
| wrong_final_diagnostic | history_absent_rule_absent | 2/3 | 1/3 | 0 | 0 |

Primary: rule-absent minus rule-present accuracy without history in the genuine-missing cohort.
Paired complete worlds: 6/9.
World-weighted rates on those same worlds: rule absent 0.0; rule present 0.0.
Difference: 0.0; descriptive 95% world-bootstrap interval: [0.0, 0.0]; full-plan difference bounds: [-0.037037037037037035, 0.18518518518518517].

All pairwise comparisons and four-arm interactions follow. Each row uses its own complete-world set.

| Cohort | Metric | Contrast | Complete / planned worlds | Difference | Descriptive 95% interval | Full-plan bounds |
|---|---|---|---:|---:|---|---|
| contradiction | false_missing | rule_effect_without_history | 9/9 | -0.15740740740740738 | [-0.3796296296296296, 0.0] | [-0.15740740740740738, -0.15740740740740738] |
| contradiction | false_missing | rule_effect_with_history | 9/9 | 0.3333333333333333 | [0.07407407407407408, 0.6296296296296297] | [0.3333333333333333, 0.3333333333333333] |
| contradiction | false_missing | history_effect_rule_present | 9/9 | 0.3796296296296296 | [0.12962962962962965, 0.6388888888888888] | [0.3796296296296296, 0.3796296296296296] |
| contradiction | false_missing | history_effect_rule_absent | 9/9 | 0.8703703703703703 | [0.6851851851851852, 1.0] | [0.8703703703703703, 0.8703703703703703] |
| contradiction | false_missing | history_by_rule_interaction | 9/9 | -0.49074074074074076 | [-0.7592592592592592, -0.2222222222222222] | [-0.49074074074074076, -0.49074074074074076] |
| contradiction | accuracy | rule_effect_without_history | 9/9 | 0.1574074074074074 | [0.0, 0.37962962962962965] | [0.1574074074074074, 0.1574074074074074] |
| contradiction | accuracy | rule_effect_with_history | 9/9 | -0.3333333333333333 | [-0.6296296296296297, -0.07407407407407408] | [-0.3333333333333333, -0.3333333333333333] |
| contradiction | accuracy | history_effect_rule_present | 9/9 | -0.3796296296296296 | [-0.6388888888888888, -0.12962962962962965] | [-0.3796296296296296, -0.3796296296296296] |
| contradiction | accuracy | history_effect_rule_absent | 9/9 | -0.8703703703703703 | [-1.0, -0.6851851851851852] | [-0.8703703703703703, -0.8703703703703703] |
| contradiction | accuracy | history_by_rule_interaction | 9/9 | 0.49074074074074076 | [0.2222222222222222, 0.7592592592592593] | [0.49074074074074076, 0.49074074074074076] |
| availability_control | false_missing | rule_effect_without_history | 7/9 | -0.14285714285714285 | [-0.42857142857142855, 0.0] | [-0.12962962962962965, 0.018518518518518514] |
| availability_control | false_missing | rule_effect_with_history | 8/9 | -0.1875 | [-0.4375, -0.020833333333333332] | [-0.16666666666666666, -0.0925925925925926] |
| availability_control | false_missing | history_effect_rule_present | 8/9 | 0.22916666666666666 | [-0.22916666666666666, 0.625] | [0.2037037037037037, 0.2314814814814815] |
| availability_control | false_missing | history_effect_rule_absent | 6/9 | 0.2222222222222222 | [0.0, 0.5555555555555556] | [0.0462962962962963, 0.24074074074074073] |
| availability_control | false_missing | history_by_rule_interaction | 6/9 | 0.25 | [0.027777777777777776, 0.5555555555555556] | [-0.03703703703703703, 0.18518518518518517] |
| availability_control | accuracy | rule_effect_without_history | 7/9 | 0.14285714285714285 | [0.0, 0.42857142857142855] | [-0.018518518518518514, 0.12962962962962962] |
| availability_control | accuracy | rule_effect_with_history | 8/9 | 0.1875 | [0.020833333333333343, 0.4375] | [0.09259259259259259, 0.16666666666666666] |
| availability_control | accuracy | history_effect_rule_present | 8/9 | -0.22916666666666669 | [-0.625, 0.22916666666666666] | [-0.2314814814814815, -0.20370370370370372] |
| availability_control | accuracy | history_effect_rule_absent | 6/9 | -0.22222222222222224 | [-0.5555555555555556, 0.0] | [-0.24074074074074078, -0.04629629629629631] |
| availability_control | accuracy | history_by_rule_interaction | 6/9 | -0.25 | [-0.5555555555555556, -0.02777777777777779] | [-0.1851851851851852, 0.037037037037037035] |
| genuine_missing_control | false_missing | rule_effect_without_history | 6/9 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| genuine_missing_control | false_missing | rule_effect_with_history | 8/9 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| genuine_missing_control | false_missing | history_effect_rule_present | 8/9 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| genuine_missing_control | false_missing | history_effect_rule_absent | 6/9 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| genuine_missing_control | false_missing | history_by_rule_interaction | 5/9 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| genuine_missing_control | accuracy | rule_effect_without_history | 6/9 | 0.0 | [0.0, 0.0] | [-0.037037037037037035, 0.18518518518518517] |
| genuine_missing_control | accuracy | rule_effect_with_history | 8/9 | 0.0 | [0.0, 0.0] | [-0.07407407407407408, 0.0] |
| genuine_missing_control | accuracy | history_effect_rule_present | 8/9 | 1.0 | [1.0, 1.0] | [0.9629629629629629, 1.0] |
| genuine_missing_control | accuracy | history_effect_rule_absent | 6/9 | 1.0 | [1.0, 1.0] | [0.7407407407407408, 1.0] |
| genuine_missing_control | accuracy | history_by_rule_interaction | 5/9 | 0.0 | [0.0, 0.0] | [-0.037037037037037035, 0.2592592592592593] |
| wrong_final_diagnostic | false_missing | rule_effect_without_history | 1/1 | -0.6666666666666667 | [-0.6666666666666667, -0.6666666666666667] | [-0.6666666666666667, -0.6666666666666667] |
| wrong_final_diagnostic | false_missing | rule_effect_with_history | 0/1 | None | None | [-0.33333333333333337, 0.0] |
| wrong_final_diagnostic | false_missing | history_effect_rule_present | 1/1 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| wrong_final_diagnostic | false_missing | history_effect_rule_absent | 0/1 | None | None | [0.3333333333333333, 0.6666666666666667] |
| wrong_final_diagnostic | false_missing | history_by_rule_interaction | 0/1 | None | None | [-0.6666666666666667, -0.3333333333333333] |
| wrong_final_diagnostic | accuracy | rule_effect_without_history | 1/1 | 0.6666666666666666 | [0.6666666666666666, 0.6666666666666666] | [0.6666666666666666, 0.6666666666666666] |
| wrong_final_diagnostic | accuracy | rule_effect_with_history | 0/1 | None | None | [0.0, 0.3333333333333333] |
| wrong_final_diagnostic | accuracy | history_effect_rule_present | 1/1 | 0.0 | [0.0, 0.0] | [0.0, 0.0] |
| wrong_final_diagnostic | accuracy | history_effect_rule_absent | 0/1 | None | None | [-0.6666666666666666, -0.3333333333333333] |
| wrong_final_diagnostic | accuracy | history_by_rule_interaction | 0/1 | None | None | [0.3333333333333333, 0.6666666666666666] |

Rule effects are rule absent minus rule present. History effects are history present minus history absent. The interaction is the history effect with the rule minus the history effect without it.

All arm rates, world memberships and bounds are in summary.json and world-contrasts.csv. Raw responses and factors are in responses.jsonl and responses.csv; the four paired response comparisons are in paired-transitions.csv.

- Primary: accuracy after prediction-rule removal minus accuracy with the rule retained, without history, in the frozen genuine-missing cohort.
- The primary outcome uses the literal table cell as the answer key: a genuinely MISSING cell is correct only when the factual answer is MISSING.
- All other cohort, metric and interaction comparisons are secondary and unadjusted; cohorts are never pooled.
- This control was designed after observing the earlier history-control results. It is a prospective follow-up on the same selected historical cases, not independent case replication.
- Weights: mean repetitions within case, mean cases within world, then equal world weight. Calls and cases are not independent worlds.
- Each pairwise estimate uses every planned case and repetition in both arms on its own complete-world set. Both reported arm rates use that exact same set.
- The interaction requires all four arms, cases and repetitions to be valid within a world. It bootstraps the actual four-arm world differences; it does not subtract pairwise confidence intervals or unmatched world estimates.
- Cell-level world-weighted rates use the common four-arm complete-world set. Raw cell counts use valid calls in that cell and may have different denominators.
- Invalid and absent responses are unknown, retained in sign-aware full-plan worst-case bounds, and never silently scored incorrect.
- A truly MISSING cell has false-missingness bounded at zero even when its response is invalid; its accuracy remains unknown.
- The 95% bootstrap intervals resample worlds and are descriptive for these selected historical cases. They do not estimate semantic missingness prevalence or population effects.
- Three temperature-zero repetitions can expose endpoint variation but do not create independent cases or worlds.
- All four arms contain fresh follow-up calls. Earlier follow-up outcomes are not imported; the saved original classification response is fixed and replayed unchanged wherever history is present.
- Rule removal deletes only the specified prediction sentence from the original user introduction. It does not regenerate or edit the saved assistant response, even if that response contains prediction language.
- The rule contrast therefore measures the effect of editing that user instruction conditional on the fixed historical response. It does not measure how the rule would change a newly generated classification response.
- History removal removes the classification question, output instructions and assistant response, and changes conversation length and turn structure. Its effect concerns the entire history package, not the explanation alone.
- The rule-absent introduction still defines MISSING, and the follow-up still offers MISSING as an answer. No condition is claimed to be a neutral retrieval baseline or a measure of latent belief.
- Similar observed rates or an interval containing zero do not establish equivalence or absence of an effect; no equivalence margin is specified.
- A degenerate bootstrap interval, especially for a single-world diagnostic, does not show an exactly known population effect.
- Availability controls have reviewed absence of a false target-missingness claim, not certified factual reasoning throughout.
- Genuine-missing controls use a different historical feature-profile query and provide separate calibration, not a matched missingness counterfactual.
- No significance threshold, scientific success gate, or outcome-dependent expansion is applied.
