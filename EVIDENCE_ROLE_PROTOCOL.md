# Evidence role and reasoning placement at row ten

Protocol: `verified-facts-evidence-role-v1`. Fixed before new model responses.
This package is independent of the query-form, column and row-position packages.
It adds files without changing historical packages, tests, configs or runs.

## Question and hypothesis

Does reasoning placed between an early entry and a final answer harm accuracy
more when the entry is an initial judgment than when it is copied from the
verified record? Does calling the same required copy an "initial answer" change
its protection? Accuracy and factual correctness of the explanation are separate
outcomes; neither alone establishes faithful internal reasoning.

Development evidence motivates this comparison: GPT-4o copied the verified class
and answered correctly in 48/48 recorded cases, whereas the separate revision
study had 46/48 correct initial answers and 33/48 correct final answers, including
13 correct-to-wrong changes. Marker copying succeeded in 48/48 cases but only
29/48 final classes were correct. Those studies differ in worlds and interface.
Their outcomes are motivation, not observations in this new sample.

## Design

- Model: `gpt-4o-2024-08-06`, temperature 0, one independent completion per task.
- 24 fresh worlds; seed `2026101201`; world IDs `er-list-000` through `023`.
- Ten records per world, plate prefix `J`, 240 distinct plates.
- Target always in displayed row **10**, after the same nine other rows in all
  conditions. Preserve the generator's relative order of those nine rows.
- Each world has two record variants. Only the target's verified class changes.
  The two target labels and the surrounding same-climate pattern label are all
  different. All six label-role permutations occur four times, twice per climate.
- Five first-entry conditions crossed with two serialized output orders.
- 24 × 2 × 5 × 2 = **480 planned calls**; 48 calls in each condition/order cell.
- Task IDs: `{world_id}/{record_variant}/{condition}/{order}`. Shuffle all 20
  tasks within each world using `rng_for(protocol, "schedule", seed, index)`.
- Every condition sees the same table, five-line target profile, introduction,
  question, permission to differ, field names, schema types and token budget.
- All arms receive 1000 completion tokens. Cumulative cap 528 attempts, including
  explicitly requested transport retries. Credentials come from `OPENAI_API_KEY`.

Row ten was chosen using the prior Mistral development run, where visible
accuracy was 47/48 at row 1, 40/48 at row 5 and 19/48 at row 10; direct accuracy
was 48/48, 47/48 and 48/48. That result reused development worlds and does not
establish the same position effect on GPT-4o. This study fixes a last-row setting
on fresh worlds before any new outcomes; it does not estimate a position effect
or generalize across positions. No world is chosen using its response.

## Exact prompts and interface

One user message per independent call:

1. Unchanged `INTRO` from `exception_explanation.core`.
2. Blank line and the seven-column table: License plate, Description,
   Transmission, Seat cover, Doors, Audit marker, Verified class.
3. Blank line and the unchanged five-line `describe(target)` profile.
4. Unchanged `QUESTION`: "Which class, A, B, or C, does this vehicle belong to?"
5. Exactly one condition instruction below.
6. The common output instruction below.

| Condition | Exact condition instruction |
|---|---|
| `copy_record` | Copy the target vehicle's Verified class cell exactly into first_value. Treat this entry as the recorded class. |
| `copy_initial` | Copy the target vehicle's Verified class cell exactly into first_value. Treat this entry as the initial answer. |
| `initial_answer` | Give your initial answer to the class question in first_value. |
| `copy_marker` | Copy the target vehicle's Audit marker cell exactly into first_value. |
| `no_entry` | Set first_value to null. |

The first two instructions differ only in "recorded class" versus "initial
answer". They require the same extraction. These are instructions about the
entry's role; no additional prose description is requested in the first field.

Common instruction, identical in all cells:

```text
Output only a JSON object with the fields "first_value", "reasoning", and "final_answer". Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. Your final answer may match or differ from the preliminary entry.
```

The strict JSON schema has these same properties in every condition:

- `first_value`: string or null. No gold value or condition-specific enumeration
  is embedded in the schema; it can express a wrong extraction or first answer.
- `reasoning`: string; actual output must contain nonempty reasoning.
- `final_answer`: string in `A`, `B`, `C`.
- All three required; no additional properties.

The **only** difference between orders is the serialized order of `properties`:

