# Feature support and recorded classes

**LIVE** — gpt-4o-2024-08-06

Returned 648/648, valid 648, retained invalid 0. Status: exploratory_complete.

Thirty-six fresh worlds; all 18 cells/world are paired. This tests deliberately structured competing cues. It does not by itself explain the earlier random-column benefit.

Primary: cot-minus-direct cue sensitivity. Positive means the secondary bundle allocation changes reasoning answers more than direct answers.

| Condition | Correct / valid | Pattern choices | Correct copy → wrong final |
|---|---:|---:|---:|
| favor_1/direct | 72/72 | 0 | None |
| favor_1/cot | 40/72 | 21 | None |
| favor_1/copy_class | 70/72 | 1 | 0 |
| favor_2/direct | 71/72 | 0 | None |
| favor_2/cot | 36/72 | 26 | None |
| favor_2/copy_class | 71/72 | 1 | 1 |
| balanced_record_cues/direct | 72/72 | 0 | None |
| balanced_record_cues/cot | 32/72 | 38 | None |
| balanced_record_cues/copy_class | 69/72 | 3 | 3 |

Intervals use 10,000 whole-world bootstrap resamples. All intervals are descriptive and unadjusted; complete-world denominators are contrast-specific. Full-plan bounds vary invalid/unreturned answers over A/B/C and are not confidence intervals. Degenerate intervals do not establish equivalence.

| Contrast | Estimate | 95% interval | Complete worlds | Full-plan bounds |
|---|---:|---|---:|---|
| cue_sensitivity/direct | 0.013888888888888888 | [0.0, 0.041666666666666664] | 36 | [0.013888888888888888, 0.013888888888888888] |
| record_sensitivity/direct | 0.9907407407407406 | [0.972222222222222, 0.9999999999999998] | 36 | [0.9907407407407406, 0.9907407407407406] |
| accuracy/favor_1/direct | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| record_sensitivity/favor_1/direct | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| accuracy/favor_2/direct | 0.9861111111111112 | [0.9583333333333334, 1.0] | 36 | [0.9861111111111112, 0.9861111111111112] |
| record_sensitivity/favor_2/direct | 0.9722222222222222 | [0.9166666666666666, 1.0] | 36 | [0.9722222222222222, 0.9722222222222222] |
| accuracy/balanced_record_cues/direct | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| record_sensitivity/balanced_record_cues/direct | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| accuracy/aligned/direct | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| accuracy/opposed/direct | 0.9861111111111112 | [0.9583333333333334, 1.0] | 36 | [0.9861111111111112, 0.9861111111111112] |
| alignment_advantage/direct | 0.013888888888888888 | [0.0, 0.041666666666666664] | 36 | [0.013888888888888888, 0.013888888888888888] |
| cue_sensitivity/cot | 0.3402777777777778 | [0.22916666666666666, 0.4513888888888889] | 36 | [0.3402777777777778, 0.3402777777777778] |
| record_sensitivity/cot | 0.3935185185185185 | [0.31481481481481477, 0.4722222222222222] | 36 | [0.3935185185185185, 0.3935185185185185] |
| accuracy/favor_1/cot | 0.5555555555555556 | [0.4444444444444444, 0.6666666666666666] | 36 | [0.5555555555555556, 0.5555555555555556] |
| record_sensitivity/favor_1/cot | 0.4027777777777778 | [0.25, 0.5555555555555556] | 36 | [0.4027777777777778, 0.4027777777777778] |
| accuracy/favor_2/cot | 0.5 | [0.3888888888888889, 0.6111111111111112] | 36 | [0.5, 0.5] |
| record_sensitivity/favor_2/cot | 0.3611111111111111 | [0.2361111111111111, 0.5] | 36 | [0.3611111111111111, 0.3611111111111111] |
| accuracy/balanced_record_cues/cot | 0.4444444444444444 | [0.3333333333333333, 0.5555555555555556] | 36 | [0.4444444444444444, 0.4444444444444444] |
| record_sensitivity/balanced_record_cues/cot | 0.4166666666666667 | [0.2916666666666667, 0.5416666666666666] | 36 | [0.4166666666666667, 0.4166666666666667] |
| accuracy/aligned/cot | 0.7222222222222222 | [0.6111111111111112, 0.8333333333333334] | 36 | [0.7222222222222222, 0.7222222222222222] |
| accuracy/opposed/cot | 0.3333333333333333 | [0.2222222222222222, 0.4444444444444444] | 36 | [0.3333333333333333, 0.3333333333333333] |
| alignment_advantage/cot | 0.3888888888888889 | [0.2361111111111111, 0.5416666666666666] | 36 | [0.3888888888888889, 0.3888888888888889] |
| cue_sensitivity/copy_class | 0.027777777777777776 | [0.0, 0.0625] | 36 | [0.027777777777777776, 0.027777777777777776] |
| record_sensitivity/copy_class | 0.9675925925925924 | [0.9305555555555556, 0.9953703703703702] | 36 | [0.9675925925925924, 0.9675925925925924] |
| accuracy/favor_1/copy_class | 0.9722222222222222 | [0.9305555555555556, 1.0] | 36 | [0.9722222222222222, 0.9722222222222222] |
| record_sensitivity/favor_1/copy_class | 0.9583333333333334 | [0.8888888888888888, 1.0] | 36 | [0.9583333333333334, 0.9583333333333334] |
| accuracy/favor_2/copy_class | 0.9861111111111112 | [0.9583333333333334, 1.0] | 36 | [0.9861111111111112, 0.9861111111111112] |
| record_sensitivity/favor_2/copy_class | 0.9861111111111112 | [0.9583333333333334, 1.0] | 36 | [0.9861111111111112, 0.9861111111111112] |
| accuracy/balanced_record_cues/copy_class | 0.9583333333333334 | [0.9027777777777778, 1.0] | 36 | [0.9583333333333334, 0.9583333333333334] |
| record_sensitivity/balanced_record_cues/copy_class | 0.9583333333333334 | [0.9027777777777778, 1.0] | 36 | [0.9583333333333334, 0.9583333333333334] |
| accuracy/aligned/copy_class | 1.0 | [1.0, 1.0] | 36 | [1.0, 1.0] |
| accuracy/opposed/copy_class | 0.9583333333333334 | [0.9027777777777778, 1.0] | 36 | [0.9583333333333334, 0.9583333333333334] |
| alignment_advantage/copy_class | 0.041666666666666664 | [0.0, 0.09722222222222222] | 36 | [0.041666666666666664, 0.041666666666666664] |
| cot_minus_direct_cue_sensitivity | 0.3263888888888889 | [0.2152777777777778, 0.4375] | 36 | [0.3263888888888889, 0.3263888888888889] |
| copy_minus_cot_cue_sensitivity | -0.3125 | [-0.4305555555555556, -0.19444444444444445] | 36 | [-0.3125, -0.3125] |
| copy_minus_cot_record_sensitivity | 0.5740740740740741 | [0.4861111111111111, 0.662037037037037] | 36 | [0.5740740740740741, 0.5740740740740741] |

Favor-1 versus favor-2 holds every pattern-class row fixed. The balanced record-cue reference also changes those rows: it is a balanced-support reference, not a pure removal of one cue.

Semantic judgments are not automatically generated. Copy reasoning-review-template.json to a separate coding file and annotate using FEATURES_PROTOCOL.md. The template removes the initial COPIED line and terminal answer and omits assigned condition/arm; prose and the truth table may still reveal them. This is partial blinding. Keep reasoning-review-key.json separate until coding is finished.
