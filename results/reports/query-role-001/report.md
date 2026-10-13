# Query-conditioned fact use: fixed first-stage screen

Status: **screen_complete**. Screen: **stop_this_screen**.

144/144 returned; 144 scorable; 0 retained invalid; 0 pending. 12 independent worlds; 144 attempts.

## Prespecified outcome

For counterfactual records a and b, score the decoded answer -1 for source a, +1 for source b, and 0 for the third value. R = (score_b - score_a) / 2. The primary interaction D = (R_downstream,visible - R_encoded,visible) - (R_downstream,direct - R_encoded,direct). Encoded harm = R_encoded,direct - R_encoded,visible. Positive D alone does not establish encoded deterioration.

## Response counts

| Query | Instruction | Returned / planned | Valid | Correct | Pattern | Other | Accuracy among valid | Direct format adherent / assessed |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| literal | direct | 24/24 | 24 | 24 | 0 | 0 | 1.000 | 24/24 |
| literal | visible | 24/24 | 24 | 24 | 0 | 0 | 1.000 | — |
| encoded | direct | 24/24 | 24 | 24 | 0 | 0 | 1.000 | 24/24 |
| encoded | visible | 24/24 | 24 | 24 | 0 | 0 | 1.000 | — |
| downstream | direct | 24/24 | 24 | 24 | 0 | 0 | 1.000 | 24/24 |
| downstream | visible | 24/24 | 24 | 24 | 0 | 0 | 1.000 | — |

Direct-instruction adherence is a separate descriptive format check, not a spending criterion; unassessed responses are excluded from its denominator.

## World-level outcomes

| Metric | Complete worlds / planned | Mean | Descriptive 95% interval | Fixed-plan bounds | Eligible vehicle / configuration |
|---|---:|---:|---|---|---:|
| literal_direct_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| literal_visible_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| encoded_direct_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| encoded_visible_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| downstream_direct_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| downstream_visible_R | 12/12 | 1.000 | [1.000, 1.000] | [1.000, 1.000] | 6 / 6 |
| literal_harm | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |
| encoded_harm | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |
| downstream_harm | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |
| primary_D | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |
| visible_role_gap | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |
| direct_role_gap | 12/12 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | 6 / 6 |

Unadjusted percentile bootstrap of whole eligible worlds, stratified by family; each family's eligible-world count is preserved.

Equal weight per complete world for each reported metric. Missingness can change eligible-family proportions; counts are reported. Fixed-plan bounds instead weight every planned world equally.

Descriptive intervals, not gate criteria or confidence intervals for missingness bounds. No interval before collection completes; at least two eligible worlds in every planned family are required. Degenerate intervals do not establish certainty or equivalence.

Bounds include pending and invalid answers and are extrema of the fixed-plan point estimate, not confidence intervals.

## Practical spending criteria

The criteria are evaluated only after all planned answers return. Invalid answers count as incorrect in direct-mode accuracy. Effect criteria use the worst-case lower bound, including within-family criteria. No second-stage calls are run automatically.

| Criterion | Observed | Required | Passed |
|---|---:|---:|---|
| fixed_144_call_12_world_plan | 1.000 | >= 1.000 | yes |
| scorable_answers | 144.000 | >= 137.000 | yes |
| literal_direct_correct_invalid_as_incorrect | 24.000 | >= 22.000 | yes |
| encoded_direct_correct_invalid_as_incorrect | 24.000 | >= 22.000 | yes |
| downstream_direct_correct_invalid_as_incorrect | 24.000 | >= 22.000 | yes |
| encoded_harm_worst_case_lower_bound | 0.000 | >= 0.150 | no |
| downstream_visible_R_worst_case_lower_bound | 1.000 | >= 0.750 | yes |
| primary_D_worst_case_lower_bound | 0.000 | >= 0.150 | no |
| vehicle_encoded_harm_worst_case_lower_bound | 0.000 | > 0.000 | no |
| vehicle_primary_D_worst_case_lower_bound | 0.000 | > 0.000 | no |
| configuration_encoded_harm_worst_case_lower_bound | 0.000 | > 0.000 | no |
| configuration_primary_D_worst_case_lower_bound | 0.000 | > 0.000 | no |

## Interpretation limits

- The outcome is record-consistent counterfactual responsiveness, not a pure measure of retrieval or internal evidence use. Mapping mistakes remain a competing explanation.
- The primary D is the downstream-minus-encoded responsiveness gap under visible reasoning minus that gap under direct answering. Encoded harm and downstream retention are separate required spending criteria.
- A returned invalid answer is retained, not replaced. Pending and invalid scores range from -1 to 1 in full-plan bounds. Coefficients are combined before bounding shared outcomes.
- Each world is an independent unit; its record variants, queries, and reasoning instructions are paired observations. Component R estimates use complete two-response pairs; contrasts require every response with a nonzero coefficient.
- All gate decisions wait for all 144 responses. Thresholds are practical spending rules, not significance tests. A failed screen is insufficient support for the fixed extension, not proof that no effect exists.
- The two task families remain close analogues of record lookup. Positive findings cannot establish broad task generality, a novel mechanism, or an internal causal explanation.
- Stage two is not implemented or automatically authorized. A passing live screen only supports a separate review of a frozen held-out design.
