# Evidence role and reasoning placement

**complete_ready_for_interpretation** — live

480/480 returned; 480 valid; 0 invalid retained. Target fixed at row 10. 480/528 cumulative attempts.

Primary: reasoning harm for initial_answer minus reasoning harm for copy_record. Harm = accuracy when reasoning follows the final answer minus accuracy when reasoning precedes it.

Primary estimate: **0.021**, descriptive 95% CI [-0.125, 0.146]; 24/24 complete worlds; exact sign p=0.727.

Working prediction: the primary contrast is positive. The secondary copied-initial versus copied-record contrast tests the role wording while requiring identical extraction. A null does not establish equivalence. No estimate triggers more calls.

## Cells

| Condition / order | Correct / valid / planned | First class correct | Copy correct | Entry format met | Pattern / other wrong | Invalid / pending | Accuracy CI | Sensitivity CI |
|---|---:|---:|---:|---:|---:|---:|---|---|
| copy_record/reason_then_answer | 38/48/48 | 33 | 33 | 33 | 10 / 0 | 0 / 0 | [0.667, 0.917] | [0.667, 0.917] |
| copy_record/answer_then_reason | 44/48/48 | 28 | 28 | 28 | 3 / 1 | 0 / 0 | [0.833, 0.979] | [0.792, 0.979] |
| copy_initial/reason_then_answer | 32/48/48 | 27 | 27 | 27 | 14 / 2 | 0 / 0 | [0.521, 0.812] | [0.458, 0.771] |
| copy_initial/answer_then_reason | 45/48/48 | 24 | 24 | 24 | 3 / 0 | 0 / 0 | [0.875, 1.000] | [0.875, 1.000] |
| initial_answer/reason_then_answer | 40/48/48 | 48 | — | 48 | 8 / 0 | 0 / 0 | [0.708, 0.938] | [0.708, 0.938] |
| initial_answer/answer_then_reason | 47/48/48 | 48 | — | 48 | 1 / 0 | 0 / 0 | [0.938, 1.000] | [0.938, 1.000] |
| copy_marker/reason_then_answer | 23/48/48 | — | 46 | 46 | 22 / 3 | 0 / 0 | [0.312, 0.646] | [0.250, 0.604] |
| copy_marker/answer_then_reason | 47/48/48 | — | 48 | 48 | 1 / 0 | 0 / 0 | [0.938, 1.000] | [0.938, 1.000] |
| no_entry/reason_then_answer | 24/48/48 | — | — | 48 | 24 / 0 | 0 / 0 | [0.312, 0.688] | [0.312, 0.688] |
| no_entry/answer_then_reason | 46/48/48 | — | — | 48 | 2 / 0 | 0 / 0 | [0.896, 1.000] | [0.896, 1.000] |

First-entry counts use the valid-final denominator; every planned case remains in the primary design. A wrong copy does not invalidate its final answer. Full cell estimates, bounds, record-variant pairs and reasoning lengths are in summary.json.

## Paired contrasts

| Effect | Mean | Descriptive 95% CI | Complete worlds | Sign p | Full-plan bounds |
|---|---:|---|---:|---:|---|
| accuracy/copy_record_reasoning_harm | 0.125 | [0.021, 0.250] | 24/24 | 0.125 | [0.125, 0.125] |
| accuracy/copy_initial_reasoning_harm | 0.271 | [0.167, 0.396] | 24/24 | 0.000 | [0.271, 0.271] |
| accuracy/initial_answer_reasoning_harm | 0.146 | [0.062, 0.250] | 24/24 | 0.016 | [0.146, 0.146] |
| accuracy/copy_marker_reasoning_harm | 0.500 | [0.333, 0.667] | 24/24 | 0.000 | [0.500, 0.500] |
| accuracy/no_entry_reasoning_harm | 0.458 | [0.292, 0.625] | 24/24 | 0.000 | [0.458, 0.458] |
| accuracy/initial_minus_record_reasoning_harm | 0.021 | [-0.125, 0.146] | 24/24 | 0.727 | [0.021, 0.021] |
| accuracy/copied_initial_minus_record_reasoning_harm | 0.146 | [0.021, 0.271] | 24/24 | 0.070 | [0.146, 0.146] |
| accuracy/marker_minus_record_reasoning_harm | 0.375 | [0.250, 0.500] | 24/24 | 0.000 | [0.375, 0.375] |
| accuracy/no_entry_minus_record_reasoning_harm | 0.333 | [0.188, 0.479] | 24/24 | 0.000 | [0.333, 0.333] |
| accuracy/record_minus_copy_initial_before_final | 0.125 | [0.042, 0.208] | 24/24 | 0.031 | [0.125, 0.125] |
| accuracy/record_minus_initial_answer_before_final | -0.042 | [-0.167, 0.083] | 24/24 | 1.000 | [-0.042, -0.042] |
| accuracy/record_minus_copy_marker_before_final | 0.312 | [0.188, 0.438] | 24/24 | 0.000 | [0.312, 0.312] |
| accuracy/record_minus_no_entry_before_final | 0.292 | [0.167, 0.438] | 24/24 | 0.001 | [0.292, 0.292] |
| record_sensitivity/copy_record_reasoning_harm | 0.104 | [-0.042, 0.250] | 24/24 | 0.125 | [0.104, 0.104] |
| record_sensitivity/copy_initial_reasoning_harm | 0.312 | [0.188, 0.458] | 24/24 | 0.000 | [0.312, 0.312] |
| record_sensitivity/initial_answer_reasoning_harm | 0.146 | [0.062, 0.250] | 24/24 | 0.016 | [0.146, 0.146] |
| record_sensitivity/copy_marker_reasoning_harm | 0.562 | [0.396, 0.729] | 24/24 | 0.000 | [0.562, 0.562] |
| record_sensitivity/no_entry_reasoning_harm | 0.458 | [0.292, 0.625] | 24/24 | 0.000 | [0.458, 0.458] |
| record_sensitivity/initial_minus_record_reasoning_harm | 0.042 | [-0.104, 0.188] | 24/24 | 0.727 | [0.042, 0.042] |
| record_sensitivity/copied_initial_minus_record_reasoning_harm | 0.208 | [0.042, 0.417] | 24/24 | 0.070 | [0.208, 0.208] |
| record_sensitivity/marker_minus_record_reasoning_harm | 0.458 | [0.312, 0.604] | 24/24 | 0.000 | [0.458, 0.458] |
| record_sensitivity/no_entry_minus_record_reasoning_harm | 0.354 | [0.208, 0.521] | 24/24 | 0.000 | [0.354, 0.354] |
| record_sensitivity/record_minus_copy_initial_before_final | 0.167 | [0.062, 0.292] | 24/24 | 0.031 | [0.167, 0.167] |
| record_sensitivity/record_minus_initial_answer_before_final | -0.042 | [-0.167, 0.083] | 24/24 | 1.000 | [-0.042, -0.042] |
| record_sensitivity/record_minus_copy_marker_before_final | 0.375 | [0.229, 0.521] | 24/24 | 0.000 | [0.375, 0.375] |
| record_sensitivity/record_minus_no_entry_before_final | 0.292 | [0.167, 0.438] | 24/24 | 0.001 | [0.292, 0.292] |

