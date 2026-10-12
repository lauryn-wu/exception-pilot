# Which secondary feature pattern changes an explicit-record answer?

The column study found that adding transmission, seat-cover, doors, and audit-marker columns improved reasoning accuracy when descriptions were present. This experiment tests one candidate explanation: those extra attributes can supply competing class patterns. It uses new, deliberately structured worlds. It cannot alone establish why the earlier randomly assigned columns helped.

## Frozen design

36 fresh worlds × 2 target recorded classes × 3 feature arrangements × 3 response instructions = **648 requests**. Model `gpt-4o-2024-08-06`, temperature 0, 1,000 completion tokens in every arm; 684 cumulative attempts including transport failures. No model results select worlds, conditions, or subsequent sample size. No scientific success gate or automatic extension.

The table always has twelve rows and seven columns in the same order: License plate, Description, Transmission, Seat cover, Doors, Audit marker, Verified class. The query gives only the target plate. The introduction, question, and direct/reason/copy-class instructions are verbatim from the column study, including its MISSING clause. Target classes are always present.

Each world contains the target plus three R1, three R2, and five P background vehicles. Its five pattern-class background vehicles have the target's climate; the six remaining background vehicles have the opposite climate. Five records therefore support the same climate-pattern class P. The target's two possible recorded classes R1 and R2 differ from P. Description wording is frozen across all cells. Six descriptors per climate avoid repeating a descriptor among opposite-climate vehicles.

Target position is 1–12, each used in three worlds. At odd positions, (R1,R2,P) uses (A,B,C), (B,C,A), (C,A,B); at even positions it uses (A,C,B), (B,A,C), (C,B,A). Each label occupies each role once within each target position; each full permutation occurs six times. Target climate is warm in 18 worlds and cold in 18. Each binary target attribute takes each value in 18 worlds. Audit markers X/Y/Z appear once per three-row core class; the two extra P rows use the two non-target markers and are held fixed across every variant. Target marker is balanced. Markers are not manipulated to predict class.

The intervention changes whole (Transmission, Seat cover, Doors) bundles assigned to background rows. Let 1 mean the target's value and 0 the other value. Every condition has the same nine-row core bundle multiset, plus two fixed 000 bundles:

`111,111,111,100,010,001,110,101,011`

| Arrangement | R1 background bundles | R2 background bundles | P background bundles |
|---|---|---|---|
| favor_1 | 111,111,111 | 100,010,001 | 110,101,011 |
| favor_2 | 100,010,001 | 111,111,111 | 110,101,011 |
| balanced_record_cues | 111,100,011 | 111,010,101 | 111,001,110 |

Balanced-reference complementary pairs rotate across classes. Within-class row assignments are randomized once with the frozen seed. Primary favor_1/favor_2 comparisons keep every P-class row identical. The nine-row core has one exact triple match per class and two matches per individual feature per class. Two-feature conjunctions can still differ by class, so balanced_record_cues means balanced on those specified summaries, not completely uninformative.

All arrangements preserve the background bundle multiset, each column's value counts, target feature values, row order, plates, class labels, and descriptions. Changing recorded-class variant changes only the target class cell. A/B/C labels, target positions, and semantics are balanced across worlds. Prompt token counts need not be identical under swaps because tokenizer boundaries can depend on neighboring cells; layout and literal value inventories are fixed.

## Outcomes and estimates

The single primary contrast is **reasoning cue sensitivity minus direct cue sensitivity**. For each world, define s(answer)=+1 for R1, −1 for R2, 0 for P. Cue sensitivity is the average across target recorded variants of:

`[s(answer under favor_1) - s(answer under favor_2)] / 2`

Positive means answers move toward the class supported by the secondary bundles. The primary asks whether this influence is larger with reasoning. All correct direct and reasoning answers give zero cue sensitivity; always following the cue gives one; always opposing it gives minus one.

Secondary descriptive outcomes:

- Record sensitivity: average across arrangements of `[s(answer with target R1) - s(answer with target R2)] / 2`.
- Cue sensitivity for each arm and copy-class minus ordinary reasoning.
- Accuracy for aligned, opposed, and balanced_record_cues conditions; alignment advantage.
- Pattern-class choices, answer distributions, paired answer transitions, format adherence, correct initial copies followed by wrong/invalid final answers.
- Manually reviewed false missingness, false reported cells, false feature matches, and claimed supporting evidence.

Every contrast first produces a within-world value. Intervals use 10,000 whole-world bootstrap resamples with seed 981723. They are descriptive, unadjusted 95% intervals. Denominators are contrast-specific complete worlds. Missing/invalid answers remain in the archive; full-plan bounds vary them over all A/B/C outcomes. Bounds are not confidence intervals; degenerate bootstrap intervals are not evidence of equivalence. Calls within a world are not independent experimental units.

