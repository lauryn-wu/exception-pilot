# Saved-history semantic audit and next-test decision

Date: 2026-10-18. Offline analysis only; no model inference, repository changes, or Runpod work.

## Decision

Keep the 208-continuation source × history experiment on hold. The crossing is a valid test of conditional source/history influence, and many pairs do contain different correct label mentions. The audit does **not** establish that the crossing lacks a meaningful manipulation. Its limitation is that it changes whole histories and introduces source/history conflicts, so it does not isolate false availability claims as a cause of the natural classification failure.

A more precise diagnostic is to change an early, naturally generated assertion that a target value is absent into an assertion that it is provided, without supplying A/B/C, and continue the original classification response. A false paraphrase controls for rewriting and removal of the literal word MISSING. This is a diagnostic of availability framing, not a mechanism-identification or publication-ready study.

## Population and method

All 104 exact saved 512-token prefixes from the 52 worlds with both variants eligible were manually read. Excluded worlds: 011,026,027,059. These are longer surviving trajectories, not a random sample of all responses. No natural-final or source-query outcomes were joined during this pass; the analysts had prior project exposure, so this is exploratory, not blinded or preregistered. No external model judges were called.

Quotes were verified as literal substrings and offsets recorded. Correct mention includes a copied target cell or listing under its actual class heading, even when contradicted elsewhere. This is a textual association, not proof of retention, recognition, or belief. Conditional/hypothetical statements such as “as if missing” were excluded from factual absence claims. A copied target `?` was treated as unknown. Generic pattern discussion was not counted as an explicit target pattern prediction.

## Results

| Textual evidence by token512 | Histories |
|---|---:|
| Mentions actual source class | 90/104 |
| Falsely describes target value as missing/unknown | 31/104 |
| Contains both of the above | 20/104 |
| Explicitly associates target with wrong recorded A/B/C | 2/104 |
| Explicit target prediction of the designated pattern label | 0/104 |

The 31 include two copied `?` cells. Correct and missing quotes can coexist in a single contradictory entry, so these are overlapping categories. Zero explicit pattern predictions by this checkpoint does not mean no pattern reasoning or implicit commitment.

Exclusive profiles: 69 correct-only under the narrow factual-claim coding;20 correct-plus-missing;11 missing-only;1 correct-plus-wrong-label;1 wrong-label-only;2 without an explicit account. “Correct-only” here does not exclude hypothetical task reinterpretation.

Among the52 pairs,39 mention the respective correct source labels in both histories;25 are correct-only in both;6 contain a factual missing/unknown claim in both histories. Five have a nominal correct-only/missing-only contrast:004,025,029,031,033. World031's nominal correct side explicitly simulates treating the known class as missing;004 has an ambiguous “unknown record” heading despite affirming the class. Only025,029,033 are unqualified under these distinctions, and even those whole histories differ in other respects. These counts refine the earlier keyword screen (15pairs contain the literal word MISSING in both): keywords also capture conditionals and generic schema descriptions.

## Concrete bounded diagnostic

Nine clear early prose claims were identified in eight worlds:012/v0,016/v1,025/v1,041/v0,050/v0,052/v0,054/v0,054/v1,056/v0. Prior text was reviewed for earlier factual target-absence assertions. Generic schema mentions of MISSING are retained. The earlier text already frames the task as pattern prediction; this diagnostic therefore cannot establish that the availability assertion initiated that framing.

For each site, retain the original table and preceding text, stop immediately after the availability clause and before its inference consequence, and use:

1. The unedited prefix, freshly continued.
2. The same prefix with the target assertion's `MISSING`/`missing` replaced by `absent from the table`.
3. The same prefix with it replaced by `provided in the table`.

The two edited claims refer to the same target and source, contain no answer label, and neither replacement uses the literal MISSING. Example: “We are given that the **Verified class** for **V5T29QTZ** is **absent from the table**” versus “… **provided in the table**”. No later “so we must predict” instruction remains fixed; it is regenerated.

All three arms require fresh continuations. Existing natural suffixes are not substitutes for fresh replay controls. The proposed diagnostic is27 continuations across8 worlds, not27 independent observations. It is a small feasibility/interpretability test, not a powered confirmation. Exact text drafts and original token boundaries are included, but edited contexts still require pinned-tokenizer validation and independent semantic review. Do not send the draft directly to a runner.

Primary outcome: correction minus false-paraphrase accuracy on the original classification question, summarized by world. No extra source queries, judges, or checkpoint readouts are necessary. Include selected histories regardless of whether their original answer was correct. Freeze all choices before any generation; do not adaptively rerun to seek an effect.

Interpretation:

- Correction outperforms false paraphrase: availability wording causally affects subsequent classification in this subset. It could act through attention, rereading, or task interpretation; it does not prove internal forgetting/restoration.
- Both edits improve similarly over unchanged: the specific availability contrast is unsupported; rewriting or lexical changes may matter.
- No reliable difference: this repair has not explained the original errors. It does not establish that the statement is causally irrelevant or that information was forgotten. Inspect only the saved diagnostic continuations to understand whether the false claim is regenerated; do not automatically expand the run.

The diagnostic is intentionally limited to clear prose. Bare copied cells, contradictory parentheticals, and hypothetical “as if missing” passages require different interventions and are not silently pooled. The nine-case set is not an estimate of all possible editable cases in the full archives.

## Files

- `combined_annotations.json`:104 history annotations, exact quote offsets, pair summaries.
- `batch1.json`, `batch2.json`, `batch3.json`: source prefixes and metadata used in annotation; no future outcomes.
- `annotations1.json`, `annotations2.json`, `annotations3.json`: original annotation batches and notes.
- `availability_edit_diagnostic_draft.json`: nine original-prefix cuts and three-arm text drafts; NOT an executable protocol.

Source archive SHA256:27f6121c7fd6e980fdd51299a0cafeab1e7857be1bce510a83a3455f69e3d192. Main plan hash:0bbad97bda79e9c249f7cea110b1f2fd96671470f190faae64181e3267f77379.
