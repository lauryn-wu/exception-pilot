# Revision after reasoning: fresh-world diagnostic

Status: **complete_ready_for_interpretation**

192/192 returned; 192 valid; 0 invalid; 0 pending.

The fixed sample contains 24 fresh worlds, two target-record variants, and four arms per world. The worlds come from the same task family and model. Partial outcomes must not determine whether to extend collection.

## Output compliance

The revision arm emits initial_answer, reasoning, final_answer. The repeat control emits initial_answer, final_answer, reasoning. The anchors emit reasoning then answer, or answer then reasoning. All reasoning fields must contain a nonempty string. Only the explicit final_answer field is scored in the two new arms; the answer field is scored in the anchors. Labels mentioned inside reasoning never replace a structured answer.

| Arm | Returned / planned | Valid | Schema valid / returned | Key order valid / returned | Nonempty reasoning / returned | Invalid |
|---|---:|---:|---:|---:|---:|---:|
| reasoning_first | 48/48 | 48 | 48/48 | 48/48 | 48/48 | 0 |
| answer_first | 48/48 | 48 | 48/48 | 48/48 | 48/48 | 0 |
| revision | 48/48 | 48 | 48/48 | 48/48 | 48/48 | 0 |
| repeat_control | 48/48 | 48 | 48/48 | 48/48 | 48/48 | 0 |

Any wrong schema, key order, empty reasoning field, or other returned invalidity causes a technical/output-manipulation stop. The output remains in the journal and is never resampled. Invalid outputs contribute no initial or final scored label. Structural schema validity can be true while order or reasoning-presence validation fails. Unknown checks are counted separately in JSON.

## Descriptive reasoning lengths

| Arm | Measured returned outputs | Mean characters | Median characters | Mean whitespace-separated words |
|---|---:|---:|---:|---:|
| reasoning_first | 48 | 1201.354 | 1191.000 | 195.083 |
| answer_first | 48 | 1308.396 | 1357.000 | 210.375 |
| revision | 48 | 1124.854 | 1109.500 | 180.146 |
| repeat_control | 48 | 1289.125 | 1285.000 | 208.979 |

Lengths describe observed strings, including those with another compliance failure. Nonemptiness and length do not establish substantive reasoning, faithfulness, or a causal mediator; they are not grounds to exclude or resample an output.

## Paired final-answer accuracy

The primary contrast is repeat control minus revision. Positive values mean lower final accuracy when reasoning occurs between the two answers. This comparison uses all cases, without filtering on initial correctness. Answer-first minus reasoning-first is the secondary anchor contrast. Each world first averages its two target-record variants; complete worlds then receive equal weight.

| Contrast | Role | World-weighted mean | Descriptive 95% interval | Complete worlds | Paired cases improved / worsened |
|---|---|---:|---|---:|---:|
| repeat_control_minus_revision | primary | 0.271 | [0.125, 0.417] | 24/24 | 14 / 1 |
| answer_first_minus_reasoning_first | secondary | 0.375 | [0.229, 0.521] | 24/24 | 18 / 0 |

## Final-answer counts

| Arm | Correct / valid | Final accuracy | Pattern choices |
|---|---:|---:|---:|
| reasoning_first | 30/48 | 0.625 | 17 |
| answer_first | 48/48 | 1.000 | 0 |
| revision | 33/48 | 0.688 | 15 |
| repeat_control | 46/48 | 0.958 | 2 |

## Initial-to-final transitions

All valid cases in each new arm contribute. Initial accuracy is diagnostic: the full schema is visible before the initial answer, so anticipation may affect that answer. These counts do not condition the primary analysis on initial correctness.

| Arm | Initial correct / valid / planned | Final correct / valid / planned | Correct → correct | Correct → wrong | Wrong → correct | Wrong → wrong |
|---|---:|---:|---:|---:|---:|---:|
| revision | 46/48/48 | 33/48/48 | 33 | 13 | 0 | 2 |
| repeat_control | 46/48/48 | 46/48/48 | 45 | 1 | 1 | 1 |

