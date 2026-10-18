# New downstream-rule results: audit and implications

## Source and scope

Source: `downstream-rule-gpt4o-001-results(1).zip`, supplied in this conversation.
Protocol: `verified-facts-downstream-rule-v1`.
Source plan hash: `76fc5e7cab0b3635732b148768861860f71a1fc2c1b0d58d9ebef8ce2b1fa445`.
Source archive SHA-256: `f3fcb71c6be4cabfc6fa608dacf9ef14224e743050d5b2f7081363daf18efb8c`.

This is an independent analysis of saved requests and responses, not a new model run.
No repository changes, paid calls, or pretrained-model inference were performed.

## Independent checks performed

- Recounted all 432 responses and checked one-to-one correspondence to the 432 planned tasks and saved attempts.
- All saved response model identities match `gpt-4o-2024-08-06`; this is a metadata check, not independent provider attestation.
- Verified that saved response text equals the raw provider message and that strict validity and correctness agree with the raw outputs.
- Parsed every requested table and verified that its unique queried row's literal Verified class cell equals the saved answer key.
- Verified all four arms keep each case's table unchanged and use the same factual follow-up question.
- Verified history-present requests contain exactly the saved original assistant response unchanged.
- Verified the rule-present and rule-absent requests differ only by removal of the specified prediction sentence, separately within each history condition.
- Verified identical requests across the three repetitions of a case/arm.
- Independently recomputed complete-world membership, point estimates, and sign-aware unknown-outcome bounds for all 40 reported contrasts. No numerical disagreements (absolute tolerance 1e-12).
- Did not independently rerun the random bootstrap draws. Quoted bootstrap intervals below are the supplied report's descriptive intervals.

Completion: 432 returned; 414 strictly valid; 18 retained invalid; no pending. All 18 invalid outputs ended with `stop`; they are formatting deviations, not token-cap truncations.

The collection contains 36 selected historical cases across 15 distinct world IDs:
13 contradiction cases across 9 worlds; 13 availability-control cases across 9 worlds; 9 genuine-missing cases across 9 worlds; one wrong-final diagnostic case.
World sets overlap. Three repetitions do not create independent cases or worlds.

## Exact factors

The removed sentence is:

> If that cell is MISSING, make your best prediction from the other records.

The definition that MISSING means the class has not been recorded remains.

The factual follow-up is:

> What is written in [vehicle ID]'s Verified class cell? Reply with exactly one of A, B, C, or MISSING.

No-history: one user message containing the introduction, original table and factual question.
History: original classification user message, fixed saved assistant response, then the factual question in a new user message.

History removal therefore removes the original classification question/instructions and assistant response, and changes turn structure and prompt length. It does NOT isolate only the false statement.
Rule removal does NOT regenerate the saved assistant response. Its effect is conditional on that fixed history.

## 1. Contradiction cohort

All 13 historical responses start by correctly copying the recorded class and finish with a correct class answer, but contain target-specific false missingness claims in their reasoning.

| History | Prediction rule | Correct factual answer | False MISSING | Invalid |
|---|---|---:|---:|---:|
| Absent | Present | 31/39 | 8/39 | 0 |
| Absent | Absent | 39/39 | 0/39 | 0 |
| Present | Present | 14/39 | 25/39 | 0 |
| Present | Absent | 5/39 | 34/39 | 0 |

These are raw call counts, not equal-world rates.

Equal-world false-MISSING rates (mean repetitions within case, cases within world, then worlds):
- No history, rule present: 0.1574074074.
- No history, rule absent: 0.
- History, rule present: 0.5370370370.
- History, rule absent: 0.8703703704.

History effect with rule absent: +0.8703703704; supplied descriptive world-bootstrap interval [0.6851851852, 1].
History effect with rule present: +0.3796296296.
Removing the rule without history: -0.1574074074.
Removing the rule with history: +0.3333333333.
All comparisons above have all 9 cohort worlds complete.

The rule is not necessary for the strong false-missingness history effect in this cohort.
Its removal does not uniformly improve reporting. This does not establish that the rule is universally protective or identify an internal mechanism.

### Concrete saved example

Case: `columns-gpt4o-001/ex-list-000/record_2/full/copy_class`.

The table contains:

`| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | C |`

The fixed assistant response begins `COPIED: C`, contains `EZKZXD (MISSING)` in two feature summaries, and ends `ANSWER: C`.

With the rule absent:
- No history: C in all three follow-up calls.
- History supplied: MISSING in all three follow-up calls.

Thus this error is not explained by simply repeating the previous final class answer. It also does not show that the target–class representation was erased.

## 2. Genuine-missing controls and the primary outcome

| History | Prediction rule | Correct literal MISSING | Invalid |
|---|---|---:|---:|
| Absent | Present | 0/26 valid | 1 |
| Absent | Absent | 0/22 valid | 5 |
| Present | Present | 27/27 valid | 0 |
| Present | Absent | 25/25 valid | 2 |