| Order | Emitted fields |
|---|---|
| `reason_then_answer` | `first_value`, `reasoning`, `final_answer` |
| `answer_then_reason` | `first_value`, `final_answer`, `reasoning` |

The user message, `required` array order and all other request fields remain
identical across this order comparison. Actual response key order is validated.
The final answer is scored from its named field, regardless of its location.

`prepare` generates `preview.md` with all 20 exact requests for world 000 and
`preview.json` with all 480 exact requests. It writes `plan.json` with source,
protocol, full-config, world and schedule identity plus an order-sensitive
SHA-256 for each exact request. [Committed preview](previews/evidence-role-gpt4o/preview.md).
These preparation artifacts contain no responses and make zero network calls.

## Estimands and analysis

The independent analysis unit is the world. Average its two record variants
within each condition/order cell, then calculate paired contrasts.

For condition c, define reasoning harm:

`H(c) = accuracy(c, answer_then_reason) - accuracy(c, reason_then_answer)`.

**Primary:** `H(initial_answer) - H(copy_record)`. Positive values mean more
harm from intervening reasoning for an initial judgment than for a copied record.
This uses final accuracy over all assigned cases, without filtering on the first
entry or selecting "initially correct" cases.

Secondary, descriptive analyses:

- `H(copy_initial) - H(copy_record)`: the bridge comparison, holding extraction
  requirements fixed while changing the role wording.
- All five H values and the marker/no-entry versus copied-record interactions.
- Within `reason_then_answer`, copied-record accuracy minus each other condition.
- The same cell estimates and contrasts on signed record sensitivity:
  +1 for the correct target label, -1 for the other record-variant label, and 0
  for the pattern label. Average the two variants; range [-1, 1]. An unchanged
  final label across record variants has zero sensitivity.
- First-class correctness, copy correctness, instruction-format compliance,
  pattern/other-error counts, paired record-variant changes and reasoning lengths.
- First-to-final transition counts for the three class-entry conditions. The
  marker is not an initial class; no marker "correct-to-wrong" count is reported.
  Null or non-class first entries have a separate category.

Use 10,000 whole-world bootstrap resamples (seed 981723) for descriptive 95%
percentile intervals. Report an exact two-sided sign test on each contrast's
nonzero world differences. It tests sign balance, not mean magnitude. Secondary
intervals and p values are unadjusted descriptive diagnostics; do not promote a
secondary finding to the primary or treat their collection as a confirmatory
family. Cell means have intervals but no meaningless sign test against zero.

For any estimate, a world must have all of that estimate's required final answers.
Report complete-world counts and excluded worlds. Full-plan bounds range pending
or invalid final answers over all three labels while holding valid answers fixed;
these are point-estimate bounds, not confidence intervals. Degenerate bootstrap
intervals do not establish certainty or equivalence.

## Explanation audit

Analyze **only the reasoning field**, in both output orders. The first entry and
final answer cannot trigger the rationale coder. Export all valid reasoning
fields to `rationales.csv`; retain every raw response in its attempt file.

Automated codes are provisional: `never_stated`, `relabeled_missing`,
`stated_then_overridden`, `stated_and_followed`. A narrow regex checks a target
plate followed within 160 characters on the same line by "class" and the expected
label. Missingness candidates require the target plate and a missingness phrase
on the same line; explicit "not missing"/"not unknown" and conditional lines
are excluded. Flags are text matches, not a complete factuality measure or
evidence that the class was internally absent or retrieved. The code can miss
tables, tuples, pronouns and implicit references, and can flag ambiguous prose.

Report counts and class shares by condition/order, plus missingness candidates
among correct answers. Correctness of the answer and correctness of the stated
account remain distinct. Longer explanations expose more possible errors.

`rationale_review.md` includes every available valid reasoning field, shuffled
with seed 981724, alongside its original table and target plate. It omits the
assigned condition, order, first entry and final answer. `rationale_key.csv`
contains the mapping. Text can reveal the assignment, so blinding is partial.
Manual review can separately code false missingness, correct record statements,
overrides, and false feature/marker claims; no paid judge model is called.

## Predictions and interpretation

Working directional prediction: the primary contrast is positive, and
`copy_record` outperforms `initial_answer` with reasoning before the final answer.
The bridge contrast has two plausible outcomes rather than a pass threshold:

