# Fresh-data wording confirmation

Model: `gpt-4o-2024-08-06`; protocol: `verified-facts-wording-v1`.

Valid: 480/480; invalid: 0; provider errors: 0; attempts: 480.

Complete independent list pairs: 20.

Fresh-data wording follow-up specified after a positive exploratory pilot. All six wording cells share each list. The independent sample size is the number of complete lists, not calls. The ordered 15 pp checks are investment rules, not significance tests, mechanistic evidence or novelty claims. No follow-up runs automatically.

Screen: **stop_explicit_record_boundary**.

The following paired table uses complete lists only. Both backgrounds retain two exceptions; the queried target records stay fixed. Each call is a fresh conversation.

| Question | Response instruction | Support accuracy | Conflict accuracy |
|---|---|---:|---:|
| original | direct | 100.0% | 100.0% |
| original | cot_classification | 95.0% | 40.0% |
| original | cot_neutral | 97.5% | 45.0% |
| recorded | direct | 100.0% | 100.0% |
| recorded | cot_classification | 100.0% | 92.5% |
| recorded | cot_neutral | 100.0% | 100.0% |

Extra conflict penalty = reasoning conflict penalty − matched direct conflict penalty.

| Question / reasoning | Extra penalty | 95% list bootstrap | Positive / zero / negative lists |
|---|---:|---|---|
| original/cot_classification | 55.0 pp | [37.5 pp, 72.5 pp] | 15 / 5 / 0 |
| original/cot_neutral | 52.5 pp | [40.0 pp, 65.0 pp] | 17 / 3 / 0 |
| recorded/cot_classification | 7.5 pp | [0.0 pp, 20.0 pp] | 2 / 18 / 0 |
| recorded/cot_neutral | 0.0 pp | [0.0 pp, 0.0 pp] | 0 / 20 / 0 |

Primary robustness contrast: recorded/cot_neutral. All three ordered checks must pass before review for another model; recorded/cot_classification is diagnostic only.

| Wording contrast | Difference in extra penalties | 95% list bootstrap |
|---|---:|---|
| original/neutral_minus_classification | -2.5 pp | [-17.5 pp, 12.5 pp] |
| recorded/neutral_minus_classification | -7.5 pp | [-20.0 pp, 0.0 pp] |
| neutral/original_minus_recorded | 52.5 pp | [40.0 pp, 65.0 pp] |

Question wording changes include removal of the original uncertainty clause. These contrasts characterize the tested prompts, not hidden computation. A boundary stop preserves the previous finding within its original wording; it stops investment in the broader wording-robust claim. A stop is not proof of no smaller effect.

## All returned answers (valid-only denominators)

| Question | Response | Background | Correct / valid / planned | Accuracy |
|---|---|---|---:|---:|
| original | direct | conflict | 40 / 40 / 40 | 100.0% |
| original | direct | support | 40 / 40 / 40 | 100.0% |
| original | cot_classification | conflict | 16 / 40 / 40 | 40.0% |
| original | cot_classification | support | 38 / 40 / 40 | 95.0% |
| original | cot_neutral | conflict | 18 / 40 / 40 | 45.0% |
| original | cot_neutral | support | 39 / 40 / 40 | 97.5% |
| recorded | direct | conflict | 40 / 40 / 40 | 100.0% |
| recorded | direct | support | 40 / 40 / 40 | 100.0% |
| recorded | cot_classification | conflict | 37 / 40 / 40 | 92.5% |
| recorded | cot_classification | support | 40 / 40 / 40 | 100.0% |
| recorded | cot_neutral | conflict | 40 / 40 / 40 | 100.0% |
| recorded | cot_neutral | support | 40 / 40 / 40 | 100.0% |
