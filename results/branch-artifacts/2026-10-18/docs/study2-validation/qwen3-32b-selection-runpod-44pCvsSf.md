# Qwen3-32B technical replay validation failure

- Run ID: `qwen3-32b-selection-runpod-44pCvsSf`
- Validation passed: `False`
- Mode: `LIVE_LOCAL`
- Scientific trajectory operations generated: `0`

## Summary

- Checkpoints: 12
- Exact-continuation failures: 2
- Probability-allclose failures: 4
- Total-variation failures above 1e-4: 3
- Argmax disagreements: 0

No scientific collection was started. Do not bypass this gate by relaxing
tolerances.

## Compact checkpoint results

```text
prompt  k   passed  exact  prob_close  argmax  TV                max_logit_err
------------------------------------------------------------------------------
     0   1    False  False       True    True   5.431543928e-11           0.25
     0   8    False   True       True    True   6.084982836e-08          0.375
     0  16    False  False      False    True     0.02456237774        0.28125
     0  32    False   True      False    True    5.12513311e-05        0.40625
     1   1    False   True       True    True   9.756200331e-10        0.28125
     1   8    False   True      False    True    0.002569158761          0.375
     1  16    False   True       True    True   6.832157144e-06           0.25
     1  32    False   True       True    True   1.038187568e-06      0.2734375
     2   1    False   True       True    True   9.634173217e-08          0.375
     2   8    False   True      False    True   0.0001840529556        0.21875
     2  16    False   True       True    True   1.836564212e-10           0.25
     2  32    False   True       True    True   1.069399922e-06           0.25
```
