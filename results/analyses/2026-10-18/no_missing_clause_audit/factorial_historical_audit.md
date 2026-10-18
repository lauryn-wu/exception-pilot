# Factorial historical saved-request audit

All 640 actual requests contain neither the exact MISSING conditional nor the word MISSING. Target labels parsed from every saved table match the answer keys. All raw text matches normalized text; 639 responses satisfy the frozen terminal parser and one remains invalid.

## Conflict-background results

| Question | Uncertainty | Direct, complete 19 lists | Reasoning, complete 19 lists | Reasoning, all 20 lists |
|---|---|---:|---:|---:|
| original | absent | 38/38 | 18/38 | 18/39 valid; 1 invalid |
| original | present | 38/38 | 19/38 | 20/40 valid; 0 invalid |
| recorded | absent | 38/38 | 38/38 | 40/40 valid; 0 invalid |
| recorded | present | 38/38 | 31/38 | 32/40 valid; 0 invalid |

The invalid case is fx-list-018/9/conflict/original/absent/cot_neutral. Its final line is a sentence ending “belongs to class B.” The frozen parser does not extract that B; expected is B, but the official classification remains invalid. Full-plan correctness bounds for original/absent/CoT/conflict are 18/40 to 19/40. A separately labeled semantic reading of that final sentence would count it correct, giving 19/40, without changing the frozen score.

## Exact wording

Original: Which class, A or B, does this vehicle belong to?
Recorded: Which class, A or B, is recorded for this vehicle in the table above?
Optional uncertainty sentence: Choose the more likely class even if uncertain.

## Exploratory target-unknown examples

All 320 reasoning responses were keyword-screened; all four candidates were manually inspected and explicitly replace a supplied target class with unknown. This is not an exhaustive semantic prevalence estimate.

- fx-list-009/0/conflict/recorded/present/cot_neutral: target FD6RUM, actual A, final B; class is rendered unknown in feature/group listings.

- fx-list-009/6/support/original/absent/cot_neutral: target F8NUJK, actual B, final B; class is rendered unknown in feature/group listings.

- fx-list-013/2/support/recorded/present/cot_neutral: target FTX9YW, actual A, final A; class is rendered unknown in feature/group listings.

- fx-list-017/0/conflict/original/present/cot_neutral: target F5CLBY, actual B, final A; class is rendered unknown in feature/group listings.

These actual saved results establish that reasoning-associated wrong answers and false unknown-class descriptions occurred without the MISSING conditional. They do not isolate the source of the current Qwen3 missingness pattern, or establish a cross-model rate comparison.

The recovery continued after the original format failure without retrying it; this remains a post-result amendment and the strict status stays technical_failure.
