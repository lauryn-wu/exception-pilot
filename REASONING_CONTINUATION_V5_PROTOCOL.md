# Study 2 v5: evidence erasure, evidence overriding and conditional text interventions

Protocol `study2-evidence-interventions-v5`. All v3/v4 and Qwen length/expanded-screen
observations are development evidence, never v5 confirmation. Code, configurations,
plans and all execution stages are separately versioned. No retrospective prompt or
threshold tuning after v5 outcomes or interventions. Mock fixtures are not evidence.

## Questions and claims

Behavioral: matched explanation instructions reduce accuracy relative to direct
answers under the original question. Secondary: explicit lookup framing attenuates
that penalty (interaction). Trajectory: verified-minus-pattern conditional log odds
change between initial and pre-answer prefixes. Intervention: value-blind repair
changes subsequent accuracy relative to an error-preserving paraphrase.

These are three different claims. Readouts are relative complete-sequence scores,
not calibrated probabilities or latent beliefs. Controlled prefix edits do not
restore an internal state or prove that the original statement caused an error.
Semantic before/after changes are descriptive, not sentence-level causal effects.

## Frozen originals

12 selection worlds (96 originals) and 48 independent confirmation worlds (384).
Each world: two target values × original/explicit-lookup question × direct/visible
instruction. Preserve the original introduction, question and instructions verbatim.
Lookup changes only the question to “According to the table, what is the value in
the Verified class column for license plate [TARGET]?” Same tables and targets.
10 vehicles; target last; four same-climate peers unanimously suggest the third
class, conflicting with both target variants. Six class-role permutations × two
climates, once in selection/four times in confirmation. Fresh seeds 20261015051/52,
V5S/V5C plate namespaces, deterministic shuffled worlds and eight cells per world.
No old worlds or trajectories are imported.

Pinned Qwen3-32B revision `9216db5781bf21249d130ec9da846c4624c16137` for weights
and tokenizer, BF16/unquantized, eager Hugging Face backend, greedy single sequence,
`enable_thinking=False`. The official empty closed thinking block stays in the
original rendered prompt. No new chat turn, hidden-thinking access, answer cues,
probes, judges or edits during original generation. Both instructions receive
**2048** tokens. The legacy loader config retains 512 solely for compatibility;
explicit v5 scientific request budgets override it. Never relabel the old config.

Record full IDs, text, EOS/finish, exact boundaries, source/model/backend fingerprint
and CUDA-synchronized timing. Preserve failed/invalid/truncated outputs, never
resample them. The terminal parser accepts plain `ANSWER: A` and balanced bold
whole-line, label or marker equivalents for A/B/C; it never infers from prose.
Truncated/no-terminal-answer correctness is unknown. Strict terminal syntax is
reported separately; strict direct compliance also requires a one-line response.

Original-framing selection gate: at least 20/24 tolerant direct correct; at least
3 matched direct-correct/visible-wrong answers equal to the pattern class across
at least 2 worlds, after the complete 96-original collection. Lookup observations
cannot satisfy this gate. This is a predeclared analogue, not a guaranteed outcome.
It does not establish 2B eligibility. Family M needs at least 2 reviewed worlds;
Family O needs at least 2 clean-override worlds for selection-stage authorization.
These are minimal coverage rules, not power guarantees. Unsupported families stay
disabled in confirmation; explicit rationale and protocol lock are required.

## Technical validation and execution

Fresh v5 validation on the new Pod, irrespective of v4's result: reuse v4's three
non-scientific prompts, 128-token original and two identical-input fresh-prefill
repeats at eligible k=0,1,8,16,32. At most 33 calls/3882 tokens per run. Require
identical repeated tokens/finish, finite full-vocabulary telemetry (151936 live),
argmax agreement, probability allclose (atol 1e-5, rtol .001), TV ≤ .0001. Raw
logits and original-versus-fresh suffix differences are diagnostic only. No old
incremental-KV/fresh exact gate. Frozen new backend identity must match every stage.

Separate commands: prepare, offline preflight, validate, first-four-world pilot
(32 originals), explicit full selection, summary, review, 2A, family-specific
2B, and explicitly locked confirmation. No command advances to another stage.
Request/start/return/fail files are immutable; ambiguous/failed operations never
resend. Genuine same-input failures block collection. Model/source changes require
a fresh separately reviewed run, never modified frozen plans.

## 2A: disposable preference readouts

Visible trajectories only: fixed original-token cuts 0,128,256,512,1024 strictly
before the first line-start eligible ANSWER marker, plus the adjacent exact
pre-answer boundary. Boundaries decode/encode exactly; whitespace-only adjacency
is permitted and documented. No answer marker means pre-answer unavailable, while
eligible fixed cuts remain. A partial/Markdown marker is conservatively treated as
a boundary; never use later original tokens. Cut zero may coincide with pre-answer;
this yields a zero-change pair and remains explicit, not silently discarded.

Independently annotate first correct target-value acknowledgment, first erasure,
first conflict acknowledgment, first actual overriding justification. Measure both
sides of each eligible event. Use the same saved original IDs, disposable frozen
`\nANSWER:` and `\nFinal answer:` cues, and full ` A\n`, ` B\n`, ` C\n`
sequence log probabilities (sums, not length normalized). Normalize over these
three candidates, record raw scores, candidate/cue IDs, preferred class, and
verified-minus-pattern log odds. No generated/sampled answers. Deduplicate exact
(task, cut, cue) within one combined fixed+event plan; separate plans are not free.

