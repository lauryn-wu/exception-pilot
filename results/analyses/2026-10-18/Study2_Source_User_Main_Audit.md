# Study 2: source-user main results audit

Audited 18 October 2026. The run completed successfully. Source transcription accuracy declines after longer saved reasoning prefixes, overwhelmingly through false `MISSING` reports. This is a behavioral source-reporting failure under the tested interface; it does not establish internal forgetting or deliberate override.

## Main results

Each input contains the unchanged original user table, the exact saved assistant prefix, and the successful pilot's fresh user request to transcribe the target Verified class cell. One source response is reused for both historical cue comparisons. All actual target cells contain A/B/C.

| Saved reasoning tokens | Correct source responses | False MISSING | Other wrong label | Invalid/incomplete |
|---|---:|---:|---:|---:|
| 0 | 111/112 (99.1%) | 0 | 1 | 0 |
| 256 | 100/112 (89.3%) | 11 | 1 | 0 |
| 512 | 80/108 (74.1%) | 27 | 1 | 0 |

All 332 returns are exact labels with terminal EOS. There are no unavailable operations, so format failures, truncation, or incomplete collection do not explain the decline.

On the same 108 trajectories eligible at all three checkpoints, correct counts are **107 → 96 → 80**. The paired 0→512 change is **−25 percentage points**, with a world-cluster bootstrap 95% interval of **−33.3 to −16.8 points** (2,000 draws; seed 2026101601). There are 27 correct→MISSING transitions and no incorrect→correct transitions. These 27 trajectories span 23 worlds.

| Paired comparison | Eligible/returned pairs | Correct→incorrect | Incorrect→correct | Accuracy change |
|---|---:|---:|---:|---:|
| 0→256 | 112 | 11 | 0 | −9.8 points |
| 0→512 | 108 | 27 | 0 | −25.0 points |
| 256→512 | 108 | 16 | 0 | −14.8 points |

The four pre-existing k512 exclusions remain unchanged: world011/v1, world026/v0, world027/v0, world059/v1. Earlier eligible checkpoints remain included. The single wrong-class trajectory is world023/v1: actual B, response A, pattern C. It is wrong already at k0 and remains A at both later checkpoints; it is separate from the 27 newly developed missingness errors.

## What the prefixes say

Manual inspection covered all 28 unique trajectories with any incorrect source response, through their 512-token prefixes. At every observed MISSING response, the supplied prefix already contains a complete target-specific missingness claim: 11/11 at k256 and 27/27 at k512.

The coding rule includes a target-specific assertion, target field, or copied target row claiming missingness. It excludes generic definitions of MISSING, prediction language alone, and purely hypothetical “if/as if missing” statements. Twenty-five of the 27 trajectories have straightforward false missingness assertions; the two world049 variants contain mixed entries combining a correct label with a missingness parenthesis. This is exploratory manual inspection informed by outcomes, not a blinded annotation study or validated model judge.

Of the 16 additional MISSING responses at k512, 15 first acquire an explicit missingness claim between the two measured checkpoints. World025/v1 already contains the false claim at k256 but still answers C correctly there. The first offending MISSING lexemes complete at tokens 56–448, 63–357 tokens before the first observed failing checkpoint. These coarse checkpoint measurements do not locate an immediate causal transition.

**Failure example: world049/v0.** The original table says:

> | V5TAY6W4 | Operates on polar ice | Automatic | Cloth | Four | Z | B |

The reasoning copies that row correctly, then states:

> - **Verified class**: B (MISSING in the question, but we are to determine it)

The source responses are **B → B → MISSING**. A correct mention can coexist with a conflicting later claim; the mention alone is not evidence of maintained internal knowledge.

**Counterexample: world056/v0.** The actual class is C. Before k256 the reasoning says:

> We are given that the **Verified class** for **V5TBWTYQ** is **MISSING**, so we must predict it based on the other records.

The source responses are **C → C → C**. World006/v1 supplies another counterexample. A false missingness statement is therefore not sufficient for failure under the fresh request.

## Existing answer readouts and natural answers

The old cues are restricted A/B/C first-class-token scores appended within the existing assistant context. The new endpoint is a generated transcription response after a new user turn. They are different elicitation interfaces, not matched generated-answer accuracies.

At k512, among the 27 false MISSING reports:

- 21 still prefer the verified class under the old `ANSWER:` cue.
- 17 still prefer it under `Final answer:`.
- 16 prefer it under both cues.

This interface dependence prevents interpreting MISSING as a general loss of access to the supplied class. The scores do not independently prove that the fact was continuously retained, because the original source is still in context and the readouts constrain the alternatives.

| Checkpoint | Cue | Uniquely wrong cached preferences | Correct source response among those cases |
|---|---|---:|---:|
| 0 | ANSWER: | 0 | 0/0 (undefined) |
| 0 | Final answer: | 9 | 9/9 |
| 256 | ANSWER: | 7 | 5/7 |
| 256 | Final answer: | 16 | 14/16 |
| 512 | ANSWER: | 8 | 1/8 |
| 512 | Final answer: | 19 | 10/19 |