| Outcome | Permitted interpretation |
|---|---|
| Both copy conditions protect accuracy; initial judgment does less well | Requiring extraction matters under these prompts; no established added benefit from the role wording |
| Copied-record framing protects more than copied-initial framing | The role-wording intervention changes the effect despite identical extraction requirements |
| Copying loses its previous advantage | The earlier result did not generalize to this matched interface; no attribution to one changed component |
| All cells perform well | The matched setup does not reproduce the failure and cannot resolve its earlier cause |
| Accuracy is high but rationale errors remain | Final-answer improvement does not establish correction of the stated account |

There is **no scientific pass gate** and no outcome triggers another run.
All results, including nulls, reversals and invalid outputs, are reported.

## Collection, stopping and limitations

Fixed 480 planned calls, cumulative cap 528 including transport retries, no sample
extension, outcome-based world selection, automatic retries, or resampling of
returned answers. Wrong copies and first-entry format failures remain final-answer
data. A valid first-entry string need not equal the expected value. Structural
JSON failures, wrong key order, empty reasoning, truncations and refusals are
retained as invalid; continue collection, report bounds, and label the intended
manipulation inconclusive if structural failures occur. Never salvage an answer
from prose or choose among multiple completions.

Stop on transport errors, model mismatch, user interruption, invocation limit or
cumulative cap. `--resume --retry-errors` retries known transport errors only.
An unresolved started request is a hard pause because it might already have
returned or incurred a charge; do not automatically retry it. Model mismatch is
a permanent stop for that run. Resume verifies source, protocol, config, schedule,
ordered request, raw response and scoring identity. Mock and live data cannot mix.

One model snapshot, one synthetic family and one position limit generality.
The model sees the full schema before its first entry. Output-order effects
include anticipation and placement/delay; they do not uniquely identify a causal
effect of the generated reasoning text. Correct copied tokens alone do not prove
internal evidence understanding. The no-entry condition emits null, and marker
copying may promote irrelevant associations. Recorded versus initial wording is
a specific instruction intervention, not an isolated latent representation.
Twenty-four worlds give limited precision for small effects. One completion per
cell does not measure repeat variability, even at temperature zero.

## Commands

Python 3.10+ and the standard library suffice. Run from this checkout's root;
the historical package manifest is unchanged. Use a new output directory.

```bash
python3 -m unittest discover -s tests -v
python3 -m exception_evidence_role prepare --config configs/evidence_role_gpt4o.json --output runs/evidence-role-gpt4o-001
caffeinate -i python3 -m exception_evidence_role run --config configs/evidence_role_gpt4o.json --output runs/evidence-role-gpt4o-001 --max-calls 20
caffeinate -i python3 -m exception_evidence_role run --config configs/evidence_role_gpt4o.json --output runs/evidence-role-gpt4o-001 --max-calls 480 --resume
python3 -m exception_evidence_role analyze --output runs/evidence-role-gpt4o-001
```

The first 20 calls cover a complete world; check technical operation, not whether
the hypothesized effect appeared. The second command completes the remaining
tasks, never adds 480 new tasks beyond the plan. Omit `caffeinate -i` off macOS.
For a known transport error, repeat the resume command with `--retry-errors`.

Offline mock check in a separate directory:

```bash
python3 -m exception_evidence_role run --config configs/evidence_role_gpt4o.json --output runs/evidence-role-SIMULATED --max-calls 20 --mock
python3 -m exception_evidence_role run --config configs/evidence_role_gpt4o.json --output runs/evidence-role-SIMULATED --max-calls 480 --resume --mock
```

Mock reports say `SIMULATED_SOFTWARE_TEST_NOT_EVIDENCE` and never authorize live
follow-ups. Both preparation and analysis are offline. Outputs: frozen plan,
previews, execution identity, atomic attempts, `summary.json`, `summary.md`,
`answers.csv`, `rationales.csv`, masked rationale review and its separate key.

If other studies are currently running, use a separate worktree so their source
files cannot change under them:

```bash
git fetch origin
git worktree add ../exception-pilot-evidence-role origin/codex/evidence-role-study
cd ../exception-pilot-evidence-role
```

## Related work

[Huang et al., ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html)
already document that intrinsic self-correction can degrade reasoning accuracy.
[Lanham et al.](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning)
use interventions to investigate dependence on stated reasoning. This study
tests a narrower matched behavioral contrast; it makes no generic novelty claim
about harmful reasoning, self-correction, or inconsistent explanations.
