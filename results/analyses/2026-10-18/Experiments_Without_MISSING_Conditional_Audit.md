# Historical experiments without the MISSING conditional

Audited 18 October 2026. No model inference was performed.

**Main finding:** substantial reasoning-associated classification errors occur in earlier experiments whose actual saved prompts contain neither “If that cell is MISSING, make your best prediction from the other records” nor the word “MISSING.” Some responses also describe a supplied target class as “unknown.” The conditional is therefore unnecessary for the broader behavioral failure, although these data do not measure its contribution to the newer Qwen experiment.

## Scope and checks

Reviewed the original uploaded counterfactual-001, wording-001, factorial-001-recovered archives and the binary anchor subset of explanation-001. All use gpt-4o-2024-08-06 with A/B classes.

- 1,328 eligible saved requests: 160 counterfactual, 480 wording, 640 factorial, and 48 explanation anchors.
- Every eligible prompt omits the exact conditional and the case-insensitive word “missing.”
- Independently matched the queried license plate to its actual table row in every eligible prompt: zero answer-key mismatches.
- Independently parsed terminal answers with the frozen A/B grammar: zero mismatches with archived answer fields.
- The explanation experiment's other 336 requests use a different ternary task and include the MISSING wording. They are excluded here.
- Recovered factorial data supersede the earlier partial snapshot of the same run; the two exports are not independent replications.
- Scope is these four archives, not a claim that every historical project branch has been audited.

## 1. Counterfactual experiment

Twenty independent lists, two queried vehicles per list, matched support/conflict backgrounds and direct/reasoning conditions. Target labels remain fixed across backgrounds; six non-target labels change, with the same total exception rate.

| Background | Direct | Reasoning |
|---|---:|---:|
| Supporting pattern | 40/40 | 40/40 |
| Conflicting pattern | 40/40 | 16/40 |

The archived extra conflict penalty under reasoning is 60 percentage points; its descriptive whole-list bootstrap interval is 47.5–72.5 points. The unit is the list, not 160 independent observations.

This establishes that changing surrounding pattern evidence affects reasoning answers even when the queried record is unchanged and no missingness instruction is present. The prompt does contain “Choose the more likely class even if uncertain,” which the later factorial experiment varies.

## 2. Fresh wording experiment

Twenty fresh lists, with all wording cells paired within each list.

| Question | Response instruction | Support | Conflict |
|---|---|---:|---:|
| Original | Direct | 40/40 | 40/40 |
| Original | Classification reasoning | 38/40 | 16/40 |
| Original | Neutral reasoning | 39/40 | 18/40 |
| Recorded value | Direct | 40/40 | 40/40 |
| Recorded value | Classification reasoning | 40/40 | 37/40 |
| Recorded value | Neutral reasoning | 40/40 | 40/40 |

Exact original question:
“Which class, A or B, does this vehicle belong to?”
It is followed by “Choose the more likely class even if uncertain.”

Exact recorded-value question:
“Which class, A or B, is recorded for this vehicle in the table above?”
This condition also removes the uncertainty sentence.

Classification reasoning requests “Work through the classification, then put A or B alone on the final line.” Neutral reasoning requests “Think step by step, then put A or B alone on the final line.”

Thus the effect persists under neutral reasoning. The original-versus-recorded comparison here changes both question and uncertainty sentence; the factorial experiment separates them.

## 3. Question × uncertainty factorial

The optional sentence is “Choose the more likely class even if uncertain.” It is a different sentence from the MISSING conditional; none of the 640 requests contains the latter.

Primary paired analysis preserves the original complete-list policy: 19 lists with all 32 answers valid, yielding 38 answers per cell.

| Question | Uncertainty sentence | Direct, conflict | Reasoning, conflict |
|---|---|---:|---:|
| Original classification | Absent | 38/38 | 18/38 (47.4%) |
| Original classification | Present | 38/38 | 19/38 (50.0%) |
| Explicit recorded value | Absent | 38/38 | 38/38 (100%) |
| Explicit recorded value | Present | 38/38 | 31/38 (81.6%) |

All corresponding support-background cells are 38/38.

This is the clearest existing result against explaining the broader failure solely by explicit prediction language: the original question produces a large reasoning penalty even with neither MISSING wording nor the uncertainty sentence.

**Retained limitation:** the full run has 639 valid answers and one formatting-invalid answer, so its archived status remains technical_failure. For original/no-uncertainty/conflict reasoning across all 20 lists: 18 correct among 39 valid, plus one invalid. The invalid response's final sentence names the correct class B but fails the frozen terminal grammar. Full-plan correctness bounds are 18/40–19/40; a separately labeled semantic sensitivity is 19/40. No invalid response was retried or silently recoded. This limitation does not plausibly account for the large observed accuracy gap, but the run should not be described as technically clean.

## 4. Explanation experiment's binary anchors

Twenty-four worlds; these anchor prompts omit the MISSING setup. The ternary diagnostic conditions in the same archive do not.

| Response | Correct |
|---|---:|
| Direct | 24/24 |
| Reasoning | 11/24 |