Primary: original-framing pre-answer minus initial log odds, averaged across both
variants then worlds; only worlds with both complete pairs enter point estimates.
Lookup is secondary. Intermediate cuts, event deltas, outcome strata and cue
differences are descriptive. Report unavailable reasons, complete pair/world
coverage, and both cue results. Events are selected without seeing readouts.

## Semantic review and cohorts

Every visible response is reviewed, including correct, wrong, invalid, truncated,
and unavailable originals. Two independently named reviewers receive only the
original prompt and pre-answer text, no parsed final answer, scores, continuations
or outcomes. Blinding cannot conceal implications already present in the reasoning.
Human/judge-authored structured review files are supported; this implementation
uses manual imports and makes **zero paid judge calls**. Disagreements require a
third independent adjudicator. All independent decisions and negatives persist.
Use exact Unicode spans, unique 40-character context anchors, first-occurrence
certification, and explicit absent/present/uncertain/excluded/invalid statuses.
No keyword detector is treated as semantic evidence.

M: falsely assert target verified evidence absent/unavailable, including prose
absence and `?`/blank/unknown reconstructed cells. Exclude hypotheticals, negation,
other vehicles, prediction uncertainty and conflict-only statements. Mis-copying a
class as a different class is a distinct observational subtype, never automatic M.
O: a correct acknowledgment followed by an explicit argument preferring an inferred
class over the recorded class. Conflict or wrong final answer alone is insufficient.
Record clean, earlier-erasure mixed, or uncertain-erasure-history strata. O's primary
cohort is **clean overrides**; never silently pool mixed cases into it. Retain both
family events when present in one trajectory, grouped in the same world.

## 2B-M and 2B-O

Per eligible event, freeze exact statement and edit span, four complete prefix
texts/IDs, deterministic order, semantic verification and source identity before
any intervention. For reconstructed cells the selected event may be the verified
cell span, with its unique row context visible to reviewers. Four arms: unchanged;
meaning-preserving but different erroneous paraphrase; value-blind correction with
no class/hint; explicit correction supplying the verified value. An independent
verifier must certify all semantic, grammar, no-leakage and structure checks against
the exact draft hash. Lexical checks supplement, never replace, semantic judgment.
Value-blind checks exclude any standalone class label or alternative suggestion.
Meaning controls may retain a correct label already present in an override, but
may not newly introduce it. Table edits stay single cells; exclude impossible edits.

Re-encode the entire edited prefix with the exact source tokenizer. No unexpected
special IDs; decoded text and prompt+prefix concatenation must match. Unchanged
IDs must equal the original prefix IDs. All edits preserve every character outside
one shared span. Budget for every arm is **2048-original_k**, even when prefix length
changes; record length deltas. Independent fresh calls, no supplied caches, future
original tokens or extra prompts. Original/unchanged suffix agreement is descriptive
only. Independent full-candidate readouts (both cues) measure post-prefix preference;
these never enter arm generation. Unavailable arms affect only their own contrasts.

Primary for each family: value-blind minus meaning-control tolerant accuracy.
Secondary: blind-minus-unchanged, meaning-minus-unchanged, explicit-minus-unchanged,
explicit-minus-blind; all analogous conditional log-odds contrasts and strict-format
scoring are secondary. Explicit-only improvement may simply supply the answer.

## Denominators and statistics

Equal weight per independent world; within each world average matched cases/variants.
Behavioral point estimates require both variants' pairs for each framing. Interaction
requires all eight cells. 2B point estimates require all frozen cases in a world
for that contrast, without discarding other contrasts. Report prevalence, eligible
worlds, cases/world, both-family dependence, initial outcomes, initially-agreed
sensitivity, strict/tolerant results, semantic exclusions, incomplete arms and
complete-world coverage. Unknown correctness remains [0,1]; aggregate worst/best
bounds across the entire frozen cohort, including failures. No finite bounds are
invented for missing log odds. 10000 deterministic world-bootstrap samples;
95% intervals, with 97.5% intervals for the two family primary accuracy tests
(Bonferroni). Preference is secondary. Degenerate/small-world intervals are flagged;
no automatic significance or adequate-power claim. Additional stratified results
are exploratory. Frozen eligibility is never chosen using 2A shifts or edit effects.

## Separately authorized future pattern-alignment control

Not in the primary schedule. Hold target label, all non-class cells, row order,
framing and instruction fixed. Pair conflict with same-climate peer labels favoring
the target. Exact class marginals cannot generally be held while changing all four
peers to a target label occurring only 2–4 times among non-targets. Predeclare a
**majority-alignment** version: use compensating swaps with opposite-climate peers
where at least 3 copies of the target label are available; freeze which three same-
climate peers are swapped, preserve global class counts, and record changed opposite-
climate pattern strength. If infeasible for a variant, mark unavailable rather than
changing the target or silently shifting marginals. This is a joint peer-label
redistribution, not a perfectly isolated same-climate manipulation. A separately
reported unanimous-alignment sensitivity changes marginals explicitly. Manipulation
checks: same target/features/order, global counts, same/opposite climate counts,
majority strength, number/positions of changed cells and no answer leakage.
With 12 fresh worlds × two variants × two backgrounds × two framings × two
instructions, ceiling 192 originals/393216 generated tokens per alignment design;
confirmation 48 worlds gives 768/1572864. Requires new plan and authorization;
no collection command implements or starts it. Row-position, new domains and other
models likewise remain future validation. Strong pattern-specific causal claims
await these controls.