| Arm | Initial accuracy | Final accuracy | Same answer | Different answer | Correct → pattern |
|---|---:|---:|---:|---:|---:|
| revision | 0.958 | 0.688 | 35 | 13 | 13 |
| repeat_control | 0.958 | 0.958 | 46 | 2 | 1 |

The following matrices retain every valid transition. Gold means the recorded target class; pattern means the background-pattern class; other means the other target-record label.

| Arm | Initial label | Final gold | Final pattern | Final other |
|---|---|---:|---:|---:|
| revision | gold | 33 | 13 | 0 |
| revision | pattern | 0 | 2 | 0 |
| revision | other | 0 | 0 | 0 |
| repeat_control | gold | 45 | 1 | 0 |
| repeat_control | pattern | 1 | 1 | 0 |
| repeat_control | other | 0 | 0 | 0 |

## Exploratory signed record sensitivity

| Effect | Mean | Descriptive 95% interval | Complete worlds |
|---|---:|---|---:|
| repeat_control_minus_revision | 0.271 | [0.125, 0.417] | 24/24 |
| answer_first_minus_reasoning_first | 0.396 | [0.229, 0.562] | 24/24 |
| reasoning_first | 0.604 | [0.438, 0.771] | 24/24 |
| answer_first | 1.000 | [1.000, 1.000] | 24/24 |
| revision | 0.688 | [0.562, 0.812] | 24/24 |
| repeat_control | 0.958 | [0.896, 1.000] | 24/24 |

Each followed target label contributes +0.5, the other target label −0.5, and the background-pattern label 0. Arm sensitivity ranges from −1 to +1; contrasts range from −2 to +2. An unchanged final answer across target-record variants scores 0. This score is not accuracy.

## Final answers across target-record variants

| Arm | Complete worlds | Both correct | Both wrong | Final answer changed | Final answer unchanged | Pattern both |
|---|---:|---:|---:|---:|---:|---:|
| reasoning_first | 24 | 11 | 5 | 18 | 6 | 5 |
| answer_first | 24 | 24 | 0 | 24 | 0 | 0 |
| revision | 24 | 11 | 2 | 22 | 2 | 2 |
| repeat_control | 24 | 22 | 0 | 24 | 0 | 0 |

These pairs compare two different target-record variants, not initial-to-final revisions. Changed answers alone do not establish retrieval: the edit also changes table-level label counts, and each cell has one sampled completion.

The primary comparison uses final-answer accuracy on all planned cases, without selecting cases by initial correctness. A positive repeat-control minus revision effect supports lower final accuracy when reasoning is placed between the two structured answers rather than after both answers, under these interfaces. Initial-answer accuracy is diagnostic: the model sees the entire schema before generating its initial answer, so output order may affect initial answers as well. Correct-to-wrong changes describe visible within-response revisions, but neither those changes nor the primary comparison uniquely identifies text self-conditioning, task selection, or a neural mechanism. The anchor comparison is answer-first minus reasoning-first. Reasoning text is not evidence of faithful internal computation; nonempty text does not establish substantive reasoning. A null result or perfect accuracy does not establish equivalence. No scientific pass threshold, outcome-dependent sample extension, or post-hoc selection by initial correctness is applied.

10,000 whole-world bootstrap resamples, seed 981723; descriptive, unadjusted 95% intervals. The sampling unit is the world, not an API call. The 24 fresh worlds come from one task family and one model; this is not a cross-model replication. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.

Each estimate excludes a world if any required answer is pending or invalid. The JSON records excluded worlds and task IDs, paired-case counts, and full-plan bounds once all planned responses return. Invalid outputs are never assigned a label from partial or malformed text. Transition counts use all valid cases and identify their denominator. All numerical outcomes are audit diagnostics only whenever interpretation_allowed is false.
