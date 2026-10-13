# Factorial continuation audit

The original strict analysis is unchanged. Returned invalid answers remain invalid and are never resampled. Continuation is a documented post-result amendment, not an unmodified completion of the original protocol.

Returned: 640/640; valid: 639; invalid retained: 1; tasks without a returned answer: 0.

Strict complete lists: 19. Strict status: `technical_failure`.

See summary.md for the unchanged strict paired estimates and all denominators. The frozen parser does not extract labels from sentences.

## Retained invalid answers

- `fx-list-018/9/conflict/original/absent/cot_neutral` (attempt 596): "Therefore, based on the description and the pattern observed, the vehicle with license plate FYXZL5 belongs to class B."

## Sensitivity bounds

Full-plan point-estimate bounds across every 0/1 assignment to invalid answers. These are sensitivity bounds, not scored answers or confidence intervals.

Each contrast has its own bounds; extreme assignments can differ across contrasts. Sampling uncertainty is separate and is not represented by these bounds.

| Full-plan contrast | Lower | Upper |
|---|---:|---:|
| extra_penalty/original/absent | 52.50 pp | 55.00 pp |
| extra_penalty/original/present | 50.00 pp | 50.00 pp |
| extra_penalty/recorded/absent | 0.00 pp | 0.00 pp |
| extra_penalty/recorded/present | 17.50 pp | 17.50 pp |
| question_by_uncertainty_interaction | -22.50 pp | -20.00 pp |
| uncertainty_effect/original | -5.00 pp | -2.50 pp |
| uncertainty_effect/recorded | 17.50 pp | 17.50 pp |
| question_effect/absent | 52.50 pp | 55.00 pp |
| question_effect/present | 32.50 pp | 32.50 pp |
| average_uncertainty_effect | 6.25 pp | 7.50 pp |
| average_question_effect | 42.50 pp | 43.75 pp |