The reasoning penalty therefore remains present in this additional task-format control.

## What the earlier reasoning says

A complete manual review of the 24 wrong counterfactual responses and 13 wrong binary-anchor responses found:

- All 37 justify their answer through patterns or feature similarity; all choose the conflicting background-pattern label. Four explanations rely on other attributes rather than the intended description pattern.
- Five explicitly label the target “Unknown” or “Unknown class”: three counterfactual, two anchor.
- None explicitly says the target is missing, absent, or not recorded; none uses literal MISSING.
- Thirty-two of the 37 errors contain no explicit missing/unknown assertion.
- Three counterfactual errors correctly place the target under its actual class somewhere in the reasoning before selecting the other class. Correct mention is not proof of stable internal retention or deliberate override.

The wording and factorial archives supplied additional manually verified target-unknown examples through keyword-assisted inspection. This is exploratory evidence, not an exhaustive blinded prevalence estimate. Correct-final responses can also label the target unknown.

### Concrete examples

**Counterfactual, cf-list-008/3/conflict/cot, attempt 000065.**

Source row:
`| VFKN67 | Built for subzero temperatures | Manual | Cloth | Two | A |`

The reasoning twice lists:
“VFKN67: Unknown class”

It concludes:
“Therefore, based on the description, the more likely class for VFKN67 is B.”

**Binary anchor, ex-list-008/anchor/cot, attempt 000132.**

The source records ETF4A9 as A. Its reasoning lists:
“ETF4A9: ‘Used at an Arctic station,’ Manual, Vinyl, Two doors, Unknown class”
and answers B.

**Wording, wd-list-018/1/conflict/original/cot_classification, attempt 000441.**

Source row:
`| WTP9E2 | Operates on polar ice | Automatic | Cloth | Two | B |`

The reasoning places WTP9E2 inside its Class B list but appends “(unknown class).” It then chooses A based on cold-climate similarity.

**Factorial, fx-list-009/0/conflict/recorded/present/cot_neutral.**

The source records FD6RUM as A. Even with the recorded-value question, the reasoning repeatedly writes “FD6RUM (Unknown class)” and answers B. The uncertainty sentence is present in this example.

**Correct-final counterexample, factorial fx-list-009/6/support/original/absent/cot_neutral.**

The source records F8NUJK as B. With neither MISSING wording nor the uncertainty sentence, the reasoning repeatedly calls F8NUJK “unknown class,” then answers B correctly.

These examples establish a related target-as-unknown behavior. They do not reproduce the newer source-transcription endpoint, where a fresh user question elicits the exact answer MISSING.

## Implications and revised recommendation

1. The MISSING conditional cannot be a necessary explanation of the project's general reasoning-associated accuracy penalty.
2. Task framing and competition from surrounding patterns have direct behavioral support. Neutral “think step by step” wording can produce the penalty; explicit recorded-value wording strongly attenuates it in these data.
3. Treating the target as unknown is one narrated subtype. Many wrong answers contain no such statement, and some unknown-class statements occur with correct answers.
4. These are GPT-4o, binary-label experiments. They do not estimate the causal effect of deleting one sentence from the newer Qwen3-32B ternary prompt. The conditional could still amplify or change the form of that model's failure.
5. A new clause-removal test should be a bounded robustness check, not the main next step justified by uncertainty about whether the broader phenomenon exists without the clause. The older data already answer that question.
6. The next explanatory study can use the existing focused continuation design on manually verified natural false-availability claims: unchanged continuation, a paraphrase retaining the false claim, and a label-free availability repair. Regenerate the suffix and score the original classification. Include correct and wrong original outcomes. An explicit-label repair is a secondary cue control. This estimates the influence of edited reasoning text in the eligible subset; it does not establish that the statement causes every original error or identify a complete internal mechanism.

No additional GPU run, model-judge call, source probe, or old readout was executed for this audit.

## Original archives

| Archive | SHA-256 |
|---|---|
| counterfactual-001.zip | 4f0fa2e43065977eb04e4763037e01c4e41eccc02ab962b01b4abeb857db2524 |
| wording-001.zip | 59fff8a003b32dbd824715563fd46a9734ff66e71dc69dbb450bb799100f3c16 |
| factorial-001-recovered.zip | d14cb780a856a3a72d32ecbeb6555f239d37137b6d4d0258b365598ce9f5e0fc |
| explanation-001.zip | 27f222e5f544d1020a1acb59709f4017181ce2551dfd8cccf9cff4c56023c077 |

Archived reports:
- [Counterfactual](https://github.com/lauryn-wu/exception-pilot/blob/main/results/reports/counterfactual-001/summary.md)
- [Wording](https://github.com/lauryn-wu/exception-pilot/blob/main/results/reports/wording-001/summary.md)
- [Factorial](https://github.com/lauryn-wu/exception-pilot/blob/main/results/reports/factorial-001/summary.md)
- [Explanation](https://github.com/lauryn-wu/exception-pilot/blob/main/results/reports/explanation-001/summary.md)

