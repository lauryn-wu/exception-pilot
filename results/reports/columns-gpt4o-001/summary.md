# Column availability and reasoning

**LIVE** — gpt-4o-2024-08-06

Status: `exploratory_complete`. Returned 576/576; valid 576; retained invalid 0; attempts 576/608.

This study reuses all 24 explanation worlds. It is exploratory development, not a fresh-world confirmation. No automated success threshold or extension.

Minimal = plate + class. Description adds Description. Other attributes adds Transmission, Seat cover, Doors, Audit marker. Full retains all seven columns.

| Table / arm | Correct / valid | Pattern choices | Invalid / unreturned | Contract / 48 | Correct copy → wrong final |
|---|---:|---:|---:|---:|---:|
| minimal/direct | 48/48 | 0 | 0/0 | 48 | — |
| minimal/cot | 48/48 | 0 | 0/0 | 48 | — |
| minimal/copy_class | 48/48 | 0 | 0/0 | 47 | 0 |
| description/direct | 48/48 | 0 | 0/0 | 48 | — |
| description/cot | 13/48 | 35 | 0/0 | 48 | — |
| description/copy_class | 48/48 | 0 | 0/0 | 48 | 0 |
| other_attributes/direct | 48/48 | 0 | 0/0 | 48 | — |
| other_attributes/cot | 37/48 | 7 | 0/0 | 48 | — |
| other_attributes/copy_class | 48/48 | 0 | 0/0 | 48 | 0 |
| full/direct | 46/48 | 2 | 0/0 | 48 | — |
| full/cot | 30/48 | 16 | 0/0 | 48 | — |
| full/copy_class | 47/48 | 1 | 0/0 | 48 | 1 |

## Paired estimates

H = direct accuracy − reasoning accuracy. The two primary contrasts average the change in H from adding each column group across absence/presence of the other group. Positive = more reasoning harm with that group.

Record sensitivity averages +1 for the target class, −1 for the other record variant's class, and 0 for the background-pattern label; range [−1, 1]. A fixed answer across variants scores 0.

Intervals use 10,000 whole-world bootstrap resamples and are descriptive and unadjusted. Complete-world denominators are contrast-specific. Full-plan bounds vary invalid/unreturned answers over A/B/C; they are not confidence intervals. Degenerate intervals do not establish precision or equivalence.

### accuracy

| Contrast | Estimate | 95% interval | Complete worlds | Full-plan bounds |
|---|---:|---|---:|---|
| cell/minimal/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/minimal/cot | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/minimal/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/description/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/description/cot | 0.271 | 0.167, 0.375 | 24 | 0.271, 0.271 |
| cell/description/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/other_attributes/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/other_attributes/cot | 0.771 | 0.646, 0.875 | 24 | 0.771, 0.771 |
| cell/other_attributes/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/full/direct | 0.958 | 0.896, 1.000 | 24 | 0.958, 0.958 |
| cell/full/cot | 0.625 | 0.479, 0.750 | 24 | 0.625, 0.625 |
| cell/full/copy_class | 0.979 | 0.938, 1.000 | 24 | 0.979, 0.979 |
| reasoning_harm/minimal | 0.000 | 0.000, 0.000 | 24 | 0.000, 0.000 |
| copy_gain/minimal | 0.000 | 0.000, 0.000 | 24 | 0.000, 0.000 |
| reasoning_harm/description | 0.729 | 0.625, 0.833 | 24 | 0.729, 0.729 |
| copy_gain/description | 0.729 | 0.625, 0.833 | 24 | 0.729, 0.729 |
| reasoning_harm/other_attributes | 0.229 | 0.125, 0.354 | 24 | 0.229, 0.229 |
| copy_gain/other_attributes | 0.229 | 0.125, 0.354 | 24 | 0.229, 0.229 |
| reasoning_harm/full | 0.333 | 0.188, 0.479 | 24 | 0.333, 0.333 |
| copy_gain/full | 0.354 | 0.208, 0.500 | 24 | 0.354, 0.354 |
| description_effect_on_reasoning_harm | 0.417 | 0.312, 0.510 | 24 | 0.417, 0.417 |
| other_attributes_effect_on_reasoning_harm | -0.083 | -0.198, 0.042 | 24 | -0.083, -0.083 |
| column_interaction_on_reasoning_harm | -0.625 | -0.854, -0.396 | 24 | -0.625, -0.625 |
| minimal_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| minimal_minus_full/cot | 0.375 | 0.250, 0.521 | 24 | 0.375, 0.375 |
| minimal_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_minimal_minus_full | -0.354 | -0.500, -0.208 | 24 | -0.354, -0.354 |
| description_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| description_minus_full/cot | -0.354 | -0.542, -0.167 | 24 | -0.354, -0.354 |
| description_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_description_minus_full | 0.375 | 0.188, 0.562 | 24 | 0.375, 0.375 |
| other_attributes_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| other_attributes_minus_full/cot | 0.146 | -0.021, 0.312 | 24 | 0.146, 0.146 |
| other_attributes_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_other_attributes_minus_full | -0.125 | -0.312, 0.083 | 24 | -0.125, -0.125 |
### record_sensitivity