The saved histories begin `COPIED: MISSING` and end with an A/B/C prediction.

All valid no-history follow-ups give A/B/C, despite a literal MISSING cell and an explicit cell-content question. All valid history follow-ups give MISSING.

The declared primary is removing the prediction rule without history in this cohort:
- 6/9 complete worlds.
- Both arm accuracies are 0 on that same complete set.
- Difference 0; supplied descriptive bootstrap [0,0].
- Full-plan strict-scoring difference bounds [-0.0370370370, 0.1851851852].

This is no observed rescue in the primary comparison, not an equivalence test or proof that the rule has no effect generally.
The striking contradiction/history findings are secondary, unadjusted analyses.

The missing-control cohort is not a fully crossed matched table/history counterfactual to the entire contradiction cohort. The source historical query includes a feature profile and comes from another run.
A retrospective exact-input check finds four present/missing no-history pairs differing only in the target cell: three contradiction cases (worlds 000 and 018) and one availability case (world 019). These limited overlaps do not make the full history comparison a matched availability factorial.

## 3. Availability controls

These historical responses have no reviewed false target-missingness assertion, but are not certified accurate in every other detail.

False MISSING counts:
- History, rule present: 15/39 valid.
- No history, rule present: 6/36 valid; 3 invalid.
- History, rule absent: 10/37 valid; 2 invalid.
- No history, rule absent: 4/35 valid; 4 invalid.

Therefore an explicit prior false-missingness assertion is not a necessary condition for every downstream MISSING error in this collection.
Do not interpret cross-cohort differences as the isolated causal contribution of that assertion: the cohorts contain different selected responses/tables.

## 4. Formatting sensitivity (post hoc, not a replacement score)

All 18 strictly invalid outputs state an unambiguous single candidate in a longer format, e.g. `COPIED: MISSING` or `The Verified class for ENA94H is B.`

A separate descriptive reading:
- All six invalid genuine-missing/no-history outputs still state an A/B/C class, so all 27 no-history outputs remain semantically wrong under either rule condition.
- The two invalid genuine-missing/history outputs state `COPIED: MISSING`; all 27 history outputs are semantically correct under either rule condition.
- The nine availability-control invalid outputs state the correct recorded class.
- The one wrong-final-diagnostic invalid output states `COPIED: C`, the correct class.

Keep the original 18 invalid statuses and strict unknown bounds. This sensitivity check shows the main genuine-missing split is not a format-parser artifact.
See `invalid_output_sensitivity.csv` for every individual output.

## Implications: recommendations, not established findings

1. Preserve Study 2A/2B and finish the already scoped judges/timing corrections. Do not insert the separate evidence probes into that patch.
2. Distinguish original classification performance from subsequent reporting of evidence status. A repair could change downstream factual reporting without changing an already-correct classification.
3. After an open-weight behavioral screen, a separately versioned downstream endpoint can append the same factual question to original and four-arm edited continuations. Keep the table fixed and score the actual cell. This measures the total downstream effect of the text intervention, not pure internal belief or the exact mediator.
4. Do not add MISSING to the existing 2A classification readout silently. A four-candidate factual-reporting readout answers a different question and belongs in a separately specified endpoint.
5. Screen open-weight models for both the native direct-versus-reasoning failure and the downstream reporting behavior, including actually missing cells. Testing GPT-4o histories on another model measures response to supplied histories, not that model's spontaneous production of such errors.
6. The probe design should distinguish literal record value/status from peer pattern and repeated values in generated text. A four-way target-cell decoder (A/B/C/MISSING) plus peer-pattern decoder can retain the two-primary-decoder structure. Include independently varied actual availability and displayed history claims, balanced label roles, constant overall marker/class-count controls, and grouped held-out evaluation.
7. No ground-truth recorded-class value exists in a MISSING cell; do not silently label it with an inferred class. Presence/status and value decoding should be evaluated separately.
8. First prioritize a matched actual-cell-status × displayed-history-claim assay on fresh tables, with roles, question, other history, and rule condition held fixed. Include accurate and false claims and semantic-preserving paraphrases. This would distinguish history following from correct availability tracking better than a single accuracy score.
9. Only then use targeted activation interventions with matched source/recipient prompts, source- and entity-specific controls, and distinct value/status output metrics. Record-only decoding does not prove native use of that record.
10. These downstream results do not themselves identify the mechanism behind earlier row-position effects or show a shared mechanism with them.

The central revised question is: when do the original table and the model's generated description of that table control subsequent factual reporting, and does the model keep the recorded value distinct from its availability/provenance?

The remaining alternatives include semantic status confusion, task reinterpretation, token-level copying/salience, and retrieval/binding differences. The current data distinguish some simple accounts but do not select one internal mechanism.
