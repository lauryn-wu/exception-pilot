# Record sensitivity and evidence use: bounded explanatory diagnostic

Specified 2026-10-08 after inspecting the completed reference, counterfactual,
wording, and factorial studies, and before collecting this diagnostic's data.
This is exploratory follow-up, not an independently preregistered confirmation.
Its purpose is to decide whether a more specific explanation merits further work.

## The question

When prompted reasoning gives an answer inconsistent with a verified individual
record, does the output fail to extract that record, or does it reproduce the
record correctly and still answer against it? Does copying the class help beyond
directing attention to the same row? How sensitive is the answer to the class
cell when the surrounding pattern is held fixed?

These are observable input/output distinctions. Copying a label is not proof
that an internal belief was correct, and a narrated explanation is not a causal
measurement of hidden computation.

## Relation to existing work

[Liu et al., ICML 2025, Mind Your Step (by Step)](https://proceedings.mlr.press/v267/liu25t.html)
already reports CoT harms on exception learning. Its
[Appendix C](https://arxiv.org/html/2410.21333v4) tests an informative feature and
retrieval-oriented instructions. Therefore, showing CoT harm or rescue by an
explicit lookup instruction is not our novelty claim.

[Halawi et al., Overthinking the Truth](https://arxiv.org/abs/2307.09476) examines
misleading demonstrations using intermediate model representations and head
ablations. Its use of “overthinking” concerns layer depth, not this generated
reasoning intervention. We are not claiming the first distinction between an
available answer and a later wrong prediction. A literature check would still
be required for any narrower result that emerges here.

The previous factorial study returned all 640 planned responses, with 639
scorable final answers. The strict paired analysis used 19 complete worlds.
Its interaction interval included zero. That uncertainty is preserved: the
new experiment does not treat the interaction as established. Literal “Unknown”
descriptions in a few saved outputs motivate this test but do not establish an
internal missing-data mechanism.

## One concrete sample

Suppose the target is EZKZXD, described as designed for humid summers. All four
other warm-climate vehicles have verified class A. The other-climate rows contain
B and C. Across three otherwise identical tables, the target's class cell is:

| Version | Target's verified class | Same-climate peers | Correct individual answer |
|---|---|---|---|
| record_1 | B | A, A, A, A | B |
| record_2 | C | A, A, A, A | C |
| missing | MISSING | A, A, A, A | Unobserved; do not score accuracy |

The target also has an audit marker, such as Z, assigned separately from class.
The same table is queried in independent calls with different instructions.
A possible class-copy response is:

```text
COPIED: B
[model-generated reasoning]
ANSWER: A
```

If actually observed, this would be a correct copy followed by an incorrect
pattern-consistent answer. It is a hypothetical example, not a predicted or
already observed result of this diagnostic. In the marker-copy condition, the
first line should instead be `COPIED: Z`; this directs attention to the same row.

## Fixed design and budget

- Model: `gpt-4o-2024-08-06`, temperature 0, one returned choice per request.
- 24 fresh worlds, one target per world, 16 requests per world: **384 planned calls**.
- All six assignments of A/B/C to the two record values and the pattern occur
  four times, twice for each target climate. License plates use a fresh E prefix.
- Within each world, only the target class cell changes across the three
  diagnostic versions. The nine other rows and every other target field remain
  fixed. All four same-climate peers have the pattern label; the five
  other-climate vehicles have the other two labels in a 3:2 or 2:3 split.
- Independent requests, randomized condition order within world. No response
  becomes another request's context. No outcomes affect generation or ordering.
- Direct completion caps: 10 tokens for original-format anchors, 16 for the
  diagnostic. All CoT conditions: 1,000 tokens. Planned output-token caps sum to
  289,392; actual usage and input tokens are saved. This is not a dollar quote.
- **400 total attempts maximum**, including errors and interruptions. This allows
  at most 16 extra transport attempts if all 384 planned tasks complete. There
  are no hidden retries. `--max-calls` additionally caps each invocation.
- The first 16 calls are a technical check within the same 384-call plan. Do not
  change prompts, sample size, or inclusion rules after viewing their outcomes.

| Condition | Visible value 1 | Visible value 2 | Missing | Calls/world |
|---|---:|---:|---:|---:|
| Direct answer | 1 | 1 | 1 | 3 |
| Neutral CoT | 1 | 1 | 1 | 3 |
| Copy class, then CoT | 1 | 1 | 1 | 3 |
| Copy audit marker, then CoT | 1 | 1 | 1 | 3 |
| Explicit record priority, then CoT | 1 | 1 | — | 2 |
| Original binary conflict task, direct + CoT | — | — | — | 2 |
| **Total** | | | | **16** |

The binary anchors reproduce the earlier factorial study's original-question,
uncertainty-absent conflict prompts on fresh worlds and one preselected target.
They omit the audit marker and missing-value instructions and keep the A/B
response format. They are a calibration check, not a crossed test of the third
class, marker column, and missing-value instructions separately.

The diagnostic introduction explicitly defines MISSING and requests a best
prediction if the class is missing. That language may itself cue lookup on
visible cases. If it removes the earlier effect, we report that boundary rather
than retroactively tuning the prompt to recover a positive result.

## Exact instructions and output rules

Every diagnostic asks: “Which class, A, B, or C, does this vehicle belong to?”
The generated `preview.md` and `preview.json` contain the entire first world's
16 requests. `core.py` is the source of exact prompt text; each attempted
request is also saved byte-for-byte as a JSON value in the journal.

- Direct: only `ANSWER: A`, `ANSWER: B`, or `ANSWER: C`.
- CoT: step-by-step response with that same final-line format.
- Copy arms: first nonempty line is `COPIED: ` plus the specified cell value;
  reasoning follows; the last nonempty line is `ANSWER: ` plus the chosen class.
- Priority: explicitly says the verified individual record is definitive even
  when other vehicles suggest a different class, then requests CoT.
- Diagnostic parsers require the exact prefix and uppercase label on the
  boundary lines, allowing surrounding whitespace. They never extract an answer
  from prose. Original anchors retain the frozen A/B parser.

Copy correctness and final correctness are separate. A valid but incorrect
copy is behavioral data. A malformed copy is recorded as a copy-format issue;
a valid final answer still enters all final-answer analyses. A correct copy
does not make a wrong final answer correct. Missing cases have no gold final
answer, even if the model chooses the peer-majority class.

A completed but unparseable final answer is retained, marked invalid, and never
resampled. Other planned tasks continue. A truncated, refused, model-mismatched,
or otherwise incomplete provider response pauses collection and cannot be
retried as a transport error. HTTP/time-out errors and interrupted unresolved
requests can be retried only with `--retry-errors`, within the cumulative cap.
An unresolved request may have been billed; the attempt is still counted.

## Primary and secondary estimands

Let the two visible recorded labels in a world be L1 and L2, and let Y1 and Y2
be the corresponding final answers under a given arm. Record sensitivity is:

```text
S = 0.5 × [1(Y1=L1) − 1(Y2=L1) + 1(Y2=L2) − 1(Y1=L2)]
```

S is +1 when both answers track their recorded labels, −1 when both are swapped,
and 0 when the answer stays the same across both target-cell edits. This differs
from accuracy: always choosing L1 gives 50% accuracy but zero record sensitivity.

**Primary:** mean world-paired `S_direct − S_cot`. A positive value means the CoT
instruction reduces directed sensitivity to the target-record intervention.

**Key secondary:** mean world-paired `S_copy_class − S_copy_marker`. This asks
whether class copying preserves sensitivity beyond the same-row marker control.
All assigned calls enter the comparison regardless of their copying success.

Other prespecified descriptions/contrasts:

- Visible accuracy: class copy minus marker copy; explicit priority minus CoT.
- Visible pattern choice: CoT minus direct.
- CoT pattern choice on missing cases minus its average on the two visible cases.
- Original-format anchor accuracy: direct minus CoT.
- Sensitivity for each individual diagnostic arm.
- Counts crossing correct/incorrect copy with correct/incorrect final answer.
  Correct-copy subgroups are descriptive and must not be called causal mediation.
- Answer distributions for all cells; no accuracy for missing cases.

For each contrast, use worlds with every required final answer scorable. A
missing-case formatting error does not remove that world from a contrast that
uses only visible cases. Report excluded worlds and cell-level format rates.
After every planned task has a returned response, also report full-plan bounds
by assigning each unscorable final answer every allowed label. These are
point-estimate bounds, not confidence intervals and not imputed scored answers.

Intervals use 10,000 paired bootstrap resamples of whole worlds, fixed seed
981723. They are exploratory and unadjusted for multiple comparisons. With
24 worlds, modest effects remain imprecise. A degenerate bootstrap interval
from uniform observations does not imply population certainty or equivalence.
There is no automated scientific pass or novelty gate.

## Interpretation and stopping

| Observed pattern | What it would support | What remains unresolved |
|---|---|---|
| Binary anchor shows harm; ternary CoT tracks records well | The new task format attenuates the effect | Which format change matters; no evidence of extraction failure |
| CoT ignores target edits and repeatedly selects the fixed peer label | Behavior is insensitive to those edits and consistent with pattern use | Internal missingness, retrieval failure, and task policy are not separated by this alone |
| Class copy helps more than marker copy | Class-specific output/attention matters beyond the same-row control | Retrieval, answer priming, and priority cues remain confounded |
| Correct class is copied, but final answer selects the peer label | Failure can persist after correct explicit extraction | It does not prove a correct latent belief was overwritten |
| Explicit priority helps while class copy leaves correct-copy/wrong-final errors | Evidence-use policy is a stronger lead than extraction alone | Still a behavioral dissociation requiring independent confirmation |
| Both copy arms help similarly | Same-row attention or added instructions may explain rescue | No class-specific benefit established |

These explanations can coexist. Cell edits also change global label counts by
one; sensitivity alone does not prove exact-row lookup. Copy instructions differ
semantically and cannot perfectly match attention or token content. Temperature
zero does not guarantee service-level determinism. The original-format anchor
has no supporting-background control and is not a new estimate of the earlier
conflict-by-CoT interaction. This is one task family on one older model snapshot.

Finish the fixed plan unless a technical problem or the user's budget stops it.
If only explicit lookup rescue is observed, it adds little beyond prior work;
stop this explanatory branch rather than expanding that result into a paper.
If the new format removes the effect, record the boundary and stop this version;
do not silently search for a format that restores it. If a distinct dissociation
emerges, manually audit examples and the alternative explanations before
proposing one independently specified validation. No second model, additional
sample block, or follow-up starts automatically.

## Run on macOS

In your existing Git checkout (keep all previous run folders):

```bash
git pull --ff-only
python3 -m exception_explanation prepare --config configs/explanation.json --output runs/explanation-001
open runs/explanation-001/preview.md
```

If this is a new zsh terminal, set your key without printing it:

```zsh
read -s "OPENAI_API_KEY?Paste your OpenAI API key: "
export OPENAI_API_KEY
```

Run the first world, then complete the same fixed plan:

```bash
caffeinate -i python3 -m exception_explanation run --config configs/explanation.json --output runs/explanation-001 --max-calls 16
caffeinate -i python3 -m exception_explanation run --config configs/explanation.json --output runs/explanation-001 --max-calls 384 --resume
```

After an error-free first block, the second command makes only 368 further calls.
For a transport failure, use that resume command with `--retry-errors`; prior
returned answers are skipped. The total never exceeds 400 journaled attempts.
If an incomplete response blocks the run or the total cap is reached, keep the
folder and inspect its report; do not restart to replace unwanted results.

```bash
python3 -m exception_explanation analyze --output runs/explanation-001
open runs/explanation-001/summary.md
zip -r explanation-001.zip runs/explanation-001
```

Send the ZIP for interpretation. It contains prompts, raw responses, scoring,
and usage; the runner does not save your API key. `prepare` and `analyze` make
zero API calls. Python 3.10+ and the standard library suffice. Linux users omit
`caffeinate -i` and open files with their usual viewer. If using a downloaded
source ZIP, get the updated source into a separate folder and retain all old
run folders; `git pull` requires a Git checkout.

For offline software checks only, use `--mock` with a separate output directory.
Mock outputs and summaries are marked simulated and cannot be mixed with a
live run. The default mock answers all visible records correctly; it does not
manufacture evidence for the research hypothesis.
