# Historical no-missing-clause audit

Scratch intermediate review, 2026-10-18. No inference or semantic judge calls.

## Scope and independent checks

Read saved request messages in all 160 counterfactual-001 attempts and all 48 explanation-001 **anchor** attempts. Neither `missing` nor `unknown` occurs in any of these 208 request prompts (case-insensitive substring check). The other explanation-001 diagnostic conditions are outside this claim and do contain the MISSING instructions.

Parsed each saved response's final line independently, checked it against the saved answer field, and joined the specific target plate to its actual input-table label. All 208 target cells agree with the metadata expected label. Counterfactual target labels are unchanged across supporting/conflicting backgrounds for all 40 queried target/world combinations (20 worlds, two targets each).

| Study/subset | Direct | Reasoning |
|---|---:|---:|
| Counterfactual supporting background | 40/40 | 40/40 |
| Counterfactual conflicting background | 40/40 | 16/40 |
| Explanation binary anchor | 24/24 | 11/24 |

These are independently reconstructed accuracy counts. Repeated calls within a world are not independent worlds.

## Manual reading of every wrong reasoning response

Read all 24 counterfactual errors and all 13 anchor errors fully. The associated machine-readable scratch record is `historical_no_missing_audit.json`; full wrong-response inputs/outputs are in `historical_wrong_bank.json`.

Annotation distinctions:

- Explicit target unknown: lists the target's class as Unknown/Unknown class despite the supplied label. This is narrower than claiming internal forgetting and different from asserting that the original table cell is absent.
- Explicit missing/absent: says the target class is missing, absent, not recorded/provided, or blank. Do not count merely attempting classification.
- Correct target-class mention: actual target plate occurs inside the correct named class group. Do not count a feature said to be consistent with the correct class.
- Pattern justification: narrated conclusion relies on feature correlations or similarity. Does not imply an explicit comparison against the known source label or deliberate override.

| Annotation among errors | Counterfactual, n=24 | Anchor, n=13 |
|---|---:|---:|
| Explicit target Unknown/Unknown class | 3 | 2 |
| Literal missing or absent/not-recorded assertion | 0 | 0 |
| Correct target class shown in a class-group list | 3 | 0 |
| Feature-pattern/similarity justification | 24 | 13 |
| Description/environment pattern specifically used | 21 | 12 |

All 37 wrong final labels match the background pattern label. This does not mean every explanation uses the intended description rule: four justify their choice using other attributes. None of the 37 outputs contains the literal word MISSING. No hypothetical-missing statement was needed to obtain these counts.

The 3 correct-group counterfactual errors are cf-list-000/6/conflict/cot, cf-list-004/7/conflict/cot, and cf-list-012/9/conflict/cot. These are correct textual mentions, not evidence that the model persistently represented the source fact and deliberately overrode it.

## Exact examples

### Target marked unknown with no prompt missingness language

Counterfactual attempt 000065.json, cf-list-008/3/conflict/cot:

Input row:

`| VFKN67 | Built for subzero temperatures | Manual | Cloth | Two | A |`

Reasoning, in two separate feature lists:

`- VFKN67: Unknown class`

Conclusion:

`Therefore, based on the description, the more likely class for VFKN67 is B.`

Final line: B.

Explanation anchor attempt 000132.json, ex-list-008/anchor/cot:

Input row:

`| ETF4A9 | Used at an Arctic station | Manual | Vinyl | Two | A |`

Reasoning:

`- ETF4A9: "Used at an Arctic station," Manual, Vinyl, Two doors, Unknown class`

Conclusion:

`Therefore, the vehicle with license plate ETF4A9 belongs to class B.`

Final line: B.

### Correct target class mentioned, then another class chosen

Counterfactual attempt 000033.json, cf-list-004/7/conflict/cot:

Input row:

`| VXGXKN | Operates in tropical forests | Automatic | Vinyl | Four | B |`

Reasoning explicitly lists the target under `**Class B:**`:

`- VXGXKN: Automatic, Vinyl, Four doors (the vehicle in question)`

Later:

`Given these observations, the vehicle VXGXKN shares more characteristics with Class A vehicles, particularly the combination of automatic transmission and vinyl seat cover.`

Final line: A.

## Interpretation

These archives already demonstrate reasoning-associated accuracy losses without the MISSING clause or even that word in the input. They also contain a smaller, semantically related behavior: declaring an explicitly labeled target class Unknown. They do not establish that the exact literal-MISSING behavior seen in the newer Qwen experiment occurs without that clause, or quantify the clause's causal contribution. Different models, binary versus ternary labels, duplicated target attributes, and other wording differ across the historical and current experiments. The counterfactual prompt also says to choose the more likely class even if uncertain; the anchor prompt omits that sentence. A matched ablation would address the clause specifically.

Most wrong historical explanations have no missing/unknown assertion; the broad reasoning failure cannot be reduced to that narrated error subtype.