Balanced backgrounds make the target's recorded class the unique global majority once the target is added (4/3/3). Record sensitivity alone therefore cannot distinguish direct target lookup from using that majority. The primary cue contrast keeps class counts fixed. Correct copies and answers do not establish faithful reasoning or stable internal beliefs. A stated rationale does not establish which information caused the answer.

## Running

Run from the repository root with Python 3.10+ and `OPENAI_API_KEY` set for live calls. Offline preparation requires no credentials:

```bash
python3 -m exception_features prepare \
  --config configs/features_gpt4o.json \
  --output runs/features-gpt4o-001
```

Inspect all 648 exact requests in `preview.json`, with a readable sample in `preview.md`. The answer-key metadata is for inspection and is not sent as a separate model message.

```bash
caffeinate -i python3 -m exception_features run \
  --config configs/features_gpt4o.json \
  --output runs/features-gpt4o-001 \
  --max-calls 648
```

A completed or deliberately paused run is resumed with `--resume`. After a recorded transport failure, use `--resume --retry-errors`; this never retries or replaces returned wrong/invalid answers. Set `--max-calls` to the maximum number of additional attempts for that invocation. The cumulative 684 cap still applies. Source/config changes, model identity failures, and unresolved in-flight calls block unsafe resume. An offline smoke run must use a separate output and `--mock`; simulated results cannot be resumed as live evidence.

```bash
python3 -m exception_features analyze --output runs/features-gpt4o-001
zip -r features-gpt4o-001-results.zip runs/features-gpt4o-001
```

Raw requests/returns and all attempts are retained. `summary.json`/`summary.md` contain estimates; `responses.jsonl` preserves all text; `responses.csv` contains case-level outcomes; `paired-transitions.csv` includes unchanged, changed, and unresolved record/cue comparisons.

## Provisional manual explanation coding

`reasoning-review-template.json` includes every returned nonempty reasoning body, including invalid final answers and noncompliant direct-arm pretext. It removes the initial COPIED line and terminal final answer and omits condition, arm, and final correctness. Review order is randomized. Each entry contains the exact truth table and target plate. This is partial blinding: the text and table may reveal an arm, answer, or support arrangement. Do not consult the separate `reasoning-review-key.json` until coding is finished.

Copy the template to a separately named file; repeated analysis regenerates the template, never the separately named coding file. All four coding fields start `null` (unreviewed). A reviewed field is an object with `present` (boolean), `quotes` (nonempty list of exact substrings from the reasoning), and `notes` (nonempty justification referring to the relevant table fact). Supply a nonempty reviewer identifier. Even an absent judgment needs a representative exact excerpt and a note that the full text was reviewed; the excerpt alone does not prove absence.

- `false_missing`: the explanation represents the target's recorded class as missing, absent, unrecorded, or unknown. A hypothetical instruction or explicit correction of a previous assertion should be described in notes, not collapsed into a hidden belief claim.
- `false_cell`: a concrete plate-to-cell or plate-to-class report disagrees with the table. Distinguish literal errors from broad interpretation.
- `false_match`: it claims exact sameness for concrete features when those cells differ. Subjective similarities between descriptions need explicit notes and should not automatically count as factual mismatches.
- `claimed_support`: it explicitly cites table evidence as support for a candidate class. Record the candidate label, relevant features/plates, and whether the cited facts are accurate in notes. This is a claim in the explanation, not established causal use.

Example reviewed field:

```json
{"present": true, "quotes": ["the target's class is missing"], "notes": "Target plate FABCDE has Verified class B in row 4; the quoted assertion is false."}
```

Only actual exact text from the response is accepted. The example is illustrative, not generated evidence.

```bash
python3 -m exception_features code-review \
  --output runs/features-gpt4o-001 \
  --coding runs/features-gpt4o-001/my-reasoning-codes.json
```

The command validates identities, frozen source text, coding structure, reviewer identity, and exact quotations, then writes `reasoning-coding-summary.json`. Unreviewed fields remain unreviewed. These are provisional judgments without adjudication; do not present them as a validated automatic semantic measure or a direct readout of the model's internal computation.

Two additional fixed pattern-class rows use bundle 000 and unique same-climate descriptions, giving 12 total rows. The pattern class remains the unique overall majority (five rows versus four and three) under either target label. These rows are identical across cue conditions. The balanced_record_cues condition balances R1 and R2 individually and for exact triple matches; it does not balance all pairwise conjunctions or match rates against the five-row pattern class.
