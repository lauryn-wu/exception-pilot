# Record sensitivity and evidence use

Status: **complete_ready_for_interpretation**

384/384 returned; 0 unscorable final answers; 0 copy-format issues.

Do not interpret partial results to decide whether to extend collection. The planned unit is 24 independent worlds, not 384 independent observations.

## Prespecified effects

| Effect | Estimate | 95% interval | Complete worlds |
|---|---:|---|---:|
| record_sensitivity/direct_minus_cot | 0.521 | [0.354, 0.688] | 24/24 |
| record_sensitivity/copy_class_minus_copy_marker | 0.438 | [0.271, 0.604] | 24/24 |
| visible_accuracy/copy_class_minus_copy_marker | 0.396 | [0.250, 0.542] | 24/24 |
| visible_accuracy/priority_minus_cot | 0.375 | [0.229, 0.521] | 24/24 |
| visible_pattern/cot_minus_direct | 0.396 | [0.250, 0.542] | 24/24 |
| pattern/cot_missing_minus_visible | 0.458 | [0.271, 0.625] | 24/24 |
| anchor_accuracy/direct_minus_cot | 0.542 | [0.333, 0.750] | 24/24 |
| record_sensitivity/direct | 0.979 | [0.938, 1.000] | 24/24 |
| record_sensitivity/cot | 0.458 | [0.292, 0.625] | 24/24 |
| record_sensitivity/copy_class | 1.000 | [1.000, 1.000] | 24/24 |
| record_sensitivity/copy_marker | 0.562 | [0.396, 0.729] | 24/24 |
| record_sensitivity/priority | 0.896 | [0.792, 0.979] | 24/24 |

Record sensitivity ranges from −1 (both labels reversed) to +1 (both followed). An unchanged answer across target-cell edits scores 0. The primary effect is direct minus CoT sensitivity; the key secondary is class-copy minus marker-copy sensitivity.

Intervals are exploratory and unadjusted; a constant observed score can have a degenerate bootstrap interval without establishing certainty or equivalence. Per-effect full-plan bounds for unscorable answers are in summary.json; they are not CIs.

## Answers

| Family | Target cell | Arm | Valid | Accuracy | Pattern choice |
|---|---|---|---:|---:|---:|
| anchor | binary | direct | 24/24 | 1.000 | 0.000 |
| anchor | binary | cot | 24/24 | 0.458 | 0.542 |
| diagnostic | record_1 | direct | 24/24 | 1.000 | 0.000 |
| diagnostic | record_1 | cot | 24/24 | 0.542 | 0.458 |
| diagnostic | record_1 | copy_class | 24/24 | 1.000 | 0.000 |
| diagnostic | record_1 | copy_marker | 24/24 | 0.625 | 0.375 |
| diagnostic | record_1 | priority | 24/24 | 0.917 | 0.083 |
| diagnostic | record_2 | direct | 24/24 | 0.958 | 0.042 |
| diagnostic | record_2 | cot | 24/24 | 0.500 | 0.375 |
| diagnostic | record_2 | copy_class | 24/24 | 1.000 | 0.000 |
| diagnostic | record_2 | copy_marker | 24/24 | 0.583 | 0.333 |
| diagnostic | record_2 | priority | 24/24 | 0.875 | 0.125 |
| diagnostic | missing | direct | 24/24 | — | 0.583 |
| diagnostic | missing | cot | 24/24 | — | 0.875 |
| diagnostic | missing | copy_class | 24/24 | — | 0.833 |
| diagnostic | missing | copy_marker | 24/24 | — | 0.500 |

MISSING has no individual ground-truth label. Pattern choice on missing cases is a descriptive outcome, not accuracy. Final answers in copy arms are scored regardless of copy success; correct-copy subgroups are descriptive only.

## Copy and final-answer joint counts

```json
[
  {
    "arm": "copy_class",
    "value_group": "visible",
    "n_planned": 48,
    "n_returned": 48,
    "n_copy_correct": 48,
    "n_copy_wrong": 0,
    "n_copy_unparseable": 0,
    "n_final_unparseable": 0,
    "joint_visible_counts": {
      "copy_0/answer_0": 0,
      "copy_0/answer_1": 0,
      "copy_1/answer_0": 0,
      "copy_1/answer_1": 48
    }
  },
  {
    "arm": "copy_class",
    "value_group": "missing",
    "n_planned": 24,
    "n_returned": 24,
    "n_copy_correct": 24,
    "n_copy_wrong": 0,
    "n_copy_unparseable": 0,
    "n_final_unparseable": 0,
    "joint_visible_counts": null
  },
  {
    "arm": "copy_marker",
    "value_group": "visible",
    "n_planned": 48,
    "n_returned": 48,
    "n_copy_correct": 48,
    "n_copy_wrong": 0,
    "n_copy_unparseable": 0,
    "n_final_unparseable": 0,
    "joint_visible_counts": {
      "copy_0/answer_0": 0,
      "copy_0/answer_1": 0,
      "copy_1/answer_0": 19,
      "copy_1/answer_1": 29
    }
  },
  {
    "arm": "copy_marker",
    "value_group": "missing",
    "n_planned": 24,
    "n_returned": 24,
    "n_copy_correct": 24,
    "n_copy_wrong": 0,
    "n_copy_unparseable": 0,
    "n_final_unparseable": 0,
    "joint_visible_counts": null
  }
]
```

The original-format binary anchor diagnoses loss of the original effect. If the anchor shows harm but the ternary baseline does not, this is a task-format boundary. This study cannot identify an internal mechanism from narrated reasoning or prove novelty.