| Contrast | Estimate | 95% interval | Complete worlds | Full-plan bounds |
|---|---:|---|---:|---|
| cell/minimal/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/minimal/cot | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/minimal/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/description/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/description/cot | 0.271 | 0.167, 0.375 | 24 | 0.271, 0.271 |
| cell/description/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/other_attributes/direct | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/other_attributes/cot | 0.688 | 0.521, 0.833 | 24 | 0.688, 0.688 |
| cell/other_attributes/copy_class | 1.000 | 1.000, 1.000 | 24 | 1.000, 1.000 |
| cell/full/direct | 0.958 | 0.896, 1.000 | 24 | 0.958, 0.958 |
| cell/full/cot | 0.583 | 0.417, 0.729 | 24 | 0.583, 0.583 |
| cell/full/copy_class | 0.979 | 0.938, 1.000 | 24 | 0.979, 0.979 |
| reasoning_harm/minimal | 0.000 | 0.000, 0.000 | 24 | 0.000, 0.000 |
| copy_gain/minimal | 0.000 | 0.000, 0.000 | 24 | 0.000, 0.000 |
| reasoning_harm/description | 0.729 | 0.625, 0.833 | 24 | 0.729, 0.729 |
| copy_gain/description | 0.729 | 0.625, 0.833 | 24 | 0.729, 0.729 |
| reasoning_harm/other_attributes | 0.312 | 0.167, 0.479 | 24 | 0.312, 0.312 |
| copy_gain/other_attributes | 0.312 | 0.167, 0.479 | 24 | 0.312, 0.312 |
| reasoning_harm/full | 0.375 | 0.208, 0.562 | 24 | 0.375, 0.375 |
| copy_gain/full | 0.396 | 0.229, 0.583 | 24 | 0.396, 0.396 |
| description_effect_on_reasoning_harm | 0.396 | 0.271, 0.510 | 24 | 0.396, 0.396 |
| other_attributes_effect_on_reasoning_harm | -0.021 | -0.156, 0.115 | 24 | -0.021, -0.021 |
| column_interaction_on_reasoning_harm | -0.667 | -0.938, -0.396 | 24 | -0.667, -0.667 |
| minimal_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| minimal_minus_full/cot | 0.417 | 0.271, 0.583 | 24 | 0.417, 0.417 |
| minimal_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_minimal_minus_full | -0.396 | -0.583, -0.229 | 24 | -0.396, -0.396 |
| description_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| description_minus_full/cot | -0.312 | -0.521, -0.104 | 24 | -0.312, -0.312 |
| description_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_description_minus_full | 0.333 | 0.125, 0.542 | 24 | 0.333, 0.333 |
| other_attributes_minus_full/direct | 0.042 | 0.000, 0.104 | 24 | 0.042, 0.042 |
| other_attributes_minus_full/cot | 0.104 | -0.104, 0.312 | 24 | 0.104, 0.104 |
| other_attributes_minus_full/copy_class | 0.021 | 0.000, 0.062 | 24 | 0.021, 0.021 |
| copy_gain_other_attributes_minus_full | -0.083 | -0.312, 0.146 | 24 | -0.083, -0.083 |

## Full table → reduced table

| Comparison | Valid pairs | Wrong → correct | Correct → wrong | Both wrong | Both correct | Changed label |
|---|---:|---:|---:|---:|---:|---:|
| full_to_minimal/direct | 48 | 2 | 0 | 0 | 46 | 2 |
| full_to_minimal/cot | 48 | 18 | 0 | 0 | 30 | 18 |
| full_to_minimal/copy_class | 48 | 1 | 0 | 0 | 47 | 1 |
| full_to_description/direct | 48 | 2 | 0 | 0 | 46 | 2 |
| full_to_description/cot | 48 | 5 | 22 | 13 | 8 | 28 |
| full_to_description/copy_class | 48 | 1 | 0 | 0 | 47 | 1 |
| full_to_other_attributes/direct | 48 | 2 | 0 | 0 | 46 | 2 |
| full_to_other_attributes/cot | 48 | 11 | 4 | 7 | 26 | 17 |
| full_to_other_attributes/copy_class | 48 | 1 | 0 | 0 | 47 | 1 |

Every case, including unchanged and unresolved pairs, is in column-transitions.csv. record-pairs.csv compares both target-class variants. responses.jsonl retains all model text for reviewing missingness claims, invented similarities, and changes in justification. These are not automatically coded as hidden beliefs or causal mechanisms.

Column deletion changes width, token count, and class-cell position as well as available information. The license-plate-only query and shared instructions are fixed. The background-pattern label remains a label identity when Description is absent; a choice of it does not prove climate inference. Chance feature correlations and background class frequencies remain. Historical responses are never pooled into these estimates.
