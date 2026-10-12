# Target location versus the order of misleading examples

Design fixed before implementation; no live observations collected here.
Base: upstream main bdc921839dc7981da406ee93cf56d0cd75e0e62e.

## Scope and overlap review

Read EVIDENCE_ROLE_PROTOCOL.md at 2eae5f2, ROW_POSITION_CONFIRM_PROTOCOL.md
at e026a97, and FEATURES_PROTOCOL.md and DOWNSTREAM_PROTOCOL.md at 28b5be0.
Those studies respectively manipulate early output roles/order, target position,
background feature assignments, and a new-turn query after a completed response.
This study changes only background record order at one fixed target row. It does
not copy or modify their code, configurations, protocols, or data. Reuse main's
counterfactual record generator, introduction, digest/RNG and atomic storage.
The new package is runnable from the checkout without editing pyproject.toml.

## Frozen inventory and counterbalancing

24 fresh worlds (seed 2026101211): six label-role permutations × two climates ×
two replicates. Ten complete records, target at data row 5 (the left middle row).
Four background records share its climate and support the misleading pattern P;
five opposite-climate records carry R1/R2 in a 3:2 split, reversed by replicate.
Two target variants set its recorded class to R1 or R2. Within every order
comparison the target record, all ten records, every label, all class counts and
all seven columns are identical. No missing cells, padding, feature edits,
record substitution, new examples, forced entries or initial-copy instructions.

Zero-based slots for the four pattern records (target slot 4):

| Arrangement | Slots | Signed row distances |
|---|---|---|
| before | 0,1,2,3 | -4,-3,-2,-1 |
| after | 5,6,7,8 | +1,+2,+3,+4 |
| both_left_near | 2,3,7,8 | -2,-1,+3,+4 |
| both_right_near | 0,1,5,6 | -4,-3,+1,+2 |

Each arrangement has the SAME absolute-distance multiset {1,2,3,4}. Average the
two both-side arrangements equally. Row 10 is always a non-pattern record.
Preserve the relative category orders within each matched quartet. Per world,
independently shuffle pattern and other records once; use all 20 joint cyclic
rotations (4 × 5). Thus every pattern identity occupies each pattern slot five
times and every other identity occupies each other slot four times, in EACH
arrangement. Reverse the two base category orders in the second replicate of
each climate/role combination. Rotations provide same-arrangement identity/order
controls; archive their variation instead of treating them as independent worlds.
This covers cyclic orders and reversal, not all 4! × 5! permutations.

Cross 24 worlds × 2 target variants × 20 rotations × 4 arrangements × 2 arms =
**7,680 planned responses**. This deliberately full counterbalance is larger
than a quick pilot. Preparing it is free. Never shorten it based on outcomes;
a smaller exploratory design requires a separately frozen protocol and seed.
Randomize the 16 cells of each world/rotation block, and the block schedule.

Direct versus visible instructions match the pending row-position study. Both
receive 1600 completion tokens, temperature zero, mistral-small-2603 with hidden
reasoning disabled. Only table order varies within an arm. The arm instruction
comes after the table, so target offsets are not changed by its length.

## Position audit and its limits

Always store character spans for target row, table plate, table class and query
plate. With --tokenizer-json, tokenize the COMPLETE user message once, using a
locally supplied model-matched tokenizer.json; save its SHA-256, token-ID hash,
token counts, and overlapping token start/end for all spans. Do not tokenize
isolated rows or use whitespace counts as model tokens. Preparation without a
tokenizer is allowed but marks positions UNMEASURED and cannot run live.
A tokenizer file alone does not prove provider equivalence: the user must supply
--tokenizer-model equal to the frozen model, and live requires --accept-tokenizer-
provenance. The manifest calls this a user-attested user-message audit, not a
verified server serialization. No tokenizer or model is downloaded automatically.

