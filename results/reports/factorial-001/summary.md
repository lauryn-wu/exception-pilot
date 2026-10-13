# Question × uncertainty diagnostic

Model: `gpt-4o-2024-08-06`; protocol: `verified-facts-factorial-v1`.

Valid: 639/640; invalid: 1; provider errors: 0; attempts: 640.

Complete independent list pairs: 19.

Explanatory study specified after observing the previous wording boundary. Question text and the uncertainty sentence vary independently. All cells share each list; the independent sample size is complete lists, not calls. Completion is not a pass, mechanism claim, novelty claim, or authorization for another study. The earlier stop_explicit_record_boundary decision is preserved.

Analysis status: **technical_failure**. No numerical pass threshold.

## Paired cell accuracies

These tables use only lists with all 32 valid answers. The target facts remain fixed across backgrounds; six non-target labels change. Every call is stateless.

| Question | Uncertainty sentence | Response | Support accuracy | Conflict accuracy |
|---|---|---|---:|---:|
| original | absent | direct | 100.0% | 100.0% |
| original | absent | cot_neutral | 100.0% | 47.4% |
| original | present | direct | 100.0% | 100.0% |
| original | present | cot_neutral | 100.0% | 50.0% |
| recorded | absent | direct | 100.0% | 100.0% |
| recorded | absent | cot_neutral | 100.0% | 100.0% |
| recorded | present | direct | 100.0% | 100.0% |
| recorded | present | cot_neutral | 100.0% | 81.6% |

## Reasoning-specific extra conflict penalties

E = (reasoning support − reasoning conflict) − (direct support − direct conflict). Positive E means conflict hurts reasoning more. Inspect the components too.

| Question / sentence | E | 95% list bootstrap | Positive / zero / negative lists |
|---|---:|---|---|
| original/absent | 52.6 pp | [36.8 pp, 68.4 pp] | 14 / 5 / 0 |
| original/present | 50.0 pp | [34.2 pp, 65.8 pp] | 14 / 5 / 0 |
| recorded/absent | 0.0 pp | [0.0 pp, 0.0 pp] | 0 / 19 / 0 |
| recorded/present | 18.4 pp | [7.9 pp, 28.9 pp] | 7 / 12 / 0 |

| Question / sentence | Direct conflict penalty | Reasoning conflict penalty | Direct − reasoning in conflict |
|---|---:|---:|---:|
| original/absent | 0.0 pp | 52.6 pp | 52.6 pp |
| original/present | 0.0 pp | 50.0 pp | 50.0 pp |
| recorded/absent | 0.0 pp | 0.0 pp | 0.0 pp |
| recorded/present | 0.0 pp | 18.4 pp | 18.4 pp |

## Factorial contrasts in E

Primary interaction = (original present − original absent) − (recorded present − recorded absent). Positive means the sentence increases E more under the original question. Zero interaction can coexist with additive wording effects.

| Contrast | Difference | 95% list bootstrap | Positive / zero / negative lists |
|---|---:|---|---|
| Sentence effect under original minus sentence effect under recorded (primary) | -21.1 pp | [-42.1 pp, 0.0 pp] | 4 / 6 / 9 |
| Original: sentence present minus absent | -2.6 pp | [-18.4 pp, 13.2 pp] | 5 / 8 / 6 |
| Recorded: sentence present minus absent | 18.4 pp | [7.9 pp, 28.9 pp] | 7 / 12 / 0 |
| Sentence absent: original minus recorded | 52.6 pp | [36.8 pp, 68.4 pp] | 14 / 5 / 0 |
| Sentence present: original minus recorded | 31.6 pp | [13.2 pp, 50.0 pp] | 11 / 6 / 2 |
| Average present-minus-absent effect across questions | 7.9 pp | [-1.3 pp, 17.1 pp] | 8 / 8 / 3 |
| Average original-minus-recorded effect across sentence levels | 42.1 pp | [27.6 pp, 56.6 pp] | 15 / 4 / 0 |

Intervals use 10,000 whole-list resamples, seed 981723. They are descriptive, not simultaneous confidence statements. Degenerate intervals reflect a constant observed vector, not population certainty. Small or uncertain effects do not prove absence. The primary contrast and all components must be interpreted together.

These are effects of exact prompt interventions on final answers, not observations of an internal mechanism. Only one snapshot and task family are tested. See FACTORIAL_PROTOCOL.md for scope, limitations, and the fixed interpretation plan.

## All returned answers (valid-only denominators)

| Question | Sentence | Response | Background | Correct / valid / planned | Accuracy |
|---|---|---|---|---:|---:|
| original | absent | direct | conflict | 40 / 40 / 40 | 100.0% |
| original | absent | direct | support | 40 / 40 / 40 | 100.0% |
| original | absent | cot_neutral | conflict | 18 / 39 / 40 | 46.2% |
| original | absent | cot_neutral | support | 40 / 40 / 40 | 100.0% |
| original | present | direct | conflict | 40 / 40 / 40 | 100.0% |
| original | present | direct | support | 40 / 40 / 40 | 100.0% |
| original | present | cot_neutral | conflict | 20 / 40 / 40 | 50.0% |
| original | present | cot_neutral | support | 40 / 40 / 40 | 100.0% |
| recorded | absent | direct | conflict | 40 / 40 / 40 | 100.0% |
| recorded | absent | direct | support | 40 / 40 / 40 | 100.0% |
| recorded | absent | cot_neutral | conflict | 40 / 40 / 40 | 100.0% |
| recorded | absent | cot_neutral | support | 40 / 40 / 40 | 100.0% |
| recorded | present | direct | conflict | 40 / 40 / 40 | 100.0% |
| recorded | present | direct | support | 40 / 40 / 40 | 100.0% |
| recorded | present | cot_neutral | conflict | 32 / 40 / 40 | 80.0% |
| recorded | present | cot_neutral | support | 39 / 40 / 40 | 97.5% |