Exact ties are excluded from uniquely wrong preferences: four for Final answer: at k256 and one at k512. All 664 historical preference computations and raw values were checked, including A/B/C mass and the separately labeled newline-inclusive sensitivity scores.

The original, unmodified trajectories have **75 correct, 33 pattern-class, 3 other-class, and 1 truncated final answers**, counted once across 112 trajectories. In the k512-eligible population, 71/108 natural final answers are correct. Exploratory cross-tabs show:

- Of the 27 MISSING reports: 17 correspond to wrong original natural finals, 9 to correct finals, and 1 to a truncated final.
- Of the 80 correct source reports: 62 correspond to correct original natural finals and 18 to wrong finals.

These natural finals are saved endpoints of the original trajectories. They were not produced after asking the new source question. Consequently these associations establish neither mediation nor the effect of the source question on a later answer.

## Execution and provenance

No blocker was found in the independent offline audit:

- All **1,941 sealed JSON hashes** verify; three other JSON files are derived reports.
- All **170 pilot snapshot files** match the previously uploaded successful pilot byte-for-byte.
- All **112 source rows** match the independently uploaded original trajectories.
- All **332 query identities and context concatenations** verify: original input IDs + exact saved prefix IDs + unchanged bridge IDs. Readable contexts and role offsets agree; the empty-assistant flag is true only at k0.
- All **664 cached raw values** match the original uploaded readout export and their preserved hashes. No original, readout, pilot, or judge calls were rerun.
- Exactly **332 unique LIVE_LOCAL returns and dispatches**, one completed invocation, one model load, zero failed/ambiguous operations, and no duplicate replay.
- Actual output: **702 tokens**, comprising A×98, B×96, C×100 and MISSING×38 across checkpoints.

The timed live invocation took **247.57 seconds (4m08s)**: backend initialization 150.72 seconds, including 127.86 seconds verifying model files; generation totaled 78.47 seconds. The report's `this_invocation` counters of zero new calls and 332 reused returns describe the archive/report refresh. Immutable live invocation records show 332 new calls and one load.

The pinned tokenizer/model assets are unavailable in this audit environment. Full tokenization and model-weight hashing were therefore not independently rerun here. The saved preparation records all 332 real-tokenizer validations, and backend telemetry matches the original pinned identity. Historical native readout journals were absent from the independently uploaded earlier export, but all required raw values match it exactly.

| Identity | Value |
|---|---|
| Archive | study2-source-user-main-v1-results-20261018T151948Z.tar.gz |
| Archive SHA-256 | 27f6121c7fd6e980fdd51299a0cafeab1e7857be1bce510a83a3455f69e3d192 |
| Reviewed/executed revision | 7f78a3338225614535b90a0d520ef6c346282d13 |
| Main plan hash | 0bbad97bda79e9c249f7cea110b1f2fd96671470f190faae64181e3267f77379 |
| Main code contract | 254e70cbcf4dfcb9d37c922c9973a3de2c63b7e1fccc54bfd88eeeb513fa588a |

## Interpretation and recommended next step

Supported claim: **After longer saved reasoning histories, the model becomes less reliable at explicitly reporting a supplied table cell, mainly by reporting that the recorded value is missing.** In the observed failures, target-specific missingness claims already occur in the reasoning history.

This does not show that the internal fact representation was erased, that a correct fact was deliberately overridden, or that the same statement caused the original classification error. Added history changes content, length, source-to-query distance, and the point where the old assistant turn closes. The current comparison does not isolate those factors.

Keep this prompt, parser, population and results frozen. The next useful direction is a **focused text intervention on the identified claims**, with the original classification continuation as the primary endpoint for explaining the paper's central failure. Select sites by explicit claim criteria, including cases whose source recovery succeeded, rather than selecting only the 27 observed failures. Freeze exact quotes/offsets and manually review the small set; no automatic semantic judge is needed to infer a latent belief.

Compare regenerated continuations after an audited correction and an appropriate control edit, preserving the preceding context and documenting token lengths, positions and information added. A correction alone can improve performance by supplying a fresh answer cue, so it is not a sufficient mechanism test. A matched correct-versus-incorrect claimed label contrast can isolate the influence of history content; a neutral replacement that supplies no answer addresses a different question. Choose the primary contrast and freeze its interpretation before executing rather than treating these controls as interchangeable.

The existing unmodified source responses can be reused if a source-recovery endpoint is included. Original classification outcomes require actual regenerated continuations from the edited contexts and a valid unedited continuation comparator. An intervention effect on transcription alone would not establish an effect on the original final classification.

This intervention logic follows the broader approach of [Lanham et al., Measuring faithfulness in Chain-of-Thought reasoning (2023)](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning), which changes reasoning text and measures downstream predictions. [Liu et al., Lost in the Middle (TACL 2024)](https://aclanthology.org/2024.tacl-1.9/) motivates care about information position, but its particular long-context findings should not be assumed to explain this shorter task. These are methodological precedents, not evidence of this experiment's mechanism or novelty.

No additional inference was performed during this audit. No rerun of the completed main experiment is needed.