Report exact plate AND class token-start matches for before/after and all-four
quartets; do not assume row equality gives token equality. Primary uses all
planned blocks; a prespecified secondary subset uses before/after comparisons
whose plate/class token starts match, selected solely from inputs before outcomes.
If none match, report unavailable. Do not pad or drop inventory to force matches.
Also report offset differences and full-message lengths. A fixed provider chat
wrapper would add a constant, but server tokenization, normalization and hidden
serialization are not audited by this interface. A tokenizer mismatch invalidates
the token-matched interpretation. A future exact local-backend replication can
remove this uncertainty; no claim of pure token-position isolation is made here.

## Comparisons and inference

Let A(w,o,a) average accuracy over variants and 20 rotations, and H=A_direct-
A_visible. Sole primary: H(after)-H(before), averaged equally across worlds.
Positive means more reasoning-related harm with misleading records after the
target. Secondary: each arm's after-before accuracy; H(both)-[H(before)+H(after)]/2;
pattern-answer rates; within-arrangement rotation variability; the token-matched
primary subset, with its retained blocks/worlds explicitly reported.

Complete-world estimates require only their own cells. Report all planned,
returned, valid, invalid and missing denominators. Full-plan bounds allow each
unknown accuracy to be 0 or 1, with the contrast's signed coefficients. Bootstrap
whole world contrasts 10,000 times (981723); intervals are descriptive, secondary
intervals unadjusted. Rotations, arms and variants are repeated measures. No
scientific success threshold, model selection, automatic extension or paid judge.

A nonzero contrast shows sensitivity to this background rearrangement despite a
fixed target row, inventory and (on the audited subset) target token locations.
It challenges a target-location-ONLY account in this setting. It does NOT show
that this explains the old first/last result; the old target sweep is not repeated.
Before/after necessarily co-moves the opposite-climate examples, their class
positions, background token distances, query proximity and potential recency.
Even with radial row distances matched, token distances and clustering differ.
It cannot separate misleading-example primacy from other-example recency,
attention, retrieval, generic class-order effects, or a psychological mechanism.
No neutral relabeling arm is added because that would change the inventory.
Nulls do not establish equivalence, especially with ceiling direct accuracy.

## Retention and execution

prepare freezes config/source/protocol/requests/schedule and writes preview.json,
preview.md and position-audit.json. run is disabled unless --mock or --live is
explicit; live additionally requires token provenance acknowledgement. Every
request has an atomic started file followed by its raw returned body and score.
Invalid and truncated returns are terminal and retained; no response resampling,
no hidden retries. An unresolved started/transport-error attempt blocks resume.
Preserve it for manual reconciliation; the runner does not guess whether it was
billed. Exact model mismatch stops collection. Config/source/tokenizer/journal
drift and mock/live mixing block resume. No credentials enter artifacts.

Offline commands (repository root, Python 3.10+):

```sh
python3 -m unittest discover -s tests -p 'test_ordering_followup.py' -v
python3 -m exception_ordering prepare --output runs/ordering-preview
python3 -m exception_ordering run --output runs/ordering-preview --mock --max-calls 16
python3 -m exception_ordering analyze --output runs/ordering-preview
```

Optional tokenizer dependency: `python3 -m pip install tokenizers`. Supply an
already obtained model-matched file; it is not bundled and is not guessed.

```sh
python3 -m exception_ordering prepare --output runs/ordering-live \
  --tokenizer-json /absolute/path/tokenizer.json --tokenizer-model mistral-small-2603
# Explicit future opt-in; not executed as part of implementation:
python3 -m exception_ordering run --output runs/ordering-live --live \
  --accept-tokenizer-provenance --max-calls 16
python3 -m exception_ordering run --output runs/ordering-live --live \
  --accept-tokenizer-provenance --max-calls 7664
python3 -m exception_ordering analyze --output runs/ordering-live
```

Set MISTRAL_API_KEY in the shell for live execution. Use separate worktrees and
output directories for concurrent experiments. No existing study must be rerun.