## First-to-final transitions

Only the three class-entry conditions have initial-class transitions. A marker is not an initial class.

| Condition / order | Correct → correct | Correct → wrong | Wrong → correct | Wrong → wrong | Non-label first entry |
|---|---:|---:|---:|---:|---:|
| copy_record/reason_then_answer | 32 | 1 | 0 | 0 | 15 |
| copy_record/answer_then_reason | 27 | 1 | 0 | 0 | 20 |
| copy_initial/reason_then_answer | 26 | 1 | 0 | 0 | 21 |
| copy_initial/answer_then_reason | 23 | 1 | 0 | 0 | 24 |
| initial_answer/reason_then_answer | 40 | 8 | 0 | 0 | 0 |
| initial_answer/answer_then_reason | 47 | 1 | 0 | 0 | 0 |

## Provisional rationale flags

Flags inspect the reasoning field only. 'Never stated' means the narrow class-statement regex did not match, not that the record was never used. Missingness matches are candidates for manual verification, not a complete factuality measure. Negated and conditional missingness lines are excluded. Longer explanations have more opportunities to trigger a flag. rationale_review.md masks assignment and scored answer; rationale_key.csv contains the key. The prose itself can reveal the condition, so blinding is partial.

| Condition / order | Reasoning fields | Never stated | Missing candidate | Stated then overridden | Stated and followed | Missing + correct |
|---|---:|---:|---:|---:|---:|---:|
| copy_record/reason_then_answer | 48 | 22 | 5 | 0 | 21 | 3 |
| copy_record/answer_then_reason | 48 | 9 | 8 | 0 | 31 | 6 |
| copy_initial/reason_then_answer | 48 | 21 | 10 | 0 | 17 | 5 |
| copy_initial/answer_then_reason | 48 | 11 | 6 | 0 | 31 | 6 |
| initial_answer/reason_then_answer | 48 | 23 | 9 | 0 | 16 | 6 |
| initial_answer/answer_then_reason | 48 | 8 | 10 | 0 | 30 | 10 |
| copy_marker/reason_then_answer | 48 | 25 | 12 | 0 | 11 | 7 |
| copy_marker/answer_then_reason | 48 | 7 | 17 | 0 | 24 | 16 |
| no_entry/reason_then_answer | 48 | 26 | 4 | 3 | 15 | 1 |
| no_entry/answer_then_reason | 48 | 12 | 8 | 0 | 28 | 8 |

10,000 whole-world bootstrap resamples, seed 981723, descriptive unadjusted 95% percentile intervals. Each world first averages its two record variants. The exact two-sided sign test omits ties and tests sign balance, not mean magnitude. Only the declared primary is primary; all other contrasts are secondary/descriptive. Complete-world estimates exclude a world if any required answer is invalid or pending. Full-plan bounds range those answers over all three labels and are not confidence intervals. Degenerate intervals do not establish certainty or equivalence.

All conditions use the same fixed row-10 tables, schema fields and permission to differ. Only entry instructions and schema property order vary. These are effects of instructions and output interfaces; they do not identify hidden beliefs, mediation by reasoning text, or effects across row positions. The whole schema is visible before the first entry, so order may affect that entry too. Wrong copies and first-entry format failures remain in final-answer estimates. Correct-to-wrong transitions are descriptive, never a selection rule. The no-entry control still writes null; it is not a format-identical replication of earlier plain-text direct/CoT arms. Audit-marker copying is an active instruction, not a proven neutral attention control. No outcome authorizes more calls automatically.

Invalid outputs remain in the journal and are never resampled. With a structural/order failure, the report is output_manipulation_inconclusive: surviving-case estimates are diagnostics, not confirmation of the intended manipulation. Entry-format failures are reported separately without deleting their valid final answers. SIMULATED outputs cannot be evidence.
